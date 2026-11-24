---
prd: docs/dev/project-management/prds/wip/00028-test-suite-takes-65-seconds-v1.md
review: 2
date: 2026-11-25
head_sha: bbfa47fdcca6b66380b529f036202fad9d86954d
codex_thread_id: 01a20fd5-c4ce-7982-bfe7-2a62569c75e9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 34349c15
  carl: 20b37bd9
---

# Review: 00028-test-suite-takes-65-seconds-v1

Diff range: `b60de139af832b6b69d431d0bc0f581c9193586b..bbfa47fdcca6b66380b529f036202fad9d86954d`

codex_rung_guard: not fired

## Review Summary

Reviewed: 5 completed tasks (incremental review of the cycle-1 rework)
PRDs checked: 00028-test-suite-takes-65-seconds-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, native Claude subagent, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens + de-slop, codex, resumed thread 01a20fd5)
- Carl: ✅ Available (UI/design lens, gemini via copilot backend, exit 0)

Context pack: ok. Mechanical test checks: 0 tautological-shape lines; the
fail-first replay reports 1 touched test passing against the pre-change code
(absorbed into R5 below). The test gate produced exit 0 with no parseable
summary through `dev/bin/release-checks`, so the suite was re-run this cycle
through `autopilot verify`; its own parser also returned no counts, and the
counts below are read from its log (`docs/dev/tmp/gate-bbfa47f.log`).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | R1's second site is untouched. `test_untouched_linked_worktree_and_submodule_compare_unchanged` still copies `template_target` and then calls `_add_submodule` per test (about 1.2 s). It has no stay-on-builder comment. The PRD requires one ("say why in a comment"). R1's fix task and the settled-decision text both promised to convert it or record why it cannot be, and the diff's one-hunk change to the state file only touched line 394. Fix: copy `template_target_with_submodule` and then run `git worktree add --detach`, or, if the worktree-before-submodule order matters, add a comment saying why. | skills/run-agoge/scripts/test_target_snapshot_state.py:430 | 5 | ALICE, BOB, CARL |
| R2 | [1/4] | 🟡 | Task 4 adds a comment to `_source_submodule`, but the callers can select a template from `source` before dispatch. All three submodule filter cases still build a submodule per case. | skills/run-agoge/scripts/test_target_snapshot_programs.py:226 | 4 | BOB |
| R3 | [1/4] | ⚪ | Wall-time gain is small. The 40 s target is unmet and the drop is near noise: the implementer's own numbers are 53.67 s to 49.91 s (c3d1956), against the 65 s figure in the PRD. The PRD calls 40 s "a guess" and requires only that time drops, so this is a deviation from the target, not a breach of the must-have. One file alone (test_target_snapshot_programs.py, 28 tests) took 19.24 s here, and its slowest tests are still submodule-shaped at about 1 s each. | skills/run-agoge/scripts/conftest.py:6 | 3 | BLAKE |
| R4 | [1/4] | ⚪ | The baseline wall time and counts are not in the commit message of the next task (c5f644c, T2) as the Phase 0 task 1 acceptance requires. They appear in the T3 message (c3d1956: 254 passed, 2 skipped, 53.67 s to 49.91 s). The data exists but not where the PRD says. | N/A | 1 | BLAKE |
| R5 | [2/4] | 🟡 | test_every_gitdir_entry_is_checked_or_listed was rewritten from `assert A or B` to `if B: continue; assert A`. The two forms are logically equivalent, so the test is not weakened. It is an edit beyond a pure fixture swap, though, and no PRD task asks for it. The fail-first replay reports this same test passing against the pre-change code. | skills/run-agoge/scripts/test_target_snapshot_state.py:394 | 3 | BLAKE, mech-check |
| R6 | [1/4] | ⚪ | Nothing prevents a test from mutating the module-scoped templates. Every call site goes through `_copy_target`, which uses `copytree(symlinks=True)` into `tmp_path`. This holds today and is not enforced. | skills/run-agoge/scripts/snapshot_fixtures.py:72 | 2 | BLAKE |
| R7 | [1/4] | ⚪ | Both dispatch logs record two successful completions with different elapsed times for each cycle-1 reviewer dispatch. Verify that the metrics summary counts each dispatch once and uses the intended duration. | docs/dev/project-management/autopilot/dispatch-metrics.jsonl:660 | general | BOB |

Mechanical absorption: the one `[MECH]` fail-first replay line names
`test_every_gitdir_entry_is_checked_or_listed` in
`skills/run-agoge/scripts/test_target_snapshot_state.py`, the same test and file as
R5, so `mech-check` was appended to that row's finders rather than added as a new
row, and the row carries the mech line's 🟡 severity.

Carry-forward: none — the cycle-1 queue file
`00028-test-suite-takes-65-seconds-v1-checks-1.json` is empty (both of Bob's
cycle-1 VERIFY items were not queued for command shape).

