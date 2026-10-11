"""Scripted development calibration, kept outside evaluation runs."""

import json
from pathlib import Path
import uuid

from keisho.agents.providers.openai_chat import OpenAIChatModel
from keisho.core import digest, primitive, utc_now
from keisho.environments import Evaluation, FilesystemEnvironment
from keisho.experiments.conditions import Condition, build_capsule
from keisho.logging.raw import EventKind, RawRun
from .agent import Recorder, run_agent
from .config import PilotConfig
from .offline import factory
from .runner import check_task, prompt
from .scoring import demonstrated_failures, established_facts, qualify_checkpoint
from .state_builder import build_state
from .sandbox import score_cases
from .tasks import load_gold, load_public
from .tools import ToolSession, file_hashes


def calibrate(config: PilotConfig, raw_root: Path, work_root: Path, sandbox) -> dict:
    records = []
    for task_id in config.data["tasks"]:
        task, gold = load_public(task_id), load_gold(task_id)
        raw = RawRun(raw_root, f"calibration-{task_id}-{uuid.uuid4()}")
        environment = FilesystemEnvironment(work_root / f"ws-{uuid.uuid4()}", task.files, lambda _: Evaluation(None, "External grading", "1.0.0"))
        initial = environment.reset(17)
        initial_score = score_cases(sandbox, environment.workspace, task.cases)
        failing = [item["id"] for item in initial_score["results"] if not item["passed"]]
        from keisho.core import require
        require(set(failing) == set(gold["success"]["initial_failing_tests"]), "initial task behavior differs from preregistered gold")
        recorder = Recorder(raw)
        execution = run_agent(factory("predecessor", task_id, None), ToolSession(task, environment.workspace, sandbox), recorder,
                              task.description, prompt("agent") + "\n" + prompt("predecessor"), "", 17,
                              config.budgets("predecessor"), "predecessor", checkpoint_tools=gold["checkpoint"]["tool_calls"])
        checkpoint = environment.snapshot()
        recorder.emit("predecessor_snapshot", EventKind.FILE_SNAPSHOT, "predecessor", {"environment_sha256": checkpoint.sha256})
        trajectory = raw.freeze()
        hashes = file_hashes(environment.workspace, task.editable_files)
        solved, grade = check_task(task, gold, environment.workspace, sandbox)
        qualification = qualify_checkpoint(gold, trajectory, hashes, execution.reason, execution.tool_calls, solved)
        require(qualification["valid"], "scripted checkpoint qualification failed")
        state = build_state(trajectory, task.description)
        raw.write_artifact("state.json", state)
        raw.write_artifact("environment.json", checkpoint)
        raw.write_artifact("calls.json", execution.calls)
        raw.write_artifact("checkpoint-grade.json", grade)
        summary_model = factory("summary", task_id, None)
        # Fixture summary only; no model API or empirical generator is invoked.
        summary = next(summary_model.responses)
        counter = OpenAIChatModel(config.data["successor"]["model_id"], authorized=False)
        native_capsules = {condition.value: primitive(build_capsule(condition, trajectory, state, summary, counter, config.data["handoff_token_budget"]).tokens) for condition in Condition}
        # Verify the supplied known correct solution in a separate private copy.
        fixed = environment.fork(work_root / f"gold-check-{uuid.uuid4()}", initial)
        for path, content in gold["correct_fix"].items():
            (fixed.workspace / path).write_text(content)
        correct, correct_grade = check_task(task, gold, fixed.workspace, sandbox)
        require(correct, "known correct fix does not satisfy success criterion")
        raw.write_artifact("gold-fix-check.json", correct_grade)
        record = {"task_id": task_id, "task_sha256": task.sha256, "gold_sha256": digest(gold), "raw_run_id": raw.path.name,
                  "checkpoint_tool_calls": execution.tool_calls, "snapshot_sha256": checkpoint.sha256, "trajectory_sha256": trajectory.sha256,
                  "initial_failing_tests": failing, "qualification": qualification, "native_handoff_counts": native_capsules,
                  "established_fact_ids": sorted(established_facts(gold, trajectory, hashes)),
                  "demonstrated_failed_target_ids": sorted(demonstrated_failures(gold, trajectory)), "known_fix_passed": correct}
        raw.write_artifact("result.json", {"synthetic": True, "calibration_only": True, **record})
        records.append(record)
    return {"version": "1.0.0", "created_at": utc_now(), "kind": "scripted development calibration, not model evidence",
            "config_sha256": config.sha256, "evaluation_pooling_allowed": False, "records": records,
            "live_model_calibration_status": "unverified; no API calls made"}
