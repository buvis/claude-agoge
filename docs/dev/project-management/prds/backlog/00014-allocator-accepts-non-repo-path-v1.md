# A mistyped or non-repo path to the PRD allocator succeeds and builds a PRD tree in the wrong place

Source: agoge run 2026-11-08, finding 8 of 18 (MEDIUM, verified, lanes walter and heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py <repo> <slug>` creates the whole `docs/dev/project-management/prds/backlog/` tree under any path: a missing one, a plain directory, or a repo subdirectory. It numbers from 00001 there and exits 0. A typo at step 9 of `run-agoge` files a PRD where nobody looks.

## Solution

Before any `mkdir`, run `git -C <repo> rev-parse --show-toplevel` and require it to equal the resolved argument. Otherwise print one line `allocate_prd_number: <repo> is not the top level of a git work tree` and exit 2, creating nothing.

## Requirements

### Must have
- A missing path, a non-repo directory and a repo subdirectory each exit 2 with one stderr line and create nothing.
- A repo top level works as before.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator refuses a path that is not a git work-tree top level`.

## Implementation

- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`; check `skills/run-agoge/references/prd-emission.md` still describes the call correctly.
- **Risk**: the allocator now needs `git` on PATH. Existing tests that use a plain temp directory as the repo must `git init` it first.

## Test Strategy

Regression tests for the three refused paths. Reproduction from the run:

```
allocate_prd_number.py $SCRATCH/no/such/repo fix-thing
  -> .../no/such/repo/docs/dev/project-management/prds/backlog/00001-fix-thing-v1.md rc=0 (whole tree created)
allocate_prd_number.py $SCRATCH/pr/docs sub-slug
  -> .../pr/docs/docs/dev/project-management/prds/backlog/00001-sub-slug-v1.md rc=0 (real next number: 00052)
allocate_prd_number.py <scratch>/nope x -> rc=0, "nope created? True"; plain dir nonrepo -> rc=0, new tree
```

## Tasks

- [ ] Add regression tests; watch them fail.
- [ ] Add the top-level check.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
