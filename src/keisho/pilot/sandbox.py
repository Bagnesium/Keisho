"""Fail-closed macOS process isolation for tiny pure-Python benchmark functions."""

import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import time

from keisho.core import ValidationError, canonical_json, require


class IsolationUnavailable(RuntimeError):
    pass


# Gold expectations stay in the parent. Child receives only function arguments.
WORKER = r'''
import sys, json, importlib, resource
resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
data = json.loads(sys.stdin.read())
sys.path.insert(0, data["workspace"])
if data.get("probe"):
    import socket, os
    def readable(path):
        try:
            with open(path) as stream: stream.read(1)
            return True
        except OSError: return False
    denied = [readable(path) for path in data["denied"]]
    try:
        socket.socket().connect(("127.0.0.1", 9))
        network_denied = False
    except PermissionError: network_denied = True
    except OSError: network_denied = False
    print(json.dumps({"own": readable(data["own"]), "outside": denied,
                      "network_denied": network_denied,
                      "credentials_absent": not any("API_KEY" in key for key in os.environ)}))
else:
    results = []
    for case in data["cases"]:
        try:
            module = importlib.import_module(case["module"])
            value = getattr(module, case["function"])(*case["args"])
            results.append({"id": case["id"], "value": value})
        except BaseException as exc:
            results.append({"id": case["id"], "exception": type(exc).__name__, "detail": str(exc)[:1000]})
    print(json.dumps({"results": results}, allow_nan=False))
'''


class MacSandbox:
    def __init__(self, timeout_seconds: float = 5.0, output_limit: int = 65536):
        self.executable = shutil.which("sandbox-exec")
        # macOS framework's command-line stub spawns Python.app; invoke the real
        # interpreter directly so task code never needs process-fork permission.
        framework_binary = Path(sys.base_prefix) / "Resources/Python.app/Contents/MacOS/Python"
        self.python = str((framework_binary if framework_binary.is_file() else Path(sys.executable)).resolve())
        self.timeout = timeout_seconds
        self.output_limit = output_limit
        self.verified = False

    def _profile(self, workspace: Path) -> str:
        def quote(path):
            return json.dumps(str(path))
        # Isolated mode plus -S avoids site customization and installed package hooks.
        roots = (Path(sys.base_prefix).resolve(), Path("/System"), Path("/usr/lib"), Path("/dev"), workspace.resolve())
        readers = " ".join(f"(subpath {quote(path)})" for path in roots)
        ancestors = sorted({parent for path in roots for parent in path.parents})
        readers += " " + " ".join(f"(literal {quote(path)})" for path in ancestors)
        # Deny filesystem content outside the minimal runtime/workspace allowlist.
        # Anonymous inherited stdin/stdout pipes retain their ordinary permissions.
        return f'''(version 1)(allow default)
(deny file-read-data (require-all (subpath "/") (require-not (require-any {readers}))))
(deny file-write* (require-all (subpath "/") (require-not (subpath "/dev"))))
(deny process-fork)
(deny process-exec (require-not (literal {quote(self.python)})))
(deny network*)'''

    def _execute(self, workspace: Path, data: dict) -> dict:
        if not self.executable:
            raise IsolationUnavailable("sandbox-exec unavailable; no unrestricted fallback")
        command = [self.executable, "-p", self._profile(workspace), self.python, "-I", "-S", "-B", "-c", WORKER]
        payload = canonical_json({"workspace": str(workspace.resolve()), **data}).encode()
        require(len(payload) <= 32768, "sandbox input exceeds limit")
        env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "17", "LANG": "C.UTF-8"}
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, cwd=workspace, start_new_session=True)
        selector = selectors.DefaultSelector()
        output = {"stdout": bytearray(), "stderr": bytearray()}
        deadline, failure = time.monotonic() + self.timeout, None
        try:
            for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            try:
                process.stdin.write(payload)
                process.stdin.close()
            except BrokenPipeError:
                # Early interpreter/sandbox exits still have diagnostic output.
                # Continue draining it, and always reap the child below.
                pass
            while selector.get_map():
                if time.monotonic() >= deadline:
                    failure = "timeout"
                    break
                for key, _ in selector.select(0.05):
                    chunk = os.read(key.fd, 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output[key.data].extend(chunk)
                        if sum(map(len, output.values())) > self.output_limit:
                            failure = "output_limit"
                            break
                if failure:
                    break
            if failure is None:
                try:
                    process.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    failure = "timeout"
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
            selector.close()
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except BrokenPipeError:
                    pass
        stderr = output["stderr"].decode(errors="replace")
        if "sandbox_apply" in stderr or "sandbox_init" in stderr:
            raise IsolationUnavailable("OS refused sandbox initialization; run from a host permitting sandbox-exec")
        if failure or process.returncode:
            return {"execution_failure": failure or "worker_exit", "returncode": process.returncode, "stderr": stderr[:4000]}
        try:
            result = json.loads(output["stdout"])
            require(isinstance(result, dict), "worker output must be an object")
            return result
        except (ValueError, TypeError):
            return {"execution_failure": "invalid_worker_output", "returncode": process.returncode}

    def verify(self, workspace: Path, own_file: Path, forbidden_files: tuple[Path, ...]) -> dict:
        result = self._execute(workspace, {"probe": True, "own": str(own_file), "denied": [str(file) for file in forbidden_files]})
        if result != {"own": True, "outside": [False] * len(forbidden_files), "network_denied": True, "credentials_absent": True}:
            raise IsolationUnavailable(f"isolation probe failed: {result}")
        self.verified = True
        return result

    def run(self, workspace: Path, cases: tuple[dict, ...]) -> dict:
        if not self.verified:
            raise IsolationUnavailable("isolation must pass its probe before executing task code")
        stripped = [{key: case[key] for key in ("id", "module", "function", "args")} for case in cases]
        return self._execute(workspace, {"cases": stripped})


def score_cases(sandbox: MacSandbox, workspace: Path, cases: tuple[dict, ...]) -> dict:
    response = sandbox.run(workspace, cases)
    if "execution_failure" in response:
        # Untrusted task-code crashes, timeouts and malformed output are task failures.
        return {"results": [{"id": case["id"], "passed": False, "execution_failure": response} for case in cases]}
    records = response.get("results", [])
    expected_ids = [case["id"] for case in cases]
    if not isinstance(records, list) or [record.get("id") for record in records if isinstance(record, dict)] != expected_ids:
        return {"results": [{"id": case["id"], "passed": False, "execution_failure": "case ID mismatch"} for case in cases]}
    results = []
    for case, actual in zip(cases, records):
        passed = "value" in actual and canonical_json(actual["value"]) == canonical_json(case["expected"])
        results.append({"id": case["id"], "passed": passed, "expected": case["expected"], **{key: value for key, value in actual.items() if key != "id"}})
    return {"results": results}
