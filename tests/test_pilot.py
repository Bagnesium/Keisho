from dataclasses import replace
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from keisho.agents.base import Message, ModelRequest, TokenCount
from keisho.agents.providers.openai_chat import OpenAIChatModel, ProviderFailure
from keisho.core import ValidationError, canonical_json, digest, primitive, text_digest
from keisho.environments import Evaluation, FilesystemEnvironment
from keisho.experiments.conditions import Condition, build_capsule
from keisho.logging.raw import EventKind, FrozenTrajectory, RawRun
from keisho.pilot.agent import Recorder, parse_output, run_agent
from keisho.pilot.cli import main, pilot_manifest, verify_sandbox
from keisho.pilot.config import PilotConfig
from keisho.pilot.offline import FixtureModel, exposed, factory
from keisho.pilot.runner import branch_status, check_task, prompt, run_block, run_pilot
from keisho.pilot.scoring import qualify_checkpoint, score_behavior, validate_review
from keisho.pilot.state_builder import build_state
from keisho.pilot.tasks import REPO, TASK_IDS, load_gold, load_public
from keisho.pilot.tools import InvalidAction, ToolSession, file_hashes
from keisho.state.provenance import EpistemicStatus as Status
from keisho.state.validator import validate_state
from tests.fixtures import fixture


class Counter:
    def count(self, text):
        return TokenCount(len(text.split()), "unit-test-tokenizer", True)


class ProviderTests(unittest.TestCase):
    def request(self):
        return ModelRequest((Message("user", "Return JSON."),), 17, 100, 0.0)

    def response(self, model="gpt-4.1-mini-2025-04-14", text="{}"):
        return {"model": model, "choices": [{"message": {"content": text, "tool_calls": []}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 20}}, "system_fingerprint": "unit-test"}

    def test_paid_gate_prevents_transport(self):
        calls = []
        model = OpenAIChatModel("gpt-4.1-mini-2025-04-14", transport=lambda *args: calls.append(args), tokenizer=Counter())
        with self.assertRaises(ProviderFailure):
            model.generate(self.request())
        self.assertEqual(calls, [])

    def test_usage_exact_identity_native_metadata_and_cached_pricing(self):
        requests = []
        def transport(body, key):
            requests.append(body)
            return self.response(), "req-unit"
        model = OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="unit-test-secret", transport=transport, tokenizer=Counter())
        response = model.generate(self.request())
        self.assertEqual(response.usage.cost_usd, "0.00005")
        self.assertEqual(response.request_id, "req-unit")
        self.assertEqual(response.system_fingerprint, "unit-test")
        self.assertEqual(requests[0]["seed"], 17)
        self.assertFalse(requests[0]["store"])
        self.assertNotIn("unit-test-secret", canonical_json(response))

    def test_provider_failures_are_not_retried_and_keep_invalid_response(self):
        attempts = []
        def transport(body, key):
            attempts.append(body)
            return self.response(model="different-model"), "bad-request"
        model = OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="unit-test-secret", transport=transport)
        with self.assertRaises(ProviderFailure) as caught:
            model.generate(self.request())
        self.assertEqual(len(attempts), 1)
        self.assertIn("different-model", caught.exception.raw_response_json)

    def test_secret_echo_is_redacted(self):
        model = OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="unit-test-secret", transport=lambda *_: (self.response(text="unit-test-secret"), "unit-test-secret"))
        self.assertNotIn("unit-test-secret", canonical_json(model.generate(self.request())))

    def test_summary_is_free_form_and_unknown_prices_remain_unknown(self):
        response = self.response(text="Narrative summary.")
        response["usage"].pop("prompt_tokens_details")
        model = OpenAIChatModel("gpt-4.1-mini-2025-04-14", authorized=True, api_key="unit-test-secret", transport=lambda *_: (response, None), mode="summary")
        self.assertNotIn("response_format", model.body(self.request()))
        self.assertIsNone(model.generate(self.request()).usage.cost_usd)


