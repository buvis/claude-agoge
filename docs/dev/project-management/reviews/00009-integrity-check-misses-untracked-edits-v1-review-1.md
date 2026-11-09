---
prd: docs/dev/project-management/prds/wip/00009-integrity-check-misses-untracked-edits-v1.md
review: 1
date: 2026-11-09
head_sha: 6cc199ea683f685c796f6aeec19e084dd8573b3c
codex_thread_id: 01a1c259-6ffa-78a1-aca9-bdcc2f1563c6
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 74673108
  carl: 72475409
---

# Review: 00009-integrity-check-misses-untracked-edits-v1

Diff range: `2bcf628cf19b94d4af469642a1a651d3e1665052..6cc199ea683f685c796f6aeec19e084dd8573b3c`

codex_rung_guard: not fired

## Review Summary

Reviewed: 5 completed tasks
PRDs checked: 00009-integrity-check-misses-untracked-edits-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, engine: legacy)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (codex, doubt lens D1-D5 + de-slop)
- Carl: ✅ Available (gemini backend: copilot)
- Eve: ⏸️ Disabled (doubt_reviewer is codex and no task was implemented by codex)

Mechanical checks: the context's two `[MECH]` blocks were absorbed into the table
(rows R1, R4 and R6 carry `mech-check` as an extra finder).

Scope: full review (cycle 1), diff staged with `--since 2bcf628`.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | Nothing pins the VERSION bump. `test_previous_version_snapshot_exits_2_with_one_line` computes `target_snapshot.VERSION - 1`, so it passes against the pre-change code (the fail-first replay confirms this) and still passes if `VERSION = 4` is reverted to 3. A real version-3 snapshot has no `untracked_fingerprints` or `ignored` keys, and nothing proves that one is rejected. Add a case that deletes those two keys from a fresh snapshot and sets `version` to 3, or assert `VERSION == 4` | skills/run-agoge/scripts/test_target_snapshot.py:809 | 3 | ALICE, BOB, mech-check |
| R2 | [2/4] | 🟡 | New failure mode with no test. `take_snapshot` now fingerprints every untracked file, so an unreadable untracked file (mode 000, or root-owned) makes `snapshot` and `compare` exit 2 with "unexpected PermissionError". Before this change such a file was only listed by name. Failing closed matches the dirty-tracked-file behaviour, but it is not stated in the PRD, the docstring or SKILL.md, and only the dirty case has a test (`test_unreadable_dirty_file_exits_2_with_one_line`). Add the untracked analogue and say so in the docstring | skills/run-agoge/scripts/target_snapshot.py:209 | 3 | ALICE, BLAKE |
| R3 | [2/4] | ⚪ | The test file is now about 1260 lines, over the 800-line limit. It was already over (about 1010 lines) and this diff adds 250. The limit is breached before and after this diff. Splitting the file (for example moving the untracked and ignored tests into their own module) belongs in a separate PRD | skills/run-agoge/scripts/test_target_snapshot.py:1 | general | ALICE, BOB |
| R4 | [1/4] | 🟡 | Mechanical analysis flags the existing either-or assertion in `test_every_gitdir_entry_is_checked_or_listed`. This assertion is unchanged and concerns the earlier git-directory coverage contract, outside this PRD. | skills/run-agoge/scripts/test_target_snapshot.py:996 | general | BOB, mech-check |
| R5 | [1/4] | ⚪ | The "control" block in `test_previous_version_snapshot_exits_2_with_one_line` does nothing. It rewrites `current-version.json` with the same version and keys, then runs compare twice on identical input. Drop it, or compare `before` once | skills/run-agoge/scripts/test_target_snapshot.py:502 | 3 | ALICE |
| R6 | [1/4] | ⚪ | `test_ignored_fifo_does_not_hang` passes against the pre-change code, so it only guards against regression. It is a PRD-mandated hang guard, so I am not asking for a change. Leave it as it is, since the 10-second timeout is the assertion | skills/run-agoge/scripts/test_target_snapshot.py:408 | 2 | ALICE, mech-check |
| R7 | [1/4] | ⚪ | The `ignored` listing and the fingerprint map grow linearly with the number of ignored or untracked files, for example `node_modules`. The snapshot JSON and the git listing cost scale with that. The PRD accepts the cost and states the risk, so this is only a note. | skills/run-agoge/scripts/target_snapshot.py:193 | general | BLAKE |

No 🔴 Critical and no 🟠 High finding was raised by any lens.

## Alice

Consensus lens, implementation-aware. Five findings (2 medium, 3 low), listed as
R1, R2, R3, R5 and R6 above.

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail

## Blake

Blind lens, PRD-only prompt. Two findings (R2, R7). He verified every PRD
contract item against the code he located himself: the unchanged `untracked`
shape, `untracked_fingerprints` built with the shared `_fingerprint` (special
files and chunked hashing intact), `ignored` as the sorted deduplicated union of
the two `ls-files` listings decoded with `os.fsdecode`, ignored contents never
read, `untracked-modified` and `ignored-removed` both exempted by `--allow` on
exact paths, `VERSION` 3 to 4 with `_load` rejecting other versions, the limit
stated in both the docstring and SKILL.md step 3, and the exact CHANGELOG line.
He ran the narrow selection `-k "untracked or ignored or version"`: 13 passed.
He did not re-run the full suite (test gate supplied) and did not verify the
task-1 fail-first acceptance check. He found no scope creep.

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
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

Doubt lens plus de-slop, codex sandbox (static only).

FIX:
- (medium) The version test passes before this change because every version
  expectation derives from `VERSION`; it does not pin rejection of the actual
  version-3 schema. Add a version-3 fixture without `untracked_fingerprints` and
  `ignored`, then assert exit 2 with one line.
  (skills/run-agoge/scripts/test_target_snapshot.py:809, task 3 - row R1)

VERIFY:
- (none)

KNOWN:
- (medium) Mechanical analysis flags the existing either-or assertion in
  `test_every_gitdir_entry_is_checked_or_listed`. Unchanged, and it concerns the
  earlier git-directory coverage contract, outside this PRD (row R4).
- (low) The test file exceeds the rubric's 800-line limit. It already exceeded it
  before this diff; splitting the established suite is outside this focused
  integrity fix (row R3).

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini lens (backend: copilot). No issues found.

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

## Notes

- The project gate command `dev/bin/release-checks` runs `pytest -q`, whose bare
  `211 passed, 2 skipped in 29.75s` summary the autopilot verification parser
  does not recognise, so `autopilot verify` exits 3 with `counts unavailable`
  while the suite itself is green at exit 0. The counts below are read from that
  run's own log (`docs/dev/tmp/gate-6cc199e.log`). Worth a follow-up in the
  autopilot pack or a `-ra`/`--tb` summary flag here; out of scope for this PRD.
- Consolidation ran through `consolidate_findings.py`; it merged row R3's two
  citations after suffix stripping (`:1` and `:1258`).
- No settled-decisions ledger existed for this PRD at cycle 1, so the two
  `--ledger` flags were omitted.
- No verification-check queue was written: the doubt lens's VERIFY bucket is
  empty.

Verdict: 7 findings
Tests: 211 passed, 2 skipped (suite run this cycle)
