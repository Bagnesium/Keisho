"""Bounded tool execution and output. History is retained; omissions are explicit."""
import hashlib
import json

from keisho.environments.base import safe_relative_path
from keisho.pilot.tools import InvalidAction
from .environment import RepositorySession, docker

VERSION = 'bounded-output/1.0'
MAX_BOUNDED_OUTPUT_BYTES = 8192
MAX_BOUNDED_CHANGED_PATHS = 25
MAX_BOUNDED_RESULT_BYTES = 12288


class BoundedRepositorySession(RepositorySession):
    def __init__(self, image, *, timeout=120, output_bytes=49152, audit=None,
                 listing_policy='legacy', patch_export_policy='legacy', tool_output_policy=VERSION):
        super().__init__(image, timeout=timeout, output_bytes=output_bytes, audit=audit,
                         listing_policy=listing_policy, patch_export_policy=patch_export_policy)
        self.tool_output_policy = tool_output_policy

    def execute(self, action):
        self.validate_action(action)
        self.actions += 1
        tool = action['tool']
        before = self.inventory()
        if tool in ('read_file', 'write_file'):
            path = action['path']
            try:
                safe_relative_path(path)
            except (TypeError, ValueError):
                raise InvalidAction('path escapes repository')
        if tool == 'list_files':
            result = (self.listings.page(before, action, self.actions) if self.listing_policy == 'bounded-listing/1.0'
                      else {'files': sorted(before)})
        elif tool == 'read_file':
            r = docker('exec', self.name, 'cat', '/testbed/' + action['path'], check=False)
            if r.returncode != 0:
                err = (r.stderr or r.stdout).decode(errors='replace').strip() or 'read failed'
                result = {'path': action['path'], 'error': err}
            else:
                content = r.stdout.decode(errors='replace')
                content_bytes = content.encode('utf-8')
                if len(content_bytes) > MAX_BOUNDED_OUTPUT_BYTES:
                    half = MAX_BOUNDED_OUTPUT_BYTES // 2
                    head = content_bytes[:half].decode('utf-8', errors='replace')
                    tail = content_bytes[-half:].decode('utf-8', errors='replace')
                    omitted = len(content_bytes) - len(head.encode('utf-8')) - len(tail.encode('utf-8'))
                    truncated_text = f"{head}\n[... file content truncated {omitted} bytes ...]\n{tail}"
                    result = {'path': action['path'], 'content': truncated_text,
                              'truncated': True, 'total_content_bytes': len(content_bytes)}
                else:
                    result = {'path': action['path'], 'content': content}
        elif tool == 'write_file':
            content = action['content']
            if not isinstance(content, str) or len(content.encode()) > self.output_bytes:
                raise InvalidAction('file write exceeds fixed byte limit')
            import base64
            code = "from pathlib import Path; import base64; p=Path('/testbed')/" + repr(action['path']) + "; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(base64.b64decode(" + repr(base64.b64encode(content.encode()).decode()) + "))"
            r = docker('exec', self.name, 'python3', '-c', code, check=False)
            if r.returncode != 0:
                err = (r.stderr or r.stdout).decode(errors='replace').strip() or 'write failed'
                result = {'path': action['path'], 'error': err}
            else:
                result = {'path': action['path'], 'content_sha256': hashlib.sha256(content.encode()).hexdigest()}
        else:
            if not isinstance(action['command'], str) or not 0 < len(action['command']) <= 8192:
                raise InvalidAction('command exceeds fixed bounds')
            r = self.command(action['command'])
            raw = (r.stdout + r.stderr).decode(errors='replace')
            raw_bytes = raw.encode('utf-8')
            if len(raw_bytes) > MAX_BOUNDED_OUTPUT_BYTES:
                half = MAX_BOUNDED_OUTPUT_BYTES // 2
                head = raw_bytes[:half].decode('utf-8', errors='replace')
                tail = raw_bytes[-half:].decode('utf-8', errors='replace')
                omitted = len(raw_bytes) - len(head.encode('utf-8')) - len(tail.encode('utf-8'))
                truncated_text = f"{head}\n[... tool output truncated {omitted} bytes ...]\n{tail}"
                result = {'exit_code': r.returncode, 'output': truncated_text,
                          'truncated': True, 'total_output_bytes': len(raw_bytes)}
            else:
                result = {'exit_code': r.returncode, 'output': raw}

        after = self.inventory()
        changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        scope = sorted(set(changed) | {p for p in after if self.base_inventory.get(p) != after[p]})
        if tool == 'read_file':
            scope = sorted(set(scope) | {action['path']})

        if len(changed) > MAX_BOUNDED_CHANGED_PATHS:
            bounded_changed = changed[:MAX_BOUNDED_CHANGED_PATHS]
            bounded_scope = sorted(set(bounded_changed) | ({action['path']} if tool == 'read_file' else set()))
            result.update(action=action, benchmark_observable=True, changed_paths=bounded_changed,
                          omitted_changed_paths_count=len(changed) - MAX_BOUNDED_CHANGED_PATHS,
                          inventory_truncated=True,
                          source_hashes_before={p: before.get(p, {}).get('sha256') for p in bounded_scope},
                          source_hashes_after={p: after.get(p, {}).get('sha256') for p in bounded_scope})
        else:
            result.update(action=action, benchmark_observable=True, changed_paths=changed,
                          source_hashes_before={p: before.get(p, {}).get('sha256') for p in scope},
                          source_hashes_after={p: after.get(p, {}).get('sha256') for p in scope})

        if self.audit is not None:
            self.audit.write_artifact(f'tool-observable-{self.actions:03d}.json', result)

        if tool == 'shell' and result['exit_code'] in (124, 137):
            raise InvalidAction('command timed out; incomplete action; no checkpoint')

        processes = [line.strip().split(None, 1)[1] for line in docker('top', self.name, '-eo', 'pid,args').stdout.decode().splitlines()[1:]]
        if len(processes) != 1 or not processes[0].endswith('sleep infinity'):
            raise InvalidAction('background process remains; cannot freeze a completed boundary')

        if len(json.dumps(result).encode()) > MAX_BOUNDED_RESULT_BYTES:
            raise InvalidAction('tool output exceeds bounded limit; use targeted inspection')
        return result
