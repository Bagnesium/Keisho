"""Minimal first provider adapter. No automatic retries, SDKs, or secret logs."""

from dataclasses import dataclass
from decimal import Decimal
import json
import os
import ssl
import time
from urllib import error, request

from keisho.agents.base import AgentModel, ModelRequest, ModelResponse, Usage
from keisho.core import ValidationError, canonical_json, decode, primitive, require
from keisho.local_env import redact_credentials
from keisho.pilot.tokenizer import NativeTokenizer

MODEL_PRICES = {
    "gpt-4.1-mini-2025-04-14": (Decimal("0.40"), Decimal("0.10"), Decimal("1.60")),
    "gpt-4.1-2025-04-14": (Decimal("2.00"), Decimal("0.50"), Decimal("8.00")),
}
PRICING_SOURCE = "https://developers.openai.com/api/docs/models/gpt-4.1;https://developers.openai.com/api/docs/models/gpt-4.1-mini (checked 2026-10-03; default service tier)"


class ProviderFailure(RuntimeError):
    def __init__(self, reason: str, *, status: int | None = None, request_id: str | None = None, raw_response_json: str | None = None):
        super().__init__(reason)
        self.status, self.request_id = status, request_id
        self.raw_response_json = raw_response_json


@dataclass(frozen=True)
class NativeResponse(ModelResponse):
    provider: str
    request_id: str | None
    latency_seconds: float
    tool_calls_json: str
    raw_response_json: str
    system_fingerprint: str | None


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None  # Never forward credentials to another endpoint.


def verified_opener(ca_file=None):
    handlers = [NoRedirect()]
    if ca_file is not None:
        context = ssl.create_default_context(cafile=str(ca_file))
        require(context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED, "verified HTTPS required")
        handlers.append(request.HTTPSHandler(context=context))
    return request.build_opener(*handlers)


