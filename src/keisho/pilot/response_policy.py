"""Prospective auxiliary annotations; structural validity never establishes truth."""
import json
import re

from keisho.core import canonical_json, require

STRICT = 'strict/1.0'
AUXILIARY = 'auxiliary-claims/2.0'
STATUSES = ('OBSERVED', 'VERIFIED', 'INFERRED', 'UNCERTAIN', 'FALSIFIED')
BASES = ('tool', 'predecessor', 'independent')

# Prospective model-facing clarification only. No enum widening, label mapping,
# semantic admission rule, or historical parser behavior changes.
ANNOTATION_GUIDANCE_VERSION = 'annotation-guidance/1.0'
ANNOTATION_GUIDANCE = '''Annotation guidance annotation-guidance/1.0 (auxiliary-claims/2.0 format unchanged):
basis is exactly one provenance class, never a free-text source description or a certainty level.
Use "tool" for a claim based on completed tool results already supplied in this conversation, including an inference from those results.
Use "predecessor" for a report inherited from predecessor context that you have not re-observed; this is reported provenance, not verification.
Use "independent" for your own reasoning or proposal without claimed tool-result support; the label does not mean independent verification.
Put concise source descriptions in statement and available result event IDs in evidence_ids, not in basis.
status describes what you are asserting: OBSERVED is a literal completed observation; VERIFIED is a claim of narrow support from a completed check at its recorded scope;
INFERRED is a conclusion beyond literal observations; UNCERTAIN is an unresolved possibility; FALSIFIED is a specific claim contradicted by evidence at its recorded scope.
These are model assertions. The validator checks structure and reference availability, not semantic truth. Model claims remain interpretations in extracted state.
Claims describe evidence available BEFORE the action in this response. Do not claim the proposed read, write, or test has already completed or passed.
For tool-based observations or verification, cite the actual supporting completed result, with the exact observed scope. A listing proves names, not file contents; a write proves a change, not correctness.
Never invent evidence, cite future results, cite historical handoff IDs as locally available results, or treat a citation as proof of support. A hypothesis may have evidence_ids:[] and must remain INFERRED or UNCERTAIN.
Keep contradictory or stale evidence scoped; code changes can require retesting. Do not turn an unknown or predecessor report into a verified result. If no appropriate annotation is available, emit claims:[].
Illustrative claims (result_read and result_test are placeholders; cite only IDs actually returned to you):
{"statement":"Read parser.py; it contains a cache lookup","status":"OBSERVED","evidence_ids":["result_read"],"basis":"tool"}
{"statement":"The cache lookup may explain the issue; this is an inference from parser.py","status":"INFERRED","evidence_ids":["result_read"],"basis":"tool"}
{"statement":"The recorded test command exited 0 on the current files; broader correctness remains unknown","status":"VERIFIED","evidence_ids":["result_test"],"basis":"tool"}
{"statement":"Predecessor notes report a cache suspicion; I have not checked it","status":"UNCERTAIN","evidence_ids":[],"basis":"predecessor"}
{"statement":"A cache invalidation bug is a possibility; no supporting result is available","status":"UNCERTAIN","evidence_ids":[],"basis":"independent"}
'''


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'ambiguous duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse_unique_json(text):
    """Reject duplicate keys and non-JSON constants before interpreting an action."""
    def invalid_constant(value):
        require(False, 'non-JSON numeric constant: ' + value)
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant)


def _invalid_constant(value):
    require(False, 'non-JSON numeric constant: ' + value)


_JSON_DECODER = json.JSONDecoder(
    object_pairs_hook=_unique_object,
    parse_constant=_invalid_constant,
)
FORBIDDEN_OUTSIDE = set('{}[]"')


