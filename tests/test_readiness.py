from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.base import Message, ModelRequest, ModelResponse, TokenCount, Usage
from keisho.agents.providers.openai_chat import OpenAIChatModel, ProviderFailure
from keisho.core import ValidationError
from keisho.pilot.calibration_block import execute_one, load_config, plan
from keisho.pilot.calibration_review import make_review
from keisho.pilot.cli import main, verify_sandbox
from keisho.pilot.offline import factory
from keisho.pilot.runner import run_block
from keisho.pilot.spending import BudgetedModel, SpendLedger
from keisho.pilot.state_builder import build_state
from keisho.pilot.tasks import REPO, load_gold
from keisho.pilot.token_audit import audit_saved_checkpoints
from keisho.logging.raw import RawRun


class Counter:
    def count(self, text):
        return TokenCount(len(text.split()), "unit-test-counter", True)


class SpendingTests(unittest.TestCase):
    def request(self):
        return ModelRequest((Message("user", "JSON please"),), 17, 2048, 0.0)

    def native(self, transport):
        return OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="fake-unit-key", transport=transport, tokenizer=Counter())

    def response(self, usage=None):
        return {"model": "gpt-4.1-mini-2025-04-14", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": usage or {"prompt_tokens": 100, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 20}}}

    def test_reservation_is_durable_before_transport_and_reconciles_without_cache_discounts(self):
        events = []
        ledger = SpendLedger("1.25", events.append)
        def transport(*_):
            self.assertEqual(events[-1]["status"], "reserved")
            self.assertEqual(ledger.held, Decimal("0.0160768"))
            return self.response(), "unit-request"
        model = BudgetedModel(self.native(transport), ledger, "predecessor", "gpt-4.1-mini-2025-04-14")
        model.generate(self.request())
        self.assertEqual(ledger.held, 0)
        self.assertEqual(ledger.accounted, Decimal("0.000056"))
        self.assertEqual(events[-1]["status"], "settled")
        self.assertEqual(events[-1]["returned_model_id"], "gpt-4.1-mini-2025-04-14")
        self.assertTrue(events[0]["request_sha256"])

    def test_insufficient_dollars_prevent_transport(self):
        attempts = []
        ledger = SpendLedger("0.001")
        model = BudgetedModel(self.native(lambda *_: attempts.append(True)), ledger, "predecessor", "gpt-4.1-mini-2025-04-14")
        with self.assertRaises(ProviderFailure):
            model.generate(self.request())
        self.assertEqual(attempts, [])
        self.assertTrue(ledger.stopped)
        self.assertEqual(ledger.accounted, 0)

    def test_unknown_usage_holds_reservation_and_blocks_next_request(self):
        attempts = []
        def transport(*_):
            attempts.append(True)
            return self.response({"prompt_tokens": None, "completion_tokens": None}), None
        ledger = SpendLedger("1.25")
        model = BudgetedModel(self.native(transport), ledger, "predecessor", "gpt-4.1-mini-2025-04-14")
        model.generate(self.request())
        self.assertTrue(ledger.stopped)
        self.assertEqual(ledger.held, Decimal("0.0160768"))
        self.assertIsNone(ledger.records[0]["provider_cost_usd"])
        with self.assertRaises(ProviderFailure):
            model.generate(self.request())
        self.assertEqual(len(attempts), 1)

    def test_failure_is_not_retried_and_retains_unknown_charge(self):
        attempts = []
        def transport(*_):
            attempts.append(True)
            raise ProviderFailure("injected offline failure")
        ledger = SpendLedger("1.25")
        model = BudgetedModel(self.native(transport), ledger, "summary", "gpt-4.1-mini-2025-04-14")
        for _ in range(2):
            with self.assertRaises(ProviderFailure):
                model.generate(self.request())
        self.assertEqual(len(attempts), 1)
        self.assertEqual(ledger.records[0]["status"], "unreconciled")
        self.assertGreater(ledger.held, 0)

    def test_shared_budget_applies_across_stages_and_rejects_large_caps(self):
        with self.assertRaises(ValidationError):
            SpendLedger("1.26")
        ledger = SpendLedger("0.09")
        first = ledger.reserve("predecessor", "gpt-4.1-mini-2025-04-14", 32000, 2048, 2000)
        ledger.settle(first, ModelResponse("gpt-4.1-mini-2025-04-14", "{}", Usage(32000, 2048), "stop"))
        with self.assertRaises(ProviderFailure):
            ledger.reserve("successor", "gpt-4.1-2025-04-14", 32000, 2048, 2000)

    def test_plan_is_one_block_and_no_api_authorization(self):
        data, pilot = load_config(REPO / "configs/calibration-task001.yaml")
        proposal = plan(data, pilot)
        self.assertEqual(proposal["maximum_calls"], 66)
        self.assertEqual(proposal["combined_token_envelope"], 333024)
        self.assertEqual(proposal["cost_envelope_usd"], "1.2286848")
        self.assertEqual(proposal["maximum_successor_branches"], 4)
        self.assertEqual(main(["calibration-block", "--config", str(REPO / "configs/calibration-task001.yaml")]), 2)
        self.assertFalse(proposal["paid_calls_authorized"])

    def test_saved_token_audit_covers_frozen_text_without_changes(self):
        audit = audit_saved_checkpoints()
        self.assertEqual(len(audit["records"]), 3)
        for row in audit["records"]:
            self.assertAlmostEqual(sum(row["category_token_equivalents"].values()), row["isolated_text_tokens"], places=2)
            self.assertIsNone(row["provider_reported_usage"])
            self.assertTrue(row["exact_duplicate_leaf_values"])
        self.assertFalse(audit["serializer_changed"])


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("sandbox-exec"), "macOS isolation required")
class CalibrationBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="keisho-readiness-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.sandbox = verify_sandbox(self.root)
        self.data, self.pilot = load_config(REPO / "configs/calibration-task001.yaml")

    def test_private_gold_hidden_grades_and_future_results_do_not_enter_handoffs(self):
        sentinel = "PRIVATE_ORACLE_CANARY_96327"
        gold = load_gold("task_001")
        gold["private_oracle_fact"] = sentinel
        gold["success"]["hidden_cases"].append({"id": "hidden-canary", "module": "api", "function": "availability", "args": [1, []], "expected": sentinel})
        with patch("keisho.pilot.runner.load_gold", return_value=gold):
            block = run_block(self.pilot, "task_001", 17, self.root / "raw", self.root / "work", self.sandbox, factory, synthetic=True)
        self.assertEqual(len(block["branches"]), 4)
        parent = next((self.root / "raw").glob("*-predecessor"))
        self.assertIn(sentinel, (parent / "checkpoint-grade.json").read_text())
        for pattern in ("*/*-request.json", "*/state.json", "*/capsule*.json"):
            for path in (self.root / "raw").glob(pattern):
                self.assertNotIn(sentinel, path.read_text(), str(path))
        frozen = RawRun.open_existing(self.root / "raw", parent.name).load_frozen()
        with self.assertRaises(ValidationError):
            build_state(frozen, "Hand-authored oracle task goal")
        for row in block["branches"]:
            self.assertEqual(row["task_success"], False)
        # Future successor outcomes cannot change reconstruction of a sealed parent.
        task_event = next(event for event in frozen.events if event.id.endswith("_task"))
        state = build_state(frozen, json.loads(task_event.payload_json)["content"])
        from keisho.compiler.fixed import compile_fixed
        from keisho.core import canonical_json
        self.assertEqual(compile_fixed(state), canonical_json(json.loads((parent / "state.json").read_text())))

    def test_one_block_review_covers_all_actions_and_repeat_execution_is_refused(self):
        path = execute_one(self.data, self.pilot, self.root / "raw", self.root / "work", self.sandbox, factory, synthetic=True)
        result = json.loads((path / "result.json").read_text())
        self.assertEqual(len(result["execution"]["branches"]), 4)
        worksheet = json.loads((path / "human-review.json").read_text())
        actions = sum(1 for run_id in result["raw_run_ids"] for event in RawRun.open_existing(self.root / "raw", run_id).load_frozen().events if event.kind.value == "tool_call")
        self.assertEqual(len(worksheet["actions"]), actions)
        self.assertTrue(any(row["rule_decisions"] for row in worksheet["actions"]))
        self.assertTrue(any(not row["rule_decisions"] for row in worksheet["actions"]))
        self.assertTrue(all(row["dependency_configuration_evidence_review"] is None for row in worksheet["actions"]))
        timeline = (path / "timeline.md").read_text()
        for condition in self.pilot.data["conditions"]:
            self.assertIn("Actual handoff: " + condition, timeline)
        with self.assertRaises(FileExistsError):
            execute_one(self.data, self.pilot, self.root / "raw", self.root / "work2", self.sandbox, factory, synthetic=True)

    def test_unknown_successor_usage_halts_before_other_branches(self):
        def missing_usage_factory(role, task_id, condition):
            model = factory(role, task_id, condition)
            if role == "successor":
                generate = model.generate
                model.generate = lambda request: replace(generate(request), usage=Usage(None, None))
            return model
        path = execute_one(self.data, self.pilot, self.root / "raw", self.root / "work", self.sandbox, missing_usage_factory, synthetic=True)
        result = json.loads((path / "result.json").read_text())
        self.assertTrue(result["spending_stopped"])
        self.assertEqual(len(result["execution"]["branches"]), 1)
        self.assertEqual(result["execution"]["status"], "spending_stopped")
        self.assertEqual(json.loads((path / "spending.json").read_text())["attempts"][-1]["status"], "unreconciled")

    def test_ineligible_checkpoint_stops_without_summary_or_successors(self):
        calls = []
        def solved_early(role, task_id, condition):
            calls.append(role)
            from keisho.pilot.offline import FixtureModel
            return FixtureModel("offline/early-finish", ('{"action":{"tool":"finish","answer":"not continuing"},"claims":[]}',))
        path = execute_one(self.data, self.pilot, self.root / "raw", self.root / "work", self.sandbox, solved_early, synthetic=True)
        result = json.loads((path / "result.json").read_text())
        self.assertEqual(result["execution"]["status"], "checkpoint_invalid")
        self.assertEqual(result["execution"]["branches"], [])
        self.assertEqual(calls, ["predecessor"])


if __name__ == "__main__":
    unittest.main()
