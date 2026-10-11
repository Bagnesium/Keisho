"""Read-only measurements of archived responses; never repairs or admits actions."""
import base64
import json

from jsonschema import Draft202012Validator

from keisho.core import canonical_json, require
from keisho.pilot.action_wire import VERSION as ACTION_WIRE_VERSION, canonicalize_action
from keisho.pilot.response_policy import agent_response_format, parse_auxiliary, validate_recordable_json

VERSION = 'response-measurements/1.0'
ACTION_WIRE_MEASUREMENT_VERSION = 'response-measurements/2.0'


def capture_response(raw, number, payload, status, redacted):
    raw.write_artifact(f'wire-response-{number:03d}.json', {
        'version': VERSION, 'capture_boundary': 'HTTP body before JSON decoding/provider validation',
        'body_base64': base64.b64encode(payload).decode('ascii'), 'http_status': status,
        'credential_redaction_applied': redacted, 'headers_recorded': False,
        'upstream_untouched_output_attested': False})


def assess_text(text, known, validate_action, action_contract_version='2.0', action_wire_version=None):
    require(action_wire_version in (None, ACTION_WIRE_VERSION), 'unsupported action wire version')
    row = {'json_syntax_valid': None, 'response_structure_valid': None,
           'action_schema_valid': None, 'auxiliary_annotations_valid': None,
           'safety_valid': None, 'proposed_action': None, 'annotations': None,
           'diagnostics': []}
    if action_wire_version is not None:
        row.update(action_wire_version=action_wire_version, wire_action_schema_valid=None,
                   canonical_action_schema_valid=None, canonical_action=None, action_wire_assessment=None)
    def error(stage, reason):
        row['diagnostics'].append({'stage': stage, 'reason': reason})
    if not isinstance(text, str):
        row['json_syntax_valid'] = False
        error('json_syntax', 'model message has no string content')
        return row
    duplicates = []
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data: duplicates.append(key)
            data[key] = value
        return data
    def constant(value):
        raise ValueError('non-JSON numeric constant: ' + value)
    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError) as exc:
        row['json_syntax_valid'] = False
        error('json_syntax', str(exc))
        return row
    row['json_syntax_valid'] = True
    if duplicates:
        row['response_structure_valid'] = False
        error('response_structure', 'ambiguous duplicate JSON keys: ' + ', '.join(duplicates))
        return row  # Never interpret a selected duplicate as the model's action.
    if action_wire_version is not None:
        try:
            validate_recordable_json(data)
        except ValueError as exc:
            row['response_structure_valid'] = False
            error('encoding', str(exc))
            if isinstance(data,dict) and 'action' in data:
                try:
                    validate_recordable_json(data['action'])
                except ValueError:
                    pass
                else:
                    row['proposed_action'] = data['action']
            return row
    row['response_structure_valid'] = (isinstance(data, dict) and set(data) == {'action', 'claims'}
        and isinstance(data['action'], dict) and isinstance(data['claims'], list) and len(data['claims']) <= 8)
    if not row['response_structure_valid']:
        error('response_structure', 'expected action object and claims array (at most eight), with no extra fields')
    if not isinstance(data, dict): return row
    if 'action' in data:
        row['proposed_action'] = data['action']
        if action_wire_version is not None:
            assessment = canonicalize_action(data['action'], validate_action)
            row.update(action_schema_valid=assessment['wire_schema_valid'],
                       wire_action_schema_valid=assessment['wire_schema_valid'],
                       canonical_action_schema_valid=assessment['canonical_schema_valid'],
                       canonical_action=assessment['canonical_action'],
                       safety_valid=assessment['safety_valid'], action_wire_assessment=assessment)
            if assessment['rejection_reason'] is not None:
                error(assessment['validation_stage'], assessment['rejection_reason'])
        else:
            validator = Draft202012Validator(agent_response_format(action_contract_version)['json_schema']['schema']['properties']['action'])
            errors = list(validator.iter_errors(data['action']))
            row['action_schema_valid'] = not errors
            for exc in errors: error('action_schema', exc.message)
            if not errors:
                try:
                    if data['action']['tool'] != 'finish': validate_action(data['action'])
                    row['safety_valid'] = True
                except (ValueError, TypeError) as exc:
                    row['safety_valid'] = False
                    error('safety', str(exc))
    if 'claims' in data:
        try:
            # Assess the original claims independently; this constructed envelope
            # is measurement only and is never sent to the agent or execution.
            annotations = parse_auxiliary(canonical_json({'action': {}, 'claims': data['claims']}), known)['annotation_report']
            row['annotations'] = annotations
            row['auxiliary_annotations_valid'] = annotations['coverage']['rejected'] == 0
            row['diagnostics'].extend({'stage': 'auxiliary_annotations', **d} for d in annotations['diagnostics'])
        except (ValueError, TypeError) as exc:
            row['auxiliary_annotations_valid'] = False
            error('auxiliary_annotations', str(exc))
    return row


