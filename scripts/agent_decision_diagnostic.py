"""Four fixed non-executing decisions, then at most one fresh fixture check."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from jsonschema import Draft202012Validator
from keisho.agents.base import ModelRequest
from keisho.agents.providers.openai_chat import http_transport
from keisho.agents.providers.openrouter_chat import BASE_URL, OpenRouterChatModel
from keisho.benchmark.comparison import (read_input, check_public_catalog, response_settings,
        SPEC_SHA, PROVIDER_SHA, IMAGE_METADATA_SHA)
from keisho.benchmark.environment import RepositorySession, docker
from keisho.core import canonical_json, decode, digest, require
from keisho.local_env import load_project_env
from keisho.logging.raw import RawRun, EventKind
from keisho.metrics.definitions import CallPurpose
from keisho.pilot.agent import Budgets, Recorder, logged_generate, parse_output, run_agent, request_upper_bound
from keisho.pilot.response_policy import AUXILIARY
from keisho.pilot.spending import BudgetedModel, SpendLedger
from keisho.pilot.tokenizer import NativeTokenizer
from scripts.benchmark_functional_check import AcceptanceBoundary, initialize_public_fixture, assess_public_fixture

CONFIG = ROOT / 'configs/listing-decision-diagnostic-v1.json'
AUTH = ROOT / 'results/listing-decision-diagnostic/authorization.json'
OUTPUT = ROOT / 'runs/listing-decision-diagnostic-v1'
PRIOR = ROOT / 'runs/swebench-integration/interface-diagnosis-v1/functional'

from keisho.benchmark.inspection import information_action

def assess_probe(text, known, files, schema, finish_reason='stop'):
    result = {'parse_valid': False, 'action_schema_valid': None, 'safety_valid': None,
              'proposed_action': None, 'would_obtain_relevant_new_information': None,
              'qualifies': False, 'actions_executed': 0, 'semantic_assessment': 'model-assisted, prospectively specified; no human review'}
    try: parsed = parse_output(text, known, AUXILIARY)
    except (ValueError, TypeError) as exc:
        result.update(parse_error=str(exc), annotation_information='unknown; response not parsed')
        return result
    action = parsed['action']
    result.update(parse_valid=True, proposed_action=action, annotations=parsed['annotation_report'])
    errors = list(Draft202012Validator(schema['json_schema']['schema']['properties']['action']).iter_errors(action))
    result['action_schema_valid'] = not errors
    result['action_schema_errors'] = [e.message for e in errors]
    try:
        if action.get('tool') == 'finish':
            require(set(action) == {'tool','answer'} and isinstance(action['answer'],str), 'invalid finish action')
        else:
            admission = RepositorySession.__new__(RepositorySession)
            admission.output_bytes = 49152
            admission.validate_action(action)
        result['safety_valid'] = True
    except (ValueError, TypeError) as exc:
        result.update(safety_valid=False, safety_error=str(exc))
    if result['action_schema_valid'] and result['safety_valid']:
        info, reason = information_action(action, files)
        result.update(would_obtain_relevant_new_information=info, information_reason=reason)
        result['qualifies'] = info is True and finish_reason == 'stop'
    result['finish_reason'] = finish_reason
    return result

def select_cell(results):
    return next((c for c in ('A','B','C','D') if results[c].get('qualifies') is True), None)

def adapter(cell, provider, native, transport=None, authorized=False):
    frozen = read_input(ROOT / 'configs/swebench-comparison-v1.1.json')
    schema = response_settings(frozen)[2] if cell['output_mode']=='json_schema' else None
    kwargs = {} if transport is None else {'transport':transport}
    return OpenRouterChatModel(cell['model_id'], authorized=authorized, tokenizer=native, mode='agent',
            response_model_ids=provider['models'][cell['role']]['accepted_response_model_ids'],
            agent_response_format=schema, **kwargs)

def execute(approve_live=False):
    require(approve_live is True, 'explicit decision diagnostic approval required')
    require(not OUTPUT.exists(), 'diagnostic guard already claimed; no retry or extra trials')
    config, auth = read_input(CONFIG), read_input(AUTH)
    require(digest(config)==auth['config_sha256'] and auth['cap_usd']==config['cap_usd']=='2.00', 'diagnostic configuration/authorization changed')
    require(config['order']==['A','B','C','D'] and config['probe_calls_per_cell']==1, 'probe count/order changed')
    frozen = read_input(ROOT / 'configs/swebench-comparison-v1.1.json')
    require(digest(frozen)==SPEC_SHA, 'original scientific specification changed')
    system, policy, schema = response_settings(frozen)
    require(policy==AUXILIARY and digest(schema)==config['schema_sha256'], 'response contract changed')
    provider = read_input(ROOT / 'configs' / frozen['provider_config'])
    require(digest(provider)==PROVIDER_SHA, 'provider mapping/routing changed')
    request = decode(ModelRequest,read_input(PRIOR / 'predecessor_call_002-request.json'))
    initial = decode(ModelRequest,read_input(PRIOR / 'predecessor_call_001-request.json'))
    fixture = read_input(PRIOR / 'fixture.json')
    require(digest(request)==config['probe_input_sha256'] and digest(initial)==config['confirmation_input_sha256'] and
            digest(fixture['original_files'])==config['fixture_sha256'], 'saved inputs changed')
    require(len(request.messages)==5 and len(initial.messages)==3 and request.messages[:3]==initial.messages, 'wrong conversation boundary')
    require(initial.messages[0].content==system and initial.messages[1].content==fixture['objective'], 'original prompts changed')
    expected = [('A','predecessor','json_schema'),('B','predecessor','json_object'),('C','successor','json_schema'),('D','successor','json_object')]
    for cell, (label,role,mode) in zip(config['cells'],expected):
        require(cell['id']==label and cell['role']==role and cell['output_mode']==mode and cell['model_id']==frozen[role+'_model'], 'cell settings changed')
    require(len(config['cells'])==4 and config['confirmation_budgets']=={**read_input(PRIOR/'config.json')['budgets']}, 'confirmation budgets changed')
    require(config['confirmation_budgets']['model_calls']==8 and config['confirmation_budgets']['tool_calls']==8, 'confirmation call bounds changed')
    ca = (ROOT / 'configs' / provider['tls']['ca_file']).resolve()
    require(hashlib.sha256(ca.read_bytes()).hexdigest()==provider['tls']['ca_sha256'], 'verified CA changed')
    require(load_project_env(ROOT)['present']['OPENROUTER_API_KEY'], 'configured credential missing')
    native = NativeTokenizer()
    catalog = check_public_catalog(ca)  # Unauthenticated public support/pricing, no paid smoke call.
    for cell in config['cells']:
        model = adapter(cell,provider,native)
        require(digest(model.body(request))==cell['wire_body_sha256'], 'cell serialization changed')
        require(request_upper_bound(model,request)<=32000, 'probe input exceeds frozen bound')
    maximum = Decimal(config['maximum_reservations_usd'])
    require(maximum==Decimal('0.87779328') and maximum<=Decimal(config['cap_usd']), 'planned reservations do not fit cap')
    raw = RawRun(OUTPUT.parent,OUTPUT.name)  # One exclusive guard for all stages.
    rec = Recorder(raw)
    count = 0
    def emit(row):
        nonlocal count
        count += 1
        rec.emit(f'spend-{count}',EventKind.ANNOTATION,'spending-control',row)
    ledger = SpendLedger('2.00',emit,provider='openrouter',authorized_ceiling_usd=auth['cap_usd'],authorization_scope='agent-decision-diagnostic')
    raw.write_artifact('authorization.json',auth)
    raw.write_artifact('launch.json',{'approve_live':True,'config_sha256':digest(config),'new_cap_usd':'2.00','old_authorizations_reopened':False})
    raw.write_artifact('config.json',config)
    raw.write_artifact('public-catalog.json',catalog)
    results = {c:{'status':'unstarted','qualifies':False} for c in config['order']}
    confirmation = {'status':'unstarted'}
    overall = 'interrupted'
    try:
        for cell in config['cells']:
            if ledger.stopped: break
            results[cell['id']]={'status':'started','qualifies':False,'actions_executed':0}
            probe = RawRun(raw.path,cell['id'])
            def transport(body,key):
                probe.write_artifact('wire-request.json',body)
                return http_transport(body,key,base_url=BASE_URL,provider='OpenRouter',ca_file=ca)
            model = BudgetedModel(adapter(cell,provider,native,transport,True),ledger,'probe_'+cell['id'],cell['model_id'])
            response,call = logged_generate(model,request,Recorder(probe),cell['id'],CallPurpose.PREDECESSOR,1)
            probe.write_artifact('call.json',call)
            if response is None:
                row = {'status':'provider_error','qualifies':False,'actions_executed':0}
            else:
                require(response.usage.input_tokens<=request_upper_bound(model,request) and response.usage.output_tokens<=request.max_output_tokens, 'provider usage exceeds request bounds')
                row = {'status':'responded',**assess_probe(response.text,{'predecessor_result_001'},fixture['original_files'],schema,response.finish_reason),
                       'requested_model':response.requested_model_id,'returned_model':response.resolved_model_id,
                       'reported_upstream_provider':response.upstream_provider,'usage':response.usage,
                       'returned_content_equals_parser_input':json.loads(response.raw_response_json)['choices'][0]['message']['content']==response.text}
            probe.write_artifact('assessment.json',row)
            probe.freeze()
            results[cell['id']]=row
        selected = select_cell(results)
        raw.write_artifact('selection.json',{'selected_cell':selected,'preference_order':config['order'],'probe_actions_executed':0})
        if selected is None or ledger.stopped:
            overall = 'stopped_no_qualifying_cell' if not ledger.stopped else 'spending_stopped'
        else:
            cell = next(c for c in config['cells'] if c['id']==selected)
            rates = ledger.prices[cell['model_id']]
            headroom = ledger.multiplier * 8 * (32000*rates[0]+2048*rates[2])/1000000
            require(ledger.accounted+ledger.held+headroom<=ledger.cap, 'remaining budget cannot reserve one full confirmation')
            image = read_input(ROOT/'.cache/swebench-evaluator/prepared-task-image.json')
            require(digest(image)==IMAGE_METADATA_SHA and image['image_id']==fixture['image_id'], 'prepared environment identity changed')
            require(json.loads(docker('image','inspect',image['image_id']).stdout)[0]['Id']==image['image_id'], 'prepared image unavailable')
            check = RawRun(raw.path,'confirmation')
            check.write_artifact('selection.json',{'cell':cell,'fresh_initial_input_sha256':digest(initial),'probe_response_included':False})
            session = None
            try:
                session = RepositorySession(image['image_id'],audit=check)
                base = initialize_public_fixture(session,check,fixture['original_files'])
                def transport(body,key):
                    check.write_artifact(f'wire-request-{len(ledger.records):03d}.json',body)
                    return http_transport(body,key,base_url=BASE_URL,provider='OpenRouter',ca_file=ca)
                model = BudgetedModel(adapter(cell,provider,native,transport,True),ledger,'confirmation',cell['model_id'])
                boundary = AcceptanceBoundary()
                execution = run_agent(model,session,Recorder(check),initial.messages[1].content,initial.messages[0].content,
                    initial.messages[2].content,initial.seed,Budgets(**config['confirmation_budgets']),role='predecessor',
                    checkpoint_predicate=boundary,time_limit_seconds=600,response_policy=policy)
                confirmation = {'selected_cell':selected,**assess_public_fixture(session,check,base,execution,boundary)}
                overall = 'confirmation_'+confirmation['status']
            finally:
                if session is not None:
                    try: session.close()
                    except Exception as exc:
                        confirmation.update(status='error',cleanup_exception=type(exc).__name__,cleanup_reason=str(exc))
                        overall='stopped_on_error'
                check.write_artifact('result.json',confirmation)
                check.freeze()
    except Exception as exc:
        raw.write_artifact('failure.json',{'exception':type(exc).__name__,'reason':str(exc),'automatic_retry':False})
        overall='stopped_on_error'
    finally:
        ledger.stop(ledger.reason or 'four-probe/one-confirmation diagnostic ended; no more calls authorized')
        raw.write_artifact('spending.json',ledger.report())
        raw.write_artifact('result.json',{'status':overall,'probes':results,'confirmation':confirmation,'swebench_executed':False})
        raw.freeze()
    print('Artifacts:',raw.path)
    print('Status:',overall)
    return 0 if overall in ('confirmation_passed','stopped_no_qualifying_cell') else 1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approve-live',action='store_true')
    return execute(p.parse_args().approve_live)

if __name__=='__main__':raise SystemExit(main())
