# agoge follow-ups, 2026-11-02 (continuation of the Codex handoff of 10:14 CET)

Measured 2026-11-02 around 10:50 CET. Each entry says what is done, what is verified, and what blocks the rest.

## 1. Snapshot decoding and exit-2 diagnostics (agoge PRD 00006)

Done and pushed (`master` `ce10d0b`):

- The held stub for ledger key d820bac9e229 became backlog PRD 00006 (kept its number) and ran through the fast-track lane, one card, all five review lenses.
- `_text` in `skills/run-agoge/scripts/target_snapshot.py` decodes with `os.fsdecode` and strips only the trailing newline. `main` turns any other unexpected error into exit 2 with one `target_snapshot: unexpected <Type>: '<message>'` line, so a crash cannot read as "target changed" (exit 1).
- Tests: `test_text_keeps_filesystem_bytes_and_trailing_space`, `test_non_utf8_refs_round_trip_through_snapshot`, `test_unreadable_dirty_file_exits_2_with_one_line`, `test_repo_dir_with_trailing_space_round_trips` pass; the first three fail against the pre-change script (fail-first shown at `c550b9b`).
- `dev/bin/release-checks`-equivalent suite (`uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q`): 167 passed, 0 failed, 1 skipped.
- Review: `docs/dev/project-management/reviews/00006-decode-git-output-as-filesystem-bytes-v1-review-1.md`, verdict converged, no CRITICAL or HIGH finding. Valid MEDIUM and LOW findings were fixed in `5281e9e`. PRD 00005's completed review history is untouched.

Not verified, and why:

- `test_non_utf8_paths_round_trip` skips on macOS APFS (Errno 92). The non-UTF-8 repository-directory, tracked-path and untracked-path round trip has not run anywhere. Run `-k round_trip` on Linux ext4 and expect `1 passed` for it.
- One full-suite run showed 6 failures from git subprocesses killed with SIGKILL (exit -9). An immediate re-run passed. The cause was not found.
- Review deviations: codex could not start its sandbox inside the host sandbox (`sandbox_apply: Operation not permitted`), so Bob's lens ran as a Claude opus subagent on the same prompt (reduced model-family diversity for that lens; Carl ran on gemini). The review-fanout Workflow tool was not used (it needs explicit user opt-in), so Alice ran as the consensus subagent.

Open: **the PRD is still in `prds/wip/` at the `done` gate.** `autopilot review-once` (the fresh-session finalize hop) fails twice at start with `Failed to authenticate: OAuth token revoked`. This is the captured error of these two launches, not the earlier `Write(**/dev/local/**)` rule error that the build audit mislabelled. `CLAUDE_CODE_OAUTH_TOKEN` is unset in the agent session; whether that is the cause is not confirmed. Re-authenticate, then run `/autopilot:run-autopilot` once in a fresh session; the done gate moves the PRD to `done/`, writes the batch report and the capsule. Nothing else in 00006 is pending.

## 2. Documentation branch `docs/agoge-0.3.0` (agent-skills, `56ba216`)

Reconciled by inspection, not edited. The branch mirrors SKILL.md and references of released 0.3.0. PRD 00006 changes only `target_snapshot.py`, its tests and agoge's `[Unreleased]` changelog; the mirror cites only "the snapshot exits 2, stop before recon", which stays true. No mirror edit is needed. The 00006 fix is unreleased; a later release needs its own mirror changelog line and fresh approval (not requested).

Integration blocked, and I did not integrate: the agent-skills closeout plan is still at Stage 1 (`repository-closeout-execution.md` records blocked/retry entries), the branch is not in its integration order, and the working tree carries five uncommitted closeout paths from another session (preserved untouched). The branch can only enter through the plan's review, approval and Stage 3 gates; add it to the plan's integration order when Stage 3 opens.

## 3. Push protection (old claude-autopilot PRD 00371 to OVCAQ 00060)

Carried by ownership map (requirements only; `claude-autopilot` is frozen and untouched):

- Loop arm, run and settle around the final agoge pass: supervision (source loop rows R13/R14) -> OVCAQ PRD 00060 (the orchestrator; Tower is the separate, planned watching layer and owns none of this). Added to `ovcaq/docs/dev/project-management/prds/backlog/00060-autopilot-supervisor-sync-v1.md`: a new feature "Agoge push hold around final QA", two files in the structure tree, a Phase 1 task, seven named scenarios (protection during the run, release when unchanged, repository change, failed comparison, interrupted run, old agoge without sidecar, undecodable path), two risks, and the dependency note.
- The guard that denies `git push` while a hold exists: plugin hook `guard_push_on_critical.py` (inventory UTIL-042, R01/R16) -> AP 00014 (`custody_push_denied`). Not edited here (peer PRD, 00013 still in review). Needs one line there: read `agoge-hold` entries beside custody. OVCAQ writes the hold file shape; the real guard's denial is 00014's acceptance.
- OVCAQ owns the check: its own snapshot comparison, independent of the agoge version or sidecar. Findings are kept; no restore command is ever run automatically.

Caveat: the `ovcaq` repo's `docs/dev/project-management/` is gitignored (`.gitignore:13`), so 00060 is an untracked local file. The edit is **uncommitted and unrecoverable from git**. That contradicts the global working-documents rule (never gitignore this tree). Un-ignoring it is a separate decision I did not make.

## 4. Verification counts (AP 00015, `agent-plugins`)

Reproduced against the port (`plugins/autopilot/scripts/verification.py`): a green `python -m pytest -q` run gives exit_code 0, `summary: null`, `reusable: false`. The build audit (`agoge-build-2026-11-02.md`) records the installed source verb exiting 3 with null counts on a green pytest run; I reproduced only the port's null counts, not that exit code. Cause: both parsers recognize only the custom `PASS n FAIL n SKIP n EXIT n` line, while `final-verification.md` promises "the runner's own summary line". The existing tests pin the custom line.

Decision (recorded in AP 00015, branch `docs/ap00015-verification-counts`, commit `a13212a`, pushed; no PR opened): correct the parser, keep the custom line, also accept pytest's final summary line (last complete line of either form wins, `failed` folds errors, exit_code from the process), keep null counts for no/`no tests ran`/malformed output, and keep timeout, cap, dirty-tree and moved-HEAD behavior. Seven named acceptance scenarios were added. Code is not changed: AP 00015 is gated on PRDs 00013 (in review under a peer) and 00014.

Blockers: AP 00015 execution waits for 00013 and 00014; the branch needs a peer merge into `master` of agent-plugins.
