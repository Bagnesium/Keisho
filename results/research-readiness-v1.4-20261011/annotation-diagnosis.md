# Annotation diagnosis and prospective prompt repair

This is an offline retrospective compatibility analysis of the sealed successful v1.3 functional confirmation. It does not demonstrate improved real-model compliance. No provider requests were made, and v1.3 records or outcomes were not changed.

## Saved evidence and diagnosis

Inspected the eight `predecessor_call_NNN-response.json` files, eight `wire-request-NNN.json` files, eight annotation diagnostics, eight raw tool observations, sealed event trajectory, actual transmitted system prompt and response format. Also inspected `pilot/response_policy.py`, `pilot/agent.py`, `benchmark/response_measurements.py`, `benchmark/comparison.py`, `handoff/session.py`, `handoff/compact.py`, `pilot/state_builder.py` and `state/extractor.py`.

The local claim contract requires exactly `statement`, `status`, `evidence_ids` and `basis`. Permitted statuses are `OBSERVED`, `VERIFIED`, `INFERRED`, `UNCERTAIN`, `FALSIFIED`; permitted basis values are exactly `tool`, `predecessor`, `independent`. References must be result event IDs already available in the current conversation. Historical handoff IDs are provenance, not newly available tool results.

The transmitted v1.3 prompt lists both enums, says to use them and warns that schema conformity does not establish truth. However, it does not define what the three basis classes mean or show a complete claim example. JSON-object generation mode sends `{"type":"json_object"}`, not the locally stored JSON Schema. Consequently the model sees the enum as prose; server generation does not constrain its basis labels.

The saved model used `basis` as a free-text description of evidence sources instead of an enum provenance class on calls 2–8. This is direct evidence of a vocabulary/semantics mismatch, not proof that the excluded statements are false. No existing parser logic uses basis to verify a statement: it validates the label and reference availability. The conservative extractor imports accepted model claims as interpretations, even when their declared status is `OBSERVED` or `VERIFIED`.

| Call | Generated basis (exact) | Declared status | Local result |
| --- | --- | --- | --- |
| 1 | `tool` | OBSERVED | Accepted structurally |
| 2 | `repository file list` | INFERRED | Rejected basis |
| 3 | `repository file list and api.py import` | INFERRED | Rejected basis |
| 4 | `ledger.py import statement` | INFERRED | Rejected basis |
| 5 | `repository file list and user instruction` | INFERRED | Rejected basis |
| 6 | `check_public.py reading tests.json` | INFERRED | Rejected basis |
| 7 | `ledger.py source and tests.json test cases` | INFERRED | Rejected basis |
| 8 | `executed check_public.py` | INFERRED | Rejected basis |

Every rejected claim has a known result reference and valid fields/status; every stored diagnostic identifies only its invalid basis enum. Availability establishes traceability, not semantic support. It would be scientifically unsound to map all these source descriptions to `tool` and announce annotation improvement: some claims also have timing or support problems.

Two separate failures must remain visible. Call 1 claims "Repository root listing retrieved" before any tool result exists. It is structurally accepted but cannot establish a completed observation at that point; extraction correctly marks it `HYPOTHESIZED`. Call 8 claims "Ran public acceptance tests after fix" before its proposed shell action executes and cites result 007, which is the write. Only subsequent result 008 contains the passing test output. Relabeling its basis would not repair this provenance mismatch. Call 7's "Fixed phantom inventory holds..." likewise precedes its write and validation; its declared `INFERRED` status does not establish completed correctness.

## Potentially useful excluded claims and independently preserved evidence

| Call | Excluded interpretation and support limits | Observable evidence preserved independently |
| --- | --- | --- |
| 2 | `api.py` relevance is a useful navigation hypothesis based on names; a listing does not prove its contents. | Completed listing result 001; completed read 002, path/hash and raw contents. |
| 3 | `ledger.py` probably contains core logic; cited `api.py` result 002 literally imports `replay` from `ledger`, while core responsibility remains an inference. | Reads of `api.py` and `ledger.py`, their hashes and original contents. |
| 4 | `normalize.py` may affect processing; `ledger.py` result 003 literally imports it. | Reads of both modules and their hashes/contents. |
| 5 | Public test location is a useful navigation hypothesis. Its cited result 004 is `normalize.py`, so that reference alone does not support the test-location claim. | Later completed read 005 preserves `check_public.py` content and hash. |
| 6 | `tests.json` contains test cases; cited result 005 literally loads it, a useful file relationship. | Completed reads of the script and `tests.json`; actual test cases remain in raw evidence. |
| 7 | Proposed reservation replacement fix gives intent/root-cause reasoning worth retaining in audit, but a proposed edit is not an executed fix or correctness check. | Completed write 007, exact changed path, before/after hashes and source content; completed test 008. |
| 8 | Proposed test action is useful intent but the claim of an already executed test has no supporting result yet. | Result 008 records command, exit code 0 and `PUBLIC_ACCEPTANCE passed 4 cases`. |

