---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: docstring sentence plus one test that pins the documented label
---
# Replacing an untracked file with a fifo reports `untracked-removed`, not `untracked-modified`

Source: agoge run 2026-11-15, finding 10 of 14 (LOW, verified, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 2 (document it).

## Problem

Git does not list fifos, sockets or devices as untracked. When an untracked file is replaced by one, `compare` in `target_snapshot.py` no longer sees the path in git's listing and reports `untracked-removed`, though something still sits at that path. The change is detected (exit 1); only the label is off, and a reader deciding how to restore may be misled by it.

Users hit: anyone who reads a `compare` report after a lane replaced a file with a special file.

## Solution

Keep the behaviour. Add one sentence to the module docstring: an untracked path replaced by a fifo, socket or device reads as `untracked-removed`, because git does not list such files.

Option 1 (report `untracked-modified` when the path still exists) was not chosen.

## Requirements

### Must have
- The module docstring states that an untracked file replaced by a special file is reported as `untracked-removed`.
- A test pins the documented label and the exit code.
- No CHANGELOG entry (docs and test only).

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`
- **Responsibility**: say what the label means in this case.
- **Exports**: none new
- New symbols: `test_untracked_file_replaced_by_fifo_reads_as_removed`
- **Risk**: the label stays wrong and may mislead a restore decision. That is the accepted cost of this option.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Reproduction from the run, restated as the pinning test (it passes before and after, since behaviour does not change):

```
rm u.txt; mkfifo u.txt, then compare: exit 1, untracked-removed u.txt; --allow u.txt gave exit 0.
```

## Tasks

### Phase 0: Document
- [ ] Add the docstring sentence - Acceptance: `rg -F "fifo, socket or device" skills/run-agoge/scripts/target_snapshot.py` hits inside the module docstring.
- [ ] Add `test_untracked_file_replaced_by_fifo_reads_as_removed` - Acceptance: `pytest -k replaced_by_fifo_reads_as_removed` passes.

## Success Criteria

- The docstring names the case; the full suite passes under `dev/bin/release-checks`.
