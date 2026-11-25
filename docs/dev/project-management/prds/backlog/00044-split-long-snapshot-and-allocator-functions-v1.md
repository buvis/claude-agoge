---
design: skip
default_model: sonnet
model_tier_rationale: behavior-preserving refactor of code pinned by the existing suite; target_snapshot.py is the integrity check, so the full review lane runs, not the solo lane
---
# Five production functions are over the 50-line limit

Source: batch `202611232314` review of PRD 00039 (deferred decision on long functions). Triaged 2026-11-25: new backlog PRD, production code only. The long test functions belong to PRD 00043.

## Problem

Five functions are longer than 50 lines (measured with `ast` on 2026-11-25):

| File | Function | Lines |
|------|----------|-------|
| `skills/run-agoge/scripts/target_snapshot.py` | `take_snapshot` | 72 |
| `skills/run-agoge/scripts/target_snapshot.py` | `compare` | 65 |
| `skills/run-agoge/scripts/target_snapshot.py` | `_filter_overrides` | 57 |
| `skills/run-agoge/scripts/allocate_prd_number.py` | `main` | 61 |
| `skills/run-agoge/scripts/allocate_prd_number.py` | `claim` | 52 |

Long functions are hard to review, and reviewers flag them in every cycle.

Users hit: the maintainer and every reviewer lane.

## Solution

Extract cohesive steps of each function into private helpers in the same file. Keep each public signature, return shape, error text, and exit code. Do not change behavior.

## Requirements

### Must have
- Every function in `target_snapshot.py` and `allocate_prd_number.py` is at most 50 lines, measured from `def` to the last line.
- No behavior change: the whole suite passes with the same pass and skip counts as the baseline, and no test file changes.
- The snapshot JSON and the CLI output of both scripts stay byte-identical for the fixtures in the suite.
- The `functools.lru_cache` reset in `take_snapshot` (`_is_symlink_escaping.cache_clear()`) still runs first in each snapshot.
- No CHANGELOG entry (refactor).

### Nice to have
- None.

## Implementation

### Module: snapshot script
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`
- **Responsibility**: split `take_snapshot`, `compare`, and `_filter_overrides` into named steps.
- **Exports**: unchanged
- **Risk**: this is the integrity check that guards target repos. A helper that changes the order of git calls or the env given to them can reopen bugs fixed in PRDs 00010, 00012, and 00033 (repo-configured programs). Keep the env construction in one place.

### Module: PRD number allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`
- **Responsibility**: split `claim` and `main` into named steps.
- **Exports**: unchanged
- **Risk**: `claim` holds the race fix from PRD 00035. Keep the lock and the create-exclusive step in one helper.

### Dependencies
- snapshot script: No dependencies (foundation)
- PRD number allocator: No dependencies (foundation)

## Test Strategy

The existing suite pins the behavior. Run it before and after, and compare the pass and skip counts. Add no tests.

## Tasks

### Phase 0: Refactor
- [ ] Split `take_snapshot`, `compare`, and `_filter_overrides` in `target_snapshot.py` - Acceptance: each function in the file is at most 50 lines; the suite passes with the baseline counts.
- [ ] Split `claim` and `main` in `allocate_prd_number.py` - Acceptance: each function in the file is at most 50 lines; the suite passes with the baseline counts.

## Success Criteria

- No function in `target_snapshot.py` or `allocate_prd_number.py` is over 50 lines, and the suite passes with the baseline pass and skip counts.
