"""Real Docker five-way software simulation. No paid/network model transport."""
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
from urllib.request import OpenerDirector

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel
from keisho.benchmark import comparison as c
from keisho.benchmark.environment import RepositorySession
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.tokenizer import NativeTokenizer

def inject(namespace,settings):
    root=Path(settings['fixture_root']);current={'stage':None};counts=defaultdict(int)
    original_private=c.PRIVATE;real_resolve=c.resolve_binding;real_evaluate=c.evaluate
    # Copy only the unchanged private grading row into the controller-only test
    # area. It is never mounted or passed to a model. Reuse the official venv/log
    # installation for the optional evaluator-only command below.
    private=original_private/'offline-fixture-private'/root.name;private.mkdir(parents=True,exist_ok=False)
    (private/'selected-task-evaluator.jsonl').write_bytes((original_private/'selected-task-evaluator.jsonl').read_bytes())
    c.PRIVATE=private
    def resolve(*args,**kwargs):
        kwargs['allow_pending']=True  # Pending scope admitted ONLY with injected no-network transport.
        binding=real_resolve(*args,**kwargs)
        return replace(binding,authorization_guard=root/'synthetic-authorization-claim')
    c.resolve_binding=resolve
    provider=json.loads((c.ROOT/'configs/calibration-task001-openrouter-v1.2.0.yaml').read_text())
    image=json.loads((original_private/'prepared-task-image.json').read_text())
    c.runtime_preflight=lambda binding,**kw:{'provider':provider,'ca':None,'native':NativeTokenizer(),
        'setup':{'synthetic_preflight':True,'reference_smoke_reused':True},'image_metadata':image,
        'credential_presence':{'OPENROUTER_API_KEY':False}}
    c.check_public_catalog=lambda *a:{'synthetic':True,'no_network':True}
    class SyntheticRawRun(RawRun):
        def __init__(self,*args):
            super().__init__(*args);current['stage']=self.path.name
            self.write_artifact('engineering-check.json',{'synthetic':True,'actual_provider_requests':0})
        def write_artifact(self,name,value):
            if name in ('result.json','spending.json') and isinstance(value,dict):
                value={**value,'synthetic_engineering_check':True,'actual_provider_cost_usd':'0'}
            super().write_artifact(name,value)
    c.RawRun=SyntheticRawRun
    class SyntheticProvider(OpenRouterChatModel):
        def __init__(self,*args,**kwargs):kwargs['api_key']='OFFLINE_FIXTURE_KEY';super().__init__(*args,**kwargs)
    c.OpenRouterChatModel=SyntheticProvider
    tokenizer=NativeTokenizer()
    def transport(body,key,**kwargs):
        stage=current['stage'];counts[stage]+=1;n=counts[stage]
        if stage=='note-generation':
            if 'response_format' not in body:
                text='Synthetic engineering predecessor inspected and appended a comment to xarray/__init__.py. Compilation exited 0. No task fix is established; verify the original issue and current repository.'
            else:
                text=json.dumps({field:'Synthetic engineering evidence: source comment present; compilation exited 0; task resolution UNKNOWN. Verify current changes.' for field in json.loads(c.PROMPTS.read_text())['structured_fields']})
        else:
            if stage=='predecessor':
                if n==1:action={'tool':'list_files','prefix':'xarray/','limit':10}
                elif n==2:action={'tool':'read_file','path':'xarray/__init__.py'}
                elif n==3:
                    feedback=json.loads(body['messages'][-1]['content'])['tool_result']
                    action={'tool':'write_file','path':'xarray/__init__.py','content':feedback['content']+'\n# SYNTHETIC_PREDECESSOR_ENGINEERING_MARKER\n'}
                else:action={'tool':'shell','command':'python -m compileall -q xarray/__init__.py'}
            elif stage=='FULL_HISTORY':
                if n==1:action={'tool':'read_file','path':'xarray/__init__.py'}
                elif n==2:
                    source=json.loads(body['messages'][-1]['content'])['tool_result']['content']
                    action={'tool':'write_file','path':'xarray/__init__.py','content':source+'\n# SYNTHETIC_SUCCESSOR_ENGINEERING_MARKER\n'}
                else:action={'tool':'finish','answer':'SYNTHETIC engineering completion, not a task solution'}
            elif stage=='REPOSITORY_ONLY':action={'tool':'read_file','path':'xarray/__init__.py'}
            elif stage=='KEISHO_2K':action={'tool':'list_files'}
            else:action={'tool':'finish','answer':'SYNTHETIC unresolved continuation'}
            text=canonical_json({'action':action,'claims':[]})
        service={'id':f'SYNTHETIC-{stage}-{n}','synthetic':True,'model':body['model'],'provider':'OpenAI',
            'choices':[{'message':{'content':text},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':sum(tokenizer.count(m['content']).count for m in body['messages']),
                'completion_tokens':tokenizer.count(text).count,'cost':'0','is_byok':False,'prompt_tokens_details':{'cached_tokens':0}}}
        kwargs['response_observer'](json.dumps(service).encode(),200,False)
        return service,'SYNTHETIC-NO-PROVIDER-NETWORK'
    c.http_transport=transport
    class FaultableSession(RepositorySession):
        def execute(self,action):
            if self.audit.path.name=='KEISHO_2K':
                self.validate_action(action)
                raise OSError('synthetic one-branch infrastructure failure')
            return super().execute(action)
    c.RepositorySession=FaultableSession
    def evaluator(private,config,task,condition,prediction,**kwargs):
        if condition=='checkpoint' and settings.get('official_evaluator'):
            # Controller-only existing official installation, after notes freeze.
            return real_evaluate(original_private,config,task,condition,prediction,**kwargs)
        from keisho.benchmark.evaluator import unique_run_id
        status='resolved' if condition=='FULL_HISTORY' else 'error' if condition=='KEISHO_2K' else 'unresolved'
        return {'status':status,'run_id':unique_run_id(task['instance_id'],condition,Path(prediction).read_text(),kwargs['run_namespace']),
            'synthetic_grading_fixture':True,'official_grade':False,'actual_provider_requests':0}
    c.evaluate=evaluator
    OpenerDirector.open=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('synthetic simulation attempted model/network I/O'))