def extract_action_json(text: str) -> tuple[dict, dict]:
    """Extract exactly one top-level action/claims JSON object without nested salvage.

    Preserves duplicate-key rejection and parse_constant rejection of NaN/Infinity/-Infinity.
    Strictly enforces the Zero-Skip Brace Rule and conservative wrapper checks.
    """
    require(isinstance(text, str), 'response text must be a string')

    fence_count = text.count('```')
    if fence_count > 0:
        require(fence_count == 2, f'ambiguous response: expected exactly one code block (2 fences), found {fence_count}')
        start_fence = text.find('```')
        end_fence = text.find('```', start_fence + 3)
        outside_before = text[:start_fence]
        outside_after = text[end_fence + 3:]

        forbidden_before = set(outside_before) & FORBIDDEN_OUTSIDE
        require(not forbidden_before, f'forbidden wrapper characters before code fence: {forbidden_before}')
        forbidden_after = set(outside_after) & FORBIDDEN_OUTSIDE
        require(not forbidden_after, f'forbidden wrapper characters after code fence: {forbidden_after}')

        inner = text[start_fence + 3 : end_fence]
        tag_match = re.match(r'^[a-zA-Z0-9_-]*\r?\n', inner)
        tag_len = tag_match.end() if tag_match else 0
        content = inner[tag_len:].strip()

        require(content.startswith('{'), 'no JSON object found inside code fence')
        try:
            data, end = _JSON_DECODER.raw_decode(content, 0)
        except (json.JSONDecodeError, ValueError) as exc:
            require(False, f'malformed JSON inside code fence: {exc}')

        require(content[end:].strip() == '', 'extra content inside code fence after JSON object')
        stripped_leading = text[:start_fence + 3 + tag_len]
        stripped_trailing = text[end_fence:]
        framing = {
            'stripped_leading': stripped_leading,
            'stripped_trailing': stripped_trailing,
            'is_fenced': True,
            'has_framing': bool(stripped_leading.strip() or stripped_trailing.strip()),
        }
        return data, framing

    first_brace = text.find('{')
    require(first_brace != -1, 'no JSON object found in response (prose only)')

    outside_before = text[:first_brace]
    forbidden_before = set(outside_before) & FORBIDDEN_OUTSIDE
    require(not forbidden_before, f'forbidden wrapper characters before JSON object: {forbidden_before}')

    # ZERO-SKIP BRACE RULE: Decode strictly from first_brace.
    # Never advance past first_brace if decoding fails; fail fast to prevent nested-object salvage.
    try:
        data, end = _JSON_DECODER.raw_decode(text, first_brace)
    except (json.JSONDecodeError, ValueError) as exc:
        require(False, f'malformed outer JSON: {exc}')

    outside_after = text[end:]
    forbidden_after = set(outside_after) & FORBIDDEN_OUTSIDE
    require(not forbidden_after, f'forbidden wrapper characters or trailing content after JSON object: {forbidden_after}')

    framing = {
        'stripped_leading': outside_before,
        'stripped_trailing': outside_after,
        'is_fenced': False,
        'has_framing': bool(outside_before.strip() or outside_after.strip()),
    }
    return data, framing


def validate_recordable_json(data):
    """Reject decoded values that cannot be losslessly stored in UTF-8 JSON."""
    try:
        canonical_json(data).encode('utf-8')
    except UnicodeEncodeError:
        require(False, 'decoded JSON strings are not valid UTF-8')
    except ValueError:
        require(False, 'decoded JSON contains non-finite numbers')
    except TypeError:
        require(False, 'decoded value is not JSON')


