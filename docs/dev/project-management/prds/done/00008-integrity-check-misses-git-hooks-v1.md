---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact paths, kind name and test contract given; two existing tests repointed by name
---
# A lane can install a git hook or edit .git/info in the target and the integrity check still says unchanged

Source: agoge run 2026-11-08, finding 2 of 18 (HIGH, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records HEAD, refs, index, tracked files, worktrees and local config, but not `.git/hooks/`, `.git/info/exclude`, `.git/info/attributes` or `config.worktree`. A lane that plants a hook gets code run on the operator's next commit, and the run report says `Target integrity: unchanged`. The gate is the pack's proof that a run left the repo as it found it.

## Solution

Locate `hooks`, `info` and `config.worktree` with `git rev-parse --git-path <name>`. Record a new snapshot key `gitdir`: a map from each file's path relative to the git dir to its `_fingerprint`, covering every file under `hooks/` and `info/` plus `config.worktree` when present. `compare` reports each added, changed or removed entry as `{"kind": "gitdir", "path": <relative path>, "before": ..., "after": ...}`. Add a module constant `GITDIR_UNCHECKED` naming the top-level git-dir entries the snapshot deliberately skips (`objects`, `logs`, `refs`, `index`, `HEAD`, `config`, `packed-refs`, `FETCH_HEAD`, `ORIG_HEAD`, `COMMIT_EDITMSG`, `description`, `branches`, `worktrees`, `modules`, and any others a fresh `git init` plus one commit creates). Bump `VERSION` to 2.

## Requirements

### Must have
- Writing, changing or removing a file under `.git/hooks/` or `.git/info/`, or `config.worktree`, makes `compare` exit 1 with kind `gitdir` and the path.
- `test_every_gitdir_entry_is_checked_or_listed` builds a repo with `git init` plus one commit and asserts every top-level `.git` entry is either `hooks`, `info`, `config.worktree` or in `GITDIR_UNCHECKED`, so a new git file forces a decision.
- `VERSION` is 2; a version-1 snapshot file exits 2 with one line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects changed git hooks and .git/info files`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: snapshot and compare the `gitdir` key.
- **Exports**: `GITDIR_UNCHECKED`, `VERSION` (now 2)
- New symbols: `GITDIR_UNCHECKED`, `gitdir`, `test_new_hook_is_gitdir_violation`, `test_changed_info_exclude_is_gitdir_violation`, `test_changed_info_attributes_is_gitdir_violation`, `test_every_gitdir_entry_is_checked_or_listed`
- **Risk**: `GITDIR_UNCHECKED` needs upkeep as git adds files. The version bump makes older snapshot files exit 2, which is the contract.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression tests: snapshot, write `hooks/pre-commit`, compare -> exit 1 kind `gitdir`; same for `info/exclude` and `info/attributes`. Reproduction from the run:

```
printf "#!/bin/sh\necho pwned\n" > hk/.git/hooks/pre-commit; chmod +x ...
compare hk -> rc=0 unchanged [] touched= []
.git/info/exclude (+lane-junk/, then new file lane-junk/x) -> rc=0 unchanged
.git/info/attributes (* filter=evil) -> rc=0 unchanged
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_new_hook_is_gitdir_violation`, `test_changed_info_exclude_is_gitdir_violation`, `test_changed_info_attributes_is_gitdir_violation` - Acceptance: `pytest -k gitdir_violation` fails on the unmodified script.
- [ ] Add the `gitdir` snapshot key, its compare, `GITDIR_UNCHECKED` and `test_every_gitdir_entry_is_checked_or_listed`; bump `VERSION` to 2 (depends on: previous task) - Acceptance: `pytest -k "gitdir"` passes.
- [ ] Repoint the two existing version tests (depends on: previous task). Premise: `rg -c '"version"' skills/run-agoge/scripts/test_target_snapshot.py` reports 2, in `test_untouched_target_compares_unchanged` (asserts `== 1`) and `test_unusable_inputs_exit_2_with_prefixed_stderr` (writes `version: 2` as the wrong version); on any other count, stop and report. - Acceptance: the first asserts `== VERSION`, the second writes `VERSION + 1`; `pytest -k "untouched_target or unusable_inputs"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "detects changed git hooks" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "gitdir or untouched_target or unusable_inputs"` passes; the full suite passes under `dev/bin/release-checks`.
