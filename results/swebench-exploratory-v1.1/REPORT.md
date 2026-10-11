# Keisho handoff evaluation on SWE-bench Verified

The successful dry-run was followed directly by **one real version-1.1 live
attempt**. The predecessor made 10 model calls and 10 completed `list_files`
actions, then stopped at the frozen cumulative token-budget gate without a source
edit or validation command. It did not reach an eligible checkpoint. All five
successors are **unstarted**, with no official grades. This is exploratory
development after a protocol repair; it supplies no comparison of handoff methods.

Provider-reported charges total **$0.0165520**. Conservative noncached accounting
totals **$0.0624400**, with **$0 outstanding reservations**. These are both the
predecessor cost and total block cost; handoff generation and continuation each
cost $0. The ledger is closed, the authorization-wide claim is sealed, and there
was no resampling, whole-run retry, extra paid smoke request or outcome-driven
software change.

The launcher defect was its hardcoded version-1.0 configuration, plan, output and
completed guard. The narrow repair added explicit config/plan/authorization/output
binding and dry-run to the existing launcher, propagated it through the runner
and evaluator paths, and retained immutable scientific-input checks and atomic
authorization-wide admission. Implementation files changed before execution:
`scripts/benchmark_compare.py`, `src/keisho/benchmark/comparison.py`, and
`src/keisho/benchmark/evaluator.py`. Tests added:
`tests/test_benchmark_launcher.py`, `tests/benchmark_cli_fixture.py`. Documentation:
`docs/swebench-handoff.md`, `protocol_amendments/swebench-launch-v1.0.md`.
The disabled prospective configuration was preserved; the execution artifact
contains that configuration with only live permission changed, plus binding metadata.

Final implementation validation passed **33 focused tests** and **145 broader
offline tests**, both exit 0. Exact commands and full output are retained in
`runs/swebench-integration/commands/launcher-focused-final/` and
`launcher-offline-final/`. Tests exercise the public CLI with non-default inputs,
downstream propagation, amended response policy, rejected mismatches/scientific
changes/missing approval/occupied destinations, non-consuming dry-run, concurrent
admission, historical preservation, accounting and isolation gates. Their injected
provider/evaluator successes are software-test results, not benchmark grades.
Implementation hashes still match the versions tested. Read-only post-run
verification also passed, exit 0, recorded in `commands/exploratory-v1.1-postrun-verification/`.

The successful real commands, from the project root, were:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.1.json \
  --plan runs/swebench-integration/response-policy-repair/prospective-plan-check.json \
  --authorization runs/swebench-integration/exploratory-v1.1-preflight/authorization.json \
  --run-dir runs/swebench-integration/exploratory-v1.1-live --dry-run

.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.1.json \
  --plan runs/swebench-integration/response-policy-repair/prospective-plan-check.json \
  --authorization runs/swebench-integration/exploratory-v1.1-preflight/authorization.json \
  --run-dir runs/swebench-integration/exploratory-v1.1-live --approve-live
