import argparse
from decimal import Decimal
import hashlib
import json
import os
import sys
from pathlib import Path
import tempfile
import uuid
from urllib import request

from keisho.agents.providers.openai_chat import OpenAIChatModel, MODEL_PRICES, PRICING_SOURCE
from keisho.core import canonical_json, digest, primitive, require, text_digest
from keisho.logging.raw import RawRun
from keisho.local_env import load_project_env
from .calibration import calibrate
from .config import PilotConfig
from .offline import factory as offline_factory
from .runner import prompt, run_pilot
from .sandbox import IsolationUnavailable, MacSandbox
from .tasks import REPO, TASK_IDS, load_public
from .tokenizer import NativeTokenizer, VOCAB_SHA256, VOCAB_URL


def verify_sandbox(root: Path) -> MacSandbox:
    workspace = root / "isolation-probe"
    workspace.mkdir()
    (workspace / "own.txt").write_text("own")
    secret = root / "gold-canary.txt"
    sibling = root / "sibling-canary.txt"
    secret.write_text("private gold canary")
    sibling.write_text("private sibling canary")
    sandbox = MacSandbox()
    sandbox.verify(workspace, workspace / "own.txt", (secret, sibling))
    return sandbox


def pilot_manifest(config: PilotConfig) -> dict:
    blocks, branches = 9, 36
    pred, succ = config.budgets("predecessor"), config.budgets("successor")
    pred_calls, succ_calls, summary_calls = blocks * pred.model_calls, branches * succ.model_calls, blocks
    def bounded_cost(role, units, budgets):
        input_rate, _, output_rate = MODEL_PRICES[config.data[role]["model_id"]]
        output = min(budgets.total_tokens, budgets.model_calls * budgets.output_tokens)
        inputs = budgets.total_tokens - output
        return units * (inputs * input_rate + output * output_rate) / Decimal(1_000_000)
    pre_cost = bounded_cost("predecessor", blocks, pred)
    suc_cost = bounded_cost("successor", branches, succ)
    p_in, _, p_out = MODEL_PRICES[config.data["predecessor"]["model_id"]]
    summary_cost = summary_calls * (pred.request_input_tokens * p_in + config.data["summary_output_tokens"] * p_out) / Decimal(1_000_000)
    prompts = {role: {"version": "0.1.0" if role == "summary" else "1.0.0", "sha256": text_digest(prompt(role)), "text": prompt(role)} for role in ("agent", "predecessor", "summary")}
    return {"version": "1.0.0", "protocol_version": config.data["protocol_version"], "config_sha256": config.sha256,
            "tasks": [{"id": task_id, "sha256": load_public(task_id).sha256, "checkpoint_tool_calls": 9} for task_id in TASK_IDS],
            "predecessor": config.data["predecessor"], "successor": config.data["successor"], "summary_model": config.data["predecessor"]["model_id"],
            "state_builder": "gold-blind-projection/1.0.0; deterministic, zero API calls", "state_version": "0.1.1",
            "conditions": config.data["conditions"], "repetitions": 3, "seeds": config.data["seeds"], "successor_branches": 36,
            "model_call_upper_bounds": {"predecessor": pred_calls, "successor": succ_calls, "summary": summary_calls, "total": pred_calls + succ_calls + summary_calls},
            "combined_token_upper_bound": blocks * pred.total_tokens + branches * succ.total_tokens + blocks * (pred.request_input_tokens + config.data["summary_output_tokens"]),
            "estimated_cost_upper_envelope_usd": str(pre_cost + suc_cost + summary_cost), "cost_by_stage_usd": {"predecessor": str(pre_cost), "successor": str(suc_cost), "summary": str(summary_cost)},
            "cost_assumptions": "Published default-tier rates checked 2026-10-03, no caching discounts, bounded total agent tokens and maximum outputs. Planning envelope, not a billing guarantee; excludes taxes, live calibration and any future separately authorized amendments.",
            "pricing_source": PRICING_SOURCE, "prompts": prompts, "paid_calls_authorized": False,
            "credential_available": bool(os.environ.get("OPENAI_API_KEY")), "api_access_verified": False,
            "live_model_checkpoint_calibration": "unverified", "scientific_readiness": "not cleared; scripted calibration and conservative scoring cannot establish live checkpoint difficulty or annotation coverage"}


