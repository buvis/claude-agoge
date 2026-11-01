---
default_model: opus
model_tier_rationale: invented snapshot and comparison contract consumed by the run wiring, and porcelain and ref parsing where a missed change degrades silently
eligibility: rg -q '^## Scratch contract' skills/run-agoge/references/finding-contract.md
---

# Check that a run leaves the target as it found it

Source: `docs/dev/project-management/intake/processed/00003-heidi-scratch-git-guard/idea.md`
(part 2 of 2; builds on PRD 00003's scratch contract, which the eligibility
check waits for)

## Overview

### Problem Statement

The pack promises that every specialist is read-and-run, "so the armed tree
stays byte-identical while the lanes work" (SKILL.md step 6), but nothing
checks it. On 2026-10-25 a heidi lane committed into the product's `master`,
tagged the commit `v1.0.0` and moved `refs/remotes/origin/master`. The run
reported normally, and the damage surfaced only after a `git fetch`.

PRD 00003 tells lanes how to stay out of the target. This PRD makes the master
prove that they did, and makes a breach loud: the run fails, and the report
names every change, quotes who made it, and gives the operator a command that
puts each moved ref back.

### Target Users

Operators who run agoge on their own checkouts, attended or as an unattended
batch drain, and push those checkouts afterwards.

### Success Metrics

- A recon or lane that moves HEAD or a ref, or changes the index, a tracked
  file, the worktree list or the local git config, or removes an untracked
  file, fails the run. The report's summary header reads
  `Target integrity: changed` with each change, and the sidecar's
  `target_integrity` carries `status` `changed`.
- After a failed check the master skips authoring and never runs a restore
  command.
- Snapshot and comparison write nothing in the target: `.git/index` bytes and
  the `.git` file list with mtimes are unchanged.
- `test_target_snapshot.py` and `test_run_integrity.py` pass, and
  `dev/bin/release-checks` passes.

## Functional Decomposition

### Capability: Target snapshot
A stdlib script, `skills/run-agoge/scripts/target_snapshot.py`, that records
what a lane could damage and compares it later.

#### Feature: Snapshot
- **Description**: `target_snapshot.py snapshot <repo> <out.json>` writes a
  snapshot of the target.
- **Inputs**: The absolute top level of a git work tree, and an output path
  outside it.
- **Outputs**: JSON with `version` 1 and the keys in B1.
- **Behavior**: Every git call is `git --no-optional-locks -C <repo> ...`,
  because a plain `git status` rewrites the index. Paths are decoded with
  Python's os.fsdecode, so a non-UTF-8 name survives the JSON round trip.

#### Feature: Compare
- **Description**: `target_snapshot.py compare <repo> <before.json>
  [--allow <path>]...` reports every difference between a snapshot and the
  target now.
- **Inputs**: The repo, a snapshot this script wrote, and repo-relative paths
  to exempt.
- **Outputs**: `{"status": "unchanged" | "changed", "violations": [...],
  "touched": [...]}` on stdout, `indent=2`. Exit 0 unchanged, 1 changed,
  2 cannot check, with one stderr line starting `target_snapshot: `.
- **Behavior**: B2 defines the violations, their order, `touched`, `--allow`
  and the exit-2 cases.

### Capability: Run wiring
The master snapshots and compares around recon and the lanes, and reports the
result.

#### Feature: Integrity check
- **Description**: Step 1 snapshots, step 3 compares before the first dispatch
  and after the last lane returns, and step 6 skips authoring after a failed
  check.
- **Inputs**: The script's output.
- **Outputs**: B3 applied to `skills/run-agoge/SKILL.md`, and B4's paragraph
  appended to the scratch contract.
- **Behavior**: A comparison that exits 1 or 2 fails the run. The lanes run
  at once, so the report lists every dispatched lane and never names one on
  its own. The master never runs a `restore`.

#### Feature: Integrity in the report
- **Description**: The summary header and the sidecar carry the result.
- **Inputs**: Both comparisons.
- **Outputs**: B5 applied to `skills/run-agoge/references/finding-contract.md`.
- **Behavior**: `status` is `unchanged` when both comparisons exited 0,
  `changed` when either exited 1, and `unknown` when one exited 2 and neither
  exited 1. Each violation gains `phase`, `recon` or `lanes`.

## Structural Decomposition

### Repository Structure

