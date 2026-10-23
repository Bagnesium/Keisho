# Methods draft

Draft 2026-10-11, based on implemented code. Research results and human review are
pending. This text describes **Keisho handoff evaluation on SWE-bench Verified**,
an adapted takeover experiment rather than an exact reproduction or leaderboard
submission. Current configuration 1.2 is disabled and has no paid authorization.

## Task and checkpoint

The environment uses real SWE-bench Verified repository issues and the official
evaluator. Dataset revision is `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`; harness
commit is `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` (version 5.0.2), with task
recipes at `3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d`. The selected exploratory
task is `pydata__xarray-6721`, base commit
`cc183652bf6e1273e985e1c4b3cba79c896c1193`. Selection was archived before outcomes,
using public difficulty metadata, a recorded shuffled order and seed 20260430.
Setup-only `sympy__sympy-20590` is excluded from live comparison.

The predecessor receives the original issue and installed repository environment.
It pauses after the first completed validation/build/lint/test result following
a prior non-test source edit. Source status and validation signals reuse published
Handoff Debt code, with local completed-command interpretation. An edit and validation
in the same shell action have unknown order and require a subsequent validation.
The rule does not require a failed attempt, task resolution or hidden test feedback.
Timeout/background-process/output-bound violations do not create a checkpoint.
No checkpoint within budget is retained as ineligible, without resampling.

After a completed boundary, the controller freezes the observable event record,
workspace inventory and Docker image. Notes are constructed before official
checkpoint grading. The private grade may classify a checkpoint as unresolved or
already resolved; it cannot change notes, stopping, selection or model inputs.
Already-resolved checkpoints measure preservation separately from completion.

## Agent interface and observability

The existing text-action runner makes one JSON-object response per model request,
containing an action and auxiliary claims. Supported actions are listing, reading,
writing a complete source file, running a contained shell command, and explicit
finish. Version 1.2 uses provider JSON-object mode with strict local top-level,
argument, path and execution validation. Invalid/ambiguous actions stop; no output
repair, forced alternative action or automatic generation retry is used.

Auxiliary policy `auxiliary-claims/2.0` separates annotation validity from action
admission. Malformed claim labels/references are archived with exact reasons and
excluded from validated state. An independently authorized valid action can proceed.
Missing annotations remain unknown; schema conformity and available citations do
not establish truth. This policy is identical for predecessor and successors.

The adapter records requested canonical identity, requested service alias, returned
identity, reported provider, usage and cost. Service IDs do not attest an unchanged
upstream output or physical model snapshot. Actual HTTP response bodies are captured
before local JSON/provider/admission processing, with no headers/API keys and explicit
credential-redaction metadata. The raw assistant content and each action/result remain
in request history in order. JSON syntax, action schema, authorization/safety,
annotations, rejected proposals and completed/successful tools are separate measures.
Invalid rates divide by actual responses received; missing responses are separate.

The optional `bounded-listing/1.0` tool supplies lexicographic pages with up to 100
paths and 8,192 path bytes, safe prefix selection and opaque cursor. Counts, truncation,
omissions and pagination instructions are explicit. Repeated identical pages refer
to an earlier retained result. File changes invalidate the inventory identity; stale
cursors yield a restart diagnostic. No conversation compression, embeddings or
task-specific file hints are used. Legacy configurations retain their original full
listing contract.

## Keisho construction and limitations

`load_session` reconstructs supported external state from a sealed event trajectory.
Tool facts become observed items, bound to event IDs and named file hashes. Model
statements remain hypotheses or unsupported rejections, regardless of asserted
verification labels. The importer does not reconstruct unrecorded reasoning or manually
infer a superior bug explanation. It records missing categories and coverage.

The benchmark-used local importer has narrower behavior than the repository's full
typed state schema. A file-read item records inspection, not a semantic source summary.
Shell validation results are scoped observations, not automatically named-test claims
or rejected approaches. Its conflict/supersession mechanism applies to structured named
test outcomes when available; arbitrary semantic contradiction detection is not
implemented by this path.

The existing scope policy compares recorded named-file hashes with the frozen inventory
and marks changed/unknown files for revalidation. This does not prove a claim false,
detect dependency/environment changes, or execute tests automatically. Interpretation
scopes and dependency relationships remain unknown. Version 1.2 fixes the benchmark
bridge's omission of this already implemented local pack/resume check.