def summarize(rows, transmitted_requests, action_wire_version=None):
    received = [row for row in rows if row['model_response_received']]
    n = len(received)
    def rate(count): return count / n if n else None
    measurements = {}
    validity_fields = ('json_syntax_valid', 'response_structure_valid', 'action_schema_valid',
                       'auxiliary_annotations_valid', 'safety_valid')
    if action_wire_version is not None:
        validity_fields += ('wire_action_schema_valid', 'canonical_action_schema_valid')
    for field in validity_fields:
        invalid = sum(r[field] is False for r in received)
        unknown = sum(r[field] is None for r in received)
        measurements[field] = {'valid_count': sum(r[field] is True for r in received),
            'invalid_count': invalid, 'invalid_rate': rate(invalid), 'unassessable_count': unknown,
            'unassessable_rate': rate(unknown), 'denominator_actual_responses': n}
    for field in ('response_rejected', 'action_rejected', 'tool_execution_completed', 'tool_execution_successful'):
        count = sum(r[field] is True for r in received)
        measurements[field] = {'count': count, 'rate': rate(count), 'denominator_actual_responses': n}
    invalid_any = sum(any(r[field] is False for field in (
        'json_syntax_valid', 'response_structure_valid', 'action_schema_valid', 'auxiliary_annotations_valid', 'safety_valid')) for r in received)
    measurements['responses_with_any_invalid_component'] = {'count': invalid_any, 'rate': rate(invalid_any),
        'denominator_actual_responses': n, 'auxiliary_exclusion_does_not_imply_action_rejection': True}
    report = {'version': ACTION_WIRE_MEASUREMENT_VERSION if action_wire_version is not None else VERSION,
        'transmitted_requests': transmitted_requests,
        'actual_responses_received': n, 'missing_model_responses': transmitted_requests - n,
        'rate_denominator': 'actual model responses received, not requests or planned calls',
        'zero_denominator_rate': 'null', 'measurements': measurements,
        'successful_execution': 'completed read/list/write; shell completed with exit 0; finish is not a tool execution',
        'annotation_validity_is_truth': False, 'rows': rows}
    if action_wire_version is not None:
        report.update(action_wire_version=action_wire_version, wire_action_contract_version='4.0',
                      internal_action_contract_version='3.0',
                      action_schema_valid_definition='accepted wire action schema, before canonicalization and safety',
                      audit_assessment_boundary='static wire/canonical/safety assessment; runtime admission is recorded separately')
    return report


