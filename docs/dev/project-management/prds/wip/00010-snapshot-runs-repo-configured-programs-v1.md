---
lane: full
design: run
default_model: opus
model_tier_rationale: security boundary and Git config precedence across includes and recursive submodules require design
---
# Taking a snapshot runs programs the repo's own git config names

Source: agoge run 2026-11-08, finding 4 of 18 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

The `git status` call inside `target_snapshot.py` honours the target's `core.fsmonitor` and clean filters (`filter.<x>.clean`, `filter.<x>.process`). A repo can therefore run any program during what the docstring calls a read-only check. Targets are the operator's own repos, so likelihood is low, but the claim "nothing runs" is false.

## Solution

In `_git`, disable fsmonitor for every Git invocation, including configuration discovery. Discover effective filter keys for each repository independently using `git config --includes --null --name-only --get-regexp '^filter\..*\.(clean|process|required)$'`, without a scope restriction. Parse NUL-delimited keys as filesystem bytes and split the final property suffix, preserving the entire filter name. Disable each driver's clean and process commands and set required to false. Never replace clean with an executable such as `cat`.

Design must select and verify an override transport that preserves names containing `=` or whitespace. Plain `-c key=value` is insufficient for equals-containing keys. A local probe confirms Git accepts `GIT_CONFIG_KEY_n=filter.a=b.clean` with an empty `GIT_CONFIG_VALUE_n`; the design must also resolve precedence against inherited command-scope configuration and preserve unrelated effective settings. Cache discovery per canonical repository, not once globally. Submodules need their own configuration discovery. Preserve the inherited repository-variable sanitization introduced by PRD 00012 in both discovery and execution. Discovery errors other than no matching keys must fail closed through the existing one-line exit-2 error contract.

## Requirements

### Must have
- A snapshot and compare of a repo with fsmonitor and clean-filter marker scripts leave no marker file.
- Marker tests cover clean and process filters from local, global, included, matching conditional-include, worktree and submodule configuration, plus filter names containing `=`, spaces and dots.
- Fixtures demonstrate that the marker program executes without the mitigation; snapshot and compare then leave the marker absent. Cover required filters and inherited command-scope configuration precedence.
- A submodule with a filter absent from its parent cannot execute that filter. Configuration discovery failures exit 2 without running configured programs.
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
- **Risk**: closes the known vectors (fsmonitor, filters), not unknown config-driven executables. Disabling a clean filter (git-lfs included) can make status report a filtered file as modified; the snapshot then records more dirty paths, which is safe. Do not claim that every possible Git-configured program is blocked.

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
- [ ] Parameterize does-not-run regression coverage for all configuration sources, special names, required filters, command-scope precedence, recursive submodules and discovery failures (depends on: previous task) - Acceptance: each executable fixture has a positive control; included, equals-named and submodule cases fail against the parked branch; all pass after implementation.
- [ ] Add the config overrides in `_git` (depends on: previous task) - Acceptance: `pytest -k "does_not_run or untouched_target"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer runs the repo's fsmonitor" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k does_not_run` passes; the full suite passes under `dev/bin/release-checks`.

## Retry evidence (2026-11-09)

Batch `202611082330` parked this PRD for F11 (includes omitted), F12 (equals-named filter bypass) and F13 (submodule filters omitted). The parked branch `fast-track/00010-snapshot-runs-repo-configured-programs-v1-c1` ends at `d3dcc4a`; its three unmerged commits remain evidence, not an approved implementation. Local probes confirmed all-scope included-key discovery and an empty environment override for an equals-named key. Those probes establish feasibility, not complete security validation. Implement against current master, preserving subsequent snapshot fixes. Re-check the premise first; if already fixed, report the evidence and skip redundant changes. Run design and the full review gate, with review in a fresh session, through the normal autopilot workflow. Historical deferred records remain unchanged.
