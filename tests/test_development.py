from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel,MODEL_ALIASES
from keisho.core import canonical_json,utc_now
from keisho.development.checkpoint import assess
from keisho.development.comparison import execute,load_prepared,plan,prepare,DevelopmentSpendLedger
from keisho.development.suite import IDS,ROOT,check_workspace,load_public,validate_suite,verify_development_sandbox,write_workspace,behavior_equal
from keisho.handoff.bundle import inspect,pack,resume
from keisho.handoff.compact import Counter
from keisho.logging.raw import RawRun,Event,EventKind,FrozenTrajectory
from keisho.pilot.cli import main
from keisho.pilot.tasks import REPO


class CheckpointTests(unittest.TestCase):
    def test_behavior_accepts_equivalent_numeric_output_but_not_boolean_substitution(self):
        self.assertTrue(behavior_equal({'timeout':2.0},{'timeout':2}))
        self.assertFalse(behavior_equal({'timeout':True},{'timeout':1}))
    def trace(self,count=12,failed_fix=False):
        events=[Event('predecessor_task',EventKind.USER_MESSAGE,'user',utc_now(),canonical_json({'content':'Task'}))]
        for n in range(count):
            action={'tool':'write_file','path':'worker.py'} if failed_fix and n==0 else {'tool':'read_file','path':'worker.py'}
            events.append(Event(f'call{n}',EventKind.TOOL_CALL,'predecessor',utc_now(),canonical_json({'action':action})))
            payload={'action':action,'content':'unfinished code','source_hashes_after':{'worker.py':'a'*64}}
            if failed_fix and n==1:payload['results']=[{'id':'recovery','passed':False}]
            events.append(Event(f'result{n}',EventKind.TOOL_RESULT,'predecessor',utc_now(),canonical_json(payload),(f'call{n}',)))
        return FrozenTrajectory.create(tuple(events))
    def test_general_continuation_does_not_need_wrong_hypothesis_or_failure(self):
        result=assess(self.trace(),[{'passed':False}])
        self.assertTrue(result['continuation_eligible'])
        self.assertFalse(result['repeated_failure_analysis']['applicable'])
        self.assertIsNone(result['repeated_failure_analysis']['metric_if_no_opportunity'])
        self.assertFalse(result['uses_hidden_evaluator_information'])
    def test_early_solution_low_information_retrospective_and_failed_fix_are_distinct(self):
        self.assertFalse(assess(self.trace(),[{'passed':True}])['continuation_eligible'])
        self.assertFalse(assess(self.trace(2),[{'passed':False}])['continuation_eligible'])
        self.assertTrue(assess(self.trace(2),[{'passed':False}],mode='user')['continuation_eligible'])
        self.assertTrue(assess(self.trace(2),[{'passed':False}],mode='retrospective-development')['retrospective'])
        self.assertTrue(assess(self.trace(failed_fix=True),[{'passed':False}])['repeated_failure_analysis']['applicable'])
    def test_fresh_paid_gate_and_cap_does_not_reuse_calibration(self):
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network forbidden')):
            self.assertEqual(main(['dev-continue','not-created']),2)
        with self.assertRaises(ValueError):DevelopmentSpendLedger('3',lambda _:None,fresh_explicit_approval=False)
        ledger=DevelopmentSpendLedger('3',lambda _:None,fresh_explicit_approval=True)
        self.assertEqual(ledger.cap,Decimal('3'));self.assertEqual(ledger.multiplier,Decimal('1.05'))
        report=plan();self.assertEqual(report['generation_calls'],0)
        self.assertFalse(report['paid_execution_authorized'])
        self.assertEqual(report['worst_case_successor_api_usage_usd'],'2.6595072')


