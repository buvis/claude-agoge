# A lane can install a git hook or edit .git/info in the target and the integrity check still says unchanged

Source: agoge run 2026-11-08, finding 2 of 18 (HIGH, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records HEAD, refs, index, tracked files, worktrees and local config, but not `.git/hooks/`, `.git/info/exclude`, `.git/info/attributes` or `config.worktree`. A lane that plants a hook gets code run on the operator's next commit, and the run report says `Target integrity: unchanged`. The gate is the pack's proof that a run left the repo as it found it.

## Solution

Hash every file under `hooks/` and `info/`, plus `config.worktree`, located with `git rev-parse --git-path`, into the snapshot as a new kind `gitdir`. Add a test that pins the list of `.git` entries the snapshot deliberately does not check (objects, logs, index, `FETCH_HEAD`, `ORIG_HEAD`, and similar), so a new git file forces a decision.

## Requirements

### Must have
- Writing, changing or removing a file under `.git/hooks/` or `.git/info/`, or `config.worktree`, makes `compare` exit 1 with kind `gitdir` and the path.
- A pinned-ignore-list test fails when the snapshot's ignore list changes without the test.
- Snapshot version bumps; an older snapshot file exits 2 with one line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects changed git hooks and .git/info files`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: the ignore list needs upkeep as git adds files. A format bump breaks older snapshot files (they exit 2, which is the contract).

## Test Strategy

Regression tests: snapshot, write `hooks/pre-commit`, compare → exit 1 kind `gitdir`; same for `info/exclude` and `info/attributes`. Reproduction from the run:

```
printf "#!/bin/sh\necho pwned\n" > hk/.git/hooks/pre-commit; chmod +x ...
compare hk -> rc=0 unchanged [] touched= []
.git/info/exclude (+lane-junk/, then new file lane-junk/x) -> rc=0 unchanged
.git/info/attributes (* filter=evil) -> rc=0 unchanged
```

## Tasks

- [ ] Add the three regression tests; watch them fail.
- [ ] Add the `gitdir` fingerprint and the pinned ignore-list test.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
