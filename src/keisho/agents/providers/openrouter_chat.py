"""Restricted OpenRouter transport; frozen exact response IDs or fail closed."""

from dataclasses import dataclass
from decimal import Decimal
from functools import partial

from keisho.agents.base import Usage
from keisho.core import canonical_json, require
from .openai_chat import NativeResponse, OpenAIChatModel, http_transport

BASE_URL = "https://openrouter.ai/api/v1"
# Canonical IDs and public aliases actually exposed by the 2026-10-04 catalog.
MODEL_ALIASES = {
    "openai/gpt-4.1-mini-2025-04-14": "openai/gpt-4.1-mini",
    "openai/gpt-4.1-2025-04-14": "openai/gpt-4.1",
}
MODEL_PRICES = {
    "openai/gpt-4.1-mini-2025-04-14": (Decimal("0.40"), Decimal("0.10"), Decimal("1.60")),
    "openai/gpt-4.1-2025-04-14": (Decimal("2.00"), Decimal("0.50"), Decimal("8.00")),
}
PRICING_SOURCE = "https://openrouter.ai/api/v1/models;https://openrouter.ai/docs/cookbook/administration/usage-accounting;https://openrouter.ai/docs/guides/overview/auth/byok (checked 2026-10-04)"
RESERVATION_MULTIPLIER = Decimal("1.05")  # Possible 5% BYOK fee, no free allowance assumed.
transport = partial(http_transport, base_url=BASE_URL, provider="OpenRouter")


def validate_catalog(catalog):
    for canonical, alias in MODEL_ALIASES.items():
        model = next(row for row in catalog["models"] if row["id"] == alias)
        require(model["canonical_slug"] == canonical, "catalog snapshot mapping changed")
        endpoints = catalog["endpoints"][alias]["data"]["endpoints"]
        selected = [row for row in endpoints if row["tag"] == "openai" and row["provider_name"] == "OpenAI"]
        require(len(selected) == 1, "exact OpenAI endpoint missing or ambiguous")
        endpoint = selected[0]
        require(endpoint["name"] == "OpenAI | " + canonical, "catalog upstream model mapping changed")
        require({"max_tokens", "seed", "temperature", "response_format"} <= set(endpoint["supported_parameters"]), "required parameters unsupported")
        require(endpoint["context_length"] >= 128000 and endpoint["max_completion_tokens"] >= 2048, "catalog request limits below frozen budgets")
        inputs, cached, outputs = MODEL_PRICES[canonical]
        price = endpoint["pricing"]
        require(Decimal(price["prompt"]) * 1_000_000 == inputs and Decimal(price["completion"]) * 1_000_000 == outputs and Decimal(price["input_cache_read"]) * 1_000_000 == cached, "catalog pricing differs from reserved prices")
        require(Decimal(price.get("request", "0")) == 0, "unreserved per-request cost")


def routing(model_id):
    rate_in, _, rate_out = MODEL_PRICES[model_id]
    return {"only": ["openai"], "order": ["openai"], "allow_fallbacks": False,
            "require_parameters": True,
            "max_price": {"prompt": float(rate_in), "completion": float(rate_out), "request": 0}}


@dataclass(frozen=True)
class OpenRouterResponse(NativeResponse):
    requested_model_id: str
    upstream_provider: str
    request_body_json: str
    is_byok: bool | None
    upstream_inference_cost_usd: str | None
    snapshot_attestation: str | None


class OpenRouterChatModel(OpenAIChatModel):
    prices = MODEL_PRICES
    key_variable = "OPENROUTER_API_KEY"
    provider = "openrouter"

    def __init__(self, model_id, *, authorized=False, api_key=None, transport=transport, tokenizer=None, mode="agent", response_model_ids=None, agent_response_format=None):
        super().__init__(model_id, authorized=authorized, api_key=api_key, transport=transport, tokenizer=tokenizer, mode=mode, agent_response_format=agent_response_format)
        allowed = (model_id,) if response_model_ids is None else tuple(response_model_ids)
        require(allowed in ((model_id,), (MODEL_ALIASES[model_id], model_id)), "only the exact catalog-confirmed same-model pair is allowed")
        self._response_model_ids = allowed

    def response_model_ids(self):
        return self._response_model_ids

    def body(self, message):
        body = super().body(message)
        body["model"] = MODEL_ALIASES[self._id]
        body["max_tokens"] = body.pop("max_completion_tokens")  # OpenAI endpoint catalog advertises this parameter.
        body.pop("store")  # Not a supported upstream parameter in this catalog.
        body.pop("service_tier")
        body.update(provider=routing(self._id), stream=False, plugins=[])
        return body  # One model only; no models array, auto router, presets or tools.

    def validate_routing(self, data):
        require(data.get("provider") == "OpenAI", "missing or disallowed upstream provider")
        require(not data["choices"][0]["message"].get("tool_calls"), "unexpected native tool execution")
        require(not ((data.get("usage") or {}).get("server_tool_use_details") or {}).get("tool_calls_executed"), "unexpected server tool charge")

    def parse_usage(self, raw):
        cost = raw.get("cost")
        is_byok = raw.get("is_byok")
        if type(is_byok) is not bool:
            cost = None  # Unknown billing route cannot establish the total charge.
        if cost is not None:
            cost = Decimal(str(cost))
            require(cost.is_finite() and cost >= 0, "invalid OpenRouter cost")
            if is_byok:
                upstream = (raw.get("cost_details") or {}).get("upstream_inference_cost")
                if upstream is None:
                    cost = None
                else:
                    upstream = Decimal(str(upstream))
                    require(upstream.is_finite() and upstream >= 0, "invalid BYOK upstream cost")
                    cost += upstream  # Router credit debit plus externally billed inference.
        return Usage(raw.get("prompt_tokens"), raw.get("completion_tokens"),
                     (raw.get("prompt_tokens_details") or {}).get("cached_tokens"),
                     str(cost) if cost is not None else None, PRICING_SOURCE if cost is not None else None)

    def native_response(self, data, body, *fields):
        raw = data.get("usage") or {}
        upstream = (raw.get("cost_details") or {}).get("upstream_inference_cost")
        return OpenRouterResponse(*fields, body["model"], data["provider"], canonical_json(body),
                                  raw.get("is_byok"), str(upstream) if upstream is not None else None, None)
