# Exploratory calibration overlay 1.0.0

Prospective, 2026-10-03, before any paid API call. This overlay applies only to
the proposed task_001/seed17 calibration. Baseline branch manifests retain
`0.1.0+phase1.1.0.0`; the separate calibration index records this overlay, exact
configuration, purpose and spending controls. It does not authorize execution.
Historical Phase 1 artifacts and all baseline serializer/prompts/scoring rules
are preserved. This is development calibration, excluded from later evaluation.

Exactly one predecessor trajectory, at the existing nine-tool checkpoint;
one free-form summary call if eligible; automatic state projection uses zero
API calls; at most four successor branches. Predecessor/summary requested ID:
`gpt-4.1-mini-2025-04-14`; successor: `gpt-4.1-2025-04-14`. Returned IDs/raw
responses are recorded and mismatches stop without substitution or retries.
Task/configuration hashes are pinned in `configs/calibration-task001.yaml`.
The production predecessor uses the existing prompt and is free to investigate;
no scripted steps or dead ends are supplied. Early resolution, insufficient
learning or ineligibility preserves the outcome and stops without resampling.

Eligible branches use identical restored task/environment, existing tools,
budgets, prompts and four handoffs. Seed17 order is NO_CONTEXT, SUMMARY,
FULL_HISTORY, FIXED_STATE, recorded before branches. All handoffs are frozen
before successors. An exclusive fixed calibration index prevents accidental
repeat execution after either success or failure. The real-calibration output
root is separate from evaluation/raw and synthetic roots.

One shared $1.25 API-usage budget (before taxes) applies to every stage. Before
each request, persist an admission reservation for the entire 32,000 input-token
allowance and requested maximum output at published default/noncached rates.
The existing native-text/framing guard also applies. Returned input/output usage
reconciles the reservation conservatively without cache discounts; invoiced
cost remains separately recorded/unknown. Unknown usage, a failed unreconciled
provider attempt or insufficient remaining dollars stops the entire block.
Reservations are retained for unknown charges. No credential-validation API
request or retry is added. The cap enforces the stated token/rate accounting;
unreported/out-of-bound usage cannot be reconciled and stops execution.

Maximum planning envelope: predecessor $0.0461184, handoff generation
$0.0144384, successors $1.168128; total $1.2286848, 66 requests and 333,024
combined tokens. Maximum outputs are allocated first to maximize cost under
each existing combined-token limit; allocated input is not a separate input
ceiling. Complete repeated context is included. Cache savings are not assumed.

SUMMARY input remains fixed prompt plus frozen observable events. FIXED_STATE
remains the gold-blind deterministic projection plus existing canonical fixed
serializer. The state builder now checks that the supplied goal equals the
task event's recorded content. This closes a potential injection at that entry
point without changing any valid baseline bytes. Private gold/hidden grading
and later successor events cannot enter either constructor.

The read-only token audit partitions complete serialized UTF-8 bytes, then
splits local BPE token weight proportionally across categories. Totals are exact
for pinned local o200k encoding; category attribution is estimated and is not
provider-reported billing. Later exact semantic/evidence leaf repetitions are
classified as duplicated content; repeated hashes/IDs/scopes remain metadata.
Partial/semantic duplication is not measured. Serializer/compression is unchanged.

The review timeline includes every external predecessor/successor action and
observation, every actual handoff, and all rule decisions/evidence. Its worksheet
covers counted and uncounted actions. Human adjudication is initially unknown;
review incoming context, purpose, changed dependencies/configuration/evidence,
test definitions and runtime before labeling waste. Hash equality alone is
insufficient. Exact-match counts stay diagnostic, broader semantic metrics stay
unknown, and candidate inheritance is never demonstrated causation. No semantic
model evaluator or metric change is introduced.

Approval and a configured API key are still required. Account/model availability
will be tested only by an approved budgeted request. No real outcomes exist.
