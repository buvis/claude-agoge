---
lane: fast-track
design: skip
default_model: opus
model_tier_rationale: invented predicate - submodule discovery and per-gitlink state; several git edge cases
---
# Changes inside linked worktrees and submodules of the target go unseen

Source: agoge run 2026-11-08, finding 7 of 18 (MEDIUM, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records the worktree list but not each linked worktree's HEAD, and treats a submodule (gitlink) as one path. A lane that moves HEAD in a linked worktree, or commits, tags, branches or writes inside a submodule, passes the integrity gate. This matters only for targets with worktrees or submodules.

## Solution

- Add key `worktree_heads`: a map from each `worktree <path>` entry in `git worktree list --porcelain` to its `HEAD <sha>` value plus its `branch <ref>` line (or `detached`).
- Add key `submodules`: for each gitlink (mode 160000 in `git ls-files -s -z`) whose directory is checked out, record `git -C <sub> rev-parse HEAD` and a sha256 of `git -C <sub> status --porcelain=v1 -z --untracked-files=all`, both run through `_git`.
- `compare` reports changes as `{"kind": "worktree-head", "worktree": ..., "before": ..., "after": ...}` and `{"kind": "submodule", "path": ..., "before": ..., "after": ...}`.
- Bump `VERSION` by one.

## Requirements

### Must have
- Detaching or moving HEAD in a linked worktree makes `compare` exit 1 with kind `worktree-head`.
- A commit, edit or new untracked file inside a submodule makes `compare` exit 1 with kind `submodule`.
- Refs and config inside a submodule are out of scope; the module docstring says so.
- `VERSION` is bumped by one; an older snapshot file exits 2 with one line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects changes in linked worktrees and submodules`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: record per-worktree HEAD and per-submodule HEAD and status hash.
- **Exports**: `VERSION` (bumped)
- New symbols: `worktree_heads`, `submodules`, `test_detached_linked_worktree_is_worktree_head_violation`, `test_submodule_commit_is_submodule_violation`, `test_submodule_untracked_file_is_submodule_violation`, `test_dirty_submodule_second_edit_is_submodule_violation`
- **Risk**: slower snapshots on repos with many submodules (two git calls each). Submodule refs and config stay unchecked.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression tests for worktree HEAD and submodule commit and untracked file. Reproduction from the run:

```
linked worktree: checkout -q --detach -> compare wt rc=0 unchanged
submodule (embedded gitlink, mode 160000), clean at baseline: tag t2 / config --local foo.y 1 / branch b2 -> each rc=0 unchanged
submodule dirty at baseline: second edit / commit -qam inner2 / untracked file -> each rc=0 unchanged; fingerprint stays " M dir"
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_detached_linked_worktree_is_worktree_head_violation`, `test_submodule_commit_is_submodule_violation`, `test_submodule_untracked_file_is_submodule_violation`, `test_dirty_submodule_second_edit_is_submodule_violation` - Acceptance: `pytest -k "worktree_head or submodule"` fails on the unmodified script.
- [ ] Record per-worktree HEAD and per-gitlink HEAD and status hash; bump `VERSION` (depends on: previous task) - Acceptance: `pytest -k "worktree_head or submodule or worktrees"` passes.
- [ ] Document the limit; add the CHANGELOG entry (depends on: previous task) - Acceptance: the docstring names submodule refs and config as unchecked; `rg -F "changes in linked worktrees and submodules" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "worktree_head or submodule"` passes; the full suite passes under `dev/bin/release-checks`.
