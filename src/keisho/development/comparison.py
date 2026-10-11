"""Freeze four conditions; optional gated continuation reuses the existing runner."""

import base64
from decimal import Decimal
from functools import partial
import hashlib
import json
from pathlib import Path
import random
import tempfile

from keisho.agents.base import Message,ModelRequest
from keisho.agents.providers.openai_chat import http_transport,ProviderFailure
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel,BASE_URL,MODEL_PRICES,RESERVATION_MULTIPLIER
from keisho.core import canonical_json,decode,digest,require,utc_now
from keisho.environments import FilesystemEnvironment,Evaluation
from keisho.environments.base import Snapshot,SnapshotFile
from keisho.handoff.bundle import validate,write
from keisho.handoff.compact import Counter,essential,item_text,PRIORITY
from keisho.local_env import load_project_env
from keisho.logging.raw import FrozenTrajectory,RawRun,EventKind,Event
from keisho.pilot.agent import Budgets,Recorder,run_agent,request_upper_bound
from keisho.pilot.calibration_block import load_config as load_provider_config
from keisho.pilot.runner import prompt
from keisho.pilot.spending import SpendLedger,BudgetedModel
from keisho.pilot.tasks import REPO
from .checkpoint import assess
from .suite import load_public,check_workspace,verify_development_sandbox,DevelopmentToolSession,evaluator_cases,grade_cases

DEFAULT=REPO/'configs/development-comparison-v1.json'
CONDITIONS=('NO_CONTEXT','FULL_HISTORY','SUMMARY_2K','KEISHO_2K')


def load_config(path=DEFAULT):
    data=json.loads(path.read_text())
    require(data['version']=='development-comparison/1.0' and tuple(data['conditions'])==CONDITIONS,'unsupported comparison config')
    require(data['paid_calls_authorized'] is False and data['automatic_retries']==0 and data['successor_conditioning'] is False,'explicit approval, no retries or conditioning required')
    provider_path=path.parent/data['provider_config'];provider,pilot=load_provider_config(provider_path)
    require(digest(provider)==data['provider_config_sha256'],'frozen provider configuration changed')
    require(data['checkpoint']=={'completed_tool_budget':12,'uses_hidden_grades':False} and data['handoff_token_budget']==2048,'prospective checkpoint or handoff budget changed')
    budgets=Budgets(**data['successor_budgets'])
    require(budgets.request_input_tokens<=32000 and budgets.output_tokens<=2048 and budgets.context_tokens<=128000,'unsupported request reservation')
    return data,provider,pilot,provider_path


def plan(path=DEFAULT):
    data,provider,pilot,_=load_config(path);budget=Budgets(**data['successor_budgets'])
    rate_in,_,rate_out=MODEL_PRICES[pilot.data['successor']['model_id']]
    outputs=min(budget.total_tokens,budget.model_calls*budget.output_tokens);inputs=budget.total_tokens-outputs
    return {'version':data['version'],'config_sha256':digest(data),'conditions':CONDITIONS,'source_material':'identical sealed observable predecessor record and public task',
            'generation':data['generation'],'generation_calls':0,'generation_cost_usd':'0','handoff_budget':2048,
            'full_history':'untruncated larger-context reference; reject if it cannot fit whole request/context budget',
            'checkpoint_policy':data['checkpoint'],'successor_model':provider['models']['successor'],'routing':provider['routing'],
            'successor_budgets':data['successor_budgets'],'maximum_successor_calls':4*budget.model_calls,
            'worst_case_successor_token_envelope':4*budget.total_tokens,
            'worst_case_successor_api_usage_usd':str(4*RESERVATION_MULTIPLIER*(inputs*rate_in+outputs*rate_out)/Decimal(1000000)),
            'paid_execution_authorized':False,'new_explicit_approval_and_supplied_shared_cap_required':True,
            'previous_calibration_authorization_reusable':False,'audit_archive_access':'denied in primary comparison; local evidence lookup is a separate operating mode',
            'units':'paired branches within checkpoint; repeated checkpoints/seeds are not independent tasks',
            'end_to_end_cost':'predecessor cost remains unknown unless complete reported accounting is imported; no zero assumption'}


