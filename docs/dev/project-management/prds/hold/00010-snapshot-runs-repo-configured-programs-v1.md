---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact git flags given; marker-file test fails loudly
---
# Taking a snapshot runs programs the repo's own git config names

Source: agoge run 2026-11-08, finding 4 of 18 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

The `git status` call inside `target_snapshot.py` honours the target's `core.fsmonitor` and clean filters (`filter.<x>.clean`, `filter.<x>.process`). A repo can therefore run any program during what the docstring calls a read-only check. Targets are the operator's own repos, so likelihood is low, but the claim "nothing runs" is false.

## Solution

In `_git`, always pass `-c core.fsmonitor=false`. Read every filter name visible to the repo with `git -c core.fsmonitor=false -C <repo> config --get-regexp '^filter\.'` (all scopes, includes followed), and pass `-c filter.<x>.clean= -c filter.<x>.process=` for each name. Compute the list once per process.

## Requirements

### Must have
- A snapshot and compare of a repo with fsmonitor and clean-filter marker scripts leave no marker file.
- Snapshot output for an ordinary repo is unchanged.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer runs the repo's fsmonitor or clean filter programs`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: neutralize config-driven programs in every git call.
- **Exports**: none new
- New symbols: `test_snapshot_does_not_run_fsmonitor`, `test_snapshot_does_not_run_clean_filter`
- **Risk**: closes the known vectors (fsmonitor, filters), not unknown config-driven executables. Disabling a clean filter (git-lfs included) can make status report a filtered file as modified; the snapshot then records more dirty paths, which is safe.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression test with marker scripts in a temp dir outside the repo. Reproduction from the run:

```
scratch repo r1, local core.fsmonitor = marker script
target_snapshot.py snapshot r1 out/s1.json -> rc=0
marker.log: "fsmonitor 2 1794168886500536000" (and the same line twice more: three runs)
fsmonitor unset, .gitattributes "*.txt filter=trudy", filter.trudy.clean=<marker>, same-size edit with newer mtime
marker.log: "filter "
core.hooksPath (reference-transaction hook) and core.pager: not triggered
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_snapshot_does_not_run_fsmonitor` and `test_snapshot_does_not_run_clean_filter` - Acceptance: `pytest -k "does_not_run"` fails on the unmodified script (marker file written).
- [ ] Add the config overrides in `_git` (depends on: previous task) - Acceptance: `pytest -k "does_not_run or untouched_target"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer runs the repo's fsmonitor" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k does_not_run` passes; the full suite passes under `dev/bin/release-checks`.
