# Keisho Research Status & Closeout Assessment — 2026-10-27

## Executive Summary & Core Conclusion

**Comparative efficacy remains untested/inconclusive.**

Across twelve historical live execution attempts on SWE-bench Verified (v1.4 through v2.5), **zero** complete five-way comparisons have finished. In all twelve attempts, all thirty-five successor condition branches (`REPOSITORY_ONLY`, `FULL_HISTORY`, `SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`) remained completely **unstarted** and **ungraded**. 

No experimental result supports either a claim that Keisho outperforms alternative handoff formats or a claim of a confirmed negative result. Software interfaces, container isolation, and model dispatch mechanisms have been repaired and verified offline, but the primary comparative empirical hypothesis remains entirely unmeasured.

---

## 1. Actual Current State & Codebase Provenance

- **Git Branch**: `feat/v2.5-repair` (clean working tree, up to date with `origin/feat/v2.5-repair`).
- **Last Five Commits**:
  1. `2939dca` — `test(v2.6): add regression test for startup KeyError and fail-closed constructor verification`
  2. `b4ded81` — `chore(v2.6): add prospective freeze artifacts, manifest, and authorization template`
  3. `f0a6bae` — `fix(v2.6): repair OpenRouter model constructor version dispatch and expose model factory`
  4. `57dfabe` — `docs(v2.6): add protocol amendment for attempt 001 startup crash and prospective repair`
  5. `79e7731` — `record(v2.5): record consumed one-attempt authorization bagi-20261024-v25-01`
- **Relationship to Repair Commit `8bd3455`**:
  Commit `8bd3455` (`fix(v2.6): prospective repair for OpenRouter model constructor version dispatch`) was originally committed on 2026-10-25 as a monolithic commit containing the full v2.6 implementation. It was subsequently reset back to `be13fce` and decomposed into the five atomic commits listed above (`79e7731` through `2939dca`). The working tree at HEAD (`2939dca`) is byte-for-byte identical to `8bd3455` (`git diff 8bd3455 HEAD` is completely empty).
- **Latest Prospective Specification (v2.6)**:
  - Configuration: `configs/swebench-comparison-v2.6.json` (canonical digest `723403df9145eb28ace3df34ba63133f8b768b966ab282274ab574cff5a099ef`)
  - Plan: `analysis/swebench-comparison-v2.6-plan.json` (canonical digest `c268053c0458116daca100cdc125282538b3faab48073db565fc0dea70a238c3`)
  - Manifest: `analysis/swebench-experiment-v2.6-manifest.json` (canonical digest `0e547275fcc4d80287b10ae3d4f38d2225a6d004d78b850fd8286fd97b837fc6`)
  - Source Freeze: `analysis/swebench-v2.6-final-source-freeze.json` (canonical digest `25e838a1bd1f33c1cff8c97cd8eaf2e27b99c4ef796451eab111083845aa05ae`)
  - Authorization Template: `analysis/swebench-comparison-v2.6-authorization-template.json` (`authorization_id: PROSPECTIVE-V26-TEMPLATE-NOT-APPROVED`, `provider_inference_authorized: false`)
- **Binding Status & Freeze Compatibility**:
  - A higher version number alone does not constitute a valid binding. The v2.6 binding is currently **INVALID for live execution** because there is no approved authorization record (`provider_inference_authorized: false`, `live_execution_authorized: false`).
  - Source module hashes in `analysis/swebench-v2.6-final-source-freeze.json` match current files exactly:
    - `scripts/benchmark_compare.py`: `86e3920ab5dca82a2177b2e85f4a3018f09e230e25758ed60b6d3458310101b4`
    - `src/keisho/benchmark/comparison.py`: `4c571d17bd30f4e4a5417ea8c31d621d2ba37997a4429568edebe8f970f15ee4`
    - `src/keisho/benchmark/experiment_freeze.py`: `704cdcb4b4a0959cb150745012dd78b42700d4eeb9e6a64069c1e9883d1c130a`
    - `src/keisho/benchmark/notes_reader.py`: `0de635927c595b7a6a21a31020c402becb35bebaadad6f56ffbc6f6e9aa53d44`
    - `src/keisho/benchmark/response_measurements.py`: `416b931ce046ab9f959343b15fef5fb9ee79951c96f3f66e5b72f1e2a0c2e738`
  - Incompatible Historical Freeze: The repaired source `src/keisho/benchmark/comparison.py` has SHA `4c571d17...`, whereas historical v2.5 expected `f5f9f778...`. Running repaired source under v2.5's freeze fails closed immediately (`pinned binding module changed: src/keisho/benchmark/comparison.py`). Repaired source must never be run under historical freezes.

