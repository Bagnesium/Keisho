from dataclasses import dataclass
from dataclasses import fields
from enum import Enum
import json

from keisho.core import decode, nonempty, primitive, require, sha256, timestamp
from .conditions import Condition

MANIFEST_VERSION = "0.1.0"


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model_id: str
    parameters_json: str
    seed_supported: bool


@dataclass(frozen=True)
class PromptRef:
    role: str
    version: str
    sha256: str


@dataclass(frozen=True)
class Runtime:
    python: str
    platform: str
    code_revision: str | None
    source_tree_sha256: str
    dependency_lock_sha256: str
    environment_kind: str


@dataclass(frozen=True)
class RunManifest:
    version: str
    run_id: str
    block_id: str
    parent_run_id: str
    task_id: str
    task_version: str
    task_sha256: str
    original_task_sha256: str
    predecessor: ModelSpec
    successor: ModelSpec
    condition: Condition
    seed: int
    checkpoint_steps: int
    handoff_token_budget: int
    successor_step_budget: int
    created_at: str
    protocol_version: str
    state_version: str
    prompts: tuple[PromptRef, ...]
    trajectory_sha256: str
    environment_sha256: str
    state_sha256: str
    capsule_sha256: str
    config_sha256: str
    runtime: Runtime

    def validate(self) -> None:
        decode(RunManifest, primitive(self))
        require(self.version == MANIFEST_VERSION, "unsupported manifest version")
        for name in ("run_id", "block_id", "parent_run_id", "task_id", "task_version", "protocol_version", "state_version"):
            nonempty(getattr(self, name), name)
        for name in ("task_sha256", "original_task_sha256", "trajectory_sha256", "environment_sha256", "state_sha256", "capsule_sha256", "config_sha256"):
            sha256(getattr(self, name), name)
        timestamp(self.created_at)
        require(self.seed >= 0 and self.checkpoint_steps > 0 and self.handoff_token_budget > 0 and self.successor_step_budget > 0, "invalid seed/budgets/checkpoint")
        require(bool(self.prompts), "versioned prompts required")
        require(len({prompt.role for prompt in self.prompts}) == len(self.prompts), "duplicate prompt role")
        for prompt in self.prompts:
            nonempty(prompt.role, "prompt role")
            nonempty(prompt.version, "prompt version")
            sha256(prompt.sha256, "prompt hash")
        for model in (self.predecessor, self.successor):
            nonempty(model.provider, "provider")
            nonempty(model.model_id, "exact model ID")
            require(isinstance(json.loads(model.parameters_json), dict), "model parameters must be a JSON object")
        for name in ("python", "platform", "environment_kind"):
            nonempty(getattr(self.runtime, name), name)
        sha256(self.runtime.source_tree_sha256, "source tree hash")
        sha256(self.runtime.dependency_lock_sha256, "lock hash")


def validate_block(manifests: tuple[RunManifest, ...]) -> None:
    """Validate a complete four-condition assignment and all manifest invariants."""
    require(len(manifests) == len(Condition), "block requires exactly four branches")
    for manifest in manifests:
        manifest.validate()
    require({manifest.condition for manifest in manifests} == set(Condition), "condition missing or duplicated")
    require(len({manifest.run_id for manifest in manifests}) == len(manifests), "run IDs must be unique")
    allowed_differences = {"run_id", "condition", "capsule_sha256", "created_at"}
    for field in fields(RunManifest):
        if field.name not in allowed_differences:
            require(all(getattr(manifest, field.name) == getattr(manifests[0], field.name) for manifest in manifests), f"branch invariant differs: {field.name}")


class RunStatus(str, Enum):
    COMPLETE = "complete"
    TASK_FAILURE = "task_failure"
    MODEL_FAILURE = "model_failure"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    INVALID = "invalid"


@dataclass(frozen=True)
class RunOutcome:
    status: RunStatus
    task_success: bool | None
    reason: str
    grader_version: str

    def validate(self) -> None:
        decode(RunOutcome, primitive(self))
        nonempty(self.reason, "outcome reason")
        nonempty(self.grader_version, "grader version")
        expected = {RunStatus.COMPLETE: True, RunStatus.TASK_FAILURE: False}.get(self.status)
        require(self.task_success is expected, "infrastructure/model/invalid failures are unscored; task results must match status")
