# run-agoge: emit per-finding lanes and score at the arm `bin/arm` prints

Status: processed, done directly in 729795c without a PRD (all four pack
changes below; `symbols` is documented as optional). Recorded 2026-11-01.

## Why

`buvis/agoge-gym` changed how it scores a run (gym commits 2b1366f..1358a8e,
2026-11-01). Three of the changes reach the pack's report contract and its
scoring instructions. Nothing in the pack was edited, because this working tree
held uncommitted edits to `skills/run-agoge/SKILL.md` and
`references/finding-contract.md` (the `dev/local` to
`docs/dev/project-management` path migration) that belong to another session.

## What changed in the gym

1. **`title` is matched, and required.** A seed is caught only by a finding
   whose `title` (plus an optional `symbols` list) contains a term from each of
   the seed's anchor groups. Path plus domain had credited 8 of 12 recorded
   seeds to findings that described other defects. A finding with no title
   makes the report exit 2. The sidecar already writes `title`, so recorded
   reports still score 12/12.
2. **Decoys.** Each fixture now holds correct code built to look broken. A
   finding that describes a decoy is a false positive and fails the bar. The
   recorded reports flag none.
3. **Per-finding `lanes`.** The scorer now reads an optional `lanes` list on
   each finding (`walter`, `heidi`, `judy`, `wendy`, `peggy`, `trudy`,
   `olivia`, `master`) and reports per seed which lanes caught it and whether
   that was by-catch. Without the field, lane credit is null. This makes PRD
   00117 Phase 3's "credited to trudy, not as by-catch" checkable.
4. **Arms live outside the gym.** `bin/arm <fixture>` now builds the arm under
   `$AGOGE_GYM_ARMED` or `$TMPDIR/agoge-armed/<fixture>` and refuses targets
   inside the gym. It also refuses to re-arm over an arm that holds a report,
   edits or extra branches, unless given `--discard`.

## What the pack should change

1. Write `lanes` on every sidecar finding: the contributing lanes after dedup,
   the same names as the report's "Found by" lines.
2. Optionally write `symbols` (functions, components, flags the finding is
   about). The scorer matches them like title words.
3. `references/finding-contract.md`, "The JSON sidecar": say that `score`
   matches `title` and reads `lanes` and `symbols`. The current text says
   matching reads only `fixture`, `domain`, `severity` and `paths`.
4. `SKILL.md`, the gym bullet: replace "run this skill at `armed/<fixture>`"
   with "run this skill at the path `bin/arm <fixture>` prints". Note that the
   report and sidecar must be copied into the gym's
   `docs/dev/project-management/audit-results/` before the next arm.

## Check

Run the pack at a fresh arm. Then run
`bin/score <sidecar> --manifest manifests/<fixture>.json` in the gym. Every
seed verdict has a non-null `lanes`, and the exit code is 0.
