# Offline reliability sprint — completed 2026-10-11

**P0–P5 completed within the authorized offline scope. No provider inference ran;
actual API spending $0. Historical runs/ledgers/guards remain closed.** Final
verification passed 69 focused tests, 189 broader tests, the scaffold check and a
real production dry-run. Working software is established with synthetic decisions;
real-model reliability and handoff effectiveness remain unproved.

## Failure and verified repair

The twelve-call confirmation crashed after one valid listing because
`PublicAcceptanceBoundary12.__call__` imported
`scripts.agent_decision_diagnostic.information_action`. Direct execution of
`scripts/benchmark_functional_check.py` puts its scripts directory, not the project
root namespace, on the import path. Its existing startup adds only `src`. Root-CWD
unit tests had masked the missing `scripts` package. Dry-run did not invoke the
callback and could not detect this.

Fresh subprocess regression on **both host Python and the installed evaluator
interpreter** reproduced exactly `ModuleNotFoundError: No module named 'scripts'`
after a real first Docker action. Original output/exit 1:
`runs/swebench-integration/commands/sprint-p0-public-before-fix/`.
An earlier dedicated-venv check found missing jsonschema; installation of the
already pinned 4.26.0 is separately recorded in
`commands/sprint-p0-venv-existing-dependency/`. Global packages were not changed.

The unchanged shared inspection predicate now lives in importable
`src/keisho/benchmark/inspection.py`. Both scripts import the package helper; the
callback no longer depends on a scripts namespace. No project-root sys.path hack
was added. The new subprocess test actually invokes the acceptance callback,
so it failed before this change and passes afterwards. The paid failed run and
its $0.0002804 record are unchanged, not relabelled successful.

## Full offline execution evidence

Durable invocation, exit 0:

```sh
python3 tests/run_offline_functional.py --output results/offline-reliability-sprint-20261011/functional-complete
```

The test wrapper launches the actual public `scripts/benchmark_functional_check.py`
entry with explicit config/authorization/run-dir/approve-live in a fresh subprocess.
Its exact child command is in `functional-complete/cli-command.json`. Test-only
PYTHONPATH/sitecustomize injection supplies synthetic provider transport and an owned
fixture; it is not installed and no production bypass flag was added. No fixture-side
source edits occur. Parser, actual Docker executor, isolation, logger, spending,
feedback and callback paths are production code.

Sequence from sealed `predecessor_tool_001`–`005` and corresponding result events
under `functional-complete/runs/functional-confirmation12-v1/`:

1. List the disposable public repository.
2. Read `ledger.py`.
3. Request `python check_public.py`, observe exit 1.
4. Request permitted complete `ledger.py` write, observe source change.
5. Request the public test again, observe exit 0 and the post-edit acceptance marker.

The callback stops at that completed boundary with a passing controller record;
independent acceptance passes 4/4, acceptance inputs unchanged and only permitted
source changed. It does not simulate an extra model finish after the boundary.
Explicit finish handling is separately exercised by synthetic benchmark branches.
Five synthetic model/tool calls; synthetic token usage 4,355 input/322 output;
actual provider cost $0. This is an engineering check, not autonomous AI evidence.

Instrumentation: actual responses 5, missing 0; syntax/action-schema/safety invalid
0/5 (0%); auxiliary invalid 1/5 (20%), diagnosed and excluded; action rejection
0/5; completed tools 5/5 (100%); successful tools 4/5 (80%). The initial nonzero test
is completed useful evidence. The deliberately unsupported first claim is preserved;
no label/action/text was repaired. Unknown-reference and malformed-annotation coverage
also remains in focused regressions.

Final public subprocess scenarios include complete execution on both interpreters,
invalid JSON, syntactically valid invalid argument types, unsafe path, provider failure
with held unknown reservation, infrastructure failure, genuine failing task and twelve-
call budget exhaustion. Missing results stop as infrastructure failures. All raw
response capture/diagnostics, no retries, history feedback and seals are checked.
Host secret/private-answer-key canaries never appear in agent artifacts; real Docker
sessions also verify no mounts, credential environment, privileged mode or network.
This tests specified channels, not all possible isolation vulnerabilities.

## Interface correction and unresolved listing cause

All five actions were expressible under the historical outgoing strict schema and
local parser; requests retained original issue plus previous assistant actions and
matching tool results. Prior saved service content matched parser text and recorded
actions. No local action replacement or forced-list setting was established.
The **cause of repeated listing remains unresolved**. Four prior probes suggest
output mode is worth testing, but cannot establish a general causal effect.

