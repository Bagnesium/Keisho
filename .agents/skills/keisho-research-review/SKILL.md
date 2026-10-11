---
name: keisho-research-review
description: "Review Keisho experiment designs, analysis plans, results, and research claims when explicitly requested. Excludes ordinary feature implementation."
---

# Keisho research review

Activate through `$keisho-research-review`. This is a developer/reviewer workflow;
never inject its instructions into experimental predecessor or successor prompts,
handoffs, or accessible research archives. Never launch paid experiments.

Read relevant [project guidance](../../../README.md), [protocol](../../../PROTOCOL.md),
[prospective amendments](../../../protocol_amendments/), and
[development comparisons](../../../docs/development-suite.md).
Identify governing versions; historical documents do not automatically govern
newer amended work.

- State the question, hypothesis, intervention, comparison, experimental unit,
  primary outcome, and observable evidence that would contradict the hypothesis.
- Count independent tasks separately from paired branches, repeated runs, and
  multiple checkpoints of one task. Do not inflate sample size or generalize
  model dependence from one model pair.
- Check identical original task, checkpoint workspace, successor configuration,
  tools, continuation budgets, scoring, and stopping rules across branches,
  except the declared handoff intervention. Check prospectively recorded order.
- Keep private evaluator data and future outcomes outside checkpoint selection,
  handoff construction, and agent inputs. Audit access must match the declared
  condition; manual evidence lookup is a separate operating mode.
- Distinguish authored fixtures, retrospective development examples, real-use
  demonstrations, and held-out evaluation. Preserve early solutions and
  low-information checkpoints; do not quietly resample.
- Treat NO_CONTEXT, FULL_HISTORY, and matched-budget summaries as distinct
  baselines. Report source information, omissions, counting method, generation
  calls, and end-to-end cost differences. Full history is a larger-context
  reference; never silently truncate it. Matched-budget representations use
  the same available material.
- Separate unknown, not applicable, unstarted, infrastructure failure, model
  failure, and task failure. Separate continuation from failure-analysis
  eligibility; absent qualifying opportunities mean N/A, not prevented errors.
- Preserve raw results and frozen configurations. Propose prospective, versioned
  protocol changes without rewriting collected evidence.
- Matching mistakes and model self-reports do not establish causal inheritance.
  Fewer tokens do not establish sufficient information. Distinguish legitimate
  verification from unnecessary repetition; retain uncertain judgments.
- Verify cited papers and actual claims against primary sources when available.
  Existing citations are leads, not proof; disclose unavailable verification.
  Keep model-assisted annotations distinct from human review.

Return a concise review: strongest supported conclusion, material validity
problems, and smallest useful next experiment. Proposing an experiment does not
authorize execution. Do not generate another framework or long readiness report.
