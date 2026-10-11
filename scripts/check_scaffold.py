#!/usr/bin/env python3
"""Cross-component offline validation. Never emits research results or API calls."""

import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from keisho.agents.scripted import ScriptedModel
from keisho.compiler.serializer import serialize
from keisho.core import canonical_json, digest, primitive, require, text_digest, utc_now
from keisho.environments import Evaluation, FilesystemEnvironment
from keisho.experiments.branching import prepare_branches
from keisho.experiments.conditions import Condition
from keisho.experiments.manifest import ModelSpec, PromptRef, RunManifest, RunOutcome, RunStatus, Runtime, validate_block
from keisho.logging.raw import Event, EventKind, RawRun
from keisho.metrics import calculate_metrics
from keisho.state.extractor import extract_state
from tests.fixtures import fixture


def source_tree_hash() -> str:
    excluded = {".git", ".venv", "__pycache__", ".agents", ".codex", "runs", "build", "dist"}
    records = {}
    for path in sorted(REPO.rglob("*")):
        relative = path.relative_to(REPO)
        if not set(relative.parts) & excluded and path.is_file() and not path.is_symlink():
            records[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(records)


def run_check(root: Path) -> tuple[RunManifest, ...]:
    config = json.loads((REPO / "configs/phase0.json").read_text())
    require(config["phase"] == 0 and config["paid_calls_authorized"] is False, "offline Phase 0 only")
    require(config["conditions"] == [condition.value for condition in Condition], "configuration condition mismatch")
    require(config["successor_conditioning_enabled"] is False, "conditioning is deferred")
    block_id = f"offline-{uuid.uuid4()}"
    raw_root = root / "raw"
    parent_run = RawRun(raw_root, f"{block_id}-predecessor")
    fixture_trajectory, fixture_state = fixture()
    for item in fixture_trajectory.events:
        parent_run.append(item)
    trajectory = parent_run.freeze()
    require(trajectory == fixture_trajectory, "frozen fixture mismatch")
    state = extract_state(primitive(fixture_state), parent_run.load_frozen())
    parent_run.write_artifact("state.json", state)
    # A single synthetic copy/restore case, not one of the three Phase 1 tasks.
    initial = {"fixture.txt": "unfinished\n"}
    grader = lambda workspace: Evaluation((workspace / "fixture.txt").read_text() == "checked\n", "Synthetic integration assertion", "synthetic/1")
    parent = FilesystemEnvironment(root / "predecessor-workspace", initial, grader)
    snapshot = parent.reset(config["seed"])
    parent_run.write_artifact("environment.json", snapshot)
    summary = "Synthetic supplied summary; the model's database belief is unverified."
    parent_run.write_artifact("summary.json", {"text": summary, "origin": "offline fixture; not LLM generated", "trajectory_sha256": trajectory.sha256})
    model = ScriptedModel()
    branches = prepare_branches(parent, snapshot, trajectory, state, summary, model, 10000, root / "branches")
    spec = ModelSpec("offline", model.model_id(), canonical_json({"temperature": 0, "max_output_tokens": 100}), True)
    runtime = Runtime(platform.python_version(), platform.platform(), None, source_tree_hash(), text_digest((REPO / "requirements.lock").read_text()), "filesystem/0.1.0")
    prompts = tuple(PromptRef(role, "0.1.0", text_digest((REPO / f"configs/prompts/{role}-v0.1.0.txt").read_text())) for role in ("summary", "successor"))
    original_task = json.loads(trajectory.events[0].payload_json)["text"]
    manifests = []
    for branch in branches:
        start = time.monotonic()
        run = RawRun(raw_root, f"{block_id}-{branch.condition.value}")
        manifest = RunManifest(
            version="0.1.0", run_id=run.path.name, block_id=block_id, parent_run_id=parent_run.path.name,
            task_id="offline-integration-fixture", task_version="synthetic/1", task_sha256=digest(initial), original_task_sha256=text_digest(original_task),
            predecessor=spec, successor=spec, condition=branch.condition, seed=config["seed"], checkpoint_steps=1,
            handoff_token_budget=10000, successor_step_budget=10, created_at=utc_now(), protocol_version="0.1.0", state_version=state.version,
            prompts=prompts, trajectory_sha256=trajectory.sha256, environment_sha256=snapshot.sha256,
            state_sha256=text_digest(serialize(state)), capsule_sha256=branch.capsule.sha256, config_sha256=digest(config), runtime=runtime,
        )
        manifest.validate()
        manifests.append(manifest)
        run.write_artifact("manifest.json", manifest)
        run.write_artifact("capsule.json", branch.capsule)
        run.write_artifact("environment.json", branch.environment.snapshot())
        def emit(key, kind, payload, parents=()):
            run.append(Event(key, kind, "successor", utc_now(), canonical_json(payload), parents))
        emit("inspect", EventKind.TOOL_CALL, {"operation": "read fixture.txt"})
        emit("read", EventKind.TOOL_RESULT, {"content": (branch.environment.workspace / "fixture.txt").read_text()}, ("inspect",))
        emit("change", EventKind.TOOL_CALL, {"operation": "write synthetic expected content"})
        (branch.environment.workspace / "fixture.txt").write_text("checked\n")
        emit("write", EventKind.TOOL_RESULT, {"content": "checked\n"}, ("change",))
        emit("final", EventKind.FINAL_ANSWER, {"text": "Synthetic integration assertion only."})
        require(branch.environment.evaluate().success is True, "synthetic checker failed")
        outcome = RunOutcome(RunStatus.COMPLETE, True, "Offline synthetic check; no model behavior measured", "synthetic/1")
        successor_trajectory = run.freeze()
        report = calculate_metrics(successor_trajectory, outcome, branch.capsule, (), (), time.monotonic() - start, frozenset(item.id for item in state.items()))
        require(report.post_handoff_steps == 3 and report.rediscovery.value is None, "metric integration mismatch")
        run.write_artifact("calls.json", ())
        run.write_artifact("outcome.json", outcome)
        run.write_artifact("metrics.json", report)
        run.write_artifact("final-environment.json", branch.environment.snapshot())
        require(run.load_frozen() == successor_trajectory, "raw trajectory verification failed")
    validate_block(tuple(manifests))
    require(parent.snapshot() == snapshot, "successor changed predecessor workspace")
    # Restoring one branch has no effect on its siblings.
    branches[0].environment.restore(snapshot)
    require(all(branch.environment.evaluate().success for branch in branches[1:]), "sibling mutation leaked")
    return tuple(manifests)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="keisho-phase0-") as temporary:
        manifests = run_check(Path(temporary))
    print(f"Offline scaffold check passed: {len(manifests)} independent conditions, sealed logs, valid manifests and metrics. No model experiments.")
