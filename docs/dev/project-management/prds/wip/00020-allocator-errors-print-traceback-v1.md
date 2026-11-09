---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact message and exit codes given; existing exit-code tests named
---
# PRD allocator errors print a traceback and exit 1 instead of one line and exit 2

Source: agoge run 2026-11-08, finding 15 of 18 (LOW, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` exits 2 on a usage error, but exits 1 with an 11-line traceback on an OS error (read-only backlog), and exits 1 on a bad slug. `target_snapshot.py` follows a one-line, exit-2 contract. A caller cannot tell bad input from a crash.

## Solution

In `main`, wrap the `claim` call: on `OSError` print `allocate_prd_number: <exc>` to stderr and return 2; on `SystemExit` raised by `claim` with a string message (bad slug, attempts exhausted), print `allocate_prd_number: <message>` to stderr and return 2. `claim` keeps raising as today, so `test_a_bad_slug_is_refused_rather_than_normalized` (which expects `SystemExit` from `claim`) is unchanged.

## Requirements

### Must have
- A read-only backlog exits 2 with exactly one `allocate_prd_number: ` stderr line and no traceback.
- A bad slug via the CLI exits 2 with one `allocate_prd_number: ` line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator reports errors as one line with exit 2`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: map every CLI failure to one line and exit 2.
- **Exports**: none new
- New symbols: `test_cli_read_only_backlog_exits_2_with_one_line`, `test_cli_bad_slug_exits_2_with_one_line`
- **Risk**: changes the CLI exit code for a bad slug from 1 to 2; no caller depends on 1 (`prd-emission.md` checks only success). PRDs 00014 and 00015 add their own exit-2 lines in `main` earlier in the batch; keep their messages.

### Dependencies
- allocator: No dependencies (foundation)

## Test Strategy

Tests run the CLI on a `git init` temp repo (needed after PRD 00014). Reproduction from the run:

```
read-only backlog -> rc=1, 11-line traceback ending "PermissionError: [Errno 13]"
bad slug -> rc=1; usage errors -> rc=2
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_cli_read_only_backlog_exits_2_with_one_line` and `test_cli_bad_slug_exits_2_with_one_line` - Acceptance: `pytest -k "exits_2_with_one_line"` fails on the unmodified script.
- [ ] Catch `OSError` and `SystemExit` in `main` (depends on: previous task) - Acceptance: `pytest test_allocate_prd_number.py` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "reports errors as one line with exit 2" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k exits_2_with_one_line` passes; the full suite passes under `dev/bin/release-checks`.
