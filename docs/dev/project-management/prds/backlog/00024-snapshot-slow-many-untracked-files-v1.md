---
lane: fast-track
design: skip
default_model: opus
model_tier_rationale: equivalence obligation on a rewritten function plus a new cache; pinned by a fingerprint test and a syscall count
---
# Snapshot and compare cost grows linearly with untracked files, 25x-40x slower than c7da90f

Source: agoge run 2026-11-15, finding 1 of 14 (HIGH, verified, lane peggy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 1 (patch).

## Problem

Every untracked file is opened, hashed and stat'ed several times. `_fingerprint` in `target_snapshot.py` calls `_external_symlink_ancestor`, which runs `os.path.islink` on each directory component of each path, then `os.path.islink(full)`, then `os.lstat(full)`: four `lstat` calls per file at depth two. Each agoge run takes at least three snapshots, so a target with a big untracked tree (build output outside `.gitignore`, vendored data) adds tens of seconds per run. The cost is stable per run and grows with the target. No budget is stated anywhere, so "slow" is a judgement.

Users hit: anyone who runs agoge at a repo with many untracked files.

## Solution

1. Memoise the symlink-ancestor answer per directory: move the walk into a helper keyed on `(repo, directory)` under `functools.lru_cache(maxsize=None)`, so each directory is walked once per process. One process takes one snapshot, so the cache never outlives the tree state it read.
2. In `_fingerprint`, call `os.lstat(full)` once and branch on `stat.S_ISLNK`, `S_ISDIR`, `S_ISREG` from that one result. Drop the separate `os.path.islink(full)`.

File contents are still hashed in full. The byte cost is PRD 00026.

## Requirements

### Must have
- Every fingerprint is byte-identical to today's for the same tree: regular file, symlink, directory, special file, absent path, and a path under a symlink that leaves the repo (`external-symlink`).
- Fingerprinting N untracked files in D directories makes at most `N + 2 * D + 10` `os.lstat` calls.
- `CHANGELOG.md` `[Unreleased]` `### Changed`: `- **run-agoge**: target snapshot stats each untracked file once and checks each directory for an escaping symlink once, so cost no longer multiplies with path depth`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: fingerprint an untracked path with one `lstat` and a per-directory symlink check.
- **Exports**: none new
- New symbols: `test_fingerprinting_many_files_stats_each_file_once`, `test_fingerprints_unchanged_by_symlink_cache`
- **Risk**: symlink-escape detection if the cache goes stale (the report marks this a guess). The cache lives for one process and one snapshot, and a lane that swaps a directory for a symlink mid-snapshot was a race before this change too.

### Dependencies
- target_snapshot: No dependencies (foundation). PRD 00026 edits the same function; land this one first.

## Test Strategy

In-process: import `target_snapshot`, build 200 untracked files across 4 directories two levels deep, wrap `os.lstat` with a counter through `monkeypatch` (`os.path.islink` calls `os.lstat`, so the counter sees both), fingerprint every file, assert the count is at most `200 + 2 * 4 + 10`. On the unmodified script the count is about 800. Each test builds its own `tmp_path` repo, so the per-`(repo, directory)` cache starts cold and the test needs no handle on the cache.

Equivalence: one tree with a regular file, a symlink, a fifo, a directory, and a file under a directory symlink that points outside the repo. Assert each fingerprint equals the literal value today's code gives (`sha256` hex, `link:<sha>`, `special:10000`, `dir`, `external-symlink`).

Reproduction from the run:

```
100k untracked files: snapshot 4.0-9.1 s, compare 3.6-7.8 s, against 0.24-0.30 s at c7da90f.
10k files: 0.45 s against 0.12-0.16 s.
before.json 13.2 MB against 3.2 MB.
cProfile of the 100k snapshot: _fingerprint 9.74 of 10.9 s, with 400k lstat calls
(four per file, from a per-path-component symlink walk). The 15 git calls total 0.73 s.
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_fingerprinting_many_files_stats_each_file_once` (in-process, in a fresh `tmp_path` repo: 200 untracked files across 4 directories two levels deep, a `monkeypatch` counter around `os.lstat`, `target_snapshot._fingerprint(repo, path)` called for every file, at most `200 + 2 * 4 + 10` calls counted) and `test_fingerprints_unchanged_by_symlink_cache` (a regular file gives its sha256 hex, a symlink `link:<sha256 of the readlink bytes>`, a fifo `special:10000`, a directory `dir`, a missing path `absent`, and a file under a directory symlink that points outside the repo `external-symlink`) - Acceptance: `pytest -k stats_each_file_once` fails on the unmodified script; `pytest -k unchanged_by_symlink_cache` passes on it.
- [ ] Memoise the ancestor walk per `(repo, directory)` under `functools.lru_cache(maxsize=None)` and take the fingerprint from one `os.lstat(full)`, branching on `stat.S_ISLNK`, `S_ISDIR` and `S_ISREG` with no separate `os.path.islink(full)` (depends on: previous task) - Acceptance: `pytest -k "stats_each_file_once or unchanged_by_symlink_cache"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "stats each untracked file once" CHANGELOG.md` hits under `[Unreleased]` `### Changed`.

## Success Criteria

- `pytest -k "stats_each_file_once or unchanged_by_symlink_cache"` passes; the full suite passes under `dev/bin/release-checks`.