def immutable_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(canonical_json(value) + "\n")


def main(argv=None):
    actual = sys.argv[1:] if argv is None else argv
    if actual and actual[0] in ("pack", "inspect", "resume"):
        from keisho.handoff.cli import main as handoff_main
        return handoff_main(actual)
    if actual and actual[0] in ("dev-suite", "dev-check", "dev-plan", "dev-prepare", "dev-continue"):
        from keisho.development.cli import main as development_main
        return development_main(actual)
    if actual and actual[0] in ("calibration-block", "audit-handoffs"):
        from .calibration_block import main as calibration_main
        return calibration_main(actual)
    parser = argparse.ArgumentParser(prog="keisho", epilog="Local handoff: pack --repo ... --session ... --task ... --out ...; inspect BUNDLE; resume BUNDLE --manual --workspace NEW_DIR")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "calibrate", "pilot"):
        command = sub.add_parser(name)
        command.add_argument("--config", type=Path, default=REPO / "configs/pilot.yaml")
        command.add_argument("--output", type=Path)
        if name == "pilot":
            command.add_argument("--offline", action="store_true")
            command.add_argument("--approve-live", action="store_true", help="explicit human authorization; never used by offline checks")
    prepare = sub.add_parser("prepare-tokenizer")
    prepare.add_argument("--output", type=Path, default=REPO / ".cache/tokenizers/o200k_base.tiktoken")
    args = parser.parse_args(argv)
    try:
        load_project_env(REPO)
        if args.command == "prepare-tokenizer":
            require(not args.output.exists(), "tokenizer asset already exists; refuse overwrite")
            with request.urlopen(VOCAB_URL, timeout=30) as response:
                data = response.read()
            require(hashlib.sha256(data).hexdigest() == VOCAB_SHA256, "download hash mismatch")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(data)
            print("Public tokenizer asset prepared; no model calls.")
            return 0
        config = PilotConfig.load(args.config)
        if args.command == "plan":
            manifest = pilot_manifest(config)
            if args.output:
                immutable_json(args.output, manifest)
                print(f"Pilot manifest saved: {args.output}")
            else:
                print(json.dumps(manifest, indent=2))
            return 0
        if args.command == "pilot" and not args.offline:
            require(args.approve_live, "paid pilot disabled; explicit --approve-live authorization required")
            require(bool(os.environ.get("OPENAI_API_KEY")), "OPENAI_API_KEY is not configured")
        if args.command == "pilot" and args.offline:
            require(not args.approve_live, "offline mode cannot carry live authorization")
        with tempfile.TemporaryDirectory(prefix="keisho-phase1-") as temporary:
            root = Path(temporary).resolve()
            sandbox = verify_sandbox(root)  # Before any model call.
            if args.command == "calibrate":
                report = calibrate(config, REPO / "runs/calibration", root / "work", sandbox)
                destination = args.output or REPO / "analysis/calibration-v1.0.0.json"
                immutable_json(destination, report)
                print(f"Scripted calibration saved: {destination}. No model evidence or API calls.")
                return 0
            if args.offline:
                model_factory = offline_factory
                raw = REPO / "runs/offline"
            else:
                NativeTokenizer()  # Exact offline counter must be available first.
                def model_factory(role, task_id, condition):
                    identity = config.data["successor" if role == "successor" else "predecessor"]["model_id"]
                    return OpenAIChatModel(identity, authorized=True, mode="summary" if role == "summary" else "agent")
                raw = REPO / "runs/raw"
            result = run_pilot(config, raw, root / "work", sandbox, model_factory, synthetic=args.offline)
            index = RawRun(raw, f"pilot-index-{uuid.uuid4()}")
            index.freeze()
            index.write_artifact("pilot-manifest.json", pilot_manifest(config))
            index.write_artifact("result.json", result)
            print(f"{'Synthetic validation' if args.offline else 'Pilot'} {result['status']}; immutable index {index.path}")
            return 0 if result["status"] == "complete" else 1
    except (ValueError, OSError, IsolationUnavailable) as exc:
        print(f"Keisho stopped: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
