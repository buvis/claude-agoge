# Decision Audit Log: 00009-integrity-check-misses-untracked-edits-v1

PRD: `00009-integrity-check-misses-untracked-edits-v1.md`
Started: 2026-11-09T22:25:11Z
Completed: 2026-11-09T22:25:11Z
Autonomous: 7  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: PRD task 4 bundles docstring, SKILL.md and CHANGELOG edits

**Choice**: docstring limit moved into task 3 (same file as the implementation); SKILL.md and CHANGELOG split into tasks 4 and 5 per the qwen eligibility trigger (preflight healthy); task 2 adds an unreadable-ignored-file test to enforce names-only; task 3 adds an older-version exit-2 test

**Rationale**: keep one file per edit owner and test every Must-have

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: ignored-removed fails a run when running the product deletes an ignored cache file (.pytest_cache lastfailed after a green run, a build clean step)

**Choice**: implement as the PRD specifies; flag at review as a possible follow-up

**Rationale**: PRD mandates the check; finding-contract.md says product-written files are listed, not failed, but does not cover removals

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: Nothing pins the VERSION bump. `test_previous_version_snapshot_exits_2_with_one_line` computes `target_snapshot.VERSION - 1`, so it passes against the pre-change code (the fail-first replay confirms this) and still passes if `VERSION = 4` is reverted to 3. A real version-3 snapshot has no `untracked_fingerprints` or `ignored` keys, and nothing proves that one is rejected. Add a case that deletes those two keys from a fresh snapshot and sets `version` to 3, or assert `VERSION == 4`

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: New failure mode with no test. `take_snapshot` now fingerprints every untracked file, so an unreadable untracked file (mode 000, or root-owned) makes `snapshot` and `compare` exit 2 with "unexpected PermissionError". Before this change such a file was only listed by name. Failing closed matches the dirty-tracked-file behaviour, but it is not stated in the PRD, the docstring or SKILL.md, and only the dirty case has a test (`test_unreadable_dirty_file_exits_2_with_one_line`). Add the untracked analogue and say so in the docstring

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: R1 and R2: the VERSION bump is not pinned by a real version-3 snapshot, and fingerprinting untracked files added an unreadable-untracked-file exit-2 path with no test and no documented limit

**Choice**: auto-fix: swept into tail-sweep tasks 6 and 7 at sonnet

**Rationale**: both are 2-of-4 consensus mediums with additive, bounded fixes (add a test, add a docstring line); cycle 1 converged with no critical or high

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: R3 to R7: the 800-line test-file breach, the pre-existing either-or assertion, a dead control block, the PRD-mandated FIFO hang guard, and the linear cost of the ignored listing

**Choice**: discarded; recorded in docs/dev/project-management/reviews/00009-integrity-check-misses-untracked-edits-v1-ledger.json

**Rationale**: R3 is a pre-existing breach both finders route to its own PRD; R4 to R7 are single-voice medium or low, and two of them explicitly ask for no change

### [autonomous] 2026-11-09T22:25:11Z

**Decision**: dev/bin/release-checks runs pytest -q, whose bare summary line the autopilot verification parser does not recognise, so autopilot verify exits 3 with counts unavailable while the suite is green at exit 0

**Choice**: recorded in the review file Notes; counts read from the gate log; no change made

**Rationale**: out of this PRD's scope; it is a gate-parser or gate-command issue, not a target_snapshot defect
