from dataclasses import replace
import unittest

from keisho.core import ValidationError, canonical_json, decode, primitive
from keisho.experiments.conditions import Condition
from keisho.experiments.manifest import ModelSpec, PromptRef, RunManifest, RunOutcome, RunStatus, Runtime, validate_block
from tests.fixtures import STAMP


def manifest(condition=Condition.NO_CONTEXT):
    hashed = "a" * 64
    model = ModelSpec("offline", "offline/scripted-whitespace-v1", canonical_json({"temperature": 0, "max_output_tokens": 100}), True)
    return RunManifest(
        version="0.1.0", run_id=f"test-{condition.value}", block_id="block-01", parent_run_id="predecessor-01",
        task_id="fixture", task_version="0.0-test", task_sha256=hashed, original_task_sha256=hashed,
        predecessor=model, successor=model, condition=condition, seed=42, checkpoint_steps=4,
        handoff_token_budget=10000, successor_step_budget=20, created_at=STAMP,
        protocol_version="0.1.0", state_version="0.1.0", prompts=(PromptRef("successor", "0.1.0", hashed),),
        trajectory_sha256=hashed, environment_sha256=hashed, state_sha256=hashed, capsule_sha256=hashed, config_sha256=hashed,
        runtime=Runtime("3.14.2", "test-platform", None, hashed, hashed, "filesystem/0.1.0"),
    )


class ManifestTests(unittest.TestCase):
    def test_round_trip_and_block_invariants(self):
        manifests = tuple(manifest(condition) for condition in Condition)
        validate_block(manifests)
        self.assertEqual(decode(RunManifest, primitive(manifests[0])), manifests[0])
        for field, value in (("seed", 7), ("environment_sha256", "b" * 64), ("successor_step_budget", 10)):
            changed = replace(manifests[0], **{field: value})
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_block((changed,) + manifests[1:])

    def test_missing_duplicate_conditions_and_duplicate_run_ids(self):
        manifests = tuple(manifest(condition) for condition in Condition)
        for block in (manifests[:3], (manifests[0],) + manifests[:3], (replace(manifests[0], run_id=manifests[1].run_id),) + manifests[1:]):
            with self.subTest(block=block), self.assertRaises(ValidationError):
                validate_block(block)

    def test_failure_categories_do_not_become_task_failures(self):
        for status in RunStatus:
            success = {RunStatus.COMPLETE: True, RunStatus.TASK_FAILURE: False}.get(status)
            RunOutcome(status, success, "Detailed outcome", "grader/1").validate()
        for outcome in (RunOutcome(RunStatus.INFRASTRUCTURE_FAILURE, False, "Test executable missing", "grader/1"), RunOutcome(RunStatus.COMPLETE, None, "No grader result", "grader/1")):
            with self.subTest(outcome=outcome), self.assertRaises(ValidationError):
                outcome.validate()
