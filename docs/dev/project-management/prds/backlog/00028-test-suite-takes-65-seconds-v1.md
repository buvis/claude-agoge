---
lane: solo
design: skip
default_model: sonnet
model_tier_rationale: test-only change; the suite itself proves nothing was lost. Solo lane - no new failing test exists for a fast-track card to start from; the fixtures file escalates the build to the full review
---
# The test suite takes 65 s, nearly four times the 17 s baseline

Source: agoge run 2026-11-15, finding 6 of 14 (MEDIUM, verified, lane peggy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 1 (module-scoped submodule fixture).

## Problem

Three snapshot test files hold nearly all of the suite's time. 83 tests take 0.5-2.7 s each, mostly because each one builds its target repo, and often a submodule, from scratch with several git processes. Release checks and CI get slower with each snapshot test added.

Users hit: the maintainer, on every `dev/bin/release-checks` and CI run.

## Solution

The builders in `snapshot_fixtures.py` (`_build_target`, `_add_submodule`) are plain helpers called per test. Build each shape once per test module and hand each test a private copy:

1. Add module-scoped pytest fixtures (in a `conftest.py` beside the tests, or in `snapshot_fixtures.py`) that build a plain target and a target with a submodule once under `tmp_path_factory`.
2. Add helpers that `shutil.copytree(template, tmp_path / "target", symlinks=True)` and return `(target, env)` in the shape `_build_target` returns today.
3. Switch call sites in the three test files to the copy helpers. Leave a test on the per-test builder when it needs something a copy cannot give, and say why in a comment.

Every test still works on its own tree, so no state is shared between tests. Tests keep spawning the script as a process: that isolation is the reason option 2 (in-process `main`) was not chosen.

## Requirements

### Must have
- The same tests run: the pass and skip counts equal the baseline the first task records (it was `241 passed, 2 skipped` on macOS when this PRD was written; earlier PRDs in the batch add tests). No test is added, deleted, skipped or weakened.
- No test reads or writes the module-scoped template tree after it is built; each test works on a copy.
- The suite's wall time under `dev/bin/release-checks` drops from the 65 s measured in the run. The implementer reports the new number with `--durations=15`. Target: under 40 s. That target is a guess; the python child processes each test spawns stay.
- No CHANGELOG entry (test-only change).

### Nice to have
- None.

## Implementation

### Module: snapshot test fixtures
- **Location**: `skills/run-agoge/scripts/snapshot_fixtures.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`, `skills/run-agoge/scripts/test_target_snapshot_programs.py`, optionally a new `skills/run-agoge/scripts/conftest.py`
- **Responsibility**: build each repo shape once per module and copy it per test.
- **Exports**: the copy helpers
- **Risk**: a copied repo keeps the template's absolute paths where git stored them (the submodule `url` in `.git/config`). A test that asserts on such a path, or that edits the submodule source repo, must stay on the per-test builder. A copied tree also carries the template's mtimes, which can change what `git status` refreshes.

### Dependencies
- snapshot test fixtures: No dependencies (foundation)

## Test Strategy

The suite is its own regression check: the pass and skip counts must match, and each converted test must still fail for its original reason. Spot-check that by reverting one fix locally (for example the chunked hash from PRD 00019) and confirming its test still fails.

Reproduction from the run:

```
uv run ... python -m pytest -q -rs -p no:cacheprovider --durations=15: 241 passed, 2 skipped in 65.05 s.
The other seven files (158 tests) take 1.77 s.
Per file alone: 14.9 s, 20.3 s, 23.5 s.
83 tests take 0.5-2.7 s, mostly submodule fixtures spawning several processes.
```

## Tasks

### Phase 0: Speed up
- [ ] Record the baseline: run `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs -p no:cacheprovider --durations=15` - Acceptance: wall time and pass/skip counts noted in the commit message of the next task (this task changes no file).
- [ ] Add the module-scoped template fixtures and the copy helpers (depends on: previous task) - Acceptance: one converted test passes on a copied tree.
- [ ] Convert call sites in the three test files (depends on: previous task) - Acceptance: pass and skip counts equal the baseline; wall time is lower than the baseline and reported.

## Success Criteria

- `dev/bin/release-checks` passes with the baseline's pass and skip counts, in less wall time than the baseline run on the same machine.
