from dataclasses import dataclass
import json
import time

from keisho.agents.base import AgentModel, Message, ModelRequest, Usage
from keisho.agents.providers.openai_chat import ProviderFailure
from keisho.core import canonical_json, digest, require, utc_now
from keisho.logging.raw import Event, EventKind, FrozenTrajectory, RawRun
from keisho.metrics.definitions import CallPurpose, CallRecord
from .sandbox import IsolationUnavailable
from .tools import InvalidAction, ToolSession
from .response_policy import STRICT, AUXILIARY, parse_auxiliary


class BudgetExceeded(ValueError):
    pass


@dataclass(frozen=True)
class Budgets:
    model_calls: int
    tool_calls: int
    output_tokens: int
    total_tokens: int
    request_input_tokens: int
    context_tokens: int


class Recorder:
    def __init__(self, raw: RawRun):
        self.raw, self.events = raw, []

    def emit(self, key, kind, actor, payload, parents=()):
        event = Event(key, kind, actor, utc_now(), canonical_json(payload), parents)
        self.raw.append(event)
        self.events.append(event)
        return event

    def trajectory(self):
        return FrozenTrajectory.create(tuple(self.events))


@dataclass(frozen=True)
class AgentExecution:
    reason: str
    model_calls: int
    tool_calls: int
    calls: tuple[CallRecord, ...]
    elapsed_seconds: float


def request_upper_bound(model: AgentModel, request: ModelRequest) -> int:
    # Native text plus any opt-in response schema and conservative framing.
    # Provider usage is checked against this reserve afterward.
    counts = [model.count_tokens(message.content) for message in request.messages]
    for count in counts:
        count.validate()
        require(count.exact, "native tokenizer required")
    return sum(count.count for count in counts) + getattr(model, 'request_extra_tokens', lambda: 0)() + 1024 + 16 * len(counts)


def logged_generate(model: AgentModel, request: ModelRequest, recorder: Recorder, actor: str, purpose: CallPurpose, number: int):
    call_id = f"{actor}_call_{number:03d}"
    request_id, response_id = f"{actor}_request_{number:03d}", f"{actor}_response_{number:03d}"
    recorder.raw.write_artifact(f"{call_id}-request.json", request)
    recorder.emit(request_id, EventKind.MODEL_REQUEST, actor, {"call_id": call_id, "request_artifact": f"{call_id}-request.json", "request_sha256": digest(request), "model_id": model.model_id()})
    start = time.monotonic()
    try:
        response = model.generate(request)
    except ProviderFailure as exc:
        record = CallRecord(call_id, purpose, model.model_id(), request_id, None, time.monotonic() - start, Usage(None, None))
        recorder.raw.write_artifact(f"{call_id}-failure.json", {"reason": str(exc), "status": exc.status, "request_id": exc.request_id, "retry": False})
        if exc.raw_response_json is not None:
            recorder.raw.write_artifact(f"{call_id}-invalid-response.json", json.loads(exc.raw_response_json))
        return None, record
    record = CallRecord(call_id, purpose, response.resolved_model_id, request_id, response_id, time.monotonic() - start, response.usage)
    recorder.raw.write_artifact(f"{call_id}-response.json", response)
    recorder.emit(response_id, EventKind.MODEL_RESPONSE, actor, {"text": response.text, "model_id": response.resolved_model_id, "finish_reason": response.finish_reason}, (request_id,))
    return response, record


def parse_output(text: str, known_evidence_ids: set[str], policy=STRICT) -> dict:
    require(policy in (STRICT, AUXILIARY), 'unsupported response policy')
    if policy == AUXILIARY:
        return parse_auxiliary(text, known_evidence_ids)
    data = json.loads(text)
    require(isinstance(data, dict) and set(data) == {"action", "claims"}, "response must contain action and claims only")
    require(isinstance(data["action"], dict) and isinstance(data["claims"], list), "invalid action/claims types")
    require(len(data["claims"]) <= 8, "too many claims")
    for claim in data["claims"]:
        require(isinstance(claim, dict) and set(claim) == {"statement", "status", "evidence_ids", "basis"}, "invalid claim fields")
        require(isinstance(claim["statement"], str) and 0 < len(claim["statement"]) <= 2000, "invalid claim statement")
        require(claim["status"] in ("OBSERVED", "VERIFIED", "INFERRED", "UNCERTAIN", "FALSIFIED"), "invalid claimed status")
        require(claim["basis"] in ("tool", "predecessor", "independent"), "invalid claim basis")
        require(isinstance(claim["evidence_ids"], list) and all(isinstance(key, str) for key in claim["evidence_ids"]), "invalid claim evidence")
        require(set(claim["evidence_ids"]) <= known_evidence_ids, "claim cites unavailable tool evidence")
    return data


