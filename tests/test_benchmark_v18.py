"""Prospective v1.8 freeze, non-fatal tool failure observations, and refusal gates."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from keisho.agents.base import TokenCount
from keisho.agents.providers.openrouter_chat import MODEL_ALIASES, OpenRouterChatModel
from keisho.benchmark import comparison as c
from keisho.benchmark.bounded_output import BoundedRepositorySession, VERSION as BOUNDED_VERSION
from keisho.benchmark.environment import RepositorySession
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import canonical_json, digest, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import AUXILIARY
from keisho.pilot.tools import InvalidAction


class Counter:
    def count(self, text):
        return TokenCount(len(text.split()), 'offline-counter', True)


class TestSession:
    validate_action = RepositorySession.validate_action
    output_bytes = 49152

    def __init__(self, file_errors=None):
        self.actions = []
        self.file_errors = file_errors or {}

    def execute(self, action):
        self.validate_action(action)
        self.actions.append(action)
        tool = action['tool']
        if tool == 'read_file':
            path = action['path']
            if path in self.file_errors:
                return {'path': path, 'error': self.file_errors[path]}
            return {'path': path, 'content': 'sample content'}
        elif tool == 'write_file':
            path = action['path']
            if path in self.file_errors:
                return {'path': path, 'error': self.file_errors[path]}
            return {'path': path, 'content_sha256': hashlib.sha256(action['content'].encode()).hexdigest()}
        elif tool == 'shell':
            return {'command': action['command'], 'exit_code': 1, 'output': 'FAILED (failures=1)'}
        elif tool == 'list_files':
            return {'files': ['file1.py', 'file2.py']}
        raise InvalidAction(f'unknown tool: {tool}')


def make_fixture_model(identity, witnesses):
    call_index = 0

    def transport(body, key):
        nonlocal call_index
        witness = witnesses[call_index]
        call_index += 1
        return {'model': MODEL_ALIASES[identity], 'provider': 'OpenAI',
                'choices': [{'message': {'content': canonical_json(witness)}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': sum(len(m['content'].split()) for m in body['messages']),
                          'completion_tokens': len(canonical_json(witness).split()), 'cost': 0, 'is_byok': False}}, None

    return OpenRouterChatModel(identity, authorized=True, api_key='offline-fixture', tokenizer=Counter(),
                               transport=transport, response_model_ids=(MODEL_ALIASES[identity], identity))


class Version18Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.8.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.7.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration',
                                   'experiment_manifest', 'experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.V18_SPEC_SHA)

        # Invariant budgets and task
        self.assertEqual(self.config['successor_budgets'], self.prior['successor_budgets'])
        self.assertEqual(self.config['predecessor_budgets'], self.prior['predecessor_budgets'])
        self.assertEqual(self.config['selected_instance'], 'sympy__sympy-20590')
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertFalse(self.config['live_execution_authorized'])

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 81)
        self.assertIn('runs/swebench-integration/preselection/sympy__sympy-20590-task.json', manifest['files'])
        self.assertIn('src/keisho/benchmark/bounded_output.py', manifest['files'])
        self.assertIn('src/keisho/pilot/agent.py', manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v1.8.json',
                                        c.ROOT / 'analysis/swebench-comparison-v1.8-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 2279)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.42721920')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.1516032')

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.8.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.8-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.8-authorization-template.json',
                        run_dir=Path(t).resolve() / 'not-started')
            binding = c.resolve_binding(**args, allow_pending=True)
            self.assertFalse(binding.authorization['provider_inference_authorized'])
            self.assertFalse(binding.authorization_guard.exists())
            with patch.object(c, 'runtime_preflight', side_effect=AssertionError('preflight must not run')):
                with self.assertRaisesRegex(ValidationError, 'not authorized'):
                    c.execute(approve_live=True, **args)
            self.assertFalse(args['run_dir'].exists())
            self.assertFalse(binding.authorization_guard.exists())

    def test_dry_run_passes_and_reflects_budget(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.8.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.8-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.8-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-out')
            out = c.dry_run(**args)
            self.assertTrue(out['dry_run'])
            self.assertEqual(out['tool_output_policy'], 'bounded-output/1.0')
            self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 400000)
            self.assertEqual(self.config['successor_budgets']['request_input_tokens'], 64000)
            self.assertEqual(out['cost_envelope_usd'], '9.42721920')
            self.assertFalse(out['guard_created'])

    def test_bounded_repository_session_cat_failure_returns_error_dict(self):
        session = BoundedRepositorySession.__new__(BoundedRepositorySession)
        session.name = 'test-container'
        session.listing_policy = 'bounded-listing/1.0'
        session.tool_output_policy = BOUNDED_VERSION
        session.output_bytes = 49152
        session.actions = 0
        session.audit = None
        session.base_inventory = {}
        session.inventory = lambda: {}
        session.validate_action = lambda action: None

        # 1. Non-fatal read failure returns error dict
        with patch('keisho.benchmark.bounded_output.docker') as mock_docker:
            mock_cat = Mock(returncode=1, stdout=b'', stderr=b'cat: /testbed/missing.py: No such file or directory')
            mock_top = Mock(stdout=b'PID COMMAND\n123 /bin/sleep infinity\n')
            mock_docker.side_effect = [mock_cat, mock_top]
            result = session.execute({'tool': 'read_file', 'path': 'missing.py'})
            self.assertEqual(result['error'], 'cat: /testbed/missing.py: No such file or directory')
            self.assertEqual(result['path'], 'missing.py')
            self.assertTrue(result['benchmark_observable'])

        # 2. Path escape raises fatal InvalidAction
        with self.assertRaisesRegex(InvalidAction, 'path escapes repository'):
            session.execute({'tool': 'read_file', 'path': '../outside.py'})

        with self.assertRaisesRegex(InvalidAction, 'path escapes repository'):
            session.execute({'tool': 'read_file', 'path': '/etc/passwd'})

    def test_non_fatal_missing_file_observation_and_continuation(self):
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t).resolve(), 'nonfatal-run')
            witnesses = [
                {'action': {'tool': 'read_file', 'path': 'sympy/core/atomic.py'}, 'claims': []},
                {'action': {'tool': 'finish', 'answer': 'completed after error observation'}, 'claims': []}
            ]
            model = make_fixture_model(self.config['predecessor_model'], witnesses)
            session = TestSession(file_errors={'sympy/core/atomic.py': 'cat: /testbed/sympy/core/atomic.py: No such file or directory'})
            system, policy, _ = c.response_settings(self.config)
            execution = run_agent(model, session, Recorder(raw), 'testbed issue', system, '',
                                  1, Budgets(5, 5, 2048, 40000, 64000, 128000), role='predecessor',
                                  response_policy=policy, **c.action_wire_options(self.config))

            self.assertEqual(execution.reason, 'finished')
            self.assertEqual(execution.model_calls, 2)
            self.assertEqual(execution.tool_calls, 1)

    def test_fatal_path_escape_halts_immediately(self):
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t).resolve(), 'path-escape-run')
            witnesses = [
                {'action': {'tool': 'read_file', 'path': '../secret.py'}, 'claims': []},
                {'action': {'tool': 'finish', 'answer': 'should not be reached'}, 'claims': []}
            ]
            model = make_fixture_model(self.config['predecessor_model'], witnesses)
            session = TestSession()
            system, policy, _ = c.response_settings(self.config)
            execution = run_agent(model, session, Recorder(raw), 'testbed issue', system, '',
                                  1, Budgets(5, 5, 2048, 40000, 64000, 128000), role='predecessor',
                                  response_policy=policy, **c.action_wire_options(self.config))

            self.assertEqual(execution.reason, 'invalid_run')
            self.assertEqual(execution.model_calls, 1)

    def test_three_consecutive_failures_halts_with_repeated_tool_failure(self):
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t).resolve(), 'repeated-failure-run')
            witnesses = [
                {'action': {'tool': 'read_file', 'path': 'bad1.py'}, 'claims': []},
                {'action': {'tool': 'read_file', 'path': 'bad2.py'}, 'claims': []},
                {'action': {'tool': 'read_file', 'path': 'bad3.py'}, 'claims': []},
                {'action': {'tool': 'finish', 'answer': 'should not run'}, 'claims': []}
            ]
            model = make_fixture_model(self.config['predecessor_model'], witnesses)
            session = TestSession(file_errors={
                'bad1.py': 'cat: /testbed/bad1.py: No such file',
                'bad2.py': 'cat: /testbed/bad2.py: No such file',
                'bad3.py': 'cat: /testbed/bad3.py: No such file',
            })
            system, policy, _ = c.response_settings(self.config)
            execution = run_agent(model, session, Recorder(raw), 'testbed issue', system, '',
                                  1, Budgets(10, 10, 2048, 40000, 64000, 128000), role='predecessor',
                                  response_policy=policy, **c.action_wire_options(self.config))

            self.assertEqual(execution.reason, 'repeated_tool_failure')
            self.assertEqual(execution.model_calls, 3)
            self.assertEqual(execution.tool_calls, 3)

    def test_nonzero_shell_command_resets_failure_counter(self):
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t).resolve(), 'reset-failure-run')
            witnesses = [
                {'action': {'tool': 'read_file', 'path': 'bad1.py'}, 'claims': []},
                {'action': {'tool': 'shell', 'command': 'pytest test_something.py'}, 'claims': []},
                {'action': {'tool': 'read_file', 'path': 'bad2.py'}, 'claims': []},
                {'action': {'tool': 'finish', 'answer': 'completed'}, 'claims': []}
            ]
            model = make_fixture_model(self.config['predecessor_model'], witnesses)
            session = TestSession(file_errors={
                'bad1.py': 'cat: /testbed/bad1.py: No such file',
                'bad2.py': 'cat: /testbed/bad2.py: No such file',
            })
            system, policy, _ = c.response_settings(self.config)
            execution = run_agent(model, session, Recorder(raw), 'testbed issue', system, '',
                                  1, Budgets(10, 10, 2048, 40000, 64000, 128000), role='predecessor',
                                  response_policy=policy, **c.action_wire_options(self.config))

            self.assertEqual(execution.reason, 'finished')
            self.assertEqual(execution.model_calls, 4)
            self.assertEqual(execution.tool_calls, 3)


if __name__ == '__main__':
    unittest.main()
