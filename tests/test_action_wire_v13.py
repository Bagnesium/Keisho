"""Prospective v1.3 wire compatibility; archived v1.2 failure stays failed.

All provider outputs here are offline fixtures. Docker tests use only a new
disposable public fixture container and never execute a benchmark evaluator.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, ValidationError as SchemaError

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES
from keisho.benchmark.comparison import ROOT
from keisho.benchmark.environment import RepositorySession, docker
from keisho.benchmark.listing import VERSION as LISTING_VERSION
from keisho.core import canonical_json, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.action_wire import VERSION, canonicalize_action
from keisho.pilot.agent import Budgets, Recorder, parse_output, run_agent
from keisho.pilot.response_policy import AUXILIARY, STRICT, agent_response_format
from keisho.pilot.tools import InvalidAction
from tests.test_agent_wire_contract import Counter, OfflineSession, native_response


ARCHIVED = ROOT/'runs/functional-confirmation12-v1.2-20261011/wire-response-001.json'
FIXTURE = ROOT/'tests/data/action-wire-v13-response.json'
MODEL = 'openai/gpt-4.1-mini-2025-04-14'
WITNESSES = (
    {'tool':'list_files'},
    {'tool':'list_files','prefix':'pkg/','cursor':None,'limit':7},
    {'tool':'list_files','cursor':'a'*64+':7','limit':100},
    {'tool':'read_file','path':'ledger.py'},
    {'tool':'write_file','path':'ledger.py','content':'# π\nvalue = "quote\\slash"\n'},
    {'tool':'shell','command':'python check_public.py'},
    {'tool':'finish','answer':'Fixture completion: π\n'},
)


def nested(action):
    return {'tool':action['tool'],'args':{k:v for k,v in action.items() if k!='tool'}}


def archived_text():
    capture=json.loads(FIXTURE.read_text())
    body=base64.b64decode(capture['body_base64'],validate=True)
    return json.loads(body)['choices'][0]['message']['content']


class BoundedSession(OfflineSession):
    listing_policy=LISTING_VERSION


def fixture_loop(root,texts,session,policy=AUXILIARY):
    sent=[]
    def transport(body,key):
        sent.append(copy.deepcopy(body))
        service=native_response(MODEL,{})
        service['choices'][0]['message']['content']=texts[len(sent)-1]
        return service,'SYNTHETIC-NOT-A-SERVICE-REQUEST'
    model=OpenRouterChatModel(MODEL,authorized=True,api_key='offline-fixture-key',tokenizer=Counter(),
        transport=transport,response_model_ids=(MODEL_ALIASES[MODEL],MODEL))
    raw=RawRun(root,'wire-v13-fixture')
    execution=run_agent(model,session,Recorder(raw),'OFFLINE fixture','unchanged fixture prompt','',1,
        Budgets(len(texts),len(texts),2048,180000,32000,128000),role='predecessor',response_policy=policy,
        action_wire_version=VERSION)
    return raw,execution,sent


class ActionWireTests(unittest.TestCase):
    def setUp(self):
        self.session=BoundedSession()
        self.schema=Draft202012Validator(agent_response_format('4.0')['json_schema']['schema'])

    def audit(self,action):
        return canonicalize_action(action,self.session.validate_action)

    def test_actual_archived_response_admitted_only_prospectively(self):
        before=ARCHIVED.read_bytes() if ARCHIVED.exists() else None
        provenance=json.loads((ROOT/'tests/data/action-wire-v13-response-provenance.json').read_text())
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),provenance['source_sha256'])
        self.assertEqual(provenance['historical_status'],'failed')
        self.assertEqual(provenance['historical_tool_actions'],0)
        self.assertEqual(provenance['historical_charge_usd'],'0.00026')
        if before is not None:self.assertEqual(FIXTURE.read_bytes(),before)
        text=archived_text()
        self.assertEqual(text,'{"action":{"tool":"list_files","args":{"limit":100}},"claims":[]}')
        parsed=parse_output(text,set(),AUXILIARY,action_wire_version=VERSION)
        audit=self.audit(parsed['action'])
        self.assertEqual(audit['original_action'],{'tool':'list_files','args':{'limit':100}})
        self.assertEqual(audit['canonical_action'],{'tool':'list_files','limit':100})
        self.assertEqual(audit['input_action_shape'],'nested_args')
        self.assertTrue(audit['canonicalization_occurred'])
        self.assertEqual(audit['validation_result'],'accepted')
        self.assertIsNone(audit['rejection_reason'])
        with self.assertRaises(InvalidAction):self.session.validate_action(parsed['action'])
        if before is not None:
            self.assertEqual(ARCHIVED.read_bytes(),before)
            result=json.loads((ARCHIVED.parent/'result.json').read_text())
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['execution']['tool_calls'],0)

    def test_every_tool_both_shapes_is_lossless_deterministic_and_schema_valid(self):
        Draft202012Validator.check_schema(self.schema.schema)
        for action in WITNESSES:
            for shape,wire in (('flat',action),('nested_args',nested(action))):
                with self.subTest(tool=action['tool'],shape=shape,action=action):
                    untouched=copy.deepcopy(wire)
                    self.schema.validate({'action':wire,'claims':[]})
                    first=self.audit(wire);second=self.audit(copy.deepcopy(wire))
                    self.assertEqual(first,second)
                    self.assertEqual(wire,untouched)
                    self.assertEqual(first['original_action'],wire)
                    self.assertEqual(first['canonical_action'],action)
                    self.assertEqual(first['input_action_shape'],shape)
                    self.assertEqual(first['canonicalization_occurred'],shape=='nested_args')
                    self.assertEqual(first['validation_result'],'accepted')
                    self.assertTrue(first['wire_schema_valid'])
                    self.assertTrue(first['canonical_schema_valid'])
                    # Mutation of either input or audit must not change the other.
                    wire_copy=copy.deepcopy(wire)
                    detached=self.audit(wire_copy)
                    wire_copy['tool']='mutated'
                    self.assertEqual(detached['original_action'],wire)

    def test_optional_listing_fields_are_never_invented(self):
        for wire in ({'tool':'list_files'},{'tool':'list_files','args':{}},
                     {'tool':'list_files','args':{'limit':100}}):
            with self.subTest(wire=wire):
                expected={'tool':'list_files',**wire.get('args',{})}
                self.assertEqual(self.audit(wire)['canonical_action'],expected)

    def test_unknown_missing_wrong_types_and_unrecognized_nesting_never_admit(self):
        invalid=(
            {'tool':'unknown'}, {'tool':'run_tests','args':{'test_ids':['full']}},
            {'tool':7}, {'tool':['list_files']}, {},
            {'tool':'list_files','args':{'path':'ledger.py'}},
            {'tool':'read_file','args':{'path':'ledger.py','unknown':'x'}},
            {'tool':'write_file','args':{'path':'ledger.py'}},
            {'tool':'read_file','args':{}}, {'tool':'shell','args':{}}, {'tool':'finish','args':{}},
            {'tool':'read_file','args':{'path':7}}, {'tool':'write_file','path':'ledger.py','content':[]},
            {'tool':'shell','args':{'command':False}}, {'tool':'finish','args':{'answer':None}},
            {'tool':'list_files','args':{'limit':True}}, {'tool':'list_files','limit':0},
            {'tool':'list_files','args':{'limit':101}}, {'tool':'list_files','cursor':12},
            {'tool':'list_files','prefix':None}, {'tool':'list_files','args':[]},
            {'tool':'list_files','args':None}, {'tool':'list_files','args':{'args':{}}},
            {'tool':'read_file','args':{'path':{'value':'ledger.py'}}},
            {'tool':'list_files','parameters':{}}, {'tool':'shell','args':{'command':'true','kwargs':{}}},
        )
        for action in invalid:
            variants=[action]
            if 'args' in action and isinstance(action['args'],dict) and not set(action['args']) & {'args','tool'}:
                variants.append({'tool':action['tool'],**action['args']})
            elif 'tool' in action and 'args' not in action:
                variants.append(nested(action))
            for wire in variants:
                with self.subTest(action=wire):
                    with self.assertRaises(SchemaError):self.schema.validate({'action':wire,'claims':[]})
                    audit=self.audit(wire)
                    self.assertEqual(audit['validation_result'],'rejected')
                    self.assertIsNone(audit['canonical_action'])
                    self.assertTrue(audit['rejection_reason'])
                    self.assertEqual(audit['original_action'],wire)
                    self.assertEqual(self.session.actions,[])

    def test_mixed_duplicate_locations_rejected_even_when_values_equal(self):
        mixed=(
            {'tool':'read_file','path':'ledger.py','args':{'path':'ledger.py'}},
            {'tool':'read_file','path':'api.py','args':{'path':'ledger.py'}},
            {'tool':'list_files','limit':100,'args':{'limit':100}},
            {'tool':'list_files','prefix':'pkg/','args':{'limit':7}},
            {'tool':'write_file','path':'ledger.py','args':{'content':'value=1\n'}},
            {'tool':'finish','answer':'x','args':{}},
        )
        for action in mixed:
            with self.subTest(action=action):
                audit=self.audit(action)
                self.assertEqual(audit['input_action_shape'],'mixed')
                self.assertEqual(audit['validation_result'],'rejected')
                self.assertIsNone(audit['canonical_action'])
                with self.assertRaises(SchemaError):self.schema.validate({'action':action,'claims':[]})

    def test_unsafe_paths_and_unauthorized_operations_still_reject_after_adapter(self):
        unsafe=(
            {'tool':'read_file','path':'/etc/passwd'}, {'tool':'read_file','path':'../escape'},
            {'tool':'read_file','path':'pkg/../../escape'}, {'tool':'read_file','path':'.git/config'},
            {'tool':'write_file','path':'pkg/../ledger.py','content':'x'},
            {'tool':'write_file','path':'ledger.py','content':'x'*49153},
            {'tool':'list_files','prefix':'../'}, {'tool':'list_files','prefix':'.git/'},
            {'tool':'list_files','cursor':'bad'}, {'tool':'list_files','limit':1.0},
            {'tool':'shell','command':''},
            {'tool':'shell','command':'true\x00false'}, {'tool':'shell','command':'x'*8193},
        )
        for action in unsafe:
            for wire in (action,nested(action)):
                with self.subTest(wire=wire):
                    self.schema.validate({'action':wire,'claims':[]})
                    audit=self.audit(wire)
                    self.assertEqual(audit['validation_result'],'rejected')
                    self.assertEqual(audit['validation_stage'],'safety')
                    self.assertEqual(audit['canonical_action'],action)
                    self.assertTrue(audit['wire_schema_valid'])
                    self.assertTrue(audit['canonical_schema_valid'])
                    self.assertTrue(audit['rejection_reason'])

    def test_malformed_duplicate_keys_and_non_json_constants_reject_both_policies(self):
        invalid=(
            '{malformed',
            '{"action":{"tool":"list_files","tool":"finish"},"claims":[]}',
            '{"action":{"tool":"list_files","args":{"limit":7,"limit":100}},"claims":[]}',
            '{"action":{"tool":"list_files"},"action":{"tool":"list_files"},"claims":[]}',
            '{"action":{"tool":"list_files","args":{"limit":NaN}},"claims":[]}',
            '{"action":{"tool":"list_files"},"claims":[],"extra":{}}',
        )
        for text in invalid:
            for policy in (STRICT,AUXILIARY):
                with self.subTest(text=text,policy=policy),self.assertRaises((ValueError,TypeError)):
                    parse_output(text,set(),policy,action_wire_version=VERSION)

    def test_auxiliary_annotations_keep_separate_acceptance_and_rejection(self):
        accepted={'statement':'Observed fixture','status':'OBSERVED','basis':'tool','evidence_ids':['tool-1']}
        rejected={'statement':'Unsupported fixture','status':'VERIFIED','basis':'invented','evidence_ids':['absent']}
        text=canonical_json({'action':nested(WITNESSES[3]),'claims':[accepted,rejected]})
        parsed=parse_output(text,{'tool-1'},AUXILIARY,action_wire_version=VERSION)
        self.assertEqual(parsed['claims'],[accepted])
        report=parsed['annotation_report']
        self.assertEqual(report['raw_claims'],[accepted,rejected])
        self.assertEqual(report['validated_claims'],[accepted])
        self.assertEqual(report['diagnostics'][0]['raw_claim'],rejected)
        self.assertEqual(self.audit(parsed['action'])['validation_result'],'accepted')
        with self.assertRaises(ValidationError):parse_output(text,{'tool-1'},STRICT,action_wire_version=VERSION)

    def loop(self,root,texts,session=None,policy=AUXILIARY):
        return fixture_loop(root,texts,session or self.session,policy)

    def test_agent_audits_raw_canonical_validation_and_feedback_without_rewriting_response(self):
        texts=[archived_text(),canonical_json({'action':nested(WITNESSES[-1]),'claims':[]})]
        with tempfile.TemporaryDirectory() as t:
            raw,execution,sent=self.loop(Path(t),texts)
            self.assertEqual((execution.reason,execution.model_calls,execution.tool_calls),('finished',2,1))
            self.assertEqual(self.session.actions,[{'tool':'list_files','limit':100}])
            saved=json.loads((raw.path/'predecessor_call_001-response.json').read_text())
            self.assertEqual(saved['text'],texts[0])
            self.assertEqual(sent[1]['messages'][3]['content'],texts[0])
            result=json.loads(sent[1]['messages'][4]['content'])['tool_result']
            self.assertEqual(result['action'],self.session.actions[0])
            audit=json.loads((raw.path/'predecessor_call_001-action-wire.json').read_text())
            self.assertEqual(audit['original_action'],json.loads(texts[0])['action'])
            self.assertEqual(audit['canonical_action'],self.session.actions[0])
            self.assertEqual(audit['validation_result'],'accepted')
            frozen=raw.freeze()
            action_events=[json.loads(e.payload_json)['action'] for e in frozen.events if e.kind.value=='tool_call']
            self.assertEqual(action_events,self.session.actions)

    def test_rejected_and_malformed_response_audits_never_execute_or_retry(self):
        cases=(canonical_json({'action':{'tool':'read_file','args':{'path':12}},'claims':[]}),
               canonical_json({'action':{'tool':'read_file','args':{'path':'../escape'}},'claims':[]}),
               '{malformed')
        for text in cases:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as t:
                raw,execution,sent=self.loop(Path(t),[text])
                self.assertEqual((execution.model_calls,execution.tool_calls,len(sent)),(1,0,1))
                self.assertEqual(self.session.actions,[])
                self.assertEqual(json.loads((raw.path/'predecessor_call_001-response.json').read_text())['text'],text)
                audit=json.loads((raw.path/'predecessor_call_001-action-wire.json').read_text())
                self.assertEqual(audit['validation_result'],'rejected')
                self.assertTrue(audit['rejection_reason'])
                if text=='{malformed':
                    self.assertIsNone(audit['original_action'])
                    self.assertIsNone(audit['canonical_action'])
                self.assertFalse(any(e.kind.value=='tool_call' for e in raw.freeze().events))

    def test_invalid_envelope_audit_preserves_identifiable_action_without_admitting_it(self):
        action={'tool':'list_files','args':{'limit':100}}
        cases=(({'action':action,'claims':{}},action,'nested_args'),
               ({'action':action,'claims':[],'extra':{}},action,'nested_args'),
               ({'action':[],'claims':[]},[],'unrecognized'),
               ([],None,'unassessable'))
        for envelope,original,shape in cases:
            text=canonical_json(envelope)
            for policy in (STRICT,AUXILIARY):
                with self.subTest(envelope=envelope,policy=policy),tempfile.TemporaryDirectory() as t:
                    raw,execution,sent=self.loop(Path(t),[text],policy=policy)
                    self.assertEqual((execution.model_calls,execution.tool_calls,len(sent)),(1,0,1))
                    wire=json.loads((raw.path/'predecessor_call_001-action-wire.json').read_text())
                    self.assertEqual(wire['input_action_shape'],shape)
                    self.assertEqual(wire['original_action'],original)
                    self.assertEqual(wire['validation_result'],'rejected')
                    self.assertEqual(wire['validation_stage'],'response')
                    self.assertFalse(wire['canonicalization_occurred'])
                    self.assertIsNone(wire['canonical_action'])
                    self.assertTrue(wire['rejection_reason'])
                    self.assertEqual(json.loads((raw.path/'predecessor_call_001-response.json').read_text())['text'],text)
                    self.assertEqual(self.session.actions,[])

    def test_unrecordable_unicode_and_numeric_overflow_reject_with_raw_text_preserved(self):
        good_action={'tool':'list_files','args':{'limit':100}}
        bad_claim={'statement':'\ud800','status':'OBSERVED','basis':'tool','evidence_ids':[]}
        cases=(
            (json.dumps({'action':{'tool':'read_file','args':{'path':'\ud800'}},'claims':[]},ensure_ascii=True),None),
            (json.dumps({'action':{'tool':'finish','args':{'answer':'\ud800'}},'claims':[]},ensure_ascii=True),None),
            (json.dumps({'action':good_action,'claims':[bad_claim]},ensure_ascii=True),good_action),
            ('{"action":{"tool":"list_files","args":{"limit":1e400}},"claims":[]}',None),
        )
        for text,original in cases:
            self.assertTrue(text.isascii())
            for policy in (STRICT,AUXILIARY):
                with self.subTest(text=text,policy=policy),tempfile.TemporaryDirectory() as t:
                    raw,execution,sent=self.loop(Path(t),[text],policy=policy)
                    self.assertEqual((execution.model_calls,execution.tool_calls,len(sent)),(1,0,1))
                    self.assertEqual(json.loads((raw.path/'predecessor_call_001-response.json').read_text())['text'],text)
                    wire=json.loads((raw.path/'predecessor_call_001-action-wire.json').read_text())
                    self.assertEqual(wire['validation_result'],'rejected')
                    self.assertEqual(wire['validation_stage'],'encoding')
                    self.assertEqual(wire['input_action_shape'],'nested_args')
                    self.assertEqual(wire['original_action'],original)
                    self.assertIsNone(wire['canonical_action'])
                    self.assertFalse(wire['canonicalization_occurred'])
                    self.assertTrue(wire['rejection_reason'])
                    raw.freeze()
        for action in ({'tool':'read_file','args':{'path':'\ud800'}},
                       {'tool':'list_files','args':{'limit':float('inf')}}):
            audit=self.audit(action)
            self.assertEqual(audit['validation_result'],'rejected')
            self.assertEqual(audit['validation_stage'],'encoding')
            self.assertIsNone(audit['original_action'])
            self.assertIsNone(audit['canonical_action'])
            canonical_json(audit).encode('utf-8')


class DockerContainmentTests(unittest.TestCase):
    def test_symlink_escape_and_git_alias_rejected_during_real_tool_execution(self):
        image=json.loads((ROOT/'.cache/swebench-evaluator/prepared-task-image.json').read_text())['image_id']
        session=RepositorySession(image,listing_policy=LISTING_VERSION)
        try:
            # New owned container only. No host mounts or evaluator invocation.
            setup="from pathlib import Path; import shutil; p=Path('/testbed'); shutil.rmtree(p); p.mkdir(); (p/'safe.py').write_text('value=1\\n'); (p/'.git').mkdir(); (p/'.git/config').write_text('private fixture'); Path('/tmp/keisho-wire-outside-v13.txt').write_text('outside untouched'); Path('/tmp/keisho-wire-dir-v13').mkdir(); (p/'outside').symlink_to('/tmp/keisho-wire-outside-v13.txt'); (p/'git-alias').symlink_to(p/'.git/config'); (p/'outside-dir').symlink_to('/tmp/keisho-wire-dir-v13')"
            docker('exec',session.name,'python3','-c',setup)
            session.base_inventory=session.inventory()
            for path in ('outside','git-alias','outside-dir/new.py'):
                for tool in ('read_file','write_file'):
                    action={'tool':tool,'path':path,**({'content':'denied'} if tool=='write_file' else {})}
                    with self.subTest(path=path,tool=tool):
                        audit=canonicalize_action(nested(action),session.validate_action)
                        self.assertEqual(audit['validation_result'],'accepted')
                        with self.assertRaisesRegex(InvalidAction,'path escapes repository'):
                            session.execute(audit['canonical_action'])
            valid=canonicalize_action({'tool':'read_file','args':{'path':'safe.py'}},session.validate_action)
            self.assertEqual(session.execute(valid['canonical_action'])['content'],'value=1\n')
            action={'tool':'write_file','args':{'path':'outside','content':'denied'}}
            text=canonical_json({'action':action,'claims':[]})
            with tempfile.TemporaryDirectory() as t:
                raw,execution,sent=fixture_loop(Path(t),[text],session)
                self.assertEqual((execution.reason,execution.model_calls,execution.tool_calls,len(sent)),('invalid_run',1,1,1))
                wire=json.loads((raw.path/'predecessor_call_001-action-wire.json').read_text())
                self.assertEqual(wire['original_action'],action)
                self.assertEqual(wire['validation_result'],'accepted')
                admission=json.loads((raw.path/'predecessor_call_001-action-admission.json').read_text())
                self.assertEqual(admission['canonical_action'],wire['canonical_action'])
                self.assertEqual(admission['runtime_validation_result'],'rejected')
                self.assertFalse(admission['tool_execution_completed'])
                self.assertIn('path escapes repository',admission['rejection_reason'])
                self.assertEqual(json.loads((raw.path/'predecessor_call_001-response.json').read_text())['text'],text)
            check="from pathlib import Path; assert Path('/tmp/keisho-wire-outside-v13.txt').read_text()=='outside untouched'; assert Path('/testbed/.git/config').read_text()=='private fixture'; assert not Path('/tmp/keisho-wire-dir-v13/new.py').exists()"
            docker('exec',session.name,'python3','-c',check)
        finally:session.close()


if __name__=='__main__':unittest.main()
