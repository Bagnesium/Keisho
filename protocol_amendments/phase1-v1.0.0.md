# Prospective Phase 1 amendment 1.0.0

Registered 2026-10-03 before any paid API request, real-model predecessor run,
or successor evaluation. Applicable protocol: `0.1.0+phase1.1.0.0`.
This supplements PROTOCOL.md 0.1.0. Hypotheses H1–H5 and the Phase 2 boundary
are unchanged. Scripted development tests are not empirical outcomes.

## Frozen infrastructure and one genuine defect

`phase0-freeze.json` records protected source, tests and historical documents.
Only `src/keisho/state/schema.py` and `validator.py` change among protected files.
State 0.1.1 preserves every category/field, permitting UNCERTAIN rejected
hypotheses alongside externally supported FALSIFIED rejections. Version 0.1.0
retains its stricter validation; the existing compiler/serializer is unchanged.

The defect exposed by automatic projection is epistemic: a predecessor's declared
rejection is observable, but it is not independent proof of refutation. Forcing
every rejection into FALSIFIED either launders model certainty or discards useful
information. Version 0.1.1 preserves such rejections as UNCERTAIN, with sources,
reason and retry conditions. Verified facts still require external support.
No gold-dependent causal promotion is allowed.

## Registered experiment and prompts

Exactly task_001, task_002 and task_003, each version 1.0.0; predecessor
`openai/gpt-4.1-mini-2025-04-14`; successor `openai/gpt-4.1-2025-04-14`.
SUMMARY reuses the predecessor identity. Seeds 17/29/43 define nine paired
blocks, each with NO_CONTEXT, FULL_HISTORY, SUMMARY and FIXED_STATE. Maximum
initial pilot: 36 successor branches. Failed/ineligible blocks are not resampled.
No successor conditioning, embedding, additional memory or model ensemble exists.

OpenAI follows local default provider configuration. No API key was available;
authenticated access and snapshot availability are unverified. Desktop login is
not an API key. Actual resolved identities and system fingerprints are recorded;
API seeds are best effort, not a determinism guarantee.

The common external action/claim prompt is `agent-v1.0.0.txt`; predecessor adds
`predecessor-v1.0.0.txt`. SUMMARY uses unchanged `summary-v0.1.0.txt`, maximum
1,024 output tokens. The old Phase 0 successor prompt remains historical/unused.
Exact prompt text and hashes are in `analysis/pilot-manifest-v1.0.0.json`.

Every agent call receives system prompt, original task and an additional handoff
message (empty for NO_CONTEXT). FULL_HISTORY is canonical JSON of every frozen
external event. Exact cumulative requests are retained as raw artifacts; events
reference their hashes instead of duplicating previous messages. SUMMARY is one
logged free-form model response from the frozen event list alone. FIXED_STATE
uses existing canonical serialization of `gold-blind-projection/1.0.0` state.
Neither summary nor state reads gold or successor results. No capsule is truncated.

## Checkpoints and eligibility

Scripted development calibration selects nine initiated tools per task because
those retained traces contain a named passing diagnostic probe, exposed hypothesis,
demonstrated failed approach, relevant inspection and unresolved tests. This is
derived from scripted investigations, not knowledge of real-model behavior.

Eligibility requires the registered cutoff, a scoped gold fact established by
tool evidence, an exposed hypothesis, falsifying evidence or demonstrated failed
path, unsolved public/hidden grading, and no exact registered correct explanation
asserted as VERIFIED. Solved/uninformative checkpoints are rejected; the pilot
halts and retains records. No automatic replacement seed or cutoff adjustment.

Mechanical checks cannot identify every almost solved explanation in other words.
Real-model development calibration and trajectory/source review are required
before calling the 36-branch evaluation scientifically clean. Any cutoff/prompt/
task/rubric change needs a new prospective version before evaluation. Calibration
is separate from evaluation and cannot optimize observed treatment outcomes.
The implementation does not certify that review occurred; current readiness is
explicitly not cleared.

## Lifecycle, isolation and failures

Reset; investigate; stop; snapshot current content/modes; seal; build summary/state;
freeze capsules; validate all four manifests before successor execution. Restore
independent copies, verify checkpoint equality, execute in seeded order, seal,
grade, score, validate bindings and write one exclusive result per branch. Every
branch references one checkpoint ID. Parent contamination is checked before a
result is published. Raw artifacts remain outside all agent workspaces.

