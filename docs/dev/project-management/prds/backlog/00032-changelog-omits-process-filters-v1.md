---
lane: solo
design: skip
default_model: sonnet
model_tier_rationale: one-line text edit with the exact wording given
---
# The changelog entry on fsmonitor and clean filters omits that process filters are also disabled

Source: agoge run 2026-11-15, finding 14 of 14 (LOW, verified, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 1 (edit the entry).

## Problem

`CHANGELOG.md` says: `- **run-agoge**: target snapshot no longer runs the repo's fsmonitor or clean filter programs`. The code in `target_snapshot.py` also disables `filter.<name>.process`, and the module docstring says so. The entry understates the protection, so a reader underrates it. Not a false claim.

Users hit: anyone who reads the changelog to learn what the snapshot refuses to run.

## Solution

Change that entry to: `- **run-agoge**: target snapshot no longer runs the repo's fsmonitor, clean or process filter programs`.

## Requirements

### Must have
- The entry names fsmonitor, clean and process filters.
- No second entry is added; the existing line is edited in place, in whichever section it sits now.

### Nice to have
- None.

## Implementation

### Module: changelog
- **Location**: `CHANGELOG.md`
- **Responsibility**: state what the code does.
- **Exports**: none
- **Risk**: none expected. If the entry already sits under a released version, editing it rewrites release notes; that is intended here, since the release did ship the process-filter protection.

### Dependencies
- changelog: No dependencies (foundation)

## Test Strategy

No new test: the behaviour is already covered and unchanged. The run's check that the claim is true:

```
With filter.evil.process and .clean set, the marker stayed empty at HEAD.
```

## Tasks

### Phase 0: Fix
- [ ] Edit the entry - Acceptance: `rg -F "fsmonitor, clean or process filter programs" CHANGELOG.md` hits once, and `rg -F "fsmonitor or clean filter programs" CHANGELOG.md` hits nothing.

## Success Criteria

- `CHANGELOG.md` carries the corrected line once.
