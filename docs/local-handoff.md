# Package a coding session locally

```sh
./keisho pack --repo /absolute/project --session /absolute/session.json \
  --task "Finish the API migration while preserving old callers" \
  --out /absolute/bundles/migration --token-budget 2048
./keisho inspect /absolute/bundles/migration
./keisho inspect /absolute/bundles/migration --item S1
./keisho resume /absolute/bundles/migration --manual --workspace /absolute/new-project
```

Open the new directory in a **fresh** coding-agent session. Supply the printed
`new-project.keisho-resume/NEXT_SESSION_PROMPT.md` file. The prompt embeds only
the compact handoff. It does not include the administrative JSON or audit archive.
No API call, commit, stash, reset, cleanup, push, dependency installation or
repository command runs during these operations. Keep bundles outside the source
repository. Existing bundle/workspace/helper paths are refused.

The complete record is `state.json`; selection omissions and exact counting
method are in `manifest.json`. Source events/notes are in `evidence/session.json`,
and changed Git index versions are in `evidence/git-index/`. Current working file
contents, deletions by absence, binary bytes and ordinary file modes are preserved.
Staging metadata is retained for inspection; Git history and the index itself are
not recreated. Symlinks, hard links, special files, privileged modes and unresolved
merge indexes are rejected. Timestamps, ACLs, extended attributes, running services
and installed dependencies are outside capture. File/total limits are 8/128 MiB.
Submodule checkouts are omitted explicitly. Git metadata queries disable repository
filters, hooks and filesystem-monitor programs; they do not execute project commands.

`.env*`, private-key filenames, personal/infrastructure directories and evaluator
materials are excluded independently of Git ignore rules. High-confidence
credential patterns are filtered or redacted. Detection is heuristic, not perfect:
inspect exclusions and source material before sharing. Git-ignored untracked files
are omitted and reported. An incomplete environment is not an exact machine copy.
Interrupted creation leaves `INCOMPLETE` and cannot be resumed.

After edits, use `inspect BUNDLE --compare-workspace /absolute/new-project` to
compare additions/deletions and named evidence scopes. A changed scope means
revalidation is needed, not that the claim became false. Unrelated paths do not
invalidate every record; unknown dependency relationships remain unknown.

## Supported session inputs

Pass a sealed Keisho run directory, its `trajectory.json`, or a JSON serialization
of `FrozenTrajectory` with `events` and `sha256`. Hash chains/seals are validated.
Only externally visible events are interpreted. Tool observations remain test/file
scoped; model claims are not promoted by their declared certainty or citations.
An existing typed `state.json` can supply the unchanged legacy-serializer comparison.
Keisho traces with pending tool calls are refused; stop at a completed boundary.
Credential-bearing legacy comparison sidecars are omitted explicitly, without
changing the legacy serializer or transferring their unredacted contents.

Native Codex, Claude and other proprietary session imports are **not supported**.
Do not point the tool at undocumented private session stores. Explicitly export
text to a UTF-8 file, or supply this documented JSON format:

```json
{
  "version": "keisho-notes/1.0",
  "acceptance": ["Both old and new API callers pass integration tests"],
  "constraints": ["Preserve the public API; do not deploy"],
  "sources": [{"id": "note1", "text": "I ran the parser tests, but not integration."}],
  "items": [
    {
      "id": "parser-note",
      "category": "observation",
      "text": "The parser tests passed according to my notes.",
      "status": "OBSERVED",
      "source_ids": ["note1"],
      "scope": {"files": {"parser.py": null}, "environment": "local Python; config unknown"}
    },
    {
      "category": "failed_approach",
      "text": "A new-format-only parser rejected the old caller.",
      "status": "REJECTED_UNSUPPORTED",
      "source_ids": ["note1"],
      "scope": {"files": {"parser.py": null}, "environment": "legacy caller"},
      "retry_when": ["After the caller contract changes"],
      "conflicts_with": []
    },
    {"category": "next_action", "text": "Run integration with mixed-version callers.", "status": "UNCERTAIN", "source_ids": ["note1"]}
  ]
}
```

Categories: `progress`, `observation`, `hypothesis`, `failed_approach`, `question`,
`next_action`, `uncertainty`, `change`. Statuses: `OBSERVED`,
`SUPPORTED_WITHIN_SCOPE`, `HYPOTHESIZED`, `UNCERTAIN`, `REJECTED_SUPPORTED`,
`REJECTED_UNSUPPORTED`, `SUPERSEDED`. Imported prose is always labeled an unverified
report; a supplied "supported" label is preserved as a declaration and downgraded
for the successor. Explicit conflicts stay visible. Use recorded SHA-256 byte
hashes for known file scope; `null` means unknown, not a matching file.

Unknown hypotheses and attempts stay unknown when no session record supplies them.
`--accept` and `--constraint` append explicit required content. The compact compiler
selects whole records, keeping uncertainty, scope and retry conditions together.
Essential content overflow fails before a completed bundle is created. The
configurable 2,048-token default is an engineering starting point. Installed pinned
o200k/tiktoken assets provide exact text counts; without them a disclosed UTF-8-byte
conservative bound is used. This is not billed request-token measurement.

Manual evidence lookup is available via `inspect --item`; research comparisons
must place the complete bundle archive outside successor access. Workspace copies
are not process sandboxes. Obtain execution permission and use the existing
appropriate isolation before running untrusted code.
