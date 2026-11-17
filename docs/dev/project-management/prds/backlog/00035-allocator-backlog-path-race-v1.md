---
design: skip
default_model: opus
model_tier_rationale: fd-relative file creation and a race test need a byte-level contract across two functions
---
# The PRD allocator can write outside the repo if the backlog path is swapped during the run

Source: agoge run 2026-11-16, finding 6 of 11 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-16.md`. Decision: accepted, option 1 (open once, create relative to the fd). The packet recommended documenting only; the human chose the fix.

## Problem

`main` in `allocate_prd_number.py` checks that the backlog path resolves inside the repo. `claim()` then calls `mkdir`, takes the lock, scans, and creates the file through the path again. If `prds/backlog` becomes a symlink in between, the file lands outside the repo while the printed path stays inside it. The attacker needs write access to the repo during the run.

Users hit: an unattended loop that points the allocator at a repo someone else can write to.

## Solution

In `claim()`, open the backlog directory once with `os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)` after `mkdir`, and create each candidate with `os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644, dir_fd=backlog_fd)`. Confirm the fd is inside the repo with `os.fstat(backlog_fd)` equal to `os.stat(resolved_backlog)` (same `st_dev` and `st_ino`) taken after the open. If `O_NOFOLLOW` rejects the path (`ELOOP` or `ENOTDIR`) or the identity differs, exit 2 with `allocate_prd_number: <backlog> resolves outside <repo>`. The printed path stays `<backlog>/<NNNNN>-<slug>-v1.md`.

## Requirements

### Must have
- If `prds/backlog` is a symlink to an outside directory at claim time, the script exits 2 and creates no file outside the repo.
- If `prds/backlog` is swapped for such a symlink after the first check and before the create, no file lands outside the repo.
- Normal runs print the same path and create the same file as before.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: PRD number allocator no longer writes outside the repo if the backlog path is swapped during the run`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: create the claimed file inside the checked directory, never through a re-resolved path.
- **Exports**: none
- New symbols: `test_claim_rejects_backlog_symlink_at_claim_time`, `test_claim_does_not_follow_backlog_swapped_after_check`
- **Risk**: `O_NOFOLLOW` fails where `backlog` is a symlink that stays inside the repo; that case now exits 2 (it was allowed). The swap test needs a monkeypatched hook between check and create (guess).

### Dependencies
- allocator: No dependencies (foundation)

## Test Strategy

For the swap test, patch `claimed_numbers` to replace `prds/backlog` with a symlink to a scratch outside directory, then assert the outside directory stays empty.

```
60000-file discovery/ widens the window; a thread polled flock on prds/ and, when held,
renamed prds/backlog to backlog.real and symlinked backlog to an outside directory.
allocate_prd_number.py <repo> probe -> exit 0, printed .../prds/backlog/60000-probe-v1.md
os.listdir(<outside dir>) -> ['60000-probe-v1.md']
```

## Tasks

### Phase 0: Fix
- [ ] Add the two tests; watch them fail - Acceptance: `pytest -k "backlog_symlink or backlog_swapped"` fails on the unmodified script.
- [ ] Change `claim()` to the fd-relative create and add the CHANGELOG line (depends on: previous task) - Acceptance: `pytest -k "backlog_symlink or backlog_swapped"` passes.

## Success Criteria

- `pytest -k "backlog_symlink or backlog_swapped"` passes; the project's full test gate passes.
