# PRD allocation writes outside the repo through a symlinked prds directory

Source: agoge run 2026-11-08, finding 9 of 18 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

If `docs/dev/project-management/prds` (or `backlog`) in the target is a symlink, `allocate_prd_number.py` follows it and creates the PRD file outside the repo, exit 0. Only a repo that plants the symlink is affected, and the write is one empty file.

## Solution

Before `mkdir` and create, resolve the backlog directory and require that the resolved repo path is its common path (`os.path.commonpath([backlog.resolve(), repo.resolve()]) == repo.resolve()`). Otherwise print one line and exit 2, creating nothing.

## Requirements

### Must have
- A symlinked `prds` or `backlog` pointing outside the repo exits 2 with one line and creates nothing.
- A symlink that stays inside the repo still works.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator refuses to write through a symlink that leaves the repo`.

## Implementation

- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Risk**: an operator who symlinks prds outside the repo on purpose gets refused.

## Test Strategy

Reproduction from the run:

```
a1/docs/dev/project-management/prds -> $SCRATCH/outside
allocate_prd_number.py a1 trudy-marker -> rc=0, file at outside/backlog/00001-trudy-marker-v1.md
```

## Tasks

- [ ] Add the regression test; watch it fail.
- [ ] Add the containment check.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes; the full suite passes under `dev/bin/release-checks`.
