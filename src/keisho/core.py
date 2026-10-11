"""Strict JSON boundaries shared by state, manifests, and raw logs."""

from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
import types
from typing import Union, get_args, get_origin, get_type_hints


class ValidationError(ValueError):
    pass


def primitive(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [primitive(item) for item in value]
    if isinstance(value, dict):
        return {key: primitive(item) for key, item in value.items()}
    return value


def canonical_json(value) -> str:
    return json.dumps(primitive(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def nonempty(value: str, label: str) -> None:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")


def sha256(value: str, label: str) -> None:
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None, f"{label} must be a SHA-256 digest")


def timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("timestamp must be ISO 8601") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "timestamp requires a timezone")


def decode(cls, value, path="root"):
    """Decode only declared types, rejecting unknown keys and implicit coercions."""
    origin, args = get_origin(cls), get_args(cls)
    if origin in (types.UnionType, Union):
        for choice in args:
            try:
                return decode(choice, value, path)
            except ValidationError:
                pass
        raise ValidationError(f"{path}: no union type matched")
    if cls is type(None):
        require(value is None, f"{path}: expected null")
        return None
    if origin is tuple:
        require(isinstance(value, (list, tuple)), f"{path}: expected array")
        require(len(args) == 2 and args[1] is Ellipsis, f"{path}: unsupported tuple type")
        return tuple(decode(args[0], item, f"{path}[{index}]") for index, item in enumerate(value))
    if is_dataclass(cls):
        require(isinstance(value, dict), f"{path}: expected object")
        declared = {field.name: field for field in fields(cls)}
        require(not value.keys() - declared.keys(), f"{path}: unknown fields {value.keys() - declared.keys()}")
        hints = get_type_hints(cls)
        kwargs = {}
        for name, field in declared.items():
            if name in value:
                kwargs[name] = decode(hints[name], value[name], f"{path}.{name}")
            else:
                require(field.default is not MISSING or field.default_factory is not MISSING, f"{path}: missing {name}")
        return cls(**kwargs)
    if isinstance(cls, type) and issubclass(cls, Enum):
        try:
            return cls(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{path}: invalid {cls.__name__}") from exc
    if cls is float:
        require(type(value) in (float, int) and math.isfinite(value), f"{path}: expected finite number")
        return float(value)
    require(type(value) is cls, f"{path}: expected {cls.__name__}")
    return value
