# v2.1 reader audit

Commands: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m unittest -v tests.test_benchmark_v21` (and `discover -s tests`), Python 3.13.5, tiktoken 0.12.0, jsonschema 4.26.0, fresh clone (no gitignored assets).

## tests/test_benchmark_v21.py on fresh clone: 2 pass, 1 fail, 5 error (evidence/v21-tests-main.log)
All 6 non-passes are missing gitignored local assets (.cache CA/tokenizer/evaluator, runs/swebench-v2.0-five-way-once-001 response).
The "8 pass" claim is only reproducible on the machine holding those files.

## Coverage vs requested cases (existing v2.1 tests)
- Real v2.0 call-1 replay: present (extract + run_agent), asserts shell + `git status --short` prefix and framing log; but run_agent test does NOT assert the executed action, and the fixture is gitignored (not in public repo). tests/data/swebench-first-response is an older xarray response, not v2.0.
- multiple objects, array/quoted wrappers (fenced/unfenced), malformed outer with/without prose, duplicate keys, NaN/Infinity/-Infinity, JSON inside+outside fence, prose only: present.
- nested salvage: only via malformed-outer cases; valid-outer-wrapping-action not covered.
## Added (tests/test_reader_audit_v21.py, tests only): 14 tests, 12 pass, 1 skip (real replay; file absent), 1 expected-failure (gap marker)
real replay asserting executed shell action (skip-if-absent); synthetic reconstruction (labelled, not evidence about real bytes) asserting executed shell action, framing log and raw preservation; prose-only executes nothing + protocol-failure artifact; nested salvage with valid outer (STRICT+AUXILIARY); nested inside fence; multiple objects with prose; fence then outside JSON; quote in prose; array after prose; duplicate keys nested/fenced; nonfinite nested/fenced/after prose; STRICT path framing; malformed inside fence with prose.

## Caller coverage
All `parse_output` callers (pilot/agent.run_agent, scripts/agent_decision_diagnostic.py, scripts/benchmark_response_replay.py) and `parse_auxiliary(str)` go through `extract_action_json`; legacy STRICT path included. Amendment line 44 discloses this ("Universal reader scope").
GAP: STRUCTURED_NOTES_2K note generation (comparison.make_handoffs) uses plain `json.loads(response.text)`: no duplicate-key rejection (last wins), no framing tolerance; prose before JSON from gpt-6-luna would abort the run before any successor (no retry), the same failure class as v2.0. json_object response_format is requested, but v2.0 showed sol emitted prose despite it. NaN is indirectly rejected by render_structured (values must be strings). Not disclosed in the amendment (plan text says "across all six roles", which reads as agent roles). Also scripts/benchmark_response_replay.py:41 uses json.loads (legacy offline script).

## Full suite (evidence/full-suite-*.log)
f09df38 + audit tests: 300 run, 13 fail, 49 error, 25 skip. bf76f6e (pre-v2.1): 278 run, 12 fail, 45 error, 24 skip.
Diff: new non-passes = exactly the 6 test_benchmark_v21 tests (missing local assets); 1 fixed (test_response_policy write_file). No regression in older tests.
Error causes: missing gitignored assets (.cache prepared image 17, CA 13, tokenizer 3, runs/ fixtures 3, evaluator venv 1) = environment/pre-existing;
"prospective plan changed" 10 + "frozen experiment component changed: agent.py" 2 = old hash-pin (older-version tests pinned to superseded files/fallback task);
remaining assertion failures (subprocess exit 1 != 0 etc.) come from the same missing assets in functional/launcher tests, pre-existing at bf76f6e.
