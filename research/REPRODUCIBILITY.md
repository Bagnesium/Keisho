# Reproducibility guide: v1.2 engineering integration

> **Scope:** This guide documents the earlier v1.2 offline/engineering
> integration and its local evaluator setup. It is not the procedure or archive
> for the later v2.7 empirical comparison. The v2.7 result and its limits are
> in the [current manuscript](../paper/MANUSCRIPT_FINAL_PILOT.md); the raw run
> archive is local and is not part of this public clone. Commands below that
> refer to v1.2 remain historical and do not authorize new provider calls.

Scope: implemented offline engineering and the prospective one-task integration.
No provider inference is authorized by this guide. Historical configurations,
results, guard directories and ledgers must not be edited or reused.

## Environment and pins

The recorded project location was machine-specific and is omitted; run the
commands from the repository root.
Current engineering host: macOS 26.6.2 ARM64, Python 3.14.2; dedicated evaluator
venv `.cache/swebench-evaluator/venv`, also Python 3.14.2. Docker Desktop daemon
29.6.2 aarch64 runs the already prepared **linux/amd64** task image under emulation.
One worker is used. The task container has Python 3.10.15; dependency/image identity
is recorded in `.cache/swebench-evaluator/prepared-task-image.json`.

| Input | Frozen value |
| --- | --- |
| Dataset | `princeton-nlp/SWE-bench_Verified`, revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a` |
| Harness | commit `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`, version 5.0.2 |
| Task recipes | `3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d` |
| Handoff Debt code | MIT commit `5179b1d759be466600c453da8b9078341967ec17` |
| Exploratory task/base | `pydata__xarray-6721` / `cc183652bf6e1273e985e1c4b3cba79c896c1193` |
| Setup-only task | `sympy__sympy-20590`, excluded from live comparison |
| Prepared agent image | `sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898` |
| Tokenizer/local schema validator | `tiktoken==0.12.0`, `jsonschema==4.26.0` |

Use the existing dedicated environment; do not alter global packages. The sprint
installed the already pinned schema validator into that venv after reproducing its
missing dependency, then reproduced the exact callback failure. Exact installation
output is in `runs/swebench-integration/commands/sprint-p0-venv-existing-dependency/`.
The project declares these dependencies in its optional `benchmark` extra for a
future clean dedicated installation. Preserve the installed official harness/source
pins when creating another environment. Do not rebuild/pull the whole image collection.

Check `docker info` and the image ID before Docker tests. If Docker is stopped,
start the existing installation with `open -a Docker`, then verify readiness.
Unsupported architecture/image or isolation is a blocker, never permission to run
uncontained. Containers receive no host mounts, credentials/socket or network.
Private evaluator rows/test patches/gold keys stay controller-side under `.cache`.

## Offline commands

From the project root, the supported broad suite is:

```sh
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

Focused public launch/interface/benchmark checks:

```sh
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest tests.test_functional_public tests.test_benchmark_real_offline tests.test_benchmark_v12 tests.test_bounded_listing tests.test_agent_wire_contract tests.test_response_measurements tests.test_response_policy tests.test_benchmark_launcher tests.test_benchmark -v
```

These tests launch the **actual public scripts in fresh subprocesses**. Test-only
`tests/offline_launch/sitecustomize.py` replaces transport at script `main()` using
explicit test PYTHONPATH/settings. It is never installed into production; there is
no production `--offline-provider` flag or disabled safety gate. It blocks provider
network I/O and labels service responses/charges synthetic. Runtime actions execute
through real parser, RepositorySession/Docker, recorder, budget and callback code.
Both host Python and the evaluator interpreter exercise the formerly failing path.
The final five-way regression stubs only grading; its workspace/tools are real Docker.

For new durable artifacts, choose **new, unoccupied** output names:

```sh
python3 tests/run_offline_functional.py --output results/offline-functional-NEW
python3 tests/run_offline_benchmark.py --output runs/offline-five-way-NEW
```

Optional evaluator-only checkpoint integration (no inference):

```sh
python3 tests/run_offline_benchmark.py --output runs/offline-five-way-official-NEW --official-checkpoint-grade
```

Only checkpoint grading in that command is actual official evaluation; **branch
grades remain synthetic fixtures**. It uses comment-only source edits, not a gold
patch. The sprint already ran this once, so a reproduction need not repeat it merely
to inspect evidence. Commands record raw subprocess invocation/exit/output. The
functional wrapper ultimately launches `scripts/benchmark_functional_check.py` with
explicit config/authorization/run-dir/approve-live inside a disposable synthetic
fixture; this flag is a test-local admission record, not real paid permission.

