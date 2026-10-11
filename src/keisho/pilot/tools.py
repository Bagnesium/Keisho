from pathlib import Path

from keisho.core import digest, require, text_digest
from keisho.environments.base import safe_relative_path
from .sandbox import MacSandbox, score_cases
from .tasks import PublicTask


class InvalidAction(ValueError):
    pass


def file_hashes(workspace: Path, files: tuple[str, ...]) -> dict[str, str]:
    return {path: text_digest((workspace / path).read_text()) for path in files}


class ToolSession:
    """No shell, arbitrary test command, absolute path, or gold access is exposed."""

    def __init__(self, task: PublicTask, workspace: Path, sandbox: MacSandbox):
        self.task, self.workspace, self.sandbox = task, workspace.resolve(), sandbox

    def _file(self, path: str, writable: bool = False) -> Path:
        if not isinstance(path, str):
            raise InvalidAction("file path must be text")
        try:
            safe_relative_path(path)
        except ValueError:
            raise InvalidAction("unsafe file path") from None
        allowed = self.task.editable_files if writable else self.task.files.keys()
        if path not in allowed:
            raise InvalidAction("file is outside the permitted task files")
        target = self.workspace / path
        if target.is_symlink() or target.resolve().parent != self.workspace or not target.is_file():
            raise InvalidAction("file is missing or its path was replaced")
        return target

    def execute(self, action: dict) -> dict:
        tool = action.get("tool")
        expected = {"list_files": {"tool"}, "read_file": {"tool", "path"}, "write_file": {"tool", "path", "content"}, "run_tests": {"tool", "test_ids"}}
        if not isinstance(tool, str) or tool not in expected or set(action) != expected[tool]:
            raise InvalidAction("unknown tool or invalid action fields")
        before = file_hashes(self.workspace, self.task.editable_files)
        if tool == "list_files":
            result = {"files": sorted(self.task.files), "test_ids": [case["id"] for case in self.task.cases]}
        elif tool == "read_file":
            result = {"path": action["path"], "content": self._file(action["path"]).read_text()}
        elif tool == "write_file":
            if not isinstance(action["content"], str) or len(action["content"].encode()) > 16384:
                raise InvalidAction("source content must be text within 16 KiB")
            self._file(action["path"], True).write_text(action["content"])
            result = {"path": action["path"], "content_sha256": text_digest(action["content"])}
        else:
            ids = action["test_ids"]
            if not isinstance(ids, list) or not ids or not all(isinstance(key, str) for key in ids) or len(ids) != len(set(ids)):
                raise InvalidAction("test IDs must be a nonempty unique array")
            if ids == ["full"]:
                cases = self.task.cases
            else:
                if not set(ids) <= {case["id"] for case in self.task.cases}:
                    raise InvalidAction("unknown public test ID")
                cases = tuple(case for key in ids for case in self.task.cases if case["id"] == key)
            result = score_cases(self.sandbox, self.workspace, cases)
        return {"action": action, **result, "source_hashes_before": before, "source_hashes_after": file_hashes(self.workspace, self.task.editable_files)}