def run_agent(model: AgentModel, session: ToolSession, recorder: Recorder, task_text: str, system_prompt: str,
              handoff_text: str, seed: int, budgets: Budgets, role="successor", checkpoint_tools: int | None = None,
              checkpoint_predicate=None, time_limit_seconds: float | None = None, response_policy=STRICT) -> AgentExecution:
    require(response_policy in (STRICT, AUXILIARY), 'unsupported response policy')
    if response_policy == AUXILIARY:
        require(callable(getattr(session, 'validate_action', None)), 'amended policy requires independent action validator')
    start = time.monotonic()
    purpose = CallPurpose.PREDECESSOR if role == "predecessor" else CallPurpose.SUCCESSOR
    messages = [Message("system", system_prompt), Message("user", task_text), Message("user", handoff_text)]
    recorder.emit(f"{role}_system", EventKind.USER_MESSAGE, "system", {"role": "system", "content": system_prompt})
    recorder.emit(f"{role}_task", EventKind.USER_MESSAGE, "user", {"role": "user", "content": task_text})
    if response_policy == AUXILIARY:
        recorder.emit(f'{role}_response_policy', EventKind.ANNOTATION, 'response-validator',
                      {'type': 'response_policy', 'version': response_policy})
    # Empty handoff message is invariant framing for NO_CONTEXT, not history.
    if handoff_text:
        recorder.emit(f"{role}_handoff", EventKind.USER_MESSAGE, "user", {"content": handoff_text})
    calls, tools, consumed, known = [], 0, 0, set()
    reason = "budget_exhausted"
    for number in range(1, budgets.model_calls + 1):
        if time_limit_seconds is not None and time.monotonic() - start >= time_limit_seconds:
            reason = "time_budget_exhausted"
            break
        request = ModelRequest(tuple(messages), seed, budgets.output_tokens, 0.0)
        upper = request_upper_bound(model, request)
        if upper > budgets.request_input_tokens or upper + budgets.output_tokens > budgets.context_tokens or consumed + upper + budgets.output_tokens > budgets.total_tokens:
            break
        response, call = logged_generate(model, request, recorder, role, purpose, number)
        calls.append(call)
        if response is None:
            reason = "model_failure"
            break
        try:
            response.usage.validate()
            accepted_ids = getattr(model, "response_model_ids", lambda: (model.model_id(),))()
            require(response.resolved_model_id in accepted_ids, "model identity changed")
            require(response.usage.input_tokens is not None and response.usage.output_tokens is not None, "usage missing; cannot enforce token budget")
            require(response.usage.input_tokens <= upper and response.usage.output_tokens <= budgets.output_tokens, "provider usage exceeds declared request bound")
            consumed += response.usage.input_tokens + response.usage.output_tokens
            require(consumed <= budgets.total_tokens, "total token budget exceeded")
            require(response.finish_reason == "stop", "truncated/refused response")
            parsed = parse_output(response.text, known, response_policy)
        except (ValueError, TypeError) as exc:
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-protocol-failure.json', {
                'exception_type': type(exc).__name__, 'reason': str(exc),
                'tool_executed': False, 'automatic_retry': False})
            reason = "model_failure"
            break
        messages.append(Message("assistant", response.text))
        if response_policy == AUXILIARY:
            report = parsed['annotation_report']
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-annotations.json', report)
            recorder.emit(f'{role}_annotations_{number:03d}', EventKind.ANNOTATION, 'response-validator',
                          {'type': 'response_annotations', **report}, (call.response_event_id,))
        action = parsed["action"]
        if action.get("tool") == "finish":
            if set(action) != {"tool", "answer"} or not isinstance(action["answer"], str):
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-failure.json',
                    {'reason':'invalid finish action','tool_executed':False,'automatic_retry':False})
                reason = "model_failure"
            else:
                recorder.emit(f"{role}_final", EventKind.FINAL_ANSWER, role, {"answer": action["answer"]}, (call.response_event_id,))
                reason = "finished"
            break
        if response_policy == AUXILIARY:
            try:
                session.validate_action(action)
            except InvalidAction as exc:
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-failure.json',
                                           {'reason': str(exc), 'tool_executed': False, 'automatic_retry': False})
                reason = 'invalid_run'
                break
        if tools >= budgets.tool_calls:
            break
        tools += 1
        tool_id, result_id = f"{role}_tool_{tools:03d}", f"{role}_result_{tools:03d}"
        recorder.emit(tool_id, EventKind.TOOL_CALL, role, {"action": action}, (call.response_event_id,))
        try:
            result = session.execute(action)
        except InvalidAction as exc:
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {"invalid_action": str(exc)}, (tool_id,))
            reason = "invalid_run"
            break
        except IsolationUnavailable:
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {'infrastructure_failure':'isolation unavailable; no completed tool result'}, (tool_id,))
            reason = "infrastructure_failure"
            break
        except (OSError, ValueError) as exc:
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {"infrastructure_failure": type(exc).__name__}, (tool_id,))
            reason = "infrastructure_failure"
            break
        if not isinstance(result,dict):
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {'infrastructure_failure':'missing or invalid tool result'}, (tool_id,))
            reason='infrastructure_failure'
            break
        recorder.emit(result_id, EventKind.TOOL_RESULT, role, result, (tool_id,))
        known.add(result_id)
        messages.append(Message("user", canonical_json({"event_id": result_id, "tool_result": result})))
        if checkpoint_predicate is not None and checkpoint_predicate(action, result):
            reason = "checkpoint"
            break
        if checkpoint_tools is not None and tools == checkpoint_tools:
            reason = "checkpoint"
            break
        if role == "successor" and action == {"tool": "run_tests", "test_ids": ["full"]} and all(item["passed"] for item in result["results"]):
            reason = "public_tests_passed"
            break
    return AgentExecution(reason, len(calls), tools, tuple(calls), time.monotonic() - start)
