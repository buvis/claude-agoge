---
head_sha: e64c6ca676ee5a611df2f551c624e4186dd6b647
reviewers: alice, blake, eve, carl
---

## Alice

**00019-snapshot-memory-grows-with-dirty-file-v1-c1**
| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟡 | skills/run-agoge/scripts/test_target_snapshot.py is 1008 lines, over the repo's 800-line file guideline; it was already 912 lines before this diff and this change adds ~96 more. Pre-existing debt, not introduced by this diff, so out of scope to fix here, but worth a follow-up to split by concern (e.g. extract gitdir/submodule/worktree tests into their own files). | skills/run-agoge/scripts/test_target_snapshot.py | general | CONSENSUS |
| R5 | [1/4] | ⚪ | The chunk size `1024 * 1024` is inlined twice in spirit (used once in `_fingerprint`); a named constant would make the budget relationship (1 MiB chunks vs 48 MiB test budget) easier to read, but this is a cosmetic nit, not a defect. | skills/run-agoge/scripts/target_snapshot.py:111 | T1 | CONSENSUS |

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
R13: fail (pre-existing file-size debt on test_target_snapshot.py, unrelated to this change's own lines)

## Blake

**00019-snapshot-memory-grows-with-dirty-file-v1-c1**
[BLAKE] ✅ No issues found

B1-B19: pass

## Eve

**00019-snapshot-memory-grows-with-dirty-file-v1-c1**
| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R2 | [1/4] | 🟡 | `-c core.bigFileThreshold=1m` on `git status` is an unstated, load-bearing scope extension: absent from PRD Solution/Tasks and both commit messages, no rationale in code, yet without it the RSS gate fails on git alone (207 MiB measured). Add a one-line comment explaining why, and extend the CHANGELOG entry to mention git status streaming. | skills/run-agoge/scripts/target_snapshot.py | T1 | DOUBT |
| R3 | [1/4] | 🟡 | `_peak_rss` discards the wrapped run's exit code (an early-crashing compare with tiny RSS could pass the budget assert); the test then re-runs `_compare` separately only to check exit 1, duplicating work and leaving a narrow validity gap between the measured run and the checked run. | skills/run-agoge/scripts/test_target_snapshot.py | T1 | DOUBT |
| R4 | [1/4] | 🟡 | `_peak_rss` relies on `/usr/bin/time` (GNU `-v` assumed on Linux, absent raises FileNotFoundError rather than skipping) plus a platform regex table, when a pure-Python wrapper using `resource.getrusage(RUSAGE_CHILDREN)` inside a fresh subprocess would measure the same tree with no external tool dependency. | skills/run-agoge/scripts/test_target_snapshot.py | T1 | DOUBT |
| R6 | [1/4] | ⚪ | `_peak_rss`'s docstring claims it reports "the peak RSS of just the one process it wraps", which is inaccurate since ru_maxrss/`/usr/bin/time` includes waited-for descendants (why the git override was needed); the same explanation is also duplicated as a comment in the test body. | skills/run-agoge/scripts/test_target_snapshot.py | T1 | DOUBT |
| R7 | [1/4] | ⚪ | `test_fingerprint_matches_whole_file_sha256`'s comment claims the content "straddles any chunk boundary non-uniformly", but `bytes(range(256)) * 4096` has a 256-byte period, so every 1 MiB chunk in the 5 MiB file is byte-identical; the streaming writer is also unnecessary at this size since the test reads the whole file back anyway. | skills/run-agoge/scripts/test_target_snapshot.py | T1 | DOUBT |

KNOWN (out of scope, accepted):
- `core.autocrlf=true` or a `text`/`eol`/`filter` attribute on the dirty file makes `git status` mmap it whole regardless of `core.bigFileThreshold` (measured 207 MiB) — the snapshot cannot change the target's attributes.
- `_gitdir_files` still hashes each checked `.git` file with one `handle.read()` — PRD 00019 covers dirty work-tree files only; gitdir entries are hook/config-sized; a follow-up could reuse the chunked hasher.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

**00019-snapshot-memory-grows-with-dirty-file-v1-c1**
[CARL] ✅ No issues found

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

Bob (codex): missing lens. Codex failed on both the initial dispatch and the one retry with `sandbox_apply: Operation not permitted` before reading any context or diff (sandbox runtime failure, not a finding). No codex output is included in the consolidated table.

Verdict: 7 findings
Tests: 43 passed, 0 failed, 2 skipped (fast-track batch suite)
codex_rung_guard: not fired
