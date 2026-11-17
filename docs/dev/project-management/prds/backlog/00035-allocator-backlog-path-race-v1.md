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

`claim()` keeps its `(repo, slug)` signature: the existing tests call it directly. `resolved_backlog` is `os.path.realpath(backlog)`, taken inside `claim()` after the open, and it must lie under `os.path.realpath(repo)`; without that the identity check compares the fd with a path that follows the same swapped link. `claim()` refuses by raising `SystemExit(f"{backlog} resolves outside {repo}")`; `main` already prints a string `SystemExit` as `allocate_prd_number: ...` with exit 2.

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
- **Risk**: `O_NOFOLLOW` fails where `backlog` is a symlink that stays inside the repo; that case now exits 2 (it was allowed). The swap test patches `claimed_numbers`, which runs between the open and the create (see Test Strategy).

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
- [ ] Add `test_claim_rejects_backlog_symlink_at_claim_time` (`prds/backlog` is a symlink to a directory outside the repo: `claim(repo, slug)` raises `SystemExit` whose text contains `resolves outside`, and the outside directory stays empty) and `test_claim_does_not_follow_backlog_swapped_after_check` (`monkeypatch` `allocate_prd_number.claimed_numbers` so that, when called, it renames `prds/backlog` to `backlog.real`, makes `prds/backlog` a symlink to an outside directory, then returns the real result: after `claim(repo, slug)` the outside directory is empty) - Acceptance: `pytest -k "backlog_symlink or backlog_swapped"` fails on the unmodified script.
- [ ] In `claim()`, keeping the `(repo, slug)` signature: after `mkdir`, open the backlog once with `os.open(backlog, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)`; raise `SystemExit(f"{backlog} resolves outside {repo}")` when that open fails with `ELOOP` or `ENOTDIR`, when `os.path.realpath(backlog)` is not under `os.path.realpath(repo)`, or when `os.fstat` of the fd and `os.stat` of that real path are not the same directory (`st_dev` and `st_ino`); create each candidate with `os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644, dir_fd=backlog_fd)`; return the same `<backlog>/<NNNNN>-<slug>-v1.md` path as today (depends on: previous task) - Acceptance: `pytest -k "backlog_symlink or backlog_swapped"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer writes outside the repo if the backlog path is swapped" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "backlog_symlink or backlog_swapped"` passes; the full suite passes under `dev/bin/release-checks`.
