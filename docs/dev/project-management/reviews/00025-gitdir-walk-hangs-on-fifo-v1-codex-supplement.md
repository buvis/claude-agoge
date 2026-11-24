# Supplement to review 1 of PRD 00025: the codex lens, run on an inlined prompt

Date: 2026-11-24. Range: `fabdc05..7de1231`. This file adds to
`00025-gitdir-walk-hangs-on-fifo-v1-review-1.md`; it does not replace it.

## Why this exists

In review 1 the codex lane (Bob) failed twice and was left out: codex could not
read the staged files (its `cat` was blocked) and returned no review. The
interactive session that drove PRD 00024 then ran `codex-run.sh` on the inlined
prompt shape of `skills/review-work-completion/references/retry-policy.md`,
which needs no file read. Codex (`gpt-6.2-sol`, read-only sandbox) returned a
full review. Raw output:
`docs/dev/tmp/codex-inlined-output-00025-gitdir-walk-hangs-on-fifo-v1-c1.txt`
(scratch; the lines below are the record).

## Findings

[BOB] 🟡 The two-second timeout does not cap memory. If the unbounded `/dev/zero` read returns, the test subprocess can exhaust available memory before the timeout. | File: skills/run-agoge/scripts/test_target_snapshot_state.py:648 | Task: 00025-gitdir-walk-hangs-on-fifo-v1-c1
[BOB] 🟡 The new tests cover symlinks to files, FIFOs, and devices. They leave open whether the existing walk records symlinks to directories. | File: skills/run-agoge/scripts/target_snapshot.py:319 | Task: 00025-gitdir-walk-hangs-on-fifo-v1-c1

R1: fail. R2 to R13: pass. D1 to D5: pass.

## Disposition

- No CRITICAL or HIGH. The outcome of review 1 does not change.
- Second finding: real, and older than PRD 00025. Probe, 2026-11-24:
  `.git/linked-hooks` pointed at one directory, `snapshot`, the link pointed at
  a second directory, `compare`: exit 0, `unchanged`. `os.walk` lists a symlink
  to a directory in its directory list, and `_gitdir_files` reads only the file
  list. Fix: PRD `00040-gitdir-directory-symlink-unseen-v1`.
- First finding: accepted, not fixed. It needs a regression of the fix under
  test before it can occur, and then the test fails loudly within two seconds.
  No PRD.
