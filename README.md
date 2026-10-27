# Keisho

Keisho packages an unfinished coding session so you can open a fresh AI session
in a separate workspace and continue with a compact, inspectable handoff.
It transfers externally observable task state, not hidden reasoning, model
weights or activations, and does not guarantee error-free continuation.

---

## 📄 Research Paper & Empirical Benchmark Findings

The primary pilot study evaluating epistemic context handoffs during mid-task frontier model takeovers on **SWE-bench Verified** is complete and available in multiple formats:

- 📑 **Publication Paper (PDF, 8 pages)**: [`paper/MANUSCRIPT_FINAL_PILOT.pdf`](paper/MANUSCRIPT_FINAL_PILOT.pdf)
- 📝 **Full Scholarly Manuscript (Markdown)**: [`paper/MANUSCRIPT_FINAL_PILOT.md`](paper/MANUSCRIPT_FINAL_PILOT.md)
- 🌐 **Academic Web Presentation (HTML5)**: [`paper/MANUSCRIPT_FINAL_PILOT.html`](paper/MANUSCRIPT_FINAL_PILOT.html)
- 📄 **Plain Text Version**: [`paper/MANUSCRIPT_FINAL_PILOT.txt`](paper/MANUSCRIPT_FINAL_PILOT.txt)
- 📂 **Research Directory & Navigation**: [`paper/README.md`](paper/README.md)

### Empirical Study Highlights: Mid-Task Frontier Takeover (`pydata__xarray-6721`)
- **Pipeline**: Predecessor `openai/gpt-6-sol` $\rightarrow$ Note Generation `openai/gpt-6-luna` $\rightarrow$ Successor `anthropic/claude-opus-5.5`
- **Interception Boundary**: Predecessor was halted *strictly prior to executing its first source edit*, leaving the container working tree unpatched.
- **Empirical Checkpoint Verification**: Unpatched baseline was executed inside official Docker containers; verified that `FAIL_TO_PASS` test failed with `UnexpectedDataAccess: Tried accessing data` while all 1,405 regression tests passed.
- **Results**: All 5 successor conditions resolved the issue (5/5 `resolved` in Docker). `KEISHO_2K` reduced successor input tokens by **65.9%** vs. `FULL_HISTORY` (47,170 vs. 138,443 tokens) and matched the minimal turn count (**4 model calls**, 34.5s), avoiding the exploratory extra verification turn required by ordinary narrative summaries (5 calls, 86.8s).
- **Execution Ledgers & Verification**: See [`analysis/checkpoint_verification_result.json`](analysis/checkpoint_verification_result.json) and [`BENCHMARK_PROGRESS.md`](BENCHMARK_PROGRESS.md).

---

```sh
./keisho pack --repo /absolute/project --session /absolute/session.json \
  --task "The actual unfinished task" --out /absolute/bundle --token-budget 2048
./keisho inspect /absolute/bundle
./keisho resume /absolute/bundle --manual --workspace /absolute/new-project
```

Open the new directory and supply the printed `NEXT_SESSION_PROMPT.md` to a fresh
coding-agent session. These commands make no API calls. See the
[session import format, evidence inspection and safety boundaries](docs/local-handoff.md).
The complete audit record stays separate from `handoff.md`; uncertainty, scoped
failures, omissions and incomplete capture remain explicit.

Six [authored development cases](docs/development-suite.md) cover persistent jobs,
API/configuration migration and incremental document indexing. They are development
applications, not held-out or real-world benchmark evidence. Run `./keisho dev-suite`
to validate initial failures, references and incomplete fixes offline.

The recorded [OpenRouter calibration](analysis/openrouter-experiment-v1.2.0.md)
made nine live calls; task_001 was solved at the cutoff, so no successors ran.
Its artifacts, authorization and guard are preserved. That completed authorization
does not cover new runs. The manual tool and new development suite run offline;
learned successor conditioning remains deferred. The
[single scope amendment](protocol_amendments/local-continuation-v2.md) records this
milestone. Read the historical [Phase 1 report](PHASE1.md),
[prospective amendment](protocol_amendments/phase1-v1.0.0.md), and
[pilot manifest](analysis/pilot-manifest-v1.0.0.json). The original
[DESIGN.md](DESIGN.md), [PROTOCOL.md](PROTOCOL.md), and [AUDIT.md](AUDIT.md)
remain historical Phase 0 records.

The earlier [one-block readiness check](analysis/one-block-readiness-v1.0.0.md)
and its $1.25 configuration remain historical records.

## Verify offline

The bounded [SWE-bench Verified handoff integration](docs/swebench-handoff.md)
uses pinned official grading and the published Handoff Debt protocol. Current
stage, exact commands, results and blockers are in [BENCHMARK_PROGRESS.md](BENCHMARK_PROGRESS.md).

Python 3.11+; validated locally on 3.14.2/macOS. Phase 0 and synthetic pilot tests
use the standard library. Native token counting additionally uses the pinned
dependencies in `configs/requirements-pilot.lock` and the hash-checked public
o200k vocabulary asset. The optional build dependency is pinned in
`requirements.lock`.
Outgoing-schema regression tests additionally use `jsonschema==4.26.0`, pinned in
`configs/requirements-interface-tests.lock`; it is already installed on this host.

