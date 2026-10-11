"""Every text-action variant through the real provider body and feedback loop.

Offline only: transport responses below are labeled test fixtures, never live
agent outputs. JSON Schema validation uses installed jsonschema 4.26.0.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, ValidationError as SchemaError
from keisho.agents.base import Message, ModelRequest, TokenCount
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES
from keisho.benchmark.comparison import response_settings, ROOT
from keisho.benchmark.environment import RepositorySession
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, parse_output, run_agent
from keisho.pilot.response_policy import AUXILIARY, STRICT
from keisho.pilot.tools import InvalidAction

WITNESSES = (
    {'action': {'tool': 'list_files'}, 'claims': []},
    {'action': {'tool': 'read_file', 'path': 'api.py'}, 'claims': []},
    {'action': {'tool': 'write_file', 'path': 'api.py', 'content': 'value = 1\n'}, 'claims': []},
    {'action': {'tool': 'shell', 'command': 'python check_public.py'}, 'claims': []},
    {'action': {'tool': 'finish', 'answer': 'Software fixture only'}, 'claims': []},
)

class Counter:
    def count(self, text):
        return TokenCount(len(text.split()), 'offline-counter', True)

class OfflineSession:
    validate_action = RepositorySession.validate_action
    output_bytes = 49152
    def __init__(self):
        self.actions = []
    def execute(self, action):
        self.validate_action(action)
        self.actions.append(action)
        return {'action': action, 'fixture_result': len(self.actions), 'files': ['api.py', 'check_public.py'],
                'content': 'initial fixture' if action['tool'] == 'read_file' else '',
                'changed_paths': ['api.py'] if action['tool'] == 'write_file' else [],
                'exit_code': 0, 'output': 'OFFLINE TEST FIXTURE'}

def native_response(identity, witness):
    return {'model': MODEL_ALIASES[identity], 'provider': 'OpenAI',
            'choices': [{'message': {'content': canonical_json(witness)}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'cost': 0.000072,
                      'is_byok': False, 'prompt_tokens_details': {'cached_tokens': 0}}}

class AgentWireTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
        self.system, self.policy, self.output_format = response_settings(self.config)

    def test_every_action_witness_passes_actual_transport_schema_and_local_contract(self):
        for identity in (self.config['predecessor_model'], self.config['successor_model']):
            for witness in WITNESSES:
                with self.subTest(model=identity, action=witness['action']['tool']):
                    captured = []
                    def transport(body, key):
                        captured.append(copy.deepcopy(body))
                        return native_response(identity, witness), 'offline-wire-fixture'
                    model = OpenRouterChatModel(identity, authorized=True, api_key='offline-fixture-key',
                          tokenizer=Counter(), transport=transport,
                          response_model_ids=(MODEL_ALIASES[identity], identity), agent_response_format=self.output_format)
                    model.generate(ModelRequest((Message('system', self.system), Message('user', 'fixture objective')), 1, 2048, 0.0))
                    schema = captured[0]['response_format']['json_schema']['schema']
                    Draft202012Validator.check_schema(schema)
                    Draft202012Validator(schema).validate(witness)
                    for policy in (STRICT, AUXILIARY):
                        self.assertEqual(parse_output(canonical_json(witness), set(), policy)['action'], witness['action'])
                    if witness['action']['tool'] != 'finish':
                        OfflineSession().validate_action(witness['action'])
                    else:
                        with tempfile.TemporaryDirectory() as t:
                            execution = run_agent(model, OfflineSession(), Recorder(RawRun(Path(t), 'finish')),
                                  'fixture objective', self.system, '', 1, Budgets(1, 1, 2048, 20000, 32000, 128000),
                                  response_policy=AUXILIARY)
                            self.assertEqual((execution.reason, execution.tool_calls), ('finished', 0))

    def test_schema_rejects_missing_extra_and_conflicting_action_arguments(self):
        model = OpenRouterChatModel(self.config['predecessor_model'], agent_response_format=self.output_format)
        body = model.body(ModelRequest((Message('user', 'fixture'),), 1, 2048, 0.0))
        validator = Draft202012Validator(body['response_format']['json_schema']['schema'])
        invalid = [{'tool': 'read_file'}, {'tool': 'write_file', 'path': 'api.py'}, {'tool': 'shell'},
                   {'tool': 'finish'}, {'tool': 'list_files', 'path': 'api.py'},
                   {'tool': 'read_file', 'path': 'api.py', 'command': 'true'},
                   {'tool': 'run_tests', 'test_ids': ['full']}, {'tool': 'unknown'}]
        for action in invalid:
            with self.subTest(action=action), self.assertRaises(SchemaError):
                validator.validate({'action': action, 'claims': []})

    def test_valid_schema_never_replaces_runtime_path_and_command_safety(self):
        validator = Draft202012Validator(self.output_format['json_schema']['schema'])
        for action in ({'tool': 'read_file', 'path': '../escape'},
                       {'tool': 'write_file', 'path': '.git/config', 'content': 'denied'},
                       {'tool': 'shell', 'command': ''}):
            witness = {'action': action, 'claims': []}
            validator.validate(witness)
            parse_output(canonical_json(witness), set(), AUXILIARY)
            with self.assertRaises(InvalidAction): OfflineSession().validate_action(action)

    def test_actual_provider_loop_transmits_all_previous_actions_and_corresponding_results(self):
        for role in ('predecessor', 'successor'):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as t:
                captured = []
                identity = self.config[role + '_model']
                def transport(body, key):
                    witness = WITNESSES[len(captured)]
                    Draft202012Validator(body['response_format']['json_schema']['schema']).validate(witness)
                    captured.append(copy.deepcopy(body))
                    return native_response(identity, witness), 'offline-wire-fixture'
                model = OpenRouterChatModel(identity, authorized=True, api_key='offline-fixture-key', tokenizer=Counter(),
                      transport=transport, response_model_ids=(MODEL_ALIASES[identity], identity), agent_response_format=self.output_format)
                session = OfflineSession()
                raw = RawRun(Path(t), 'wire-loop')
                execution = run_agent(model, session, Recorder(raw), 'original fixture objective', self.system,
                        '', 1, Budgets(5, 4, 2048, 80000, 32000, 128000), role=role, response_policy=AUXILIARY)
                self.assertEqual((execution.reason, execution.model_calls, execution.tool_calls), ('finished', 5, 4))
                events = {e.id: json.loads(e.payload_json) for e in raw.freeze().events}
                for n, body in enumerate(captured):
                    self.assertEqual(len(body['messages']), 3 + 2*n)
                    self.assertEqual(body['messages'][:3], captured[0]['messages'])
                    self.assertEqual(body['messages'][1]['content'], 'original fixture objective')
                    for prior in range(n):
                        self.assertEqual(json.loads(body['messages'][3 + 2*prior]['content']), WITNESSES[prior])
                        feedback = json.loads(body['messages'][4 + 2*prior]['content'])
                        result_id = f'{role}_result_{prior+1:03d}'
                        self.assertEqual(feedback['event_id'], result_id)
                        self.assertEqual(feedback['tool_result'], events[result_id])
                    self.assertNotIn('tools', body)
                    self.assertNotIn('tool_choice', body)

    def test_functional_check_does_not_choose_actions_or_accept_compile_as_public_test(self):
        from scripts.benchmark_functional_check import AcceptanceBoundary
        boundary = AcceptanceBoundary()
        self.assertFalse(boundary({'tool': 'list_files'}, {'files': ['ledger.py']}))
        self.assertFalse(boundary.inspected)
        self.assertFalse(boundary({'tool': 'read_file', 'path': 'ledger.py'}, {'content': 'public initial contents'}))
        self.assertTrue(boundary.inspected)
        self.assertFalse(boundary({'tool': 'write_file', 'path': 'ledger.py'}, {'changed_paths': ['ledger.py']}))
        self.assertFalse(boundary({'tool': 'shell', 'command': 'python -m compileall ledger.py'}, {'exit_code': 0}))
        self.assertFalse(boundary({'tool': 'shell', 'command': 'echo "python check_public.py"'}, {'exit_code': 0}))
        self.assertTrue(boundary({'tool': 'shell', 'command': 'python check_public.py'}, {'exit_code': 1, 'output': 'fixture failure'}))
        self.assertEqual(boundary.test_event['exit_code'], 1)  # Stop first attempted post-edit test, even if failed.

    def test_functional_fixture_reuses_only_existing_public_files(self):
        from scripts.benchmark_functional_check import fixture_files
        files = fixture_files()
        self.assertEqual(set(files), {'api.py', 'ledger.py', 'normalize.py', 'CONTRACT.md', 'tests.json', 'check_public.py'})
        cases = json.loads(files['tests.json'])
        public = json.loads((ROOT / 'tasks/task_001/public.json').read_text())['cases']
        self.assertEqual(cases, [{k: v for k, v in c.items() if k != 'initial_failure'} for c in public])

    def test_functional_stage_caps_and_guard_gate_without_network(self):
        from decimal import Decimal
        from scripts.benchmark_functional_check import execute
        from keisho.core import ValidationError
        from unittest.mock import patch
        ceiling = Decimal('1.05') * 8 * (32000 * Decimal('.4') + 2048 * Decimal('1.6')) / 1000000
        self.assertEqual(ceiling, Decimal('.13504512'))
        self.assertLess(ceiling, Decimal('.50'))
        with patch('keisho.agents.providers.openai_chat.http_transport', side_effect=AssertionError('offline; network forbidden')):
            with self.assertRaisesRegex(ValidationError, 'approval required'): execute(False)

if __name__ == '__main__': unittest.main()
