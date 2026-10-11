# Frozen exploratory five-way SWE-bench experiment

Prospective experiment `swebench-handoff/1.4`, prepared 2026-10-11. This document
specifies one new predecessor attempt and, if it reaches the registered checkpoint,
five independent successor branches. **No inference, benchmark run, or spending is
authorized by this specification.** The successful v1.3 public functional fixture
is interface evidence, not a SWE-bench outcome. Historical attempts remain closed.

The executable specification is [swebench-comparison-v1.4.json](../configs/swebench-comparison-v1.4.json),
with its matched [launch plan](../analysis/swebench-comparison-v1.4-plan.json).
The final offline report records their hashes and the implementation freeze.
Runtime component pins are recorded in
[swebench-experiment-v1.4-manifest.json](../analysis/swebench-experiment-v1.4-manifest.json).
Version 1.4 adds a shared annotation-guidance prompt supplement and a clean,
audited cumulative patch exporter. It retains the action contract, annotation
format and validation policy, task, models, budgets, checkpoint, five memory
representations and grading. It does not retroactively reinterpret v1.3 responses.

| Admission / interface pin | Frozen Keisho digest |
| --- | --- |
| v1.4 config | `e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f` |
| v1.4 launch plan | `60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff` |
| Runtime component manifest | `b1bd32a720c195fadc92b2e39818a3f4a3a1cb1d633abfe639358fc523f461cd` |
| Shared agent prompt | `4f99b6495be87680583af9460943a26fbd389ee017007e289e7fbe1a5dfc527d` |
| Annotation guidance | `4355a256a11dc729a2c6d35e95b770ae041777a1c96d19217003222406f25d1e` |
| Wire action schema | `b17d5737b9f67e70f8b21ea6e7d27a800b726acee86d4fe1b88f7e975e678d95` |
| Internal action schema | `48af7498236adb94a9e291c17269239ef998c1eda977dfd13e7dc1c14da73388` |

These are SHA-256 of Keisho's canonical JSON values (`keisho.core.digest`), including
canonical JSON string encoding for prompt text. The runtime manifest separately
pins raw file-byte SHA-256 hashes; do not interchange the two hash conventions.
The admission module records the exact config/plan pair and verifies mechanism
files on load. Its own final source hash is in the final-source freeze, outside
this manifest to avoid a circular digest.

## Task, source pins and selection

| Field | Frozen value |
| --- | --- |
| Dataset | `princeton-nlp/SWE-bench_Verified` |
| Dataset revision | `c104f840cc67f8b6eec6f759ebc8b2693d585d4a` |
| Task | `pydata__xarray-6721`, repository `pydata/xarray` |
| Official base commit | `cc183652bf6e1273e985e1c4b3cba79c896c1193` |
| Public task digest | `1ece7acf4065ac5399dfc0781af941c52b5498c5192e51fcf4d3bd59512bf125` |
| Official harness | SWE-bench `5.0.2`, commit `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` |
| Official task recipe commit | `3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d` |
| Handoff Debt code commit | `5179b1d759be466600c453da8b9078341967ec17` |
| Prepared agent image | `sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898` |
| Image platform | `linux/amd64`, local ARM Docker Desktop emulation |

The public issue concerns accessing chunk metadata on a lazily backed xarray
dataset. The model receives the verbatim archived issue, rather than a rewritten
task or a suggested fix. Public input fields are only `instance_id`, `repo`,
`base_commit`, `problem_statement`, `version`, `difficulty` and `created_at`.

Selection was frozen before predecessor model outcomes: start with the pinned 500
Verified rows, exclude the setup-only `sympy__sympy-20590` and rows outside the
published `15 min - 1 hour` / `1-4 hours` tiers, sort the remaining instance IDs,
then use Python `random.Random(20260430).shuffle`. Select the first ID once. The
saved selection has 302 candidates and 198 exclusions; do not regenerate it or
choose the next task after failure. The source evidence is
[selection.json](../runs/swebench-integration/preselection/selection.json),
[task.json](../runs/swebench-integration/preselection/task.json) and
[the original selection plan](../runs/swebench-integration/preselection/plan.json).
The task has since been inspected during development and belongs to the
exploratory development set, not a future held-out confirmatory set.

