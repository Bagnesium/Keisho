# One fresh functional confirmation of repaired v1.2

Frozen 2026-10-11 before this scope's provider inference. The user authorizes
up to $0.50 for one fresh 12-call functional confirmation on the repaired v1.2
path, with current pricing checked first, no retries, and no SWE-bench.

Configuration: `configs/functional-confirmation12-v1.2.json`, canonical SHA256
`a2e7207a8226c173ec76eb43256f8011e80e6e3b26a8fadab1e032cfb5e327b4`.
Authorization: `results/functional-confirmation12-v1.2-live-20261011/authorization.json`.
Exclusive output/attempt guard: `runs/functional-confirmation12-v1.2-20261011`.
The previous configuration, interrupted run, ledger and guard remain historical.

Use the existing functional launcher and agent loop with v1.2's frozen
`benchmark-agent/3.0`, JSON-object output, local action contract 3.0 and
`bounded-listing/1.0`. The repaired inspection callback imports the shared
predicate from `keisho.benchmark.inspection`. Source configuration is the disabled
`configs/swebench-comparison-v1.2.json`, canonical SHA256
`f4c7733335e0991aebdc59ac393b8a347207b452accc1119831273f77691d425`.
Reading its contract does not authorize benchmark execution. This run replaces
the disposable container's repository with the unchanged six-file public fixture.

Retain the original fixture, objective, model, seed, temperature, token/time/tool
limits, acceptance rule and response capture. Twelve model/tool calls are ceilings.
Stop at the first completed direct model-requested post-edit public test, pass or
fail; malformed actions, provider/infrastructure failure or exhausted budgets stop
without regeneration. Success requires source inspection, permitted edits, that
test exiting 0 with the acceptance marker, independent acceptance passing, and
unchanged immutable inputs. Model context begins with only the frozen v1.2 system,
original objective and empty handoff. No historical response or solution is supplied.

Unauthenticated current catalog verification confirmed mini input/cache/output
rates of $0.40/$0.10/$1.60 per million and the exact OpenAI route. Twelve complete
32000-input/2048-output reservations with a possible 5% BYOK contingency total
$0.20256768, below $0.50. The live launcher rechecks the catalog before inference.
No paid validation request or credit top-up is permitted. The existing spending
ledger admits requests before transport, settles returned charges conservatively,
and retains the full reservation and stops when accounting is unknown.

Archive response bytes before JSON/provider/action processing with explicit
credential redaction and no headers. Use action contract 3.0 in stage measurements.
Report actual received-response denominators, unstarted calls, missing responses,
invalid JSON/actions/annotations, tool execution, task acceptance and spending
separately. A synthetic CLI pass establishes software behavior only; this one
public fixture cannot establish SWE-bench readiness or handoff effectiveness.
