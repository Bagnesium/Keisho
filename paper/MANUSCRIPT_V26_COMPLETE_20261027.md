# Epistemic Handoffs in Multi-Agent Software Engineering: Empirical Evaluation and Complete Pilot Comparison on SWE-bench Verified

**Authors**: Keisho Research Working Group (Lead: bagnesium)  
**Status**: COMPLETED PILOT MANUSCRIPT (FIRST SUCCESSFUL FIVE-WAY COMPARISON)  
**Date**: October 27, 2026  
**Governing Specification**: `swebench-handoff/2.6` (`configs/swebench-comparison-v2.6.json`)  
**Completed Comparison Run**: `runs/swebench-v2.6-five-way-once-001`  
**Evaluation Target**: SWE-bench Verified (`sympy__sympy-20590`)  

---

## Abstract

We report the first successfully completed empirical five-way comparison evaluating agent handoff representations on a real software engineering repair task from SWE-bench Verified. The benchmark assesses five context transfer conditions: `REPOSITORY_ONLY` (no handoff context), `FULL_HISTORY` (uncompressed conversation turns), `SUMMARY_2K` (ordinary 2,048-token LLM summary), `STRUCTURED_NOTES_2K` (7-field schema notes + deterministic facts), and `KEISHO_2K` (compiler-generated typed items with file-revalidation scoping).

Following twelve historical failed attempts caused by real-world model compliance crashes and API failures, prospective specification v2.6 completed with end-to-end execution across all five successor conditions. The predecessor reached the checkpoint on `sympy__sympy-20590` at Call 9, with its cumulative patch officially resolving the issue (`resolved`). Across all five successor branches evaluated from this identical checkpoint, all five conditions preserved task resolution (5/5 `resolved` by official Docker SWE-bench evaluation). While resolution rates were identical on this preservation task, efficiency differed substantially: `STRUCTURED_NOTES_2K` consumed the fewest successor input tokens (8,159 tokens, 3 calls), followed by `SUMMARY_2K` (11,585 tokens, 4 calls) and `KEISHO_2K` (14,163 tokens, 3 calls). In contrast, `REPOSITORY_ONLY` required 38,116 input tokens and 8 calls to re-explore the repository from scratch, and `FULL_HISTORY` required 39,716 input tokens carrying the full conversational history.

Actual provider billing for the entire five-way comparison was **$0.183058** (conservative accounted spend: **$0.389669**; unreconciled reservations: **$0.00**), well within the authorized $10.00 cap. This completed run constitutes an exploratory development pilot (N=1 task, N=1 run). Because the predecessor's checkpoint patch already resolved the task, the run measured solution preservation, not continuation of unfinished work; the efficacy question for genuinely unfinished tasks remains untested, not answered in either direction. In this preservation regime, observed successor input usage was 8,159–14,163 tokens across the three note-based handoffs versus 38,116 (`REPOSITORY_ONLY`) and 39,716 (`FULL_HISTORY`). Accuracy could not differentiate any condition, since all five tied at `resolved`.

---

## 1. Introduction and Research Question

In multi-agent and takeover software engineering workflows, transferring context from an exhausted predecessor agent to a successor agent is a fundamental bottleneck. Prior work on *Handoff Debt* (KC & Budathoki, 2026) demonstrated that lossy unstructured summaries introduce systematic cognitive debt, inducing hallucinations, false confidence, and contradictory code modifications.

Keisho proposes a deterministic, compiler-based handoff mechanism: rather than prompting an LLM to generate natural language prose, the compiler extracts verified observable events from the predecessor's hash-chained trajectory, binds them to exact tool actions and named file SHA-256 hashes, and tags modified files with explicit `REVALIDATE` directives.