The deterministic importer retains 8 completed tool results and 59 source events: 6 `OBSERVED` observation items (five inspected files and the shell command/output), 2 `OBSERVED` changes, 2 `OBSERVED` progress items and 1 `HYPOTHESIZED` accepted model claim. The two change items describe one actual write, not two modifications. Raw listing paths, file contents, rejected annotations and diagnostics remain in the full archive. Compact state contains inspected paths and scoped observations; it does not automatically copy complete file contents or excluded model interpretations. Thus some potentially useful interpretation is absent from compact state, but the seven rejected annotations do not mean seven lost tool observations. The shell output is a recorded observation, not an independently inferred official benchmark resolution.

The compiler (`compact/1.0`) already transfers complete items with labels, scope, sources, missing evidence, conflicts, supersession and revalidation warnings. It prioritizes changes/observations and fails explicit essential overflow. It does not semantically upgrade model claims. Neither this compiler, the state representation nor benchmark baselines were changed for this repair.

## Smallest prospective repair

Added only `ANNOTATION_GUIDANCE_VERSION = 'annotation-guidance/1.0'` and `ANNOTATION_GUIDANCE` in `pilot/response_policy.py`; the prospective `benchmark-agent/4.0` prompt appends that guidance to the unchanged v1.3 agent prompt. `auxiliary-claims/2.0`, all fields/enums, local validation, action wire `flat-or-args/1.0`, internal action schema 3.0 and JSON-object mode remain unchanged. There is no canonical mapping and no silent claim repair. No new annotation format version is necessary because the format and parser have not changed; the model-facing guidance and prompt are separately versioned and frozen.

The guidance defines `basis` as provenance class: `tool` for already completed current-conversation tool evidence (including inference from that evidence); `predecessor` for an inherited report not re-observed; `independent` for the model's own reasoning/proposal, never independent verification. `status` remains the model's epistemic assertion. It defines observation versus inference, narrows verification to completed checks and recorded scope, forbids claiming the action in the same response has completed, requires actual supporting prior result IDs, and supplies five examples. No evidence or truth is invented, and hypotheses without evidence remain explicitly hypotheses or uncertain possibilities. All predecessor/successor conditions receive this same prompt and policy.

Guidance canonical JSON digest: `4355a256a11dc729a2c6d35e95b770ae041777a1c96d19217003222406f25d1e`.

## Retrospective compatibility counts

| Measure | Original v1.3 contract | Proposed prompt contract |
| --- | ---: | ---: |
| Actual archived responses | 8 | 8 |
| Supplied claims | 8 | 8 |
| Structurally accepted claims | 1 (12.5%) | 1 (12.5%) |
| Rejected claims | 7 (87.5%) | 7 (87.5%) |
| Responses with all supplied annotations accepted | 1/8 | 1/8 |
| Responses with rejected annotations | 7/8 | 7/8 |

These counts intentionally stay unchanged. Replaying saved text cannot test whether a model will follow new wording. Real-model annotation reliability under the revised prompt is **unverified** until a separately authorized prospective model run. Structural acceptance does not measure semantic accuracy, sufficiency of citations or truth; the existing parser remains permissive about schema-valid semantically incorrect claims, and the extractor conservatively prevents their automatic promotion. Natural-language contradiction between model claims is not automatically adjudicated. Contradictory structured tool results at identical scope remain linked conflicts; differing-scope test evidence is superseded and code changes trigger revalidation.

Exact reports, diagnostics, raw text hashes and deterministic extracted items are in `annotation-retrospective-stats.json`. The tracked 76,905-byte `tests/data/annotation-v1.3-live-packet.json` preserves exact model response text and the sealed observable trajectory, with original file provenance hashes. It does not replace or edit the historical run.

## Focused offline verification

`PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python -m unittest tests.test_annotation_readiness -v`

Passed **16 tests**. Coverage includes all existing basis/status combinations; exact archived acceptance/rejection and diagnostics; invalid basis values/types without mapping; missing/invalid provenance; unavailable historical, future and non-result references; hypotheses without evidence; schema-valid premature observations and verification labels without promotion; contradictory model claims; a failed tool test contradicted by a model's passing claim; unsupported model falsification; same-scope test conflicts; superseded evidence and scope revalidation after code changes; unchanged schema hash; real tool evidence retained despite rejection; and independent raw-versus-canonical action/annotation records. No paid inference, synthetic agent execution or benchmark was launched by these tests. Final broader tests are recorded in the session's combined readiness report after all edits.
