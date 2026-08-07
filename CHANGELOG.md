# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **run-agoge**: the unarmed-row exception no longer arms the security lane from
  a row with no tactics; that row now reports `skipped` and points at
  `--refresh-profile`.
- **run-agoge**: PRD emission no longer assumes `CLAUDE_SKILL_DIR` is set. It is
  empty in at least some headless runs, where the documented command would have
  resolved to `/scripts/allocate_prd_number.py` and failed.

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
