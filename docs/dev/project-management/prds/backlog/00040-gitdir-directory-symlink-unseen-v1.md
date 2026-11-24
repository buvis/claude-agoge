---
design: skip
default_model: sonnet
model_tier_rationale: one loop change with its exact expression and one test that fails on the old code
---
# The integrity check does not see a directory symlink in the git dir

Source: codex supplement to review 1 of PRD 00025 (`docs/dev/project-management/reviews/00025-gitdir-walk-hangs-on-fifo-v1-codex-supplement.md`), second finding, confirmed by a probe on 2026-11-24. The defect is older than PRD 00025.

## Problem

`_gitdir_files` in `skills/run-agoge/scripts/target_snapshot.py` walks the git dir with `os.walk` and records only the entries in the walk's file list. `os.walk` puts a symlink to a directory in its directory list and does not follow it, so the link is never recorded. A lane that adds such a link, removes it, or points it at another directory leaves `compare` at `unchanged`, exit 0. Measured 2026-11-24: `.git/linked-hooks` pointed at one directory, `snapshot`, the link pointed at a second directory, `compare`: exit 0, no violation. A repo whose `.git/hooks` is a symlink is the real case: a lane can point it at other hooks and the check does not report it.

Users hit: an operator who trusts `unchanged` after a run on a repo with a symlinked directory in its git dir.

## Solution

Record a directory symlink the same way PRD 00025 records a file symlink: its fingerprint is `link:` plus the sha256 of the link's target path, from `_fingerprint`. The walk still does not follow the link, so files behind it are not read; a change to those files with the link unchanged stays unseen, which is the risk PRD 00025 accepted for file symlinks.

## Requirements

### Must have
- A directory symlink in the git dir that is added, removed or pointed at another directory gives a `gitdir` violation and exit 1.
- The files behind the link are not read.
- An entry whose top component is in `GITDIR_UNCHECKED` stays unchecked.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot reports a directory symlink in the git dir that is added, removed or retargeted`.

### Nice to have
- None.

## Implementation

### Module: git-dir walk
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `CHANGELOG.md`
- **Responsibility**: record every entry of the git dir that can change what git does, without following links.
- **Exports**: none
- New symbols: `test_retargeted_directory_symlink_in_git_dir_is_reported`
- **Risk**: a `before.json` written by the old script has no entry for such a link, so a compare by the new script reports the link as added. Snapshots live for one run, so the two versions do not meet; `VERSION` does not change.

### Dependencies
- git-dir walk: No dependencies (foundation)

## Tasks

### Phase 0: Fix
- [ ] Add `test_retargeted_directory_symlink_in_git_dir_is_reported` in `skills/run-agoge/scripts/test_target_snapshot_state.py`: two directories outside the target, each with a file `pre-commit`; `.git/linked-hooks` is a symlink to the first; `_snap`; replace the link with a symlink to the second; `_compare` exits 1 and reports one `gitdir` violation with path `linked-hooks` whose `before` and `after` both start with `link:` and differ - Acceptance: `pytest -k retargeted_directory_symlink_in_git_dir` fails on the unmodified script.
- [ ] In `_gitdir_files`, bind the walk's directory list to the name `dirs` and loop over the file list plus every entry of `dirs` for which `os.path.islink(os.path.join(root, name))` is true; keep the `GITDIR_UNCHECKED` skip and the `_fingerprint(git_dir, rel)` call as they are, so a directory symlink is recorded as `link:` plus the sha256 of its target path and is not followed (depends on: previous task) - Acceptance: `pytest -k retargeted_directory_symlink_in_git_dir` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "reports a directory symlink in the git dir" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k retargeted_directory_symlink_in_git_dir` passes; the full suite passes under `dev/bin/release-checks`.
