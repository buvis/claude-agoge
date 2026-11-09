---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact validation rule given; one regression test
---
# A crafted before.json puts git options into the printed restore command

Source: agoge run 2026-11-08, finding 11 of 18 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`compare` builds `restore` command strings from ref names and values loaded from the snapshot file. Shell metacharacters are quoted with `shlex.quote`, but a name or value that starts with a dash reaches git as an option (`update-ref --stdin`). Exploiting it needs someone to tamper with the master's scratch snapshot and the operator to run the printed line, so the risk is low.

## Solution

In `_load`, validate the snapshot's `refs` map: every key starts with `refs/` (that is all `git for-each-ref` emits; `HEAD` lives under the separate `head` key), and every value matches `^[0-9a-f]{40}$` or `^[0-9a-f]{64}$`. Otherwise raise `Fail(f"snapshot {path} has a malformed ref")`, which exits 2 with one line.

## Requirements

### Must have
- A snapshot file with a ref named `--stdin`, or a value `--no-deref`, makes `compare` exit 2 with one line.
- Valid snapshots load as before.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target compare rejects a snapshot file with malformed ref names or ids`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: reject malformed refs when loading a snapshot.
- **Exports**: none new
- New symbols: `test_malformed_ref_name_in_snapshot_exits_2`, `test_malformed_ref_value_in_snapshot_exits_2`
- **Risk**: none expected; `refs/stash`, notes and remote refs all start with `refs/`.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Reproduction from the run (the printed lines were not executed):

```
before.json ref keys: --stdin, "; echo TRUDY #", refs/heads/$(echo TRUDY) (value --no-deref); compare -> rc=1
restore = git -C …/r2 update-ref --stdin x ''
restore = … update-ref 'refs/heads/$(echo TRUDY)' --no-deref ''
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_malformed_ref_name_in_snapshot_exits_2` and `test_malformed_ref_value_in_snapshot_exits_2` - Acceptance: `pytest -k malformed_ref` fails on the unmodified script.
- [ ] Add the validation in `_load` (depends on: previous task) - Acceptance: `pytest -k "malformed_ref or restore_commands or non_utf8_refs"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "rejects a snapshot file with malformed ref" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k malformed_ref` passes; the full suite passes under `dev/bin/release-checks`.
