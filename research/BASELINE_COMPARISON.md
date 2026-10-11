# Implementation audit: Keisho and Handoff Debt

**No comparative advantage has been demonstrated.** Handoff Debt already includes
many epistemic safeguards sometimes described as Keisho differences. This audit
identifies implemented mechanisms, not their effectiveness or novelty against
all related work. Review date: 2026-10-11; judgments are model-assisted, with no
human research review recorded.

The [Handoff Debt paper, v2](https://arxiv.org/html/2606.02875v2) links its
[released repository](https://github.com/anjilab/agent-handoff-debt). Actual source
was inspected at MIT-licensed commit
`5179b1d759be466600c453da8b9078341967ec17`, already downloaded under
`.cache/swebench-evaluator/sources/agent-handoff-debt-5179b1d759be466600c453da8b9078341967ec17`.
Keisho reuses pinned author signal code and generation/takeover prompts; its
text-action runner is not the author's OpenHands runtime. This is an adaptation,
not an exact reproduction or official leaderboard entry.

## Source index

Author links below are immutable commit permalinks. Line anchors identify the
starting location; named functions identify the behavior.

- **HD-S**: [structured_summarizer.py:16](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_summarizer.py#L16),
  fields; `generate_structured_fields` at 58, validation at 160/182, repair at 203.
- **HD-D**: [structured_notes.py:43](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/structured_notes.py#L43),
  latest edit, validation/outcome at 54/93, continuation state at 141/155,
  record rendering at 211.
- **HD-E**: [evidence_packet.py:11](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/evidence_packet.py#L11),
  clipping/sanitization at 28/35, checkpoint filter at 50, timeline at 143,
  observable state at 167, structured/summary packets at 187/224.
- **HD-P**: [prompt_parts.py:8](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/prompt_parts.py#L8),
  `takeover-v2` shared verification/preservation instructions.
- **HD-C**: [summarizer_common.py:21](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/handoff/summarizer_common.py#L21),
  model call, 1,600-token cap, JSON recovery and text validation.
- **HD-T**: [schemas.py:48](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/src/handoff_debt/schemas.py#L48),
  `TraceEvent`, Git snapshot, checkpoint and handoff structures.
- **K-I**: [handoff/session.py](../src/keisho/handoff/session.py), `load_session`
  at 25: automatic observable import, claims at 98–119, named-test conflicts at
  170–181. This is the benchmark-used `local-state/1.0` path.
- **K-R**: [handoff/workspace.py](../src/keisho/handoff/workspace.py),
  `compare_scope` at 174 and `compare_scope_hashes` at 186.
- **K-C**: [handoff/compact.py](../src/keisho/handoff/compact.py),
  `item_text` at 27 and `compile_handoff` at 65.
- **K-B**: [benchmark/comparison.py](../src/keisho/benchmark/comparison.py),
  `make_handoffs` at 216; [benchmark/protocol.py](../src/keisho/benchmark/protocol.py),
  `deterministic_fields` at 81, `generation_messages` at 121, `render_structured` at 136.
- **K-A**: [pilot/response_policy.py](../src/keisho/pilot/response_policy.py),
  `parse_auxiliary` at 20; [logging/raw.py](../src/keisho/logging/raw.py),
  exclusive artifacts and hash-chained/sealed observable events.

## Feature comparison

“Not exposed” refers to the inspected structured-note path. It is not proof that
no author component could implement a capability elsewhere. Unverified behavior
is unknown. A prose field or instruction is distinguished from automated behavior.

| Feature | Published implementation | Keisho benchmark implementation | Defensible difference |
| --- | --- | --- | --- |
| Explicit epistemic status | HD-S has `evidence_observed`, uncertainty/failure fields, UNKNOWN/NONE OBSERVED instructions, and an overconfidence check. No required per-claim status enum in its seven-string schema. | K-I assigns OBSERVED to tool facts; model assertions remain HYPOTHESIZED or REJECTED_UNSUPPORTED regardless of a declared VERIFIED/FALSIFIED label. K-A excludes invalid annotations. | **Partial mechanism difference:** typed item labels and conservative import, not invention of uncertainty awareness or truth verification. |
| Observations versus interpretation | HD-S distinguishes command invocation from observed result; its prompt forbids invented findings. Generated prose still mixes model interpretation within string fields. HD-D contributes rule-derived facts. | K-I separates tool observations from model statements and stores the declared status. File-read items say a file was inspected; they do not summarize or certify its meaning. | **Genuine implementation distinction in granularity**, with a potential information-loss tradeoff. No accuracy benefit demonstrated. |
| Hypotheses and failed approaches | HD-S requests understanding, observed errors, uncertainty, rollback and next action. Hypotheses can be expressed in prose; no dedicated hypothesis field. | K-I categories include hypothesis/failed_approach. A FALSIFIED model assertion becomes unsupported rejection; named test failures have scoped retry conditions. Ordinary benchmark shell output is an observation, not automatically a rejected theory. | **Partial:** explicit categories exist, but automatic extraction of comprehensive investigations is not implemented. Failed-approach retention alone is already covered. |
| Item-level provenance | HD-E timeline attaches step, source and event type; HD-T stores raw trace and Git snapshots. Generated note strings need not cite individual timeline entries. | K-I binds items to event IDs; sources store event digests, kind and archive locations. K-C renders item IDs and source/evidence IDs. | **Genuine within the inspected note contract:** required item attribution. Compact text contains IDs, not the complete archive or all hashes; successors cannot fetch it. Attribution is not semantic support. |
| Evidence references | HD-E supplies attributable event excerpts. HD-S has no required machine-checked claim-to-event reference field. Arbitrary references in generated prose are possible. | K-A checks annotation references against result IDs actually supplied to that conversation. Unsupported references are diagnosed/excluded; K-I preserves missing references for other supported import types. | **Narrow genuine mechanism difference:** reference availability checks. Entailment and citation usefulness remain unverified. |
| Evidence scope | HD-D names changed files, validation command and recent output/failure signature. HD-P asks verification against current state. No per-claim file-hash scope exposed in seven-string notes. | K-I tool items capture named file hashes and a limited environment description. Model interpretation scope is unknown. Dependency coverage is explicitly unknown. | **Partial:** hash-bound named scope differs; author already provides file/validation context. Neither establishes dependency-complete validity. |
| Staleness after edits | HD-D selects validation after latest edit; HD-S distinguishes historical/current errors. HD-P treats notes as historical. Per-item hash invalidation was not found in this inspected handoff path; behavior elsewhere is **unknown**. | K-R compares recorded file hashes with current files/inventory; K-C emits REVALIDATE on changed/unknown paths. New 1.2 benchmark bridge now invokes this existing policy. | **Narrow genuine distinction:** mechanical file-level staleness labels. Empty scopes have no hash disagreement to detect; environment/dependency changes can be missed. No automatic test rerun. |
| Revalidation | HD-P explicitly asks current inspection/claim verification and preserving already-correct work. HD-D gives latest validation state. | K-C supplies scope flags and historical labels; the same HD-P instructions are shared by all successors. | **Already covered at instruction level.** Keisho adds deterministic triggers, not unique verification behavior. Actual successor compliance is pending. |
| Contradiction handling | HD-S detects selected no-change/remaining-implementation contradictions, rewrites those phrases, validates forbidden/overconfident text and allows two generation attempts. These are real code behaviors, not just fields. | K-I links conflicting named test outcomes at identical scope; changed scope supersedes the earlier test item. K-C requires linked items together. Arbitrary semantic contradiction detection is absent from this path. | **Different limited mechanisms.** Claiming Handoff Debt lacks contradiction handling is false. Keisho's named-test mechanism is usually not triggered by free-form SWE-bench shell output. |
| Compact selection | HD-E supplies at most 80 recent events, each clipped to 1,200 characters; structured input sanitizes patch/code guidance. HD-C generates capped prose; no equivalent whole-item selector was found in inspected notes code. | K-C selects whole labelled items with fixed priority and explicit omissions, retaining conflict/supersession pairs; essential overflow stops. | **Genuine implementation difference:** deterministic budgeting rather than learned summarization. Priority is heuristic; sufficiency/optimality is unproved. |
| Generation cost | HD-C uses a model call; HD-S permits another validation attempt. Budget/cost recording of the full author experiment was not audited here. | Primary adapted summary and structured conditions each generate once with the same mini model; Keisho compilation makes zero extra model calls. Predecessor annotation tokens are still charged. | **Genuine local cost distinction**, not zero end-to-end Keisho cost. Wall time, total inference and downstream work must also be compared. |

## Existing STRUCTURED_NOTES_2K adaptation

`structured-adapter/1.1` preserves all seven author fields, UNKNOWN/NONE OBSERVED
rules, invocation/result separation, uncertainty/errors/rollback, conditional
source-change acknowledgment, verify-before-further-edit guidance, and the shared
`takeover-v2` instructions. Deterministic changed files, artifacts, latest
post-edit command/output and continuation state remain present. These are
substantive baseline information, not deliberately vague summary substitutes.

Differences are material and must be reported:

1. Both local generators see the same complete permitted observable record,
   original issue, changed inventory and **cumulative predecessor patch**. The
   author structured packet excludes patch text, sanitizes code/patch guidance and
   clips event history; its ordinary-summary packet is less sanitized. Equalizing
   the local sources changes the published protocol. It does not prove the local
   structured baseline is stronger or equivalent.
2. The author helper already uses a 1,600-token generation cap; this was **not a
   newly invented Keisho difference**. Local rendering additionally must fit 2,048
   native tokens, including deterministic fields. Overflow stops without silent
   clipping. Author note generation and runtime/context limits differ elsewhere.
3. Local generation uses the author's first-pass prompts, strict nonempty string
   fields, and no JSON extraction, field coercion, semantic phrase replacement or
   second attempt. The author implements these recovery behaviors. This is an
   existing declared adaptation, unchanged in this sprint; it can affect baseline
   reliability. No superiority claim may ignore this difference. A later
   author-faithful sensitivity condition needs a new plan and accounted costs.
4. Local completed-action events and exit codes replace author text-marker
   inference. Same-action edit/test ordering stays unknown and requires another
   completed validation action. A zero exit status means the command succeeded;
   a compilation result or no-tests run is not proof of task correctness.
5. Local state labels express **observable** continuation state, with official
   checkpoint classification withheld. The older vendored provenance description
   pertains to adapter 1.0; actual adapter 1.1 code governs current behavior.

## Smallest defensible contribution

A testable contribution is an **auditable deterministic compiler for observable
handoff items, carrying explicit interpretation status, event references and
named-file revalidation flags under a fixed compact budget**. That is a mechanism
positioning relative to this audited baseline, not a claim of unprecedented
provenance, complete epistemic reconstruction, reduced hallucination, or better
coding agents. The actual importer leaves many hypotheses/next steps unknown and
does not recover hidden reasoning. A successor's inability to inspect the source
archive may limit the utility of references. Global novelty requires broader
related-work review. Effectiveness requires controlled real continuations.

The strongest next analysis is whether those flags improve **appropriate reuse
and scope-sensitive revalidation** compared with already careful structured notes,
without lowering official resolution or increasing total cost. The corresponding
rejection criteria and ablations are in [RESEARCH_PLAN.md](RESEARCH_PLAN.md).
