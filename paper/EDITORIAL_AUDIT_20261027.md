# Editorial audit — 27 October 2026

## Scope and disposition

The source set included the v2.7 draft, a separate v2.6 manuscript, methods notes, an outline, and a pending-results note. They were used to establish the study/version boundaries and cross-check claims against the completed run artifacts, benchmark replay, and cited papers. The superseded drafts and working notes were deleted after the revision. The canonical deliverables are `MANUSCRIPT_FINAL_PILOT.md`, `.txt`, `.html`, and `.pdf`. The path `INCOMPLETE_MANUSCRIPT_20261027.md` supplied in the request was not present.

The paper is suitable for research review as an exploratory, single-task pilot. It is not ready to be represented as a completed confirmatory study or submitted under a venue-specific format. Author identity, affiliation, corresponding-author details, and a public artifact archive remain to be confirmed.

## Editorial changes

- Reframed the title, abstract, introduction, discussion, and conclusion around the actual study: one xarray checkpoint, five successor handoff conditions, and one completed run per condition.
- Replaced claims of general effectiveness with descriptive observations. The abstract and conclusion now state that all five branches were graded `resolved` on this task and that the experiment cannot rank the conditions by task success.
- Distinguished persistent repository state, predecessor observations, proposed edits, and executed edits. The manuscript says that the proposed predecessor edit was intercepted before execution.
- Removed causal language about why some branches used additional calls. The trace records an inspection call in two branches; it does not establish that handoff format caused the call.
- Clarified that the local lazy-array reproduction used an in-memory fixture, not a live Zarr store.
- Clarified that `STRUCTURED_NOTES_2K` was a local adaptation and is not an author-faithful reproduction of the published system.
- Added related work on SWE-bench, Handoff Debt, ESAA-Conversational, MemTrace, and Scroll, while stating that the latter systems were not comparison baselines.
- Added the four preceding protocol attempts and their billing separately from the completed five-condition outcomes.
- Removed claims that Keisho was the most token-efficient condition. The two generated summaries used fewer successor input tokens; Keisho used fewer than full history and matched its observed call count.
- Replaced presentation language that implied a publication venue, endorsement, or broader validation with a neutral research-manuscript layout.

## Technical and numerical checks

- The official empty-patch result for the predecessor is `unresolved`, `empty_patch: true`, exit code 0. Because this evaluator path does not execute the target tests, the manuscript reports the independent pinned-Docker replay separately.
- The replay collected 1,445 tests: the target test failed with `UnexpectedDataAccess`, 1,405 passed, 33 were skipped, one was xfailed, and five were xpassed. The earlier phrasing “all 1,405 regression tests passed” omitted the other collected outcomes and blurred the target failure; it has been replaced with the full accounting.
- The five successor grades and resource counts were checked against the completed run result. Input-token totals exclude predecessor and note-generation calls; the reported run-level charges include those stages.
- The checkpoint-verification result records the date, but its exact execution time could not be confirmed from the retained command log. The JSON now marks the ISO time uncertain and preserves the former value as unverified.
- The total billed and conservative-accounted amounts across attempts 001–005 are calculated from unrounded ledger values: USD 2.051310325 and USD 2.508869925. Displayed row amounts are rounded to six decimal places. Attempt 003 retains USD 0.379008 unreconciled.
- The run order was fixed, the branches were sequential, and the successor route did not support the requested provider-side seed. Elapsed times therefore remain descriptive and are not attributed to handoff representation.
- Run 005 is marked exploratory after protocol repairs. The four earlier v2.7 attempts are disclosed but are not pooled with the outcome comparison. The separate v2.6 SymPy experiment used a checkpoint with the repair already applied and is excluded.

## Citation and source checks

Bibliographic metadata and paper descriptions were checked against the cited arXiv records and the ICLR proceedings entry available during editing. The paper summarizes each work narrowly and does not claim that these systems were benchmarked against Keisho. The local structured-notes condition is explicitly distinguished from the published Handoff Debt implementation.

The references are not yet a substitute for a final citation-style pass against a target venue. Before submission, confirm the current versions and preferred archival records for the arXiv papers, and verify that each related-work description still matches the version cited.

## Remaining checks for the author

1. The byline now reads “Bagdat Beimzhan.” Add a formal affiliation, corresponding-author details, or a contribution statement if required by the target venue.
2. Decide whether the run artifacts and code will receive a public, stable archive. The manuscript currently says that no public archive or DOI is provided.
3. Confirm the experimental labels, model identifiers, and billing figures against the provider invoices and immutable run records before public release. The manuscript records the available run IDs and hashes, but this edit does not independently re-run the experiment.
4. Choose a target venue before final submission formatting. The current document uses a neutral single-column academic layout and makes no claim of acceptance or venue affiliation.
5. Consider a follow-up that holds handoff content constant while varying evidence labels, then repeats across tasks and runs. The current experiment changes content-selection rules as well as representation, so it cannot isolate a causal effect of typed provenance.

## Fidelity statement

No experimental result, sample count, task identity, reported model condition, or reported metric was intentionally changed. The benchmark replay counts are stated with the target failure and all reported collection outcomes. Interpretive claims were narrowed where the evidence did not support causal, statistical, or generalizable conclusions. Numerical summaries are descriptive for the single completed run.
