# Pilot Status: Keisho SWE-bench Verified Handoff Evaluation (v2.1)

> [!NOTE]
> This repository represents a code release and preregistered exploratory pilot, NOT a published paper.

## Scope & Experimental Design

- **Task**: SWE-bench Verified instance `sympy__sympy-20590` (commit `3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d`, dataset revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`).
- **Nature of Comparison**: Continuation handoff from an unfinished predecessor coding agent session to a successor coding agent session across five handoff representation conditions:
  1. `REPOSITORY_ONLY`
  2. `FULL_HISTORY`
  3. `SUMMARY_2K`
  4. `STRUCTURED_NOTES_2K`
  5. `KEISHO_2K`
  *(Note: This is an evaluation of handoff representation formats between an unfinished predecessor session and a successor session, NOT a single-agent vs. multi-agent comparison).*
- **Handoff Token Budget**: 2,048 tokens for compact handoff conditions (`SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`).
- **Models**:
  - Predecessor: `openai/gpt-6-sol-20260922` (reasoning effort: `none`)
  - Successor: `openai/gpt-6-sol-20260922` (reasoning effort: `none`)
  - Note generators: `openai/gpt-6-luna-20260922`

## Historical Attempts (v1.4 – v2.0)

Across seven historical evaluation attempts (v1.4 through v2.0), all seven runs halted during the predecessor phase before reaching the checkpoint; consequently, no successor condition ran, and no comparative results exist (35 successor conditions remained completely unstarted).

Total spend across historical attempts: **$0.8893** actual provider-billed spend / **$2.3853** conservative ledger-accounted cost ($0.8848 actual / $2.3808 ledger across v1.4–v1.9).

1. **v1.4** (`openai/gpt-4.1-mini-2025-04-14`): Halted at Call 6 (`budget_exhausted`).
2. **v1.5** (`openai/gpt-4.1-2025-04-14`): Halted at Call 13 (`budget_exhausted`).
3. **v1.6** (`openai/gpt-4.1-2025-04-14`): Halted at Call 14 (`stopped_on_error` / `budget_exhausted`).
4. **v1.7** (`openai/gpt-4.1-2025-04-14`): Halted at Call 8 (`invalid_run`).
5. **v1.8** (`openai/gpt-4.1-2025-04-14`): Halted at Call 22 (`budget_exhausted`).
6. **v1.9** (`openai/gpt-4.1-2025-04-14`): Halted at Call 29 (`finished` / `checkpoint_not_reached`).
7. **v2.0** (`openai/gpt-6-sol-20260922`): Halted at Call 1 (`model_failure`). The model emitted conversational preamble prose before the JSON action (`"I’ll trace Symbol’s inheritance..."`), causing the strict parser to stop immediately on predecessor Call 1 (`JSONDecodeError: Expecting value: line 1 column 1`) with zero retries.

## Specification v2.1 Status

- **Guarded Reader**: Specification v2.1 introduces a robust, non-salvaging single top-level JSON reader enforcing the Zero-Skip Brace Rule, single code block parsing, conservative wrapper rejection (disallowing `{}[]"` outside the admitted object/fence), and unconditional UTF-8 record validation across predecessor and all five successor conditions.
- **Execution Status**: **Not launched**.
  - `live_execution_authorized`: `false` (in `configs/swebench-comparison-v2.1.json`)
  - `spending_authorized`: `false` (in `analysis/five-way-cost-v2.1.json`)
  - `provider_requests`: `0` (`offline_only: true`)
- **Cost Envelope**: $10.00 proposed total cap; settled maximum conservative cost is $9.53369760 with $0.15590400 reservation headroom (peak in-flight envelope: $9.68960160; 3.104% safety margin).
- **Current State**: Not launch-ready from the public repo alone: local gitignored freeze inputs must be verified on the launch machine, a structured-notes reader gap is open, and explicit live spending authorization is pending (see review/ on branch review/v2.1-readiness).
