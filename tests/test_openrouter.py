import copy
from dataclasses import replace
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from keisho.agents.base import Message, ModelRequest, TokenCount
from keisho.agents.providers.openai_chat import NoRedirect, OpenAIChatModel, ProviderFailure, http_transport
from keisho.agents.providers.openrouter_chat import MODEL_ALIASES, OpenRouterChatModel, routing, validate_catalog
from keisho.core import ValidationError, canonical_json
from keisho.local_env import load_project_env
from keisho.pilot.calibration_block import execute_one, load_config, plan
from keisho.pilot.cli import main, verify_sandbox
from keisho.pilot.offline import openrouter_factory
from keisho.pilot.spending import BudgetedModel, SpendLedger
from keisho.pilot.tasks import REPO

MINI = "openai/gpt-4.1-mini-2025-04-14"
CONFIG = REPO / "configs/calibration-task001-openrouter-v1.1.0.yaml"


class Counter:
    def count(self, text):
        return TokenCount(len(text.split()), "offline-test-counter", True)


def response():
    return {"model": MINI, "provider": "OpenAI", "id": "synthetic-generation", "system_fingerprint": "synthetic-fingerprint",
            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "cost": 0.00005,
                      "is_byok": False, "prompt_tokens_details": {"cached_tokens": 20}}}


def model(transport, **kwargs):
    return OpenRouterChatModel(MINI, authorized=True, api_key="fake-router-key", transport=transport, tokenizer=Counter(), **kwargs)


def request():
    return ModelRequest((Message("user", "Return JSON"),), 17, 2048, 0.0)


class LocalEnvTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, text):
        path = self.root / ".env"
        path.write_text(text)
        path.chmod(0o600)
        return path

    def test_literal_loading_and_environment_precedence_including_empty_values(self):
        path = self.write("# Local only\nOPENROUTER_API_KEY='file-router-secret'\nexport OPENAI_API_KEY=\"$(never-executed)\" # literal\nOTHER_API_KEY=ignored\n")
        before = path.read_bytes()
        environ = {"OPENROUTER_API_KEY": "existing-secret"}
        status = load_project_env(self.root, environ)
        self.assertEqual(environ, {"OPENROUTER_API_KEY": "existing-secret", "OPENAI_API_KEY": "$(never-executed)"})
        self.assertNotIn("secret", canonical_json(status))
        self.assertEqual(path.read_bytes(), before)
        environ = {"OPENROUTER_API_KEY": ""}
        self.assertFalse(load_project_env(self.root, environ)["present"]["OPENROUTER_API_KEY"])

    def test_no_discovery_in_task_workspace_or_parent_directory(self):
        self.write("OPENROUTER_API_KEY=parent-secret\n")
        workspace = self.root / "task-workspace"
        workspace.mkdir()
        (workspace / ".env").write_text("OPENROUTER_API_KEY=task-secret\n")
        trusted = self.root / "project"
        trusted.mkdir()
        environ = {}
        with patch("os.getcwd", return_value=str(workspace)):
            load_project_env(trusted, environ)
        self.assertEqual(environ, {})

    def test_permissions_symlinks_and_malformed_files_fail_without_secret_echo_or_partial_load(self):
        path = self.write("OPENROUTER_API_KEY=sentinel-secret\nnot-an-assignment-sentinel-secret\n")
        environ = {}
        with self.assertRaises(ValidationError) as caught:
            load_project_env(self.root, environ)
        self.assertNotIn("sentinel-secret", str(caught.exception))
        self.assertEqual(environ, {})
        path.chmod(0o644)
        with self.assertRaises(ValidationError):
            load_project_env(self.root, environ)
        path.unlink()
        target = self.root / "other"
        target.write_text("OPENROUTER_API_KEY=sentinel-secret\n")
        path.symlink_to(target)
        with self.assertRaises((ValidationError, OSError)):
            load_project_env(self.root, environ)

    def test_cli_loads_trusted_root_explicitly_and_keeps_changed_run_gated(self):
        with patch("keisho.pilot.calibration_block.load_project_env") as loader, patch("sys.stdout", new_callable=io.StringIO), patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network forbidden")):
            self.assertEqual(main(["calibration-block", "--config", str(CONFIG)]), 2)
            loader.assert_called_once_with(REPO)


