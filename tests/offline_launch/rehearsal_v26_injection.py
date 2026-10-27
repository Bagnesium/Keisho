"""Real Docker five-way software rehearsal for v2.6 binding.
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
                'rehearsal_binding': 'v2.6',
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
    saved_helpers_content = {}

    def transport(body, key, **kwargs):
        stage = current['stage']
        counts[stage] += 1
        n = counts[stage]

        if stage in ('note_generation_summary', 'note_generation_structured') or stage == 'note-generation':
            if 'response_format' not in body:
                text = (
                    "Predecessor inspected sympy/core/_print_helpers.py and validated syntax via compileall. "
                    "The issue involves Symbol instances having __dict__ in sympy 1.7 because Printable mixin "
                    "lacks empty __slots__. Non-test source edit applied; checkpoint reached. Official grade withheld."
                )
            else:
                text = json.dumps({
                    "problem_understanding": "Symbol instances in Sympy 1.7 have __dict__ because mixin Printable lacks empty __slots__.",
                    "work_completed": "Inspected sympy/core/_print_helpers.py, added comment marker, verified syntax with compileall.",
                    "evidence_observed": "python -m compileall sympy/core/_print_helpers.py completed with exit code 0.",
                    "observed_failures_or_error_evidence": "No unit tests run yet during predecessor stage.",
                    "remaining_uncertainty": "Whether setting __slots__ = () on Printable fully resolves test_immutable.",
                    "rollback_notes": "Revert edit to sympy/core/_print_helpers.py if regressions occur.",
                    "recommended_next_action": "Add __slots__ = () to Printable and run bin/test sympy/core/tests/test_basic.py."
                })
        elif stage == 'predecessor':
            if n == 1:
                action = {'tool': 'read_file', 'path': 'sympy/core/_print_helpers.py'}
            elif n == 2:
                last_msg = body['messages'][-1]['content']
                feedback = json.loads(last_msg)['tool_result']
                content = feedback.get('content', '')
                saved_helpers_content['base'] = content
                marker = '\n# REHEARSAL PREDECESSOR EDIT: mixin slots\n'
                action = {'tool': 'write_file', 'path': 'sympy/core/_print_helpers.py', 'content': content + marker}
            elif n == 3:
                action = {'tool': 'shell', 'command': 'python -m compileall sympy/core/_print_helpers.py'}
            else:
                action = {'tool': 'finish', 'answer': 'Predecessor finished'}
            text = canonical_json({'action': action, 'claims': []})
        else:
            # Successor branches (FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY, KEISHO_2K, STRUCTURED_NOTES_2K)
            if stage == 'KEISHO_2K':
                if n == 1:
                    action = {'tool': 'read_file', 'path': 'sympy/core/_print_helpers.py'}
                elif n == 2:
                    last_msg = body['messages'][-1]['content']
                    feedback = json.loads(last_msg)['tool_result']
                    content = feedback.get('content', '')
                    target = 'class Printable:'
                    replacement = 'class Printable:\n    __slots__ = ()'
                    if target in content:
                        fixed_content = content.replace(target, replacement, 1)
                    else:
                        fixed_content = content + '\n# KEISHO FIX\n'
                    action = {'tool': 'write_file', 'path': 'sympy/core/_print_helpers.py', 'content': fixed_content}
                else:
                    action = {'tool': 'finish', 'answer': 'KEISHO_2K completed with repair'}
            else:
                if n == 1:
                    action = {'tool': 'read_file', 'path': 'sympy/core/_print_helpers.py'}
                else:
                    action = {'tool': 'finish', 'answer': f'{stage} completed without repair'}
            text = canonical_json({'action': action, 'claims': []})

        service = {
            'id': f'REHEARSAL-{stage}-{n}',
            'synthetic': True,
            'model': body.get('model', 'openai/gpt-6-sol'),
            'provider': 'OpenAI',
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