def measure_run(raw, validate_action, *, role='predecessor', action_contract_version='2.0', action_wire_version=None):
    require(action_wire_version in (None, ACTION_WIRE_VERSION), 'unsupported action wire version')
    events, _ = raw._read_chain()
    payloads = {e.id: json.loads(e.payload_json) for e in events}
    rows = []
    wire_requests = sorted(raw.path.glob('wire-request-*.json'))
    for request_path in wire_requests:
        number = int(request_path.stem.rsplit('-', 1)[1])
        body = json.loads(request_path.read_text())
        known = set()
        for message in body['messages']:
            if message['role'] != 'user': continue
            try: feedback = json.loads(message['content'])
            except (ValueError, TypeError): continue
            if isinstance(feedback, dict) and 'tool_result' in feedback and isinstance(feedback.get('event_id'), str):
                known.add(feedback['event_id'])
        row = {'call': number, 'model_response_received': False, 'response_rejected': False,
               'action_rejected': False, 'tool_execution_completed': False, 'tool_execution_successful': False,
               **assess_text(None, known, validate_action, action_contract_version, action_wire_version)}
        prefix = f'{role}_call_{number:03d}'
        if action_wire_version is not None:
            for suffix, field in (('action-wire','action_wire_audit'), ('action-admission','action_admission_audit')):
                path = raw.path / f'{prefix}-{suffix}.json'
                row[field] = json.loads(path.read_text()) if path.exists() else None
        response_path = raw.path / f'wire-response-{number:03d}.json'
        if not response_path.exists():
            row['diagnostics'] = [{'stage': 'transport', 'reason': 'no HTTP response body received/captured'}]
            rows.append(row)
            continue
        capture = json.loads(response_path.read_text())
        try:
            service = json.loads(base64.b64decode(capture['body_base64']))
            choices = service.get('choices', []) if isinstance(service, dict) else []
            message = choices[0].get('message') if choices and isinstance(choices[0], dict) else None
        except (ValueError, TypeError, KeyError):
            message = None
        if not isinstance(message, dict):
            row['diagnostics'] = [{'stage': 'transport', 'reason': 'received HTTP body has no model message; missing response, not invalid model JSON'}]
            rows.append(row)
            continue
        row.update(assess_text(message.get('content'), known, validate_action, action_contract_version, action_wire_version))
        row['model_response_received'] = True
        row['service_returned_model'] = service.get('model')
        row['service_reported_upstream'] = service.get('provider')
        row['finish_reason'] = choices[0].get('finish_reason')
        row['response_artifact'] = response_path.name
        for suffix in ('failure', 'protocol-failure', 'action-failure'):
            failure = raw.path / f'{prefix}-{suffix}.json'
            if failure.exists():
                row['response_rejected'] = True
                row['diagnostics'].append({'stage': 'actual_admission', 'artifact': failure.name,
                    'detail': json.loads(failure.read_text())})
        action = row['proposed_action']
        tool = payloads.get(f'{role}_tool_{number:03d}')
        # There is one model action per response; finish and invalid generations
        # stop, so prior tool numbering remains aligned throughout this check.
        result = payloads.get(f'{role}_result_{number:03d}')
        completed = tool is not None and result is not None and not any(k in result for k in ('invalid_action', 'infrastructure_failure'))
        row['tool_execution_completed'] = completed
        row['tool_execution_successful'] = completed and not result.get('cursor_stale',False) and (action.get('tool') != 'shell' or result.get('exit_code') == 0)
        row['response_rejected'] |= any(row[field] is False for field in (
            'json_syntax_valid', 'response_structure_valid', 'action_schema_valid', 'safety_valid'))
        row['action_rejected'] = isinstance(action, dict) and (row['response_rejected'] or bool(result and 'invalid_action' in result))
        if row['action_rejected']: row['response_rejected'] = True
        rows.append(row)
    report = summarize(rows, len(wire_requests), action_wire_version)
    report['generation_calls_logged'] = len(list(raw.path.glob(f'{role}_call_*-request.json')))
    report['calls_not_transmitted'] = report['generation_calls_logged'] - len(wire_requests)
    report['rejected_action_definition'] = 'an identifiable action proposal withheld by generation/response/safety admission or runtime rejection; not necessarily malformed'
    return report
