# Keisho SWE-bench response-policy repair

Offline repair completed on 2026-10-07. No inference or credential-validation
request ran; new provider cost is $0. The completed comparison remains a protocol
failure with one response, zero tools, no checkpoint and five unstarted/ungraded
conditions. This is software regression evidence, not a resumed benchmark result.

The exact original response was copied byte-for-byte from
`runs/swebench-integration/comparison/predecessor/predecessor_call_001-response.json`
into `tests/data/swebench-first-response/`, alongside its original request and
postrun diagnosis. The provider JSON string and model text are also preserved
without replacing the response with an example. `provenance.json` records source
paths/fields and SHA-256 values. The historical diagnosis was written after the
failed run; it was not an original per-call protocol-failure artifact. Local replay
of the original parser reproduces **ValidationError: invalid claim basis**.

| Claim index | Actual basis | Result under the original enum |
| --- | --- | --- |
| 0 | `issue report` | Invalid |
| 1 | `user environment details` | Invalid |
| 2 | `issue traceback` | Invalid |
| 3 | `issue report` | Invalid |

Allowed bases were `tool`, `predecessor`, `independent`. Allowed statuses were
OBSERVED, VERIFIED, INFERRED, UNCERTAIN, FALSIFIED; all four returned statuses were
schema-valid. All evidence lists were empty. The allowed bases and statuses were
explicitly supplied in the saved system message. The actual OpenRouter request
used `response_format: {"type":"json_object"}`, which requested JSON without
enforcing these enums or the action schema. The current adapter reconstructs the
saved request body exactly offline. `parse_output` validated claims before action
admission, so the first unsupported basis rejected the whole response.

The proposed action independently meets the repository tool shape and bounds:
exactly `tool`, `path`, `content`; `write_file`; relative `test_chunk_access.py`;
1,133 UTF-8 bytes under 49,152; no traversal, absolute path, NUL or `.git` component.
Runtime containment was verified with the actual RepositorySession in a newly
owned Docker container from the existing setup-only Sympy image, not the original
Xarray workspace. The target was absent, the contained write succeeded, and the
resulting content hash matched. Container creation retained network none, no host
mounts/credentials/socket, dropped capabilities and resource/process gates. No
model-proposed shell action ran. The script contents, URL, imports and assertions
were never executed: a permitted write does not establish a usable reproduction,
valid validation or task progress. The original experiment executed none of it.

Claims are auxiliary because `RepositorySession.execute` admits tools using
arguments and container/workspace restrictions, while spending admission precedes
responses. Neither consults claim annotations. The opt-in `auxiliary-claims/2.0`
policy therefore separates their validation from action admission. It keeps raw
claims, per-index errors and coverage; rejects unsupported/unavailable annotations
from state; records their information as unknown; and creates no replacement
claims. The saved reply has coverage 4 supplied / 0 validated / 4 rejected. Its
independently valid write proceeds only in the offline fixture. Unknown tools,
extra/wrong arguments, unsafe paths and ambiguous duplicate JSON keys remain
fatal to action admission. A Git-metadata symlink alias is also rejected. Refused
actions are not imported as completed work. Schema-valid VERIFIED statements
remain model hypotheses with unestablished scope, not facts.

`strict/1.0` remains the default and the legacy malformed-claim test still fails
closed as originally specified. Prospective predecessor and every successor use
the same amended policy, system prompt, schema and action validator. Both accepted
writes with bad claims and rejected actions with valid claims were tested across
all five conditions and the predecessor. Raw model text remains in observable
history, accompanied by explicit annotation diagnostics; it is not erased from
FULL_HISTORY or promoted into validated Keisho state.

