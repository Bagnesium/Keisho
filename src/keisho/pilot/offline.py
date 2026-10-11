"""Explicit synthetic actors for calibration/plumbing, never empirical agents.

Fixtures deliberately consult gold to construct known cases. Production models,
summary generation, state construction and tool sessions do not import this path.
"""

from keisho.agents.base import AgentModel, ModelResponse, TokenCount, Usage
from keisho.core import canonical_json
from keisho.experiments.conditions import Condition
from .tasks import load_gold, load_public


def exposed(action, statement=None, status="INFERRED", basis="independent", evidence=()):
    return canonical_json({"action": action, "claims": [] if statement is None else [{"statement": statement, "status": status, "evidence_ids": list(evidence), "basis": basis}]})


class FixtureModel(AgentModel):
    def __init__(self, identity: str, responses: tuple[str, ...]):
        self.identity, self.responses, self.requests = identity, iter(responses), []

    def model_id(self):
        return self.identity

    def count_tokens(self, text):
        return TokenCount(len(text.split()), "offline/whitespace-fixture-v1", True)

    def generate(self, request):
        self.requests.append(request)
        try:
            text = next(self.responses)
        except StopIteration:
            from keisho.agents.providers.openai_chat import ProviderFailure
            raise ProviderFailure("synthetic response sequence exhausted") from None
        return ModelResponse(self.identity, text, Usage(sum(self.count_tokens(message.content).count for message in request.messages), self.count_tokens(text).count, 0, "0", "explicit synthetic fixture"), "stop")


def predecessor_responses(task_id: str) -> tuple[str, ...]:
    gold = load_gold(task_id)
    task = load_public(task_id)
    calibration = gold["calibration"]
    false = next(item["statement"] for item in gold["hypotheses"] if item["truth"] is False)
    reads = calibration["read_paths"]
    responses = [exposed({"tool": "list_files"}, false), exposed({"tool": "run_tests", "test_ids": ["full"]}),
                 exposed({"tool": "read_file", "path": reads[0]}), exposed({"tool": "read_file", "path": reads[1]}),
                 exposed({"tool": "run_tests", "test_ids": [calibration["probe"]]}, false)]
    if "wrong_patch_path" in calibration:
        path = calibration["wrong_patch_path"]
        responses += [exposed({"tool": "write_file", "path": path, "content": calibration["wrong_patch_content"]}),
                      exposed({"tool": "run_tests", "test_ids": ["full"]}),
                      exposed({"tool": "write_file", "path": path, "content": task.files[path]}),
                      exposed({"tool": "read_file", "path": reads[2]}, false, "FALSIFIED", "tool", ("predecessor_result_005", "predecessor_result_007"))]
    else:
        responses += [exposed({"tool": "read_file", "path": reads[2]}),
                      exposed({"tool": "run_tests", "test_ids": [calibration["failed_probe"]]}),
                      exposed({"tool": "read_file", "path": reads[3]}),
                      exposed({"tool": "run_tests", "test_ids": ["nonempty_metadata"]}, false, "FALSIFIED", "tool", ("predecessor_result_005", "predecessor_result_007"))]
    return tuple(responses)


def factory(role: str, task_id: str, condition: Condition | None):
    gold, task = load_gold(task_id), load_public(task_id)
    false = next(item["statement"] for item in gold["hypotheses"] if item["truth"] is False)
    if role == "predecessor":
        return FixtureModel("offline/predecessor-sequence/1", predecessor_responses(task_id))
    if role == "summary":
        return FixtureModel("offline/predecessor-sequence/1", (f"Synthetic free-form summary: investigated public tests. The predecessor hypothesized: {false} A probe and failed approach left the task unresolved. This is a fixture, not an LLM summary.",))
    target = gold["repeated_failure_targets"][0]
    responses = [exposed({"tool": "run_tests", "test_ids": [gold["facts"][0]["test_id"]]})]
    if "patch_path" in target:
        repeated = {"tool": "write_file", "path": target["patch_path"], "content": target["patch_content"]}
    else:
        repeated = {"tool": "run_tests", "test_ids": target["test_ids"]}
    responses.append(exposed(repeated, false, "VERIFIED", "independent" if condition == Condition.NO_CONTEXT else "predecessor"))
    if "patch_path" in target:
        responses.append(exposed({"tool": "write_file", "path": target["patch_path"], "content": task.files[target["patch_path"]]}))
    responses.extend(exposed({"tool": "write_file", "path": path, "content": content}) for path, content in gold["correct_fix"].items())
    responses.append(exposed({"tool": "run_tests", "test_ids": ["full"]}))
    return FixtureModel("offline/successor-sequence/1", tuple(responses))


def openrouter_factory(role, task_id, condition):
    """Same explicit fixtures through an injected, entirely offline router transport."""
    from types import SimpleNamespace
    from keisho.agents.providers.openrouter_chat import MODEL_ALIASES, OpenRouterChatModel
    fixture = factory(role, task_id, condition)
    identity = tuple(MODEL_ALIASES)[1 if role == "successor" else 0]
    def transport(body, _key):
        text = next(fixture.responses)
        return {"model": identity, "provider": "OpenAI", "id": "synthetic-openrouter",
                "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": sum(len(message["content"].split()) for message in body["messages"]),
                          "completion_tokens": len(text.split()), "cost": 0, "is_byok": False}}, None
    return OpenRouterChatModel(identity, authorized=True, api_key="synthetic-offline-key", transport=transport,
                               tokenizer=SimpleNamespace(count=fixture.count_tokens), mode="summary" if role == "summary" else "agent")
