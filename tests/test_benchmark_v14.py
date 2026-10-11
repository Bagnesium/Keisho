"""Prospective freeze/parity and refusal gates; no comparison is launched."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES
from keisho.benchmark import comparison as c
from keisho.benchmark.experiment_freeze import validate_freeze
from keisho.core import digest, ValidationError
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.response_policy import ANNOTATION_GUIDANCE, AUXILIARY
from tests.test_agent_wire_contract import Counter, OfflineSession, native_response


class Version14Tests(unittest.TestCase):
    def setUp(self):
        self.config = c.read_input(c.ROOT/'configs/swebench-comparison-v1.4.json')
        self.prior = c.read_input(c.ROOT/'configs/swebench-comparison-v1.3.json')

    def test_only_registered_prospective_changes(self):
        changed = {k for k in self.config.keys() | self.prior.keys()
                   if self.config.get(k) != self.prior.get(k)}
        self.assertEqual(changed, {'version','supersedes_configuration','agent_prompt_version',
            'agent_prompt_sha256','annotation_guidance_version','annotation_guidance_sha256',
            'execution_contract_version','patch_export_policy','experiment_manifest','experiment_manifest_sha256'})
        self.assertEqual(digest(self.config), c.READINESS_SPEC_SHA)
        self.assertEqual(self.config['conditions'], ['REPOSITORY_ONLY','FULL_HISTORY','SUMMARY_2K',
                         'STRUCTURED_NOTES_2K','KEISHO_2K'])
        self.assertFalse(self.config['live_execution_authorized'])

    def test_prompt_append_and_action_annotation_contracts_unchanged(self):
        old, old_policy, old_format = c.response_settings(self.prior)
        new, policy, output_format = c.response_settings(self.config)
        self.assertEqual(new, old + ANNOTATION_GUIDANCE)
        self.assertEqual((policy, output_format), (AUXILIARY, None))
        self.assertEqual((policy, output_format), (old_policy, old_format))
        self.assertEqual(c.action_wire_options(self.config), c.action_wire_options(self.prior))
        self.assertTrue(c.observable_audit_enabled(self.config))
        for field in ('action_contract_sha256','internal_action_contract_sha256','response_policy',
                      'notes_adapter_version','agent_output_format_sha256'):
            self.assertEqual(self.config[field], self.prior[field])

    def test_pending_binding_never_calls_preflight_or_claims_guard(self):
        with tempfile.TemporaryDirectory() as t:
            args = dict(config_path=c.ROOT/'configs/swebench-comparison-v1.4.json',
                plan_path=c.ROOT/'analysis/swebench-comparison-v1.4-plan.json',
                authorization_path=c.ROOT/'analysis/swebench-comparison-v1.4-authorization-template.json',
                run_dir=Path(t).resolve()/'not-started')
            binding = c.resolve_binding(**args, allow_pending=True)
            self.assertFalse(binding.authorization['provider_inference_authorized'])
            self.assertFalse(binding.authorization_guard.exists())
            with patch.object(c, 'runtime_preflight', side_effect=AssertionError('preflight must not run')):
                with self.assertRaisesRegex(ValidationError, 'not authorized'):
                    c.execute(approve_live=True, **args)
            self.assertFalse(args['run_dir'].exists())
            self.assertFalse(binding.authorization_guard.exists())

    def test_real_component_manifest_verifies_before_admission(self):
        manifest = validate_freeze(self.config, c.ROOT)
        self.assertGreaterEqual(len(manifest['files']), 80)
        for path in ('src/keisho/handoff/compact.py','src/keisho/handoff/session.py',
                     'src/keisho/benchmark/vendor/prompts.json','src/keisho/benchmark/protocol.py',
                     'src/keisho/pilot/response_policy.py','src/keisho/benchmark/patch_export.py'):
            self.assertIn(path, manifest['files'])
        _, _, plan = c.load_frozen_plan(c.ROOT/'configs/swebench-comparison-v1.4.json',
                                      c.ROOT/'analysis/swebench-comparison-v1.4-plan.json')
        self.assertEqual(plan['first_request_upper_bound'], 4782)
        self.assertEqual(plan['branch_order'], ['FULL_HISTORY','SUMMARY_2K','REPOSITORY_ONLY',
                                              'KEISHO_2K','STRUCTURED_NOTES_2K'])

    def test_component_changes_missing_paths_symlinks_and_manifest_changes_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve(); component = root/'component.py'; component.write_text('original\n')
            manifest = {'version':'swebench-experiment-freeze/1.4',
                        'files':{'component.py':hashlib.sha256(component.read_bytes()).hexdigest()}}
            path = root/'manifest.json'; path.write_text(json.dumps(manifest))
            config = {'experiment_manifest':'manifest.json','experiment_manifest_sha256':digest(manifest)}
            self.assertEqual(validate_freeze(config, root), manifest)
            component.write_text('mutated\n')
            with self.assertRaisesRegex(ValidationError, 'component changed'): validate_freeze(config, root)
            component.unlink()
            with self.assertRaisesRegex(ValidationError, 'missing frozen component'): validate_freeze(config, root)
            component.symlink_to(path)
            with self.assertRaisesRegex(ValidationError, 'unsafe or missing'): validate_freeze(config, root)
            path.write_text(json.dumps({**manifest,'extra':'mutation'}))
            with self.assertRaisesRegex(ValidationError, 'manifest pin changed'): validate_freeze(config, root)
            with self.assertRaisesRegex(ValidationError, 'unsafe experiment manifest path'):
                validate_freeze({**config,'experiment_manifest':'../manifest.json'}, root)

    def test_changed_budget_or_rehashed_plan_is_unregistered(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            config = {**self.config, 'checkpoint':'choose after passing official evaluation'}
            plan = c.read_input(c.ROOT/'analysis/swebench-comparison-v1.4-plan.json')
            plan['config_sha256'] = digest(config)
            (root/'config.json').write_text(json.dumps(config)); (root/'plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValidationError, 'frozen supported specification'):
                c.load_frozen_plan(root/'config.json', root/'plan.json')

    def test_every_role_uses_same_guidance_and_wire_with_json_object_mode(self):
        for role, condition in [('predecessor','predecessor')] + [('successor', x) for x in self.config['conditions']]:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as t:
                raw = RawRun(Path(t).resolve(), 'unit-response')
                sent = []; identity = self.config[role+'_model']
                def transport(body, key):
                    sent.append(body)
                    response = native_response(identity, {'action':{'tool':'finish','args':{'answer':'offline unit'}},
                        'claims':[{'statement':'An unsupported possibility','status':'UNCERTAIN',
                                   'evidence_ids':[],'basis':'independent'}]})
                    return response, 'SYNTHETIC-NO-NETWORK'
                model = OpenRouterChatModel(identity,authorized=True,api_key='offline-fixture',tokenizer=Counter(),
                    transport=transport,response_model_ids=(MODEL_ALIASES[identity],identity))
                system, policy, _ = c.response_settings(self.config)
                execution = run_agent(model,OfflineSession(),Recorder(raw),'offline unit objective',system,'',
                    1,Budgets(1,1,2048,20000,32000,128000),role=role,response_policy=policy,
                    **c.action_wire_options(self.config))
                self.assertEqual((execution.reason,execution.model_calls,execution.tool_calls),('finished',1,0))
                self.assertEqual(sent[0]['response_format'], {'type':'json_object'})
                self.assertEqual(sent[0]['messages'][0]['content'], system)
                annotation = json.loads((raw.path/f'{role}_call_001-annotations.json').read_text())
                self.assertEqual(annotation['coverage'], {'supplied':1,'validated':1,'rejected':0})
                self.assertFalse(annotation['semantic_truth_verified'])


if __name__ == '__main__': unittest.main()
