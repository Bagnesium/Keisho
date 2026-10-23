# SWE-bench interface amendment v2.1

Dated 2026-10-23. Supersedes `swebench-interface-v2.0.md`.

## Context & empirical motivation

Across seven consecutive handoff evaluation attempts on SWE-bench Verified (v1.4 through v2.0), all seven runs halted during the predecessor phase before any successor condition could run.

### Cost reconciliation across historical attempts

Earlier draft text reported row amounts summing to $1.2890 while stating an aggregate of $0.8845. This discrepancy arose from combining provider-billed figures for v1.4–v1.8 and v2.0 with the ledger-accounted ceiling figure for v1.9 ($0.7397), and comparing against the provider-billed total for v1.4–v1.9 ($0.8848). Below, costs are strictly separated by category (actual provider-billed cost returned by the API vs. conservative ledger-accounted non-cached cost ceiling):

| Attempt | Model | Halting Reason | Model Calls | Provider-Billed Cost (USD) | Ledger-Accounted Cost (USD) | Source Artifact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **v1.4** | `openai/gpt-4.1-mini-2025-04-14` | `budget_exhausted` (Call 6) | 6 | $0.0164184 (~$0.0164) | $0.0257496 (~$0.0257) | `runs/swebench-v1.4-five-way-once-001/spending.json` |
| **v1.5** | `openai/gpt-4.1-2025-04-14` | `budget_exhausted` (Call 13) | 13 | $0.1129100 (~$0.1129) | $0.3340940 (~$0.3341) | `runs/swebench-v1.5-five-way-once-001/spending.json` |
| **v1.6** | `openai/gpt-4.1-2025-04-14` | `stopped_on_error` / `budget_exhausted` (Call 14) | 14 | $0.1269260 (~$0.1269) | $0.4103180 (~$0.4103) | `runs/swebench-v1.6-five-way-once-001/spending.json` |
| **v1.7** | `openai/gpt-4.1-2025-04-14` | `invalid_run` (Call 8) | 8 | $0.0341920 (~$0.0342) | $0.0933280 (~$0.0933) | `runs/swebench-v1.7-five-way-once-001/spending.json` |
| **v1.8** | `openai/gpt-4.1-2025-04-14` | `budget_exhausted` (Call 22) | 22 | $0.2694420 (~$0.2694) | $0.7776660 (~$0.7777) | `runs/swebench-v1.8-five-way-once-001/spending.json` |
| **v1.9** | `openai/gpt-4.1-2025-04-14` | `finished` / `checkpoint_not_reached` (Call 29) | 29 | $0.3249300 (~$0.3249) | $0.7396500 (~$0.7397) | `runs/swebench-v1.9-five-way-once-001/spending.json` |
| **v2.0** | `openai/gpt-6-sol-20260922` | `model_failure` (Call 1) | 1 | $0.0044815 (~$0.0045) | $0.0044815 (~$0.0045) | `runs/swebench-v2.0-five-way-once-001/spending.json` |
| **Total (v1.4–v1.9)** | — | 6 predecessor halts | 92 | **$0.8848184** (~**$0.8848**) | **$2.3808056** (~**$2.3808**) | Sum within respective category |
| **Total (v1.4–v2.0)** | — | 7 predecessor halts | 93 | **$0.8892999** (~**$0.8893**) | **$2.3852871** (~**$2.3853**) | Sum within respective category |

Across all seven attempts, 35 successor conditions remained completely unstarted. In v2.0 attempt 001, `openai/gpt-6-sol-20260922` prepended conversational preamble prose before the JSON action on Call 1 (`"I’ll trace Symbol’s inheritance..."`), immediately failing strict JSON decoding (`JSONDecodeError: Expecting value: line 1 column 1`) with zero retries.

Specification v2.1 introduces a robust, non-salvaging single top-level JSON reader to admit valid actions enclosed in conversational prose or markdown code fences while rigorously rejecting ambiguous or malformed payloads.

## Interventions in v2.1

### 1. Robust single top-level JSON extraction
- **Zero-Skip Brace Rule**: The extractor scans for the first opening brace `{`. If unfenced, decoding begins strictly at that first brace using `_JSON_DECODER`. If decoding fails, the parser immediately raises `malformed outer JSON` without scanning further into the string, completely preventing nested-object salvage.
- **Strict single code block**: If markdown code fences are present, exactly one code block (2 fences) must exist. Content inside the fence must start with `{` and parse completely to the end.
- **Conservative wrapper rejection**: Text outside the admitted JSON object or its code block must NOT contain braces (`{`, `}`), brackets (`[`, `]`), or double quotes (`"`). This strictly rejects:
  - Multiple JSON objects
  - Array wrappers (`[{...}]`)
  - Quoted JSON string wrappers (`"{...}"`)
  - Mixed inside/outside fence actions
- **Internal string preservation**: Braces, brackets, and escaped quotes occurring *inside* JSON string values (such as shell commands or test scripts) remain fully valid.
- **Strict value validation preserved**: Rejection of duplicate keys (`_unique_object`) and non-finite numeric constants (`NaN`, `Infinity`, `-Infinity`) is preserved on all decoding paths.

### 2. Single extraction, framing metadata, & raw preservation
- `parse_output` extracts once per response. When `policy == AUXILIARY`, pre-extracted data is validated without redundant parsing.
- **Universal reader scope**: Every `parse_output` caller across the codebase now uses this reader (`extract_action_json`), including legacy `STRICT` paths that previously called plain `json.loads`.
- **Unconditional UTF-8 record validation**: `validate_recordable_json(data)` now runs unconditionally on every parsing path immediately after decoding. This intercepts unescaped lone surrogates (such as `\ud800`) as parse-time `ValidationError` exceptions instead of allowing downstream JSON serialization in event recording to crash with an unhandled `UnicodeEncodeError`. This change explains why the surrogate error in `test_response_policy` was resolved. No other behavioral changes are introduced.
- The raw response string is preserved byte-identically in `response.text` and conversation message history.
- Extracted framing metadata (`stripped_leading`, `stripped_trailing`, `is_fenced`, `has_framing`) is returned and recorded to `{role}_call_{number:03d}-stripped-framing.json`.
- The exact same reader and framing logger are applied across the predecessor and all five successor conditions. Zero retries remain enforced.

### 3. Preserved specification invariants
- **Task**: `sympy__sympy-20590`.
- **Prompts**: `SYSTEM_V5` (`benchmark-agent/5.0`) with verbatim workflow guidance block.
- **Models**: `openai/gpt-6-sol-20260922` (predecessor and successors) and `openai/gpt-6-luna-20260922` (note generators).
- **Reasoning effort**: `none` (`body["reasoning"] = {"effort": "none"}`).
- **Budgets**: Predecessor total tokens at 276,000; successor total tokens at 248,400; 64k request input limits; 2,048 output limits.
- **Cap & Cost Envelope**: Settled conservative envelope: **$9.53369760**; largest request headroom: **$0.155904**; peak in-flight: **$9.68960160** <= **$10.00** (3.104% margin).
