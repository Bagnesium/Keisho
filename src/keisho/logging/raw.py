"""Exclusive artifact creation and sealed, hash-chained external events."""

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re

from keisho.core import canonical_json, digest, nonempty, require, timestamp

LOG_VERSION = "0.1.0"


class EventKind(str, Enum):
    USER_MESSAGE = "user_message"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_SNAPSHOT = "file_snapshot"
    ANNOTATION = "annotation"
    FINAL_ANSWER = "final_answer"


@dataclass(frozen=True)
class Event:
    id: str
    kind: EventKind
    actor: str
    timestamp: str
    payload_json: str
    parent_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        nonempty(self.id, "event ID")
        nonempty(self.actor, "event actor")
        require(isinstance(self.kind, EventKind), "invalid event kind")
        timestamp(self.timestamp)
        require(isinstance(json.loads(self.payload_json), dict), "event payload must be an object")
        require(canonical_json(json.loads(self.payload_json)) == self.payload_json, "payload must be canonical JSON")
        require(isinstance(self.parent_ids, tuple) and all(isinstance(key, str) and key for key in self.parent_ids), "invalid parent IDs")
        require(len(set(self.parent_ids)) == len(self.parent_ids), "duplicate parent IDs")


@dataclass(frozen=True)
class FrozenTrajectory:
    events: tuple[Event, ...]
    sha256: str

    @classmethod
    def create(cls, events: tuple[Event, ...]):
        known = set()
        for event in events:
            event.validate()
            require(event.id not in known, "duplicate trajectory event ID")
            require(set(event.parent_ids) <= known, "event parent must precede its child")
            known.add(event.id)
        return cls(events, digest(events))

    def validate(self) -> None:
        require(FrozenTrajectory.create(self.events).sha256 == self.sha256, "trajectory hash mismatch")


def _name(value: str) -> None:
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is not None, "unsafe artifact/run name")


def _exclusive_json(path: Path, value) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o444)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


class RawRun:
    """One writer per run. Existing artifacts are never overwritten through this API.

    Read-only files and hashes detect tampering; this is not an OS security boundary.
    Keep raw directories outside successor workspaces.
    """

    def __init__(self, root: Path, run_id: str):
        _name(run_id)
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / run_id
        self.path.mkdir(exist_ok=False)
        (self.path / "events").mkdir()

    def write_artifact(self, name: str, value) -> None:
        require(not getattr(self, "_read_only", False), "reopened run is read-only")
        _name(name)
        require(name.endswith(".json") and name != "trajectory.json", "artifact requires a .json name; trajectory is reserved")
        _exclusive_json(self.path / name, value)

    def append(self, event: Event) -> None:
        require(not getattr(self, "_read_only", False), "reopened run is read-only")
        require(not (self.path / "trajectory.json").exists(), "trajectory is sealed")
        events, previous = self._read_chain()
        event.validate()
        known = {item.id for item in events}
        require(event.id not in known and set(event.parent_ids) <= known, "invalid event ID/parents")
        record = {"version": LOG_VERSION, "sequence": len(events), "previous_sha256": previous, "event": json.loads(canonical_json(event))}
        record["sha256"] = digest(record)
        _exclusive_json(self.path / "events" / f"{len(events):08d}.json", record)

    def _read_chain(self) -> tuple[tuple[Event, ...], str | None]:
        from keisho.core import decode

        events, previous = [], None
        files = sorted((self.path / "events").iterdir())
        for index, path in enumerate(files):
            require(path.name == f"{index:08d}.json" and path.is_file() and not path.is_symlink(), "noncontiguous or unsafe event log")
            record = json.loads(path.read_text())
            require(set(record) == {"version", "sequence", "previous_sha256", "event", "sha256"}, "invalid event record fields")
            claimed = record.pop("sha256")
            require(record["version"] == LOG_VERSION and type(record["sequence"]) is int and record["sequence"] == index and record["previous_sha256"] == previous, "invalid event chain")
            require(digest(record) == claimed, "event hash mismatch")
            events.append(decode(Event, record["event"]))
            previous = claimed
        FrozenTrajectory.create(tuple(events))
        return tuple(events), previous

    def freeze(self) -> FrozenTrajectory:
        require(not getattr(self, "_read_only", False), "reopened run is read-only")
        events, last = self._read_chain()
        frozen = FrozenTrajectory.create(events)
        _exclusive_json(self.path / "trajectory.json", {"version": LOG_VERSION, "event_count": len(events), "last_event_sha256": last, "trajectory_sha256": frozen.sha256})
        return frozen

    def load_frozen(self) -> FrozenTrajectory:
        events, last = self._read_chain()
        frozen = FrozenTrajectory.create(events)
        seal = json.loads((self.path / "trajectory.json").read_text())
        require(seal == {"version": LOG_VERSION, "event_count": len(events), "last_event_sha256": last, "trajectory_sha256": frozen.sha256}, "trajectory seal mismatch")
        return frozen

    @classmethod
    def open_existing(cls, root: Path, run_id: str):
        """Reopen a persisted run for verified replay, without permitting writes."""
        _name(run_id)
        obj = cls.__new__(cls)
        obj.path = Path(root) / run_id
        require(obj.path.is_dir() and not obj.path.is_symlink(), "existing raw run missing or unsafe")
        require((obj.path / "events").is_dir() and not (obj.path / "events").is_symlink(), "existing event directory missing or unsafe")
        obj._read_only = True
        return obj
