---
prd: docs/dev/project-management/prds/wip/00005-check-run-leaves-target-unchanged-v1.md
review: 2
date: 2026-11-02
head_sha: 7ca9229f02e87fe317d9c1418c6820dab03b5908
codex_thread_id: 01a19946-92bd-7a11-be80-ee78a9965706
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: skipped (batch-latched unavailable)
dispatch_rows:
  bob: bc3f66ed
  carl: null
---

# Review: 00005-check-run-leaves-target-unchanged-v1 (cycle 2, incremental)

Diff range: `e2bced15a19ac63a13e2ebab1505694474ba12f0..7ca9229f02e87fe317d9c1418c6820dab03b5908`

codex_rung_guard: not fired

carl: skipped (permanently unavailable since cycle 1 of 00005-check-run-leaves-target-unchanged-v1.md)

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/claude-agoge`) - review degraded, not invalid.

Staging note: a previous session of this same cycle staged reviewer inputs at cycle id `202611012245` BEFORE the cycle-1 rework commits (bf18bc9, 192cef1) landed, then died. Those outputs described pre-fix code and were discarded unused. This cycle re-staged from scratch at cycle id `00005c2`.

Build-phase gap carried forward from cycle 1: the step-5.7 per-task reviewer (Pat) was unavailable for the whole build session (sonnet-run.sh OAuth token revoked). Task 8's cycle-1 rework attempt also records `review: failed:oauth_revoked`; task 9 was docs-only. These PRD-level lenses remain the only review those diffs have had.

## Review Summary

Reviewed: 9 completed tasks (incremental scope: the cycle-1 rework commits bf18bc9 and 192cef1)
PRD checked: 00005-check-run-leaves-target-unchanged-v1.md
Reviewers run: Alice (consensus), Blake (blind, PRD-only), Bob (codex doubt lens D1-D5 + de-slop, resumed thread 01a19946)

Prior-cycle resolution: Alice verified cycle-1 findings R1 (os.fsdecode on paths), R2 (compare/snapshot split into separate Bash calls) and R3 (external-symlink ancestor traversal) as resolved in the code, and found no regression from the rework.

Mechanical test checks (computed, not re-judged):
- Tautological test shapes: none found (21 test functions in 1 test file checked).
- Fail-first replay: 1 touched test ran, 1 failed against base, 0 passed. The new symlink regression test does pin this change.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | ⚪ | `_text` (skills/run-agoge/scripts/target_snapshot.py:49) still does a strict `.decode()` on `rev-parse --show-toplevel` (line 86), `for-each-ref` (line 117) and `symbolic-ref` (line 129). A non-UTF-8 repo path or refname would still raise UnicodeDecodeError with exit 1. This is rare and narrower than the settled path-name case. Use `os.fsdecode` in `_text` for consistency | skills/run-agoge/scripts/target_snapshot.py:49 | 8 | ALICE, BLAKE |
| R2 | [1/3] | 🟠 | Prior R1 remains partially unresolved: `_text()` still uses strict UTF-8 decoding. `_resolve_repo()` passes the repository path through it, and `for-each-ref` passes refnames through it. A non-UTF-8 repository directory or refname still causes an uncaught UnicodeDecodeError. Use `os.fsdecode` for these outputs. | skills/run-agoge/scripts/target_snapshot.py:49 | 8 | BOB |
| R3 | [1/3] | 🟡 | The snapshot adds a fingerprint value `external-symlink`. B1 allows only a sha256, `link:<sha>`, `dir` or `absent`. `_external_symlink_ancestor` is a hardening step the PRD never asked for. It changes the snapshot data format and adds behavior beyond the spec. The motive is sound (it stops the script reading outside the repo through a swapped-in symlink), but it is a deviation, and the PRD should absorb it or the code should drop it. | skills/run-agoge/scripts/target_snapshot.py:56 | general | BLAKE |
| R4 | [1/3] | 🟡 | SKILL.md step 3 does not follow B3 item 4. B3 puts compare and snapshot in one bash block. The implementation splits them into two Bash calls and adds a "only on exit 0" gate. This is behaviorally safer, because a shared block would mask the compare's exit code. It is still a verbatim-text deviation from the appendix, and it is not recorded in the PRD. | skills/run-agoge/SKILL.md:148 | general | BLAKE |
| R5 | [1/3] | ⚪ | The first assert in the new symlink test compares `after` to `f" D {sha}"`, which has a leading space and the wrong XY order, since real porcelain output is `D  <fp>`. It can never fail, so only the second assert carries the test. Drop it, or assert `after == "D  external-symlink"` | skills/run-agoge/scripts/test_target_snapshot.py:498 | 8 | ALICE |
| R6 | [1/3] | ⚪ | The new SKILL.md text gates the `lanes.json` snapshot on the compare's exit 0, but says nothing about the snapshot's own exit 2 (skills/run-agoge/SKILL.md:159). The lanes would be dispatched without a baseline. The later lanes compare would fail closed with exit 2, so the run still ends as `unknown`. Add "if it exits 2, dispatch nobody and go to step 7" | skills/run-agoge/SKILL.md:159 | 9 | ALICE |
| R7 | [1/3] | ⚪ | `_fingerprint` opens a dirty tracked path with a plain `open(..., "rb")`. A FIFO or device node swapped in for a tracked file would block the comparison. B1 does not cover this case. | skills/run-agoge/scripts/target_snapshot.py:80 | general | BLAKE |
| R8 | [1/3] | ⚪ | The CHANGELOG entry sits under Unreleased after `### Fixed`. B7 says to insert it "before its `### Changed`", but Unreleased has no `### Changed`. The placement is a reasonable reading of an ambiguous instruction. | CHANGELOG.md:20 | general | BLAKE |

