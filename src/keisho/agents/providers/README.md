# Provider adapter contract

Phase 0 implements the interface and an offline scripted test double only.
Before Phase 1, implement one OpenAI adapter; add Anthropic when credentials
exist, and a local/alternative adapter when feasible. Keep SDK/authentication
inside this package. Do not read credentials during offline tests.

Adapters must preserve raw requests/responses, resolved model IDs, tool calls,
finish reasons, usage (including whether cached tokens are a subset of input),
and missing cost data. Token counting must identify its method and precision;
string length is not a tokenizer. Record unsupported seed behavior explicitly.
Native tool/context overhead belongs in full-request usage/context checks,
separate from additional handoff-text tokens. No provider is implemented or
called in Phase 0.
