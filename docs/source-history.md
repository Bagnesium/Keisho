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
selected safe metadata is explicitly staged when needed for frozen bindings and
closed-authorization provenance.

A clone is not the complete local evaluation installation or audit archive.
Docker-dependent and historical-artifact-dependent tests require the documented
local setup and retained artifacts; the public repository alone cannot reproduce
private evaluator inputs. See [the reproducibility guide](../research/REPRODUCIBILITY.md).
No credentials, old authorization or Git push grants new provider spending.

Current research evidence remains limited: official evaluator smoke validation,
closed real-model development failures/diagnostics, and explicitly synthetic
software checks. Source publication does not turn those into a five-way empirical
comparison or a demonstrated Keisho advantage.
