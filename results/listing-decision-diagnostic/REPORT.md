# Controlled listing decision diagnostic

Both strict-schema probes proposed another listing. Both JSON-object probes
proposed reading `api.py`. The prescribed preference order selected **B: predecessor
mini + JSON object**. Its one fresh confirmation inspected sources, reproduced the
failure, and edited `ledger.py`, but reached eight calls before model-run post-edit
validation. The independent public check then passed all four cases. The frozen
confirmation rule therefore records **failed/incomplete**, not a complete agent
workflow. No ninth call, second confirmation, or SWE-bench run occurred.

The requested output format is a plausible contributor to this listing behavior
in the tested model/service setup. One response per cell does not identify whether
schema constraints, the model's response to them, or upstream processing caused
the difference. The JSON-object confirmation demonstrates actual reads, a shell
test and a source write; it does not establish general reliability or handoff
effectiveness. Interpretations of relevance and behavior are model-assisted,
without human review.

The previous eight-call check configured canonical
`openai/gpt-4.1-mini-2025-04-14`, requested public alias `openai/gpt-4.1-mini`, and
received that same service model identifier. The service reported upstream
`OpenAI`, through the OpenRouter adapter. All eight requests used strict
`json_schema` (`keisho_agent_response_v2`, strict true), `plugins: []`, no visible
`transforms` field, and no native tools/tool-choice setting. Saved returned message
content equals parser input and recorded action. No local default action or action
replacement was observed. The adapter performs credential redaction before
archiving; these are saved service responses, not attested untouched upstream
outputs. Unreported upstream processing and physical model identity remain unknown.
`prior-response-audit.json` records the evidence for every prior call.

Before inference, `configs/listing-decision-diagnostic-v1.json` froze the exact
second logical request, including all five messages: original system/objective,
empty framing message, first assistant listing and corresponding result. No later
listing, new instruction, solution or probe result was added. The same messages,
seed 20261007, temperature 0, 2,048 output tokens, stream false, plugins and local
auxiliary policy were used in A/B/C/D order. Probe input cap: 32,000; context cap:
128,000. Requested model and its routing price ceilings are the only model-specific
parameter differences. Within each model pair, the actual wire bodies differ only
in `response_format`. All four wire message arrays match exactly.

