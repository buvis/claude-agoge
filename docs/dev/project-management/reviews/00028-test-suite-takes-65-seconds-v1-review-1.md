---
prd: docs/dev/project-management/prds/wip/00028-test-suite-takes-65-seconds-v1.md
review: 1
date: 2026-11-25
head_sha: b60de139af832b6b69d431d0bc0f581c9193586b
codex_thread_id: 01a20fd5-c4ce-7982-bfe7-2a62569c75e9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 0ced8c39
  carl: d68be853
---

# Review: 00028-test-suite-takes-65-seconds-v1

Diff range: `d188630e7fbccacb1e9a6fef5fcb0da39fb7eaec..b60de139af832b6b69d431d0bc0f581c9193586b`

codex_rung_guard: not fired

## Review Summary

Reviewed: 3 completed tasks
PRDs checked: 00028-test-suite-takes-65-seconds-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, native Claude subagent, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens + de-slop, codex)
- Carl: ✅ Available (UI/design lens, gemini via copilot backend)

Context pack: ok. Mechanical test checks: 1 tautological-shape line (absorbed below);
fail-first replay collected 0 touched tests at base (the three test files cannot be
collected at `d188630e7fbc` because the new template fixtures do not exist there).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | Two sites still use the per-test builder with no comment saying why, which the PRD requires ("say why in a comment"). `_source_submodule` calls `_add_submodule` per test, which costs about 1.2 s in each of the three parametrized cases that use it. `test_untouched_linked_worktree_and_submodule_compare_unchanged` copies `template_target` and then adds a submodule per test. Convert the second test to `template_target_with_submodule` plus the worktree add. For the first, either take the submodule template or add a comment giving the reason it can't. | skills/run-agoge/scripts/test_target_snapshot_programs.py:226 | 3 | ALICE, BLAKE, BOB |
| R2 | [3/4] | 🟡 | `test_target_snapshot.py` is 809 lines, over the 800-line cap. The cap was already flagged in the 00027 review, and this diff leaves the count unchanged, so the file stays over. Split the file or move tests out. | skills/run-agoge/scripts/test_target_snapshot.py:809 | general | ALICE, BOB, CARL |
| R3 | [2/4] | 🟡 | The baseline numbers are missing from the T2 commit message. Task 1 says the baseline must be noted in the next task's commit message. c5f644c has no wall time or pass/skip counts. They appear only in the T3 message (53.67 s, 254 passed, 2 skipped). | N/A | 1 | BLAKE, BOB |
| R4 | [2/4] | ⚪ | The wall-time target is not met on this run: the suite took 54.9 s against the 65 s baseline, and the PRD target is under 40 s. The PRD calls the target a guess and requires only that the time drops, so this is not a defect. Confirm the implementer reported `--durations=15` output and the baseline counts in the T3 commit message. | N/A | 3 | ALICE, BLAKE |
| R5 | [2/4] | ⚪ | The fail-first replay could not collect the three touched test files at the base commit, because the `template_target` fixtures do not exist there. The converted tests therefore have no evidence that they still fail for their original reasons. Run the PRD's spot-check of reverting one fix, for example the chunked hash from PRD 00019. | N/A | general | ALICE, BLAKE |
| R6 | [1/4] | 🟠 | Wall-time goal is not met in substance. Blake ran all three snapshot test files (254 passed, 2 skipped) at HEAD and at c5f644c~1, on the same machine, back to back. HEAD took 55.18 s and the pre-change tree took 56.99 s, a gain of about 3%, which is noise level. The PRD target is under 40 s. The implementer's own numbers are 53.67 s to 49.91 s (7%). The "wall time drops" criterion is met only nominally. The PRD calls the 40 s target "a guess", but the Problem statement says the cost is per-test repo building. The measured result suggests the time is dominated elsewhere, probably the python child process each test spawns, so the fix barely addresses the stated problem. | skills/run-agoge/scripts/conftest.py:6 | 3 | BLAKE |
| R7 | [1/4] | 🟡 | The same gap in the state file: the per-test `_add_submodule` call has no stay-on-builder comment, and no `template_target_with_submodule` fixture is used there. | skills/run-agoge/scripts/test_target_snapshot_state.py:428 | 3 | ALICE |
| R8 | [1/4] | 🟡 | `_big_file_target` still builds a plain repo per test. The large file setup works on a copy, so the comment about its cost does not establish the PRD's exception. Pass in the plain template and keep the large file setup local. | skills/run-agoge/scripts/test_target_snapshot_state.py:597 | 3 | BOB |
| R9 | [1/4] | 🟡 | The mechanical check flags the existing either-or assertion. An entry under a category in `GITDIR_UNCHECKED` can be absent from the snapshot and still pass. | skills/run-agoge/scripts/test_target_snapshot_state.py:394 | general | BOB |
| R10 | [2/4] | 🟡 | test_every_gitdir_entry_is_checked_or_listed hedges with or: either outcome satisfies it | skills/run-agoge/scripts/test_target_snapshot_state.py:394 | general | CARL, mech-check |
| R11 | [1/4] | 🟡 | test_untouched_linked_worktree_and_submodule_compare_unchanged builds submodule from scratch instead of using template_target_with_submodule | skills/run-agoge/scripts/test_target_snapshot_state.py:425 | 3 | CARL |
| R12 | [1/4] | ⚪ | The mech-check `or` hedge on `test_every_gitdir_entry_is_checked_or_listed` (`rel in gitdir or top in GITDIR_UNCHECKED`) is a real "checked or listed" membership invariant, not a tautology. The test existed before this diff and was only switched to the copy helper. Leave it as is, or add a comment saying the `or` is the invariant. | skills/run-agoge/scripts/test_target_snapshot_state.py:394 | 3 | ALICE |
| R13 | [1/4] | ⚪ | The linked-worktree test still builds a submodule per test and gives no reason for the exception. Document why the worktree must be created before the submodule, if that order is part of the test. | skills/run-agoge/scripts/test_target_snapshot_state.py:425 | 3 | BOB |
| R14 | [1/4] | ⚪ | The replay collected zero tests, so it provides no evidence that a converted test still detects its original regression. | skills/run-agoge/scripts/test_target_snapshot_state.py:565 | 3 | BOB |