class RouterTests(unittest.TestCase):
    def test_endpoint_and_key_selection_without_network_and_redirects_disabled(self):
        class FakeHTTP:
            headers = {"x-request-id": "synthetic-request"}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self):
                return json.dumps(response()).encode()
        opener = Mock()
        opener.open.return_value = FakeHTTP()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-openai-key", "OPENROUTER_API_KEY": "fake-router-key"}, clear=True), patch("urllib.request.build_opener", return_value=opener) as build:
            router = OpenRouterChatModel(MINI, authorized=True, tokenizer=Counter())
            router.generate(request())
            sent = opener.open.call_args.args[0]
            self.assertEqual(sent.full_url, "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(sent.get_header("Authorization"), "Bearer fake-router-key")
            self.assertIsInstance(build.call_args.args[0], NoRedirect)
            http_transport({}, "fake-openai-key")
            sent = opener.open.call_args.args[0]
            self.assertEqual(sent.full_url, "https://api.openai.com/v1/chat/completions")
            self.assertEqual(sent.get_header("Authorization"), "Bearer fake-openai-key")
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example"))

    def test_no_key_fallback_or_live_authorization_fallback_or_router_key_to_openai(self):
        for adapter, identity, available in ((OpenRouterChatModel, MINI, {"OPENAI_API_KEY": "fake-openai-key"}),
                                              (OpenAIChatModel, "gpt-4.1-mini-2025-04-14", {"OPENROUTER_API_KEY": "fake-router-key"})):
            with self.subTest(adapter=adapter), patch.dict(os.environ, available, clear=True):
                transport = Mock()
                with self.assertRaises(ProviderFailure):
                    adapter(identity, authorized=True, transport=transport).generate(request())
                transport.assert_not_called()
        transport = Mock()
        with self.assertRaises(ProviderFailure):
            OpenRouterChatModel(MINI, api_key="fake-router-key", transport=transport).generate(request())
        with self.assertRaises(ProviderFailure):
            OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="sk-or-v1-fake", transport=transport).generate(request())
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-router-key"}), self.assertRaises(ProviderFailure):
            OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="fake-router-key", transport=transport).generate(request())
        transport.assert_not_called()

    def test_request_routing_and_limits_match_saved_catalog(self):
        body = model(Mock()).body(request())
        self.assertEqual(body["model"], MODEL_ALIASES[MINI])
        self.assertEqual(body["provider"], routing(MINI))
        self.assertEqual(body["max_tokens"], request().max_output_tokens)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["plugins"], [])
        for key in ("models", "route", "tools", "store", "service_tier", "max_completion_tokens"):
            self.assertNotIn(key, body)
        self.assertNotIn("response_format", model(Mock(), mode="summary").body(request()))
        data, pilot = load_config(CONFIG)
        catalog = json.loads((CONFIG.parent / data["catalog_path"]).read_text())
        validate_catalog(catalog)
        bad = copy.deepcopy(catalog)
        for endpoint in bad["endpoints"][MODEL_ALIASES[MINI]]["data"]["endpoints"]:
            if endpoint["tag"] == "openai":
                endpoint["supported_parameters"].remove("seed")
        with self.assertRaises(ValidationError):
            validate_catalog(bad)
        proposal = plan(data, pilot)
        self.assertEqual(proposal["maximum_calls"], 66)
        self.assertEqual(Decimal(proposal["cost_envelope_usd"]), Decimal("1.29011904"))
        self.assertEqual(proposal["dollar_cap_usd"], "1.25")
        self.assertFalse(proposal["paid_calls_authorized"])
        _, original = load_config(REPO / "configs/calibration-task001.yaml")
        for role in ("predecessor", "successor"):
            self.assertEqual(pilot.budgets(role), original.budgets(role))
        self.assertEqual(pilot.data["conditions"], original.data["conditions"])

    def test_alias_unknown_route_and_tool_execution_fail_once_with_evidence(self):
        for change in ({"model": "openai/gpt-4.1-mini"}, {"provider": "Azure"}, {"provider": None},
                       {"choices": [{"message": {"content": "{}", "tool_calls": [{}]}, "finish_reason": "stop"}]}):
            with self.subTest(change=change):
                raw = response(); raw.update(change)
                transport = Mock(return_value=(raw, "synthetic-request"))
                with self.assertRaises(ProviderFailure) as caught:
                    model(transport).generate(request())
                self.assertIsNotNone(caught.exception.raw_response_json)
                self.assertEqual(transport.call_count, 1)

    def test_both_credentials_are_redacted_and_exposed_routing_ids_are_recorded(self):
        raw = response()
        raw["choices"][0]["message"]["content"] = "fake-router-key fake-openai-key"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-openai-key", "OPENROUTER_API_KEY": "fake-router-key"}):
            native = model(Mock(return_value=(raw, "fake-router-key"))).generate(request())
        saved = canonical_json(native)
        self.assertNotIn("fake-router-key", saved)
        self.assertNotIn("fake-openai-key", saved)
        self.assertEqual(native.requested_model_id, MODEL_ALIASES[MINI])
        self.assertEqual(native.resolved_model_id, MINI)
        self.assertEqual(native.upstream_provider, "OpenAI")
        self.assertIsNone(native.snapshot_attestation)
        self.assertIn('"provider"', native.request_body_json)