```
skills/run-agoge/scripts/target_snapshot.py        # Target snapshot (new)
skills/run-agoge/scripts/test_target_snapshot.py   # Snapshot and comparison tests (new)
skills/run-agoge/scripts/test_run_integrity.py     # Wiring, report and incident tests (new)
skills/run-agoge/SKILL.md                          # Integrity check (B3)
skills/run-agoge/references/finding-contract.md    # Scratch contract paragraph (B4), report and sidecar (B5)
README.md                                          # "How a run goes" (B6)
CHANGELOG.md                                       # Unreleased entry (B7)
```

### Module: target_snapshot
- **Maps to capability**: Target snapshot
- **Responsibility**: Record and compare a repository without writing to it.
- **Exports**:
  - `snapshot <repo> <out.json>` - writes the snapshot
  - `compare <repo> <before.json> [--allow <path>]...` - prints the comparison
- New symbols: `target_snapshot`, `snapshot`, `head`, `head.ref`, `head.commit`, `refs`, `worktrees`, `untracked`, `violations`, `touched`, `reflog`, `committer`, `restore`, `dir`

### Module: run wiring
- **Maps to capability**: Run wiring
- **Responsibility**: Call the script at the right points and report its result.
- **Exports**:
  - The `Target integrity:` header line and the sidecar's `target_integrity`
- New symbols: `target_integrity`, `unknown`

### Module: integrity tests
- **Maps to capability**: Target snapshot, Run wiring
- **Responsibility**: Prove the comparison catches each kind of change, and pin
  the wiring.
- **Exports**:
  - `skills/run-agoge/scripts/test_target_snapshot.py`
  - `skills/run-agoge/scripts/test_run_integrity.py`

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **target_snapshot**: The snapshot and the comparison, with their tests.

### Core Layer (Phase 1)
- **run wiring**: Depends on [target_snapshot]

### Integration Layer (Phase 2)
- **README.md and CHANGELOG.md**: Depends on [run wiring]

## Implementation Phases

Premise for every edit that quotes old text: the old text occurs exactly once
in the named file (`rg -F -c '<old text>' <file>` prints 1), except where the
edit names which occurrence it means. If it does not, skip that edit, report
it, and never force a match.

Run tests from the repo root as
`uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q <file> [-k <filter>]`.
Test repositories run with `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_NOSYSTEM=1`, `HOME` set to the test's tmp dir, and an author and
committer identity set through git's environment variables. Tests drive the
script through `subprocess` with `sys.executable`.

### Phase 0: Foundation
**Goal**: A snapshot and comparison that catch each kind of change and write
nothing.

**Tasks**:
- [ ] Write `skills/run-agoge/scripts/test_target_snapshot.py`, one test per
  case (no deps): an untouched target compares unchanged; snapshot and compare
  write nothing in the target while a stat-dirty tracked file is present; a
  new commit on the current branch is one `ref` violation carrying its
  `commit` evidence, and no `head` violation; a new tag; a moved
  remote-tracking ref; a branch switch is a `head` violation; a staged change
  is an `index` violation; editing an already modified file is a `tracked`
  violation although its status letters are the same; reverting a modified
  file is a `tracked` violation; a removed untracked file is an
  `untracked-removed` violation; a new untracked file is `touched` and exit 0;
  an `--allow` path is neither; an added remote is a `config` violation whose
  output does not contain the remote's URL; an added worktree; each `restore`
  command, run, puts its ref back (a created tag, a created branch and a moved
  remote-tracking ref, then compare exits 0); a snapshot path inside the
  target, a snapshot of another repo, and an unborn target each exit 2 -
  Acceptance: the file collects these tests, and they fail because the script
  does not exist.
- [ ] Write `skills/run-agoge/scripts/target_snapshot.py` to B1 and B2, stdlib
  only, with `from __future__ import annotations` and a module docstring that
  states its usage, like `allocate_prd_number.py` (depends on: the test task)
  - Acceptance: `pytest -q test_target_snapshot.py` passes.

**Exit Criteria**: Both commands behave as specified against real repositories.

### Phase 1: Core
**Goal**: Every run checks the target and reports what it found.

