from keisho.core import canonical_json, digest, primitive
from keisho.logging.raw import Event, EventKind, FrozenTrajectory
from keisho.state.provenance import Evidence, EpistemicStatus as Status, Provenance, Source, SourceType, Verdict
from keisho.state.schema import ActionOutcome, FailedAttempt, Goal, GoalStatus, Hypothesis, KeishoState, RejectedHypothesis, VerifiedFact

STAMP = "2026-10-03T12:00:00+00:00"
SCOPE = "configuration X at frozen checkpoint"


def event(key, kind=EventKind.TOOL_RESULT, actor="predecessor", payload=None, parents=()):
    return Event(key, kind, actor, STAMP, canonical_json(payload or {"text": key}), parents)


def fixture():
    events = (
        event("user_01", EventKind.USER_MESSAGE, "user", {"text": "Fix authentication while preserving the API."}),
        event("tool_01", payload={"text": "Regression: missing metadata fails; database initialization passes."}),
        event("model_01", EventKind.MODEL_RESPONSE, payload={"text": "I suspect the database is causing authentication failures."}),
        event("tool_02", payload={"text": "Changing database initialization does not fix the regression."}),
    )
    trajectory = FrozenTrajectory.create(events)
    kinds = (SourceType.USER_MESSAGE, SourceType.TOOL_RESULT, SourceType.MODEL_MESSAGE, SourceType.TOOL_RESULT)
    sources = tuple(Source(item.id, kind, f"events/{item.id}", digest(item)) for item, kind in zip(events, kinds))
    evidence = (
        Evidence("ev_fact", "tool_01", "fact_01", "Regression test confirms the missing-metadata case.", Verdict.SUPPORTS, SCOPE, "deterministic regression test"),
        Evidence("ev_reject", "tool_02", "rejected_01", "The database change does not fix the failure.", Verdict.REFUTES, SCOPE, "controlled database initialization intervention"),
        Evidence("ev_failure", "tool_02", "failure_01", "The attempted database fix failed.", Verdict.SUPPORTS, SCOPE, "regression test after the change"),
    )
    def provenance(status, source, ev=()):
        return Provenance(status, (source,), ev, SCOPE)
    state = KeishoState(
        version="0.1.0", trajectory_sha256=trajectory.sha256, created_at=STAMP,
        goal=Goal(id="goal_01", provenance=provenance(Status.OBSERVED, "user_01"), description="Fix authentication", status=GoalStatus.ACTIVE),
        sources=sources, evidence=evidence,
        verified_facts=(VerifiedFact(id="fact_01", provenance=provenance(Status.VERIFIED, "tool_01", ("ev_fact",)), statement="The missing-metadata regression fails."),),
        hypotheses=(Hypothesis(id="hypothesis_01", provenance=provenance(Status.INFERRED, "model_01"), statement="The database causes authentication failures.", confidence=0.8, supporting_evidence=(), contradicting_evidence=()),),
        rejected_hypotheses=(RejectedHypothesis(id="rejected_01", provenance=provenance(Status.FALSIFIED, "tool_02", ("ev_reject",)), statement="Changing database initialization fixes the regression.", reason="Regression still fails under configuration X.", retry_conditions=("Revisit if relevant database configuration changes.",)),),
        failed_attempts=(FailedAttempt(id="failure_01", provenance=provenance(Status.OBSERVED, "tool_02", ("ev_failure",)), attempt="Change database initialization", failure="Regression still fails", outcome=ActionOutcome.FAILURE, retry_conditions=("Revisit if relevant configuration changes.",)),),
    )
    return trajectory, state


def annotation():
    return primitive(fixture()[1])
