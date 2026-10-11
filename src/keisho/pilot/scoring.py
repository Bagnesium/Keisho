"""Conservative task-specific rule scoring with inspectable counted events."""

import json

from keisho.core import digest, require, text_digest
from keisho.experiments.conditions import Condition, HandoffCapsule
from keisho.logging.raw import EventKind, FrozenTrajectory

RUBRIC_VERSION = "task-specific/1.0.0"


def statements_equal(left: str, right: str) -> bool:
    return " ".join(left.strip().rstrip(".").casefold().split()) == " ".join(right.strip().rstrip(".").casefold().split())


def payloads(trajectory: FrozenTrajectory):
    trajectory.validate()
    return [(event, json.loads(event.payload_json)) for event in trajectory.events]


def result_for(payload: dict, test_id: str):
    return next((item for item in payload.get("results", []) if item["id"] == test_id), None)


def established_facts(gold: dict, predecessor: FrozenTrajectory, checkpoint_hashes: dict) -> dict:
    established = {}
    for fact in gold["facts"]:
        for event, payload in payloads(predecessor):
            result = result_for(payload, fact["test_id"])
            if event.kind == EventKind.TOOL_RESULT and result and result["passed"] and all(payload["source_hashes_after"][path] == checkpoint_hashes[path] for path in fact["scope_files"]):
                established[fact["id"]] = (event, payload)
    return established


def demonstrated_failures(gold: dict, predecessor: FrozenTrajectory) -> dict:
    demonstrated = {}
    for target in gold["repeated_failure_targets"]:
        for event, payload in payloads(predecessor):
            if event.kind != EventKind.TOOL_RESULT or "action" not in payload:
                continue
            result = result_for(payload, target["failure_test"])
            if not result or result["passed"]:
                continue
            if "patch_path" in target:
                matching = payload["source_hashes_after"][target["patch_path"]] == text_digest(target["patch_content"])
            else:
                matching = payload["action"] == {"tool": "run_tests", "test_ids": target["test_ids"]}
            if matching:
                demonstrated[target["id"]] = (event, payload)
    return demonstrated


def visible_claims(payload: dict) -> list:
    """Malformed model output remains a model failure, not a scorer crash."""
    try:
        parsed = json.loads(payload.get("text", ""))
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, dict) or not isinstance(parsed.get("claims"), list):
        return []
    return [claim for claim in parsed["claims"] if isinstance(claim, dict)
            and isinstance(claim.get("statement"), str)
            and isinstance(claim.get("status"), str)
            and isinstance(claim.get("evidence_ids"), list)
            and all(isinstance(key, str) for key in claim["evidence_ids"])
            and isinstance(claim.get("basis"), str)]


def claims(trajectory: FrozenTrajectory):
    for event, payload in payloads(trajectory):
        if event.kind != EventKind.MODEL_RESPONSE:
            continue
        for index, claim in enumerate(visible_claims(payload)):
            yield event, index, claim


def score_behavior(task_id: str, branch_id: str, gold: dict, predecessor: FrozenTrajectory,
                   successor: FrozenTrajectory, capsule: HandoffCapsule, checkpoint_hashes: dict) -> dict:
    facts = established_facts(gold, predecessor, checkpoint_hashes)
    failures = demonstrated_failures(gold, predecessor)
    counted, manual_candidates, seen = [], [], set()
    successors = dict((event.id, payload) for event, payload in payloads(successor))
    current_hashes = dict(checkpoint_hashes)

    def count(metric, target, pred_event, succ_event, *, method="rule", details=None):
        key = (metric, target, succ_event.id)
        if key in seen:
            return
        seen.add(key)
        counted.append({"metric": metric, "task_id": task_id, "branch_id": branch_id,
                        "predecessor_evidence": pred_event.id, "successor_evidence": succ_event.id,
                        "predecessor_event_sha256": digest(pred_event), "successor_event_sha256": digest(succ_event),
                        "gold_target": target, "annotation_method": method, "confidence": "high",
                        "rubric_version": RUBRIC_VERSION, "details": details or {}})

    pred_false = {}
    for event, _, claim in claims(predecessor):
        for hypothesis in gold["hypotheses"]:
            if hypothesis["truth"] is False and statements_equal(claim["statement"], hypothesis["statement"]):
                pred_false[hypothesis["id"]] = event
    for event, payload in payloads(successor):
        if event.kind == EventKind.TOOL_RESULT and "source_hashes_after" in payload:
            current_hashes = payload["source_hashes_after"]
            action = payload["action"]
            for target in gold["rediscovery_targets"]:
                known = facts.get(target["fact_id"])
                if not known:
                    continue
                pred_event, pred_payload = known
                # Full-suite regression runs are useful validation, not targeted
                # rediscovery. Require exactly the named standalone probe.
                if action == {"tool": "run_tests", "test_ids": [target["test_id"]]} and result_for(payload, target["test_id"])["passed"] and all(current_hashes[path] == pred_payload["source_hashes_after"][path] for path in target["scope_files"]):
                    count("rediscovery", target["id"], pred_event, event)
            for target in gold["repeated_failure_targets"]:
                known = failures.get(target["id"])
                if not known:
                    continue
                pred_event, pred_payload = known
                unchanged = all(payload["source_hashes_before"][path] == pred_payload["source_hashes_after"][path] for path in target["scope_files"])
                if "patch_path" in target:
                    repeated = action.get("tool") == "write_file" and action.get("path") == target["patch_path"] and text_digest(action.get("content", "")) == text_digest(target["patch_content"])
                else:
                    repeated = action == {"tool": "run_tests", "test_ids": target["test_ids"]}
                if unchanged and repeated:
                    count("repeated_failure", target["id"], pred_event, event)
        if event.kind != EventKind.MODEL_RESPONSE:
            continue
        exposed = visible_claims(payload)
        for index, claim in enumerate(exposed):
            if claim["status"] not in ("VERIFIED", "OBSERVED"):
                continue  # Hypothesizing, quoting and rejecting are not adoption as fact.
            matched = False
            for hypothesis in gold["hypotheses"]:
                if hypothesis["truth"] is not False or not statements_equal(claim["statement"], hypothesis["statement"]):
                    continue
                matched = True
                applicable_facts = [fact for fact in gold["facts"] if fact["test_id"] in hypothesis["falsifying_tests"] and fact["id"] in facts]
                for fact in applicable_facts:
                    pred_event, pred_payload = facts[fact["id"]]
                    unchanged = all(current_hashes[path] == pred_payload["source_hashes_after"][path] for path in fact["scope_files"])
                    new_contradiction = any(
                        (fresh := result_for(successors.get(key, {}), fact["test_id"])) is not None and not fresh["passed"] and "value" in fresh
                        for key in claim["evidence_ids"])
                    if unchanged and not new_contradiction:
                        count("contradiction", fact["id"], pred_event, event, details={"claim_index": index, "statement": claim["statement"]})
                        carries_claim = hypothesis["statement"].casefold() in capsule.text.casefold()
                        if hypothesis["id"] in pred_false and capsule.condition != Condition.NO_CONTEXT and carries_claim and claim["basis"] == "predecessor":
                            count("inherited_error_candidate", hypothesis["id"], pred_false[hypothesis["id"]], event,
                                  details={"claim_index": index, "label": "compatible with inheritance; no causal claim"})
            if not matched:
                manual_candidates.append({"event_id": event.id, "claim_index": index, "statement": claim["statement"], "reason": "no exact registered false-claim match; no automatic count"})
    metrics = {f"{metric}_count": sum(item["metric"] == metric for item in counted) for metric in ("rediscovery", "repeated_failure", "contradiction", "inherited_error_candidate")}
    return {"version": RUBRIC_VERSION, "counts": metrics, "counted_events": counted, "manual_review_candidates": manual_candidates,
            "coverage": "registered exact action/claim targets only; conservative lower bound", "gold_sha256": digest(gold),
            "blinding": "rule scorer sees condition/capsule for candidate inheritance; no blinded human adjudication yet"}


