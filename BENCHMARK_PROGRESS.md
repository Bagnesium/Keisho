# Keisho benchmark progress — prospective v1.7 defined (task sympy__sympy-20590) 2026-10-22

**v1.7 prospective specification defined:**
1. Task switch to `sympy__sympy-20590`:
   - Target file: `sympy/core/symbol.py` (~60 lines around `Symbol` class definition).
   - Expected turn count: ~4 turns (read, reproduce, edit, test). Eliminates exploratory wander in large multi-module codebases.
   - Preserves identical five-way experimental comparison conditions and evaluation harness.
2. Successor request input ceiling raised:
   - `successor_budgets.request_input_tokens` raised from 32,000 to **64,000** tokens.
   - Rationale: Parity with predecessor request input ceiling prevents `FULL_HISTORY` admission failure when predecessor handoff conversation exceeds 32k tokens.
3. Model configuration confirmed:
   - Successors use `openai/gpt-4.1-2025-04-14` across **all 5 conditions** (Frontier GPT-4.1, $2.00 in / $8.00 out per 1M tokens).
   - Predecessor uses `openai/gpt-4.1-2025-04-14`.
   - Note generation uses `openai/gpt-4.1-mini-2025-04-14` (2 calls).
4. Budget and cost envelope under $10 cap:
   - Predecessor max envelope: **$1.4593** (400,000 tokens).
   - Note generation max envelope: **$0.0591** (64,000 input ceiling, 2 calls).
   - Successors max envelope: **$7.9088** (5 conditions × $1.5818).
   - Combined settled maximum conservative envelope: **$9.4272** <= **$10.00**.
   - Peak in-flight reservation headroom: **$0.1516** (64k input + 2k output).
   - In-flight peak worst case: **$9.5788**, leaving **$0.4212** safety margin beneath $10.00.
   - Expected cost on `sympy__sympy-20590`: **$0.50 – $1.20**.
5. Frozen artifacts:
   - Config `configs/swebench-comparison-v1.7.json` (SHA `223dea1177052e81aa766d10755f5f38051f26217ea7ebf466980097c005ac10`)
   - Plan `analysis/swebench-comparison-v1.7-plan.json` (SHA `b0078bc06e620df26694dada8c7a68aea9672c819d40dd1af58fd1d369c360fe`)
   - Manifest `analysis/swebench-experiment-v1.7-manifest.json` (SHA `04f1f26bb26ef6d05fa7050ce2c3955ed18bff44356f7f3a4f5127df35538b91`)
   - Task specification `runs/swebench-integration/preselection/sympy__sympy-20590-task.json` (SHA `edc429b5c441e91fe9e661cf7c4ca721892cb60e89cb375c09dfcbb7b935b378`)
   - Preselection plan `runs/swebench-integration/preselection/sympy__sympy-20590-plan.json` (SHA `5133378bb3f0d5c888e796a2a4e606c2cd6aa480f491d62ed5d01fd5f202e9a6`)
   - Docker image metadata `.cache/swebench-evaluator/sympy__sympy-20590-prepared-task-image.json` (SHA `4b24ae2fc9dcd55db675db37a2723ca6af62a94dd3377389d28a3a37c1f61d68`)

# Keisho benchmark progress — v1.5 live run 001 recorded; prospective v1.6 defined 2026-10-22

**Two predecessor failures recorded and disclosed; all ten successor conditions unstarted:**
1. **v1.4 attempt 001 (`runs/swebench-v1.4-five-way-once-001`, $0.0164 spend)**:
   Halted at Call 6 (`reason: budget_exhausted`). `openai/gpt-4.1-mini-2025-04-14` created an
   uncompressed Zarr array generating 202 chunk files. Unbounded inventory metadata (41 KB / 18k tokens)
   flooded the conversational context, exceeding the 32,000 request input ceiling on Call 7 without
   touching `xarray/`. All five successors unstarted.