**Tasks**:
- [ ] Write `skills/run-agoge/scripts/test_run_integrity.py` (depends on:
  Phase 0): "wiring" (SKILL.md step 1 snapshots to `start.json`; step 3
  compares `start.json` with both profile paths allowed, snapshots to
  `lanes.json` before the dispatch, and compares `lanes.json` after it, in
  that order); "authoring" (step 6 skips after a failed comparison, and the
  skill says never to run a `restore`); "contract" (the scratch contract ends
  with B4); "report" (the markdown report's item 1 holds
  `Target integrity: unchanged`, `Target integrity: changed` and the
  do-not-push line); "sidecar" (a JSON block in the sidecar section has
  `target_integrity` with `status`, `violations` and `touched`, and its
  violation has `phase`, `kind` and `restore`); "incident" (snapshot a target
  with an `origin/master` ref and an untracked file, run the five incident
  commands `test_scratch_contract.py` runs, without the preamble; `compare`
  exits 1 with `ref` violations for `refs/heads/master`, `refs/tags/v1.0.0`
  and `refs/remotes/origin/master`, each with a `restore`) - Acceptance: the
  file collects these tests, and "incident" passes.
- [ ] Apply B3 to `skills/run-agoge/SKILL.md` (depends on: the test task) -
  Acceptance: `pytest -q test_run_integrity.py -k "wiring or authoring"`,
  `pytest -q test_scratch_contract.py` and
  `pytest -q test_agoge_authorization_gate.py` pass.
- [ ] Apply B4 and B5 to `skills/run-agoge/references/finding-contract.md`
  (depends on: the test task) - Acceptance:
  `pytest -q test_run_integrity.py -k "contract or report or sidecar"` and
  `pytest -q test_sidecar_contract.py` pass.

**Exit Criteria**: `pytest -q test_run_integrity.py` passes.

### Phase 2: Integration
**Goal**: The change is documented and recorded for the release.

**Tasks**:
- [ ] Apply B6 to `README.md` and B7 to `CHANGELOG.md` (depends on: Phase 1)
  - Acceptance: `rg -F -c 'The target stays as found' README.md` prints 1,
  `rg -F -c 'target_snapshot.py' CHANGELOG.md` prints 1, and
  `pytest -q test_agoge_registry.py -k extraction_clean` passes.

**Exit Criteria**: `dev/bin/release-checks` passes.

## Test Strategy

### Critical Scenarios
- **Happy path**: snapshot, touch nothing, compare → Expected: exit 0,
  `status` `unchanged`, no violations.
- **Edge case**: recon writes a fresh profile and the product drops an
  untracked file → Expected: the profile is allowed, the other file is
  `touched`, exit 0.
- **Edge case**: a lane edits a file the operator had already modified →
  Expected: a `tracked` violation, although `git status` looks the same.
- **Error case**: an unborn target, a snapshot of another repo, or a snapshot
  path inside the target → Expected: exit 2 and one `target_snapshot: ` line.
- **Regression**: the 2026-10-25 commands without the scratch preamble →
  Expected: three `ref` violations, each with a working `restore`.

## Risks

- **The operator works in the target during a run**: the comparison reports
  their commit or edit as a change. Mitigation: the report quotes the commit
  and reflog identities and never blames one lane, and rerunning is cheap.
- **A product that rewrites a tracked file whenever it runs fails every run**:
  Mitigation: the violation names the file. That is a product finding, and the
  operator decides.
- **Unchecked areas**: ignored paths, the contents of untracked files, the
  repositories of submodules, and `.git/hooks`. Mitigation: the scratch
  contract is the guard there; the comparison covers what a push can publish.
- **`restore` puts refs back, not the index or files**: after a commit made
  with `git add -A`, moving the branch back leaves those files staged.
  Mitigation: the `index` and `tracked` violations name what else changed, and
  the operator decides how to undo it.
- **A git filter that fails under `git status`** makes the comparison exit 2.
  Mitigation: the run reports integrity `unknown` and fails closed.
- **Out of scope**: teaching agoge-gym's `bin/score` to refuse a sidecar whose
  `target_integrity` is not `unchanged`; mirroring the agent-skills
  documentation copy after the release.

## Appendix: exact texts

### B1. Snapshot keys

