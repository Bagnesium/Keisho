"""Offline provider-boundary witnesses; never reported as model effectiveness."""
import base64
from decimal import Decimal
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from keisho.agents.providers.openai_chat import http_transport, ProviderFailure
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES
from keisho.benchmark.comparison import ROOT, response_settings
from keisho.benchmark.response_measurements import capture_response, assess_text, measure_run, summarize
from keisho.core import canonical_json, digest, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import AUXILIARY
from keisho.pilot.spending import SpendLedger, BudgetedModel
from scripts.benchmark_functional_check import execute_confirmation12, PublicAcceptanceBoundary12
from tests.test_agent_wire_contract import Counter, OfflineSession, native_response, WITNESSES

MINI = 'openai/gpt-4.1-mini-2025-04-14'
CONFIG = ROOT / 'configs/functional-confirmation12-v1.json'


class ResponseMeasurementTests(unittest.TestCase):
    def loop(self, root, texts, *, failure=None, usage=None, session=None):
        raw = RawRun(root, 'offline-confirmation')
        session = session or OfflineSession()
        sent = []
        ledger = SpendLedger('.50', provider='openrouter', authorized_ceiling_usd='2', authorization_scope='agent-decision-diagnostic')
        def transport(body, key):
            n = len(sent) + 1
            sent.append(body)
            raw.write_artifact(f'wire-request-{n:03d}.json', body)
            if failure: raise ProviderFailure('OFFLINE missing response fixture')
            service = native_response(MINI, {})
            service['choices'][0]['message']['content'] = texts[n-1]
            if usage: service['usage'].update(usage)
            capture_response(raw, n, json.dumps(service).encode(), 200, False)
            # This capture occurs before the real adapter's routing/usage/text
            # checks. The loop uses the real BudgetedModel and parser.
            return service, 'offline-fixture'
        model = OpenRouterChatModel(MINI, authorized=True, api_key='offline-key', tokenizer=Counter(),
            response_model_ids=(MODEL_ALIASES[MINI], MINI), transport=transport)
        execution = run_agent(BudgetedModel(model, ledger, 'offline-confirmation', MINI), session, Recorder(raw),
            'OFFLINE objective', response_settings(json.loads((ROOT/'configs/swebench-comparison-v1.1.json').read_text()))[0],
            '', 1, Budgets(12,12,2048,180000,32000,128000), role='predecessor', response_policy=AUXILIARY)
        return raw, execution, measure_run(raw, session.validate_action), sent, ledger

    def test_invalid_json_preserved_without_repair_or_retry(self):
        text = '{"action": {"tool":"read_file","path":"api.py"},'
        with tempfile.TemporaryDirectory() as t:
            raw, execution, report, sent, _ = self.loop(Path(t), [text])
            self.assertEqual(len(sent), 1)
            self.assertEqual(execution.tool_calls, 0)
            saved = json.loads((raw.path/'predecessor_call_001-response.json').read_text())
            self.assertEqual(saved['text'], text)
            wire = json.loads(base64.b64decode(json.loads((raw.path/'wire-response-001.json').read_text())['body_base64']))
            self.assertEqual(wire['choices'][0]['message']['content'], text)
            self.assertEqual(report['actual_responses_received'], 1)
            self.assertEqual(report['missing_model_responses'], 0)
            self.assertEqual(report['measurements']['json_syntax_valid']['invalid_rate'], 1)
            self.assertEqual(report['measurements']['action_schema_valid']['unassessable_count'], 1)

    def test_invalid_auxiliary_claim_does_not_reject_valid_action(self):
        claim = {'statement':'unsupported','status':'VERIFIED','basis':'tool/predecessor','evidence_ids':['not-known']}
        with tempfile.TemporaryDirectory() as t:
            raw, execution, report, sent, _ = self.loop(Path(t), [canonical_json({'action':{'tool':'read_file','path':'api.py'},'claims':[claim]}), canonical_json(WITNESSES[-1])])
            self.assertEqual(execution.tool_calls, 1)
            self.assertEqual(report['measurements']['auxiliary_annotations_valid']['invalid_count'], 1)
            self.assertEqual(report['measurements']['auxiliary_annotations_valid']['invalid_rate'], .5)
            self.assertEqual(report['measurements']['action_rejected']['count'], 0)
            self.assertEqual(report['measurements']['tool_execution_successful']['count'], 1)
            annotations = report['rows'][0]['annotations']
            self.assertEqual(annotations['raw_claims'], [claim])
            self.assertEqual(annotations['validated_claims'], [])
            self.assertEqual(annotations['diagnostics'][0]['annotation_information'], 'unknown')
            self.assertEqual(len(sent[1]['messages']), 5)

    def test_invalid_action_with_valid_claims_never_executes(self):
        for action in ({'tool':'read_file'}, {'tool':'list_files','path':'api.py'}, {'tool':'unknown'}, {'tool':'finish'}):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as t:
                _, execution, report, sent, _ = self.loop(Path(t), [canonical_json({'action':action,'claims':[]})])
                self.assertEqual((execution.model_calls, execution.tool_calls, len(sent)), (1,0,1))
                self.assertEqual(report['measurements']['action_schema_valid']['invalid_count'], 1)
                self.assertEqual(report['measurements']['auxiliary_annotations_valid']['invalid_count'], 0)
                self.assertEqual(report['measurements']['action_rejected']['count'], 1)

    def test_unsafe_action_schema_valid_but_admission_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, sent, _ = self.loop(Path(t), [canonical_json({'action':{'tool':'read_file','path':'../escape'},'claims':[]})])
            self.assertEqual(execution.tool_calls, 0)
            self.assertTrue(report['rows'][0]['action_schema_valid'])
            self.assertFalse(report['rows'][0]['safety_valid'])
            self.assertEqual(report['measurements']['action_rejected']['count'], 1)

    def test_ambiguous_duplicate_json_keys_not_interpreted_as_action(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, _, _ = self.loop(Path(t), ['{"action":{"tool":"list_files"},"action":{"tool":"finish","answer":"x"},"claims":[]}'])
            self.assertEqual(execution.tool_calls, 0)
            self.assertTrue(report['rows'][0]['json_syntax_valid'])
            self.assertFalse(report['rows'][0]['response_structure_valid'])
            self.assertIsNone(report['rows'][0]['proposed_action'])

    def test_missing_response_not_counted_invalid_and_unknown_spending_stops(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, sent, ledger = self.loop(Path(t), [], failure=True)
            self.assertEqual((len(sent), execution.tool_calls), (1,0))
            self.assertEqual(report['actual_responses_received'], 0)
            self.assertEqual(report['missing_model_responses'], 1)
            self.assertIsNone(report['measurements']['json_syntax_valid']['invalid_rate'])
            self.assertTrue(ledger.stopped)
            self.assertEqual(ledger.held, Decimal('.01688064'))

    def test_returned_text_captured_when_provider_usage_check_rejects_it(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, sent, ledger = self.loop(Path(t), [canonical_json(WITNESSES[0])], usage={'cost':None})
            self.assertEqual((len(sent), execution.tool_calls), (1,0))
            self.assertEqual(report['actual_responses_received'], 1)
            self.assertTrue(report['rows'][0]['json_syntax_valid'])
            self.assertTrue(report['rows'][0]['response_rejected'])
            self.assertEqual(ledger.records[0]['status'], 'unreconciled')

    def test_refusal_message_is_received_invalid_content_not_missing(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, sent, _ = self.loop(Path(t), [None])
            self.assertEqual((len(sent), execution.tool_calls), (1,0))
            self.assertEqual(report['actual_responses_received'], 1)
            self.assertFalse(report['rows'][0]['json_syntax_valid'])

    def test_nonzero_shell_is_completed_but_not_successful_execution(self):
        class Session(OfflineSession):
            def execute(self, action):
                return {**super().execute(action), 'exit_code':1}
        with tempfile.TemporaryDirectory() as t:
            _, _, report, _, _ = self.loop(Path(t), [canonical_json(WITNESSES[3]),canonical_json(WITNESSES[4])], session=Session())
            self.assertEqual(report['measurements']['tool_execution_completed']['count'], 1)
            self.assertEqual(report['measurements']['tool_execution_successful']['count'], 0)
            self.assertEqual(report['measurements']['tool_execution_completed']['rate'], .5)

    def test_all_five_action_variants_and_multiturn_feedback_same_local_policy(self):
        with tempfile.TemporaryDirectory() as t:
            _, execution, report, sent, _ = self.loop(Path(t), [canonical_json(w) for w in WITNESSES])
            self.assertEqual((execution.reason,execution.model_calls,execution.tool_calls),('finished',5,4))
            self.assertEqual(report['actual_responses_received'], 5)
            self.assertEqual(report['measurements']['action_schema_valid']['valid_count'],5)
            self.assertEqual(report['measurements']['tool_execution_successful']['count'],4)
            for n, body in enumerate(sent):
                self.assertEqual(body['response_format'], {'type':'json_object'})
                self.assertEqual(len(body['messages']), 3+2*n)
                for i in range(n):
                    self.assertEqual(json.loads(body['messages'][3+2*i]['content']),WITNESSES[i])
                    self.assertEqual(json.loads(body['messages'][4+2*i]['content'])['event_id'], f'predecessor_result_{i+1:03d}')

    def test_http_body_observer_precedes_json_decode_and_redacts_only_credentials(self):
        class HTTP:
            headers={'x-request-id':'fixture','Authorization':'NEVER_RECORD_HEADER'}
            status=200
            def __enter__(self): return self
            def __exit__(self,*a): pass
            def read(self): return b'{malformed ORIGINAL-body fake-key'
        observed=[]
        opener=Mock();opener.open.return_value=HTTP()
        with patch('keisho.agents.providers.openai_chat.verified_opener', return_value=opener):
            with self.assertRaises(ProviderFailure):
                http_transport({},'fake-key',base_url='https://openrouter.ai/api/v1',response_observer=lambda *args:observed.append(args))
        self.assertEqual(observed,[(b'{malformed ORIGINAL-body [REDACTED_API_KEY]',200,True)])
        self.assertNotIn('NEVER_RECORD_HEADER',str(observed))
        self.assertEqual(opener.open.call_count,1)

    def test_http_error_body_without_message_is_missing_not_invalid_response(self):
        with tempfile.TemporaryDirectory() as t:
            raw=RawRun(Path(t),'http-error')
            raw.write_artifact('wire-request-001.json',{'messages':[]})
            opener=Mock();opener.open.side_effect=HTTPError('https://openrouter.ai/api/v1/chat/completions',429,'fixture',{},io.BytesIO(b'{"error":"fake-key"}'))
            with patch('keisho.agents.providers.openai_chat.verified_opener',return_value=opener), self.assertRaises(ProviderFailure):
                http_transport({},'fake-key',base_url='https://openrouter.ai/api/v1',response_observer=lambda *args:capture_response(raw,1,*args))
            report=measure_run(raw,OfflineSession().validate_action)
            self.assertEqual(report['actual_responses_received'],0)
            self.assertEqual(report['missing_model_responses'],1)

    def test_new_success_rule_requires_real_post_edit_public_test(self):
        boundary=PublicAcceptanceBoundary12()
        boundary({'tool':'read_file','path':'ledger.py'},{'content':'source'})
        boundary({'tool':'write_file','path':'ledger.py'},{'changed_paths':['ledger.py']})
        for command in ('echo "python check_public.py"','python -m compileall ledger.py','cat check_public.py'):
            self.assertFalse(boundary({'tool':'shell','command':command},{'exit_code':0,'output':'PUBLIC_ACCEPTANCE passed 4 cases'}))
        self.assertTrue(boundary({'tool':'shell','command':'python3 check_public.py'},{'exit_code':0,'output':'PUBLIC_ACCEPTANCE passed 4 cases'}))
        self.assertTrue(boundary.inspected)
        self.assertTrue(boundary.edited)

    def test_real_cli_dry_run_consumes_no_guard_or_authorization(self):
        config=json.loads(CONFIG.read_text())
        destination=ROOT/config['run_dir']
        occupied=destination.exists()
        before=(destination/'trajectory.json').read_bytes() if occupied else None
        env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')}
        result=subprocess.run(['python3',str(ROOT/'scripts/benchmark_functional_check.py'),'--config',str(CONFIG),
            '--run-dir',str(destination),'--dry-run'],env=env,capture_output=True,text=True)
        if occupied:
            self.assertNotEqual(result.returncode,0)
            self.assertIn('already claimed',result.stderr)
            self.assertEqual((destination/'trajectory.json').read_bytes(),before)
            return  # Completed historical admission must remain refused.
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['provider_requests'],0)
        self.assertEqual(report['budgets']['model_calls'],12)
        self.assertFalse(report['live_admission'])
        self.assertFalse(destination.exists())
        with self.assertRaisesRegex(ValidationError,'new spending authorization'):
            execute_confirmation12(CONFIG,None,destination,approve_live=True)

    def test_configuration_changes_and_old_authorization_cannot_admit_live(self):
        config=json.loads(CONFIG.read_text())
        with tempfile.TemporaryDirectory() as t:
            altered=Path(t).resolve()/'config.json'
            altered.write_text(json.dumps({**config,'budgets':{**config['budgets'],'model_calls':13}}))
            with self.assertRaisesRegex(ValidationError,'configuration changed'):
                execute_confirmation12(altered,None,ROOT/config['run_dir'],dry_run=True)
            old=ROOT/'results/listing-decision-diagnostic/authorization.json'
            with self.assertRaises((ValidationError,KeyError)):
                execute_confirmation12(CONFIG,old,ROOT/config['run_dir'],approve_live=True)

    def test_prepared_execution_path_uses_real_loop_and_archives_before_adapter(self):
        import scripts.benchmark_functional_check as script
        config=json.loads(CONFIG.read_text())
        image=json.loads((ROOT/'.cache/swebench-evaluator/prepared-task-image.json').read_text())['image_id']
        actions=[{'tool':'read_file','path':'ledger.py'},
                 {'tool':'write_file','path':'ledger.py','content':'OFFLINE fixture edit'},
                 {'tool':'shell','command':'python3 check_public.py'}]
        sent=[]
        class Session(OfflineSession):
            def __init__(self,*args,**kwargs): super().__init__()
            def close(self): pass
            def execute(self,action):
                return {**super().execute(action),'changed_paths':['ledger.py'] if action['tool']=='write_file' else [],
                        'output':'PUBLIC_ACCEPTANCE passed 4 cases'}
        def transport(body,key,**kwargs):
            sent.append(body)
            service=native_response(MINI,{'action':actions[len(sent)-1],'claims':[]})
            kwargs['response_observer'](json.dumps(service).encode(),200,False)
            return service,'offline-functional-fixture'
        with tempfile.TemporaryDirectory() as t:
            temporary=Path(t).resolve()
            from tests.test_functional_public import prepare
            prepare(temporary)
            local_config=temporary/'configs/functional-confirmation12-v1.json'
            auth=temporary/'authorization.json'
            auth.write_text(json.dumps({'version':config['version'],'config_sha256':digest(config),
                'run_dir':config['run_dir'],'attempts':1,'user_authorized':True,'swebench_authorized':False,'cap_usd':'.50',
                'software_fixture_only':True}))
            def owned(root,name): return RawRun(temporary,name)
            with patch.object(script,'ROOT',temporary),patch.object(script,'RawRun',owned), patch.object(script,'RepositorySession',Session), \
                 patch.object(script,'docker',return_value=SimpleNamespace(stdout=json.dumps([{'Id':image}]).encode())), \
                 patch.object(script,'load_project_env',return_value={'present':{'OPENROUTER_API_KEY':True}}), \
                 patch.object(script,'check_public_catalog',return_value={'software_fixture_only':True}), \
                 patch.object(script,'NativeTokenizer',Counter), patch.object(script,'http_transport',transport), \
                 patch.object(script,'initialize_public_fixture',return_value='offline-base'), \
                 patch.object(script,'assess_public_fixture',return_value={'status':'passed','software_fixture_only':True}), \
                 patch.dict('os.environ',{'OPENROUTER_API_KEY':'offline-fixture-key'}):
                self.assertEqual(execute_confirmation12(local_config,auth,temporary/config['run_dir'],approve_live=True),0)
                with self.assertRaises(FileExistsError):
                    execute_confirmation12(local_config,auth,temporary/config['run_dir'],approve_live=True)
            saved=temporary/Path(config['run_dir']).name
            self.assertEqual(len(sent),3)
            self.assertTrue(all(body['response_format']=={'type':'json_object'} for body in sent))
            measurements=json.loads((saved/'response-measurements.json').read_text())
            self.assertEqual(measurements['actual_responses_received'],3)
            self.assertEqual(measurements['measurements']['tool_execution_successful']['count'],3)
            self.assertTrue(json.loads((saved/'spending.json').read_text())['stopped'])
            RawRun.open_existing(saved.parent,saved.name).load_frozen()


if __name__ == '__main__': unittest.main()
