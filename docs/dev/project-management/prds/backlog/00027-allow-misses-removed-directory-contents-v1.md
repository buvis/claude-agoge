---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: matching rule given exactly; the run's reproduction is the test
---
# `--allow` on a removed directory does not exempt the files inside it

Source: agoge run 2026-11-15, finding 5 of 14 (MEDIUM, verified, lane walter), `docs/dev/project-management/audit-results/agoge-2026-11-15.md`. Decision: accepted, option 2 (prefix match plus a usage line).

## Problem

`compare` in `target_snapshot.py` matches `--allow` paths exactly. Removing an ignored or untracked directory yields one violation per entry, so a user cannot exempt a deliberately removed directory without listing every file in it. An empty removed ignored directory also needs the trailing slash to match. Stable.

Users hit: anyone who calls `compare --allow` with a directory, the run-agoge master included.

## Solution

Add `_allowed(path: str, allow: set[str]) -> bool`: strip one trailing `/` from the path and from each allow entry, then return true when the path equals an entry or starts with `entry + "/"`. Use it at every place `compare` consults `allow` (tracked, untracked-removed, untracked-modified, ignored-removed, touched).

Document the rule where a user reads it: the `--allow` sentence in the module docstring, and `help=` on the `--allow` argument so `compare --help` shows it.

## Requirements

### Must have
- `--allow igndir` and `--allow igndir/` each exempt `igndir/`, `igndir/f` and `igndir/sub/g`.
- `--allow ign` does not exempt `igndir/f` (a prefix matches whole path components only).
- An exact file path still exempts that file and nothing else.
- The docstring and `compare --help` both say that an allowed directory exempts everything under it.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target compare \`--allow <dir>\` now exempts everything under that directory, with or without a trailing slash`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: match an allowed path as itself or as a parent directory.
- **Exports**: none new
- New symbols: `_allowed`, `test_allow_directory_exempts_its_removed_contents`, `test_allow_prefix_matches_whole_components_only`
- **Risk**: prefix matching widens what one flag exempts. The run-agoge skill passes only the two profile file paths, so its own calls do not widen.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Reproduction from the run, to be restated as the test:

```
Ignored igndir/ with f and sub/g, then rm -r igndir.
--allow igndir gave exit 1 (three violations).
--allow igndir/ gave exit 1 (igndir/f, igndir/sub/g left).
Only all three paths together gave exit 0.
An empty removed ignored dir needs the trailing slash.
```

After the fix both `--allow igndir` and `--allow igndir/` give exit 0 with no violations. Add the same case for an untracked (not ignored) directory, and the negative case `--allow ign`, which must still exit 1.

## Tasks

### Phase 0: Fix
- [ ] Add `test_allow_directory_exempts_its_removed_contents` and `test_allow_prefix_matches_whole_components_only` - Acceptance: `pytest -k allow_directory_exempts` fails on the unmodified script.
- [ ] Add `_allowed` and use it in `compare`; update the docstring and the `--allow` help text (depends on: previous task) - Acceptance: `pytest -k "allow_directory or allow_prefix"` passes, and `python3 skills/run-agoge/scripts/target_snapshot.py compare --help` mentions directories.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "exempts everything under that directory" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- Both new tests pass; the full suite passes under `dev/bin/release-checks`.
