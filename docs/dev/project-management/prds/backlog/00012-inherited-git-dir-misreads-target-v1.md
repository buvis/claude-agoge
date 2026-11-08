# An inherited GIT_DIR makes the snapshot record another repository under the target's name

Source: agoge run 2026-11-08, finding 6 of 18 (MEDIUM, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` runs `git -C <repo>`, but `-C` does not override `GIT_DIR` in the environment. A caller with `GIT_DIR` set (a git hook, some wrappers) gets a snapshot of a different repo, labelled with the target's path, and exit 0. A compare against it then checks the wrong repo.

## Solution

In `_git`, pass an `env` copy with `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR` and `GIT_NAMESPACE` removed.

## Requirements

### Must have
- With `GIT_DIR` pointing at a second repo, `snapshot <target>` records the target's refs.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot ignores an inherited GIT_DIR and related variables`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: hides from the caller that its environment had a stray `GIT_DIR`.

## Test Strategy

Regression test: two scratch repos with different refs, run snapshot of repo A with `GIT_DIR` set to repo B's `.git`, assert the refs are A's. Reproduction from the run:

```
GIT_DIR=$SCRATCH/base/.git python3 -I target_snapshot.py snapshot $SCRATCH/hk out.json -> rc=0
output: repo: .../hk, refs: ['refs/heads/master', 'refs/tags/v1']   (base's refs)
hk really has: refs/heads/master, refs/stash
```

## Tasks

- [ ] Add the regression test; watch it fail.
- [ ] Strip the variables in `_git`.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes; the full suite passes under `dev/bin/release-checks`.
