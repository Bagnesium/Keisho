"""Prospective cumulative Git patch export; runs inside the owned container.

This module deliberately uses only the standard library so its exact source can
be executed in the isolated repository without installing Keisho there.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

VERSION = 'source-and-artifacts/2.0'
CACHE_DIRECTORIES = frozenset(('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.hypothesis'))


def excluded_reason(path):
    parts = PurePosixPath(path).parts
    if '__pycache__' in parts:
        return 'python-bytecode-cache-directory'
    if path.endswith(('.pyc', '.pyo')):
        return 'python-bytecode-file'
    if any(part in CACHE_DIRECTORIES for part in parts):
        return 'documented-test-cache-directory'
    return None


def export_cumulative_patch(root, base):
    """Return patch plus complete exclusion audit, or an audited rejection.

    Ignored and untracked files are eligible. Binary contents are eligible. A
    changed tracked cache path rejects the whole export instead of silently
    dropping a potentially intentional edit. Git's original index is untouched.
    """
    audit = {'policy': VERSION, 'base_commit': base, 'validation_result': 'rejected',
             'rejection_reason': None, 'excluded_paths': [], 'included_changed_paths': [],
             'official_base_apply_check': {'status': 'not_run'}, 'disabled_filter_keys': [],
             'byte_preservation_check': {'status': 'not_run', 'mismatched_paths': []}}
    result = {'patch': None, 'audit': audit}
    try:
        if not isinstance(base, str) or not re.fullmatch('[a-f0-9]{40}', base):
            raise ValueError('invalid official base commit')
        root = Path(root)
        if root.is_symlink() or not root.is_dir():
            raise ValueError('unsafe repository root')
        root = root.resolve()
        if (root / '.git').is_symlink() or not (root / '.git').is_dir():
            raise ValueError('Git metadata must be a local directory')
        environment = dict(os.environ)
        for key in ('GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
            environment.pop(key, None)
        base_command = ['git', '--literal-pathspecs', '-C', str(root), '-c', 'core.fsmonitor=false',
                        '-c', 'core.hooksPath=/dev/null', '-c', 'core.autocrlf=false',
                        '-c', 'core.safecrlf=false', '-c', 'core.filemode=true']
        # Staging must not execute configured programs or normalize source
        # bytes. Disable repository/global/environment clean/process drivers.
        drivers = subprocess.run(base_command + ['config', '--null', '--name-only', '--get-regexp',
                                 r'^filter\..*\.(clean|smudge|process|required)$'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, check=False)
        if drivers.returncode not in (0, 1):
            raise ValueError('Git filter configuration query failed')
        filter_overrides = []
        for encoded in drivers.stdout.split(b'\0'):
            if not encoded:
                continue
            key = encoded.decode('utf-8')
            if not re.fullmatch(r'filter\.[A-Za-z0-9_.-]+\.(clean|smudge|process|required)', key):
                raise ValueError('unsupported Git filter name')
            filter_overrides.extend(('-c', key + ('=false' if key.endswith('.required') else '=')))
            audit['disabled_filter_keys'].append(key)
        audit['disabled_filter_keys'] = sorted(set(audit['disabled_filter_keys']))

        def git(*args, input=None, env=None):
            command = [*base_command, *filter_overrides, *args]
            completed = subprocess.run(command, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       env=environment if env is None else env, check=False)
            if completed.returncode:
                raise ValueError('Git patch operation failed: ' + completed.stderr.decode(errors='replace')[-2000:])
            return completed.stdout

        if Path(os.fsdecode(git('rev-parse', '--show-toplevel').rstrip(b'\n'))).resolve() != root:
            raise ValueError('Git worktree escapes repository')
        git_dir = Path(os.fsdecode(git('rev-parse', '--absolute-git-dir').rstrip(b'\n')))
        if git_dir.resolve() != root / '.git':
            raise ValueError('Git metadata escapes repository')
        tree = {}
        for record in git('ls-tree', '-r', '-z', base).split(b'\0'):
            if record:
                metadata, path = record.split(b'\t', 1)
                mode, kind, blob = metadata.split(b' ')
                if kind != b'blob':
                    raise ValueError('submodules are unsupported by safe patch export')
                tree[os.fsdecode(path)] = (mode.decode(), blob.decode())
        tracked = {os.fsdecode(path) for path in git('ls-files', '-z').split(b'\0') if path}
        present = set()
        for directory, dirs, files in os.walk(root, followlinks=False):
            if directory == str(root):
                dirs[:] = [name for name in dirs if name != '.git']
                files = [name for name in files if name != '.git']
            for name in list(dirs):
                path = Path(directory) / name
                if path.is_symlink():
                    present.add(path.relative_to(root).as_posix())
                    dirs.remove(name)
                elif name == '.git':
                    raise ValueError('nested Git metadata is unsupported')
            present.update((Path(directory) / name).relative_to(root).as_posix() for name in files)

        def safe(path):
            pure = PurePosixPath(path)
            if (not path or pure.is_absolute() or pure.as_posix() != path or '\\' in path or '\x00' in path
                    or any(part in ('.', '..', '.git') for part in path.split('/'))):
                raise ValueError('unsafe patch path: ' + repr(path))
            path.encode('utf-8')
            absolute = root / path
            for parent in absolute.parents:
                if parent == root:
                    break
                if parent.is_symlink():
                    raise ValueError('symlink parent in patch path: ' + repr(path))
            if absolute.is_symlink():
                # Git stages the link bytes, never its target. Containment and
                # metadata checks still apply, including for excluded caches.
                target = absolute.resolve()
                try:
                    relative = target.relative_to(root)
                except ValueError:
                    raise ValueError('symlink escapes repository: ' + repr(path)) from None
                if '.git' in relative.parts:
                    raise ValueError('symlink reaches Git metadata: ' + repr(path))
            elif absolute.exists() and not absolute.is_file():
                raise ValueError('non-regular patch path: ' + repr(path))
            return absolute

        selected = []
        ambiguous = []
        for path in sorted(set(tree) | tracked | present):
            absolute = safe(path)
            reason = excluded_reason(path)
            if reason is None:
                if path in tree or path in present:
                    selected.append(path)
                continue
            current_mode = current_blob = None
            exists = path in present
            if exists and path in tree:
                if absolute.is_symlink():
                    content = os.fsencode(os.readlink(absolute))
                    current_mode = '120000'
                else:
                    content = absolute.read_bytes()
                    current_mode = '100755' if absolute.stat().st_mode & stat.S_IXUSR else '100644'
                current_blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            changed_tracked = (path in tree and tree[path] != (current_mode, current_blob)) or (path in tracked and path not in tree)
            audit['excluded_paths'].append({'path': path, 'reason': reason, 'tracked_at_base': path in tree,
                                           'tracked_in_original_index': path in tracked, 'worktree_present': exists,
                                           'changed_tracked_path': changed_tracked})
            if changed_tracked:
                ambiguous.append(path)
        if ambiguous:
            raise ValueError('changed tracked cache paths require explicit review: ' + repr(ambiguous))

        with tempfile.TemporaryDirectory(prefix='keisho-patch-export-') as temporary:
            export_environment = {**environment, 'GIT_INDEX_FILE': str(Path(temporary) / 'index')}
            git('read-tree', base, env=export_environment)
            if selected:
                payload = b'\0'.join(os.fsencode(path) for path in selected) + b'\0'
                git('add', '--all', '--force', '--pathspec-from-file=-', '--pathspec-file-nul', input=payload, env=export_environment)
            staged = {}
            for record in git('ls-files', '--stage', '-z', env=export_environment).split(b'\0'):
                if record:
                    metadata, encoded = record.split(b'\t', 1)
                    mode, blob, stage = metadata.decode().split()
                    if stage != '0':
                        raise ValueError('unmerged export index')
                    staged[os.fsdecode(encoded)] = (mode, blob)
            mismatches = []
            for path in selected:
                absolute = safe(path)
                raw = None
                if path in present:
                    if absolute.is_symlink():
                        content, mode = os.fsencode(os.readlink(absolute)), '120000'
                    else:
                        content = absolute.read_bytes()
                        mode = '100755' if absolute.stat().st_mode & stat.S_IXUSR else '100644'
                    raw = (mode, hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest())
                if staged.get(path) != raw:
                    mismatches.append({'path': path, 'raw_mode_and_blob': raw,
                                       'staged_mode_and_blob': staged.get(path)})
            audit['byte_preservation_check'] = {'status': 'rejected' if mismatches else 'passed',
                                               'mismatched_paths': mismatches}
            if mismatches:
                raise ValueError('Git attributes or staging changed raw file bytes/modes; export requires review')
            patch_bytes = git('diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--no-textconv',
                              '--no-renames', base, '--', env=export_environment)
            # Changes are relative to the official base, including predecessor
            # edits, subsequent edits, deletions, new ignored files and binaries.
            fields = git('diff', '--cached', '--name-status', '-z', '--no-renames', base, '--', env=export_environment).split(b'\0')
            for index in range(0, len(fields) - 1, 2):
                path = os.fsdecode(fields[index + 1])
                if excluded_reason(path):
                    raise ValueError('excluded path entered staged patch: ' + repr(path))
                audit['included_changed_paths'].append({'path': path, 'status': fields[index].decode()})
            # Verify against a separate, untouched official-base index. This is
            # an export admission check, not an execution of official grading.
            if patch_bytes:
                acceptance_environment = {**environment, 'GIT_INDEX_FILE': str(Path(temporary) / 'acceptance-index')}
                git('read-tree', base, env=acceptance_environment)
                git('apply', '--cached', '--check', '--binary', '-', input=patch_bytes, env=acceptance_environment)
            audit['official_base_apply_check'] = {'status': 'passed', 'empty_patch': not bool(patch_bytes),
                                                  'method': 'git apply --cached --check --binary' if patch_bytes else 'no changes'}
        result['patch'] = patch_bytes.decode('utf-8')
        audit.update(validation_result='accepted', patch_sha256=hashlib.sha256(patch_bytes).hexdigest())
    except (ValueError, UnicodeError, OSError, RuntimeError) as error:
        audit['rejection_reason'] = str(error)
    return result


if __name__ == '__main__':
    print(json.dumps(export_cumulative_patch('.', sys.argv[1]), sort_keys=True))
