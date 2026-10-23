# Specification v2.2 — FROZEN (live execution NOT authorized)

Status: frozen 2026-10-23 (Asia/Almaty, UTC+5) with Bagi's approval of the v2.2 freeze. `live_execution_authorized: false`; the authorization template
has `provider_inference_authorized: false`. No provider calls made. v2.1 and all historical records are unchanged.

## Motivation (prospective, from offline audit; no v2.1 run exists)
v2.1 guards the six agent roles, but STRUCTURED_NOTES_2K note generation parsed `gpt-6-luna` output with plain `json.loads`: prose before
the object would abort the comparison before any successor (zero retries) - the v2.0 failure class - and duplicate keys were silently
last-wins. Also the binding module `comparison.py` was not hash-pinned.

## Changes
1. `structured-notes-reader/1.0` (`src/keisho/benchmark/notes_reader.py`), used only when `version == swebench-handoff/2.2`:
   exactly one JSON object, optionally with prose before/after (quotes allowed) or inside exactly one code fence; `{}[]` outside the
   object/fence = ambiguous -> reject; no nested salvage; duplicate keys, NaN/Infinity/-Infinity, malformed JSON rejected; schema = exactly the
   7 frozen `structured_fields`, each a non-empty string (then the unchanged `render_structured`). Writes `structured-stripped-framing.json`;
   on rejection writes `structured-protocol-failure.json` (`automatic_retry: false`) and stops. Raw response is preserved by `logged_generate`.
2. SUMMARY_2K is free text (strip, non-empty); no JSON parsing, so no change. KEISHO_2K is compiled deterministically (no model call).
3. Binding-module pin: `analysis/swebench-v2.2-final-source-freeze.json` pins sha256 of `scripts/benchmark_compare.py`,
   `src/keisho/benchmark/comparison.py`, `experiment_freeze.py`, `notes_reader.py`; the authorization record must carry its digest
   (`final_source_freeze_sha256`), checked in `resolve_binding` (breaks the config<->comparison.py digest cycle).
4. Manifest v2.2 = v2.1 manifest (all 84 hashes identical) + `notes_reader.py` + `vendor/provenance.json`.

Unchanged: task sympy__sympy-20590, five conditions, prompts, models (gpt-6-sol x6 roles, gpt-6-luna x2 notes), reasoning effort none,
budgets, retries 0, cap $10, envelope $9.53369760, peak $9.68960160.

## Anchors (keisho canonical-JSON digest; regenerate with `python -B scripts/v22_freeze_digests.py`)
config e4afa4d3b87aa478f4ffd3c01789a3d98c5d86c1345c6b6eb25370484742ed8a
plan 35979af0c8ba6bff3ef87240503f6d7a4e738dbd795cd1b3367b95a807a60346
manifest 3658f6c13291c7d8d3893821329b36609f992be9443e63504d194a507d147ee1
final source freeze 8e11770df318af7b37172d72281a06a90945d6a48b9662026fdbdefdc9081c97
Any later edit to comparison.py/notes_reader.py requires regenerating all of the above.

Launch requires a fresh authorization record binding config, plan and final_source_freeze_sha256 with provider_inference_authorized true.
