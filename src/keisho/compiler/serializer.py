import json

from keisho.core import ValidationError, canonical_json, decode
from keisho.state.schema import KeishoState
from keisho.state.validator import validate_state


def serialize(state: KeishoState) -> str:
    validate_state(state)
    return canonical_json(state)


def deserialize(text: str) -> KeishoState:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key {key}")
            result[key] = value
        return result
    try:
        data = json.loads(text, object_pairs_hook=unique_keys)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"invalid state JSON: {exc}") from exc
    state = decode(KeishoState, data)
    validate_state(state)
    return state