The models are distinct configured mappings: mini above, and successor
`openai/gpt-4.1-2025-04-14` requested as `openai/gpt-4.1`. Current unauthenticated
catalog metadata confirmed both mappings, OpenAI routing, pricing and advertised
response-format/structured-output support. JSON object mode uses the existing
adapter default without a schema. The public documentation describes these modes.
[OpenRouter parameters](https://openrouter.ai/docs/api_reference/parameters),
[structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).
Catalog snapshots are preserved before inference and in the live run.

In the table, **mini** is requested/returned `openai/gpt-4.1-mini`; **full** is
requested/returned `openai/gpt-4.1`. Every new response reports upstream **OpenAI**;
no snapshot attestation/fingerprint was returned. New request plugin settings
remain empty and transforms absent. Probe costs below are identical under returned
charges and conservative accounting. No proposed probe action executed.

| Cell | Requested / returned | Format | Proposed action | Parse / action schema / safety | Relevant new info | Annotation accepted / supplied | Input / output tokens | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | mini / mini | Strict schema | `list_files` | Yes / Yes / Yes | No | 1 / 1 | 860 / 53 | $0.0004288 |
| B | mini / mini | JSON object | `read_file`, `api.py` | Yes / Yes / Yes | Yes, qualifies | 1 / 1 | 624 / 68 | $0.0003584 |
| C | full / full | Strict schema | `list_files` | Yes / Yes / Yes | No | 1 / 1 | 796 / 60 | $0.0020720 |
| D | full / full | JSON object | `read_file`, `api.py` | Yes / Yes / Yes | Yes, qualifies | 0 / 1 | 554 / 67 | $0.0016440 |

D's annotation basis was exactly `tool/predecessor`; permitted values are `tool`,
`predecessor`, `independent`. It was excluded with an explicit diagnostic and
annotation information unknown. Its action remained independently valid under
the same auxiliary policy. No label/reference was repaired or replacement claim
invented. Relevance was assessed prospectively from existing fixture contents;
reading a file would attempt new information, while repeated inventory would not.
These are proposals, not observed read results.

Confirmation B started from the saved fixture's initial files and **three-message
initial context**, with no probe response/action or previous trajectory. It used
the same mini mapping, JSON-object mode, system/task prompt, existing Docker tools,
eight model/tool calls, 2,048 output, 32,000 request input, 128,000 context, 180,000
cumulative tokens and 600-second limit. Docker was already active; the existing
immutable image was reused, with no mounts/network/host credentials/socket and
the existing resource/action containment. No image or evaluator was rebuilt.

Actual confirmation sequence, inspectable in its `predecessor_result_001`–`008`
events under `runs/listing-decision-diagnostic-v1/confirmation/`:

1. Listed the fresh six-file repository.
2. Read `api.py`.
3. Read `ledger.py`.
4. Read `normalize.py`.
5. Read `check_public.py`.
6. Read `tests.json`.
7. Ran `python3 check_public.py`: exit 1, two public cases failed.
8. Wrote `ledger.py`, changing replacement accounting.

The model made no post-edit test call. The independent controller check exited 0:
`single_release`, `replacement_then_release`, `replacement_active`, and
`normalizer_preserves_events` all passed. Acceptance files were unchanged and only
permitted source changed. This is limited four-case public-test evidence; broader
correctness is unverified. The saved patch also contains controller-created Python
cache additions, preserved as-is and never submitted as a benchmark prediction.

The raw helper field `model_executed_public_test: false` tracks its **post-edit**
acceptance boundary. It does not mean no test was executed: event 007 is the actual
pre-edit failing test. `verified-outcome.json` records both meanings explicitly
without rewriting the original result. The eight-call ceiling bound; tokens
(12,042 input / 737 output, 27.33 seconds) and dollars were not exhausted.

Confirmation annotations: 8 supplied, 7 contract-accepted, 1 excluded. The first
response cited unavailable evidence ID `1`; its exact reason/raw claim is archived.
The listing action still passed independent admission. Invalid annotation is not
relabeled false/falsified, and contract acceptance is not semantic truth. All 12
new saved message contents, parser inputs and proposed/recorded actions match.
Confirmation feedback retains its own previous responses/results in order.

| Stage | Model calls | Input / output tokens | Provider-reported charges | Conservative accounting |
| --- | --- | --- | --- | --- |
| Four probes | 4 | 2,834 / 248 | $0.0045032 | $0.0045032 |
| One confirmation | 8 | 12,042 / 737 | $0.0040376 | $0.0059960 |
| Total | 12 | 14,876 / 985 | **$0.0085408** | **$0.0104992** |

All requests settled; outstanding reservations **$0**. Shared cap **$2**, unused
conservative allowance $1.9895008. The ledger/scope are closed; remaining allowance
is not permission for another trial. The pre-inference worst-case reservations
were $0.87779328, including possible 5% BYOK fees and no cache discount. No charged
provider failures, inference smoke calls, credit purchases or automatic retries.

Implementation is the small diagnostic launcher `scripts/agent_decision_diagnostic.py`,
using existing adapters, logger, parser, runtime validator and agent loop. A new
$2 scope is narrowly registered in `src/keisho/pilot/spending.py`; legacy checks
remain. Existing public-fixture setup/assessment were extracted for reuse in
`scripts/benchmark_functional_check.py` without changing their behavior. Regression
coverage: `tests/test_decision_diagnostic.py`; prospective procedure:
`protocol_amendments/listing-decision-diagnostic-v1.md`. No production default
format, handoff representation, benchmark baseline or scientific settings changed.

Final offline checks passed **43 focused / 160 broader tests**, exit 0. Exact
commands/output: `runs/swebench-integration/commands/decision-diagnostic-focused-01/`
and `decision-diagnostic-offline-01/`. Their injected fixture results are software
checks, not API confirmation successes. The one real command was:

```sh
python3 scripts/agent_decision_diagnostic.py --approve-live
```

Its complete invocation/output is in `commands/decision-diagnostic-live-01/`,
exit **1** for the incomplete confirmation. Authorization reference:
`results/listing-decision-diagnostic/authorization.json`. Exclusive guard/complete
raw requests, responses, assessments, accounting and trajectory seals:
`runs/listing-decision-diagnostic-v1/`. Post-run read-only verification passed,
exit 0, recorded in `commands/decision-diagnostic-postrun-verification/`.
All **585 protected historical files** and pre-inference source hashes are unchanged;
old/new seals verify. No old ledger or authorization was reopened. Progress updated;
no commit, push, merge, publication, additional confirmation or SWE-bench execution.
