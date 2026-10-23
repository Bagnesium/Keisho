"""Regression for the v2.2 launch NameError (claim_launch deleted in 94b4fe2).

Offline only: no network, no provider, no Docker. Drives execute() through the
real claim_launch with temp guard/run dirs and stops at the first post-claim step.
"""
import ast
import builtins
import importlib
import inspect
import json
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from keisho.benchmark import comparison as c

CONFIG = c.ROOT / 'configs/swebench-comparison-v2.2.json'


class Stop(Exception):
    pass


class V22LivePathOffline(unittest.TestCase):
    def test_every_name_called_in_execute_is_defined(self):
        tree = ast.parse(textwrap.dedent(inspect.getsource(c.execute)))
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        local = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        local |= {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}
        local |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        local |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and n.name}
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    local.add((a.asname or a.name).split('.')[0])
                if isinstance(n, ast.ImportFrom):  # local imports must resolve too
                    mod = importlib.import_module(('.' * n.level) + (n.module or ''), 'keisho.benchmark')
                    for a in n.names:
                        self.assertTrue(hasattr(mod, a.name), 'unresolvable local import %s' % a.name)
        missing = sorted(n for n in (called | loaded) - local if not hasattr(c, n) and not hasattr(builtins, n))
        self.assertEqual(missing, [], 'undefined names in execute(): %s' % missing)
        self.assertTrue(callable(c.claim_launch))

    def test_claim_launch_matches_main_semantics(self):
        src = inspect.getsource(c.claim_launch)
        for s in ('safe_destination(binding.run_dir)', "claim.write_artifact('claim.json', binding.record())", 'claim.freeze()'):
            self.assertIn(s, src)

    def test_live_path_claims_once_then_refuses_second_launch(self):
        config = json.loads(CONFIG.read_text())
        with tempfile.TemporaryDirectory() as t:
            t = Path(t).resolve()
            plan = t / 'plan.json'
            plan.write_text(json.dumps({'branch_order': ['REPOSITORY_ONLY']}))
            (t / 'guards').mkdir()
            binding = c.LaunchBinding(config_path=CONFIG, plan_path=plan, authorization_path=t / 'auth.json',
                                      run_dir=t / 'run-001', authorization_guard=t / 'guards' / 'authorized-test',
                                      config=config, task={'instance_id': 'x'}, plan={'branch_order': ['REPOSITORY_ONLY']},
                                      authorization={'cap_usd': '10.00', 'authorization_id': 'test'})
            net = AssertionError('network/provider must not be used')
            with patch.object(c, 'resolve_binding', return_value=binding), \
                 patch.object(c, 'runtime_preflight', return_value={'provider': None, 'ca': None, 'native': None}), \
                 patch.object(c, 'check_public_catalog', return_value={}), \
                 patch.object(c, 'http_transport', side_effect=net), \
                 patch.object(c, 'Recorder', side_effect=Stop):
                with self.assertRaises(Stop):
                    c.execute(approve_live=True, config_path=CONFIG, plan_path=plan, run_dir=binding.run_dir,
                              authorization_path=binding.authorization_path)
                self.assertTrue((binding.authorization_guard / 'claim.json').is_file())
                with self.assertRaisesRegex(c.ValidationError if hasattr(c, 'ValidationError') else Exception, 'already claimed'):
                    c.execute(approve_live=True, config_path=CONFIG, plan_path=plan, run_dir=t / 'run-002',
                              authorization_path=binding.authorization_path)


if __name__ == '__main__':
    unittest.main()