Mechanical absorption: the one `[MECH]` tautological-shape line names
`test_every_gitdir_entry_is_checked_or_listed` at
`skills/run-agoge/scripts/test_target_snapshot_state.py:394`, the same test and file as
R10, so `mech-check` was appended to that row's finders rather than added as a new row.

Carry-forward: none (cycle 1 has no prior queue file).

## Alice

- Medium: Two per-test builder sites carry no "why" comment, which the PRD requires: `_source_submodule` (`skills/run-agoge/scripts/test_target_snapshot_programs.py:226`) and the linked-worktree test (`skills/run-agoge/scripts/test_target_snapshot_state.py:428`).
- Medium: `test_target_snapshot.py` is 809 lines, over the 800-line cap.
- Low: The `or` hedge at `test_target_snapshot_state.py:394` is a real membership invariant, not a tautology.
- Low: Wall time on her run was 54.9 s against the 65 s baseline; the PRD's under-40 s figure is a stated guess and only "time drops" is required.
- Low: The fail-first replay could not collect the touched tests at base, so the converted tests have no replay evidence.

Her test run: 254 passed, 2 skipped in 54.91 s.

Rubric verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass,
R9 fail, R10 pass, R11 pass, R12 pass, R13 fail.

## Blake

- High: Wall-time goal not met in substance: his same-machine measurement put HEAD at 55.18 s and the pre-change tree at 56.99 s (about 3%, noise level) against a 40 s target.
- Medium: Two per-test builder sites have no explaining comment; only `_big_file_target` carries a rationale comment.
- Low: The baseline numbers are missing from the T2 commit message (they appear only in T3).
- Low: The `--durations=15` table is in neither the repo nor the commit message.
- Low: He did not run the PRD's revert-one-fix spot-check and found no evidence anyone did.

