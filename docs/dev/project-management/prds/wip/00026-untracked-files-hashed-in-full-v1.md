---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: fingerprint format and cap given; the weakened guarantee is stated, not left to the implementer
---
# Untracked files are hashed in full, so snapshot cost grows with file bytes

Source: agoge run 2026-11-15, finding 3 of 14 (MEDIUM, verified, lanes peggy and trudy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 2 (hash first and last MiB plus size above a cap).

## Problem

`_fingerprint` in `target_snapshot.py` hashes every byte of every untracked or dirty regular file. Cost is about 1.1-1.2 s per GiB for zeros, and real data adds disk IO. A multi-GB untracked file (dataset, VM image) costs minutes over the three snapshots of one agoge run. Memory stays at 30 MB, and ignored files are never read.

Users hit: anyone who runs agoge at a repo holding a large untracked or dirty file.

## Solution

Add a module constant `SAMPLE_ABOVE = 64 * 1024 * 1024`. The value is a guess: no budget exists, and 64 MiB hashes in well under 0.1 s. In `_fingerprint`, for a regular file whose `st_size` is above `SAMPLE_ABOVE`, read the first MiB and the last MiB and return `sample:<st_size>:<sha256 of first + last>`. At or below the cap, hash the whole file as today.

State the limit in the module docstring: above 64 MiB a file is fingerprinted by its size and its first and last MiB, so an edit in the middle that keeps the size is not detected.

## Requirements

### Must have
- A regular file at or below `SAMPLE_ABOVE` keeps today's fingerprint (sha256 hex of the whole content).
- A file above `SAMPLE_ABOVE` gets `sample:<size>:<hex>` and at most 2 MiB of it is read.
- For a file above the cap, `compare` reports `untracked-modified` when its first byte changes, when its last byte changes, and when its size changes.
- The module docstring states the cap and what goes undetected.
- `CHANGELOG.md` `[Unreleased]` `### Changed`: `- **run-agoge**: target snapshot fingerprints a file above 64 MiB by its size and its first and last MiB, so cost no longer grows with file bytes; an edit in the middle of such a file that keeps its size is not detected`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `CHANGELOG.md`
- **Responsibility**: bound the bytes read per file.
- **Exports**: `SAMPLE_ABOVE`
- New symbols: `SAMPLE_ABOVE`, `test_file_at_cap_is_hashed_whole`, `test_file_above_cap_is_sampled`, `test_sampled_file_head_tail_and_size_edits_are_reported`
- **Risk**: any sampling weakens the "never changed the target" guarantee. A lane that rewrites the middle of a file above 64 MiB and keeps its size passes integrity as unchanged. The same fingerprint serves dirty tracked files, so the limit applies there too, and to git-dir files once PRD 00025 routes them through `_fingerprint`. `_big_file_target` in `test_target_snapshot_state.py` builds a 200 MiB file; above the cap that file is sampled, so the two peak-RSS tests of PRD 00019 would stop exercising the chunked whole-file hash unless the fixture shrinks to the cap.

### Dependencies
- target_snapshot: PRD 00024 edits the same function; land that one first.

## Test Strategy

Build files with `os.truncate` so they are sparse and cost no disk. Case 1: a file of exactly `SAMPLE_ABOVE` bytes fingerprints as the sha256 of that many zero bytes. Case 2: a file of `SAMPLE_ABOVE + 1` bytes fingerprints with the `sample:` prefix and its size. Case 3: snapshot, write one byte at offset 0, compare, expect `untracked-modified`; repeat for the last byte, and for a one-byte append.

Reproduction from the run:

```
Sparse untracked file: 1 GiB snapshot 2.26 s (c7da90f 0.72 s); 4 GiB 5.00 s (0.79 s);
a 50 GiB sparse file took 22.4 s (trudy).
About 1.1-1.2 s per GiB for zeros; real data adds disk IO.
Memory stays 30 MB. Ignored files are never read.
```

Expected effect, not a requirement and not checked by the loop: a 4 GiB sparse untracked file snapshots in under 1.5 s on the same machine (was 5.00 s). The suite pins the read bound through the fingerprint format, not through timing.

## Tasks

### Phase 0: Fix
- [ ] Add `test_file_at_cap_is_hashed_whole` (an untracked sparse file of exactly `SAMPLE_ABOVE` bytes, the constant read from the `target_snapshot` module, built with `os.truncate`, fingerprints as the sha256 hex of that many zero bytes), `test_file_above_cap_is_sampled` (a file of `SAMPLE_ABOVE + 1` bytes fingerprints as `sample:<st_size>:<sha256 hex of its first MiB followed by its last MiB>`) and `test_sampled_file_head_tail_and_size_edits_are_reported` (for a file above the cap, `compare` reports `untracked-modified` after a change to its first byte, to its last byte, and after a one-byte append). In `skills/run-agoge/scripts/test_target_snapshot_state.py`, change the size in `_big_file_target` from `200 * 1024 * 1024` to that module's `SAMPLE_ABOVE`, so the two peak-RSS tests keep hashing a whole file; premise: `rg -n "200 \* 1024 \* 1024" skills/run-agoge/scripts/test_target_snapshot_state.py` hits exactly once, else skip that edit and report - Acceptance: `pytest -k "at_cap or above_cap or sampled_file"` fails on the unmodified script, which has no `SAMPLE_ABOVE`.
- [ ] Add the module constant `SAMPLE_ABOVE = 64 * 1024 * 1024` and the sampled branch in `_fingerprint` for a regular file whose `st_size` is above it (read the first MiB and the last MiB only); state in the module docstring that above 64 MiB a file is fingerprinted by its size and its first and last MiB, so a same-size edit in the middle is not detected (depends on: previous task) - Acceptance: `pytest -k "at_cap or above_cap or sampled_file"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "its first and last MiB" CHANGELOG.md` hits under `[Unreleased]` `### Changed`.

## Success Criteria

- The three new tests pass; the full suite passes under `dev/bin/release-checks`.
