from dataclasses import dataclass
import json
from pathlib import Path

from keisho.core import digest, require
from keisho.experiments.conditions import Condition
from .agent import Budgets
from .tasks import TASK_IDS


@dataclass(frozen=True)
class PilotConfig:
    data: dict
    sha256: str

    @classmethod
    def load(cls, path: Path):
        # Deliberately support the JSON-compatible subset of YAML, no extra parser.
        data = json.loads(path.read_text())
        require(data["version"] == "1.0.0" and data["protocol_version"] == "0.1.0+phase1.1.0.0", "unsupported pilot protocol")
        require(tuple(data["tasks"]) == TASK_IDS, "exactly the three registered tasks required")
        require(data["conditions"] == [condition.value for condition in Condition], "exactly four baseline conditions required")
        require(data["repetitions"] == 3 and data["seeds"] == [17, 29, 43] and data["max_successor_branches"] == 36, "pilot cannot expand beyond three repetitions/36 branches")
        require(data["predecessor"]["model_id"] == "gpt-4.1-mini-2025-04-14" and data["successor"]["model_id"] == "gpt-4.1-2025-04-14", "model snapshots differ from registered pilot")
        require(data["paid_calls_authorized"] is False and data["successor_conditioning"] is False, "configuration must retain explicit live gate and four baselines")
        for role in ("predecessor", "successor"):
            require(data[role]["provider"] == "openai", "registered provider differs")
            budgets = Budgets(**data[role]["budgets"])
            require(all(type(value) is int and value > 0 for value in budgets.__dict__.values()), "invalid agent budget")
            require(budgets.model_calls <= (9 if role == "predecessor" else 14) and budgets.tool_calls <= (9 if role == "predecessor" else 12), "registered call budgets cannot be increased")
            require(budgets.output_tokens <= 2048 and budgets.total_tokens <= 60000 and budgets.request_input_tokens <= 32000 and budgets.context_tokens <= 128000, "registered token budgets cannot be increased")
        require(all(type(data[key]) is int and data[key] > 0 for key in ("handoff_token_budget", "summary_output_tokens")), "invalid handoff/summary budget")
        require(data["handoff_token_budget"] <= 24000 and data["summary_output_tokens"] <= 1024, "handoff/summary budget increased")
        return cls(data, digest(data))

    def budgets(self, role: str) -> Budgets:
        return Budgets(**self.data[role]["budgets"])