```

Both command exits were 0. Live exit 0 means the bounded outcome was recorded;
the experiment result is `checkpoint_not_reached`, not task success. Exact argv,
timestamps and complete output: `commands/launcher-real-dry-run-docker-active/`
and `commands/live-v1.1-authorized/`, under `runs/swebench-integration/`.
The earlier Docker-off dry-run and its report remain historical and unchanged.

Actual binding, recorded in the sealed live `binding.json`:

| Input | Path or identity | Canonical SHA-256 |
| --- | --- | --- |
| Configuration | `configs/swebench-comparison-v1.1.json` | `f6c5898f2400e7f6d24f70643da2333ea86fd3ba1b5fd30f4ec64ea0c2b3895e` |
| Plan | `runs/swebench-integration/response-policy-repair/prospective-plan-check.json` | `acdb2ec7a25568290b2d0f4ace90b5c43190088825f9ea543402a71d18480ba2` |
| Existing $10 authorization | `runs/swebench-integration/exploratory-v1.1-preflight/authorization.json` | `92736e956e4a097172a4addd7f99fb54e862ad0544325efd9298c184bd0d6276` |
| Agent prompt | `benchmark-agent/2.0` | `054a669071973a82c98bb7bb2c7f858e585a21fc1c86a1386396e4eb84f2644e` |
| Response schema | `json_schema/2.0`, strict `keisho_agent_response_v2` | `e5852f087c53d95a994682cf19715090139f4545e1716f666cbbd620fc1d712c` |

Output/guard: `runs/swebench-integration/exploratory-v1.1-live/`.
Authorization-wide guard: `runs/swebench-integration/authorized-92736e956e4a097172a4addd/`.
This consumed the existing scope; a different output name cannot authorize another
attempt. The zero-spend blocked preflight and the completed version-1.0 ledger
were not reopened. Policy remains `auxiliary-claims/2.0`, notes adapter
`structured-adapter/1.1`; task, checkpoint rule, five conditions, 2,048-token
compact-note caps and all continuation budgets are unchanged. Frozen order:
FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY, KEISHO_2K, STRUCTURED_NOTES_2K.

Preflight verified credentials by presence only, Docker daemon and pinned image,
dedicated evaluator installation and prior successful official setup smoke,
input/prompt/schema hashes, spending admission, and current public provider
catalog. The $8.14048704 planned envelope plus $0.0844032 reservation headroom fit
$10. No component was rebuilt/downloaded or isolation relaxed. Public catalog
responses are archived in live `public-catalog-preflight.json`.

Task `pydata__xarray-6721` started at official base
`cc183652bf6e1273e985e1c4b3cba79c896c1193`. Dataset revision:
`c104f840cc67f8b6eec6f759ebc8b2693d585d4a`; harness 5.0.2 at
`02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`; task recipes
`3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d`; Handoff Debt author code
`5179b1d759be466600c453da8b9078341967ec17`. Image:
`swebench/sweb.eval.x86_64.pydata_1776_xarray-6721@sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898`,
linux/amd64 through ARM Docker Desktop emulation; Python 3.10.15,
xarray 2022.6.0rc1.dev17+gcc183652b, NumPy 1.23.0, pandas 1.5.3.
Container restrictions remained network disabled, no host mounts/credentials/socket,
capabilities dropped and no-new-privileges, with existing resource/tool limits.
These controls do not establish complete isolation.

The first real request exercised the prepared strict provider schema. All 10 raw
provider message contents match the separately saved response texts; all request
schema hashes match. API request and returned model were `openai/gpt-4.1-mini`,
configured canonical identity `openai/gpt-4.1-mini-2025-04-14`, upstream OpenAI via
OpenRouter with OpenAI-only routing and no fallbacks. No snapshot attestation or
system fingerprint was returned. Successor `openai/gpt-4.1` and note generation
were never requested. Provider usage: **154,512 input / 397 output tokens**,
including 152,960 cached input tokens. Conservative accounting does not assume
cache discounts; all 10 attempts settled, none failed with unknown usage.

The predecessor established the 312-file inventory, not the bug's cause. Every
`predecessor_tool_001` through `_010` was `list_files`; each corresponding result
has identical payload hash and no changed paths. The cumulative terminal patch
from the official base is empty (`predecessor/terminal-patch.json`). No repository
file contents were read, no edit occurred, and no test/build/lint/validation ran.
Source events and per-call hashes are listed in this report's `verification.json`.

Model-assisted interpretation, without human review: the repeated inventory
requests made no observable new repository information available after the first
result. For example, `predecessor_response_002` conjectured the role of
`xarray/core/dataset.py` while requesting the inventory again. Responses `_008`,
`_009`, and `_010` repeated the same conjecture about `xarray/core/common.py`, with
updated references to prior inventory results. These are not inspected source
evidence, demonstrated fixes, or successor reuse/inherited-belief examples.
Why the model chose only inventory calls remains unknown; the schema permits all
five declared action types. No causal claim about the schema is established.

The stopping cause is independently reproducible offline: consumed input/output
154,909 + next input upper bound 31,574 + output reservation 2,048 = **188,531**,
above the frozen **180,000** predecessor total. The next request would fit the
32,000 input and 128,000 context limits; it fails the cumulative limit. No eleventh
request was sent. The API-dollar cap was not exhausted. The specified checkpoint
requires validation after a non-test source edit, so eligibility is false and no
private checkpoint classification or official evaluator invocation was performed.

Annotations: **10 supplied, 10 contract-accepted, 0 excluded; no unsupported
evidence IDs**. Diagnostic arrays and raw claims are preserved for every response.
Contract acceptance is not truth: nine claims used `VERIFIED` while citing only
inventory results. A read-only post-run importer inspection retained 10 claims
as **HYPOTHESIZED** and 10 completed-action items as **OBSERVED**, preserving
declared labels and references without promoting them to verified facts. This
derived state is outside the sealed run in `postrun-imported-state.json`; no
Keisho handoff was compiled and no successor saw it. Missing observations,
changes, failures, questions, uncertainty and next actions remain unknown.

| Condition | Execution | Official outcome | Handoff tokens | Post-handoff model/tool calls | Input/output tokens | Generation cost | Continuation cost | Annotation coverage/exclusions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPOSITORY_ONLY | Unstarted | None: no eligible checkpoint | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | N/A; 0 supplied, 0 excluded |
| FULL_HISTORY | Unstarted | None: no eligible checkpoint | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | N/A; 0 supplied, 0 excluded |
| SUMMARY_2K | Unstarted | None: no eligible checkpoint | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | N/A; 0 supplied, 0 excluded |
| STRUCTURED_NOTES_2K | Unstarted | None: no eligible checkpoint | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | N/A; 0 supplied, 0 excluded |
| KEISHO_2K | Unstarted | None: no eligible checkpoint | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | N/A; 0 supplied, 0 excluded |

Separate condition JSON artifacts accompany this report. No handoff text differed
because none was constructed; no successor took an action. No prediction was
submitted, and no new official grading run ID exists. Unstarted branches are not
unresolved task failures. The earlier reference-patch smoke remains evaluator
setup evidence only. This attempt cannot support a Keisho win/loss, reduced
hallucinations, leaderboard result or general advantage. Another comparison
cannot be justified as a handoff-effectiveness replication from these data; a
future separately authorized investigation would first need to explain the
predecessor's repeated inventory behavior.

All 70 protected historical artifacts/configuration files remain byte-identical;
the old, new predecessor, live-run and authorization seals verify. Original raw
requests/responses, events, execution metadata, pricing metadata, empty cumulative
patch and closed ledger remain in the live directory. `verification.json` and its
read-only `verify_outcome.py` record post-run checks. `BENCHMARK_PROGRESS.md` now
records the completed bounded attempt. No commit, push, merge, publication,
execution-guard reset or modification of Keisho in response to this outcome.