`compact/1.0` retains the task framing, acceptance, constraints, workspace metadata and
unknowns, then selects complete labelled items by deterministic category priority.
Conflict/supersession-linked items are retained together. Whole-item omissions are
recorded and essential overflow stops. The resulting text includes item/source IDs,
limited scope and revalidation labels. The complete audit and source hashes remain
controller-side; successors cannot fetch referenced records. Selection is heuristic,
not proven optimal or minimally sufficient. Compilation makes no extra provider call;
predecessor annotation tokens still consume budget.

## Handoff conditions

Every successor receives the same issue, image-restored checkpoint workspace, tools,
system/takeover instructions, model route, seed and continuation budgets. Only handoff
representation differs: REPOSITORY_ONLY, FULL_HISTORY, SUMMARY_2K,
STRUCTURED_NOTES_2K or KEISHO_2K. The three compact conditions have a 2,048-native-token
maximum; original issue and common system framing are outside that handoff limit but
inside request/context accounting. FULL_HISTORY remains complete or is reported too
large; it is never silently truncated.

Ordinary and structured notes use the same generator model and complete permitted
predecessor packet, including changed inventory and cumulative patch. The structured
baseline reuses the published seven fields and first-pass prompts from Handoff Debt
commit `5179b1d759be466600c453da8b9078341967ec17`, under MIT license. Adapter 1.1
adds deterministic current-change/latest-post-edit-validation facts and the conditional
author source-change rule; shared `takeover-v2` verification/preservation instructions
apply to all successors. The author already covers uncertainty, observed errors and
verification. These mechanisms are not Keisho novelty.

Adaptations include equal full source packets where the author structured packet
sanitizes/clips/excludes patch text, a matched rendered token cap, local event/exit
interpretation, strict string fields and no author JSON extraction/coercion, contradiction
phrase repair or validation retry. These differences constrain reproduction and any
effectiveness claim. No baseline generation prompts or memory representation changed
in the current sprint. Author-faithful recovery is a later sensitivity study.

## Environment, isolation and official scoring

Agent containers use the immutable prepared image
`sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898`.
The current host is macOS ARM64; Linux amd64 image execution uses existing Docker
emulation. Each container has its own writable layer, no network/host bind mounts,
no privileged mode, dropped capabilities, no-new-privileges, resource limits and
no host credential environment or Docker socket. File tools reject escaping symlinks
and Git metadata. Shell commands operate inside the container. These controls address
specific channels; they do not establish complete isolation against all vulnerabilities.

Repository Git storage is replaced with a shallow official-base-only repository,
without remotes or later solution refs. All successors start from the same frozen
image and verified inventory in fresh message contexts. Audit archives, other branches,
development conversation, gold/test patches, answer-key lists and checkpoint grade are
not passed or mounted. Private evaluator data resides outside agent-visible storage.

Predictions contain `instance_id`, `model_name_or_path` and `model_patch` in official
JSONL format. Patches include cumulative changes from the official base, including
predecessor and successor work, staged/untracked/deleted/binary changes. The separate,
unchanged evaluator installation grades each patch using one worker and a unique
condition/patch/run identifier. Completed commands and an agent's finish declaration
are not official resolution. Results distinguish resolved/unresolved/error from
execution interruption, budget stop and unstarted status.

## Budgets and launch admission

The frozen mapping is mini predecessor/generator
`openai/gpt-4.1-mini-2025-04-14` and full successor
`openai/gpt-4.1-2025-04-14`, via existing OpenRouter aliases and OpenAI-only routing
without fallbacks. No live request occurred under version 1.2. Proposed budget is one
$10 block, subject to a future explicit new authorization and current pricing checks.

Predecessor ceilings are 48 model/36 tool calls and 180,000 combined tokens;
successors have 64/48 calls and 360,000 tokens each. Each request allows 2,048 output,
32,000 input and 128,000 context tokens. Two note requests allow 1,600 output tokens
each. Runtime allows 1,800 seconds, tool deadline 120 seconds and output bound 49,152
bytes. Order is prospectively frozen: FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY,
KEISHO_2K, STRUCTURED_NOTES_2K. Model calls stop on cumulative token/request/time/tool
limits or insufficient/unknown spending reservations; unused budget is not a retry.

