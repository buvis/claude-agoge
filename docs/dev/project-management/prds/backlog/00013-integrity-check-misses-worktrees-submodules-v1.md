# Changes inside linked worktrees and submodules of the target go unseen

Source: agoge run 2026-11-08, finding 7 of 18 (MEDIUM, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records the worktree list but not each linked worktree's HEAD, and treats a submodule (gitlink) as one path. A lane that moves HEAD in a linked worktree, or commits, tags, branches or writes inside a submodule, passes the integrity gate. This matters only for targets with worktrees or submodules.

## Solution

- Record the HEAD of every entry in `git worktree list --porcelain`.
- For each gitlink (mode 160000 in `git ls-files -s`) with a checked-out directory, record `git -C <sub> rev-parse HEAD` and a hash of `git -C <sub> status --porcelain=v1 -z --untracked-files=all`.
- Report changes as kinds `worktree-head` and `submodule`.

## Requirements

### Must have
- Detaching or moving HEAD in a linked worktree makes `compare` exit 1 with kind `worktree-head`.
- A commit, edit or new untracked file inside a submodule makes `compare` exit 1 with kind `submodule`.
- Refs and config inside a submodule are out of scope; state this in the docstring.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects changes in linked worktrees and submodules`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: slower snapshots on repos with many submodules (two git calls each). Submodule refs and config stay unchecked.

## Test Strategy

Regression tests for worktree HEAD and submodule commit and untracked file. Reproduction from the run:

```
linked worktree: checkout -q --detach -> compare wt rc=0 unchanged
submodule (embedded gitlink, mode 160000), clean at baseline: tag t2 / config --local foo.y 1 / branch b2 -> each rc=0 unchanged
submodule dirty at baseline: second edit / commit -qam inner2 / untracked file -> each rc=0 unchanged; fingerprint stays " M dir"
```

## Tasks

- [ ] Add regression tests; watch them fail.
- [ ] Record per-worktree HEAD and per-gitlink HEAD and status hash.
- [ ] Document the limit; add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
