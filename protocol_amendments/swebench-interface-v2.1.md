# SWE-bench interface amendment v2.1

Dated 2026-10-23. Supersedes `swebench-interface-v2.0.md`.

## Context & empirical motivation

Across seven consecutive handoff evaluation attempts on SWE-bench Verified (v1.4 through v2.0), all seven runs halted during the predecessor phase before any successor condition could run ($0.8845 total spend):
1. **v1.4** (`runs/swebench-v1.4-five-way-once-001`, $0.0164 spend): Halted at Call 6 (`reason: budget_exhausted`) due to context overflow from unbounded directory listing.
2. **v1.5** (`runs/swebench-v1.5-five-way-once-001`, $0.1129 spend): Halted at Call 13 (`reason: budget_exhausted`) after correctly inspecting code but reaching 180k tokens before editing.
3. **v1.6** (`runs/swebench-v1.6-five-way-once-001`, $0.1272 spend): Halted at Call 10 (`reason: budget_exhausted`) exceeding 32k request ceiling.
4. **v1.7** (`runs/swebench-v1.7-five-way-once-001`, $0.0342 spend): Halted at Call 8 (`reason: invalid_run`) due to fatal `read_file` error on misspelled `atomic.py`.
5. **v1.8** (`runs/swebench-v1.8-five-way-once-001`, $0.2541 spend): Halted at Call 22 (`reason: budget_exhausted` at 400k tokens) while reading inheritance chains without editing.
6. **v1.9** (`runs/swebench-v1.9-five-way-once-001`, $0.7397 spend): On `sympy__sympy-20590` with `benchmark-agent/5.0` workflow guidance, `openai/gpt-4.1-2025-04-14` executed 29 calls, correctly identified the bug, but called `finish` without attempting an edit or test.
7. **v2.0** (`runs/swebench-v2.0-five-way-once-001`, $0.0045 spend): On `sympy__sympy-20590` with `openai/gpt-6-sol-20260922`, the model correctly planned its actions but prepended conversational preamble prose before the JSON object on Call 1 (`"I’ll trace Symbol’s inheritance..."`). The strict JSON-only parser rejected the response (`JSONDecodeError: Expecting value: line 1 column 1`), halting the evaluation immediately without retries. All five successors unstarted.

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
