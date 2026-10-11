# SWE-bench launch binding 1.0

This user-authorized launcher repair binds the prepared, disabled comparison
configuration 1.1 and its recorded plan to a new output directory. It extends the
existing entry point and runner; scientific settings and response-policy 2.0
remain unchanged. Source configuration, plan, selected task/order, provider
mapping and image metadata are checked against immutable hashes from the repair
and preflight records. Candidate hashes are not adopted as new expectations.

The explicit CLI requires `--config`, `--plan`, `--run-dir`, and `--authorization`.
`--dry-run` shares binding and local runtime validation with execution, reads only
credential presence, makes no provider request, and creates no live guard. The
live command also requires `--approve-live`, verifies current unauthenticated
public catalog pricing/endpoint support, then uses the existing exclusive RawRun
mechanism to claim the recorded authorization before constructing a model client.
The authorization claim depends on the reference record hash, not the output name;
copies or concurrent launches cannot supply another attempt. Occupied, historical,
private and symlink output destinations are refused without a force option.

Execution continues the $10 scope recorded in
`runs/swebench-integration/exploratory-v1.1-preflight/authorization.json`.
Its historical ledger has zero attempts/charges/held reservations, verified before
binding the active ledger. This is not another $10 allowance and does not reopen
or edit the completed 1.0 ledger or the blocked preflight. The source 1.1 permission
remains false; a recorded execution copy changes only that permission and attaches
the explicit authorization/output metadata. One shared existing SpendLedger and
BudgetedModel retain conservative reservations and unknown-usage stops.

Run bindings propagate through note generation, per-condition artifacts, private
prediction namespaces and unique official evaluation IDs. A non-checkpoint
predecessor's terminal cumulative patch is preserved without scoring it as a
checkpoint. Automatic importer state and handoff token counts are saved for audit.
Whole-request handoff admission includes the already configured schema tokens;
budgets and handoff limits do not change. Budget-stopped execution is labeled
separately from finished or interrupted execution. No model notes are manually
rewritten and no benchmark-outcome repair is authorized.

Offline tests inject providers/evaluators and owned claim storage only through
test code, exercising the real public CLI. Production exposes no offline bypass
flag. Software fixture results are distinct from the one exploratory live attempt
after the protocol repair; no superiority or held-out reproduction claim follows.
