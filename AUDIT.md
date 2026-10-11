# Phase 0 architecture audit

Reviewed after implementation, before any LLM experiments. Protocol/state/log/
manifest versions: `0.1.0`. No unrelated files or existing changes were present
in the initial repository. No paid calls, credentials checks, or empirical
results. This is an internal architecture inspection, not an independent review.

## Decision

The scaffold is sufficient to start authoring the three Phase 1 tasks. It is
**not ready for model experiments**. Keep the design small: do not add model
conditioning, benchmarks, training, embeddings, a database, or a dashboard yet.

## Enforced and tested

- Strict typed state and canonical round-trips preserve all categories, status,
  scope and provenance. Unknown fields, invalid types, unsupported state versions,
  missing evidence and conflicting stable-ID duplicates fail validation.
- Incorrect predecessor inferences stay inferred. Verification/refutation
  requires matching external evidence; evidence links are bidirectional.
  Conflicting evidence cannot retain verified/falsified status. Failures and
  inconclusive outcomes differ and retain retry conditions.
- External source records bind to frozen event ID, kind, location and hash.
  Extraction is explicit annotation ingestion; no implicit prose-to-truth rule.
- Logs use exclusive artifact creation, read-only files, sequence/hash chaining,
  frozen seals and read-only replay. Corruption is detected, never silently
  repaired. Unique run directories refuse reuse. One writer per run is assumed.
- Current checkpoint copies preserve files, content, supported file modes and
  empty directories. Restoration verifies equality, removes stale files and
  rejects traversal, symlinks, special files and hard links. Initial task resets
  and sibling mutations are deterministic in offline tests.
- Exactly four condition labels are implemented. Fixed JSON is model-agnostic;
  full history is never truncated. Budget enforcement rejects approximate
  counts. Scripted whitespace tokens are explicitly synthetic and model-specific.
- A block validator checks all manifest invariants and unique condition/run
  assignment. Failure statuses do not turn infrastructure problems into task
  failure data. Raw calls and annotations remain in metric reports.
- Metric annotations require eligible external event kinds, predecessor
  references, scope and rationale. Duplicate opportunities and missing/mismatched
  successor call/response records fail. Rates with no opportunities, missing
  usage/prices and incomplete upstream accounting stay unknown.

## Methodological concerns and repairs

| Concern | Repair or explicit limit |
| --- | --- |
| Branch outcomes are correlated | Register task/checkpoint/model/seed blocks and paired comparisons; do not treat branches as independent task samples. |
| One model pair cannot establish H2 model dependence | Phase 1 tests feasibility only. Require multiple successor identities and a prospective held-out plan in Phase 2. |
| Verification metadata can be circular or semantically wrong | Require external sources and claim/scope links; retain raw evidence. Semantic verification remains an annotator/grader responsibility. |
| Matching predecessor mistakes need not mean inheritance | Define externally visible error alignment and use `NO_CONTEXT` as a background control. Do not claim access to internal reasoning or psychological causation. |
| Rates can improve by changing the opportunity denominator | Preserve raw numerator/denominator, including negatives, and compare counts and paired success/steps alongside rates. Missing coverage is not zero error. |
| Preprocessing cost can erase handoff savings | Separate predecessor/extraction/summary/successor accounting; mark upstream coverage unknown unless verified complete. |
| Full history may exceed model context | Reject and retain the entire ineligible block; no selective truncation. Declare the resulting domain restriction. Full request context validation is still needed. |
| Task scoring/state annotation can leak hidden answers | Keep graders outside workspaces and out of frozen trajectories; freeze summaries/state before successors. Phase 1 must audit leakage explicitly. |
| Checkpoint selection can favor treatment or lack useful knowledge | Separate calibration from evaluation, freeze action cutoffs, retain calibration logs and test that facts/dead ends/false beliefs are observable. |
| Filesystem cloning does not isolate model tools/processes | Implement confined tools, subprocess/service/cache isolation and pure graders before real agents; copied branches currently share the host. |
| Hashes/read-only files are not tamper-proof storage | API immutability and detection only. Owners can delete or rewrite files/hashes. Archive raw artifacts independently before collecting results. |

## Remaining implementation limits

- No native OpenAI/Anthropic/local adapter, LLM summary generator, automatic
  extractor, action execution loop, scoring UI, or actual task set exists.
- No chronological handoff runner exists: Phase 1 must ensure the snapshot and
  sealed trajectory really come from the same stopped predecessor, verify actual
  provider requests against manifests, and log all missing/failed attempts.
- Scope is human-readable, not an automatic dependency system. Changes can
  invalidate prior verification; the scorer must judge applicability.
- Graders are callables and must be pure/isolated. Copies do not isolate mutable
  grader globals. Directory permissions, mtimes, environment variables, process
  state, caches and network services are outside the snapshot contract. Use
  content-deterministic tasks within this boundary or extend it deliberately.
- Adapters must count native tokens and validate complete provider context,
  tool overhead and output reservation. An exact capsule count alone does not
  establish that a complete request fits.
- Main-study thresholds, sample size, power and scoring agreement are not
  preregistered yet. The protocol is a hypothesis/feasibility registration,
  not a finished confirmatory analysis plan.
- Runtime/tests are dependency-free. Optional distribution builds require the
  pinned setuptools package; a package build was not attempted. Local validation
  uses Python 3.14.2, not a cross-version or cross-platform matrix.

## Verification

`PYTHONPATH=src python3 -m unittest discover -s tests -v`: **32 passing, 0 failing**.
Includes schema, provenance, serialization, merging, evidence links, rejection
scope, adversarial inference, branch isolation, snapshots, resets, condition
assignment, metrics, immutability, token accounting and an artifact pipeline.

`python3 scripts/check_scaffold.py`: temporary offline cross-component check of
four conditions, independent copies, manifests, sealed logs and metrics. These
are synthetic correctness assertions, not four model runs or research results.

## Exact next experimental step

Author exactly three deterministic debugging tasks with hidden tests and
documented dead ends/incorrect-inference opportunities. Calibrate meaningful
unfinished action checkpoints on development fixtures and freeze them before
evaluation. Complete the controlled runner, native adapter/tokenizer, summary/
state workflow, masked annotation rubric and process/tool isolation; rerun
offline validation. Only then request authorization for the three-seed,
36-successor-branch Phase 1 pilot. Do not add successor conditioning yet.
