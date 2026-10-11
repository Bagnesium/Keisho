# Prospective action-wire compatibility: interface v1.3

Recorded 2026-10-11 before any v1.3 model inference. This amendment authorizes
offline development and software tests only. No paid inference, benchmark task
execution, official evaluator run or new spending scope is authorized.

The sealed v1.2 functional attempt remains failed: one received response, zero
tools and $0.00026 charged. Its exact JSON text contained
`{"action":{"tool":"list_files","args":{"limit":100}},"claims":[]}`.
Using that text as a labeled offline fixture does not change the historical result.

## Identifiable intervention

`flat-or-args/1.0` is opt-in. Its local wire action schema 4.0 accepts two forms:

```json
{"tool":"list_files","limit":100}
{"tool":"list_files","args":{"limit":100}}
```

Both yield the same flat internal action under unchanged internal schema 3.0.
Nested form requires exactly `tool` and `args` at the action's top level.
Every argument must be inside `args`, whose value must be an object. Flat form
retains the existing tool and argument fields. Any mixture is rejected, including
equal or conflicting duplicate argument locations; values are never merged.

| Tool | Documented arguments |
| --- | --- |
| `list_files` | Optional `prefix` string, `cursor` string or null, `limit` integer 1–100 |
| `read_file` | Required `path` string |
| `write_file` | Required `path` and `content` strings |
| `shell` | Required `command` string |
| `finish` | Required `answer` string |

No unknown tools or arguments, missing required values, type coercions, alternative
wrappers or further nested structures are admitted. Duplicate JSON keys, non-finite
numeric constants, malformed JSON and unsupported string encodings are rejected.
Supported argument values, Unicode and whitespace remain exact. Omitted optional
arguments remain omitted; defaults belong to the unchanged listing implementation.
No action is invented, substituted, regenerated or retried.

Canonical actions still pass the existing session validator and execution checks:
safe relative paths, Git metadata restrictions, listing bounds, content/command
bounds, runtime symlink containment and the same Docker isolation. Shell remains
the existing repository-command capability within its isolated container; the
adapter does not grant host/network/credential access or relax command restrictions.
Immutable public fixture inputs remain part of the independent acceptance gate.
Accepted static validation is not proof of permitted runtime execution or task success.

## Unchanged generation and experimental inputs

The system prompt remains exactly `benchmark-agent/3.0`, SHA256
`47e63eb19aec604408d88f0463485ba6fb55a55af8c9a8d5053ec15ff6c4583c`.
Provider generation remains `response_format: {"type":"json_object"}` with output
mode `json_object/3.0`. Schema 4.0 is local and is never sent to the provider.
Models, routing, seed, temperature, fixture/objective, token/call/time/tool budgets,
checkpoint and public acceptance rule are unchanged from v1.2.

One explicit adapter option is shared by the predecessor and every successor
condition. There is no Keisho-specific recovery. The handoff representation,
compiler, importer, baseline instructions and note-generation prompts are unchanged.
New wire/admission diagnostics are artifacts outside the trajectory, so they do
not enrich handoff or full-history inputs. The original response is retained in
MODEL_RESPONSE events and assistant history; TOOL_CALL and callbacks use only
the admitted canonical action.

## Separate raw, compatibility and runtime records

HTTP bodies and provider/model response artifacts retain their existing capture
boundary and credential redaction. Each attempted v1.3 generation additionally
records `<role>_call_NNN-action-wire.json`: wire version, original decoded action
where unambiguous and representable, input shape, canonicalization flag, canonical
action, wire/canonical schema validation, static safety result and rejection reason.
Malformed, duplicate-key or unrepresentable inputs retain their original raw text;
the decoded action is unknown rather than a chosen or repaired interpretation.

Actual tool execution separately records `-action-admission.json`, with the
canonical action, runtime completed/rejected/infrastructure/not-executed result
and reason. Runtime symlink rejection cannot be mistaken for successful static
admission. `finish` is a terminal declaration, not a tool execution. A completed
shell command with nonzero exit is not a successful tool or successful task.

Opt-in `response-measurements/2.0` adds wire/canonical assessments and the actual
audit records. Legacy measurements retain their old version and semantics. Rates
continue to use actual model responses received; unstarted slots and missing
responses stay separate. Auxiliary annotation policy 2.0 is unchanged: invalid
annotations are diagnosed/excluded independently of action admission and accepted
annotations do not establish truth.

## Frozen prospective bindings

- Disabled comparison: `configs/swebench-comparison-v1.3.json`, canonical SHA256
  `471feb73c690c9d202ef7a42dc25bd0d00175dd752256973adf3e3afdc043a5a`.
- Matched plan: `analysis/swebench-comparison-v1.3-plan.json`, canonical SHA256
  `48ffc5d96806d5e4d3bbfb75ff41ec01ea3ab9b1fd3ec3f847b4101e9a873d42`.
- Disabled public confirmation: `configs/functional-confirmation12-v1.3.json`,
  canonical SHA256 `a833849a3b6706b17c96ed60e2e3252b89fa57e03418c8720cce8b067e781f61`.
- Wire schema SHA256 `b17d5737b9f67e70f8b21ea6e7d27a800b726acee86d4fe1b88f7e975e678d95`;
  internal schema SHA256 `48af7498236adb94a9e291c17269239ef998c1eda977dfd13e7dc1c14da73388`.

Both new authorization templates have inference permission false. Public dry-run
may inspect the pending binding without creating a guard or provider request.
A future confirmation must use a fresh user authorization bound to this config,
one attempt, `runs/functional-confirmation12-v1.3-pending` and a new explicit cap;
current pricing and environment must pass live preflight. The proposed $0.50 is a
planning cap, not permission. No historical authorization, guard or ledger reopens.
The comparison template likewise grants no benchmark permission.

Offline synthetic execution with the archived first action proves software
compatibility and fixture execution only. It does not establish a real-model
confirmation, general action reliability, benchmark readiness or handoff efficacy.
