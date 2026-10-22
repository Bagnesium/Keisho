"""Prospective v1.5 freeze/parity and refusal gates; no comparison is launched."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.benchmark.bounded_output import (BoundedRepositorySession, VERSION as BOUNDED_VERSION,
                                            MAX_BOUNDED_OUTPUT_BYTES, MAX_BOUNDED_CHANGED_PATHS)
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError
from keisho.pilot.tools import InvalidAction


class Version15Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.5.json')
        self.prior = c.read_input(c.ROOT / 'configs/swebench-comparison-v1.4.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration', 'predecessor_model',
                                   'execution_contract_version', 'tool_output_policy',
                                   'experiment_manifest', 'experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.V15_SPEC_SHA)
        self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['successor_model'], 'openai/gpt-4.1-2025-04-14')
        self.assertEqual(self.config['tool_output_policy'], 'bounded-output/1.0')
        self.assertEqual(self.config['execution_contract_version'], 'agent-runtime/3.3')
        self.assertFalse(self.config['live_execution_authorized'])

    def test_bounded_output_truncation_and_inventory_bounding(self):
        session = BoundedRepositorySession.__new__(BoundedRepositorySession)
        session.name = 'test-container'
        session.listing_policy = 'bounded-listing/1.0'
        session.tool_output_policy = BOUNDED_VERSION
        session.output_bytes = 49152
        session.actions = 0
        session.audit = None
        session.base_inventory = {}

        # 1. Test shell command stdout truncation
        session.validate_action = lambda action: None
        session.inventory = lambda: {}
        huge_stdout = b"A" * 10000
        mock_r = unittest.mock.Mock(returncode=0, stdout=huge_stdout, stderr=b"")
        session.command = lambda cmd: mock_r
        with patch('keisho.benchmark.bounded_output.docker') as mock_docker:
            mock_docker.return_value.stdout = b"PID COMMAND\n123 /bin/sleep infinity\n"
            result = session.execute({'tool': 'shell', 'command': 'echo big'})
            self.assertTrue(result['truncated'])
            self.assertEqual(result['total_output_bytes'], 10000)
            self.assertIn('[... tool output truncated 1808 bytes ...]', result['output'])
            self.assertLessEqual(len(result['output'].encode('utf-8')), MAX_BOUNDED_OUTPUT_BYTES + 100)

        # 2. Test bulk changed files bounding (> 25 files)
        normal_stdout = b"done"
        session.command = lambda cmd: unittest.mock.Mock(returncode=0, stdout=normal_stdout, stderr=b"")
        # Generate 100 changed files (before is empty, after has 100 files)
        after_inv = {f"chunk_{i:03d}.zarr": {"sha256": f"hash_{i}"} for i in range(100)}
        inv_sequence = iter([{}, after_inv])
        session.inventory = lambda: next(inv_sequence)
        with patch('keisho.benchmark.bounded_output.docker') as mock_docker:
            mock_docker.return_value.stdout = b"PID COMMAND\n123 /bin/sleep infinity\n"
            result = session.execute({'tool': 'shell', 'command': 'create_chunks'})
            self.assertTrue(result['inventory_truncated'])
            self.assertEqual(result['omitted_changed_paths_count'], 75)
            self.assertEqual(len(result['changed_paths']), 25)
            self.assertEqual(len(result['source_hashes_after']), 25)
            self.assertLessEqual(len(json.dumps(result).encode()), 12288)

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.5.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.5-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.5-authorization-template.json',
                        run_dir=Path(t).resolve() / 'not-started')
            binding = c.resolve_binding(**args, allow_pending=True)
            self.assertFalse(binding.authorization['provider_inference_authorized'])
            self.assertFalse(binding.authorization_guard.exists())
            with patch.object(c, 'runtime_preflight', side_effect=AssertionError('preflight must not run')):
                with self.assertRaisesRegex(ValidationError, 'not authorized'):
                    c.execute(approve_live=True, **args)
            self.assertFalse(args['run_dir'].exists())
            self.assertFalse(binding.authorization_guard.exists())

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 81)
        self.assertIn('src/keisho/benchmark/bounded_output.py', manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT / 'configs/swebench-comparison-v1.5.json',
                                        c.ROOT / 'analysis/swebench-comparison-v1.5-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 4782)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY',
                                                'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertTrue(plan['plausibly_fits'])
        self.assertEqual(plan['total_envelope_usd'], '8.93833920')

    def test_dry_run_passes_and_reflects_bounded_policy(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT / 'configs/swebench-comparison-v1.5.json',
                        plan_path=c.ROOT / 'analysis/swebench-comparison-v1.5-plan.json',
                        authorization_path=c.ROOT / 'analysis/swebench-comparison-v1.5-authorization-template.json',
                        run_dir=Path(t).resolve() / 'dry-run-out')
            out = c.dry_run(**args)
            self.assertTrue(out['dry_run'])
            self.assertEqual(out['tool_output_policy'], 'bounded-output/1.0')
            self.assertEqual(self.config['predecessor_model'], 'openai/gpt-4.1-2025-04-14')
            self.assertEqual(out['cost_envelope_usd'], '8.93833920')
            self.assertFalse(out['guard_created'])


if __name__ == '__main__':
    unittest.main()