Note: `consolidate_findings.py` merged Alice's and Blake's `_text` rows onto R1 after citation-suffix stripping (`:49` ~ `:48`). Bob's row names the same defect in the same file but did not merge, so R1 and R2 are one defect carried at two severities: two of three reviewers call it low, Bob calls it high. The gate took the higher severity at face value rather than downgrade it (see the decision record), so this cycle does not converge on the severity bar.

## Alice

Prior findings R1, R2 and R3 verified resolved; full suite run in `skills/run-agoge/scripts`: 163 passed, 0 failed, 0 skipped.

- R1 is resolved. `target_snapshot.py:93` now parses `status -z` as bytes and `os.fsdecode`s the paths; likewise worktrees (121), untracked (135) and the rename "from" field (103). Symlink text at 75 uses `os.fsencode`.
- R2 is resolved. `SKILL.md:148` splits compare and snapshot into separate Bash calls, snapshot gated "only on exit 0". The wiring test still passes.
- R3 is resolved. `_external_symlink_ancestor` (56) checks each directory component with a realpath/commonpath test against the already-realpath'd repo; `_fingerprint` returns the `external-symlink` marker without opening the file. An in-repo symlink is still followed; a symlink as final component is not followed.

Findings:

[ALICE] ⚪ The first assert in the new symlink test compares `after` to `f" D {sha}"`, which has a leading space and the wrong XY order, since real porcelain output is `D  <fp>`. It can never fail, so only the second assert carries the test. Drop it, or assert `after == "D  external-symlink"` | File: skills/run-agoge/scripts/test_target_snapshot.py:498 | Task: 8
[ALICE] ⚪ `_text` (skills/run-agoge/scripts/target_snapshot.py:49) still does a strict `.decode()` on `rev-parse --show-toplevel` (line 86), `for-each-ref` (line 117) and `symbolic-ref` (line 129). A non-UTF-8 repo path or refname would still raise UnicodeDecodeError with exit 1. This is rare and narrower than the settled path-name case. Use `os.fsdecode` in `_text` for consistency | File: skills/run-agoge/scripts/target_snapshot.py:49 | Task: 8
[ALICE] ⚪ The new SKILL.md text gates the `lanes.json` snapshot on the compare's exit 0, but says nothing about the snapshot's own exit 2 (skills/run-agoge/SKILL.md:159). The lanes would be dispatched without a baseline. The later lanes compare would fail closed with exit 2, so the run still ends as `unknown`. Add "if it exits 2, dispatch nobody and go to step 7" | File: skills/run-agoge/SKILL.md:159 | Task: 9

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

