"""Prospective v2.0 freeze, GPT-6 models transition, reasoning effort none, and budget envelope."""
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError
from keisho.pilot.tokenizer import NativeTokenizer
from keisho.agents.base import Message, ModelRequest
from keisho.agents.providers import openrouter_chat, openai_chat

WORKFLOW_BLOCK_VERBATIM = (
    "Workflow: 1. Read the issue and locate the relevant code with targeted shell searches (grep, head) "
    "instead of reading whole modules. 2. Reproduce the problem with a short script or an existing test when practical. "
    "3. Make the smallest edit that fixes it; make your first edit by turn 12. 4. Run the relevant public tests. "
    "5. When tests pass, call finish with a short summary. Do not spend more than a third of your budget exploring."
)


class Version20Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v2.0.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.9.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        expected_changed = {
            'version', 'supersedes_configuration',
            'predecessor_model', 'successor_model', 'generation_model',
            'provider_config', 'predecessor_budgets', 'successor_budgets',
            'experiment_manifest', 'experiment_manifest_sha256'
        }
        self.assertEqual(changed, expected_changed)
        self.assertEqual(digest(self.config), c.V20_SPEC_SHA)
        self.assertEqual(self.config['version'], 'swebench-handoff/2.0')
        self.assertEqual(self.config['supersedes_configuration'], 'configs/swebench-comparison-v1.9.json')

        # Models switched to GPT-6
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-6-sol-20260922')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-6-sol-20260922')
        self.assertEqual(self.config['generation_model'], 'openai/gpt-6-luna-20260922')
        self.assertEqual(self.config['provider_config'], 'calibration-task001-openrouter-v2.0.yaml')

        # Proportional budget ceilings scaled by 69% preserving 10:9 ratio
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
        self.assertFalse(self.config['live_execution_authorized'])

    def test_prompts_byte_identical_to_system_v5_and_workflow_block_present(self):
        # 1. System prompt byte-identical to SYSTEM_V5
        self.assertEqual(self.config['agent_prompt_sha256'], digest(c.SYSTEM_V5))
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, c.SYSTEM_V5)

        # 2. Check predecessor and all 5 successor conditions receive the prompt identically
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
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 84)
        self.assertIn('runs/swebench-integration/preselection/sympy__sympy-20590-task.json', manifest['files'])
        self.assertIn('configs/calibration-task001-openrouter-v2.0.yaml', manifest['files'])
        self.assertIn('runs/swebench-integration/preselection/provider-catalog-v2.0.json', manifest['files'])

        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v2.0.json',
                                        c.ROOT / 'analysis/swebench-comparison-v2.0-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 2380)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.53369760')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.155904')

        # Envelope + reservation fits within $10.00 with >= 3% margin
        peak = Decimal(plan['total_envelope_usd']) + Decimal(plan['largest_request_reservation_usd'])
        cap = Decimal(self.config['cap_usd'])
        self.assertLessEqual(peak, cap)
        margin = (cap - peak) / cap
        self.assertGreaterEqual(margin, Decimal('0.03'))

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v2.0.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v2.0-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v2.0-authorization-template.json',
                        run_dir=Path(t).resolve() / 'not-started-v20')
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
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v2.0.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v2.0-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v2.0-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-v20-out')
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
        # 1. Pricing tables include new models
        self.assertIn('openai/gpt-6-sol-20260922', openrouter_chat.MODEL_PRICES)
        self.assertIn('openai/gpt-6-luna-20260922', openrouter_chat.MODEL_PRICES)
        self.assertEqual(openrouter_chat.MODEL_PRICES['openai/gpt-6-sol-20260922'],
                         (Decimal('2.00'), Decimal('0.20'), Decimal('10.00')))
        self.assertEqual(openrouter_chat.MODEL_PRICES['openai/gpt-6-luna-20260922'],
                         (Decimal('0.10'), Decimal('0.01'), Decimal('0.50')))

        # 2. V20OpenRouterChatModel body enforces reasoning effort 'none' and pops temperature
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


if __name__ == '__main__':
    unittest.main()
