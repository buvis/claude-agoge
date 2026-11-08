---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact check and message given; mirrors target_snapshot._resolve_repo
---
# A mistyped or non-repo path to the PRD allocator succeeds and builds a PRD tree in the wrong place

Source: agoge run 2026-11-08, finding 8 of 18 (MEDIUM, verified, lanes walter and heidi), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py <repo> <slug>` creates the whole `docs/dev/project-management/prds/backlog/` tree under any path: a missing one, a plain directory, or a repo subdirectory. It numbers from 00001 there and exits 0. A typo at step 9 of `run-agoge` files a PRD where nobody looks.

## Solution

In `main`, before calling `claim`, run `git -C <repo> rev-parse --show-toplevel` and require `os.path.realpath` of its output to equal `os.path.realpath` of the argument (the same check as `_resolve_repo` in `target_snapshot.py`). Otherwise print one line `allocate_prd_number: <repo> is not the top level of a git work tree` to stderr and return 2, creating nothing. `claim` itself is unchanged, so tests that call `claim(tmp_path, ...)` directly need no `git init`.

## Requirements

### Must have
- A missing path, a non-repo directory and a repo subdirectory each exit 2 with one stderr line and create nothing.
- A repo top level works as before.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator refuses a path that is not a git work-tree top level`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: refuse a repo argument that is not a work-tree top level.
- **Exports**: none new
- New symbols: `test_cli_refuses_missing_path`, `test_cli_refuses_non_repo_dir`, `test_cli_refuses_repo_subdirectory`
- **Risk**: the allocator CLI now needs `git` on PATH. CLI tests that pass a plain temp directory (`test_cli_prints_the_path_it_claimed`) must `git init` it first. `skills/run-agoge/references/prd-emission.md` already passes an absolute repo top level and needs no change.

### Dependencies
- allocator: No dependencies (foundation)

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

### Phase 0: Fix
- [ ] Add `test_cli_refuses_missing_path`, `test_cli_refuses_non_repo_dir`, `test_cli_refuses_repo_subdirectory` - Acceptance: `pytest -k cli_refuses` fails on the unmodified script.
- [ ] Add the top-level check in `main`; `git init` the temp dir in `test_cli_prints_the_path_it_claimed` (depends on: previous task) - Acceptance: `pytest test_allocate_prd_number.py` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "refuses a path that is not a git work-tree top level" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k cli_refuses` passes; the full suite passes under `dev/bin/release-checks`.
