"""One task_001 exploratory block, gated independently from the 36-branch pilot."""

import argparse
import copy
from decimal import Decimal
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import tempfile

from keisho.agents.providers.openai_chat import MODEL_PRICES, OpenAIChatModel, PRICING_SOURCE, http_transport, verified_opener
from keisho.agents.providers import openrouter_chat
from keisho.core import digest, require, text_digest
from keisho.logging.raw import EventKind, RawRun
from keisho.local_env import load_project_env
from .agent import Recorder
from .calibration_review import make_review
from .config import PilotConfig
from .runner import prompt, run_block
from .spending import BudgetedModel, SpendLedger
from .tasks import REPO, load_public
from .token_audit import audit_saved_checkpoints
from .tokenizer import NativeTokenizer


def load_config(path):
    data = json.loads(path.read_text())
    require(data["version"] in ("1.0.0", "1.1.0", "1.2.0") and data["task_id"] == "task_001" and data["seed"] == 17, "only the preregistered task_001/seed17 calibration is allowed")
    require(load_public("task_001").sha256 == data["task_sha256"], "registered calibration task changed")
    require(data["max_blocks"] == data["max_predecessor_trajectories"] == 1 and data["max_successor_branches"] == 4, "calibration scope cannot expand")
    require(data["automatic_retries"] == 0 and data["paid_calls_authorized"] is False and data["successor_conditioning"] is False, "retain live gate/no retries/no conditioning")
    require(data["pilot_config"] == "pilot.yaml", "use the existing pilot configuration")
    pilot = PilotConfig.load(path.parent / data["pilot_config"])
    require(pilot.sha256 == data["pilot_config_sha256"], "frozen pilot configuration changed")
    provider = data.get("provider", "openai")
    if data["version"] == "1.0.0":
        require(provider == "openai", "original calibration retains direct OpenAI")
    else:
        require(provider == "openrouter" and data["automatic_model_selection"] is False and data["model_fallbacks"] is False, "explicit restricted OpenRouter selection required")
        require(data["routing"] == {"only": ["openai"], "order": ["openai"], "allow_fallbacks": False, "require_parameters": True}, "routing restrictions changed")
        require(data["reservation_multiplier"] == "1.05", "BYOK fee reservation changed")
        if data["version"] == "1.1.0":
            require(data["identity_policy"] == "exact dated canonical response model and OpenAI provider required; aliases rejected; upstream snapshot attestation unavailable", "snapshot identity policy changed")
            require(data["catalog_path"] == "../analysis/openrouter-catalog-v1.0.0.json", "use frozen public catalog evidence")
        else:
            require(data["identity_policy"] == "exact requested public ID or catalog-confirmed canonical ID; OpenAI provider required; upstream snapshot attestation unavailable", "same-model identity policy changed")
            require(data["catalog_path"] == "../analysis/openrouter-catalog-v1.2.0.json", "use amended frozen public catalog evidence")
            require(data["dollar_cap_usd"] == "1.35", "single-block amended cap changed")
            require(data["tls"]["ca_file"] == "../.cache/certificates/openrouter-ca-v1.2.0.pem", "use the frozen project-local CA bundle")
            ca_file = (path.parent / data["tls"]["ca_file"]).resolve()
            require(hashlib.sha256(ca_file.read_bytes()).hexdigest() == data["tls"]["ca_sha256"], "frozen CA bundle changed")
            require(data["tls"]["certificate_verification"] is True and data["tls"]["hostname_verification"] is True, "verified TLS required")
            verified_opener(ca_file)  # Validate the bundle without network access.
        catalog = json.loads((path.parent / data["catalog_path"]).read_text())
        require(digest(catalog) == data["catalog_sha256"], "catalog evidence changed")
        openrouter_chat.validate_catalog(catalog)
        effective = copy.deepcopy(pilot.data)
        for role, canonical in zip(("predecessor", "successor"), openrouter_chat.MODEL_ALIASES):
            mapping = {"request_model_id": openrouter_chat.MODEL_ALIASES[canonical], "model_id": canonical}
            if data["version"] == "1.2.0":
                mapping["accepted_response_model_ids"] = [openrouter_chat.MODEL_ALIASES[canonical], canonical]
            require(data["models"][role] == mapping, "registered OpenRouter model mapping changed")
            effective[role].update(provider="openrouter", model_id=canonical)
            if data["version"] == "1.2.0":
                effective[role]["accepted_response_model_ids"] = mapping["accepted_response_model_ids"]
        pilot = PilotConfig(effective, digest(effective))  # Budgets/protocol/prompts unchanged; separate manifest identity.
    SpendLedger(data["dollar_cap_usd"], provider=provider, authorized_ceiling_usd=authorization_ceiling(data))
    return data, pilot


def authorization_ceiling(data):
    return "1.35" if data["version"] == "1.2.0" and data.get("provider") == "openrouter" else "1.25"


