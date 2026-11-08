---
lane: fast-track
design: skip
default_model: sonnet
model_tier_rationale: exact contract text given; pinned by hygiene and behaviour tests
---
# A lane's git identity is overridden by the launcher, so a leaked commit does not name the lane

Source: agoge run 2026-11-08, finding 16 of 18 (LOW, verified, lanes walter, heidi and wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

The scratch contract in `skills/run-agoge/references/finding-contract.md` tells each lane to commit with `-c user.name=agoge-<lane> -c user.email=agoge-<lane>@example.invalid`. Environment variables beat `-c`, and this operator's launcher exports `GIT_AUTHOR_NAME` and `GIT_COMMITTER_NAME`. Scratch commits are recorded under the operator's name; only the email names the lane. If a commit leaks into a target, the integrity report's identity evidence points at the operator.

## Solution

In `## Scratch contract`, replace the `-c user.name=... -c user.email=...` instruction with the `env` form: `env GIT_AUTHOR_NAME=agoge-<lane> GIT_AUTHOR_EMAIL=agoge-<lane>@example.invalid GIT_COMMITTER_NAME=agoge-<lane> GIT_COMMITTER_EMAIL=agoge-<lane>@example.invalid git --git-dir=... --work-tree=... <command>`, with one sentence saying `-c` loses to exported variables. Keep "never `export` one". No agent file carries the old form (`rg "user\.name" agents` is empty), so only the contract changes.

## Requirements

### Must have
- `finding-contract.md` `## Scratch contract` gives the `env` form and says why (`-c` loses to exported variables).
- A hygiene test in `test_scratch_contract.py` pins the `env GIT_AUTHOR_NAME=agoge-` form.
- A test makes a commit with the documented form under an environment that exports `GIT_AUTHOR_NAME`, and asserts the author name is `agoge-<lane>`.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: lane commits name the lane even when the launcher exports a git identity`.

### Nice to have
- None.

## Implementation

### Module: scratch-contract
- **Location**: `skills/run-agoge/references/finding-contract.md`, `skills/run-agoge/scripts/test_scratch_contract.py`, `CHANGELOG.md`
- **Responsibility**: give lanes an identity form that survives an exported git identity.
- **Exports**: none
- New symbols: `test_scratch_contract_sets_identity_with_env`, `test_env_identity_beats_exported_author`
- **Risk**: longer git commands in every lane.

### Dependencies
- scratch-contract: No dependencies (foundation)

## Test Strategy

Reproduction from the run:

```
environment: GIT_AUTHOR_NAME=Agent ran by Tomáš Bouška, GIT_COMMITTER_NAME=...
scratch commit with -c user.name=agoge-walter
  -> "author": "Agent ran by Tomáš Bouška <agoge-walter@example.invalid>"
heidi and wendy: same shape, only the email named the lane
```

## Tasks

### Phase 0: Fix
- [ ] Add `test_scratch_contract_sets_identity_with_env` and `test_env_identity_beats_exported_author` - Acceptance: `pytest -k "identity_with_env"` fails on the unmodified contract.
- [ ] Update the scratch contract text (depends on: previous task) - Acceptance: `pytest -k "identity_with_env or beats_exported_author"` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "lane commits name the lane" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "identity_with_env or beats_exported_author"` passes; the full suite passes under `dev/bin/release-checks`.