Preserve each invocation with the existing command recorder:

```sh
python3 scripts/benchmark_record.py --label UNIQUE_LABEL -- env PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 scripts/check_scaffold.py
```

Records are exclusive under `runs/swebench-integration/commands/UNIQUE_LABEL/`.
Earlier failed records are not replaced by passing ones.

## Configuration selection and real dry-run

New disabled specification: `configs/swebench-comparison-v1.2.json`.
Matched plan: `analysis/swebench-comparison-v1.2-plan.json`.
Pending reference: `analysis/swebench-comparison-v1.2-authorization-template.json`.
The complete pin/amendment details are in
`protocol_amendments/swebench-interface-v1.2.md`.
Canonical specification/plan hashes are immutable launcher anchors, not hashes to
regenerate after editing a scientific setting. A different experiment needs explicit
review/versioning. Existing v1.0/v1.1 scientific inputs remain separate and frozen.

The real production dry-run, with no test injection, is:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v1.2.json --plan analysis/swebench-comparison-v1.2-plan.json --authorization analysis/swebench-comparison-v1.2-authorization-template.json --run-dir runs/swebench-integration/exploratory-v1.2-pending --dry-run
```

It checks source/task/schema/prompt/provider/image/evaluator/budget bindings and reports
that the pending scope is **not admitted live**. It makes no provider request, creates
no output/guard and does not consume an authorization. Credential presence is a
boolean, not a displayed value. It is a local dry-run, not paid model validation.

## Later live execution requirements

All old spending permissions are closed. A future user must explicitly authorize
one fresh comparison and cap. Create a new authorization record referencing the exact
1.2 config/plan hashes, stable unique authorization ID, cap and one attempt, with
`provider_inference_authorized: true`; preserve the pending template. A file edit is
not itself user permission. Do not reuse/change an old guard or ledger, or rename
an output path to repeat a claimed scope.

After that authorization only, the supported command shape is:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v1.2.json --plan analysis/swebench-comparison-v1.2-plan.json --authorization AUTHORIZED_NEW_RECORD --run-dir NEW_UNOCCUPIED_RUN_DIRECTORY --approve-live
```

The launcher checks current public catalog mapping/routing/price assumptions,
credential presence, official smoke/evaluator/image readiness and reservation
headroom before its first inference. No paid smoke or automatic retry. An atomic
authorization-ID guard admits one launch; failures remain recorded. The pending
template fails before provider/environment admission. No model substitution or
fallback is allowed. Proposed worst-case pricing envelope is $8.14048704 plus
$0.0844032 largest reservation; a $10 proposal is not a current spending allowance.
Unknown usage stops later calls. Larger numeric predecessor budgets are only a
proposal in `analysis/swebench-predecessor-budget-v1.2.json`, not silently applied.

## Inspecting and interpreting outputs

Use controller-only `binding.json`, `execution-config.json`, `authorization.json`,
`plan.json`, `task-image.json`, predecessor raw/wire responses, checkpoint inventory,
handoffs/imported state/omissions, generator artifacts, per-condition inputs/calls,
measurements/predictions/results and shared spending. Validate seals through
`RawRun.open_existing(...).load_frozen()`; archive files are exclusive/read-only
through the API, not a complete OS tamper-proof boundary.

Successor patches are cumulative from official base, not incremental. Unique official
run IDs prevent cached reports being mistaken for new grades. Official invocation
command/exit/report paths stay in `.cache/swebench-evaluator/invocations/` and
`logs/evaluation/`. A launcher exit 0 means its command returned; inspect `result.json`
for interrupted/ineligible outcomes, rather than inferring resolution from exit or
agent finish. Unstarted branches are ungraded, never failures. Separate service charges,
uncached conservative accounting and synthetic estimates. Annotation contract validity
is not truth; repetition interpretations require source events and human/model labels.

Actual software evidence, the completed empirical pilot, and its remaining limits are
reported separately in `paper/MANUSCRIPT_FINAL_PILOT.md` and
`paper/EDITORIAL_AUDIT_20261027.md`. Final sprint command outputs,
preservation evidence, and the blocker recorded at that time are indexed by
`BENCHMARK_PROGRESS.md` and
`results/offline-reliability-sprint-20261011/REPORT.md`.
