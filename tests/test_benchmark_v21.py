"""Prospective v2.1 freeze, robust reader admission, and offline proving suite."""
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import canonical_json, digest, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Message, ModelRequest, Recorder, parse_output, run_agent
from keisho.pilot.response_policy import extract_action_json, AUXILIARY, STRICT
from keisho.pilot.tokenizer import NativeTokenizer
from keisho.agents.providers import openrouter_chat, openai_chat

WORKFLOW_BLOCK_VERBATIM = (
    "Workflow: 1. Read the issue and locate the relevant code with targeted shell searches (grep, head) "
    "instead of reading whole modules. 2. Reproduce the problem with a short script or an existing test when practical. "
    "3. Make the smallest edit that fixes it; make your first edit by turn 12. 4. Run the relevant public tests. "
    "5. When tests pass, call finish with a short summary. Do not spend more than a third of your budget exploring."
)



def _v21_superseded():
    """True on branches (v2.4+) where a v2.1-pinned component has moved on; v2.1 must then refuse (fail closed)."""
    import hashlib, json as _json
    m = _json.loads((c.ROOT / 'analysis/swebench-experiment-v2.1-manifest.json').read_text())
    return any((c.ROOT / f).is_file() and hashlib.sha256((c.ROOT / f).read_bytes()).hexdigest() != h
               for f, h in m['files'].items() if f in ('src/keisho/pilot/agent.py', 'src/keisho/benchmark/evaluator.py'))

