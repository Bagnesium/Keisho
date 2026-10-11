# 12-call functional confirmation preparation

Implemented the requested measurements and froze one fresh 12-call procedure.
**No new provider request was made.** Live confirmation awaits a new dollar
authorization; all prior scopes are closed. No live ledger/guard was created,
and no SWE-bench run is authorized by this preparation.

Changes: optional pre-decoding HTTP-body observer in
`src/keisho/agents/providers/openai_chat.py`; read-only stage measurements in
`src/keisho/benchmark/response_measurements.py`; explicit config/authorization/run
binding in the existing `scripts/benchmark_functional_check.py`; regression tests
in `tests/test_response_measurements.py`. No new agent loop, production default
mode, Keisho representation, or baseline prompts. The old eight-call entry point
and frozen benchmark configuration stay intact.

Every received body will be archived before provider and local action processing,
including responses rejected for routing, missing usage, refused content, malformed
JSON or invalid arguments. Original body bytes are preserved as base64 except
explicit credential redaction; no authorization headers. This does not establish
what upstream processing occurred. Strict action/path/runtime checks and existing
auxiliary diagnostics are retained, with no repairs or generation retries.

`response-measurements.json` will report invalid counts and rates separately for
JSON syntax, response structure, action schema, auxiliary annotations and safety,
plus action/response rejection, completed and successful tool executions. All
rates divide by actual model messages received. Missing network/HTTP responses,
untransmitted requests and unstarted calls stay separate. Unassessable downstream
fields remain unknown; zero denominators have null rates. Auxiliary-invalid
responses can still contain admissible actions. Neither accepted annotations nor
successful tool calls establish task correctness.

Frozen config `configs/functional-confirmation12-v1.json`, canonical SHA256
`1cb6cab0b171ca0adbb9d6ba4f2e75738e640f88d70690dbff40d6c682a1e76c`;
procedure `protocol_amendments/functional-confirmation12-v1.md`. Retains mini plus
JSON-object mode from B, original system/task, fresh existing public fixture,
all prior token/time/tool limits, and extends only model/tool ceilings from 8 to
12. Success requires source inspection, permitted edit, actual passing model-run
post-edit public test, then independent acceptance with immutable inputs preserved.
Independent acceptance alone is not a confirmation pass.

Current live status: **unstarted**; actual responses 0, transmitted requests 0,
missing responses 0, invalid responses 0 with rate **undefined (0 denominator)**.
No new costs/reservations. Planned worst-case reservation sum $0.20256768 under
recorded mini rates and 5% possible BYOK margin. The existing registered $2
technical ceiling is not user authorization; the live cap must be explicitly
provided and bound to this new attempt. Public pricing and image/credential
availability are rechecked by live preflight, without paid validation calls.

Final-state offline checks: **59 focused / 176 broader tests pass**, exit 0.
Injected responses exercise the real adapter/loop, every action variant, feedback,
annotation exclusions, rejected actions, body capture before failed validation,
missing/refused responses, nonzero tests, immutable raw artifacts, new guard and
spending behavior. These are software tests, not an API-driven success. The first
58-test focused invocation failed because the new temporary input path traversed
macOS's `/var` symlink; the test now resolves it without weakening the input gate.
Its output also exposed HTTPError cleanup, now explicit. Both original failures
and passing invocations are preserved in `runs/swebench-integration/commands/`:
`confirmation12-focused-01`, `confirmation12-focused-final-02`,
`confirmation12-offline-final-01`, `confirmation12-budget-review`, and
`confirmation12-dry-run`.

Successful public dry-run, exit 0, no guard or provider calls:

```sh
python3 scripts/benchmark_functional_check.py --config configs/functional-confirmation12-v1.json --run-dir runs/functional-confirmation12-v1 --dry-run
```

Budget review: saved original benchmark issue/system produce a 4101-input-token
initial upper bound with JSON-object mode. Frozen 48 model/36 tool calls and
180000 cumulative tokens plausibly allow 14–15 calls at moderate 1024-token net
history growth or 10–11 at 2048. These sensitivity assumptions are recorded,
not observed future trajectories. They permit a plausible targeted investigation,
edit and validation, but larger reads/results can bind earlier. No numerical
benchmark increase is justified now; 48 must not be reported as guaranteed.
Before any future SWE-bench run, freeze and validate any required mode/budget
amendment and dollar/context plan. Use one identical successor model/output mode
across all conditions, with no baseline/memory changes.

Historical preservation checks and final source hashes are in `final-verification.json`.
No old response, grade, guard, ledger, or configuration was rewritten or reused.
No commit/push/merge/publication occurred.
