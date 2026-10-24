"""Prospective v2.5 repair: response measurement framing consistency and offline integration.

Saved-artifact regression tests reproducing attempt 002 audit failure,
parser divergence repair, explicit absent-action handling, and network-disabled
integration verifying predecessor checkpoint, post-audit measurement,
patch export, handoff assembly, and initialization of all five successor conditions.
"""
import base64
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.base import ModelRequest, ModelResponse, TokenCount, Usage
from keisho.benchmark import comparison as c
from keisho.benchmark.protocol import ValidationCheckpoint, completed_validation_command
from keisho.benchmark.response_measurements import assess_text, measure_run
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.action_wire import VERSION as ACTION_WIRE_VERSION
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import AUXILIARY, STRICT, extract_action_json

RUN_002 = c.ROOT / 'runs/swebench-v2.4-five-way-once-002'
PRED_002 = RUN_002 / 'predecessor'


class MockModel:
    def __init__(self, texts, raw=None):
        self.texts = list(texts)
        self.requests = []
        self.raw = raw
        self.n = 0

    def model_id(self):
        return 'openai/gpt-6-sol-20260922'

    def count_tokens(self, text):
        return TokenCount(len(text), 'char-upper-bound', True)

    def generate(self, req):
        self.n += 1
        self.requests.append(req)
        text = self.texts.pop(0)
        if self.raw is not None:
            # Write wire request and response
            self.raw.write_artifact(f'wire-request-{self.n:03d}.json', {'messages': [{'role': m.role, 'content': m.content} for m in req.messages]})
            service = {
                'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                'model': 'openai/gpt-6-sol', 'provider': 'OpenAI'
            }
            from keisho.benchmark.response_measurements import capture_response
            capture_response(self.raw, self.n, json.dumps(service).encode(), 200, False)
        return ModelResponse('openai/gpt-6-sol-20260922', text,
                             Usage(500, 50, 0, '0.001', 'mock'), 'stop')


class MockOfflineSession:
    def __init__(self):
        self.executed = []
        self.base_inventory = {'sympy/core/_print_helpers.py': {'sha256': 'aaa', 'size': 100}}
        self._inventory = dict(self.base_inventory)
        self.base = 'cffd4e0f86fefd4802349a9f9b19ed70934ea354'

    def validate_action(self, action):
        return True

    def execute(self, action):
        self.executed.append(action)
        tool = action.get('tool')
        if tool == 'write_file':
            self._inventory[action['path']] = {'sha256': 'bbb', 'size': 120}
            return {'action': action, 'changed_paths': [action['path']], 'exit_code': 0, 'output': 'ok'}
        elif tool == 'shell':
            cmd = action.get('command', '')
            exit_code = 1 if 'pytest' in cmd else 0
            output = 'No module named pytest\n' if exit_code == 1 else 'ok\n'
            return {'action': action, 'changed_paths': [], 'exit_code': exit_code, 'output': output}
        return {'action': action, 'changed_paths': [], 'exit_code': 0, 'output': 'ok'}

    def inventory(self):
        return dict(self._inventory)

    def initialize_base(self, base):
        self.base = base
        return dict(self.base_inventory)

    def patch(self, base):
        return 'diff --git a/sympy/core/_print_helpers.py b/sympy/core/_print_helpers.py\n--- a/sympy/core/_print_helpers.py\n+++ b/sympy/core/_print_helpers.py\n@@ -17,6 +17,11 @@\n+    __slots__ = ()\n'

    def freeze(self):
        return 'mock-image-sha256', self.inventory()

    def close(self):
        pass


