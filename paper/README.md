# Research manuscript

This directory contains the revised manuscript and supporting study records for a single-task, five-condition coding-agent handoff pilot on SWE-bench Verified task `pydata__xarray-6721`.

## Deliverables

- [Revised manuscript (Markdown)](MANUSCRIPT_FINAL_PILOT.md)
- [Revised manuscript (plain text)](MANUSCRIPT_FINAL_PILOT.txt)
- [Academic HTML layout](MANUSCRIPT_FINAL_PILOT.html)
- [Print PDF](MANUSCRIPT_FINAL_PILOT.pdf)
- [Editorial audit and unresolved author checks](EDITORIAL_AUDIT_20261027.md)

The Markdown file is the canonical source. Run `python3 paper/render_manuscript.py` from the repository root to regenerate the text and HTML exports, then run `swift paper/render_pdf.swift` to regenerate the paginated PDF.

## Study summary

All five successor conditions received an official `resolved` grade in one run on the same task. `KEISHO_2K` used 47,170 successor input tokens, compared with 138,443 for `FULL_HISTORY`; under the same successor-call accounting, both generated summaries used fewer tokens than Keisho. Each condition was run once, in fixed order, with one model pair and no provider-side seed pinning. The results are descriptive and do not establish a general advantage or a causal effect of handoff representation.

The official evaluator marked the predecessor's empty patch `unresolved` without running the target test. A separate Docker replay confirmed the target failure and reported the full collected-test accounting in the manuscript.

## Supporting records

- Completed run: `runs/swebench-v2.7-five-way-once-005/` (local, Git-ignored;
  not included in this clone or in a public data archive)
- Checkpoint replay: `analysis/checkpoint_verification_command.sh`, `analysis/checkpoint_verification_log.txt`, and `analysis/checkpoint_verification_result.json`
- Run history and protocol attempts: `BENCHMARK_PROGRESS.md`
- Superseded manuscript versions and working notes have been removed. The revised manuscript above is the canonical paper.
