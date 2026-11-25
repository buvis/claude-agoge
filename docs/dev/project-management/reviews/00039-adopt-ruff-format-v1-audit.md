# Decision Audit Log: 00039-adopt-ruff-format-v1

PRD: `00039-adopt-ruff-format-v1.md`
Started: 2026-11-25T05:44:31Z
Completed: 2026-11-25T05:44:31Z
Autonomous: 8  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: dev/bin/release-checks fails with exit 2 under agent sandbox because uvx requires writable ~/.local/share/uv/tools

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: R3: dev/bin/release-checks (and the CI/AGENTS.md commands) use uvx ruff, which cannot write ~/.local/share/uv/tools under the agent sandbox and exits 2 before any check runs

**Choice**: auto-fix: mechanical swap to a sandbox-safe invocation (uv run --with ruff ruff ...), verified working by Carl; queued as rework task 6

**Rationale**: single-voice but HIGH, and reproduced independently by this gate: the gate the PRD introduced cannot run in the environment the project's own agents use

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: R4-R10: seven single-voice Medium/Low findings (stale capsule discard instruction, no negative test for the gate ordering, unpinned ruff, style-commit isolation unproven, non-string ref diagnostic, file sizes, AGENTS.md uvx commands)

**Choice**: discard, recorded in docs/dev/project-management/reviews/00039-adopt-ruff-format-v1-ledger.json

**Rationale**: single-voice Medium/Low per the decision gate's classification rule; R10's substance is fixed by R3's rework task

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: dev/bin/release-checks:12 no longer matches the PRD's literal `uvx ruff` contract or its `rg -c "^uvx ruff "` acceptance check (now prints 0); the rework is justified but the PRD or a waiver should record it

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: AGENTS.md:6 still recommends sandbox-failing `uvx ruff` commands although the settled R10 discard assumed the R3 fix would update it; the settled reason no longer holds

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: The ledger says the sandbox fix also updates `AGENTS.md`. The guide still directs agents to use `uvx` for both pre-commit Ruff commands, so that workflow still hits the tool-directory failure the rework addressed.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: R1/R2/R3: release-checks and AGENTS.md deviate from the PRD's literal uvx ruff contract after the cycle-1 sandbox fix

**Choice**: swept into tail-sweep tasks 7 and 8

**Rationale**: cycle 2 converged with no CRITICAL/HIGH; three reviewers named the gate-script deviation and two named the AGENTS.md line, so both are multi-voice medium findings the tail sweep fixes before finalize

### [autonomous] 2026-11-25T05:44:31Z

**Decision**: R2 and R3 are one defect at AGENTS.md:6 that consolidate_findings.py left as two single-voice rows

**Choice**: merged by gate judgment into one two-voice finding (ALICE, BOB) instead of discarding both as single-voice

**Rationale**: same file and same line, same substance; Blake raised it independently too (ledger-dismissed), so discarding on row count would drop a three-sighting defect

### [deferred] 2026-11-25T05:44:31Z

**Decision**: Pre-existing over-50-line functions that the PRD forbids touching beyond formatting: take_snapshot (72 lines), compare (65), main (61), claim (52), test_env_identity_beats_exported_author (117) and others. No new function crosses the limit, but the reformat lengthened some of them.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-25T05:44:31Z

**Decision**: Pre-existing file-size debt (deferred as 00041) is now larger after reformatting: test_target_snapshot.py is 1126 lines and test_target_snapshot_state.py is 1038, both over the 800-line cap. The 800-line cap is not met, but this PRD (format only, "no manual edits") cannot fix it.

**Choice**: deferred

**Rationale**: deferred by review-close
