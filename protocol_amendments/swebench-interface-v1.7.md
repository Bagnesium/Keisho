# SWE-bench interface amendment v1.7

Dated 2026-10-22. Supersedes `swebench-interface-v1.6.md`.

## Context & empirical motivation

Three iterations on `pydata__xarray-6721` revealed two structural failure modes at the predecessor:
1. **Run `swebench-v1.4-five-way-once-001` (`gpt-4.1-mini`)**: Halted at Call 6 ($0.0164) due to 202 Zarr chunk files flooding context with 41 KB of file metadata exceeding the 32,000 input token ceiling.
2. **Run `swebench-v1.5-five-way-once-001` (`gpt-4.1`)**: Halted at Call 13 ($0.1129) under `bounded-output/1.0`. Navigated 5 core modules but exhausted the 180,000 cumulative token budget.
3. **v1.6 analysis**: While predecessor ceilings were raised (400,000 total / 64,000 input), `pydata__xarray-6721` spans thousands of lines across distributed modules. Successor handoff for `FULL_HISTORY` would carry over 32k tokens, causing an immediate admission failure because `successor_budgets.request_input_tokens` was frozen at 32,000 in `configs/swebench-comparison-v1.6.json`.

## Interventions in v1.7

1. **Task switch to `sympy__sympy-20590`**:
   - Target file: `sympy/core/symbol.py` (compact ~60 lines surrounding the `Symbol` slot/attribute definition).
   - Problem: `Symbol` instances have `__slots__ = ('name',)` but lacked `__dict__` in `_unhandled` or attribute lookup, a one-line/15-line clean fix.
   - Requires only a simple read-and-edit cycle (~4 turns), eliminating multi-module search loops and large directory traversals while preserving the exact same SWE-bench evaluation harness and five-way condition comparison.
2. **Successor single-request input token ceiling raise**:
   - `successor_budgets.request_input_tokens` is raised from 32,000 to **64,000** tokens.
   - *Rationale*: Predecessor handoffs to `FULL_HISTORY` can reach 32k–50k input tokens. Parity between predecessor and successor single-request input ceilings ensures `FULL_HISTORY` is never rejected by admission preflight upon receiving the predecessor's conversation.
3. **Model confirmations & invariant baselines**:
   - Predecessor model: `openai/gpt-4.1-2025-04-14` ($2.00 / $8.00 per 1M tokens)
   - Successor model: `openai/gpt-4.1-2025-04-14` across **all five conditions** ($2.00 / $8.00 per 1M tokens)
   - Generation model: `openai/gpt-4.1-mini-2025-04-14` (only used for `SUMMARY_2K` and `STRUCTURED_NOTES_2K` note creation)
   - Tool bounding: `bounded-output/1.0` (8,192 byte command output cap, 25 changed paths cap, 12,288 byte payload cap)
   - Predecessor budgets: 48 calls, 400,000 total tokens, 64,000 request input tokens
   - Successor budgets: 64 calls, 360,000 total tokens, 64,000 request input tokens
4. **Budget & spending envelope under $10 cap**:
   - Predecessor maximum cost (400,000 tokens): **$1.4593**.
   - Note generation maximum cost (64,000 input ceiling, 2 calls): **$0.0591**.
   - Successor maximum cost per condition (360,000 tokens): **$1.5818**.
   - Combined five successors maximum: **$7.9088**.
   - Combined five-way settled maximum conservative envelope: **$9.4272** <= **$10.00**.
   - Peak in-flight reservation headroom (64k input + 2k output): **$0.1516**.
   - Worst-case in-flight envelope including reservation: **$9.5788** <= **$10.00**.
   - Preserves **$0.4212** safety margin beneath the strict $10.00 cap.
