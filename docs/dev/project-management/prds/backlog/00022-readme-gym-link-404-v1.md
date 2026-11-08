---
lane: solo
design: skip
catchup: skip
model_tier_rationale: one docs sentence; haiku acceptable, so default_model is omitted
---
# The README link to the agoge-gym repo is a 404

Source: agoge run 2026-11-08, finding 17 of 18 (LOW, verified, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`README.md` says the pack is "calibrated against [buvis/agoge-gym](https://github.com/buvis/agoge-gym)". That repo does not exist publicly; readers hit a 404. The gym is a local eval repo by design, because its manifests are the answer key.

## Solution

In `README.md`, replace the link with plain text: the pack is calibrated against `buvis/agoge-gym`, a private, local fixture gym that is not published. `skills/run-agoge/SKILL.md` names the gym without a URL and stays unchanged.

## Requirements

### Must have
- `README.md` has no `https://github.com/buvis/agoge-gym` link and states the gym is private and not published.
- `rg -n "github.com/buvis/agoge-gym" README.md skills agents` returns nothing. (The audit report and this PRD quote the URL as evidence; they are out of scope.)

### Nice to have
- None.

## Implementation

### Module: readme
- **Location**: `README.md`
- **Responsibility**: describe the gym without a dead link.
- **Exports**: none
- **Risk**: the gym stays undiscoverable. Docs-only change, no CHANGELOG entry required.

### Dependencies
- readme: No dependencies (foundation)

## Test Strategy

Reproduction from the run:

```
curl -s -o /dev/null -w "%{http_code}" https://github.com/buvis/agoge-gym -> 404
gh repo view buvis/agoge-gym -> "Could not resolve to a Repository"
local ~/git/src/github.com/buvis/agoge-gym: git remote -v printed nothing
```

## Tasks

### Phase 0: Fix
- [ ] Replace the link with a private, not-published note - Acceptance: `rg -n "github.com/buvis/agoge-gym" README.md skills agents` exits 1; `rg -n "agoge-gym" README.md` still hits once.

## Success Criteria

- The scoped `rg` check returns nothing; the full suite passes under `dev/bin/release-checks`.