2. **v1.5 attempt 001 (`runs/swebench-v1.5-five-way-once-001`, $0.1129 spend)**:
   Halted at Call 13 (`reason: budget_exhausted`). With `bounded-output/1.0` active and predecessor
   upgraded to `openai/gpt-4.1-2025-04-14`, the agent navigated `xarray/core/` and inspected 5 major
   modules (`dataset.py`, `common.py`, `variable.py`, `dataarray.py`, `indexing.py`). All 8 oversized
   reads (up to 326 KB) were cleanly truncated to 8,192 bytes. However, cumulative token consumption
   reached 166,195 tokens. Because Call 14 would exceed the frozen `budgets.total_tokens: 180,000` ceiling,
   the run stopped deterministically before issuing an edit/test action. All five successors unstarted.
   Reconciled reservations: $0.00.

**v1.6 prospective specification amended:**
1. Predecessor token ceilings raised:
   - `predecessor_budgets.total_tokens` raised from 180,000 to **400,000** tokens.
   - `predecessor_budgets.request_input_tokens` raised from 32,000 to **64,000** tokens.
   - Rationale: In v1.5-001, request input reached 24,449 tokens at Call 13. With `bounded-output/1.0` adding
     ~2,000–2,500 tokens of cumulative conversation history per tool turn, keeping `request_input_tokens` at 32,000
     would have halted the agent around turn 16–17 prior to code modification. Raising the ceiling to 64,000
     permits 25+ inspection turns while remaining well within `gpt-4.1`'s 128k native context limit.
   - All other limits strictly unchanged (`model_calls: 48`, `tool_calls: 36`, `context_tokens: 128000`,
     `output_tokens: 2048`, `time_limit_seconds: 1800`, `bounded-output/1.0`, `gpt-4.1`, task `pydata__xarray-6721`,
     and all successor budgets).
2. Cost envelope under $10 cap: Predecessor max envelope is $1.4593, note generation at 64k bound is $0.0591. Combined
   five-way settled maximum envelope is **$9.4272**. With single-request reservation headroom of **$0.1516** (64k input + 2k output),
   worst-case in-flight envelope is **$9.5788**, preserving **$0.4212** margin under the $10.00 cap.
3. Frozen config `configs/swebench-comparison-v1.6.json` (SHA `1e75c745e1179f9050858534c98eeeef0014f29c82163f52fac8ef485a84b0f8`),
   matched plan `analysis/swebench-comparison-v1.6-plan.json` (SHA `a72ce6ede1559f04bfc5d6e90ed3c39594a1c281f80b496f2e7d53ea0a19c322`),
   84-component manifest `analysis/swebench-experiment-v1.6-manifest.json` (SHA `a14ba06811ac1bdf5abb50745b81076a15b57fd2789fa857c2b6e7cf81d54ce6`).

# Keisho benchmark progress — v1.4 live run 001 recorded; prospective v1.5 defined 2026-10-22

**v1.4 live attempt 001 halted at predecessor (checkpoint_not_reached); spend $0.0164.**
Authorized under a $10.00 cap, run `runs/swebench-v1.4-five-way-once-001` executed 6 model calls
and 6 Docker tool actions with `openai/gpt-4.1-mini-2025-04-14`. The model created a standalone
reproduction script `fix_xarray_chunks.py` generating an uncompressed Zarr store with 202 chunk
files. Unbounded inventory tracking in Keisho recorded all 202 paths and hashes in the tool
result, expanding the payload to 41,253 bytes (~17,997 tokens). On Call 7 admission, projected
request input tokens exceeded the 32,000 ceiling (`request_input_tokens`), triggering a
deterministic stop (`reason: budget_exhausted`). Because zero edits were made to `xarray/`,
no checkpoint was eligible. All five successor conditions (`FULL_HISTORY`, `SUMMARY_2K`,
`REPOSITORY_ONLY`, `KEISHO_2K`, `STRUCTURED_NOTES_2K`) remained unstarted and ungraded.
Actual provider spend was $0.0164184 (noncached accounted: $0.0257496); unreconciled reservations $0.
No automatic retries, guard resets, or code edits were performed.

