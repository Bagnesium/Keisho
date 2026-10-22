# SWE-bench interface amendment v1.6

Dated 2026-10-22. Supersedes `swebench-interface-v1.5.md`.

## Context & empirical motivation

Two prior exploratory attempts failed to reach the predecessor checkpoint:
1. **Run `swebench-v1.4-five-way-once-001` (`gpt-4.1-mini`)**: Halted at Call 6 ($0.0164). The model created a toy reproduction script producing 202 Zarr chunk files. Unbounded changed-paths metadata (41 KB / 18k tokens) flooded the context, exceeding the 32,000-token single-request input ceiling on Call 7 without touching `xarray/`.
2. **Run `swebench-v1.5-five-way-once-001` (`gpt-4.1`)**: Halted at Call 13 ($0.1129). The `bounded-output/1.0` mechanism successfully truncated 8 oversized file reads (including a 326 KB read on `dataset.py`) to 8,192 bytes, allowing the model to navigate `xarray/core/` across 13 inspection turns. However, cumulative token consumption reached 166,195 tokens. Because Call 14 would exceed the frozen `budgets.total_tokens: 180,000` ceiling, the run halted with `reason: budget_exhausted` before issuing an edit/test action.

## Interventions in v1.6

1. **Predecessor cumulative token ceiling raise**:
   - `predecessor_budgets.total_tokens` is raised from 180,000 to **400,000** tokens.
2. **Predecessor single-request input token ceiling raise**:
   - `predecessor_budgets.request_input_tokens` is raised from 32,000 to **64,000** tokens.
   - *Rationale*: In v1.5-001, request input reached 24,449 tokens at Call 13. With `bounded-output/1.0` adding ~2,000–2,500 tokens of conversation history per tool turn, keeping `request_input_tokens` at 32,000 would have halted the agent around turn 16–17 prior to code modification. Raising the ceiling to 64,000 permits 25+ inspection turns while remaining well within `gpt-4.1`'s 128k native context limit.
3. **Identical invariant baselines**:
   - Task: `pydata__xarray-6721`
   - Predecessor model: `openai/gpt-4.1-2025-04-14`
   - Successor model: `openai/gpt-4.1-2025-04-14`
   - Generation model: `openai/gpt-4.1-mini-2025-04-14`
   - Tool bounding: `bounded-output/1.0` (8,192 byte command output cap, 25 changed paths cap, 12,288 byte payload cap)
   - Successor budgets: 64 calls, 360,000 total tokens, 32,000 request input tokens
4. **Budget & spending envelope under $10 cap**:
   - Predecessor maximum cost (400,000 tokens): **$1.4593** (from $0.9973 in v1.5).
   - Note generation maximum cost (64,000 input ceiling, 2 calls): **$0.0591** (from $0.0323).
   - Single-request pre-call admission reservation headroom (64k input + 2k output): **$0.1516** (from $0.0844).
   - Combined five-way settled maximum conservative envelope: **$9.4272** <= **$10.00**.
   - Worst-case in-flight envelope including reservation: **$9.5788** <= **$10.00**.
   - Preserves **$0.4212** safety margin beneath the strict $10.00 cap.
