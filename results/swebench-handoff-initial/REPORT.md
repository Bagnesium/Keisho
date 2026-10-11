# Keisho handoff evaluation on SWE-bench Verified

The official evaluator is validated and the continuation bridge is implemented.
This attempted live block produced **no handoff comparison**.

- Setup-only `sympy__sympy-20590`: gold resolved, unpatched unresolved according
  to unchanged official per-instance reports. Gold was never a Keisho success.
- Exactly one prospectively selected live task: `pydata__xarray-6721`.
- Predecessor: 1 model call, 0 tool calls, 2,971 input / 512 output tokens.
  Cost: **$0.0020076**, settled; no unreconciled reservations.
- Requested canonical model: `openai/gpt-4.1-mini-2025-04-14`.
  API request and returned model: `openai/gpt-4.1-mini`; upstream provider OpenAI.
  Snapshot attestation remains unavailable, as in the configured identity policy.
- Its first response used unsupported claim basis values, including `issue report`
  and `user environment details`; allowed values were tool/predecessor/independent.
  The proposed file write was never executed. Checkpoint eligibility is false;
  official checkpoint classification was not run.
- REPOSITORY_ONLY, FULL_HISTORY, SUMMARY_2K, STRUCTURED_NOTES_2K and KEISHO_2K
  are all **unstarted and ungraded**, not task failures. Note generation cost $0.
- No prediction was submitted for the live task. Cumulative patch export and
  prediction formatting were exercised by offline Git/Docker software checks.
- Reuse/repetition cannot be assessed: there are no executed tool actions or
  successor trajectories. No semantic or human effectiveness review is asserted.

The source image build failed on an incomplete libgdal-core download. Its complete
failure log is preserved. The official amd64 image was then pulled by manifest
digest, verified at the official base commit and used for the one predecessor.
There is no remaining host-platform blocker demonstrated by this run.

All costs, pins, commands, reports and per-condition states are in `report.json`.
Full raw requests/responses, diagnosis, sealed trajectory and spending ledger are
in `runs/swebench-integration/comparison/`. The exclusive execution guard is retained.
No retry, resampling, second task or further spending was performed. This bounded
block is closed; unused cap is not authorization for another trajectory.

This is integration/feasibility evidence, not a statistical research result,
exact reproduction, leaderboard submission or demonstration of Keisho superiority.

Final-state verification: 12 focused tests and 124 supported broader offline
tests passed. Docker restoration/independence/export/exclusion checks passed.
Earlier failed invocations are preserved separately. Per-condition metadata
artifacts are in `conditions/`; no live handoff notes were generated.
