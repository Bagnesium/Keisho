# Keisho

Keisho is research software for transferring task state between coding-agent
sessions. It records externally observable work, evidence scope, uncertainty,
and attempted actions, then compiles a bounded handoff for a successor. It does
not transfer hidden reasoning or guarantee that a successor will solve the task.

## Research status

The current paper reports one exploratory five-condition comparison on the
SWE-bench Verified task `pydata__xarray-6721`. Each condition ran once from the
same checkpoint, and all five patches received an official `resolved` grade.
The branches share one task and checkpoint, so they are not independent task
observations. The result cannot establish a general, causal, or statistical
advantage for any handoff condition.

`KEISHO_2K` used 47,170 successor input tokens, compared with 138,443 for
`FULL_HISTORY`; the two generated summaries used fewer tokens than Keisho. The
successor order was fixed and the provider did not support the requested seed.
These are descriptive observations from one run, not evidence of general
efficiency or latency effects. The official evaluator did not run the target
test for the predecessor's empty patch. A separate pinned-Docker replay found
the target failure and recorded all 1,445 collected-test outcomes.

- [Research manuscript (PDF)](paper/MANUSCRIPT_FINAL_PILOT.pdf)
- [Research manuscript (Markdown)](paper/MANUSCRIPT_FINAL_PILOT.md)
- [Editorial audit and author checks](paper/EDITORIAL_AUDIT_20261027.md)
- [Experiment specification](research/FIVE_WAY_EXPERIMENT_SPEC.md)
- [Reproducibility notes and limits](research/REPRODUCIBILITY.md)
- [Chronological experiment record](BENCHMARK_PROGRESS.md)

The raw pilot run archive and private evaluator inputs are not included in this
clone. There is no public data archive or DOI, so the reported run cannot be
independently replayed from this repository alone.

## Try the local handoff tool

Python 3.11 or newer is required. The local `pack`, `inspect`, and `resume`
workflow does not make model API calls. Start with:

```sh
./keisho --help
```

See [local handoff usage, input formats, and safety boundaries](docs/local-handoff.md).
For the bounded SWE-bench integration and its limitations, see
[the benchmark guide](docs/swebench-handoff.md).

## Repository map

- `src/keisho/` — implementation.
- `tests/` — unit, interface, and offline integration checks.
- `tasks/` — authored development fixtures; evaluator-only answers stay out of
  agent workspaces.
- `configs/`, `analysis/`, `protocol_amendments/` — versioned specifications,
  plans, protocol changes, and historical authorization records.
- `research/`, `paper/` — study design, reproducibility limits, manuscript, and
  editorial audit.
- `DESIGN.md`, `PROTOCOL.md`, `AUDIT.md`, and `PHASE1.md` — early phase records;
  they describe historical specifications, not the current pilot result.
- `BENCHMARK_PROGRESS.md` — chronological record; older entries describe the
  state at the time and may be superseded by later entries and the paper.
- `runs/`, most of `results/`, and `.cache/` — local archives or evaluator data;
  these are intentionally excluded from Git.
- `AGENTS.md` — research and repository guidance for coding agents.

Existing authorization files document past scopes. They do not authorize new
provider requests. Never commit `.env`, `.cache/`, raw run archives, or private
evaluator data. A clone contains code and public research records, not the
complete local evaluation installation.

## License status

Keisho-authored code and documentation are licensed under the MIT License; see
[`LICENSE`](LICENSE). Third-party code, datasets, service-derived metadata, and
other assets are excluded and may have different terms. In particular, the
tracked OpenRouter catalog snapshots have unresolved redistribution status.
Review [`review/LICENSE_RESEARCH.md`](review/LICENSE_RESEARCH.md) before
redistributing those materials.
