# run-agoge: a lane's scratch git commands ran in the target repo

Status: intake, not yet specced. Recorded 2026-10-25.

## What happened

During the agoge pass that followed autopilot batch 202610242315 in buvis/gems
(session `cc50273b-f487-4b88-94b7-4e646dc1f728`, heidi subagent
`agent-a734f4d54281c581c`), heidi's integration lane left three changes in the
target checkout itself, not in her scratch repo:

1. A commit on `master`: `chore(probe): seed scratch dotfiles`, author
   `Test User <test@test.local>`, created 2026-10-25 12:09:20 +0100. `add -A`
   swept in whatever was untracked at that moment: `dev/local/meta/agoge-profile.md`,
   the batch's `state-final.json`, the empty agoge log and two metrics rows.
2. A tag `v1.0.0` on that commit. The repo's real tags are `gems-v*`, and
   `publish.yml` triggers on tag pushes, so a later `git push --tags` would have
   tried to publish a bogus release.
3. `refs/remotes/origin/master` moved to that commit with an empty reflog
   message. `git status` then reported master "in sync" while 13 commits (a whole
   PRD) had never been pushed. Only a `git fetch` revealed it.

The lane script in the transcript contains exactly those three operations:

```sh
$GIT -C "$R" add -A; $GIT -C "$R" commit -q -F "$LANE/msg-seed.txt"
$GIT -C "$R" tag v1.0.0
printf 'more\n' >> "$R/README.md"; $GIT -C "$R" add -A; $GIT -C "$R" commit -q -F "$LANE/msg-a.txt"
$GIT -C "$R" remote add origin https://github.com/heidi-org/heidi-repo.git
$GIT -C "$R" update-ref refs/remotes/origin/master HEAD
```

with `GIT_AUTHOR_NAME="Test User"` and `GIT_AUTHOR_EMAIL=test@test.local`
exported for the whole script (`t7_postup.sh`, lines 6 to 14; `R` is
`<lane>/t7/roots/heidi-repo`, and the lane directory is
`<target>/docs/dev/tmp/agoge/heidi`, inside the product checkout).

Root cause, measured on 2026-10-25:

1. Under the operator's Seatbelt profile, `git init` of a repository anywhere
   inside the product checkout fails with
   `.git/hooks/: Operation not permitted` and exits 1 after writing only
   `description` and `info/`. Both `/opt/homebrew/bin/git` 2.56.0 and
   `/usr/bin/git` 2.54.0 fail the same way, with or without heidi's
   `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1`. The identical `init`
   succeeds in `$TMPDIR` and in the session scratchpad. `git clone` into the
   checkout fails the same way (the `t5_dot.sh` lane never got its
   `t5/init` clone: `fatal: cannot change to '.../t5/init'`).
2. The lane script has no `set -e`, so it continued past the failed `init`.
3. `git -C "$R"` then started in a directory whose `.git` is not a valid
   repository. Git discovery climbed from `$R` through `docs/dev/tmp/...` to
   the first valid repository: the product checkout. `git -C <that dir>
   rev-parse --git-dir` still answers `<target>/.git` today.
4. `add -A`, `commit`, `tag v1.0.0` and `update-ref` therefore acted on the
   product. `remote add origin` failed because the product already has one;
   the second commit found nothing to add (the README written under `$R` is
   ignored there) and `commit -q` failed silently.

The `t5` lane was spared only because its `clone` created no directory at all,
so `-C` failed instead of falling through. Walter's 2026-10-19 lane seeded with
explicit `--git-dir=<lane>/origin.git --work-tree=<lane>/seedwt`, which cannot
fall back to an enclosing repository.

## Impact

- Unpushed work hidden behind a lying remote-tracking ref (the worst outcome:
  a clean `git status` that is false).
- A foreign commit and tag on the product's default branch, under a fake
  identity, that a later push would have published.
- Cleanup needed `git reset`, `git tag -d`, a corrected ignore rule for
  `dev/local/` (agoge assumes it is ignored; gems did not ignore it) and a
  re-commit of the swept-in batch records.

## Proposed fix

1. **Lane script hygiene, in `agents/heidi.md` and the data playbook.**
   Scratch repositories live outside the product checkout (`mktemp -d` under
   `$TMPDIR`), never under `docs/dev/tmp/`, because the sandbox refuses
   `.git/hooks/` there and a half-made repository is worse than none. Every
   lane script starts with `set -eu` and exports
   `GIT_CEILING_DIRECTORIES=<lane root>` so discovery can never climb into the
   product even when a scratch init fails. Mutating git commands name their
   repository explicitly (`git --git-dir=<abs> --work-tree=<abs>`), never rely
   on `-C` plus discovery. Identity exports stay scoped to the scratch
   commands.
2. **A target-repo invariant in `run-agoge`.** Before dispatch, record the
   target's `HEAD`, tag list, remote-tracking refs and `status --porcelain`.
   After each lane, compare. Any new commit, tag, moved `refs/remotes/*` or
   new tracked change is a run failure that names the lane, not a finding to
   file quietly. The pre-dispatch snapshot also makes the report's "what did
   agoge touch" answerable.
3. **Profile location.** `dev/local/` is only safe when the target ignores it.
   Either the gate checks `git check-ignore dev/local` and refuses to write the
   profile there otherwise, or the profile moves under the target's declared
   scratch tree (`docs/dev/tmp/` in buvis repos).

## Acceptance ideas

- A test that runs a lane script with `R` unset against a fixture repo and
  proves no commit, tag or ref changes in that repo.
- A test for the invariant: seed a fixture target, simulate a lane that
  commits into it, assert the run fails and names the lane.
- Re-run agoge against gems and diff `git log --oneline -1`, `git tag` and
  `git rev-parse refs/remotes/origin/master` before and after: identical.
