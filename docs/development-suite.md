# Authored continuation development suite

The original three tasks and experiment settings are unchanged. These six cases
are authored controlled applications, not historical bugs, production products
or real-world benchmark evidence. Shared family scaffolds avoid padded files;
each case has a public behavioral contract, initial overrides and private
evaluator scenarios/reference/incomplete candidates.

| Family/cases | Meaningful continuation |
| --- | --- |
| `jobs_duplicate`, `jobs_recovery` | Durable queue deliveries, job identity, effects, result commits, acknowledgment and bounded retry policy interact. Duplicate suppression must preserve distinct jobs; an interrupted transaction must roll back while a committed result survives restart and lets later deliveries progress. |
| `migration_compat`, `migration_cache` | Legacy seconds/additional-retries and modern milliseconds/total-attempts must agree through parser, validation, normalized cache keys, policy schedules and both callers. Local new-format tests cannot establish mixed-version compatibility or freshness after configuration changes. |
| `index_update`, `index_delete` | Ingestion, Unicode/content normalization, chunk boundaries, SQLite generations, metadata and lookup must agree after updates/deletion/restart. A global cleanup can fix one document while destroying unrelated documents; filtering lookup alone leaves persistent orphan rows. |

SQLite databases are reopened during deterministic interruption/recovery tests.
No paid embedding service is used. Reproducible generated sequences use seeds
17, 29 and 43; failing seed names remain in validation output. Complete generated
operation sequences are preserved in `analysis/implementation-delivery-v2.json`
and can be reproduced with `property_case` in `development/suite.py`.
Acceptance compares behavior rather than a reference patch.
Other valid source implementations can pass. Human review for hardcoding/API
changes/grader interference is still separate from passing the grader.

```sh
./keisho dev-suite --out /absolute/new-validation.json
./keisho dev-check jobs_duplicate --public
./keisho dev-check jobs_duplicate --workspace /absolute/captured-job-app --public
./keisho dev-plan
```

`dev-check` returns 1 for a behaviorally failing task, including an unchanged initial
case. `dev-suite` verifies all six initial failures, six passing references and six
rejected incomplete candidates. Public diagnostics are visible to agents; private
checks and generated evaluator inputs remain host-side. Untrusted application code
runs under the existing macOS isolation, extended only to allow SQLite writes in
its own `.runtime` directory. Source files, siblings, evaluator archives,
credentials and network remain inaccessible or read-only. There is no unrestricted
fallback on unsupported hosts. Workspace management is separate from this sandbox.

## Checkpoints and conditions

`checkpoint/2.0` uses exactly 12 completed tool calls prospectively, or an explicit
user-triggered completed boundary. Public acceptance work must remain unfinished
and the trace must contain useful file/test/change information. No particular
command, wrong hypothesis or failed patch is required. Public completion is not
hidden acceptance proof. Early solutions, low-information and incomplete-boundary
outcomes are retained; no automatic resampling is performed.

Repeated-failure eligibility is separate. A recorded implementation write followed
by failure at matching named source scope supplies a candidate opportunity. A
baseline failing diagnostic alone does not. With no qualifying opportunity,
repeated-failure metrics are N/A, not zero prevented errors. Checkpoints chosen
after inspecting a completed trajectory use `retrospective-development` mode.

Use the actual public task description as the bundle goal, and package only the
registered application files and relevant `.runtime` state. Notes exports work
for manual use; primary research preparation requires a sealed Keisho tool trace.

```sh
./keisho dev-prepare jobs_duplicate --bundle /absolute/checkpoint-bundle \
  --out /absolute/prepared-block --seed 17 --checkpoint-mode prospective
```

This performs an isolated public-only checkpoint check, freezes the workspace,
and prepares NO_CONTEXT, FULL_HISTORY, SUMMARY_2K and KEISHO_2K. The two 2K forms
use identical source material and the same exact native tokenizer. The current
baseline is deterministic prose, with zero generation calls; it is not an
evaluated LLM-generated summary. Keisho also compiles deterministically. A later
model-generated variant must use the same generator identity for both, record
every generation call and share the supplied ledger. Learned/successor-specific
compilation is deferred.

Full history is a larger-context reference and is never silently truncated. Every
whole request must fit the configured 32,000-input-token and 128,000-context caps.
Both 2K forms retain whole-item uncertainty/scope and record omissions; essential
overflow stops preparation. The default is an engineering budget, not optimality.
Seeded condition order is frozen before execution. All branches share the task,
snapshot, successor, provider routing, tools, seed, continuation budgets, grader
and stopping rules. The archive stays outside each successor's accessible
workspace. Evidence lookup is absent in the primary comparison. Manual lookup is
a separate mode; future comparisons must equalize fetch access and charge tokens
and tool calls.

## Automated continuation requires new approval

Automated continuation is implemented using existing adapters, `run_agent` and
request reservations. It has been exercised with injected offline responses only.
**No new paid run is authorized or performed in this milestone.**

After a separate fresh approval specifying a total cap, the command shape is:

```sh
./keisho dev-continue /absolute/prepared-block --approve-live --dollar-cap APPROVED_USD
```

There is one exclusive execution guard per prepared block, including failure.
No automatic retry, model substitution, provider fallback, credit purchase or
billing-setting change occurs. The entire new block shares the provided cap.
Noncached reservations and the 5% BYOK contingency remain; unknown route/cost holds
the reservation and stops all later requests. The original calibration ledger,
configs and guard are untouched. Its $1.35 approval cannot authorize this command.

Current continuation bounds are 32 model calls, 24 tools and 120,000 combined
tokens per branch, with 2,048 output tokens per request. The four-branch token-price
envelope is $2.6595072 including fee contingency, before any external predecessor
cost. This is a frozen-catalog planning envelope, not live billing verification
or a guarantee that all branches finish under a chosen cap. Admission reserves
32,000 input tokens before every request. New-call accounting and prior reported
predecessor cost are separate; incomplete predecessor accounting makes end-to-end
cost unknown. Any new generation calls would have to join the ledger.

Results retain acceptance success, model/tool calls, handoff and continuation
tokens, generation cost, accounted new cost, available predecessor cost and
end-to-end availability. Review worksheets include equivalent public test sets,
potential repetition, legitimate-verification review and unsupported inherited-claim
candidates. Human semantic judgments remain null until reviewed. Identical command
strings or source hashes alone do not prove unnecessary repetition; inheritance
candidates do not establish causation.

Branches from one checkpoint are paired, and repeated seeds/checkpoints are not
independent tasks. One model pair does not establish model dependence. These
development fixtures and the real local preview-feature handoff are separate from
held-out research evaluation. No general effectiveness, minimal sufficiency,
hallucination prevention or state-of-the-art claim is justified.
