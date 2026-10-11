# Prospective interface amendment: SWE-bench handoff 1.2

Recorded 2026-10-11, before any version-1.2 provider inference. This amendment
defines exploratory development after interface repairs. It authorizes **no
spending**. Earlier attempts, configurations, responses, costs and execution
guards remain historical; none becomes a successful continuation retroactively.

## Shared execution contract

`agent-runtime/3.0`, `benchmark-agent/3.0`, `json_object/3.0` and local action
contract `3.0` replace provider-enforced action schemas for this prospective
configuration only. The existing adapter sends `response_format: {type:
json_object}`, with the frozen model aliases, OpenAI-only routing, empty plugins,
seed and temperature unchanged. All predecessor and successor conditions use the
same contract. Existing strict-schema configurations keep their original pins.

Local top-level and action validation remains mandatory: exactly one action and
at most eight auxiliary claims, recognized tool, correct arguments, safe paths,
bounded content/commands, Docker containment and completion checks. JSON-object
mode permits invalid generations to be received; it does not authorize them.
Malformed actions stop without repair or retry. `auxiliary-claims/2.0` remains
unchanged: malformed annotations are preserved, diagnosed and excluded from
validated state; unavailable information stays unknown. Accepted annotations are
not certified true. HTTP bodies are archived before JSON/provider/admission
processing, without headers or keys; credential redaction is explicit. Returned
service model/provider metadata is recorded without upstream-output attestation.

## Bounded discovery

`bounded-listing/1.0` accepts optional literal relative `prefix`, opaque `cursor`
and integer `limit` from 1 to 100. A page contains at most 100 paths and 8,192 path
bytes. Lexicographic order, counts, omission text, `has_more`, `truncated` and
`next_cursor` make partial results explicit. All entries remain discoverable by
paging or narrower prefixes. No task-specific hints or action substitutions occur.

Identical pages return an explicit reference to the earlier `listing_id` and tool
action, rather than repeating paths. The earlier response remains in the full
conversation and audit. Cache eviction may repeat a page; no evidence is silently
removed. File content/mode changes invalidate cursors and cached identities.
A well-formed stale cursor returns a diagnostic instructing a fresh listing;
it is not counted as successful discovery. Malformed or out-of-range arguments
remain refused. No context trimming, embeddings or learned selection is added.

## Runtime repairs and existing state reuse

The functional acceptance callback imports `information_action` from
`keisho.benchmark.inspection`, rather than the launcher-only `scripts` namespace.
This fixes the demonstrated public-process import failure without root-path
injection. Missing tool results and isolation interruptions are explicit
infrastructure outcomes, never evidence of successful execution.

The benchmark now invokes Keisho's existing file-scope revalidation policy against
the frozen workspace inventory before compact compilation. The local pack/resume
path already performed this check; the benchmark bridge omitted it. The state
schema, observable importer, compiler and baseline prompts are unchanged. File
hash disagreement marks an observation for revalidation, not false. Empty scopes
and dependency/environment coverage remain unknown. This is bridge integration,
not a new memory mechanism or demonstrated research contribution.

## Frozen experiment and binding

- Configuration: `configs/swebench-comparison-v1.2.json`, canonical SHA-256
  `f4c7733335e0991aebdc59ac393b8a347207b452accc1119831273f77691d425`.
- Plan: `analysis/swebench-comparison-v1.2-plan.json`, canonical SHA-256
  `6bd86821a4d40df417c49a03f5564546e212d7f401bd74d8d0ee9ea5105902ba`.
- Pending reference: `analysis/swebench-comparison-v1.2-authorization-template.json`;
  inference permission is false. It cannot start a paid run.
- Task `pydata__xarray-6721`; mini predecessor/generator, full successor; published
  source pins, checkpoint rule, five conditions, branch order, 2,048-token compact
  budgets, continuation budgets, official grader and numerical predecessor budgets
  remain identical to 1.1. Structured-notes adapter remains `structured-adapter/1.1`.

Public launch resolution checks exact supported specification/plan hashes and
their task, source, prompt and action pins. A future new authorization must bind
both hashes, one attempt, its cap and a stable authorization ID. The authorization
guard depends on that ID, not a directory name or mutable timestamp. Concurrent
starts cannot claim two attempts. Dry-run follows binding and environment checks
without model construction, paid validation, live guard or output creation.

## Budget assessment and evidentiary limits

`analysis/swebench-predecessor-budget-v1.2.json` records conservative sensitivity
from a 4,227-token first request. The 48-call ceiling is not guaranteed: 1,024
tokens of retained growth allows 13–15 calls; 2,048 allows 10–11 under the frozen
180,000-token gate. Targeted investigation, edit and validation is plausible;
lengthy file/test output can still prevent a checkpoint. No numerical increase is
applied. A larger predecessor budget must be a separately frozen amendment with
recomputed note/full-history fit and total spending envelope, not an in-run change.

The recorded worst-case model envelope is $8.14048704 plus $0.0844032 reservation
headroom under frozen rates and fee contingency. These are planning estimates,
not current-price verification or authorization. No paid requests ran in this
amendment. Full-history overflow still stops without truncation. A future launch
must recheck public model/routing/pricing and available funds.

Offline public-process/Docker fixtures prove software execution. Scripted choices
and synthetic branch grades provide no model or handoff-effectiveness evidence.
The earlier four probes motivate testing JSON-object mode but do not identify a
general output-format effect. See `research/BASELINE_COMPARISON.md` for adaptation
limits and `research/REPRODUCIBILITY.md` for commands and artifacts.
