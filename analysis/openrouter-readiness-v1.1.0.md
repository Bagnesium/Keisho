# OpenRouter implementation and offline validation

Implementation is complete; no calibration was launched. No inference or
credential-validation request was made. Public catalog GETs were unauthenticated.
The old direct-OpenAI approval does not authorize this new configuration.

## Changed files

- `.gitignore`: ignore `.env` and `.env.*`, except `.env.example`; isolate future router run directories.
- `.env.example`: tracked empty `OPENROUTER_API_KEY` template.
- `.env`: newly created, ignored local file; contents not printed; mode 0600.
- `src/keisho/local_env.py`: trusted project-root literal credential loading, environment precedence, safe diagnostics and credential redaction.
- `src/keisho/agents/providers/openai_chat.py`: shared transport/response hooks, redirect refusal, wrong-provider credential rejection and redaction of both keys. Original endpoint, model IDs and request parameters remain unchanged.
- `src/keisho/agents/providers/openrouter_chat.py`: explicit router endpoint/key, catalog-derived mapping, restricted routing, exact response identity, saved routing metadata and documented usage/cost parsing.
- `src/keisho/pilot/calibration_block.py`: separate versioned config/guard, catalog validation, effective provider manifest, shared ledger and explicit provider initialization.
- `src/keisho/pilot/cli.py`: explicit project-root loading before provider initialization.
- `src/keisho/pilot/runner.py`: record the configured provider in branch manifests.
- `src/keisho/pilot/spending.py`: router price ceilings, possible 5% BYOK reservation, returned-cost reconciliation and shared unknown-cost stop.
- `src/keisho/pilot/offline.py`: same scripted fixtures through an injected offline router transport.
- `tests/test_openrouter.py`: 15 focused offline tests.
- `configs/calibration-task001-openrouter-v1.1.0.yaml`: prospective bounded router configuration; original config untouched.
- `protocol_amendments/openrouter-calibration-v1.1.0.md`: prospective scope, model identity limitations and approval boundary.
- `analysis/openrouter-catalog-v1.0.0.json`: saved public catalog and endpoint evidence.
- `analysis/openrouter-calibration-plan-v1.1.0.json`: no-call plan including exact prompts, model mapping, routing and spending bounds.
- `analysis/openrouter-validation-v1.1.0.json`: test, preservation and secret-file checks.
- `analysis/openrouter-readiness-v1.1.0.md`: this report.
- `README.md`: local credential instructions and links to these records.

Only `.gitignore` and the empty `.env.example` were staged. No commit was made;
the repository's previously untracked project files remain in their existing state.

## Local credential status

Path: `/Users/bagnesium/Documents/GitHub/Keisho/.env`.
`OPENROUTER_API_KEY` is not currently populated in the loaded process environment.
No real secret file is tracked. Existing local contents are never overwritten.
The loader does not search parents, task workspaces or other dotenv names, execute
shell syntax, interpolate values, or import unrelated variables. Both keys remain
outside model prompts, snapshots, manifests and scrubbed tool environments.

## Actual checks

- 14 focused provider, loader and accounting tests: passed, 0 failures/errors/skips (0.015 s).
- 1 focused macOS isolation/injected-router block test: passed (0.899 s). The four synthetic branches completed; both key canaries and the host `.env` were inaccessible to subprocesses and absent from every saved workspace/artifact.
- Full existing plus new regression suite: **82 tests passed**, 0 failures/errors/skips (12.040 s):

```sh
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

The tests inject fake transports and scripted responses. They establish local
behavior, not live access or snapshot identity. The first automatic approval check
timed out before an isolation test started; its allowed retry passed. No approval
block remains. Both real execution directories and guards remain absent.

All 2,799 inventoried original config, task, protocol, compiler/state and artifact
files were byte-for-byte unchanged. Prompts, checkpoint rules, serializer, scoring,
handoff conditions, task_001 and all continuation budgets remain unchanged. Human
review fields remain pending.

## Model and cost limitations

The proposed mapping is `openai/gpt-4.1-mini` to required response
`openai/gpt-4.1-mini-2025-04-14`, and `openai/gpt-4.1` to required response
`openai/gpt-4.1-2025-04-14`, with only the `openai` upstream allowed. The public
catalog exposes the dated canonical labels, but this does not prove a served
upstream snapshot. An alias-only response is rejected, never treated as equivalent.
The response provider, model, generation ID, request ID, fingerprint and raw routing
fields are preserved when exposed; unexposed endpoint/snapshot identifiers remain
unknown. No authenticated completion behavior was checked.

The checked input/output prices per million tokens are $0.40/$1.60 (mini) and
$2/$8 (full). No cache saving or free BYOK allowance is assumed. Router reservations
include a possible 5% BYOK fee. Reported router debit plus known BYOK upstream
billing is compared with the noncached ceiling; the greater amount is accounted.
Unknown cost or billing route stops the block before its output can cause a tool
action or another request. Retries, fallback models and auto selection are absent.

| Stage | Maximum calls | Conservative envelope (USD) |
| --- | ---: | ---: |
| Predecessor | 9 | 0.04842432 |
| Summary | 1 | 0.01516032 |
| Four successors | 56 | 1.2265344 |
| Total | 66 | **1.29011904** |

Without BYOK fees the catalog-rate token envelope is $1.2286848. The shared cap
stays **$1.25 API usage, excluding taxes**. Conservative request reservations are
$0.01688064 for predecessor, $0.01516032 for summary, and $0.0844032 for successor.
Actual usage may allow completion; the cap can also stop before all four branches
start or finish. No complete comparison is justified in that event.

An unauthenticated public-catalog read through the current Python TLS stack failed
CA certificate verification. Catalog data was obtained using the system HTTPS
client with verification enabled. The live adapter still uses Python's verified
TLS; its CA setup needs attention before a paid attempt. TLS verification was not
disabled, and no credential or model-access probe was made.

See the [prospective amendment](../protocol_amendments/openrouter-calibration-v1.1.0.md)
for primary documentation links and the proposed command. Separate human approval
is required; no execution or guard reset follows from these offline results.