History retention makes the call cap an upper ceiling rather than achievable length.
Analytical sensitivity from the 4,227-token first request gives 13–15 moderate-growth
or 10–11 larger-growth predecessor calls. Numeric budgets remain unchanged; a proposed
larger-budget sensitivity is not implemented. Dollar planning includes conservative
uncached usage and fee contingency, and each new request needs reservation headroom.
Reported charges and conservative accounting remain distinct.

The public launcher explicitly resolves configuration, matched plan, new authorization
and unoccupied output path. Exact frozen hashes prevent scientific mutations disguised
as execution metadata. A stable authorization-wide atomic guard prevents duplicate
starts even at different output names. Dry-run checks the same binding/environment
without creating the live guard or invoking a provider. Completed failures remain
guarded. Configuration 1.2 and its pending authorization template are not executable
with paid permission merely because credentials exist.

## Prior pilot disclosure and protocol evolution

Seven earlier exploratory pilot runs on SWE-bench Verified (specifications v1.4 through v2.0,
totaling approximately $0.8893 in actual provider spend / $2.3853 in conservative ledger accounting;
$0.8848 actual / $2.3808 accounted across v1.4–v1.9) stopped early during the predecessor phase
before any successor condition ran:
1. **v1.4** (`runs/swebench-v1.4-five-way-once-001`, $0.0164 actual spend / $0.0257 accounted spend): halted at Call 6
   (`budget_exhausted`) due to conversational context flooding from unbounded file listing.
2. **v1.5** (`runs/swebench-v1.5-five-way-once-001`, $0.1129 actual spend / $0.3341 accounted spend): halted at Call 13
   (`budget_exhausted` at 180k tokens) while inspecting xarray formatting logic.
3. **v1.6** (`runs/swebench-v1.6-five-way-once-001`, $0.1269 actual spend / $0.4103 accounted spend): halted at Call 14
   (`stopped_on_error` / `budget_exhausted`) exceeding the 32k request input ceiling.
4. **v1.7** (`runs/swebench-v1.7-five-way-once-001`, $0.0342 actual spend / $0.0933 accounted spend): halted at Call 8
   (`invalid_run`) due to fatal `read_file` error on misspelled `atomic.py`.
5. **v1.8** (`runs/swebench-v1.8-five-way-once-001`, $0.2694 actual spend / $0.7777 accounted spend): halted at Call 22
   (`budget_exhausted` at 400k tokens) tracing inheritance chains without editing.
6. **v1.9** (`runs/swebench-v1.9-five-way-once-001`, $0.3249 actual spend / $0.7397 accounted spend): halted at Call 29
   (`checkpoint_not_reached`). With `benchmark-agent/5.0` workflow pacing, the predecessor
   diagnosed the bug in `sympy/core/symbol.py` but finished without making a non-test source edit.
7. **v2.0** (`runs/swebench-v2.0-five-way-once-001`, $0.0045 actual spend / $0.0045 accounted spend): halted at Call 1
   (`model_failure`). `openai/gpt-6-sol-20260922` prepended conversational preamble prose before its JSON action,
   failing strict JSON-only decoding with zero retries.

All thirty-five successor conditions across these seven pilot runs remained unstarted. Following
these disclosures, specification v2.1 introduces a robust single top-level JSON reader with Zero-Skip
brace enforcement and conservative wrapper checks, applied identically across predecessor and all five
successor conditions, while preserving byte-identical prompt text, task (`sympy__sympy-20590`), models
(`openai/gpt-6-sol` and `openai/gpt-6-luna` with reasoning effort `"none"`), and the $10.00 cap.

## Engineering validation and planned analysis

Fresh public-command subprocesses on host Python and the evaluator venv reproduce and
fix the historical callback import error. Test-only interpreter injection supplies
explicitly synthetic service responses while preserving real parser, runtime, Docker,
logger and callback paths. A disposable public fixture follows list→read→failing test→
source write→passing post-edit test and independent acceptance. Invalid JSON/actions,
annotations, provider/infrastructure failures and token stops are separately tested.
No synthetic action is reported as model reasoning or research performance.

The five-way public launcher has likewise executed synthetic branches with real Docker
freeze/restore and cumulative exports. Branch grades are explicitly stubbed software
fixtures. Separately, one comment-only checkpoint patch was graded **unresolved** by
the actual official evaluator; no agent effectiveness follows. Historical gold-patch
smoke validation was setup-only. Confirmatory paired metrics, clustered analysis,
multiple model pairs and rejection criteria are prospective in
`research/RESEARCH_PLAN.md`; numerical comparative results remain pending.