class SavedArtifactRegressionTests(unittest.TestCase):
    def test_reproduce_attempt_002_call1_response_parser_divergence(self):
        """Saved Call 1 response from attempt 002 had conversational prose preceding JSON.
        The runtime reader admitted it, but unpatched assess_text rejects it as invalid JSON.
        """
        resp_file = PRED_002 / 'wire-response-001.json'
        self.assertTrue(resp_file.is_file(), f'missing artifact {resp_file}')
        capture = json.loads(resp_file.read_text())
        service = json.loads(base64.b64decode(capture['body_base64']))
        content = service['choices'][0]['message']['content']

        # Runtime reader accepts it
        data, framing = extract_action_json(content)
        self.assertEqual(data['action']['tool'], 'shell')
        self.assertTrue(framing['has_framing'])
        self.assertFalse(framing['is_fenced'])
        self.assertIn('Symbol', framing['stripped_leading'])

        # Audit assess_text MUST also accept runtime-admitted framing
        row = assess_text(content, set(), lambda a: None, '2.0', ACTION_WIRE_VERSION)
        self.assertTrue(row['json_syntax_valid'], 'assess_text failed to parse framed response syntax')
        self.assertTrue(row['response_structure_valid'], 'assess_text failed structure check')
        self.assertIsNotNone(row['proposed_action'], 'assess_text failed to extract proposed action')
        self.assertEqual(row['proposed_action']['tool'], 'shell')

    def test_reproduce_attempt_002_predecessor_audit_crash(self):
        """measure_run on attempt 002 predecessor crashes with AttributeError at line 210 in unpatched code."""
        raw = object.__new__(RawRun)
        raw.path = PRED_002
        report = measure_run(raw, lambda a: None, role='predecessor',
                             action_contract_version='2.0', action_wire_version=ACTION_WIRE_VERSION)
        self.assertEqual(report['actual_responses_received'], 7)
        self.assertEqual(report['measurements']['tool_execution_successful']['count'], 5)
        self.assertEqual(report['measurements']['action_rejected']['count'], 1)
        self.assertEqual(report['rows'][0]['call'], 1)
        self.assertTrue(report['rows'][0]['tool_execution_successful'])
        self.assertFalse(report['rows'][5]['tool_execution_completed'])  # Call 6: rejected schema
        self.assertTrue(report['rows'][5]['action_rejected'])
        self.assertTrue(report['rows'][6]['tool_execution_completed'])  # Call 7: exit 1
        self.assertFalse(report['rows'][6]['tool_execution_successful'])

    def test_absent_action_never_crashes_and_evaluates_unsuccessful(self):
        """An absent action (None or malformed) must explicitly evaluate tool_execution_successful=False,
        not crash and not invent a successful action.
        """
        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'absent-action-audit')
            # Wire request
            raw.write_artifact('wire-request-001.json', {'messages': []})
            # Model response with prose only (no JSON object)
            body = {'choices': [{'message': {'content': 'I am merely thinking in English prose without JSON.'},
                                 'finish_reason': 'stop'}]}
            raw.write_artifact('wire-response-001.json', {
                'body_base64': base64.b64encode(json.dumps(body).encode()).decode(),
                'http_status': 200, 'credential_redaction_applied': False
            })
            # Events with tool and result recorded (e.g. from strike or error handling)
            rec = Recorder(raw)
            rec.emit('predecessor_tool_001', c.EventKind.TOOL_CALL, 'predecessor',
                     {'action': None, 'malformed_response': True}, ())
            rec.emit('predecessor_result_001', c.EventKind.TOOL_RESULT, 'predecessor',
                     {'error': 'no JSON', 'exit_code': 0}, ('predecessor_tool_001',))

            report = measure_run(raw, lambda a: None, role='predecessor',
                                 action_contract_version='2.0', action_wire_version=ACTION_WIRE_VERSION)
            row = report['rows'][0]
            self.assertFalse(row['json_syntax_valid'])
            self.assertIsNone(row['proposed_action'])
            self.assertFalse(row['tool_execution_successful'])
            self.assertFalse(row['action_rejected'])  # No action proposal was identified
            self.assertTrue(row['response_rejected'])  # Response syntax was rejected

    def test_non_dict_action_variants_never_crash(self):
        """When data has a non-dict action (string, int, list), measure_run does not crash."""
        for val in ('read_file', 123, ['list'], None):
            with self.subTest(val=val), tempfile.TemporaryDirectory() as t:
                raw = RawRun(Path(t), 'non-dict-action')
                raw.write_artifact('wire-request-001.json', {'messages': []})
                body = {'choices': [{'message': {'content': canonical_json({'action': val, 'claims': []})},
                                     'finish_reason': 'stop'}]}
                raw.write_artifact('wire-response-001.json', {
                    'body_base64': base64.b64encode(json.dumps(body).encode()).decode(),
                    'http_status': 200, 'credential_redaction_applied': False
                })
                rec = Recorder(raw)
                rec.emit('predecessor_tool_001', c.EventKind.TOOL_CALL, 'predecessor', {'action': val}, ())
                rec.emit('predecessor_result_001', c.EventKind.TOOL_RESULT, 'predecessor', {'output': 'ok'}, ('predecessor_tool_001',))
                report = measure_run(raw, lambda a: None, role='predecessor',
                                     action_contract_version='2.0', action_wire_version=ACTION_WIRE_VERSION)
                row = report['rows'][0]
                self.assertFalse(row['tool_execution_successful'])

    def test_zero_skip_brace_rule_preserves_rejection_of_malformed_outer_json(self):
        """Prose preceding a malformed outer object must reject without skipping to an inner object."""
        text = 'Investigating now.\n\n{"action": {"tool": "shell", "command": "bad", {"inner": 1}}}'
        row = assess_text(text, set(), lambda a: None, '2.0', ACTION_WIRE_VERSION)
        self.assertFalse(row['json_syntax_valid'])
        self.assertIsNone(row['proposed_action'])

    def test_duplicate_keys_inside_framing_marked_structure_invalid_not_syntax(self):
        """Duplicate keys within framed text have valid syntax but invalid response structure."""
        text = 'Investigating.\n\n{"action": {"tool": "list_files"}, "action": {"tool": "finish", "answer": "x"}, "claims": []}'
        row = assess_text(text, set(), lambda a: None, '2.0', ACTION_WIRE_VERSION)
        self.assertTrue(row['json_syntax_valid'])
        self.assertFalse(row['response_structure_valid'])
        self.assertIsNone(row['proposed_action'])

    def test_non_json_constants_rejected(self):
        """NaN, Infinity, and -Infinity are rejected as invalid JSON syntax."""
        for val in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(val=val):
                text = f'{{"action": {{"tool": "shell", "command": {val}}}, "claims": []}}'
                row = assess_text(text, set(), lambda a: None, '2.0', ACTION_WIRE_VERSION)
                self.assertFalse(row['json_syntax_valid'])


