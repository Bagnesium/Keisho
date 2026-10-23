"""Reader-coverage audit tests for v2.1 (added on review branch; tests only, no protocol change).

The real v2.0 call-1 response (runs/swebench-v2.0-five-way-once-001/...) is gitignored and absent
from the public repository. RealReplay tests skip when it is missing; Reconstructed tests use a
clearly synthetic stand-in built from the prose and command prefix quoted in tests/test_benchmark_v21.py
and protocol_amendments/swebench-interface-v2.1.md. A reconstruction is NOT evidence about the real bytes.
"""
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from keisho.benchmark import comparison as c
from keisho.core import ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, parse_output, run_agent
from keisho.pilot.response_policy import extract_action_json, AUXILIARY, STRICT

REAL = c.ROOT / 'runs/swebench-v2.0-five-way-once-001/predecessor/predecessor_call_001-response.json'
PROSE = ("I\u2019ll trace Symbol\u2019s inheritance and slot definitions, reproduce the behavior, "
         "then make the smallest fix and run the relevant tests.\n\n")
SYNTHETIC = PROSE + '{"action":{"tool":"shell","command":"git status --short && grep -rn __slots__ sympy/core/symbol.py"},"claims":[]}'
OK = '{"action": {"tool": "list_files"}, "claims": []}'


def _replay(text):
    from keisho.agents.base import ModelResponse, Usage, TokenCount
    executed = []

    class Model:
        def model_id(self): return 'openai/gpt-6-sol-20260922'
        def count_tokens(self, t): return TokenCount(len(t), "test-char-upper-bound", True)  # offline upper-bound stand-in; no tokenizer asset needed
        def generate(self, req):
            return ModelResponse('openai/gpt-6-sol-20260922', text, Usage(100, 50, 0, '0.001', 'mock'), 'stop')

    class Session:
        def validate_action(self, action): return True
        def execute(self, action):
            executed.append(action)
            return {'output': 'ok', 'exit_code': 0}

    t = tempfile.TemporaryDirectory()
    raw = RawRun(Path(t.name), 'predecessor')
    run_agent(Model(), Session(), Recorder(raw), 'task', c.SYSTEM_V5, '', 1,
              Budgets(1, 1, 2048, 10000, 64000, 128000), role='predecessor',
              response_policy=AUXILIARY, action_wire_version='flat-or-args/1.0')
    base = Path(t.name) / 'predecessor'
    framing = base / 'predecessor_call_001-stripped-framing.json'
    return t, executed, (json.loads(framing.read_text()) if framing.is_file() else None), base


class RealReplay(unittest.TestCase):
    @unittest.skipUnless(REAL.is_file(), 'real v2.0 call-1 response is gitignored/absent in this checkout')
    def test_real_v20_call1_executes_shell_and_logs_framing(self):
        text = json.loads(REAL.read_text())['text']
        t, executed, framing, base = _replay(text)
        with t:
            self.assertEqual(len(executed), 1)
            self.assertEqual(executed[0]['tool'], 'shell')
            self.assertTrue(executed[0]['command'].startswith('git status --short'))
            self.assertTrue(framing['has_framing'])
            self.assertEqual(json.loads((base / 'predecessor_call_001-response.json').read_text())['text'], text)


class Reconstructed(unittest.TestCase):
    def test_synthetic_prose_then_json_executes_shell_and_logs_framing(self):
        t, executed, framing, base = _replay(SYNTHETIC)
        with t:
            self.assertEqual([a['tool'] for a in executed], ['shell'])
            self.assertTrue(executed[0]['command'].startswith('git status --short'))
            self.assertEqual(framing['stripped_leading'], PROSE)
            self.assertFalse(framing['is_fenced'])
            self.assertEqual(json.loads((base / 'predecessor_call_001-response.json').read_text())['text'], SYNTHETIC)

    def test_prose_only_executes_nothing_and_records_failure(self):
        t, executed, framing, base = _replay('I will inspect the repository first.')
        with t:
            self.assertEqual(executed, [])
            self.assertIsNone(framing)
            self.assertTrue((base / 'predecessor_call_001-protocol-failure.json').is_file())


class EdgeCases(unittest.TestCase):
    def rej(self, text, pattern='.'):
        with self.assertRaisesRegex(ValidationError, pattern):
            extract_action_json(text)

    def test_nested_salvage_valid_outer_not_unwrapped(self):
        data, _ = extract_action_json('Plan: {"wrapper": ' + OK + '}')
        self.assertEqual(set(data), {'wrapper'})
        for policy in (STRICT, AUXILIARY):
            with self.assertRaises(ValidationError):
                parse_output('Plan: {"wrapper": ' + OK + '}', set(), policy=policy)

    def test_nested_salvage_inside_fence(self):
        self.rej('```json\n{"bad": ' + OK + '\n```', 'malformed JSON inside code fence')

    def test_multiple_objects_with_prose_between(self):
        self.rej(OK + ' and also ' + OK, 'trailing')

    def test_fence_then_json_outside(self):
        self.rej('```json\n' + OK + '\n```\n' + OK, 'after code fence')

    def test_prose_with_quote_before_json_rejected(self):
        self.rej('I said "hi" ' + OK, 'before JSON object')

    def test_array_wrapper_after_prose(self):
        self.rej('Here: [' + OK + ']', 'before JSON object')

    def test_duplicate_keys_nested_and_fenced(self):
        self.rej('{"action": {"tool": "a", "tool": "b"}, "claims": []}', 'duplicate')
        self.rej('```json\n{"action": {}, "claims": [], "claims": []}\n```', 'duplicate')

    def test_nonfinite_nested_and_fenced(self):
        self.rej('{"action": {"tool": "x", "n": [NaN]}, "claims": []}', 'NaN')
        self.rej('```json\n{"action": {"tool": "x", "n": -Infinity}, "claims": []}\n```', '-Infinity')
        self.rej('Prose. {"action": {"tool": "x", "n": Infinity}, "claims": []}', 'Infinity')

    def test_strict_policy_accepts_prose_framing_and_keeps_strict_checks(self):
        out = parse_output('Note.\n' + OK, set(), policy=STRICT)
        self.assertEqual(out['action']['tool'], 'list_files')
        self.assertTrue(out['framing']['has_framing'])
        with self.assertRaisesRegex(ValidationError, 'duplicate'):
            parse_output('{"action": {}, "action": {}, "claims": []}', set(), policy=STRICT)

    def test_malformed_outer_inside_fence_with_prose(self):
        self.rej('Plan below\n```json\n{"action": {"tool": "x"}, "claims": [\n```', 'malformed JSON inside code fence')


class CallerCoverage(unittest.TestCase):
    @unittest.expectedFailure
    def test_structured_note_generation_uses_guarded_reader(self):
        """Documents a gap: make_handoffs parses STRUCTURED_NOTES_2K with plain json.loads(response.text)
        (no duplicate-key rejection, no prose/framing tolerance or framing log). Expected to fail on v2.1."""
        src = inspect.getsource(c.make_handoffs)
        self.assertNotIn('json.loads(response.text)', src)


if __name__ == '__main__':
    unittest.main()