There is demonstrated inventory overhead. Deterministic `bounded-listing/1.0` now
offers prefix/cursor/limit paging, explicit omissions and counts, and references to
earlier retained identical pages. Changed inventory invalidates cursors; stale cursor
feedback asks a restart without replacing the requested action. History is retained,
not compressed. The mechanism applies equally across all conditions and has no
task-specific hints. Tests discover all 1,500 fixture paths and cover byte/entry
bounds, repeats, edits, prefixes, malformed arguments and multi-turn history.

Read-only reconstruction of the same ten historical Xarray messages: 312 paths;
legacy listing 2,598 tokens, first bounded page 1,051, duplicate marker 264;
message-content total 150,852 versus reconstructed 47,217 (difference 103,635).
`listing-token-audit.json` records assumptions. This omits service framing and schema
charges, uses placeholder hashes and changes no historical telemetry. It is payload
analysis, not a prediction of actual model behavior or a reason to increase budgets.

## Five-way integration and official grading

Actual invocation, exit 0:

```sh
python3 tests/run_offline_benchmark.py --output runs/offline-sprint-five-way-02 --official-checkpoint-grade
```

This launches the real public comparison entry with the frozen 1.2 config/plan,
test-only synthetic admission and transport, **real Docker base initialization,
four-action predecessor, checkpoint, note construction, freeze/restoration and five
independent successor sessions**. Raw artifacts are in
`runs/offline-sprint-five-way-02/runs/five-way-synthetic/`.
Every branch uses the same model settings, system/tools, snapshot, budgets and task.
Assertions cover separate contexts, identical allowed note source packets, no private
grade/answer-key/cross-branch inputs, complete history, compact limits, cumulative
predecessor-plus-successor export and unique evaluation IDs.

Predecessor: list/read/write a **comment-only synthetic marker**/compile; checkpoint
after source edit and completed compile. It establishes source-change/checkpoint
plumbing only. All handoffs derive from that same record. Its earlier read becomes
REVALIDATE under Keisho's existing scope policy, which the benchmark bridge previously
failed to invoke. No new state schema/compiler/semantic importer was introduced.

| Condition | Execution | Grade used by fixture, **not official** | Handoff tokens | Synthetic model/tool calls | Synthetic input/output tokens | Estimated note / continuation dollars | Annotation exclusions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REPOSITORY_ONLY | Budget stopped, repeated reads | Stub unresolved | 0 | 24 / 24 | 345,732 / 504 | 0 / 0.695496 | 0; no claims supplied |
| FULL_HISTORY | Read, add second comment, explicit finish | Stub resolved | 11,224 | 3 / 2 | 47,300 / 880 | 0 / 0.101640 | 0; no claims supplied |
| SUMMARY_2K | Explicit finish | Stub unresolved | 35 | 1 / 0 | 3,320 / 21 | 0.0059604 / 0.006808 | 0; no claims supplied |
| STRUCTURED_NOTES_2K | Explicit finish | Stub unresolved | 339 | 1 / 0 | 3,624 / 21 | 0.0063044 / 0.007416 | 0; no claims supplied |
| KEISHO_2K | Injected executor interruption | Stub error | 549 | 1 / 1 attempted | 3,834 / 12 | 0 / 0.007764 | 0; no claims supplied |

These choices/grades intentionally exercise state handling; **the table cannot rank
handoffs or show a Keisho loss/win**. Synthetic annotation coverage has zero supplied
claims, not 100% meaningful coverage. Estimated predecessor dollars 0.0083868;
generation 0.0122648; total ledger estimate 0.8397756, reservations 0. Actual charges
are $0 and no service request occurred. Synthetic tokens are supplied test telemetry.

One checkpoint grade was **actually official**, after note freeze: run ID
`keisho-five-way-synthetic-checkpoint-699d233da7c7-1141e7ad5560`, evaluator exit 0,
**unresolved**. It graded the cumulative comment-only checkpoint patch on the unchanged
selected-task harness/image. Invocation/output is under
`.cache/swebench-evaluator/invocations/<run-id>/`; report under
`.cache/swebench-evaluator/logs/evaluation/<run-id>/results.json`.
Detailed answer-key material remains private. Branch grading is explicitly stubbed;
no five official task solutions or real model continuations are claimed.

## Prospective binding and budget

- Disabled config `configs/swebench-comparison-v1.2.json`, canonical SHA
  `f4c7733335e0991aebdc59ac393b8a347207b452accc1119831273f77691d425`.
- Matched plan `analysis/swebench-comparison-v1.2-plan.json`, canonical SHA
  `6bd86821a4d40df417c49a03f5564546e212d7f401bd74d8d0ee9ea5105902ba`.
- Pending authorization template, **false inference permission**, stable ID and
  exact config/plan bindings. It is not user approval and no real guard exists.
- `benchmark-agent/3.0`, JSON-object/3.0, local action contract 3.0, unchanged
  auxiliary-claims/2.0 and structured-adapter/1.1; pins in config/amendment.