Only whitelisted file inspection, named source writes and immutable public cases
are exposed. No shell. Fresh isolated Python workers receive function arguments,
never hidden expected answers; host comparison determines passing results.
macOS rules deny outside file data, filesystem writes, network and process forks.
Environment is scrubbed and site hooks disabled. CPU/descriptor/output/wall limits
apply; there is no hard memory cap. Runtime/system data remains readable; ancestor
directory metadata is visible. This bounded benchmark sandbox is not formally
verified arbitrary-code containment. Unsupported isolation fails closed.

Wrong/incomplete fixes and budget exhaustion are TASK_FAILURE. Provider errors,
missing usage, refusal/truncation and malformed output are MODEL_FAILURE. Broken
isolation/host execution is INFRASTRUCTURE_FAILURE. Forbidden tools/paths and
invalid capsule/block invariants are INVALID_RUN. Public and hidden passes give
functional SUCCESS. `task_success` is boolean for task outcomes, null for non-task
failures, preserving Phase 0 semantics. All failures remain recorded. Controller
exceptions create separate failure records with partial run IDs. No silent retries.

Functional SUCCESS still needs source review for task-specific exclusions:
hardcoding, API changes and grader interference. Every result marks that review
pending. Finite tests cannot prove their absence. Human adjudication is a separate
immutable artifact/amendment, not an overwrite of the original record.

## Prospective count rubric

`task-specific/1.0.0` reports exact registered-target counts, not exhaustive
semantic rates. Phase 0 rate APIs remain unchanged. Missing broad annotation
coverage is not zero error and supplies no opportunity denominator.

* Rediscovery: predecessor passed the target probe at applicable hashes, then
  successor repeats that exact standalone probe with a passing result at unchanged
  relevant hashes. Full-suite regression and changed-scope reverification are excluded.
* Repeated failure: predecessor demonstrated the failing registered patch/probe;
  successor reapplies that exact patch/cache-clear probe with registered partner
  files unchanged. Equivalent rewrites and inconclusive approaches are not auto-counted.
* Contradiction: an OBSERVED/VERIFIED claim exactly matches a registered false
  hypothesis contradicted by still-applicable predecessor facts, with no cited
  fresh contrary test value. Hypothesizing, quotation/rejection, changed scope
  and new evidence are excluded. Matching normalizes case/whitespace/trailing
  periods only; no semantic model is used.
* Inherited-error candidate: that contradiction also repeats an exposed predecessor
  false claim, the additional handoff literally carries it, condition is contextual,
  and successor declares predecessor basis. Independent agreement is excluded
  even with full history available. The label means compatible with inheritance,
  never causal evidence.

Each count includes task/branch, target, predecessor/successor event IDs and
hashes, rule, confidence and rubric. Validation reconstructs totals and rejects
duplicate/missing links. Unmatched assertions become manual review candidates.
Rules see condition/capsule for candidate inheritance; blinded human reliability
is unmeasured. Probe evidence is finite/source-scoped, not an unrestricted input
claim. Exact matching may substantially under-count natural language behavior;
review must assess coverage. No LLM silently produces final counts.

## Budgets and accounting

Predecessor: nine model/nine tools, 2,048 output tokens per call, 60,000 combined
tokens. Successor: fourteen model/twelve tools, 2,048 outputs, 60,000 combined.
Both: 32,000 request-input cap and 128,000 context cap. Handoff: 24,000 native
isolated-text tokens. Guards include a conservative framing reserve, check before
dispatch, then validate provider usage. This is not exact billing prediction.
SUMMARY checks its 32,000 input cap before dispatch. Unknown usage fails the model
run; unknown prices stay null.

Handoff size is an integer plus tokenizer metadata, excludes common prompts and
current files, and is zero for NO_CONTEXT. Post-handoff totals sum input/output;
cached input is included once. Each attempt retains request/response, actual ID,
request ID if available, native tool calls, latency, finish reason, usage and
decimal USD cost where cache reporting allows calculation. Authorization headers
and keys are never logged. Agent tools are text JSON actions; native API function
tools are not offered.

`success_cost` includes every post-handoff call, including failed branches. Shared
predecessor/summary costs remain in separate raw calls and planning totals. At
published default rates without cache discounts, the envelope is 594 calls,
2,997,216 combined tokens and $11.0581632. This is a registered-budget planning
bound, not expected average spend or a billing guarantee; taxes and separately
authorized real-model development calibration are excluded.

## Live stop

No paid execution is authorized. Default pilot stops before transport; offline
mode cannot carry live authorization. Later execution needs explicit human
authorization and an API key. Neither authorization nor scripted tests establishes
scientific readiness. Current blockers: real-model checkpoint calibration/review,
authenticated access, and annotation/exclusion review coverage. Report these;
do not silently bypass them or present synthetic validation as pilot evidence.
