# Supplement to review 1 of PRD 00024: the codex lens, run again on the real model

Date: 2026-11-24. Range: `4d4a315..8e136c5`. This file adds to
`00024-snapshot-slow-many-untracked-files-v1-review-1.md`; it does not replace it.

## Why this exists

In review 1 the codex lane (Bob) did not run on codex. The codex CLI could not
start its own sandbox inside the agent sandbox (`sandbox_apply: Operation not
permitted`), exited 0 and returned no review. The driver put a Claude opus
subagent in its place. That was a deviation: the fast-track skill allows the
substitute only when `codex-run.sh` exits 3, and the one retry was not spent.

The plugin already has the recovery: an inlined prompt, which codex can review
without reading a file (`skills/review-work-completion/references/retry-policy.md`,
section "Inlined prompt (Bob's first dispatch)"). The driver built that prompt
on 2026-11-24 and ran `codex-run.sh` on it. Codex (`gpt-6.2-sol`, read-only
sandbox) returned a full review. Raw output:
`docs/dev/tmp/codex-inlined-output-00024-snapshot-slow-many-untracked-files-v1-c1.txt`
(scratch; the lines below are the record).

## Findings

[BOB] 🟠 FIX: The process-wide cache can reuse a safe directory result after that directory becomes a symlink outside the repo. A later snapshot in the same process can then open and hash the external file. Scope cached results to one snapshot and test directory replacement between snapshots. | File: skills/run-agoge/scripts/target_snapshot.py:237 | Task: 00024-snapshot-slow-many-untracked-files-v1-c1
[BOB] 🟡 FIX: The recursive ancestor walk can raise `RecursionError` on valid deeply nested paths. Walk ancestors iteratively, retain directory memoization, and test a path deep enough to expose the regression. | File: skills/run-agoge/scripts/target_snapshot.py:237 | Task: 00024-snapshot-slow-many-untracked-files-v1-c1
[BOB] 🟡 FIX: The stat-count regression creates a directory tree without initializing Git. Use a fresh Git repo as required by the acceptance criteria. | File: skills/run-agoge/scripts/test_target_snapshot.py:588 | Task: 00024-snapshot-slow-many-untracked-files-v1-c1
[BOB] 🟡 FIX: The distinct-digest assertion adds a uniqueness requirement after the exact expected digests have already been checked. Keep the exact comparison and drop the uniqueness assertion. | File: skills/run-agoge/scripts/test_target_snapshot.py:588 | Task: 00024-snapshot-slow-many-untracked-files-v1-c1
[BOB] ⚪ KNOWN: The compatibility test passes against the prior code, which fails the literal R2 criterion. The PRD explicitly requires that result, so changing the test to force a prior-code failure is outside scope. | File: skills/run-agoge/scripts/test_target_snapshot.py:615 | Task: 00024-snapshot-slow-many-untracked-files-v1-c1

R1: fail, R2: fail, R3: pass, R4: fail, R6: pass, R7: fail, R8: pass, R9: fail,
R10: pass, R11: pass, R12: pass, R13: pass. D1 to D5: all pass.

## Disposition

- The HIGH is real. Review 1 had it as MEDIUM (Eve) and LOW (Blake, the
  substitute). No adversarial verify lane ran on it; the driver confirmed it
  with a probe on 2026-11-24 instead: in one process, a dirty tracked file under
  `sub/`, `take_snapshot`, `sub` replaced by a symlink to an outside directory,
  then `compare`. The violation's `after` held the sha256 of the outside file,
  so the script read outside the repo. No shipped command does this today: each
  CLI call is one process with one snapshot. PRD 00037 adds in-process tests
  that take a snapshot and compare.
- The first MEDIUM is real: `_fingerprint(repo, "d/" * 3000 + "f.txt")` raises
  `RecursionError` (measured on the same day).
- The second MEDIUM is rejected: `_fingerprint` reads no git state, and "repo"
  in the card means the directory.
- The third MEDIUM is accepted (a dead assert).
- With a HIGH raised, the fast-track lane would have run the verify lane and,
  on a confirmed finding, one rework before the commit. That did not happen.
  The fix is PRD `00038-symlink-cache-outlives-snapshot-v1`, which gets its own
  review. PRD 00024 stays done.
