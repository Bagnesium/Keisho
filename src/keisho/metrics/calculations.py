from decimal import Decimal
import math

from keisho.core import decode, nonempty, primitive, require, text_digest
from keisho.experiments.conditions import HandoffCapsule
from keisho.experiments.manifest import RunOutcome
from keisho.logging.raw import EventKind, FrozenTrajectory
from .definitions import Accounting, BehaviorMetric, CallPurpose, CallRecord, MetricAnnotation, MetricReport, Rate


def _sum_known(values):
    return None if any(value is None for value in values) else sum(values)


def calculate_metrics(trajectory: FrozenTrajectory, outcome: RunOutcome, capsule: HandoffCapsule, annotations: tuple[MetricAnnotation, ...], calls: tuple[CallRecord, ...], branch_elapsed_seconds: float, known_reference_ids: frozenset[str], complete_call_purposes: frozenset[CallPurpose] = frozenset()) -> MetricReport:
    """Aggregate explicit scoring records; never classify behavior from prose.

    Each annotation is one adjudicated opportunity for one metric. Supply all
    eligible opportunities, including negatives; missing annotations are not
    evidence of zero errors. Scorer scope judgments must be reviewed separately.
    """
    trajectory.validate()
    outcome.validate()
    require(all(isinstance(purpose, CallPurpose) for purpose in complete_call_purposes), "invalid accounting coverage stage")
    decode(HandoffCapsule, primitive(capsule))
    require(capsule.sha256 == text_digest(capsule.text), "capsule hash mismatch")
    capsule.tokens.validate()
    require(type(branch_elapsed_seconds) in (float, int) and math.isfinite(branch_elapsed_seconds) and branch_elapsed_seconds >= 0, "invalid branch elapsed time")
    events = {event.id: event for event in trajectory.events}
    eligible_kinds = {
        BehaviorMetric.REDISCOVERY: {EventKind.TOOL_CALL},
        BehaviorMetric.REPEATED_FAILURE: {EventKind.TOOL_CALL},
        BehaviorMetric.INHERITED_ERROR: {EventKind.MODEL_RESPONSE, EventKind.FINAL_ANSWER},
        BehaviorMetric.CONTRADICTION: {EventKind.MODEL_RESPONSE, EventKind.FINAL_ANSWER},
    }
    seen = set()
    for annotation in annotations:
        decode(MetricAnnotation, primitive(annotation))
        key = (annotation.metric, annotation.event_id)
        require(key not in seen, "duplicate metric opportunity")
        seen.add(key)
        require(annotation.event_id in events and events[annotation.event_id].actor == "successor", "annotation must target a successor event")
        require(events[annotation.event_id].kind in eligible_kinds[annotation.metric], "event kind is not an eligible metric opportunity")
        require(set(annotation.reference_ids) <= known_reference_ids, "unknown predecessor knowledge/evidence reference")
        require(not annotation.positive or bool(annotation.reference_ids), "positive behavior label requires predecessor reference")
        for value in (annotation.scope, annotation.rationale, annotation.adjudicator, annotation.rubric_version):
            nonempty(value, "annotation metadata")
    call_ids, request_ids, response_ids = set(), set(), set()
    for call in calls:
        decode(CallRecord, primitive(call))
        call.usage.validate()
        nonempty(call.id, "call ID")
        nonempty(call.model_id, "exact model ID")
        nonempty(call.request_event_id, "call request ID")
        require(call.id not in call_ids, "duplicate call ID")
        call_ids.add(call.id)
        require(call.elapsed_seconds >= 0, "negative call duration")
        if call.purpose == CallPurpose.SUCCESSOR:
            require(call.request_event_id not in request_ids, "duplicate successor request record")
            request_ids.add(call.request_event_id)
            require(call.request_event_id in events and events[call.request_event_id].kind == EventKind.MODEL_REQUEST and events[call.request_event_id].actor == "successor", "missing successor request event")
            if call.response_event_id is not None:
                require(call.response_event_id not in response_ids, "duplicate successor response record")
                response_ids.add(call.response_event_id)
                require(call.response_event_id in events and events[call.response_event_id].kind == EventKind.MODEL_RESPONSE and events[call.response_event_id].actor == "successor" and call.request_event_id in events[call.response_event_id].parent_ids, "missing or mismatched successor response event")
    require(request_ids == {event.id for event in trajectory.events if event.kind == EventKind.MODEL_REQUEST and event.actor == "successor"}, "every successor request needs a raw call record, including failures")
    require(response_ids == {event.id for event in trajectory.events if event.kind == EventKind.MODEL_RESPONSE and event.actor == "successor"}, "every successor response needs a linked raw call record")
    rates = {}
    for metric in BehaviorMetric:
        records = [item for item in annotations if item.metric == metric]
        numerator, denominator = sum(item.positive for item in records), len(records)
        rates[metric.value] = Rate(numerator, denominator, numerator / denominator if denominator else None)
    accounting = []
    for purpose in CallPurpose:
        records = [call for call in calls if call.purpose == purpose]
        costs = [Decimal(call.usage.cost_usd) if call.usage.cost_usd is not None else None for call in records]
        complete = purpose == CallPurpose.SUCCESSOR or purpose in complete_call_purposes
        total_cost = _sum_known(costs) if complete else None
        accounting.append(Accounting(purpose, complete, len(records), _sum_known([call.usage.input_tokens for call in records]) if complete else None, _sum_known([call.usage.output_tokens for call in records]) if complete else None, str(total_cost) if total_cost is not None else None, sum(call.elapsed_seconds for call in records)))
    steps = sum(event.actor == "successor" and event.kind in (EventKind.TOOL_CALL, EventKind.FINAL_ANSWER) for event in trajectory.events)
    return MetricReport("0.1.0", outcome.task_success, outcome.status.value, capsule.tokens, steps, **rates, branch_elapsed_seconds=float(branch_elapsed_seconds), accounting=tuple(accounting), annotations=annotations, calls=calls)
