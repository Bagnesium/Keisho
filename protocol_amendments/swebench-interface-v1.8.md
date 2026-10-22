# SWE-bench interface amendment v1.8

Dated 2026-10-22. Supersedes `swebench-interface-v1.7.md`.

## Context & empirical motivation

During the live run under specification v1.7 (`runs/swebench-v1.7-five-way-once-001`), the predecessor attempt executed 8 model calls and 8 tool actions on `sympy__sympy-20590` ($0.0342 provider spend).
The predecessor model (`openai/gpt-4.1-2025-04-14`) inspected `sympy/core/symbol.py`, `basic.py`, `assumptions.py`, and `expr.py` to trace the inheritance chain of `Symbol`. On turn 8, it issued a `read_file` action for `sympy/core/atomic.py`. Because the SymPy module is named `sympy/core/atom.py` rather than `atomic.py`, the container `cat` operation returned exit code 1.
In specification v1.7, any non-zero exit from `cat` raised a fatal `InvalidAction('read failed')`, immediately halting the runner with `reason: invalid_run`. All five successor branches remained unstarted and ungraded.

## Interventions in v1.8

1. **Non-fatal file tool error observations**:
   - `read_file` failures (non-existent file, directory read, or permission error) return an error observation dictionary `{'path': path, 'error': error_text}` to the agent rather than terminating the run.
   - `write_file` execution failures return an error observation dictionary `{'path': path, 'error': error_text}` rather than raising fatal errors.
2. **Defensive tool error continuation**:
   - In `agent.py`, rejected non-escape tool actions return the error observation to the conversation history, allowing the agent to diagnose and correct mistakes on the next turn.
3. **Fatal path escape defense**:
   - Any path escape attempt (meaning `..` traversal or absolute paths outside the repository) remains a fatal `InvalidAction`, is logged in failure records, and terminates the run with `reason: invalid_run`.
4. **Consecutive failure ceiling (`repeated_tool_failure`)**:
   - To prevent runaway loops or budget waste, 3 consecutive failed or rejected tool calls terminate the run with `reason: repeated_tool_failure`.
   - Normal shell and test command executions (including non-zero test exits) remain normal observations and reset the consecutive failure counter.
5. **Invariant models, budgets & spending envelope under $10 cap**:
   - Task: `sympy__sympy-20590`.
   - Predecessor model: `openai/gpt-4.1-2025-04-14` ($2.00 / $8.00 per 1M tokens).
   - Successor model: `openai/gpt-4.1-2025-04-14` across all 5 conditions.
   - Generation model: `openai/gpt-4.1-mini-2025-04-14`.
   - Predecessor budgets: 48 calls, 400,000 total tokens, 64,000 request input tokens.
   - Successor budgets: 64 calls, 360,000 total tokens, 64,000 request input tokens.
   - Combined five-way settled maximum conservative envelope: **$9.4272** <= **$10.00**.
   - Peak in-flight envelope including reservation: **$9.5788** <= **$10.00**.
