# Keisho protocol 0.1.0

Preregistered before any model experiment. Status: Phase 0 scaffold only.
No empirical results, main-study effect thresholds, or main-study sample size
have been chosen. This protocol preregisters the hypotheses and feasibility
procedure; an explicit prospective amendment is required before Phase 2.

## Research question and intervention

What is the minimal sufficient externally reconstructable task and epistemic
state needed for a successor LLM agent to continue an unfinished task without
rediscovery, repeated failure, or unsupported belief inheritance?

The central eventual comparison is a **fixed handoff representation versus a
successor-conditioned representation**, both compiled from the same
model-agnostic `KeishoState`. This is state transfer across a controlled agent
handoff, not generic memory retrieval. No access to hidden chain-of-thought is
assumed or claimed.

## Hypotheses, fixed in advance

**H1.** A structured Keisho state will outperform a generic summary on
continuation efficiency.

**H2.** The optimal handoff representation depends on the successor model.
Therefore, `SUCCESSOR_CONDITIONED` should outperform or achieve a better
success/token tradeoff than `FIXED_STATE`.

**H3.** Explicitly transferring rejected hypotheses and failed attempts will
reduce repeated errors.

**H4.** Separating evidence from predecessor interpretation will reduce
inherited-error propagation.

**H5.** Full trajectory transfer will not always be the optimal condition
despite containing the most information.

These statements must not be rewritten after results. Prospective amendments
must keep this version, give a reason, identify affected runs, and register
the new version before collecting new evaluation data.

## Stages and stopping points

**Phase 0:** design note, schema, provenance validation, fixed serialization,
external-annotation ingestion, immutable artifact format, run manifests, model
interface, deterministic filesystem environment, metric definitions and offline
tests. Stop and inspect architecture. Native adapters, actual debugging tasks,
summary generation, an agent execution loop, and successor conditioning are
outside this milestone.

**Phase 1 feasibility pilot:** exactly three deterministic debugging tasks;
one exact predecessor model ID and one exact successor model ID; four conditions:

| Condition | Additional handoff content |
| --- | --- |
| `NO_CONTEXT` | Empty; original task and current environment are still supplied |
| `FULL_HISTORY` | Complete externally exposed predecessor trajectory |
| `SUMMARY` | Normal LLM-generated summary using the frozen versioned prompt |
| `FIXED_STATE` | Canonical structured JSON, identical serializer for every model |

Run three repetitions per task/checkpoint, with seeds 17, 29, and 43: nine
paired blocks and 36 successor branches. The pilot tests feasibility; this
sample does not justify significance claims or a claim of model dependence.
API determinism is not guaranteed even when a provider accepts seeds.

Tasks must allow file inspection, tests, code changes, hypotheses, at least one
plausible scoped dead end, and a meaningful unfinished checkpoint. Use hidden
deterministic tests outside successor workspaces. Select checkpoints by a
prespecified count of action steps after separate development calibration,
before evaluating treatment effects. Preserve calibration logs and never pool
them into evaluation. A checkpoint already solved, with no relevant known fact,
failure, or false-belief opportunity is unsuitable for this pilot.

**Phase 2 main intervention:** add `SUCCESSOR_CONDITIONED`, initially using
deterministic rules or a separately logged LLM selector. Compare against the
same extracted state under matched boundary budgets. A single successor can
test a within-model treatment effect, but cannot establish model dependence:
H2's model-dependence claim requires at least two successor identities and a
held-out model/task evaluation plan. Register that plan, effect thresholds,
sample size, token budgets, scoring reliability and analysis before Phase 2.
Do not learn rules or tune profiles on the evaluation branches. H3/H4 require
focused removal ablations after main-pipeline validation. Scale task/model
counts only after a meaningful Phase 2 signal. No training or broad ablations
are planned initially.

## Experimental unit, invariants, and sequence

