# Actual OpenRouter calibration 1.2.0

Exactly one live task_001/seed17 block was executed. The predecessor wrote a
working fix at tool 9, the frozen cutoff. All four public and three hidden grader
cases passed. The checkpoint was **ineligible**, so no summary, handoff or
successor inference ran. Execution stopped without resampling or resetting its
guard. No credits were purchased and no account billing settings were changed.

The controller recorded `checkpoint_invalid` and exited 1. The predecessor's
`INVALID_RUN` label describes checkpoint eligibility. Its task passed the grader;
this outcome is neither a task failure nor an infrastructure failure.

## Calls, tokens and costs

| Stage | API calls | Tool calls | Input tokens | Output tokens | Accounted USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Predecessor | 9 | 9 | 21,171 | 1,000 | 0.0100684 |
| Handoff generation | 0 | 0 | 0 | 0 | 0 |
| Successors | 0 | 0 | 0 | 0 | 0 |
| Total | 9 | 9 | 21,171 | 1,000 | **0.0100684** |

Combined tokens: 22,171, including 16,000 reported cached input tokens.
OpenRouter reported **$0.0052684** in credit usage. All nine responses explicitly
reported `is_byok: false`; there was no external BYOK charge to add. The conservative
ledger retained the noncached price ceiling, giving **$0.0100684 accounted** against
the **$1.35 shared cap**, with **$0 unreconciled reservations**. Reported upstream
cost fields are preserved separately; they are not double-counted as external
BYOK charges when the response reports credit-funded inference.

Reservations kept the 5% possible BYOK fee contingency for every request, and
request-level maximum pricing remained zero. No account mode or free allowance
was assumed before dispatch. The preflight worst-case planning envelope was
$1.29011904 for at most 66 calls and 333,024 combined tokens. There were zero
inference retries, paid smoke tests or unlogged inference calls. Costs are from
response usage and the conservative ledger; invoices were not independently checked.

## Checkpoint and actual branch participation

The cutoff and hypothesis-exposure checks passed. Three eligibility checks failed:

- `task_unfinished`: the ninth tool wrote the successful fix.
- `established_observation`: the registered normalizer fact was not demonstrated
  by a passing probe in the predecessor trace. The later host grade cannot supply
  predecessor-visible evidence retroactively.
- `falsified_path_or_failed_approach`: no qualifying failed approach or refutation
  was demonstrated. The original failing task test alone does not satisfy this rule.

| Condition | Participation | Task outcome |
| --- | --- | --- |
| NO_CONTEXT | Unstarted | Unknown |
| FULL_HISTORY | Unstarted | Unknown |
| SUMMARY | Unstarted | Unknown |
| FIXED_STATE | Unstarted | Unknown |

Unstarted branches are not failures. The scripted checkpoint selection narrative
describes a failed ID-dedup patch and restoration; neither happened in this live
trace. The frozen checkpoint did not produce the required unfinished, informative
state. This block supplies no comparison of handoff conditions.

## Visible reuse and repetition

These are **model-assisted interpretations of recorded actions**. Human
adjudication remains pending; no hidden reasoning or causal inheritance is inferred.

- Within the predecessor, `predecessor_result_006` showed
  `replacement_then_release` returning 7 instead of 10. The public test definition
  in result 007 supported the replacement-accounting hypothesis in response 008.
  Tool 009 subtracted the prior hold before adding the replacement units. This is
  visible reuse within one trajectory; cross-model reuse was not measured.
- Tools 001 and 005 both called `list_files`, returning identical file and test-ID
  inventories with unchanged source hashes. The second listing added no new
  inventory and is a candidate for unnecessary repetition.
- Tools 003 and 008 read identical `ledger.py` contents. The second read immediately
  preceded the patch and may be legitimate implementation verification. Identical
  content alone does not establish waste.

## Connection, identity and verification

The key was loaded from the existing private project-root `.env` without printing
it. Python 3.14.2's absent default CA file caused certificate verification code 20.
A hash-pinned project-local copy of the installed certifi bundle repaired the
runner's explicit CA configuration. Public metadata GETs and inference used the
same Python urllib opener with certificate and hostname verification enabled,
and redirects refused. No system settings were changed.

The [API response schema](https://openrouter.ai/docs/api_reference/overview)
does not promise `response.model == catalog.canonical_slug`. The exact public and
canonical pair for each model was catalog-confirmed and saved before inference
in the prospective v1.2.0 amendment. The original strict v1.1.0 config remains
unchanged. All nine actual responses returned `openai/gpt-4.1-mini`, exactly the
requested public ID, with provider `OpenAI`. The dated canonical catalog ID was
`openai/gpt-4.1-mini-2025-04-14`. Returned metadata was preserved, not rewritten.
No response exposed a system fingerprint; upstream snapshot attestation remains
unknown. The full successor model's live availability and identity were not tested.

All 89 final offline regression tests passed, including credential isolation,
actual-alias controller/manifest validation, shared-budget stopping and the
exclusive guard. An earlier test caught a frozen core-interface change; the
interface was restored without altering the existing regression test. All 2,807
inventoried original files were checked: 2,805 were unchanged, while the two
agent/controller files contain the recorded identity-validation and fail-closed
infrastructure amendments. Tasks, prompts, budgets, serializers, scoring and
original configs were preserved.

There were **zero live transport, routing, provider, accounting or isolation
failures**. Both saved trajectory seals verified; all 90 raw artifact files were
inventoried and scanned, including decoded workspace snapshots. Neither credential
nor `.env` leaked into the artifacts. No source code changed after final preflight.

Human source-exclusion review and semantic annotation remain pending. Deterministic
grader success is separate from human review. A single task, seed and trajectory,
with no successors, supports no general effectiveness claim.

## Preserved evidence

- [Machine-readable experiment](openrouter-experiment-v1.2.0.json)
- [Final configuration](../configs/calibration-task001-openrouter-v1.2.0.yaml)
- [Prospective amendment](../protocol_amendments/openrouter-calibration-v1.2.0.md)
- [Connection evidence](openrouter-connection-v1.2.0.json)
- [Offline validation](openrouter-validation-v1.2.0.json)
- [Actual spending ledger](../runs/real-calibration-openrouter/calibration-task001-seed17-openrouter-v1.2.0/spending.json)
- [Complete recorded timeline](../runs/real-calibration-openrouter/calibration-task001-seed17-openrouter-v1.2.0/timeline.md)
- [Checkpoint](../runs/real-calibration-openrouter/pilot-5bce702b-c5e7-4f4c-94d9-0e59e8360644-predecessor/checkpoint.json)
- [Public and hidden grade](../runs/real-calibration-openrouter/pilot-5bce702b-c5e7-4f4c-94d9-0e59e8360644-predecessor/checkpoint-grade.json)
