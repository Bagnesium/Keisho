# Pilot Limitations: Keisho SWE-bench Verified Evaluation (v2.1)

> [!NOTE]
> This repository represents a code release and preregistered exploratory pilot, NOT a published paper.

1. **Single Task (`sympy__sympy-20590`)**:
   The pilot evaluates only one SWE-bench Verified instance (`sympy__sympy-20590`). Performance on this specific issue cannot represent behavior across the full SWE-bench benchmark or general software development tasks.

2. **Single Run ($n=1$ per Condition)**:
   The evaluation specifies exactly one run per condition (`count: 1`, seed `20260430`, branch seed `20261007`). With $n=1$, there is zero measure of run-to-run variance or dispersion.

3. **No Statistical Significance or Generalization Claims**:
   Because each condition is executed only once on a single problem instance, no claims of statistical significance, comparative ranking, or generalization across repositories, languages, or problem types can be made.

4. **Handoff Format Scope (Not Single- vs. Multi-Agent)**:
   The study evaluates five handoff representation conditions (`REPOSITORY_ONLY`, `FULL_HISTORY`, `SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`) transferring observable state from an unfinished predecessor to a successor session. It does not evaluate or compare single-agent vs. multi-agent architectures.

5. **Single Model Family**:
   All agent roles use a single model family via OpenRouter: `openai/gpt-6-sol-20260922` for predecessor and successors, and `openai/gpt-6-luna-20260922` for note generation (reasoning effort: `none`). The evaluation cannot assess cross-family model dependence or sensitivity.

6. **Cost Ceiling Truncation Risk**:
   Runs are subject to strict token ceilings (predecessor 276,000 total tokens / 48 calls; successor 248,400 total tokens / 64 calls) under a conservative $10.00 total cap. As observed in prior historical attempts (v1.4, v1.5, v1.6, v1.8), budget exhaustion can truncate agent execution prior to checkpoint creation or task resolution.

7. **Post-Hoc Reader Intervention**:
   The guarded JSON reader introduced in v2.1 (Zero-Skip Brace Rule, single code block parsing, wrapper rejection) was implemented post-hoc following an observed parsing failure on Call 1 of v2.0 (preamble prose before the JSON action). It was not specified a priori.

8. **Unlaunched Status & Unverified Live Behavior (TO VERIFY)**:
   Specification v2.1 has not been launched (`live_execution_authorized: false`, `spending_authorized: false`, `provider_requests: 0`). Across all seven prior attempts (v1.4–v2.0), all 35 successor conditions remained completely unstarted. Whether the guarded reader avoids premature parsing failures and enables successors to reach evaluation under live execution remains TO VERIFY upon authorized execution.
