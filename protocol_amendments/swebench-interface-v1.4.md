# Prospective annotation guidance and cumulative patch amendment v1.4

Prepared offline on 2026-10-11, after the sealed successful v1.3 functional
confirmation. This amendment authorizes no inference, benchmark, retry or spending.
Historical configurations, raw responses, rejected annotations, patches, guards,
ledgers and outcomes retain their original meaning.

## Changes

1. `benchmark-agent/4.0` appends `annotation-guidance/1.0` to the exact v1.3
   system prompt. It defines `basis` as one provenance class (`tool`,
   `predecessor`, `independent`), distinguishes model status from evidence origin,
   gives five examples, and requires claims to describe completed prior evidence
   rather than the proposed action. Annotation format/parser `auxiliary-claims/2.0`
   and every enum remain unchanged. No label mapping or semantic repair exists.
2. `agent-runtime/3.2` selects `source-and-artifacts/2.0` cumulative official-base
   patch export. Bytecode and explicitly named caches are excluded and recorded;
   other ignored/untracked source and binary artifacts remain eligible. Changed
   tracked cache paths reject the whole export for explicit review. Each accepted
   diff passes `git apply --cached --check --binary` against a separate base index.
   Configured Git filters are disabled and inventoried; staged blobs/modes must
   match raw worktree/link bytes exactly or export rejects with diagnostics.
   Attribute-driven transformations are never silently substituted.
   An empty diff is explicitly recorded. Original Git index and safe path/symlink
   enforcement are preserved. The legacy exporter remains available to historical
   configurations.
3. The new config pins an 83-component manifest. Local admission verifies component
   bytes, model-facing guidance, provider policy, published baseline prompts,
   state extraction/compiler, selection/checkpoint, task and environment inputs.
   The binding module embeds config/plan pins and is separately recorded in final
   source-freeze evidence to avoid a circular digest.

Both predecessor and all five successor conditions use the same action adapter,
annotation guidance/parser, JSON-object generation, tool safety and export policy.
Wire schema 4.0 / internal schema 3.0 / `flat-or-args/1.0`, listing policy,
handoff representation and `compact/1.0` compiler, `structured-adapter/1.1`,
baseline instructions, task, models, provider restrictions, numeric budgets,
checkpoint rule and official grader remain unchanged. No Keisho-specific recovery.

## Evidence and interpretation

The eight saved v1.3 claims contain one permitted basis and seven free-text source
descriptions. Old and proposed contracts accept 1/8 and reject 7/8 claims, with
identical diagnostics. This is retrospective compatibility analysis, not measured
prompt compliance improvement. The accepted first claim is itself premature;
the last rejected claim cites a write before its proposed test executes. Structural
validity does not establish semantic or temporal support. The unchanged extractor
keeps model claims as interpretations and independently preserves all eight
completed tool results. Real-model reliability with the new wording is unverified.

Dirty Git and real Docker export fixtures preserve cumulative edits, new source,
ignored relevant files, deletions and binaries while excluding generated caches.
Independent pristine-base application and source/binary acceptance pass. This
checks patch syntax/coverage, not official task resolution. Generic binary files
remain eligible because contents alone cannot distinguish a fixture from output.

## Frozen bindings and future scope

Canonical JSON digests:

| Artifact | SHA-256 |
| --- | --- |
| `configs/swebench-comparison-v1.4.json` | `e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f` |
| `analysis/swebench-comparison-v1.4-plan.json` | `60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff` |
| `analysis/swebench-experiment-v1.4-manifest.json` | `b1bd32a720c195fadc92b2e39818a3f4a3a1cb1d633abfe639358fc523f461cd` |
| `benchmark-agent/4.0` prompt string | `4f99b6495be87680583af9460943a26fbd389ee017007e289e7fbe1a5dfc527d` |
| `annotation-guidance/1.0` string | `4355a256a11dc729a2c6d35e95b770ae041777a1c96d19217003222406f25d1e` |

The first-request upper bound is 4,782 native tokens, 555 more than v1.3; numeric
budgets remain fixed. The comparison remains exploratory development work on
`pydata__xarray-6721`; it is not held out or evidence of general superiority.
See [FIVE_WAY_EXPERIMENT_SPEC.md](../research/FIVE_WAY_EXPERIMENT_SPEC.md) and
[FIVE_WAY_COST_PLAN.md](../analysis/FIVE_WAY_COST_PLAN.md). A new explicit one-attempt
authorization of at most $10 total provider usage and current public price/routing
verification are required. Pending authorization is false; no guard or ledger is
created by this amendment. Final tests and preservation evidence are recorded in
`results/research-readiness-v1.4-20261011/REPORT.md`.
