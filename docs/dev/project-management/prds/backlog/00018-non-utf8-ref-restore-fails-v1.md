# The restore command printed for a moved non-UTF-8 ref fails when run

Source: agoge run 2026-11-08, finding 12 of 18 (LOW, mocked, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`compare` prints restore commands with ref names in Python's surrogate-escaped form (`refs/heads/bad-\udcff`). Git refuses that name, so the operator's one-step restore does nothing for a non-UTF-8 ref. The `[Unreleased]` CHANGELOG entry claims non-UTF-8 refnames are handled. The evidence is mocked: the ref existed only in an emulated `packed-refs`, because this macOS disk rejects such names.

## Solution

When a ref name or path in a restore command does not round-trip through UTF-8, quote it from its filesystem bytes (`os.fsencode`) as a bash ANSI-C string, `$'refs/heads/bad-\xff'`. Other names keep `shlex.quote`.

## Requirements

### Must have
- Running a printed restore line under bash for a moved non-UTF-8 packed ref puts the ref back.
- UTF-8 names print exactly as today.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: restore commands for non-UTF-8 refs quote the raw bytes so they run`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Risk**: the restore line becomes bash-specific for such names. The fix is tested against an emulated ref unless CI Linux runs it on a real one.

## Test Strategy

Regression test: write a non-UTF-8 ref into `packed-refs`, snapshot, move it, compare, run `violation["restore"]` with `bash -c`, assert the ref is back. Reproduction from the run:

```
compare printed: "restore": "git -C .../r update-ref 'refs/heads/bad-\udcff' a9fc956... f606e91..."
running it: fatal: update_ref failed for ref 'refs/heads/bad-\udcff': refusing to update ref with bad name 'refs/heads/bad-\udcff'  rc=128
test_non_utf8_refs_round_trip_through_snapshot never checks restore
```

## Tasks

- [ ] Add the regression test; watch it fail.
- [ ] Quote undecodable names from bytes.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New test passes (locally and on CI Linux); the full suite passes under `dev/bin/release-checks`.
