# One authorized real v1.3 functional confirmation

**Passed in 8 model calls and 8 successful tool actions.** The single new
$0.50 authorization is consumed and closed. Four of the twelve permitted call
slots remained unstarted. No retry, guard reset, additional confirmation or
SWE-bench execution occurred.

The model inspected `api.py`, `ledger.py` and `normalize.py`, then inspected the
public checker and cases. It changed only the source file `ledger.py`, subtracting
the old reservation's units before replacing it. Its next action directly requested
`python3 check_public.py`; that post-edit test exited 0 and reported
`PUBLIC_ACCEPTANCE passed 4 cases`. Independent controller acceptance also passed
4/4. Immutable test/contract inputs were preserved. The exported patch additionally
contains test-generated Python bytecode caches, which the existing inventory excludes.

Exactly one canonicalization occurred: the first model response proposed
`{"tool":"list_files","args":{"limit":100}}`, which was recorded separately
and validated as `{"tool":"list_files","limit":100}`. The remaining seven
actions were flat. All eight responses had valid JSON/envelopes, valid wire and
canonical actions, and admissible actions. Rejected actions/responses: **0**.
All eight runtime tool actions completed successfully.

**Seven of eight responses contained invalid auxiliary annotations.** Each supplied
one claim with an unsupported free-text `basis` value rather than the declared
`tool`, `predecessor` or `independent` enum. All seven claims and exact diagnostics
were archived and excluded under the unchanged auxiliary policy. The first claim
was structurally accepted; no annotation's semantic truth was certified. A functional
pass does not make these annotation errors disappear.

## Calls and provider charges

| Call | Action | Wire shape | Input/output tokens | Provider charge USD | Annotation |
| --- | --- | --- | --- | --- | --- |
| 1 | List files, limit 100 | Nested args, canonicalized | 600 / 45 | 0.000312 | 1 structurally valid |
| 2 | Read api.py | Flat | 875 / 56 | 0.0004396 | Invalid basis, excluded |
| 3 | Read ledger.py | Flat | 1120 / 55 | 0.000536 | Invalid basis, excluded |
| 4 | Read normalize.py | Flat | 1507 / 56 | 0.0003084 | Invalid basis, excluded |
| 5 | Read check_public.py | Flat | 1839 / 53 | 0.0003212 | Invalid basis, excluded |
| 6 | Read tests.json | Flat | 2175 / 61 | 0.0003532 | Invalid basis, excluded |
| 7 | Write ledger.py | Flat | 2850 / 55 | 0.0006136 | Invalid basis, excluded |
| 8 | python3 check_public.py | Flat | 3315 / 34 | 0.0004204 | Invalid basis, excluded |

Actual provider charge: **$0.0033044**. Conservative noncached ledger accounting:
**$0.0063764**. The difference reflects 10,240 cached input tokens; total usage was
14,281 input and 415 output tokens. Every request settled with known cost, non-BYOK
billing and service-reported OpenAI routing. Held reservations: **$0**. The unused
provider cap of $0.4966956 grants no permission for another attempt.

All response-stage rates use eight actual received model messages. Invalid JSON,
envelope, wire/canonical action and static safety counts were 0/8. Annotation-invalid
responses were 7/8 (87.5%), and annotations supplied/validated/excluded were 8/1/7.
Completed and successful tool counts were 8/8. Missing responses, denied transmissions
and rejected actions were zero. Exact measurements and stage audits remain in the run.

## Preflight and preserved evidence

Current unauthenticated OpenRouter catalog verification preceded execution and
was repeated by the existing launcher. The exact mini/OpenAI mapping, required
parameters and input/cache/output prices were $0.40/$0.10/$1.60 per million.
OpenAI-only routing disabled fallbacks. Twelve full reservations including a possible
5% BYOK contingency totaled $0.20256768, below the new cap.
Sources: [current model pricing](https://openrouter.ai/openai/gpt-4.1-mini/performance),
[BYOK fee policy](https://openrouter.ai/docs/guides/overview/auth/byok).
No paid validation call, credit purchase or model/provider substitution occurred.

Prepared config remained unchanged at canonical SHA256
`a833849a3b6706b17c96ed60e2e3252b89fa57e03418c8720cce8b067e781f61`.
Model, task/system prompts, action contracts, representation and budgets were not
modified. The first request body is identical to the historical v1.2 first request:
the frozen system, original objective and empty handoff only. Generation remained
JSON-object mode with `flat-or-args/1.0` local adaptation. The service reported
`openai/gpt-4.1-mini` through `OpenAI`, without upstream snapshot attestation.

Fresh authorization: `analysis/functional-confirmation12-v1.3-authorization.json`,
copied to this report directory and the raw run. Exclusive guard and new ledger:
`runs/functional-confirmation12-v1.3-pending/`. The directory retains the frozen
prepared name; it is now occupied by this completed real attempt and cannot be reused.
The pending template and all prior authorizations remain unchanged.

Exact command, invoked once after verified preflight:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python scripts/benchmark_record.py --label confirmation12-v1.3-20261011-live-execution -- .cache/swebench-evaluator/venv/bin/python scripts/benchmark_functional_check.py --config configs/functional-confirmation12-v1.3.json --authorization analysis/functional-confirmation12-v1.3-authorization.json --run-dir runs/functional-confirmation12-v1.3-pending --approve-live
```

Command, timing, output and exit 0 are preserved under
`runs/swebench-integration/commands/confirmation12-v1.3-20261011-live-execution/`.
Raw HTTP bodies were archived before JSON/provider/admission processing; original
response text, canonicalization/admission records, annotation diagnostics, calls,
patch, acceptance outputs and cost ledger are retained. No headers were recorded.
Body/adapter/text identities verify, and no credentials appear in the archives.

`verified-outcome.json` confirms all **9,178 protected historical files** and all
**124 frozen implementation/source entries unchanged**, valid old/new seals, zero
held spending and no remaining owned agent containers. The new trajectory contains
59 events, SHA256 `f4ec784f6f1f160ec990c43e6e76a067968577b5426005e37dc956f775a36a30`.
Independent read-only audit agreed with the outcome and accounting. This is one
public fixture confirmation, not benchmark or handoff-effectiveness evidence.
No commit, push, merge or publication occurred. Work stopped after reporting.