def prose_summary(state,workspace,budget=2048,counter=None):
    counter=counter or Counter()
    # Identical essential task data and whole-record semantics, rendered as prose paragraphs.
    text=essential(state,workspace).replace('## Selected task state','## Continuation summary')
    selected=[];omitted=[]
    ordered=sorted(state['items'],key=lambda item:(PRIORITY[item['category']],item['id']))
    required_ids=set()
    for item in state['items']:
        if item.get('conflicts_with') or item.get('superseded_by'):
            required_ids.add(item['id']);required_ids.update(item.get('conflicts_with',[]))
            if item.get('superseded_by'):required_ids.add(item['superseded_by'])
    ordered.sort(key=lambda item:item['id'] not in required_ids)
    require(counter.count(text+'\n').count<=budget,'summary essential content over budget')
    for item in ordered:
        status={'OBSERVED':'a recorded observation','SUPPORTED_WITHIN_SCOPE':'supported only within the stated test/environment scope',
                'HYPOTHESIZED':'a hypothesis, not an established fact','UNCERTAIN':'uncertain','REJECTED_SUPPORTED':'rejected only within the recorded failure scope',
                'REJECTED_UNSUPPORTED':'a reported rejection without independently sufficient evidence','SUPERSEDED':'superseded by later information'}[item['status']]
        rendered=item['text'].rstrip('.')+'. This is '+status+'. '
        if item.get('imported_report'):rendered+='It is an imported, unverified report. '
        rendered+='Its scope is '+(', '.join(item['scope'].get('files',{})) or 'unknown files')+' in '+item['scope'].get('environment','an unknown environment')+'. '
        refs=item['source_ids']+item.get('evidence_ids',[])
        if refs:rendered+='The supporting source references are '+', '.join(dict.fromkeys(refs))+'; traceability alone does not prove the interpretation. '
        if item.get('retry_when'):rendered+='Reconsider this scoped approach when '+ '; '.join(item['retry_when'])+'. '
        if item.get('conflicts_with'):rendered+='It conflicts with '+', '.join(item['conflicts_with'])+'; both accounts are retained. '
        if item.get('superseded_by'):rendered+='Later record '+item['superseded_by']+' supersedes it. '
        if item.get('revalidation',{}).get('requires_revalidation'):rendered+='The recorded scope changed or is unknown; revalidate before relying on it. '
        if item.get('missing_evidence'):rendered+='Evidence references are missing: '+', '.join(item['missing_evidence'])+'. '
        candidate=text+'\n\n'+rendered
        if counter.count(candidate+'\n').count<=budget:text=candidate;selected.append(item['id'])
        elif item['id'] in required_ids:raise ValueError('summary conflict cannot fit without losing meaning')
        else:omitted.append(item['id'])
    return text+'\n',{'generator':'deterministic-prose/1.0','api_calls':0,'selected_ids':selected,'omitted_ids':omitted,'count':counter.count(text+'\n').__dict__}


def snapshot(bundle,workspace,task):
    files=[];dirs=set()
    for row in workspace['files']:
        require(row['path'] in task.files or row['path'].startswith('.runtime/'),'research workspace contains non-task files; remove audit/session material before preparing')
        require(row['mode'] in (0o600,0o644,0o700,0o755),'research snapshot mode outside existing environment contract')
        files.append(SnapshotFile(row['path'],base64.b64encode((bundle/'workspace'/row['path']).read_bytes()).decode(),row['mode']))
        parent=Path(row['path']).parent
        while parent.as_posix()!='.':dirs.add(parent.as_posix());parent=parent.parent
    require(set(task.files)<={row.path for row in files},'research task workspace incomplete')
    for row in workspace['directories']:
        require(row['path'] in dirs or row['path']=='.runtime' or row['path'].startswith('.runtime/'),'research workspace contains a non-task directory')
        dirs.add(row['path'])
    return Snapshot.create(tuple(files),tuple(dirs))


