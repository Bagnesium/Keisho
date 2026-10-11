import json
from pathlib import Path
import tempfile
import unittest

from keisho.core import ValidationError
from keisho.logging.raw import EventKind, RawRun
from tests.fixtures import event


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = RawRun(Path(self.temp.name), "run-01")

    def test_exclusive_artifacts_and_unique_runs(self):
        self.run.write_artifact("manifest.json", {"seed": 42})
        with self.assertRaises(FileExistsError):
            self.run.write_artifact("manifest.json", {"seed": 7})
        with self.assertRaises(FileExistsError):
            RawRun(Path(self.temp.name), "run-01")
        for name in ("../escape.json", "trajectory.json"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.run.write_artifact(name, {})

    def test_hash_chain_freeze_and_round_trip(self):
        self.run.append(event("one", EventKind.USER_MESSAGE))
        self.run.append(event("two", parents=("one",)))
        first = (self.run.path / "events/00000000.json").read_bytes()
        frozen = self.run.freeze()
        self.assertEqual(self.run.load_frozen(), frozen)
        reopened = RawRun.open_existing(Path(self.temp.name), "run-01")
        self.assertEqual(reopened.load_frozen(), frozen)
        with self.assertRaises(ValidationError):
            reopened.write_artifact("new.json", {})
        self.assertEqual((self.run.path / "events/00000000.json").read_bytes(), first)
        with self.assertRaises(ValidationError):
            self.run.append(event("three"))
        with self.assertRaises(FileExistsError):
            self.run.freeze()

    def test_tampering_detected_even_if_owner_changes_permissions(self):
        self.run.append(event("one"))
        self.run.freeze()
        path = self.run.path / "events/00000000.json"
        path.chmod(0o644)
        record = json.loads(path.read_text())
        record["event"]["actor"] = "tampered"
        path.write_text(json.dumps(record))
        with self.assertRaises(ValidationError):
            self.run.load_frozen()

    def test_parent_ids_duplicates_and_missing_sequence(self):
        with self.assertRaises(ValidationError):
            self.run.append(event("one", parents=("future",)))
        self.run.append(event("one"))
        with self.assertRaises(ValidationError):
            self.run.append(event("one"))
        (self.run.path / "events/00000000.json").rename(self.run.path / "events/00000001.json")
        with self.assertRaises(ValidationError):
            self.run.freeze()
