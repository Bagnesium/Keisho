"""Prospective binding and shared-loop parity; no benchmark is executed."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES
from keisho.benchmark import comparison as c
from keisho.core import digest, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from tests.test_agent_wire_contract import Counter, OfflineSession, native_response
from scripts import benchmark_functional_check as functional


class Version13Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT/'configs/swebench-comparison-v1.3.json')
        self.prior = c.read_input(c.ROOT/'configs/swebench-comparison-v1.2.json')

    def test_only_wire_and_audit_contract_change(self):
        changed = {key for key in self.config.keys() | self.prior.keys()
                   if self.config.get(key) != self.prior.get(key)}
        self.assertEqual(changed, {'version', 'supersedes_configuration', 'action_contract_version',
            'action_contract_sha256', 'action_wire_version', 'internal_action_contract_version',
            'internal_action_contract_sha256', 'execution_contract_version', 'measurement_version'})
        self.assertEqual(c.response_settings(self.config), c.response_settings(self.prior))
        self.assertEqual(self.config['internal_action_contract_sha256'], self.prior['action_contract_sha256'])
        self.assertEqual(digest(self.config), c.WIRE_SPEC_SHA)
        self.assertEqual(c.action_wire_options(self.prior), {})
        self.assertEqual(c.action_wire_options(self.config), {'action_wire_version':'flat-or-args/1.0'})

    def test_pending_comparison_binding_never_authorizes_execution(self):
        with tempfile.TemporaryDirectory() as t:
            output = Path(t).resolve()/'never-started'
            args = {'config_path':c.ROOT/'configs/swebench-comparison-v1.3.json',
                    'plan_path':c.ROOT/'analysis/swebench-comparison-v1.3-plan.json',
                    'authorization_path':c.ROOT/'analysis/swebench-comparison-v1.3-authorization-template.json',
                    'run_dir':output}
            binding = c.resolve_binding(**args, allow_pending=True)
            self.assertFalse(binding.authorization['provider_inference_authorized'])
            with self.assertRaisesRegex(ValidationError, 'not authorized'):
                c.resolve_binding(**args)
            self.assertFalse(output.exists())

    def test_interface_mutation_and_rehashed_plan_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            config = {**self.config, 'action_wire_version':'unregistered/1.0'}
            plan = c.read_input(c.ROOT/'analysis/swebench-comparison-v1.3-plan.json')
            plan['config_sha256'] = digest(config)
            (root/'config.json').write_text(json.dumps(config))
            (root/'plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValidationError, 'frozen supported specification'):
                c.load_frozen_plan(root/'config.json', root/'plan.json')

    def test_pending_functional_public_dry_run_and_live_gate(self):
        config = c.ROOT/'configs/functional-confirmation12-v1.3.json'
        auth = c.ROOT/'analysis/functional-confirmation12-v1.3-authorization-template.json'
        output = c.ROOT/c.read_input(config)['run_dir']
        occupied = output.exists()
        before = (output/'trajectory.json').read_bytes() if occupied else None
        result = subprocess.run([sys.executable, str(c.ROOT/'scripts/benchmark_functional_check.py'),
            '--config',str(config),'--authorization',str(auth),'--run-dir',str(output),'--dry-run'],
            cwd=c.ROOT,capture_output=True,text=True)
        if occupied:
            self.assertNotEqual(result.returncode,0)
            self.assertIn('already claimed',result.stderr)
            self.assertEqual((output/'trajectory.json').read_bytes(),before)
            return  # The sealed successful confirmation must remain refused.
        self.assertEqual(result.returncode,0,result.stderr)
        record = json.loads(result.stdout)
        self.assertFalse(record['live_admission'])
        self.assertFalse(record['live_guard_created'])
        self.assertEqual(record['provider_requests'],0)
        self.assertEqual(record['action_wire_version'],'flat-or-args/1.0')
        with patch.object(functional,'check_public_catalog',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(ValidationError,'authorization'):
                functional.execute_confirmation12(config,auth,output,approve_live=True)
        self.assertFalse(output.exists())

    def test_predecessor_and_all_successor_conditions_use_identical_adapter(self):
        capture = c.read_input(c.ROOT/'tests/data/action-wire-v13-response.json')
        archived = json.loads(base64.b64decode(capture['body_base64']))['choices'][0]['message']['content']
        options = c.action_wire_options(self.config)
        system,policy,output_format = c.response_settings(self.config)
        cases = [('predecessor','predecessor')] + [('successor',name) for name in self.config['conditions']]
        for role,condition in cases:
            with self.subTest(condition=condition),tempfile.TemporaryDirectory() as t:
                raw = RawRun(Path(t).resolve(), 'unit-loop')
                identity = self.config[role+'_model']
                sent = []
                def transport(body,key):
                    sent.append(body)
                    service = native_response(identity, {'action':{'tool':'finish','args':{'answer':'offline unit fixture'}},'claims':[]})
                    if len(sent)==1: service['choices'][0]['message']['content']=archived
                    return service,'SYNTHETIC-NO-NETWORK'
                model = OpenRouterChatModel(identity,authorized=True,api_key='offline-key',tokenizer=Counter(),
                    transport=transport,response_model_ids=(MODEL_ALIASES[identity],identity),
                    agent_response_format=output_format)
                session = OfflineSession();session.listing_policy='bounded-listing/1.0'
                execution = run_agent(model,session,Recorder(raw),'offline unit objective',system,'',
                    1,Budgets(2,2,2048,20000,32000,128000),role=role,response_policy=policy,**options)
                self.assertEqual((execution.reason,execution.model_calls,execution.tool_calls),('finished',2,1))
                self.assertEqual(session.actions,[{'tool':'list_files','limit':100}])
                self.assertEqual(sent[0]['response_format'],{'type':'json_object'})
                self.assertEqual(sent[1]['messages'][3]['content'],archived)
                events = raw.freeze().events
                responses = [json.loads(e.payload_json) for e in events if e.kind.value=='model_response']
                self.assertEqual(responses[0]['text'],archived)
                audit = json.loads((raw.path/f'{role}_call_001-action-wire.json').read_text())
                self.assertEqual(audit['input_action_shape'],'nested_args')
                self.assertTrue(audit['canonicalization_occurred'])
                self.assertEqual(audit['canonical_action'],session.actions[0])
                self.assertEqual(audit['validation_result'],'accepted')
                self.assertFalse(any('wire_version' in json.loads(e.payload_json) for e in events))


if __name__ == '__main__': unittest.main()