class RouterSpendingTests(unittest.TestCase):
    def wrapped(self, raw, cap="1.25"):
        ledger = SpendLedger(cap, provider="openrouter")
        transport = Mock(return_value=(raw, "synthetic-request"))
        return BudgetedModel(model(transport), ledger, "predecessor", MINI), ledger, transport

    def test_conservative_reservation_precedes_transport_and_ignores_cache_savings(self):
        events = []
        ledger = SpendLedger("1.25", events.append, provider="openrouter")
        def transport(*_):
            self.assertEqual(events[-1]["status"], "reserved")
            self.assertEqual(ledger.held, Decimal("0.01688064"))
            return response(), None
        BudgetedModel(model(transport), ledger, "predecessor", MINI).generate(request())
        self.assertEqual(ledger.accounted, Decimal("0.000056"))
        self.assertEqual(ledger.held, 0)
        self.assertEqual(ledger.records[0]["api_request_model_id"], MODEL_ALIASES[MINI])
        self.assertEqual(ledger.records[0]["upstream_provider"], "OpenAI")

    def test_returned_cost_above_token_estimate_is_accounted(self):
        raw = response();raw["usage"]["cost"] = 0.001
        wrapped, ledger, _ = self.wrapped(raw)
        wrapped.generate(request())
        self.assertEqual(ledger.accounted, Decimal("0.001"))

    def test_byok_includes_upstream_billing_and_possible_fee(self):
        raw = response()
        raw["usage"].update(is_byok=True, cost=0.0000026, cost_details={"upstream_inference_cost": 0.000052})
        wrapped, ledger, _ = self.wrapped(raw)
        native = wrapped.generate(request())
        self.assertEqual(Decimal(native.usage.cost_usd), Decimal("0.0000546"))
        self.assertEqual(ledger.accounted, Decimal("0.0000588"))

    def test_unknown_cost_route_or_usage_and_overruns_stop_all_stages_without_retry(self):
        for updates in ({"cost": None}, {"is_byok": None}, {"is_byok": True, "cost_details": {}},
                        {"prompt_tokens": None}, {"prompt_tokens": 32001}, {"completion_tokens": 2049},
                        {"cost": 1}, {"cost": "NaN"}, {"cost": -1}):
            with self.subTest(updates=updates):
                raw = response();raw["usage"].update(updates)
                wrapped, ledger, transport = self.wrapped(raw)
                with self.assertRaises(ProviderFailure):
                    wrapped.generate(request())
                self.assertTrue(ledger.stopped)
                self.assertEqual(ledger.held, Decimal("0.01688064"))
                self.assertEqual(ledger.records[0]["status"], "unreconciled")
                with self.assertRaises(ProviderFailure):
                    wrapped.generate(request())
                self.assertEqual(transport.call_count, 1)

    def test_insufficient_reservation_denies_transport_and_failures_hold_charge(self):
        wrapped, ledger, transport = self.wrapped(response(), cap="0.0168")
        with self.assertRaises(ProviderFailure):
            wrapped.generate(request())
        transport.assert_not_called()
        self.assertTrue(ledger.stopped)
        wrapped, ledger, transport = self.wrapped(response())
        transport.side_effect = ProviderFailure("offline simulated model-access failure")
        with self.assertRaises(ProviderFailure):
            wrapped.generate(request())
        with self.assertRaises(ProviderFailure):
            wrapped.generate(request())
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(ledger.held, Decimal("0.01688064"))


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("sandbox-exec"), "macOS isolation required")
class SecretIsolationTests(unittest.TestCase):
    def test_offline_router_block_keeps_credentials_and_dotenv_out_of_every_artifact_and_child(self):
        with tempfile.TemporaryDirectory(prefix="keisho-router-test-") as temporary:
            root = Path(temporary).resolve()
            trusted = root / "trusted-project";trusted.mkdir()
            local = trusted / ".env"
            local.write_text("OPENROUTER_API_KEY=ROUTER_CANARY_78249\nOPENAI_API_KEY=OPENAI_CANARY_94281\n")
            local.chmod(0o600)
            with patch.dict(os.environ, {}, clear=True), patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("offline only")):
                load_project_env(trusted)
                sandbox = verify_sandbox(root)
                probe = root / "isolation-probe"
                result = sandbox.verify(probe, probe / "own.txt", (local,))
                self.assertTrue(result["credentials_absent"])
                self.assertEqual(result["outside"], [False])
                data, pilot = load_config(CONFIG)
                path = execute_one(data, pilot, root / "raw", root / "work", sandbox, openrouter_factory, synthetic=True)
            execution = json.loads((path / "result.json").read_text())
            self.assertEqual(execution["execution"]["status"], "complete")
            self.assertEqual(len(execution["execution"]["branches"]), 4)
            self.assertFalse(execution["human_review_complete"])
            for base in (root / "raw", root / "work"):
                for item in base.rglob("*"):
                    if item.is_file():
                        text = item.read_text()
                        self.assertNotIn("ROUTER_CANARY_78249", text)
                        self.assertNotIn("OPENAI_CANARY_94281", text)
                        self.assertNotEqual(item.name, ".env")


if __name__ == "__main__":
    unittest.main()
