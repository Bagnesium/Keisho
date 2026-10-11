# Keisho handoff evaluation on SWE-bench Verified: launcher repair and execution stop

The launcher integration is implemented and validated. Live execution was not
reached because the actual dry-run failed at Docker availability. No real model
request, predecessor, checkpoint, handoff generation, successor or new official
grade occurred. New provider charges and conservative accounting are $0, with
zero outstanding reservations. This is an environment-stopped execution milestone,
not model-effectiveness evidence.

The former launcher accepted only `--approve-live` and bound every downstream
path to the completed 1.0 run. It now requires explicit `--config`, `--plan`,
`--run-dir` and `--authorization`; supports `--dry-run`; and propagates the binding
through the existing runner, note generation, branch artifacts, prediction
namespaces and official evaluation identifiers. Immutable hashes from the repair
and recorded preflight reject changes to scientific settings or candidate hashes.
The source 1.1 file remains disabled; the supported execution copy changes only
permission and attaches authorization/output metadata.

An authorization-wide exclusive RawRun claim precedes model construction and
inference. It is independent of output name, so duplicate/concurrent starts
cannot create another attempt under this scope. The completed 1.0 guard and
blocked preflight remain historical. No module-level constants are redirected,
force option or production offline bypass is exposed, or expected input hashes
regenerated to hide mismatches.

Changed implementation: `scripts/benchmark_compare.py`,
`src/keisho/benchmark/comparison.py`, and `src/keisho/benchmark/evaluator.py`.
Added regression tests: `tests/test_benchmark_launcher.py` and test-only dependency
injection helper `tests/benchmark_cli_fixture.py`. Updated documentation:
`docs/swebench-handoff.md`, `protocol_amendments/swebench-launch-v1.0.md`, and
`BENCHMARK_PROGRESS.md`. Existing parser/claims, compiler, provider adapters,
spending controls, container isolation, task/model settings and official grading
were not modified in response to outcomes. Automatic importer state, handoff
token counts and non-checkpoint terminal cumulative patches are retained by the
bound execution path for audit.

Final-state offline validation passed **33 focused tests and 145 broader tests**.
The public CLI test uses non-default configuration/plan/output paths and injected
offline providers/evaluators, exercises an eligible software-fixture checkpoint,
all five branches, schema selection, note generation, prediction paths and
evaluation namespaces. Other tests cover mismatches, scientific changes concealed
by candidate rehashing, missing approval/counterparts, occupied/historical/symlink
destinations, dry-run without provider construction/requests/claims, concurrent
admission across different output names and historical preservation. These are
software fixtures, not real benchmark grades or provider requests.

Exact test argv, exit codes and complete output are saved in
`runs/swebench-integration/commands/launcher-focused-final/` and
`commands/launcher-offline-final/` (both exit 0). The earlier focused invocation
`commands/launcher-focused-01/` also passed and remains separate.

Bindings selected for the actual dry-run:

- Configuration: `configs/swebench-comparison-v1.1.json`, canonical hash
  `f6c5898f2400e7f6d24f70643da2333ea86fd3ba1b5fd30f4ec64ea0c2b3895e`.
- Plan: `runs/swebench-integration/response-policy-repair/prospective-plan-check.json`,
  canonical hash `acdb2ec7a25568290b2d0f4ace90b5c43190088825f9ea543402a71d18480ba2`.
- Existing authorization: `runs/swebench-integration/exploratory-v1.1-preflight/authorization.json`,
  canonical hash `92736e956e4a097172a4addd7f99fb54e862ad0544325efd9298c184bd0d6276`.
  The preflight's zero-usage ledger is reconciled read-only. No additional $10 scope
  was created, and no earlier completed ledger was reopened.
- Proposed run/output guard: `runs/swebench-integration/exploratory-v1.1-live`.
  Authorization claim: `runs/swebench-integration/authorized-92736e956e4a097172a4addd`.
  Both remain absent; this authorization was not consumed by dry-run.
- Task `pydata__xarray-6721`, official base `cc183652bf6e1273e985e1c4b3cba79c896c1193`;
  response policy `auxiliary-claims/2.0`, prompt/schema 2.0, structured adapter 1.1;
  predecessor/generator `openai/gpt-4.1-mini-2025-04-14`, successor
  `openai/gpt-4.1-2025-04-14`, unchanged public/canonical mapping and OpenAI-only routing.
- Frozen order: FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY, KEISHO_2K,
  STRUCTURED_NOTES_2K. Recorded envelope $8.14048704 plus $0.0844032 reservation
  headroom fits the same $10 ceiling under recorded assumptions. Current public
  catalog verification would occur before live admission; it was not reached.

The actual command was:

```sh
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.1.json \
  --plan runs/swebench-integration/response-policy-repair/prospective-plan-check.json \
  --authorization runs/swebench-integration/exploratory-v1.1-preflight/authorization.json \
  --run-dir runs/swebench-integration/exploratory-v1.1-live --dry-run
```

It exited **1**, with:

```text
failed to connect to the docker API at unix:///Users/bagnesium/.docker/run/docker.sock
connect: no such file or directory
```

Exact argv/output: `commands/launcher-real-dry-run/`. A separate recorded
`docker context show` returned `desktop-linux` (exit 0), while
`docker info --format '{{.ServerVersion}}'` reproduced the missing-socket error
(exit 1). The config/task/authorization/prompt/schema, saved catalog/provider,
credential-presence, TLS, tokenizer and installed harness checks preceded the
Docker failure. No secret was printed, inference or credential-validation request
sent, image pulled/built, Docker setting changed or isolation relaxed. Current
image availability could not be verified. The existing official smoke artifacts
and installed grading modules were reused, not rebuilt or regraded.

No successful real dry-run or live command exists for this task. The live command
would use the same arguments with `--approve-live` replacing `--dry-run`; it was
not issued after this unrelated environment blocker, per the user's stop rule.
Once the Docker daemon is available, the recorded dry-run is the exact next check.

| Condition | Execution | Official grade | Handoff tokens | Model/tool calls | Input/output tokens | Generation cost | Continuation cost | Annotation exclusions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPOSITORY_ONLY | Unstarted | None: Docker preflight failed | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0; no annotations supplied |
| FULL_HISTORY | Unstarted | None: Docker preflight failed | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0; no annotations supplied |
| SUMMARY_2K | Unstarted | None: Docker preflight failed | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0; no annotations supplied |
| STRUCTURED_NOTES_2K | Unstarted | None: Docker preflight failed | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0; no annotations supplied |
| KEISHO_2K | Unstarted | None: Docker preflight failed | Not constructed | 0 / 0 | 0 / 0 | $0 | $0 | 0; no annotations supplied |

Predecessor cost: $0. Total provider-reported charges from zero requests: $0.
Conservative accounted usage: $0. Held reservations: $0. No live ledger, agent
raw responses, importer state, checkpoint classification or evaluation IDs were
created. Unstarted branches are not task failures. There is no behavioral evidence
about reuse, repetition, inherited beliefs or relative handoff effectiveness;
software-fixture successes do not supply that evidence.

All 70 protected prior artifacts/configuration files remain byte-identical,
including the old cost record/guard, blocked preflight, disabled 1.1 configuration,
prepared plan and frozen selection. The old trajectory seal still verifies.
`runs/swebench-integration/launcher-integration/` contains preservation checks,
the selected binding, source hashes and this task's machine summary. No commit,
push, merge, publication, task resampling, model substitution or additional attempt
occurred. Stopped at the concrete Docker daemon blocker with the implementation
preserved.
