"""v2.3 proposal: non-empty no-handoff turn, premature-finish guard, pre-registered predecessor attempts. Offline only."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from keisho.agents.base import ModelResponse, TokenCount, Usage
from keisho.benchmark import comparison as c
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import AUXILIARY

DATA = Path(__file__).parent / 'data/swebench-v2.2-premature-finish/provenance.json'
V22 = json.loads((c.ROOT / 'configs/swebench-comparison-v2.2.json').read_text())
V23 = json.loads((c.ROOT / 'configs/swebench-comparison-v2.3.json').read_text())
REPLAY = json.loads(DATA.read_text())['text']


class ReplayModel:
    def __init__(self, texts):
        self.texts, self.requests = list(texts), []
    def model_id(self): return 'openai/gpt-6-sol-20260922'
    def count_tokens(self, text): return TokenCount(len(text), 'test-char-upper-bound', True)  # offline stand-in
    def generate(self, req):
        self.requests.append(req)
        return ModelResponse('openai/gpt-6-sol-20260922', self.texts.pop(0), Usage(1322, 31, 0, '0.0036115', 'replay'), 'stop')


class Session:
    def validate_action(self, action): return True
    def execute(self, action): return {'output': 'ok', 'exit_code': 0}


def replay(texts, handoff):
    model = ReplayModel(texts)
    with tempfile.TemporaryDirectory() as t:
        raw = RawRun(Path(t), 'predecessor')
        ex = run_agent(model, Session(), Recorder(raw), 'issue text', c.SYSTEM_V5, handoff, V23['branch_seed'],
                       Budgets(4, 4, 2048, 100000, 64000, 128000), role='predecessor',
                       response_policy=AUXILIARY, action_wire_version='flat-or-args/1.0')
        return model, c.execution_result(ex)


class V23PrematureFinish(unittest.TestCase):
    def test_config_proposal_flags(self):
        self.assertEqual(V23['version'], c.V23_VERSION)
        self.assertFalse(V23['live_execution_authorized'])
        self.assertEqual(V23['automatic_retries'], 0)
        self.assertTrue(V23['empty_handoff_user_text'].strip())
        self.assertEqual(c.predecessor_attempt_limit(V23), 3)
        self.assertEqual(c.predecessor_attempt_limit(V22), 1)

    def test_replay_v22_finish_is_premature_and_admits_one_new_attempt(self):
        model, info = replay([REPLAY], V23['empty_handoff_user_text'])
        self.assertEqual((info['reason'], info['tool_calls'], info['model_calls']), ('finished', 0, 1))
        g = c.classify_premature_finish(V23, info)
        self.assertEqual(g['guard'], 'premature-finish-guard/1.0')
        self.assertTrue(g['counts_as_invalid_attempt'])
        self.assertFalse(g['automatic_retry'])
        self.assertFalse(g['handoff_built'])
        # v2.2 and earlier: unchanged behaviour, no guard
        self.assertIsNone(c.classify_premature_finish(V22, info))

    def test_no_empty_user_message_under_v23(self):
        model, _ = replay([REPLAY], V23['empty_handoff_user_text'])
        roles = [(m.role, m.content) for m in model.requests[0].messages]
        self.assertEqual([r for r, _ in roles], ['system', 'user', 'user'])
        self.assertTrue(all(content.strip() for _, content in roles))
        self.assertEqual(roles[2][1], V23['empty_handoff_user_text'])
        model, _ = replay([REPLAY], '')  # legacy v2.2 framing: recorded empty trailing user turn
        self.assertEqual(model.requests[0].messages[2].content, '')

    def test_finish_after_tool_is_not_premature(self):
        tool = json.dumps({'action': {'tool': 'list_files'}, 'claims': []})
        _, info = replay([tool, REPLAY], V23['empty_handoff_user_text'])
        self.assertEqual((info['reason'], info['tool_calls']), ('finished', 1))
        self.assertIsNone(c.classify_premature_finish(V23, info))

    def test_zero_tool_finish_after_rejected_action_ends_run(self):
        bad = json.dumps({'action': {'tool': 'unknown'}, 'claims': []})
        info = {'reason': 'finished', 'tool_calls': 0, 'model_calls': 2}
        g = c.classify_premature_finish(V23, info)
        self.assertFalse(g['counts_as_invalid_attempt'])

    def test_attempt_limit_bounds(self):
        for bad in (0, 4, '3', None):
            with self.assertRaises(Exception):
                c.predecessor_attempt_limit(dict(V23, predecessor_attempts={'max_attempts': bad}))

    def test_envelope_fits_cap_with_reservation(self):
        from decimal import Decimal as D
        plan = json.loads((c.ROOT / 'analysis/swebench-comparison-v2.3-plan.json').read_text())
        parts = plan['maximum_noncached_costs_usd']
        self.assertEqual(sum(D(v) for v in parts.values()), D(plan['total_envelope_usd']))
        self.assertLessEqual(D(plan['total_envelope_usd']) + D(plan['largest_request_reservation_usd']), D(V23['cap_usd']))
        self.assertEqual(plan['config_sha256'], c.digest(V23))
        self.assertEqual(c.V23_SPEC_SHA, c.digest(V23))
        self.assertEqual(c.V23_PLAN_SHA, c.digest(plan))


class V23AttemptLoop(unittest.TestCase):
    """Drives execute() predecessor stage with fakes; no Docker, network or provider."""

    def run_execute(self, reasons):
        from types import SimpleNamespace
        seq = list(reasons)
        calls = []
        def fake_run_agent(*a, **k):
            calls.append(a[5])  # handoff/no-handoff text actually sent
            reason, tools, n = seq.pop(0)
            return SimpleNamespace(reason=reason, model_calls=n, tool_calls=tools, calls=[], elapsed_seconds=0.1)
        class FakeSession:
            def initialize_base(self, commit): return {}
            def patch(self, commit): return ''
            def close(self): pass
            def validate_action(self, action): return True
            def __getattr__(self, name): return MagicMock()
        with tempfile.TemporaryDirectory() as t:
            t = Path(t).resolve()
            (t / 'guards').mkdir(); (t / 'private').mkdir()
            ds = t / 'private' / 'x-selected-task-evaluator.jsonl'; ds.write_text('{}')
            import hashlib
            plan = t / 'plan.json'; plan.write_text(json.dumps({'branch_order': V23['conditions']}))
            binding = c.LaunchBinding(config_path=t / 'cfg.json', plan_path=plan, authorization_path=t / 'auth.json',
                                      run_dir=t / 'run-001', authorization_guard=t / 'guards' / 'authorized-test',
                                      config=V23, task={'instance_id': 'x', 'base_commit': 'abc', 'problem_statement': 'issue'},
                                      plan={'branch_order': V23['conditions'], 'total_envelope_usd': '1'},
                                      authorization={'cap_usd': '10.00', 'authorization_id': 'test'})
            meta = {'instance_id': 'x', 'environment_verified': True, 'image_id': 'img',
                    'evaluator_dataset_sha256': hashlib.sha256(b'{}').hexdigest()}
            prov = {'models': {r: {'accepted_response_model_ids': ['m']} for r in ('predecessor', 'successor', 'generation')}}
            ctx = {'provider': prov, 'ca': None, 'native': None, 'image_metadata': meta, 'credential_presence': {}, 'setup': {}}
            with patch.object(c, 'resolve_binding', return_value=binding), \
                 patch.object(c, 'runtime_preflight', return_value=ctx), \
                 patch.object(c, 'check_public_catalog', return_value={}), \
                 patch.object(c, 'PRIVATE', t / 'private'), \
                 patch.object(c, 'docker', return_value=SimpleNamespace(stdout=json.dumps([{'Id': 'img'}]))), \
                 patch.object(c, 'run_agent', side_effect=fake_run_agent), \
                 patch.object(c, 'V20OpenRouterChatModel', MagicMock()), patch.object(c, 'BudgetedModel', MagicMock()), \
                 patch('keisho.benchmark.bounded_output.BoundedRepositorySession', return_value=FakeSession()), \
                 patch.object(c, 'RepositorySession', return_value=FakeSession(), create=True), \
                 patch('keisho.benchmark.response_measurements.measure_run', return_value={}):
                try:
                    c.execute(approve_live=True, config_path=binding.config_path, plan_path=plan, run_dir=binding.run_dir,
                              authorization_path=binding.authorization_path)
                except Exception as exc:  # report setup gaps clearly
                    raise AssertionError('execute raised %r' % exc)
            run = binding.run_dir
            result = json.loads((run / 'result.json').read_text())
            dirs = sorted(p.name for p in run.iterdir() if p.is_dir() and p.name.startswith('predecessor'))
            guards = {d: json.loads((run / d / 'premature-finish.json').read_text()) for d in dirs if (run / d / 'premature-finish.json').exists()}
            return result, dirs, guards, calls

    def test_three_premature_finishes_stop_after_limit(self):
        result, dirs, guards, sent = self.run_execute([('finished', 0, 1)] * 3)
        self.assertEqual(result['status'], 'predecessor_premature_finish')
        self.assertEqual(dirs, ['predecessor', 'predecessor-attempt-02', 'predecessor-attempt-03'])
        self.assertEqual([guards[d]['new_attempt'] for d in dirs], [True, True, False])
        self.assertTrue(all(s == V23['empty_handoff_user_text'] for s in sent))
        self.assertTrue(all(v['status'] == 'unstarted' for v in result['conditions'].values()))

    def test_premature_then_ordinary_terminal_stops_without_more_attempts(self):
        result, dirs, guards, _ = self.run_execute([('finished', 0, 1), ('budget_exhausted', 5, 9)])
        self.assertEqual(result['status'], 'checkpoint_not_reached')
        self.assertEqual(dirs, ['predecessor', 'predecessor-attempt-02'])
        self.assertEqual(list(guards), ['predecessor'])

    def test_zero_tool_finish_after_rejections_ends_without_new_attempt(self):
        result, dirs, guards, _ = self.run_execute([('finished', 0, 2)])
        self.assertEqual(result['status'], 'predecessor_premature_finish')
        self.assertEqual(dirs, ['predecessor'])
        self.assertFalse(guards['predecessor']['new_attempt'])


if __name__ == '__main__':
    unittest.main()


class V23CacheWriteLedger(unittest.TestCase):
    def test_reserves_input_at_cache_write_rate(self):
        cfg = json.loads((c.ROOT / 'configs/swebench-comparison-v2.3.json').read_text())
        led = c.make_ledger(cfg, cfg['cap_usd'], provider='openrouter', authorized_ceiling_usd='10.00', authorization_scope='swebench-one-comparison')
        self.assertIsInstance(led, c.CacheWriteReservingLedger)
        rec = led.reserve('predecessor', cfg['predecessor_model'], 64000, 2048, 1000)
        from decimal import Decimal
        self.assertEqual(Decimal(rec['reservation_usd']), Decimal('1.05') * (64000 * Decimal('2.5') + 2048 * Decimal('10')) / 1000000)
        self.assertEqual(rec['reservation_pricing'], 'cache-write-input')
        self.assertEqual(led.prices[cfg['predecessor_model']][0], Decimal('2.0'))  # catalog prompt rate restored

    def test_v22_keeps_plain_ledger(self):
        cfg = json.loads((c.ROOT / 'configs/swebench-comparison-v2.2.json').read_text())
        self.assertIs(type(c.make_ledger(cfg, cfg['cap_usd'], provider='openrouter', authorized_ceiling_usd='10.00', authorization_scope='swebench-one-comparison')), c.SpendLedger)


class ExecuteNamesDefined(unittest.TestCase):
    def test_every_name_in_execute_is_defined(self):
        import ast, builtins, inspect, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(c.execute)))
        local = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.Lambda)):
                a = n.args
                local |= {x.arg for x in a.args + a.kwonlyargs + a.posonlyargs + ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else [])}
                if isinstance(n, ast.FunctionDef): local.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): local.add(n.id)
            elif isinstance(n, ast.ExceptHandler) and n.name: local.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)): local |= {(x.asname or x.name).split('.')[0] for x in n.names}
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        missing = sorted(u for u in used if u not in local and not hasattr(c, u) and not hasattr(builtins, u))
        self.assertEqual(missing, [])


class V23RateLookup(unittest.TestCase):
    def test_catalog_alias_and_dated_ids_resolve(self):
        from decimal import Decimal
        cfg = json.loads((c.ROOT / 'configs/swebench-comparison-v2.3.json').read_text())
        self.assertEqual(c.reservation_input_rate(cfg, 'openai/gpt-6-sol', 'openai/gpt-6-sol'), Decimal('2.5'))
        self.assertEqual(c.reservation_input_rate(cfg, 'openai/gpt-6-luna'), Decimal('0.125'))
        self.assertEqual(c.reservation_input_rate(cfg, 'openai/gpt-6-sol-20260922'), Decimal('2.5'))
        with self.assertRaises(Exception):
            c.reservation_input_rate(cfg, 'openai/gpt-4.1')
