---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact expression given; timeout test fails loudly
---
# Snapshot hangs forever when a tracked file has been replaced by a FIFO

Source: agoge run 2026-11-08, finding 5 of 18 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`_fingerprint` in `target_snapshot.py` opens each dirty path with `open(full, "rb")`. When a named pipe replaces a tracked file, the open blocks forever. The master's integrity gate stalls with no exit code instead of exiting 2, and an unattended loop hangs.

## Solution

In `_fingerprint`, after the existing symlink, absent and directory branches, `os.lstat` the path. If `not stat.S_ISREG(st.st_mode)`, return `f"special:{stat.S_IFMT(st.st_mode):o}"` (a FIFO gives `special:10000`) without opening it.

## Requirements

### Must have
- A snapshot of a repo with a FIFO in place of a tracked file exits 0 within a 10-second subprocess timeout and records `special:10000` for the path.
- A compare after the FIFO is replaced by a regular file reports the path as `tracked`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer hangs on a named pipe in the work tree`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: fingerprint non-regular files without opening them.
- **Exports**: none new
- New symbols: `test_fifo_in_place_of_tracked_file_does_not_hang`, `test_fifo_replaced_by_file_is_tracked_violation`
- **Risk**: none expected; regular-file fingerprints are unchanged.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression test: `os.mkfifo` in place of a tracked file, run `snapshot` in a subprocess with `timeout=10`, assert exit 0. Reproduction from the run:

```
mkfifo r2/f.txt (in place of tracked f.txt), snapshot with 15 s timeout -> TIMEOUT after 15s
git status alone -> 0.01 s, "M f.txt"
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_fifo_in_place_of_tracked_file_does_not_hang` and `test_fifo_replaced_by_file_is_tracked_violation` - Acceptance: `pytest -k fifo` fails on the unmodified script (subprocess timeout).
- [ ] Add the `S_ISREG` check (depends on: previous task) - Acceptance: `pytest -k fifo` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer hangs on a named pipe" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k fifo` passes; the full suite passes under `dev/bin/release-checks`.