[BLAKE] 🟡 The snapshot adds a fingerprint value `external-symlink`. B1 allows only a sha256, `link:<sha>`, `dir` or `absent`. `_external_symlink_ancestor` is a hardening step the PRD never asked for. It changes the snapshot data format and adds behavior beyond the spec. The motive is sound (it stops the script reading outside the repo through a swapped-in symlink), but it is a deviation, and the PRD should absorb it or the code should drop it. | File: skills/run-agoge/scripts/target_snapshot.py:56 | Task: general
[BLAKE] 🟡 SKILL.md step 3 does not follow B3 item 4. B3 puts compare and snapshot in one bash block. The implementation splits them into two Bash calls and adds a "only on exit 0" gate. This is behaviorally safer, because a shared block would mask the compare's exit code. It is still a verbatim-text deviation from the appendix, and it is not recorded in the PRD. | File: skills/run-agoge/SKILL.md:148 | Task: general
[BLAKE] ⚪ `_text()` uses a strict `.decode()` on `symbolic-ref` and `for-each-ref` output, while B1 asks for os.fsdecode on paths. A ref or branch name that is not UTF-8 would raise an uncaught UnicodeDecodeError. The script would then exit 1 with a traceback, not 2 with a `target_snapshot: ` line. The failure is closed, but it breaks the exit-code contract. I could not reproduce it: macOS rejects non-UTF-8 ref names. | File: skills/run-agoge/scripts/target_snapshot.py:48 | Task: general
[BLAKE] ⚪ `_fingerprint` opens a dirty tracked path with a plain `open(..., "rb")`. A FIFO or device node swapped in for a tracked file would block the comparison. B1 does not cover this case. | File: skills/run-agoge/scripts/target_snapshot.py:80 | Task: general
[BLAKE] ⚪ The CHANGELOG entry sits under Unreleased after `### Fixed`. B7 says to insert it "before its `### Changed`", but Unreleased has no `### Changed`. The placement is a reasonable reading of an ambiguous instruction. | File: CHANGELOG.md:20 | Task: general

Checked and conforming: B1's snapshot keys, `--no-optional-locks` on every git call, rename/copy suffix on `dirty`, unborn-HEAD exit 2, the refusal to write inside the repo, the cross-repo snapshot rejection, exit codes 0/1/2 and the `target_snapshot: ` stderr prefix; B2's violation kinds and order, the single `ref` violation for a moved current branch, the remote-URL-free `config` violation, `--allow` scoping and shell-quoted `restore` forms; every SKILL.md, finding-contract.md, README.md and CHANGELOG.md edit the PRD lists. Tests cover every PRD-listed case (37 passed across the four test files he ran). He did not run `dev/bin/release-checks`.

B1: pass
B2: fail
B3: pass
B4: pass
B5: pass
B6: fail
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

FIX:
- [BOB] 🟠 Prior R1 remains partially unresolved: `_text()` still uses strict UTF-8 decoding. `_resolve_repo()` passes the repository path through it, and `for-each-ref` passes refnames through it. A non-UTF-8 repository directory or refname still causes an uncaught UnicodeDecodeError. Use `os.fsdecode` for these outputs. | File: skills/run-agoge/scripts/target_snapshot.py:49 | Task: 8

VERIFY:
- (none)

KNOWN:
- (none)

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: 8 findings
Tests: 163 passed, 0 failed, 0 skipped (suite run this cycle)
