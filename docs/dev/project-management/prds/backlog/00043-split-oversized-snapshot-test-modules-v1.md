---
lane: solo
design: skip
default_model: sonnet
model_tier_rationale: test-only move; collected test ids before and after prove nothing was lost
---
# Two snapshot test modules are over the 800-line cap

Source: batch `202611232314` review. Flagged by the reviews of PRDs 00027, 00028 (R2), and 00039. Triaged 2026-11-25: new backlog PRD.

## Problem

`skills/run-agoge/scripts/test_target_snapshot.py` is 1126 lines and `skills/run-agoge/scripts/test_target_snapshot_state.py` is 1059 lines. The cap is 800 lines. The ruff format in PRD 00039 made them longer. Reviewers flag the files in every cycle, and it is hard to find a test by topic.

Users hit: the maintainer and every reviewer lane.

## Solution

Split each file into modules by topic (for example fifo, symlink, gitdir and worktree, restore, allow and compare). Move test functions without changes. Shared helpers go to `snapshot_fixtures.py` or `conftest.py` and are not copied.

## Requirements

### Must have
- Every new test module is at most 800 lines.
- The set of collected test names (`pytest --collect-only -q`, compared by function name and parameter id, not file path) is the same before and after.
- Test bodies do not change. Only imports, helper locations, and module docstrings may change.
- `dev/bin/release-checks` passes, and its file lists (if any name these modules) are updated.
- No CHANGELOG entry (test-only change).

### Nice to have
- None.

## Implementation

### Module: snapshot test layout
- **Location**: `skills/run-agoge/scripts/test_target_snapshot*.py`, `skills/run-agoge/scripts/snapshot_fixtures.py`, `skills/run-agoge/scripts/conftest.py`, `dev/bin/release-checks`, CI workflow files that name test modules
- **Responsibility**: group snapshot tests by topic in modules under the size cap.
- **Exports**: none
- **Risk**: a module-scoped template fixture (PRD 00028) builds once per module, so more modules mean more builds. Measure wall time before and after, and report it.

### Dependencies
- snapshot test layout: No dependencies (foundation)

## Test Strategy

Compare the collected test names before and after the split. The pass and skip counts must match.

## Tasks

### Phase 0: Split
- [ ] Record the collected test names and the pass/skip counts (`uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -p no:cacheprovider --collect-only`) - Acceptance: the list is saved under `docs/dev/tmp/` and the counts are in the commit message of the next task (this task changes no file).
- [ ] Split both modules by topic (depends on: previous task) - Acceptance: every snapshot test module is at most 800 lines; the collected test names equal the recorded list; pass and skip counts match; wall time is reported.

## Success Criteria

- No file under `skills/run-agoge/scripts/` that starts with `test_target_snapshot` is over 800 lines, and the suite runs the same tests.
