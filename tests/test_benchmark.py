"""Offline integration contracts, never model-effectiveness evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.scripted import ScriptedModel
from keisho.benchmark.environment import RepositorySession, run_arguments
from keisho.benchmark.evaluator import write_prediction, unique_run_id, report_status
from keisho.benchmark.protocol import ValidationCheckpoint, completed_validation_command, generation_messages, render_structured, deterministic_fields
from keisho.benchmark.comparison import load_frozen_plan, validate_setup
from keisho.core import ValidationError
from keisho.handoff.session import load_session
from keisho.handoff.compact import compile_handoff
from keisho.logging.raw import RawRun, EventKind
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.spending import SpendLedger
from keisho.agents.providers.openai_chat import ProviderFailure


class BenchmarkTests(unittest.TestCase):
    def test_validation_checkpoint_no_failed_attempt_required(self):
        gate = ValidationCheckpoint()
        self.assertFalse(gate({'tool': 'shell', 'command': 'pytest'}, {'exit_code': 1}))
        self.assertFalse(gate({'tool': 'write_file'}, {'changed_paths': ['tests/test_api.py']}))
        self.assertFalse(gate({'tool': 'write_file'}, {'changed_paths': ['pkg/api.py']}))
        self.assertFalse(gate({'tool': 'shell', 'command': 'echo pytest'}, {'exit_code': 0}))
        self.assertFalse(gate({'tool': 'shell', 'command': 'python -m compileall pkg'}, {}))
        self.assertTrue(gate({'tool': 'shell', 'command': 'python -m compileall pkg'}, {'exit_code': 0}))
        self.assertEqual(gate.checkpoint['exit_code'], 0)
        self.assertFalse(gate.checkpoint['uses_hidden_grades'])

    def test_executed_validation_heads(self):
        for command in ('pytest -q', 'cd pkg && python -m unittest', 'pnpm run lint', 'python check_case.py', 'python setup.py build'):
            self.assertTrue(completed_validation_command(command), command)
        for command in ('cat tests/test_api.py', 'echo "pytest -q"', 'python -c "print(\"all tests passed\")"', 'git diff'):
            self.assertFalse(completed_validation_command(command), command)

    def test_combined_action_order_unknown_and_timeout_output_preserved(self):
        gate = ValidationCheckpoint()
        action = {'tool': 'shell', 'command': 'pytest; python edit_source.py'}
        self.assertFalse(gate(action, {'changed_paths': ['api.py'], 'exit_code': 0}))
        self.assertTrue(gate({'tool': 'shell', 'command': 'pytest'}, {'exit_code': 0}))
        from types import SimpleNamespace
        event = SimpleNamespace(kind=EventKind.TOOL_RESULT, payload_json=json.dumps({'action': action,
                      'changed_paths': ['api.py'], 'exit_code': 0, 'output': 'validation before edit'}))
        self.assertEqual(deterministic_fields([event], ['api.py'])['validation_outcome_after_latest_source_change'], 'UNKNOWN')
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'timeout-fixture')
            session = RepositorySession.__new__(RepositorySession)
            session.name, session.actions, session.audit = 'owned-fixture', 0, raw
            session.output_bytes, session.base_inventory = 49152, {}
            session.inventory = lambda: {}
            session.command = lambda _: subprocess.CompletedProcess([], 137, b'partial observable output', b'')
            from keisho.pilot.tools import InvalidAction
            with self.assertRaises(InvalidAction):
                session.execute({'tool': 'shell', 'command': 'pytest'})
            result = json.loads((raw.path / 'tool-observable-001.json').read_text())
            self.assertEqual(result['exit_code'], 137)
            self.assertEqual(result['output'], 'partial observable output')

    def test_existing_loop_stops_on_completed_result(self):
        actions = ({'tool': 'write_file', 'path': 'api.py', 'content': 'x=1'}, {'tool': 'shell', 'command': 'pytest'}, {'tool': 'finish', 'answer': 'should not run'})
        model = ScriptedModel(tuple(json.dumps({'action': a, 'claims': []}) for a in actions))
        class Session:
            def execute(self, action):
                return {'action': action, 'changed_paths': ['api.py'] if action['tool'] == 'write_file' else [], **({'exit_code': 0, 'output': '1 passed'} if action['tool'] == 'shell' else {})}
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'test')
            result = run_agent(model, Session(), Recorder(raw), 'public issue', 'fixed instructions', '', 1,
                         Budgets(4, 4, 256, 20000, 32000, 128000), role='predecessor', checkpoint_predicate=ValidationCheckpoint())
            self.assertEqual((result.reason, result.model_calls, result.tool_calls), ('checkpoint', 2, 2))
            frozen = raw.freeze()
            self.assertEqual(frozen.events[-1].kind, EventKind.TOOL_RESULT)

    def test_malformed_claim_stops_before_tools_and_records_diagnosis(self):
        response = json.dumps({'action': {'tool': 'write_file', 'path': 'api.py', 'content': 'change'},
                 'claims': [{'statement': 'issue says this', 'status': 'UNCERTAIN', 'evidence_ids': [], 'basis': 'issue report'}]})
        model = ScriptedModel((response,))
        class Session:
            def execute(self, action):
                raise AssertionError('invalid protocol must never execute a tool')
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'malformed')
            result = run_agent(model, Session(), Recorder(raw), 'public issue', 'fixed schema', '', 1,
                 Budgets(4, 4, 256, 20000, 32000, 128000), role='predecessor')
            self.assertEqual((result.reason, result.model_calls, result.tool_calls), ('model_failure', 1, 0))
            self.assertEqual(json.loads((raw.path / 'predecessor_call_001-protocol-failure.json').read_text())['reason'], 'invalid claim basis')

    def test_shell_observable_import_unknown_stays_unknown(self):
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'predecessor')
            rec = Recorder(raw)
            rec.emit('call', EventKind.TOOL_CALL, 'predecessor', {'action': {'tool': 'shell', 'command': 'pytest'}})
            rec.emit('result', EventKind.TOOL_RESULT, 'predecessor', {'benchmark_observable': True,
                 'action': {'tool': 'shell', 'command': 'pytest'}, 'exit_code': 1, 'output': 'public assertion failed',
                 'changed_paths': ['pkg/api.py'], 'source_hashes_after': {'pkg/api.py': 'a' * 64}}, ('call',))
            raw.freeze()
            state, archive, _ = load_session(raw.path, 'public issue')
            texts = '\n'.join(i['text'] for i in state['items'])
            self.assertIn('public assertion failed', texts)
            self.assertIn('Recorded file content/mode change: pkg/api.py', texts)
            self.assertIn('hypothesis', state['unknown'])
            self.assertEqual({i['status'] for i in state['items']}, {'OBSERVED'})
            self.assertTrue(state['checkpoint']['completed_boundary'])
            self.assertNotIn('FAIL_TO_PASS', json.dumps(archive))

    def test_identical_note_sources_schema_and_private_grade_exclusion(self):
        source = 'same public issue and predecessor record only'
        for kind in ('summary', 'structured'):
            messages = generation_messages(kind, source)
            self.assertIn(source, messages[1]['content'])
            self.assertNotIn('FAIL_TO_PASS', json.dumps(messages))
        fields = {name: 'UNKNOWN' for name in ('problem_understanding', 'work_completed', 'evidence_observed',
            'observed_failures_or_error_evidence', 'remaining_uncertainty', 'rollback_notes', 'recommended_next_action')}
        deterministic = deterministic_fields([], [])
        rendered = render_structured(fields, deterministic)
        self.assertIn('official classification withheld', rendered)
        with self.assertRaises(ValidationError):
            render_structured({'problem_understanding': 'only one field'}, deterministic)

    def test_docker_boundary_no_host_mounts_or_credentials(self):
        args = run_arguments('sha256:' + 'a' * 64, 'owned-unique')
        self.assertIn('none', args)
        self.assertIn('no-new-privileges', args)
        self.assertFalse(any(s in args for s in ('-v', '--mount', '--privileged', '--env', '-e', '--network=host')))
        self.assertNotIn(str(Path.home()), ' '.join(args))
        with self.assertRaises(ValidationError):
            run_arguments('mutable:latest', 'x')

    def test_real_git_cumulative_patch_staged_untracked_deleted_binary(self):
        with tempfile.TemporaryDirectory() as t:
            repo = Path(t)
            def git(*args):
                return subprocess.run(['git', '-C', t, *args], check=True, capture_output=True).stdout.decode().strip()
            git('init', '-q')
            git('config', 'user.name', 'offline fixture')
            git('config', 'user.email', 'offline@example.invalid')
            (repo / 'api.py').write_text('before\n')
            (repo / 'deleted.py').write_text('old\n')
            git('add', '-A')
            git('commit', '-qm', 'offline fixture base')
            base = git('rev-parse', 'HEAD')
            (repo / 'api.py').write_text('predecessor\n')
            git('add', 'api.py')
            (repo / 'api.py').write_text('predecessor\nsuccessor\n')
            (repo / 'new.py').write_text('new\n')
            (repo / 'deleted.py').unlink()
            (repo / 'binary.dat').write_bytes(b'\0\x01\x02')
            session = RepositorySession.__new__(RepositorySession)
            session.command = lambda cmd: subprocess.run(['/bin/bash', '-c', cmd], cwd=repo,
                 env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_GLOBAL': '/dev/null'}, capture_output=True)
            diff = session.patch(base)
            self.assertIn('+predecessor', diff)
            self.assertIn('+successor', diff)
            self.assertIn('new.py', diff)
            self.assertIn('deleted file mode', diff)
            self.assertIn('GIT binary patch', diff)
            prediction = write_prediction(repo / 'prediction.jsonl', {'instance_id': 'actual-id'}, 'fixed-model', diff)
            self.assertEqual(json.loads((repo / 'prediction.jsonl').read_text()), prediction)
            self.assertEqual(set(prediction), {'instance_id', 'model_name_or_path', 'model_patch'})
            self.assertNotEqual(unique_run_id('actual-id', 'KEISHO_2K', diff), unique_run_id('actual-id', 'KEISHO_2K', diff))

    def test_new_cost_cap_and_unknown_attempt_stop(self):
        with self.assertRaises(ValidationError):
            SpendLedger('10')
        ledger = SpendLedger('10', provider='openrouter', authorized_ceiling_usd='10', authorization_scope='swebench-one-comparison')
        r = ledger.reserve('predecessor', 'openai/gpt-4.1-mini-2025-04-14', 32000, 2048, 2000)
        ledger.unknown(r, 'charged failed request unknown')
        self.assertGreater(ledger.held, 0)
        with self.assertRaises(ProviderFailure):
            ledger.reserve('successor', 'openai/gpt-4.1-2025-04-14', 32000, 2048, 2000)
        small = SpendLedger('.01', provider='openrouter', authorized_ceiling_usd='10', authorization_scope='swebench-one-comparison')
        with self.assertRaises(ProviderFailure):
            small.reserve('successor', 'openai/gpt-4.1-2025-04-14', 32000, 2048, 2000)
        self.assertFalse(small.records)

    def test_setup_error_never_admits_paid_calls(self):
        with patch('keisho.benchmark.comparison.ROOT', Path('/nonexistent-test-fixture')):
            with self.assertRaises(ValidationError):
                validate_setup({'smoke_instance': 'setup-id'})
        self.assertEqual(report_status({'resolved_ids': ['setup-id']}, 'setup-id'), 'resolved')
        self.assertEqual(report_status({'unresolved_ids': ['setup-id']}, 'setup-id'), 'unresolved')
        self.assertEqual(report_status({'error_ids': ['setup-id']}, 'setup-id'), 'error')

    def test_original_issue_is_outside_handoff_budget_and_remains_in_state(self):
        original = 'Original issue details ' * 3000
        state = {'goal': original, 'acceptance': ['Resolve original issue'], 'constraints': [],
                 'items': [], 'unknown': {}, 'warnings': []}
        workspace = {'files': [], 'exclusions': [], 'original_issue_supplied_separately': True,
                     'benchmark_environment': 'Independent frozen container.'}
        class FixtureCounter:
            count = ScriptedModel().count_tokens
        text, meta = compile_handoff(state, workspace, 2048, FixtureCounter())
        self.assertLessEqual(meta['tokens'], 2048)
        self.assertNotIn(original, text)
        self.assertEqual(state['goal'], original)
        self.assertIn('supplied separately and verbatim', text)


if __name__ == '__main__':
    unittest.main()
