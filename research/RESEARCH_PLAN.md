# Research plan: observable state at coding-agent handoff

Version 0.1, 2026-10-11. Model-assisted prospective design, not preregistered or
human-reviewed. No new inference spending, tasks or experiments are authorized by
this document. The current one-task configuration is exploratory development.

## Question and positioning

Does a compact, deterministically selected record of observable work, item
provenance and named-file revalidation flags help a successor continue a frozen
coding task, compared with ordinary summaries and careful structured notes?

[Handoff Debt v2](https://arxiv.org/html/2606.02875v2) supplies the takeover framing
and four baseline views. Keisho adds a fifth compact representation and a narrow
scope/provenance mechanism, not a new primary benchmark. Its actual baseline
coverage and adaptations are documented in [BASELINE_COMPARISON.md](BASELINE_COMPARISON.md).
[SWE-bench](https://arxiv.org/abs/2310.06770) supplies real repository issues;
[Verified](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified) and the
[official evaluator](https://www.swebench.com/SWE-bench/guides/evaluation/) supply
task and grading provenance. Do not call this an exact Handoff Debt reproduction
or leaderboard result.

## Hypotheses and rejection

- **H1, primary:** KEISHO_2K improves official resolution over
  STRUCTURED_NOTES_2K at identical continuation budgets on unresolved checkpoints.
  Reject an improvement claim if the paired difference is nonpositive, uncertainty
  does not exclude no improvement, or an apparent gain depends on ignoring
  ungraded/interrupted assignments. A positive one-task difference is insufficient.
- **H2:** Keisho lowers total inference cost/tokens needed for useful continuation
  without materially lowering resolution. Count annotation and generation costs.
  Do not select only successful branches for the primary efficiency analysis.
  Reject efficiency claims if costs grow or savings reflect early failure/no work.
  Any noninferiority margin must be chosen before confirmatory inference and power
  analysis; none is established by current observations.
- **H3, mechanism:** item references and scope flags increase appropriate evidence
  reuse/revalidation and reduce unsupported reliance on stale scoped observations.
  Reject this explanation if blinded review finds no such change or if the
  corresponding ablation preserves the entire effect. Missing annotations reduce
  exposure; missing opportunities make this metric N/A.
- **H4, exploratory:** representation effects differ by predecessor/successor pair.
  Require an interaction contrast across pairs. A positive result on one pair does
  not establish a model-dependent handoff benefit.

## Unit, eligibility and sampling

The source **task** is the independent sampling unit. A frozen predecessor
trajectory/checkpoint forms a paired block with five successor branches. Branches,
multiple checkpoints and repeated seeds are not additional independent tasks.

Use SWE-bench Verified at a pinned revision. Select tasks reproducibly using public
metadata and an archived order/seed before model outcomes. Record environment
exclusions, not favorable-trajectory resampling. Exclude setup-only and development
tasks from a later held-out confirmatory pool, including the already inspected
`pydata__xarray-6721`. Retain no-checkpoint outcomes as predecessor eligibility
yield. A frozen workspace is classified by the official evaluator only after notes
are constructed; this classification never enters model inputs or checkpoint
selection. Unresolved checkpoints test completion; resolved checkpoints test
preservation and are reported separately.

The implemented checkpoint is first completed validation/build/lint/test result
following a prior non-test source edit. Passing or failing results qualify.
Timeouts and unknown within-action edit/validation ordering do not. The rule is
based on command interpretation and observable changes, not hidden correctness.
Budgets are recorded before inference; no eligible checkpoint means stop, not
another predecessor attempt. Full-history overflow is explicit, never truncation.

## Conditions and controlled variables

| Condition | Handoff input beyond issue and identical workspace |
| --- | --- |
| REPOSITORY_ONLY | None; invariant empty framing message |
| FULL_HISTORY | Complete permitted observable predecessor history |
| SUMMARY_2K | Competent model-generated ordinary summary, ≤2,048 native tokens |
| STRUCTURED_NOTES_2K | Published seven-field schema plus deterministic continuation facts, ≤2,048 |
| KEISHO_2K | Existing deterministic compact compiler output, ≤2,048 |

Equalize generator model and source packet for generated compact notes. Report
adaptations and generator failures; do not silently improve Keisho or impoverish
the ordinary summary. Freeze successor model, service routing, shared takeover
prompt, action/output policy, tools, workspace image, budgets, stopping, scoring,
seed and branch order. Independent fresh containers and message arrays prevent
cross-branch context reuse. Complete audits/private grades/gold and test patches,
answer-key lists and later Git refs stay controller-side.

## Multiple model pairs, later

A concrete initial factorial extension uses the two existing frozen model mappings:
mini→full, mini→mini, full→mini, full→full, where mini is
`openai/gpt-4.1-mini-2025-04-14` and full is `openai/gpt-4.1-2025-04-14` under the
verified route. Each successor condition within a block retains the same model.
For each predecessor mapping, generate one independently frozen trajectory per
task/seed, then use that same checkpoint for both successor mappings. No successor
sees the other pair's outcomes. Freeze output mode uniformly across all conditions
of each study; generator identity remains constant and separately costed.

This crosses direction and capacity within one family; it cannot support
cross-provider/family generalization. A subsequent independently authorized,
prospectively pinned second family would be required for that claim. Do not select
a new model because an exploratory output looks better. Record both requested and
returned IDs/routing; service identifiers are not physical snapshot attestation.
Any pair with unavailable routing is unavailable, not silently substituted.

## Metrics and analysis

Primary outcome: official resolved/unresolved status on eligible unresolved
checkpoints, paired KEISHO_2K versus STRUCTURED_NOTES_2K. Also report preservation
rate on already-resolved checkpoints, predecessor checkpoint yield, and all
protocol/provider/infrastructure/budget interruptions with assignment denominators.
An unstarted branch has no grade and is never a task failure.

Secondary outcomes: model/tool calls; cumulative actual input/output tokens;
handoff tokens; note-generation, continuation and shared predecessor cost;
end-to-end block cost; wall time; post-edit validation; scope revalidation; and
inspectable reuse/repetition examples. Provider charges and conservative uncached
accounting are separate. Unknown usage stops later calls and remains missing.
JSON syntax, action schema, safety/admission and auxiliary annotations receive
separate invalid counts/rates over **actual responses received**. Missing responses
have a separate denominator. Action attempts, completed tools and successful tools
are not interchangeable; a nonzero public test is legitimate evidence collection.

Report paired differences and intervals, not five unpaired leaderboard scores.
For the initial confirmatory primary contrast, use exact paired binary analysis
(e.g. McNemar discordant pairs) and task-cluster bootstrap intervals. For the
factorial extension, estimate within-task effects by pair and a representation×pair
interaction with task clustering; use a prespecified mixed logistic model only if
sample/discordance supports it. Repository effects and repeated seeds remain
clustered. Do not infer significance from branch count. Correct a declared family
of secondary contrasts (e.g. Holm); label post hoc explorations.

Choose task count from a separate development pilot's paired discordance/power
simulation, effect threshold and feasible costs **before** held-out execution.
No credible effect size or sample requirement is currently measured. Fix exclusion,
missingness and interruption treatment prospectively; include a sensitivity that
treats launched ungraded branches as nonresolution for operational success, while
retaining their true status. Budget-stopped patches can still receive official
grades. Model-error branches can also leave useful patches; score actual patches,
not declarations. Efficiency includes all launched branches; solved-only costs
are a clearly labelled descriptive supplement subject to selection bias.

Semantic metrics require a blinded rubric with two reviewers on a sampled subset,
agreement/adjudication and source-event citations. Until that exists, mark judgments
model-assisted. Repeating a command can be necessary verification; matching a
mistake does not prove inherited belief. Scope opportunities should specify file
hash changes and relevant evidence without using gold answers to construct notes.

## Ablations and threats

Later, separately budgeted ablations: remove item references; remove revalidation
flags; remove epistemic labels; replace whole-item priority with a prospectively
fixed alternative; compare supported tool facts alone with facts plus auxiliary
claims. Keep budgets/source material equal. Measure annotation coverage, compiler
omissions and essential overflow. Do not add these conditions to the current run.
Compare an author-faithful recovery/sanitization baseline in a distinct sensitivity
study, with all generation attempts/costs recorded.

Threats include task memorization and development contamination; checkpoint
eligibility/survivorship; low-information or already-solved checkpoints; mode/model
interaction; provider alias drift; strict local rejection; imperfect command/test
recognition; narrow file scopes and unavailable dependencies; lossy import;
summary generation variability; tokenization/context overhead; compiler heuristic;
long FULL_HISTORY overflow; baseline adaptation; Docker emulation/timeouts; ordering
and shared-budget attrition; incomplete upstream telemetry; and annotation scarcity.
Freeze branch order before outcomes and use enough shared reservation headroom;
report unstarted branches separately. Infrastructure controls mitigate specific
channels but do not justify a claim of complete isolation.

## Current evidence and next authorized execution

There is no real five-way outcome. Closed real attempts stopped before a checkpoint.
Small output-mode probes and an incomplete public fixture are exploratory; the
latest one-action functional run crashed in the acceptance callback. New public
subprocess/Docker tests now exercise the full path with explicitly synthetic
provider decisions. Official smoke tests validate grading, not agent effectiveness.

Version 1.2 retains numeric benchmark budgets; its separate sensitivity review
shows 13–15 moderate-growth or 10–11 larger-growth predecessor calls, not guaranteed
48. This plausibly permits targeted investigation/edit/test but cannot guarantee
meaningful progress. A proposed 240,000-token alternative is unimplemented and
requires a new amendment/plan and whole-block price review. Before any real run:
fresh explicit spending scope, selected frozen specification, final offline checks,
public route/pricing/environment checks, then one new trajectory under its rule.
No in-run budget rescue or favorable resampling.
