# SWE-bench interface amendment v1.5

Dated 2026-10-22. Supersedes `swebench-interface-v1.4.md`.

## Context & empirical motivation

During the first live run under specification v1.4 (`runs/swebench-v1.4-five-way-once-001`), the predecessor attempt halted with `reason: budget_exhausted` at model call 6.
The predecessor model (`openai/gpt-4.1-mini-2025-04-14`) created a standalone reproduction script `fix_xarray_chunks.py` generating an uncompressed Zarr array. This created 202 individual chunk files (`example.zarr/0.0` through `example.zarr/9.9`).
While the command stdout was only 2,659 bytes, Keisho's environment recorded all 202 changed files in `changed_paths`, `source_hashes_before`, and `source_hashes_after`. The tool result payload expanded to 41,253 bytes (~17,997 tokens). On the next turn, total request input tokens exceeded the 32,000-token ceiling (`request_input_tokens`). Zero source edits were made to `xarray/`, and no checkpoint was eligible. All five successor branches remained unstarted and ungraded, with total actual provider spend of $0.0164.

## Interventions in v1.5

1. **Tool output & metadata bounding (`bounded-output/1.0`)**:
   - Command output (stdout + stderr) is capped at 8,192 bytes. Outputs exceeding this limit are truncated keeping the first 4,096 bytes and the last 4,096 bytes with an explicit non-silent marker `\n[... tool output truncated {N} bytes ...]\n` and metadata `{"truncated": true, "total_output_bytes": N}`.
   - Changed-paths inventory in conversational tool results is capped at 25 entries. Filesystems with bulk modifications record the first 25 paths and explicit metadata `{"omitted_changed_paths_count": N - 25, "inventory_truncated": true}`, while the underlying container and Git workspace preserve all files.
   - Total serialized conversational tool result payload is capped at 12,288 bytes (~3,000 tokens).
   - This bounding applies identically to predecessor and all five successor conditions.
2. **Predecessor model alignment (`openai/gpt-4.1-2025-04-14`)**:
   - Upgrades predecessor from `gpt-4.1-mini` to `gpt-4.1` (matching the successors) to improve localization and prevent toy script distractions.
   - Conservative maximum spending rises to $8.94 (envelope) + $0.08 (reservation) = $9.02, remaining securely beneath the authorized $10.00 cap.

## Invariant components retained from v1.4

- Five memory representations: `REPOSITORY_ONLY`, `FULL_HISTORY`, `SUMMARY_2K`, `STRUCTURED_NOTES_2K`, `KEISHO_2K`.
- Wire action contract: `flat-or-args/1.0`.
- Annotation guidance: `annotation-guidance/1.0`.
- Cumulative patch exporter: `source-and-artifacts/2.0`.
- Strict provider routing: `OpenAI` upstream via OpenRouter, zero automatic retries, immediate halt at cap.
- Evaluation harness: SWE-bench Verified `5.0.2` on Docker image for `pydata__xarray-6721`.
