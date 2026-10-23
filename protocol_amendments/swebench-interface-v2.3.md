# SWE-bench interface amendment v2.3 — PROPOSAL (live execution NOT authorized)

Status: PROPOSAL. `live_execution_authorized: false`. No v2.3 authorization exists; the
template carries `PENDING-V23-NEW-USER-AUTHORIZATION`. Supersedes v2.2 on this branch only;
v2.1/v2.2 frozen records and raw runs are unchanged.

## 1. Diagnosis of the v2.2 predecessor early finish (sympy__sympy-20590, gpt-6-sol)

Evidence (from the v2.2 run dir and v2.0 raw records, read-only):
- E1. Call 1 returned `finish` with 0 tool calls and the prose "Unable to investigate or modify
  the repository in this run."; empty patch; status `checkpoint_not_reached`; cost USD 0.0036115.
- E2. The request messages were byte-identical to v2.0 call 1 (same system prompt v5, task text,
  seed 20261007, reasoning none, max_tokens 2048, json_object). v2.0 answered with prose + a shell
  action instead. Same input, different output: the seed does not make this endpoint deterministic
  (`system_fingerprint` null).
- E3. Messages are [system 5665 chars, user 758 chars, user 0 chars]. The trailing empty user
  message (NO_CONTEXT "invariant framing") has been present since v1.4. v1.5–v1.9 runs acted
  normally with it.
- E4. The system prompt has no "cannot access" wording. It lists `finish` among the tools, and
  nothing forbids calling it on turn 1. The harness accepts a turn-1 zero-tool finish as a
  normal ending.
- E5. Usage: cached 0, cache_write 1315. Billed = 1315×2.5e-6 + 7×2e-6 + 31×1e-5, so the provider
  charged the cache-WRITE rate (2.5e-6), which is above the 2.0e-6 the v2.2 plan assumed. v2.0
  call 1 had the same pattern.
- E6. Under sol prompt v5 on this task, 0 of 2 first calls were valid actions (v2.0 framing
  failure, v2.2 premature finish).

Hypotheses (not established):
- H1. The empty trailing user turn reads as "nothing to do / no access" and contributes to the
  finish. It is not sufficient on its own (E3).
- H2. Offering `finish` with no precondition makes a zero-work exit an available low-effort reply.
- H3. The first-call early-finish rate is non-trivial (unknown; n=1 observed).

## 2. Changes (all in src/keisho/benchmark/comparison.py; agent.py untouched because it is manifest-pinned)
1. Non-empty constant user turn (`empty_handoff_user_text`) replaces '' for the predecessor and
   for the REPOSITORY_ONLY successor. The text is constant across conditions that previously got ''.
   Disclosed side effect: the recorder logs it as a `*_handoff` event.
2. Early-finish guard `premature-finish-guard/1.0`: post hoc classification only. A predecessor
   `finished` with 0 tool calls is invalid. It is never fed back to the model (no in-conversation
   retry). `premature-finish.json` is written and no handoff is built from it.
3. Pre-registered attempts: `predecessor_attempts.max_attempts` = 3, same seed. A new attempt
   (fresh session, `predecessor-attempt-NN`) happens ONLY after a first-call (model_calls == 1)
   zero-tool finish and only while the ledger is not stopped. A zero-tool finish after rejected
   actions, or any other terminal state, ends the run. A valid attempt = ≥1 completed tool call.
   All attempts are disclosed in result.json and the report.
4. v2.3 final-source freeze (`analysis/swebench-v2.3-final-source-freeze.json`) pins the binding
   modules. Because comparison.py changed, a v2.2 launch from this branch now refuses (fail
   closed). This is intended supersession.

## 3. Envelope (cache-write input pricing, fee 1.05)
predecessor 1.498644; successor 8.232210 (successor total_tokens lowered 248400→234000 to fit);
note_generation 0.018480; invalid predecessor attempts (2 × first-request bound 2444 in /
2048 out) 0.055839. Total 9.805173 + reservation 0.189504 = 9.994677 ≤ 10.00.
Finding: the v2.2 envelope does not fit $10 if cache-write rates apply.

## 4. Open decisions (Bagi)
N attempts (1–3); same vs varied seed; apply the user turn to REPOSITORY_ONLY or not; lower the
successor budget vs raise the cap; price reservations at the cache-write rate in the ledger;
whether to fund an early-finish rate estimate (N cheap first calls, ~$0.004 each observed,
≤ $0.028 each bound; N=20 ≈ $0.08 observed / ≤ $0.56 worst case). NOT run.
