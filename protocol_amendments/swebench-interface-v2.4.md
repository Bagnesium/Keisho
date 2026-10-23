# SWE-bench interface amendment v2.4 — FROZEN 2026-10-23 (live execution requires a separate authorization record)

Approved by Bagi on 2026-10-23 at 15:17 UTC+5 ("freeze v2.4 with both fixes and run one pilot"). It supersedes v2.3 on branch feat/v2.4.
All earlier freezes and raw runs are byte-identical. Budgets, prices, prompts, models, the task and the envelope are unchanged from v2.3.

## v2.3 outcome (motivation)
One launch, at 15:13:30 UTC+5 (run runs/swebench-v2.3-five-way-once-001), ended with status checkpoint_not_reached and no condition run.
- The predecessor made 8 calls and 7 tools, including a correct source edit (`__slots__ = ()` on Printable).
- Call 8 nested `claims` inside `action` and was rejected as "response must contain action and claims only". Under v2.3 a response-level parse/schema error was terminal (model_failure), even though malformed actions inside a valid envelope count as strikes.
- Spend: billed USD 0.0333914, ledger USD 0.079986.
- Offline grading found a second defect. `evaluator.evaluate()` always used `.cache/swebench-evaluator/selected-task-evaluator.jsonl`, which holds pydata__xarray-6721, so grading of any sympy__sympy-20590 condition would have errored.
- Graded supplementarily, the predecessor's terminal patch resolved the task. It is not a condition.

## Changes
1. **invalid-action-strike/1.0** (`src/keisho/pilot/agent.py`, opt-in parameter; only v2.4 passes it). This applies when the response passed the usage, identity, budget and truncation checks but failed parsing or schema validation (`parse_output`). Then:
   - nothing is executed;
   - the response text is appended as the assistant turn, and the model receives the same `{"error", "invalid_action"}` tool-result feedback as the invalid-action path;
   - the response counts against the tool-call budget and the existing 3-consecutive-strikes rule (`repeated_tool_failure`);
   - protocol-failure.json records `counted_as_invalid_action` and the strike count.

   Usage, identity, token-ceiling and truncation failures stay terminal. There are still no automatic retries, and all token and cost ceilings are unchanged.
2. **Evaluator dataset** (`src/keisho/benchmark/evaluator.py`). Grading uses `<instance_id>-selected-task-evaluator.jsonl` (or the generic file) and refuses unless that file holds exactly one row whose instance_id equals the frozen task.

## Effect on earlier versions on this branch
`agent.py` and `evaluator.py` are pinned in the v2.1–v2.3 manifests, so a v2.1–v2.3 launch from feat/v2.4 refuses (fail closed). This is intended supersession. Earlier freezes stay valid on their own branches.
Do not run scripts/v23_proposal_digests.py on this branch; v2.4 files are produced by scripts/v24_freeze_digests.py.

## Digests
manifest / config / plan / final source freeze: 7f1b07990c8d77b06863fa33878841edf4c2d4e98fa387453875c4ed88d7d330 e9fe9eaa098cba683d52a121bf6c23d1995ae9aefb09fce6ce894bbbfae0c7b9 6f68728f10457269cb86410316286d48235ce30276c52ed9934e6a997f266e56 3babe47ed75f33c859fc02d354533c868aec6edb537575c53c38f19bc88b5151

## Envelope (unchanged from v2.3, cache-write input pricing, fee 1.05)
predecessor 1.498644 + successor 8.232210 + note generation 0.018480 + invalid predecessor attempts 0.055839 = 9.805173.
Adding the largest reservation, 0.189504, gives 9.994677 ≤ 10.00. Malformed-response strikes consume the same per-run token budgets, so they add no new spending.