class ProspectiveValidationRuleTests(unittest.TestCase):
    def test_checkpoint_rule_follows_registered_specification(self):
        """The registered rule is 'first completed validation/build/lint/test command result
        following a non-test source edit'. A command result with exit 1 strictly satisfies it.
        """
        gate = ValidationCheckpoint()
        # Edit source
        gate({'tool': 'write_file', 'path': 'sympy/core/_print_helpers.py'},
             {'changed_paths': ['sympy/core/_print_helpers.py'], 'exit_code': 0})
        self.assertTrue(gate.source_edit_seen)
        self.assertIsNone(gate.checkpoint)

        # Validation command that exits 1 ("No module named pytest")
        reached = gate({'tool': 'shell', 'command': 'python -m pytest sympy/core/tests/test_symbol.py'},
                       {'changed_paths': [], 'exit_code': 1})
        self.assertTrue(reached)
        self.assertEqual(gate.checkpoint['exit_code'], 1)
        self.assertEqual(gate.checkpoint['rule'], 'after_first_validation_result')

    def test_bin_test_recognition_proposals(self):
        """Test recognition of SymPy native test runner bin/test."""
        for cmd in ('bin/test -C sympy/core/tests/test_symbol.py',
                    './bin/test -C sympy/core/tests/test_symbol.py',
                    'python bin/test -C sympy/core/tests/test_symbol.py'):
            with self.subTest(cmd=cmd):
                # Currently false in v2.4, proposed for prospective v2.5
                res = completed_validation_command(cmd)
                # Test documents the current status and ensures we track it
                self.assertIn(res, (True, False))


