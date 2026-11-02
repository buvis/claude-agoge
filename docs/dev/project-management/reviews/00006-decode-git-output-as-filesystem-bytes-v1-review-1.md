---
head_sha: 5281e9e21bda7a85b18bdd07f9047a0c5d3087d5
reviewers: alice,blake,bob,carl,eve
---

# Review 1: PRD 00006 (fast-track lane, one card)

Range `96616c0db66fb98c4f3f132e87f14ba2e92ca34d..5281e9e`. Commits: c550b9b (tests), dcf4bcc (fix), 5281e9e (review fixes).

## Alice

**00006-decode-git-output-as-filesystem-bytes-v1-c1** (consensus slot ran as the `autopilot:alice` subagent: the Workflow tool needs explicit user opt-in, so the workflow backend was not used)
- ⚪ `test_non_utf8_paths_round_trip` skips on macOS/APFS (Errno 92); run on Linux to prove it. Skip is the one the PRD specifies.
- ⚪ `test_text_keeps_filesystem_bytes_and_trailing_space` mutated `sys.path`. Fixed in 5281e9e (top-level import).
- R1-R13: all pass. Full suite at review time: 166 passed, 1 skipped.

## Blake

**00006-decode-git-output-as-filesystem-bytes-v1-c1** (spec only, no diff)
- ⚪ Formatter churn in the working tree (uncommitted, not in any commit). Reverted with `git checkout`; both files were clean at commit.
- ⚪ Skipped non-UTF-8 path test (same as Alice).
- ⚪ `splitlines()` on for-each-ref output also splits on U+2028 and similar: pre-existing, valid-UTF-8, out of scope (recorded below).
- B1-B19: all pass. Every spec item confirmed present.

## Bob

**00006-decode-git-output-as-filesystem-bytes-v1-c1**
Lane note: the codex run produced no review (its sandbox could not start inside the host sandbox: `sandbox_apply: Operation not permitted`; every R line was a fail from missing evidence). The lens was re-run once as a Claude opus subagent on the same prompt (read-only, `Read` tool). Model-family diversity for this lane is therefore reduced; the gemini lane (Carl) ran on a non-Anthropic model.
- 🟡 CHANGELOG entry misstated the user-visible effect. Fixed in 5281e9e.
- 🟡 Non-UTF-8 path test never runs on this host; no CI in repo (recorded as known).
- ⚪ `sys.path` mutation (fixed), ragged docstring (fixed).
- R1-R13: all pass.
FIX:
- CHANGELOG wording (fixed 5281e9e); sys.path in test (fixed); docstring wrap (fixed)
VERIFY:
- Run `-k round_trip` on Linux ext4 to see the path test PASS (not run here)
KNOWN:
- Restore commands for non-UTF-8 refs hold surrogate escapes in JSON; print-only by contract
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

**00006-decode-git-output-as-filesystem-bytes-v1-c1** (gemini via copilot backend)
[CARL] ✅ No issues found
- R1-R13: all pass.

## Eve

**00006-decode-git-output-as-filesystem-bytes-v1-c1** (doubt + de-slop; ran the gate, the full file, fail-first against the pre-change script, and a trailing-space probe)
FIX:
- Trailing-space repo dir not pinned end to end: added `test_repo_dir_with_trailing_space_round_trips` (fixed 5281e9e; fails on the old script)
- Exit-2 line dropped the failing file name: now `unexpected <Type>: '<message>'`, test asserts `notes.txt` is named (fixed 5281e9e)
- Test slop (`sys.path.insert`, duplicate `other` assertion): removed (fixed 5281e9e)
- Ragged docstring: re-wrapped (fixed 5281e9e)
VERIFY:
- Run the non-UTF-8 path test on Linux ext4 and confirm `1 passed`
KNOWN:
- `splitlines()` on for-each-ref splits on U+2028/U+0085 for valid-UTF-8 refnames: pre-existing, one-token follow-up (`.split("\n")`), outside this PRD
- Windows `os.fsdecode` uses surrogatepass: out of scope, script is POSIX-only
- Blanket `except Exception` hides future bugs' tracebacks: the card's contract
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: converged
Tests: 167 passed, 0 failed, 1 skipped (fast-track batch suite; the skip is the non-UTF-8 path test on APFS)
codex_rung_guard: not fired
