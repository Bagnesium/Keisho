# Prospective v1.3 action-wire repair — offline only

**Implemented and verified offline. No new paid inference, benchmark execution
or official evaluator run occurred; new actual provider spending is $0.**
The historical v1.2 attempt remains failed after one response, zero tools and
$0.00026 charged. Its guard, ledger, raw body and outcome were not changed.

## Exact compatibility change

Opt-in `flat-or-args/1.0` accepts the existing flat action or a pure nested `args`
object containing only the selected tool's documented arguments. Local wire
schema 4.0 admits both; both validate as the unchanged flat internal schema 3.0:

```json
{"tool":"list_files","limit":100}
{"tool":"list_files","args":{"limit":100}}
```

Both produce `{"tool":"list_files","limit":100}`. The five supported tools are
`list_files`, `read_file`, `write_file`, `shell` and `finish`. Listing retains
optional prefix/cursor/limit; the others retain required path, path/content,
command or answer respectively. The amendment contains the full argument table.

All mixed flat/nested layouts reject, including equal duplicate values. Unknown
tools/arguments, missing required values, wrong types, alternate wrappers, further
nested structures, duplicate JSON keys, malformed JSON, non-finite decoded numbers
and unsupported Unicode encodings reject. Supported values are copied exactly:
no coercion, merging, defaults, action substitution, regeneration or retry.
Existing path, Git metadata, size, cursor, command and Docker runtime restrictions
still apply to the canonical action. Symlink containment is checked during execution.

The parser retains the original response text and assistant history. Separate
`-action-wire.json` artifacts record original shape/action, whether canonicalization
occurred, canonical action, wire/internal validation, static safety and rejection
reason. Separate `-action-admission.json` artifacts record runtime completion or
rejection. Unrepresentable/ambiguous decoded inputs remain unknown with the raw
response preserved. Static acceptance never establishes runtime or task success.

New diagnostics are outside trajectory events; they do not enrich handoff inputs.
`response-measurements/2.0` records wire/canonical assessments and actual audits.
Legacy paths keep their previous schemas, measurements and admission behavior.

One shared adapter option is used by the predecessor and every successor condition.
There is no Keisho-specific recovery. The exact v1.2 system prompt, models, routing,
JSON-object provider mode, seeds, budgets, public fixture/objective, acceptance rule,
handoff representation and baseline instructions remain unchanged. Schema 4.0 is
local and is not sent as a provider-enforced schema.

## Final verification after implementation edits

- **89 focused tests passed**, exit 0 (`actionwire-v13-final-focused-01`).
- **209 broader offline tests passed**, exit 0 (`actionwire-v13-final-broader-01`).
  The one existing public five-way benchmark-launch test was excluded before
  execution under the user's no-benchmark scope. No selected test was skipped.
  Parent-process provider/network I/O was guarded; CLI transports were synthetic.
- Scaffold check passed, exit 0 (`actionwire-v13-final-scaffold`).
- Pending public functional dry-run passed, live admission false, zero requests
  and no guard (`actionwire-v13-pending-functional-dry-run`).

New regressions use an exact tracked copy of the actual archived rejected response,
SHA256 `416621486868d09b5d194cfaa0094a5448bbc51a8d10343825a7acc517ab01fd`,
with provenance retaining the historical failure and charge. Coverage includes
all five tools in both shapes, conflicts, invalid fields/types, missing arguments,
malformed/duplicate JSON, unsafe paths, runtime symlink/Git aliases, annotation
acceptance/exclusion, lossless values, raw/canonical audits, and identical adaptation
for predecessor plus all five successor conditions. This is prospective software
testing of archived content, not a regrade or continuation of the historical run.

One durable fresh public-CLI synthetic execution passed using real Docker tools:

```sh
PYTHONPATH=src python3 tests/run_offline_functional.py --config-name functional-confirmation12-v1.3.json --output results/action-wire-v1.3-20261011/public-cli-synthetic
```

Its first synthetic response contains the exact archived text. Five responses
drove listing, source read, an intentionally failing pre-edit public test, permitted
source write, and passing direct post-edit public test. Independent acceptance
passed 4/4; immutable inputs were preserved. Five tools completed, four succeeded;
one unsupported auxiliary annotation was excluded without authorizing an action.
Actual provider requests/cost were 0/$0. All artifacts, command and seal are under
`public-cli-synthetic/`; this synthetic authorization exists only in the test fixture.

`preservation-and-final-verification.json` confirms all **9,040 protected historical
files**, **22 handoff/baseline files**, and **124 frozen source-manifest entries**
unchanged. Old/new trajectory seals validate; no owned agent containers remain.
All command logs are in `runs/swebench-integration/commands/<label>/`.
No commit, push, merge or publication occurred.

## Remaining limits and future confirmation

This verifies deterministic compatibility and software execution, not real-model
reliability, benchmark readiness or handoff effectiveness. Only the two documented
wire shapes are accepted; other layouts still stop. Static action validation is
not semantic authorization of arbitrary shell text: the unchanged repository
shell capability remains subject to its existing Docker containment and acceptance
checks. Annotation validity still does not establish truth.

Prospective amendment: `protocol_amendments/swebench-interface-v1.3.md`.
Disabled confirmation config: `configs/functional-confirmation12-v1.3.json`,
canonical SHA256 `a833849a3b6706b17c96ed60e2e3252b89fa57e03418c8720cce8b067e781f61`.
The template `analysis/functional-confirmation12-v1.3-authorization-template.json`
has both user and provider permission false. The proposed $0.50 cap is not authorized.
Twelve calls remain a ceiling; the first completed post-edit public test or an
admission/provider/infrastructure/budget failure ends the attempt without retry.

After fresh explicit authorization, create a new bound authorization record at
the path below; retain the disabled template and all old scopes. Recheck current
pricing/environment before inference. Proposed command, **not executed**:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python scripts/benchmark_functional_check.py \
  --config configs/functional-confirmation12-v1.3.json \
  --authorization analysis/functional-confirmation12-v1.3-authorization.json \
  --run-dir runs/functional-confirmation12-v1.3-pending \
  --approve-live
```

The comparison v1.3 config/plan also remain disabled and pending; they bind the
shared adapter prospectively without granting any benchmark authorization.
