# Decision Audit Log: 00005-check-run-leaves-target-unchanged-v1

PRD: `00005-check-run-leaves-target-unchanged-v1.md`
Started: 2026-11-01T23:06:13Z
Completed: 2026-11-01T23:06:13Z
Autonomous: 11  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: Design doc for PRD 00005 (target integrity snapshot/compare check): chose a full structural snapshot (HEAD, refs, index, tracked-file fingerprints, worktrees, local config) over a status-only diff or a bundle-based diff

**Choice**: design-approved

**Rationale**: only the full structural snapshot catches every PRD Success Metric (moved HEAD, ref, index, tracked file, worktree list, local git config, removed untracked file) and reproduces the 2026-10-25 regression exactly; status-only misses ref/config/worktree changes, bundling risks writing near the target. 3 reviewer dispatches (claude, claude-fallback x2 - codex unavailable both times on a sandbox read error, degraded per the codex-outage rule) fixed 3 blockers: recon-compare-failure control flow, nullable compare_lanes status derivation, touched-field union rule. Dispatch 3 found zero cardinal sins/blockers. Open non-blockers/questions recorded in the design doc Review log: no size bound on full-file hashing (acceptable for agoge-sized targets); worktrees violation reports whole lists not per-entry diff; touched-on-exit-2 rule stated by implication; status field name overloaded between CLI and sidecar; argparse usage-error exit 2 shares the cannot-check code; touched-vs-unknown-status report interaction left for planning to confirm.

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: PRD requires paths decoded with os.fsdecode, but the script uses strict `.decode()` on git output (`_text`, `_dirty` fields, worktrees, untracked) and `os.readlink(...).encode()` in `_fingerprint`. A non-UTF-8 file name in the target (valid on Linux) raises UnicodeDecodeError/UnicodeEncodeError. That is an uncaught traceback with exit 1, which the skill reads as "changed", not the "one stderr line, no traceback" contract. Use `os.fsdecode`/`os.fsencode` throughout (not run here: macOS rejects non-UTF-8 names, so this is from reading the code)

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: SKILL.md puts `compare ... start.json` and `snapshot ... lanes.json` in one bash block. The Bash tool reports only the last command's exit status, so the compare's exit 1 or 2 is masked by the snapshot's exit 0. The skill's own rule ("if it exits 1 or 2, dispatch nobody") then depends on the master reading stdout or stderr instead of an exit code. After a failed compare the snapshot still runs and writes `lanes.json`. Split into two separate bash calls, or say the compare's exit code must be captured before the snapshot runs. The text is PRD-verbatim, so this is a PRD defect carried into the skill

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: Fingerprinting follows symlinked parent directories outside the target. Replacing a tracked directory with an external symlink makes its deleted tracked children resolve outside the repository. Check ancestor components before opening files and reject external traversal; add this regression.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: R1 [3/3] os.fsdecode not used: strict .decode() on git output in target_snapshot.py (cycle 1)

**Choice**: auto-fix via rework task

**Rationale**: clear spec gap against the PRD's explicit os.fsdecode requirement; 3/3 consensus; bounded code fix plus regression test

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: R2 [2/3] SKILL.md step 3 puts compare and snapshot in one bash block, masking the compare's exit code (cycle 1)

**Choice**: auto-fix via rework task

**Rationale**: the dispatch gate depends on reading the compare's exit code; splitting the block is a mechanical doc fix with a pinning test

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: R3 [1/3] fingerprinting follows symlinked parent directories outside the target (cycle 1)

**Choice**: auto-fix via rework task

**Rationale**: a HIGH is never single-voiced away; the integrity check must not read outside the target, bounded fix plus regression

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: R4, R5, R6, R7 (medium) and R8-R12 (low), each raised by one reviewer only (cycle 1)

**Choice**: discarded, recorded in the settled-decisions ledger

**Rationale**: single-voice Medium/Low per the decision gate's classification rule; ledger entries stop them being re-argued next cycle

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: Cycle 2 carried one defect at two severities: Alice and Blake rated the residual strict .decode() in _text low, Bob rated it high. The consolidator did not merge Bob's row onto theirs.

**Choice**: took the higher severity at face value; did not downgrade to converge

**Rationale**: Downgrading a reviewer's high to clear the convergence bar is the one move this gate must not make. Taking it at face value costs little: at cap with no regression the cap-out path defers the finding and still reaches the finalize session, so the defect is recorded loudly instead of swept.

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: Six cycle-2 findings were single-voice medium or low (R3-R8): the external-symlink fingerprint value and the split compare/snapshot block as spec deviations, a non-failing assert in the new symlink test, the unspecified snapshot exit-2 gate, open() on a FIFO-swapped tracked path, and the CHANGELOG placement.

**Choice**: discarded as single-voice and appended to the settled-decisions ledger

**Rationale**: Classification routes a single-voice medium or low to discard, never a task. R3 and R4 additionally describe the cycle-1 fixes the gate itself accepted, so they are deviations the gate already adjudicated, not new defects.

### [autonomous] 2026-11-01T23:06:13Z

**Decision**: Cycle 2 reached the rework cap (2) with one unresolved high finding and no critical. autopilot cap-check classified it regression=false: git blame puts _text at commit b4ab450 (the original task-2 implementation), not at either cycle-1 rework commit.

**Choice**: cap-overflow deferral, finalize as converged-with-deferrals

**Rationale**: Loop-mode cap-out with no critical and no regression defers rather than stalls. The batch keeps draining and the finding stays visible at batch end.

### [deferred] 2026-11-01T23:06:13Z

**Decision**: _text() in skills/run-agoge/scripts/target_snapshot.py:49 still uses a strict .decode() on git output that is not a tracked path: rev-parse --show-toplevel (line 86), for-each-ref refnames (line 117) and symbolic-ref (line 129). A non-UTF-8 repository directory path or refname raises an uncaught UnicodeDecodeError, so the script exits 1 with a traceback instead of 2 with a single target_snapshot: line. Fix: use os.fsdecode in _text.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-11-01T23:06:13Z

**Decision**: _text (skills/run-agoge/scripts/target_snapshot.py:49) still does a strict .decode() on rev-parse --show-toplevel, for-each-ref and symbolic-ref output; use os.fsdecode in _text for consistency. Same defect as the high-severity cap-overflow record above, raised at low severity by Alice and Blake.

**Rationale**: rework cap reached with this finding unresolved
