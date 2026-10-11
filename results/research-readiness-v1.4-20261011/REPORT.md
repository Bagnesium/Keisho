# Final offline research-readiness report — prospective v1.4

Completed annotation diagnosis/repair, real cumulative patch-export repair,
prospective experiment freeze, and the exact five-way method/cost plan. **$0 new
provider usage; no functional confirmation, SWE-bench or official evaluator run.**
No project commit, push, publication or deployment. The sealed v1.3 result remains
passed with its original dirty patch and rejected annotations.

## Annotation finding and repair

The actual model used `basis` as a source-description string: `repository file
list`, `repository file list and api.py import`, `ledger.py import statement`,
`repository file list and user instruction`, `check_public.py reading tests.json`,
`ledger.py source and tests.json test cases`, and `executed check_public.py`.
The allowed labels remain `tool`, `predecessor`, `independent`. The v1.3 transmitted
prompt listed them but defined neither their provenance semantics nor examples;
JSON-object mode supplied no server-enforced schema. This is a contract mismatch,
not proof that the rejected statements were false.

Implemented only prospective `annotation-guidance/1.0`, appended in
`benchmark-agent/4.0`: basis means provenance; status is a model epistemic
assertion; observations/checks must already have completed and cite actual prior
results at their scope. Five examples distinguish tool observation, inference,
scoped checking, inherited report and unsupported hypothesis. Annotation schema,
parser/enums `auxiliary-claims/2.0` remain unchanged. No mapping, evidence invention,
truth promotion or silent semantic repair. All six agent roles share this guidance.

| Archived retrospective measure | Old contract | Proposed contract |
| --- | ---: | ---: |
| Responses / supplied individual claims | 8 / 8 | 8 / 8 |
| Structurally accepted individual claims | 1 (12.5%) | 1 (12.5%) |
| Rejected individual claims | 7 (87.5%) | 7 (87.5%) |
| Responses with all supplied annotations accepted | 1/8 | 1/8 |

These identical counts are **retrospective compatibility analysis**, not
improvement in real-model compliance. Real-model annotation reliability with the
new wording remains **unverified**. The first accepted claim describes a listing
before it executes; the last rejected claim describes a test before execution and
cites the preceding write. Structural acceptance does not verify support/timing.
Useful navigation/root-cause interpretations were rejected, but deterministic
extraction still preserves all 8 completed results, inspected paths/hashes, the
edit and the actual passing test output. Accepted model claims remain hypotheses.
Arbitrary natural-language contradictions are not automatically adjudicated;
structured test conflicts, supersession and named-file revalidation remain scoped.
See [diagnosis](annotation-diagnosis.md), [exact replay statistics](annotation-retrospective-stats.json)
and tracked [archive/adversarial tests](../../tests/test_annotation_readiness.py).

## Cumulative patch export

Prospective `source-and-artifacts/2.0` replaces unrestricted add-all staging for
v1.4 only. A separate Git index exports cumulative changes from the official base,
including predecessor/successor edits, new ignored/untracked source, deletions and
relevant binaries. Explicit bytecode/test-cache paths are excluded and inventoried;
a new untracked cache cannot silently re-enter. Modified/deleted/newly staged
tracked cache paths reject for review. Unsafe paths, escaping links, symlink
parents and Git metadata aliases reject; safe link bytes remain eligible.

Configured clean/smudge/process filters are disabled and recorded. Staged blobs
and modes must match raw worktree or symlink bytes exactly, including deletions;
attribute-driven transformations reject with per-path diagnostics. Hostile-filter
regressions prove no filter execution and exact CRLF preservation.

Every accepted diff independently passes official-base `git apply --cached
--check --binary` in a second temporary index; empty patches are explicit. The
real host and Docker dirty-repository exporters each preserved 8 intended changed
paths and excluded 8 generated paths. Pristine-base clones accepted both patches,
with independent source/addition/deletion/binary checks and untouched original
indexes. Prediction JSONL matches the official three-field format. This verifies
format/coverage offline, not behavioral SWE-bench resolution. Generic binaries remain eligible: bytes alone cannot distinguish generated
output from legitimate task fixtures. See [export report](patch-export/PATCH_EXPORT_REPORT.md) and
[final real exporter evidence](patch-export/evidence-filter-safe/RESULT.json).

## Final verification and preservation

After final implementation edits, **40 focused and 238 broader offline tests pass**,
exit 0; `git diff --check` passes. Commands:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python -m unittest \
  tests.test_annotation_readiness tests.test_patch_export \
  tests.test_benchmark_v14 tests.test_benchmark_v13 -v
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python \
  results/research-readiness-v1.4-20261011/run_broader_offline.py
