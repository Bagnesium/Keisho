# PROPOSAL — Specification v2.2 (NOT APPROVED, NOT FROZEN, NOT AUTHORIZED)

Status: draft prepared 2026-10-23 (Asia/Almaty, UTC+5) on a review branch. `live_execution_authorized: false`; the authorization template
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

## Anchors (keisho canonical-JSON digest; regenerate with `python -B scripts/v22_proposal_digests.py`)
config 0ea44d2fa53940bb2db20ac9fba123edc941a39aae7b04f5a85381599460e3be
plan 173633b56fce5f9cf1f5827617acaad60a49887a51aa134e56db8cdfcf57ebca
manifest 20860583df679d405742f95fede64d316bd69f8a9e0aea19b691aa67d3e7fed9
final source freeze 05d6f5521acc07cf17bc9daec4193b412f9d6c6af81ed48e628472cd67d7603c
Any later edit to comparison.py/notes_reader.py requires regenerating all of the above.
