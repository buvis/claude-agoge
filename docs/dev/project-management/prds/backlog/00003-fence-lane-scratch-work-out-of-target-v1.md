---
default_model: sonnet
model_tier_rationale: every edit carries its exact final text in the appendix; the incident test runs the documented preamble and fails loudly if it lets git fall through
---

# Fence lane scratch work out of the target repo

Source: `docs/dev/project-management/intake/processed/00003-heidi-scratch-git-guard/idea.md`
(part 1 of 2; PRD 00005 adds the master's check of the target)

## Overview

### Problem Statement

On 2026-10-25 a heidi lane changed the product it was probing. It made its
scratch repository inside the target checkout, where the sandbox refused
`git init` and left a `.git` holding only `description` and `info/`. The lane
script had no `set -e`, so it carried on, and `git -C <scratch dir>` climbed to
the nearest valid repository: the product. The script committed into the
product's `master` under a fake identity, tagged that commit `v1.0.0` (the
product publishes on tag pushes) and moved `refs/remotes/origin/master`, so
`git status` hid 13 unpushed commits.

No lane is told where scratch work may live or how to use git. Only walter's
charter and the browser playbook say "outside the repo", and nothing covers git.

### Target Users

Operators who run agoge on their own checkouts, attended or as an unattended
batch drain, and push those checkouts afterwards.

### Success Metrics

- The incident's command sequence, opened with the contract's documented
  preamble, exits non-zero and leaves the target's refs, index and status
  unchanged, even with the scratch repository inside the target. Without the
  preamble the same sequence changes the target (the control).
- Every dispatch prompt and the recon prompt carry the contract, and all seven
  charters point at it.
- `test_scratch_contract.py` passes, and `dev/bin/release-checks` passes.

## Functional Decomposition

### Capability: Scratch contract
Doctrine that makes a failed scratch step stop instead of falling through into
the target.

#### Feature: Contract section
- **Description**: A `## Scratch contract` section in
  `skills/run-agoge/references/finding-contract.md`.
- **Inputs**: None.
- **Outputs**: Appendix A1 and A2, verbatim.
- **Behavior**: One `mktemp -d` scratch root outside the target; a `set -eu`
  and `GIT_CEILING_DIRECTORIES` preamble opening every Bash call that writes;
  `--git-dir` and `--work-tree` on every scratch git write; a lane identity per
  command; a read-only target. The second bash block of A2 is executable, and
  the incident test runs it as written.

#### Feature: Prompt wiring
- **Description**: The master pastes the section into every dispatch and into
  the recon prompt.
- **Inputs**: The section.
- **Outputs**: Appendix A3, applied to `skills/run-agoge/SKILL.md`.
- **Behavior**: Dispatch part 4 carries the finding and scratch contracts, the
  recon prompt gains item 7, and the master's own pins file stays outside the
  target.

#### Feature: Charter pointers
- **Description**: Each charter says its prompt carries the contract.
- **Inputs**: None.
- **Outputs**: Appendix A4, as the last `## Rules` bullet of each charter.
- **Behavior**: Mirrors how the harness lanes point at their playbooks: a
  pasted contract that a charter never mentions reads as optional. It names no
  path, because an agent file names none.

## Structural Decomposition

### Repository Structure

```
skills/run-agoge/references/finding-contract.md    # Contract section (A1, A2)
skills/run-agoge/references/browser-playbook.md    # Probe scripts go under the scratch root (A5)
skills/run-agoge/SKILL.md                          # Prompt wiring (A3)
skills/run-agoge/scripts/test_scratch_contract.py  # Contract, incident and wiring tests (new)
agents/walter.md                                   # Charter pointer (A4)
agents/heidi.md                                    # Charter pointer (A4)
agents/judy.md                                     # Charter pointer (A4)
agents/wendy.md                                    # Charter pointer (A4)
agents/peggy.md                                    # Charter pointer (A4)
agents/trudy.md                                    # Charter pointer (A4)
agents/olivia.md                                   # Charter pointer (A4)
CHANGELOG.md                                       # Unreleased entry (A6)
```

