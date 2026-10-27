"""Real Docker five-way software rehearsal for v2.7 binding.
No paid/network model transport. Uses real official SWE-bench evaluator in Docker.
"""
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
import socket
from urllib.request import OpenerDirector

from keisho.agents.providers import openai_chat, openrouter_chat
from keisho.benchmark import comparison as c
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.tokenizer import NativeTokenizer


def inject(namespace, settings):
    root = Path(settings['fixture_root'])
    current = {'stage': None}
    counts = defaultdict(int)

    # 1. Strict Fail-Closed Network Traps (Zero External Requests)
    OpenerDirector.open = lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError('Synthetic simulation attempted model/network I/O')
    )
    real_socket_connect = socket.socket.connect

    def guarded_connect(self, address):
        if getattr(self, 'family', None) == getattr(socket, 'AF_UNIX', None):
            return real_socket_connect(self, address)
        raise AssertionError(f'Rehearsal attempted external network connection to {address}')

    socket.socket.connect = guarded_connect

    # 2. Binding & Rehearsal-Only Authorization Isolation
    real_resolve = c.resolve_binding

    def resolve(*args, **kwargs):
        kwargs['allow_pending'] = True  # Pending scope admitted ONLY with offline injected transport
        binding = real_resolve(*args, **kwargs)
        # Isolate authorization claim guard in fixture root to prevent interference with live guards
        return replace(binding, authorization_guard=root / 'rehearsal-authorization-claim')

    c.resolve_binding = resolve

    # 3. Offline Public Catalog (No External Network Call)
    catalog_path = c.PRESELECT / 'provider-catalog-v2.0.json'
    cached_catalog = json.loads(catalog_path.read_text())
    c.check_public_catalog = lambda *a, **kw: cached_catalog

    # 4. Explicit Integration-Evidence Labeling
    class SyntheticRawRun(RawRun):
        def __init__(self, *args):
            super().__init__(*args)
            current['stage'] = self.path.name
            self.write_artifact('engineering-check.json', {
                'synthetic_engineering_check': True,
                'actual_provider_requests': 0,
                'actual_provider_cost_usd': '0',
                'rehearsal_binding': 'v2.7',
                'evidence_type': 'offline_integration_rehearsal',
                'disclaimer': 'Offline software rehearsal with scripted inputs; zero evidence of model efficacy.'
            })

        def write_artifact(self, name, value):
            if name in ('result.json', 'spending.json') and isinstance(value, dict):
                value = {
                    **value,
                    'synthetic_engineering_check': True,
                    'actual_provider_cost_usd': '0',
                    'actual_provider_requests': 0
                }
            super().write_artifact(name, value)

    c.RawRun = SyntheticRawRun

    # 5. Scripted Transport for Predecessor, Generators, and Successors
    tokenizer = NativeTokenizer()

    def transport(body, key, **kwargs):
        stage = current['stage']
        counts[stage] += 1
        n = counts[stage]
        model_id = body.get('model', 'openai/gpt-6-sol')

        if stage in ('note_generation_summary', 'note_generation_structured') or stage == 'note-generation':
            if 'response_format' not in body:
                text = (
                    "Predecessor investigated issue with xarray Dataset.chunks loading data into memory unexpectedly. "
                    "Created reproduce_issue.py using InaccessibleVariableDataStore, which raises UnexpectedDataAccess "
                    "when ds.chunks is accessed. Genuine task bug reproduced; predecessor stopped before editing source code."
                )
            else:
                text = json.dumps({
                    "problem_understanding": "Dataset.chunks triggers unexpected data loading on lazy-backed stores because chunks property iterates over variables and checks hasattr(v.data, 'chunks').",
                    "work_completed": "Wrote reproduce_issue.py with InaccessibleVariableDataStore and verified reproduction of UnexpectedDataAccess.",
                    "evidence_observed": "python reproduce_issue.py raised UnexpectedDataAccess: Tried accessing data with exit code 1.",
                    "observed_failures_or_error_evidence": "xarray/core/common.py:2026 accesses v.data in get_chunksizes instead of v._data.",
                    "remaining_uncertainty": "Whether changing hasattr(v.data, 'chunks') to hasattr(v._data, 'chunks') in xarray/core/common.py avoids all eager loading without breaking duck arrays.",
                    "rollback_notes": "No source files were edited during predecessor stage.",
                    "recommended_next_action": "Modify xarray/core/common.py get_chunksizes to inspect v._data instead of v.data."
                })
        elif stage == 'predecessor':
            if n == 1:
                action = {'tool': 'read_file', 'path': 'xarray/core/common.py'}
            elif n == 2:
                action = {'tool': 'write_file', 'path': 'xarray/core/common.py', 'content': '# attempt edit'}
            else:
                action = {'tool': 'finish', 'answer': 'Predecessor finished'}
            text = canonical_json({'action': action, 'claims': []})
        else:
            # Successor branches (FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY, KEISHO_2K, STRUCTURED_NOTES_2K)
            if stage == 'KEISHO_2K':
                if n == 1:
                    action = {'tool': 'read_file', 'path': 'xarray/core/common.py'}
                elif n == 2:
                    cmd = 'python -c "p=\'xarray/core/common.py\'; s=open(p).read(); open(p,\'w\').write(s.replace(\'hasattr(v.data, \\"chunks\\")\', \'hasattr(v._data, \\"chunks\\")\'))"'
                    action = {'tool': 'shell', 'command': cmd}
                elif n == 3:
                    action = {'tool': 'shell', 'command': 'python reproduce_issue.py'}
                else:
                    action = {'tool': 'finish', 'answer': 'KEISHO_2K completed with repair'}
            else:
                if n == 1:
                    action = {'tool': 'read_file', 'path': 'xarray/core/common.py'}
                else:
                    action = {'tool': 'finish', 'answer': f'{stage} completed without repair'}
            text = canonical_json({'action': action, 'claims': []})

        provider = 'Anthropic' if 'anthropic' in model_id.lower() else 'OpenAI'

        service = {
            'id': f'REHEARSAL-{stage}-{n}',
            'synthetic': True,
            'model': model_id,
            'provider': provider,
            'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
            'usage': {
                'prompt_tokens': sum(tokenizer.count(m['content']).count for m in body['messages']),
                'completion_tokens': tokenizer.count(text).count,
                'total_tokens': sum(tokenizer.count(m['content']).count for m in body['messages']) + tokenizer.count(text).count,
                'cost': 0,
                'is_byok': False,
                'prompt_tokens_details': {'cached_tokens': 0}
            }
        }
        if kwargs.get('response_observer'):
            kwargs['response_observer'](json.dumps(service).encode('utf-8'), 200, False)
        return service, 'REHEARSAL-NO-PROVIDER-NETWORK'

    c.http_transport = transport
    openai_chat.http_transport = transport
    openrouter_chat.transport = transport
