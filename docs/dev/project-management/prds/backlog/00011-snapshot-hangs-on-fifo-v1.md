# Snapshot hangs forever when a tracked file has been replaced by a FIFO

Source: agoge run 2026-11-08, finding 5 of 18 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`_fingerprint` in `target_snapshot.py` opens each dirty path with `open(full, "rb")`. When a named pipe replaces a tracked file, the open blocks forever. The master's integrity gate stalls with no exit code instead of exiting 2, and an unattended loop hangs.

## Solution

`lstat` the path first. If it is not a regular file (`stat.S_ISREG`) and not a symlink (already handled), fingerprint it as `special:<octal mode>` without opening it.

## Requirements

### Must have
- A snapshot of a repo with a FIFO in place of a tracked file finishes within a few seconds and records `special:<mode>`.
- A compare after the FIFO is replaced by a regular file reports the path as `tracked`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer hangs on a named pipe in the work tree`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: none expected; regular-file fingerprints are unchanged.

## Test Strategy

Regression test: `os.mkfifo` in place of a tracked file, run `snapshot` in a subprocess with a timeout (for example 10s), assert exit 0. Reproduction from the run:

```
mkfifo r2/f.txt (in place of tracked f.txt), snapshot with 15 s timeout -> TIMEOUT after 15s
git status alone -> 0.01 s, "M f.txt"
```

## Tasks

- [ ] Add the FIFO test; watch it time out.
- [ ] Add the `S_ISREG` check.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- FIFO test passes; the full suite passes under `dev/bin/release-checks`.