### Primary Empirical Question
> *Does a compact, deterministically selected record of observable work, item provenance, and named-file revalidation flags (`KEISHO_2K`) improve successor continuation on an unfinished coding task compared to ordinary summaries (`SUMMARY_2K`), structured notes (`STRUCTURED_NOTES_2K`), full history (`FULL_HISTORY`), or repository only (`REPOSITORY_ONLY`)?*

---

## 2. Pinned Experimental Protocol (v2.6)

Governed by canonical specification `configs/swebench-comparison-v2.6.json` (SHA-256 `723403df...`) and plan `analysis/swebench-comparison-v2.6-plan.json` (SHA-256 `c268053c...`):

- **Task**: `sympy__sympy-20590` (SWE-bench Verified, git base commit `cffd4e0f86fefd4802349a9f9b19ed70934ea354`).
- **Models**: Predecessor and Successors: `openai/gpt-6-sol-20260922` (OpenRouter alias `openai/gpt-6-sol`, reasoning effort `none`). Note Generators: `openai/gpt-6-luna-20260922` (OpenRouter alias `openai/gpt-6-luna`, reasoning effort `none`).
- **Predecessor Checkpoint Rule**: "first completed validation/build/lint/test command result following a non-test source edit".
- **Budgets**: Predecessor: 276,000 total tokens, 64,000 request input limit, 48 model calls, 36 tools, 1,800s. Successors: 234,000 total tokens, 64,000 request input limit, 64 model calls, 48 tools, 1,800s. Handoff limit: 2,048 tokens.
- **Execution Order**: Prospectively seeded pseudorandom sequence:
  1. `FULL_HISTORY`
  2. `SUMMARY_2K`
  3. `REPOSITORY_ONLY`
  4. `KEISHO_2K`
  5. `STRUCTURED_NOTES_2K`
- **Evaluation**: The official SWE-bench evaluation harness (`swebench eval`) running inside Docker image `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest`.

---

## 3. Disclosed Historical Attempts Prior to v2.6

Twelve prior live attempts on SWE-bench Verified halted without completing comparisons:
- **v1.4-001**: Call 6 budget exhausted (Zarr array metadata overflow). ($0.0164 spend)
- **v1.5-001**: Call 13 budget exhausted (166k tokens before edit). ($0.1129 spend)
- **v1.6-001**: Call 14 request input ceiling exceeded on call 11. ($0.1269 spend)
- **v1.7-001**: Call 8 invalid action reading non-existent file. ($0.0342 spend)
- **v1.8-001**: Call 22 budget exhausted reading inheritance chains. ($0.2694 spend)
- **v1.9-001**: Call 29 finished without source edit. ($0.3249 spend)
- **v2.0-001**: Call 1 conversational prose preceding JSON wire object. ($0.0045 spend)
- **v2.2-001**: Call 1 finished immediately on turn 1. ($0.0036 spend)
- **v2.3-001**: Call 8 prose syntax rejection after 7 tools executed. ($0.0334 spend)
- **v2.4-001**: Call 9 checkpoint reached; Call 10 note generation failed at provider API with null usage. ($0.0464 recorded spend, 1 call unknown)
- **v2.4-002**: Call 7 checkpoint reached; post-run measurement framing AttributeError. ($0.0328 spend)
- **v2.5-001**: Call 0 startup KeyError in model constructor dispatch. ($0.0000 spend)

Cumulative historical spend prior to v2.6: **$1.005455** recorded provider billing, **$2.679119** accounted spend, **$0.009240** unreconciled reservation.

Scope note: the twelve attempts above are the five-way series v1.4–v2.5. Two earlier integration pilots are disclosed separately: `swebench-integration/comparison` ($0.002008 billed) and `exploratory-v1.1-live` ($0.0165520 billed); they are excluded from the totals above. Historical billing remains not fully reconciled because the v2.4-001 Call 10 provider charge is unknown (null usage, $0.009240 reservation held).

---

## 4. Empirical Results: Completed Five-Way Comparison `swebench-v2.6-five-way-once-001`

