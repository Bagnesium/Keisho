import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.base import ModelRequest
from keisho.agents.providers.openrouter_chat import MODEL_ALIASES
from keisho.benchmark.comparison import ROOT, response_settings
from keisho.core import ValidationError, decode
from keisho.pilot.spending import SpendLedger, BudgetedModel
from keisho.pilot.agent import Recorder, logged_generate
from keisho.logging.raw import RawRun
from keisho.metrics.definitions import CallPurpose
from scripts.agent_decision_diagnostic import adapter, assess_probe, information_action, select_cell, execute
from tests.test_agent_wire_contract import Counter, native_response

class DecisionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.frozen=json.loads((ROOT/'configs/swebench-comparison-v1.1.json').read_text())
        self.provider=json.loads((ROOT/'configs/calibration-task001-openrouter-v1.2.0.yaml').read_text())
        self.schema=response_settings(self.frozen)[2]
        self.request=decode(ModelRequest,json.loads((ROOT/'runs/swebench-integration/interface-diagnosis-v1/functional/predecessor_call_002-request.json').read_text()))
        self.cells=[{'id':label,'role':role,'output_mode':mode,'model_id':self.frozen[role+'_model']}
                    for label,role,mode in [('A','predecessor','json_schema'),('B','predecessor','json_object'),('C','successor','json_schema'),('D','successor','json_object')]]

    def test_four_wire_bodies_have_same_messages_plugins_and_decoding(self):
        bodies=[adapter(c,self.provider,Counter()).body(self.request) for c in self.cells]
        for body in bodies:
            self.assertEqual(body['messages'],bodies[0]['messages'])
            for field in ('plugins','seed','temperature','stream','max_tokens'): self.assertEqual(body[field],bodies[0][field])
            self.assertEqual(body['plugins'],[])
            self.assertNotIn('transforms',body)
        for x,y in ((0,1),(2,3)):
            self.assertEqual({k:v for k,v in bodies[x].items() if k!='response_format'},
                             {k:v for k,v in bodies[y].items() if k!='response_format'})
            self.assertEqual(bodies[x]['response_format'],self.schema)
            self.assertEqual(bodies[y]['response_format'],{'type':'json_object'})
        self.assertNotEqual(bodies[0]['model'],bodies[2]['model'])

    def test_same_parser_and_validator_without_probe_action_execution(self):
        for cell in self.cells:
            with self.subTest(cell=cell['id']), tempfile.TemporaryDirectory() as t:
                witness={'action':{'tool':'read_file','path':'ledger.py'},'claims':[]}
                sent=[]
                def transport(body,key):
                    sent.append(body)
                    return native_response(cell['model_id'],witness),'offline-probe'
                ledger=SpendLedger('2',provider='openrouter',authorized_ceiling_usd='2',authorization_scope='agent-decision-diagnostic')
                model=BudgetedModel(adapter(cell,self.provider,Counter(),transport,True),ledger,'probe',cell['model_id'])
                model.model._key='offline-fixture-key'
                with patch('keisho.benchmark.environment.RepositorySession.execute',side_effect=AssertionError('probe action must not execute')):
                    raw=RawRun(Path(t),'probe')
                    response,_=logged_generate(model,self.request,Recorder(raw),cell['id'],CallPurpose.PREDECESSOR,1)
                    assessment=assess_probe(response.text,{'predecessor_result_001'},{'ledger.py':'fixture'},self.schema)
                self.assertEqual(len(sent),1)
                self.assertTrue(assessment['qualifies'])
                self.assertEqual(assessment['actions_executed'],0)
                self.assertEqual(ledger.records[0]['status'],'settled')

    def test_invalid_actions_and_missing_annotations_not_silently_repaired(self):
        for text in ('{"action":{"tool":"read_file","path":"ledger.py"}}',
                     '{"action":{"tool":"read_file","path":"ledger.py"},"action":{"tool":"list_files"},"claims":[]}'):
            self.assertFalse(assess_probe(text,set(),{'ledger.py':'fixture'},self.schema)['parse_valid'])
        for action in ({'tool':'read_file','path':'../outside'}, {'tool':'read_file'},
                       {'tool':'write_file','path':'ledger.py','content':'blind fix'}, {'tool':'finish','answer':'done'},
                       {'tool':'list_files'}, {'tool':'shell','command':'echo cat ledger.py'},
                       {'tool':'shell','command':"sed -i.bak -n '1,20p' ledger.py"},
                       {'tool':'shell','command':'rg --pre evil reserve ledger.py'}):
            self.assertFalse(assess_probe(json.dumps({'action':action,'claims':[]}),set(),{'ledger.py':'fixture'},self.schema)['qualifies'])

    def test_auxiliary_exclusions_do_not_replace_action(self):
        action={'tool':'read_file','path':'ledger.py'}
        claim={'statement':'unsupported','status':'OBSERVED','basis':'issue report','evidence_ids':['future']}
        row=assess_probe(json.dumps({'action':action,'claims':[claim]}),set(),{'ledger.py':'fixture'},self.schema)
        self.assertTrue(row['qualifies'])
        self.assertEqual(row['proposed_action'],action)
        self.assertEqual(row['annotations']['coverage'],{'supplied':1,'validated':0,'rejected':1})
        self.assertEqual(row['annotations']['raw_claims'],[claim])

    def test_relevance_and_preference_order_frozen_before_response_selection(self):
        files={'ledger.py':'fixture','CONTRACT.md':'public contract'}
        self.assertTrue(information_action({'tool':'read_file','path':'CONTRACT.md'},files)[0])
        self.assertTrue(information_action({'tool':'shell','command':"sed -n '1,80p' ledger.py"},files)[0])
        self.assertTrue(information_action({'tool':'shell','command':'grep -n reserve ledger.py'},files)[0])
        self.assertFalse(information_action({'tool':'read_file','path':'absent'},files)[0])
        self.assertIsNone(information_action({'tool':'shell','command':'python -c "print(1)"'},files)[0])
        rows={c:{'qualifies':True} for c in 'ABCD'}
        for expected in 'ABCD':
            self.assertEqual(select_cell(rows),expected)
            rows[expected]['qualifies']=False
        self.assertIsNone(select_cell(rows))

    def test_new_shared_two_dollar_scope_preserves_legacy_and_stops_unknown_calls(self):
        ledger=SpendLedger('2',provider='openrouter',authorized_ceiling_usd='2',authorization_scope='agent-decision-diagnostic')
        r=ledger.reserve('A',self.cells[0]['model_id'],32000,2048,2000)
        ledger.unknown(r,'fixture charged failure unknown')
        from keisho.agents.providers.openai_chat import ProviderFailure
        with self.assertRaises(ProviderFailure): ledger.reserve('B',self.cells[1]['model_id'],32000,2048,2000)
        self.assertEqual(len(ledger.records),1)
        with self.assertRaises(ValidationError): SpendLedger('2.01',provider='openrouter',authorized_ceiling_usd='2',authorization_scope='agent-decision-diagnostic')
        with self.assertRaises(ValidationError): SpendLedger('2',provider='openrouter',authorized_ceiling_usd='10',authorization_scope='agent-decision-diagnostic')
        with self.assertRaises(ValidationError): execute(False)

    def flow(self, temporary, qualifying=False):
        from types import SimpleNamespace
        from scripts import agent_decision_diagnostic as d
        config=json.loads(d.CONFIG.read_text())
        auth=json.loads(d.AUTH.read_text())
        original_guard=ROOT/'runs/swebench-integration/interface-diagnosis-v1/functional/trajectory.json'
        before=original_guard.read_bytes()
        requests=[]
        def transport(body,key,**kwargs):
            requests.append(body)
            action=({'tool':'read_file','path':'ledger.py'} if qualifying and len(requests)>1 else {'tool':'list_files'})
            identity=next(k for k,v in MODEL_ALIASES.items() if v==body['model'])
            return native_response(identity,{'action':action,'claims':[]}), 'offline-flow'
        image=json.loads((ROOT/'.cache/swebench-evaluator/prepared-task-image.json').read_text())['image_id']
        class Session:
            def __init__(self,*a,**kw):pass
            def close(self):pass
        captured=[]
        def run(*args,**kwargs):
            captured.append((args,kwargs))
            return SimpleNamespace(reason='checkpoint')
        guard=temporary/'owned-diagnostic'
        with patch.object(d,'OUTPUT',guard), patch.object(d,'load_project_env',return_value={'present':{'OPENROUTER_API_KEY':True}}), \
             patch.object(d,'check_public_catalog',return_value={'offline_fixture':True}), patch.object(d,'NativeTokenizer',Counter), \
             patch.object(d,'http_transport',transport), patch.dict('os.environ',{'OPENROUTER_API_KEY':'offline-fixture-key'}), \
             patch.object(d,'docker',return_value=SimpleNamespace(stdout=json.dumps([{'Id':image}]).encode())), \
             patch.object(d,'RepositorySession',Session), patch.object(d,'initialize_public_fixture',return_value='fixture-base'), \
             patch.object(d,'run_agent',run), patch.object(d,'assess_public_fixture',return_value={'status':'passed','software_fixture_only':True}):
            # Session substitution is only needed by confirmation. Probe safety
            # admission uses the actual method through a deliberately bound shim.
            Session.validate_action=__import__('keisho.benchmark.environment',fromlist=['RepositorySession']).RepositorySession.validate_action
            result=execute(True)
            with self.assertRaisesRegex(ValidationError,'guard already claimed'):execute(True)
        self.assertEqual(original_guard.read_bytes(),before)
        self.assertEqual(len(requests),4)
        self.assertTrue(all(body['messages']==requests[0]['messages'] for body in requests))
        self.assertEqual(len(json.loads((guard/'spending.json').read_text())['attempts']),4)
        return guard, captured

    def test_full_offline_flow_executes_no_probe_actions_and_claims_only_once(self):
        with tempfile.TemporaryDirectory() as t:
            guard,captured=self.flow(Path(t))
            result=json.loads((guard/'result.json').read_text())
            self.assertEqual(result['status'],'stopped_no_qualifying_cell')
            self.assertFalse(captured)
            self.assertTrue(all(row['actions_executed']==0 for row in result['probes'].values()))

    def test_confirmation_uses_preferred_cell_and_fresh_initial_context(self):
        with tempfile.TemporaryDirectory() as t:
            guard,captured=self.flow(Path(t),True)
            self.assertEqual(json.loads((guard/'selection.json').read_text())['selected_cell'],'B')
            self.assertEqual(len(captured),1)
            args,kwargs=captured[0]
            initial=json.loads((ROOT/'runs/swebench-integration/interface-diagnosis-v1/functional/predecessor_call_001-request.json').read_text())
            self.assertEqual(args[3],initial['messages'][1]['content'])
            self.assertEqual(args[4],initial['messages'][0]['content'])
            self.assertEqual(args[5],'')
            self.assertEqual(args[0].model.body(self.request)['response_format'],{'type':'json_object'})
            self.assertEqual(args[7].model_calls,8)

if __name__=='__main__':unittest.main()
