# Read the agoge profile from dev/local/meta/

Source: 2026-08-23 `~/.claude` layout change - keepers moved from `dev/local`
root to `dev/local/meta/` (canonical), with compat symlinks left at root so
released plugins keep working. This PRD repoints agoge so the symlinks can
retire (`~/.claude` PRD 00139 removes them once all plugin repoints ship).

## Overview

### Problem Statement

The profile path `dev/local/agoge-profile.md` is a shipped contract: it appears
in `skills/run-agoge/SKILL.md` (profile location AND the authorization
assertion line `Asserted by: profile (dev/local/agoge-profile.md)`),
`references/finding-contract.md`, `scripts/test_agoge_registry.py`, and
`README.md`. On migrated stores it resolves only through a root compat symlink;
when the symlinks retire, every armed run loses its authorization source.

### Success Metrics

- `rg -n "dev/local/agoge-profile" .` returns only `dev/local/meta/...` forms
  (plus the documented root fallback sentence).
- An armed run on a migrated target repo asserts authorization from
  `dev/local/meta/agoge-profile.md`; an unmigrated repo still works via the
  root path.

## Functional Decomposition

### Capability: profile resolution is meta-first with root fallback

The profile is `dev/local/meta/agoge-profile.md` in the target repo, falling
back to `dev/local/agoge-profile.md` when meta/ has none. The authorization
assertion line names whichever path actually resolved.

## Implementation Phases

### Phase 1: Repoint and release

1. `skills/run-agoge/SKILL.md`: profile location prose, the authorization
   table row, and the recon dispatch instructions -> meta-first path with the
   fallback sentence.
2. `references/finding-contract.md` and `README.md`: same repoint.
3. `scripts/test_agoge_registry.py`: update the pinned path assertions; add
   the fallback case if the test harness exercises resolution.
4. CHANGELOG entry under `### Changed`.
5. Release and update the installed plugin - a plugin fix is not done until it
   ships (`~/.claude` PRD 00118 precedent).

*Acceptance:* success metrics above; registry tests green.

## Test Strategy

- `test_agoge_registry.py` binds the contract path; extend it to cover
  meta-first resolution and the root fallback.

## Risks

- **Authorization gate wording**: the asserted-by line is compared verbatim in
  the unattended gate - update both sides in the same release or armed runs
  fail closed (which is at least the safe direction).
