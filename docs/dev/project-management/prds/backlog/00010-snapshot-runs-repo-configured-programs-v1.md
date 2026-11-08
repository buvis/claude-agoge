# Taking a snapshot runs programs the repo's own git config names

Source: agoge run 2026-11-08, finding 4 of 18 (MEDIUM, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

The `git status` call inside `target_snapshot.py` honours the target's `core.fsmonitor` and clean filters (`filter.<x>.clean`, `filter.<x>.process`). A repo can therefore run any program during what the docstring calls a read-only check. Targets are the operator's own repos, so likelihood is low, but the claim "nothing runs" is false.

## Solution

In `_git`, pass `-c core.fsmonitor=false`. Read the local filter names (`git config --local --get-regexp '^filter\.'`, itself run with fsmonitor off) and pass `-c filter.<x>.clean= -c filter.<x>.process=` for each. Add a regression test with marker scripts.

## Requirements

### Must have
- A snapshot and compare of a repo with fsmonitor and clean-filter marker scripts leave no marker file.
- Snapshot output for an ordinary repo is unchanged.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot no longer runs the repo's fsmonitor or clean filter programs`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: closes the known vectors (fsmonitor, filters), not unknown config-driven executables. Disabling the clean filter can make status report a filtered file as modified; the snapshot then records more dirty paths, which is safe.

## Test Strategy

Regression test with marker scripts in a temp dir. Reproduction from the run:

```
scratch repo r1, local core.fsmonitor = marker script
target_snapshot.py snapshot r1 out/s1.json -> rc=0
marker.log: "fsmonitor 2 1794168886500536000" (and the same line twice more: three runs)
fsmonitor unset, .gitattributes "*.txt filter=trudy", filter.trudy.clean=<marker>, same-size edit with newer mtime
marker.log: "filter "
core.hooksPath (reference-transaction hook) and core.pager: not triggered
```

## Tasks

- [ ] Add the marker regression test; watch it fail.
- [ ] Add the config overrides in `_git`.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- Marker test passes; the full suite passes under `dev/bin/release-checks`.
