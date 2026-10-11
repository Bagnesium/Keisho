from dataclasses import replace
import base64
import os
from pathlib import Path
import tempfile
import unittest

from keisho.core import ValidationError
from keisho.environments import Evaluation, FilesystemEnvironment, Snapshot
from keisho.environments.base import SnapshotFile
from keisho.experiments.branching import prepare_branches
from keisho.experiments.conditions import Condition, HandoffBudgetExceeded, build_capsule
from keisho.agents.base import TokenCount
from keisho.agents.scripted import ScriptedModel
from tests.fixtures import fixture


def grader(workspace):
    return Evaluation((workspace / "src/main.py").read_text() == "fixed\n", "Exact fixture result", "test-grader/1")


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = FilesystemEnvironment(self.root / "predecessor", {"src/main.py": "broken\n", "config.txt": "X\n"}, grader)
        self.trajectory, self.state = fixture()
        self.model = ScriptedModel()

    def test_reset_is_deterministic_and_evaluation_observes_changes(self):
        first = self.env.reset(42)
        self.assertFalse(self.env.evaluate().success)
        (self.env.workspace / "src/main.py").write_text("fixed\n")
        self.assertTrue(self.env.evaluate().success)
        self.assertEqual(self.env.reset(42), first)
        self.assertEqual(self.env.reset(99), first)

    def test_restore_preserves_checkpoint_changes_empty_dirs_and_modes(self):
        (self.env.workspace / "src/main.py").write_text("partly fixed\n")
        (self.env.workspace / "empty").mkdir()
        (self.env.workspace / "config.txt").chmod(0o600)
        snapshot = self.env.snapshot()
        (self.env.workspace / "leftover.txt").write_text("pollution")
        self.env.reset(0)
        self.env.restore(snapshot)
        self.assertEqual(self.env.snapshot(), snapshot)
        self.assertFalse((self.env.workspace / "leftover.txt").exists())

    def test_invalid_restore_does_not_destroy_environment(self):
        snapshot = self.env.snapshot()
        with self.assertRaises(ValidationError):
            self.env.restore(replace(snapshot, sha256="0" * 64))
        self.assertEqual(self.env.snapshot(), snapshot)
        for path in ("../escape", "/absolute", "a/../escape", "a\\escape", "a//b"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                Snapshot.create((SnapshotFile(path, base64.b64encode(b"x").decode(), 0o644),), ())

    def test_snapshot_rejects_symlinks_and_hard_links(self):
        link = self.env.workspace / "link"
        link.symlink_to(self.env.workspace / "config.txt")
        with self.assertRaises(ValidationError):
            self.env.snapshot()
        link.unlink()
        os.link(self.env.workspace / "config.txt", link)
        with self.assertRaises(ValidationError):
            self.env.snapshot()

    def test_four_conditions_and_branch_filesystem_isolation(self):
        # Preserve a predecessor modification rather than restoring the initial task.
        (self.env.workspace / "src/main.py").write_text("handoff checkpoint\n")
        snapshot = self.env.snapshot()
        branches = prepare_branches(self.env, snapshot, self.trajectory, self.state, "Normal supplied summary.", self.model, 10000, self.root / "branches")
        self.assertEqual({branch.condition for branch in branches}, set(Condition))
        for branch in branches:
            self.assertEqual(branch.environment.snapshot(), snapshot)
            self.assertEqual(branch.capsule.condition, branch.condition)
        (branches[0].environment.workspace / "src/main.py").write_text("fixed\n")
        self.assertEqual(self.env.snapshot(), snapshot)
        for branch in branches[1:]:
            self.assertEqual(branch.environment.snapshot(), snapshot)
        with self.assertRaises(FileExistsError):
            prepare_branches(self.env, snapshot, self.trajectory, self.state, "summary", self.model, 10000, self.root / "branches")

    def test_condition_content_and_no_silent_truncation(self):
        capsules = {condition: build_capsule(condition, self.trajectory, self.state, "supplied summary", self.model, 10000) for condition in Condition}
        self.assertEqual(capsules[Condition.NO_CONTEXT].text, "")
        self.assertEqual(capsules[Condition.NO_CONTEXT].tokens.count, 0)
        self.assertEqual(capsules[Condition.SUMMARY].text, "supplied summary")
        self.assertIn("I suspect the database", capsules[Condition.FULL_HISTORY].text)
        self.assertIn('"epistemic_status":"INFERRED"', capsules[Condition.FIXED_STATE].text)
        with self.assertRaises(HandoffBudgetExceeded):
            build_capsule(Condition.FULL_HISTORY, self.trajectory, self.state, "summary", self.model, 1)
        class EstimatedModel(ScriptedModel):
            def count_tokens(self, text):
                return TokenCount(1, "byte estimate", False)
        with self.assertRaises(ValidationError):
            build_capsule(Condition.FIXED_STATE, self.trajectory, self.state, "summary", EstimatedModel(), 10000)

    def test_branch_preparation_rejects_wrong_checkpoint(self):
        snapshot = self.env.snapshot()
        (self.env.workspace / "config.txt").write_text("changed\n")
        with self.assertRaises(ValidationError):
            prepare_branches(self.env, snapshot, self.trajectory, self.state, "summary", self.model, 10000, self.root / "branches")
        self.assertFalse((self.root / "branches").exists())
