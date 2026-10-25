# SWE-bench interface amendment v2.6 — PROSPECTIVE PROPOSAL (live execution NOT authorized)

**Status**: Prospective proposal on branch `feat/v2.5-repair`. Bagi has **not** approved this proposal. Live execution is **not authorized** (`provider_inference_authorized: false`, `live_execution_authorized: false`).
All earlier freezes (v1.0 through v2.5) and all archived run directories (`runs/swebench-v2.4-five-way-once-001`, `runs/swebench-v2.4-five-way-once-002`, `runs/swebench-v2.5-five-way-once-001`) remain byte-identical and untouched.

---

## 1. Motivation: Attempt 001 Startup Failure & Root Cause Diagnosis

On 2026-10-24, fresh attempt `runs/swebench-v2.5-five-way-once-001` was launched under Bagi's one-launch authorization `bagi-20261024-v25-01` (capped at USD 10.00).

### What Happened
- Execution halted immediately during initialization before any LLM inference:
  ```json
  {"exception":"KeyError","reason":"'openai/gpt-6-sol-20260922'","retry":false}
  ```
- **Zero tokens** were consumed, **zero model calls** were made, and ledger spending is recorded as `$0.00` billed / `$0.00` accounted / `$0.00` reservations.
- Predecessor and all five successor conditions remained unstarted.

### Root Cause Analysis: Dispatch Version Check Omission
1. In `src/keisho/benchmark/comparison.py:705`:
   ```python
   model_cls = V20OpenRouterChatModel if config.get('version') in ('swebench-handoff/2.0', 'swebench-handoff/2.1', 'swebench-handoff/2.2', 'swebench-handoff/2.3', 'swebench-handoff/2.4') else OpenRouterChatModel
   ```
2. When `config['version']` was set to `'swebench-handoff/2.5'`, the version check returned `False`.
3. Execution fell back to legacy `OpenRouterChatModel`.
4. In `src/keisho/agents/providers/openrouter_chat.py:68`:
   ```python
   require(allowed in ((model_id,), (MODEL_ALIASES[model_id], model_id)), "only the exact catalog-confirmed same-model pair is allowed")
   ```
   Legacy `MODEL_ALIASES` contained only GPT-4.1 aliases (`openai/gpt-4.1-mini-2025-04-14` and `openai/gpt-4.1-2025-04-14`). Accessing `MODEL_ALIASES['openai/gpt-6-sol-20260922']` raised `KeyError: 'openai/gpt-6-sol-20260922'`.

### Audit of Related Version Checks
An audit across `src/keisho/benchmark/comparison.py` revealed additional version omissions:
- **`check_public_catalog` (line 601)**: checked `config.get('version') in ('swebench-handoff/2.0', ..., '2.4')`, failing to flag `v20 = True` for v2.5 and prospective v2.6.
- **`runtime_preflight` (lines 494, 496)**: duplicated the version list up to `v2.5`, omitting prospective `v2.6`.
- **`execute` model factory**: lacked a standalone, callable factory function, which prevented offline unit tests from directly verifying production constructor selection without duplicating logic.

---

## 2. Changes in v2.6

1. **Single Source of Truth for Handoff Model Selection**:
   - Defined `V20_HANDOFF_VERSIONS = ('swebench-handoff/2.0', 'swebench-handoff/2.1', 'swebench-handoff/2.2', 'swebench-handoff/2.3', 'swebench-handoff/2.4', 'swebench-handoff/2.5', 'swebench-handoff/2.6')`.
   - Unified `select_model_class(config)` to return `V20OpenRouterChatModel` for all versions in `V20_HANDOFF_VERSIONS`, and legacy `OpenRouterChatModel` for prior versions.

2. **Production Model Factory (`build_model`)**:
   - Exposed `build_model(config, provider, role, ledger, *, mode='agent', stage=None, native_tokenizer=None, output_format=None, transport=None)` at module level.
   - `execute()` delegates directly to `build_model()`.
   - Ensures production constructor selection and instantiation are tested directly across predecessor, both note generators, and all 5 successor conditions.

3. **Auditing & Version Parity**:
   - `runtime_preflight` uses `V20_HANDOFF_VERSIONS` for catalog selection (`provider-catalog-v2.0.json`) and endpoint parameter checks.
   - `check_public_catalog` sets `v20 = bool(config and config.get('version') in V20_HANDOFF_VERSIONS)`.
   - `make_handoffs` recognizes `V26_VERSION`.
   - `malformed_options` in `execute` recognizes `V26_VERSION`.
   - `GUARDED_VERSIONS` includes `V26_VERSION`.

4. **Fail-Closed Offline Testing**:
   - `tests/test_v26_repair.py` patches `socket.socket.connect` and `urllib.request.urlopen` to fail closed with `AssertionError`, guaranteeing no test can accidentally contact external endpoints.
   - Model constructors accept `transport=fail_closed_transport`.

5. **Historical Preservation**:
   - `runs/swebench-v2.5-five-way-once-001/` and all historical runs/freezes remain byte-identical.
   - Consumed authorization `bagi-20261024-v25-01` remains expired and unchanged.
   - Prospective v2.6 template sets `provider_inference_authorized: false`.
