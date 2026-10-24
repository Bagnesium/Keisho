# SWE-bench interface amendment v2.5 — PROSPECTIVE PROPOSAL (live execution NOT authorized)

**Status**: Prospective proposal on branch `feat/v2.5-repair`. Bagi has **not** approved this proposal. Live execution is **not authorized**.
All earlier freezes (v1.0 through v2.4) and all archived run directories (`runs/swebench-v2.4-five-way-once-001`, `runs/swebench-v2.4-five-way-once-002`, etc.) remain byte-identical and untouched.

---

## 1. Motivation: Attempt 002 Outcome & Audit Failure Diagnosis

On 2026-10-24, fresh attempt `runs/swebench-v2.4-five-way-once-002` executed under Bagi's one-launch authorization (capped at USD 10.00).

### What Succeeded
- The predecessor agent completed 7 model calls and 7 tool executions on `sympy__sympy-20590`.
- In Call 1, the model emitted conversational prose before its JSON action (`"I’ll trace the \`Symbol\` inheritance chain..."`).
- The runtime framing reader (`extract_action_json` via `parse_output`) correctly admitted the response under the Zero-Skip Brace Rule, stripped the framing, logged `predecessor_call_001-stripped-framing.json`, and executed the tool.
- In Call 5, the model edited `sympy/core/_print_helpers.py` (adding `__slots__ = ()` to `Printable`) and `sympy/core/tests/test_symbol.py`.
- In Call 6, the model placed `claims: []` inside `action`; this was correctly rejected under `invalid-action-strike/1.0` as strike 1, and the model received structured error feedback without terminating the run.
- In Call 7, the model corrected its action schema and executed a validation shell command (`python -m pytest sympy/core/tests/test_symbol.py ...`).
- Python returned exit code 1 (`No module named pytest`).
- The checkpoint predicate (`ValidationCheckpoint`) correctly triggered `checkpoint` (the first completed validation command result following a non-test source edit).

### Why Attempt 002 Stopped
Immediately after reaching checkpoint, `comparison.py` invoked post-execution observational response auditing:
```python
measure(predecessor, session, 'predecessor')
```
This crashed inside `src/keisho/benchmark/response_measurements.py:210`:
```
AttributeError: 'NoneType' object has no attribute 'get'
```

### Root Cause Analysis: Parser Divergence
1. **Auditor Divergence**: In v2.1, runtime response parsing was updated to `extract_action_json()` in `response_policy.py` to allow conversational framing under conservative rules. However, `response_measurements.py:assess_text()` was never updated; it continued using strict `json.loads(text)`.
2. When evaluating Call 1, `assess_text` encountered leading prose, raised `JSONDecodeError`, and returned `json_syntax_valid = False` with `proposed_action = None`.
3. In `measure_run()` line 210:
   ```python
   row['tool_execution_successful'] = completed and not result.get('cursor_stale',False) and (action.get('tool') != 'shell' or result.get('exit_code') == 0)
   ```
   `completed` was `True` (tool and result events existed in the ledger), but `action` was `None`. Evaluating `action.get('tool')` crashed with `AttributeError`.
4. Because `measure()` had no error isolation, this audit crash killed the run before handoff notes were compiled or successors were initialized.

---

## 2. Checkpoint Rule & Test Runner Findings

### Checkpoint Rule Assessment
- Registered rule in `configs/swebench-comparison-v2.4.json`:
  `"first completed validation/build/lint/test command result following a non-test source edit"`
- The predecessor's Call 7 command was `python -m pytest ...`. `completed_validation_command` recognized `python -m pytest` as a validation command head. The command executed in the container and completed with integer exit code 1.
- **Finding**: Checkpoint reached with exit code 1 **strictly follows the registered rule**. Checkpoint is an empirical boundary marking when predecessor work ends and successor takeover begins; it is **not** a passing grade. Exit code 1 is recorded in `checkpoint.json` and passed to handoff adapters (e.g. `source-change-with-failing-validation`). It is not an implementation defect.

### Test Runner Resolution: Repository-Local `bin/test` Recognition
- Inspection of the official SWE-bench evaluation script (`sympy__sympy-20590-selected-task-evaluator.jsonl`) reveals the command used by official grading:
  `PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' bin/test -C --verbose sympy/core/tests/test_basic.py`
- In SWE-bench's SymPy testbed, `pytest` is **not installed** in conda environment `testbed` or the base image. SymPy uses its own test runner script: `/testbed/bin/test`.
- In `src/keisho/benchmark/protocol.py`, `completed_validation_command` is extended to recognize repository-local `bin/test` forms:
  - `bin/test ...`, `./bin/test ...`, and `/testbed/bin/test ...`
  - `python bin/test ...`, `python ./bin/test ...`, and `python /testbed/bin/test ...`
  - Explicitly rejects POSIX system test utilities such as `/usr/bin/test`, `/bin/test`, or shell builtin `test`.
  - Reaffirms that checkpoint is an empirical boundary marking when predecessor work ends and successor takeover begins, triggered on completed validation results regardless of pass/fail (exit 0 vs exit 1).

---

## 3. Changes in v2.5

1. **Response Measurement Alignment (`src/keisho/benchmark/response_measurements.py`)**:
   - `assess_text()` now uses `extract_action_json(text)` from `keisho.pilot.response_policy`.
   - Stripped framing metadata is recorded into `row['framing']`.
   - Ambiguous duplicate keys within framed text continue to evaluate to `json_syntax_valid = True` and `response_structure_valid = False`.
   - Non-JSON numeric constants (`NaN`, `Infinity`, `-Infinity`) continue to evaluate to `json_syntax_valid = False`.