A block = task/version × frozen predecessor checkpoint × exact successor ID ×
repetition seed. Conditions are correlated branches within that block. Analyze
paired outcomes and report task-level variation. Do not count 36 branches as
36 independent task samples. With three tasks, broad generalization is weak.

1. Reset the predecessor to the deterministic initial task state.
2. Run to the checkpoint fixed before evaluation. A step is one initiated tool
   call or submitted final answer; model calls are recorded separately.
3. Snapshot the **current**, potentially modified environment. Stop predecessor
   execution and seal its complete external event trajectory.
4. Create summary and state from that frozen trajectory alone. Log extractor,
   summary prompt, responses, annotator decisions and costs separately. Task
   grader knowledge and successor results must never enter a handoff.
5. Build every condition from the same checkpoint. Freeze capsules and hashes
   before successor work. Reject over-budget input; never silently truncate
   full history. Reject the entire block as ineligible if any condition cannot
   fit the selected handoff/context cap. Retain the rejected records. This
   restriction limits generalization to checkpoints where history fits.
6. Restore a fresh environment for each condition. Keep original task, tools,
   successor prompt, model settings, seed policy, context/output limits,
   stopping rule, grader and event logging invariant. Condition order may be
   randomized by the registered seed to reduce time/order confounding.
7. Execute independently. Neither sibling artifacts nor raw logs may be read
   by successors. Phase 0 copying is **not** a process/network sandbox; Phase 1
   must restrict tools and isolate subprocesses, caches and any services.
8. Record raw requests/responses, tool inputs/outputs, snapshots, state, summary,
   capsule, manifest, timings, usage, outcome and annotations. Score condition
   labels masked where possible; record any unavoidable unmasking.

The manifest fixes all branch invariants; only run ID, handoff condition,
capsule hash and creation timestamp may differ within a block. A preparation
helper does not itself enforce provider parameter equality at execution time.
The Phase 1 runner must verify actual requests against manifests.

## State and epistemic discipline

`KeishoState` 0.1.0 has a goal, source/evidence registries and separate atomic
categories: constraints (requirement or preference), observations, verified
facts, hypotheses, rejected hypotheses, actions, failed attempts, changes, open
questions, uncertainties, current plan and next actions. Items carry stable
IDs, `OBSERVED`, `VERIFIED`, `INFERRED`, `UNCERTAIN` or `FALSIFIED` status,
source IDs, evidence IDs and scope. All lists, including empty ones, serialize.

Verified claims require declared supporting evidence from external tool/file
events. Rejected hypotheses require external refuting evidence and explicit
retry conditions. Failed attempts preserve failure versus inconclusive result,
scope and retry conditions. Evidence records link to one exact claim and scope.
No statement-similarity merge or confidence threshold promotes a hypothesis.
Only exact stable-ID duplicates merge; conflicting duplicate content fails.
Verified knowledge is checkpoint-scoped and may require reverification after
relevant environment changes. A failed approach is never an absolute ban.

Phase 0 extraction ingests explicit structured annotations and validates their
links to frozen external events. It is not automatic prose extraction. A
validator can establish type, hash and reference consistency; semantic support
and truth require reviewed verification. A tool output can itself be wrong.

## Metric rubric 0.1.0

All rates preserve raw numerator, denominator, labeled event ID, predecessor
reference ID, scope, rationale, adjudicator and rubric version. Positive and
negative eligible opportunities must both be annotated. Labels must refer to
externally exposed actions/assertions, not inferred internal reasoning. A zero
denominator gives `null`. Missing annotation coverage is not zero error.

