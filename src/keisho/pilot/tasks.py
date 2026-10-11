from dataclasses import dataclass
import json
from pathlib import Path

from keisho.core import digest, require

TASK_IDS = ("task_001", "task_002", "task_003")
REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class PublicTask:
    id: str
    version: str
    description: str
    files: dict[str, str]
    editable_files: tuple[str, ...]
    cases: tuple[dict, ...]
    sha256: str


def load_public(task_id: str, root: Path = REPO / "tasks") -> PublicTask:
    require(task_id in TASK_IDS, "only the three registered tasks are supported")
    path = root / task_id
    public = json.loads((path / "public.json").read_text())
    files = {file.relative_to(path / "initial").as_posix(): file.read_text() for file in sorted((path / "initial").rglob("*")) if file.is_file()}
    require(public["task_id"] == task_id and len({case["id"] for case in public["cases"]}) == len(public["cases"]), "invalid public task")
    require(set(public["editable_files"]) <= files.keys(), "editable source missing")
    return PublicTask(task_id, public["version"], public["description"], files, tuple(public["editable_files"]), tuple(public["cases"]), digest({"public": public, "files": files}))


def load_gold(task_id: str, root: Path = REPO / "tasks") -> dict:
    """Evaluator only. Never hand this object to models, tools or the extractor."""
    require(task_id in TASK_IDS, "unknown gold task")
    return json.loads((root / task_id / "gold.json").read_text())