### Auto-dismissed (ledger)

- [BLAKE] ⚪ test_untouched_linked_worktree_and_submodule_compare_unchanged still calls the per-test `_add_submodule` after copying the plain template. The PRD says to leave a test on the per-test builder only with a comment saying why. This one has no comment, unlike skills/run-agoge/scripts/test_target_snapshot_state.py:599 and skills/run-agoge/scripts/test_target_snapshot_programs.py:226. | File: skills/run-agoge/scripts/test_target_snapshot_state.py:430 — Duplicate of R1, whose text names this same site; R1's fix task covers it.

## Alice

- Medium: R1's second site is untouched — `test_untouched_linked_worktree_and_submodule_compare_unchanged` (`skills/run-agoge/scripts/test_target_snapshot_state.py:430`) still copies `template_target` and calls `_add_submodule` per test, with no stay-on-builder comment.

Prior findings she verified as resolved: R10 (the `or` hedge at
`test_target_snapshot_state.py:394` — the new `if top in GITDIR_UNCHECKED: continue`
plus a named assertion message keeps the invariant and still fails when a git-dir
file is neither snapshotted nor listed) and R1's `_source_submodule` site
(`test_target_snapshot_programs.py:226` — the stay-on-builder comment now states the
reason). No regression from the rework. She ran the two touched state tests: 2 passed.

Rubric verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass,
R9 fail, R10 pass, R11 pass, R12 pass, R13 pass.

## Blake

- Low: Wall-time gain is small (53.67 s → 49.91 s against the 65 s baseline; the 40 s target is a stated guess).
- Low: The linked-worktree test still calls the per-test `_add_submodule` with no comment saying why.
- Low: The baseline numbers are in the T3 commit message, not the T2 one the task's acceptance names.
- Low: `test_every_gitdir_entry_is_checked_or_listed` was rewritten beyond a pure fixture swap; the two forms are logically equivalent.
- Low: Nothing structurally prevents a test from mutating the module-scoped templates; no call site does today.

Verified as compliant: the two module-scoped fixtures sit in
`skills/run-agoge/scripts/conftest.py`; `_copy_target` returns `_build_target`'s
shape and uses `copytree(symlinks=True)`; all three test files are converted, the
per-test builder remaining only at the two commented sites plus the uncommented
linked-worktree case; `--collect-only` shows 256 tests, matching 254 passed + 2
skipped; no CHANGELOG change, no new dependency, no production code touched.
Not verified: the Test Strategy's revert-one-fix spot-check.

Rubric verdicts: B1 pass, B2 pass, B3 pass, B4 fail, B5 pass, B6 pass, B7 pass,
B8 pass, B9 pass, B10 pass, B11 pass, B12 pass, B13 pass, B14 pass, B15 pass,
B16 pass, B17 pass, B18 pass, B19 pass.

## Bob

- Medium: Task 4's comment on `_source_submodule` does not remove the per-case submodule builds; callers can select a template from `source` before dispatch (`skills/run-agoge/scripts/test_target_snapshot_programs.py:226`).
- Medium: The linked-worktree test is neither converted nor documented (`skills/run-agoge/scripts/test_target_snapshot_state.py:430`).
- Low: The cycle-1 dispatch log records two successful completions per reviewer dispatch with different elapsed times; confirm the metrics summary counts each dispatch once.

Consensus rubric verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass,
R8 pass, R9 fail, R10 pass, R11 pass, R12 pass, R13 pass.

FIX:
- Per-case submodule builds in the filter tests — skills/run-agoge/scripts/test_target_snapshot_programs.py:226 — Select the submodule template before dispatch when `source == "submodule"` and configure `target / "sub"` in the handler.
- Unresolved linked-worktree setup exception — skills/run-agoge/scripts/test_target_snapshot_state.py:430 — Copy the submodule template before adding the linked worktree, or document the test invariant that requires the current order.

VERIFY:
- Duplicate dispatch completions — Feed the cycle-1 rows into the dispatch metrics summarizer. Confirm it reports two successful dispatches for the two IDs and uses the duration selected by its duplicate-event rule. (not queued: command shape — no exact runnable command.)

KNOWN:
- (none)

Doubt rubric verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

## Carl

Backend: copilot (`gemini-run.sh`), exit 0.

- Medium: Prior R1 partially unresolved — `test_untouched_linked_worktree_and_submodule_compare_unchanged` still builds the submodule per test instead of using `template_target_with_submodule` (`skills/run-agoge/scripts/test_target_snapshot_state.py:427`).

He also probed the proposed fix directly: copying the submodule template and then
running `git worktree add --detach` produced a clean compare, which is evidence the
conversion is feasible.

Rubric verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass,
R9 fail, R10 pass, R11 pass, R12 pass, R13 pass.

Verdict: 7 findings
Tests: 254 passed, 2 skipped, 0 failed (suite run this cycle)
