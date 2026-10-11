"""Phase 0 extraction is strict ingestion of explicit, external annotations.

No heuristic converts prose into verified claims. The annotator's semantic
judgments remain auditable inputs, not validator-established truth.
"""

from keisho.core import decode, digest, require
from keisho.logging.raw import EventKind, FrozenTrajectory
from .provenance import SourceType
from .schema import KeishoState
from .validator import validate_state

SOURCE_KINDS = {
    SourceType.USER_MESSAGE: {EventKind.USER_MESSAGE},
    SourceType.MODEL_MESSAGE: {EventKind.MODEL_RESPONSE, EventKind.FINAL_ANSWER},
    SourceType.TOOL_CALL: {EventKind.TOOL_CALL},
    SourceType.TOOL_RESULT: {EventKind.TOOL_RESULT},
    SourceType.FILE_SNAPSHOT: {EventKind.FILE_SNAPSHOT},
    SourceType.ANNOTATION: {EventKind.ANNOTATION},
}


def extract_state(annotation: dict, trajectory: FrozenTrajectory) -> KeishoState:
    trajectory.validate()
    state = decode(KeishoState, annotation)
    validate_state(state)
    require(state.trajectory_sha256 == trajectory.sha256, "state derived from another trajectory")
    events = {event.id: event for event in trajectory.events}
    for source in state.sources:
        require(source.id in events, "source must identify an external trajectory event")
        event = events[source.id]
        require(source.location == f"events/{event.id}" and source.sha256 == digest(event), "source location/hash mismatch")
        require(event.kind in SOURCE_KINDS[source.source_type], "source type does not match observable event")
    return state
