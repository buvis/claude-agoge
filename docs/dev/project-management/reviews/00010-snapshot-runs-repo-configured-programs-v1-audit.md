# Decision Audit Log: 00010-snapshot-runs-repo-configured-programs-v1

PRD: `00010-snapshot-runs-repo-configured-programs-v1.md`
Started: 2026-11-10T01:48:07Z
Completed: 2026-11-10T01:48:07Z
Autonomous: 13  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: PRD 00010 design: how to stop the target repo running its own configured programs (core.fsmonitor, filter.*.clean/process) during a read-only snapshot, including filter names containing =, spaces and dots, from every config scope and in submodules.

**Choice**: Neutralize at the single _git choke point: core.fsmonitor=false as a static override, plus per-repository discovery of effective filter.*.(clean|process|required) keys and empty-value overrides carried through the GIT_CONFIG_COUNT/KEY_n/VALUE_n env transport. Discovery cached per realpath so submodules discover independently; discovery failures fail closed to exit 2. _dirty keeps its -c core.bigFileThreshold=1m unchanged.

**Rationale**: Command-line -c cannot express a filter name containing = (git parses filter.a=b.clean=x as key filter.a), which is exactly how the parked attempt was bypassed. Measured on git 2.56.0: -c beats the env transport for the same key, the later GIT_CONFIG_COUNT index wins, an empty value disables a filter without spawning anything, and an unscoped git config --includes --get-regexp reaches local, global, include.path, matching includeIf, worktree and submodule config. 3 review dispatches (1 claude, 2 claude-fallback after codex sandbox failure), 4 blockers raised and all fixed, 0 open.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: Design review carried one open non-blocker to planning: target_snapshot VERSION stays 4 while the dirty map VALUES change on a normalizing-filter target, so a v4 snapshot taken before this change and compared after it can report spurious tracked violations (exit 1) on an untouched repo. The operator s own global config declares filter.lfs.clean/process/required, so every target discovers and disables lfs.

**Choice**: Do NOT bump VERSION. Task 3 pins VERSION at 4 and records the cross-build comparison as out of contract.

**Rationale**: Simplest safe assumption, and two PRD facts decide it: the PRD requires snapshot output for an ordinary repo to be unchanged (a bump changes it), and snapshot/compare are contractually a same-build pair in agoge s own use (the master takes the snapshot and compares it within one run). Bumping would also force an edit to test_previous_version_snapshot_exits_2_with_one_line, widening the diff for a hazard the product never hits.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: `_base_env` preserves `GIT_CONFIG`, which can redirect `git config` discovery to an empty file while `git status` still reads repository filters. This leaves configured programs executable. Strip `GIT_CONFIG` and add a marker regression with an empty alternate config, proving the bare-status control fires and snapshot/compare suppress it.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: `test_snapshot_does_not_run_fsmonitor`, `test_snapshot_does_not_run_clean_filter`, `test_snapshot_does_not_run_clean_filter_named` and `test_snapshot_does_not_run_clean_filter_from_any_source` each inline the positive-control block (status, assert log non-empty, unlink). `_assert_program_ran` was extracted for exactly that block, and the first two tests also inline what `_capture_untouched` does. Use the helpers.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: Must-have says marker tests cover clean and process filters from local, global, included, conditional-include, worktree and submodule configuration. The source matrix `_FILTER_SOURCES` (test_target_snapshot.py:1547) configures only `filter.<x>.clean` through `_configure_filter`. The only process-filter marker test is local-only (`test_snapshot_does_not_run_required_process_filter`). The code treats clean and process identically, so the risk is low, but the matrix is incomplete.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: `test_target_snapshot.py` is 1936 lines against the 800-line limit. It was already about 1280 lines before this diff, which adds 654. Splitting the does-not-run suite into `test_target_snapshot_programs.py` would fix it.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: R3 (cycle 1): _base_env preserves GIT_CONFIG, so an inherited GIT_CONFIG blinds filter discovery while git status still runs the repo's clean filter