```sh
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 scripts/check_scaffold.py
./keisho plan --config configs/pilot.yaml
./keisho pilot --config configs/pilot.yaml --offline
```

Synthetic pilot outputs are scripted fixtures, never LLM results. The plan
reports whether an API key is configured, never its value. Tests use fake
provider transports. No model API requests are made. On this host the enclosing
Codex sandbox must permit `sandbox-exec` so child isolation can be verified;
the runner fails closed if it cannot. See PHASE1.md for calibration and live gates.

## Implemented boundary

| Area | Phase 0 implementation |
| --- | --- |
| State | Immutable typed atomic categories, explicit epistemic status, scoped sources/evidence, strict JSON round-trip, exact-ID duplicate merging |
| Extraction | Validated ingestion of externally supplied annotations tied to frozen event hashes; no automatic truth inference |
| Compilation | Canonical fixed JSON; four Phase 1 capsule formats; exact-count budget rejection without truncation |
| Models | Provider-neutral `AgentModel`, requests/responses/usage contracts, offline scripted test double |
| Environment | Owned filesystem workspace, deterministic reset, file/content/mode and empty-directory snapshots, verified restoration |
| Branches | Independent copies of the current checkpoint, unique condition assignment and manifest invariant validation |
| Logging | Exclusive JSON artifacts, read-only hash-chained external events, sealed immutable trajectory contract |
| Metrics | Raw counts/denominators, explicit reviewed annotations, action steps, null-aware stage token/time/cost accounting and failure categories |

`KeishoState` keeps constraints/preferences, observations, verified facts,
hypotheses, rejected hypotheses, actions, failed/inconclusive attempts, changes,
questions, uncertainties, plans and next actions distinct. A schema-valid
verification link is not proof of semantic truth. See the audit for limits.

The source tree mirrors these areas under `src/keisho`. `tasks/`, `configs/`,
`runs/raw/`, `runs/processed/`, `analysis/` and `results/` separate later task
fixtures, versioned settings, immutable artifacts and derived research outputs.
Raw runs are git-ignored; archive them explicitly before publishing results.

## Raw run contract

Create a fresh `RawRun(root, run_id)` per predecessor/successor. Write validated
`manifest.json` once, and log every externally exposed event via `append`.
`freeze()` seals the event stream; `load_frozen()` verifies the chain and seal.
`RawRun.open_existing(root, run_id)` permits verified read-only replay later.
Artifacts are JSON values; event payloads are canonical JSON object strings, allowing
arbitrary provider-native request/response objects without schema coercion.

```text
runs/raw/<run-id>/
  manifest.json
  events/00000000.json ...
  trajectory.json            # seal: count, last event hash, trajectory hash
  environment.json          # versioned content snapshot
  state.json                # extracted state, if derived for this block
  summary.json              # text, prompt and source hashes
  capsule.json              # condition, text, hash, token count/method
  calls.json                # every call, including failures
  outcome.json              # separate task/model/infrastructure/invalid status
  metrics.json              # raw annotations/calls plus counts/denominators
```

Shared artifacts can live in the parent run; successors refer to their hashes
in manifests. Keep these directories outside all agent-visible workspaces.
The Phase 0 API prevents overwrite and detects event tampering. It cannot stop
an owner from manually deleting files or rewriting hashes; use independent
archival storage before research runs. One writer per run is assumed.

## Current boundary

The original pilot retains exactly three debugging tasks, a four-condition runner, provider adapter,
gold-blind state projection, summary generation, and evidence-linked count scorer
are implemented. Phase 1 adds `annotation-review.json` and one immutable
`result.json` per branch; the Phase 0 layout above remains the infrastructure API.

The default `./keisho pilot --config configs/pilot.yaml` stops before a model
request. The new controlled continuation entry point also requires fresh approval
and an explicit shared cap; see `./keisho dev-plan`. Read the report before live execution. A
single model pair can test feasibility but cannot establish model dependence.
## Local credentials and prospective OpenRouter calibration

Keisho explicitly loads only this checkout's project-root `.env` before CLI provider
initialization. Existing environment variables win, including existing empty values.
Only `OPENAI_API_KEY` and `OPENROUTER_API_KEY` are imported; values are literal, with
no shell execution or variable expansion. Task workspaces are never searched.

The local `.env` is ignored and restricted to the current user. `.env.example` is the
tracked empty template. Add your key privately in your editor; do not paste it into
chat or commands containing the literal key. Direct OpenAI uses `OPENAI_API_KEY`;
the separate OpenRouter configuration uses `OPENROUTER_API_KEY`, without fallback.

See [OpenRouter amendment](protocol_amendments/openrouter-calibration-v1.1.0.md) and
[offline validation report](analysis/openrouter-readiness-v1.1.0.md) for the model-ID
limitations and spending estimate. OpenRouter supports the bounded calibration
and gated development continuations; the original pilot remains direct OpenAI.