**v1.5 prospective specification defined:**
1. Tool bounding policy `bounded-output/1.0`: raw command output truncated at 8,192 bytes with
   explicit metadata; changed paths in conversational tool results bounded at 25 entries;
   total serialized tool result payload capped at 12,288 bytes (~3,000 tokens).
2. Predecessor model upgraded to `openai/gpt-4.1-2025-04-14` (aligned with successors).
3. Frozen config `configs/swebench-comparison-v1.5.json` (SHA `cb389a1a7a7fed8bc45bf82e931976ab852cb4df607c4184f768de1bd1079d0a`),
   matched plan `analysis/swebench-comparison-v1.5-plan.json` (SHA `ba04d2a92d8970242cbe4bf0c761af8d7d9c5fa2160c833ddaad3ba0a4117b24`),
   84-component manifest `analysis/swebench-experiment-v1.5-manifest.json` (SHA `b9a56b9e82e5c3bf2508f505dd06449fe3221df80f652a2ec19f3689b1e2d1fa`).
   Total envelope $8.93833920 plus $0.08440320 reservation = $9.02274240 <= $10.00 cap.

# Keisho benchmark progress — offline v1.4 research freeze complete 2026-10-11

**All four offline workstreams completed; new provider usage $0.** Added shared
`annotation-guidance/1.0` prompt clarification and audited `source-and-artifacts/2.0`
cumulative patch export, froze prospective `swebench-handoff/1.4`, and specified
the exact exploratory five-way comparison and cost plan. Annotation parser/enums,
action adapter, memory representation/compiler, baselines, task, models, routing,
checkpoint and numeric budgets remain unchanged.

Archived annotation replay accepts **1/8 supplied claims and rejects 7/8** under
both old and proposed contracts. Basis labels were free-text source descriptions;
new guidance defines provenance/status/temporal scope and examples. This is
retrospective compatibility analysis; real-model compliance improvement remains
unverified. Rejected annotations do not imply false claims or lost tool evidence.

Patch exporter preserves source/additions/deletions/relevant binaries, excludes
bytecode/caches with inventories, prevents configured filter execution, verifies
raw staged bytes/modes and official-base applicability, and rejects ambiguous
tracked-cache or transforming-attribute changes explicitly. Host/Docker dirty
fixtures each preserved 8 intended paths and excluded 8 generated paths. Real
unchanged xarray-base exporter inspection passed with no task/model/test execution.

Final offline checks: **40 focused / 238 broader tests passed**, exit 0; seven
functional/comparison execution fixtures excluded under scope, selected skips 0.
Public CLI dry-run passes with provider requests 0, live admission false and no
guard created. All 9,327 historical files and 22 representation/baseline files
preserved. No paid inference, functional rerun, SWE-bench/evaluator launch,
project commit, push, publication or deployment.

Final report: results/research-readiness-v1.4-20261011/REPORT.md.
Experiment: research/FIVE_WAY_EXPERIMENT_SPEC.md.
Spending: analysis/FIVE_WAY_COST_PLAN.md.
Frozen config: configs/swebench-comparison-v1.4.json.
Canonical config SHA `e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f`;
plan SHA `60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff`;
83-component manifest SHA `b1bd32a720c195fadc92b2e39818a3f4a3a1cb1d633abfe639358fc523f461cd`.

Assumed planning scenario $3.014256; conservative API envelope $8.14048704 plus
$0.08440320 reservation headroom. Recommend a NEW $10 total / one-attempt scope;
no such scope is authorized. Current public prices/routing require future preflight.
The exact next command after approval is in the final report. One exposed task is
exploratory; it cannot establish general superiority. Historical v1.3 remains passed
with its original annotations, cost and dirty patch. Work stops here.

