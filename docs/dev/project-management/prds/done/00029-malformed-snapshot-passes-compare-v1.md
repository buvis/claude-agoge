---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: key and type table given; each bad shape has a quoted reproduction
---
# A malformed `before.json` exits 2 with "unexpected KeyError", and some bad shapes pass silently

Source: agoge run 2026-11-15, finding 7 of 14 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 1 (type-check in `_load`).

## Problem

`compare` in `target_snapshot.py` does not validate the snapshot's shape. `_load` checks only `version`, `repo` and ref names. A missing key surfaces as `unexpected KeyError`. `version: 4.0` passes, because `4.0 == 4` in Python. A string where a list belongs is iterated by character and yields fake removed paths. A hand-edited snapshot therefore gives a poor message or a wrong verdict. Exit codes stay in contract.

Users hit: anyone who edits or truncates a snapshot file by hand.

## Solution

In `_load`, after the JSON parses and before the `belongs to another repo` check (so a missing `repo` reads as malformed):

1. Require `type(data.get("version")) is int` and equal to `VERSION`. This rejects `4.0` and `True`.
2. Check each top-level key is present with its type. One tuple of `(key, type)` pairs is enough:

| Key | Type |
|---|---|
| `repo`, `config`, `index` | `str` |
| `head`, `refs`, `worktree_heads`, `submodules`, `dirty`, `untracked_fingerprints`, `gitdir` | `dict` |
| `worktrees`, `untracked`, `ignored` | `list` |

3. Require every entry of `untracked` to be a key of `untracked_fingerprints`; a miss reports the key `untracked_fingerprints`.

Any miss raises `Fail(f"snapshot {path} is malformed: {key}")`. Element types inside the dicts and lists are not checked: that is the full schema table the operator did not pick.

## Requirements

### Must have
- A snapshot with any key above missing or of the wrong type exits 2 with one line `target_snapshot: snapshot <path> is malformed: <key>`, and never `unexpected`.
- `version: float(VERSION)` (4.0 today) and `version: true` exit 2 with the existing `is not version <VERSION>` line. The tests take the number from `target_snapshot.VERSION`, never a literal: PRD 00037 bumps it.
- A snapshot written by `snapshot` still loads.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target compare rejects a snapshot file with a missing or wrongly typed field, naming the field, instead of reporting an unexpected error or a false verdict`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: fail closed on a snapshot of the wrong shape.
- **Exports**: none new
- New symbols: `test_snapshot_missing_field_is_rejected_by_name`, `test_snapshot_wrongly_typed_field_is_rejected_by_name`, `test_snapshot_float_or_bool_version_is_rejected`
- **Risk**: a key added to `take_snapshot` later without a row here loads unchecked; a key added here without one in `take_snapshot` rejects every snapshot, which the existing suite catches at once. Nested submodule snapshots are not checked.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Take a real snapshot, load the JSON, break one thing, write it back, run `compare`, and check with `_assert_exit2`. Parametrize the missing-field test over every key in the table, so a new unchecked key is the only way to miss one.

Reproduction from the run:

```
Missing untracked_fingerprints: unexpected KeyError: "'untracked_fingerprints'", exit 2.
version: 4.0 gave exit 0 unchanged.
untracked as "abc" gave exit 1 with fake untracked-removed a, b, c.
No traceback.
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_snapshot_missing_field_is_rejected_by_name` (parametrized over `repo`, `config`, `index`, `head`, `refs`, `worktree_heads`, `submodules`, `dirty`, `untracked_fingerprints`, `gitdir`, `worktrees`, `untracked`, `ignored`: take a real snapshot, delete the key, and `compare` exits 2 with the one line `target_snapshot: snapshot <path> is malformed: <key>`), `test_snapshot_wrongly_typed_field_is_rejected_by_name` (`untracked` as the string `"abc"` and `refs` as a list give the same line with that key; an `untracked` entry missing from `untracked_fingerprints` gives it with `untracked_fingerprints`) and `test_snapshot_float_or_bool_version_is_rejected` (`float(target_snapshot.VERSION)` and `True` exit 2 with the existing `is not version` line; no literal version number in the test) - Acceptance: `pytest -k "snapshot_missing_field or snapshot_wrongly_typed or float_or_bool_version"` fails on the unmodified script.
- [ ] In `_load`, before the `belongs to another repo` check: require `type(data.get("version")) is int` and equal to `VERSION`; check each top-level key against its type (`repo`, `config`, `index`: `str`; `head`, `refs`, `worktree_heads`, `submodules`, `dirty`, `untracked_fingerprints`, `gitdir`: `dict`; `worktrees`, `untracked`, `ignored`: `list`); require every `untracked` entry to be a key of `untracked_fingerprints`; any miss raises `Fail(f"snapshot {path} is malformed: {key}")` (depends on: previous task) - Acceptance: `pytest -k "snapshot_missing_field or snapshot_wrongly_typed or float_or_bool_version"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "missing or wrongly typed field" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- The three new tests pass; the full suite passes under `dev/bin/release-checks`.
