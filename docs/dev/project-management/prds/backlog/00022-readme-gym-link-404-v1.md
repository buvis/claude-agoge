# The README link to the agoge-gym repo is a 404

Source: agoge run 2026-11-08, finding 17 of 18 (LOW, verified, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`README.md` says the pack is "calibrated against [buvis/agoge-gym](https://github.com/buvis/agoge-gym)". That repo does not exist publicly; readers hit a 404. The gym is a local eval repo by design, because its manifests are the answer key.

## Solution

Drop the link. Say the pack is calibrated against a private, local fixture gym (`buvis/agoge-gym`, not published). Leave `SKILL.md`'s gym notes alone unless they also link the URL.

## Requirements

### Must have
- `README.md` has no `https://github.com/buvis/agoge-gym` link and states the gym is private or local-only.
- `rg -n "github.com/buvis/agoge-gym"` over the repo returns nothing.

## Implementation

- **Location**: `README.md` (and `skills/run-agoge/SKILL.md` only if it links the URL)
- **Risk**: the gym stays undiscoverable. Docs-only change, no CHANGELOG entry required.

## Test Strategy

Reproduction from the run:

```
curl -s -o /dev/null -w "%{http_code}" https://github.com/buvis/agoge-gym -> 404
gh repo view buvis/agoge-gym -> "Could not resolve to a Repository"
local ~/git/src/github.com/buvis/agoge-gym: git remote -v printed nothing
```

## Tasks

- [ ] Replace the link with a local-only note.

## Success Criteria

- The `rg` check returns nothing; the full suite passes under `dev/bin/release-checks`.
