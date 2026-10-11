"""Offline real-Git regressions for prospective cumulative patch export."""
import json
import os
from pathlib import Path
import py_compile
import shlex
import subprocess
import sys
import tempfile
import unittest

from keisho.benchmark.environment import RepositorySession
from keisho.benchmark.patch_export import VERSION, export_cumulative_patch
from keisho.benchmark.evaluator import write_prediction
from keisho.core import ValidationError
from keisho.logging.raw import RawRun


class PatchExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repository'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'offline fixture')
        self.git('config', 'user.email', 'offline@example.invalid')
        self.write('source.py', 'value = 1\n')
        self.write('deleted.py', 'obsolete = True\n')
        self.write('.gitignore', 'ignored_source.py\n__pycache__/\n.pytest_cache/\nignored-data.bin\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'official synthetic base')
        self.base = self.git('rev-parse', 'HEAD').stdout.decode().strip()

    def git(self, *args, repo=None, check=True, input=None):
        return subprocess.run(['git', '-C', str(repo or self.repo), *args], input=input,
                              check=check, capture_output=True)

    def write(self, path, contents):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents if isinstance(contents, bytes) else contents.encode())

    def session(self, *, audit=None, policy=VERSION):
        session = RepositorySession.__new__(RepositorySession)
        session.patch_export_policy = policy
        session.audit = audit
        session.command = lambda command: subprocess.run(['/bin/bash', '-c', command], cwd=self.repo,
                env={**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null'}, capture_output=True)
        return session

    def dirty(self):
        self.write('source.py', 'predecessor = 2\n')
        self.git('add', 'source.py')
        self.git('commit', '-qm', 'predecessor edit after official base')
        self.write('source.py', 'predecessor = 2\nsuccessor = 3\n')
        self.write('new_source.py', 'new = True\n')
        self.write('ignored_source.py', 'ignored_but_relevant = True\n')
        self.write('ignored-data.bin', b'\x00\x01\xfe')
        self.write('fixtures/relevant.bin', b'\x00\x02\xff')
        self.write('space and\nnewline.py', 'unusual_name = True\n')
        self.write(':literal[abc].py', 'literal_path = True\n')
        bytecode = self.repo / '__pycache__/source.cpython-310.pyc'
        bytecode.parent.mkdir()
        py_compile.compile(str(self.repo / 'source.py'), cfile=str(bytecode), doraise=True)
        self.write('nested/__pycache__/another.pyc', b'\x00untracked')
        self.write('standalone.pyo', b'\x00generated')
        self.write('.pytest_cache/v/cache/nodeids', '[]')
        self.write('.pytest_cache/binary-output.bin', b'\x00\xffgenerated test result')
        self.write('.mypy_cache/3.10/cache.json', '{}')
        self.write('.ruff_cache/entry', b'\x00cache')
        self.write('.hypothesis/constants/generated', 'cache')
        (self.repo / 'deleted.py').unlink()

    def test_real_export_preserves_cumulative_changes_and_excludes_ignored_untracked_caches(self):
        self.dirty()
        original_index = (self.repo / '.git/index').read_bytes()
        raw = RawRun(self.root / 'audit', 'dirty-export')
        session = self.session(audit=raw)
        patch = session.patch(self.base)
        self.assertEqual((self.repo / '.git/index').read_bytes(), original_index)
        self.assertIn('+predecessor = 2', patch)
        self.assertIn('+successor = 3', patch)
        self.assertIn('new_source.py', patch)
        self.assertIn('ignored_source.py', patch)
        self.assertIn('deleted file mode', patch)
        self.assertIn('GIT binary patch', patch)
        self.assertNotIn('__pycache__', patch)
        self.assertNotIn('.pytest_cache', patch)
        self.assertNotIn('.pyo', patch)
        audit = json.loads((raw.path / 'patch-export-001.json').read_text())
        self.assertEqual(audit, session.patch_export_audit)
        self.assertEqual(audit['validation_result'], 'accepted')
        self.assertEqual(audit['byte_preservation_check']['status'], 'passed')
        self.assertEqual(audit['official_base_apply_check']['status'], 'passed')
        self.assertFalse(audit['official_base_apply_check']['empty_patch'])
        excluded = {row['path'] for row in audit['excluded_paths']}
        self.assertEqual(excluded, {'__pycache__/source.cpython-310.pyc', 'nested/__pycache__/another.pyc',
                 'standalone.pyo', '.pytest_cache/v/cache/nodeids', '.pytest_cache/binary-output.bin', '.mypy_cache/3.10/cache.json',
                 '.ruff_cache/entry', '.hypothesis/constants/generated'})
        self.assertTrue(all(not row['changed_tracked_path'] for row in audit['excluded_paths']))
        selected = {row['path'] for row in audit['included_changed_paths']}
        self.assertEqual(selected, {'source.py', 'deleted.py', 'new_source.py', 'ignored_source.py',
                                  'ignored-data.bin', 'fixtures/relevant.bin', 'space and\nnewline.py', ':literal[abc].py'})
        # Independent base checkout proves official Git patch application syntax.
        checkout = self.root / 'acceptance'
        self.git('clone', '-q', '--no-local', str(self.repo), str(checkout), repo=self.root)
        self.git('checkout', '-q', self.base, repo=checkout)
        self.git('apply', '--check', '-', repo=checkout, input=patch.encode())
        self.git('apply', '-', repo=checkout, input=patch.encode())
        self.assertEqual((checkout / 'source.py').read_text(), 'predecessor = 2\nsuccessor = 3\n')
        self.assertFalse((checkout / 'deleted.py').exists())
        self.assertEqual((checkout / 'ignored-data.bin').read_bytes(), b'\x00\x01\xfe')
        self.assertFalse((checkout / '__pycache__').exists())
        prediction = write_prediction(self.root / 'prediction.jsonl', {'instance_id': 'offline-synthetic'}, 'frozen-model', patch)
        self.assertEqual(json.loads((self.root / 'prediction.jsonl').read_text()), prediction)
        self.assertEqual(set(prediction), {'instance_id', 'model_name_or_path', 'model_patch'})
        # A cache created after the first export cannot re-enter via untracked
        # staging; the next export records a fresh, distinct exclusion inventory.
        self.write('untracked-new/__pycache__/fresh.pyc', b'\x00late-generated')
        self.assertEqual(session.patch(self.base), patch)
        self.assertTrue((raw.path / 'patch-export-002.json').is_file())
        second = json.loads((raw.path / 'patch-export-002.json').read_text())
        self.assertIn('untracked-new/__pycache__/fresh.pyc', {row['path'] for row in second['excluded_paths']})

    def test_default_legacy_behavior_is_preserved(self):
        self.write('__pycache__/generated.pyc', b'\x00bytecode')
        self.write('unignored.pyc', b'\x00bytecode')
        session = self.session(policy='legacy')
        self.assertIn('unignored.pyc', session.patch(self.base))
        self.assertFalse(hasattr(session, 'patch_export_audit'))

    def test_unchanged_tracked_cache_is_preserved_at_base_but_edits_and_deletion_reject(self):
        self.write('fixtures/tracked.pyc', b'\x00intentional fixture')
        self.git('add', '-f', 'fixtures/tracked.pyc')
        self.git('commit', '-qm', 'tracked fixture baseline')
        self.base = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.write('source.py', 'legitimate = True\n')
        exported = export_cumulative_patch(self.repo, self.base)
        self.assertEqual(exported['audit']['validation_result'], 'accepted')
        self.assertNotIn('tracked.pyc', exported['patch'])
        for modification in ('edit', 'delete'):
            with self.subTest(modification=modification):
                if modification == 'edit':
                    self.write('fixtures/tracked.pyc', b'\x00changed fixture')
                else:
                    (self.repo / 'fixtures/tracked.pyc').unlink()
                exported = export_cumulative_patch(self.repo, self.base)
                self.assertIsNone(exported['patch'])
                self.assertIn('require explicit review', exported['audit']['rejection_reason'])
                self.assertTrue(exported['audit']['excluded_paths'][0]['changed_tracked_path'])

    def test_new_staged_cache_rejects_and_preserves_audit(self):
        self.write('__pycache__/new.pyc', b'\x00intentional-or-generated')
        self.git('add', '--force', '__pycache__/new.pyc')
        raw = RawRun(self.root / 'audit', 'rejected-export')
        session = self.session(audit=raw)
        with self.assertRaisesRegex(ValidationError, 'require explicit review'):
            session.patch(self.base)
        self.assertEqual(json.loads((raw.path / 'patch-export-001.json').read_text())['validation_result'], 'rejected')

    def test_deleted_new_staged_source_does_not_create_an_invalid_pathspec(self):
        self.write('transient.py', 'temporary = True\n')
        self.git('add', 'transient.py')
        (self.repo / 'transient.py').unlink()
        session = self.session()
        self.assertEqual(session.patch(self.base), '')
        self.assertEqual(session.patch_export_audit['official_base_apply_check']['status'], 'passed')
        self.assertTrue(session.patch_export_audit['official_base_apply_check']['empty_patch'])

    def test_safe_symlink_is_exported_without_following_target(self):
        (self.repo / 'safe-link.py').symlink_to('source.py')
        patch = self.session().patch(self.base)
        self.assertIn('new file mode 120000', patch)
        self.assertIn('+source.py', patch)
        self.assertNotIn('+value = 1', patch)

    def test_unsafe_symlinks_reject_including_excluded_paths_and_parent_replacement(self):
        for path, target in (('escape.py', '/etc/passwd'), ('git-link', '.git/config'),
                             ('__pycache__', '/tmp'), ('source.py', '/etc/passwd')):
            with self.subTest(path=path):
                absolute = self.repo / path
                saved = absolute.read_bytes() if absolute.exists() else None
                if saved is not None:
                    absolute.unlink()
                absolute.symlink_to(target)
                exported = export_cumulative_patch(self.repo, self.base)
                self.assertEqual(exported['audit']['validation_result'], 'rejected')
                self.assertIn('symlink', exported['audit']['rejection_reason'])
                absolute.unlink()
                if saved is not None:
                    absolute.write_bytes(saved)

    def test_git_metadata_alias_and_nested_git_reject(self):
        metadata = self.repo / '.git'
        metadata.rename(self.repo / 'moved-git')
        metadata.symlink_to('moved-git')
        self.assertIn('local directory', export_cumulative_patch(self.repo, self.base)['audit']['rejection_reason'])
        metadata.unlink()
        (self.repo / 'moved-git').rename(metadata)
        (self.repo / 'nested/.git').mkdir(parents=True)
        self.assertIn('nested Git metadata', export_cumulative_patch(self.repo, self.base)['audit']['rejection_reason'])

    def test_symlink_parent_of_base_tracked_file_rejects_even_when_target_is_inside(self):
        self.write('package/source.py', 'base = True\n')
        self.git('add', 'package/source.py')
        self.git('commit', '-qm', 'package baseline')
        self.base = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        (self.repo / 'package/source.py').unlink()
        (self.repo / 'package').rmdir()
        (self.repo / 'other').mkdir()
        (self.repo / 'package').symlink_to('other')
        exported = export_cumulative_patch(self.repo, self.base)
        self.assertEqual(exported['audit']['validation_result'], 'rejected')
        self.assertIn('symlink parent', exported['audit']['rejection_reason'])

    def test_unsafe_path_and_invalid_base_reject(self):
        self.write('back\\slash.py', 'bad_path = True\n')
        self.assertIn('unsafe patch path', export_cumulative_patch(self.repo, self.base)['audit']['rejection_reason'])
        for base in ('HEAD', '../escape', 'a' * 39, 'z' * 40):
            with self.subTest(base=base):
                exported = export_cumulative_patch(self.repo, base)
                self.assertEqual(exported['audit']['validation_result'], 'rejected')
                self.assertEqual(exported['audit']['rejection_reason'], 'invalid official base commit')

    def test_configured_filters_never_execute_and_source_bytes_are_preserved(self):
        marker = self.root / 'filter-executed'
        filter_script = self.root / 'hostile-filter.py'
        filter_script.write_text("import pathlib,sys; pathlib.Path(" + repr(str(marker)) +
                                 ").write_text('ran'); sys.stdout.buffer.write(b'silently transformed\\n')")
        command = shlex.quote(sys.executable) + ' ' + shlex.quote(str(filter_script))
        for operation in ('clean', 'smudge', 'process'):
            self.git('config', 'filter.hostile.' + operation, command)
        self.git('config', 'filter.hostile.required', 'true')
        self.git('config', 'core.autocrlf', 'true')
        self.write('.gitattributes', '*.py filter=hostile\n')
        original = b'raw_source = True\r\nsecond = 2\r\n'
        self.write('source.py', original)
        self.write('ignored_source.py', b'ignored_source = True\r\n')
        session = self.session()
        patch = session.patch(self.base)
        self.assertFalse(marker.exists(), 'clean/process/smudge programs must never execute')
        self.assertEqual((self.repo / 'source.py').read_bytes(), original)
        audit = session.patch_export_audit
        self.assertEqual(audit['byte_preservation_check']['status'], 'passed')
        self.assertEqual(audit['disabled_filter_keys'], ['filter.hostile.clean', 'filter.hostile.process',
                                                       'filter.hostile.required', 'filter.hostile.smudge'])
        acceptance = self.root / 'filter-acceptance'
        self.git('clone', '-q', '--no-local', str(self.repo), str(acceptance), repo=self.root)
        self.git('checkout', '-q', self.base, repo=acceptance)
        self.git('apply', '--check', '-', repo=acceptance, input=patch.encode())
        self.git('apply', '-', repo=acceptance, input=patch.encode())
        self.assertEqual((acceptance / 'source.py').read_bytes(), original)
        self.assertEqual((acceptance / 'ignored_source.py').read_bytes(), b'ignored_source = True\r\n')
        self.assertFalse(marker.exists())

    def test_attribute_forced_normalization_rejects_instead_of_silently_changing_bytes(self):
        self.git('config', 'core.autocrlf', 'true')
        self.write('.gitattributes', 'source.py text\n')
        original = b'raw_source = True\r\n'
        self.write('source.py', original)
        exported = export_cumulative_patch(self.repo, self.base)
        self.assertIsNone(exported['patch'])
        self.assertEqual(exported['audit']['validation_result'], 'rejected')
        self.assertEqual(exported['audit']['byte_preservation_check']['status'], 'rejected')
        self.assertEqual([row['path'] for row in exported['audit']['byte_preservation_check']['mismatched_paths']], ['source.py'])
        self.assertIn('changed raw file bytes/modes', exported['audit']['rejection_reason'])
        self.assertEqual((self.repo / 'source.py').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
