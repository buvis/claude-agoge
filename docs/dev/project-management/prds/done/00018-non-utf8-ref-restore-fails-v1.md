---
lane: fast-track
design: skip
default_model: opus
model_tier_rationale: invented contract - byte-level shell quoting that must round-trip through bash and git; platform-split test
---
# The restore command printed for a moved non-UTF-8 ref fails when run

Source: agoge run 2026-11-08, finding 12 of 18 (LOW, mocked, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`compare` prints restore commands with ref names in Python's surrogate-escaped form (`refs/heads/bad-\udcff`). Git refuses that name, so the operator's one-step restore does nothing for a non-UTF-8 ref. The `[Unreleased]` CHANGELOG entry claims non-UTF-8 refnames are handled. The evidence is mocked: the ref existed only in an emulated `packed-refs`, because this macOS disk rejects such names.

## Solution

In `_ref_violation`, quote each word of the restore command with a helper `_shell_quote(word)`: when `word` does not encode as UTF-8 (`word.encode("utf-8")` raises `UnicodeEncodeError`), take `os.fsencode(word)` and emit a bash ANSI-C string `$'...'`, writing every byte outside printable ASCII, plus `'` and `\`, as `\xHH`. Otherwise return `shlex.quote(word)`. This applies to ref names and the repo path alike.

## Requirements

### Must have
- Running a printed restore line under `bash -c` for a moved non-UTF-8 packed ref puts the ref back, on a filesystem that accepts non-UTF-8 names.
- UTF-8 names print exactly as today.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: restore commands for non-UTF-8 refs quote the raw bytes so they run`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: print restore commands that run for non-UTF-8 names.
- **Exports**: none new
- New symbols: `_shell_quote`, `test_restore_command_puts_non_utf8_ref_back`, `test_utf8_restore_command_is_unchanged`
- **Risk**: the restore line becomes bash-specific for such names. macOS APFS rejects the loose ref file `update-ref` writes, so the restore test skips there and runs on CI Linux.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression test: first try to create a file named `b"probe-\xff"` in `tmp_path`; on `OSError`, `pytest.skip("filesystem rejects non-UTF-8 names: ...")` (same reason text as `test_non_utf8_paths_round_trip`). Otherwise write a non-UTF-8 ref into `packed-refs`, snapshot, move it, compare, run `violation["restore"]` with `bash -c`, assert the ref is back. A second test asserts a UTF-8 restore line is byte-identical to `shlex.quote` output. Reproduction from the run:

```
compare printed: "restore": "git -C .../r update-ref 'refs/heads/bad-\udcff' a9fc956... f606e91..."
running it: fatal: update_ref failed for ref 'refs/heads/bad-\udcff': refusing to update ref with bad name 'refs/heads/bad-\udcff'  rc=128
test_non_utf8_refs_round_trip_through_snapshot never checks restore
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_restore_command_puts_non_utf8_ref_back` and `test_utf8_restore_command_is_unchanged` - Acceptance: on Linux, `pytest -k "restore_command_puts_non_utf8"` fails on the unmodified script; on macOS it skips with the filesystem reason.
- [ ] Add `_shell_quote` and use it in `_ref_violation` (depends on: previous task) - Acceptance: `pytest -k "restore_command or restore_commands"` passes (non-UTF-8 case passes on Linux, skips on macOS).
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "quote the raw bytes so they run" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k restore_command` passes (one skip allowed on macOS); the full suite passes under `dev/bin/release-checks`.
