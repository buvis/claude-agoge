# Design: Check that a run leaves the target as it found it

## Architecture fit

This PRD adds a second line of defense on top of PRD 00003's scratch
contract (prose discipline for specialists) with a mechanical check the
master runs itself. It lands in the same component the capsule names as
owning all paths: `skills/run-agoge/SKILL.md` (master orchestration). The
new script is a sibling of `scripts/allocate_prd_number.py` — a stdlib-only
helper invoked by the skill via `subprocess`/Bash, not imported — and the
new contract paragraph extends `references/finding-contract.md`'s
`## Scratch contract` section, which is already pasted verbatim into every
dispatch and recon prompt. No specialist agent file changes: the check is
the master's own, run before and after dispatch, never inside a lane's
prompt.

## Module placement

New files:

- `skills/run-agoge/scripts/target_snapshot.py` — the snapshot/compare CLI.
- `skills/run-agoge/scripts/test_target_snapshot.py` — unit tests for the
  script in isolation.
- `skills/run-agoge/scripts/test_run_integrity.py` — tests for the SKILL.md
  wiring, the contract paragraph, the report/sidecar additions, and the
  incident regression.

Edits to existing files:

- `skills/run-agoge/SKILL.md` — steps 1, 2 (comment-only path clarification
  already in PRD text), 3, 6, 7 per PRD Appendix B3.
- `skills/run-agoge/references/finding-contract.md` — append to
  `## Scratch contract` (B4), extend `### The markdown report` and
  `### The JSON sidecar` (B5).
- `README.md` — `## How a run goes` gains item 3 (B6).
- `CHANGELOG.md` — `## [Unreleased]` gains an `### Added` entry (B7).

## Interfaces & contracts

### CLI: `target_snapshot.py`

```
python3 target_snapshot.py snapshot <repo> <out.json>
python3 target_snapshot.py compare <repo> <before.json> [--allow <path>]...
```

Both subcommands take `<repo>` as an absolute path. `snapshot` writes to
`<out.json>` (must resolve outside `<repo>`, else exit 2). `compare` reads
`<before.json>` and prints a JSON object to stdout.

Every git call is built as a list (never through a shell), prefixed
`["git", "--no-optional-locks", "-C", str(repo)]`, so a filter or alias
cannot inject a shell metacharacter and a plain `git status` never touches
the index.

### Snapshot shape (`version: 1`)

```python
{
  "version": 1,
  "repo": str,       # os.path.realpath of `git rev-parse --show-toplevel`
  "head": {"ref": str | None, "commit": str},
  "refs": {str: str},             # refname -> oid, from for-each-ref
  "config": str,                  # sha256 hex of `config --local --list -z`
  "worktrees": [str, ...],        # paths from `worktree list --porcelain`
  "index": str,                   # sha256 hex of `ls-files --stage -z`
  "dirty": {str: str},            # path -> "<XY> <print>"[ " from <old>"]
  "untracked": [str, ...],        # sorted paths
}
```

Field derivations, exact commands:

| Key | Command | Derivation |
|---|---|---|
| `repo` | `rev-parse --show-toplevel` | `os.path.realpath(stdout.strip())`; must equal `os.path.realpath(repo_arg)` or exit 2 |
| `head.ref` | `symbolic-ref -q HEAD` | stdout stripped, or `None` on exit 1 (detached HEAD; this is the one git call allowed to exit non-zero) |
| `head.commit` | `rev-parse --verify -q HEAD^{commit}` | stdout stripped; exit 2 (unborn HEAD) if this fails |
| `refs` | `for-each-ref --format=%(refname)%00%(objectname)` | split each line on `\0` into `(refname, oid)` |
| `config` | `config --local --list -z` | `hashlib.sha256(stdout_bytes).hexdigest()` |
| `worktrees` | `worktree list --porcelain` | lines starting `worktree `, the rest of the line |
| `index` | `ls-files --stage -z` | `hashlib.sha256(stdout_bytes).hexdigest()` |
| `dirty` | `status --porcelain=v1 -z --untracked-files=no` | NUL-delimited records; each record's first 2 chars are `XY`, char 3 is a space, rest is the path (and for `R`/`C` the next NUL field is the old path, appended as `" from <old path>"`); value is `f"{XY} {_fingerprint(path)}"` + that suffix |
| `untracked` | `ls-files --others --exclude-standard -z` | sorted list of NUL-split paths |

`_fingerprint(path)` (repo-relative, resolved against `repo`, never
followed through a symlink target outside `repo`):

