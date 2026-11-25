---
lane: solo
design: skip
default_model: sonnet
model_tier_rationale: test-only change; the suite itself proves nothing was lost. The profile task decides which cost to cut, so the work is measure-then-edit, not design
---
# The snapshot tests still take 55 s after PRD 00028

Source: batch `202611232314` review of PRD 00028 (ledger key `08bc95ed41ae`, deferred finding R6, and its duplicate, former hold stub 00042). Triaged 2026-11-25: promoted to backlog.

## Problem

PRD 00028 made tests copy a template repo instead of building one each time. The suite went from 56.99 s to 55.18 s on the same machine, about 3%. The target was under 40 s. The review guessed that the time goes to the python child process each test spawns (`snapshot_fixtures._run`, `test_target_snapshot_state.py:50`), but nobody measured that. Each snapshot run also starts several git processes, which can cost more than the python start.

Users hit: the maintainer, on every `dev/bin/release-checks` and CI run, and every autopilot gate run.

## Solution

1. Profile before you edit. Measure where one slow test spends its time: python interpreter start, imports, git subprocesses inside `target_snapshot.py`, and fixture copying.
2. Cut the largest cost that the measurement shows, and keep test isolation. Examples: run `target_snapshot.main()` in-process for tests that do not depend on process-level state (env, cwd, signals, exit codes), share read-only snapshots inside one test, or drop git calls that give the same answer twice.
3. Keep any test that needs a real process boundary on the subprocess path. Add a comment that says why.

## Requirements

### Must have
- The first task records the profile in its commit message: the top costs per slow test, with numbers.
- The same tests run: the pass and skip counts equal the baseline that the first task records. No test is added, deleted, skipped, or weakened.
- An in-process test must not leak state to the next test: env, cwd, `sys.argv`, module globals, and `functools` caches (`_is_symlink_escaping`) are reset or isolated.
- Wall time under `dev/bin/release-checks` drops by at least 25% from the baseline on the same machine. Report it with `--durations=15`. If the profile shows that 25% is not reachable without a loss of isolation, stop after the profile task, record the numbers, and close this PRD with that evidence.
- No CHANGELOG entry (test-only change).

### Nice to have
- None.

## Implementation

### Module: snapshot test harness
- **Location**: `skills/run-agoge/scripts/snapshot_fixtures.py`, `skills/run-agoge/scripts/conftest.py`, `skills/run-agoge/scripts/test_target_snapshot*.py`; `skills/run-agoge/scripts/target_snapshot.py` only if the profile shows repeated git calls in it
- **Responsibility**: run the snapshot script under test at the lowest cost that keeps each test isolated.
- **Exports**: none new, unless an in-process runner helper is needed
- **Risk**: an in-process run can hide bugs that only a real process shows (exit codes, stdout encoding, env inheritance). Keep at least one subprocess test per CLI verb.

### Dependencies
- snapshot test harness: No dependencies (foundation)

## Test Strategy

The suite is its own regression check: the pass and skip counts must match. For each converted test, revert one known fix locally (for example the chunked hash from PRD 00019) and confirm that the test still fails.

## Tasks

### Phase 0: Measure
- [ ] Record the baseline and profile one slow test from each snapshot test file (`uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs -p no:cacheprovider --durations=15`, plus `python -X importtime` or `cProfile` on one run) - Acceptance: wall time, pass/skip counts, and the top three costs are in the commit message of the next task (this task changes no file).

### Phase 1: Cut
- [ ] Remove the largest measured cost while each test keeps its own state (depends on: previous task) - Acceptance: pass and skip counts equal the baseline; wall time is at least 25% lower and reported.

## Success Criteria

- `dev/bin/release-checks` passes with the baseline's pass and skip counts, in at least 25% less wall time than the baseline run on the same machine, or the PRD is closed with the profile that shows why not.
