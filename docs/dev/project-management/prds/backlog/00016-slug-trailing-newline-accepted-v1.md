# A slug ending in a newline is accepted and creates a file name split across two lines

Source: agoge run 2026-11-08, finding 10 of 18 (LOW, verified, lanes walter and trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` validates the slug with a regex ending in `$`, which in Python also matches before a final newline. Slug `'x\n'` passes and creates `00053-x\n-v1.md`. The printed path spans two lines, so a caller reading the first line writes to a wrong path.

## Solution

Validate with `SLUG_RE.fullmatch(slug)`.

## Requirements

### Must have
- Slug `"ab\n"` is rejected like other bad slugs.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator rejects a slug with a trailing newline`.

## Implementation

- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Risk**: none expected.

## Test Strategy

Reproduction from the run:

```
slug='x\n' rc= 0 out= .../00053-x
-v1.md
backlog listing: '00053-x\n-v1.md'
rejected as expected: ../x, /etc/x, UP, a\nb, café, a-, empty string
```

## Tasks

- [ ] Add the regression test; watch it fail.
- [ ] Switch to `fullmatch`.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes; the full suite passes under `dev/bin/release-checks`.
