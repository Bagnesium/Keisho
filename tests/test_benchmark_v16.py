"""Prospective v1.6 freeze/parity and refusal gates; no comparison is launched."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError


class Version16Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.6.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.5.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration', 'predecessor_budgets',
                                   'experiment_manifest', 'experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.V16_SPEC_SHA)

        # Check that ONLY total_tokens and request_input_tokens changed within predecessor_budgets
        budget_changed = {k for k in self.config['predecessor_budgets'].keys() | self.prior['predecessor_budgets'].keys()
                          if self.config['predecessor_budgets'].get(k) != self.prior['predecessor_budgets'].get(k)}
        self.assertEqual(budget_changed, {'total_tokens', 'request_input_tokens'})
        self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 400000)
        self.assertEqual(self.prior['predecessor_budgets']['total_tokens'], 180000)
        self.assertEqual(self.config['predecessor_budgets']['request_input_tokens'], 64000)
        self.assertEqual(self.prior['predecessor_budgets']['request_input_tokens'], 32000)

        # Invariant limits
        self.assertEqual(self.config['predecessor_budgets']['model_calls'], 48)
        self.assertEqual(self.config['predecessor_budgets']['tool_calls'], 36)
        self.assertEqual(self.config['predecessor_budgets']['context_tokens'], 128000)
        self.assertEqual(self.config['predecessor_budgets']['output_tokens'], 2048)

        # Models, tool bounding and successors identical
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertEqual(self.config['successor_budgets'], self.prior['successor_budgets'])
        self.assertFalse(self.config['live_execution_authorized'])

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 81)
        self.assertIn('src/keisho/benchmark/bounded_output.py', manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v1.6.json',
                                        c.ROOT / 'analysis/swebench-comparison-v1.6-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 4782)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '9.40033920')
        self.assertEqual(plan['largest_request_reservation_usd'], '0.1516032')

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.6.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.6-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.6-authorization-template.json',
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
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.6.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.6-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.6-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-out')
            out = c.dry_run(**args)
            self.assertTrue(out['dry_run'])
            self.assertEqual(out['tool_output_policy'], 'bounded-output/1.0')
            self.assertEqual(self.config['predecessor_budgets']['total_tokens'], 400000)
            self.assertEqual(self.config['predecessor_budgets']['request_input_tokens'], 64000)
            self.assertEqual(out['cost_envelope_usd'], '9.40033920')
            self.assertFalse(out['guard_created'])


if __name__ == '__main__':
    unittest.main()
