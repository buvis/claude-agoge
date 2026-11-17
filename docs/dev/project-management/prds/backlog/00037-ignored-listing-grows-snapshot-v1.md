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

Add a module constant `IGNORED_FILE_CAP = 20000`. Keep recording every ignored entry when there are at most that many file entries (the entries of the listing without `--directory`). Above that, record only directory entries (names ending in `/`, from the `--directory` listing) plus the integer `ignored_overflow` equal to the count of file entries seen. The key `ignored_overflow` is written only above the cap, so a snapshot under the cap keeps today's key set (`test_ignored_contents_are_never_read` pins it). `compare` then reports `ignored-removed` for a missing directory entry only, and does not check files inside an overflowed tree: when either snapshot carries `ignored_overflow`, only the before entries ending in `/` are checked. Without that rule, a tree that crosses the cap between snapshot and compare reports every file named before as removed. The docstring states the cap and the loss. Bump snapshot `VERSION` from 4 to 5; older files exit 2 as today.

If `_load` type-checks top-level keys by then (PRD 00029: `rg -n "is malformed" skills/run-agoge/scripts/target_snapshot.py` hits), it accepts a missing `ignored_overflow` and requires `type(...) is int` when the key is present.

## Requirements

### Must have
- A repo with 20001 or more ignored files writes no file names, only directory entries and `ignored_overflow`. Expected effect, not asserted: `before.json` for 100k ignored files drops from 4 MB to under 1 MB.
- A repo at or under 20000 ignored files behaves as now (every file named, no `ignored_overflow` key).
- Removing an ignored directory under overflow gives `ignored-removed` for the directory entry.
- A tree that crosses the cap between snapshot and compare, in either direction, reports no `ignored-removed` for a file entry.
- A v4 `before.json` exits 2 with `is not version 5`.
- `CHANGELOG.md` `[Unreleased]` `### Changed`: `- **run-agoge**: target snapshot stops listing individual ignored files above 20000 and checks only ignored directories there`.

### Nice to have
- None.

## Implementation

### Module: snapshot ignored listing
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: bound the ignored listing and say what is not checked.
- **Exports**: none
- New symbols: `test_ignored_listing_over_cap_records_directories_only`, `test_ignored_listing_at_cap_records_every_file`, `test_ignored_listing_crossing_cap_reports_no_file_removals`, `test_v4_snapshot_refused_after_ignored_cap`, `IGNORED_FILE_CAP`, `ignored_overflow`
- **Risk**: above the cap a removed single ignored file goes unseen (the ignored-removed check weakens). The one literal version assertion, `assert target_snapshot.VERSION == 4` in `test_previous_version_snapshot_exits_2_with_one_line` (`test_target_snapshot.py`), must change to 5.

### Dependencies
- snapshot ignored listing: No dependencies (foundation)

## Test Strategy

Patch `IGNORED_FILE_CAP` to a small number in tests; do not create 20000 files. The other snapshot tests spawn the script, which a patch cannot reach, so these tests call `target_snapshot.take_snapshot` and `target_snapshot.compare` in-process, with the fixture's git environment applied through `monkeypatch.setenv`.

```
100k ignored files: snapshot 0.31s (old 0.12s), before.json 4.04 MB (old 0.00 MB), compare peak RSS 68 MiB
50k ignored files: 0.23s, 1.99 MB, 45 MiB
2 GiB sparse ignored file: never read, 0.19s, 0.00 MB
```

## Tasks

### Phase 0: Fix
- [ ] Add, in `skills/run-agoge/scripts/test_target_snapshot_state.py`, with the `target_snapshot` module's `IGNORED_FILE_CAP` patched to a small number through `monkeypatch` and `take_snapshot` and `compare` called in-process under the fixture's git environment: `test_ignored_listing_over_cap_records_directories_only` (more ignored files than the cap: `ignored` holds only entries ending in `/`, `ignored_overflow` is the integer count of ignored files, and removing an ignored directory gives `ignored-removed` for that directory entry), `test_ignored_listing_at_cap_records_every_file` (exactly the cap: every file is named and the snapshot has no `ignored_overflow` key), `test_ignored_listing_crossing_cap_reports_no_file_removals` (a snapshot at the cap, one more ignored file added, then `compare`: no `ignored-removed` violation) and `test_v4_snapshot_refused_after_ignored_cap` (a snapshot rewritten with `"version": 4` makes `compare` exit 2 with a line containing `is not version 5`) - Acceptance: `pytest -k "ignored_listing or ignored_cap"` fails on the unmodified script.
- [ ] In `skills/run-agoge/scripts/test_target_snapshot.py`, change `assert target_snapshot.VERSION == 4` to `== 5`. Premise: `rg -n "VERSION == 4" skills/run-agoge/scripts` hits exactly that one line, in `test_previous_version_snapshot_exits_2_with_one_line`; if it hits elsewhere or nowhere, skip and report - Acceptance: `pytest -k previous_version_snapshot` fails on the unmodified script.
- [ ] Add `IGNORED_FILE_CAP = 20000`; in `take_snapshot`, when the listing without `--directory` has more entries than the cap, store only the `--directory` listing's entries ending in `/` and add `ignored_overflow` (that count), else store what it stores today and no `ignored_overflow` key; in `compare`, when either snapshot has `ignored_overflow`, check only the before entries ending in `/` for `ignored-removed`; where `_load` type-checks top-level keys, accept a missing `ignored_overflow` and require an `int` when present; bump `VERSION` to 5; state the cap and the loss in the docstring (depends on: previous task) - Acceptance: `pytest -k "ignored_listing or ignored_cap"` passes, and `pytest -k previous_version_snapshot` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "stops listing individual ignored files above 20000" CHANGELOG.md` hits under `[Unreleased]` `### Changed`.

## Success Criteria

- `pytest -k "ignored_listing or ignored_cap"` passes; the full suite passes under `dev/bin/release-checks`.
