"""Offline patch-export fixture; no providers, benchmark launcher or grader."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.benchmark.environment import RepositorySession, docker
from keisho.benchmark.evaluator import write_prediction
from keisho.benchmark.patch_export import VERSION
from keisho.logging.raw import RawRun

# Also executed verbatim inside an owned container, with no copied task data.
FIXTURE = '''import os,pathlib,subprocess,py_compile,shutil
root=pathlib.Path.cwd()
def git(*args):
 return subprocess.run(['git',*args],check=True,capture_output=True).stdout.decode().strip()
def write(name,data):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else data.encode())
git('init','-q');git('config','user.name','offline fixture');git('config','user.email','offline@example.invalid')
write('source.py','value = 1\\n');write('deleted.py','obsolete = True\\n')
write('.gitignore','ignored_source.py\\n__pycache__/\\n.pytest_cache/\\nignored-data.bin\\n')
git('add','-A');git('commit','-qm','official synthetic base');base=git('rev-parse','HEAD')
write('source.py','predecessor = 2\\n');git('add','source.py');git('commit','-qm','predecessor edit after official base')
write('source.py','predecessor = 2\\nsuccessor = 3\\n');write('new_source.py','new = True\\n')
write('ignored_source.py','ignored_but_relevant = True\\n');write('ignored-data.bin',bytes([0,1,254]))
write('fixtures/relevant.bin',bytes([0,2,255]));write('space and\\nnewline.py','unusual_name = True\\n')
write(':literal[abc].py','literal_path = True\\n')
bytecode=root/'__pycache__/source.pyc';bytecode.parent.mkdir();py_compile.compile(str(root/'source.py'),cfile=str(bytecode),doraise=True)
write('nested/__pycache__/another.pyc',bytes([0])+b'untracked');write('standalone.pyo',bytes([0])+b'generated')
write('.pytest_cache/v/cache/nodeids','[]');write('.mypy_cache/3.10/cache.json','{}')
write('.pytest_cache/binary-output.bin',bytes([0,255])+b'generated test result')
write('.ruff_cache/entry',bytes([0])+b'cache');write('.hypothesis/constants/generated','cache')
(root/'deleted.py').unlink()
print(base)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--docker-image')
    arguments = parser.parse_args()
    out = arguments.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'fixture.py').write_text(FIXTURE)
    repo = out / 'dirty-repository'
    repo.mkdir()
    setup = subprocess.run([sys.executable, '-c', FIXTURE], cwd=repo, capture_output=True, check=True)
    base = setup.stdout.decode().strip()
    original_index = hashlib.sha256((repo / '.git/index').read_bytes()).hexdigest()
    status = subprocess.run(['git', 'status', '--short', '--untracked-files=all', '--ignored'], cwd=repo,
                            capture_output=True, check=True)
    (out / 'dirty-status.txt').write_bytes(status.stdout)
    audit = RawRun(out / 'audit', 'host-export')
    session = RepositorySession.__new__(RepositorySession)
    session.patch_export_policy, session.audit = VERSION, audit
    session.command = lambda command: subprocess.run(['/bin/bash', '-c', command], cwd=repo,
        env={**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null'}, capture_output=True)
    patch = session.patch(base)
    (out / 'cumulative.patch').write_text(patch)
    write_prediction(out / 'prediction.jsonl', {'instance_id': 'offline-synthetic'}, 'frozen-model', patch)
    acceptance = out / 'independent-base-checkout'
    subprocess.run(['git', 'clone', '-q', '--no-local', str(repo), str(acceptance)], check=True)
    subprocess.run(['git', 'checkout', '-q', base], cwd=acceptance, check=True)
    subprocess.run(['git', 'apply', '--check', '-'], cwd=acceptance, input=patch.encode(), check=True)
    subprocess.run(['git', 'apply', '-'], cwd=acceptance, input=patch.encode(), check=True)
    assert (acceptance / 'source.py').read_text() == 'predecessor = 2\nsuccessor = 3\n'
    assert (acceptance / 'ignored_source.py').is_file()
    assert (acceptance / 'ignored-data.bin').read_bytes() == bytes([0, 1, 254])
    assert not (acceptance / 'deleted.py').exists()
    assert not (acceptance / '__pycache__').exists()
    assert original_index == hashlib.sha256((repo / '.git/index').read_bytes()).hexdigest()
    record = {'scope': 'offline synthetic Git patch export only', 'policy': VERSION, 'base_commit': base,
              'provider_calls': 0, 'benchmark_executions': 0, 'functional_confirmations': 0,
              'host_git_apply_check': 'passed', 'independent_source_and_binary_acceptance': 'passed',
              'original_index_unchanged': True, 'included_paths': session.patch_export_audit['included_changed_paths'],
              'excluded_paths': session.patch_export_audit['excluded_paths'],
              'byte_preservation_check': session.patch_export_audit['byte_preservation_check'],
              'disabled_filter_keys': session.patch_export_audit['disabled_filter_keys']}
    if arguments.docker_image:
        container_audit = RawRun(out / 'audit', 'docker-export')
        container = RepositorySession(arguments.docker_image, audit=container_audit, patch_export_policy=VERSION)
        try:
            reset = "import pathlib,shutil; p=pathlib.Path('/testbed'); shutil.rmtree(p); p.mkdir()"
            docker('exec', container.name, 'python3', '-c', reset)
            response = container.command('python3 -c ' + shlex.quote(FIXTURE))
            assert response.returncode == 0, response.stderr.decode(errors='replace')
            docker_base = response.stdout.decode().strip()
            container_patch = container.patch(docker_base)
            (out / 'docker-cumulative.patch').write_text(container_patch)
            container_audit.write_artifact('fixture.json', {'image_id': arguments.docker_image,
                'base_commit': docker_base, 'public_fixture_only': True, 'fixture_sha256': hashlib.sha256(FIXTURE.encode()).hexdigest()})
            # The real repository exporter has run; inspect actual patch and
            # separately apply it to its base inside the same owned container.
            check = "import pathlib,subprocess,base64; root=pathlib.Path('/tmp/keisho-export-acceptance'); subprocess.run(['git','clone','-q','--no-local','/testbed',str(root)],check=True); subprocess.run(['git','checkout','-q'," + repr(docker_base) + "],cwd=root,check=True); patch=base64.b64decode(" + repr(__import__('base64').b64encode(container_patch.encode()).decode()) + "); subprocess.run(['git','apply','--check','-'],cwd=root,input=patch,check=True); subprocess.run(['git','apply','-'],cwd=root,input=patch,check=True); assert (root/'source.py').read_text()=='predecessor = 2\\nsuccessor = 3\\n'; assert (root/'ignored_source.py').is_file(); assert (root/'ignored-data.bin').read_bytes()==bytes([0,1,254]); assert not (root/'deleted.py').exists(); assert not (root/'__pycache__').exists(); print('git-apply-check and independent acceptance passed')"
            checked = docker('exec', container.name, 'python3', '-c', check)
            (out / 'docker-acceptance.txt').write_bytes(checked.stdout + checked.stderr)
            record['docker'] = {'image_id': arguments.docker_image, 'owned_container': container.name,
                 'base_commit': docker_base, 'git_apply_check': 'passed', 'independent_acceptance': 'passed',
                 'included_paths': container.patch_export_audit['included_changed_paths'],
                 'excluded_paths': container.patch_export_audit['excluded_paths'],
                 'byte_preservation_check': container.patch_export_audit['byte_preservation_check'],
                 'disabled_filter_keys': container.patch_export_audit['disabled_filter_keys']}
        finally:
            container.close()
    record['source_sha256'] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
        ('src/keisho/benchmark/environment.py', 'src/keisho/benchmark/patch_export.py', 'tests/test_patch_export.py')}
    (out / 'RESULT.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'result': str(out / 'RESULT.json'), 'included_count': len(record['included_paths']),
                      'excluded_count': len(record['excluded_paths']), 'docker': bool(arguments.docker_image)}))


if __name__ == '__main__':
    main()
