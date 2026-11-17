---
design: skip
default_model: opus
model_tier_rationale: a cap changes the snapshot file contract and the compare logic across two functions
---
# Listing ignored files grows the snapshot file and memory with the ignored tree

Source: agoge run 2026-11-16, finding 10 of 11 (LOW, verified, lane peggy), `docs/dev/project-management/audit-results/agoge-2026-11-16.md`. Decision: accepted. The packet recommended accepting the cost; the human chose a cap (option 2). No budget is stated, so the numbers are observation-only.

## Problem

`take_snapshot` stores the name of every ignored file in `before.json`. A repo with 100k ignored files (`node_modules`) gives a 4.04 MB snapshot file (old 0 MB), 0.31s snapshot time (old 0.12s) and 68 MiB compare peak memory. Cost is linear in the ignored tree.

Users hit: anyone running agoge on a repo with a large ignored tree.

## Solution

Keep recording every ignored entry when there are at most 20000 file entries. Above that, record only directory entries (names ending in `/`, from the `--directory` listing) plus the integer `ignored_overflow` equal to the count of file entries seen. `compare` then reports `ignored-removed` for a missing directory entry only, and does not check files inside an overflowed tree. The docstring states the cap and the loss. Bump snapshot `VERSION` from 4 to 5; older files exit 2 as today.

## Requirements

### Must have
- A repo with 20001 or more ignored files writes no file names, only directory entries and `ignored_overflow`, and its `before.json` is under 1 MB.
- A repo at or under 20000 ignored files behaves as now (every file named).
- Removing an ignored directory under overflow gives `ignored-removed` for the directory entry.
- A v4 `before.json` exits 2 with `is not version 5`.
- `CHANGELOG.md` `[Unreleased]` `### Changed`: `- **run-agoge**: target snapshot stops listing individual ignored files above 20000 and checks only ignored directories there`.

### Nice to have
- None.

## Implementation

### Module: snapshot ignored listing
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `CHANGELOG.md`
- **Responsibility**: bound the ignored listing and say what is not checked.
- **Exports**: none
- New symbols: `test_ignored_listing_over_cap_records_directories_only`, `test_ignored_listing_at_cap_records_every_file`, `test_v4_snapshot_refused_after_ignored_cap`, `IGNORED_FILE_CAP`
- **Risk**: above the cap a removed single ignored file goes unseen (the ignored-removed check weakens). Existing tests that assert `VERSION` 4 must change to 5.

### Dependencies
- snapshot ignored listing: No dependencies (foundation)

## Test Strategy

Patch `IGNORED_FILE_CAP` to a small number in tests; do not create 20000 files.

```
100k ignored files: snapshot 0.31s (old 0.12s), before.json 4.04 MB (old 0.00 MB), compare peak RSS 68 MiB
50k ignored files: 0.23s, 1.99 MB, 45 MiB
2 GiB sparse ignored file: never read, 0.19s, 0.00 MB
```

## Tasks

### Phase 0: Fix
- [ ] Add the three tests; watch them fail - Acceptance: `pytest -k "ignored_listing or ignored_cap"` fails on the unmodified script.
- [ ] Add `IGNORED_FILE_CAP`, the overflow record, the compare rule, the `VERSION` bump, the docstring and the CHANGELOG line (depends on: previous task) - Acceptance: `pytest -k "ignored_listing or ignored_cap"` passes.

## Success Criteria

- `pytest -k "ignored_listing or ignored_cap"` passes; the project's full test gate passes.
