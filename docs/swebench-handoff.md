# Keisho handoff evaluation on SWE-bench Verified

This is a narrow bridge to existing tasks and unchanged official grading. It is
an adapted handoff evaluation, not an exact reproduction or leaderboard result.
One task cannot support statistical or general superiority claims.

## Pins and author reuse

`configs/swebench-comparison-v1.json` pins the official dataset revision, harness
commit/version and task-recipe commit. The two selected recipes were compared
privately with the revision-pinned HF dataset, including exact solution/test
patches and grading lists. Those fields stay in `.cache/swebench-evaluator/`.
The public task JSON contains only an explicit allowlist of issue metadata.

Handoff Debt v2 links a released MIT reference implementation. Its pinned pure
source-file signals and note/takeover prompts are retained in
`src/keisho/benchmark/vendor/` with license, source paths and SHA-256 provenance.
We reuse these artifacts, not its OpenHands runtime. Both note generators use
the same complete observable predecessor record, issue, changed-file inventory
and checkpoint cumulative patch. Keisho uses its automatic observable importer
and existing `compact/1.0` compiler. No developer-written bug explanation enters
an agent prompt.

Adaptations: existing Keisho JSON action/claim loop and provider models;
completed command heads rather than string matches in echoed text; compile/build
command recognition; 1600 generation output tokens; 2048 rendered handoff tokens;
no author retries or semantic text repair. The historical 1.0 adapter made its
continuation label UNKNOWN. Source inspection established that the author's label
uses observable events rather than hidden grades; prospective adapter 1.1 restores
that label and conditional verification advice. Official checkpoint grades remain
unavailable to all note constructors. See the
[response-policy amendment](../protocol_amendments/swebench-response-policy-v1.1.md)
and [offline repair report](../results/swebench-response-policy-repair/REPORT.md).
Deterministic validation excerpts retain at most the last 2000 characters with
an explicit omission label; generators receive full recorded output. Keisho
selects whole state items and records omissions. FULL_HISTORY contains every
observable event in the sealed predecessor record and is rejected if it cannot
fit the same 32000-input-token reservation, never silently truncated.
The original issue is a separate, identical task input for all five conditions;
the compact compiler's benchmark adapter references it instead of duplicating it
inside the 2048-token handoff. The complete state retains the original goal. This
is necessary for the selected issue, whose original text itself exceeds 2048 tokens.

The checkpoint occurs after the first completed validation/build/lint/test result
following a non-test source byte/mode change. The author's source-file heuristic
excludes tests and root scratch scripts. Recognized command heads include pytest,
unittest, compileall, build, lint/check tools and common project test/build
commands; `echo pytest` and reading test files do not count. A nonzero result is
eligible; a timeout is an incomplete action and cannot yield a checkpoint.
An edit first observed at the same boundary as validation has unknown intra-action
ordering; that records the edit and requires a subsequent validation result.
No checkpoint by the frozen 48-model/36-tool/180000-token predecessor budget ends
the experiment without resampling. Model messages are claims, not verified facts.

## Environment and isolation

The host uses a dedicated Python venv with the pinned harness, not global package
changes. `commands/environment-freeze/output.txt` records exact installed versions.
The pinned task Dockerfiles target linux/amd64. The harness invokes Buildx with
that platform on this ARM Mac; successful execution is emulated, not native ARM.
The gold smoke built one image locally, without registry fallback.
The selected Xarray source build failed because the libgdal-core download was
incomplete (8,896,512 of 10,419,110 declared bytes). Its complete failure log is
preserved under `commands/selected-image-build/harness-build-image.log`.
The official published amd64 image is an available recovery path, pinned to
manifest digest `58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898`.
`scripts/benchmark_image_prepare.py` verifies its official base and imports before
model admission and records the actual immutable image ID and environment versions.
The evaluator receives a documented local JSONL dataset input containing the
unchanged pinned official task-repo row (privately cross-checked against HF),
with only its image reference set to the digest. Official grading stays unchanged;
this avoids repeating the failed source build for each grade. No binary evaluator
assets are needed by this one selected instance.

Agents receive independent Docker writable layers of the same immutable frozen
image. No host volumes, home directory, Docker socket or provider credentials
are passed. Network is disabled, capabilities dropped, privilege escalation
disabled and process/memory/CPU limits are equal. Original Git storage is replaced
with a shallow repository at the official base commit, with no remote or later
solution refs. Background processes or output overflow stop execution. File
tools reject absolute/traversal/symlink escapes. Arbitrary repository commands
remain inside the container. This is a tested boundary, not a claim of complete
isolation against every Docker/kernel vulnerability.

