from dataclasses import dataclass
from enum import Enum

from keisho.agents.base import TokenCount, Usage


class BehaviorMetric(str, Enum):
    REDISCOVERY = "rediscovery"
    REPEATED_FAILURE = "repeated_failure"
    INHERITED_ERROR = "inherited_error"
    CONTRADICTION = "contradiction"


@dataclass(frozen=True)
class MetricAnnotation:
    metric: BehaviorMetric
    event_id: str
    positive: bool
    reference_ids: tuple[str, ...]
    scope: str
    rationale: str
    adjudicator: str
    rubric_version: str


class CallPurpose(str, Enum):
    PREDECESSOR = "predecessor"
    SUCCESSOR = "successor"
    EXTRACTION = "extraction"
    SUMMARY = "summary"


@dataclass(frozen=True)
class CallRecord:
    id: str
    purpose: CallPurpose
    model_id: str
    request_event_id: str
    response_event_id: str | None
    elapsed_seconds: float
    usage: Usage


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int
    value: float | None


@dataclass(frozen=True)
class Accounting:
    purpose: CallPurpose
    coverage_complete: bool
    model_calls: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: str | None
    model_elapsed_seconds: float


@dataclass(frozen=True)
class MetricReport:
    version: str
    task_success: bool | None
    run_status: str
    handoff_tokens: TokenCount
    post_handoff_steps: int
    rediscovery: Rate
    repeated_failure: Rate
    inherited_error: Rate
    contradiction: Rate
    branch_elapsed_seconds: float
    accounting: tuple[Accounting, ...]
    annotations: tuple[MetricAnnotation, ...]
    calls: tuple[CallRecord, ...]