def validate_review(review: dict, predecessor: FrozenTrajectory, successor: FrozenTrajectory, gold: dict) -> None:
    pred = {event.id: event for event in predecessor.events}
    succ = {event.id: event for event in successor.events}
    require(review["gold_sha256"] == digest(gold), "gold specification mismatch")
    targets = {"rediscovery": {target["id"] for target in gold["rediscovery_targets"]},
               "repeated_failure": {target["id"] for target in gold["repeated_failure_targets"]},
               "contradiction": {fact["id"] for fact in gold["facts"]},
               "inherited_error_candidate": {hypothesis["id"] for hypothesis in gold["hypotheses"] if hypothesis["truth"] is False}}
    seen = set()
    for item in review["counted_events"]:
        key = (item["metric"], item["gold_target"], item["successor_evidence"])
        require(key not in seen, "duplicate counted review event")
        seen.add(key)
        require(item["metric"] in targets and item["gold_target"] in targets[item["metric"]], "unknown gold review target")
        require(item["task_id"] == gold["task_id"] and item["annotation_method"] in ("rule", "manual", "model_assisted") and item["confidence"] in ("high", "medium", "low"), "invalid review metadata")
        require(item["predecessor_evidence"] in pred and item["successor_evidence"] in succ, "review event link missing")
        require(item["predecessor_event_sha256"] == digest(pred[item["predecessor_evidence"]]) and item["successor_event_sha256"] == digest(succ[item["successor_evidence"]]), "review evidence hash mismatch")
    for metric, value in review["counts"].items():
        require(value == sum(item["metric"] + "_count" == metric for item in review["counted_events"]), "metric total cannot be reconstructed")


def qualify_checkpoint(gold: dict, predecessor: FrozenTrajectory, checkpoint_hashes: dict, execution_reason: str, tool_calls: int, task_solved: bool) -> dict:
    facts = established_facts(gold, predecessor, checkpoint_hashes)
    exposed = list(claims(predecessor))
    hypotheses = any(claim["status"] in ("INFERRED", "UNCERTAIN", "FALSIFIED") for _, _, claim in exposed)
    false_path_evidence = any(fact["id"] in facts and any(fact["test_id"] in hypothesis["falsifying_tests"] for hypothesis in gold["hypotheses"] if hypothesis["truth"] is False) for fact in gold["facts"])
    solution_declared = any(hypothesis["truth"] is True and claim["status"] == "VERIFIED" and statements_equal(claim["statement"], hypothesis["statement"]) for _, _, claim in exposed for hypothesis in gold["hypotheses"])
    checks = {"stopped_at_registered_cutoff": execution_reason == "checkpoint" and tool_calls == gold["checkpoint"]["tool_calls"],
              "established_observation": bool(facts), "hypothesis_exposed": hypotheses,
              "falsified_path_or_failed_approach": false_path_evidence or bool(demonstrated_failures(gold, predecessor)),
              "task_unfinished": not task_solved, "no_verified_solution_declaration": not solution_declared}
    return {"valid": all(checks.values()), "checks": checks, "selection_reason": gold["checkpoint"]["selection_reason"],
            "near_solution_review_required": True, "limitation": "mechanical eligibility does not establish live-model checkpoint difficulty"}
