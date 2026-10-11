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

def prepare(root, mode='complete'):
    for name in ('configs/functional-confirmation12-v1.json', 'configs/swebench-comparison-v1.1.json',
                 'configs/calibration-task001-openrouter-v1.2.0.yaml','.cache/swebench-evaluator/prepared-task-image.json',
                 'tasks/task_001/public.json'):
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    shutil.copytree(ROOT/'tasks/task_001/initial', root/'tasks/task_001/initial')
    provider=json.loads((root/'configs/calibration-task001-openrouter-v1.2.0.yaml').read_text())
    ca=Path('configs')/provider['tls']['ca_file']
    (root/ca).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/ca,root/ca)
    config=json.loads((root/'configs/functional-confirmation12-v1.json').read_text())
    auth={'version':config['version'],'config_sha256':digest(config),'run_dir':config['run_dir'],
          'attempts':1,'user_authorized':True,'swebench_authorized':False,'cap_usd':'.50','synthetic_engineering_check':True}
    (root/'authorization.json').write_text(json.dumps(auth))
    (root/'settings.json').write_text(json.dumps({'fixture_root':str(root),'mode':mode,
         'public_entry':str(ROOT/'scripts/benchmark_functional_check.py')}))
    (root/'private-answer-key.txt').write_text('OFFLINE_EVALUATOR_CANARY_NOT_AGENT_VISIBLE')
    return config

def launch(root, interpreter=sys.executable):
    config=json.loads((root/'configs/functional-confirmation12-v1.json').read_text())
    env={**os.environ,'PYTHONPATH':str(ROOT/'tests/offline_launch')+os.pathsep+str(ROOT/'src'),
         'KEISHO_TEST_LAUNCH_SETTINGS':str(root/'settings.json'),
         'OPENROUTER_API_KEY':'OFFLINE_HOST_SECRET_CANARY','OPENAI_API_KEY':'OFFLINE_HOST_OPENAI_CANARY'}
    command=[str(interpreter),str(ROOT/'scripts/benchmark_functional_check.py'),'--config',str(root/'configs/functional-confirmation12-v1.json'),
             '--authorization',str(root/'authorization.json'),'--run-dir',str(root/config['run_dir']),'--approve-live']
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=180)
    (root/'cli-output.txt').write_text(result.stdout+result.stderr)
    (root/'cli-command.json').write_text(json.dumps({'command':command,'exit_code':result.returncode,'synthetic':True}))
    return result, root/config['run_dir']

class PublicFunctionalTests(unittest.TestCase):
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
