---
design: skip
default_model: sonnet
model_tier_rationale: one exception branch with exact message text and one test
---
# An unreadable untracked file exits 2 with `unexpected PermissionError`

Source: agoge run 2026-11-16, finding 9 of 11 (LOW, mocked, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-16.md`. Decision: accepted, option 1. The git-dir case is PRD 00025; this PRD covers work-tree files only.

## Problem

A mode-000 untracked file makes `snapshot` and `compare` exit 2 with `unexpected PermissionError: "[Errno 13] ..."`. The docstring calls this case expected, so "unexpected" misleads. The exit code and one-line shape are right.

Users hit: an operator whose repo holds an unreadable untracked file.

## Solution

In `_fingerprint`, catch `PermissionError` and raise `Fail(f"cannot read {path}: permission denied")`. The result is one stderr line `target_snapshot: cannot read <path>: permission denied`, exit 2, no JSON. `<path>` is the repo-relative path.

Once PRD 00025 has landed, `_gitdir_files` also calls `_fingerprint`, so a mode-000 git-dir file gets this message too (with its git-dir-relative path) in place of 00025's `in the git dir` wording. That is accepted. `test_unreadable_git_dir_file_names_the_file` asserts only the file name and the absence of `unexpected`, so it still passes; do not edit it.

## Requirements

### Must have
- A mode-000 untracked file gives exit 2 and stderr exactly one line of that form, at snapshot and at compare.
- The line does not contain `unexpected`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot names an unreadable untracked file without calling the error unexpected`.

### Nice to have
- None.

## Implementation

### Module: snapshot errors
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `CHANGELOG.md`
- **Responsibility**: report an unreadable untracked file in the documented form.
- **Exports**: none
- New symbols: `test_unreadable_untracked_file_error_is_not_called_unexpected`
- **Risk**: none expected. The test skips when `os.geteuid() == 0` (root reads mode 000). Mocked: mode 000 stands in for a file owned by another user.

### Dependencies
- snapshot errors: No dependencies (foundation)

## Test Strategy

```
Mode 000 u.txt: rc=2
target_snapshot: unexpected PermissionError: "[Errno 13] Permission denied: '/private/var/.../e1/u.txt'"
Same at compare time.
```

Status is mocked: a file owned by another user cannot be created without root.

## Tasks

### Phase 0: Fix
- [ ] Add `test_unreadable_untracked_file_error_is_not_called_unexpected` in `skills/run-agoge/scripts/test_target_snapshot_state.py` (a mode-000 untracked `u.txt`: `snapshot`, and `compare` against a snapshot taken before the `chmod`, each exit 2 with exactly one stderr line `target_snapshot: cannot read u.txt: permission denied`; skip when `os.geteuid() == 0`; restore the mode in `finally`) - Acceptance: `pytest -k unreadable_untracked` fails on the unmodified script.
- [ ] In `_fingerprint`, catch `PermissionError` and raise `Fail(f"cannot read {path}: permission denied")`, where `path` is the repo-relative path (depends on: previous task) - Acceptance: `pytest -k unreadable_untracked` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "names an unreadable untracked file" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k unreadable_untracked` passes; the full suite passes under `dev/bin/release-checks`.
