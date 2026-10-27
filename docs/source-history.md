# Source publication boundary

The first Git history records the already implemented Keisho tree in logical
subsystem commits. It does not reconstruct earlier development states or imply
that each commit was separately tested when that feature was originally written.
Commit timestamps reflect this initial publication, not experimental execution.

Tracked material includes source, tests, authored development fixtures (including
their evaluator-only cases), disabled configurations, pinned public protocol
resources, research documents and selected reviewed reports/metadata. Authored
fixture answers are not SWE-bench gold patches; runtime isolation keeps them out
of agent workspaces.

Raw execution archives, captured/resumed workspaces, installed environments,
Docker images, local certificates, credentials and official evaluator answer-key
material remain local. Their files and execution guards are preserved, not deleted
or reopened. The broad runs/results ignore rules prevent an accidental bulk add;
selected reports and metadata are tracked for frozen bindings and historical
provenance. The redistribution status of tracked OpenRouter catalog snapshots is
unresolved; see [the licensing review](../review/LICENSE_RESEARCH.md).

A clone is not the complete local evaluation installation or audit archive.
Docker-dependent and historical-artifact-dependent tests require the documented
local setup and retained artifacts; the public repository alone cannot reproduce
private evaluator inputs. See [the reproducibility guide](../research/REPRODUCIBILITY.md).
No credentials, old authorization or Git push grants new provider spending.

The superseded pre-run v2.1 draft pages and older paper drafts were removed;
versioned protocol records and the benchmark chronology preserve the relevant
history. The current empirical record is one completed five-condition exploratory run
on `pydata__xarray-6721`, reported in
[`paper/MANUSCRIPT_FINAL_PILOT.md`](../paper/MANUSCRIPT_FINAL_PILOT.md). Each
condition ran once from a shared checkpoint and all five patches received an
official `resolved` grade. This single-task result does not establish a causal,
statistical, or general advantage for Keisho. The current run archive and
private evaluator inputs remain local; the public clone cannot replay the paid
comparison. Earlier development failures and synthetic checks remain separate
from those empirical observations.
