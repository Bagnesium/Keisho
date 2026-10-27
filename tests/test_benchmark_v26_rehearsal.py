"""Actual public subprocess, Docker tools, and five independent synthetic branches under v2.6.

Exercises the complete prospective v2.6 pipeline through scripts/benchmark_compare.py:
- Predecessor reaching frozen checkpoint on sympy__sympy-20590
- Actual handoff-generation, schema validation, token bounds (<=2048), provenance checks
- All five successors from checkpoint in frozen branch order
- Prediction artifacts, accounting, and final output generation
- Actual pinned official SWE-bench evaluator running in Docker on all five branch outputs
- Zero real provider requests and zero provider charges
"""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from keisho.benchmark.comparison import ROOT
from keisho.logging.raw import RawRun


class PublicV26FiveWayRehearsalTests(unittest.TestCase):
    def test_real_public_five_way_v26_rehearsal(self):
        output = ROOT / 'runs' / ('offline-rehearsal-v26-' + uuid.uuid4().hex[:12])
        command = [sys.executable, str(ROOT / 'tests/run_offline_rehearsal_v26.py'), '--output', str(output)]
        # Allow sufficient time for 6 Docker SWE-bench evaluations (~30s each)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + '\n' + result.stderr)

        run = output / 'runs' / output.name
        summary = json.loads((run / 'result.json').read_text())
        self.assertTrue(summary['synthetic_engineering_check'])
        self.assertEqual(summary['actual_provider_cost_usd'], '0')
        self.assertEqual(summary['predecessor']['reason'], 'checkpoint')

        predecessor = run / 'predecessor'
        checkpoint = json.loads((predecessor / 'checkpoint.json').read_text())
        self.assertTrue(checkpoint['eligible'])
        self.assertEqual(checkpoint['exit_code'], 0)

        handoffs = json.loads((predecessor / 'handoffs.json').read_text())
        self.assertEqual(handoffs['official_classification'], 'withheld')
        for condition in ('SUMMARY_2K', 'STRUCTURED_NOTES_2K', 'KEISHO_2K'):
            self.assertLessEqual(handoffs['tokens'][condition], 2048)

        frozen_pred = RawRun.open_existing(run, 'predecessor').load_frozen()
        self.assertEqual(handoffs['source_trajectory_sha256'], frozen_pred.sha256)

        # Verify note generation calls
        notes = run / 'note-generation'
        self.assertTrue((notes / 'summary-call.json').exists())
        self.assertTrue((notes / 'structured-call.json').exists())
        self.assertTrue((notes / 'structured-stripped-framing.json').exists())

        # Verify checkpoint official evaluation
        self.assertEqual(summary['checkpoint_classification']['status'], 'unresolved')
        self.assertEqual(summary['checkpoint_classification']['exit_code'], 0)

        expected_order = [
            'FULL_HISTORY',
            'SUMMARY_2K',
            'REPOSITORY_ONLY',
            'KEISHO_2K',
            'STRUCTURED_NOTES_2K'
        ]
        self.assertEqual(set(summary['conditions'].keys()), set(expected_order))
        # Verify chronological execution order matches plan branch order exactly
        ordered_by_time = sorted(
            summary['conditions'].keys(),
            key=lambda c: summary['conditions'][c]['official_evaluation']['started_at']
        )
        self.assertEqual(ordered_by_time, expected_order)

        for condition in expected_order:
            row = summary['conditions'][condition]
            branch = run / condition
            self.assertTrue(branch.is_dir())

            data = json.loads((branch / 'input.json').read_text())
            self.assertEqual(data['image_id'], checkpoint['image_id'])
            expected_handoff = handoffs['texts'][condition] or "No handoff context is provided for this run. The repository is available at /testbed; begin work on the issue above using the tools."
            self.assertEqual(data['handoff'], expected_handoff)

            pred_f = branch / 'prediction.json'
            self.assertTrue(pred_f.exists())
            patch_data = json.loads(pred_f.read_text())
            self.assertEqual(patch_data['instance_id'], 'sympy__sympy-20590')

            eval_res = row['official_evaluation']
            self.assertEqual(eval_res['exit_code'], 0)
            self.assertIn(eval_res['status'], ('resolved', 'unresolved'))

            if condition == 'KEISHO_2K':
                self.assertEqual(row['official_status'], 'resolved')
            else:
                self.assertEqual(row['official_status'], 'unresolved')

            measurements = json.loads((branch / 'response-measurements.json').read_text())
            self.assertEqual(measurements['actual_responses_received'], row['model_calls'])

        # Verify financial ledger
        ledger = json.loads((run / 'spending.json').read_text())
        self.assertEqual(ledger['actual_provider_cost_usd'], '0')
        self.assertTrue(ledger['stopped'])
        self.assertEqual(Decimal(ledger['unreconciled_reservations_usd']), 0)


if __name__ == '__main__':
    unittest.main()
