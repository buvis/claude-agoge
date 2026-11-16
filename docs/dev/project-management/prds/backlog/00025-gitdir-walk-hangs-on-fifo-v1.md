---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: one function, behaviour per file type listed, each case has a quoted reproduction
---
# A fifo or odd file under `.git` hangs the snapshot, a large one fills memory, and a symlink is followed out of the repo

Source: agoge run 2026-11-15, findings 2, 4 and 8 of 14 (MEDIUM, MEDIUM, LOW; verified; lanes trudy and peggy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted as one cluster, approved by the operator, option 2 (root fix) for each.

## Problem

`_gitdir_files` in `target_snapshot.py` reads every file under the git dir's checked entries (hooks, info and similar) with `open(path, "rb")` and one `handle.read()`. Three symptoms come from that one line:

- **Hang (finding 2).** A fifo, a symlink to a fifo, or a symlink to `/dev/zero` blocks or reads without bound. A hostile or odd repo stalls the whole agoge run before any lane starts, or eats memory.
- **Memory (finding 4).** A large file is read whole. A 1 GiB hook needs 1.1 GB of RAM. Same at c7da90f, so not a regression.
- **Symlinks and errors (finding 8).** A symlink to a file outside the repo is followed and the outside file's hash enters the snapshot. A mode-000 file exits 2 with `unexpected PermissionError`, which names no file.

Users hit: anyone who runs agoge at a repo they did not build themselves, or one with a large or unreadable file in `.git`. Unlikely on the operator's own repos; stable.

## Solution

`_fingerprint(repo, path)` already does the right thing for work-tree paths: one `lstat`, `link:<sha of readlink>` for symlinks, `special:<mode>` for non-regular files, and a 1 MiB chunked hash for regular files. Use it for the git dir: `files[rel] = _fingerprint(git_dir, rel)`. Wrap the call so an `OSError` raises `Fail(f"cannot read {rel} in the git dir: {exc.strerror}")`.

`os.walk` lists a symlink to a directory under directories, not files, so it stays unrecorded as today. That gap is out of scope here.

## Requirements

### Must have
- `snapshot` and `compare` finish on a repo with a fifo at `.git/hooks/ff`, a symlink to a fifo at `.git/info/lf`, and a symlink to `/dev/zero` at `.git/hooks/z`. Each exits 0 within 10 s.
- The `gitdir` entry for a fifo starts with `special:`; for a symlink it is `link:` plus the sha256 of the link target path, never the hash of the target's content.
- Replacing a regular hook with a fifo, or repointing a symlink, between snapshot and compare gives a `gitdir` violation for that path.
- A regular file's `gitdir` value is byte-identical to today's (sha256 of its content).
- A 64 MiB hook keeps the snapshot child's peak RSS under 48 MiB.
- A mode-000 file under `.git/info` exits 2 with one line that names the file and does not contain `unexpected`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer hangs on a fifo or device symlink in the git dir, reads large git-dir files in chunks, records a symlink there by its target path instead of following it, and names an unreadable file in its error`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `CHANGELOG.md`
- **Responsibility**: fingerprint git-dir files without opening anything that is not a regular file, in constant memory.
- **Exports**: none new
- New symbols: `test_fifo_in_git_dir_does_not_hang_snapshot`, `test_git_dir_symlink_recorded_by_target_not_content`, `test_changed_git_dir_special_file_is_reported`, `test_large_git_dir_file_peak_rss_under_48_mib`, `test_unreadable_git_dir_file_names_the_file`
- **Risk**: a symlinked hook is no longer content-hashed, so an edit to the file a hook symlink points at goes unseen (a repointed link is still seen). A `before.json` written by the old code for a repo with a symlinked git-dir file compares as changed once; snapshots live in scratch for one run, so `VERSION` stays 4.

### Dependencies
- target_snapshot: No dependencies (foundation). PRD 00024 and 00026 edit `_fingerprint`; this PRD only calls it.

## Test Strategy

Run each hang case through `_run(..., timeout=10)` so a regression fails as a timeout, not a stuck suite. Measure RSS as `test_large_dirty_file_snapshot_peak_rss_under_48_mib` does (fresh wrapper process, `RUSAGE_CHILDREN`). Skip the mode-000 test when `os.geteuid() == 0`.

Reproduction from the run, finding 2:

```
timeout 30 python3 -I target_snapshot.py snapshot <repo> out.json:
.git/hooks/ff fifo gave exit 124 at 30.0 s;
.git/info/lf symlink to a fifo gave 124;
.git/hooks/z symlink to /dev/zero gave 124 and reads without bound.
```

Finding 4:

```
256 MB hook: peak RSS 298.9 MB. 1 GiB hook: 1,104,199,680 B RSS. Times 0.3-0.6 s.
```

Finding 8:

```
.git/hooks/o as a symlink to a planted outside file: exit 0, and the outside file's hash entered gitdir.
.git/info/u at mode 000: exit 2, unexpected PermissionError.
```

## Tasks

### Phase 0: Fix
- [ ] Add the five tests named above - Acceptance: `pytest -k "git_dir and (fifo or symlink or special or peak_rss or unreadable)"` fails on the unmodified script (the fifo test by timeout).
- [ ] Route `_gitdir_files` through `_fingerprint` and map `OSError` to `Fail` (depends on: previous task) - Acceptance: the same `pytest -k` selection passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer hangs on a fifo or device symlink in the git dir" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- The five new tests pass; the full suite passes under `dev/bin/release-checks`.
