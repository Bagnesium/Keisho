# Keisho benchmark progress — offline sprint completed 2026-10-11

**P0–P5 done in the authorized offline scope. No paid provider inference authorized or
performed; actual new API spending $0. Old ledgers/guards closed and unchanged.**
Report: results/offline-reliability-sprint-20261011/REPORT.md.
Earlier full progress: results/offline-reliability-sprint-20261011/progress-before.md.

## Completed implementation and evidence

- P0: exact scripts ModuleNotFoundError reproduced after real Docker action in public
  subprocess with host Python and evaluator venv. Shared predicate moved to importable
  src/keisho/benchmark/inspection.py; callback invoked by regression. No root sys.path hack.
  Dedicated venv received existing pinned jsonschema 4.26.0, not global changes.
- P1: actual public functional CLI + synthetic test-only transport + real Docker:
  list/read/failing public test/source write/passing post-edit test/independent 4/4.
  Disposable artifacts: results/offline-reliability-sprint-20261011/functional-complete/.
  JSON/action/annotation/provider/infrastructure/task/budget failures separately exercised.
- P2: opt-in bounded-listing/1.0 (100 entries, 8192 path bytes), prefix/cursor pagination,
  explicit omissions, retained duplicate-page references, stale-cursor diagnostics.
  Local strict actions/raw-response diagnostics retained. Legacy contracts unchanged.
  Listing-loop cause unresolved; reconstruction payload audit is not model evidence.
- P3: real public five-way Docker simulation with synthetic model decisions and branch
  grades; frozen snapshot/independent contexts/history/budgets/notes/patches/guards tested.
  runs/offline-sprint-five-way-02/runs/five-way-synthetic/.
  ONE actual unchanged official checkpoint grade: unresolved, exit 0;
  keisho-five-way-synthetic-checkpoint-699d233da7c7-1141e7ad5560.
  Its .cache evaluator invocation/report is controller-only; synthetic branch grades
  cannot rank handoffs. Existing scope-revalidation policy now invoked by benchmark bridge.
- P4: research/BASELINE_COMPARISON.md and RESEARCH_PLAN.md; pinned code audit acknowledges
  Handoff Debt's uncertainty, failures, latest-change validation and contradiction repair.
  Narrow mechanism distinction; no effectiveness advantage/global novelty established.
- P5: paper/OUTLINE.md, METHODS_DRAFT.md, RESULTS_PENDING.md;
  research/REPRODUCIBILITY.md with exact commands, pins, boundaries and pending evidence.

## Final validation (after final implementation edits)

Records: runs/swebench-integration/commands/<label>/{command,result,output}.
- sprint-final-focused-02: 69 tests, exit 0.
  PYTHONPATH=src python3 -W error::ResourceWarning -m unittest tests.test_functional_public tests.test_benchmark_real_offline tests.test_benchmark_v12 tests.test_bounded_listing tests.test_agent_wire_contract tests.test_response_measurements tests.test_response_policy tests.test_benchmark_launcher tests.test_benchmark -v
- sprint-final-broad-01: 189 tests, exit 0, no skips.
  PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
- sprint-final-scaffold: python3 scripts/check_scaffold.py, exit 0.
- sprint-final-real-dry-run: real production command below, exit 0; live admission FALSE,
  no provider call, pending guard/output absent. Historical failures preserved.
- results/offline-reliability-sprint-20261011/preservation-verification.json:
  4992 historical files unchanged; implementation-manifest.json records current source hashes.

## Prospective disabled binding

- configs/swebench-comparison-v1.2.json: canonical SHA
  f4c7733335e0991aebdc59ac393b8a347207b452accc1119831273f77691d425.
- analysis/swebench-comparison-v1.2-plan.json: canonical SHA
  6bd86821a4d40df417c49a03f5564546e212d7f401bd74d8d0ee9ea5105902ba.
- analysis/swebench-comparison-v1.2-authorization-template.json: PENDING, inference false.
- protocol_amendments/swebench-interface-v1.2.md: agent-runtime/3.0, benchmark-agent/3.0,
  JSON-object/3.0 with local action schema 3.0; unchanged auxiliary-claims/2.0 and
  structured-adapter/1.1, memory/compiler/baseline prompts, task/models/order/budgets.
- analysis/swebench-predecessor-budget-v1.2.json: 48 calls is a ceiling; conservative
  projection 13–15 moderate-growth or 10–11 larger-growth calls. No budget increase.
  Proposed later 240k sensitivity is not applied. Envelope estimate $8.14048704 plus
  $0.0844032 headroom under frozen rates, not authorization/current billing verification.

## Frozen inputs / preserved history

Task pydata__xarray-6721, base cc183652bf6e1273e985e1c4b3cba79c896c1193.
Dataset c104f840cc67f8b6eec6f759ebc8b2693d585d4a; harness
02e7a74ffd0b707aab73d203fe87bdc7c76afc8e /5.0.2; recipes
3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d; MIT Handoff Debt
5179b1d759be466600c453da8b9078341967ec17.
Prepared image sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898,
amd64 under existing ARM Docker Desktop emulation. Image/evaluator reused, no rebuild.
Gold setup smoke keisho-setup-gold-20261007-01 resolved; unpatched unresolved;
setup-only, never agent effectiveness.
Mini predecessor/generator and full successor remain frozen OpenRouter OpenAI-only mappings.
Five conditions/order/2048 compact limits unchanged.
Closed runs: comparison (protocol failure); exploratory-v1.1-live (ten lists/no checkpoint);
interface-diagnosis and listing-decision diagnostic; functional-confirmation12-v1
(one list/import error, $0.0002804, reservations zero). None reopened/replayed as new behavior.

## Next command / blocker

Offline reproduction (uses no spending and creates no guard):
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v1.2.json --plan analysis/swebench-comparison-v1.2-plan.json --authorization analysis/swebench-comparison-v1.2-authorization-template.json --run-dir runs/swebench-integration/exploratory-v1.2-pending --dry-run

Live blocker is **no new spending authorization**, not a launcher gap. Later explicitly
authorize one new scope/config/plan/cap, verify current catalog/pricing and environment,
then public --approve-live with a new record/output. Do not reset guards, resample tasks,
reuse old permissions or infer success from synthetic fixtures. Completed real functional
confirmation remains unmeasured. No commit/push/merge/deploy/publication. Sprint stopped.
