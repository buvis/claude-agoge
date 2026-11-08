# A crafted before.json puts git options into the printed restore command

Source: agoge run 2026-11-08, finding 11 of 18 (LOW, verified, lane trudy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`compare` builds `restore` command strings from ref names and values loaded from the snapshot file. Shell metacharacters are quoted with `shlex.quote`, but a name or value that starts with a dash reaches git as an option (`update-ref --stdin`). Exploiting it needs someone to tamper with the master's scratch snapshot and the operator to run the printed line, so the risk is low.

## Solution

In `_load`, validate the snapshot: every ref name is `HEAD` or starts with `refs/`, and every ref value is a hex object id (40 or 64 characters) or null. Otherwise exit 2 with one line.

## Requirements

### Must have
- A snapshot file with a ref named `--stdin`, or a value `--no-deref`, makes `compare` exit 2 with one line.
- Valid snapshots load as before.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target compare rejects a snapshot file with malformed ref names or ids`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: a valid but unusual ref could be rejected; check what `for-each-ref` can emit (for example `refs/stash`, notes) against the rule.

## Test Strategy

Reproduction from the run (the printed lines were not executed):

```
before.json ref keys: --stdin, "; echo TRUDY #", refs/heads/$(echo TRUDY) (value --no-deref); compare -> rc=1
restore = git -C …/r2 update-ref --stdin x ''
restore = … update-ref 'refs/heads/$(echo TRUDY)' --no-deref ''
```

## Tasks

- [ ] Add the regression test; watch it fail.
- [ ] Add the validation in `_load`.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes; the full suite passes under `dev/bin/release-checks`.
