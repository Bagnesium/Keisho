# Package a coding session and continue in a fresh workspace

Keisho now implements local `pack → inspect → resume --manual`. It reads an
explicit repository/session, writes a compact handoff and separate complete
audit, restores allowed files into a new directory, and produces the exact
fresh-session prompt. These operations make no API calls and do not modify the
source repository. The legacy serializer and previous experiment guards remain.

```sh
./keisho pack --repo /absolute/project --session /absolute/session.json \
  --task "The actual unfinished task" --out /absolute/new-bundle --token-budget 2048
./keisho inspect /absolute/new-bundle
./keisho inspect /absolute/new-bundle --item S1
./keisho resume /absolute/new-bundle --manual --workspace /absolute/new-workspace
```

Use the documented `keisho-notes/1.0` format or an explicit UTF-8 text export for
your own notes; native Codex/Claude session import is unsupported. Imported prose
remains an unverified report. See `docs/local-handoff.md` for scope, exclusions,
omissions, supported filesystem features, and revalidation.

## Actual unfinished development handoff

The objective was defined before bounded work: implement read-only capture
preview, preserving the existing capture policy and CLI behavior. Actual work
inspected capture and CLI code, implemented a preview helper, ran its no-write
check and CLI help, then copied a capture correction. CLI registration,
regression tests and documentation remain unfinished. Six actual tool operations
are recorded; there is no fabricated successor trajectory.

Open `runs/local-dogfood-v2-complete/delivery-workspace` in a **fresh** coding-agent
session and supply
`runs/local-dogfood-v2-complete/delivery-workspace.keisho-resume/NEXT_SESSION_PROMPT.md`.
The transferred model-facing text is
`runs/local-dogfood-v2-complete/delivery-bundle/handoff.md`.

```sh
./keisho inspect runs/local-dogfood-v2-complete/delivery-bundle
./keisho inspect runs/local-dogfood-v2-complete/delivery-bundle --item S6
./keisho resume runs/local-dogfood-v2-complete/delivery-bundle --manual \
  --workspace runs/local-dogfood-v2-complete/my-fresh-preview-workspace
```

The last command requires a nonexistent destination/helper. The already delivered
workspace is usable without restoring again. The sealed supporting session is
`runs/local-dogfood-v2-complete/session/actual-preview-with-capture-correction`.
The initial source-copy manifest is `capture-source-manifest.json` in the same
dogfooding directory. This is a filtered historical checkpoint copy, not the
latest full Keisho checkout: credentials, evaluator files, tokenizer cache and
three credential-canary test files were excluded before investigation. The later
bundle excludes eleven cache directories. No Git baseline/history is recreated.
False-positive exclusions are visible; an independent human has not reviewed them.

Useful surviving information: `S6` records that the preview helper's no-write
check passed, with its source event and named file scope. Capture code changed
later, so that observation explicitly requires revalidation. It is not presented
as proof of CLI correctness. The next work is wiring the helper and adding tests.
The prototype check used the host capture implementation; this limitation remains
in its source record. This Codex conversation is not an independent successor.

On that same six-operation observable record, exact `tiktoken/0.12.0:o200k_base`
text counts are **904 compact tokens** versus **13,518 legacy fixed-state tokens**.
The complete local audit is 3,016 tokens; the exact manual prompt, including path
and operating instructions, is 1,049. No selected state items were omitted.
These are text sizes, not billed token measurements or sufficiency evidence.

## Development cases and validation

| Cases | Interactions and invariants |
| --- | --- |
| `jobs_duplicate`, `jobs_recovery` | SQLite queue, immutable job identity, effects, result transaction, acknowledgment and retry policy. Prevent duplicate effects without losing distinct jobs; recover after interrupted writes and result-before-ack crashes. |
| `migration_compat`, `migration_cache` | Old/new parser contracts, validation, service, normalized cache, retry schedules and callers. Preserve units and retry semantics, reject invalid mixed inputs, refresh changed configurations and avoid mutable returned-value aliasing. |
| `index_update`, `index_delete` | Ingestion, Unicode normalization, chunks, SQLite generations, metadata and lookup. Remove stale/orphan chunks, survive reopen, preserve unaffected documents and support normalized deletion/readdition. |

