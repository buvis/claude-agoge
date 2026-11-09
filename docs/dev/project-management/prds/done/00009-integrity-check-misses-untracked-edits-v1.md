---
lane: full
design: skip
default_model: sonnet
model_tier_rationale: explicit two-list union and violation contracts; additive regression tests
---
# Overwriting an existing untracked file or deleting an ignored file in the target goes undetected

Source: agoge run 2026-11-08, finding 3 of 18 (HIGH, verified, lanes heidi and walter), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records untracked files by name only and ignored files not at all. A lane that overwrites the operator's uncommitted notes or deletes an ignored `.env` passes the integrity gate. These are the files hardest to recover, because git holds no copy.

## Solution

Keep the snapshot's `untracked` key as it is (a sorted list; `test_non_utf8_paths_round_trip` asserts its shape). Add a key `untracked_fingerprints`: a map from each untracked path to `_fingerprint` (the same function dirty tracked files use); a changed fingerprint for a path present in both snapshots is reported as `{"kind": "untracked-modified", "path": ...}`. Add a key `ignored`: the sorted, deduplicated union of two NUL-delimited listings: `git ls-files -o -i --exclude-standard -z` (individual files, including children of ignored directories) and the same command with `--directory` (including empty ignored directories). Decode paths with `os.fsdecode`. Do not fingerprint ignored paths: their contents are outside this contract. A name present before and absent after is reported as `{"kind": "ignored-removed", "path": ...}`. Bump `VERSION` by one from its execution-time value. State in the module docstring and in `skills/run-agoge/SKILL.md` step 3 that edits inside ignored files are not checked.

## Requirements

### Must have
- Overwriting a pre-existing untracked file makes `compare` exit 1 with kind `untracked-modified`.
- Deleting a pre-existing ignored file or directory makes `compare` exit 1 with kind `ignored-removed`.
- Deleting one child of a directory ignored by `vault/`, while another child remains, reports the deleted child's path. Deleting an empty ignored directory also reports removal.
- Ignored paths are names only; do not read ignored file contents or block on ignored FIFOs.
- `--allow` exempts both kinds like other path kinds.
- The limit (ignored-file edits unchecked) is stated in the docstring and `SKILL.md` step 3.
- `VERSION` is bumped by one; an older snapshot file exits 2 with one line.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects overwritten untracked files and deleted ignored files`.

### Nice to have
- None.

## Implementation

### Module: target_snapshot
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `skills/run-agoge/SKILL.md`, `CHANGELOG.md`
- **Responsibility**: fingerprint untracked files and record ignored names.
- **Exports**: `VERSION` (bumped)
- New symbols: `untracked_fingerprints`, `test_overwritten_untracked_file_is_untracked_modified_violation`, `test_deleted_ignored_file_is_ignored_removed_violation`, `test_deleted_ignored_dir_is_ignored_removed_violation`, `test_allow_exempts_untracked_modified_and_ignored_removed`
- **Risk**: hashing large untracked trees costs time, linear in bytes. Enumerating ignored children costs time proportional to the listing. Edits to ignored files stay invisible by design. PRDs 00011 and 00019 are done: preserve special-file handling and chunked hashing.

### Dependencies
- target_snapshot: No dependencies (foundation)

## Test Strategy

Regression tests for both kinds. Reproduction from the run:

```
heidi: notes.md untracked at snapshot; echo CLOBBERED > un/notes.md; compare un -> rc=0 unchanged [] touched= []
heidi: delete ignored .env -> rc=0 unchanged
walter: wrote REWRITTEN into preexisting-untracked.txt, rm -r ignored/ ->
  compare reported only [('tracked', 'new\nline.txt'), ('tracked', 'čeština ü.txt')]
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_overwritten_untracked_file_is_untracked_modified_violation`, `test_deleted_ignored_file_is_ignored_removed_violation`, `test_deleted_ignored_dir_is_ignored_removed_violation`, `test_allow_exempts_untracked_modified_and_ignored_removed` - Acceptance: `pytest -k "untracked_modified or ignored_removed"` fails on the unmodified script.
- [ ] Extend the ignored-removal cases to cover a deleted child with a surviving sibling, an empty ignored directory, an ignored FIFO with a 10-second subprocess timeout, and exact-path allow exemptions (depends on: previous task) - Acceptance: the child-deletion case fails against the parked branch; ignored contents are never fingerprinted; all cases pass after implementation.
- [ ] Implement the untracked fingerprint map, the `ignored` key and the version bump (depends on: previous task) - Acceptance: `pytest -k "untracked_modified or ignored_removed or untracked"` passes.
- [ ] Document the limit; add the CHANGELOG entry (depends on: previous task) - Acceptance: `rg -n "ignored" skills/run-agoge/SKILL.md` hits in step 3 and the docstring names the limit; `rg -F "detects overwritten untracked files" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "untracked_modified or ignored_removed"` passes; the full suite passes under `dev/bin/release-checks`.

## Retry evidence (2026-11-09)

Batch `202611082330` parked this PRD after a HIGH finding: `--directory` collapsed ignored children into their parent. Local probes confirmed that the two listings above retain both child paths and empty directory names. The parked branch `fast-track/00009-integrity-check-misses-untracked-edits-v1-c1` has three unmerged commits, ending at `951401a`; retain it as evidence. Implement against current master, reusing reviewed fragments only, because later PRDs changed this module. Do not merge the old module wholesale. Re-check the premise before implementation; if already fixed, report that evidence and skip redundant changes. Full-lane review must run in a fresh session under the normal autopilot workflow. Historical deferred records remain unchanged.
