# Keisho agent-interface diagnosis and functional check

**The one real functional check failed.** It made eight API calls and eight
`list_files` actions, with no contents inspected, source edited, or model-executed
test. Its unchanged public test still fails. No new handoff comparison was started:
both required gates are unsatisfied—a passing functional check and a demonstrated
shared-interface repair. Basic API-driven usability has not been established under
this contract. Neither completed run is a Keisho-effectiveness result.

New-scope charges: **$0.0027084 provider-reported**, **$0.0046284 conservatively
accounted**, **$0 outstanding reservations**. All eight calls settled; no charged
failure with unknown usage. The unused shared allowance is $9.9953716 by conservative
accounting, but it does not authorize a retry after the failed one-attempt check.
Comparison/handoff generation/continuation spending is $0. The new scope is closed.
Old charges, ledgers and guards remain separate and unchanged.

No schema, serialization, feedback or local token-gate defect was demonstrated.
The original outgoing payloads are saved in each response's `request_body_json`;
they were not reconstructed and labeled telemetry. Rebuilding them with the
current actual provider adapter reproduces all ten bodies exactly. Every original
body contains the same strict `keisho_agent_response_v2` schema. Its nested action
union permits all advertised operations:

| Action | Valid witness arguments | Original wire schema | Local parser/admission |
| --- | --- | --- | --- |
| list_files | `tool` | Pass | Pass |
| read_file | `tool`, relative `path` | Pass | Pass |
| write_file | `tool`, relative `path`, string `content` | Pass | Pass |
| shell | `tool`, string `command` (`python check_public.py`) | Pass | Pass |
| finish | `tool`, string `answer` | Pass | Pass: runner completion branch |

