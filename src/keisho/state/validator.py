from dataclasses import fields, replace

from keisho.core import decode, nonempty, primitive, require, sha256, timestamp
from .provenance import EpistemicStatus as Status, SourceType, Verdict
from .schema import CATEGORY_NAMES, STATE_VERSION, ActionOutcome, KeishoState


def validate_state(state: KeishoState) -> None:
    # Re-decode even programmatically constructed dataclasses: type hints do not validate at runtime.
    decode(KeishoState, primitive(state))
    require(state.version in ("0.1.0", STATE_VERSION), "unsupported state version")
    sha256(state.trajectory_sha256, "trajectory hash")
    timestamp(state.created_at)
    sources = {source.id: source for source in state.sources}
    evidence = {record.id: record for record in state.evidence}
    items = {item.id: item for item in state.items()}
    for label, records, index in (("source", state.sources, sources), ("evidence", state.evidence, evidence), ("item", state.items(), items)):
        require(len(records) == len(index), f"duplicate {label} ID")
        for key in index:
            nonempty(key, f"{label} ID")
    require(not (sources.keys() & evidence.keys() or sources.keys() & items.keys() or evidence.keys() & items.keys()), "IDs must be unique across namespaces")
    for source in state.sources:
        nonempty(source.location, "source location")
        sha256(source.sha256, "source hash")
    for record in state.evidence:
        require(record.source_id in sources, f"dangling evidence source {record.source_id}")
        require(record.claim_id in items, f"dangling evidence claim {record.claim_id}")
        nonempty(record.description, "evidence description")
        nonempty(record.scope, "evidence scope")
        nonempty(record.verification_method, "verification method")
        require(record.id in items[record.claim_id].provenance.evidence_ids, "evidence must be linked back from its claim")
    allowed = {
        "constraints": {Status.OBSERVED, Status.UNCERTAIN},
        "observations": {Status.OBSERVED, Status.VERIFIED, Status.UNCERTAIN},
        "verified_facts": {Status.VERIFIED},
        "hypotheses": {Status.INFERRED, Status.UNCERTAIN},
        "rejected_hypotheses": {Status.FALSIFIED, Status.UNCERTAIN} if state.version == "0.1.1" else {Status.FALSIFIED},
        "actions": {Status.OBSERVED, Status.UNCERTAIN},
        "failed_attempts": {Status.OBSERVED, Status.UNCERTAIN},
        "changes": {Status.OBSERVED, Status.VERIFIED, Status.UNCERTAIN},
        "open_questions": {Status.UNCERTAIN},
        "uncertainties": {Status.UNCERTAIN},
        "current_plan": {Status.INFERRED, Status.UNCERTAIN},
        "next_actions": {Status.INFERRED, Status.UNCERTAIN},
        "goal": {Status.OBSERVED},
    }
    for category in ("goal",) + CATEGORY_NAMES:
        for item in ((state.goal,) if category == "goal" else getattr(state, category)):
            provenance = item.provenance
            require(provenance.epistemic_status in allowed[category], f"{category}: invalid epistemic status")
            nonempty(provenance.scope, "item scope")
            require(bool(provenance.source_ids), f"{item.id}: source required")
            require(len(set(provenance.source_ids)) == len(provenance.source_ids), "duplicate source reference")
            require(len(set(provenance.evidence_ids)) == len(provenance.evidence_ids), "duplicate evidence reference")
            require(set(provenance.source_ids) <= sources.keys(), f"{item.id}: dangling source")
            require(set(provenance.evidence_ids) <= evidence.keys(), f"{item.id}: dangling evidence")
            linked = [evidence[key] for key in provenance.evidence_ids]
            require(all(record.claim_id == item.id and record.scope == provenance.scope for record in linked), f"{item.id}: evidence claim/scope mismatch")
            for field in fields(item):
                value = getattr(item, field.name)
                if isinstance(value, str):
                    nonempty(value, f"{item.id}.{field.name}")
            if hasattr(item, "confidence"):
                require(0 <= item.confidence <= 1, "confidence outside [0, 1]")
            if category == "observations":
                timestamp(item.timestamp)
            if provenance.epistemic_status in (Status.VERIFIED, Status.FALSIFIED):
                verdict = Verdict.SUPPORTS if provenance.epistemic_status == Status.VERIFIED else Verdict.REFUTES
                require(any(record.verdict == verdict and sources[record.source_id].source_type in (SourceType.TOOL_RESULT, SourceType.FILE_SNAPSHOT) for record in linked), f"{item.id}: external verification/refutation evidence required")
                opposite = Verdict.REFUTES if verdict == Verdict.SUPPORTS else Verdict.SUPPORTS
                require(not any(record.verdict == opposite for record in linked), f"{item.id}: conflicting evidence requires uncertain/inferred status")
            if category == "hypotheses":
                for keys, verdict in ((item.supporting_evidence, Verdict.SUPPORTS), (item.contradicting_evidence, Verdict.REFUTES)):
                    require(set(keys) <= set(provenance.evidence_ids), "hypothesis evidence missing from provenance")
                    require(all(evidence[key].verdict == verdict for key in keys), "hypothesis evidence verdict mismatch")
            if category in ("failed_attempts", "rejected_hypotheses"):
                require(bool(item.retry_conditions), "scoped failure/rejection requires retry conditions")
                for condition in item.retry_conditions:
                    nonempty(condition, "retry condition")
            if category == "failed_attempts":
                require(item.outcome in (ActionOutcome.FAILURE, ActionOutcome.INCONCLUSIVE), "a successful attempt is not a failure")
                require(bool(linked), "failed/inconclusive attempt requires evidence")
                require(all(record.verdict == Verdict.INCONCLUSIVE for record in linked) if item.outcome == ActionOutcome.INCONCLUSIVE else any(record.verdict == Verdict.SUPPORTS for record in linked), "failure evidence must distinguish failure from inconclusive")
                require(any(sources[record.source_id].source_type in (SourceType.TOOL_RESULT, SourceType.FILE_SNAPSHOT) for record in linked), "failed/inconclusive attempt requires external evidence")


def merge_states(*states: KeishoState) -> KeishoState:
    """Merge exact stable-ID duplicates only; conflicting records fail closed.

    Statement similarity never licenses merging epistemic status, scope, or evidence.
    """
    require(bool(states), "at least one state required")
    for state in states:
        validate_state(state)
        require((state.version, state.trajectory_sha256, state.created_at, state.goal) == (states[0].version, states[0].trajectory_sha256, states[0].created_at, states[0].goal), "cannot merge different checkpoints/goals")
    merged = {}
    for category in ("sources", "evidence") + CATEGORY_NAMES:
        records = {}
        for state in states:
            for record in getattr(state, category):
                require(record.id not in records or records[record.id] == record, f"conflicting duplicate {record.id}")
                records.setdefault(record.id, record)
        merged[category] = tuple(records.values())
    result = replace(states[0], **merged)
    validate_state(result)
    return result
