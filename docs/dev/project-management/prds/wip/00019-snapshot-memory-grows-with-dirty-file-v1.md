---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact loop and threshold given; equivalence pinned by a hash test
---
# Snapshot peak memory grows with the largest dirty file because it is read whole

Source: agoge run 2026-11-08, finding 13 of 18 (LOW, verified, lane peggy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`_fingerprint` in `target_snapshot.py` hashes each dirty file with one `handle.read()`. Peak memory is about 25MB plus the largest dirty file, so a target with a large dirty data file makes each of the run's three snapshot and compare calls hold it all in memory. No budget is stated; no failure was seen.

## Solution

In `_fingerprint`, hash in 1 MiB chunks: `digest = hashlib.sha256()`, `for chunk in iter(lambda: handle.read(1 << 20), b""): digest.update(chunk)`, return `digest.hexdigest()`. This keeps Python 3.10 support (`hashlib.file_digest` needs 3.11).

## Requirements

### Must have
- Fingerprints are byte-identical to today's for the same content.
- Snapshotting a repo whose one dirty tracked file was committed small and overwritten with 64 MiB keeps the snapshot child's peak RSS under 48 MiB.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot hashes dirty files in chunks instead of loading them whole`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: hash dirty files in constant memory.
- **Exports**: none new
- New symbols: `test_large_dirty_file_snapshot_peak_rss_under_48_mib`, `test_fingerprint_matches_whole_file_sha256`
- **Risk**: none expected; same digest, same output.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Measure in a fresh wrapper process so earlier test children do not pollute the maximum: run `[sys.executable, "-c", WRAPPER]` where the wrapper runs `target_snapshot.py snapshot` via `subprocess.run` and prints `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss`. Convert to bytes (`ru_maxrss` is bytes on macOS, KiB on Linux) and assert it is under 48 MiB. Reproduction from the run:

```
10 x 10MB dirty: peak RSS 36MB, 104,924,742 bytes hashed
10 x 50MB dirty: peak RSS 78MB, 524,355,142 bytes hashed
1 x 256MB dirty: peak RSS 294MB
1 x 1GB dirty: peak RSS 1099MB, 0.55s (reproduced 3 times for snapshot and 3 for compare)
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_large_dirty_file_snapshot_peak_rss_under_48_mib` and `test_fingerprint_matches_whole_file_sha256` - Acceptance: `pytest -k peak_rss` fails on the unmodified script.
- [ ] Switch `_fingerprint` to the chunked loop (depends on: previous task) - Acceptance: `pytest -k "peak_rss or fingerprint_matches"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "hashes dirty files in chunks" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "peak_rss or fingerprint_matches"` passes; the full suite passes under `dev/bin/release-checks`.
