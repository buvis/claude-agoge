# Supplement to the fast-track review of PRD 00027: the codex lens, run on an inlined prompt

Date: 2026-11-25. Range: commits `6f5d24d` and `aca127f`. This file adds to
`00027-allow-misses-removed-directory-contents-v1-fast-track-review.md`; it does
not replace it.

## Why this exists

In the fast-track review the codex lane (Bob) returned no review: a hook blocked
every `cat` codex tried. The loop session put a Claude subagent in its place.
The rows marked `CODEX` in that review's table are therefore from an Anthropic
model. The skill allows that substitute only when `codex-run.sh` exits 3.

The monitoring session ran `codex-run.sh` on the inlined prompt shape of
`skills/review-work-completion/references/retry-policy.md`, which needs no file
read. Codex (`gpt-6.2-sol`, read-only sandbox) returned a full review. Raw
output: `docs/dev/tmp/codex-inlined-output-00027-c1.txt` (scratch; the lines
below are the record).

## Findings

[BOB] 🟡 `_allowed` leaves the snapshot path unchanged and strips all trailing slashes from allow entries. The PRD requires stripping one from each. | File: skills/run-agoge/scripts/target_snapshot.py:424 | Task: 00027-allow-misses-removed-directory-contents-v1-c1
[BOB] 🟡 The directory regression omits empty ignored directories and directory allowances for tracked changes, modified untracked files, and newly touched files. | File: skills/run-agoge/scripts/test_target_snapshot.py:317 | Task: 00027-allow-misses-removed-directory-contents-v1-c1
[BOB] 🟡 The prefix test can pass without checking that `igndir/f` remains a violation or that an exact file allowance leaves a same-prefix sibling reportable. | File: skills/run-agoge/scripts/test_target_snapshot.py:347 | Task: 00027-allow-misses-removed-directory-contents-v1-c1

R1: fail, R9: fail. R2 to R4, R6 to R8 and R10 to R13: pass. D1 to D5: pass.

## Disposition

- No CRITICAL or HIGH. The outcome of the fast-track review does not change.
- The first finding is row R2 of that review (there LOW, here MEDIUM). The
  second is rows R1 and R5. Both stay with that review's follow-up.
- The third finding is new: the prefix test does not pin that a sibling path
  with the same prefix stays reportable. It is a test-strength gap, MEDIUM, not
  fixed. It belongs with row R1 when that row is worked.