`offline-diagnosis.json` contains the exact witnesses and original-schema results.
New regressions validate those witnesses at the real request-building/transport
boundary for both frozen models, then the parser and applicable runtime validator.
They also exercise finish through `run_agent`, reject missing/extra/conflicting
arguments, preserve local path/command safety, and verify multi-turn feedback
for predecessor and successor. `run_tests` is not this runner's advertised action;
public testing uses shell. Schema validity does not authorize unsafe paths or
prove annotation truth. OpenAI documents nested `anyOf` within its supported
subset; local schema compatibility does not prove every branch works at the
upstream decoder. [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

The original issue exactly matches the public selected-task record. Requests 1,
2 and 10 have 3, 5 and 21 messages respectively. All ten retain that issue/system
prompt, preceding assistant response texts, and the corresponding result event
IDs/payloads in order. Results are intelligible inventories; none were dropped,
replaced or attached to another action. There is no native `tools`/`tool_choice`
setting forcing listing. The system advertises five actions and puts listing first,
but does not require repeated listing. Production code transports each request and
returns its provider response without using a scripted fixture; ten distinct
provider generation IDs are recorded. Provider prompt caching is not evidence
of local response replay.

Original stop reconstruction:

| Call | Actual input/output tokens | Conservative input upper | Previous inventory results in input |
| --- | --- | --- | --- |
| 1 | 3,349 / 59 | 4,444 | 0 |
| 2 | 6,030 / 69 | 7,147 | 1 |
| 10 | 27,560 / 13 | 28,861 | 9 |

Each dollar reservation was $0.01688064, based on the full 32,000-input/2,048-output
caps, no cache discount and possible 5% BYOK fee. Token admission instead uses
native message text + schema + conservative framing. After ten calls, provider
usage totaled 154,909 input/output tokens. The next upper bound was 31,574 plus
2,048 output: **188,531 cumulative tokens > 180,000**. It would fit the 32,000
request-input and 128,000 context caps and the remaining $10 dollar budget.
The cumulative gate stopped it before an eleventh request; one request did not
exceed its context. No budget/history/compression change was made.

The inventory was transmitted 45 times across requests: 431,865 bytes and 115,335
isolated component BPE tokens. The tenth input alone contains nine inventories,
23,067 component tokens; all full feedback messages together contain 117,540
isolated tokens. The difference includes event/action/hash wrappers. These component
counts are not additive attribution of provider context usage. Provider completion
counts also differ from isolated response-text counts, particularly original calls
6–10 (13 reported versus 69–78 isolated); upstream accounting semantics remain
unverified. The recorded provider usage/billing and conservative reservations were
preserved, not replaced with inferred measurements.

Model-assisted interpretation, without human review: repeated inventory feedback
inflated cumulative usage but does not explain the action choice. The first union
variant was selected consistently. Competing explanations remain model behavior
under this prompt/schema and unobserved upstream constrained-decoding behavior.
The failed six-file check shows that a large inventory and this xarray issue were
not necessary to reproduce the looping. It does not identify the causal mechanism.
No action was substituted, listing banned, schema arbitrarily reordered, model
switched, solution hinted or predecessor investigation hand-written.

One demonstrated **test-only** defect was repaired: the offline CLI fixture
substituted a temporary guard only at claim time, after admission had already
checked the consumed real guard. It now binds temporary guard storage before
admission, while retaining real scientific-input validation and exclusive claim
code. The completed live guard/ledger were untouched. This test correction is
not an API-interface repair and cannot justify replaying the benchmark.

Files added: `tests/test_agent_wire_contract.py`,
`scripts/benchmark_functional_check.py`, `configs/swebench-functional-check-v1.json`,
`configs/requirements-interface-tests.lock`, and
`protocol_amendments/swebench-interface-diagnosis-v1.md`. Test-only fixture/assertion
changes: `tests/benchmark_cli_fixture.py`, `tests/test_benchmark_launcher.py`.
README documents the already-installed jsonschema 4.26.0 test dependency.
No production parser/provider/agent/tool/compiler/comparison settings changed.
Contract versions remain auxiliary-claims/2.0, prompt/schema 2.0 and notes adapter 1.1.

Offline validation after final implementation edits: **55 focused and 152 broader
tests pass**, exit 0; native tokenizer tiktoken 0.12.0. Exact commands, exit codes
and full output are under `runs/swebench-integration/commands/`:
`interface-focused-final-02/`, `interface-offline-final-02/`, and
`interface-original-wire-diagnosis/`. The earlier 47-test focused pass and failed
152-test broader run are retained in `interface-focused-final/` and
`interface-offline-final/`. An initial helper import error was corrected before
inference and recorded in scope `preparation-failure.json`. No legacy assertions
were removed or failures overwritten.

The functional attempt reused task_001's existing public initial source/contract
and public cases, with a minimal public-case checker. It was seeded into a uniquely
owned container using the already-prepared image after replacing only that container's
`/testbed`. No gold/hidden tests, prior responses or development conversation were
supplied. The unchanged existing agent loop, provider/model mapping, schema and
Docker tools made the actual choices. The first post-edit acceptance-test attempt
would stop it, pass or fail; no such action occurred.

The one live command was:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_functional_check.py --approve-live
```

Recorded wrapper/argv/output: `commands/interface-functional-live-01/`, exit **1**.
Authorization: `runs/swebench-integration/interface-diagnosis-v1/authorization.json`;
prospective config: `configs/swebench-functional-check-v1.json`; exclusive guard/raw
artifacts: `runs/swebench-integration/interface-diagnosis-v1/functional/`.
`preinference-estimate.json` freezes eight maximum request reservations totaling
$0.13504512, below the $0.50 stage ceiling. The prospective comparison envelope
$8.14048704 plus $0.0844032 headroom would fit the shared cap even after those
maximum setup reservations; affordability was not the blocker. Docker was already
active. Credential presence, verified CA, current unauthenticated catalog pricing/
schema support, input hashes and prepared image identity passed before inference.
No separate paid smoke request or component build/download occurred.

Actual API requested/returned identity was `openai/gpt-4.1-mini`, frozen canonical
mapping `openai/gpt-4.1-mini-2025-04-14`, upstream OpenAI via OpenRouter; no fallback,
snapshot attestation or fingerprint. The check used **9,791 input / 445 output
tokens**, eight model/eight tool calls, 20.62 seconds. It stopped at the **eight-call
ceiling**, not cumulative tokens, context or dollars. A hypothetical next input upper
bound is only 3,106. All eight results list the same six files with no source changes.
Response 8 explicitly annotates repeated listing “before reading source files,”
but never reads them (`predecessor_response_008`, `predecessor_result_008`).

Initial and independent final public tests both exit 1: `single_release` and
`normalizer_preserves_events` pass; `replacement_then_release` and
`replacement_active` fail. The model ran no acceptance test. **9 annotations
supplied, 9 contract-accepted, 0 excluded, 0 unsupported references**; raw contents
and diagnostics remain separate. Read-only importer inspection retains 9 hypotheses
and 8 observed actions; no interpretation is promoted to verified truth.
Controller test checks created Python caches: the saved cumulative fixture patch
contains three `__pycache__/*.pyc` additions, not model source edits. That artifact
is retained as-is and is never a SWE-bench prediction.

| New comparison condition | Execution | Official outcome | Handoff tokens | Model/tool calls | Input/output tokens | Generation/continuation cost |
| --- | --- | --- | --- | --- | --- | --- |
| REPOSITORY_ONLY | Unstarted | Ungraded: setup failed; no justified repair | Not constructed | 0 / 0 | 0 / 0 | $0 / $0 |
| FULL_HISTORY | Unstarted | Ungraded: setup failed; no justified repair | Not constructed | 0 / 0 | 0 / 0 | $0 / $0 |
| SUMMARY_2K | Unstarted | Ungraded: setup failed; no justified repair | Not constructed | 0 / 0 | 0 / 0 | $0 / $0 |
| STRUCTURED_NOTES_2K | Unstarted | Ungraded: setup failed; no justified repair | Not constructed | 0 / 0 | 0 / 0 | $0 / $0 |
| KEISHO_2K | Unstarted | Ungraded: setup failed; no justified repair | Not constructed | 0 / 0 | 0 / 0 | $0 / $0 |

No new benchmark predecessor, checkpoint, handoff, successor, prediction or official
evaluation ID exists. Unstarted methods are not task failures. The selected task,
models, five conditions, branch order, budgets, checkpoint, baseline/Keisho
representations and official grading remain frozen. No comparison configuration
was generated to bypass the failed gate.

Read-only post-run verification passed, exit 0 (`commands/interface-postrun-verification/`).
`functional-verification.json` includes per-call metadata, accounting, annotation
coverage and artifact checks; `scope-spending-final.json` closes this scope. All
211 protected historical files and all pre-inference source hashes verify unchanged.
Both completed runs/guards/results remain preserved. BENCHMARK_PROGRESS.md records
the failed check and stop. No retry, guard reset, commit, push, merge or publication.
