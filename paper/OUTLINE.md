# Paper outline

Working title: **Auditable Observable-State Handoffs for Interrupted Coding Agents**

Status: methods implemented and software-tested; comparative results pending.
Potential workshop submission, not a finished empirical paper. No abstract claiming
better accuracy, reduced hallucinations or state-of-the-art performance is justified.

1. **Problem and question.** Repository edits survive an interruption; the meaning
   and validity of predecessor observations may not. Define observable task state,
   historical interpretation, named scope and continuation separately from hidden
   reasoning. Ask whether compact provenance/revalidation aids continuation.
2. **Related work and baseline audit.** Cite Handoff Debt's takeover protocol and
   actual released structured-note mechanisms, SWE-bench/Verified, then conduct a
   broader provenance/memory/context-selection review before any global novelty
   statement. Acknowledge baseline uncertainty, post-edit validation and contradiction
   repair. See `research/BASELINE_COMPARISON.md`.
3. **Implemented representation.** Automatic event import; conservative interpretation
   labels; source IDs/event hashes; named-file scope; existing revalidation policy;
   deterministic whole-item compact selection. State unknowns and lossy extraction.
   Compact references are not an agent-accessible evidence database.
4. **Evaluation method.** One observable checkpoint, same frozen workspace, five
   independent continuation contexts, matched compact limits, equal generator
   sources/model, unchanged official grading of cumulative patches. Explain output
   policy, resource/spending admission and baseline adaptations.
5. **Engineering validation.** Public-process import regression; synthetic provider
   through real Docker/tools; complete edit/test path; malformed generation and
   fault cases; five-branch orchestration. Keep this separate from model experiments.
6. **Empirical results — pending.** Predecessor eligibility/classification, paired
   resolution/preservation, end-to-end cost, scope-sensitive evidence reuse,
   annotation coverage, failures and omissions. No invented tables or placeholders
   resembling measured values. Closed development attempts belong in a limitations
   or engineering appendix, not an effectiveness aggregate.
7. **Ablations and validity.** Item provenance, labels, scope flags, deterministic
   selection; pair interactions and author-faithful baseline sensitivity. Report
   interruptions/unstarted branches and clustered units. Tests of interface behavior
   are not tests of research hypotheses.
8. **Discussion.** What observed evidence can and cannot preserve; representation
   overhead and low annotation coverage; conditions where existing notes suffice.
   Mechanism difference is not demonstrated benefit.
9. **Reproducibility/ethics.** Frozen sources/configs, protected evaluator data,
   raw observables without keys, no hidden chain of thought, paid scope guards,
   retained failures, model-assisted versus human-reviewed judgments.

Planned figures/tables, only when data exists: protocol/evaluator boundary; audited
mechanism table; task-level paired outcomes; total-cost versus resolution; annotation
coverage; model-pair interaction; examples with source events. Synthetic test outcomes
must carry explicit engineering labels. Do not graph their fixture grades as model
performance.