---

## 2. Research Question, Conditions, Evaluation & Stopping Rules

- **Research Question**: Does a compact, deterministically selected record of observable work, item provenance, and named-file revalidation flags (`KEISHO_2K`) improve successor continuation on an unfinished coding task compared to ordinary summaries (`SUMMARY_2K`), structured notes (`STRUCTURED_NOTES_2K`), full history (`FULL_HISTORY`), or repository only (`REPOSITORY_ONLY`)?
- **Task & Sampling**: Single exploratory task `sympy__sympy-20590` (SWE-bench Verified revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`, base commit `cffd4e0f86fefd4802349a9f9b19ed70934ea354`, image `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590@sha256:8945b0b70f8c3a5c17bf57d4eee2166ad813e0f369f9cad35f8345bf79705deb`).
- **Models**:
  - Predecessor and Successors: `openai/gpt-6-sol-20260922` (OpenRouter alias `openai/gpt-6-sol`, reasoning effort `none`).
  - Note Generators: `openai/gpt-6-luna-20260922` (OpenRouter alias `openai/gpt-6-luna`, reasoning effort `none`).
- **Five Conditions**:
  1. `REPOSITORY_ONLY`: issue + workspace only; invariant empty framing message.
  2. `FULL_HISTORY`: complete permitted observable predecessor history (up to request input token limit; rejected if exceeding bound, never truncated).
  3. `SUMMARY_2K`: model-generated unstructured summary (≤2,048 native tokens).
  4. `STRUCTURED_NOTES_2K`: model-generated 7-field schema + deterministic continuation facts (≤2,048 native tokens).
  5. `KEISHO_2K`: Keisho compiler output of observable state items, provenance, and revalidation flags (≤2,048 native tokens).
- **Primary Evaluation Criterion**: Pinned official SWE-bench Verified grading (`resolved` vs `unresolved`) comparing paired `KEISHO_2K` vs `STRUCTURED_NOTES_2K` on unresolved checkpoints.
- **Stopping Rules**:
  - Predecessor stops on: total tokens (276,000), request input tokens (64,000), model calls (48), tool calls (36), timeout (1,800s), 3 consecutive tool failures, premature finish (under v2.3+ early finish guard), or reaching checkpoint (`first completed validation/build/lint/test command result following a non-test source edit`).
  - Experiment halting: If the predecessor fails to reach the checkpoint within registered attempts (up to 3 under v2.3+ if initial attempts terminate on call 1 with 0 tools), the run stops immediately; successors remain unstarted. If note generation fails, the run stops immediately without retry.
  - Spending Cap: Hard cap of $10.00. Any unreconciled reservation or unknown cost halts execution immediately.

---

## 3. Separation of Completed Results, Partial Runs, Mocked Tests, and Demos

### A. Completed Comparisons
- **None (0/5 conditions run across all versions)**. No comparative efficacy data exists.

### B. Live Run History & Financial Accounting
Across all 12 live attempts on SWE-bench:
- **Recorded Actual Provider Spend**: **$1.083247** (where recorded; 1 call in v2.4-001 unknown).
- **Conservative Accounted Spend**: **$2.678917**.
- **Unreconciled Reservations**: **$0.009240** (v2.4-001).

| Run Label | Version | Actual Spend (USD) | Accounted Spend (USD) | Predecessor Status | Reason / Point of Failure | Successors |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `runs/swebench-v1.4-five-way-once-001` | v1.4 | $0.016418 | $0.025750 | Halted (Call 6) | `budget_exhausted` (uncompressed Zarr metadata overflow) | 0/5 unstarted |
| `runs/swebench-v1.5-five-way-once-001` | v1.5 | $0.112910 | $0.334094 | Halted (Call 13) | `budget_exhausted` (166k/180k tokens before source edit) | 0/5 unstarted |
| `runs/swebench-v1.6-five-way-once-001` | v1.6 | $0.126926 | $0.410318 | Halted (Call 14) | `stopped_on_error` (request exceeded token bounds) | 0/5 unstarted |
| `runs/swebench-v1.7-five-way-once-001` | v1.7 | $0.034192 | $0.093328 | Halted (Call 8) | `invalid_run` (cat failed on missing `sympy/core/atomic.py`) | 0/5 unstarted |
| `runs/swebench-v1.8-five-way-once-001` | v1.8 | $0.269442 | $0.777666 | Halted (Call 22) | `budget_exhausted` (400k tokens without source edit) | 0/5 unstarted |
| `runs/swebench-v1.9-five-way-once-001` | v1.9 | $0.324930 | $0.739650 | Halted (Call 29) | `finished` without source edit (`checkpoint_not_reached`) | 0/5 unstarted |
| `runs/swebench-v2.0-five-way-once-001` | v2.0 | $0.004482 | $0.004482 | Halted (Call 1) | `model_failure` (GPT-6 conversational prose preceding JSON) | 0/5 unstarted |
| `runs/swebench-v2.2-five-way-once-001` | v2.2 | $0.003612 | $0.003612 | Halted (Call 1) | `finished` immediately (`checkpoint_not_reached`) | 0/5 unstarted |
| `runs/swebench-v2.3-five-way-once-001` | v2.3 | $0.033391 | $0.079986 | Halted (Call 8) | `model_failure` (7 tools executed; `checkpoint_not_reached`) | 0/5 unstarted |
| `runs/swebench-v2.4-five-way-once-001` | v2.4 | $0.124156* | $0.133396 | Checkpoint (Call 9) | Note generation failed (`ValidationError: note generation failed; no retry` at Call 10) | 0/5 unstarted |
| `runs/swebench-v2.4-five-way-once-002` | v2.4 | $0.032788 | $0.076838 | Checkpoint (Call 7) | Post-execution measurement failed (`AttributeError: 'NoneType' object has no attribute 'get'`) | 0/5 unstarted |
| `runs/swebench-v2.5-five-way-once-001` | v2.5 | $0.000000 | $0.000000 | Halted (Call 0) | Startup crash (`KeyError: 'openai/gpt-6-sol-20260922'`) | 0/5 unstarted |

*\* Note: In `runs/swebench-v2.4-five-way-once-001`, actual costs are recorded for Calls 1–9 ($0.124156). Call 10 failed at the provider interface with `provider_cost_usd: null` and holds an unreconciled reservation of $0.009240. Its actual charge is marked **unknown**.*

### C. Mocked & Synthetic Offline Tests
- `PublicFiveWayTests` (`tests/test_benchmark_real_offline.py`): Real Docker tool execution using synthetic model decisions and synthetic branch grades. Proves container isolation and file management. Exercises software fixtures, not real-model performance.
- `NetworkDisabledIntegrationTests` (`tests/test_v25_repair.py`): End-to-end integration test with mocked model responses and mock session. Exercises predecessor checkpoint, patch export, `make_handoffs`, and successor input initialization.
- `EvaluatorDataset` (`tests/test_v24_fixes.py`): Pinned task-specific row validation and evaluation bridge tests using a mock shell-script stub for `swebench`.
- `TestV26StartupDispatchRepair` (`tests/test_v26_repair.py`): Verifies version dispatch, model factory, catalog preflight, and binding validation under strict fail-closed network traps.

### D. Manual Website / Local Dogfood Demos
- `runs/local-dogfood-v2-complete`: Manual, offline developer verification of `./keisho pack`, `inspect`, and `resume` commands on an internal feature addition. Zero model inference, zero provider costs. Distinct from benchmark evaluation.

---

## 4. Execution Path Verification (Offline Tests)

1. **Production Startup**: Verified offline (`tests/test_v26_repair.py`). The unpatched dispatch KeyError is reproduced and fixed. `select_model_class` and `build_model` correctly instantiate `V20OpenRouterChatModel` for v2.0–v2.6 across predecessor, note generators, and all 5 successor branches.
2. **Predecessor Checkpoint**: State transition and checkpoint predicate logic verified offline (`tests/test_v25_repair.py`). Real-model compliance in reaching the checkpoint remains low (2 of 11 live attempts).
3. **Generated-Note Conditions**: Compilation logic verified offline (`tests/test_notes_reader_v22.py`). Real-model schema generation remains unverified (failed with `ValidationError` in live attempt v2.4-001).
4. **All Five Successor Branches**: Branch initialization, container isolation, and context separation verified offline (`tests/test_benchmark_real_offline.py`, `tests/test_v25_repair.py`). Real-model successor performance has never executed.
5. **Official Pinned Grading**: Verified bridge logic (`tests/test_v24_fixes.py`). Task Docker image `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest` (ID `8945b0b70f8c`) is present locally. Pinned gold setup smoke check (`runs/swebench-integration/commands/smoke-gold-01/result.json`) is resolved and archived. Official grading of successor predictions has never been reached.

---

## 5. Shortest Concrete Route to Experiment Completion

### A. Evidence-Supported Blockers
1. **No Valid Spending Authorization**: There is no approved authorization record for v2.6. `analysis/swebench-comparison-v2.6-authorization-template.json` is explicitly marked `provider_inference_authorized: false` and `authorization_id: PROSPECTIVE-V26-TEMPLATE-NOT-APPROVED`.
2. **Configuration Locked**: `configs/swebench-comparison-v2.6.json` has `live_execution_authorized: false`.
3. **Previous Authorizations Consumed**: `bagi-20261024-v25-01` was consumed by failed attempt v2.5-001 and is bound to superseded source code.
4. **Unverified Model Interfaces**: Scripted provider tests do not guarantee that real models will output valid JSON actions, reach the checkpoint, or satisfy the structured note schema without error.

### B. Applicable Cost Bounds
- **Applicable Plan**: `analysis/swebench-comparison-v2.6-plan.json`
- **Authorized Spending Cap**: $10.00
- **Total Conservative Envelope**: **$9.80517300**
  - Predecessor: $1.49864400 (276,000 tokens)
  - Successors (5 branches): $8.23221000 (234,000 tokens each)
  - Note Generation: $0.01848000 (2 calls, 64k token allowance)
  - Invalid Predecessor Attempts: $0.05583900 (up to 2 extra first-call attempts)
- **Largest Single-Request Reservation**: **$0.18950400**
- **Peak In-Flight Worst-Case Reservation**: **$9.99467700** ($0.005323 safety margin under $10.00).

### C. Exact Commands Involved

- **Safe Offline Dry-Run** (Verifies binding and catalog preflight without inference or guard creation):
  ```sh
  .cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
    --config configs/swebench-comparison-v2.6.json \
    --plan analysis/swebench-comparison-v2.6-plan.json \
    --authorization analysis/swebench-comparison-v2.6-authorization-template.json \
    --run-dir runs/swebench-v2.6-dryrun \
    --dry-run
  ```
  *(Verified: exits 0, reports `live_start_admitted: false`, creates no guards, makes 0 requests).*

- **Safe Live Launch Command**:
  There is currently **NO SAFE LAUNCH COMMAND**. Any live launch attempt with the prospective template fails closed immediately (`new paid scope is not authorized`). 
  
  If and only if the user explicitly authorizes a fresh paid scope binding the v2.6 source freeze:
  ```sh
  .cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
    --config configs/swebench-comparison-v2.6.json \
    --plan analysis/swebench-comparison-v2.6-plan.json \
    --authorization analysis/<FRESH_APPROVED_AUTHORIZATION>.json \
    --run-dir runs/swebench-v2.6-five-way-once-001 \
    --approve-live
  ```

---

## 6. Reproducibility & Research Decision

No new benchmark or prospective version (v2.7+) should be proposed merely to simulate progress. The research infrastructure and offline pipeline are complete and verified. Until a user authorizes a fresh paid execution under v2.6, the honest scientific status of the research is that **comparative efficacy remains untested/inconclusive**.


---

## 7. Final Rehearsal & Current Session Status — 2026-10-27

### A. End-to-End Rehearsal Execution & Results
The continuous offline rehearsal for prospective v2.6 (`tests/test_benchmark_v26_rehearsal.py` via `tests/run_offline_rehearsal_v26.py` and `scripts/benchmark_compare.py`) was executed and passed with exit code 0 (`runs/offline-rehearsal-v26-ce748a82a10a`):
1. **Predecessor Checkpoint**: Reached checkpoint on `sympy__sympy-20590` (`rule: after_first_validation_result`, exit code 0). Checkpoint officially evaluated in Docker via SWE-bench harness (`status: unresolved`).
2. **Note Generation**: Generated unstructured `SUMMARY_2K` and schema-compliant `STRUCTURED_NOTES_2K` within token ceiling (≤2,048 tokens). Trajectory SHA-256 provenance verified.
3. **All Five Successor Conditions**: Executed in exact pinned plan sequence:
   `FULL_HISTORY` -> `SUMMARY_2K` -> `REPOSITORY_ONLY` -> `KEISHO_2K` -> `STRUCTURED_NOTES_2K`.
4. **Official SWE-bench Evaluation**: All five successor branch predictions were graded using the **actual official SWE-bench evaluation harness** inside Docker containers (`sweb.eval.x86_64.sympy_1776_sympy-20590`):
   - `FULL_HISTORY`: `unresolved` (exit 0)
   - `SUMMARY_2K`: `unresolved` (exit 0)
   - `REPOSITORY_ONLY`: `unresolved` (exit 0)
   - `KEISHO_2K`: `resolved` (exit 0; repair patch verified by official test suite)
   - `STRUCTURED_NOTES_2K`: `unresolved` (exit 0)
5. **Network Traps & Financial Ledger**: Injected socket-level fail-closed traps blocked all external non-UNIX traffic. Provider requests: exactly 0. Provider charges: exactly $0.00.
6. **Artifact Distinction**: All rehearsal outputs are explicitly tagged with `synthetic_engineering_check: true` and `evidence_type: offline_integration_rehearsal` to prevent confusion with empirical model efficacy findings.

### B. Accurate Historical Spend Reconciliation
Audited from primary artifacts across all 12 live five-way comparison attempts:
- Recorded actual provider-billed spend: **$1.0054550**
- Conservative ledger-accounted spend: **$2.6791186**
- Unreconciled reservations: **$0.00924000** (Call 10 in v2.4-001; actual charge unknown)
- Completed five-way comparisons: **0** (0/35 successor branches started)

### C. Prepared Artifacts
- Manuscript: `paper/INCOMPLETE_MANUSCRIPT_20261027.md`
- Progress Record: `BENCHMARK_PROGRESS.md` (appended reconciliation)
- Rehearsal Drivers: `tests/run_offline_rehearsal_v26.py`, `tests/test_benchmark_v26_rehearsal.py`, `tests/offline_launch/rehearsal_v26_injection.py`


---

## 8. Completed Live Five-Way Comparison: Attempt v2.6-001 (`runs/swebench-v2.6-five-way-once-001`)

Following user approval in this continuous session, attempt `swebench-v2.6-five-way-once-001` executed to 100% completion across all five successor branches under authorization `bagi-20261027-v26-01`.

### A. Execution & Outcome Summary
- **Overall Status**: **`complete`** (Predecessor reached checkpoint; note generators succeeded; all 5 successors completed and graded).
- **Predecessor**: Reached checkpoint at Call 9 after editing `sympy/core/_print_helpers.py` and running `pytest`.
  - Checkpoint Official Evaluation: **`resolved`** (`keisho-swebench-v2.6-five-way-once-001-checkpoint`).
- **Successor Evaluations (Official SWE-bench Verified in Docker)**:
  1. `FULL_HISTORY`: `status: completed`, `official_status: resolved` (2 calls, 1 tool, 39,716 input tokens).
  2. `SUMMARY_2K`: `status: completed`, `official_status: resolved` (4 calls, 3 tools, 11,585 input tokens).
  3. `REPOSITORY_ONLY`: `status: completed`, `official_status: resolved` (8 calls, 7 tools, 38,116 input tokens).
  4. `KEISHO_2K`: `status: completed`, `official_status: resolved` (3 calls, 2 tools, 14,163 input tokens).
  5. `STRUCTURED_NOTES_2K`: `status: completed`, `official_status: resolved` (3 calls, 2 tools, 8,159 input tokens).
- **Primary Comparative Outcome**: All 5 conditions preserved the resolution of the solved checkpoint. `KEISHO_2K` showed no accuracy advantage over alternative handoffs on this task. Token consumption was substantially lower for condensed representations (`STRUCTURED_NOTES_2K`, `SUMMARY_2K`, `KEISHO_2K`) than for full history or repository-only context.

### B. Financial Accounting (Attempt v2.6-001)
- **Actual Provider Billed Charges**: **$0.183058450** (31 settled API calls).
- **Conservative Accounted Spend**: **$0.389669350**.
- **Unreconciled Reservations**: **$0.000000**.
- **Approved Cap**: $10.00 (Run utilized 1.83% of approved budget).

### C. Cumulative Research Spend (All 13 Attempts)
- **Total Recorded Provider Spend**: **$1.18851345** ($1.0054550 prior + $0.18305845 v2.6-001).
- **Total Accounted Spend**: **$3.06878795** ($2.6791186 prior + $0.38966935 v2.6-001).
- **Total Unreconciled Reservations**: **$0.00924000** (Call 10 in v2.4-001).
- **Completed Comparisons**: **1** (`runs/swebench-v2.6-five-way-once-001`).
- **Completed Manuscript**: `paper/MANUSCRIPT_V26_COMPLETE_20261027.md`.
