# Assumptions ledger — PRD 00009 (integrity-check-misses-untracked-edits)

## 1: Add failing regression tests for untracked-modified and ignored-removed

- Added a private helper `_commit_gitignore(target, env, *rules)` in the test file so three tests share the write-add-commit of `.gitignore`.
- The expected violation order in the ignored-dir test was set from the contract, not observed, because the tests fail before ordering is reached.

## 2: Extend ignored-removal tests: surviving sibling, empty dir, FIFO, unreadable file, exact-path allow

- `test_ignored_fifo_does_not_hang` calls `_run` directly for snapshot and compare so it can pass `timeout=10`, and reads violations from the compare stdout JSON.
- Orchestrator note: the implementor's edit was followed by a whole-file formatter reflow of the test file (known churn, see project capsule); the reflow was discarded and only the five new tests were committed.

## 3: Implement untracked fingerprints, ignored-name listing and VERSION bump in target_snapshot

- Tess: the stderr reason text for a version mismatch is unspecified, so only the `target_snapshot: ` prefix and the single line are checked.
- Tess: a snapshot with no `version` key counts as unusable and must exit 2 (suggested by the orchestrator; the PRD says only "older snapshot").
- Tess: cross-kind violation order is not pinned by the PRD, so strengthened assertions compare sorted `(kind, path)` pairs.
- Tess: nested untracked files sit beside a committed `sub/keep.txt` so git lists them individually.
- Orchestrator: the CHANGELOG line (task 5) was committed with this `fix` commit, because a `fix` commit must carry its changelog entry.
- Orchestrator: the per-task review ran on the native `autopilot:pat` Sonnet agent; the external `sonnet-run.sh` route failed twice (OAuth session expired, then a reused session id).

## 5: Add the CHANGELOG Unreleased Fixed entry

- Orchestrator: no dispatch. The exact PRD line was already committed with task 3's `fix` commit (5aef0a5); this task only verified it sits under `[Unreleased]` `### Fixed` (line 27, before `## [0.3.0]` at line 29).
