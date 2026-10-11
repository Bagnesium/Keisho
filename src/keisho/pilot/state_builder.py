"""Gold-blind deterministic projection of visible tests, actions and claims."""

import json

from keisho.core import canonical_json, digest, primitive, require
from keisho.logging.raw import EventKind, FrozenTrajectory
from keisho.state.extractor import extract_state
from keisho.state.provenance import Evidence, EpistemicStatus as Status, Provenance, Source, SourceType, Verdict
from keisho.state.schema import Action, ActionOutcome, Change, FailedAttempt, Goal, GoalStatus, Hypothesis, KeishoState, Observation, RejectedHypothesis, VerifiedFact

BUILDER_VERSION = "gold-blind-projection/1.0.0"


def build_state(trajectory: FrozenTrajectory, task_description: str) -> KeishoState:
    sources, evidence, observations, facts, hypotheses, rejected, actions, failures, changes = [], [], [], [], [], [], [], [], []
    kinds = {EventKind.USER_MESSAGE: SourceType.USER_MESSAGE, EventKind.MODEL_RESPONSE: SourceType.MODEL_MESSAGE,
             EventKind.TOOL_CALL: SourceType.TOOL_CALL, EventKind.TOOL_RESULT: SourceType.TOOL_RESULT,
             EventKind.FILE_SNAPSHOT: SourceType.FILE_SNAPSHOT, EventKind.FINAL_ANSWER: SourceType.MODEL_MESSAGE}
    task_event = next(item for item in trajectory.events if item.id.endswith("_task"))
    require(json.loads(task_event.payload_json).get("content") == task_description,
            "state goal must equal the original task recorded in the frozen trajectory")
    for event in trajectory.events:
        if event.kind in kinds:
            sources.append(Source(event.id, kinds[event.kind], f"events/{event.id}", digest(event)))
    scope = "frozen task checkpoint; relevant changes require reverification"
    for event in trajectory.events:
        payload = json.loads(event.payload_json)
        if event.kind == EventKind.MODEL_RESPONSE:
            try:
                exposed = json.loads(payload["text"])
            except (KeyError, ValueError):
                continue
            for index, claim in enumerate(exposed.get("claims", [])):
                claim_id = f"claim_{event.id}_{index}"
                # A model's declared certainty is not verification. Preserve the
                # original declaration in text and raw source; never promote it.
                source_ids = (event.id,)
                linked_evidence = []
                for citation_index, cited in enumerate(claim["evidence_ids"]):
                    evidence_id = f"citation_{event.id}_{index}_{citation_index}"
                    evidence.append(Evidence(evidence_id, cited, claim_id, "Predecessor cited this tool result; semantic support/refutation is unverified", Verdict.INCONCLUSIVE, scope, "explicit external claim citation"))
                    linked_evidence.append(evidence_id)
                declared = claim["status"]
                statement = claim["statement"]
                if declared == "FALSIFIED":
                    rejected.append(RejectedHypothesis(id=claim_id, statement=statement, reason="Predecessor-declared rejection; semantic refutation is unverified", retry_conditions=("Revisit if scope changes or new supporting evidence appears",), provenance=Provenance(Status.UNCERTAIN, source_ids, tuple(linked_evidence), scope)))
                else:
                    hypotheses.append(Hypothesis(id=claim_id, statement=f"[{declared} asserted by predecessor; not independently verified] {statement}", confidence=0.5, supporting_evidence=(), contradicting_evidence=(), provenance=Provenance(Status.INFERRED if declared == "INFERRED" else Status.UNCERTAIN, source_ids, tuple(linked_evidence), scope)))
        if event.kind != EventKind.TOOL_RESULT or "action" not in payload:
            continue
        snapshot_scope = canonical_json(payload["source_hashes_after"])
        action_id = f"action_{event.id}"
        test_results = payload.get("results", [])
        failed = bool(test_results) and any(not item["passed"] for item in test_results)
        actions.append(Action(id=action_id, description=canonical_json(payload["action"]), result=canonical_json({key: value for key, value in payload.items() if key not in ("action", "source_hashes_before", "source_hashes_after")}), outcome=ActionOutcome.FAILURE if failed else ActionOutcome.SUCCESS, provenance=Provenance(Status.OBSERVED, (event.id,), (), snapshot_scope)))
        if payload["action"]["tool"] == "write_file":
            changes.append(Change(id=f"change_{event.id}", target=payload["path"], change=f"Wrote source with SHA-256 {payload['content_sha256']}", reason="Predecessor executed the recorded write action; intent remains in exposed claims", provenance=Provenance(Status.OBSERVED, (event.id,), (), snapshot_scope)))
        for index, result in enumerate(test_results):
            item_id, evidence_id = f"test_fact_{event.id}_{index}", f"test_evidence_{event.id}_{index}"
            statement = f"Public test {result['id']!r} returned passed={result['passed']} on the recorded source hashes."
            evidence.append(Evidence(evidence_id, event.id, item_id, statement, Verdict.SUPPORTS, snapshot_scope, "host comparison of isolated function output against immutable public case"))
            facts.append(VerifiedFact(id=item_id, statement=statement, provenance=Provenance(Status.VERIFIED, (event.id,), (evidence_id,), snapshot_scope)))
        if failed:
            item_id, evidence_id = f"failed_{event.id}", f"failed_evidence_{event.id}"
            evidence.append(Evidence(evidence_id, event.id, item_id, "Visible test failures were returned", Verdict.SUPPORTS, snapshot_scope, "isolated public case results"))
            failures.append(FailedAttempt(id=item_id, attempt=canonical_json(payload["action"]), failure="One or more public tests failed; this alone does not identify a root cause", outcome=ActionOutcome.FAILURE, retry_conditions=("Relevant code changes or new evidence justify another run",), provenance=Provenance(Status.OBSERVED, (event.id,), (evidence_id,), snapshot_scope)))
        if payload["action"]["tool"] == "read_file":
            observations.append(Observation(id=f"observed_{event.id}", statement=f"Read {payload['path']}; content SHA-256 {digest(payload['content'])}", timestamp=event.timestamp, provenance=Provenance(Status.OBSERVED, (event.id,), (), snapshot_scope)))
    state = KeishoState(version="0.1.1", trajectory_sha256=trajectory.sha256, created_at=trajectory.events[-1].timestamp,
                        goal=Goal(id="goal", description=task_description, status=GoalStatus.ACTIVE, provenance=Provenance(Status.OBSERVED, (task_event.id,), (), scope)),
                        sources=tuple(sources), evidence=tuple(evidence), observations=tuple(observations), verified_facts=tuple(facts),
                        hypotheses=tuple(hypotheses), rejected_hypotheses=tuple(rejected), actions=tuple(actions), failed_attempts=tuple(failures), changes=tuple(changes))
    return extract_state(primitive(state), trajectory)
