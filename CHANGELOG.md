# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **run-agoge**: restore commands for non-UTF-8 refs quote the raw bytes so they run
- **run-agoge**: target compare rejects a snapshot file with malformed ref names or ids
- **run-agoge**: PRD number allocation now refuses a path that is not a git work-tree top level, and refuses a missing path, instead of silently creating `docs/` in the wrong place; refusal exits 2 with one diagnostic line and ignores an inherited GIT_DIR and related variables
- **run-agoge**: PRD number allocation refuses to write through a symlink that leaves the repo, instead of following `prds` or `backlog` out and creating the claimed file there
- **run-agoge**: target snapshot handles non-UTF-8 repository paths and refnames and keeps trailing spaces in paths. Any other unexpected error, such as an unreadable file, now exits 2 with one diagnostic line, not 1 with a traceback
- **run-agoge**: emitted PRDs follow create-prd's minimal template, with module and dependency blocks, a phase heading and an acceptance check on every task, so an unattended autopilot loop can plan them without guessing
- **run-agoge**: concurrent PRD claims with different slugs get distinct numbers
- **run-agoge**: target snapshot now detects changed git hooks, `.git/info/exclude`, `.git/info/attributes` and worktree-local config, so a lane that plants a hook no longer passes integrity as unchanged
- **run-agoge**: target snapshot no longer hangs on a named pipe in place of a tracked file; it now reports it as a tracked violation instead of blocking the integrity gate forever
- **run-agoge**: target snapshot ignores an inherited GIT_DIR and related variables
- **run-agoge**: target snapshot now detects changes in linked worktrees and submodules, reporting a moved HEAD in a linked worktree (`worktree-head`) and any commit, edit or new file inside a checked-out submodule (`submodule`); an uninitialized submodule is still unchecked
- **run-agoge**: PRD number allocation now rejects a slug with a trailing newline instead of silently accepting it

## [0.3.0] - 2026-11-02

### Fixed

- **run-agoge**: a lane can no longer fall through into the target's own git
  repository. Every dispatch and the recon prompt carry a scratch contract: one
  scratch root outside the target, a `set -eu` and `GIT_CEILING_DIRECTORIES`
  preamble, explicit `--git-dir` on scratch git writes, a per-command lane
  identity, and a read-only target. A heidi lane whose scratch `git init`
  failed inside the target once committed, tagged and moved a remote-tracking
  ref in the product.

### Added

- **run-agoge**: the master snapshots the target before recon and again before
  the lanes, with the new `scripts/target_snapshot.py`, and compares after
  each. A moved HEAD or ref, a changed index, tracked file, worktree list or
  local git config, or a removed untracked file fails the run; the report and
  the sidecar's `target_integrity` list each change, with a restore command for
  the operator.

## [0.2.0] - 2026-11-01

### Changed

- **run-agoge**: read and write durable project-management artifacts under
  `docs/dev/project-management/`, with temporary assets under `docs/dev/tmp/`.
  Nothing under `dev/local/` is read any more: move an existing profile and any
  unwalked report to the new location.
- **run-agoge**: every finding in the JSON sidecar carries `lanes`, the lanes
  merged into it, so `agoge-gym`'s scorer can tell a lane's own catch from
  another lane's by-catch, and a `title` that names the defect, which that
  scorer now matches. The gym notes point at the arm `bin/arm` prints, outside
  the gym, and say to copy a run's report out before re-arming.

## [0.1.4] - 2026-08-26

### Changed

- **run-agoge**: the strategy profile is read from
  `dev/local/meta/agoge-profile.md`, falling back to the older
  `dev/local/agoge-profile.md` when `meta/` has none. The security lane's
  `Asserted by: profile (<path>)` line now names whichever path resolved, so
  an armed run keeps its authorization source once the root compat symlinks
  retire.

## [0.1.3] - 2026-08-26

### Fixed

- **run-agoge**: specialists are now dispatched as `agoge:<persona>`. The skill
  named them bare, which a plugin-owned agent never resolves as, so recon failed
  to dispatch, no lane got a strategy row, and the run still wrote a report that
  read like a pass.

## [0.1.2] - 2026-08-25

### Fixed

- **run-agoge**: a vetoed security-lane run authorized both by the profile
  line and `--authorized <source>` now records no `source` (the profile
  wins), the same precedence part 5 already states for the non-vetoed case.
  That combined case previously had two live rules pulling different ways
  with no stated tiebreaker.

## [0.1.1] - 2026-08-17

### Fixed

- **run-agoge**: a profile row with no tactics can no longer dispatch any
  specialist. The rule now governs the normal dispatch path as well as the
  unarmed-row exception, so an `armed` row with empty tactics reports `skipped`
  and points at `--refresh-profile` instead of probing blind while the report
  claims the lane ran armed.
- **run-agoge**: PRD emission no longer assumes `CLAUDE_SKILL_DIR` is set. It is
  empty in at least some headless runs, where the documented command would have
  resolved to `/scripts/allocate_prd_number.py` and failed.
- **run-agoge**: `--authorized <source>` is bounded to a single shell-word token
  (letters, digits, dash, underscore). Anything else is the same error as an
  empty source, so a source built from a branch or CI value cannot carry an
  instruction into the security lane's prompt.
- **run-agoge**: a run where the security lane is vetoed *and* `--authorized`
  was passed now records route `vetoed` and the overruled source, in both the
  report header and the sidecar. That case previously had no route value, so
  the one decision where the operator said no left no audit trail. All three
  veto cases are now defined: a veto over an `--authorized` assertion records
  the overruled token, a veto over a profile-line assertion records no source,
  and a veto with nothing asserted reads `none` rather than `vetoed`. Step 7
  of the skill, which is what actually writes the report, names all four
  routes instead of three.
- **run-agoge**: two gate wordings no longer read two ways. `--authorized` with
  no value is an error, while not passing it at all is not; and an absent or
  empty-valued `Authorization:` line now explicitly fails closed.

## [0.1.0] - 2026-08-06

### Added

- Initial release: one skill and seven agents.
  - `run-agoge` — the master skill: recon, armed-only dispatch, status audit,
    dedup, one report about the product rather than the diff, and a findings
    walkthrough that never auto-files its own results as work.
  - `olivia` — recon; inventories runnable surfaces and assigns each specialist
    an armed or unarmed strategy. The only agent that writes, and only the profile.
  - `walter` — journeys; runs the product end to end.
  - `heidi` — integration and database contracts, live where reachable and mocked
    where not.
  - `judy` — UX; drives a real interface, and skips loudly where there is none.
  - `wendy` — release truth; changelog, docs and upgrade path against reality.
  - `peggy` — performance; measured numbers, not impressions.
  - `trudy` — runtime security; behaviour under hostile input, gated on an
    explicit human authorization that no agent may write for itself.
- Execution playbooks for the browser, data, performance and security lanes,
  pasted verbatim into the dispatch that needs one.
- Finding, report and strategy-profile contracts, including the four-status rule
  (`verified` / `unverified` / `mocked` / `skipped`) and the downgrade rule that
  turns an unevidenced `verified` claim back into `unverified`.
- `--authorized <source>` for arming the security lane from an unattended runner,
  with the asserting act recorded in both the report and the JSON sidecar.
