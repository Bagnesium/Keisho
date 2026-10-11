# Prospective OpenRouter calibration amendment 1.2.0

Authorized by the user's 2026-10-05 instruction for exactly one exploratory
task_001/seed17 calibration with `--approve-live`. API usage across predecessor,
handoff generation and all started successors shares a $1.35 cap, including any
request fees and BYOK charges, excluding taxes and credit-purchase fees. No credit
purchase or account billing change is authorized. The original direct-OpenAI
configuration, strict OpenRouter v1.1.0 configuration and their artifacts remain
unchanged. This amendment is recorded before inference.

The [API response schema](https://openrouter.ai/docs/api_reference/overview)
defines `model` as a string and illustrates a public model ID. It does not promise
equality to the catalog's `canonical_slug`. The model catalog is a separate
metadata contract. Consequently the strict equality assumption is unsupported by
the documented contract; this is a documentation finding, not a live observation.

The new public catalog was read without credentials using the exact runner Python
and shared urllib opener. Both mappings and endpoint restrictions were validated
before inference and frozen in `analysis/openrouter-catalog-v1.2.0.json`:

| Role | Exact request ID | Exact allowed response IDs |
| --- | --- | --- |
| Predecessor and summary | `openai/gpt-4.1-mini` | `openai/gpt-4.1-mini`, `openai/gpt-4.1-mini-2025-04-14` |
| Successor | `openai/gpt-4.1` | `openai/gpt-4.1`, `openai/gpt-4.1-2025-04-14` |

Only this exact pair per model is accepted in v1.2.0. v1.1.0 still accepts only
the canonical ID. No fuzzy matching, substitution or metadata rewriting is
permitted. Registered pricing identity, requested ID, actual returned ID,
reported upstream provider and fingerprint are recorded separately. Missing or
non-OpenAI provider metadata stops the block. Catalog labels and any reported
fingerprint do not attest the served upstream snapshot; attestation stays unknown.

Provider `only`/`order` stay `openai`, fallbacks stay disabled and parameter support
is required. Token rates remain $0.40/$1.60 per million input/output tokens for
mini and $2/$8 for full. Each request caps provider token prices at those rates and
per-request fees at zero. The confirmed catalog exposes no request-price surcharge
for these endpoints; absence is not independent billing attestation, so the
request-level maximum price remains explicitly zero.
No plugins or native tools are enabled. Reservations retain the 5% possible BYOK
fee contingency described in [BYOK pricing](https://openrouter.ai/docs/guides/overview/auth/byok),
without assuming account mode or a free allowance. Reported `is_byok` determines
settlement; absent route/cost stops execution. BYOK requires separately known
upstream billing, added to the router credit debit. The noncached ceiling and
reported total API cost are compared and the greater amount is accounted.

The worst-case planning envelope is $1.29011904 for 66 calls and 333,024 combined
tokens, leaving $0.05988096 beneath the cap. This is a planning envelope subject to
conservative per-request admission, not a promise that every branch will finish.
Every request, including the summary, reserves its full 32,000-token input
allowance and maximum output before transport. Unknown or failed attempts retain
their reservations and stop later calls. Automatic retries remain zero.

Python 3.14.2's configured default CA file was absent; an unauthenticated urllib
catalog request failed `SSLCertVerificationError`, verification code 20. The
repair is an explicit, hash-pinned project-local copy of the already installed
certifi CA bundle. `ssl.create_default_context(cafile=...)` keeps `CERT_REQUIRED`
and hostname verification enabled. The same shared opener is used for successful
public preflight and live requests. No system certificate or unrelated setting
was changed. Redirects remain refused.

Task content, prompts, nine-tool checkpoint criteria, handoff formats, serializer,
scoring rules and continuation budgets are preserved. Identity validation in the
agent/controller now reads the frozen exact allowlist; actual response IDs remain
unaltered. There is one predecessor, and at most four successors only after a
qualifying checkpoint. Early solution or ineligibility is saved without resampling.
The exclusive execution guard is never reset. No paid smoke test or unlogged
inference is permitted. All artifacts are retained; no general effectiveness
claim or human adjudication is implied.

Authorized execution:

```sh
./keisho calibration-block --config configs/calibration-task001-openrouter-v1.2.0.yaml --approve-live
```