def parse_auxiliary(text_or_data, known_evidence_ids):
    if isinstance(text_or_data, str):
        data, framing = extract_action_json(text_or_data)
        validate_recordable_json(data)
    elif isinstance(text_or_data, tuple) and len(text_or_data) == 2:
        data, framing = text_or_data
    else:
        data, framing = text_or_data, {'has_framing': False, 'stripped_leading': '', 'stripped_trailing': '', 'is_fenced': False}
    require(isinstance(data, dict) and set(data) == {'action', 'claims'}, 'response must contain action and claims only')
    require(isinstance(data['action'], dict) and isinstance(data['claims'], list), 'invalid action/claims types')
    require(len(data['claims']) <= 8, 'too many claims')
    accepted, rejected = [], []
    for index, claim in enumerate(data['claims']):
        errors = []
        if not isinstance(claim, dict) or set(claim) != {'statement', 'status', 'evidence_ids', 'basis'}:
            errors.append({'field': 'claim', 'reason': 'invalid claim fields'})
        if isinstance(claim, dict):
            statement = claim.get('statement')
            if not isinstance(statement, str) or not 0 < len(statement) <= 2000:
                errors.append({'field': 'statement', 'reason': 'invalid claim statement'})
            if claim.get('status') not in STATUSES:
                errors.append({'field': 'status', 'reason': 'invalid claimed status', 'permitted': list(STATUSES)})
            if claim.get('basis') not in BASES:
                errors.append({'field': 'basis', 'reason': 'invalid claim basis', 'permitted': list(BASES)})
            refs = claim.get('evidence_ids')
            if not isinstance(refs, list) or not all(isinstance(key, str) for key in refs):
                errors.append({'field': 'evidence_ids', 'reason': 'invalid claim evidence'})
            elif not set(refs) <= known_evidence_ids:
                errors.append({'field': 'evidence_ids', 'reason': 'claim cites unavailable tool evidence',
                               'unavailable': sorted(set(refs) - known_evidence_ids)})
        if errors:
            rejected.append({'index': index, 'raw_claim': claim, 'errors': errors, 'annotation_information': 'unknown'})
        else:
            accepted.append(claim)
    report = {'policy': AUXILIARY, 'raw_claims': data['claims'], 'validated_claims': accepted,
              'diagnostics': rejected, 'coverage': {'supplied': len(data['claims']), 'validated': len(accepted), 'rejected': len(rejected)},
              'annotation_information': 'unknown' if not accepted else 'schema-validated interpretation only',
              'semantic_truth_verified': False}
    return {'action': data['action'], 'claims': accepted, 'annotation_report': report, 'framing': framing}


def agent_response_format(version='2.0'):
    require(version in ('2.0','3.0','4.0'),'unsupported action contract version')
    def obj(fields):
        return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    string = {'type': 'string'}
    def action(name, **fields):
        return obj({'tool': {'type': 'string', 'enum': [name]}, **fields})
    schema = obj({'action': {'anyOf': [action('list_files'), action('read_file', path=string),
                         action('write_file', path=string, content=string), action('shell', command=string), action('finish', answer=string)]},
                  'claims': {'type': 'array', 'items': obj({'statement': string,
                         'status': {'type': 'string', 'enum': list(STATUSES)},
                         'evidence_ids': {'type': 'array', 'items': string},
                         'basis': {'type': 'string', 'enum': list(BASES)}})}})
    if version in ('3.0','4.0'):
        listing={'type':'object','properties':{'tool':{'const':'list_files'},'prefix':string,
            'cursor':{'type':['string','null']},'limit':{'type':'integer','minimum':1,'maximum':100}},
            'required':['tool'],'additionalProperties':False}
        schema['properties']['action']['anyOf'][0]=listing
    if version=='4.0':
        # Prospective wire compatibility only. The execution contract remains
        # the same flat 3.0 actions, including omitted optional listing fields.
        variants = schema['properties']['action']['anyOf']
        nested = []
        for flat in variants:
            arguments = {key:value for key,value in flat['properties'].items() if key!='tool'}
            args = {'type':'object','properties':arguments,
                    'required':[key for key in flat['required'] if key!='tool'],
                    'additionalProperties':False}
            nested.append(obj({'tool':flat['properties']['tool'],'args':args}))
        schema['properties']['action']['anyOf'] = variants + nested
    # Dynamic evidence availability, lengths, paths and authorization stay local.
    return {'type': 'json_schema', 'json_schema': {'name': 'keisho_agent_response_v'+version[0], 'strict': True, 'schema': schema}}
