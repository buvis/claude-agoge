# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
