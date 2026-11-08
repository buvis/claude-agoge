# Two PRD claims made at the same time with different slugs get the same number

Source: agoge run 2026-11-08, finding 1 of 18 (HIGH, verified, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`allocate_prd_number.py` claims a number with `O_CREAT|O_EXCL` on the full file name `NNNNN-<slug>-v1.md`. Two callers that run at once with different slugs never collide on that name, so both take the same number and exit 0. The allocator exists to keep two writers off one number, and it only does so when the slugs match. Anyone emitting PRDs in parallel (an interactive walk beside an unattended loop) gets duplicate numbers in the backlog.

## Solution

Claim the number itself: create an exclusive marker `backlog/.NNNNN.claim` with `O_CREAT|O_EXCL` first; on `FileExistsError`, move to the next number. Only the holder of the marker creates `NNNNN-<slug>-v1.md`. The scan treats marker files as taken numbers.

## Requirements

### Must have
- N processes started together with distinct slugs get N distinct numbers.
- A leftover marker (crash between marker and file) counts as a taken number; the next caller skips it.
- The existing sequential and same-slug behaviour is unchanged.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: concurrent PRD claims with different slugs get distinct numbers`.

## Implementation

- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `CHANGELOG.md`
- **Risk**: one hidden marker file per number in `backlog/`. A crash leaves a stale marker that skips a number, which is harmless.

## Test Strategy

Regression test: start N (for example 16) processes behind a barrier with distinct slugs, assert N distinct numbers. It must fail on the current script. Reproduction from the run:

```
16 callers via runpy.run_path(allocate_prd_number.py), slugs s0..s15, 10 trials:
distinct 0 ok 16 distinct 9 dups {'00001': 5, '00006': 2, '00003': 3}
backlog: 00001-s0-v1.md 00001-s1-v1.md 00001-s12-v1.md 00001-s4-v1.md 00001-s9-v1.md ...
two callers (alpha, beta): same number in 19 of 20 trials
same-slug callers: distinct in 10 of 10 trials
```

## Tasks

- [ ] Add the parallel distinct-slug test; watch it fail on the unmodified script.
- [ ] Implement the number marker claim; the scan counts markers as taken.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- The parallel test passes in 10 of 10 runs; the full suite passes under `dev/bin/release-checks`.
