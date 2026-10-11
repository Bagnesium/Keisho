"""Offline regression checks for the authorized single-block amendment."""

import copy
from decimal import Decimal
from functools import partial
import json
from pathlib import Path
import shutil
import ssl
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from keisho.agents.providers.openai_chat import ProviderFailure, verified_opener
from keisho.agents.providers.openrouter_chat import MODEL_ALIASES, OpenRouterChatModel
from keisho.core import ValidationError, canonical_json
from keisho.pilot.calibration_block import execute_one, load_config, plan
from keisho.pilot.cli import verify_sandbox
from keisho.pilot.offline import factory as fixture_factory
from keisho.pilot.spending import BudgetedModel, SpendLedger
from keisho.pilot.tasks import REPO
from tests.test_openrouter import Counter, MINI, model, request, response

CONFIG = REPO / "configs/calibration-task001-openrouter-v1.2.0.yaml"
ALIAS = MODEL_ALIASES[MINI]


class AmendmentTests(unittest.TestCase):
    def test_only_exact_pair_accepted_and_actual_metadata_preserved(self):
        for returned in (ALIAS, MINI):
            raw = response(); raw["model"] = returned
            native = model(Mock(return_value=(raw, "request-id")), response_model_ids=[ALIAS, MINI]).generate(request())
            self.assertEqual(native.resolved_model_id, returned)
            self.assertEqual(json.loads(native.raw_response_json)["model"], returned)
            self.assertEqual(native.requested_model_id, ALIAS)
            self.assertEqual(native.upstream_provider, "OpenAI")
        for returned in ("openai/gpt-4.1", ALIAS.upper(), ALIAS + " ", "gpt-4.1-mini", None):
            raw = response(); raw["model"] = returned
            transport = Mock(return_value=(raw, None))
            with self.assertRaises(ProviderFailure):
                model(transport, response_model_ids=[ALIAS, MINI]).generate(request())
            self.assertEqual(transport.call_count, 1)
        with self.assertRaises(ValidationError):
            model(Mock(), response_model_ids=[ALIAS, "other/model"])

    def test_strict_default_and_wrong_provider_still_stop(self):
        raw = response(); raw["model"] = ALIAS
        with self.assertRaises(ProviderFailure):
            model(Mock(return_value=(raw, None))).generate(request())
        for provider in ("Azure", "openai", None):
            raw["provider"] = provider
            ledger = SpendLedger("1.35", provider="openrouter", authorized_ceiling_usd="1.35")
            transport = Mock(return_value=(raw, None))
            wrapped = BudgetedModel(model(transport, response_model_ids=[ALIAS, MINI]), ledger, "predecessor", MINI)
            with self.assertRaises(ProviderFailure): wrapped.generate(request())
            with self.assertRaises(ProviderFailure): wrapped.generate(request())
            self.assertTrue(ledger.stopped)
            self.assertEqual(transport.call_count, 1)
            self.assertGreater(ledger.held, 0)

    def test_cap_is_explicit_and_summary_uses_same_remaining_budget(self):
        with self.assertRaises(ValidationError): SpendLedger("1.35", provider="openrouter")
        with self.assertRaises(ValidationError): SpendLedger("1.3501", provider="openrouter", authorized_ceiling_usd="1.35")
        with self.assertRaises(ValidationError): SpendLedger("1.35", provider="openai", authorized_ceiling_usd="1.35")
        ledger = SpendLedger("1.35", provider="openrouter", authorized_ceiling_usd="1.35")
        transport = Mock(return_value=(response(), None))
        BudgetedModel(model(transport), ledger, "predecessor", MINI).generate(request())
        ledger.accounted = ledger.cap - Decimal("0.001")
        summary = BudgetedModel(model(transport, mode="summary"), ledger, "summary", MINI)
        with self.assertRaises(ProviderFailure): summary.generate(request())
        self.assertEqual(transport.call_count, 1)
        self.assertTrue(ledger.stopped)

    def test_billing_routes_and_fee_contingency_recorded_separately(self):
        for byok in (False, True):
            raw = response(); raw["model"] = ALIAS
            raw["usage"].update(is_byok=byok, cost=0.00005, cost_details={"upstream_inference_cost":0.000052})
            ledger = SpendLedger("1.35", provider="openrouter", authorized_ceiling_usd="1.35")
            native = BudgetedModel(model(Mock(return_value=(raw, None)), response_model_ids=[ALIAS, MINI]), ledger, "predecessor", MINI).generate(request())
            record = ledger.records[0]
            self.assertEqual(record["reservation_multiplier"], "1.05")
            self.assertEqual(record["returned_model_id"], ALIAS)
            self.assertEqual(record["api_request_model_id"], ALIAS)
            self.assertEqual(Decimal(record["openrouter_credit_cost_usd"]), Decimal("0.00005"))
            self.assertEqual(Decimal(native.usage.cost_usd), Decimal("0.000102") if byok else Decimal("0.00005"))
            self.assertEqual(record["system_fingerprint"], "synthetic-fingerprint")

    def test_verified_ca_context_and_frozen_config_bounds(self):
        data,pilot = load_config(CONFIG)
        ca = (CONFIG.parent / data["tls"]["ca_file"]).resolve()
        with patch("urllib.request.build_opener") as build:
            verified_opener(ca)
            handler = build.call_args.args[1]
            self.assertEqual(handler._context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(handler._context.check_hostname)
        _,original = load_config(REPO / "configs/calibration-task001.yaml")
        for role in ("predecessor", "successor"):
            self.assertEqual(pilot.budgets(role), original.budgets(role))
        self.assertEqual(pilot.data["conditions"], original.data["conditions"])
        proposal = plan(data,pilot)
        self.assertEqual(proposal["maximum_calls"], 66)
        self.assertEqual(proposal["cost_envelope_usd"], "1.29011904")
        self.assertLess(Decimal(proposal["cost_envelope_usd"]),Decimal(proposal["dollar_cap_usd"]))


def alias_fixture_factory(role, task_id, condition, *, fail_successor=False, seen=None):
    fixture = fixture_factory(role, task_id, condition)
    identity = tuple(MODEL_ALIASES)[1 if role == "successor" else 0]
    alias = MODEL_ALIASES[identity]
    def transport(body, _key):
        if seen is not None: seen.append(role)
        text = "invalid-json" if fail_successor and role == "successor" else next(fixture.responses)
        return {"model": alias, "provider": "OpenAI", "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": sum(len(row["content"].split()) for row in body["messages"]),
                          "completion_tokens": len(text.split()), "cost": 0, "is_byok": False}}, None
    return OpenRouterChatModel(identity, authorized=True, api_key="offline-synthetic-key", transport=transport,
                               tokenizer=Counter(), mode="summary" if role == "summary" else "agent",
                               response_model_ids=[alias, identity])


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("sandbox-exec"), "macOS isolation required")
class AliasBlockTests(unittest.TestCase):
    def execute(self, root, factory):
        data,pilot=load_config(CONFIG)
        sandbox=verify_sandbox(root)
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("offline only")):
            path=execute_one(data,pilot,root/"raw",root/"work",sandbox,factory,synthetic=True)
        return path,json.loads((path/"result.json").read_text())

    def test_alias_responses_pass_agent_and_manifest_validation_with_one_guard(self):
        with tempfile.TemporaryDirectory(prefix="keisho-alias-test-") as temporary:
            root=Path(temporary).resolve()
            path,result=self.execute(root,alias_fixture_factory)
            self.assertEqual(result["execution"]["status"],"complete")
            self.assertEqual(len(result["execution"]["branches"]),4)
            ledger=json.loads((path/"spending.json").read_text())
            self.assertTrue(all(row["returned_model_id"]==row["api_request_model_id"] for row in ledger["attempts"]))
            with self.assertRaises(FileExistsError):
                data,pilot=load_config(CONFIG)
                execute_one(data,pilot,root/"raw",root/"work",Mock(verified=True),alias_fixture_factory,synthetic=True)

    def test_model_protocol_failure_stops_after_first_started_branch(self):
        with tempfile.TemporaryDirectory(prefix="keisho-alias-failure-") as temporary:
            seen=[]
            _,result=self.execute(Path(temporary).resolve(),partial(alias_fixture_factory,fail_successor=True,seen=seen))
            self.assertEqual(result["execution"]["status"],"model_failure")
            self.assertEqual(len(result["execution"]["branches"]),1)
            self.assertEqual(seen.count("successor"),1)


if __name__ == "__main__":
    unittest.main()
