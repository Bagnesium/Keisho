# Guidance for coding agents

Read the root README before changing code or research records. For the current
study, read the [manuscript](paper/MANUSCRIPT_FINAL_PILOT.md) and
[editorial audit](paper/EDITORIAL_AUDIT_20261027.md). Use the
[experiment specification](research/FIVE_WAY_EXPERIMENT_SPEC.md),
[reproducibility guide](research/REPRODUCIBILITY.md), and
[benchmark chronology](BENCHMARK_PROGRESS.md) for protocol and execution
details. Historical plans and progress entries do not supersede the current
paper or a later versioned protocol amendment.

## Scientific boundaries

- The current empirical comparison is one task, one run per condition, and
  five branches from a shared checkpoint. All five received `resolved` grades.
  Do not present the branches as five independent task samples or infer a
  causal, statistical, or general advantage.
- Keep `REPOSITORY_ONLY`, `FULL_HISTORY`, `SUMMARY_2K`,
  `STRUCTURED_NOTES_2K`, and `KEISHO_2K` distinct. Their transferred content
  differed as well as their representation.
- The official empty-patch grade did not execute the target test. Refer to the
  independent Docker replay for checkpoint verification and preserve its full
  test accounting.
- Separate implementation, evaluation, observation, interpretation, and
  proposed work. Do not turn a model claim into an observed fact or a local
  fixture into real-world evidence.
- Preserve failed and incomplete attempts. Record prospective protocol changes
  in a new version; do not rewrite frozen configurations, authorizations, or
  run records to make historical evidence appear cleaner.

## Data and execution boundaries

- Raw `runs/` archives, private SWE-bench evaluator inputs, and `.cache/` are
  local and excluded from Git. Do not bulk-stage them or copy evaluator-only
  material into an agent workspace.
- Never commit `.env`, credentials, local certificates, or private evaluator
  data. New `runs/` and most generated `results/` files are ignored; selected
  historical reports already tracked in `results/` are explicit exceptions.
- Existing authorization JSON files document completed or historical scopes;
  they are not permission for another provider request. Paid inference requires
  fresh, explicit user authorization for the exact experiment and budget.
- The local handoff CLI and offline checks are separate from paid experiments.
  Follow the commands and environment requirements in the relevant guide.

## Reproducibility

Keep exact commands, configuration versions, source pins, and output locations
with any new engineering or research record. Use a new, unoccupied output path;
do not overwrite a prior run. Distinguish synthetic offline fixtures from
provider results and official benchmark grades. The public repository does not
contain the complete raw archive needed to replay the current paid comparison.

The MIT license covers Keisho-authored code and documentation. It does not
cover third-party research assets or service-derived metadata. Keep separate
notices intact and review `review/LICENSE_RESEARCH.md` before redistributing
those materials.