def prepare(case_id,bundle,out,seed=17,mode='prospective',config=DEFAULT):
    bundle=Path(bundle).resolve();out=Path(out).resolve();require(not out.exists(),'comparison output already exists')
    data,provider,pilot,_=load_config(config)
    manifest,state,workspace=validate(bundle);task,public=load_public(case_id)
    require(state['extraction']['format']=='keisho-frozen-trajectory/0.1.0','research preparation requires a supported sealed tool trace; notes remain available for manual use')
    archive=json.loads((bundle/'evidence/session.json').read_text());trajectory=FrozenTrajectory.create(tuple(decode(Event,event) for event in archive['events']))
    original_goal=next((json.loads(event.payload_json).get('content') for event in trajectory.events if event.id.endswith('_task')),None)
    require(state['goal']==original_goal==task.description,'original public task must be identical across conditions')
    frozen=snapshot(bundle,workspace,task)
    with tempfile.TemporaryDirectory(prefix='keisho-checkpoint-public-') as temporary:
        root=Path(temporary).resolve();sandbox=verify_development_sandbox(root)
        environment=FilesystemEnvironment(root/'checkpoint',{},lambda _:Evaluation(None,'public-only probe','1'))
        environment.restore(frozen)
        grade=check_workspace(case_id,environment.workspace,sandbox,public_only=True)
    qualification=assess(trajectory,grade['results'],mode,data['checkpoint']['completed_tool_budget'])
    out.mkdir(parents=True,exist_ok=False);write(out/'INCOMPLETE','comparison preparation incomplete\n')
    write(out/'checkpoint.json',canonical_json(qualification)+'\n');write(out/'public-grade.json',canonical_json(grade)+'\n')
    write(out/'snapshot.json',canonical_json(frozen)+'\n');write(out/'task.json',canonical_json({'id':case_id,'sha256':task.sha256,'description':task.description,'origin':public['origin']})+'\n')
    write(out/'audit/session.json',canonical_json(archive)+'\n');write(out/'audit/state.json',canonical_json(state)+'\n')
    counter=Counter();require(counter.native is not None,'research comparisons require the pinned exact native tokenizer')
    summary,summary_meta=prose_summary(state,workspace,2048,counter)
    texts={'NO_CONTEXT':'','FULL_HISTORY':canonical_json(archive['events']),'SUMMARY_2K':summary,'KEISHO_2K':(bundle/'handoff.md').read_text()}
    require(manifest['token_counts']['compact']['budget']==2048 and counter.count(texts['KEISHO_2K']).count<=2048,'compact handoff must use the matched 2048-token budget')
    budgets=Budgets(**data['successor_budgets'])
    for condition,text in texts.items():
        request=ModelRequest((Message('system',prompt('agent')),Message('user',task.description),Message('user',text)),seed,budgets.output_tokens,0.0)
        estimate=sum(counter.count(message.content).count for message in request.messages)+1024+16*len(request.messages)
        require(estimate<=budgets.request_input_tokens and estimate+budgets.output_tokens<=budgets.context_tokens,f'{condition}: full request cannot fit; no truncation permitted')
        write(out/'conditions'/(condition+'.md'),text)
    order=list(CONDITIONS);random.Random(seed).shuffle(order)
    prepared={'version':'prepared-comparison/1.0','created_at':utc_now(),'config':data,'config_sha256':digest(data),'case_id':case_id,'task_sha256':task.sha256,
              'snapshot_sha256':frozen.sha256,'source_bundle_sha256':manifest['sha256'],'source_material_sha256':digest(archive['events']),
              'seed':seed,'branch_order':order,'checkpoint_qualified':qualification['continuation_eligible'],
              'conditions':{condition:{'sha256':hashlib.sha256(text.encode()).hexdigest(),'tokens':counter.count(text).__dict__} for condition,text in texts.items()},
              'summary_generation':summary_meta,'keisho_generation':{'generator':'compact/1.0','api_calls':0},
              'predecessor_reported_cost_usd':archive.get('accounting',{}).get('reported_cost_usd'),'generation_cost_usd':'0','api_calls':0,'human_review_complete':False,'evaluation_pooling_allowed':False,
              'audit_access_mode':'archive outside every successor workspace; no evidence fetch tool','paid_calls_authorized':False}
    artifacts={str(path.relative_to(out)):hashlib.sha256(path.read_bytes()).hexdigest() for path in out.rglob('*') if path.is_file() and path.name!='INCOMPLETE'}
    prepared['artifacts']=artifacts;prepared['sha256']=digest(prepared)
    write(out/'manifest.json',canonical_json(prepared)+'\n');(out/'INCOMPLETE').unlink()
    return prepared


