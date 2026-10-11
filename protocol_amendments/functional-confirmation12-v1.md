# Prospective 12-call confirmation and response measurements

Frozen 2026-10-09, before any new inference. This setup-only procedure does not
authorize SWE-bench or reopen the completed four-probe/eight-call diagnostic.

Configuration: `configs/functional-confirmation12-v1.json`, canonical SHA256
`1cb6cab0b171ca0adbb9d6ba4f2e75738e640f88d70690dbff40d6c682a1e76c`.
The existing public fixture and objective/system text stay unchanged. Use mini
`openai/gpt-4.1-mini-2025-04-14` requested as `openai/gpt-4.1-mini` via OpenRouter,
OpenAI-only routing, and JSON-object mode, the previously preferred cell B.
No prior response, probe decision, patch or development context enters the new run.

One fresh attempt has at most 12 model and 12 tool calls, 2048 output per call,
32000 request input, 128000 context, 180000 cumulative tokens, 600 seconds,
120-second tools and 49152-byte tool output. Only the call ceilings increase
from the completed eight-call setup check; no other decoding or token budgets
change. No automatic retry or malformed-action recovery is added.

Success (`public-acceptance-boundary/2.0`) requires actual source inspection,
permitted source edits, a subsequent direct `python[3] [-B] check_public.py`
request whose completed result exits 0 and contains the public acceptance marker,
then independent controller acceptance, unchanged acceptance inputs, and no
unpermitted changes. Stop at the first completed post-edit public test, pass or
fail. An independent pass without the model's post-edit test remains incomplete.
The old eight-call result and old boundary remain historical and unchanged.

`response-measurements/1.0` archives HTTP body bytes before JSON decoding,
provider identity/routing/usage checks, local action parsing, and spending
settlement. Bodies are stored as base64, losslessly except explicit API credential
redaction. Authorization headers and other headers are never archived. Captured
service bodies do not attest untouched upstream processing. HTTP error bodies
are retained as well; a network error may have no response body.

Measure JSON syntax, top-level structure/ambiguity, declared action schema,
auxiliary annotation contract, and runtime admission separately. Duplicate keys
are grammatically JSON but ambiguous and rejected. Unsupported annotations are
retained with exact reasons, excluded, and remain unknown; structural acceptance
is not truth. Actions are never silently changed. The unchanged local parser and
runtime validator remain the admission authorities; diagnostics do not grant
execution. Invalid generation/action or unknown accounting stops the attempt.

For each measure report counts, rates, and unassessable counts. Every rate uses
actual model responses received as denominator. Refusal/null-content messages
are responses received; HTTP/network errors without a model message are missing
responses, not invalid model JSON. Planned/unstarted calls and denied transmissions
are separate. Zero-denominator rates are null. Rejected action proposals may be
independently schema-valid but withheld by envelope/provider/safety admission.
Completed shell commands with nonzero exit are executions, not successful tools.
`finish` is not a tool execution. Annotation failure does not itself reject actions.

A fresh authorization must bind the configuration, one fixed output directory,
one attempt and an explicit new dollar cap. All previous scopes remain closed.
Reuse the existing diagnostic spending ledger implementation with its registered
$2 technical ceiling; this ceiling is not an authorization. The actual cap comes
from the new user authorization. All 12 full request reservations total
$0.20256768 under recorded mini $0.40/$1.60 per-million rates plus possible 5%
BYOK margin, without cache savings. Recheck public pricing/catalog, credentials
by presence only, image identity and the gate before live execution. Any unknown
cost retains reservation and stops. Atomic RawRun creation prevents duplicate
admission. Dry-run never creates that guard or requests inference.

Benchmark budget review is recorded in
`results/functional-confirmation12-preparation/budget-review.json`. Initial issue
and system reserve 4101 input tokens under JSON-object mode. At net history growth
1024 tokens per turn, the frozen 180000 total supports about 14–15 calls; at 2048,
10–11, under the stated assumptions. The nominal 48 calls is only a ceiling.
This plausibly permits targeted investigation, source editing and validation,
without guaranteeing it. No numerical benchmark amendment is justified solely
by listing loops or a tiny fixture; original configurations stay unchanged.

Before any future benchmark inference, freeze any necessary mode/budget amendment
and matched plan prospectively, preserving the old specification. All five
successors must use the same frozen model/routing/output mode, tools and budgets;
do not tune conditions individually. This does not require identical predecessor
and successor models. Recheck FULL_HISTORY context fit and the shared cost envelope.
Keisho memory and all baseline generation/successor prompt text remain unchanged.
