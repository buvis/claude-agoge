---
head_sha: 133e8c7beafce4c06d75b3954e9d82289bea43ff
reviewers: fanout, blake, eve, bob, carl
---

## Fanout

**00035-allocator-backlog-path-race-v1-c1**

[fast-track:00035-allocator-backlog-path-race-v1-c1] ✅ No issues found

Advisory (does not block): CHANGELOG entry text doesn't match required acceptance string — resolved in rework.

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: fail (noted: missing post-open containment/identity check — resolved in rework)
R11: pass
R12: pass
R13: pass

## Blake

**00035-allocator-backlog-path-race-v1-c1**

[BLAKE] 🟠 claim() skips the step the spec requires: comparing os.fstat(fd) with os.stat(realpath) by st_dev and st_ino. It also runs the realpath check BEFORE the os.open, not after it. O_NOFOLLOW guards only the last path component. So if an attacker swaps an intermediate directory (prds/ or project-management/) for a symlink between the check and the open, the file lands outside the repo while the printed path stays inside. I reproduced it. | File: skills/run-agoge/scripts/allocate_prd_number.py:57 | Task: 2 — **CONFIRMED by victor, fixed in rework commit 133e8c7**
[BLAKE] 🟠 The CHANGELOG acceptance fails. | File: CHANGELOG.md:21 | Task: 3 — **fixed in rework commit 133e8c7**
[BLAKE] 🟡 ELOOP/ENOTDIR from the backlog open escapes as OSError instead of SystemExit. | File: skills/run-agoge/scripts/allocate_prd_number.py:64 | Task: 2 — **fixed in rework commit 133e8c7**
[BLAKE] ⚪ The serialization lock moved from prds/ to backlog/, and the spec does not ask for this. | File: skills/run-agoge/scripts/allocate_prd_number.py:70 | Task: 2 — not reworked (out of rework scope; LOW)

## Eve

**00035-allocator-backlog-path-race-v1-c1**

Round 1 (doubt lens on the initial implementation):

FIX:
- [HIGH] claim() checks the backlog path before os.open and never compares os.fstat(fd) with os.stat(realpath) by st_dev/st_ino, so an ancestor directory swap between check and open still escapes the repo. Reproduced live. — **CONFIRMED by victor, fixed in rework commit 133e8c7**
- [MEDIUM] ELOOP/ENOTDIR escapes as raw OSError instead of SystemExit. — **fixed in rework commit 133e8c7**
- [MEDIUM] CHANGELOG acceptance phrase mismatch. — **fixed in rework commit 133e8c7**

KNOWN: lock location change, redundant O_NOFOLLOW on create, refusal-message variable choice — out of rework scope (LOW).

D1-D5: pass.

Round 2 (delta review, scoped to rework commit `d441429..HEAD`):

Both round-1 findings confirmed resolved (verified with a harness-control test and an in-memory removal of the fix, which reliably failed without it; reproduced live with real symlink-swap probes A-D).

FIX (surviving, both MEDIUM/LOW, neither blocking):
- [MEDIUM] The fstat/stat identity check is unpinned by a test: no test exercises a swap-before-open-then-restore-before-realpath window.
- [LOW] The code comment overstates coverage ("ancestor swapped around the open cannot redirect the file" is false for a swap-restore-swap sequence).

KNOWN (out of scope, explicitly accepted): a double ancestor swap (swap, restore, swap) still escapes — needs a different mechanism than the PRD specifies and would break the supported in-repo `prds` symlink case; `mkdir` creates an empty outside `backlog/` before refusal on a pre-existing symlinked ancestor — the PRD's must-haves cover files only; an in-repo `backlog` symlink is now refused, which the PRD's Risk section already accepts.

D1-D5: pass.

## Bob

**00035-allocator-backlog-path-race-v1-c1**

[BOB] 🟠 The containment check runs before `os.open`, and `O_NOFOLLOW` protects only the final path component. The required post-open containment and device/inode checks are missing. | File: skills/run-agoge/scripts/allocate_prd_number.py:64 | Task: 00035-allocator-backlog-path-race-v1-c1 — **CONFIRMED by victor, fixed in rework commit 133e8c7**
[BOB] 🟡 ELOOP/ENOTDIR escape as OSError instead of SystemExit. | File: skills/run-agoge/scripts/allocate_prd_number.py:64 | Task: 00035-allocator-backlog-path-race-v1-c1 — **fixed in rework commit 133e8c7**
[BOB] 🟡 The allocator scans the backlog by path while locking/writing through the fd. | File: skills/run-agoge/scripts/allocate_prd_number.py:71 | Task: 00035-allocator-backlog-path-race-v1-c1 — not reworked (MEDIUM, out of confirmed-finding scope)
[BOB] 🟡 Required rejection paths lack tests. | File: skills/run-agoge/scripts/test_allocate_prd_number.py:366 | Task: 00035-allocator-backlog-path-race-v1-c1 — addressed by rework's new test; residual gap recorded by Eve's delta review (MEDIUM)
[BOB] 🟡 Redundant O_NOFOLLOW on candidate creation. | File: skills/run-agoge/scripts/allocate_prd_number.py:80 | Task: 00035-allocator-backlog-path-race-v1-c1 — not reworked (LOW)
[BOB] 🟡 The changelog entry misses the exact phrase required. | File: CHANGELOG.md:21 | Task: 00035-allocator-backlog-path-race-v1-c1 — **fixed in rework commit 133e8c7**
[BOB] ⚪ The returned path can point at the replacement backlog. | File: skills/run-agoge/scripts/allocate_prd_number.py:85 | Task: 00035-allocator-backlog-path-race-v1-c1 — KNOWN, PRD-accepted (out of scope)
[BOB] ⚪ main() exceeds the 50-line limit (pre-existing). | File: skills/run-agoge/scripts/allocate_prd_number.py:95 | Task: 00035-allocator-backlog-path-race-v1-c1 — KNOWN, pre-existing, unchanged by this diff (out of scope)

## Carl

**00035-allocator-backlog-path-race-v1-c1**

[CARL] 🟠 Containment check runs before os.open and omits required post-open fstat/stat identity verification | File: skills/run-agoge/scripts/allocate_prd_number.py:64 | Task: 2 — **CONFIRMED by victor, fixed in rework commit 133e8c7**
[CARL] 🟠 ELOOP/ENOTDIR escape as unhandled OSError rather than SystemExit | File: skills/run-agoge/scripts/allocate_prd_number.py:64 | Task: 2 — **fixed in rework commit 133e8c7**
[CARL] 🟡 CHANGELOG.md entry text does not match acceptance criteria check string | File: CHANGELOG.md:21 | Task: 3 — **fixed in rework commit 133e8c7**
[CARL] 🟡 PRD task 2 error paths and directory identity verification are not covered by unit tests | File: skills/run-agoge/scripts/test_allocate_prd_number.py:366 | Task: 1 — addressed by rework's new test; residual gap recorded by Eve's delta review (MEDIUM)
[CARL] 🟡 Candidate creation includes redundant O_NOFOLLOW flag | File: skills/run-agoge/scripts/allocate_prd_number.py:80 | Task: 2 — not reworked (LOW)
[CARL] ⚪ Function main exceeds 50-line limit (61 lines) | File: skills/run-agoge/scripts/allocate_prd_number.py:95 | Task: general — KNOWN, pre-existing, unchanged by this diff (out of scope)

Verdict: 2 findings
Tests: 288 passed, 0 failed, 2 skipped (fast-track batch suite)
codex_rung_guard: not fired
