import base64
from pathlib import Path
import shutil
import stat
from typing import Callable, Mapping

from keisho.core import decode, nonempty, primitive, require
from .base import DeterministicEnvironment, Evaluation, Snapshot, SnapshotFile, safe_relative_path


class FilesystemEnvironment(DeterministicEnvironment):
    """An owned local workspace, not a sandbox for arbitrary generated code.

    Caller keeps graders/raw logs outside it. Symlinks, special files, and hard
    links are rejected; subprocess state, services, directory modes and mtimes
    are outside the snapshot contract. Phase 1 must isolate those separately.
    """

    def __init__(self, workspace: Path, initial_files: Mapping[str, str], grader: Callable[[Path], Evaluation]):
        # Validate input before creating or touching the workspace.
        files, directories = [], set()
        for path, content in initial_files.items():
            safe_relative_path(path)
            require(isinstance(content, str), "initial file content must be text")
            files.append(SnapshotFile(path, base64.b64encode(content.encode()).decode("ascii"), 0o644))
            parent = Path(path).parent
            while parent.as_posix() != ".":
                directories.add(parent.as_posix())
                parent = parent.parent
        self._initial = Snapshot.create(tuple(files), tuple(directories))
        candidate = Path(workspace).absolute()
        require(not candidate.is_symlink(), "workspace root cannot be a symlink")
        self.workspace = candidate.parent.resolve() / candidate.name
        self.workspace.mkdir(parents=True, exist_ok=False)
        self._grader = grader
        self.restore(self._initial)

    def _owned_root(self) -> None:
        require(self.workspace.is_dir() and not self.workspace.is_symlink(), "workspace root replaced or missing")
        require(self.workspace.resolve() == self.workspace, "workspace ancestry contains a symlink")

    def reset(self, seed: int) -> Snapshot:
        require(type(seed) is int and seed >= 0, "invalid environment seed")
        # No randomness in v1; record the seed anyway for the experimental block.
        self.restore(self._initial)
        return self.snapshot()

    def snapshot(self) -> Snapshot:
        self._owned_root()
        files, directories = [], []
        for path in sorted(self.workspace.rglob("*")):
            info = path.lstat()
            require(not path.is_symlink(), "symlinks are outside snapshot contract")
            relative = path.relative_to(self.workspace).as_posix()
            if stat.S_ISDIR(info.st_mode):
                directories.append(relative)
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "special/hard-linked files are outside snapshot contract")
                files.append(SnapshotFile(relative, base64.b64encode(path.read_bytes()).decode("ascii"), stat.S_IMODE(info.st_mode)))
        return Snapshot.create(tuple(files), tuple(directories))

    def restore(self, snapshot: Snapshot) -> None:
        snapshot.validate()
        self._owned_root()
        for path in self.workspace.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        for relative in snapshot.directories:
            (self.workspace / relative).mkdir(parents=True, exist_ok=True)
        for file in snapshot.files:
            path = self.workspace / file.path
            path.write_bytes(base64.b64decode(file.content_base64, validate=True))
            path.chmod(file.mode)
        require(self.snapshot() == snapshot, "restore did not reproduce snapshot")

    def evaluate(self) -> Evaluation:
        result = self._grader(self.workspace)
        decode(Evaluation, primitive(result))
        nonempty(result.detail, "evaluation detail")
        nonempty(result.grader_version, "grader version")
        return result

    def fork(self, workspace: Path, snapshot: Snapshot):
        snapshot.validate()
        child = FilesystemEnvironment(workspace, {}, self._grader)
        child.restore(snapshot)
        return child
