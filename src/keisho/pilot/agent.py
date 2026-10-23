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
from .response_policy import STRICT, AUXILIARY, extract_action_json, parse_auxiliary, parse_unique_json, validate_recordable_json
from .action_wire import VERSION as ACTION_WIRE_VERSION, canonicalize_action, rejected_response


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


def parse_output(text: str, known_evidence_ids: set[str], policy=STRICT, action_wire_version=None) -> dict:
    require(policy in (STRICT, AUXILIARY), 'unsupported response policy')
    require(action_wire_version in (None, ACTION_WIRE_VERSION), 'unsupported action wire version')
    data, framing = extract_action_json(text)
    validate_recordable_json(data)
    if policy == AUXILIARY:
        return parse_auxiliary((data, framing), known_evidence_ids)
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
    data["framing"] = framing
    return data


def is_path_escape(action, reason=""):
    text = str(reason).lower()
    if "escape" in text or "unsafe repository path" in text or "unsafe listing prefix" in text:
        return True
    if isinstance(action, dict):
        for key in ("path", "prefix"):
            val = action.get(key)
            if isinstance(val, str):
                if val.startswith("/") or any(part == ".." for part in val.replace("\\", "/").split("/")):
                    return True
    return False


def run_agent(model: AgentModel, session: ToolSession, recorder: Recorder, task_text: str, system_prompt: str,
              handoff_text: str, seed: int, budgets: Budgets, role="successor", checkpoint_tools: int | None = None,
              checkpoint_predicate=None, time_limit_seconds: float | None = None, response_policy=STRICT,
              action_wire_version=None) -> AgentExecution:
    require(response_policy in (STRICT, AUXILIARY), 'unsupported response policy')
    require(action_wire_version in (None, ACTION_WIRE_VERSION), 'unsupported action wire version')
    if response_policy == AUXILIARY or action_wire_version is not None:
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
    consecutive_failures = 0
    reason = "budget_exhausted"
    def audit_admission(number, action, result, rejection_reason=None):
        if action_wire_version is not None:
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-admission.json',
                {'wire_version':action_wire_version, 'canonical_action':action,
                 'runtime_validation_result':result, 'tool_execution_completed':result=='completed',
                 'rejection_reason':rejection_reason})
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
            if action_wire_version is not None:
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-wire.json',
                    rejected_response('provider did not return an admitted model response', stage='generation'))
            reason = "model_failure"
            break
        parsing_started = False
        try:
            response.usage.validate()
            accepted_ids = getattr(model, "response_model_ids", lambda: (model.model_id(),))()
            require(response.resolved_model_id in accepted_ids, "model identity changed")
            require(response.usage.input_tokens is not None and response.usage.output_tokens is not None, "usage missing; cannot enforce token budget")
            require(response.usage.input_tokens <= upper and response.usage.output_tokens <= budgets.output_tokens, "provider usage exceeds declared request bound")
            consumed += response.usage.input_tokens + response.usage.output_tokens
            require(consumed <= budgets.total_tokens, "total token budget exceeded")
            require(response.finish_reason == "stop", "truncated/refused response")
            parsing_started = True
            parsed = parse_output(response.text, known, response_policy, action_wire_version)
        except (ValueError, TypeError) as exc:
            if action_wire_version is not None:
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-wire.json',
                    rejected_response(str(exc), text=response.text, stage='response' if parsing_started else 'generation'))
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-protocol-failure.json', {
                'exception_type': type(exc).__name__, 'reason': str(exc),
                'tool_executed': False, 'automatic_retry': False})
            reason = "model_failure"
            break
        messages.append(Message("assistant", response.text))
        if 'framing' in parsed:
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-stripped-framing.json', parsed['framing'])
        if response_policy == AUXILIARY:
            report = parsed['annotation_report']
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-annotations.json', report)
            recorder.emit(f'{role}_annotations_{number:03d}', EventKind.ANNOTATION, 'response-validator',
                          {'type': 'response_annotations', **report}, (call.response_event_id,))
        action = parsed["action"]
        if action_wire_version is not None:
            wire_report = canonicalize_action(action, session.validate_action)
            recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-wire.json', wire_report)
            if wire_report['validation_result'] != 'accepted':
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-failure.json',
                    {'reason':wire_report['rejection_reason'], 'tool_executed':False, 'automatic_retry':False})
                if is_path_escape(action, wire_report['rejection_reason']):
                    reason = 'invalid_run'
                    break
                if tools >= budgets.tool_calls:
                    audit_admission(number, action, 'not_executed', 'tool call budget exhausted')
                    break
                tools += 1
                tool_id, result_id = f"{role}_tool_{tools:03d}", f"{role}_result_{tools:03d}"
                recorder.emit(tool_id, EventKind.TOOL_CALL, role, {"action": action}, (call.response_event_id,))
                audit_admission(number, action, 'rejected', wire_report['rejection_reason'])
                result = {"error": wire_report['rejection_reason'], "invalid_action": wire_report['rejection_reason']}
                recorder.emit(result_id, EventKind.TOOL_RESULT, role, result, (tool_id,))
                known.add(result_id)
                messages.append(Message("user", canonical_json({"event_id": result_id, "tool_result": result})))
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    reason = "repeated_tool_failure"
                    break
                continue
            action = wire_report['canonical_action']
        if action.get("tool") == "finish":
            if set(action) != {"tool", "answer"} or not isinstance(action["answer"], str):
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-failure.json',
                    {'reason':'invalid finish action','tool_executed':False,'automatic_retry':False})
                reason = "model_failure"
            else:
                recorder.emit(f"{role}_final", EventKind.FINAL_ANSWER, role, {"answer": action["answer"]}, (call.response_event_id,))
                reason = "finished"
            break
        if response_policy == AUXILIARY and action_wire_version is None:
            try:
                session.validate_action(action)
            except InvalidAction as exc:
                recorder.raw.write_artifact(f'{role}_call_{number:03d}-action-failure.json',
                                           {'reason': str(exc), 'tool_executed': False, 'automatic_retry': False})
                if is_path_escape(action, str(exc)):
                    reason = 'invalid_run'
                    break
                if tools >= budgets.tool_calls:
                    audit_admission(number, action, 'not_executed', 'tool call budget exhausted')
                    break
                tools += 1
                tool_id, result_id = f"{role}_tool_{tools:03d}", f"{role}_result_{tools:03d}"
                recorder.emit(tool_id, EventKind.TOOL_CALL, role, {"action": action}, (call.response_event_id,))
                audit_admission(number, action, 'rejected', str(exc))
                result = {"error": str(exc), "invalid_action": str(exc)}
                recorder.emit(result_id, EventKind.TOOL_RESULT, role, result, (tool_id,))
                known.add(result_id)
                messages.append(Message("user", canonical_json({"event_id": result_id, "tool_result": result})))
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    reason = "repeated_tool_failure"
                    break
                continue
        if tools >= budgets.tool_calls:
            audit_admission(number, action, 'not_executed', 'tool call budget exhausted')
            break
        tools += 1
        tool_id, result_id = f"{role}_tool_{tools:03d}", f"{role}_result_{tools:03d}"
        recorder.emit(tool_id, EventKind.TOOL_CALL, role, {"action": action}, (call.response_event_id,))
        try:
            result = session.execute(action)
        except InvalidAction as exc:
            audit_admission(number, action, 'rejected', str(exc))
            if is_path_escape(action, str(exc)):
                recorder.emit(result_id, EventKind.TOOL_RESULT, role, {"invalid_action": str(exc)}, (tool_id,))
                reason = "invalid_run"
                break
            result = {"error": str(exc), "invalid_action": str(exc)}
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, result, (tool_id,))
            known.add(result_id)
            messages.append(Message("user", canonical_json({"event_id": result_id, "tool_result": result})))
            consecutive_failures += 1
            if consecutive_failures >= 3:
                reason = "repeated_tool_failure"
                break
            continue
        except IsolationUnavailable:
            audit_admission(number, action, 'infrastructure_failure', 'isolation unavailable; no completed tool result')
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {'infrastructure_failure':'isolation unavailable; no completed tool result'}, (tool_id,))
            reason = "infrastructure_failure"
            break
        except (OSError, ValueError) as exc:
            audit_admission(number, action, 'infrastructure_failure', type(exc).__name__)
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {"infrastructure_failure": type(exc).__name__}, (tool_id,))
            reason = "infrastructure_failure"
            break
        if not isinstance(result,dict):
            audit_admission(number, action, 'infrastructure_failure', 'missing or invalid tool result')
            recorder.emit(result_id, EventKind.TOOL_RESULT, role, {'infrastructure_failure':'missing or invalid tool result'}, (tool_id,))
            reason='infrastructure_failure'
            break
        audit_admission(number, action, 'completed')
        recorder.emit(result_id, EventKind.TOOL_RESULT, role, result, (tool_id,))
        known.add(result_id)
        messages.append(Message("user", canonical_json({"event_id": result_id, "tool_result": result})))
        if action.get("tool") in ("read_file", "write_file") and "error" in result:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                reason = "repeated_tool_failure"
                break
        elif action.get("tool") == "shell":
            consecutive_failures = 0
        else:
            consecutive_failures = 0
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
