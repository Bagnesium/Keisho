"""Complete observable timelines and explicit pending human adjudication."""

import json

from keisho.core import canonical_json
from keisho.logging.raw import EventKind, RawRun

METRICS = ("rediscovery_count", "repeated_failure_count", "contradiction_count", "inherited_error_candidate_count")


def make_review(raw_root, run_ids):
    lines = ["# Exploratory calibration review", "",
             "All content below is externally recorded. No hidden reasoning is inferred.",
             "Rule counts are exact-target diagnostics. Adjudicated semantic counts remain unknown.",
             "Matching source hashes alone do not establish complete dependency/configuration/evidence equivalence.",
             "Review legitimate verification separately from wasteful repetition. Attribution is not causation.", ""]
    worksheets = []
    for run_id in run_ids:
        path = raw_root / run_id
        if not (path / "events").exists():
            continue
        lines += [f"## {run_id}", ""]
        for capsule in sorted(path.glob("capsule-*.json")):
            data = json.loads(capsule.read_text())
            lines += [f"### Actual handoff: {data['condition']}", "", f"SHA-256: {data['sha256']}", "", "````text", data["text"] or "[Empty handoff message]", "````", ""]
        if not (path / "trajectory.json").exists():
            lines += ["Trajectory unsealed after controller failure; review incomplete.", ""]
            continue
        trajectory = RawRun.open_existing(raw_root, run_id).load_frozen()
        review_file, result_file = path / "annotation-review.json", path / "result.json"
        review = json.loads(review_file.read_text()) if review_file.exists() else None
        result = json.loads(result_file.read_text()) if result_file.exists() else None
        counts = review["counts"] if review is not None else None
        decisions = review["counted_events"] if review is not None else []
        for event in trajectory.events:
            payload = json.loads(event.payload_json)
            lines += [f"### {event.id} — {event.kind.value} — {event.timestamp}", "", "````json", json.dumps(payload, indent=2, ensure_ascii=False), "````", ""]
            if event.kind == EventKind.TOOL_CALL:
                results = [item for item in trajectory.events if item.kind == EventKind.TOOL_RESULT and event.id in item.parent_ids]
                linked_ids = {event.id, *(item.id for item in results)}
                positives = [decision for decision in decisions if decision["successor_evidence"] in linked_ids]
                row = {"run_id": run_id, "action_event_id": event.id, "result_event_ids": [item.id for item in results],
                       "action": payload["action"], "rule_decisions": positives,
                       "rule_disposition": "counted exact target" if positives else "uncounted; outside exact match, justified verification, or no established target",
                       "human_disposition": None, "dependency_configuration_evidence_review": None,
                       "legitimate_verification_or_wasteful_repetition": None}
                worksheets.append(row)
                lines += [f"Rule disposition: {row['rule_disposition']}.",
                          "Human review: **pending**. Check purpose, dependencies, public test definitions, runtime/configuration, evidence changes and equivalent approaches; source equality alone is insufficient.", ""]
        if review is not None:
            lines += ["### Scorer decisions and evidence", "", "````json", json.dumps(review, indent=2, ensure_ascii=False), "````", ""]
        lines += ["### Outcome and metric availability", "", "````json", json.dumps({
            "recorded_status": result.get("status") if result else None,
            "registered_target_rule_counts": counts,
            "human_adjudicated_counts": {metric: None for metric in METRICS},
            "demonstrated_causal_inheritance": None,
            "coverage": "pending complete action/assertion review; diagnostic zero is not zero semantic error"}, indent=2), "````", ""]
    return "\n".join(lines), {"version": "calibration-review/1.0.0", "actions": worksheets,
                               "human_review_complete": False, "demonstrated_causal_inheritance": None}
