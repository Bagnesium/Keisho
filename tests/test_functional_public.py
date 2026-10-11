"""Real public subprocess and real Docker; all provider messages are synthetic."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from keisho.benchmark.comparison import ROOT
from keisho.core import digest
from keisho.logging.raw import RawRun

def prepare(root, mode='complete', config_name='functional-confirmation12-v1.json'):
    config=json.loads((ROOT/'configs'/config_name).read_text())
    for name in ('configs/' + config_name, 'configs/swebench-comparison-v1.1.json', 'configs/swebench-comparison-v1.2.json',
                 'configs/' + config.get('source_comparison_config','swebench-comparison-v1.1.json'),
                 'configs/calibration-task001-openrouter-v1.2.0.yaml','.cache/swebench-evaluator/prepared-task-image.json',
                 'tasks/task_001/public.json'):
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    shutil.copytree(ROOT/'tasks/task_001/initial', root/'tasks/task_001/initial')
    provider=json.loads((root/'configs/calibration-task001-openrouter-v1.2.0.yaml').read_text())
    ca=Path('configs')/provider['tls']['ca_file']
    (root/ca).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/ca,root/ca)
    config=json.loads((root/'configs'/config_name).read_text())
    auth={'version':config['version'],'config_sha256':digest(config),'run_dir':config['run_dir'],
          'attempts':1,'user_authorized':True,'swebench_authorized':False,'cap_usd':'.50','synthetic_engineering_check':True}
    if config.get('action_wire_version'):
        auth['provider_inference_authorized']=True  # Isolated synthetic transport; never a real authorization.
        archived=ROOT/'tests/data/action-wire-v13-response.json'
        historical=ROOT/'runs/functional-confirmation12-v1.2-20261011/wire-response-001.json'
        if historical.exists():assert archived.read_bytes()==historical.read_bytes()
        shutil.copyfile(archived,root/'archived-rejected-wire-response.json')
    (root/'authorization.json').write_text(json.dumps(auth))
    (root/'settings.json').write_text(json.dumps({'fixture_root':str(root),'mode':mode,'config_name':config_name,
         'action_contract_version':config.get('action_contract_version','2.0'),
         'action_wire_version':config.get('action_wire_version'),
         'public_entry':str(ROOT/'scripts/benchmark_functional_check.py')}))
    (root/'private-answer-key.txt').write_text('OFFLINE_EVALUATOR_CANARY_NOT_AGENT_VISIBLE')
    return config

def launch(root, interpreter=sys.executable):
    settings=json.loads((root/'settings.json').read_text())
    config_path=root/'configs'/settings['config_name']
    config=json.loads(config_path.read_text())
    env={**os.environ,'PYTHONPATH':str(ROOT/'tests/offline_launch')+os.pathsep+str(ROOT/'src'),
         'KEISHO_TEST_LAUNCH_SETTINGS':str(root/'settings.json'),
         'OPENROUTER_API_KEY':'OFFLINE_HOST_SECRET_CANARY','OPENAI_API_KEY':'OFFLINE_HOST_OPENAI_CANARY'}
    command=[str(interpreter),str(ROOT/'scripts/benchmark_functional_check.py'),'--config',str(config_path),
             '--authorization',str(root/'authorization.json'),'--run-dir',str(root/config['run_dir']),'--approve-live']
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=180)
    (root/'cli-output.txt').write_text(result.stdout+result.stderr)
    (root/'cli-command.json').write_text(json.dumps({'command':command,'exit_code':result.returncode,'synthetic':True,
        'provider_transport':'tests/offline_launch/functional_injection.py','provider_network_requests':0}))
    return result, root/config['run_dir']

class PublicFunctionalTests(unittest.TestCase):
    def test_version13_public_cli_canonicalizes_actual_rejected_response_in_real_docker(self):
        import base64
        historical=ROOT/'runs/functional-confirmation12-v1.2-20261011'
        names=('wire-response-001.json','predecessor_call_001-response.json','trajectory.json','result.json','spending.json')
        sealed={name:(historical/name).read_bytes() for name in names}
        original=json.loads(base64.b64decode(json.loads(sealed['wire-response-001.json'])['body_base64']))['choices'][0]['message']['content']
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();config=prepare(root,config_name='functional-confirmation12-v1.3.json')
            result,run=launch(root)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            outcome=json.loads((run/'result.json').read_text())
            self.assertEqual(outcome['status'],'passed')
            for field in ('synthetic_engineering_check','model_executed_post_edit_public_test','post_edit_acceptance_marker',
                          'independent_public_test_passed','immutable_inputs_preserved','allowed_source_changes_only'):
                self.assertTrue(outcome[field],field)
            first=json.loads((run/'predecessor_call_001-response.json').read_text())
            self.assertEqual(first['text'],original)
            capture=json.loads((run/'wire-response-001.json').read_text())
            native=json.loads(base64.b64decode(capture['body_base64']))
            self.assertEqual(native['choices'][0]['message']['content'],original)
            self.assertTrue(native['synthetic'])
            self.assertEqual(native['usage']['cost'],'0')
            request=json.loads((run/'wire-request-001.json').read_text())
            self.assertEqual(request['response_format'],{'type':'json_object'})
            self.assertEqual(digest(request['messages'][0]['content']),config['system_sha256'])
            self.assertEqual(config['system_sha256'],json.loads((ROOT/'configs/functional-confirmation12-v1.2.json').read_text())['system_sha256'])
            wire=json.loads((run/'predecessor_call_001-action-wire.json').read_text())
            self.assertEqual(wire['input_action_shape'],'nested_args')
            self.assertTrue(wire['canonicalization_occurred'])
            self.assertEqual(wire['original_action'],{'tool':'list_files','args':{'limit':100}})
            self.assertEqual(wire['canonical_action'],{'tool':'list_files','limit':100})
            self.assertEqual(wire['validation_result'],'accepted')
            self.assertIsNone(wire['rejection_reason'])
            listing=json.loads((run/'tool-observable-001.json').read_text())
            self.assertEqual(listing['action'],wire['canonical_action'])
            self.assertEqual(len(listing['files']),6)
            measurements=json.loads((run/'response-measurements.json').read_text())
            self.assertEqual(measurements['actual_responses_received'],5)
            self.assertEqual(measurements['measurements']['action_schema_valid']['valid_count'],5)
            self.assertEqual(measurements['measurements']['tool_execution_completed']['count'],5)
            self.assertEqual(measurements['measurements']['auxiliary_annotations_valid']['invalid_count'],1)
            measured=measurements['rows'][0]
            self.assertEqual(measured['proposed_action'],wire['original_action'])
            self.assertEqual(measured['canonical_action'],wire['canonical_action'])
            self.assertTrue(measured['wire_action_schema_valid'])
            self.assertTrue(measured['canonical_action_schema_valid'])
            self.assertEqual(measured['action_wire_audit'],wire)
            self.assertEqual(measured['action_admission_audit']['runtime_validation_result'],'completed')
            ledger=json.loads((run/'spending.json').read_text())
            self.assertEqual(len(ledger['attempts']),5)
            self.assertEqual(ledger['actual_provider_cost_usd'],'0')
            frozen=RawRun.open_existing(run.parent,run.name).load_frozen()
            for event in frozen.events:
                if event.kind.value=='annotation':
                    self.assertNotIn(json.loads(event.payload_json).get('type'),('action_wire','action_admission'))
        self.assertEqual({name:(historical/name).read_bytes() for name in names},sealed)

    def test_version12_public_cli_uses_repaired_prompt_and_bounded_listing(self):
        historical=ROOT/'runs/functional-confirmation12-v1/trajectory.json'
        before=historical.read_bytes()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()
            config=prepare(root, config_name='functional-confirmation12-v1.2.json')
            result,run=launch(root)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            outcome=json.loads((run/'result.json').read_text())
            self.assertEqual(outcome['status'],'passed')
            self.assertTrue(outcome['model_executed_post_edit_public_test'])
            self.assertTrue(outcome['post_edit_acceptance_marker'])
            self.assertTrue(outcome['independent_public_test_passed'])
            self.assertTrue(outcome['immutable_inputs_preserved'])
            self.assertTrue(outcome['allowed_source_changes_only'])
            request=json.loads((run/'wire-request-001.json').read_text())
            self.assertEqual(request['response_format'],{'type':'json_object'})
            self.assertEqual(digest(request['messages'][0]['content']),config['system_sha256'])
            self.assertIn('benchmark-agent/3.0',request['messages'][0]['content'])
            listing=json.loads((run/'tool-observable-001.json').read_text())
            self.assertEqual(listing['action'],{'tool':'list_files','prefix':'','limit':2})
            self.assertTrue(listing['has_more'])
            self.assertEqual(len(listing['files']),2)
            measurements=json.loads((run/'response-measurements.json').read_text())
            self.assertEqual(measurements['actual_responses_received'],5)
            self.assertEqual(measurements['measurements']['action_schema_valid']['valid_count'],5)
            self.assertEqual(measurements['measurements']['tool_execution_completed']['count'],5)
            ledger=json.loads((run/'spending.json').read_text())
            self.assertEqual(len(ledger['attempts']),5)
            self.assertEqual(ledger['actual_provider_cost_usd'],'0')
            self.assertEqual(ledger['cap_usd'],'0.50')
            RawRun.open_existing(run.parent,run.name).load_frozen()
            again,_=launch(root)
            self.assertNotEqual(again.returncode,0)
            self.assertIn('already claimed',again.stderr)
        self.assertEqual(historical.read_bytes(),before)

    def test_actual_public_subprocess_complete_loop_and_callback(self):
        for interpreter in (shutil.which('python3'),ROOT/'.cache/swebench-evaluator/venv/bin/python'):
            with self.subTest(interpreter=str(interpreter)), tempfile.TemporaryDirectory() as t:
                root=Path(t).resolve();prepare(root)
                result,run=launch(root,interpreter)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                outcome=json.loads((run/'result.json').read_text())
                self.assertTrue(outcome['synthetic_engineering_check'])
                self.assertEqual(outcome['status'],'passed')
                self.assertTrue(outcome['model_executed_post_edit_public_test'])
                self.assertTrue(outcome['independent_public_test_passed'])
                events=RawRun.open_existing(run.parent,run.name).load_frozen().events
                actions=[json.loads(e.payload_json)['action'] for e in events if e.kind.value=='tool_call']
                self.assertEqual([a['tool'] for a in actions],['list_files','read_file','shell','write_file','shell'])
                results=[json.loads(e.payload_json) for e in events if e.kind.value=='tool_result']
                self.assertEqual((results[2]['exit_code'],results[4]['exit_code']),(1,0))
                self.assertEqual(results[3]['changed_paths'],['ledger.py'])
                measurements=json.loads((run/'response-measurements.json').read_text())
                self.assertEqual(measurements['actual_responses_received'],5)
                self.assertEqual(measurements['measurements']['auxiliary_annotations_valid']['invalid_count'],1)
                self.assertEqual(measurements['measurements']['tool_execution_completed']['count'],5)
                self.assertEqual(measurements['measurements']['tool_execution_successful']['count'],4)
                for n in range(1,6):
                    body=json.loads((run/f'wire-request-{n:03d}.json').read_text())
                    self.assertEqual(len(body['messages']),3+2*(n-1))
                    for prior in range(1,n):
                        self.assertEqual(body['messages'][1+2*prior]['content'],json.loads((run/f'predecessor_call_{prior:03d}-response.json').read_text())['text'])
                ledger=json.loads((run/'spending.json').read_text())
                self.assertEqual(len(ledger['attempts']),5);self.assertTrue(ledger['stopped'])
                self.assertEqual(ledger['actual_provider_cost_usd'],'0')
                with self.assertRaises(FileExistsError):RawRun(run.parent,run.name)
                for path in run.rglob('*.json'):
                    text=path.read_text()
                    self.assertNotIn('OFFLINE_HOST_SECRET_CANARY',text)
                    self.assertNotIn('OFFLINE_HOST_OPENAI_CANARY',text)
                    self.assertNotIn('OFFLINE_EVALUATOR_CANARY_NOT_AGENT_VISIBLE',text)

    def test_invalid_json_and_arguments_fail_without_repair_or_retry(self):
        for mode in ('invalid_json','invalid_action','invalid_action_schema','provider_failure','infrastructure','task_failure','budget'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                root=Path(t).resolve();prepare(root,mode)
                result,run=launch(root)
                self.assertNotEqual(result.returncode,0)
                outcome=json.loads((run/'result.json').read_text())
                self.assertEqual(outcome['status'],'failed',result.stdout+result.stderr)
                measurements=json.loads((run/'response-measurements.json').read_text())
                expected=12 if mode=='budget' else 5 if mode=='task_failure' else 1
                self.assertEqual(measurements['generation_calls_logged'],expected)
                if mode=='invalid_json':self.assertEqual(measurements['measurements']['json_syntax_valid']['invalid_count'],1)
                if mode=='invalid_action':self.assertEqual(measurements['measurements']['safety_valid']['invalid_count'],1)
                if mode=='invalid_action_schema':
                    self.assertEqual(measurements['measurements']['json_syntax_valid']['valid_count'],1)
                    self.assertEqual(measurements['measurements']['action_schema_valid']['invalid_count'],1)
                    self.assertEqual(measurements['measurements']['tool_execution_completed']['count'],0)
                if mode=='provider_failure':self.assertEqual(measurements['missing_model_responses'],1)
                if mode=='budget':self.assertEqual(outcome['execution']['reason'],'budget_exhausted')
                RawRun.open_existing(run.parent,run.name).load_frozen()

if __name__=='__main__':unittest.main()