@unittest.skipUnless(sys.platform=='darwin' and shutil.which('sandbox-exec'),'macOS isolation required')
class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
    def test_six_behavioral_initial_failures_references_and_incomplete_fixes(self):
        report=validate_suite()
        self.assertEqual({row['task_id'] for row in report['records']},set(IDS))
        for row in report['records']:
            self.assertFalse(row['outcomes']['initial']['passed']);self.assertTrue(row['outcomes']['reference']['passed'])
            self.assertFalse(row['outcomes']['incomplete']['passed'])
            self.assertTrue(any('generated_' in case['id'] for case in row['outcomes']['reference']['results']))
    def test_restored_real_application_runs_checks_under_scratch_only_isolation(self):
        task,public=load_public('jobs_duplicate');repo=self.root/'task';write_workspace(repo,task.files)
        notes=self.root/'notes.json';notes.write_text(json.dumps({'version':'keisho-notes/1.0','acceptance':public['acceptance'],'constraints':public['constraints'],
            'sources':[{'id':'observed','text':'A reference candidate still needs implementation and recovery validation'}],
            'items':[{'id':'result','category':'hypothesis','text':'Recipient deduplication might suffice','status':'HYPOTHESIZED','source_ids':['observed'],
                      'scope':{'files':{'results.py':hashlib.sha256((repo/'results.py').read_bytes()).hexdigest()},'environment':'duplicate delivery only'}}]}))
        bundle=self.root/'bundle';restored=self.root/'restored'
        def cli(*args):
            return subprocess.run([str(REPO/'keisho'),*map(str,args)],cwd=REPO,capture_output=True,text=True)
        packed=cli('pack','--repo',repo,'--session',notes,'--task',task.description,'--out',bundle,'--token-budget','4096')
        self.assertEqual(packed.returncode,0,packed.stdout+packed.stderr)
        inspected=cli('inspect',bundle,'--item','result')
        self.assertEqual(inspected.returncode,0,inspected.stdout+inspected.stderr)
        continued=cli('resume',bundle,'--manual','--workspace',restored)
        self.assertEqual(continued.returncode,0,continued.stdout+continued.stderr)
        sandbox=verify_development_sandbox(self.root/'probes')
        self.assertFalse(all(row['passed'] for row in check_workspace(task.id,restored,sandbox)['results']))
        public_initial=cli('dev-check',task.id,'--workspace',restored,'--public')
        self.assertEqual(public_initial.returncode,1,public_initial.stdout+public_initial.stderr)
        for file in (ROOT/'private'/task.id/'reference').glob('*.py'):(restored/file.name).write_text(file.read_text())
        self.assertTrue(all(row['passed'] for row in check_workspace(task.id,restored,sandbox)['results']))
        public_reference=cli('dev-check',task.id,'--workspace',restored,'--public')
        self.assertEqual(public_reference.returncode,0,public_reference.stdout+public_reference.stderr)
        self.assertTrue(inspect(bundle,compare_workspace=restored)['scope_comparison']['result']['requires_revalidation'])
        self.assertEqual((repo/'results.py').read_text(),task.files['results.py'])
        (restored/'isolation_checks.py').write_text("""from pathlib import Path
def check(forbidden):
    def can_read(path):
        try: return bool(Path(path).read_bytes())
        except OSError: return False
    blocked=False
    try: Path('diagnostics.py').write_text('tampered')
    except PermissionError: blocked=True
    Path('.runtime/probe').write_text('allowed')
    return {'outside_read':can_read(forbidden),'code_write_blocked':blocked,'scratch':Path('.runtime/probe').read_text()}
""")
        output=sandbox.run(restored,({'id':'isolation','module':'isolation_checks','function':'check','args':[str(bundle/'evidence/session.json')]},))
        self.assertEqual(output['results'][0]['value'],{'outside_read':False,'code_write_blocked':True,'scratch':'allowed'})
    def prepared(self):
        task,public=load_public('migration_cache');repo=self.root/'repo';write_workspace(repo,task.files)
        raw=RawRun(self.root/'trace','synthetic-software-fixture')
        raw.append(Event('predecessor_task',EventKind.USER_MESSAGE,'user',utc_now(),canonical_json({'content':task.description})))
        raw.append(Event('origin',EventKind.ANNOTATION,'fixture',utc_now(),canonical_json({'origin':'synthetic software test; no model behavior evidence','type':'local_task_state','acceptance':public['acceptance'],'constraints':public['constraints']})))
        hashes={name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in task.editable_files}
        for n in range(12):
            action={'tool':'read_file','path':'cache.py'};call=f'tool{n}'
            raw.append(Event(call,EventKind.TOOL_CALL,'fixture',utc_now(),canonical_json({'action':action})))
            raw.append(Event(f'result{n}',EventKind.TOOL_RESULT,'fixture',utc_now(),canonical_json({'action':action,'path':'cache.py','content':task.files['cache.py'],'source_hashes_before':hashes,'source_hashes_after':hashes}),(call,)))
        raw.freeze();bundle,_=pack(repo,raw.path,task.description,self.root/'bundle')
        prepared=prepare(task.id,bundle,self.root/'prepared')
        return task,prepared
    def test_four_conditions_same_material_budgets_no_archive_and_zero_generation_calls(self):
        task,prepared=self.prepared()
        self.assertTrue(prepared['checkpoint_qualified'])
        self.assertIn('.runtime',json.loads((self.root/'prepared/snapshot.json').read_text())['directories'])
        self.assertEqual(set(prepared['conditions']),{'NO_CONTEXT','FULL_HISTORY','SUMMARY_2K','KEISHO_2K'})
        self.assertEqual(prepared['conditions']['NO_CONTEXT']['tokens']['count'],0)
        self.assertLessEqual(prepared['conditions']['SUMMARY_2K']['tokens']['count'],2048)
        self.assertLessEqual(prepared['conditions']['KEISHO_2K']['tokens']['count'],2048)
        self.assertEqual(prepared['summary_generation']['api_calls'],0)
        self.assertGreater(prepared['conditions']['FULL_HISTORY']['tokens']['count'],prepared['conditions']['KEISHO_2K']['tokens']['count'])
        reference={p.name:p.read_text() for p in (ROOT/'private'/task.id/'reference').glob('*.py')}
        identity=tuple(MODEL_ALIASES)[1];alias=MODEL_ALIASES[identity];counter=Counter().native
        def factory(condition):
            responses=iter([canonical_json({'action':{'tool':'write_file','path':'cache.py','content':reference['cache.py']},'claims':[]}),canonical_json({'action':{'tool':'run_tests','test_ids':['full']},'claims':[]})])
            def transport(body,key):
                text=next(responses)
                return {'model':alias,'provider':'OpenAI','choices':[{'message':{'content':text},'finish_reason':'stop'}],
                        'usage':{'prompt_tokens':sum(counter.count(message['content']).count for message in body['messages']),
                                 'completion_tokens':counter.count(text).count,'is_byok':False,'cost':0}},None
            return OpenRouterChatModel(identity,authorized=True,api_key='synthetic-offline-key',transport=transport,tokenizer=counter,response_model_ids=[alias,identity])
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('offline only')):
            path=execute(self.root/'prepared','3',factory=factory,synthetic=True,raw_root=self.root/'raw')
        result=json.loads((path/'result.json').read_text())
        self.assertEqual(result['status'],'complete');self.assertEqual(len(result['branches']),4)
        self.assertTrue(all(row['task_success'] for row in result['branches']))
        self.assertIsNone(result['end_to_end_cost_usd'])
        with self.assertRaises(FileExistsError):execute(self.root/'prepared','3',factory=factory,synthetic=True,raw_root=self.root/'raw')
        (self.root/'prepared/conditions/FULL_HISTORY.md').write_text('corrupt')
        with self.assertRaises(ValueError):load_prepared(self.root/'prepared')


if __name__=='__main__':unittest.main()
