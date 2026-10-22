"""Prospective v1.9 freeze, benchmark-agent/5.0 workflow guidance, and parity gates."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError

WORKFLOW_BLOCK_VERBATIM = (
    "Workflow: 1. Read the issue and locate the relevant code with targeted shell searches (grep, head) "
    "instead of reading whole modules. 2. Reproduce the problem with a short script or an existing test when practical. "
    "3. Make the smallest edit that fixes it; make your first edit by turn 12. 4. Run the relevant public tests. "
    "5. When tests pass, call finish with a short summary. Do not spend more than a third of your budget exploring."
)


class Version19Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.9.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.8.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration',
                                   'agent_prompt_version', 'agent_prompt_sha256',
                                   'experiment_manifest', 'experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.V19_SPEC_SHA)
        self.assertEqual(self.config['agent_prompt_version'], 'benchmark-agent/5.0')
        self.assertEqual(self.config['agent_prompt_sha256'], digest(c.SYSTEM_V5))

        # Invariant limits, models, and task
        self.assertEqual(self.config['successor_budgets'], self.prior['successor_budgets'])
        self.assertEqual(self.config['predecessor_budgets'], self.prior['predecessor_budgets'])
        self.assertEqual(self.config['selected_instance'], 'sympy__sympy-20590')
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertFalse(self.config['live_execution_authorized'])

    def test_workflow_block_present_in_all_conditions_and_rest_byte_identical_to_system_v4(self):
        # 1. Verbatim text presence in c.SYSTEM_V5
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, c.SYSTEM_V5)
        self.assertEqual(c.WORKFLOW_GUIDANCE.strip(), WORKFLOW_BLOCK_VERBATIM)

        # 2. Everything else is byte-identical to SYSTEM_V4
        stripped_v5 = c.SYSTEM_V5.replace(c.WORKFLOW_GUIDANCE, '')
        self.assertEqual(stripped_v5, c.SYSTEM_V4)

        # 3. Check predecessor and all 5 successor conditions receive the prompt identically
        system, policy, _ = c.response_settings(self.config)
        self.assertEqual(system, c.SYSTEM_V5)
        self.assertEqual(policy, 'auxiliary-claims/2.0')
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, system)

        takeover = json.loads(c.PROMPTS.read_text())['takeover']
        successor_system = system + takeover
        self.assertIn(WORKFLOW_BLOCK_VERBATIM, successor_system)

        # Verify across all 5 conditions in config
        for condition in self.config['conditions']:
            with self.subTest(condition=condition):
                self.assertIn(WORKFLOW_BLOCK_VERBATIM, successor_system)
                self.assertEqual(successor_system.replace(c.WORKFLOW_GUIDANCE, ''),
                                 c.SYSTEM_V4 + takeover)

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 81)
        self.assertIn('runs/swebench-integration/preselection/sympy__sympy-20590-task.json', manifest['files'])
        self.assertIn('src/keisho/benchmark/bounded_output.py', manifest['files'])
        self.assertIn('src/keisho/pilot/agent.py', manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v1.9.json',
                                        c.ROOT / 'analysis/swebench-comparison-v1.9-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 2380)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.42721920')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.1516032')

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.9.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.9-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.9-authorization-template.json',
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
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.9.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.9-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.9-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-out')
            out = c.dry_run(**args)
            self.assertTrue(out['dry_run'])
            self.assertEqual(out['tool_output_policy'], 'bounded-output/1.0')
            self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 400000)
            self.assertEqual(self.config['successor_budgets']['request_input_tokens'], 64000)
            self.assertEqual(out['cost_envelope_usd'], '9.42721920')
            self.assertFalse(out['guard_created'])


if __name__ == '__main__':
    unittest.main()
