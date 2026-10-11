from dataclasses import dataclass
from pathlib import Path

from keisho.agents.base import AgentModel
from keisho.core import primitive, require
from keisho.environments.base import Snapshot
from keisho.environments.filesystem import FilesystemEnvironment
from keisho.logging.raw import FrozenTrajectory
from keisho.state.extractor import extract_state
from keisho.state.schema import KeishoState
from .conditions import Condition, HandoffCapsule, build_capsule


@dataclass(frozen=True)
class Branch:
    condition: Condition
    environment: FilesystemEnvironment
    capsule: HandoffCapsule
    environment_sha256: str


def prepare_branches(parent: FilesystemEnvironment, snapshot: Snapshot, trajectory: FrozenTrajectory, state: KeishoState, summary: str, successor: AgentModel, handoff_token_budget: int, root: Path) -> tuple[Branch, ...]:
    """Prepare all four branches from one frozen checkpoint, without running agents.

    This guarantees filesystem copies, not hostile-agent process isolation.
    A separate runner must enforce sibling/raw-log access restrictions in Phase 1.
    """
    snapshot.validate()
    require(parent.snapshot() == snapshot, "parent differs from the handoff checkpoint")
    extract_state(primitive(state), trajectory)
    capsules = tuple(build_capsule(condition, trajectory, state, summary, successor, handoff_token_budget) for condition in Condition)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    branches = tuple(Branch(capsule.condition, parent.fork(root / capsule.condition.value, snapshot), capsule, snapshot.sha256) for capsule in capsules)
    require(parent.snapshot() == snapshot, "branch preparation changed parent")
    return branches
