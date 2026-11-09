---
head_sha: a7c2b65d6d74d1d8d399647033670a68be06a03b
reviewers: alice, blake, eve, carl
---

## Alice

**00018-non-utf8-ref-restore-fails-v1-c1**

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟠 | The regression test `test_restore_command_puts_non_utf8_ref_back` passes against the unchanged code, so it is tautological (resolved by rework: see Delta below). | skills/run-agoge/scripts/test_target_snapshot.py:888 | 1 | Alice, Blake |
| R2 | [1/4] | 🟡 | No test covers the new `$'...'` branch of `_shell_quote` on any platform. | skills/run-agoge/scripts/target_snapshot.py:194 | 2 | Alice |
| R4 | [1/4] | ⚪ | `test_utf8_restore_command_is_unchanged` checks the same value twice. | skills/run-agoge/scripts/test_target_snapshot.py:911 | 1 | Alice |

Verdict: converged (after rework)

## Blake

**00018-non-utf8-ref-restore-fails-v1-c1**

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R3 | [1/4] | 🟡 | `compare` prints JSON, which doubles the backslash in the restore string; only works after JSON decoding, undocumented. | skills/run-agoge/scripts/target_snapshot.py:301 | 2 | Blake |
| R5 | [1/4] | ⚪ | `$'...'` restore line only works in bash/zsh, not POSIX sh/dash/fish; noted only in the docstring. | skills/run-agoge/scripts/target_snapshot.py:203 | 2 | Blake |

Verdict: converged

## Eve

**00018-non-utf8-ref-restore-fails-v1-c1** (round 1)

FIX:
- Regression test passes against pre-fix code — skills/run-agoge/scripts/test_target_snapshot.py:888 — add `assert violation["restore"].isascii()` and encode to ASCII before feeding to `bash -c`. **CONFIRMED by Victor; reworked in commit a7c2b65.**
- Redundant assertion (lines 910-911 of the original) — delete the duplicate.

VERIFY:
- Post-fix behavior never observed on a filesystem that accepts the non-UTF-8 name — run on Linux CI.
- `_shell_quote(repo)` for a non-UTF-8 repo path has no test.

KNOWN:
- `$'...'` is bash/zsh-specific; PRD accepted this drawback.
- Non-UTF-8 detection relies on `os.fsdecode` surrogateescape; a legacy non-UTF-8 locale could misbehave — pre-existing from PRD 00006, not introduced here.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

**00018-non-utf8-ref-restore-fails-v1-c1** (delta, rework round)

Prior HIGH finding: RESOLVED. Verified empirically: pre-fix restore line fails `isascii()`/`.encode("ascii")`; post-fix line is pure ASCII and round-trips through `bash -c` correctly on a reftable-backed repo (APFS workaround). Full file run: 41 passed, 2 skipped (expected skips).

FIX:
- `test_utf8_restore_command_is_unchanged` still asserts the same value twice (pre-existing, not introduced by rework) — skills/run-agoge/scripts/test_target_snapshot.py:906-912 — keep the `expected`-join assert, delete the redundant f-string line.

VERIFY:
- No Linux CI run yet exists for HEAD — confirm the `test` workflow's ubuntu-latest job passes for a7c2b65 and the non-UTF-8 test is not skipped there.

KNOWN:
- `isascii()` check covers the whole restore line including the repo path; a non-ASCII username would fail spuriously — out of scope per PRD.
- Permanent macOS skip (APFS); PRD accepts and delegates to Linux CI.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: converged

## Carl

**00018-non-utf8-ref-restore-fails-v1-c1**

[CARL] ✅ No issues found

Verdict: converged

## Codex (Bob)

Unavailable: both dispatches (initial and one retry) hit `sandbox_apply: Operation not permitted` before reading any file — a codex sandbox/hook environment failure, not a code finding. Per the one-retry rule this lane counts as failed/unavailable for this cycle.

Verdict: converged
Tests: 195 passed, 2 skipped (fast-track batch suite)
codex_rung_guard: not fired
