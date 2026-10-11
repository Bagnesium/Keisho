"""Controlled lifecycle for one nine-block/four-condition Phase 1 pilot."""

from contextlib import contextmanager
from decimal import Decimal
import json
from pathlib import Path
import platform
import random
import time
import uuid

from keisho.agents.base import Message, ModelRequest
from keisho.compiler.serializer import serialize
from keisho.core import ValidationError, canonical_json, digest, primitive, require, text_digest, utc_now
from keisho.environments import Evaluation, FilesystemEnvironment
from keisho.experiments.conditions import Condition, HandoffBudgetExceeded, build_capsule
from keisho.experiments.manifest import ModelSpec, PromptRef, RunManifest, RunOutcome, RunStatus, Runtime, validate_block
from keisho.logging.raw import EventKind, RawRun
from keisho.metrics.definitions import CallPurpose
from .agent import Recorder, logged_generate, request_upper_bound, run_agent
from .config import PilotConfig
from .sandbox import MacSandbox, score_cases
from .scoring import qualify_checkpoint, score_behavior, validate_review
from .state_builder import BUILDER_VERSION, build_state
from .tasks import REPO, load_gold, load_public
from .tools import ToolSession, file_hashes


def prompt(role: str) -> str:
    version = "0.1.0" if role == "summary" else "1.0.0"
    return (REPO / f"configs/prompts/{role}-v{version}.txt").read_text()


