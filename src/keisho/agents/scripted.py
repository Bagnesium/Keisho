"""A deterministic test double, not an LLM or a behavioral baseline."""

from keisho.core import decode, primitive, require
from .base import AgentModel, ModelRequest, ModelResponse, TokenCount, Usage


class ScriptedModel(AgentModel):
    def __init__(self, responses: tuple[str, ...] = ()):
        self._responses = iter(responses)
        self.requests: list[ModelRequest] = []

    def model_id(self) -> str:
        return "offline/scripted-whitespace-v1"

    def count_tokens(self, text: str) -> TokenCount:
        # This tokenizer is exact only for this synthetic model identity.
        return TokenCount(len(text.split()), "scripted-whitespace-v1", True)

    def generate(self, request: ModelRequest) -> ModelResponse:
        decode(ModelRequest, primitive(request))
        require(request.max_output_tokens > 0 and request.temperature >= 0, "invalid generation parameters")
        self.requests.append(request)
        text = next(self._responses)
        require(self.count_tokens(text).count <= request.max_output_tokens, "script exceeds output budget")
        inputs = sum(self.count_tokens(message.content).count for message in request.messages)
        return ModelResponse(self.model_id(), text, Usage(inputs, self.count_tokens(text).count, 0, "0", "offline scripted test double"), "stop")