### Module: scratch contract
- **Maps to capability**: Scratch contract
- **Responsibility**: Say where a lane may write and how it may use git.
- **Exports**:
  - `## Scratch contract` section - pasted verbatim into prompts
- New symbols: `GIT_CEILING_DIRECTORIES`, `SCRATCH`

### Module: prompt wiring
- **Maps to capability**: Scratch contract (Prompt wiring)
- **Responsibility**: Put the section into every prompt that reaches a lane.
- **Exports**:
  - Dispatch part 4 and recon item 7 in `skills/run-agoge/SKILL.md`

### Module: charters
- **Maps to capability**: Scratch contract (Charter pointers)
- **Responsibility**: Make each persona treat the contract as binding.
- **Exports**:
  - One `## Rules` bullet in each of the seven agent files

### Module: contract tests
- **Maps to capability**: Scratch contract
- **Responsibility**: Prove the documented preamble stops the incident, and pin
  the wiring.
- **Exports**:
  - `skills/run-agoge/scripts/test_scratch_contract.py`
- New symbols: `LANE`

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **contract tests**: Written first; they fail until the section exists.
- **scratch contract**: The section itself.

### Core Layer (Phase 1)
- **prompt wiring**: Depends on [scratch contract]
- **charters**: Depends on [scratch contract]

### Integration Layer (Phase 2)
- **CHANGELOG.md**: Depends on [prompt wiring, charters]

## Implementation Phases

Premise for every edit that quotes old text: the old text occurs exactly once
in the named file (`rg -F -c '<old text>' <file>` prints 1). If it does not,
skip that edit, report it, and never force a match.

Run tests from the repo root as
`uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q <file> [-k <filter>]`.

### Phase 0: Foundation
**Goal**: The contract exists and stops the incident.

**Tasks**:
- [ ] Write `skills/run-agoge/scripts/test_scratch_contract.py` (no deps).
  Test repositories run with `GIT_CONFIG_GLOBAL=/dev/null`,
  `GIT_CONFIG_NOSYSTEM=1`, `HOME` set to the test's tmp dir, and the author
  and committer identity `Test User <test@test.local>` set through git's
  environment variables, as in the incident. Tests, named with these phrases
  so the filters below select them:
  1. "mechanisms": the section exists and contains `mktemp -d`, `set -eu`,
     `GIT_CEILING_DIRECTORIES`, `--git-dir` and `read-only`.
  2. "incident ... preamble": build a target repo with one commit, a ref
     `refs/remotes/origin/master` at that commit, and one untracked file; a lane
     dir `docs/dev/tmp/agoge/heidi` inside it; and under the lane dir
     `t7/roots/heidi-repo/.git` holding only `description` and an empty
     `info/`, which is what the refused init left. Take the section's bash
     block that exports `GIT_CEILING_DIRECTORIES`, replace
     `<the path mktemp printed>` with the shell-quoted lane dir, append A7, run
     it with `bash -c` and `LANE` set to the lane dir. Assert a non-zero exit,
     and identical output of `git --no-optional-locks for-each-ref`,
     `ls-files --stage -z` and `status --porcelain=v1 -z` before and after.
  3. "incident ... control": the same, without the block. Assert that
     `refs/heads/master` moved, `refs/tags/v1.0.0` exists and
     `refs/remotes/origin/master` moved, so test 2 can fail.
  4. "charter": every one of the seven agent files mentions
     `scratch contract`, compared whitespace-normalized and case-insensitive.
  5. "prompt": in `skills/run-agoge/SKILL.md`, dispatch part 4 names
     `## Scratch contract`, and the recon prompt's item 7 names it.

  Acceptance: the file collects five tests, and tests 1, 2, 4 and 5 fail
  because nothing is written yet.
