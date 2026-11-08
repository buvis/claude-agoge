# A lane's git identity is overridden by the launcher, so a leaked commit does not name the lane

Source: agoge run 2026-11-08, finding 16 of 18 (LOW, verified, lanes walter, heidi and wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

The scratch contract in `references/finding-contract.md` tells each lane to commit with `-c user.name=agoge-<lane> -c user.email=agoge-<lane>@example.invalid`. Environment variables beat `-c`, and this operator's launcher exports `GIT_AUTHOR_NAME` and `GIT_COMMITTER_NAME`. Scratch commits are recorded under the operator's name; only the email names the lane. If a commit leaks into a target, the integrity report's identity evidence points at the operator.

## Solution

Change the scratch contract to set identity with environment variables on the command: `env GIT_AUTHOR_NAME=agoge-<lane> GIT_AUTHOR_EMAIL=agoge-<lane>@example.invalid GIT_COMMITTER_NAME=agoge-<lane> GIT_COMMITTER_EMAIL=agoge-<lane>@example.invalid git --git-dir=... --work-tree=... <command>`. Keep "never `export` one". Pin the new text in the hygiene suite.

## Requirements

### Must have
- `finding-contract.md` `## Scratch contract` gives the `env` form and says why (`-c` loses to exported variables).
- A hygiene test in `test_scratch_contract.py` pins the `env GIT_AUTHOR_NAME=agoge-` form.
- A test makes a commit with the documented form under an environment that exports `GIT_AUTHOR_NAME`, and asserts the author name is `agoge-<lane>`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: lane commits name the lane even when the launcher exports a git identity`.

## Implementation

- **Location**: `skills/run-agoge/references/finding-contract.md`, `skills/run-agoge/scripts/test_scratch_contract.py`, `CHANGELOG.md`; check agent files for copies of the old form.
- **Risk**: longer git commands in every lane.

## Test Strategy

Reproduction from the run:

```
environment: GIT_AUTHOR_NAME=Agent ran by Tomáš Bouška, GIT_COMMITTER_NAME=...
scratch commit with -c user.name=agoge-walter
  -> "author": "Agent ran by Tomáš Bouška <agoge-walter@example.invalid>"
heidi and wendy: same shape, only the email named the lane
```

## Tasks

- [ ] Add the tests; watch them fail.
- [ ] Update the scratch contract text.
- [ ] Add the CHANGELOG entry.

## Success Criteria

- New tests pass; the full suite passes under `dev/bin/release-checks`.
