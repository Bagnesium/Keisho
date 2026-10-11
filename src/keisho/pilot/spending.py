"""One shared calibration ledger; admission precedes transport, never retries."""

from decimal import Decimal
import json

from keisho.agents.base import AgentModel
from keisho.agents.providers.openai_chat import MODEL_PRICES, ProviderFailure
from keisho.agents.providers import openrouter_chat
from keisho.core import digest, require
from .agent import request_upper_bound


class SpendLedger:
    def __init__(self, cap_usd, emit=lambda _: None, *, provider="openai", authorized_ceiling_usd="1.25", authorization_scope="calibration"):
        self.cap = Decimal(cap_usd)
        ceiling = Decimal(authorized_ceiling_usd)
        if authorization_scope == "swebench-one-comparison":
            require(ceiling == Decimal('10') and provider == 'openrouter', 'unregistered benchmark authorization')
        elif authorization_scope == 'agent-decision-diagnostic':
            require(ceiling == Decimal('2') and provider == 'openrouter', 'unregistered decision diagnostic authorization')
        else:
            require(authorization_scope == 'calibration' and ceiling in (Decimal("1.25"), Decimal("1.35")) and (ceiling == Decimal("1.25") or provider == "openrouter"), "unregistered calibration authorization")
        require(self.cap.is_finite() and 0 < self.cap <= ceiling, "calibration dollar cap exceeds authorized ceiling")
        self.emit, self.records = emit, []
        self.accounted, self.held = Decimal(0), Decimal(0)
        self.stopped, self.reason = False, None
        require(provider in ("openai", "openrouter"), "unregistered spending provider")
        self.provider = provider
        self.prices = openrouter_chat.MODEL_PRICES if provider == "openrouter" else MODEL_PRICES
        self.multiplier = openrouter_chat.RESERVATION_MULTIPLIER if provider == "openrouter" else Decimal(1)

    def stop(self, reason):
        self.stopped, self.reason = True, reason

    def reserve(self, stage, model_id, input_cap, output_cap, text_bound, request_sha256=None, *, api_metadata=None):
        if self.stopped:
            raise ProviderFailure("shared calibration spending control already stopped")
        require(0 < text_bound <= input_cap <= 32000 and 0 < output_cap <= 2048, "request exceeds reserved token bounds")
        rate_in, _, rate_out = self.prices[model_id]
        maximum = self.multiplier * (input_cap * rate_in + output_cap * rate_out) / Decimal(1_000_000)
        if self.accounted + self.held + maximum > self.cap:
            self.stop("insufficient remaining dollars for full request reservation")
            self.emit({"type": "admission_denied", "stage": stage, "model_id": model_id,
                       "reservation_usd": str(maximum), "transmitted": False})
            raise ProviderFailure("request not transmitted: insufficient shared dollar budget")
        record = {"number": len(self.records) + 1, "stage": stage, "requested_model_id": model_id,
                  "reserved_input_tokens": input_cap, "native_text_plus_framing_estimate": text_bound,
                  "reserved_output_tokens": output_cap, "reservation_usd": str(maximum),
                  "status": "reserved", "cache_discount_assumed": False}
        record.update(provider=self.provider, reservation_multiplier=str(self.multiplier))
        if api_metadata:
            record.update(api_metadata)
        record["request_sha256"] = request_sha256
        self.held += maximum
        self.records.append(record)
        self.emit(dict(record))  # Durable reservation before the network operation.
        return record

    def settle(self, record, response):
        usage = response.usage
        try:
            usage.validate()
            require(usage.input_tokens is not None and usage.output_tokens is not None, "usage unknown")
            require(usage.input_tokens <= record["reserved_input_tokens"] and usage.output_tokens <= record["reserved_output_tokens"], "usage exceeds reservation")
            rate_in, _, rate_out = self.prices[record["requested_model_id"]]
            accounted = (usage.input_tokens * rate_in + usage.output_tokens * rate_out) / Decimal(1_000_000)
            if self.provider == "openrouter":
                require(usage.cost_usd is not None, "OpenRouter total API cost unknown")
                require(type(getattr(response, "is_byok", None)) is bool, "OpenRouter billing route unknown")
                accounted = max(accounted * (self.multiplier if response.is_byok else Decimal(1)), Decimal(usage.cost_usd))
                require(accounted <= Decimal(record["reservation_usd"]), "OpenRouter cost exceeds reservation")
        except (ValueError, TypeError):
            self.unknown(record, "usage/cost unknown or outside reserved bounds", response)
            return
        self.held -= Decimal(record["reservation_usd"])
        self.accounted += accounted
        record.update(status="settled", returned_model_id=response.resolved_model_id,
                      input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                      noncached_accounted_usd=str(accounted), provider_cost_usd=usage.cost_usd)
        if self.provider == "openrouter":
            record.update(upstream_provider=response.upstream_provider, is_byok=response.is_byok,
                          upstream_inference_cost_usd=response.upstream_inference_cost_usd,
                          openrouter_credit_cost_usd=str((json.loads(response.raw_response_json).get('usage') or {}).get('cost')),
                          system_fingerprint=response.system_fingerprint)
        self.emit(dict(record))

    def unknown(self, record, reason, response=None):
        record.update(status="unreconciled", provider_cost_usd=None)
        if response is not None:
            record.update(returned_model_id=response.resolved_model_id,
                          input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens,
                          reported_cost_usd=response.usage.cost_usd)
        self.stop(reason)  # Keep the entire reservation held; never assume free.
        self.emit(dict(record))

    def report(self):
        return {"cap_usd": str(self.cap), "noncached_accounted_usd": str(self.accounted),
                "unreconciled_reservations_usd": str(self.held), "stopped": self.stopped,
                "stop_reason": self.reason, "attempts": self.records,
                "provider": self.provider,
                "accounting": "greater of noncached price ceiling and returned total API cost; OpenRouter BYOK includes upstream billing and possible 5% fee; unknown attempts retain reservations"}


class BudgetedModel(AgentModel):
    def __init__(self, model, ledger, stage, pricing_model_id, input_cap=32000):
        self.model, self.ledger, self.stage = model, ledger, stage
        self.pricing_model_id, self.input_cap = pricing_model_id, input_cap

    def model_id(self):
        return self.model.model_id()

    def count_tokens(self, text):
        return self.model.count_tokens(text)

    def request_extra_tokens(self):
        return getattr(self.model, 'request_extra_tokens', lambda: 0)()

    def response_model_ids(self):
        return getattr(self.model, "response_model_ids", lambda: (self.model.model_id(),))()

    def generate(self, request):
        metadata = None
        if getattr(self.model, "provider", None) == "openrouter":
            body = self.model.body(request)
            metadata = {"api_request_model_id": body["model"], "routing": body["provider"], "api_request_sha256": digest(body),
                        "accepted_response_model_ids": list(self.response_model_ids())}
        reservation = self.ledger.reserve(self.stage, self.pricing_model_id, self.input_cap,
                                          request.max_output_tokens, request_upper_bound(self, request), digest(request), api_metadata=metadata)
        try:
            response = self.model.generate(request)
        except Exception:
            self.ledger.unknown(reservation, "provider attempt failed; usage unavailable")
            raise
        self.ledger.settle(reservation, response)
        if self.ledger.stopped and self.ledger.provider == "openrouter":
            # Stop before unaccounted output becomes another prompt/tool action.
            raise ProviderFailure(self.ledger.reason, raw_response_json=getattr(response, "raw_response_json", None))
        return response