2. **Explicit Absent-Action Handling (`src/keisho/benchmark/response_measurements.py`)**:
   - Line 210 guards `action` with `is_action_dict = isinstance(action, dict)`:
     ```python
     is_action_dict = isinstance(action, dict)
     row['tool_execution_successful'] = (
         completed
         and not result.get('cursor_stale', False)
         and is_action_dict
         and (action.get('tool') != 'shell' or result.get('exit_code') == 0)
     )
     ```
   - If `action` is absent (`None` or not a dict):
     - `tool_execution_successful` explicitly evaluates to `False`.
     - No action proposal is invented.
     - `action_rejected` evaluates to `False` (no identifiable action was proposed), while `response_rejected` evaluates to `True` based on syntax/structure validity.

3. **Audit Measurement Error Isolation Policy (`src/keisho/benchmark/comparison.py`)**:
   - Post-execution response measurement is observational telemetry.
   - `measure()` in `comparison.py` wraps `measure_run()` calculation in a `try...except Exception as exc:` block.
   - Upon calculation failure:
     - `raw.write_artifact('response-measurements-failure.json', failure_record)` is persisted with error details and status `audit_calculation_failed`.
     - The top-level `result.json` records `'audit_status': 'audit_failed'` and `'audit_failures': [...]`.
     - Missing metrics are not labeled successful or fabricated.
     - The benchmark run continues without halting.
   - Failures writing artifacts (e.g. disk/permissions) remain outside the calculation handler and remain fatal.

4. **Repository Native Runner Recognition (`src/keisho/benchmark/protocol.py`)**:
   - `completed_validation_command()` recognizes repository-local `bin/test` and `python bin/test` command heads while rejecting system commands like `/usr/bin/test`.
   - Preserves explicit `exit_code` recording in checkpoint metadata.

5. **Test Version String Update (`tests/test_notes_reader_v22.py`)**:
   - Updated `test_v22_uses_guarded_reader_and_logs_without_retry` assertion to accept `V25_VERSION`.

---

## 4. Reconciled Accounting Across All Attempts

| Attempt | Status / Cause | Billed Cost (USD) | Ledger Cost (USD) | Notes |
|:---|:---|:---|:---|:---|
| v1.4 | Stopped: Call 1 URL escape | $0.0465 | $0.0543 | Reconciled |
| v1.5 | Stopped: Call 2 schema rejection | $0.0151 | $0.0210 | Reconciled |
| v1.6 | Stopped: Call 2 schema rejection | $0.0465 | $0.0543 | Reconciled |
| v1.7 | Stopped: Call 2 schema rejection | $0.0465 | $0.0543 | Reconciled |
| v1.8 | Stopped: Call 1 schema rejection | $0.0069 | $0.0094 | Reconciled |
| v1.9 | Stopped: Call 14 transport timeout | $0.3250 | $0.7397 | Held reservation $0.41472 |
| v2.0-001 | Stopped: Call 1 leading prose | $0.0465 | $0.0543 | Reconciled |
| v2.3-001 | Stopped: Call 8 malformed action | $0.0334 | $0.0800 | Corrected by strike rule in v2.4 |
| v2.4-001 | Stopped: Call 10 transport error | $0.0464* | $0.2359 | Call 10 billed UNKNOWN; held $0.189504 |
| v2.4-002 | Stopped: Call 7 audit crash | $0.0328 | $0.0768 | Predecessor reached checkpoint; audit crash |
| **Total Settled** | | **$0.6456** | **$1.3790** | *(Excluding unknown Call 10 and unreleased reservations)* |

---

## 5. Prospective Freeze Digests & Cost Envelope

- **Configuration Digest (`configs/swebench-comparison-v2.5.json`)**: `8facce961117b57c480a0bbf54138f460e59f2219fe1e82d89b2cab639e6a452`
- **Plan Digest (`analysis/swebench-comparison-v2.5-plan.json`)**: `2246575ecd820564c6607a2dfc9e3faf56420be0940a5a505fc1394008966a28`
- **Manifest Digest (`analysis/swebench-experiment-v2.5-manifest.json`)**: `bf4d261f64c995dc3fbe208c32be78ea42cd6785c63d4fc02582cccf4019b1da`
- **Final Source Freeze (`analysis/swebench-v2.5-final-source-freeze.json`)**: `b7db8ad583a779d664cad1aeab6eba7a05c0c79f764210eeff01562ccac13a5b`
- **Authorization Template (`analysis/swebench-comparison-v2.5-authorization-template.json`)**: `428e1085052c78a8de6e7a4192d876d7d4a482f43b1ae73941a3786e8f08deb4`

### Cost Envelope (Unchanged from v2.4)
- Predecessor maximum: $1.498644
- Successor maximum (5 conditions): $8.232210
- Note generation (2 calls): $0.018480
- Invalid predecessor attempts allowance (2 attempts): $0.055839
- **Total Shared Envelope**: **$9.805173**
- Largest single request reservation: **$0.189504**
- **Peak Bound**: $9.805173 + $0.189504 = **$9.994677 ≤ $10.00**
- Remaining headroom under $10.00 cap: **$0.005323**
