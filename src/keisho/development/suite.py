"""Public task loading and offline behavioral reference validation."""

import json
from pathlib import Path
import random
import tempfile

from keisho.core import digest,require,utc_now
from keisho.pilot.cli import verify_sandbox
from keisho.pilot.sandbox import MacSandbox,score_cases
from keisho.pilot.tasks import PublicTask,REPO
from keisho.pilot.tools import ToolSession

ROOT=REPO/'tasks/development'
IDS=('jobs_duplicate','jobs_recovery','migration_compat','migration_cache','index_update','index_delete')


def behavior_equal(actual,expected):
    """JSON contract equality; equal finite numeric values need not have identical spelling."""
    if type(actual) in (int,float) and type(expected) in (int,float):return actual==expected
    if type(actual)!=type(expected):return False
    if isinstance(actual,dict):return actual.keys()==expected.keys() and all(behavior_equal(actual[key],expected[key]) for key in actual)
    if isinstance(actual,list):return len(actual)==len(expected) and all(behavior_equal(a,b) for a,b in zip(actual,expected))
    return actual==expected


def reconcile_numeric_results(result):
    for row in result['results']:
        if 'value' in row and 'expected' in row:row['passed']=behavior_equal(row['value'],row['expected'])
    return result


class DevelopmentToolSession(ToolSession):
    def execute(self,action):
        result=super().execute(action)
        if action.get('tool')=='run_tests':reconcile_numeric_results(result)
        return result


class DevelopmentSandbox(MacSandbox):
    """Existing isolation with writes limited to a per-workspace SQLite scratch area."""
    def _profile(self,workspace):
        profile=super()._profile(workspace)
        clause='(require-not (subpath "/dev"))'
        require(profile.count(clause)==1,'base isolation profile changed; do not broaden permissions silently')
        return profile.replace(clause,'(require-not (require-any (subpath "/dev") (subpath '+json.dumps(str((workspace/'.runtime').resolve()))+')))',1)


def load_public(case_id):
    require(case_id in IDS,'unknown development case')
    public=json.loads((ROOT/case_id/'public.json').read_text())
    files={p.name:p.read_text() for p in (ROOT/'applications'/public['family']).glob('*.py')}
    for p in (ROOT/case_id/'initial-overrides').glob('*.py'):files[p.name]=p.read_text()
    files['CONTRACT.md']=public['description']+'\n\nAcceptance:\n'+'\n'.join('- '+value for value in public['acceptance'])+'\n\nConstraints:\n'+'\n'.join('- '+value for value in public['constraints'])+'\n'
    files['public_tests.json']=json.dumps(public['cases'],indent=2,ensure_ascii=False)+'\n'
    description=files['CONTRACT.md']+'\nDiagnose and continue the unfinished implementation. Public diagnostics use deterministic SQLite persistence and scheduling. No particular wrong hypothesis or failed approach is required.'
    return PublicTask(case_id,public['version'],description,files,tuple(public['editable_files']),tuple(public['cases']),digest({'public':public,'files':files})),public


def property_case(family,seed):
    rng=random.Random(seed)
    if family=='jobs':
        jobs=[{'id':f'job{n}','payload':{'amount':rng.randint(1,9),'recipient':f'team{rng.randrange(3)}','failures':rng.randrange(3)}} for n in range(12)]
        ops=[];balances={}
        for job in jobs:
            ops.append({'op':'enqueue',**job});balances[job['payload']['recipient']]=balances.get(job['payload']['recipient'],0)+job['payload']['amount']
            if rng.choice((True,False)):ops.append({'op':'enqueue',**job})
        ops += [{'op':'step','now':0},{'op':'restart'},{'op':'drain'}]
        args={'ops':ops,'select':['balances','completed','effects','pending']}
        expected={'balances':balances,'completed':12,'effects':12,'pending':0}
    elif family=='migration':
        configs=[];modern=[]
        for n in range(12):
            timeout=rng.choice([250,1000,2000]);attempts=rng.randint(1,5)
            if n%2:raw={'endpoint':'shared','timeout':timeout/1000,'retries':attempts-1}
            else:raw={'endpoint':'shared','version':2,'request':{'timeout_ms':timeout,'max_attempts':attempts}}
            configs.append(raw);modern.append({'endpoint':'shared','timeout_ms':timeout,'max_attempts':attempts})
        args={'configs':configs,'select':['modern','errors']};expected={'modern':modern,'errors':0}
    else:
        current={};versions={};ops=[];changes=[]
        for _ in range(32):
            key=f'doc{rng.randrange(6)}'
            if rng.randrange(4)==0:
                ops.append({'op':'delete','id':key});current.pop(key,None);versions.pop(key,None)
            else:
                text=f'word{rng.randrange(5)} marker{rng.randrange(7)}';changed=current.get(key)!=text
                versions[key]=(versions.get(key,0)+1) if changed else versions[key];current[key]=text
                changes.append(changed);ops.append({'op':'update','id':key,'text':text})
            if rng.randrange(8)==0:ops.append({'op':'restart'})
        args={'ops':ops,'select':['documents','stored_chunks','orphans','changes']}
        expected={'documents':{key:{'version':versions[key],'chunks':1} for key in current},'stored_chunks':len(current),'orphans':0,'changes':changes}
    return {'id':f'generated_{family}_seed_{seed}','module':'diagnostics','function':'run_scenario','args':[args],'expected':expected}


