---
name: keisho-testing
description: "Implement or repair Keisho behavior using reproducible debugging, meaningful regression tests, and final-state verification when explicitly requested."
---

# Keisho testing

Activate through `$keisho-testing`. This is a developer workflow; never silently
inject these instructions into experimental predecessor or successor agents.

Inspect [README commands](../../../README.md), [environment configuration](../../../pyproject.toml),
[handoff boundaries](../../../docs/local-handoff.md), and relevant
[development checks](../../../docs/development-suite.md). Retain standard-library
unittest unless a framework change is explicitly justified.

- Establish initial public behavior and reproduce relevant failures. Record
  commands, environment, workspace state, and outputs; distinguish existing
  failures from regressions introduced by this change.
- Trace the cause across relevant components before patching. For new behavior
  or a bug fix, add a focused failing test when practical, then implement the
  smallest correct change. Do not delete working code merely because it predates
  a test.
- Test public behavior and invariants rather than matching one reference patch.
  Exercise actual CLI, filesystem, persistence, recovery, or integration paths
  when relevant; mocked responses alone do not establish these behaviors.
- For relevant changes, cover dirty-workspace restoration, staged/untracked/deleted
  files, exclusions, unsafe paths, incomplete bundles, conflicting evidence,
  stale scopes, interrupted operations, and token-budget overflow. Preserve
  uncertainty, failure scope, and omission reporting. Evidence links establish
  traceability, not semantic truth.
- Use reproducible operation sequences or property-based tests where useful;
  retain failing seeds or counterexamples. Do not add dependencies without
  authorization.
- Label fake model responses and scripted successors as software fixtures,
  never evidence that Keisho helps real models.
- Run focused checks after changes and the appropriate broader offline suite
  after the final edit. Recheck final files rather than reporting results
  from an earlier implementation. The documented broad command is:

  ```sh
  PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
  ```

- Keep copying separate from process isolation. Use existing appropriate sandbox
  controls; if isolation is unavailable, report blocked checks rather than
  bypassing it. Do not weaken tests, alter frozen results/configurations,
  print secrets, or reset experiment guards to obtain a pass.
- No provider API calls without separate explicit authorization. A configured key
  or historical spending cap is not new permission; preserve shared request
  accounting and unknown-cost stopping.

Report the implemented change, initial failure and regression evidence, exact
final-state commands/results, checks not run or skipped with reasons, and remaining
limitations. Do not claim “all tests pass” beyond the executed scope. Human review
remains distinct from model-assisted interpretation.
