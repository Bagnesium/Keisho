# One authorized 12-call functional confirmation

**Infrastructure interruption after one response and one tool action.** The new
attempt did not complete the success rule. No retry, extra functional attempt,
SWE-bench or handoff comparison occurred. The exclusive guard and ledger are closed.

The model proposed `list_files`, and the tool returned the six-file inventory.
After that completed result, `PublicAcceptanceBoundary12` attempted
`from scripts.agent_decision_diagnostic import information_action` at
`scripts/benchmark_functional_check.py:122`. Public script startup adds `src` to
the module path at line 16, but not the project root needed for the `scripts`
namespace. The recorded exception is `ModuleNotFoundError: No module named 'scripts'`.
The earlier offline tests imported through the project root, and the actual CLI
dry-run never reached this callback. That coverage gap let this launcher defect
through. The previous 59 focused/176 broader passing tests remain historical
software results; they did not establish live operability.

An isolated offline reconstruction of the script's module paths reproduces the
exact exception using only the saved action/result in the callback. It executes
no repository tool and makes no provider request. This is diagnostic reproduction,
not original traceback telemetry or agent continuation. Implementation was left
unchanged after this outcome; no guard was reset or attempt resumed elsewhere.

There was no second request. This one initial inventory action is insufficient
to assess repetition, model investigation quality, or the effect of output mode.
No relevant source contents were inspected, no source edit was observed, and no
model test or independent final acceptance occurred. The initial controller public
test failed two of four cases as designed. Final acceptance and cumulative patch
artifacts were not produced because the callback interrupted execution; they
must not be represented as passing or as measured task failures.

The only model response was archived at the HTTP-body boundary before JSON
decoding, provider validation, spending settlement or action parsing:
`runs/functional-confirmation12-v1/wire-response-001.json`. Credential redaction
was not needed for that body; no headers were saved. Its message content matches
the adapter/parser input, and its action matches the actual recorded tool call.
No local replacement, repair or generation retry occurred. These are service
response bytes, not an attestation of untouched upstream processing.

Configured canonical model: `openai/gpt-4.1-mini-2025-04-14`; requested and returned
service identifier: `openai/gpt-4.1-mini`. The service reported upstream `OpenAI`
through OpenRouter, without snapshot attestation/fingerprint. Output format was
`json_object`, plugins `[]`, transforms absent, seed 20261007, temperature 0,
2048 maximum output, OpenAI-only routing without fallback. The three-message
initial context contains only the frozen system, original fixture objective and
empty framing—no old response, patch, probe action or development conversation.

All rates below use **one actual model response received**, not the twelve-call
ceiling. Missing responses: **0**; eleven call slots remained unstarted, not
missing or invalid responses.

| Measure | Count / actual responses | Rate |
| --- | --- | --- |
| Invalid JSON syntax | 0 / 1 | 0% |
| Invalid response structure/ambiguity | 0 / 1 | 0% |
| Invalid action schema | 0 / 1 | 0% |
| Invalid auxiliary annotation contract | 0 / 1 | 0% |
| Invalid static safety admission | 0 / 1 | 0% |
| Responses with any invalid component | 0 / 1 | 0% |
| Rejected action proposals | 0 / 1 | 0% |
| Successful tool executions | 1 / 1 | 100% |

The successful tool was an inventory listing, not task completion. One annotation
was supplied and contract-accepted; none were excluded and no unsupported reference
was supplied. It used `VERIFIED`, `basis: tool`, and empty evidence IDs before
any tool evidence existed. Structural acceptance does not verify that annotation's
meaning or justification; semantic truth remains unknown. No Keisho state/handoff
was constructed. Exact response and annotation reasons/coverage are preserved.

New authorization: `results/functional-confirmation12-live/authorization.json`,
one attempt, **$0.50** cap, no benchmark permission. Config
`configs/functional-confirmation12-v1.json` remains disabled and unchanged,
canonical SHA256 `1cb6cab0b171ca0adbb9d6ba4f2e75738e640f88d70690dbff40d6c682a1e76c`.
Procedure remains `protocol_amendments/functional-confirmation12-v1.md`.

Docker was stopped, so the installed app was opened and its daemon became
available. The existing immutable amd64 image was reused on Apple Silicon; no
build/download, paid hosting or security change. Current unauthenticated catalog
metadata confirmed the frozen mapping/support/pricing before inference; credentials
were checked by presence only. The worst-case twelve full reservations were
$0.20256768, within the new cap. No paid smoke or credential-validation request.

Actual usage: **1 call, 497 input / 51 output tokens**. Provider-reported charge
and conservative accounting both **$0.0002804**. Outstanding reservations **$0**;
all requests settled, no charged generation failure. The unused $0.4997196 does
not authorize a restart; the one-attempt scope is closed.

Authorized dry-run exited 0 without creating the guard. Exact live command:

```sh
python3 scripts/benchmark_functional_check.py --config configs/functional-confirmation12-v1.json --authorization results/functional-confirmation12-live/authorization.json --run-dir runs/functional-confirmation12-v1 --approve-live
```

Live exit **1**, recorded with command/timing/output under
`runs/swebench-integration/commands/confirmation12-live-execution/`.
Other exact records: `confirmation12-docker-start`, `confirmation12-authorized-dry-run`,
`confirmation12-live-preflight`, `confirmation12-import-failure-reproduction`, and
`confirmation12-live-postrun-verification`. The last two offline checks exited 0,
with no inference or tool-action replay. Post-run verification confirms raw/body/
action identity, all old/new seals, all **4,938 protected historical files** unchanged,
tested source unchanged, no remaining agent containers, and zero held spending.
`verified-outcome.json` contains the derived evidence; original run artifacts were
never rewritten. Progress updated. No commit, push, merge or publication.
