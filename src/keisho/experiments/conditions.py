from dataclasses import dataclass
from enum import Enum

from keisho.agents.base import AgentModel, TokenCount
from keisho.compiler.fixed import compile_fixed
from keisho.core import ValidationError, canonical_json, require, text_digest
from keisho.logging.raw import FrozenTrajectory
from keisho.state.schema import KeishoState


class Condition(str, Enum):
    NO_CONTEXT = "NO_CONTEXT"
    FULL_HISTORY = "FULL_HISTORY"
    SUMMARY = "SUMMARY"
    FIXED_STATE = "FIXED_STATE"


class HandoffBudgetExceeded(ValidationError):
    pass


@dataclass(frozen=True)
class HandoffCapsule:
    version: str
    condition: Condition
    text: str
    sha256: str
    tokens: TokenCount


def build_capsule(condition: Condition, trajectory: FrozenTrajectory, state: KeishoState, summary: str, model: AgentModel, token_budget: int) -> HandoffCapsule:
    trajectory.validate()
    require(isinstance(condition, Condition), "unknown handoff condition")
    require(type(token_budget) is int and token_budget > 0, "invalid handoff budget")
    require(state.trajectory_sha256 == trajectory.sha256, "state/checkpoint mismatch")
    require(isinstance(summary, str) and summary.strip(), "summary must be supplied, not fabricated")
    text = {
        Condition.NO_CONTEXT: "",
        Condition.FULL_HISTORY: canonical_json(trajectory.events),
        Condition.SUMMARY: summary,
        Condition.FIXED_STATE: compile_fixed(state),
    }[condition]
    tokens = model.count_tokens(text)
    tokens.validate()
    require(tokens.exact, "exact model tokenizer required to enforce handoff budget")
    if tokens.count > token_budget:
        raise HandoffBudgetExceeded(f"{condition.value} needs {tokens.count} handoff tokens, budget {token_budget}; no truncation applied")
    return HandoffCapsule("0.1.0", condition, text, text_digest(text), tokens)
