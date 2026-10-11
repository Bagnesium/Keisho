from pathlib import Path
import tempfile
import unittest

from scripts.check_scaffold import run_check
from keisho.experiments.conditions import Condition


class PipelineTests(unittest.TestCase):
    def test_complete_offline_artifact_pipeline(self):
        with tempfile.TemporaryDirectory(prefix="keisho-test-") as root:
            manifests = run_check(Path(root))
            self.assertEqual({manifest.condition for manifest in manifests}, set(Condition))
            for manifest in manifests:
                self.assertTrue((Path(root) / "raw" / manifest.run_id / "metrics.json").exists())


if __name__ == "__main__":
    unittest.main()