| Key | Source, each through `git --no-optional-locks -C <repo>` |
|---|---|
| `version` | the integer 1 |
| `repo` | `rev-parse --show-toplevel`; its realpath (Python's os.path.realpath) must equal that of the given path |
| `head` | `{"ref": <symbolic-ref -q HEAD, or null when detached>, "commit": <rev-parse --verify -q HEAD^{commit}>}` |
| `refs` | `for-each-ref --format=%(refname)%00%(objectname)`, as `{refname: oid}` |
| `config` | sha256 hex of the output of `config --local --list -z` |
| `worktrees` | the paths on the `worktree ` lines of `worktree list --porcelain` |
| `index` | sha256 hex of the output of `ls-files --stage -z` |
| `dirty` | one key per entry of `status --porcelain=v1 -z --untracked-files=no`, the value `"<XY> <print>"`, plus `" from <old path>"` when X or Y is `R` or `C` (that entry's next NUL-separated field is the old path). `<print>` is the sha256 of the file's bytes, `link:` and the sha256 of the link text for a symlink, `dir` for a directory, or `absent` |
| `untracked` | the sorted paths of `ls-files --others --exclude-standard -z` |

### B2. Comparison

Violations, in this order (refs, `tracked` and `untracked-removed` sorted by
name):

| `kind` | When | Fields |
|---|---|---|
| `head` | `head.ref` differs, or both are null and `head.commit` differs | `before`, `after`: the two `head` objects |
| `ref` | a ref was created, deleted or moved | `ref`; `before` and `after`, an oid or null; `commit` when `after` peels to a commit: `author` and `committer` as `Name <email>`, `date` as `%cI`, `subject`; `reflog`: `<name> <email> \| <message>` from `reflog show -n1 --format=%gn <%ge> \| %gs <ref>`, or null when that prints nothing or `after` is null; `restore` |
| `config` | the `config` digests differ | none: remote URLs can hold credentials |
| `worktrees` | the lists differ | `before`, `after` |
| `index` | the `index` digests differ | none |
| `tracked` | a `dirty` value differs, or the key appeared or went | `path`; `before` and `after`, a value or null |
| `untracked-removed` | an `untracked` path is gone | `path` |

A moved current branch is one `ref` violation, never also a `head` one.
`touched` lists the untracked paths that appeared. `--allow` exempts a path
from `tracked`, `untracked-removed` and `touched`, and from nothing else.
`restore`, every argument shell-quoted:

- created: `git -C <repo> update-ref -d <ref> <after>`
- deleted: `git -C <repo> update-ref <ref> <before> ""`
- moved: `git -C <repo> update-ref <ref> <before> <after>`

Exit 2 when the path is not a work tree's top level; HEAD has no commit; a git
call exits non-zero, other than `symbolic-ref -q` on a detached HEAD; the
snapshot file is missing, unreadable, not JSON, not `version` 1, or names
another `repo`; or `snapshot` was asked to write inside the repo.

### B3. SKILL.md edits

1. In `## Dependencies`, insert before
   ``- Path: `references/{browser,data,perf,security}-playbook.md` in this skill's``:

~~~markdown
- Path: `scripts/target_snapshot.py` in this skill's directory — the snapshot
  and comparison that prove a run left the target as it found it. Steps 1
  and 3.
~~~

2. In step 1, insert before `Everything downstream uses absolute paths. Never `cd`.`:

~~~markdown
Then make the master's own scratch root and snapshot the target:

```bash
mktemp -d "${TMPDIR:-/tmp}/agoge-master.XXXXXX"
python3 "${CLAUDE_SKILL_DIR}/scripts/target_snapshot.py" snapshot /absolute/target/repo <master scratch root>/start.json
```

When `CLAUDE_SKILL_DIR` is unset, use the absolute directory this skill was
loaded from, as `references/prd-emission.md` explains for its own script. If
the snapshot exits 2, stop before recon and report why: a run that cannot
check the target dispatches nobody.
~~~

3. In step 2, replace `to a scratch file outside the target *before* the`
   with `to a file in the master's scratch root *before* the`.
4. In step 3, insert before `Dispatch every armed specialist **in one message**`:

~~~markdown
**Check the target, then snapshot it, before the first dispatch:**

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/target_snapshot.py" compare /absolute/target/repo <master scratch root>/start.json \
  --allow docs/dev/project-management/meta/agoge-profile.md \
  --allow docs/dev/project-management/agoge-profile.md
python3 "${CLAUDE_SKILL_DIR}/scripts/target_snapshot.py" snapshot /absolute/target/repo <master scratch root>/lanes.json
```

The comparison allows the profile, which recon may write, and nothing else. If
it exits 1 or 2, dispatch nobody and go to step 7.
~~~

5. In step 3, insert after the paragraph that ends `so do not.`:

~~~markdown
**When every lane has returned, compare again**, allowing nothing:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/target_snapshot.py" compare /absolute/target/repo <master scratch root>/lanes.json
```

Exit 1 or 2 fails the run. Keep going through steps 4, 5 and 7 so the findings
are not lost, skip step 6, and carry both comparisons into the report. The
lanes ran at once, so a comparison cannot say which one made a change: the
report lists every dispatched lane, and the identities the comparison quotes
are the evidence. **Never run a `restore` command the comparison prints.** It
changes the operator's repository, and only the operator decides.
~~~

6. In step 6, replace
   `no finding survived step 4 as `verified`, or the target's tree is dirty.`
   with `no finding survived step 4 as `verified`, the target's tree is dirty,
   or a target comparison in step 3 did not exit 0.`
7. In step 7, replace `and who was armed, unarmed or vetoed;` with
   `who was armed, unarmed or vetoed, and the target's integrity;`, and insert
   after `a lane's own catch from another lane's by-catch.`, as the last line of
   the same bullet: `It also carries `target_integrity`, step 3's result, in
   the contract's shape.`

### B4. Scratch contract paragraph

Append as the last paragraph of `## Scratch contract`, before
`## Report contract`:

~~~markdown
**The master checks.** It snapshots the target's HEAD, refs, index, tracked
files, worktrees and local git config before recon and again before the lanes,
and compares after each. Any change fails the whole run, and the report names
it. Files the product itself writes into its checkout when you run it are
listed, not failed.
~~~

### B5. Report and sidecar

In `### The markdown report`, insert after
`profile, so state the route, never just "authorized".` (the end of item 1):

~~~markdown
   It also states the **target's integrity** from step 3 of the skill:
   `Target integrity: unchanged`, or `Target integrity: changed` (`unknown`
   when a comparison could not run) followed by each violation with its
   `restore` command, the lanes that were dispatched, and the line
   **Do not push this repository until you have run or rejected the restore
   commands above.** Then it lists the comparisons' `touched` paths: the files
   this run left in the target.
~~~

In `### The JSON sidecar`, insert before
`` `fixture` names the target the run was pointed at.``:

~~~markdown
The sidecar also carries the target's integrity, the result of step 3's two
comparisons:

```json
{"target_integrity": {
  "status": "changed",
  "violations": [
    {"phase": "lanes", "kind": "ref", "ref": "refs/tags/v1.0.0",
     "before": null, "after": "<new oid>",
     "commit": {"author": "agoge-heidi <agoge-heidi@example.invalid>",
                "committer": "agoge-heidi <agoge-heidi@example.invalid>",
                "date": "2026-10-25T12:09:20+01:00",
                "subject": "chore(probe): seed scratch dotfiles"},
     "reflog": null,
     "restore": "git -C /absolute/target/repo update-ref -d refs/tags/v1.0.0 <new oid>"}
  ],
  "touched": []
}}
```

`status` is `unchanged` when both comparisons exited 0, `changed` when either
exited 1, and `unknown` when one could not run and neither exited 1.
`violations` and `touched` are the comparisons' own, each violation tagged with
the `phase` it was found in, `recon` or `lanes`. The scorer ignores this key,
and only the operator runs a `restore` command.
~~~

### B6. README item

Insert as item 3 of `## How a run goes`, before
`3. **Every finding carries a status**`, and renumber that item and the two
after it to 4, 5 and 6:

~~~markdown
3. **The target stays as found.** The master snapshots the target's refs,
   index and tracked files before recon and again before the lanes, and
   compares after each. Any change fails the run, and the report names what
   moved and how to put it back. Every lane works in a scratch root outside
   the target.
~~~

### B7. CHANGELOG entry

Insert under `## [Unreleased]`, before its `### Changed` (the first one in the
file):

~~~markdown
### Added

- **run-agoge**: the master snapshots the target before recon and again before
  the lanes, with the new `scripts/target_snapshot.py`, and compares after
  each. A moved HEAD or ref, a changed index, tracked file, worktree list or
  local git config, or a removed untracked file fails the run; the report and
  the sidecar's `target_integrity` list each change, with a restore command for
  the operator.

~~~
