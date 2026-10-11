# Exploratory Keisho comparison: blocked before execution

The new $10 authorization was recorded, but a required launch check failed.
The prepared 1.1 policy is not launchable through the existing supported entry
point. No predecessor or successor ran, no provider or credential-validation
request was sent, and new spending is $0. This is not a benchmark result.

`scripts/benchmark_compare.py --help` exposes only `--approve-live`.
`comparison.execute` accepts only that argument; its module constants bind
`configs/swebench-comparison-v1.json`, the old preselection plan, and the completed
`runs/swebench-integration/comparison/` guard. The root run ID is also hardcoded
as `comparison`. The existing guard rejects a launch before credential inspection.
There is no supported run-specific config/plan/output binding. The repair prepared
the 1.1 response contract but did not implement that launch mechanism.

The prepared configuration remains disabled and unchanged. Its canonical hash
matches the saved prospective plan check, and the prompt/schema hashes validate.
The old loader's plan binds the 1.0 config hash, not this 1.1 hash. Simply enabling
the prepared file would not make it loadable through the existing entry point.
The recorded $8.14048704 envelope plus $0.0844032 headroom fits $10 under recorded
pricing assumptions; that does not resolve the missing binding. Credential,
current-pricing, Docker and evaluator runtime checks were not performed after
this earlier required check failed. Their current status is unverified.

| Condition | Execution | Official outcome | Handoff tokens | Model/tool calls | Input/output tokens | Generation cost | Continuation cost | Annotation coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPOSITORY_ONLY | Unstarted | No grade: preflight blocked | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0 supplied / 0 accepted / 0 excluded |
| FULL_HISTORY | Unstarted | No grade: preflight blocked | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0 supplied / 0 accepted / 0 excluded |
| SUMMARY_2K | Unstarted | No grade: preflight blocked | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0 supplied / 0 accepted / 0 excluded |
| STRUCTURED_NOTES_2K | Unstarted | No grade: preflight blocked | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0 supplied / 0 accepted / 0 excluded |
| KEISHO_2K | Unstarted | No grade: preflight blocked | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0 supplied / 0 accepted / 0 excluded |

Predecessor cost: $0. Total reported charges from zero requests: $0; conservative
accounting: $0; held reservations: $0. The fresh preflight ledger has no attempts.
No annotation diagnostics, imported claims, patches or evaluation run IDs exist
for this request. No new trajectory established anything about the issue, and
there are no handoff differences or successor actions to interpret. Unstarted
conditions are not task failures. No effectiveness evidence supports another
scientific comparison yet.

New artifacts are in `runs/swebench-integration/exploratory-v1.1-preflight/`:
authorization, archived prepared config/plan, fresh zero-usage ledger, launch
contract, per-condition result, preservation hashes and a sealed preflight record.
This directory is a preflight archive, not a paid comparison guard. Exact command
arguments, exit codes and outputs are saved under
`commands/exploratory-v1.1-launch-help/` and
`commands/exploratory-v1.1-preflight-verification/`.
All 142 protected source/config/previous-artifact files remain byte-identical.
The old protocol-failure guard and $0.0020076 ledger were not reopened or reset.
Keisho code, task, models, handoffs, budgets, isolation and grading were not changed.

Execution requires a supported launcher that binds an authorized run-specific
1.1 copy, a matching frozen plan and fresh output/guard identifiers while enforcing
unchanged scientific settings. None exists in the inspected implementation.
No globals were redirected, unsupported flags invented, or old default executed.
Stopped at this concrete implementation blocker as instructed.
