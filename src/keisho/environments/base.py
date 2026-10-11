from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from pathlib import PurePosixPath

from keisho.core import decode, digest, nonempty, primitive, require


def safe_relative_path(value: str) -> None:
    nonempty(value, "snapshot path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and all(part not in (".", "..") for part in value.split("/")), "unsafe snapshot path")
    require("\\" not in value and "\x00" not in value, "unsafe snapshot path")


@dataclass(frozen=True)
class SnapshotFile:
    path: str
    content_base64: str
    mode: int


@dataclass(frozen=True)
class Snapshot:
    version: str
    files: tuple[SnapshotFile, ...]
    directories: tuple[str, ...]
    sha256: str

    @classmethod
    def create(cls, files: tuple[SnapshotFile, ...], directories: tuple[str, ...]):
        data = {"version": "0.1.0", "files": tuple(sorted(files, key=lambda file: file.path)), "directories": tuple(sorted(directories))}
        snapshot = cls(**data, sha256=digest(data))
        snapshot.validate()
        return snapshot

    def validate(self) -> None:
        decode(Snapshot, primitive(self))
        require(self.version == "0.1.0", "unsupported snapshot version")
        paths = [file.path for file in self.files] + list(self.directories)
        require(len(set(paths)) == len(paths), "duplicate snapshot path")
        require(tuple(sorted(self.directories)) == self.directories and tuple(sorted(self.files, key=lambda file: file.path)) == self.files, "snapshot records must be sorted")
        for path in paths:
            safe_relative_path(path)
            parent = PurePosixPath(path).parent
            while parent.as_posix() != ".":
                require(parent.as_posix() in self.directories, "snapshot parent directory missing")
                parent = parent.parent
        for file in self.files:
            require(file.mode in (0o600, 0o644, 0o700, 0o755), "unsupported file mode")
            try:
                base64.b64decode(file.content_base64, validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("invalid base64 snapshot content") from exc
        expected = digest({"version": self.version, "files": self.files, "directories": self.directories})
        require(self.sha256 == expected, "snapshot hash mismatch")


@dataclass(frozen=True)
class Evaluation:
    success: bool | None
    detail: str
    grader_version: str


class DeterministicEnvironment(ABC):
    @abstractmethod
    def reset(self, seed: int) -> Snapshot:
        pass

    @abstractmethod
    def snapshot(self) -> Snapshot:
        pass

    @abstractmethod
    def restore(self, snapshot: Snapshot) -> None:
        pass

    @abstractmethod
    def evaluate(self) -> Evaluation:
        pass