def runtime() -> Runtime:
    import hashlib
    files = {}
    for base in ("src", "configs", "tasks"):
        for path in sorted((REPO / base).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files[path.relative_to(REPO).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return Runtime(platform.python_version(), platform.platform(), None, digest(files), text_digest((REPO / "configs/requirements-pilot.lock").read_text()), "macos-sandbox/1.0.0")


def check_task(task, gold, workspace, sandbox):
    records = score_cases(sandbox, workspace, task.cases + tuple(gold["success"]["hidden_cases"]))
    return all(result["passed"] for result in records["results"]), records


def branch_status(reason: str, solved: bool) -> RunOutcome:
    exceptional = {"model_failure": RunStatus.MODEL_FAILURE, "infrastructure_failure": RunStatus.INFRASTRUCTURE_FAILURE, "invalid_run": RunStatus.INVALID}
    if reason in exceptional:
        return RunOutcome(exceptional[reason], None, reason, "public+hidden-host-grader/1.0.0")
    return RunOutcome(RunStatus.COMPLETE if solved else RunStatus.TASK_FAILURE, solved, reason, "public+hidden-host-grader/1.0.0")


@contextmanager
def preserve_branch_failure(raw, manifest, checkpoint_id, synthetic):
    """A controller/validation failure must not leave a launched branch unlabeled."""
    try:
        yield
    except Exception as exc:
        if not (raw.path / "trajectory.json").exists():
            raw.freeze()
        if not (raw.path / "result.json").exists():
            raw.write_artifact("result.json", {
                "version": "1.0.0", "run_id": manifest.run_id, "block_id": manifest.block_id,
                "checkpoint_id": checkpoint_id, "task_id": manifest.task_id,
                "condition": manifest.condition.value, "seed": manifest.seed, "synthetic": synthetic,
                "status": "INVALID_RUN" if isinstance(exc, ValidationError) else "INFRASTRUCTURE_FAILURE",
                "task_success": None, "exception_type": type(exc).__name__,
                "artifact_validation": "failed; inspect partial artifacts and controller failure record",
                "post_handoff_model_calls": None, "post_handoff_tool_calls": None,
                "handoff_input_tokens": None, "total_post_handoff_tokens": None, "success_cost": None,
                "rediscovery_count": None, "repeated_failure_count": None,
                "contradiction_count": None, "inherited_error_candidate_count": None})
        raise


def validate_artifacts(raw: RawRun, manifest: RunManifest, capsule, predecessor, gold, review, calls) -> None:
    manifest.validate()
    successor = raw.load_frozen()
    require(manifest.capsule_sha256 == capsule.sha256 and manifest.trajectory_sha256 == predecessor.sha256, "branch artifact binding mismatch")
    requests = {event.id for event in successor.events if event.kind == EventKind.MODEL_REQUEST and event.actor == "successor"}
    responses = {event.id for event in successor.events if event.kind == EventKind.MODEL_RESPONSE and event.actor == "successor"}
    require(requests == {call.request_event_id for call in calls}, "call/request coverage mismatch")
    require(responses == {call.response_event_id for call in calls if call.response_event_id is not None}, "call/response coverage mismatch")
    for call in calls:
        call.usage.validate()
        accepted_ids = json.loads(manifest.successor.parameters_json).get("accepted_response_model_ids", [manifest.successor.model_id])
        require(call.model_id in accepted_ids, "actual model differs from frozen manifest allowlist")
        request = json.loads((raw.path / f"{call.id}-request.json").read_text())
        require(request["seed"] == manifest.seed and request["temperature"] == 0.0, "actual sampling differs from manifest")
        require(request["max_output_tokens"] == json.loads(manifest.successor.parameters_json)["output_tokens"], "actual output cap differs from manifest")
    validate_review(review, predecessor, successor, gold)
    require(all(item["branch_id"] == manifest.run_id for item in review["counted_events"]), "review branch identity mismatch")


def run_block(config: PilotConfig, task_id: str, seed: int, raw_root: Path, work_root: Path, sandbox: MacSandbox, factory, *, synthetic: bool, stop_check=None):
    task = load_public(task_id)
    block_id = f"{'offline' if synthetic else 'pilot'}-{uuid.uuid4()}"
    parent_raw = RawRun(raw_root, f"{block_id}-predecessor")
    parent = FilesystemEnvironment(work_root / f"ws-{uuid.uuid4()}", task.files, lambda _: Evaluation(None, "Controller grades only after stopping", "1.0.0"))
    parent.reset(seed)
    recorder = Recorder(parent_raw)
    predecessor_model = factory("predecessor", task_id, None)
    predecessor = run_agent(predecessor_model, ToolSession(task, parent.workspace, sandbox), recorder, task.description,
                            prompt("agent") + "\n" + prompt("predecessor"), "", seed, config.budgets("predecessor"), "predecessor", checkpoint_tools=9)
    snapshot = parent.snapshot()
    checkpoint_id = f"checkpoint-{uuid.uuid4()}"
    recorder.emit("predecessor_snapshot", EventKind.FILE_SNAPSHOT, "predecessor", {"checkpoint_id": checkpoint_id, "environment_sha256": snapshot.sha256})
    frozen = parent_raw.freeze()
    parent_raw.write_artifact("environment.json", snapshot)
    parent_raw.write_artifact("calls.json", predecessor.calls)
    parent_raw.write_artifact("execution.json", predecessor)
    gold = load_gold(task_id)  # Evaluator only, after predecessor has stopped.
    solved, grade = check_task(task, gold, parent.workspace, sandbox)
    parent_raw.write_artifact("checkpoint-grade.json", grade)
    checkpoint_hashes = file_hashes(parent.workspace, task.editable_files)
    qualification = qualify_checkpoint(gold, frozen, checkpoint_hashes, predecessor.reason, predecessor.tool_calls, solved)
    parent_raw.write_artifact("checkpoint.json", {"checkpoint_id": checkpoint_id, "synthetic": synthetic, "task_id": task_id, "seed": seed, "trajectory_sha256": frozen.sha256, "environment_sha256": snapshot.sha256, **qualification})
    if not qualification["valid"]:
        parent_raw.write_artifact("result.json", {"status": "INVALID_RUN", "reason": "checkpoint ineligible", "qualification": qualification, "synthetic": synthetic})
        return {"block_id": block_id, "status": "checkpoint_invalid", "branches": []}
    state = build_state(frozen, task.description)
    parent_raw.write_artifact("state.json", state)
    parent_raw.write_artifact("state-construction.json", {"builder_version": BUILDER_VERSION, "gold_access": False, "input_trajectory_sha256": frozen.sha256})
    summary_raw = RawRun(raw_root, f"{block_id}-summary-generator")
    summary_recorder = Recorder(summary_raw)
    summary_model = factory("summary", task_id, None)
    require(summary_model.model_id() == predecessor_model.model_id(), "summary must reuse predecessor identity")
    summary_request = ModelRequest((Message("system", prompt("summary")), Message("user", canonical_json(frozen.events))), seed, config.data["summary_output_tokens"], 0.0)
    summary_input_bound = request_upper_bound(summary_model, summary_request)
    require(summary_input_bound <= config.budgets("predecessor").request_input_tokens, "summary input exceeds cap before dispatch")
    require(summary_input_bound + config.data["summary_output_tokens"] <= config.budgets("predecessor").context_tokens, "summary context exceeds cap")
    summary_response, summary_call = logged_generate(summary_model, summary_request, summary_recorder, "summary", CallPurpose.SUMMARY, 1)
    summary_raw.freeze()
    summary_raw.write_artifact("calls.json", (summary_call,))
    if summary_response is None or summary_response.finish_reason != "stop" or not summary_response.text.strip():
        parent_raw.write_artifact("result.json", {"status": "MODEL_FAILURE", "reason": "summary generation failed; no branches launched", "synthetic": synthetic})
        return {"block_id": block_id, "status": "summary_failure", "branches": []}
    require(summary_call.usage.input_tokens is not None and summary_call.usage.output_tokens is not None, "summary usage missing")
    require(summary_call.usage.input_tokens <= config.budgets("predecessor").request_input_tokens and summary_call.usage.output_tokens <= config.data["summary_output_tokens"], "summary usage exceeds budget")
    parent_raw.write_artifact("summary.json", {"text": summary_response.text, "source_run_id": summary_raw.path.name, "prompt_version": "0.1.0", "trajectory_sha256": frozen.sha256})
    successor_models = {condition: factory("successor", task_id, condition) for condition in Condition}
    require(len({model.model_id() for model in successor_models.values()}) == 1, "all conditions require the same successor identity")
    try:
        capsules = {condition: build_capsule(condition, frozen, state, summary_response.text, successor_models[condition], config.data["handoff_token_budget"]) for condition in Condition}
        for condition in Condition:
            first = ModelRequest((Message("system", prompt("agent")), Message("user", task.description), Message("user", capsules[condition].text)), seed, config.budgets("successor").output_tokens, 0.0)
            require(request_upper_bound(successor_models[condition], first) <= config.budgets("successor").request_input_tokens, "initial successor request cannot fit budget")
    except (ValueError, HandoffBudgetExceeded) as exc:
        parent_raw.write_artifact("result.json", {"status": "INVALID_RUN", "reason": str(exc), "synthetic": synthetic})
        return {"block_id": block_id, "status": "context_invalid", "branches": []}
    runtime_info = runtime()
    prompt_refs = tuple(PromptRef(role, "0.1.0" if role == "summary" else "1.0.0", text_digest(prompt(role))) for role in ("agent", "predecessor", "summary"))
    provider = "offline" if synthetic else config.data["predecessor"]["provider"]
    def model_spec(model, role):
        parameters = primitive(config.budgets(role))
        accepted_ids = getattr(model, "response_model_ids", lambda: (model.model_id(),))()
        if len(accepted_ids) > 1:
            parameters["accepted_response_model_ids"] = list(accepted_ids)
        return ModelSpec(provider, model.model_id(), canonical_json(parameters), True)
    pred_spec = model_spec(predecessor_model, "predecessor")
    succ_spec = model_spec(next(iter(successor_models.values())), "successor")
    manifests, branches = {}, []
    order = list(Condition)
    random.Random(seed).shuffle(order)
    parent_raw.write_artifact("branch-order.json", {"seed": seed, "conditions": [condition.value for condition in order]})
    # All capsules are immutable before any successor is launched.
    for condition, capsule in capsules.items():
        parent_raw.write_artifact(f"capsule-{condition.value}.json", capsule)
        manifests[condition] = RunManifest(version="0.1.0", run_id=f"{block_id}-{condition.value}", block_id=block_id, parent_run_id=parent_raw.path.name,
            task_id=task.id, task_version=task.version, task_sha256=task.sha256, original_task_sha256=text_digest(task.description),
            predecessor=pred_spec, successor=succ_spec, condition=condition, seed=seed, checkpoint_steps=predecessor.tool_calls,
            handoff_token_budget=config.data["handoff_token_budget"], successor_step_budget=config.budgets("successor").tool_calls,
            created_at=utc_now(), protocol_version=config.data["protocol_version"], state_version=state.version, prompts=prompt_refs,
            trajectory_sha256=frozen.sha256, environment_sha256=snapshot.sha256, state_sha256=text_digest(serialize(state)),
            capsule_sha256=capsule.sha256, config_sha256=config.sha256, runtime=runtime_info)
    validate_block(tuple(manifests.values()))
    parent_raw.write_artifact("branch-manifests.json", tuple(manifests.values()))
    parent_raw.write_artifact("block-validation.json", {"status": "passed", "before_successors": True, "manifest_hashes": {condition.value: digest(manifest) for condition, manifest in manifests.items()}})
    for condition in order:
        start = time.monotonic()
        manifest = manifests[condition]
        raw = RawRun(raw_root, manifest.run_id)
        with preserve_branch_failure(raw, manifest, checkpoint_id, synthetic):
            environment = parent.fork(work_root / f"ws-{uuid.uuid4()}", snapshot)
            require(environment.snapshot() == snapshot, "branch restoration differs from checkpoint")
            model, capsule = successor_models[condition], capsules[condition]
            raw.write_artifact("manifest.json", manifest)
            raw.write_artifact("checkpoint-reference.json", {"checkpoint_id": checkpoint_id, "parent_run_id": parent_raw.path.name, "synthetic": synthetic})
            raw.write_artifact("environment.json", environment.snapshot())
            raw.write_artifact("capsule.json", capsule)
            branch_recorder = Recorder(raw)
            execution = run_agent(model, ToolSession(task, environment.workspace, sandbox), branch_recorder, task.description, prompt("agent"), capsule.text, seed, config.budgets("successor"))
            successor = raw.freeze()
            if execution.reason in ("model_failure", "infrastructure_failure", "invalid_run"):
                success, grade = False, {"scored": False, "reason": execution.reason}
            else:
                success, grade = check_task(task, gold, environment.workspace, sandbox)
            outcome = branch_status(execution.reason, success)
            outcome.validate()
            raw.write_artifact("calls.json", execution.calls)
            raw.write_artifact("outcome.json", outcome)
            raw.write_artifact("grade.json", grade)
            raw.write_artifact("final-environment.json", environment.snapshot())
            review = score_behavior(task_id, raw.path.name, gold, frozen, successor, capsule, checkpoint_hashes)
            raw.write_artifact("annotation-review.json", review)
            validate_artifacts(raw, manifest, capsule, frozen, gold, review, execution.calls)
            require(parent.snapshot() == snapshot, "branch contaminated predecessor")
            usages = [call.usage for call in execution.calls]
            tokens = None if any(usage.input_tokens is None or usage.output_tokens is None for usage in usages) else sum(usage.input_tokens + usage.output_tokens for usage in usages)
            cost = None if any(usage.cost_usd is None for usage in usages) else str(sum((Decimal(usage.cost_usd) for usage in usages), Decimal(0)))
            aliases = {RunStatus.COMPLETE: "SUCCESS", RunStatus.TASK_FAILURE: "TASK_FAILURE", RunStatus.MODEL_FAILURE: "MODEL_FAILURE", RunStatus.INFRASTRUCTURE_FAILURE: "INFRASTRUCTURE_FAILURE", RunStatus.INVALID: "INVALID_RUN"}
            result = {"version": "1.0.0", "run_id": raw.path.name, "block_id": block_id, "checkpoint_id": checkpoint_id, "task_id": task_id,
                      "condition": condition.value, "seed": seed, "synthetic": synthetic, "status": aliases[outcome.status],
                      "task_success": outcome.task_success, "post_handoff_model_calls": execution.model_calls,
                      "post_handoff_tool_calls": execution.tool_calls, "handoff_input_tokens": capsule.tokens.count,
                      "handoff_token_accounting": primitive(capsule.tokens),
                      "total_post_handoff_tokens": tokens, "success_cost": cost, "cost_currency": "USD",
                      "branch_elapsed_seconds": time.monotonic() - start, **review["counts"],
                      "annotation_review_sha256": digest(review), "scoring_coverage": review["coverage"],
                      "task_specific_exclusion_review": "pending human source review for hardcoding/API changes/grader interference",
                      "trajectory_sha256": successor.sha256, "manifest_sha256": digest(manifest), "artifact_validation": "passed"}
            raw.write_artifact("result.json", result)
            branches.append(result)
        if stop_check is not None and stop_check():
            parent_raw.write_artifact("result.json", {"status": "spending_stopped", "synthetic": synthetic, "checkpoint_id": checkpoint_id, "branch_run_ids": [branch["run_id"] for branch in branches]})
            return {"block_id": block_id, "status": "spending_stopped", "branches": branches}
        if stop_check is not None and execution.reason in ("model_failure", "infrastructure_failure", "invalid_run"):
            parent_raw.write_artifact("result.json", {"status": execution.reason, "synthetic": synthetic,
                                      "checkpoint_id": checkpoint_id, "branch_run_ids": [branch["run_id"] for branch in branches]})
            return {"block_id": block_id, "status": execution.reason, "branches": branches}
    parent_raw.write_artifact("result.json", {"status": "prepared_and_executed", "synthetic": synthetic, "checkpoint_id": checkpoint_id, "branch_run_ids": [branch["run_id"] for branch in branches]})
    return {"block_id": block_id, "status": "complete", "branches": branches}


def run_pilot(config: PilotConfig, raw_root: Path, work_root: Path, sandbox: MacSandbox, factory, *, synthetic: bool):
    require(sandbox.verified, "sandbox must be verified before any model calls")
    records = []
    for task_id in config.data["tasks"]:
        for seed in config.data["seeds"]:
            before = {path.name for path in raw_root.iterdir()} if raw_root.exists() else set()
            try:
                record = run_block(config, task_id, seed, raw_root, work_root, sandbox, factory, synthetic=synthetic)
            except Exception as exc:
                # Preserve partial runs and distinguish invariant invalidity.
                partial = sorted({path.name for path in raw_root.iterdir()} - before)
                failed = RawRun(raw_root, f"controller-failure-{uuid.uuid4()}")
                failed.freeze()
                invalid = isinstance(exc, ValidationError)
                failed.write_artifact("result.json", {"status": "INVALID_RUN" if invalid else "INFRASTRUCTURE_FAILURE", "exception_type": type(exc).__name__, "partial_run_ids": partial, "synthetic": synthetic, "task_id": task_id, "seed": seed})
                return {"status": "halted", "reason": "invalid_run" if invalid else "infrastructure_failure", "failure_run_id": failed.path.name, "blocks": records, "synthetic": synthetic}
            records.append(record)
            if record["status"] != "complete":
                return {"status": "halted", "reason": record["status"], "blocks": records, "synthetic": synthetic}
    require(sum(len(record["branches"]) for record in records) == 36, "pilot branch count mismatch")
    return {"status": "complete", "blocks": records, "synthetic": synthetic}