Authorized under fresh scope `bagi-20261027-v26-01`, run `runs/swebench-v2.6-five-way-once-001` executed to full completion across all five successor conditions.

### 4.1 Predecessor Checkpoint
- **Execution**: 9 model calls, 9 tool calls, 56,453 input tokens, 1,207 output tokens.
- **Checkpoint Boundary**: On Call 7, the predecessor applied empty `__slots__ = ()` to mixin class `Printable` in `sympy/core/_print_helpers.py` and added a regression test in `sympy/core/tests/test_symbol.py`. On Call 9, it executed `python -m pytest -q sympy/core/tests/test_symbol.py sympy/printing/tests/test_str.py`, which completed with exit code 0.
- **Official Checkpoint Grade**: Evaluated in Docker: **`resolved`** (`keisho-swebench-v2.6-five-way-once-001-checkpoint`).
- **Nature of the Continuation**: Because the predecessor patch already resolved the issue, this comparison tested **solution preservation and regression resistance** under takeover.

### 4.2 Note Generation
- **Summary Generator** (`openai/gpt-6-luna`): Call 10 completed; generated 276 output tokens; billed $0.002517.
- **Structured Notes Generator** (`openai/gpt-6-luna`): Call 11 completed; generated 264 output tokens matching all 7 required schema fields; billed $0.002538.
- **Handoff Token Bounds**:
  - `SUMMARY_2K`: 326 native tokens (≤2,048)
  - `STRUCTURED_NOTES_2K`: 482 native tokens (≤2,048)
  - `KEISHO_2K`: 591 native tokens (≤2,048)
  - `FULL_HISTORY`: 19,435 native tokens (carried complete context without truncation)
  - `REPOSITORY_ONLY`: 0 handoff tokens (standard framing text)

### 4.3 Five-Way Comparison Outcomes

| Condition | Successor Status | Model Calls | Tool Calls | Input Tokens | Output Tokens | SWE-bench Outcome | Preserved Solution? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`FULL_HISTORY`** | `completed` | 2 | 1 | 39,716 | 203 | **`resolved`** | **Yes** |
| **`SUMMARY_2K`** | `completed` | 4 | 3 | 11,585 | 575 | **`resolved`** | **Yes** |
| **`REPOSITORY_ONLY`** | `completed` | 8 | 7 | 38,116 | 1,011 | **`resolved`** | **Yes** |
| **`KEISHO_2K`** | `completed` | 3 | 2 | 14,163 | 337 | **`resolved`** | **Yes** |
| **`STRUCTURED_NOTES_2K`** | `completed` | 3 | 2 | 8,159 | 451 | **`resolved`** | **Yes** |

### 4.4 Financial Reconciliation
- **Total Incurred Provider Charges**: **$0.183058** (exact sum: $0.18305845)
  - Predecessor (9 calls): $0.048350
  - Note Generation (2 calls): $0.005055 ($0.002517 summary, $0.002538 structured)
  - `FULL_HISTORY` (2 calls): $0.056623
  - `SUMMARY_2K` (4 calls): $0.014315
  - `REPOSITORY_ONLY` (8 calls): $0.031066
  - `KEISHO_2K` (3 calls): $0.016141
  - `STRUCTURED_NOTES_2K` (3 calls): $0.011508
- **Conservative Accounted Spend**: **$0.389669**
- **Unreconciled Reservations**: **$0.000000**
- **Authorized Spending Cap**: $10.00 (Run utilized 1.83% of approved funds).
*(Reconciliation note: Exact component sums from `spending.json` sum to $0.18305845. A prior report cited predecessor cost as $0.048264 due to an unrounded subtraction error of $0.000086, fully reconciled here).*

---

## 5. Discussion and Scientific Findings

### 5.1 Resolution Preservation
On this task (`sympy__sympy-20590`), all five conditions successfully preserved the working patch and achieved official resolution. Neither `REPOSITORY_ONLY` nor the condensed summaries (`SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`) regressed the predecessor's fix or introduced fatal syntax errors.

