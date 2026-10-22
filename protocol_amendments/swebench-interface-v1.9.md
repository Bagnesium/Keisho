# SWE-bench interface amendment v1.9

Dated 2026-10-22. Supersedes `swebench-interface-v1.8.md`.

## Context & empirical motivation

During the live run under specification v1.8 (`runs/swebench-v1.8-five-way-once-001`), the predecessor attempt executed 22 model calls and 22 tool actions on `sympy__sympy-20590` ($0.7777 accounted / $0.2541 actual provider spend).
The predecessor model (`openai/gpt-4.1-2025-04-14`) successfully demonstrated the v1.8 non-fatal tool observation and wire recovery mechanisms:
- On Call 10 and Call 11, missing file errors for `sympy/core/atom.py` and `atomic.py` were ingested as non-fatal observations without killing the run.
- On Call 20, an invalid-argument wire rejection (`length`, `offset`) returned an observation to the model, which correctly pivoted to targeted shell commands (`head`, `tail`, `grep`) on Calls 21 and 22.

However, lacking explicit workflow pacing or early-edit guidance, the predecessor spent all 22 calls reading modules and tracing inheritance chains (`Symbol`, `Basic`, `Expr`) without ever attempting a code edit or executing tests. At Call 22, cumulative token consumption reached 385,584 tokens, exhausting the 400,000 total token budget (`budget_exhausted`). The handoff checkpoint was never triggered, leaving all five successor conditions unstarted.

## Interventions in v1.9

1. **Workflow guidance in system prompt (`benchmark-agent/5.0`)**:
   The agent system prompt is upgraded to `benchmark-agent/5.0` (`SYSTEM_V5`), applied identically to predecessor and all five successor conditions, by adding the following workflow block verbatim:
   ```text
   Workflow: 1. Read the issue and locate the relevant code with targeted shell searches (grep, head) instead of reading whole modules. 2. Reproduce the problem with a short script or an existing test when practical. 3. Make the smallest edit that fixes it; make your first edit by turn 12. 4. Run the relevant public tests. 5. When tests pass, call finish with a short summary. Do not spend more than a third of your budget exploring.
   ```
2. **Byte-identical claims and interface invariants**:
   - The claims rules (`auxiliary-claims/2.0`), tool definitions, listing policy (`bounded-listing/1.0`), and annotation guidance (`annotation-guidance/1.0`) remain strictly byte-identical to `SYSTEM_V4`.
   - Tool execution bounding (`bounded-output/1.0`), non-fatal error observations, fatal path escape checks, and 3-consecutive-failure limits remain active.
3. **Invariant models, budgets & spending envelope under $10 cap**:
   - Task: `sympy__sympy-20590`.
   - Predecessor model: `openai/gpt-4.1-2025-04-14` ($2.00 / $8.00 per 1M tokens).
   - Successor model: `openai/gpt-4.1-2025-04-14` across all 5 conditions.
   - Generation model: `openai/gpt-4.1-mini-2025-04-14`.
   - Predecessor budgets: 48 calls, 400,000 total tokens, 64,000 request input tokens.
   - Successor budgets: 64 calls, 360,000 total tokens, 64,000 request input tokens.
   - First request upper bound: 2,380 tokens.
   - Combined five-way settled maximum conservative envelope: **$9.4272** <= **$10.00**.
   - Peak in-flight envelope including reservation: **$9.5788** <= **$10.00**.
