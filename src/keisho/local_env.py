"""Literal credentials from one trusted project-root file; no discovery or shell."""

import os
import re
import stat

from keisho.core import require

KEYS = ("OPENAI_API_KEY", "OPENROUTER_API_KEY")


def load_project_env(project_root, environ=None):
    environ = os.environ if environ is None else environ
    path = project_root / ".env"
    try:
        require(not path.is_symlink(), "project .env cannot be a symlink")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return {"path": str(path), "present": {key: bool(environ.get(key)) for key in KEYS}}
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= 16384, "project .env must be a small regular file")
        if os.name == "posix":
            require(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, "project .env must be owned by the current user with private permissions")
        pending = {}
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            matched = re.fullmatch(r"(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)", line)
            require(matched is not None, f"invalid project .env assignment at line {number}")
            key, value = matched.groups()
            if key not in KEYS:
                continue  # Do not import unrelated process configuration.
            if value.startswith(("'", '"')):
                quote = value[0]
                end = value.find(quote, 1)
                require(end >= 1 and (not value[end + 1:].strip() or value[end + 1:].lstrip().startswith("#")), f"invalid project .env value at line {number}")
                value = value[1:end]  # Literal: no interpolation/escape evaluation.
            else:
                value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
                require(not any(char.isspace() for char in value), f"quote project .env value at line {number}")
            require(key not in pending, f"duplicate credential assignment at line {number}")
            pending[key] = value
    for key, value in pending.items():
        environ.setdefault(key, value)  # Even an existing empty variable wins.
    return {"path": str(path), "present": {key: bool(environ.get(key)) for key in KEYS}}


def redact_credentials(text, *extra):
    for secret in {*extra, *(os.environ.get(key) for key in KEYS)}:
        if secret:
            text = text.replace(secret, "[REDACTED_API_KEY]")
    return text