**Choice**: auto-fix via [D1] task 5 at opus

**Rationale**: Reproduced directly by the decision gate (discovery exit 1 with GIT_CONFIG=empty file, marker still ran on git status), so it is not taken on Carl's contaminated consensus. It defeats the PRD's central must-have; the fix is additive (strip GIT_CONFIG, add a marker regression). Kept at opus because the PRD's default_model rationale is exactly git-config precedence.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: R1, R2, R4 (cycle 1): test helpers not reused, process-filter source matrix incomplete, test module 1936 lines against the 800 limit

**Choice**: auto-fix via [D1] task 6, tier lowered from the passed default opus to sonnet

**Rationale**: All three are mechanical and additive (reuse _assert_program_ran/_capture_untouched, parameterize the source matrix over clean and process, split the does-not-run suite out). No red row routes to this task, so the default_model floor does not apply and the documented sonnet default governs; measured opus rework runs 3-4x longer for no gain.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: R5-R9, R11-R17 (cycle 1): twelve single-voice medium and low findings

**Choice**: discarded, ledgered as single-voice

**Rationale**: Each was raised by one reviewer only; the gate's single-voice rule discards a medium or low [1/N] row and ledgers it so a re-raise is auto-dismissed next cycle. Blake's grandchild-submodule probe (R9) and Alice's GIT_CONFIG_PARAMETERS gap (R5) are recorded in the ledger with their evidence rather than lost.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: Cycle 1 lens degradation: the fail-first replay was skipped (runner exit 4, test path not found from the replay worktree) and Carl read Bob's output file mid-run

**Choice**: logged and continued; R3 verified by the gate itself instead of by consensus

**Rationale**: Graceful degradation per the Safety Checks table: four reviewers produced parseable output and the tautological-shape lens still ran. Carl's three findings are treated as echoes, not independent votes, so the one high finding was reproduced directly rather than trusted. The replay-cmd path mismatch is recorded here so a later cycle can fix the --replay-cmd working directory.

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: Task 6 finding claims splitting the does-not-run suite out of test_target_snapshot.py brings it under 800 lines; the remainder is ~1150 lines, so one split cannot satisfy the limit

**Choice**: widened the task-6 allowlist with a second split module (test_target_snapshot_state.py) and re-dispatched Ivan at the same sonnet tier (spec-gap repair, not a capability escalation)

**Rationale**: the finding's intent is the 800-line limit, not the specific one-file split it guessed at; Ivan measured the remainder and reported the gap instead of guessing

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: TEST_ENV inherits the caller's GIT_CONFIG_COUNT/KEY_*/VALUE_* command-scope pairs, so an ambient core.fsmonitor override makes the two fsmonitor positive controls fail (snapshot_fixtures.py:11)

**Choice**: severity adjudicated from Carl's high to medium, then swept by the tail sweep for a real fix

**Rationale**: reproduced directly by this gate (2 failed with GIT_CONFIG_KEY_3=core.fsmonitor), so not single-voice; product code is unaffected, the failure is loud rather than a false pass, and the non-hermetic TEST_ENV predates this PRD's work range at 8c1bf7b

### [autonomous] 2026-11-10T01:48:07Z

**Decision**: `TEST_ENV` inherits the caller's `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_*` / `GIT_CONFIG_VALUE_*` command-scope pairs from `os.environ`, so an ambient `core.fsmonitor` override beats the repo-local one the fixture sets. `test_snapshot_does_not_run_fsmonitor` and `test_snapshot_does_not_run_submodule_only_fsmonitor` then fail on their positive control. Strip the command-scope family (and `GIT_CONFIG`) from `TEST_ENV`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [deferred] 2026-11-10T01:48:07Z

**Decision**: The supplied mechanical check identifies an either-or hedge in `test_every_gitdir_entry_is_checked_or_listed`.

**Choice**: deferred

**Rationale**: deferred by review-close
