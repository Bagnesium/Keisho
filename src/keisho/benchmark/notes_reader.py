"""Schema-specific guarded reader for STRUCTURED_NOTES_2K generator output (proposed v2.2).

Independent of the action/claims reader. Accepts exactly one JSON object holding exactly the frozen
structured note fields (non-empty strings), optionally surrounded by prose or inside exactly one code
fence. Rejects malformed or ambiguous output, duplicate keys, non-finite constants and schema
violations. Never salvages nested objects, never repairs, never retries. Returns the parsed fields and
framing metadata (stripped text) so callers can log it; the raw response is preserved by logged_generate.
"""
import json
import re

from keisho.core import require

NOTES_READER_VERSION = 'structured-notes-reader/1.0'
# Outside the admitted object/fence, prose may contain quotes but no JSON structural characters:
# any brace or bracket outside means a second (or wrapping) candidate and is ambiguous.
_STRUCTURAL = set('{}[]')
_FENCE = '```'


def _unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'structured notes: duplicate JSON key: ' + key)
        out[key] = value
    return out


def _nonfinite(value):
    require(False, 'structured notes: non-JSON numeric constant: ' + value)


_DECODER = json.JSONDecoder(object_pairs_hook=_unique, parse_constant=_nonfinite)


def _decode_whole(content, where):
    require(content.startswith('{'), 'structured notes: no JSON object ' + where)
    try:
        data, end = _DECODER.raw_decode(content, 0)
    except (json.JSONDecodeError, ValueError) as exc:
        if 'structured notes:' in str(exc):
            raise
        require(False, 'structured notes: malformed JSON ' + where + ': ' + str(exc))
    require(content[end:].strip() == '', 'structured notes: ambiguous trailing content ' + where)
    return data


def _check_outside(text, where):
    bad = set(text) & _STRUCTURAL
    require(not bad, 'structured notes: ambiguous JSON-like characters ' + where + ': ' + ''.join(sorted(bad)))


def read_structured_notes(text, fields):
    """Return (notes_dict, framing). Raises ValidationError on any violation."""
    require(isinstance(text, str), 'structured notes: response text must be a string')
    fields = tuple(fields)
    fences = text.count(_FENCE)
    if fences:
        require(fences == 2, 'structured notes: expected exactly one code block, found %d fence markers' % fences)
        start = text.find(_FENCE)
        stop = text.find(_FENCE, start + 3)
        before, inner, after = text[:start], text[start + 3:stop], text[stop + 3:]
        _check_outside(before, 'before code fence')
        _check_outside(after, 'after code fence')
        tag = re.match(r'^[A-Za-z0-9_-]*\r?\n', inner)
        tag_len = tag.end() if tag else 0
        data = _decode_whole(inner[tag_len:].strip(), 'inside code fence')
        framing = {'stripped_leading': text[:start + 3 + tag_len], 'stripped_trailing': text[stop:], 'is_fenced': True}
    else:
        first = text.find('{')
        require(first != -1, 'structured notes: no JSON object found (prose only)')
        before = text[:first]
        _check_outside(before, 'before JSON object')
        try:
            data, end = _DECODER.raw_decode(text, first)
        except (json.JSONDecodeError, ValueError) as exc:
            if 'structured notes:' in str(exc):
                raise
            require(False, 'structured notes: malformed outer JSON: ' + str(exc))
        after = text[end:]
        _check_outside(after, 'after JSON object')
        framing = {'stripped_leading': before, 'stripped_trailing': after, 'is_fenced': False}
    framing['has_framing'] = bool(before.strip() or after.strip())
    framing['reader_version'] = NOTES_READER_VERSION
    require(isinstance(data, dict), 'structured notes: top-level value must be an object')
    require(set(data) == set(fields), 'structured notes: schema fields differ (missing %s, extra %s)' % (
        sorted(set(fields) - set(data)), sorted(set(data) - set(fields))))
    for key in fields:
        require(isinstance(data[key], str) and data[key].strip(), 'structured notes: field must be a non-empty string: ' + key)
    try:
        json.dumps(data, ensure_ascii=False).encode('utf-8')
    except (UnicodeEncodeError, ValueError):
        require(False, 'structured notes: value not representable as UTF-8 JSON')
    return data, framing
