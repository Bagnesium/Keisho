"""Prospective auxiliary annotations; structural validity never establishes truth."""
import json

from keisho.core import require

STRICT = 'strict/1.0'
AUXILIARY = 'auxiliary-claims/2.0'
STATUSES = ('OBSERVED', 'VERIFIED', 'INFERRED', 'UNCERTAIN', 'FALSIFIED')
BASES = ('tool', 'predecessor', 'independent')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'ambiguous duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse_auxiliary(text, known_evidence_ids):
    def invalid_constant(value):
        require(False, 'non-JSON numeric constant: ' + value)
    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant)
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
    return {'action': data['action'], 'claims': accepted, 'annotation_report': report}


def agent_response_format(version='2.0'):
    require(version in ('2.0','3.0'),'unsupported action contract version')
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
    if version=='3.0':
        listing={'type':'object','properties':{'tool':{'const':'list_files'},'prefix':string,
            'cursor':{'type':['string','null']},'limit':{'type':'integer','minimum':1,'maximum':100}},
            'required':['tool'],'additionalProperties':False}
        schema['properties']['action']['anyOf'][0]=listing
    # Dynamic evidence availability, lengths, paths and authorization stay local.
    return {'type': 'json_schema', 'json_schema': {'name': 'keisho_agent_response_v'+version[0], 'strict': True, 'schema': schema}}
