# v2.1 launch readiness review (offline, box clone of f09df38)

Prepared 2026-10-23 (Asia/Almaty, UTC+5). No provider calls, no benchmark launch.

## Freeze integrity (digest = keisho canonical-JSON sha256, `keisho.core.digest`)
| Anchor | Registered | Computed | Match |
|---|---|---|---|
| config `configs/swebench-comparison-v2.1.json` vs `V21_SPEC_SHA`, plan.config_sha256, auth template | 0700ede4…eb5d | 0700ede4aed6d884cce2fdb50bdbedcc3bac427a5a195cc3bfdcc16bb437eb5d | yes |
| plan `analysis/swebench-comparison-v2.1-plan.json` vs `V21_PLAN_SHA`, auth template | f4fc73c0…ef2b | f4fc73c008785a909f12fcb74a16fa0810214a91b22f3894c55442de5b21ef2b | yes |
| manifest vs config.experiment_manifest_sha256 | 8bdb2fa9…4d08 | 8bdb2fa94a742aaae59b81e0860f76cbfadfe6a75d357c5feee05a18c4a64d08 | yes |
| 84 manifest component files (raw sha256) | — | 78 match, 0 mismatch, 6 absent (gitignored) | see below |

Raw-file sha256 (NOT the anchor scheme; likely source of earlier "conflicting digest" reports):
config 499a2e66…b9f7, plan 6797321e…dc17, manifest 8419be23…c958.
No manifest-frozen file changed between freeze commit 655a352 and f09df38.
`src/keisho/benchmark/comparison.py` (binding module, raw sha256 f9c78985…319c) is NOT in the manifest; the manifest refers to a
separate "final-source-freeze artifact" for it, and no v2.1 such artifact is committed. Unpinned binding module = gap.

Absent from a fresh clone (gitignored `/.cache/`, `/runs/*`), so freeze cannot be verified here:
`.cache/certificates/openrouter-ca-v1.2.0.pem`, `.cache/swebench-evaluator/sympy__sympy-20590-prepared-task-image.json`,
`.cache/swebench-evaluator/sympy__sympy-20590-selected-task-evaluator.jsonl`, `.cache/tokenizers/o200k_base.tiktoken`,
`runs/swebench-integration/preselection/sympy__sympy-20590-plan.json`, `runs/swebench-integration/preselection/sympy__sympy-20590-task.json`.

## Dry-run
The repo has `--dry-run` (scripts/benchmark_compare.py -> comparison.dry_run; zero provider requests). On the fresh clone it refuses:
`Benchmark start refused: prospective plan changed` (evidence/dry-run-fresh-clone.log). Cause: `load_frozen_plan` silently falls back
to `preselection/task.json` (pydata__xarray-6721) when the sympy task file is absent; its digest != plan.task_sha256 (edc429b5…b378).
Fails closed (good) but with a misleading message. Dry-run must be re-run on Bagi's machine that has the local assets.

## Exact commands (from code; run-dir name is a choice, must be new; authorization file must be a NEW record)
Dry-run (no spend):
```
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v2.1.json \
  --plan analysis/swebench-comparison-v2.1-plan.json --authorization analysis/swebench-comparison-v2.1-authorization-template.json \
  --run-dir runs/swebench-v2.1-five-way-once-001 --dry-run
```
Live (PAID, NOT RUN; requires Bagi's explicit approval and a new authorization JSON with version swebench-authorization/2.0,
config_sha256 0700ede4…, plan_sha256 f4fc73c0…, attempts 1, cap_usd "10.00", provider_inference_authorized true, fresh authorization_id):
```
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py --config configs/swebench-comparison-v2.1.json \
  --plan analysis/swebench-comparison-v2.1-plan.json --authorization <NEW-authorization.json> \
  --run-dir runs/swebench-v2.1-five-way-once-001 --approve-live
```

## Settings verified from config/plan/cost file
predecessor & successor model openai/gpt-6-sol-20260922 (request slug openai/gpt-6-sol per test), generation openai/gpt-6-luna-20260922, 2 generation calls,
reasoning effort none (plan assumptions + test asserting body reasoning={'effort':'none'}), automatic_retries 0, total tokens 276,000 / 248,400,
request input 64,000, output 2,048, cap $10.00, live_execution_authorized false. All match reports.

## Cost envelope recomputed (formula in analysis/five-way-cost-v2.1.json; rates sol $2/$10, luna $0.10/$0.50 per M, x1.05)
predecessor 1.05*(177,696*2 + 98,304*10)/1e6 = 1.40535360; each successor 1.05*(117,328*2 + 131,072*10)/1e6 = 1.62264480 (x5 = 8.11322400);
each note 1.05*(64,000*0.10 + 1,600*0.50)/1e6 = 0.00756 (x2 = 0.01512). Total 9.53369760. Largest reservation 1.05*(64,000*2+2,048*10)/1e6 = 0.15590400.
Peak 9.68960160 <= cap 10.00 (margin 0.31039840, 3.10%). Matches. Rates are from a 2026-10-22 unauthenticated catalog check; live preflight re-checks.
Historical spend: amendment table rows sum to 0.8892999 billed / 2.3852871 ledger (matches); underlying spending.json files are gitignored, not verifiable here.