These are authored controlled development applications, not historical benchmark
evidence. Behavioral acceptance allows multiple source solutions. Offline
validation proves six initial failures, six passing references (52 acceptance
scenarios total), and six failing incomplete fixes. Generated sequences retain
seeds 17/29/43 and their full fixtures in the JSON delivery record. This does not
establish model difficulty or AI effectiveness.

```sh
./keisho dev-suite --out /tmp/keisho-new-development-validation.json
./keisho dev-plan
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest tests.test_local_handoff tests.test_development -q
```

The full regression suite passed 109 tests before final handoff changes. The final
23 focused tests passed, including the actual CLI through pack, inspect, restore
and isolated public application checks; corruption/traversal/link refusal;
dirty/staged/deleted/binary/Unicode contents; scoped contradictory and unsupported
claims; missing evidence; overflow; interrupted creation; credential-bearing
legacy omission; and refusal of incomplete tool boundaries. macOS sandbox tests
confirm scratch-only SQLite writes, read-only source and blocked audit access.
All 115 restored files match recorded bytes/modes. All 2,881 protected original
files, including original tasks/configurations/run artifacts, match their baseline.
Provider adapters, original sandbox/spending controls and legacy compiler match
their previous validation hashes. `git diff --check` passed.

An early dogfood packaging failure and intermediate bundles are preserved. That
failure exposed a credential heuristic false positive on a source initializer;
the filter was corrected and regression checked. Later fixes corrected ancestor
Git detection, numeric behavioral equality, empty scratch-directory restoration,
one-way conflict retention, legacy credential leakage and deleted index audit
contents. No unresolved defect was observed in the executed checks. Supported
boundaries remain narrower than a complete machine snapshot: Git history/index,
dependencies, services, symlinks/hard links, ACLs/xattrs and native private-session
imports are not restored. Manual use was validated on this macOS/POSIX host;
Windows portability is unverified. Secret detection is heuristic.

## Controlled comparison and what remains unrun

`development-comparison-v1.json` prepares NO_CONTEXT, untruncated FULL_HISTORY,
deterministic prose SUMMARY_2K, and compact KEISHO_2K from the same supported
material. The two 2K forms cost zero generation calls. The prose baseline is not
an evaluated model-generated summary. A prospective 12-completed-tool policy
uses public-only information; user boundaries and retrospective development data
are labeled separately. Continuation eligibility does not require a failure.
Repeated-failure analysis is N/A without a qualifying opportunity; no resampling.

Seeded order, task/snapshot/model/routing/tools/budgets/scoring are fixed within a
block. The complete archive is outside every primary successor workspace. Review
worksheets retain candidates and null human judgments; equivalent actions are
considered, and legitimate verification remains separate from unnecessary work.
Four injected offline branches validate runner mechanics only.

Automated continuation reuses existing adapters and request accounting, requires
fresh `--approve-live` **and** a newly approved shared `--dollar-cap`, and retains
no-retry guards, unknown-cost stopping, OpenAI-only routing, disabled fallbacks
and the BYOK fee contingency. The four-successor planning envelope is $2.6595072
before external predecessor cost. That is conservative frozen-catalog planning,
not live billing or new authorization. Incomplete prior accounting leaves
end-to-end cost unknown.

**No new live request or paid comparison was made.** Previous task_001 solved
early; its completed calibration, guards and authorization are preserved. That
$1.35 authorization is not reusable. The delivered preview work needs a genuinely
fresh session for successor behavior; paid evaluation needs a new authorization.
Codex-authored annotations and this inspection are model-assisted work, not
independent human review. No general effectiveness claim follows from these checks.
