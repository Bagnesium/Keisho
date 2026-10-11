"""Atomic, model-agnostic state. Empty categories remain explicit."""

from dataclasses import dataclass, fields
from enum import Enum

from .provenance import Evidence, Provenance, Source

STATE_VERSION = "0.1.1"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETE = "complete"
    PAUSED = "paused"


class ConstraintKind(str, Enum):
    REQUIREMENT = "requirement"
    PREFERENCE = "preference"


class ActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"


class Importance(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, kw_only=True)
class StateItem:
    id: str
    provenance: Provenance


@dataclass(frozen=True, kw_only=True)
class Goal(StateItem):
    description: str
    status: GoalStatus


@dataclass(frozen=True, kw_only=True)
class Constraint(StateItem):
    statement: str
    kind: ConstraintKind
    confidence: float


@dataclass(frozen=True, kw_only=True)
class Observation(StateItem):
    statement: str
    timestamp: str


@dataclass(frozen=True, kw_only=True)
class VerifiedFact(StateItem):
    statement: str


@dataclass(frozen=True, kw_only=True)
class Hypothesis(StateItem):
    statement: str
    confidence: float
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class RejectedHypothesis(StateItem):
    statement: str
    reason: str
    retry_conditions: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class Action(StateItem):
    description: str
    result: str
    outcome: ActionOutcome


@dataclass(frozen=True, kw_only=True)
class FailedAttempt(StateItem):
    attempt: str
    failure: str
    outcome: ActionOutcome
    retry_conditions: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class Change(StateItem):
    target: str
    change: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class OpenQuestion(StateItem):
    question: str
    importance: Importance


@dataclass(frozen=True, kw_only=True)
class Uncertainty(StateItem):
    statement: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class PlanStep(StateItem):
    step: str


@dataclass(frozen=True, kw_only=True)
class NextAction(StateItem):
    action: str
    rationale: str


@dataclass(frozen=True, kw_only=True)
class KeishoState:
    version: str
    trajectory_sha256: str
    created_at: str
    goal: Goal
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    observations: tuple[Observation, ...] = ()
    verified_facts: tuple[VerifiedFact, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    rejected_hypotheses: tuple[RejectedHypothesis, ...] = ()
    actions: tuple[Action, ...] = ()
    failed_attempts: tuple[FailedAttempt, ...] = ()
    changes: tuple[Change, ...] = ()
    open_questions: tuple[OpenQuestion, ...] = ()
    uncertainties: tuple[Uncertainty, ...] = ()
    current_plan: tuple[PlanStep, ...] = ()
    next_actions: tuple[NextAction, ...] = ()

    def items(self) -> tuple[StateItem, ...]:
        return (self.goal,) + tuple(item for name in CATEGORY_NAMES for item in getattr(self, name))


CATEGORY_NAMES = tuple(field.name for field in fields(KeishoState) if field.name not in {
    "version", "trajectory_sha256", "created_at", "goal", "sources", "evidence"
})