def load_prepared(path):
    require(not (path/'INCOMPLETE').exists(),'interrupted comparison preparation')
    require(path.is_dir() and not path.is_symlink(),'comparison directory missing or symlinked')
    data=json.loads((path/'manifest.json').read_text());claimed=data['sha256'];unhashed=dict(data);del unhashed['sha256']
    require(digest(unhashed)==claimed,'comparison manifest integrity mismatch')
    require(data['version']=='prepared-comparison/1.0','unsupported prepared comparison')
    from keisho.environments.base import safe_relative_path
    actual=set()
    for file in path.rglob('*'):
        require(not file.is_symlink(),'comparison contains symlink')
        if file.is_file():actual.add(str(file.relative_to(path)))
    require(actual==set(data['artifacts'])|{'manifest.json'},'comparison inventory mismatch')
    for relative,sha in data['artifacts'].items():
        safe_relative_path(relative);require(hashlib.sha256((path/relative).read_bytes()).hexdigest()==sha,'comparison artifact integrity mismatch')
    require(digest(data['config'])==data['config_sha256'],'comparison config binding mismatch')
    return data


class DevelopmentSpendLedger(SpendLedger):
    """Same request controls; new explicit run authorization, never historical approval."""
    def __init__(self,cap,emit,*,fresh_explicit_approval):
        require(fresh_explicit_approval is True,'new paid-run approval required')
        supplied=Decimal(cap);require(supplied.is_finite() and supplied>0,'supply a positive shared dollar cap')
        super().__init__('1.25',emit,provider='openrouter')
        self.cap=supplied