- missing on disk → `"absent"`
- `os.path.islink` → `"link:" + sha256(os.readlink(path).encode()).hexdigest()`
- `os.path.isdir` → `"dir"`
- else → `sha256(file_bytes).hexdigest()`

### Compare output shape

```python
{"status": "unchanged" | "changed", "violations": [...], "touched": [...]}
```

Exit code: 0 (`unchanged`), 1 (`changed`), 2 (cannot check — printed to
stdout is skipped in this case; only the stderr line fires, see below).

Comparison order (fixed, so test assertions can match on index):
`head`, then `ref` (sorted by refname), `config`, `worktrees`, `index`,
then `tracked` (sorted by path), then `untracked-removed` (sorted by
path).

Violation shapes:

```python
# head
{"kind": "head", "before": {...head obj...}, "after": {...head obj...}}

# ref
{"kind": "ref", "ref": str, "before": str | None, "after": str | None,
 "commit": {"author": str, "committer": str, "date": str, "subject": str} | <absent>,
 "reflog": str | None, "restore": str}

# config
{"kind": "config"}

# worktrees
{"kind": "worktrees", "before": [str, ...], "after": [str, ...]}

# index
{"kind": "index"}

# tracked
{"kind": "tracked", "path": str, "before": str | None, "after": str | None}

# untracked-removed
{"kind": "untracked-removed", "path": str}
```

Rules:

- A ref whose current branch (`after_head.ref` points at it) moved is
  reported as `ref` only, never also as `head`, per B2. Detect this by
  computing `head` first, then excluding from `ref` detection any refname
  equal to `after.head.ref` when `before.head.ref == after.head.ref`
  (same branch, moved) — the move already shows as the `ref` row's
  `before`/`after` oids, and `head` only fires when `head.ref` itself
  differs or both are null and `head.commit` differs. The exclusion is
  deliberately same-branch-only: a branch *switch* to a branch B whose
  own tip also advanced (`before.head.ref != after.head.ref`) reports
  both a `head` violation (the switch) and a `ref` violation for B (the
  advance) — two distinct, independently restorable facts, not
  double-reporting of one event. B2's "never also a `head`" rule names
  only the same-branch case.
- `ref.commit` is present only when `after` is not null and
  `rev-parse --verify -q <after>^{commit}` succeeds; its fields come from
  `log -1 --format=%an <%ae>%x00%cn <%ce>%x00%cI%x00%s <after>` (NUL-split).
- `ref.reflog` runs `reflog show -n1 --format=%gn <%ge> | %gs <ref>`; `None`
  when that prints nothing or `after` is null.
- `ref.restore`, one of, every argument through `shlex.quote`:
  - created (`before is None`): `git -C <repo> update-ref -d <ref> <after>`
  - deleted (`after is None`): `git -C <repo> update-ref <ref> <before> ""`
  - moved: `git -C <repo> update-ref <ref> <before> <after>`
- `tracked` fires when a `dirty` key's value differs between snapshots, or
  the key exists in one and not the other (present → absent is `after: None`
  and vice versa).
- `untracked-removed` fires when a path in `before.untracked` is absent
  from `after.untracked`.
- `touched`: `sorted(set(after.untracked) - set(before.untracked))`,
  **after** removing `--allow`ed paths.
- `--allow <path>` (repeatable, repo-relative) exempts `<path>` from
  `tracked`, `untracked-removed` and `touched` only — never from `head`,
  `ref`, `config`, `worktrees` or `index`.

### Exit 2 cases (compare and snapshot both)

One line to stderr, exactly `target_snapshot: <reason>`, no traceback:

- `<repo>` is not a work tree's top level (`rev-parse --show-toplevel`
  fails or its realpath disagrees with the arg's realpath).
- HEAD has no commit (unborn branch).
- Any required git call exits non-zero (the only git call allowed to fail
  is `symbolic-ref -q HEAD` on a detached HEAD).
- (`compare` only) the snapshot file is missing, unreadable, not valid
  JSON, its `version` is not `1`, or its `repo` (realpath) does not equal
  the target's own realpath.