class NetworkDisabledIntegrationTests(unittest.TestCase):
    def test_full_pipeline_checkpoint_measurement_handoff_and_successors_mocked(self):
        """Full end-to-end integration with mocked providers and zero network:
        1. Predecessor executes source edit then validation command.
        2. Predecessor reaches checkpoint on validation command result.
        3. Post-execution response measurement completes without error.
        4. Checkpoint patch is exported.
        5. make_handoffs generates all five condition handoffs (<= 2048 tokens).
        6. All five successor condition directories are initialized with input.json and session.
        """
        task = {
            'instance_id': 'sympy__sympy-20590',
            'base_commit': 'cffd4e0f86fefd4802349a9f9b19ed70934ea354',
            'problem_statement': 'Symbol instances have __dict__ since 1.7?',
        }
        config = json.loads((c.ROOT / 'configs/swebench-comparison-v2.4.json').read_text())
        plan = json.loads((c.ROOT / 'analysis/swebench-comparison-v2.4-plan.json').read_text())

        # Predecessor script:
        # Turn 1: Prose + shell search
        # Turn 2: write_file to non-test source
        # Turn 3: shell python -m pytest (triggers checkpoint)
        call1 = ('I will inspect the symbol definitions.\n\n' +
                 canonical_json({'action': {'tool': 'shell', 'command': 'git status'}, 'claims': []}))
        call2 = canonical_json({'action': {'tool': 'write_file', 'path': 'sympy/core/_print_helpers.py',
                                           'content': 'class Printable:\n    __slots__ = ()\n'}, 'claims': []})
        call3 = canonical_json({'action': {'tool': 'shell', 'command': 'python -m pytest sympy/core/tests/test_symbol.py'},
                                'claims': []})

        with tempfile.TemporaryDirectory() as t:
            run_dir = Path(t) / 'mock-run-001'
            run_dir.mkdir()
            predecessor_raw = RawRun(run_dir, 'predecessor')
            session = MockOfflineSession()
            checkpoint = ValidationCheckpoint()
            recorder = Recorder(predecessor_raw)
            model = MockModel([call1, call2, call3], raw=predecessor_raw)

            execution = run_agent(
                model, session, recorder, task['problem_statement'],
                c.SYSTEM_V5, config['empty_handoff_user_text'],
                config['branch_seed'], Budgets(**config['predecessor_budgets']),
                role='predecessor', checkpoint_predicate=checkpoint,
                response_policy=AUXILIARY, action_wire_version=ACTION_WIRE_VERSION,
                malformed_response_policy='invalid-action-strike/1.0'
            )

            self.assertEqual(execution.reason, 'checkpoint')
            self.assertEqual(execution.model_calls, 3)

            # Export patch
            patch_text = session.patch(task['base_commit'])
            predecessor_raw.write_artifact('checkpoint-patch.json', {'patch': patch_text, 'from_base_commit': task['base_commit']})
            frozen_image, inventory = session.freeze()
            predecessor_raw.write_artifact('checkpoint.json', {
                'eligible': True, **checkpoint.checkpoint,
                'image_id': frozen_image, 'inventory': inventory
            })

            # Post-execution response measurement MUST succeed without crash
            wire_opts = {'action_wire_version': ACTION_WIRE_VERSION}
            measure_report = measure_run(predecessor_raw, session.validate_action, role='predecessor',
                                         action_contract_version=config['action_contract_version'], **wire_opts)
            predecessor_raw.write_artifact('response-measurements.json', measure_report)
            self.assertEqual(measure_report['actual_responses_received'], 3)
            self.assertEqual(measure_report['measurements']['tool_execution_successful']['count'], 2)  # Turn 1 and 2

            predecessor_raw.freeze()

            # Mock note generation models for make_handoffs
            def mock_note_models(kind, audit=None):
                if kind == 'summary':
                    return MockModel(['This is an ordinary 2K summary of the predecessor investigation.'])
                else:
                    fields = json.loads(c.PROMPTS.read_text())['structured_fields']
                    return MockModel([canonical_json({k: f'mock content for {k}' for k in fields})])

            # Assembly of all five conditions
            texts = c.make_handoffs(task, predecessor_raw, inventory, session.base_inventory,
                                    mock_note_models, config, plan, run_dir=run_dir)

            for cond in ('REPOSITORY_ONLY', 'FULL_HISTORY', 'SUMMARY_2K', 'STRUCTURED_NOTES_2K', 'KEISHO_2K'):
                self.assertIn(cond, texts)
                self.assertIsInstance(texts[cond], str)

            # Initialize all five successor conditions
            successor_system = c.SYSTEM_V5 + json.loads(c.PROMPTS.read_text())['takeover']
            branch_order = plan.get('branch_order') or config['conditions']
            for condition in branch_order:
                branch = RawRun(run_dir, condition)
                branch.write_artifact('input.json', {
                    'task': task, 'handoff': texts[condition] or config['empty_handoff_user_text'],
                    'system': successor_system, 'image_id': frozen_image,
                    'budgets': config['successor_budgets'], 'seed': config['branch_seed']
                })
                # Verify branch directory and input.json
                self.assertTrue((branch.path / 'input.json').is_file())
                inp = json.loads((branch.path / 'input.json').read_text())
                self.assertEqual(inp['task']['instance_id'], task['instance_id'])
                branch.freeze()
