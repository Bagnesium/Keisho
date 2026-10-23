"""Offline consistency checks for the v2.2 freeze (no network, no models, no launch)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.core import digest, ValidationError

L = lambda p: json.loads((c.ROOT / p).read_text())


class V22Freeze(unittest.TestCase):
    def setUp(self):
        self.cfg, self.prior = L('configs/swebench-comparison-v2.2.json'), L('configs/swebench-comparison-v2.1.json')
        self.plan, self.auth = L('analysis/swebench-comparison-v2.2-plan.json'), L('analysis/swebench-comparison-v2.2-authorization-template.json')
        self.freeze = L('analysis/swebench-v2.2-final-source-freeze.json')

    def test_only_registered_config_changes(self):
        changed = {k for k in self.cfg.keys() | self.prior.keys() if self.cfg.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version', 'supersedes_configuration', 'experiment_manifest', 'experiment_manifest_sha256', 'notes_reader_version'})
        self.assertFalse(self.cfg['live_execution_authorized'])

    def test_anchor_chain(self):
        self.assertEqual(digest(self.cfg), c.V22_SPEC_SHA)
        self.assertEqual(digest(self.plan), c.V22_PLAN_SHA)
        self.assertEqual(self.plan['config_sha256'], digest(self.cfg))
        self.assertEqual(self.cfg['experiment_manifest_sha256'], digest(L(self.cfg['experiment_manifest'])))
        self.assertEqual((self.auth['config_sha256'], self.auth['plan_sha256'], self.auth['final_source_freeze_sha256']),
                         (digest(self.cfg), digest(self.plan), digest(self.freeze)))
        self.assertFalse(self.auth['provider_inference_authorized'])
        self.assertEqual(self.plan['total_envelope_usd'], '9.53369760')

    def test_manifest_superset_of_v21_with_identical_hashes(self):
        a, b = L('analysis/swebench-experiment-v2.1-manifest.json')['files'], L('analysis/swebench-experiment-v2.2-manifest.json')['files']
        self.assertTrue(all(b[k] == v for k, v in a.items()))
        self.assertIn('src/keisho/benchmark/notes_reader.py', b)

    def test_final_source_freeze_pins_binding_modules(self):
        import hashlib
        pinned = self.freeze['files']['src/keisho/benchmark/comparison.py']
        if hashlib.sha256((c.ROOT / 'src/keisho/benchmark/comparison.py').read_bytes()).hexdigest() != pinned:
            # On v2.3+ branches comparison.py has moved on: the frozen v2.2 binding must refuse (fail closed).
            with self.assertRaisesRegex(ValidationError, 'pinned binding module changed'):
                c.validate_final_source_freeze(self.auth)
            return
        c.validate_final_source_freeze(self.auth)
        self.assertIn('src/keisho/benchmark/comparison.py', self.freeze['files'])
        with self.assertRaisesRegex(ValidationError, 'bind the final source freeze'):
            c.validate_final_source_freeze(dict(self.auth, final_source_freeze_sha256='0' * 64))
        with tempfile.TemporaryDirectory() as t:
            fake = Path(t).resolve() / 'f.json'
            fake.write_text(json.dumps(dict(self.freeze, files={'src/keisho/benchmark/comparison.py': '0' * 64})))
            with patch.object(c, 'V22_FINAL_SOURCE_FREEZE', str(fake)):
                with self.assertRaisesRegex(ValidationError, 'pinned binding module changed'):
                    c.validate_final_source_freeze(dict(self.auth, final_source_freeze_sha256=digest(json.loads(fake.read_text()))))

    def test_pending_template_never_executes(self):
        with patch.object(c, 'load_frozen_plan', return_value=(self.cfg, {'instance_id': 'sympy__sympy-20590'}, self.plan)), \
             patch.object(c, 'runtime_preflight', side_effect=AssertionError('no preflight')), tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValidationError, 'not authorized'):
                c.execute(approve_live=True, config_path=c.ROOT / 'configs/swebench-comparison-v2.2.json',
                          plan_path=c.ROOT / 'analysis/swebench-comparison-v2.2-plan.json', run_dir=Path(t) / 'x',
                          authorization_path=c.ROOT / 'analysis/swebench-comparison-v2.2-authorization-template.json')


if __name__ == '__main__':
    unittest.main()
