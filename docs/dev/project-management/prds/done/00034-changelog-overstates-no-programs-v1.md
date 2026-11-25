---
design: skip
default_model: sonnet
model_tier_rationale: one-line text edit with the exact wording given
---
# The changelog reads as if the snapshot runs no repo programs

Source: agoge run 2026-11-16, finding 7 of 11 (LOW, verified, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-16.md`. Decision: accepted, option 1. Extends PRD 00032, which fixes only the `process` omission.

## Problem

The 0.3.1 entry says the snapshot "no longer runs the repo's fsmonitor or clean filter programs". It omits that other repo programs can still run (`core.pager`, hooks, `diff.external`), and that a disabled filter makes a file whose bytes differ from its filtered blob read as dirty. The docstring says both; the CHANGELOG does not.

Users hit: anyone who reads the changelog to learn what the snapshot refuses to run.

## Solution

Land after PRD 00032 (the batch order gives this). Edit the 0.3.1 line, in whichever form it has then (the original `... fsmonitor or clean filter programs` or the line PRD 00032 produced), to: `- **run-agoge**: target snapshot no longer runs the repo's fsmonitor, clean or process filter programs; other repo-configured programs such as core.pager, hooks and diff.external are not covered, and with a filter disabled a file that differs from its filtered blob reads as dirty`. Do not add `gpg` to this line: it sits under 0.3.1, which did not ship the gpg fix. PRD 00033 adds its own `[Unreleased]` entry for gpg.

## Requirements

### Must have
- The line names fsmonitor, clean and process filters, states the uncovered programs, and states the extra-dirty effect.
- The existing line is edited in place; no second entry.

### Nice to have
- None.

## Implementation

### Module: changelog
- **Location**: `CHANGELOG.md`
- **Responsibility**: state what the code does and does not do.
- **Exports**: none
- **Risk**: if the line sits under a released version, this rewrites release notes; intended, as in PRD 00032.

### Dependencies
- changelog: No dependencies (foundation)

## Test Strategy

No new test; behaviour is unchanged. The run's check:

```
CHANGELOG.md line 30: "target snapshot no longer runs the repo's fsmonitor or clean filter programs"
HEAD: core.fsmonitor, filter.cf.clean, filter.pf.process markers all absent after snapshot.
Docstring: "it is not a claim that nothing a repo configures can run".
```

## Tasks

### Phase 0: Fix
- [ ] Edit the entry - Acceptance: `rg -F "other repo-configured programs such as core.pager" CHANGELOG.md` hits once, and `rg -F "fsmonitor or clean filter programs" CHANGELOG.md` and `rg -F "fsmonitor, gpg" CHANGELOG.md` each hit nothing.

## Success Criteria

- `CHANGELOG.md` carries the corrected line once.
