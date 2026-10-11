from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from keisho.core import decode, nonempty, primitive, require


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class TokenCount:
    count: int
    method: str
    exact: bool

    def validate(self) -> None:
        decode(TokenCount, primitive(self))
        require(self.count >= 0, "negative token count")
        nonempty(self.method, "token counting method")


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[Message, ...]
    seed: int
    max_output_tokens: int
    temperature: float


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None = None
    cost_usd: str | None = None
    pricing_source: str | None = None

    def validate(self) -> None:
        decode(Usage, primitive(self))
        for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens):
            require(value is None or value >= 0, "negative usage")
        if self.cached_input_tokens is not None and self.input_tokens is not None:
            require(self.cached_input_tokens <= self.input_tokens, "cached tokens exceed input total")
        if self.cost_usd is not None:
            try:
                cost = Decimal(self.cost_usd)
            except InvalidOperation as exc:
                raise ValueError("invalid USD cost") from exc
            require(cost.is_finite() and cost >= 0, "invalid USD cost")
            require(self.pricing_source is not None, "priced usage requires a pricing source")
            nonempty(self.pricing_source, "pricing source")


@dataclass(frozen=True)
class ModelResponse:
    resolved_model_id: str
    text: str
    usage: Usage
    finish_reason: str


class AgentModel(ABC):
    """Providers own authentication, native message translation, and tokenization.

    Preserve exact resolved model IDs and raw responses. Unsupported seeds and
    non-exact token estimates must be disclosed by the adapter/run manifest.
    Experiments must not contain provider-specific SDK calls.
    """

    @abstractmethod
    def model_id(self) -> str:
        pass

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> TokenCount:
        """Count handoff text separately from whole-request provider usage."""
        pass
