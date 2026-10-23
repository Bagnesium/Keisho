# Gitignored manifest inputs (6) — classification

All 6 verified on Bagi's Mac against the manifest (sha256 match). Not in git; regenerate locally.

| File | Content | Source / regenerate | Redistribute in repo? |
|---|---|---|---|
| CA cert bundle | 121 public roots (Mozilla/certifi) | certifi, MPL-2.0 | Possible with MPL notice; prefer not |
| tokenizer o200k_base | public OpenAI BPE vocab | tokenizer CLI (VOCAB_URL, hash-pinned) | No (no stated license) |
| selected-task-evaluator.jsonl | full SWE-bench row incl. gold/test patch, FAIL_TO_PASS, eval_script | scripts/benchmark_prepare.py | **No** — hidden-test leakage |
| prepared-task-image.json | docker image id/ref, platform metadata | scripts/benchmark_image_prepare.py | No — local host info |
| sympy task.json | public problem fields | scripts/benchmark_prepare.py | OK but unneeded |
| sympy plan | cost plan, hashes, credential_presence booleans | benchmark_compare dry/plan | No — local state |