```

[Focused log](focused-tests.log), [broader log](broader-tests.log). The broader
suite explicitly excludes 7 functional/comparison execution fixtures under this
scope; selected tests have zero skips. Its provider-network guard blocks HTTP
and connection attempts. Pure synthetic unit/admission tests remain. Coverage
includes archived/adversarial annotations, conflicts/scope, all action shapes,
export caches/additions/deletions/binaries/filters, freeze mutation/refusal and
six-role parity. Earlier development logs remain available; a first freeze test
caught a noncanonical CA path, which was corrected before final validation.

A public-CLI **dry-run only** passes prepared task/image, provider/config, local
harness and frozen-component admission checks. Provider requests 0, live admission
false, guard created false. Current public pricing/routing is pending for any future
paid launch. [Dry-run record](public-cli-dry-run.json).

**All 9,327 protected historical files and 22 representation/baseline files are
byte-identical to the starting snapshot.** Old ledgers, execution guards, raw
trajectories, configurations and results remain intact. Final component/source
verification is recorded in [validation.json](validation.json).

An exporter-only inspection of the real prepared xarray base also accepted an
empty patch with exact base inventory and passed raw-byte/no-change audits;
no model, task test, agent action or evaluator ran. Its owned container was closed.
[Official-base exporter inspection](patch-export/official-base-export/RESULT.json).

The handoff representation/compiler and benchmark baselines remain unchanged.
The frozen checkpoint recognizer is lexical: `false && pytest` can qualify a
validation-looking command without running that subcommand. This limitation is
explicit in the registered method; checkpoint exit status is not test-success
attestation. One exposed development task cannot establish general superiority.

## Frozen experiment and exact five-way plan

[Frozen config](../../configs/swebench-comparison-v1.4.json),
[matched launch plan](../../analysis/swebench-comparison-v1.4-plan.json),
[83-component runtime manifest](../../analysis/swebench-experiment-v1.4-manifest.json)
and [prospective amendment](../../protocol_amendments/swebench-interface-v1.4.md).
Config/plan canonical digests are embedded in admission; the manifest verifies
source-byte hashes on load and is archived on an eventual authorized run. The
binding module is separately included in the [final source freeze](final-source-freeze.json)
to avoid a circular digest. Full interface and source pins are recorded there.

| Canonical JSON value | SHA-256 |
| --- | --- |
| v1.4 config | `e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f` |
| v1.4 plan | `60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff` |
| Runtime manifest | `b1bd32a720c195fadc92b2e39818a3f4a3a1cb1d633abfe639358fc523f461cd` |
| Agent prompt | `4f99b6495be87680583af9460943a26fbd389ee017007e289e7fbe1a5dfc527d` |
| Annotation guidance | `4355a256a11dc729a2c6d35e95b770ae041777a1c96d19217003222406f25d1e` |


The exact [five-way specification](../../research/FIVE_WAY_EXPERIMENT_SPEC.md)
retains `pydata__xarray-6721`, the original selection and checkpoint, mini
predecessor/generators and full GPT-4.1 successors, OpenAI-only/no-fallback identity
checks, predecessor 48-model/36-tool/180K-total and each successor
64-model/48-tool/360K-total limits, ≤2,048 tokens for three compact handoffs, and
unchanged official grading. REPOSITORY_ONLY, FULL_HISTORY, SUMMARY_2K,
STRUCTURED_NOTES_2K and KEISHO_2K fork independently from one checkpoint. Shared
annotation/action/safety/export policy; no Keisho recovery. Early stops,
no-checkpoint, generation overflow/failure and unstarted/ungraded branches retain
their actual denominators, costs and outcomes without replacement or selection.

## Spending and next command after approval

[Cost plan](../../analysis/FIVE_WAY_COST_PLAN.md) uses the trustworthy saved
2026-10-11 public catalog offline; future current rates/fee/routing verification
is pending. Assumed planning scenario **$3.014256**; conservative API envelope
**$8.14048704**; temporary reservation **$0.08440320**; envelope plus reservation
**$8.22489024**. Recommend **$10 total** for exactly one fresh five-way block:
$0.22 predecessor, $0.02 each generator, $1.65 each successor, $1.49 common margin.
Allocations are advisory; existing common ledger/numeric budgets remain unchanged.
Local grading/compilation has zero model API cost; paid-host compute is unpriced.

Fresh explicit authorization must bind the final config/plan and one unique scope,
with one attempt, no retry/guard reset/fallback. The template is false; an approved
record does not yet exist. After that approval only, the exact next command is:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.4.json \
  --plan analysis/swebench-comparison-v1.4-plan.json \
  --authorization analysis/swebench-comparison-v1.4-authorization.json \
  --run-dir runs/swebench-v1.4-five-way-once-001 \
  --approve-live
```

The proposed live launch command was not executed. All offline tasks
are complete; future model reliability and five-way outcomes remain unmeasured.
