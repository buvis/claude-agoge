---
head_sha: 80f73d5be18ebc030641add62741715f4aab4787
reviewers: alice, blake, eve, carl
---

## Alice

**00012-inherited-git-dir-misreads-target-v1-c1**
[ALICE] ✅ No issues found. Verified fail-first against pre-fix commit 8908f12 (the new test fails with the decoy's HEAD leaking into the target's snapshot), full suite green (33 passed, 1 skipped in the module, 179 passed/1 skipped repo-wide), CHANGELOG entry correctly placed under `[Unreleased]`/`### Fixed`. No hardcoded secrets, no injection risk, function/file sizes well within limits. Noted one non-blocking out-of-scope observation: `test_scratch_contract.py` invokes git via `cwd=` rather than `-C`, also subject to an inherited GIT_DIR, but out of this PRD's declared file scope.

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: pass, R8: pass, R9: pass, R10: pass, R11: pass, R12: pass, R13: pass

## Blake

**00012-inherited-git-dir-misreads-target-v1-c1**
[BLAKE] ✅ No issues found. Verdict: PASS. All three card tasks (test, fix, changelog) implemented and independently verified against the card alone, with no diff seen. Confirmed the fail-first test fails on the pre-fix commit and passes at HEAD, full suite green, CHANGELOG grep hits. All 19 blind-rubric rules (B1-B19) pass.

## Eve

**00012-inherited-git-dir-misreads-target-v1-c1**
Doubt + de-slop review, scope `07bb481..HEAD`. Independently confirmed fail-first and ran a parametrized hijack over all 7 stripped env vars: the pre-fix code silently misreads the target on 4 of 7 (GIT_DIR, GIT_COMMON_DIR, GIT_INDEX_FILE with exit 0; GIT_WORK_TREE with exit 2), and the fix passes all 7.

FIX (none CRITICAL/HIGH):
- Only GIT_DIR is pinned by name in the new test; removing GIT_COMMON_DIR or GIT_INDEX_FILE from `_GIT_REPO_VARS` would still pass the suite though both are confirmed silent-misread vectors — recommends parametrizing the test over an explicit list of vars (test_target_snapshot.py:750).
- One assertion (line 771) and one env alias (`decoy_env`, line 752) in the new test are redundant with earlier lines.
- Module docstring (target_snapshot.py:14-17) doesn't mention the new env-scrub behavior.

KNOWN (both explicitly out of scope, accepted as-is):
- `_ref_violation`'s emitted `restore` shell commands run in the operator's own shell, which the script cannot scrub — out of this PRD's scope (covers the script's own git calls only).
- GIT_CEILING_DIRECTORIES / GIT_DISCOVERY_ACROSS_FILESYSTEM are not stripped, but verified they cannot cause a silent misread of a toplevel target (worst case is a loud exit 2).

D1: pass, D2: pass, D3: pass, D4: pass, D5: pass

## Carl

**00012-inherited-git-dir-misreads-target-v1-c1**
[CARL] ✅ No issues found. Independently ran the new test against the pre-fix commit (confirmed failure), ran the full module suite at HEAD, and verified the CHANGELOG entry. Left the repo correctly switched back to `master` at the correct HEAD after its own checkout experiments.

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: pass, R8: pass, R9: pass, R10: pass, R11: pass, R12: pass, R13: pass

Verdict: converged
Tests: 179 passed, 1 skipped, 0 failed (fast-track batch suite)
codex_rung_guard: not fired