def plan(data, pilot):
    provider = data.get("provider", "openai")
    prices = openrouter_chat.MODEL_PRICES if provider == "openrouter" else MODEL_PRICES
    multiplier = openrouter_chat.RESERVATION_MULTIPLIER if provider == "openrouter" else Decimal(1)
    stages = {}
    for stage, role, units in (("predecessor", "predecessor", 1), ("handoff_generation", "predecessor", 1), ("successors", "successor", 4)):
        budget = pilot.budgets(role)
        if stage == "handoff_generation":
            inputs, outputs, calls = budget.request_input_tokens, pilot.data["summary_output_tokens"], 1
        else:
            outputs = min(budget.total_tokens, budget.model_calls * budget.output_tokens)
            inputs, calls = budget.total_tokens - outputs, units * budget.model_calls
        rate_in, _, rate_out = prices[pilot.data[role]["model_id"]]
        stages[stage] = {"maximum_calls": calls, "input_tokens_in_cost_maximizing_mix": units * inputs,
                         "maximum_output_token_allowance": units * outputs,
                         "combined_token_envelope": units * (inputs + outputs),
                         "cost_envelope_usd": str(multiplier * units * (inputs * rate_in + outputs * rate_out) / Decimal(1_000_000))}
    return {"version": "calibration-block/" + data["version"], "exploratory": True, "evaluation_pooling_allowed": False,
            "provider": provider, "model_mapping": data.get("models"), "identity_policy": data.get("identity_policy", "exact direct-OpenAI snapshot response required"),
            "routing": {role: openrouter_chat.routing(pilot.data[role]["model_id"]) for role in ("predecessor", "successor")} if provider == "openrouter" else None,
            "catalog_sha256": data.get("catalog_sha256"), "original_pilot_config_sha256": data["pilot_config_sha256"],
            "tls": data.get("tls"),
            "config_sha256": digest(data), "pilot_config_sha256": pilot.sha256,
            "task": {"id": "task_001", "sha256": load_public("task_001").sha256}, "seed": 17,
            "predecessor_model_id": pilot.data["predecessor"]["model_id"], "successor_model_id": pilot.data["successor"]["model_id"],
            "conditions": pilot.data["conditions"], "checkpoint_tool_calls": 9,
            "maximum_predecessor_trajectories": 1, "maximum_successor_branches": 4,
            "stage_envelopes": stages, "maximum_calls": sum(item["maximum_calls"] for item in stages.values()),
            "combined_token_envelope": sum(item["combined_token_envelope"] for item in stages.values()),
            "cost_envelope_usd": str(sum((Decimal(item["cost_envelope_usd"]) for item in stages.values()), Decimal(0))),
            "dollar_cap_usd": data["dollar_cap_usd"], "reservation_multiplier": str(multiplier),
            "reservation_policy": "reserve full 32000 input allowance and requested maximum outputs before every network attempt; no cache discounts; OpenRouter adds possible 5% BYOK fee and requires known returned total API cost",
            "context_policy": "complete cumulative messages sent every call; repeated task/handoff/history included in input and combined-token caps",
            "retry_policy": "zero; stop entire block on unreconciled usage or denied reservation; no favorable-checkpoint resampling",
            "state_generation_calls": 0, "summary_calls": 1, "paid_calls_authorized": False,
            "credential_available": bool(os.environ.get("OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY")), "api_access_verified": False,
            "pricing_source": openrouter_chat.PRICING_SOURCE if provider == "openrouter" else PRICING_SOURCE,
            "prompts": {role: {"version": "0.1.0" if role == "summary" else "1.0.0", "sha256": text_digest(prompt(role)), "text": prompt(role)} for role in ("agent", "predecessor", "summary")}}


def execute_one(data, pilot, raw_root, work_root, sandbox, factory, *, synthetic):
    require(sandbox.verified, "sandbox must be verified before any model call")
    # Fixed exclusive index prevents accidental repeat trajectories after failure.
    provider = data.get("provider", "openai")
    index = RawRun(raw_root, "calibration-task001-seed17-" + ("openrouter-" if provider == "openrouter" else "") + "v" + data["version"])
    index.write_artifact("calibration-plan.json", plan(data, pilot))
    index.write_artifact("calibration-config.json", data)
    index.write_artifact("execution-context.json", {"synthetic": synthetic, "explicit_live_authorization": not synthetic,
                        "protocol_overlay": "exploratory-calibration/" + data["version"], "evaluation_pooling_allowed": False,
                        "provider": provider, "snapshot_attestation": None if provider == "openrouter" else "direct model ID check",
                        "baseline_protocol": pilot.data["protocol_version"]})
    recorder = Recorder(index)
    number = 0
    def emit(record):
        nonlocal number
        number += 1
        recorder.emit(f"spending_{number:03d}", EventKind.ANNOTATION, "spending-control", record)
    ledger = SpendLedger(data["dollar_cap_usd"], emit, provider=provider, authorized_ceiling_usd=authorization_ceiling(data))
    def guarded_factory(role, task_id, condition):
        registered = pilot.data["successor" if role == "successor" else "predecessor"]["model_id"]
        model = factory(role, task_id, condition)
        if not synthetic:
            require(model.model_id() == registered, "no model substitution allowed")
        return BudgetedModel(model, ledger, role, registered)
    before = {path.name for path in raw_root.iterdir()}
    try:
        result = run_block(pilot, "task_001", 17, raw_root, work_root, sandbox, guarded_factory,
                           synthetic=synthetic, stop_check=lambda: ledger.stopped)
    except Exception as exc:
        result = {"status": "halted", "exception_type": type(exc).__name__, "branches": []}
    ids = sorted({path.name for path in raw_root.iterdir()} - before)
    # Timelines follow actual branch order, rather than directory label order.
    parents = [name for name in ids if name.endswith("-predecessor")]
    ordered = list(parents) + [name for name in ids if name.endswith("-summary-generator")]
    if parents and (raw_root / parents[0] / "branch-order.json").exists():
        block_id = parents[0].removesuffix("-predecessor")
        order = json.loads((raw_root / parents[0] / "branch-order.json").read_text())["conditions"]
        ordered += [f"{block_id}-{condition}" for condition in order if f"{block_id}-{condition}" in ids]
    ordered += [name for name in ids if name not in ordered]
    timeline, worksheet = make_review(raw_root, ordered)
    index.write_artifact("human-review.json", worksheet)
    with (index.path / "timeline.md").open("x") as stream:
        stream.write(timeline)
    index.write_artifact("spending.json", ledger.report())
    index.write_artifact("result.json", {"synthetic": synthetic, "exploratory": True, "evaluation_pooling_allowed": False,
                        "execution": result, "spending_stopped": ledger.stopped, "raw_run_ids": ordered,
                        "admitted_request_attempts": len(ledger.records), "provider_execution": "synthetic" if synthetic else "real",
                        "human_review_complete": False})
    index.freeze()
    return index.path


