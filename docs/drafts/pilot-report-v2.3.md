# Pilot report — Keisho v2.3, sympy__sympy-20590 (DRAFT)

Launched once on 2026-10-23 at 15:13:30 UTC+5 on Bagnesium-3.local from feat/v2.3-proposal @ e9781a5.
Authorization `bagi-20261023-v23-01` (file sha256 c72e9a30…c3f6; guard authorized-cd228ec0228cc2ccc599eb75, now consumed).
Run dir: runs/swebench-v2.3-five-way-once-001 (result.json sha256 9d074418…ccb8, spending.json sha256 d138bbfb…2b1d).

## Outcome
**Status `checkpoint_not_reached`. No condition ran.** The predecessor (attempt 1 of 3) made 8 model calls and 7 shell tool calls.
- Calls 1–5 and 7 inspected the code (symbol.py, _print_helpers.py, the tests).
- Call 6 edited `sympy/core/_print_helpers.py`, adding `__slots__ = ()` to `Printable`.
- Call 8 tried to add a regression test and run pytest. That test run would have been the checkpoint. The JSON was malformed: `claims` was nested inside `action`, so the top level had no `claims`. The harness rejected it ("response must contain action and claims only"), executed nothing and did not retry. Reason: `model_failure`.
- No premature finish happened, so the v2.3 guard and the attempt rule did not fire (`resampling` false, no premature-finish.json).
- The v2.3 non-empty user turn was sent: messages were [system 5665, user 758, user 132 chars].

## Spend
| | USD |
|---|---|
| Billed (sum of provider costs, 8 calls) | 0.0333914 |
| Ledger accounted (greater-of rule) | 0.079986 |
| Unreconciled reservations | 0 |
| Cap | 10.00 |
Every reservation was 0.189504, at the cache-write input rate. The plan's largest_request_reservation matches.

## Per-condition results
| Condition | Status | Official SWE-bench |
|---|---|---|
| REPOSITORY_ONLY | unstarted | n/a |
| FULL_HISTORY | unstarted | n/a |
| SUMMARY_2K | unstarted | n/a |
| STRUCTURED_NOTES_2K | unstarted | n/a |
| KEISHO_2K | unstarted | n/a |
There are no condition patches to evaluate.

Supplementary (NOT a condition and NOT part of the comparison): the predecessor's terminal patch was graded offline with the official harness, swebench 5.0.2, run id `keisho-v23-supplementary-predecessor-terminal-02`. Result: **resolved** (FAIL_TO_PASS test_immutable passed; 21/21 PASS_TO_PASS passed). The fix was correct, but the predecessor stopped one step before the checkpoint.

## Audit
- Inputs: the predecessor request matched the v2.3 definition (seed 20261007, max_tokens 2048, the frozen prompt, the constant no-handoff user text). The budgets were not approached: 33,873 input and 1,224 output tokens against the 276,000 total.
- Freeze: the manifest, including the 6 local files, verified before launch, and the v2.3 final-source freeze validated. v2.1/v2.2 records are untouched.
- No relaunch was made. The authorization guard is consumed.

## Anomalies
1. **Evaluator dataset bug (latent, would affect any condition grading).** `evaluator.evaluate()` always uses `.cache/swebench-evaluator/selected-task-evaluator.jsonl`, and that file contains **pydata__xarray-6721**, not sympy__sympy-20590. comparison.py's preflight uses the per-task file, but evaluate() doesn't. My first supplementary grading attempt failed with "prediction IDs not found in dataset". Any condition evaluation in this run would have returned `error`. Fixing it needs a v2.4 change to evaluator.py, which is manifest-pinned.
2. **Response-level schema errors are terminal.** One malformed JSON response ends the run immediately. It is not counted as an invalid action under the 3-strike rule. The early-finish guard does not cover this failure mode.
3. Billed cost was well under the ledger figure (0.033 vs 0.080), as expected from the greater-of accounting.
