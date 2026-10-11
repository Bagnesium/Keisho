"""Public CLI/binding/atomic guard contracts, with no live transports."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from keisho.benchmark import comparison as c
from keisho.core import ValidationError

CONFIG = c.ROOT / 'configs/swebench-comparison-v1.1.json'
PLAN = c.ROOT / 'runs/swebench-integration/response-policy-repair/prospective-plan-check.json'
AUTH = c.ROOT / 'runs/swebench-integration/exploratory-v1.1-preflight/authorization.json'


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.config = self.root / 'nondefault-config.json'; self.config.write_bytes(CONFIG.read_bytes())
        self.plan = self.root / 'nondefault-plan.json'; self.plan.write_bytes(PLAN.read_bytes())
        self.output = self.root / ('nondefault-run-' + uuid.uuid4().hex[:12])
        self.protected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for directory in
                          [c.RUNROOT, AUTH.parent] for p in directory.rglob('*') if p.is_file()}
        self.protected[CONFIG] = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        self.real_guard = c.RUNROOT.parent / ('authorized-' + c.AUTH_SHA[:24])
        self.guard_existed = self.real_guard.exists()
    def tearDown(self):
        for p, sha in self.protected.items(): self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), sha, p)
        self.assertEqual(self.real_guard.exists(), self.guard_existed)
        owned_predictions = c.PRIVATE / 'predictions' / self.output.name
        if owned_predictions.exists(): shutil.rmtree(owned_predictions)
        self.tmp.cleanup()
    def binding(self, **kwargs):
        return c.resolve_binding(kwargs.get('config', self.config), kwargs.get('plan', self.plan),
                                 kwargs.get('output', self.output), kwargs.get('auth', AUTH))
    def args(self):
        return ['--config', str(self.config), '--plan', str(self.plan), '--run-dir', str(self.output), '--authorization', str(AUTH)]
    def cli(self, *extra, injected=False, mode='dry'):
        script = c.ROOT / ('tests/benchmark_cli_fixture.py' if injected else 'scripts/benchmark_compare.py')
        command = [sys.executable, str(script)]
        if injected: command += [mode, str(self.root)]
        return subprocess.run([*command, *self.args(), *extra], cwd=c.ROOT,
                              env={'PATH': '/usr/bin:/bin:/usr/local/bin', 'PYTHONPATH': str(c.ROOT / 'src')}, capture_output=True, text=True)

    def test_explicit_nondefault_selection_and_no_guard(self):
        b = self.binding()
        self.assertEqual(b.config_path, self.config)
        self.assertEqual(c.response_settings(b.config)[1], 'auxiliary-claims/2.0')
        self.assertEqual(b.plan['branch_order'], ['FULL_HISTORY', 'SUMMARY_2K', 'REPOSITORY_ONLY', 'KEISHO_2K', 'STRUCTURED_NOTES_2K'])
        self.assertFalse(self.output.exists())

    def test_mismatched_config_or_plan_before_provider(self):
        for field in ('config', 'plan'):
            path = getattr(self, field); old = path.read_bytes()
            data = json.loads(old); data['config_sha256' if field == 'plan' else 'successor_budgets'] = 'changed'
            path.write_text(json.dumps(data))
            with patch.object(c, 'runtime_preflight', side_effect=AssertionError('must reject before provider/environment')):
                with self.assertRaises(ValidationError): self.binding()
            path.write_bytes(old)

    def test_scientific_change_cannot_be_hidden_by_rehash(self):
        from keisho.core import digest
        data = json.loads(self.config.read_text()); data['successor_model'] = 'different-model'
        self.config.write_text(json.dumps(data))
        plan = json.loads(self.plan.read_text()); plan['config_sha256'] = digest(data); self.plan.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValidationError, 'frozen supported specification'): self.binding()

    def test_missing_counterparts_and_approval_cli(self):
        r = subprocess.run([sys.executable, str(c.ROOT/'scripts/benchmark_compare.py'), '--config', str(self.config), '--approve-live'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0); self.assertIn('--plan', r.stderr)
        r = self.cli()
        self.assertEqual(r.returncode, 1); self.assertIn('explicit new live authorization required', r.stderr)
        self.assertFalse(self.output.exists())

    def test_occupied_historical_and_symlink_destinations_refused(self):
        self.output.mkdir()
        for output in (self.output, c.RUNROOT, c.RUNROOT / 'another-attempt'):
            with self.assertRaises(ValidationError): self.binding(output=output)
        link = self.root/'link'; link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValidationError): self.binding(output=link/'escape')

    def test_dry_run_actual_cli_consumes_no_live_guard_or_provider(self):
        r = self.cli('--dry-run', injected=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report['config_path'], str(self.config))
        self.assertEqual(report['run_dir'], str(self.output))
        self.assertEqual(report['response_policy'], 'auxiliary-claims/2.0')
        self.assertEqual(report['provider_requests'], 0)
        self.assertFalse(self.output.exists()); self.assertFalse((self.root/'test-authorization-claim').exists())

    def test_full_cli_downstream_binding_with_offline_provider_evaluator(self):
        r = self.cli('--approve-live', injected=True, mode='live')
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads((self.output/'result.json').read_text())
        self.assertEqual(result['status'], 'complete', json.dumps(result))
        self.assertEqual(result['predecessor']['reason'], 'checkpoint')
        self.assertEqual(json.loads((self.output/'binding.json').read_text())['config_path'], str(self.config))
        self.assertEqual(json.loads((self.output/'binding.json').read_text())['authorization_guard'],
                         str(self.root / 'test-authorization-claim'))
        self.assertTrue((self.output/'note-generation').is_dir())
        self.assertFalse((c.RUNROOT/'note-generation').exists())
        for condition in json.loads(CONFIG.read_text())['conditions']:
            self.assertTrue((self.output/condition/'prediction.json').is_file())
            data = json.loads((self.output/condition/'input.json').read_text())
            self.assertIn('Response contract benchmark-agent/2.0', data['system'])
            self.assertIn(self.output.name, result['conditions'][condition]['official_evaluation']['run_id'])
            response = json.loads((self.output/condition/'successor_call_001-response.json').read_text())
            self.assertEqual(json.loads(response['request_body_json'])['response_format']['type'], 'json_schema')
        ledger = json.loads((self.output/'spending.json').read_text())
        self.assertEqual(len(ledger['attempts']), 9)  # 2 predecessor + 2 generation + 5 successors
        self.assertEqual(json.loads((self.output/'authorization.json').read_text())['reference_sha256'], c.AUTH_SHA)

    def test_duplicate_and_concurrent_claim_across_output_names(self):
        b = replace(self.binding(), authorization_guard=self.root/'owned-test-claim')
        b2 = replace(b, run_dir=self.root/'second-output')
        def attempt(binding):
            try: return c.claim_launch(binding)
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [b, b2]))
        self.assertEqual(sum(r is not None for r in results), 1)
        with self.assertRaises(FileExistsError): c.claim_launch(replace(b, run_dir=self.root/'third-output'))
        self.assertFalse((self.root/'third-output').exists())


if __name__ == '__main__': unittest.main()
