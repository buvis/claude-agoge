---
lane: fast-track
design: skip
model_tier_rationale: one-token change with its regression case; haiku acceptable, so default_model is omitted
---
# A slug ending in a newline is accepted and creates a file name split across two lines

Source: agoge run 2026-11-08, finding 10 of 18 (LOW, verified, lanes walter and trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` validates the slug with a regex ending in `$`, which in Python also matches before a final newline. Slug `'x\n'` passes and creates `00053-x\n-v1.md`. The printed path spans two lines, so a caller reading the first line writes to a wrong path.

## Solution

In `claim`, replace `SLUG_RE.match(slug)` with `SLUG_RE.fullmatch(slug)`.

## Requirements

### Must have
- Slug `"ab\n"` is rejected like other bad slugs.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator rejects a slug with a trailing newline`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: reject slugs with a trailing newline.
- **Exports**: none new
- **Risk**: none expected.

### Dependencies
- allocator: No dependencies (foundation)

## Test Strategy

Add `"ab\n"` to the parametrized slugs of `test_a_bad_slug_is_refused_rather_than_normalized`. Reproduction from the run:

```
slug='x\n' rc= 0 out= .../00053-x
-v1.md
backlog listing: '00053-x\n-v1.md'
rejected as expected: ../x, /etc/x, UP, a\nb, café, a-, empty string
```

## Tasks

### Phase 0: Fix
- [ ] Add `"ab\n"` to the bad-slug parameters - Acceptance: `pytest -k bad_slug_is_refused` fails on the unmodified script.
- [ ] Switch to `fullmatch` (depends on: previous task) - Acceptance: `pytest -k bad_slug_is_refused` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "rejects a slug with a trailing newline" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k bad_slug_is_refused` passes; the full suite passes under `dev/bin/release-checks`.
