---
design: skip
default_model: opus
model_tier_rationale: concurrency - interleaving decides correctness; the lock scope must be exact
---
# Two PRD claims made at the same time with different slugs get the same number

Source: agoge run 2026-11-08, finding 1 of 18 (HIGH, verified, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` claims a number with `O_CREAT|O_EXCL` on the full file name `NNNNN-<slug>-v1.md`. Two callers that run at once with different slugs never collide on that name, so both take the same number and exit 0. The allocator exists to keep two writers off one number, and it only does so when the slugs match. Anyone emitting PRDs in parallel (an interactive walk beside an unattended loop) gets duplicate numbers in the backlog.

## Solution

Serialize scan and create: in `claim`, after `mkdir` of the backlog, open the `docs/dev/project-management/prds` directory itself (`os.open(prds, os.O_RDONLY)`) and hold `fcntl.flock(fd, fcntl.LOCK_EX)` around the `claimed_numbers` scan and the exclusive create; release and close the fd in a `finally`. Locking the directory leaves no lock or marker file in the target repo. Keep the `O_CREAT|O_EXCL` create as a second guard.

## Requirements

### Must have
- N processes started together with distinct slugs get N distinct numbers.
- No file other than the claimed PRD file is created in the target repo.
- The existing sequential and same-slug behaviour is unchanged.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: concurrent PRD claims with different slugs get distinct numbers`.

### Nice to have
- None.

## Implementation

### Module: allocator
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Responsibility**: claim the next free PRD number under an exclusive `flock` on the `prds` directory.
- **Exports**: `claim()` (behaviour change only)
- New symbols: `test_parallel_distinct_slugs_get_distinct_numbers`
- **Risk**: `fcntl` is POSIX-only (macOS and Linux, the supported platforms). A crashed holder releases the lock when its fd closes.

### Dependencies
- allocator: No dependencies (foundation)

## Test Strategy

Regression test: start 16 processes behind a `multiprocessing.Barrier` with distinct slugs, assert 16 distinct numbers. It must fail on the current script. Reproduction from the run:

```
16 callers via runpy.run_path(allocate_prd_number.py), slugs s0..s15, 10 trials:
distinct 0 ok 16 distinct 9 dups {'00001': 5, '00006': 2, '00003': 3}
backlog: 00001-s0-v1.md 00001-s1-v1.md 00001-s12-v1.md 00001-s4-v1.md 00001-s9-v1.md ...
two callers (alpha, beta): same number in 19 of 20 trials
same-slug callers: distinct in 10 of 10 trials
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_parallel_distinct_slugs_get_distinct_numbers` (16 processes, barrier, distinct slugs) - Acceptance: run 5 times against the unmodified script, `pytest -k parallel_distinct_slugs` fails at least once.
- [ ] Wrap scan and create in `flock` on the `prds` directory (depends on: previous task) - Acceptance: `pytest -k parallel_distinct_slugs` passes 10 of 10 runs; after the test the `prds` tree holds only the 16 PRD files.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "concurrent PRD claims with different slugs get distinct numbers" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `test_parallel_distinct_slugs_get_distinct_numbers` passes 10 of 10 runs; the full suite passes under `dev/bin/release-checks`.