The complete audit, note-generator source packet, other branches and evaluator
data stay host-side. The experiment agents are provider requests constructed by
`run_agent`; they do not inherit this development chat, skills or Codex contexts.
Docker freezing captures filesystem/environment state, not running processes.
Byte/mode restoration is checked before each branch. Gold/test patches are applied
only to separate official evaluator containers after continuation. Every submitted
patch is a binary-capable Git diff from the official base, including predecessor,
successor, staged, deleted and nonignored untracked changes.

## Commands and records

All setup/development commands and exact exit/output records live in
`runs/swebench-integration/commands/`. Earlier failures remain separate records.
Download/install commands can be replayed from their `command.json` in a fresh
checkout after creating `.cache/swebench-evaluator/sources` and the dedicated
venv. Source archives are commit-specific; the dataset parquet is revision-specific.
`scripts/benchmark_prepare.py` is exclusive and freezes exactly one task, order,
exclusions, branch order, current provider catalog and worst-case cost estimate.
Do not rerun it over an existing preselection or rewrite its frozen plan.

```sh
# Setup-only gold validation; never a Keisho success.
cd .cache/swebench-evaluator
venv/bin/swebench eval verified --gold -i sympy__sympy-20590 \
  --run-id UNIQUE_SETUP_GOLD_ID -j 1 \
  --task-repo sources/swe-bench-tasks-3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d

# Optional unpatched setup check, using official run_instances(skip_patch=True).
venv/bin/python ../../scripts/benchmark_unpatched.py \
  --task-repo sources/swe-bench-tasks-3d07b464b7b311a0cbfb5ed5b2d8a3b96f84a33d \
  --instance sympy__sympy-20590 --run-id UNIQUE_SETUP_UNPATCHED_ID
```

The official aggregate reporter counts an empty unpatched prediction separately;
inspect its unchanged per-instance `report.json` for the resolved boolean. CLI
exit zero alone does not establish resolution.

From the project root, final offline checks and the gated live entry point are:

```sh
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest tests.test_benchmark -v
PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_container_check.py
# After downloading the one digest-pinned selected official image:
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_image_prepare.py
# The completed 1.0 command remains closed. Explicit 1.1 launch binding:
.cache/swebench-evaluator/venv/bin/python scripts/benchmark_compare.py \
  --config configs/swebench-comparison-v1.1.json \
  --plan runs/swebench-integration/response-policy-repair/prospective-plan-check.json \
  --authorization runs/swebench-integration/exploratory-v1.1-preflight/authorization.json \
  --run-dir runs/swebench-integration/exploratory-v1.1-live --dry-run
# The same arguments with --approve-live instead of --dry-run execute once.
```

The live entry point validates the actual gold report and unchanged installed
grading modules before admission, then exclusively claims the referenced
authorization and the selected fresh run directory. See
[launch binding 1.0](../protocol_amendments/swebench-launch-v1.0.md). It must not
be restarted under another output name after that authorization is claimed.
The historical `comparison/` guard stays intact.
The new $10 authorization is registered separately from closed calibrations.
One shared existing SpendLedger/BudgetedModel reserves each request before
transport and includes predecessor, generation and all successors. Unknown
usage/route/cost retains the full reservation and stops further calls. No automatic
API retries or routing fallback. Frozen maximum token-price estimate is $8.14048704
with possible 5% BYOK fees; largest admission reservation is $0.0844032.

Equal successors have 64 model calls, 48 tools, 360000 combined tokens,
2048 output tokens/request and 1800 seconds. Branch order is frozen in the plan.
The same successor identity, system prompt, tools and stopping rules apply.
Official run IDs include condition, patch digest and a unique nonce, including
checkpoint grading. Resolved/unresolved/error grades and interrupted/unstarted
execution states are distinct. The provider ledger records requested/returned
model IDs, provider, usage and conservative/returned costs. Note-generation cost
is reported separately. Semantic reuse/repetition/inheritance assessments remain
unreviewed unless a human or explicitly labeled model-assisted review is saved.
Necessary verification is not automatically redundant work.

For Linux execution, use the same source/data pins and dedicated Python 3.10+
environment, an accessible Docker daemon with Buildx, linux/amd64 support,
sufficient disk for the two selected images, and preferably 16 GiB RAM. Official
full-benchmark documentation recommends 120 GB free disk, 16 GB RAM and 8 CPUs;
this bounded integration always starts with one worker. Paid cloud provisioning
is outside authorization. Preserve `BENCHMARK_PROGRESS.md` and guards when moving
artifacts; do not resample a task or restart attempted paid calls.