- [ ] Apply A1 and A2 to `skills/run-agoge/references/finding-contract.md`
  (depends on: the test task) - Acceptance:
  `pytest -q test_scratch_contract.py -k "mechanisms or incident"` passes, and
  `pytest -q test_sidecar_contract.py` passes.
- [ ] Apply A5 to `skills/run-agoge/references/browser-playbook.md` (no deps)
  - Acceptance: `rg -F -c 'agoge-<lane>/' skills/run-agoge/references/browser-playbook.md`
  finds nothing, and `pytest -q test_agoge_registry.py -k playbook` passes.

**Exit Criteria**: The incident test and its control both pass.

### Phase 1: Core
**Goal**: Every lane and recon receive the contract and treat it as binding.

**Tasks**:
- [ ] Apply A3 to `skills/run-agoge/SKILL.md` (depends on: Phase 0) -
  Acceptance: `pytest -q test_scratch_contract.py -k prompt` and
  `pytest -q test_agoge_authorization_gate.py` pass.
- [ ] Append A4 as the last `## Rules` bullet of `agents/walter.md`,
  `agents/heidi.md`, `agents/judy.md`, `agents/wendy.md`, `agents/peggy.md`,
  `agents/trudy.md` and `agents/olivia.md` (depends on: Phase 0) -
  Acceptance: `pytest -q test_scratch_contract.py -k charter` and
  `pytest -q test_agoge_registry.py` pass.

**Exit Criteria**: Both prompt paths and all seven charters carry the contract.

### Phase 2: Integration
**Goal**: The change is recorded for the release.

**Tasks**:
- [ ] Add A6 to `CHANGELOG.md` (depends on: Phase 1) - Acceptance:
  `rg -F -c 'scratch contract' CHANGELOG.md` prints 1, and
  `pytest -q test_agoge_registry.py -k extraction_clean` passes.

**Exit Criteria**: `dev/bin/release-checks` passes.

## Test Strategy

### Critical Scenarios
- **Happy path**: a lane follows the contract and inits its scratch repository
  under a `mktemp -d` root → Expected: the repository works below the ceiling,
  and the target is never named in a git write.
- **Edge case**: the scratch repository sits inside the target and its init
  failed → Expected: the documented preamble makes the next git write fail with
  exit 128, and the target is unchanged (test 2).
- **Error case**: the same commands without the preamble → Expected: the target
  gains a commit, a tag and a moved remote-tracking ref (test 3, the control).

## Risks

- **`set -eu` aborts a probe that expects a failure**: the contract says to
  capture an expected failure with `|| rc=$?`.
- **A lane ignores the contract**: doctrine cannot force behaviour. PRD 00005
  adds the master's snapshot and comparison, which catches any change that
  reaches refs, the index or tracked files.
- **`TMPDIR` points inside the target**: the contract tells the lane to stop
  and report `unverified` when the root it got is inside the target.
- **Out of scope**: the master's check of the target (PRD 00005); intake item
  3, the profile location, which 817dbfe settled by moving the profile under
  `docs/dev/project-management/meta/`; mirroring the agent-skills
  documentation copy after the release.

## Appendix: exact texts

### A1. Contracts intro

Replace the first two paragraphs of
`skills/run-agoge/references/finding-contract.md`, from
`Three contracts every agoge run obeys` through `names no path at all.`, with:

~~~markdown
Four contracts every agoge run obeys: what a specialist returns, where it may
write and how it may use git, what the run writes, and what the strategy
profile holds.

The seven agent bodies carry none of this. They receive the finding and scratch
contracts in their prompts, so the personas stay portable and the skill owns
every path — an agent file names no path at all.
~~~

### A2. The section

Insert immediately before `## Report contract`:

~~~markdown
## Scratch contract

Every specialist, recon included, works under these rules. A lane once
committed, tagged and moved a remote-tracking ref in the product itself: its
scratch `git init` failed inside the product's checkout, the script carried on,
and git found the product's repository instead of the scratch one.

