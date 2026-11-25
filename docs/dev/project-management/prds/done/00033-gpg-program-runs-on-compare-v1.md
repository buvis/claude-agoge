---
design: skip
default_model: sonnet
model_tier_rationale: add fixed config overrides and one marker test; every check fails loudly
---
# `compare` runs the target's `gpg.program` when a ref changes

Source: agoge run 2026-11-16, finding 1 of 11 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-16.md`. Decision: accepted, option 1 (add overrides).

## Problem

When a ref is new or changed, `compare` in `target_snapshot.py` runs `git log -1 --format=... <sha>` and `git reflog show` through `_ref_violation`. If the target's config sets `log.showSignature=true` and `gpg.program`, git runs that program on a commit with a `gpgsig` header. A hostile repo can create such a ref itself. The docstring's out-of-scope list does not name gpg, so this is a gap.

Users hit: the operator, when a lane or the target adds a ref during a run on an untrusted repo.

## Solution

Add these pairs to `_STATIC_OVERRIDES` so every git call the script makes carries them: `log.showSignature=false`, `gpg.program=false`, `gpg.ssh.program=false`, `gpg.x509.program=false`. Add `gpg.program` and `log.showSignature` to the docstring's statement of what the snapshot disables. The `_ref_violation` git calls must run with `_STATIC_OVERRIDES`.

## Requirements

### Must have
- With `gpg.program` set to a marker-writing script and `log.showSignature=true`, `compare` on a repo that gained a ref at a commit with a `gpgsig` header exits 1 and the marker file does not exist.
- A control in the same test proves the marker fires under plain `git log -1 <sha>` in that repo.
- The docstring names `gpg.program` as disabled.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer runs the repo's gpg program when a ref changes`.

### Nice to have
- None.

## Implementation

### Module: snapshot overrides
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_programs.py`, `CHANGELOG.md`
- **Responsibility**: no repo-configured signing program runs during snapshot or compare.
- **Exports**: none
- New symbols: `test_compare_does_not_run_gpg_program_on_new_signed_ref`
- **Risk**: the deny-list covers only the names above; a new signing hook in a future git is missed. Signature text no longer appears in `git log` output (the script does not use it).

### Dependencies
- snapshot overrides: No dependencies (foundation)

## Test Strategy

Use the helpers in `snapshot_fixtures.py`. Build the signed commit with `git hash-object -t commit -w`. Run `compare` through the same runner other program tests use, with a timeout.

```
scratch repo: gpg.program=<marker script>, log.showSignature=true
snapshot, then add refs/heads/evilref at a commit with a fake gpgsig header
target_snapshot.py compare -> exit 1 (ref violation), marker file gained "gpgprog" twice
git log -1 --format=%an <sha> -> marker gained a third "gpgprog" line
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_compare_does_not_run_gpg_program_on_new_signed_ref` in `skills/run-agoge/scripts/test_target_snapshot_programs.py` (the target sets `gpg.program` to a marker-writing script and `log.showSignature=true`; after `snapshot`, add `refs/heads/evilref` at a commit with a `gpgsig` header built with `git hash-object -t commit -w`; `compare` exits 1 under a timeout and the marker file does not exist; then, as a control in the same test, plain `git log -1 <sha>` in that repo writes the marker) - Acceptance: `pytest -k gpg_program` fails on the unmodified script.
- [ ] Add `("log.showSignature", "false")`, `("gpg.program", "false")`, `("gpg.ssh.program", "false")` and `("gpg.x509.program", "false")` to `_STATIC_OVERRIDES`, and name `gpg.program` and `log.showSignature` in the docstring's statement of what every git call refuses to run (depends on: previous task) - Acceptance: `pytest -k gpg_program` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "no longer runs the repo's gpg program" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k gpg_program` passes; the full suite passes under `dev/bin/release-checks`.
