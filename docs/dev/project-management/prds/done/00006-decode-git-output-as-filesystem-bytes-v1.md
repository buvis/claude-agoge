---
catchup: skip
design: skip
default_model: sonnet
model_tier_rationale: transcription only - exact expressions given, additive tests; tasks carry the premise re-check
---

# Decode git output as filesystem bytes in target_snapshot

Source: promoted from held stub 00006 (ledger `deferred/202611012029-deferred.json`, key d820bac9e229, raised against `00005-check-run-leaves-target-unchanged-v1.md`, which stays done with its capped review history).

## Problem

`_text()` in `skills/run-agoge/scripts/target_snapshot.py` decodes git output with strict UTF-8 and strips all surrounding whitespace. Its callers read the repository top level (`rev-parse --show-toplevel`), ref names (`for-each-ref`), the HEAD ref (`symbolic-ref`), commit identities and reflog lines. A non-UTF-8 repository path or refname raises an uncaught UnicodeDecodeError. The script then exits 1 with a traceback. Exit 1 means "target changed", so a crash reads as an integrity violation, and the documented contract (exit 2, one `target_snapshot: <reason>` line) breaks. Any other unexpected error (an unreadable dirty file, for example) fails the same way. Strip also corrupts a path that ends in a space.

## Solution

Decode git output with `os.fsdecode` and drop only the trailing newline, so every path and refname round-trips byte for byte through the snapshot JSON (the JSON default ASCII escaping keeps lone surrogates as `\udcXX` escapes). Catch any unexpected exception at the CLI boundary and exit 2 with a single `target_snapshot: unexpected <repr>` line, so a crash can never look like "changed". The saved restore commands stay print-only, as the run-agoge skill already requires.

## Requirements

### Must have
- `_text` returns `os.fsdecode(result.stdout)` with only trailing newlines removed (`.rstrip("\n")`).
- `main` catches `Exception` after the `Fail` handler, prints `target_snapshot: unexpected {exc!r}` to stderr (one line) and returns 2.
- A snapshot and compare of a repository whose HEAD branch and another ref have non-UTF-8 names exit 0 when nothing changed, and report the changed non-UTF-8 ref by its fsdecoded name when one moves.
- An unreadable dirty tracked file makes `snapshot` exit 2 with exactly one `target_snapshot: ` line and no traceback.
- `CHANGELOG.md` `[Unreleased]` gets a `### Fixed` entry prefixed `**run-agoge**:`.

### Nice to have
- None.

## Implementation

### Module: target-snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: snapshot and compare git state with byte-faithful decoding; never let a crash exit 1
- **Exports**: unchanged (`take_snapshot()`, `compare()`, `main()`)
New symbols: `test_text_keeps_filesystem_bytes_and_trailing_space`, `test_non_utf8_refs_round_trip_through_snapshot`, `test_non_utf8_paths_round_trip`, `test_unreadable_dirty_file_exits_2_with_one_line`

Premise: `_text` is called at the rev-parse, for-each-ref, symbolic-ref, rev-parse HEAD, log and reflog sites and nowhere else. Re-check before editing with `rg -c "_text\(" skills/run-agoge/scripts/target_snapshot.py`; if a caller feeds `_text` anything that is not git output, skip that site and report it, never force.

### Dependencies
- target-snapshot: No dependencies (foundation)

## Tasks

### Phase 0: Foundation
- [ ] Add regression tests to `skills/run-agoge/scripts/test_target_snapshot.py` that fail against the old code - Acceptance: `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -k "filesystem_bytes or round_trip or unreadable"` fails on the unmodified script. Tests: `test_text_keeps_filesystem_bytes_and_trailing_space` (calls `_text` on a `subprocess.CompletedProcess` with stdout `b"/a/\xff b \n"`, expects `"/a/\udcff b "`); `test_non_utf8_refs_round_trip_through_snapshot` (writes `packed-refs` with `refs/heads/\xff` and later `refs/heads/\xfe`, points HEAD at the first, asserts exit 0 unchanged, then exit 1 with a ref violation named `os.fsdecode(b"refs/heads/\xfe")`, JSON loads); `test_non_utf8_paths_round_trip` (non-UTF-8 repo directory plus tracked and untracked file names; skip the test when the filesystem raises `OSError` on creation); `test_unreadable_dirty_file_exits_2_with_one_line` (rewrite `notes.txt` longer, `chmod 0o000`, `_assert_exit2`; skip when `os.geteuid() == 0`).

### Phase 1: Core
- [ ] Change `_text` in `skills/run-agoge/scripts/target_snapshot.py` to `return os.fsdecode(result.stdout).rstrip("\n")` (depends on: Phase 0) - Acceptance: the `_text` and round-trip tests pass; premise re-check above holds.
- [ ] Add `except Exception as exc: print(f"target_snapshot: unexpected {exc!r}", file=sys.stderr); return 2` after the `Fail` handler in `main`, and add the sentence "Any other unexpected error also exits 2." to the module docstring exit-code paragraph (depends on: Phase 0) - Acceptance: `test_unreadable_dirty_file_exits_2_with_one_line` passes.
- [ ] Add the `CHANGELOG.md` entry under `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot exits 2 with one diagnostic line, not 1 with a traceback, on non-UTF-8 repository paths, refnames or unreadable files` (depends on: Phase 1) - Acceptance: `rg -c "target snapshot exits 2" CHANGELOG.md` prints 1.

## Success Criteria

- `test_text_keeps_filesystem_bytes_and_trailing_space`, `test_non_utf8_refs_round_trip_through_snapshot`, `test_non_utf8_paths_round_trip` and `test_unreadable_dirty_file_exits_2_with_one_line` pass (the path test may skip where the filesystem forbids non-UTF-8 names; report that).
- Every pre-existing test in `skills/run-agoge/scripts/` still passes under `dev/bin/release-checks` (run once, after the last task).
- `docs/dev/project-management/prds/hold/` no longer holds the stub.
