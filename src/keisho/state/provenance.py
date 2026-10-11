from dataclasses import dataclass
from enum import Enum


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNCERTAIN = "UNCERTAIN"
    FALSIFIED = "FALSIFIED"


class SourceType(str, Enum):
    USER_MESSAGE = "user_message"
    MODEL_MESSAGE = "model_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_SNAPSHOT = "file_snapshot"
    ANNOTATION = "annotation"


class Verdict(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Source:
    id: str
    source_type: SourceType
    location: str
    sha256: str


@dataclass(frozen=True)
class Evidence:
    id: str
    source_id: str
    claim_id: str
    description: str
    verdict: Verdict
    scope: str
    verification_method: str


@dataclass(frozen=True)
class Provenance:
    epistemic_status: EpistemicStatus
    source_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    scope: str
