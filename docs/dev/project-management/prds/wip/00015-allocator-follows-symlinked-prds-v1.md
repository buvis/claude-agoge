---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact containment expression given; one regression test
---
# PRD allocation writes outside the repo through a symlinked prds directory

Source: agoge run 2026-11-08, finding 9 of 18 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

If `docs/dev/project-management/prds` (or `backlog`) in the target is a symlink, `allocate_prd_number.py` follows it and creates the PRD file outside the repo, exit 0. Only a repo that plants the symlink is affected, and the write is one empty file.

## Solution

In `main`, before calling `claim`, require `os.path.commonpath([backlog.resolve(), repo.resolve()]) == str(repo.resolve())`, where `backlog` is `repo / "docs/dev/project-management/prds/backlog"`. Otherwise print one line `allocate_prd_number: <backlog> resolves outside <repo>` to stderr and return 2, creating nothing.

## Requirements

### Must have
- A symlinked `prds` or `backlog` pointing outside the repo exits 2 with one line and creates nothing.
- A symlink that stays inside the repo still works.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD allocator refuses to write through a symlink that leaves the repo`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: refuse a backlog path that resolves outside the repo.
- **Exports**: none new
- New symbols: `test_cli_refuses_prds_symlink_leaving_repo`, `test_cli_refuses_backlog_symlink_leaving_repo`, `test_cli_follows_symlink_inside_repo`
- **Risk**: an operator who symlinks prds outside the repo on purpose gets refused.

### Dependencies
- allocator: No dependencies (foundation)

## Test Strategy

Tests run the CLI on a `git init` temp repo. Reproduction from the run:

```
a1/docs/dev/project-management/prds -> $SCRATCH/outside
allocate_prd_number.py a1 trudy-marker -> rc=0, file at outside/backlog/00001-trudy-marker-v1.md
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_cli_refuses_prds_symlink_leaving_repo`, `test_cli_refuses_backlog_symlink_leaving_repo`, `test_cli_follows_symlink_inside_repo` - Acceptance: `pytest -k "symlink_leaving_repo"` fails on the unmodified script.
- [ ] Add the containment check (depends on: previous task) - Acceptance: `pytest -k "symlink"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "refuses to write through a symlink" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k symlink` passes; the full suite passes under `dev/bin/release-checks`.
