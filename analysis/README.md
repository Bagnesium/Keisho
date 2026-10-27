# Analysis and study records

This directory contains versioned study plans, configuration bindings, cost
records, and selected verification outputs. It is not a single analysis
notebook, and most files are protocol history rather than inferential results.

## Current empirical study

The completed v2.7 comparison is reported in
[`paper/MANUSCRIPT_FINAL_PILOT.md`](../paper/MANUSCRIPT_FINAL_PILOT.md), with
editorial and verification issues in
[`paper/EDITORIAL_AUDIT_20261027.md`](../paper/EDITORIAL_AUDIT_20261027.md).
The study used one SWE-bench Verified task and one run per handoff condition.
All five branches received an official `resolved` grade. The shared task and
checkpoint, fixed order, and one run per condition do not support statistical
inference, a causal comparison, or generalization across tasks.

The raw run at `runs/swebench-v2.7-five-way-once-005/` is local and ignored by
Git. The public clone does not contain its provider traces or the private
evaluator installation. The checkpoint replay command, log, and structured
result are the tracked files `checkpoint_verification_command.sh`,
`checkpoint_verification_log.txt`, and `checkpoint_verification_result.json`.

## How to navigate the records

- `swebench-comparison-v2.7-plan.json`, the matching config under `configs/`,
  `swebench-experiment-v2.7-manifest.json`, and
  `swebench-v2.7-final-source-freeze.json` record the final planned bindings.
- `swebench-comparison-v*-authorization*.json` records historical and
  prospective scopes. A record is not current permission to spend or rerun.
- Earlier versioned plans, manifests, freezes, and cost files preserve protocol
  development and failed attempts. Do not treat a higher version number alone
  as evidence that an experiment ran.
- `research-closeout-2026-10-27.md` is a superseded historical status report;
  its executive summary predates the v2.7 comparison. Use the current paper for
  the result.
- `../BENCHMARK_PROGRESS.md` is the chronological execution log. Its older
  interpretations are historical; the current paper states the supported
  conclusion.
- `../research/REPRODUCIBILITY.md` documents the earlier v1.2 engineering
  integration and its local setup. It is not the v2.7 run archive.

No pooled or confirmatory statistical analysis is reported. Synthetic
development fixtures and offline rehearsals are software evidence, not
empirical model outcomes. Preserve each frozen record and use a new version for
prospective changes.