def http_transport(body: dict, api_key: str, *, base_url="https://api.openai.com/v1", provider="OpenAI", ca_file=None, response_observer=None) -> tuple[dict, str | None]:
    require(base_url in ("https://api.openai.com/v1", "https://openrouter.ai/api/v1"), "unregistered provider endpoint")
    if base_url == "https://api.openai.com/v1":
        require(not api_key.startswith("sk-or-") and api_key != os.environ.get("OPENROUTER_API_KEY"), "OpenRouter credential cannot be used at the direct OpenAI endpoint")
    message = request.Request(base_url + "/chat/completions", data=canonical_json(body).encode(),
                              headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    def observe(payload, status):
        if response_observer is not None:
            # Capture before JSON decoding, routing/usage validation and action
            # parsing. Only credential redaction changes the archived bytes.
            saved = payload
            for secret in {api_key, *(os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"))}:
                if secret:
                    saved = saved.replace(secret.encode(), b"[REDACTED_API_KEY]")
            response_observer(saved, status, saved != payload)
    try:
        with verified_opener(ca_file).open(message, timeout=60) as response:
            payload = response.read()
            observe(payload, getattr(response, 'status', 200))
            return json.loads(payload), response.headers.get("x-request-id")
    except error.HTTPError as exc:
        try:
            if response_observer is not None:
                observe(exc.read(), exc.code)
        finally:
            exc.close()
        # Do not log response bodies or exception strings that may echo credentials.
        identifier = exc.headers.get("x-request-id")
        raise ProviderFailure(f"{provider} HTTP failure; no retry performed", status=exc.code, request_id=redact_credentials(identifier, api_key) if identifier else None) from None
    except (OSError, ValueError) as exc:
        raise ProviderFailure(f"{provider} transport failure ({type(exc).__name__}); no retry performed") from None


class OpenAIChatModel(AgentModel):
    prices = MODEL_PRICES
    key_variable = "OPENAI_API_KEY"
    provider = "openai"

    def __init__(self, model_id: str, *, authorized: bool = False, api_key: str | None = None, transport=http_transport, tokenizer=None, mode="agent", agent_response_format=None):
        require(model_id in self.prices, "only registered exact model snapshots are supported")
        require(mode in ("agent", "summary", "state"), "unknown request mode")
        self._id, self._authorized, self._key = model_id, authorized, api_key
        self._transport, self._tokenizer, self._mode = transport, tokenizer, mode
        require(agent_response_format is None or mode == 'agent', 'agent schema cannot change note generation')
        self._agent_response_format = agent_response_format

    def model_id(self) -> str:
        return self._id

    def response_model_ids(self) -> tuple[str, ...]:
        return (self._id,)

    def accepts_response_model(self, returned: str) -> bool:
        return returned in self.response_model_ids()

    def count_tokens(self, text):
        if self._tokenizer is None:
            self._tokenizer = NativeTokenizer()
        return self._tokenizer.count(text)

    def body(self, message: ModelRequest) -> dict:
        decode(ModelRequest, primitive(message))
        require(message.max_output_tokens > 0 and message.seed >= 0 and 0 <= message.temperature <= 2, "invalid request parameters")
        body = {"model": self._id, "messages": primitive(message.messages), "seed": message.seed,
                "temperature": message.temperature, "max_completion_tokens": message.max_output_tokens,
                "store": False, "service_tier": "default"}
        if self._mode != "summary":
            body["response_format"] = self._agent_response_format or {"type": "json_object"}
        return body

    def request_extra_tokens(self):
        if self._agent_response_format is None:
            return 0
        count = self.count_tokens(canonical_json(self._agent_response_format))
        count.validate()
        require(count.exact, 'native schema token count required')
        return count.count

    def generate(self, message: ModelRequest) -> NativeResponse:
        if not self._authorized:
            raise ProviderFailure("paid execution is gated; explicit live approval required")
        key = self._key or os.environ.get(self.key_variable)
        if not key:
            raise ProviderFailure(f"{self.key_variable} is not configured")
        if self.provider == "openai" and (key.startswith("sk-or-") or key == os.environ.get("OPENROUTER_API_KEY")):
            raise ProviderFailure("OpenRouter credential cannot be used for direct OpenAI; no request made")
        body, start = self.body(message), time.monotonic()
        data, request_id = self._transport(body, key)
        elapsed = time.monotonic() - start
        data = json.loads(redact_credentials(canonical_json(data), key))
        request_id = redact_credentials(request_id, key) if request_id else None
        try:
            require(self.accepts_response_model(data["model"]), "resolved model differs from registered snapshot/allowlist")
            self.validate_routing(data)
            require(len(data["choices"]) == 1, "exactly one model choice required")
            choice = data["choices"][0]
            native = choice["message"]
            text = native.get("content")
            require(isinstance(text, str), "missing model text or refusal")
            usage = self.parse_usage(data.get("usage") or {})
            usage.validate()
            return self.native_response(data, body, data["model"], text, usage, choice["finish_reason"], self.provider, request_id,
                                  elapsed, canonical_json(native.get("tool_calls") or []), canonical_json(data), data.get("system_fingerprint"))
        except ValidationError as exc:
            raise ProviderFailure(str(exc), request_id=request_id, raw_response_json=canonical_json(data)) from None
        except (KeyError, IndexError, TypeError, ValueError, AttributeError, ArithmeticError):
            raise ProviderFailure("malformed/mismatched provider response; no retry performed", request_id=request_id, raw_response_json=canonical_json(data)) from None

    def validate_routing(self, data):
        pass

    def native_response(self, data, body, *fields):
        return NativeResponse(*fields)

    def parse_usage(self, raw_usage):
        inputs, outputs = raw_usage.get("prompt_tokens"), raw_usage.get("completion_tokens")
        cached = (raw_usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        cost = None
        if inputs is not None and outputs is not None and cached is not None:
            price_input, price_cached, price_output = self.prices[self._id]
            cost = str(((inputs - cached) * price_input + cached * price_cached + outputs * price_output) / Decimal(1_000_000))
        return Usage(inputs, outputs, cached, cost, PRICING_SOURCE if cost is not None else None)