| Metric | Raw operational definition |
| --- | --- |
| Task success | Hidden grader returns true or false. Infrastructure/model/invalid runs are unscored (`null`); incomplete/wrong task at the fixed step limit is a task failure. |
| Handoff tokens | Successor-native tokens in additional handoff text encoded in isolation, excluding the identical original task/system prompt. Store method and exactness; empty `NO_CONTEXT` adds zero. This measures serialized content size, not marginal billed tokens. Full provider-request tokens/context overhead are recorded separately. |
| Post-handoff steps | Count successor-initiated tool calls plus submitted final answers; exclude tool results, evaluator annotations and model requests. A failed tool call still consumes a step. |
| Rediscovery rate | Redundant investigation of still-applicable knowledge established before handoff / all annotated successor investigation opportunities (tool calls). Reverification justified by changed scope/new evidence is negative. |
| Repeated failure rate | Repetition of a documented failed approach in unchanged scope without meeting retry conditions / all annotated successor approach-attempt opportunities. An inconclusive predecessor attempt alone does not establish known failure. |
| Inherited error rate | Successor treats an annotated unsupported/false predecessor belief as established without fresh supporting evidence / all annotated successor assertion opportunities about such predecessor beliefs. |
| Contradiction rate | Unsupported successor contradiction of applicable verified predecessor knowledge without new evidence / all annotated successor assertion opportunities about verified predecessor knowledge. |
| Time/cost | Branch wall time; per-call stage, exact model ID, request/response IDs, elapsed time, input/output/cached tokens, cost as decimal USD string and pricing source. Preserve unknown usage/prices as `null`. |

An assertion repeating a false predecessor belief is an operational error
alignment, not proof of psychological inheritance. `NO_CONTEXT` supplies an
important background error control. Scorers must distinguish independent
agreement, quoted/rejected claims, valid scope changes, and genuinely new
support. Opportunity denominators can depend on treatment: compare raw counts
and paired task outcomes alongside rates, not rates alone. Do not infer a
causal effect of failure-awareness or provenance from an uncontrolled category
comparison. Record inter-annotator agreement before confirmatory use.

Successor accounting requires one raw call record per request, including
failed calls. Upstream totals remain unknown unless complete call coverage is
explicitly asserted after verifying the parent/extraction/summary logs. Cached
input is a subset of input, never added twice. Report per-stage costs and
allocation of shared predecessor/extraction costs; do not hide preprocessing
costs behind boundary-token savings. Empty/partial accounting is not evidence
that model calls were free.

Continuation efficiency uses paired successor steps and continuation token/cost
at comparable task success; a cheap failure does not count as an efficiency
gain. Inspect success versus handoff-token/total-cost frontiers. The pilot
reports descriptive values only. No composite efficiency score, significance
threshold, or winner-selection rule is chosen after seeing pilot results.

## Failure handling and reproducibility

Separate `complete`, `task_failure`, `model_failure`, `infrastructure_failure`
and `invalid`. Unsupported contexts, broken restoration, mismatched manifests,
missing logs, or tool leakage invalidate a branch/block as appropriate. Preserve
everything with the reason; never count broken infrastructure as model behavior
or discard unsuccessful valid branches. Report exclusion counts by condition.

Store unique run/block/parent IDs, exact model IDs, explicit seeds, prompt/state/
protocol/task/compiler versions, timezone-aware timestamps, dependency lock and
source-tree hashes, original task hash, snapshot/trajectory/capsule hashes and
full configuration. With an uncommitted tree, the tree hash is required even if
a Git revision is absent. Freeze resolved versions of aliases in native adapters.
Retain sealed raw artifacts; derived analysis goes to `runs/processed` and
`analysis`. Raw records may include source code and prompts; export separately.

## What could disconfirm the hypotheses

H1 receives no support if structured state does not improve continuation at
comparable success. H2 receives no support if conditioning fails to improve
held-out frontiers, or reproducible differences do not depend on successor
identity. H3/H4 receive no support if their registered removals do not worsen
repeated failure/error propagation. H5 receives no support in the tested domain
if full history weakly dominates all other conditions. Null results and worse
Keisho outcomes must be retained and reported. The tiny pilot alone cannot
confirm or falsify these general claims.

## Authorization and amendments

Offline tests and synthetic fixtures are authorized. No paid model calls have
been authorized. Keep this version; add future amendments as separate files in
`protocol_amendments/` and reference the applicable version in every manifest.
