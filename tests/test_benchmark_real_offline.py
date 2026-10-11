"""Actual public subprocess, Docker tools and five independent synthetic branches.

Branch grading here is an explicitly synthetic fixture. An unchanged official
checkpoint evaluation is separately archived, not repeatedly run by this test.
"""
import json
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

from keisho.benchmark.comparison import ROOT
from keisho.logging.raw import RawRun


class PublicFiveWayTests(unittest.TestCase):
    def test_real_public_five_way_contexts_patches_and_gates(self):
        output = ROOT/'runs'/('offline-sprint-test-'+uuid.uuid4().hex[:12])
        command = [sys.executable,str(ROOT/'tests/run_offline_benchmark.py'),'--output',str(output)]
        result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=240)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        run = output/'runs/five-way-synthetic'
        summary = json.loads((run/'result.json').read_text())
        self.assertTrue(summary['synthetic_engineering_check'])
        self.assertEqual(summary['actual_provider_cost_usd'],'0')
        self.assertEqual(summary['predecessor']['reason'],'checkpoint')
        predecessor = run/'predecessor'
        checkpoint = json.loads((predecessor/'checkpoint.json').read_text())
        handoffs = json.loads((predecessor/'handoffs.json').read_text())
        self.assertEqual(handoffs['official_classification'],'withheld')
        self.assertIn('REVALIDATE scope: xarray/__init__.py',handoffs['texts']['KEISHO_2K'])
        for condition in ('SUMMARY_2K','STRUCTURED_NOTES_2K','KEISHO_2K'):
            self.assertLessEqual(handoffs['tokens'][condition],2048)
        frozen = RawRun.open_existing(run, 'predecessor').load_frozen()
        self.assertEqual(handoffs['source_trajectory_sha256'],frozen.sha256)
        common = None
        identifiers = {summary['checkpoint_classification']['run_id']}
        for condition, row in summary['conditions'].items():
            branch = run/condition
            data = json.loads((branch/'input.json').read_text())
            self.assertEqual(data['image_id'],checkpoint['image_id'])
            current = (data['task'],data['system'],data['budgets'],data['seed'])
            if common is None: common = current
            self.assertEqual(common,current)
            self.assertEqual(data['handoff'],handoffs['texts'][condition])
            patch = json.loads((branch/'prediction.json').read_text())['model_patch']
            self.assertIn('+\n+# SYNTHETIC_PREDECESSOR_ENGINEERING_MARKER',patch)
            if condition=='FULL_HISTORY':self.assertIn('SYNTHETIC_SUCCESSOR_ENGINEERING_MARKER',patch)
            else:self.assertNotIn('SYNTHETIC_SUCCESSOR_ENGINEERING_MARKER',patch)
            first = json.loads((branch/'wire-request-001.json').read_text())
            self.assertEqual(len(first['messages']),3)
            self.assertEqual(first['response_format'],{'type':'json_object'})
            self.assertEqual(first['messages'][1]['content'],data['task']['problem_statement'])
            for path in branch.glob('wire-request-*.json'):
                text = path.read_text()
                for forbidden in ('OFFLINE_HOST_CANARY','OFFLINE_HOST_CANARY_OPENAI',
                                  'SYNTHETIC_SUCCESSOR_ENGINEERING_MARKER' if condition!='FULL_HISTORY' else 'NO_REAL_SECRET',
                                  'FAIL_TO_PASS','PASS_TO_PASS','selected-task-evaluator.jsonl',
                                  'checkpoint-grade-private','ModuleNotFoundError'):
                    self.assertNotIn(forbidden,text)
            self.assertTrue(row['official_evaluation']['synthetic_grading_fixture'])
            self.assertFalse(row['official_evaluation']['official_grade'])
            self.assertNotIn(row['official_evaluation']['run_id'],identifiers)
            identifiers.add(row['official_evaluation']['run_id'])
            measurements = json.loads((branch/'response-measurements.json').read_text())
            self.assertEqual(measurements['actual_responses_received'],row['model_calls'])
            RawRun.open_existing(run,condition).load_frozen()
            with self.assertRaises(FileExistsError):RawRun(run,condition)
        self.assertEqual(summary['conditions']['REPOSITORY_ONLY']['status'],'budget_stopped')
        self.assertEqual(summary['conditions']['KEISHO_2K']['reason'],'infrastructure_failure')
        self.assertEqual(summary['conditions']['FULL_HISTORY']['status'],'completed')
        self.assertEqual(summary['conditions']['SUMMARY_2K']['official_status'],'unresolved')
        # Both generators receive byte-identical allowed source packets; private
        # grading and prior successor results cannot enter notes retrospectively.
        notes = run/'note-generation'
        sources = [json.loads((notes/(kind+'_call_'+number+'-request.json')).read_text())
                   for kind,number in (('summary','001'),('structured','002'))]
        packets = []
        for request in sources:
            text = request['messages'][1]['content']
            start = text.index('{"checkpoint_changed_file_inventory":')
            packet, end = json.JSONDecoder().raw_decode(text[start:])
            packets.append(text[start:start+end])
            self.assertIn('observable_events',packet)
        self.assertEqual(packets[0],packets[1])  # Instructions differ; allowed evidence does not.
        ledger = json.loads((run/'spending.json').read_text())
        self.assertEqual(ledger['actual_provider_cost_usd'],'0')
        self.assertTrue(ledger['stopped'])
        self.assertEqual(Decimal(ledger['unreconciled_reservations_usd']),0)
        RawRun.open_existing(run.parent,run.name).load_frozen()
        RawRun.open_existing(output,'synthetic-authorization-claim').load_frozen()

if __name__=='__main__':unittest.main()
