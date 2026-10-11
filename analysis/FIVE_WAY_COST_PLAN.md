# Five-way provider API spending plan

Prospective v1.4 plan, 2026-10-11. **No spending, credit purchase or execution is
authorized.** Recommend one overall **$10.00 total provider API ceiling** for one
fresh five-way block, conditional on explicit future authorization and current
public preflight. This retains the existing registered experiment ceiling and
numeric agent budgets. It is not an additional allocation under a historical scope.

The executable config's canonical digest is
`e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f`;
the matched launch plan's is
`60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff`.
The runtime manifest's canonical digest is
`b1bd32a720c195fadc92b2e39818a3f4a3a1cb1d633abfe639358fc523f461cd`.
The detailed independently checked arithmetic is also recorded in
[five-way-cost-v1.4.json](five-way-cost-v1.4.json).

## Dated pricing evidence and assumptions

Rates were read offline from the saved unauthenticated public OpenRouter catalog
[public-catalog-preflight.json](../results/functional-confirmation12-v1.3-live-20261011/public-catalog-preflight.json),
checked **2026-10-11 18:24:51.666536 UTC**. Its stated public source is
[OpenRouter's model catalog](https://openrouter.ai/api/v1/models), with saved exact
OpenAI endpoints and canonical mappings for both aliases. No public page or API
was fetched for this offline plan. These are trustworthy dated saved rates,
**not a claim of current prices at the future launch**; that verification remains
pending and is an admission gate.

| OpenAI endpoint model | Uncached input / million | Cached input / million | Output / million |
| --- | ---: | ---: | ---: |
| GPT-4.1-mini, `2025-04-14` | $0.40 | $0.10 | $1.60 |
| GPT-4.1, `2025-04-14` | $2.00 | $0.50 | $8.00 |

Only the catalog-confirmed OpenAI route is permitted. Do not use Azure/other route
prices to fit the plan. No cache discount, free credits, fee waiver or free BYOK
allowance is assumed. Conservative figures include a **1.05 multiplier** for the
existing possible 5% BYOK fee assumption. Its basis is the frozen provider policy
and recorded [OpenRouter BYOK documentation source](https://openrouter.ai/docs/guides/overview/auth/byok);
future fee policy also needs public verification. Account for total provider
usage, including upstream inference billed separately when BYOK is used. Credit
purchase/payment fees are not inference usage and are outside this estimate;
no purchase is planned or authorized. Unknown cost/billing route stops execution
and retains the request reservation rather than treating the attempt as free.

## Expected scenario: explicit assumptions, not a forecast

No SWE-bench model trajectory has established expected utilization. The following
planning scenario assumes a checkpoint within 12 predecessor calls and 20 calls
per successor; it is not extrapolated from the tiny successful public functional
fixture. Input means charged prompt tokens including retained history/framing,
not unique issue tokens. All five branches receive identical scenario assumptions
because there is no evidence to predict condition-specific cost advantages.

| Component | Assumed calls | Assumed input tokens | Assumed output tokens | Estimated API cost, 1.05 included |
| --- | ---: | ---: | ---: | ---: |
| Predecessor | 12 | 96,000 (8,000/call) | 12,000 (1,000/call) | $0.060480 |
| SUMMARY generation | 1 | 12,000 | 1,000 | $0.006720 |
| STRUCTURED_NOTES generation | 1 | 12,000 | 1,200 | $0.007056 |
| Keisho compilation | 0 | 0 | 0 | $0.000000 |
| REPOSITORY_ONLY successor | 20 | 200,000 (10,000/call) | 20,000 (1,000/call) | $0.588000 |
| FULL_HISTORY successor | 20 | 200,000 | 20,000 | $0.588000 |
| SUMMARY_2K successor | 20 | 200,000 | 20,000 | $0.588000 |
| STRUCTURED_NOTES_2K successor | 20 | 200,000 | 20,000 | $0.588000 |
| KEISHO_2K successor | 20 | 200,000 | 20,000 | $0.588000 |
| **Scenario total** | **114** | **1,120,000** | **114,200** | **$3.014256** |

Each assumed agent run fits its cumulative token ceiling; the table does not
guarantee that a next full-output request can always be admitted. Actual history
growth, annotation output, full-history size, edits and early stops can change
calls and costs substantially. Annotation tokens are included in agent output;
Keisho has zero extra compiler API calls, not zero end-to-end inference cost.
Full-history may cost more or stop earlier; this scenario deliberately does not
invent a measured representation saving.

## Conservative API upper bound

The frozen cumulative budgets are **input plus output**, so adding maximum output
on top of the total would double count. For a role with cumulative budget `T`,
call ceiling `N`, output cap `Q` and rates `r_in`, `r_out`, the safe ceiling is
`1.05 × ((T − O) × r_in + O × r_out) / 1,000,000`, where
`O = min(T, N × Q)`. Output costs more than input for both models, so maximizing
output under both constraints maximizes cost. This is an upper bound; real input
framing/history and request admission can make the extremum unreachable.

| Component | Call ceiling | Output ceiling used | Remaining input ceiling | Maximum accounted API cost |
| --- | ---: | ---: | ---: | ---: |
| Predecessor | 48 | 98,304 | 81,696 | $0.19946304 |
| SUMMARY generation | 1 | 1,600 | 32,000 | $0.01612800 |
| STRUCTURED_NOTES generation | 1 | 1,600 | 32,000 | $0.01612800 |
| Keisho compilation | 0 | 0 | 0 | $0.00000000 |
| REPOSITORY_ONLY successor | 64 | 131,072 | 228,928 | $1.58175360 |
| FULL_HISTORY successor | 64 | 131,072 | 228,928 | $1.58175360 |
| SUMMARY_2K successor | 64 | 131,072 | 228,928 | $1.58175360 |
| STRUCTURED_NOTES_2K successor | 64 | 131,072 | 228,928 | $1.58175360 |
| KEISHO_2K successor | 64 | 131,072 | 228,928 | $1.58175360 |
| **Total envelope** | **370** | **756,864** | **1,290,336** | **$8.14048704** |

Successor cumulative ceiling is 360,000 per branch; predecessor is 180,000.
Each note generator separately uses up to 32,000 input + 1,600 output. There are
at most 36 predecessor + 5×48 successor tool calls, **276 total**; tools do not
incur provider API charges. No retries, separate planning calls, semantic review
calls, checkpoint classifiers or model-smoke calls are budgeted or permitted.

The largest full request reservation is the full successor bound:
`1.05 × (32,000 × $2 + 2,048 × $8) / 1,000,000 = $0.08440320`.
It is temporary admission headroom, not another inference charge. Conservative
envelope plus this reservation is **$8.22489024**, leaving **$1.77510976** beneath
the proposed $10.00 cap. Settled-envelope margin alone is **$1.85951296**.
Do not spend this margin on extra calls or change the registered token budgets.

## Allocation recommendation and ledger behavior

| Planning allocation | Dollars |
| --- | ---: |
| Shared predecessor | $0.22 |
| Summary generation | $0.02 |
| Structured generation | $0.02 |
| Each of five successor branches | $1.65 each; $8.25 combined |
| Common reservation / uncertainty margin | $1.49 |
| **Overall proposed ceiling** | **$10.00** |

These are **advisory stage allocations**, not new branch dollar stopping budgets.
The existing shared ledger enforces one overall cap; all five successors keep
the same frozen model/tool/token/time ceilings. Imposing per-condition dollar
cutoffs would be a further experimental intervention and is not part of v1.4.
Fixed branch order is FULL_HISTORY, SUMMARY_2K, REPOSITORY_ONLY, KEISHO_2K,
STRUCTURED_NOTES_2K. Before each provider request, reserve its entire uncached
32K-input/full-output amount with 1.05 multiplier; settle from known usage with
the greater of noncached ceiling accounting or reported total API cost, recording
cached usage and BYOK/upstream/router costs separately. Unknown usage retains the
entire reservation and prevents subsequent calls. An authorization-wide atomic
guard prevents another run-directory name from reusing the same scope.

Current-price/routing mismatch must stop before inference; no cheaper model,
provider fallback or larger cap is automatic. Predecessor no-checkpoint means
only its actual spending is charged and all branches stay unstarted. If note
generation fails/overflows, retain incurred generator charges and stop without
regeneration. If a shared stop prevents later branches, record unstarted branches
as ungraded, not failures. Early finish and budget-stopped executed branches keep
their actual usage and terminal patches/grades where produced. Report the entire
assigned block; do not condition the cost comparison on only successful branches.

## Official evaluation and local costs

The unchanged official harness uses local Docker/CPU, **zero provider model API
calls**. The planned block has at most one checkpoint and five branch evaluations.
Keisho compilation and independent patch-format verification are also local.
Docker image storage, local electricity and host time are not dollar API usage.
No new paid cloud host is specified; if a future operator uses cloud compute,
that cost is **unknown and requires a separate quote and authorization**, not a
fabricated zero estimate. Log official evaluation wall time/resources separately.
Existing prepared images/source downloads and historical setup evaluations are
sunk development costs and are not charged again to this fresh provider scope.

Patch export disables configured Git filter drivers and checks staged content/modes
against raw worktree bytes/modes. Attribute transformations or changed tracked cache
paths reject with diagnostics before a grade; retain actual earlier inference costs
and the export-error status, without paying for a repair or retry. These checks
and official-base application verification are local, with no provider API charge.

## Required authorization and next command

Fresh authorization must bind the final v1.4 config and plan hashes, exactly one
fresh predecessor/five-way block, a unique authorization ID, no retries/fallbacks,
and at most $10.00 total provider API usage. It must explicitly set
`provider_inference_authorized=true` in a new authorization record; a template
with `false` is not approval. No historical $0.50 functional scope applies. The
launcher creates a fresh spending ledger and guard and rechecks public metadata.
See [FIVE_WAY_EXPERIMENT_SPEC.md](../research/FIVE_WAY_EXPERIMENT_SPEC.md) for the
complete frozen procedure. After that approval only, the next proposed command is:

```sh
PYTHONPATH=src .cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.4.json \
  --plan analysis/swebench-comparison-v1.4-plan.json \
  --authorization analysis/swebench-comparison-v1.4-authorization.json \
  --run-dir runs/swebench-v1.4-five-way-once-001 \
  --approve-live
```

This is a spending recommendation and an execution specification, **not an
authorization**. No paid call, functional run or SWE-bench execution was performed
to prepare this plan.
