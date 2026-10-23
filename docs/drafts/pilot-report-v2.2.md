# Keisho v2.2 pilot report (DRAFT)

Single task (SWE-bench Verified `sympy__sympy-20590`), single run, single attempt. No general or causal claims.

## Run identity
- Code: `review/v2.2-proposal` @ 1b0ba10 (final source freeze r2, d87b3d13…2aa6)
- Config e4afa4d3…ed8a · plan 35979af0…0346 · manifest 3658f6c1…7ee1
- Authorization `bagi-v22-sympy-20590-20261023-02` (launcher digest 7a77a6c4…062d), cap USD 10.00, 1 attempt
- Pre-launch gate: full suite 320 tests, 8 failures / 23 errors (= Mac baseline), no `claim_launch` errors
- Launched 2026-10-23 14:46:35 (UTC+5); exited within 90 s. Run dir `runs/swebench-v2.2-five-way-once-001`
- Earlier attempt at 14:36 with authorization -01 crashed with `NameError: claim_launch` before claim or any model call ($0); see protocol amendment, freeze revision 2.

## Outcome
`result.json` status: **`checkpoint_not_reached`**.

The predecessor (`openai/gpt-6-sol`) made 1 model call (1,322 input / 31 output tokens, 2.46 s) and its very first
action was `finish` with answer "Unable to investigate or modify the repository in this run.", 0 tool calls, empty patch
(sha256 of empty string). `checkpoint.json`: `eligible: false, reason: finished`. Per protocol no handoff was produced,
so none of the five successor conditions started.

| Condition | Status | Successor input | Patch | Official evaluation |
|---|---|---|---|---|
| REPOSITORY_ONLY | unstarted | none | none | not applicable |
| FULL_HISTORY | unstarted | none | none | not applicable |
| SUMMARY_2K | unstarted | none | none | not applicable |
| STRUCTURED_NOTES_2K | unstarted | none | none | not applicable |
| KEISHO_2K | unstarted | none | none | not applicable |
| (predecessor terminal) | finished, no edits | — | empty | not run: empty patch, trivially unresolved |

## Spend (vs USD 10.00 cap)
- Provider-reported (OpenRouter `usage.cost`, upstream OpenAI): **USD 0.0036115**
- Ledger (`spending.json`, noncached accounted): **USD 0.0036115**; unreconciled reservations 0.000000; 1 attempt, settled
- Note generation: USD 0. Total ≈ 0.04 % of cap.

## Input audit
- Successor inputs: none exist (no condition started), so condition-definition and 2K token-budget checks could not be performed.
- Predecessor request: messages byte-identical to the v2.0 run's first request
  (`runs/swebench-v2.0-five-way-once-001`), same seed 20261007, `reasoning.effort: none`, same routing. v2.0 started
  with a shell investigation; this run finished immediately. Same input, different output.
- Request contains a trailing empty user message (len 0). This is long-standing frozen behavior (present in v1.4–v2.0 runs), not new in v2.2.
- Response reports `cache_write_tokens: 1315`, `cached_tokens: 0`; the ledger assumes no cache discount (conservative).

## Anomalies / limitations
- One run, one task: the early finish is one sample and says nothing about the frequency of this behavior or about the conditions.
- The v2.2 structured-notes reader was never exercised live (no note generation happened).
- The authorization -02 is consumed (guard `authorized-489eee8b…` exists); any further run needs a new authorization and approval.

## Raw records
Unmodified under `runs/swebench-v2.2-five-way-once-001/` (result.json, spending.json, predecessor/*).