- Same Xarray task/model routing/conditions/order/checkpoint/numeric budgets as 1.1.
  No old config, prospective permission bit, ledger or guard was overwritten.

Explicit launcher resolution accepts exact supported config/plan hashes and passes
binding through output/ledger/guard/notes/branches/evaluation IDs. Metadata cannot
authorize scientific changes. New scope guards are keyed to stable authorization ID,
so changing a timestamp/output does not admit a second concurrent attempt. Pending
scope live start fails before provider admission. Real dry-run, exit 0:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v1.2.json --plan analysis/swebench-comparison-v1.2-plan.json --authorization analysis/swebench-comparison-v1.2-authorization-template.json --run-dir runs/swebench-integration/exploratory-v1.2-pending --dry-run
```

Record `commands/sprint-final-real-dry-run/` reports no requests/guard and
`live_start_admitted: false`, pending authorization. Real image/evaluator/package/source
checks pass. No paid catalog/credential-validation/inference call was made.

Predecessor review `analysis/swebench-predecessor-budget-v1.2.json`: first input upper
4,227; 180k total permits roughly 13–15 moderate-growth or 10–11 larger-growth
actions under stated conservative assumptions. That can plausibly permit a targeted
investigation/edit/test; it cannot guarantee 48 calls or a useful checkpoint. Numeric
limits stay frozen. A proposed 240k sensitivity needs a distinct future amendment and
plan; it was not applied. Recorded full-block envelope $8.14048704 plus $0.0844032
reservation headroom is a frozen-price estimate, not fresh spending permission.

## Final-state tests and preserved failures

All commands/output/exit codes live under `runs/swebench-integration/commands/`:

| Invocation | Result |
| --- | --- |
| `sprint-final-focused-02`: focused command in reproducibility guide | 69 tests, exit 0 |
| `sprint-final-broad-01`: `PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v` | 189 tests, exit 0, no skips |
| `sprint-final-scaffold`: `python3 scripts/check_scaffold.py` | Four-condition legacy scaffold passed, exit 0 |
| `sprint-final-real-dry-run`: exact production command above | Passed local checks; paid admission false, exit 0 |

Earlier failures remain: missing dedicated-env dependency; exact scripts import
failure; legacy response-measurement test assuming a now-sealed guard absent; correct
rejection of synthetic output under protected results; evidence-packet assertion that
mistakenly included differing generator instructions; zero-string versus Decimal zero;
and an old constructor-bypassing fixture missing explicit legacy listing policy.
Tests were corrected to their intended contracts, with diagnostics preserved;
no real guard was reset or legacy action validation weakened. The latter fixture now
declares the same legacy policy as the constructor; old protocol failure tests remain.

`preservation-verification.json` confirms **4,992 historical files unchanged**, including
configurations, ledgers/guards/results. Implementation hashes and environment versions
are in `implementation-manifest.json`. Final code edits precede both passing suites.

## Deliverables and limitations

Changed runtime files: the two functional/diagnostic scripts; new benchmark inspection
and listing modules; benchmark environment/comparison/evaluator/response measurements;
agent missing-result/failure handling; versioned local schema; existing workspace scope
adapter; optional benchmark dependencies. Focused tests/new subprocess injection/wrappers
and v1.2 disabled config/plan/template were added. Exact inventory is in the implementation
manifest. No baseline prompt or Keisho memory representation was redesigned.

Research artifacts: `research/BASELINE_COMPARISON.md`, `research/RESEARCH_PLAN.md`,
`research/REPRODUCIBILITY.md`; `paper/OUTLINE.md`, `paper/METHODS_DRAFT.md`,
`paper/RESULTS_PENDING.md`; prospective `protocol_amendments/swebench-interface-v1.2.md`.
The audit acknowledges actual baseline uncertainty, failure/post-edit validation,
verification instructions and limited contradiction repair. Defensible difference:
deterministic whole-item compact selection with explicit event attribution and named-file
revalidation labels. It is a narrow mechanism claim, not demonstrated improvement or
global novelty. Baseline adaptation/recovery differences and importer loss limit claims.

Remaining steps for a first real five-way comparison: fresh explicit one-attempt spending
authorization bound to the disabled 1.2 config/plan (or separately reviewed prospective
budget amendment); check current route/prices and local gates; run one public live command
in a new output namespace; retain its predecessor outcome; only if eligible, freeze notes,
run five independent successors and grade cumulative patches with unique IDs. No
no-checkpoint resampling. A completed **real** twelve-call functional check is still absent;
if required as an additional gate, it needs its own expressly budgeted authorization.
No further infrastructure phase is required by the demonstrated launch-path defect.
No commit, push, merge, deployment, paid run or publication occurred.