The published reference is [Handoff Debt, v2](https://arxiv.org/html/2606.02875v2)
and its [pinned released implementation](https://github.com/anjilab/agent-handoff-debt/tree/5179b1d759be466600c453da8b9078341967ec17).
This experiment adapts its four views to Keisho's existing text-action runner;
it does not reproduce the author's OpenHands runtime or model profiles. The
substantive baseline features and declared deviations are frozen in
[BASELINE_COMPARISON.md](BASELINE_COMPARISON.md).

## Models, routing and identity

| Role | Canonical identity | OpenRouter request alias |
| --- | --- | --- |
| Predecessor | `openai/gpt-4.1-mini-2025-04-14` | `openai/gpt-4.1-mini` |
| Summary / structured generator | `openai/gpt-4.1-mini-2025-04-14` | `openai/gpt-4.1-mini` |
| Every successor | `openai/gpt-4.1-2025-04-14` | `openai/gpt-4.1` |

Use the existing provider configuration
[calibration-task001-openrouter-v1.2.0.yaml](../configs/calibration-task001-openrouter-v1.2.0.yaml).
Routing is `only=["openai"]`, `order=["openai"]`, `allow_fallbacks=false`,
`require_parameters=true`; price ceilings are the frozen input/output rates with
zero permitted request charge. No automatic model selection, model list,
alternate provider, native/server tools, plugin or retry is allowed. Both public
aliases and their catalog-confirmed exact canonical IDs may be returned; the
returned upstream provider must be `OpenAI`. A different ID/provider is a stopped
attempt, not an invitation to substitute a model. Snapshot attestation is absent:
these checks establish catalog/service identity, not a cryptographic physical
snapshot guarantee. Archive request/response IDs, provider and any fingerprint.

Before any future authorized execution, recheck unauthenticated public prices,
alias-to-canonical mapping, exact OpenAI endpoint, required parameters and limits.
If they differ from the pins, refuse execution and require a prospective amended
plan; do not spend a credential-validation or model-smoke call. TLS and hostname
verification use the pinned CA. Temperature is `0.0`, seed `20261007`, streaming
disabled. Agent generation remains `{"type":"json_object"}`.

## Shared agent interface and annotation policy

Predecessor and **all five successors** use the same `benchmark-agent/4.0` prompt,
`annotation-guidance/1.0` supplement, `auxiliary-claims/2.0` annotation parser,
wire action schema `4.0`, internal schema `3.0`, `flat-or-args/1.0` adapter,
`bounded-listing/1.0` and runtime `agent-runtime/3.2`. The only successor prompt
addition is the unchanged published takeover guidance shared by every condition.

The model emits one object with `action` and `claims`. The five tools are bounded
`list_files`, `read_file`, `write_file`, `shell` and `finish`. Each action accepts
the existing flat documented arguments or an exclusive `args` object containing
those same arguments. The shared deterministic adapter preserves the raw response
and records shape, canonicalization, canonical action, validation and rejection;
it never fills missing arguments, invents actions or retries rejected output.
Unknown tools/arguments, ambiguous duplicate locations, invalid types, unsafe
paths and unauthorized operations reject under the same policy for every role.

`claims` remains an auxiliary array of at most eight annotations. The unchanged
basis values are `tool`, `predecessor`, `independent`; declared status is one of
`OBSERVED`, `VERIFIED`, `INFERRED`, `UNCERTAIN`, `FALSIFIED`. The v1.4 supplement
defines `tool` as reliance on completed results in this conversation, including
inferences from them; `predecessor` as an inherited report not re-observed; and
`independent` as the model's own reasoning/proposal without claimed tool support,
not independent verification. Basis is provenance; status is the assertion's
epistemic character. It gives examples and distinguishes evidence available before
the proposed action from an action that has not yet completed. It does not add
observed invalid labels to the enum or silently map them to evidence. The referenced result IDs must
already be available to that conversation. Historical handoff IDs are provenance,
not fresh tool results. Annotation acceptance establishes contract conformance
and available references, not entailment, truth or current validity. The unchanged
extractor retains model claims as interpretations and independently imports
observable tool facts. Invalid annotations remain in raw archives/diagnostics and
are excluded from validated annotation state. No condition gets recovery behavior.

Offline archived-response analysis is **retrospective compatibility analysis**.
Unchanged old/new acceptance counts do not measure prompt compliance improvement.
Real-model annotation reliability under the supplement remains unverified until
new, explicitly authorized model responses are measured.

## Checkpoint and budgets

The checkpoint is the **first completed validation/build/lint/test command result
following a previously completed non-test source edit**, recognized by the pinned
Handoff Debt source-file heuristic plus the existing local executed-command-head
adapter. The recorded exit code may be zero or nonzero. The rule does not wait
for a passing test or an official grade. An edit and validation within the same
shell action have unknown internal ordering: record the edit, then require a
subsequent completed validation action. Timeout, unknown completion, background
process and rejected action boundaries do not qualify.

The operational head recognizer is **lexical**, not subcommand execution
attestation. It recognizes command heads in shell compounds and records the
completed shell process's overall exit/output; `false && pytest` can qualify even
though short-circuiting prevents pytest from running. Checkpoint eligibility
therefore does not establish that tests actually executed. This existing rule
remains frozen; archive the exact command/result and treat this as a limitation,
rather than repairing the checkpoint after an outcome.

| Budget | Predecessor | Each successor |
| --- | ---: | ---: |
| Model call ceiling | 48 | 64 |
| Tool call ceiling | 36 | 48 |
| Output tokens per response | 2,048 | 2,048 |
| Cumulative input + output tokens | 180,000 | 360,000 |
| Input tokens per request | 32,000 | 32,000 |
| Context tokens | 128,000 | 128,000 |
| Elapsed agent seconds | 1,800 | 1,800 |

Each tool has a 120-second timeout and 49,152-byte result ceiling. Listings have
at most 100 entries / 8,192 path bytes per page. Call ceilings are upper bounds,
not promised call counts: retained history and full-output reservation can hit
the cumulative/input limits earlier. The budget gate accounts for the next full
output cap before transmission. No history removal, context rescue, enlarged
budget, extra predecessor or checkpoint resampling is permitted.
The prospective first predecessor request upper bound is 4,782 native/framing
tokens in the frozen launch plan; guidance changes prompt overhead, not budgets.

If the predecessor finishes, fails, times out or exhausts budget before the
checkpoint, archive its terminal cumulative patch and exact stop reason with
`eligible=false`, `resampling=false`; all five branches remain `unstarted` and
ungraded. Report checkpoint yield as 0/1 attempted blocks. Do not call that five
successor failures, replace the task, or omit the attempted block from reporting.

## Five handoff procedures and matched compact limit

Every successor gets the same original issue and the same frozen checkpoint
container image. Additional handoff input alone differs:

| Condition | Frozen procedure |
| --- | --- |
| `REPOSITORY_ONLY` | Empty handoff framing message; issue and checkpoint workspace only. |
| `FULL_HISTORY` | Canonical JSON of the complete permitted observable predecessor archive. No hidden reasoning or official grade. |
| `SUMMARY_2K` | One first-pass mini-model call using the pinned published summary prompt and the common permitted evidence packet; nonempty plain summary text. |
| `STRUCTURED_NOTES_2K` | One first-pass mini-model call using the pinned seven-string published structured prompt and `structured-adapter/1.1`; render generated fields with deterministic continuation facts. |
| `KEISHO_2K` | Existing observable state import, named-file scope comparison and unchanged deterministic `compact/1.0` compiler; no generation call. |

Both model-generated notes see the identical packet: original issue, complete
permitted observable predecessor events, changed-file inventory, deterministic
continuation facts and cumulative predecessor patch. No hidden answer or grade
appears. Each generation call has ≤32,000 input and ≤1,600 output tokens; two
calls total, no second pass, JSON recovery, semantic replacement or coercion.
Structured fields remain `problem_understanding`, `work_completed`,
`evidence_observed`, `observed_failures_or_error_evidence`,
`remaining_uncertainty`, `rollback_notes`, `recommended_next_action`.
UNKNOWN/NONE OBSERVED and invocation-versus-result guidance remain intact.

`SUMMARY_2K`, `STRUCTURED_NOTES_2K` and `KEISHO_2K` must each fit **at most 2,048
native tokens including all rendered headings/metadata**; they are matched
ceilings, not padding to identical lengths. Keisho keeps whole items and records
omissions; required linked conflict/supersession items or essential-header overflow
fail explicitly. Summaries/notes are never silently clipped. `FULL_HISTORY` has
no 2K ceiling, but shares the 32K input and cumulative successor limits. A packet,
rendered handoff or full-history overflow stops the existing block before branch
launch, with all actual generator calls/costs retained and branches unstarted.
This all-or-stop generation behavior is a declared limitation, not a favorable
selection rule.

The author's runtime, history clipping/sanitization and structured-generation
recovery differ from this local adaptation. Their baseline already includes
uncertainty, evidence/result distinctions, historical/current failures, deterministic
continuation facts and verification guidance. Do not portray those as Keisho-only
features. Do not change prompts, compact priorities, extractor state format or
baseline procedures after seeing this block's outcomes.

## Isolation and information-leakage boundaries

The predecessor starts at the official base with a shallow one-commit Git history,
no remote, no later Git refs. Each successor starts in a fresh independent writable
container from the single frozen image and verifies its inventory against the
checkpoint inventory before acting. Branches have separate message arrays, raw
runs, calls, patches and evaluator namespaces. No branch sees another branch's
work or outcome. No work is cherry-picked between branches.

Agent containers have no host bind mounts, credentials, Docker socket, evaluator
files, archive lookup, or network; capabilities are dropped and privileges are
disabled. Agents see public repository files and installed task dependencies.
Shell runs inside the isolated testbed. File tools enforce relative paths,
containment and symlink restrictions. These are concrete isolation controls,
not a claim of exhaustive adversarial containment.

Gold patch, hidden test patch, `FAIL_TO_PASS`, `PASS_TO_PASS`, official evaluation
scripts/keys and private logs stay controller-side. The pinned dataset/task recipe
equality check emits only booleans. Notes are built before checkpoint grading;
checkpoint grading never enters notes, model messages, stopping or selection.
Successor grades cannot affect other branches. Existing setup gold/unpatched
checks are admission evidence only. The supervisor has development-task knowledge;
this task cannot later count as held out. No explicit baseline oracle is available.

Branch order remains the archived result of
`random.Random(20261007).sample(conditions, 5)`:
`FULL_HISTORY`, `SUMMARY_2K`, `REPOSITORY_ONLY`, `KEISHO_2K`,
`STRUCTURED_NOTES_2K`. The shared dollar ledger and fixed order can create attrition;
retain this order and report it. Do not shuffle after results or selectively spend
remaining funds on a favored condition.

## Cumulative patches and official grading

Export every checkpoint/terminal successor patch from the **official base**,
including predecessor changes, successor changes, additions and deletions; do
not export only successor deltas. Use prospective `source-and-artifacts/2.0` in
the real exporter with recorded exclusion inventory. Generated bytecode/caches
are excluded even when ignored or untracked. Relevant new source and ordinary
task artifacts remain eligible; unsafe path/symlink or export/format failure is
explicit, rather than silently dropping an unknown change. Archive the raw patch,
base commit, export policy, exclusions and hash. Preserve the old v1.3 dirty patch
as historical evidence.

Export uses a temporary index and disables configured Git clean/smudge/process
filter drivers, required-filter flags, hooks, fsmonitor and automatic CRLF
conversion. It then independently compares staged blob identities and file modes
with actual worktree bytes and Git-representable modes (regular executable or
nonexecutable, or symlink), including link bytes for permitted symlinks and
deletions. If Git attributes or staging still transform bytes or modes, reject
the whole export with mismatched paths recorded; do not silently normalize source
or discard legitimate changes. Changed tracked paths matching the cache exclusions
also reject for explicit review. Archive disabled filter keys and the raw-byte/mode
preservation check alongside path exclusions. Attribute-dependent repositories can
therefore stop at export even if the intended edit is useful; such rejection is a
declared limitation, not task nonresolution or permission to improvise an exporter.

For each exported diff, verify the intended changed-path inventory and absence of
excluded paths. Independently verify official-base application with a separate
temporary index loaded from the official base and `git apply --cached --check`;
this does not rewrite the agent worktree or index. The offline regression fixture
also applies the real exported patch in a fresh base clone and inspects the result;
that fixture is not an additional runtime branch. Inspect any binary hunk explicitly;
use the official evaluator's unmodified patch application behavior. Do not claim
format compatibility implies behavioral correctness. Verify branch restoration
and cumulative coverage before interpreting an official grade.

Use the unchanged official [SWE-bench evaluator](https://www.swebench.com/SWE-bench/guides/evaluation/)
through the pinned dedicated venv: prediction JSONL has exactly `instance_id`,
`model_name_or_path`, `model_patch`. The existing bridge invokes
`.cache/swebench-evaluator/venv/bin/swebench eval
.cache/swebench-evaluator/selected-task-evaluator.jsonl -i pydata__xarray-6721
--run-id <unique-private-id> -j 1 -p <prediction.jsonl>`.
Archive command, exit status, timestamps, reports and logs. Grade the checkpoint
once after handoffs and each launched successor's final cumulative patch once:
up to six official evaluations, with no repeated grading rescue. Gold/reference
patches are never predictions for agent branches. A nonzero/missing harness report
is `error`, not `unresolved`. An explicit unstarted branch has no grade. Budget-stop
and model-error branches may retain useful patches: grade the actual exported
patch when the runner completes its export/evaluation path, retaining both the
execution stop reason and official result. An exception before that point remains
launched/ungraded; do not invent its grade or rerun it.

The official harness applies the prediction and its private test/evaluation
procedure, parses the repository's test results, and classifies full resolution
when its fail-to-pass resolution metric and pass-to-pass maintenance metric both
equal 1. Retain the official report's classifications and parser behavior; do not
replace them with public-test exit codes, model claims or local acceptance checks.
Its internal application/error-handling behavior is unchanged; the one-invocation
rule forbids launching a second evaluation to rescue a recorded outcome.

## Metrics, annotation coverage and interpretation

Primary descriptive contrast is official resolved status for `KEISHO_2K` versus
`STRUCTURED_NOTES_2K` on this shared **unresolved** eligible checkpoint. If the
checkpoint is already resolved, report preservation instead of claiming new
resolution. Present all five actual statuses alongside checkpoint eligibility and
the supervisor-only checkpoint classification. Denominators are one selected
task, one attempted predecessor, five assigned conditions, actual branches
launched, and actual graded branches; never exchange them.

Secondary metrics are model/tool calls, actual input/output tokens, handoff native
tokens, note-generation cost, per-branch continuation cost, shared predecessor
cost, whole-block cost, elapsed time, completed post-edit public validation,
patch/path counts, export exclusions, action shape/canonicalization, invalid
JSON/action/safety/annotation components, and infrastructure/provider/budget
interruptions. Report provider-returned total API cost separately from conservative
uncached accounting; missing usage remains missing with retained reservation.
All launched branches contribute to efficiency reporting. Solved-only cost is an
explicitly selection-biased descriptive supplement.

For predecessor and each branch, report received responses / transmitted requests,
responses with any supplied annotation, responses with any accepted annotation,
responses with rejected annotations, and individual supplied/accepted/rejected
annotation counts. Use actual received responses for response validity rates,
individual supplied annotations for annotation rejection rates, and separate
missing/unparseable denominators. Empty `claims=[]` is valid but supplies zero
annotations; it is not evidence of reliable substantive coverage. Report basis,
status, rejection-reason and unsupported-reference counts. Preserve raw annotations
and diagnostics. Compare extractor observable items to accepted model annotation
items and report compiler selected/omitted items plus essential overflow. Rejected
annotation rate is not false-claim rate or lost-state rate.

Derive these coverage counts from each archived `response-measurements.json` row's
annotation report/diagnostics and original claims array, plus the state import's
`annotation_coverage`; they are not all emitted as a single precomputed summary.
Do not infer supplied-annotation coverage from response-validity alone. Count
unparseable responses separately and keep every raw response available for audit.

Semantic reuse/rediscovery/repeated-failure/scope-revalidation metrics require a
fixed rubric, source-event citations and independently blinded adjudication of
all eligible opportunities, including negatives. Repeating a command can be
necessary revalidation. This launcher does not manufacture those judgments;
unreviewed semantic metrics remain unmeasured/model-assisted, not zero. Tool facts
and model claims can contradict; provenance checks do not resolve arbitrary
semantic contradictions. Named-file hashes do not establish dependency-complete
scope or freshness of environment facts.

## Stopping, limitations and evidence against Keisho

Early finish, no checkpoint, call/token/tool/time exhaustion, action rejection,
note failure/overflow, provider identity mismatch, unknown usage, insufficient
reservation, export failure and evaluator failure are distinct recorded outcomes.
There is one attempt, no retries or guard reset, no resampling and no outcome-based
configuration changes. If a common stop prevents later branches, retain their
`unstarted` status and missing grade. For an optional operational-success sensitivity,
count **launched ungraded** branches as nonresolution while also preserving their
actual statuses; never silently count unstarted branches as failed tasks.

One task and one trajectory give one paired block, not five independent samples.
Do not report significance, general superiority, confidence intervals pretending
five branches are five tasks, or a reliable effect size. Prior development exposure,
task memorization, strict local first-pass baseline adaptation, small checkpoint
information, model/prompt interaction, history overflow, heuristic source/checkpoint
recognition, incomplete annotation coverage, scope limitations, ordering and local
emulation remain threats. A positive single-task contrast is exploratory evidence
for designing a larger held-out study only.

Evidence against the proposed benefit includes Keisho unresolved while structured
notes resolve; failure to preserve an already-resolved patch; higher total work or
cost without a resolution benefit; essential overflow or omissions of task-relevant
state; and audited unsupported reliance on stale evidence despite available scope
flags. Equal resolution with no measured mechanism improvement supplies no support
for a superiority claim. If apparent savings arise from rejection, budget failure
or less useful work, they do not establish efficiency. Low annotation coverage can
limit mechanism exposure without proving that rejected claims were false. A
checkpoint/generation failure leaves the comparison inconclusive and remains part
of reported operational yield.

## Future authorized launch

The proposed API cap and stage allocations are in
[FIVE_WAY_COST_PLAN.md](../analysis/FIVE_WAY_COST_PLAN.md). Fresh authorization
must bind exactly the v1.4 config and plan hashes, one attempt, a new authorization
ID, ≤$10.00 total provider API usage and the complete five-way block. Historical
functional or benchmark scopes do not authorize it. Create a fresh ledger and
atomic guard through the existing launcher; never reset one. Public catalog checks
must pass again immediately before launch. The command is provided for future
approval and **has not been executed**:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.4.json \
  --plan analysis/swebench-comparison-v1.4-plan.json \
  --authorization analysis/swebench-comparison-v1.4-authorization.json \
  --run-dir runs/swebench-v1.4-five-way-once-001 \
  --approve-live
```

If the named run destination exists or authorization was claimed, the launcher
must refuse. A new destination does not restore a consumed authorization. No
functional-confirmation rerun is part of this block.