def main(argv):
    parser = argparse.ArgumentParser(prog="keisho " + argv[0])
    parser.add_argument("--config", type=Path, default=REPO / "configs/calibration-task001.yaml")
    parser.add_argument("--output", type=Path)
    if argv[0] == "calibration-block":
        parser.add_argument("--plan", action="store_true")
        parser.add_argument("--offline", action="store_true")
        parser.add_argument("--approve-live", action="store_true")
    args = parser.parse_args(argv[1:])
    try:
        from .cli import immutable_json, verify_sandbox
        load_project_env(REPO)
        if argv[0] == "audit-handoffs":
            report = audit_saved_checkpoints()
            require(args.output is not None, "provide a new output file for token audit")
            immutable_json(args.output, report)
            print(f"Token audit saved: {args.output}; unchanged serializer; no API calls.")
            return 0
        data, pilot = load_config(args.config)
        if args.plan:
            require(not args.approve_live and not args.offline, "planning cannot authorize execution")
            report = plan(data, pilot)
            if args.output:
                immutable_json(args.output, report)
                print(f"One-block calibration plan saved: {args.output}; no API calls.")
            else:
                print(json.dumps(report, indent=2))
            return 0
        require(args.output is None, "execution uses the fixed calibration directory, not --output")
        require(not (args.offline and args.approve_live), "offline mode cannot carry live authorization")
        if not args.offline:
            require(args.approve_live, "one-block paid calibration disabled; explicit --approve-live authorization required")
            key_variable = "OPENROUTER_API_KEY" if data.get("provider") == "openrouter" else "OPENAI_API_KEY"
            require(bool(os.environ.get(key_variable)), f"{key_variable} is not configured; no credential-validation request made")
        with tempfile.TemporaryDirectory(prefix="keisho-one-calibration-") as temporary:
            root = Path(temporary).resolve()
            sandbox = verify_sandbox(root)
            if args.offline:
                from .offline import factory, openrouter_factory
                factory = openrouter_factory if data.get("provider") == "openrouter" else factory
                raw = REPO / ("runs/readiness-offline-openrouter" if data.get("provider") == "openrouter" else "runs/readiness-offline")
            else:
                counter = NativeTokenizer()
                def factory(role, task_id, condition):
                    spec = pilot.data["successor" if role == "successor" else "predecessor"]
                    identity = spec["model_id"]
                    adapter = openrouter_chat.OpenRouterChatModel if data.get("provider") == "openrouter" else OpenAIChatModel
                    options = {}
                    if data["version"] == "1.2.0":
                        options = {"response_model_ids": spec["accepted_response_model_ids"],
                                   "transport": partial(http_transport, base_url=openrouter_chat.BASE_URL, provider="OpenRouter",
                                                        ca_file=(args.config.parent / data["tls"]["ca_file"]).resolve())}
                    return adapter(identity, authorized=True, tokenizer=counter, mode="summary" if role == "summary" else "agent", **options)
                raw = REPO / ("runs/real-calibration-openrouter" if data.get("provider") == "openrouter" else "runs/real-calibration")
            path = execute_one(data, pilot, raw, root / "work", sandbox, factory, synthetic=args.offline)
            recorded = json.loads((path / "result.json").read_text())
            print(f"{'Synthetic check' if args.offline else 'Exploratory calibration'} {recorded['execution']['status']}; recorded: {path}; inspect timeline.md and spending.json.")
            return 0 if recorded["execution"]["status"] == "complete" and not recorded["spending_stopped"] else 1
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Keisho stopped: {exc}")
        return 2
