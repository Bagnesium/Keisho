"""Synthetic provider through the real public CLI, real Docker and real loop."""
import json
from pathlib import Path
from urllib.request import OpenerDirector

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.tokenizer import NativeTokenizer

FIX = '''from normalize import normalize

def replay(capacity, events):
    state = {"active": {}, "reserved": 0, "releases": 0}
    for event in normalize(events):
        key = event["id"]
        if event["kind"] == "reserve":
            units = event["units"]
            previous = state["active"].get(key)
            if previous is not None:
                state["reserved"] -= previous
            state["active"][key] = units
            state["reserved"] += units
        else:
            previous = state["active"].pop(key, None)
            if previous is not None:
                state["reserved"] -= previous
                state["releases"] += 1
    return {"available": capacity - state["reserved"], "active": state["active"], "releases": state["releases"]}
'''

def inject(namespace, settings):
    root = Path(settings['fixture_root'])
    mode = settings.get('mode', 'complete')
    namespace['ROOT'] = root
    namespace['load_project_env'] = lambda *a, **kw: {'present': {'OPENROUTER_API_KEY': True}}
    namespace['check_public_catalog'] = lambda *a: {'synthetic_engineering_check': True, 'no_network': True}
    tokenizer = NativeTokenizer()
    class SyntheticModel(OpenRouterChatModel):
        def __init__(self, *args, **kwargs):
            kwargs['api_key'] = 'OFFLINE_FIXTURE_KEY'
            super().__init__(*args, **kwargs)
    namespace['OpenRouterChatModel'] = SyntheticModel
    class SyntheticRawRun(RawRun):
        def __init__(self, *args):
            super().__init__(*args)
            self.write_artifact('engineering-check.json', {'synthetic': True, 'provider_network_requests': 0})
        def write_artifact(self, name, value):
            if name in ('result.json', 'spending.json') and isinstance(value, dict):
                value = {**value, 'synthetic_engineering_check': True, 'actual_provider_cost_usd': '0'}
            super().write_artifact(name, value)
    namespace['RawRun'] = SyntheticRawRun
    actions = [{'tool':'list_files'}, {'tool':'read_file','path':'ledger.py'},
               {'tool':'shell','command':'python check_public.py'},
               {'tool':'write_file','path':'ledger.py','content':FIX},
               {'tool':'shell','command':'python check_public.py'}]
    number = 0
    def transport(body, key, **kwargs):
        nonlocal number
        number += 1
        if mode == 'provider_failure':
            from keisho.agents.providers.openai_chat import ProviderFailure
            raise ProviderFailure('synthetic provider failure; no network, no retry')
        claim = {'statement':'Synthetic unsupported annotation', 'status':'VERIFIED',
                 'basis':'unsupported', 'evidence_ids':['not-available']}
        action = actions[number-1] if mode not in ('budget', 'infrastructure', 'invalid_action', 'task_failure') else {'tool':'list_files'}
        if mode == 'invalid_action': action = {'tool':'read_file','path':'../escape'}
        if mode == 'invalid_action_schema': action = {'tool':'read_file','path':12}
        if mode == 'task_failure':
            action = actions[number-1]
            if number == 4: action = {**action, 'content':'from normalize import normalize\ndef replay(capacity, events):\n    return {}\n'}
        text = '{malformed' if mode == 'invalid_json' else canonical_json({'action':action,'claims':[claim] if number==1 else []})
        usage = {'prompt_tokens':sum(tokenizer.count(m['content']).count for m in body['messages']),
                 'completion_tokens':tokenizer.count(text).count, 'cost':'0', 'is_byok':False,
                 'prompt_tokens_details':{'cached_tokens':0}}
        service = {'id':f'SYNTHETIC-{number}', 'synthetic':True, 'model':body['model'],'provider':'OpenAI',
                   'choices':[{'message':{'content':text},'finish_reason':'stop'}],'usage':usage}
        kwargs['response_observer'](json.dumps(service).encode(),200,False)
        return service, 'SYNTHETIC-NOT-A-SERVICE-REQUEST'
    namespace['http_transport'] = transport
    def no_network(*a, **kw): raise AssertionError('offline test attempted provider/network I/O')
    OpenerDirector.open = no_network
    if mode == 'infrastructure':
        original = namespace['RepositorySession']
        class InterruptedSession(original):
            def execute(self, action):
                from keisho.pilot.sandbox import IsolationUnavailable
                raise IsolationUnavailable('synthetic infrastructure interruption')
        namespace['RepositorySession'] = InterruptedSession
