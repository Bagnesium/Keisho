# Prospective OpenRouter calibration amendment 1.1.0

Status: implementation/offline validation only. No live execution is authorized by
this amendment. The earlier direct-OpenAI approval does not cover this configuration.
Original configs and all earlier artifacts are preserved.

The separate `configs/calibration-task001-openrouter-v1.1.0.yaml` uses the same
task_001 hash, seed 17, nine-tool checkpoint, four handoff conditions, prompts,
state serializer, scoring and continuation budgets as the original calibration.
Only authentication, provider routing, model-ID mapping and provider accounting
change. This remains one exploratory block, excluded from evaluation; no pilot,
conditioning or checkpoint resampling is permitted.

The public catalog checked on 2026-10-04 exposes:

| Role | Request ID | Required response model ID |
| --- | --- | --- |
| Predecessor/summary | `openai/gpt-4.1-mini` | `openai/gpt-4.1-mini-2025-04-14` |
| Successor | `openai/gpt-4.1` | `openai/gpt-4.1-2025-04-14` |

The dated IDs are actual catalog `canonical_slug` values, also exposed in OpenAI
endpoint names. They were not constructed from a presumed naming convention.
Catalog labels do not attest an actual upstream snapshot. No completion response
has been examined. Both the exact dated response ID and response provider `OpenAI`
are required; an alias-only, missing-provider or different-provider response stops
the block and retains its sanitized evidence. Snapshot attestation remains unknown.
Accepting aliases would require another explicit amendment and approval.

Routing sets `only` and `order` to `openai`, `allow_fallbacks: false`, and
`require_parameters: true`. One model is supplied, with no auto router, fallback
array, preset or plugins. `max_tokens`, seed, temperature and JSON response format
are supported by the selected endpoint catalog. Request prices are capped at the
catalog rates; per-request pricing is capped at zero. No SDK or client retry is used.
Returned IDs, provider, fingerprint, request body and usage are saved when exposed;
unexposed endpoint variants and upstream snapshot IDs are not inferred.

Catalog input/output rates per million tokens are $0.40/$1.60 for mini and $2/$8
for full. Full-input/output reservations assume no cache discount and add a possible
5% BYOK fee without assuming a free allowance. Settlement uses the greater of the
noncached ceiling and returned API cost. BYOK also requires known upstream billing;
missing cost, unknown billing route, overrun or provider failure holds the reservation
and stops every later stage. The $1.25 cap is unchanged. The 66-call, 333,024-token
planning envelope is $1.29011904; four-branch completion is not guaranteed.

Sources: [catalog](https://openrouter.ai/api/v1/models),
[routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting),
[BYOK pricing](https://openrouter.ai/docs/guides/overview/auth/byok).
Frozen public catalog evidence is in `analysis/openrouter-catalog-v1.0.0.json`.

After a separate human approval of this mapping and cap, the proposed command is:

```sh
./keisho calibration-block --config configs/calibration-task001-openrouter-v1.1.0.yaml --approve-live
```

This command was not run. Future execution uses its own exclusive guard and artifact
directory; the original guard is never reset. Human review fields remain pending.
