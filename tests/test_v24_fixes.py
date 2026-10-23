"""v2.4: malformed responses are invalid-action strikes; evaluator uses the task-specific row. Offline only."""
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from keisho.agents.base import ModelResponse, TokenCount, Usage
from keisho.benchmark import comparison as c
from keisho.benchmark import evaluator as ev
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import AUXILIARY

PROV = json.loads((Path(__file__).parent / 'data/swebench-v2.3-malformed-call8/provenance.json').read_text())
CALL8 = PROV['text']
V24 = json.loads((c.ROOT / 'configs/swebench-comparison-v2.4.json').read_text())
FINISH = json.dumps({'action': {'tool': 'finish', 'answer': 'done'}, 'claims': []})
LIST = json.dumps({'action': {'tool': 'list_files'}, 'claims': []})


class Model:
    def __init__(self, texts): self.texts, self.requests = list(texts), []
    def model_id(self): return 'openai/gpt-6-sol-20260922'
    def count_tokens(self, text): return TokenCount(len(text), 'test-char-upper-bound', True)
    def generate(self, req):
        self.requests.append(req)
        return ModelResponse('openai/gpt-6-sol-20260922', self.texts.pop(0), Usage(1000, 50, 0, '0.001', 'replay'), 'stop')


class Session:
    def __init__(self): self.executed = []
    def validate_action(self, action): return True
    def execute(self, action): self.executed.append(action); return {'output': 'ok', 'exit_code': 0}


def run(texts, policy=c.MALFORMED_RESPONSE_POLICY, tool_calls=10):
    model, session = Model(texts), Session()
    t = tempfile.mkdtemp()
    raw = RawRun(Path(t), 'predecessor')
    ex = run_agent(model, session, Recorder(raw), 'issue', c.SYSTEM_V5, V24['empty_handoff_user_text'], V24['branch_seed'],
                   Budgets(8, tool_calls, 2048, 100000, 64000, 128000), role='predecessor', response_policy=AUXILIARY,
                   action_wire_version='flat-or-args/1.0', **({'malformed_response_policy': policy} if policy else {}))
    return model, session, ex, Path(t) / 'predecessor'


class MalformedStrike(unittest.TestCase):
    def test_replay_is_byte_exact(self):
        self.assertEqual(hashlib.sha256(CALL8.encode()).hexdigest(), PROV['text_sha256'])

    def test_v23_call8_becomes_strike_one_and_run_continues(self):
        model, session, ex, raw = run([CALL8, LIST, FINISH])
        self.assertEqual(ex.reason, 'finished')
        self.assertEqual(ex.model_calls, 3)
        self.assertEqual(session.executed, [{'tool': 'list_files'}])  # malformed response executed nothing
        failure = json.loads((raw / 'predecessor_call_001-protocol-failure.json').read_text())
        self.assertEqual(failure['reason'], PROV['recorded_reason'])
        self.assertTrue(failure['counted_as_invalid_action'])
        self.assertEqual(failure['consecutive_failures_after'], 1)
        self.assertFalse(failure['automatic_retry'])
        # same rejection feedback shape as the invalid-action path
        fb = json.loads(model.requests[1].messages[-1].content)
        self.assertEqual(fb['tool_result'], {'error': PROV['recorded_reason'], 'invalid_action': PROV['recorded_reason']})
        self.assertEqual(model.requests[1].messages[-2].content, CALL8)

    def test_three_malformed_is_repeated_tool_failure(self):
        _, session, ex, _ = run([CALL8, CALL8, CALL8, FINISH])
        self.assertEqual((ex.reason, ex.model_calls, session.executed), ('repeated_tool_failure', 3, []))

    def test_valid_action_resets_strikes(self):
        _, _, ex, _ = run([CALL8, CALL8, LIST, CALL8, CALL8, FINISH])
        self.assertEqual(ex.reason, 'finished')

    def test_strikes_respect_tool_budget(self):
        _, _, ex, _ = run([CALL8, CALL8, FINISH], tool_calls=1)
        self.assertEqual(ex.model_calls, 2)

    def test_legacy_policy_unchanged_terminal(self):
        _, session, ex, _ = run([CALL8, FINISH], policy=None)
        self.assertEqual((ex.reason, ex.model_calls, session.executed), ('model_failure', 1, []))

    def test_v24_config_wires_policy(self):
        self.assertEqual(V24['version'], c.V24_VERSION)
        self.assertEqual(V24['malformed_response_policy'], c.MALFORMED_RESPONSE_POLICY)
        self.assertFalse(V24['live_execution_authorized'])
        import inspect
        self.assertEqual(inspect.getsource(c.execute).count('**malformed_options'), 2)


def private_with(row_id, task_id='sympy__sympy-20590', resolved=True):
    p = Path(tempfile.mkdtemp())
    (p / f'{task_id}-selected-task-evaluator.jsonl').write_text(json.dumps({'instance_id': row_id}) + '\n')
    (p / 'selected-task-evaluator.jsonl').write_text(json.dumps({'instance_id': 'pydata__xarray-6721'}) + '\n')
    (p / 'venv/bin').mkdir(parents=True)
    key = 'resolved_ids' if resolved else 'unresolved_ids'
    script = p / 'venv/bin/swebench'
    script.write_text('#!/bin/sh\n# offline fake of the official CLI: records argv, writes a report\nwhile [ $# -gt 0 ]; do [ "$1" = "--run-id" ] && RID=$2; shift; done\n'
                      f'mkdir -p logs/evaluation/$RID && echo \'{{"{key}": ["{task_id}"]}}\' > logs/evaluation/$RID/results.json\n')
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return p


class EvaluatorDataset(unittest.TestCase):
    task = {'instance_id': 'sympy__sympy-20590'}

    def test_task_specific_row_selected(self):
        p = private_with('sympy__sympy-20590')
        self.assertEqual(ev.evaluator_dataset(p, 'sympy__sympy-20590').name, 'sympy__sympy-20590-selected-task-evaluator.jsonl')

    def test_instance_id_mismatch_refuses(self):
        p = private_with('pydata__xarray-6721')
        with self.assertRaisesRegex(ValueError, 'instance id mismatch'):
            ev.evaluator_dataset(p, 'sympy__sympy-20590')
        (p / 'sympy__sympy-20590-selected-task-evaluator.jsonl').unlink()  # generic fallback holds another task
        with self.assertRaisesRegex(ValueError, 'instance id mismatch'):
            ev.evaluator_dataset(p, 'sympy__sympy-20590')

    def test_end_to_end_offline_grading(self):
        p = private_with('sympy__sympy-20590')
        pred = p / 'pred.jsonl'
        ev.write_prediction(pred, self.task, 'm', 'diff --git a/x b/x\n')
        r = ev.evaluate(p, V24, self.task, 'REPOSITORY_ONLY', pred, run_namespace='offline-test')
        self.assertEqual(r['status'], 'resolved')
        self.assertIn('sympy__sympy-20590-selected-task-evaluator.jsonl', r['command'][2])
        p2 = private_with('sympy__sympy-20590', resolved=False)
        pred2 = p2 / 'pred.jsonl'; ev.write_prediction(pred2, self.task, 'm', 'x')
        self.assertEqual(ev.evaluate(p2, V24, self.task, 'SUMMARY_2K', pred2)['status'], 'unresolved')
