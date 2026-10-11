"""Docker-only repository tools for the existing Keisho text-action loop.

No host bind mounts, network, credentials, socket, evaluator files or archive.
Image snapshots preserve the installed environment in independent writable layers.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import uuid

from keisho.core import require
from keisho.environments.base import safe_relative_path
from keisho.pilot.tools import InvalidAction
from .vendor.signals import is_source_file
from .listing import BoundedListing, VERSION as LISTING_VERSION, parameters as listing_parameters
from .patch_export import VERSION as PATCH_EXPORT_VERSION

INVENTORY = '''import os,json,hashlib,stat
rows={}
for root,dirs,files in os.walk('/testbed'):
 dirs[:]=[d for d in dirs if d not in ('.git','__pycache__','.pytest_cache') and not d.endswith('.egg-info')]
 for name in files:
  p=os.path.join(root,name); r=os.path.relpath(p,'/testbed'); s=os.lstat(p)
  if stat.S_ISLNK(s.st_mode): rows[r]={'sha256':hashlib.sha256(os.readlink(p).encode()).hexdigest(),'mode':s.st_mode,'symlink':True}
  elif stat.S_ISREG(s.st_mode) and not name.endswith(('.pyc','.pyo')):
   rows[r]={'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'mode':stat.S_IMODE(s.st_mode)}
print(json.dumps(rows,sort_keys=True))'''


def docker(*args, input=None, timeout=180, check=True):
    r = subprocess.run(['docker', *args], input=input, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    if check:
        require(r.returncode == 0, 'Docker operation failed: ' + r.stderr.decode(errors='replace')[-2000:])
    return r


def run_arguments(image, name):
    require(re.fullmatch(r'sha256:[a-f0-9]{64}', image), 'use immutable image ID')
    return ['run', '-d', '--name', name, '--network', 'none', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '256',
            '--memory', '4g', '--cpus', '2', '--entrypoint', '/bin/sleep', image, 'infinity']


class RepositorySession:
    def __init__(self, image, *, timeout=120, output_bytes=49152, audit=None, listing_policy='legacy', patch_export_policy='legacy'):
        require(listing_policy in ('legacy',LISTING_VERSION),'unsupported listing policy')
        require(patch_export_policy in ('legacy',PATCH_EXPORT_VERSION),'unsupported patch export policy')
        self.listing_policy=listing_policy
        self.patch_export_policy=patch_export_policy
        self.listings=BoundedListing()
        self.name = 'keisho-agent-' + uuid.uuid4().hex
        self.image = image
        self.timeout, self.output_bytes = timeout, output_bytes
        self.audit, self.actions = audit, 0
        docker(*run_arguments(image, self.name))
        inspection = json.loads(docker('inspect', self.name).stdout)[0]
        require(not inspection['Mounts'] and not inspection['HostConfig']['Privileged'] and
                inspection['HostConfig']['NetworkMode'] == 'none', 'container isolation invariant failed')
        require(not any(re.search(r'(API_KEY|ACCESS_TOKEN|SECRET|PASSWORD)=', s) for s in inspection['Config']['Env']), 'image contains credential environment')

    def command(self, command, timeout=None):
        # Command text is interpreted inside the isolated container only.
        return docker('exec', '-w', '/testbed', self.name, '/usr/bin/timeout', '-s', 'KILL',
                      str(timeout or self.timeout), '/bin/bash', '-lc',
                      'source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed && ' + command,
                      timeout=(timeout or self.timeout) + 15, check=False)

    def inventory(self):
        r = docker('exec', self.name, 'python3', '-c', INVENTORY)
        return json.loads(r.stdout)

    def initialize_base(self, base):
        require(re.fullmatch('[a-f0-9]{40}', base), 'invalid official base commit')
        # The official image may have its synthetic setup commit/history. Replace
        # Git storage with a shallow clone at the official base, including no later refs.
        script = f'''set -e
git reset --hard {base}
git clean -fdx
git clone --depth 1 --no-local --no-hardlinks --single-branch file:///testbed /tmp/keisho-base
git -C /tmp/keisho-base remote remove origin
python3 -c 'import shutil; shutil.rmtree("/testbed/.git"); shutil.copytree("/tmp/keisho-base/.git","/testbed/.git"); shutil.rmtree("/tmp/keisho-base")'
test "$(git rev-parse HEAD)" = {base}
test "$(git rev-list --all --count)" = 1
test -z "$(git remote)"
'''
        r = self.command(script)
        require(r.returncode == 0, 'base initialization failed: ' + r.stderr.decode(errors='replace')[-2000:])
        self.base = base
        self.base_inventory = self.inventory()
        return self.base_inventory

    def patch(self, base):
        require(re.fullmatch('[a-f0-9]{40}', base), 'invalid base commit')
        if getattr(self,'patch_export_policy','legacy') == PATCH_EXPORT_VERSION:
            source = Path(__file__).with_name('patch_export.py').read_text()
            r = self.command('python3 -c ' + shlex.quote(source) + ' ' + shlex.quote(base))
            require(r.returncode == 0, 'cumulative patch export process failed')
            exported = json.loads(r.stdout)
            self.patch_export_audit = exported['audit']
            if getattr(self,'audit',None) is not None:
                self.patch_exports = getattr(self,'patch_exports',0) + 1
                self.audit.write_artifact(f'patch-export-{self.patch_exports:03d}.json', self.patch_export_audit)
            require(self.patch_export_audit['validation_result'] == 'accepted',
                    'cumulative patch export rejected: ' + str(self.patch_export_audit['rejection_reason']))
            return exported['patch']
        r = self.command(f'export GIT_INDEX_FILE=/tmp/keisho-export-index; git read-tree {base} && git add -A && git diff --cached --binary {base} --; code=$?; rm -f /tmp/keisho-export-index; exit $code')
        require(r.returncode == 0, 'cumulative patch export failed')
        return r.stdout.decode()

    def freeze(self):
        before = self.inventory()
        docker('stop', self.name)
        image = docker('commit', self.name).stdout.decode().strip()
        return image, before

    def close(self):
        # Only the uniquely named owned container; historical images/results stay.
        docker('rm', '-f', self.name)

    def validate_action(self, action):
        if not isinstance(action, dict):
            raise InvalidAction('invalid repository action')
        tool = action.get('tool')
        expected = {'list_files': {'tool'}, 'read_file': {'tool', 'path'},
                    'write_file': {'tool', 'path', 'content'}, 'shell': {'tool', 'command'}}
        if tool=='list_files' and getattr(self,'listing_policy','legacy')==LISTING_VERSION:
            listing_parameters(action)
            return
        if not isinstance(tool, str) or tool not in expected or set(action) != expected[tool]:
            raise InvalidAction('invalid repository action')
        if tool in ('read_file', 'write_file'):
            path = action['path']
            try:
                safe_relative_path(path)
                path.encode('utf-8')
                require('.git' not in path.split('/'), 'Git metadata edits are not a file tool')
            except (TypeError, ValueError):
                raise InvalidAction('unsafe repository path') from None
        if tool == 'write_file':
            try:
                require(isinstance(action['content'], str) and len(action['content'].encode()) <= self.output_bytes, 'invalid file contents')
            except (ValueError, TypeError):
                raise InvalidAction('file write exceeds fixed byte limit or invalid encoding') from None
        if tool == 'shell' and (not isinstance(action['command'], str) or not action['command'].strip() or len(action['command']) > 8192 or '\x00' in action['command']):
            raise InvalidAction('command exceeds fixed bounds')
        if tool == 'shell':
            try: action['command'].encode('utf-8')
            except UnicodeError: raise InvalidAction('invalid command encoding') from None

    def execute(self, action):
        self.validate_action(action)
        self.actions += 1
        tool = action['tool']
        before = self.inventory()
        if tool in ('read_file', 'write_file'):
            path = action['path']
            # Resolve inside the container; symlink escape is refused for file tools.
            check = "from pathlib import Path; p=Path('/testbed')/" + repr(path) + "; resolved=p.resolve(); assert resolved.is_relative_to('/testbed'); assert '.git' not in resolved.relative_to('/testbed').parts; assert not p.is_symlink()"
            r = docker('exec', self.name, 'python3', '-c', check, check=False)
            if r.returncode:
                raise InvalidAction('path escapes repository')
        if tool == 'list_files':
            result = (self.listings.page(before,action,self.actions) if self.listing_policy==LISTING_VERSION
                      else {'files': sorted(before)})
        elif tool == 'read_file':
            r = docker('exec', self.name, 'cat', '/testbed/' + action['path'], check=False)
            require(r.returncode == 0, 'read failed')
            result = {'path': action['path'], 'content': r.stdout.decode()}
        elif tool == 'write_file':
            content = action['content']
            if not isinstance(content, str) or len(content.encode()) > self.output_bytes:
                raise InvalidAction('file write exceeds fixed byte limit')
            code = "from pathlib import Path; import base64; p=Path('/testbed')/" + repr(action['path']) + "; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(base64.b64decode(" + repr(base64.b64encode(content.encode()).decode()) + "))"
            docker('exec', self.name, 'python3', '-c', code)
            result = {'path': action['path'], 'content_sha256': hashlib.sha256(content.encode()).hexdigest()}
        else:
            if not isinstance(action['command'], str) or not 0 < len(action['command']) <= 8192:
                raise InvalidAction('command exceeds fixed bounds')
            r = self.command(action['command'])
            result = {'exit_code': r.returncode, 'output': (r.stdout + r.stderr).decode(errors='replace')}
        after = self.inventory()
        changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        scope = sorted(set(changed) | {p for p in after if self.base_inventory.get(p) != after[p]})
        if tool == 'read_file':
            scope = sorted(set(scope) | {action['path']})
        result.update(action=action, benchmark_observable=True, changed_paths=changed,
                      source_hashes_before={p: before.get(p, {}).get('sha256') for p in scope},
                      source_hashes_after={p: after.get(p, {}).get('sha256') for p in scope})
        if self.audit is not None:
            self.audit.write_artifact(f'tool-observable-{self.actions:03d}.json', result)
        # Preserve output and edits before rejecting an incomplete action.
        if tool == 'shell' and result['exit_code'] in (124, 137):
            raise InvalidAction('command timed out; incomplete action; no checkpoint')
        processes = [line.strip().split(None, 1)[1] for line in docker('top', self.name, '-eo', 'pid,args').stdout.decode().splitlines()[1:]]
        if len(processes) != 1 or not processes[0].endswith('sleep infinity'):
            raise InvalidAction('background process remains; cannot freeze a completed boundary')
        if len(json.dumps(result).encode()) > self.output_bytes:
            # Full output is retained by host; refuse another agent action rather
            # than silently change FULL_HISTORY or request/context budget.
            raise InvalidAction('tool output exceeds frozen bounds; no truncation allowed')
        return result