Verified as compliant: pass/skip counts equal the baseline (254 passed, 2 skipped);
no test reads or writes a template directly; `_copy_target` uses
`shutil.copytree(..., symlinks=True)` and returns the `_build_target` shape; the
module-scoped fixtures sit in `skills/run-agoge/scripts/conftest.py`; no CHANGELOG
change in the T2/T3 commits; no new dependencies and no production code changed.

Rubric verdicts: B1 pass, B2 pass, B3 pass, B4 fail, B5 pass, B6 pass, B7 pass,
B8 pass, B9 pass, B10 pass, B11 pass, B12 pass, B13 pass, B14 pass, B15 pass,
B16 fail, B17 pass, B18 pass, B19 pass.

## Bob

- Medium: `_big_file_target` still builds a plain repo per test (`skills/run-agoge/scripts/test_target_snapshot_state.py:597`).
- Medium: The parametrized submodule filter cases still build a submodule per case through `_source_submodule`.
- Medium: The review record omits the same-machine baseline and the `--durations=15` comparison.
- Medium: The mechanical check's either-or assertion at `test_target_snapshot_state.py:394` stands.
- Low: The linked-worktree test still builds a submodule per test with no stated reason.
- Low: The replay collected zero tests, so no converted test is shown to still detect its original regression.
- Low: `test_target_snapshot.py` reaches 809 lines, over the 800-line limit.

Consensus rubric verdicts: R1 pass, R2 fail, R3 pass, R4 pass, R6 pass, R7 pass,
R8 pass, R9 fail, R10 pass, R11 pass, R12 pass, R13 fail.

FIX:
- Per-test plain repo in `_big_file_target` — skills/run-agoge/scripts/test_target_snapshot_state.py:597 — Pass `template_target` into the helper and use `_copy_target`.
- Per-case submodule setup in the filter tests — skills/run-agoge/scripts/test_target_snapshot_programs.py:225 — Select the submodule template for the `submodule` cases and configure the copied checkout.
- Undocumented linked-worktree exception — skills/run-agoge/scripts/test_target_snapshot_state.py:425 — Explain the need to preserve setup order, or use the submodule template if order is immaterial.

VERIFY:
- Baseline and timing evidence — Check the fixture commit message for the recorded baseline, then compare it with the reviewed revision's same-machine pytest run using `-q -rs -p no:cacheprovider --durations=15`, recording pass count, skip count and wall time for both. (not queued: command shape — a multi-revision comparison procedure, not one runnable command.)
- Regression spot-check — Run `test_fingerprint_matches_whole_file_sha256` with tracked-file hashing temporarily limited to its first chunk; confirm the test fails with the mutation and passes after restoring the implementation. (not queued: command shape — requires mutating production code, which is a state change.)

KNOWN:
- Existing either-or assertion — skills/run-agoge/scripts/test_target_snapshot_state.py:394 — The setup change preserves the assertion; changing what the test requires is outside the fixture PRD.
- Existing 809-line test file — skills/run-agoge/scripts/test_target_snapshot.py:809 — Splitting the module is outside the fixture PRD.

Doubt rubric verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

## Carl

Backend: copilot (`gemini-run.sh`), exit 0.

- Medium: `test_every_gitdir_entry_is_checked_or_listed` hedges with `or`: either outcome satisfies it (`skills/run-agoge/scripts/test_target_snapshot_state.py:394`).
- Medium: `test_target_snapshot.py` exceeds the 800-line limit (809 lines).
- Medium: `test_untouched_linked_worktree_and_submodule_compare_unchanged` builds the submodule from scratch instead of using `template_target_with_submodule`.

Rubric verdicts: R1 pass, R2 fail, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass,
R9 pass, R10 pass, R11 pass, R12 pass, R13 fail.

Verdict: 14 findings
Tests: 254 passed, 2 skipped, 0 failed (suite run this cycle)
