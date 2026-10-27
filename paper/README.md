# Keisho Research: Epistemic Handoffs in Multi-Agent Software Engineering

This directory contains the primary research paper and related manuscripts evaluating agent context handoff representations during mid-task takeovers between frontier model families on SWE-bench Verified.

---

## Primary Publication Deliverables

| Deliverable | Format | Description |
| :--- | :--- | :--- |
| [**MANUSCRIPT_FINAL_PILOT.pdf**](MANUSCRIPT_FINAL_PILOT.pdf) | PDF (8 pages) | Clean, publication-ready academic typesetting with full figures, tables, and reproducibility appendix |
| [**MANUSCRIPT_FINAL_PILOT.md**](MANUSCRIPT_FINAL_PILOT.md) | Markdown | Complete unversioned scholarly manuscript source |
| [**MANUSCRIPT_FINAL_PILOT.html**](MANUSCRIPT_FINAL_PILOT.html) | HTML5 | Self-contained, responsive academic web layout with print CSS |
| [**MANUSCRIPT_FINAL_PILOT.txt**](MANUSCRIPT_FINAL_PILOT.txt) | Plain Text | Formatted ASCII/UTF-8 text version for review and archival |

---

## Executive Summary

**Paper Title**: *Epistemic Handoffs in Multi-Agent Software Engineering: Empirical Evaluation of Mid-Task Frontier Takeover on SWE-bench Verified*  
**Authors**: Keisho Research Working Group (Lead: bagnesium)  
**Evaluation Target**: SWE-bench Verified (`pydata__xarray-6721`)  
**Frontier Pipeline**: Predecessor `openai/gpt-6-sol` $\rightarrow$ Note Generation `openai/gpt-6-luna` $\rightarrow$ Successor `anthropic/claude-opus-5.5`  

### Key Benchmark Results (5-Way Successor Takeover)

| Condition | Official Docker Status | Model Calls | Tool Calls | Successor Input Tokens | Successor Output Tokens | Wall-Clock Time (s) | Patch Strategy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`FULL_HISTORY`** | **`resolved`** | 4 | 3 | 138,443 | 1,585 | 32.7s | Replaced `hasattr(v.data, 'chunks')` with `v.chunks is not None` |
| **`SUMMARY_2K`** | **`resolved`** | 5 | 4 | 44,126 | 1,931 | 86.8s | Replaced `v.data` with `v._data` |
| **`REPOSITORY_ONLY`** | **`resolved`** | 7 | 6 | 54,526 | 2,315 | 53.8s | Replaced `v.data` with `v._data` |
| **`STRUCTURED_NOTES_2K`** | **`resolved`** | 5 | 4 | 45,429 | 1,650 | 86.5s | Replaced `v.data` with `v._data` |
| **`KEISHO_2K`** | **`resolved`** | **4** | **3** | **47,170** | **1,493** | **34.5s** | Replaced `v.data` with `v._data` |

### Core Findings
1. **5-Way Resolution**: All five conditions successfully resolved the task in official SWE-bench Docker containers.
2. **Context Token Savings**: `KEISHO_2K` achieved a **65.9% reduction in input tokens** (47,170 tokens) relative to `FULL_HISTORY` (138,443 tokens).
3. **Turn Efficiency**: `KEISHO_2K` completed the repair in the **joint-minimum number of model calls (4 calls)**, matching `FULL_HISTORY`, whereas narrative summaries (`SUMMARY_2K`, `STRUCTURED_NOTES_2K`) required 5 calls due to an exploratory verification step, and `REPOSITORY_ONLY` required 7 calls to re-explore from scratch.
4. **Empirically Verified Unresolved Checkpoint**: Verified directly in Docker that the predecessor's pre-execution intercepted unpatched state reproduced the target defect (`FAIL_TO_PASS` failed with `UnexpectedDataAccess: Tried accessing data`), while passing all 1,405 regression tests.
5. **Cost**: Actual provider billing was **$1.534741** for the completed comparison run ($2.051311 across all five session attempts).

---

## Supporting Artifacts

- **Docker Checkpoint Verification**:
  - Script: [`analysis/checkpoint_verification_command.sh`](../analysis/checkpoint_verification_command.sh)
  - Pytest Log: [`analysis/checkpoint_verification_log.txt`](../analysis/checkpoint_verification_log.txt)
  - Structured Outcome: [`analysis/checkpoint_verification_result.json`](../analysis/checkpoint_verification_result.json)
- **Historical Comparison Manuscripts**:
  - Earlier Preservation Pilot (`sympy__sympy-20590`): [`MANUSCRIPT_V26_COMPLETE_20261027.md`](MANUSCRIPT_V26_COMPLETE_20261027.md)
  - Working Draft Record: [`MANUSCRIPT_V27_COMPLETE_20261027.md`](MANUSCRIPT_V27_COMPLETE_20261027.md)
