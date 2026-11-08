---
head_sha: b4305c5d7203f3c3b1c5e914aeada150b31bc0b3
reviewers: alice, blake, eve, carl
---

## Alice

**00008-integrity-check-misses-git-hooks-v1-c1**

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🔴 | `_gitdir_files` silently returned `{}` for any target whose `.git` is a worktree pointer file (not a directory), so the new hook/info-exclude/info-attributes/config.worktree detection was a complete no-op for worktree-shaped targets — fixed in the rework by resolving the real git-common-dir | skills/run-agoge/scripts/target_snapshot.py:118 | general | CONSENSUS, BLIND, GEMINI |
| R2 | [1/4] | 🟡 | CHANGELOG.md:15 overstated the fix ("worktree-local config" now detected) while the linked-worktree gap stood; the gap this line referred to is now closed for hooks/info by the rework | CHANGELOG.md:15 | general | BLIND |

## Blake

**00008-integrity-check-misses-git-hooks-v1-c1**

[BLAKE] 🔴 config.worktree is explicitly named in the PRD Goal as a gap this fast-track must close, and the CHANGELOG entry claims it ("worktree-local config" now detected), but `GITDIR_UNCHECKED` skipped the whole top-level `worktrees` directory, so `.git/worktrees/<id>/config.worktree` for any linked worktree was never hashed or compared. Verified live with `core.hooksPath` redirection via a linked worktree's config.worktree bypassing the gate. | File: skills/run-agoge/scripts/target_snapshot.py:32 | Task: general
[BLAKE] 🟡 CHANGELOG.md:15 overstated the fix when only the main worktree's own config.worktree was covered. | File: CHANGELOG.md:15 | Task: general
[BLAKE] ✅ All four PRD task bullets otherwise verified: three new `*_gitdir_violation` tests, the `gitdir` snapshot key/compare/`GITDIR_UNCHECKED`/`VERSION=2` bump, the two repointed version tests, and the CHANGELOG entry are all present and correct; all stated gates pass. | File: N/A | Task: general

## Eve

**00008-integrity-check-misses-git-hooks-v1-c1**

Doubt + de-slop review (range 2de383e..c44bd76). Reproduced the linked-worktree bypass live (same root cause Alice, Blake and Carl independently found): `_gitdir_files` hardcoded `<repo>/.git`, which is a file in a linked worktree, so a hook planted in the shared git dir compared `unchanged`.

Additional findings raised (none escalated — the sole CRITICAL/HIGH confirmed row was R1 above, which the rework fixed; these are recorded for a follow-up, not reworked in this cycle):
- Non-regular entries under a checked git-dir top (sockets from `core.fsmonitor`, dangling/external symlinks in `hooks/`) abort the gate with exit 2 or silently skip, instead of reporting a violation.
- The exec bit is not fingerprinted: `chmod +x` on an existing non-executable hook activates it with no content change and compares `unchanged`.
- The three new violation tests assert only `any(v["kind"] == "gitdir")`, never pinning path/before/after.
- `test_every_gitdir_entry_is_checked_or_listed` reimplements `_gitdir_files`'s own walk/skip rule, so it is a tautology on intent.
- Module docstring still describes the v1 snapshot shape (no `gitdir` key/kind mentioned).
- (Delta pass) Linked-worktree `config.worktree` (`.git/worktrees/<id>/config.worktree`) is still undetected — the `worktrees` top stays in `GITDIR_UNCHECKED` — so an attacker can still redirect `core.hooksPath` via a linked worktree's own config scope even after the rework fixed hooks/info detection for the shared git dir.

KNOWN (out of scope for this item): submodule gitdirs (`.git/modules/<name>/hooks/`) are not checked; `objects/info/alternates` is not checked (sits under the unchecked `objects` top); `.git/lfs/` would be hashed wholesale if the LFS filter were configured (not configured in this org today).

D1-D5: pass

## Carl

**00008-integrity-check-misses-git-hooks-v1-c1**

[CARL] 🟠 `_gitdir_files` silently returned `{}` when target `.git` is a worktree pointer file, making hook, info/exclude, and worktree config detection a no-op for worktree-shaped lanes | File: skills/run-agoge/scripts/target_snapshot.py:118 | Task: general

## Victor (verification)

R1 (CRITICAL, linked-worktree gitdir no-op): **CONFIRMED**. `_gitdir_files` built the git-dir path with `os.path.join(repo, ".git")` and walked it with `os.walk`; for a linked worktree `<repo>/.git` is a plain pointer file, so `os.walk` silently yields nothing and the function returned `{}`, matching all four reviewers' live repros. No other code path resolves the real git-dir. Fixed in the rework commit.

## Rework

Dispatched a fresh `autopilot:ivan` with the confirmed CRITICAL finding. Fix: `_gitdir_files` now resolves the git-common-dir via `git rev-parse --path-format=absolute --git-common-dir` instead of assuming `<repo>/.git` is a directory. Added regression test `test_new_hook_on_linked_worktree_is_gitdir_violation` (creates a linked worktree, snapshots it, plants a hook in the shared `.git/hooks`, asserts a `gitdir` violation). Commit: `fix(00008-integrity-check-misses-git-hooks-v1-c1): address confirmed findings`.

## Delta

One `autopilot:eve` dispatch over the rework diff (`c44bd76..b4305c5`). Prior CRITICAL confirmed RESOLVED for hooks and `info/*` (regression test fails on pre-rework code, passes now; full file suite 30 passed, 1 pre-existing skip). Raised several new residual findings (listed under Eve's section above, including a narrower remaining gap: linked-worktree `config.worktree` is still undetected) — none tagged CRITICAL/HIGH and confirmed, so nothing further reworked this cycle; the lane runs rework at most once.

Verdict: converged
Tests: 176 passed, 1 skipped (`dev/bin/release-checks` at b4305c5d7203f3c3b1c5e914aeada150b31bc0b3)
codex_rung_guard: not fired

## Reviewer availability

- alice: available (consensus, ran as the `autopilot:alice` subagent — no `review-fanout.workflow.js` call recorded in this cycle's dispatch rows; the Workflow tool was available but the consensus lane was dispatched as the subagent fallback)
- blake: available
- eve: available
- bob (codex): unavailable — codex's sandbox blocked all reads twice (`sandbox_apply: Operation not permitted`) on both the first dispatch and its one retry; hand-off to a general-purpose subagent substitute was not attempted this cycle
- carl (gemini): available

## Dispatch counts

fast-track:blake 1
fast-track:bob 2
fast-track:carl 1
fast-track:delta 1
fast-track:eve 1
fast-track:fanout 1
fast-track:ivan 2
fast-track:tess 1
fast-track:victor 1