- (`snapshot` only) the resolved `<out.json>` path is inside `<repo>`
  (`os.path.commonpath` check against the repo's realpath).

### SKILL.md wiring (B3, applied verbatim from the PRD appendix)

- Step 1: after `git -C ... rev-parse HEAD`, `mktemp -d` a master scratch
  root and run `target_snapshot.py snapshot <target> <root>/start.json`.
  Exit 2 stops before recon.
- Step 3: `start.json`'s compare runs before the first dispatch, allowing
  the two profile paths (`docs/dev/project-management/meta/agoge-profile.md`
  and the root-fallback `docs/dev/project-management/agoge-profile.md`
  from SKILL.md step 2 — recon may write either one). `lanes.json` is
  snapshotted right after that compare passes and compared again after
  every lane returns, allowing nothing.
  Per the PRD's B3 edit 4 ("If it exits 1 or 2, dispatch nobody and go to
  step 7"): a non-zero `compare_recon` dispatches **no lanes** and the
  master goes **straight to step 7** (report) — steps 4 (audit) and 5
  (dedup) are skipped too, since there are no lane findings to audit or
  dedup yet. A non-zero `compare_lanes` (lanes already ran, so there are
  findings) still runs 4, 5, 7 in order, skipping only step 6 (author).
  Neither failure ever runs a printed `restore` command.
- Step 6: skip authoring when, in addition to today's two reasons, "a
  target comparison in step 3 did not exit 0".
- Step 7: the summary header's armed/unarmed/vetoed sentence also states
  target integrity; a new sentence confirms `target_integrity` carries
  step 3's result.

### Report / sidecar additions (B5)

- Markdown report, end of item 1: `Target integrity: unchanged` /
  `changed` / `unknown`, each violation with its `restore` command when
  `changed`, the dispatched lanes, the do-not-push line, then the
  comparisons' `touched` paths.
- Sidecar, top level: `target_integrity: {status, violations, touched}`.
  `compare_lanes` is **nullable**: when `compare_recon` is non-zero, lanes
  never dispatch and `compare_lanes` never runs, so `status` is derived
  from `compare_recon` alone in that case — `"changed"` if it exited 1,
  `"unknown"` if it exited 2. When `compare_recon` exited 0 (so
  `compare_lanes` did run), the existing two-call rule applies: `status`
  is `"unchanged"` iff both exited 0; `"changed"` iff either exited 1;
  `"unknown"` iff one exited 2 and neither exited 1. Each violation object
  gains `"phase": "recon" | "lanes"` (which compare call found it)
  alongside its own `kind` fields above; a `compare_recon`-only failure
  produces only `"phase": "recon"` violations. An exit-2 call (no
  parseable stdout) contributes **zero violations** to the merge — its
  only effect is on `status` (via the rule above), never on the
  `violations` list. `touched` is the **union** of both calls' `touched`
  lists (each already de-duplicated against its own baseline), with the
  union itself de-duplicated by path: a path recon introduced and the
  lanes step left alone appears once, even though `compare_lanes` cannot
  see it again (it is already in `lanes.json`'s baseline).

## Data flow

1. Master resolves the target repo, makes its own scratch root
   (`mktemp -d`), calls `target_snapshot.py snapshot` → `start.json`.
2. Master runs recon (olivia) if the profile is stale.
3. Master calls `target_snapshot.py compare <target> start.json --allow <profile paths>` →
   `compare_recon` result (JSON on stdout, exit code captured). Non-zero
   (1 or 2) → per the PRD's B3 edit 4, dispatch **no lanes** and jump
   straight to step 7 (report); `compare_lanes` never runs (it stays
   `None`), steps 4 and 5 are skipped (no lane findings exist yet to
   audit or dedup), and step 6 (author) is skipped as always on a failed
   check.
4. On `compare_recon` exit 0, master snapshots again → `lanes.json`, then
   dispatches armed specialists concurrently (unchanged from today —
   lanes write only to their own scratch roots per PRD 00003).
5. After every lane returns, master calls
   `target_snapshot.py compare <target> lanes.json` (no `--allow`) →
   `compare_lanes` result.
6. Master derives `target_integrity.status` (nullable-`compare_lanes`
   rule, see Interfaces & contracts § Report / sidecar additions) and
   tags each violation's `phase` (`"recon"` for violations from
   `compare_recon`, `"lanes"` for `compare_lanes`), merging both
   violation lists in that order (an absent `compare_lanes`, or a call
   that exited 2 with no parseable stdout, contributes zero violations —
   see § Report / sidecar additions). `touched` is the de-duplicated
   union of both calls' `touched` lists (same section).
7. Steps 4 (audit) and 5 (dedup) run only when lanes dispatched (i.e.
   `compare_recon` exited 0); step 7 (report) always runs and reads
   `target_integrity` to write the new report/sidecar fields and to
   decide whether step 6 (author) may run. The master never executes a
   `restore` command; it only quotes it.

## Reuse inventory

- `skills/run-agoge/scripts/allocate_prd_number.py` — the only existing
  stdlib-only script in this skill; reused as the **style template**
  (module docstring stating usage up top, `from __future__ import
  annotations`, a `main(argv)` returning an int, `if __name__ ==
  "__main__": sys.exit(main(sys.argv))`). Not reused for logic — it does
  no git work.
- `skills/run-agoge/references/finding-contract.md`'s existing
  `## Scratch contract` prose already documents the git commands this
  script must wrap (`--no-optional-locks`, `--git-dir`/`--work-tree`
  naming, read-only verbs on the target) — the script's own git-call list
  is written to match that prose, not reinvented.
- `skills/run-agoge/scripts/test_scratch_contract.py`'s `_snapshot()` /
  `_refs()` helpers and its `_build_incident_fixture` / the exact A7
  incident commands (`git add -A && commit && tag v1.0.0 && update-ref
  refs/remotes/origin/master HEAD`) are reused directly as the basis for
  `test_run_integrity.py`'s "incident" test (PRD's own instruction: "the
  five incident commands `test_scratch_contract.py` runs, without the
  preamble").
- Nothing in this repo already does structured git-state diffing;
  greps tried: `rg "git --no-optional-locks"`, `rg -l "snapshot" --glob
  '*.py'`, `rg -l "for-each-ref"`, `rg -l "update-ref"` (all four returned
  only this PRD's own text, PRD 00003's artifacts, and
  `test_scratch_contract.py`'s incident-fixture commands — confirmed the
  searches work since they returned those real hits, so "nothing
  reusable" is not a dead search).
- Python stdlib covers every need (`subprocess`, `hashlib`, `json`,
  `shlex`, `os.path`) — no new dependency.

## Alternatives considered

1. **Smallest-diff: `git status --porcelain` diff only, no full snapshot
   object.** Compare `git status --porcelain=v1 -z` and `git
   rev-parse HEAD` before/after; flag any difference. Rejected as the sole
   mechanism — it is exactly the gap the PRD's Problem Statement calls
   out: `git status` cannot see a ref move that leaves the tree clean
   (new tag, moved `refs/remotes/origin/master`) or a local-config change,
   which is precisely how the 2026-10-25 incident went undetected. Kept
   as a comment in the script (`status --porcelain` for the `dirty` key)
   but not as the whole design.
2. **Chosen: full structural snapshot/compare per B1/B2.** Snapshots
   HEAD, refs, index, tracked-file fingerprints, worktrees and local
   config; diffs by key. Larger than option 1, but it is the only option
   that catches every kind of change the PRD's Success Metrics name
   (moved HEAD, moved/created/deleted ref, index, tracked file, worktree
   list, local config, removed untracked file) and reproduces the
   regression test's three-ref incident exactly.
3. **Shell out to `git diff --stat` between two commits of a throwaway
   git bundle of the target.** Rejected: bundling the target itself risks
   writing into or near it, and still cannot see untracked-file removal,
   config changes, or worktree-list changes without extra machinery that
   ends up re-deriving most of option 2 anyway, at higher risk.

The chosen design's extra size over option 1 buys the exact three ref
violations the regression incident requires (`refs/heads/master`,
`refs/tags/v1.0.0`, `refs/remotes/origin/master`) plus config/worktree
coverage the PRD's Success Metrics explicitly list — option 1 cannot
produce any of those.

## Risks & edge cases

- **Likely next change 1**: scoring the sidecar's `target_integrity` in
  `agoge-gym`'s `bin/score` (explicitly out of scope here, per the PRD's
  Risks section) — this design's `status`/`violations`/`touched` shape is
  written to be directly scoreable later without a reshape.
- **Likely next change 2**: extending the snapshot to cover `.git/hooks`
  or submodule repositories (explicitly out of scope per the PRD) — the
  `version: 1` field on the snapshot JSON exists so a future `version: 2`
  can add keys without breaking `compare`'s "names another repo" check,
  which only compares `repo`, not the full key set.
- **Likely next change 3**: a lane wanting to assert its own sub-scope
  integrity (e.g. heidi checking only its own scratch repo) — `compare`'s
  `--allow` list is repeatable and repo-relative, so a future caller can
  widen the exemption list without a script change.
- **A git filter/hook that fails under `git status`** makes `compare`
  exit 2 for that call; the design reports `unknown` rather than guessing
  `unchanged`, per B2's "fails closed" principle, and per B5's
  `status` derivation (`unknown` iff one exited 2 and neither exited 1).
- **The operator edits the target during a run**: reported as a change
  like any other; mitigation is entirely on the report side (B5: quote
  commit/reflog identities, never blame a lane) — nothing in the script
  itself tries to distinguish an operator edit from a lane's.
- **`restore` only touches refs**: after a `git add -A && commit`, moving
  the branch back with `update-ref` leaves the index/files staged. The
  script's `restore` strings intentionally cover only the `ref` kind;
  `index` and `tracked` violations carry no `restore` field by design
  (B2 lists `restore` only under `ref`), so the operator is told what else
  changed but given no auto-fix for it.

## Test strategy outline

`test_target_snapshot.py` (Phase 0, unit-level, one test per PRD Phase 0
task bullet): untouched target → unchanged; snapshot/compare write
nothing to the target even with a stat-dirty tracked file present; new
commit → one `ref` violation with `commit` evidence, no `head` violation;
new tag → `ref`; moved remote-tracking ref → `ref`; branch switch → `head`;
staged change → `index`; re-editing an already-modified file → `tracked`
(even though status letters repeat); reverting a modified file → `tracked`;
removed untracked file → `untracked-removed`; new untracked file →
`touched` + exit 0; `--allow`ed path → neither; added remote → `config`
(assert output never contains the remote URL); added worktree →
`worktrees`; each generated `restore` command, executed, puts its ref back
(tag, branch, moved remote-tracking ref), then a follow-up `compare` exits
0; snapshot-path-inside-target, snapshot-of-another-repo, and
snapshot-of-an-unborn-repo each exit 2 with the `target_snapshot: ` stderr
prefix.

`test_run_integrity.py` (Phase 1, integration-level, each named case from
the PRD): `wiring` (asserts the SKILL.md step 1/3 text names `start.json`
before dispatch and `lanes.json` before/after, in that textual order);
`authoring` (step 6 text includes the new skip reason; the skill text says
never to run `restore`); `contract` (the scratch contract section ends
with the B4 paragraph); `report` (the markdown report item 1 contains
`Target integrity: unchanged`, `Target integrity: changed`, and the
do-not-push line); `sidecar` (the JSON sidecar section's example has
`target_integrity.{status,violations,touched}` and a violation with
`phase`, `kind`, `restore`); `incident` (reuses `test_scratch_contract.py`'s
`_build_incident_fixture`-equivalent target with an `origin/master` ref and
an untracked file; runs the A7 commands without the scratch preamble
against the real target; `compare` exits 1 with three `ref` violations for
`refs/heads/master`, `refs/tags/v1.0.0`, `refs/remotes/origin/master`, each
carrying a working `restore`).

Regression anchor: the `incident` test is the PRD's named regression case
(the 2026-10-25 commands) and must pass before anything else in Phase 1 is
considered done.

## Review log

- non-blocker: full-file sha256 hashing on every snapshot/compare has no
  size bound for large repos; acceptable for agoge's dev-sized targets,
  noted here as a known limitation rather than fixed.
- non-blocker: the `worktrees` violation reports whole before/after lists
  rather than a per-entry diff; matches the PRD's B1/B2 appendix (no
  per-item diff required there), flagged only as a report-readability nit.
dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 2, question 1

- question: an exit-2 compare call's effect on the merged `violations`
  list was unstated; resolved — it contributes zero violations (only
  `status` is affected).
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 1, question 1

- non-blocker: the exit-2 rule for `touched` ("zero violations, empty
  set") is covered by the same "its only effect is on status" sentence
  but not spelled out per-field as explicitly as the `violations` rule;
  recorded as a documentation nit, not fixed (the behavior is already
  correct and inferable).
- question: `status` names two different value domains (the CLI's own
  `{unchanged, changed}` vs. the master-derived sidecar/report
  `{unchanged, changed, unknown}`); not renamed since `target_integrity.`
  already namespaces the sidecar field distinctly from the CLI's bare
  `status` key.
- question: an `argparse` usage error (bad invocation) also exits 2,
  which SKILL.md's wiring would absorb into "unknown, fails closed"
  alongside a genuine cannot-check state; left as-is since the caller
  (SKILL.md) controls the invocation shape and a usage bug there is a
  caller defect, not a target-integrity ambiguity.
- question: whether `touched` still prints when `status` is `unknown`;
  not resolved with new doc text (the Test strategy outline and report
  wording already imply touched prints from whichever call returned
  parseable stdout, regardless of status) — left for planning to confirm
  against the written report format, not a design-level blocker.
dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 1, question 3
