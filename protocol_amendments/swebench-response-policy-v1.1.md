# Prospective SWE-bench response-policy amendment 1.1

2026-10-07. Scope: implementation repair and offline validation only. This
amendment grants no inference, credential-validation, spending, task selection,
or execution-guard reset. The completed `comparison/` remains a protocol failure:
one charged response, zero repository actions, no checkpoint, five unstarted
conditions. Its original requests, responses, diagnosis, ledger and seals remain
unchanged. Offline fixtures are software tests, never experimental continuations.

The original `strict/1.0` response parser remains the default for historical
pilots/configuration. The proposed `swebench-handoff/1.1` configuration opts into
`auxiliary-claims/2.0`, `benchmark-agent/2.0`, `json_schema/2.0` and
`structured-adapter/1.1`. Prompt and output-schema hashes are checked together.
The proposed configuration is explicitly offline-only and is not bound to a new
paid-run guard. A future run needs separate authorization and a new prospective
binding to the same selected task; the completed guard must never be reset.

Claim annotations do not authorize repository actions: tool arguments, workspace
containment, container isolation and spending admission already do that. Under
2.0, exact top-level structure, JSON disambiguation and the eight-claim envelope
remain mandatory. Each annotation is validated independently. Unsupported bases,
statuses, fields and unavailable/malformed references reject the annotation,
preserve its original contents and diagnostics, and leave unavailable information
unknown. Nothing is relabeled as observed or replaced with invented claims.
The importer revalidates against preceding available results, excludes rejected
annotations and records coverage. Schema-valid model interpretations remain
hypotheses, including those labeled VERIFIED by the model.

An independently valid action may proceed after annotation rejection. Unknown
tools, malformed/excess arguments, unsafe paths, Git metadata aliases, invalid
encodings and bounds violations cannot authorize a write. Runtime symlink
containment, no network/host mounts/credentials/socket, time/output/process checks
stay enforced. A refused action is not imported as completed work. The same policy,
prompt and schema apply to the predecessor and every successor condition. No
condition-specific repair or paid retry is introduced.

The frozen OpenAI endpoints for GPT-4.1 mini and GPT-4.1 advertise
`structured_outputs`. Read-only provider documentation confirms JSON Schema
support. The opt-in adapter supplies `response_format` with a strict schema;
generation keeps its existing formats. Native schema tokens are included in
request bounds and conservative reservations. Provider enforcement has not been
tested live. Local tool/reference checks remain required, and schema conformity
does not establish truth. Routing, accepted identities and no-fallback behavior
are unchanged.

Source inspection found baseline adaptation gaps: the published continuation
label is observable, not an official grade; conditional first-pass advice to
verify existing changes had been omitted during prompt extraction; scratch
artifacts were limited to final changes; stale validation commands could appear
under latest-edit metadata. Adapter 1.1 restores the observable label and advice,
retains observed scratch history, and withholds validation metadata when no
subsequent completed validation is recorded. Event ordering inside one action
remains unknown. The seven published note fields and shared takeover instructions
are retained. Author semantic rewriting/retry, clipped patch-excluding packets,
and text-marker grading heuristics are not reproduced; these differences are
documented in the repair report. No Keisho memory feature is added.

Task/base, dataset/harness/author pins, models/routing, five conditions and order,
2,048 handoff tokens, checkpoint rule, official grading, tools, time/token/call
budgets and $10 proposed cap remain unchanged. Frozen-price envelope remains
$8.14048704 plus $0.0844032 admission headroom, with no cache discount and possible
5% BYOK fees. Unknown usage stops further calls. This estimate is a proposal, not
renewed authorization or current live endpoint verification.