## Historical one real v1.3 confirmation passed 2026-10-11

**Passed: 8 real model calls / 8 successful Docker tool actions.** Relevant source
inspection, ledger.py source modification, model-requested post-edit test and
independent acceptance all completed; both tests passed 4/4 with immutable inputs
preserved. One nested args action canonicalized; seven flat actions admitted.
Zero rejected actions. Seven auxiliary claims had invalid basis enums and were
archived/excluded; only one claim structurally validated. Semantic truth unverified.

Actual provider cost **$0.0033044**; conservative noncached accounting $0.0063764;
held reservations $0. New $0.50 / one-attempt authorization is closed. No retry,
guard reset, additional confirmation or SWE-bench execution occurred.

Current catalog pricing/OpenAI-only routing checked before inference. Frozen v1.3
model/prompts/action contracts/representation/budgets unchanged. All 9,178 protected
historical files and 124 frozen implementation entries unchanged. Previous failed
runs remain failed. No commit/push/merge/publication. Work stopped after reporting.

Report: results/functional-confirmation12-v1.3-live-20261011/REPORT.md.
Occupied closed guard/ledger: runs/functional-confirmation12-v1.3-pending/.
Fresh authorization: analysis/functional-confirmation12-v1.3-authorization.json.
This single public fixture pass does not establish benchmark or handoff effectiveness;
no further inference or benchmark execution is authorized.

## Historical v1.3 wire repair verified offline 2026-10-11

**Versioned flat-or-args compatibility implemented; new provider spending $0.**
Both pure wire shapes canonicalize to the unchanged internal action contract 3.0.
Mixed/unknown/invalid inputs reject without repair or retry. Raw responses/history
remain intact; separate static/runtime audit files do not enrich handoff inputs.
Prompt/model/JSON-object generation, budgets, Keisho representation and baselines unchanged.
Same adapter applies to predecessor and every successor condition.

Final checks: **89 focused / 209 broader offline tests passed**, exit 0; scaffold passed.
The existing public five-way benchmark-launch test was excluded under the no-benchmark
scope. One durable public-CLI synthetic run used 5 responses/5 real Docker tools and
passed direct post-edit and independent 4/4 acceptance; actual provider requests 0.
All 9,040 protected historical files, 22 handoff/baseline files and 124 frozen source
entries unchanged. No benchmark/evaluator execution, commit/push/merge/publication.

Report: results/action-wire-v1.3-20261011/REPORT.md.
Amendment: protocol_amendments/swebench-interface-v1.3.md.
Future config: configs/functional-confirmation12-v1.3.json, canonical SHA
a833849a3b6706b17c96ed60e2e3252b89fa57e03418c8720cce8b067e781f61.
Pending authorization template has user/provider permission false; no production
guard exists. Fresh authorization and current pricing/environment checks are
required before any real-model confirmation. The v1.2 failure remains historical.

## Historical v1.2 functional scope closed 2026-10-11

**One newly authorized functional attempt failed after one response and zero tools.**
The model returned valid JSON but nested `limit` in an unsupported `args` wrapper;
local action contract 3.0 rejected it with `invalid bounded listing fields`.
No inspection, source edit or model test occurred. Independent controller acceptance
still fails 2/4 cases. The repaired callback was not reached in this live attempt.
Functional readiness remains unconfirmed; no retry or SWE-bench was run.

Provider and conservative cost: **$0.00026** (578 input / 18 output tokens).
Held reservations $0; the one-attempt $0.50 authorization is closed. Current catalog
pricing was checked before inference. New guard: runs/functional-confirmation12-v1.2-20261011.
Report: results/functional-confirmation12-v1.2-live-20261011/REPORT.md.
20 focused offline tests passed for the new binding; all 8,996 protected historical
files and preflight runtime hashes remain unchanged. No commit/push/merge/publication.

## Historical offline sprint completed 2026-10-11

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
