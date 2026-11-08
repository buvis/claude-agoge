# Overwriting an existing untracked file or deleting an ignored file in the target goes undetected

Source: agoge run 2026-11-08, finding 3 of 18 (HIGH, verified, lanes heidi and walter), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`target_snapshot.py` records untracked files by name only and ignored files not at all. A lane that overwrites the operator's uncommitted notes or deletes an ignored `.env` passes the integrity gate. These are the files hardest to recover, because git holds no copy.

## Solution

Fingerprint each untracked path (same `_fingerprint` as dirty tracked files) and report a changed hash as new kind `untracked-modified`. Record the names of ignored paths (`git ls-files -o -i --exclude-standard --directory`) so a deletion is reported as `ignored-removed`. Document in the module docstring and in `SKILL.md` step 3 that edits to ignored files are not checked.

## Requirements

### Must have
- Overwriting a pre-existing untracked file makes `compare` exit 1 with kind `untracked-modified`.
- Deleting a pre-existing ignored file or directory makes `compare` exit 1 with kind `ignored-removed`.
- `--allow` exempts both kinds like other path kinds.
- The limit (ignored-file edits unchecked) is stated in the docstring and `SKILL.md`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target integrity check detects overwritten untracked files and deleted ignored files`.

## Implementation

- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `skills/run-agoge/SKILL.md`, `CHANGELOG.md`
- **Risk**: hashing large untracked trees costs time, linear in bytes (perf lane: about 0.15s per 1k dirty 1KB files). Edits to ignored files stay invisible by design.

## Test Strategy

Regression tests for both kinds. Reproduction from the run:

```
heidi: notes.md untracked at snapshot; echo CLOBBERED > un/notes.md; compare un -> rc=0 unchanged [] touched= []
heidi: delete ignored .env -> rc=0 unchanged
walter: wrote REWRITTEN into preexisting-untracked.txt, rm -r ignored/ ->
  compare reported only [('tracked', 'new\nline.txt'), ('tracked', 'čeština ü.txt')]
```

## Tasks

- [ ] Add regression tests; watch them fail.
- [ ] Implement the untracked fingerprint and ignored-name record.
- [ ] Document the limit; add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
