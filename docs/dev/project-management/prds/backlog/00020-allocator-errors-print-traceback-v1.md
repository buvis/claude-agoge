# PRD allocator errors print a traceback and exit 1 instead of one line and exit 2

Source: agoge run 2026-11-08, finding 15 of 18 (LOW, verified, lane heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` exits 2 on a usage error, but exits 1 with an 11-line traceback on an OS error (read-only backlog), and exits 1 on a bad slug. `target_snapshot.py` follows a one-line, exit-2 contract. A caller cannot tell bad input from a crash.

## Solution

In `main`, catch `OSError` and print `allocate_prd_number: <reason>` to stderr, then exit 2. A bad slug also exits 2 with one line.

## Requirements

### Must have
- A read-only backlog exits 2 with exactly one `allocate_prd_number: ` line and no traceback.
- A bad slug exits 2 with one line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator reports errors as one line with exit 2`.

## Implementation

- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Risk**: changes an exit code; existing tests that expect 1 for a bad slug must change with it (no other caller found). Coordinate with 00014 and 00015, which add exit-2 paths to the same script.

## Test Strategy

Reproduction from the run:

```
read-only backlog -> rc=1, 11-line traceback ending "PermissionError: [Errno 13]"
bad slug -> rc=1; usage errors -> rc=2
```

## Tasks

- [ ] Add regression tests; watch them fail.
- [ ] Catch `OSError`; make the bad-slug exit 2.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