class Version21Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v2.1.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v2.0.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        expected_changed = {
            'version', 'supersedes_configuration',
            'experiment_manifest', 'experiment_manifest_sha256'
        }
        self.assertEqual(changed, expected_changed)
        self.assertEqual(digest(self.config), c.V21_SPEC_SHA)
        self.assertEqual(self.config['version'], 'swebench-handoff/2.1')
        self.assertEqual(self.config['supersedes_configuration'], 'configs/swebench-comparison-v2.0.json')

        # Models, pricing, and reasoning effort preserved from v2.0
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-6-sol-20260922')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-6-sol-20260922')
        self.assertEqual(self.config['generation_model'], 'openai/gpt-6-luna-20260922')
        self.assertEqual(self.config['provider_config'], 'calibration-task001-openrouter-v2.0.yaml')

        # Budgets preserved from v2.0
        self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 276000)
        self.assertEqual(self.config['successor_budgets']['total_tokens'], 248400)
        self.assertEqual(self.config['predecessor_budgets']['model_calls'], 48)
        self.assertEqual(self.config['successor_budgets']['model_calls'], 64)
        self.assertEqual(self.config['predecessor_budgets']['request_input_tokens'], 64000)
        self.assertEqual(self.config['successor_budgets']['request_input_tokens'], 64000)
        self.assertEqual(self.config['predecessor_budgets']['output_tokens'], 2048)
        self.assertEqual(self.config['successor_budgets']['output_tokens'], 2048)

        # Invariant prompt, task, tools, and execution flags
        self.assertEqual(self.config['selected_instance'], 'sympy__sympy-20590')
        self.assertEqual(self.config['agent_prompt_version'], 'benchmark-agent/5.0')
        self.assertEqual(self.config['agent_prompt_sha256'], digest(c.SYSTEM_V5))
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertEqual(self.config['cap_usd'], '10.00')
        self.assertEqual(self.config['automatic_retries'], 0)
        self.assertFalse(self.config['live_execution_authorized'])

    def test_prompts_byte_identical_to_system_v5_and_workflow_block_present(self):
        self.assertEqual(self.config['agent_prompt_sha256'], digest(c.SYSTEM_V5))
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, c.SYSTEM_V5)

        system, policy, _ = c.response_settings(self.config)
        self.assertEqual(system, c.SYSTEM_V5)
        self.assertEqual(policy, 'auxiliary-claims/2.0')

        takeover = json.loads(c.PROMPTS.read_text())['takeover']
        successor_system = system + takeover
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, successor_system)

        for condition in self.config['conditions']:
            with self.subTest(condition=condition):
                self.assertIn(WORKFLOW_BLOCK_VERBATIM, successor_system)
                self.assertEqual(successor_system.replace(c.WORKFLOW_GUIDANCE, ''),
                                 c.SYSTEM_V4 + takeover)

    def test_real_component_manifest_verifies_before_admission(self):
        if _v21_superseded():
            with self.assertRaisesRegex(ValidationError, 'frozen experiment component changed'):
                validate_freeze(self.config, c.ROOT)
            return
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 84)
        self.assertIn('src/keisho/pilot/agent.py', manifest['files'])
        self.assertIn('src/keisho/pilot/response_policy.py', manifest['files'])
        self.assertIn('configs/calibration-task001-openrouter-v2.0.yaml', manifest['files'])

        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v2.1.json',
                                        c.ROOT / 'analysis/swebench-comparison-v2.1-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 2380)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.53369760')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.155904')

        peak = Decimal(plan['total_envelope_usd']) + Decimal(plan['largest_request_reservation_usd'])
        cap = Decimal(self.config['cap_usd'])
        self.assertLessEqual(peak, cap)
        margin = (cap - peak) / cap
        self.assertGreaterEqual(margin, Decimal('0.03'))

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v2.1.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v2.1-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v2.1-authorization-template.json',
                        run_dir=Path(t).resolve() / 'not-started-v21')
            if _v21_superseded():
                with patch.object(c, 'runtime_preflight', side_effect=AssertionError('preflight must not run')):
                    with self.assertRaises(ValidationError):
                        c.execute(approve_live=True, **args)
                self.assertFalse(args['run_dir'].exists())
                return
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
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v2.1.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v2.1-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v2.1-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-v21-out')
            out = c.dry_run(**args)
            self.assertTrue(out['dry_run'])
            self.assertEqual(out['tool_output_policy'], 'bounded-output/1.0')
            self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 276000)
            self.assertEqual(self.config['successor_budgets']['total_tokens'], 248400)
            self.assertEqual(self.config['predecessor_budgets']['request_input_tokens'], 64000)
            self.assertEqual(self.config['successor_budgets']['request_input_tokens'], 64000)
            self.assertEqual(out['cost_envelope_usd'], '9.53369760')
            self.assertEqual(out['reservation_headroom_usd'], '0.155904')
            self.assertFalse(out['guard_created'])

    def test_model_configuration_pricing_and_reasoning_effort(self):
        self.assertIn('openai/gpt-6-sol-20260922', openrouter_chat.MODEL_PRICES)
        self.assertIn('openai/gpt-6-luna-20260922', openrouter_chat.MODEL_PRICES)
        self.assertEqual(openrouter_chat.MODEL_PRICES['openai/gpt-6-sol-20260922'],
                         (Decimal('2.00'), Decimal('0.20'), Decimal('10.00')))
        self.assertEqual(openrouter_chat.MODEL_PRICES['openai/gpt-6-luna-20260922'],
                         (Decimal('0.10'), Decimal('0.01'), Decimal('0.50')))

        tok = NativeTokenizer()
        m_sol = c.V20OpenRouterChatModel('openai/gpt-6-sol-20260922', authorized=True, tokenizer=tok)
        body_sol = m_sol.body(ModelRequest((Message('user', 'test prompt'),), 20261007, 2048, 0.0))
        self.assertEqual(body_sol['model'], 'openai/gpt-6-sol')
        self.assertEqual(body_sol['reasoning'], {'effort': 'none'})
        self.assertNotIn('temperature', body_sol)
        self.assertEqual(body_sol['max_tokens'], 2048)

        m_luna = c.V20OpenRouterChatModel('openai/gpt-6-luna-20260922', authorized=True, tokenizer=tok, mode='summary')
        body_luna = m_luna.body(ModelRequest((Message('user', 'test summary'),), 20261007, 1600, 0.0))
        self.assertEqual(body_luna['model'], 'openai/gpt-6-luna')
        self.assertEqual(body_luna['reasoning'], {'effort': 'none'})
        self.assertNotIn('temperature', body_luna)
        self.assertEqual(body_luna['max_tokens'], 1600)

    def test_offline_proving_suite_saved_v20_and_edge_cases(self):
        # 1. Exact saved v2.0 Call 1 response
        saved_file = c.ROOT / 'runs/swebench-v2.0-five-way-once-001/predecessor/predecessor_call_001-response.json'
        self.assertTrue(saved_file.is_file(), 'saved v2.0 response missing')
        saved_text = json.loads(saved_file.read_text())['text']

        data, framing = extract_action_json(saved_text)
        self.assertEqual(data['action']['tool'], 'shell')
        self.assertTrue(data['action']['command'].startswith('git status --short'))
        self.assertEqual(data['claims'], [])
        self.assertTrue(framing['has_framing'])
        self.assertFalse(framing['is_fenced'])
        self.assertEqual(framing['stripped_leading'],
                         "I’ll trace Symbol’s inheritance and slot definitions, reproduce the behavior, then make the smallest fix and run the relevant tests.\n\n")
        self.assertEqual(framing['stripped_trailing'], "")

        # Also prove via parse_output in both AUXILIARY and STRICT policies
        aux_out = parse_output(saved_text, set(), policy=AUXILIARY)
        self.assertEqual(aux_out['action']['tool'], 'shell')
        self.assertEqual(aux_out['framing'], framing)

        strict_out = parse_output(saved_text, set(), policy=STRICT)
        self.assertEqual(strict_out['action']['tool'], 'shell')
        self.assertEqual(strict_out['framing'], framing)

        # 2. Clean JSON
        clean_text = '{"action": {"tool": "list_files"}, "claims": []}'
        data, framing = extract_action_json(clean_text)
        self.assertEqual(data['action']['tool'], 'list_files')
        self.assertFalse(framing['has_framing'])
        self.assertEqual(framing['stripped_leading'], '')
        self.assertEqual(framing['stripped_trailing'], '')

        # 3. Leading and trailing prose (without wrapper characters)
        prose_text = 'Checking code now.\n\n{"action": {"tool": "list_files"}, "claims": []}\n\nWill report.'
        data, framing = extract_action_json(prose_text)
        self.assertEqual(data['action']['tool'], 'list_files')
        self.assertTrue(framing['has_framing'])
        self.assertEqual(framing['stripped_leading'], 'Checking code now.\n\n')
        self.assertEqual(framing['stripped_trailing'], '\n\nWill report.')

        # 4. Code fences with and without tag
        fenced_tag = 'Prose:\n```json\n{"action": {"tool": "list_files"}, "claims": []}\n```\nDone.'
        data, framing = extract_action_json(fenced_tag)
        self.assertEqual(data['action']['tool'], 'list_files')
        self.assertTrue(framing['is_fenced'])
        self.assertTrue(framing['has_framing'])

        fenced_notag = '```\n{"action": {"tool": "list_files"}, "claims": []}\n```'
        data, framing = extract_action_json(fenced_notag)
        self.assertEqual(data['action']['tool'], 'list_files')
        self.assertTrue(framing['is_fenced'])

        # 5. Strings containing braces and escaped quotes
        str_with_braces = '{"action": {"tool": "shell", "command": "echo \\"{brace}\\" and \\"quote\\""}, "claims": []}'
        data, framing = extract_action_json(str_with_braces)
        self.assertEqual(data['action']['command'], 'echo "{brace}" and "quote"')

        # 6. REJECTIONS: JSON inside and outside a fence
        with self.assertRaisesRegex(ValidationError, 'forbidden wrapper characters'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": []}\n```json\n{"action": {"tool": "list_files"}, "claims": []}\n```')

        # 7. REJECTIONS: Multiple objects
        with self.assertRaisesRegex(ValidationError, 'forbidden wrapper characters or trailing content'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": []}\n{"action": {"tool": "list_files"}, "claims": []}')

        # 8. REJECTIONS: Array wrappers (unfenced and fenced)
        with self.assertRaisesRegex(ValidationError, 'forbidden wrapper characters'):
            extract_action_json('[{"action": {"tool": "list_files"}, "claims": []}]')
        with self.assertRaisesRegex(ValidationError, 'no JSON object found'):
            extract_action_json('```json\n[{"action": {"tool": "list_files"}, "claims": []}]\n```')

        # 9. REJECTIONS: Quoted wrappers (unfenced and fenced)
        with self.assertRaisesRegex(ValidationError, 'forbidden wrapper characters'):
            extract_action_json('"{\\"action\\": {\\"tool\\": \\"list_files\\"}, \\"claims\\": []}"')
        with self.assertRaisesRegex(ValidationError, 'no JSON object found'):
            extract_action_json('```json\n"{\\"action\\": {\\"tool\\": \\"list_files\\"}, \\"claims\\": []}"\n```')

        # 10. REJECTIONS: Malformed outer JSON alone (never salvage nested)
        with self.assertRaisesRegex(ValidationError, 'malformed outer JSON'):
            extract_action_json('{"corrupted": [1, {"action": {"tool": "list_files"}, "claims": []}')

        # 11. REJECTIONS: Malformed outer JSON after prose (never salvage nested)
        with self.assertRaisesRegex(ValidationError, 'malformed outer JSON'):
            extract_action_json('Here is my plan: {"corrupted": [1, {"action": {"tool": "list_files"}, "claims": []}')

        # 12. REJECTIONS: Multiple fences
        with self.assertRaisesRegex(ValidationError, 'expected exactly one code block'):
            extract_action_json('```json\n{"action": {"tool": "list_files"}, "claims": []}\n```\n```json\n{}\n```')

        # 13. REJECTIONS: Duplicate keys
        with self.assertRaisesRegex(ValidationError, 'ambiguous duplicate JSON key'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": [], "action": {"tool": "finish"}}')

        # 14. REJECTIONS: Nonfinite constants (NaN, Infinity, -Infinity)
        with self.assertRaisesRegex(ValidationError, 'non-JSON numeric constant: NaN'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": [], "bad": NaN}')
        with self.assertRaisesRegex(ValidationError, 'non-JSON numeric constant: Infinity'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": [], "bad": Infinity}')
        with self.assertRaisesRegex(ValidationError, 'non-JSON numeric constant: -Infinity'):
            extract_action_json('{"action": {"tool": "list_files"}, "claims": [], "bad": -Infinity}')

        # 15. REJECTIONS: Prose only
        with self.assertRaisesRegex(ValidationError, 'no JSON object found in response'):
            extract_action_json('I will read the repository files and write a patch.')

        # 16. REJECTIONS: Invalid action schemas (via parse_output)
        with self.assertRaisesRegex(ValidationError, 'response must contain action and claims only'):
            parse_output('{"action": {"tool": "list_files"}}', set(), policy=AUXILIARY)
        with self.assertRaisesRegex(ValidationError, 'invalid action/claims types'):
            parse_output('{"action": "list_files", "claims": []}', set(), policy=AUXILIARY)

    def test_run_agent_logs_stripped_framing_and_preserves_raw_response(self):
        saved_file = c.ROOT / 'runs/swebench-v2.0-five-way-once-001/predecessor/predecessor_call_001-response.json'
        saved_text = json.loads(saved_file.read_text())['text']

        class MockModel:
            def __init__(self):
                self._tok = NativeTokenizer()
            def model_id(self): return 'openai/gpt-6-sol-20260922'
            def count_tokens(self, text): return self._tok.count(text)
            def generate(self, req):
                from keisho.agents.base import ModelResponse, Usage
                return ModelResponse('openai/gpt-6-sol-20260922', saved_text, Usage(100, 50, 0, '0.001', 'mock_source'), 'stop')

        class MockSession:
            def validate_action(self, action): return True
            def execute(self, action):
                return {'output': 'test_output', 'exit_code': 0}

        with tempfile.TemporaryDirectory() as t:
            raw = RawRun(Path(t), 'predecessor')
            recorder = Recorder(raw)
            budgets = Budgets(1, 1, 2048, 10000, 64000, 128000)
            res = run_agent(MockModel(), MockSession(), recorder, 'test task',
                            c.SYSTEM_V5, '', 1, budgets, role='predecessor',
                            response_policy=AUXILIARY, action_wire_version='flat-or-args/1.0')

            self.assertEqual(res.model_calls, 1)
            self.assertEqual(res.tool_calls, 1)

            # Framing artifact logged
            framing_file = Path(t) / 'predecessor' / 'predecessor_call_001-stripped-framing.json'
            self.assertTrue(framing_file.is_file(), 'stripped framing artifact not written')
            framing_data = json.loads(framing_file.read_text())
            self.assertTrue(framing_data['has_framing'])
            self.assertEqual(framing_data['stripped_leading'],
                             "I’ll trace Symbol’s inheritance and slot definitions, reproduce the behavior, then make the smallest fix and run the relevant tests.\n\n")

            # Raw response preserved
            resp_file = Path(t) / 'predecessor' / 'predecessor_call_001-response.json'
            self.assertTrue(resp_file.is_file())
            resp_data = json.loads(resp_file.read_text())
            self.assertEqual(resp_data['text'], saved_text)


if __name__ == '__main__':
    unittest.main()
