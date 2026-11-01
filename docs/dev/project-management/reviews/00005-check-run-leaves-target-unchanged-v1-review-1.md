---
prd: docs/dev/project-management/prds/wip/00005-check-run-leaves-target-unchanged-v1.md
review: 1
date: 2026-11-01
head_sha: e2bced15a19ac63a13e2ebab1505694474ba12f0
codex_thread_id: 01a19946-92bd-7a11-be80-ee78a9965706
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: permanently unavailable
dispatch_rows:
  bob: ebc94bda
  carl: d68c5a21
---

# Review: 00005-check-run-leaves-target-unchanged-v1

Diff range: `80ce7a5c68082f4b6b10fd9a1232c82c1df840b5..e2bced15a19ac63a13e2ebab1505694474ba12f0`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/claude-agoge`) - review degraded, not invalid.

Carl: permanently unavailable (gemini-run backend=copilot model=gemini-3.8-flash; "copilot authentication failed (permanent; no fallback)" - GitHub token invalid/expired). Latched for batch 202611012029; no UI lens this cycle.

Build-phase gap carried into this review: the step-5.7 per-task reviewer (Pat) was unavailable for the whole build session (sonnet-run.sh OAuth token revoked), so tasks 2, 4 and 5 carry `review: "failed:oauth_token_revoked"`. These PRD-level lenses are the only review those three diffs have had; the reviewers were told so.

## Review Summary

Reviewed: 7 completed tasks
PRD checked: 00005-check-run-leaves-target-unchanged-v1.md
Reviewers run: Alice (consensus), Blake (blind, PRD-only), Bob (codex doubt lens D1-D5 + de-slop)

Mechanical test checks (computed, not re-judged):
- Tautological test shapes: none found (26 test functions in 2 test files checked).
- Fail-first replay: skipped (runner produced no results - exit 4: `file or directory not found: skills/run-agoge/scripts/test_run_integrity.py`, because that test file does not exist at the pre-change base). No replay findings available this cycle.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟠 | PRD requires paths decoded with os.fsdecode, but the script uses strict `.decode()` on git output (`_text`, `_dirty` fields, worktrees, untracked) and `os.readlink(...).encode()` in `_fingerprint`. A non-UTF-8 file name in the target (valid on Linux) raises UnicodeDecodeError/UnicodeEncodeError. That is an uncaught traceback with exit 1, which the skill reads as "changed", not the "one stderr line, no traceback" contract. Use `os.fsdecode`/`os.fsencode` throughout (not run here: macOS rejects non-UTF-8 names, so this is from reading the code) | skills/run-agoge/scripts/target_snapshot.py:49 | 2 | ALICE, BLAKE, BOB |
| R2 | [2/3] | 🟠 | SKILL.md puts `compare ... start.json` and `snapshot ... lanes.json` in one bash block. The Bash tool reports only the last command's exit status, so the compare's exit 1 or 2 is masked by the snapshot's exit 0. The skill's own rule ("if it exits 1 or 2, dispatch nobody") then depends on the master reading stdout or stderr instead of an exit code. After a failed compare the snapshot still runs and writes `lanes.json`. Split into two separate bash calls, or say the compare's exit code must be captured before the snapshot runs. The text is PRD-verbatim, so this is a PRD defect carried into the skill | skills/run-agoge/SKILL.md:148 | 4 | ALICE, BOB |
| R3 | [1/3] | 🟠 | Fingerprinting follows symlinked parent directories outside the target. Replacing a tracked directory with an external symlink makes its deleted tracked children resolve outside the repository. Check ancestor components before opening files and reject external traversal; add this regression. | skills/run-agoge/scripts/target_snapshot.py:57 | 2 | BOB |
| R4 | [1/3] | 🟡 | Untested new branches in `_dirty` and `_fingerprint`: the rename/copy `" from <old path>"` suffix (I confirmed by hand that it works), the `absent` fingerprint for a deleted tracked file, the `link:` fingerprint for a symlink, the `dir` fingerprint, snapshotting a detached HEAD, and the `<out.json>` write-failure exit 2. The tests cover only the PRD-listed cases, which leaves these spec'd behaviors unpinned. Add a rename test, a deleted-file test and a symlink test | skills/run-agoge/scripts/test_target_snapshot.py:1 | 1 | ALICE |
| R5 | [1/3] | 🟡 | `--allow` values are compared as raw strings against git's repo-relative paths. `./docs/...`, a trailing slash or an absolute path silently fail to exempt, and a profile write then fails the run. The skill passes canonical paths, so this is latent. Optionally normalize with `os.path.normpath`, or reject non-relative values with exit 2 | skills/run-agoge/scripts/target_snapshot.py:201 | 2 | ALICE |
| R6 | [1/3] | 🟡 | Filesystem errors during fingerprinting escape as tracebacks because `main` catches only `Fail`. An unreadable tracked file therefore violates the exit-2 contract. Convert fingerprint read errors into `Fail` and test empty stdout plus one prefixed stderr line. | skills/run-agoge/scripts/target_snapshot.py:64 | 2 | BOB |
| R7 | [1/3] | 🟡 | The runtime sidecar contract omits the design's explicit merge rules: nullable lane comparison, zero contributions from exit-2 calls, and a deduplicated union of touched paths. Add these rules so report generation preserves recon artifacts and handles early failure consistently. | skills/run-agoge/references/finding-contract.md:252 | 5 | BOB |
| R8 | [1/3] | ⚪ | `test_run_integrity.py` carries about 70 lines of regex and shell-parsing machinery (`_commands`, `_invocation`, `_sentence`, `_WORD`, `_SCRIPT`) to pin prose. It is heavy for the checks it does and brittle to harmless rewording, for example the `\bcompar` count == 1 assertion in step 6. Consider simpler substring and order assertions | skills/run-agoge/scripts/test_run_integrity.py:1113 | 3 | ALICE |
| R9 | [1/3] | ⚪ | `_env_for` is defined in `test_target_snapshot.py` and also imported from `test_scratch_contract.py` in `test_run_integrity.py`. That makes two copies of the same helper, and the cross-test-module import relies on pytest's prepend import mode. Share one helper (for example a conftest) | skills/run-agoge/scripts/test_target_snapshot.py:1332 | 3 | ALICE |
| R10 | [1/3] | ⚪ | The `touched` union and de-duplication across both comparisons, and the `status` derivation when `compare_lanes` never ran, are specified only in the design doc. The contract text in finding-contract.md says only "the comparisons' own". A master following the contract alone may duplicate or drop paths | skills/run-agoge/references/finding-contract.md:250 | 5 | ALICE |
| R11 | [1/3] | ⚪ | The step 7 edit is applied literally, but the result reads badly. "...skipped counts" is followed by "who was armed, unarmed or vetoed, and the target's integrity;" with no "and" or comma before "who". The cause is the PRD's own replace text, which drops the leading "and". | skills/run-agoge/SKILL.md:264 | 6 | BLAKE |
| R12 | [1/3] | ⚪ | Test gap against the spec's own claims. `test_target_snapshot.py` has no rename/copy case (the `from <old path>` suffix) and no non-UTF-8 name case. The spec's required list is otherwise covered, plus extras: detached HEAD, deleted ref, changed config value, swapped worktree. | skills/run-agoge/scripts/test_target_snapshot.py | 1 | BLAKE |

Note: `consolidate_findings.py` merged Alice's and Blake's `_fingerprint` OSError / `_load` KeyError rows onto R1 and R6 after citation-suffix stripping (same file, paraphrased defect); their verbatim text is in the per-reviewer sections below.

## Alice

[ALICE] 🟠 PRD requires paths decoded with os.fsdecode, but the script uses strict `.decode()` on git output (`_text`, `_dirty` fields, worktrees, untracked) and `os.readlink(...).encode()` in `_fingerprint`. A non-UTF-8 file name in the target (valid on Linux) raises UnicodeDecodeError/UnicodeEncodeError. That is an uncaught traceback with exit 1, which the skill reads as "changed", not the "one stderr line, no traceback" contract. Use `os.fsdecode`/`os.fsencode` throughout | File: skills/run-agoge/scripts/target_snapshot.py:49 | Task: 2
[ALICE] 🟡 Other uncaught-exception paths break the "exit 2, one `target_snapshot:` line, no traceback" contract: `open(full, "rb")` in `_fingerprint` (unreadable file; a tracked path swapped for a FIFO would also block forever), `FileNotFoundError` when git is missing, and `KeyError` in `compare` for a snapshot with the right `version` and `repo` but missing keys. Catch OSError in `_fingerprint` and map it to `Fail`; validate required keys in `_load` | File: skills/run-agoge/scripts/target_snapshot.py:64 | Task: 2
[ALICE] 🟡 SKILL.md puts `compare ... start.json` and `snapshot ... lanes.json` in one bash block; the compare's exit 1 or 2 is masked by the snapshot's exit 0 | File: skills/run-agoge/SKILL.md:148 | Task: 4
[ALICE] 🟡 Untested new branches in `_dirty` and `_fingerprint`: rename/copy suffix, `absent`, `link:`, `dir`, detached HEAD, `<out.json>` write-failure exit 2 | File: skills/run-agoge/scripts/test_target_snapshot.py:1 | Task: 1
[ALICE] 🟡 `--allow` values are compared as raw strings against git's repo-relative paths; `./docs/...`, a trailing slash or an absolute path silently fail to exempt | File: skills/run-agoge/scripts/target_snapshot.py:201 | Task: 2
[ALICE] ⚪ `test_run_integrity.py` carries ~70 lines of regex/shell-parsing machinery to pin prose; heavy and brittle to harmless rewording | File: skills/run-agoge/scripts/test_run_integrity.py:1113 | Task: 3
[ALICE] ⚪ `_env_for` duplicated between `test_target_snapshot.py` and the cross-module import in `test_run_integrity.py` | File: skills/run-agoge/scripts/test_target_snapshot.py:1332 | Task: 3
[ALICE] ⚪ The `touched` union/de-duplication and the `status` derivation when `compare_lanes` never ran are specified only in the design doc | File: skills/run-agoge/references/finding-contract.md:250 | Task: 5

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

[BLAKE] 🟠 target_snapshot.py never uses os.fsdecode, which the spec requires so non-UTF-8 names survive. Strict `.decode()` on `status -z`, `ls-files --others -z`, `worktree list` and every `_text()` call. On Linux one such name raises an uncaught UnicodeDecodeError: traceback and exit 1, not the exit 0/2 the spec defines. No test covers it | File: skills/run-agoge/scripts/target_snapshot.py:49 | Task: 2
[BLAKE] 🟡 `_fingerprint` has no OSError handling around `open`, `readlink` or `isdir`; an unreadable tracked file or a vanished path gives a traceback and exit 1. Opening a FIFO that replaced a tracked file would block forever | File: skills/run-agoge/scripts/target_snapshot.py:56 | Task: 2
[BLAKE] 🟡 `_load` validates only `version` and `repo`; a snapshot missing `refs`, `head` or `dirty` raises KeyError in `compare`, so exit 1 ("changed") instead of exit 2 ("cannot check") | File: skills/run-agoge/scripts/target_snapshot.py:175 | Task: 2
[BLAKE] ⚪ The step 7 edit is applied literally but reads badly: "...skipped counts" followed by "who was armed..." with no "and" or comma. Cause is the PRD's own replace text | File: skills/run-agoge/SKILL.md:264 | Task: 6
[BLAKE] ⚪ Test gap: no rename/copy case (`from <old path>` suffix) and no non-UTF-8 name case | File: skills/run-agoge/scripts/test_target_snapshot.py | Task: 1

Verified as compliant (blind lens): B1 snapshot keys and B2 comparison implemented; violation order, head/ref exclusivity, `--allow` scope, `touched`, the `restore` forms with shell-quoting, config violations without the URL, exit codes, stderr prefix and `indent=2` all match; every git call uses `--no-optional-locks -C`; writing inside the repo is refused before any write; SKILL.md edits 1-7 all present; B4/B5/B6/B7 text present in the contract, README (items renumbered 4, 5, 6) and CHANGELOG; no scope creep.

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: fail
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

FIX:
- [BOB] 🟠 Non-UTF-8 filenames crash snapshot and compare: path-bearing Git output uses strict `.decode()`, contrary to the required `os.fsdecode` round trip. Use filesystem decoding for paths and `os.fsencode` for symlink text; add a non-UTF-8 filename regression. | File: skills/run-agoge/scripts/target_snapshot.py:79 | Task: 2
- [BOB] 🟠 Fingerprinting follows symlinked parent directories outside the target. Replacing a tracked directory with an external symlink makes its deleted tracked children resolve outside the repository. Check ancestor components before opening files and reject external traversal; add this regression. | File: skills/run-agoge/scripts/target_snapshot.py:57 | Task: 2
- [BOB] 🟠 Dispatch has no failure gate for creating `lanes.json`. If this second snapshot exits 2, the instructions still proceed to dispatch without a valid baseline. Explicitly stop dispatch and report unknown integrity when this snapshot fails. | File: skills/run-agoge/SKILL.md:154 | Task: 4
- [BOB] 🟡 Filesystem errors during fingerprinting escape as tracebacks because `main` catches only `Fail`. An unreadable tracked file therefore violates the exit-2 contract. Convert fingerprint read errors into `Fail` and test empty stdout plus one prefixed stderr line. | File: skills/run-agoge/scripts/target_snapshot.py:64 | Task: 2
- [BOB] 🟡 The runtime sidecar contract omits the design's explicit merge rules: nullable lane comparison, zero contributions from exit-2 calls, and a deduplicated union of touched paths. Add these rules so report generation preserves recon artifacts and handles early failure consistently. | File: skills/run-agoge/references/finding-contract.md:252 | Task: 5

VERIFY:
- (none)

KNOWN:
- (none)

R1: fail
R2: pass
R3: pass
R4: fail
R6: pass
R7: fail
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

## Carl

Carl: permanently unavailable (no backend model) - copilot authentication failed (permanent; no fallback). No output published; nothing consolidated for this lens.

Verdict: 12 findings
Tests: 162 passed, 0 failed, 0 skipped (suite run this cycle)
