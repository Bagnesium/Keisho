# Phase 1 tasks

Exactly three deterministic fixtures are registered, all version 1.0.0:

| Task | Bug | False path available before handoff |
| --- | --- | --- |
| task_001 | Replacing a reservation double counts aggregate inventory | Deduplicating events by reservation ID |
| task_002 | Character lengths written into a byte-oriented UTF-8 frame | Tolerant decoding instead of fixing frame lengths |
| task_003 | Middleware changes signed empty metadata; error blames a key cache | Clearing an already correct cache |

`public.json` and `initial/` supply the agent-visible task, source, contract and
public cases. `gold.json` contains evaluator-only bugs, known fixes, hidden cases,
hypotheses, falsifying probes, scoped fact/action targets, exclusions and checkpoint
selection reasons. Gold files and raw logs are never copied into agent workspaces.

Nine-tool scripted development traces establish a useful observation and failed
approach while leaving each task unfinished. They do not establish real-model
checkpoint difficulty. See [calibration](../analysis/calibration-v1.0.0.json) and
[the Phase 1 report](../PHASE1.md). Synthetic traces are development artifacts,
not evaluation evidence.