def execute(prepared_path,cap,*,approve_live=False,factory=None,synthetic=False,raw_root=None):
    require((approve_live and not synthetic) or (synthetic and not approve_live and factory is not None),'live continuation requires fresh --approve-live; offline requires injected transport')
    prepared_path=Path(prepared_path).resolve();data=load_prepared(prepared_path)
    current,provider,pilot,provider_path=load_config()
    require(digest(current)==data['config_sha256'],'prepared configuration changed')
    raw_root=raw_root or REPO/('runs/development-offline' if synthetic else 'runs/development-real')
    index=RawRun(raw_root,'continuation-'+data['sha256'][:24])
    recorder=Recorder(index);number=0
    def emit(record):
        nonlocal number
        number+=1;recorder.emit(f'spend{number}',EventKind.ANNOTATION,'spending-control',record)
    ledger=DevelopmentSpendLedger(cap,emit,fresh_explicit_approval=True)
    index.write_artifact('plan.json',plan());index.write_artifact('authorization.json',{'fresh_explicit_live_approval':approve_live,'synthetic':synthetic,'shared_cap_usd':str(ledger.cap),'previous_calibration_approval_used':False})
    branches=[];status='checkpoint_ineligible'
    try:
        if data['checkpoint_qualified']:
            if not synthetic:load_project_env(REPO)
            task,_=load_public(data['case_id']);require(task.sha256==data['task_sha256'],'public task changed after preparation')
            evaluation_cases=task.cases+evaluator_cases(task.id)
            index.write_artifact('evaluation-contract.json',{'evaluator_only':True,'cases':evaluation_cases,'sha256':digest(evaluation_cases),
                                'scoring':'behavior-json/1.0','stopping':'public full-suite pass, finish, fixed continuation budgets, or block failure/budget stop'})
            frozen=decode(Snapshot,json.loads((prepared_path/'snapshot.json').read_text()));frozen.validate()
            counter=Counter();require(counter.native is not None,'native tokenizer required')
            budgets=Budgets(**current['successor_budgets'])
            with tempfile.TemporaryDirectory(prefix='keisho-continuations-') as temporary:
                root=Path(temporary).resolve();sandbox=verify_development_sandbox(root)
                status='complete'
                for condition in data['branch_order']:
                    if ledger.stopped:status='spending_stopped';break
                    raw=RawRun(raw_root,index.path.name+'-'+condition)
                    environment=FilesystemEnvironment(root/condition,{},lambda _:Evaluation(None,'host evaluator after stop','1'))
                    environment.restore(frozen);require(environment.snapshot()==frozen,'checkpoint restoration changed')
                    identity=pilot.data['successor']['model_id']
                    if factory:model=factory(condition)
                    else:model=OpenRouterChatModel(identity,authorized=True,tokenizer=counter.native,
                        response_model_ids=provider['models']['successor']['accepted_response_model_ids'],
                        transport=partial(http_transport,base_url=BASE_URL,provider='OpenRouter',ca_file=(provider_path.parent/provider['tls']['ca_file']).resolve()))
                    require(model.model_id()==identity,'no model substitution')
                    guarded=BudgetedModel(model,ledger,'successor',identity)
                    text=(prepared_path/'conditions'/(condition+'.md')).read_text()
                    raw.write_artifact('manifest.json',{'condition':condition,'prepared_sha256':data['sha256'],'snapshot_sha256':frozen.sha256,'model_id':identity,
                        'provider_configuration':provider,'budgets':current['successor_budgets'],'task_sha256':task.sha256,'seed':data['seed'],
                        'tool_access':'same public TaskSession; no archive/evaluator access','synthetic':synthetic})
                    execution=run_agent(guarded,DevelopmentToolSession(task,environment.workspace,sandbox),Recorder(raw),task.description,prompt('agent'),text,data['seed'],budgets)
                    raw.freeze();raw.write_artifact('calls.json',execution.calls);raw.write_artifact('execution.json',execution)
                    raw.write_artifact('final-workspace.json',environment.snapshot())
                    if execution.reason in ('model_failure','infrastructure_failure','invalid_run'):
                        grade=None;success=None;status=execution.reason
                    else:
                        grade=grade_cases(environment.workspace,sandbox,evaluation_cases,task.files['diagnostics.py']);success=all(row['passed'] for row in grade['results'])
                    result={'condition':condition,'task_success':success,'grade':grade,'model_calls':execution.model_calls,'tool_calls':execution.tool_calls,
                        'continuation_tokens':sum(call.usage.input_tokens+call.usage.output_tokens for call in execution.calls) if all(call.usage.input_tokens is not None and call.usage.output_tokens is not None for call in execution.calls) else None,
                        'handoff_tokens':data['conditions'][condition]['tokens'],'reported_continuation_cost_usd':str(sum((Decimal(call.usage.cost_usd) for call in execution.calls),Decimal(0))) if all(call.usage.cost_usd is not None for call in execution.calls) else None,
                        'human_source_exclusion_review_complete':False,'human_behavior_review_complete':False,'synthetic':synthetic}
                    raw.write_artifact('result.json',result)
                    from .review import review_candidates
                    raw.write_artifact('review.json',review_candidates(prepared_path,raw,task))
                    branches.append(result)
                    if ledger.stopped:status='spending_stopped';break
                    if status!='complete':break
    except Exception as exc:
        status='infrastructure_or_validation_failure';index.write_artifact('failure.json',{'exception_type':type(exc).__name__,'reason':str(exc),'no_retry':True})
        # Preserve launched partial branches; never label attempted work unstarted.
        for condition in data['branch_order']:
            path=Path(raw_root)/(index.path.name+'-'+condition)
            if path.exists() and condition not in [row['condition'] for row in branches]:
                raw=RawRun.__new__(RawRun);raw.path=path
                if not (path/'trajectory.json').exists():raw.freeze()
                events=raw.load_frozen().events
                partial={'condition':condition,'task_success':None,'status':'INFRASTRUCTURE_OR_VALIDATION_FAILURE',
                         'model_calls':sum(event.kind.value=='model_request' for event in events),
                         'tool_calls':sum(event.kind.value=='tool_call' for event in events),'continuation_tokens':None,'synthetic':synthetic}
                if not (path/'result.json').exists():raw.write_artifact('result.json',partial)
                branches.append(partial)
    index.write_artifact('spending.json',ledger.report())
    index.write_artifact('result.json',{'status':status,'branches':branches,'unstarted_conditions':[condition for condition in data['branch_order'] if condition not in [row['condition'] for row in branches]],
                                      'generation_calls':0,'generation_cost_usd':'0','new_api_usage_accounted_usd':str(ledger.accounted),'predecessor_cost_usd':data.get('predecessor_reported_cost_usd'),
                                      'end_to_end_cost_usd':str(ledger.accounted+Decimal(data['predecessor_reported_cost_usd'])) if data.get('predecessor_reported_cost_usd') is not None and not ledger.held else None,
                                      'end_to_end_limitation':'Unknown predecessor or unreconciled new usage remains unknown; prior reported cost is separate from new authorized usage','synthetic':synthetic,'human_review_complete':False})
    index.freeze();return index.path