class ContractTests(unittest.TestCase):
    def test_pilot_cannot_expand_and_plan_has_exact_36_branches(self):
        config = PilotConfig.load(REPO / "configs/pilot.yaml")
        manifest = pilot_manifest(config)
        self.assertEqual(manifest["successor_branches"], 36)
        self.assertEqual(manifest["model_call_upper_bounds"]["total"], 594)
        self.assertEqual(manifest["estimated_cost_upper_envelope_usd"], "11.0581632")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.yaml"
            expanded = copy.deepcopy(config.data)
            expanded["repetitions"] = 4
            path.write_text(json.dumps(expanded))
            with self.assertRaises(ValidationError):
                PilotConfig.load(path)
            expanded = copy.deepcopy(config.data)
            expanded["successor"]["budgets"]["total_tokens"] = 60001
            path.write_text(json.dumps(expanded))
            with self.assertRaises(ValidationError):
                PilotConfig.load(path)

    def test_cli_live_gate_stops_before_credentials_and_calls(self):
        self.assertEqual(main(["pilot", "--config", str(REPO / "configs/pilot.yaml")]), 2)

    def test_no_fake_evidence_ids_or_hidden_reasoning_fields(self):
        claim = {"statement": "A claim", "status": "INFERRED", "basis": "tool", "evidence_ids": ["unknown"]}
        with self.assertRaises(ValidationError):
            parse_output(canonical_json({"action": {"tool": "list_files"}, "claims": [claim]}), set())
        with self.assertRaises(ValidationError):
            parse_output('{"action":{},"claims":[],"thoughts":"private"}', set())

    def test_new_uncertain_rejection_preserves_old_validation(self):
        _, state = fixture()
        rejection = replace(state.rejected_hypotheses[0], provenance=replace(state.rejected_hypotheses[0].provenance, epistemic_status=Status.UNCERTAIN))
        with self.assertRaises(ValidationError):
            validate_state(replace(state, rejected_hypotheses=(rejection,)))
        validate_state(replace(state, version="0.1.1", rejected_hypotheses=(rejection,)))

    def test_phase0_fingerprint_has_only_two_documented_defects_changed(self):
        protected = json.loads((REPO / "protocol_amendments/phase0-freeze.json").read_text())["protected_files"]
        import hashlib
        changed = {path for path, hashed in protected.items() if hashlib.sha256((REPO / path).read_bytes()).hexdigest() != hashed}
        self.assertEqual(changed, {"src/keisho/state/schema.py", "src/keisho/state/validator.py"})


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("sandbox-exec"), "macOS sandbox required")
class IsolatedPilotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="keisho-pilot-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.sandbox = verify_sandbox(self.root)
        self.config = PilotConfig.load(REPO / "configs/pilot.yaml")

    def environment(self, task_id):
        task = load_public(task_id)
        env = FilesystemEnvironment(self.root / f"workspace-{task_id}", task.files, lambda _: Evaluation(None, "External grading", "test/1"))
        return task, env, ToolSession(task, env.workspace, self.sandbox)

    def predecessor(self, task_id="task_003"):
        task, env, tools = self.environment(task_id)
        recorder = Recorder(RawRun(self.root / "raw", "pred-test"))
        execution = run_agent(factory("predecessor", task_id, None), tools, recorder, task.description, prompt("agent"), "", 17, self.config.budgets("predecessor"), "predecessor", 9)
        snapshot = env.snapshot()
        recorder.emit("snapshot", EventKind.FILE_SNAPSHOT, "predecessor", {"environment_sha256": snapshot.sha256})
        trajectory = recorder.raw.freeze()
        return task, env, tools, trajectory, execution

    def test_all_initial_failures_and_known_fixes_are_deterministic(self):
        for task_id in TASK_IDS:
            task, env, tools = self.environment(task_id)
            gold = load_gold(task_id)
            initial = env.reset(17)
            result = tools.execute({"tool": "run_tests", "test_ids": ["full"]})
            self.assertEqual({record["id"] for record in result["results"] if not record["passed"]}, set(gold["success"]["initial_failing_tests"]))
            self.assertEqual(env.reset(43), initial)
            for path, content in gold["correct_fix"].items():
                tools.execute({"tool": "write_file", "path": path, "content": content})
            self.assertTrue(check_task(task, gold, env.workspace, self.sandbox)[0])

    def test_tools_deny_gold_absolute_paths_protected_tests_and_shell(self):
        _, _, tools = self.environment("task_001")
        for action in ({"tool": "read_file", "path": "../gold.json"}, {"tool": "read_file", "path": str(REPO / "tasks/task_001/gold.json")}, {"tool": "write_file", "path": "tests.json", "content": "[]"}, {"tool": "shell", "command": "cat gold.json"}):
            with self.subTest(action=action), self.assertRaises(InvalidAction):
                tools.execute(action)
        for action in ({"tool": []}, {"tool": "read_file", "path": {}}, {"tool": "run_tests", "test_ids": [{}]}):
            with self.subTest(action=action), self.assertRaises(InvalidAction):
                tools.execute(action)

    def test_task_code_cannot_read_gold_or_sibling_content_or_write_workspace(self):
        task, env, tools = self.environment("task_003")
        secret = self.root / "host-secret.txt"
        secret.write_text("gold sentinel")
        source = f'def cache_identity():\n    return open({str(secret)!r}).read()\n'
        tools.execute({"tool": "write_file", "path": "keys.py", "content": source})
        result = tools.execute({"tool": "run_tests", "test_ids": ["cache_identity"]})
        self.assertEqual(result["results"][0]["exception"], "PermissionError")
        self.assertFalse(result["results"][0]["passed"])
        for operation in ('open("keys.py", "w").write("changed")', '__import__("os").fork()', '__import__("socket").socket().connect(("127.0.0.1", 9))'):
            source = f'def cache_identity():\n    {operation}\n    return True\n'
            tools.execute({"tool": "write_file", "path": "keys.py", "content": source})
            result = tools.execute({"tool": "run_tests", "test_ids": ["cache_identity"]})
            self.assertEqual(result["results"][0]["exception"], "PermissionError")
            self.assertEqual((env.workspace / "keys.py").read_text(), source)

    def test_early_worker_exit_timeout_and_output_limit_are_reaped(self):
        _, env, _ = self.environment("task_001")
        for worker, failure in (('import os; os._exit(7)', "worker_exit"),
                                ('import time; time.sleep(30)', "timeout"),
                                ('print("x" * 70000)', "output_limit")):
            with self.subTest(failure=failure), patch("keisho.pilot.sandbox.WORKER", worker):
                self.sandbox.timeout = 0.15
                result = self.sandbox._execute(env.workspace, {"cases": []})
                self.assertEqual(result["execution_failure"], failure)

    def test_state_builder_never_promotes_model_certainty_and_keeps_rejections(self):
        task, env, _, predecessor, _ = self.predecessor()
        state = build_state(predecessor, task.description)
        validate_state(state)
        self.assertTrue(state.verified_facts)
        self.assertTrue(state.failed_attempts)
        self.assertTrue(state.rejected_hypotheses)
        self.assertEqual(state.rejected_hypotheses[0].provenance.epistemic_status, Status.UNCERTAIN)
        self.assertTrue(all(fact.statement.startswith("Public test") for fact in state.verified_facts))

    def test_checkpoint_rejects_solved_and_uninformative_traces(self):
        task, env, _, predecessor, execution = self.predecessor()
        hashes = file_hashes(env.workspace, task.editable_files)
        gold = load_gold(task.id)
        self.assertTrue(qualify_checkpoint(gold, predecessor, hashes, execution.reason, execution.tool_calls, False)["valid"])
        self.assertFalse(qualify_checkpoint(gold, predecessor, hashes, execution.reason, execution.tool_calls, True)["valid"])
        self.assertFalse(qualify_checkpoint(gold, FrozenTrajectory.create(()), hashes, "checkpoint", 9, False)["valid"])

    def test_new_contradictory_evidence_and_scope_changes_exclude_error(self):
        task, env, tools, predecessor, _ = self.predecessor()
        gold = load_gold(task.id)
        checkpoint = file_hashes(env.workspace, task.editable_files)
        raw = Recorder(RawRun(self.root / "raw", "new-evidence"))
        content = task.files["keys.py"].replace('return get_key("demo") == KEYS["demo"]', 'return False')
        tools.execute({"tool": "write_file", "path": "keys.py", "content": content})
        result = tools.execute({"tool": "run_tests", "test_ids": ["cache_identity"]})
        raw.emit("fresh", EventKind.TOOL_RESULT, "successor", result)
        false = gold["hypotheses"][0]["statement"]
        raw.emit("claim", EventKind.MODEL_RESPONSE, "successor", {"text": exposed({"tool": "finish", "answer": "fixture"}, false, "VERIFIED", "tool", ("fresh",))})
        capsule = build_capsule(Condition.FULL_HISTORY, predecessor, build_state(predecessor, task.description), "fixture", FixtureModel("offline/counter", ()), 24000)
        review = score_behavior(task.id, "new-evidence", gold, predecessor, raw.trajectory(), capsule, checkpoint)
        self.assertEqual(review["counts"]["contradiction_count"], 0)
        self.assertEqual(review["counts"]["inherited_error_candidate_count"], 0)

    def test_new_evidence_exclusion_is_separate_from_changed_scope(self):
        task, env, _, predecessor, _ = self.predecessor()
        gold = load_gold(task.id)
        hashes = file_hashes(env.workspace, task.editable_files)
        raw = Recorder(RawRun(self.root / "raw", "same-scope-new-evidence"))
        # Deliberately adversarial synthetic observation: unchanged source scope,
        # a fresh contrary value, and an explicit evidence citation.
        raw.emit("fresh", EventKind.TOOL_RESULT, "successor", {
            "action": {"tool": "run_tests", "test_ids": ["cache_identity"]},
            "source_hashes_before": hashes, "source_hashes_after": hashes,
            "results": [{"id": "cache_identity", "passed": False, "value": False}]})
        false = gold["hypotheses"][0]["statement"]
        raw.emit("claim", EventKind.MODEL_RESPONSE, "successor", {"text": exposed({"tool": "finish", "answer": "fixture"}, false, "VERIFIED", "predecessor", ("fresh",))})
        capsule = build_capsule(Condition.FULL_HISTORY, predecessor, build_state(predecessor, task.description), "fixture", FixtureModel("offline/counter", ()), 24000)
        review = score_behavior(task.id, "same-scope-new-evidence", gold, predecessor, raw.trajectory(), capsule, hashes)
        self.assertEqual(review["counts"]["contradiction_count"], 0)
        self.assertEqual(review["counts"]["inherited_error_candidate_count"], 0)

    def test_identical_error_with_independent_basis_is_not_inheritance(self):
        task, env, _, predecessor, _ = self.predecessor()
        gold = load_gold(task.id)
        hashes = file_hashes(env.workspace, task.editable_files)
        raw = Recorder(RawRun(self.root / "raw", "independent-error"))
        raw.emit("claim", EventKind.MODEL_RESPONSE, "successor", {"text": exposed({"tool": "finish", "answer": "fixture"}, gold["hypotheses"][0]["statement"], "VERIFIED", "independent")})
        capsule = build_capsule(Condition.FULL_HISTORY, predecessor, build_state(predecessor, task.description), "fixture", FixtureModel("offline/counter", ()), 24000)
        review = score_behavior(task.id, "independent-error", gold, predecessor, raw.trajectory(), capsule, hashes)
        self.assertEqual(review["counts"]["contradiction_count"], 1)
        self.assertEqual(review["counts"]["inherited_error_candidate_count"], 0)

    def test_all_four_conditions_record_expected_events_and_review_reconstructs_totals(self):
        block = run_block(self.config, "task_003", 17, self.root / "raw", self.root / "work", self.sandbox, factory, synthetic=True)
        self.assertEqual(block["status"], "complete")
        self.assertEqual({row["condition"] for row in block["branches"]}, {condition.value for condition in Condition})
        self.assertEqual(len({row["checkpoint_id"] for row in block["branches"]}), 1)
        for row in block["branches"]:
            self.assertTrue(row["task_success"])
            self.assertEqual(row["rediscovery_count"], 1)
            self.assertEqual(row["repeated_failure_count"], 1)
            self.assertEqual(row["contradiction_count"], 1)
            self.assertEqual(row["inherited_error_candidate_count"], 0 if row["condition"] == "NO_CONTEXT" else 1)
            raw = RawRun.open_existing(self.root / "raw", row["run_id"])
            review = json.loads((raw.path / "annotation-review.json").read_text())
            manifest = json.loads((raw.path / "manifest.json").read_text())
            pred = RawRun.open_existing(self.root / "raw", manifest["parent_run_id"]).load_frozen()
            validate_review(review, pred, raw.load_frozen(), load_gold("task_003"))
            for key, value in review["counts"].items():
                self.assertEqual(value, row[key])
            if review["counted_events"]:
                tampered = copy.deepcopy(review)
                tampered["counted_events"].append(tampered["counted_events"][0])
                with self.assertRaises(ValidationError):
                    validate_review(tampered, pred, raw.load_frozen(), load_gold("task_003"))

    def test_full_36_branch_offline_lifecycle_and_gold_not_in_summary_prompts(self):
        result = run_pilot(self.config, self.root / "raw", self.root / "work", self.sandbox, factory, synthetic=True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(sum(len(block["branches"]) for block in result["blocks"]), 36)
        for block in result["blocks"]:
            for branch in block["branches"]:
                self.assertEqual(branch["status"], "SUCCESS")
                self.assertEqual(branch["artifact_validation"], "passed")
        for path in (self.root / "raw").glob("*-summary-generator/*-request.json"):
            text = path.read_text()
            for forbidden in ("correct_fix", "hidden_cases", "rediscovery_targets", "initial_failing_tests"):
                self.assertNotIn(forbidden, text)

    def test_model_failure_logged_once_and_remains_separate(self):
        task, _, tools = self.environment("task_001")
        recorder = Recorder(RawRun(self.root / "raw", "failure"))
        failing = FixtureModel("offline/failure", ())
        execution = run_agent(failing, tools, recorder, task.description, prompt("agent"), "", 17, self.config.budgets("successor"))
        self.assertEqual(execution.reason, "model_failure")
        self.assertEqual(execution.model_calls, 1)
        self.assertIsNone(branch_status(execution.reason, False).task_success)
        recorder.raw.freeze()
        self.assertTrue((recorder.raw.path / "successor_call_001-failure.json").exists())

    def test_malformed_responses_keep_four_immutable_model_failure_rows(self):
        def malformed_factory(role, task_id, condition):
            model = factory(role, task_id, condition)
            return FixtureModel(model.model_id(), ("[]",)) if role == "successor" else model
        block = run_block(self.config, "task_003", 17, self.root / "raw", self.root / "work", self.sandbox, malformed_factory, synthetic=True)
        self.assertEqual(len(block["branches"]), 4)
        for row in block["branches"]:
            self.assertEqual(row["status"], "MODEL_FAILURE")
            self.assertIsNone(row["task_success"])
            self.assertEqual(row["post_handoff_model_calls"], 1)
            self.assertTrue((self.root / "raw" / row["run_id"] / "result.json").exists())

    def test_artifact_validation_failure_retains_invalid_branch_and_halts(self):
        with patch("keisho.pilot.runner.validate_artifacts", side_effect=ValidationError("injected invariant mismatch")):
            result = run_pilot(self.config, self.root / "raw", self.root / "work", self.sandbox, factory, synthetic=True)
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "invalid_run")
        branches = list((self.root / "raw").glob("*/manifest.json"))
        self.assertEqual(len(branches), 1)
        row = json.loads((branches[0].parent / "result.json").read_text())
        self.assertEqual(row["status"], "INVALID_RUN")
        self.assertIsNone(row["task_success"])
        self.assertIsNone(row["contradiction_count"])


if __name__ == "__main__":
    unittest.main()