### 5.2 Efficiency and Context Dynamics
While resolution rates were tied at 100%, token efficiency diverged sharply:
1. **Compact Notes Efficiency**: `STRUCTURED_NOTES_2K` (8,159 input tokens) and `SUMMARY_2K` (11,585 input tokens) required the fewest input tokens, followed by `KEISHO_2K` (14,163 input tokens). These successor input figures exclude note-generation cost for `SUMMARY_2K` and `STRUCTURED_NOTES_2K` (two `gpt-6-luna` generator calls, $0.005055 total; `KEISHO_2K` is deterministically compiled, with no model-generation call evidenced in this run) and output tokens; `FULL_HISTORY` and `REPOSITORY_ONLY` carry no generation cost, so input-token ratios are not full-cost ratios.
2. **Observed Repository-Only Behavior**: Without handoff context, `REPOSITORY_ONLY` used 8 model turns and 7 tool calls (running `pytest`, reading test files, inspecting inheritance), consuming 38,116 input tokens and 1,011 output tokens, compared to 2–4 model calls in the handoff conditions.
3. **Context Weight in Full History**: `FULL_HISTORY` carried 19,435 prompt tokens on turn 1 and 20,281 on turn 2, requiring 39,716 input tokens despite making only two calls.

### 5.3 Comparative Hypothesis Assessment
The primary hypothesis—that `KEISHO_2K` provides an effectiveness advantage over `STRUCTURED_NOTES_2K` or `SUMMARY_2K`—is **not supported** by this run, and the solved-checkpoint regime means the run cannot test it: with all conditions tied at `resolved`, effectiveness differences are unmeasurable here. Both structured notes and ordinary summaries preserved the solution at equal accuracy, with `STRUCTURED_NOTES_2K` requiring slightly fewer tokens (8.2k vs 14.2k) than `KEISHO_2K`'s explicit file inventory.

---

## 6. Threats to Validity and Limitations

1. **Pilot Scope (N=1)**: This comparison represents a single exploratory task instance. It proves pipeline functionality and demonstrates preservation feasibility, but cannot establish statistical significance or generalizable conclusions across coding benchmarks.
2. **Preservation vs Incomplete Continuation**: Because the predecessor solved the problem before handoff, this run tested *solution retention*, not *recovery from an incomplete or failing attempt*. Handoff formats may perform differently when the successor must diagnose a failing test or backtrack from a bad edit.
3. **Single Model Pair**: The experiment used `gpt-6-sol` and `gpt-6-luna`. Behavior may vary under models with different instruction-following compliance.
4. **Local Literature Boundaries**: External agent architectures (e.g. SWE-agent, Agentless) were not evaluated locally and are excluded from comparative claims.

---

## 7. Conclusion

Specification v2.6 achieved the first complete, fully graded five-way agent takeover comparison on SWE-bench Verified. Under identical Docker evaluation, all five handoff conditions preserved the resolution of an already-solved checkpoint. Condensed handoffs reduced successor input tokens compared to `FULL_HISTORY` (39,716): `STRUCTURED_NOTES_2K` by 79% (8,159), `SUMMARY_2K` by 71% (11,585) and `KEISHO_2K` by 64% (14,163). Accuracy could not differentiate any condition on this pilot task (all tied at `resolved` on an already-solved checkpoint), so the run leaves Keisho's efficacy on genuinely unfinished work untested rather than showing equivalence or advantage.

---

## References

1. **KC, D., & Budathoki, A. (2026).** *Handoff Debt: The Rediscovery Cost When Coding Agents Take Over Interrupted Tasks*. arXiv preprint [arXiv:2606.02875](https://arxiv.org/abs/2606.02875).
2. **Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024).** *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* In The Twelfth International Conference on Learning Representations (ICLR 2024).