**One scratch root, outside the target.** Make it once, first:

```bash
mktemp -d "${TMPDIR:-/tmp}/agoge-<lane>.XXXXXX"
```

Everything you create goes under the path it prints: scripts, data, databases,
clones and scratch repositories. Nothing goes inside the target, not even into
a directory the target ignores. If the printed path is inside the target, stop
and report the lane `unverified`.

**Open every Bash call that writes with this preamble**, with the path written
out in full. Do not rely on a variable set by an earlier call:

```bash
set -eu
SCRATCH=<the path mktemp printed>
export GIT_CEILING_DIRECTORIES="$SCRATCH"
```

`set -eu` stops the call at the first failed step. The ceiling stops git from
looking above the root for a repository, so a scratch repository that failed to
initialize is an error instead of whichever repository sits above it. When a
probe expects a command to fail, capture it: `cmd || rc=$?`.

**Name the scratch repository in every git command that writes**:
`git --git-dir="$SCRATCH/<repo>/.git" --work-tree="$SCRATCH/<repo>" <command>`,
never `git -C <dir> <command>`. Give each such command your lane's identity,
`-c user.name=agoge-<lane> -c user.email=agoge-<lane>@example.invalid`, and
never `export` one: a commit or ref move that escapes then names your lane.

**The target is read-only, git included.** Read it with `git log`,
`git show`, `git diff`, `git status`, `git tag --list`, `git for-each-ref` and
`git rev-parse`. To run another version, `git clone <target> "$SCRATCH/<name>"`
and check it out there, or
`mkdir -p "$SCRATCH/<dir>" && git -C <target> archive <rev> | tar -x -C "$SCRATCH/<dir>"`.
Never run `git commit`, `git tag <name>`, `git checkout`, `git switch`,
`git reset`, `git stash`, `git worktree`, `git remote`, `git config` or
`git update-ref` against the target.
~~~

### A3. SKILL.md edits

1. In `## Dependencies`, replace `finding, report and profile contracts.` with
   `finding, scratch, report and profile contracts.`
2. In step 2, replace `to a scratch file *before* the` with
   `to a scratch file outside the target *before* the`.
3. In step 3, replace `4. The `## Finding contract` section, pasted verbatim.`
   with `4. The `## Finding contract` and `## Scratch contract` sections,
   pasted verbatim.`
4. In `## The recon prompt`, insert before
   `She writes the profile and returns a summary.`, followed by a blank line:
   `7. The `## Scratch contract` section from `references/finding-contract.md`,
   pasted verbatim.`

### A4. Charter bullet

~~~markdown
- Your prompt carries a scratch contract. Follow it: it decides where you may
  write and how you may run git.
~~~

### A5. Browser playbook

Replace `` scratch directory outside it (`"${TMPDIR:-/tmp}"/agoge-<lane>/`) ``
with `scratch file under the root the scratch contract gives you`.

### A6. CHANGELOG entry

Add under `## [Unreleased]`, after the `### Changed` list:

~~~markdown
### Fixed

- **run-agoge**: a lane can no longer fall through into the target's own git
  repository. Every dispatch and the recon prompt carry a scratch contract: one
  scratch root outside the target, a `set -eu` and `GIT_CEILING_DIRECTORIES`
  preamble, explicit `--git-dir` on scratch git writes, a per-command lane
  identity, and a read-only target. A heidi lane whose scratch `git init`
  failed inside the target once committed, tagged and moved a remote-tracking
  ref in the product.
~~~

### A7. The incident's commands

From the 2026-10-25 lane script, with the message file inlined:

```bash
R="$LANE/t7/roots/heidi-repo"
git -C "$R" add -A
git -C "$R" commit -q -m "chore(probe): seed scratch dotfiles"
git -C "$R" tag v1.0.0
git -C "$R" update-ref refs/remotes/origin/master HEAD
```
