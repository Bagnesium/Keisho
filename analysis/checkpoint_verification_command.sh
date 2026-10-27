#!/bin/bash
# Checkpoint Verification Command for pydata__xarray-6721 Unpatched Base State
# Run on 2026-10-27
# Verified Docker image: swebench/sweb.eval.x86_64.pydata_1776_xarray-6721@sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898

docker run --rm -i --platform linux/amd64 swebench/sweb.eval.x86_64.pydata_1776_xarray-6721@sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898 /bin/bash << 'EOF'
set -uxo pipefail
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
cd /testbed
git status
git show --oneline -s
git -c core.fileMode=false diff cc183652bf6e1273e985e1c4b3cba79c896c1193
python -m pip install -e .
git checkout cc183652bf6e1273e985e1c4b3cba79c896c1193 xarray/tests/test_dataset.py
git apply -v - <<'EOF_TEST_PATCH'
diff --git a/xarray/tests/test_dataset.py b/xarray/tests/test_dataset.py
--- a/xarray/tests/test_dataset.py
+++ b/xarray/tests/test_dataset.py
@@ -992,6 +992,13 @@ def test_attrs(self) -> None:
         assert data.attrs["foobar"], "baz"
         assert isinstance(data.attrs, dict)
 
+    def test_chunks_does_not_load_data(self) -> None:
+        # regression test for GH6538
+        store = InaccessibleVariableDataStore()
+        create_test_data().dump_to_store(store)
+        ds = open_dataset(store)
+        assert ds.chunks == {}
+
     @requires_dask
     def test_chunk(self) -> None:
         data = create_test_data()

EOF_TEST_PATCH
echo ">>>>> Start Test Output"
pytest -rA xarray/tests/test_dataset.py || true
echo ">>>>> End Test Output"
EOF
