# Preregistered Results Table: Keisho SWE-bench Verified Pilot (v2.1)

> [!NOTE]
> This is a code release and preregistered exploratory pilot, NOT a published paper. No live runs have been launched under specification v2.1 (`live_execution_authorized: false`), and all seven predecessor attempts (v1.4–v2.0) halted before any successor ran. Every cell is prospective and PENDING.

## Condition Comparison: sympy__sympy-20590

Continuation handoff from an unfinished predecessor session to a successor session on SWE-bench Verified task `sympy__sympy-20590` ($n=1$ per condition). This evaluates five handoff representation conditions, not a single-agent vs. multi-agent comparison.

| Condition | Resolved (FAIL_TO_PASS / PASS_TO_PASS) | Handoff Tokens | Successor Model Calls | Tokens | Cost (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `REPOSITORY_ONLY` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `FULL_HISTORY` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `SUMMARY_2K` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `STRUCTURED_NOTES_2K` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `KEISHO_2K` | PENDING | PENDING | PENDING | PENDING | PENDING |

### Table Notes

- **Unlaunched Status**: v2.1 has not executed (`live_execution_authorized: false`, `spending_authorized: false`, `provider_requests: 0`).
- **Prior Attempts**: Across attempts v1.4 through v2.0, all seven runs halted during the predecessor phase; no successor condition ever executed.
- **Budget Ceilings**: Planned successor limits per condition are 64 model calls, 248,400 total tokens, and a $10.00 total experiment cap under `configs/swebench-comparison-v2.1.json`. Compact conditions (`SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`) have a 2,048 handoff token budget.
