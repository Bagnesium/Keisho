"""Prospective, deterministic wire adaptation; never chooses or repairs actions."""
from copy import deepcopy

from keisho.core import require
from .response_policy import agent_response_format, parse_unique_json, validate_recordable_json

VERSION = 'flat-or-args/1.0'


def _input_shape(action):
    return ('unrecognized' if not isinstance(action,dict) else
            'flat' if 'args' not in action else
            'nested_args' if set(action)=={'tool','args'} else 'mixed')


def rejected_response(reason, *, text=None, stage='response', shape='unassessable'):
    """Record identifiable input without admitting an already rejected response."""
    original = None
    if isinstance(text,str):
        try:
            data = parse_unique_json(text)
        except (ValueError,TypeError):
            shape = 'unparseable'
        else:
            try:
                validate_recordable_json(data)
            except ValueError:
                stage = 'encoding'
            if isinstance(data,dict) and 'action' in data:
                shape = _input_shape(data['action'])
                try:
                    validate_recordable_json(data['action'])
                except ValueError:
                    stage = 'encoding'
                else:
                    original = data['action']
    return {'wire_version':VERSION, 'input_action_shape':shape, 'original_action':original,
            'canonicalization_occurred':False, 'canonical_action':None,
            'wire_schema_valid':None, 'canonical_schema_valid':None,
            'validation_result':'rejected', 'validation_stage':stage,
            'rejection_reason':reason, 'safety_valid':None}


def canonicalize_action(action, validate_action):
    """Return an audit containing the sole admitted flat action, or a rejection.

    Nested arguments must be the action's only argument location. No values are
    merged, coerced, defaulted or substituted. The existing session validator
    retains authority over workspace paths and permitted operations.
    """
    from jsonschema import Draft202012Validator

    shape = _input_shape(action)
    report = {'wire_version':VERSION, 'input_action_shape':shape,
              'original_action':deepcopy(action), 'canonicalization_occurred':False,
              'canonical_action':None, 'wire_schema_valid':False,
              'canonical_schema_valid':None, 'validation_result':'rejected',
              'validation_stage':'wire_schema', 'rejection_reason':None, 'safety_valid':None}
    def reject(reason):
        report['rejection_reason'] = reason
        return report
    try:
        validate_recordable_json(action)
    except ValueError as exc:
        report.update(original_action=None, wire_schema_valid=None, validation_stage='encoding')
        return reject(str(exc))
    if not isinstance(action,dict): return reject('action must be an object')
    tool = action.get('tool')
    variants = agent_response_format('3.0')['json_schema']['schema']['properties']['action']['anyOf']
    by_tool = {item['properties']['tool'].get('const',item['properties']['tool'].get('enum',[None])[0]):item for item in variants}
    if not isinstance(tool,str) or tool not in by_tool: return reject('unknown tool name')
    if shape=='mixed': return reject('conflicting argument locations: args cannot coexist with flat arguments')
    arguments = action.get('args') if shape=='nested_args' else {key:value for key,value in action.items() if key!='tool'}
    if not isinstance(arguments,dict): return reject('args must be an object')
    flat_schema = by_tool[tool]
    allowed = set(flat_schema['properties'])-{'tool'}
    unknown = sorted(set(arguments)-allowed)
    if unknown: return reject('unknown arguments for '+tool+': '+', '.join(unknown))
    missing = sorted(set(flat_schema['required'])-{'tool'}-set(arguments))
    if missing: return reject('missing arguments for '+tool+': '+', '.join(missing))
    wire_schema = agent_response_format('4.0')['json_schema']['schema']['properties']['action']
    errors = sorted(Draft202012Validator(wire_schema).iter_errors(action), key=lambda error:error.message)
    if errors: return reject('invalid action argument types or structure: '+errors[0].message)
    report['wire_schema_valid'] = True
    canonical = {'tool':tool, **deepcopy(arguments)}
    report['canonical_action'] = canonical
    report['canonicalization_occurred'] = shape=='nested_args'
    report['validation_stage'] = 'canonical_schema'
    errors = sorted(Draft202012Validator(flat_schema).iter_errors(canonical), key=lambda error:error.message)
    report['canonical_schema_valid'] = not errors
    if errors: return reject('invalid canonical action: '+errors[0].message)
    report['validation_stage'] = 'safety'
    try:
        require(callable(validate_action), 'action-wire amendment requires independent action validator')
        if tool!='finish': validate_action(canonical)
    except (ValueError,TypeError) as exc:
        report['safety_valid'] = False
        return reject(str(exc))
    report.update(validation_result='accepted', validation_stage='accepted', safety_valid=True)
    return report