def evaluator_cases(case_id):
    """Host evaluator only; never called by compiler or checkpoint selection."""
    _,public=load_public(case_id)
    private=json.loads((ROOT/'private'/case_id/'evaluator.json').read_text())
    return tuple(private['cases'])+tuple(property_case(public['family'],seed) for seed in private['property_seeds'])


def write_workspace(path,files):
    path.mkdir(exist_ok=False)
    for name,content in files.items():(path/name).write_text(content)
    (path/'.runtime').mkdir()


def grade_cases(workspace,sandbox,cases,diagnostics):
    (workspace/'.runtime').mkdir(exist_ok=True)
    require((workspace/'diagnostics.py').read_text()==diagnostics,'diagnostic harness modified')
    return reconcile_numeric_results(score_cases(sandbox,workspace,cases))


def check_workspace(case_id,workspace,sandbox,*,public_only=False):
    task,_=load_public(case_id)
    cases=task.cases if public_only else task.cases+evaluator_cases(case_id)
    return grade_cases(workspace,sandbox,cases,task.files['diagnostics.py'])


def verify_development_sandbox(root):
    root.mkdir(parents=True,exist_ok=True)
    workspace=root/'isolation';workspace.mkdir();(workspace/'own').write_text('own');(workspace/'.runtime').mkdir()
    forbidden=root/'evaluator-canary';forbidden.write_text('private')
    sandbox=DevelopmentSandbox();sandbox.verify(workspace,workspace/'own',(forbidden,REPO/'.env'))
    return sandbox


def validate_suite():
    records=[]
    with tempfile.TemporaryDirectory(prefix='keisho-development-') as temporary:
        root=Path(temporary).resolve();sandbox=verify_development_sandbox(root)
        for case_id in IDS:
            task,public=load_public(case_id);outcomes={}
            for variant in ('initial','reference','incomplete'):
                files=dict(task.files)
                if variant!='initial':
                    files.update({p.name:p.read_text() for p in (ROOT/'private'/case_id/variant).glob('*.py')})
                path=root/(case_id+'-'+variant);write_workspace(path,files)
                result=check_workspace(case_id,path,sandbox)
                outcomes[variant]={'passed':all(row['passed'] for row in result['results']),
                                   'failing_cases':[row['id'] for row in result['results'] if not row['passed']],
                                   'results':result['results']}
            require(not outcomes['initial']['passed'],f'{case_id}: initial state does not fail')
            require(any(row['id'] in {case['id'] for case in task.cases} and not row['passed'] for row in outcomes['initial']['results']),f'{case_id}: no observable public failure')
            require(outcomes['reference']['passed'],f'{case_id}: reference failed acceptance')
            require(not outcomes['incomplete']['passed'],f'{case_id}: incomplete fix unexpectedly accepted')
            records.append({'task_id':case_id,'task_sha256':task.sha256,'family':public['family'],'origin':public['origin'],
                            'acceptance':public['acceptance'],'outcomes':outcomes,'property_seeds':[17,29,43]})
    return {'version':'development-validation/1.0','created_at':utc_now(),'records':records,'api_calls':0,
            'model_evaluation':False,'human_review_complete':False,'acceptance':'behavioral; not matching a reference patch',
            'scoring':'behavior-json/1.0: recursive JSON contract equality; numerically equal int/float values allowed; boolean substitution rejected',
            'isolation':'macOS base sandbox; writes allowed only in per-workspace .runtime; evaluator and credentials denied'}