The frozen catalog advertises `structured_outputs` for both selected OpenAI
endpoints. Current read-only documentation lists structured output support for
[GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini) and
[GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1), and describes
[OpenRouter's endpoint-specific JSON Schema routing](https://openrouter.ai/docs/guides/features/structured-outputs).
The narrow opt-in adapter uses a strict JSON Schema with closed object keys,
tool-specific arguments and claim enums. Dynamic reference availability, lengths,
paths and authorization remain local checks. The 343 native schema tokens are
included in request bounds and the shared conservative reservation calculation;
the proposed first request upper bound is 4,444 tokens, below 32,000. Generation
formats and routing stay unchanged. No live schema enforcement was tested, and
conforming claims can still be false. No retries, fallback or response-healing
plugin was added.

The following comparison is source inspection and model-assisted interpretation;
no human semantic review or evaluated continuation supports effectiveness claims.
All author links refer to the downloaded MIT implementation at
`5179b1d759be466600c453da8b9078341967ec17`. Inspected file hashes are recorded in
`runs/swebench-integration/response-policy-repair/source-manifest.json`.

| Area | Published structured-notes behavior actually implemented | Keisho boundary / defensible distinction |
| --- | --- | --- |
| Evidence vs interpretation | Seven model-written strings include evidence observed and problem understanding; deterministic repository/validation metadata is rendered separately. Generation rules distinguish invocations from results and edits from proof of a fix. [Generator](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_summarizer.py#L16), [renderer](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_notes.py#L211). | Observable events and model hypotheses are separate state items. Separation itself is already covered by the baseline; schema validation cannot adjudicate either representation's truth. |
| Uncertainty and failed approaches | Explicit failure/error, uncertainty and rollback fields; UNKNOWN/NONE OBSERVED rules and historical/current failure distinction. [Generation rules](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_summarizer.py#L98). | Typed statuses and scoped retry notes differ in representation. Claiming that the baseline omits uncertainty or failures would be wrong. |
| Validation after latest edit | Deterministic latest-edit filtering, commands, failure signatures, outcome and observable continuation label, using text markers/checkpoint metadata. [Functions](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_notes.py#L43). | The adapter uses completed tool-result ordering and exit codes, retaining intra-action order as unknown. Latest-edit awareness is already covered; the differing heuristics need empirical validation. |
| Claim-level source references | Timeline entries expose step/source/event type. The seven-string schema and inspected validator do not enforce per-claim references. Prose references remain possible; other uninspected capabilities are unknown. [Timeline](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/evidence_packet.py#L137). | State items carry event IDs and missing-reference information. A dedicated representation is a plausible distinction, not proof of better evidence use; historical IDs do not grant successor audit access. |
| Evidence scope and revalidation | Shared takeover instructions tell every view to inspect, treat notes as historical, verify important claims and preserve an already-solved task; conditional generation advice prioritizes verification after changes. [Shared prompt](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/prompt_parts.py#L10), [conditional rule](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_summarizer.py#L65). | Recorded file hashes/scope exist. Local pack/resume can compare hashes, but this benchmark calls the compact compiler directly and does not run that local revalidation flow. Compact scope text names files; dependency scope is unknown. Generic revalidation is already covered. |
| Contradictions | Regex consistency checks and implemented repair replace particular no-change/further-implementation contradictions when source changes exist; up to two generation attempts, overconfidence and forbidden-phrase checks. [Consistency/repair](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_summarizer.py#L182). | Keisho retains same-scope typed test-result conflicts and supersedes differing scopes. Benchmark shell output has no typed test claim key, so this does not establish general contradiction detection for these tasks. The baseline already implements narrow contradiction handling. |

Keisho source locations: [observable importer and conflict mapping](/Users/bagnesium/Documents/GitHub/Keisho/src/keisho/handoff/session.py:25),
[local hash comparison](/Users/bagnesium/Documents/GitHub/Keisho/src/keisho/handoff/workspace.py:174),
[compact scope/source formatting](/Users/bagnesium/Documents/GitHub/Keisho/src/keisho/handoff/compact.py:27),
[benchmark construction](/Users/bagnesium/Documents/GitHub/Keisho/src/keisho/benchmark/comparison.py:92),
and [prospective annotation validator](/Users/bagnesium/Documents/GitHub/Keisho/src/keisho/pilot/response_policy.py:24).

The old STRUCTURED_NOTES_2K adapter retained all seven substantive model fields
and the shared takeover prompt, but was not fully faithful: it suppressed the
observable continuation label, omitted the conditional source-change instruction,
and limited scratch metadata to final changes. Adapter 1.1 corrects those gaps
and removes stale command/evidence from latest-edit metadata. Published fields
remain problem_understanding, work_completed, evidence_observed,
observed_failures_or_error_evidence, remaining_uncertainty, rollback_notes and
recommended_next_action. No new Keisho feature was added to manufacture a contrast.

Remaining adaptations are explicit: JSON rendering; 2,048 total handoff tokens;
1,600 generation output tokens (also the author's configured generator maximum);
the same full allowed history/issue/inventory/cumulative patch for both generated
baselines. The author structured packet excludes raw patches/assignment snippets,
clips events to 1,200 characters and retains the latest 80; this bridge provides
both generators the complete record instead. It rejects overflow without silent
truncation. Author field coercion, regex semantic rewriting and retry behavior are
not reused; this adapter requires seven nonempty strings and permits no automatic
paid repair/retry. Artifact classification and validation use the existing
completed-result mapping, not the author's prose-marker heuristic. Official
grades remain outside notes. Substantive categories are preserved prospectively,
but processing and evidence exposure differ: this is an adaptation, not an exact
reproduction or a demonstrated capability equivalence.

| Recorded command label | Exit / outcome |
| --- | --- |
| response-repair-focused-01 | 1; 24 tests, one tokenizer-stub interface error; preserved |
| response-repair-focused-02 | 0; 24 tests passed |
| response-repair-focused-final | 0; 25 tests passed after final implementation edits |
| response-repair-offline-final | 0; supported broader suite, 137 tests passed |
| response-repair-docker-01 | 0; exact saved write, actual isolated setup container, script unexecuted |
| response-repair-container-final | 0; actual restoration, independent branches, cumulative patch and host/credential/socket exclusions |
| response-repair-plan-final | 0; native schema counting, frozen mapping and cost bounds |
| response-repair-scaffold-final | 0; existing offline scaffold check |

Each invocation's exact argv, working directory, exit code and complete output
are retained under `runs/swebench-integration/commands/<label>/`. Coverage includes
unsupported and unknown references, malformed claims, valid claims with invalid
actions, raw-response/diagnostic retention, identical condition behavior, legacy
strict behavior, isolation, unknown usage/insufficient funds stops, cumulative
patch formatting and unique grading IDs. No legacy test expectation was weakened.

Thirty-three protected files across the original comparison, initial report,
preselection and original config are byte-identical, with no files added to their
trees. Both original trajectory seals verify; see `preservation-verification.json`.
The historical ledger's `stopped:false` bookkeeping value was deliberately not
rewritten: its settled $0.0020076, zero held funds and guard remain intact. The
entry point now rejects that existing guard before any credential inspection.

The proposed next configuration is `configs/swebench-comparison-v1.1.json`, canonical
hash `f6c5898f2400e7f6d24f70643da2333ea86fd3ba1b5fd30f4ec64ea0c2b3895e`.
Task, base, models, routing, five conditions/order, checkpoint, grading, token/time/
tool/call budgets and $10 proposed bound match 1.0. Cost assumptions remain
$0.19946304 predecessor + $0.032256 generation + $7.908768 successors =
$8.14048704, plus $0.0844032 largest admission reservation headroom. These use
frozen rates, no cache discount, possible 5% BYOK fee, two note calls and no retries;
unknown charges stop further requests. No paid execution is enabled or authorized
by this proposal. A future authorized attempt requires a new prospective binding
to this same task and fresh provider verification within that authorization;
neither the original guard nor its ledger may be reset or reused.

The remaining plausible differences concern explicit item provenance/scope and
deterministic compact selection with an external audit. Uncertainty, failure
recording, latest-edit validation, revalidation advice and narrow contradiction
handling are already present in the published baseline. Their mere presence
cannot support a novelty or superiority claim. No checkpoint or successor data
yet compares their effectiveness. The author construction also saves its allowed
evidence packet and rendered record; the existence of audit artifacts alone is
not distinctive.
