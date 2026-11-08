# Snapshot peak memory grows with the largest dirty file because it is read whole

Source: agoge run 2026-11-08, finding 13 of 18 (LOW, verified, lane peggy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`_fingerprint` in `target_snapshot.py` hashes each dirty file with one `handle.read()`. Peak memory is about 25MB plus the largest dirty file, so a target with a large dirty data file makes each of the run's three snapshot and compare calls hold it all in memory. No budget is stated; no failure was seen.

## Solution

Hash with `hashlib.file_digest(handle, "sha256")` (Python 3.11+; CI runs 3.12, local 3.15).

## Requirements

### Must have
- Fingerprints are byte-identical to today's for the same content.
- Snapshotting a repo with one 64MB dirty file keeps child peak RSS well under 64MB above baseline.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot hashes dirty files in chunks instead of loading them whole`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: drops Python 3.10 support for the script.

## Test Strategy

Regression test: one 64MB dirty file, run `snapshot` in a subprocess, read `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss`, assert it stays well under 64MB (mind macOS bytes versus Linux KB units). Reproduction from the run:

```
10 x 10MB dirty: peak RSS 36MB, 104,924,742 bytes hashed
10 x 50MB dirty: peak RSS 78MB, 524,355,142 bytes hashed
1 x 256MB dirty: peak RSS 294MB
1 x 1GB dirty: peak RSS 1099MB, 0.55s (reproduced 3 times for snapshot and 3 for compare)
```

## Tasks

- [ ] Add the memory test; watch it fail.
- [ ] Switch to `hashlib.file_digest`.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes; the full suite passes under `dev/bin/release-checks`.
