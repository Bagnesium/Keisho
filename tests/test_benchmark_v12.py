"""New frozen specification admission; no real provider requests."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keisho.benchmark import comparison as c
from keisho.core import ValidationError, digest


class Version12Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.config = self.root/'config.json'
        self.plan = self.root/'plan.json'
        self.auth = self.root/'authorization.json'
        for target, source in ((self.config,'configs/swebench-comparison-v1.2.json'),
                               (self.plan,'analysis/swebench-comparison-v1.2-plan.json'),
                               (self.auth,'analysis/swebench-comparison-v1.2-authorization-template.json')):
            target.write_bytes((c.ROOT/source).read_bytes())
        self.output = self.root/'output'

    def tearDown(self): self.tmp.cleanup()

    def binding(self, pending=True):
        return c.resolve_binding(self.config,self.plan,self.output,self.auth,allow_pending=pending)

    def test_pending_is_dry_only_and_new_contract_explicit(self):
        binding = self.binding()
        system, policy, schema = c.response_settings(binding.config)
        self.assertIn('benchmark-agent/3.0',system)
        self.assertIn('next_cursor',system)
        self.assertEqual(policy,'auxiliary-claims/2.0')
        self.assertIsNone(schema)  # Adapter JSON-object mode; strict local actions remain.
        with patch.object(c,'runtime_preflight',side_effect=AssertionError('must reject before environment/provider')):
            with self.assertRaisesRegex(ValidationError,'not authorized'):
                c.execute(approve_live=True,config_path=self.config,plan_path=self.plan,
                          run_dir=self.output,authorization_path=self.auth)
        self.assertFalse(binding.authorization_guard.exists())
        self.assertFalse(self.output.exists())

    def test_scientific_or_plan_mutation_is_not_fixed_by_rehashing(self):
        original = self.config.read_bytes()
        data = json.loads(original)
        data['predecessor_budgets']['total_tokens'] += 1
        self.config.write_text(json.dumps(data))
        plan = json.loads(self.plan.read_text()); plan['config_sha256'] = digest(data)
        self.plan.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValidationError,'frozen supported specification'): self.binding()
        self.config.write_bytes(original)
        with self.assertRaisesRegex(ValidationError,'matched frozen plan'): self.binding()

    def test_authorization_scope_not_metadata_or_output_name_owns_guard(self):
        first = self.binding()
        authorization = json.loads(self.auth.read_text())
        authorization['created_at'] = 'different execution metadata'
        self.auth.write_text(json.dumps(authorization))
        second = self.binding()
        self.assertEqual(first.authorization_guard,second.authorization_guard)
        self.assertNotEqual(digest(first.authorization),digest(second.authorization))
        # Own test guard, never a pending or historical production scope.
        first = replace(first,authorization_guard=self.root/'owned-synthetic-claim')
        second = replace(second,authorization_guard=first.authorization_guard,run_dir=self.root/'other-output')
        def claim(binding):
            try: return c.claim_launch(binding)
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            admitted = list(pool.map(claim,(first,second)))
        self.assertEqual(sum(item is not None for item in admitted),1)
        with self.assertRaises(FileExistsError):
            c.claim_launch(replace(first,run_dir=self.root/'third-output'))
        self.assertFalse((self.root/'third-output').exists())

    def test_old_defaults_and_hashes_remain_distinct(self):
        self.assertNotEqual(c.SPEC_SHA,c.NEXT_SPEC_SHA)
        self.assertNotEqual(c.PLAN_SHA,c.NEXT_PLAN_SHA)
        old = json.loads((c.ROOT/'configs/swebench-comparison-v1.1.json').read_text())
        self.assertIsNotNone(c.response_settings(old)[2])
        new = self.binding().config
        for key in ('selected_instance','conditions','branch_seed','predecessor_model','successor_model',
                    'generation_model','predecessor_budgets','successor_budgets','checkpoint',
                    'handoff_token_budget','harness_commit','dataset_revision','notes_adapter_version'):
            self.assertEqual(old[key],new[key],key)

if __name__ == '__main__': unittest.main()
