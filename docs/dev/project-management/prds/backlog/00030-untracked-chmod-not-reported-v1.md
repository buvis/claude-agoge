---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: docstring sentence plus one test that pins the documented limit
---
# `chmod` on an untracked file is not reported by compare

Source: agoge run 2026-11-15, finding 9 of 14 (LOW, verified, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 2 (document that modes are ignored).

## Problem

The untracked-file fingerprint in `target_snapshot.py` holds content, not mode bits. A lane that runs `chmod` on an untracked file leaves the target changed and `compare` says `unchanged`. The module docstring lists what is and is not checked and says nothing about modes, so a reader cannot tell this is a limit and not a bug. The agoge profile expected `untracked-modified` here.

Users hit: anyone who reads an `unchanged` verdict as "nothing at all changed".

## Solution

Keep the behaviour. Add one sentence to the module docstring, beside "Edits inside ignored files are not checked": `Permission bits of untracked files are not checked; only content, file type and symlink target are.` The profile's walter row still expects `untracked-modified` here; the profile is recon's output and is not a file of this PRD (tracked as a follow-up in `docs/dev/project-management/audit-results/backlog-review-2026-11-17.md`).

Option 1 (add `stat.S_IMODE` to the fingerprint and bump `VERSION` to 5) was not chosen: git itself tracks only the exec bit.

## Requirements

### Must have
- The module docstring states that permission bits of untracked files are not checked.
- A test pins the documented behaviour, so a later change to mode tracking is a decision, not an accident.
- No CHANGELOG entry (docs and test only).

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`
- **Responsibility**: say what the check does not cover.
- **Exports**: none new
- New symbols: `test_untracked_mode_change_is_not_reported`
- **Risk**: a mode change on an untracked file stays unseen. That is the accepted cost of this option.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Reproduction from the run, restated as the pinning test. The behaviour half passes before and after. The test also asserts the docstring sentence, so it fails first: the fast-track lane stops a card whose new test is green before the change.

```
chmod 755 u.txt (was 644), then compare: exit 0 unchanged.
Rewrite and truncate give exit 1.
```

## Tasks

### Phase 0: Document
- [ ] Add `test_untracked_mode_change_is_not_reported` (an untracked file at mode 644 is `chmod`-ed to 755 between snapshot and compare: `compare` exits 0 with status `unchanged`; and `target_snapshot.__doc__`, with whitespace collapsed, contains `Permission bits of untracked files are not checked`) - Acceptance: `pytest -k mode_change_is_not_reported` fails on the unmodified script, whose docstring lacks the sentence.
- [ ] Add to the module docstring, beside "Edits inside ignored files are not checked", the sentence `Permission bits of untracked files are not checked; only content, file type and symlink target are.` (depends on: previous task) - Acceptance: `pytest -k mode_change_is_not_reported` passes.

## Success Criteria

- The docstring names the limit; the full suite passes under `dev/bin/release-checks`.
