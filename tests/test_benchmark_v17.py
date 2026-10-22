"""Prospective v1.7 freeze/parity and refusal gates for task sympy__sympy-20590."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError


class Version17Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.7.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.6.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration', 'selected_instance',
                                   'successor_budgets', 'experiment_manifest', 'experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.V17_SPEC_SHA)

        # Check successor_budgets request_input_tokens raised to 64000
        budget_changed = {k for k in self.config['successor_budgets'].keys() | self.prior['successor_budgets'].keys()
                          if self.config['successor_budgets'].get(k) != self.prior['successor_budgets'].get(k)}
        self.assertEqual(budget_changed, {'request_input_tokens'})
        self.assertEqual(self.config['successor_budgets']['request_input_tokens'], 64000)
        self.assertEqual(self.prior['successor_budgets']['request_input_tokens'], 32000)

        # Task changed to sympy__sympy-20590
        self.assertEqual(self.config['selected_instance'], 'sympy__sympy-20590')
        self.assertEqual(self.prior['selected_instance'], 'pydata__xarray-6721')

        # Models, tool bounding and predecessor identical
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertEqual(self.config['predecessor_budgets'], self.prior['predecessor_budgets'])
        self.assertFalse(self.config['live_execution_authorized'])

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 81)
        self.assertIn('runs/swebench-integration/preselection/sympy__sympy-20590-task.json', manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v1.7.json',
                                        c.ROOT / 'analysis/swebench-comparison-v1.7-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 2279)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.42721920')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.1516032')

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.7.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.7-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.7-authorization-template.json',
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
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.7.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.7-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.7-authorization-template.json',
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
