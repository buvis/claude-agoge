# Project Capsule: claude-agoge

Generated: 2026-11-03

## Key Invariants

- A finding only counts if `status: verified`; `unverified`/`mocked`/`skipped` never fail a run. The master audits claimed evidence, not the specialist's prose.
- Specialists are personas (`agents/*.md`) with no path knowledge of their own — every path, contract and rule reaches them through the dispatch prompt (`skills/run-agoge/SKILL.md`). Keeping agent files path-free is deliberate: it keeps personas portable across invocation sites.
- An unarmed lane never dispatches — recon (`olivia`) decides armed/unarmed per specialist and that decision is the cost gate.
- Trudy (security lane) refuses to run without an explicit authorization assertion in the profile's `## Pins and vetoes` section or a `--authorized <source>` flag on invocation; recon itself can never assert authorization.
- The profile's `## Pins and vetoes` section is human-owned; a profile refresh must copy it through byte-identically.
- `target_snapshot.py` exit contract: 0 unchanged, 1 changed, 2 cannot run (one `target_snapshot: <reason>` stderr line). Any unexpected error must map to 2, never 1, so a crash cannot read as "target changed". Git output is decoded with `os.fsdecode` (filesystem bytes), not strict UTF-8.

## Architecture Decisions

- Prompts, not code, carry the contracts (finding contract and scratch contract) — this is why `skills/run-agoge/references/finding-contract.md` is injected verbatim into both the dispatch and recon prompts rather than referenced by path.
- Intake docs under `docs/dev/project-management/intake/processed/` record the originating incident/idea per PRD; PRD 00003 and PRD 00005 both derive from `00003-heidi-scratch-git-guard/idea.md` (00003 = contract/doctrine, 00005 = master's own verification check of the target).
- The scratch contract plus the master's snapshot/compare is a deliberate two-layer defence (doctrine in prompts, mechanical check in code).

## Component Boundaries

- `skills/run-agoge/SKILL.md` — master orchestration: recon dispatch, specialist dispatch, dedup, one report. Owns all paths referenced by prompts.
- `skills/run-agoge/references/finding-contract.md` — the contract text pasted into prompts (finding + scratch contract).
- `skills/run-agoge/references/*-playbook.md` — browser, data, perf, security, authoring playbooks; `prd-emission.md`.
- `skills/run-agoge/scripts/{target_snapshot,allocate_prd_number}.py` — the only executable code; stdlib-only, `git` binary dependency. `allocate_prd_number.py` WRITES into its repo arg (scratch repos only).
- `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md` — seven charters, each with a `## Rules` section pointing at the scratch contract.
- `skills/run-agoge/scripts/test_*.py` — 7 pytest suites; `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q` (also the release gate, `dev/bin/release-checks`). Last known: 167 passed, 1 skipped (non-UTF-8 path round trip skips on macOS APFS, Errno 92).
- `dev/bin/release` needs sibling `../claude-plugins`, pulls, tags, pushes. Never run from a session.

## Active Work

### Batch 202611082330
- [x] 00007-parallel-claims-share-prd-number-v1.md (1 cycle)
- [x] 00008-integrity-check-misses-git-hooks-v1.md (1 cycle)
- [x] 00011-snapshot-hangs-on-fifo-v1.md (1 cycle)
- [x] 00012-inherited-git-dir-misreads-target-v1.md (1 cycle)
- [x] 00013-integrity-check-misses-worktrees-submodules-v1.md (1 cycle)
- [x] 00014-allocator-accepts-non-repo-path-v1.md (1 cycle)
- [x] 00015-allocator-follows-symlinked-prds-v1.md (1 cycle)
- [x] 00016-slug-trailing-newline-accepted-v1.md (1 cycle)
- [x] 00017-crafted-snapshot-injects-restore-options-v1.md (fast-track, 1 card)
- [x] 00018-non-utf8-ref-restore-fails-v1.md (1 cycle)
- [x] 00019-snapshot-memory-grows-with-dirty-file-v1.md (fast-track, 1 card)
- [x] 00020-allocator-errors-print-traceback-v1.md (fast-track, 1 card)
- [ ] 00009-integrity-check-misses-untracked-edits-v1.md (parked in hold/)
- [ ] 00010-snapshot-runs-repo-configured-programs-v1.md (parked in hold/)
- [x] 00021-lane-git-identity-overridden-v1.md (fast-track, 1 card)
- [x] 00022-readme-gym-link-404-v1.md (solo lane, 1 cycle)
- [x] 00023-ci-release-checks-suite-drift-v1.md (1 cycle)

Observations: 00007 fixed parallel PRD-number claims with a directory flock (fast-track lane, 1 review pass). 00008 fixed the integrity check missing git hooks and .git/info changes (fast-track lane escalated to full, 1 review pass). 00011 fixed target_snapshot hanging on a named pipe (fast-track lane, override to full, 1 review pass). 00012 fixed inherited GIT_DIR/GIT_WORK_TREE env vars redirecting the snapshot target (fast-track lane, 1 review pass, no findings survived). 00013 fixed the integrity check missing worktrees and submodules (fast-track lane, 1 review pass). 00014 fixed the allocator accepting a non-repo path (fast-track lane, 1 rework cycle). 00015 fixed the PRD-number allocator following a symlinked PRD out of the repo (fast-track lane, 1 review pass, 7 MEDIUM/LOW findings did not survive, no rework). 00018 fixed non-UTF-8 ref restore quoting raw bytes (fast-track lane escalated to full on an unnamed-path signal, 1 review pass, no findings survived). 00019 fixed snapshot memory growth on dirty files by hashing in chunks (fast-track lane, 1 review pass, codex lens unavailable (sandbox failure x2)). 00020 fixed the allocator printing an 11-line traceback instead of a one-line exit-2 message on OS errors and bad slugs (fast-track lane, 1 review pass). 00021 fixed the lane overriding the user's git identity env vars (fast-track lane, override, 1 review pass, no findings survived). 00022 fixed the dead agoge-gym README link with plain text (solo lane, override, 1 review pass, no findings survived). 00023 fixed CI release-checks to show pytest skips instead of overclaiming suite parity (solo lane escalated to full on an unnamed-path signal, 1 review pass, no findings survived). Batch 202611082330 drained backlog/wip; 00009 and 00010 remain parked in hold/ pending operator triage.

### Batch 202611021020 (closed)
- [x] 00006-decode-git-output-as-filesystem-bytes-v1.md (fast-track lane, 1 review pass; finalized in 2b9b475)

Fix is **unreleased**: `CHANGELOG [Unreleased]` carries one Fixed entry after `[0.3.0] - 2026-11-02`; tags go v0.1.0..v0.3.0.

### Batch 202611012029 (closed)
- [x] 00003 (2 cycles), 00005 (2 cycles). 00005 deferred a residual strict `.decode()` at the rework cap; that became PRD 00006.

### Open items from `audit-results/agoge-followups-2026-11-02.md` (item 1 resolved; round trip verified 2026-11-04)
- Non-UTF-8 path round trip: passes on Linux CI (run 41791600904, 168 passed, 0 skipped). Still skips on macOS APFS.
- One full-suite run showed 6 git subprocess SIGKILLs (exit -9) in an agent session. Not reproduced: 5 local runs (4 in parallel) and 2 CI runs all clean. Likely environmental (sandbox), not code; reopen if it recurs.
- Docs branch `docs/agoge-0.3.0` (agent-skills `56ba216`) is blocked on that repo's closeout plan; the 00006 fix needs its own mirror line at the next release.
- Cross-repo carries (OVCAQ 00060 push hold; AP 00015 verification counts) live in other repos, not here.

Working tree: `docs/dev/project-management/meta/agoge-profile.md` is untracked (recon output, last recon 2026-11-03 at HEAD 035f5d2; `Authorization:` asserted by the operator 2026-11-05). Local master == origin/master.

## Related context

No topic this session: on master with no wip PRD, so the engram queries were skipped. The repo was not gita-registered, so `engram harvest` returned `no_repo`; after `gita add` (2026-11-04) it upserted the 5 review files. The 3 `*-audit.md` files have no frontmatter and are not harvestable. Staleness stamp not taken.

## GitHub State

- 0 open issues, 0 open PRs.
- Active branches (14d): `origin/master` only.
- No GitHub releases; versions are git tags v0.1.0..v0.3.0.
- CI: `.github/workflows/test.yml` (e95d42f) runs pytest on ubuntu and macOS for every push and PR. First run green on both.

## Project Health

Healthy and idle. CI green on both OSes. Backlog is empty. Remaining risks: unreleased 00006 fix, SIGKILL flake seen once and not reproduced, none on authorization: the operator asserted it in the profile on 2026-11-05, so trudy can run.

## Project Memories

- Whole-file python reformatting (probably a loupe autofix hook) can leave AST-identical churn in `target_snapshot.py` and its test after edits or test runs. Before committing or reviewing, `git status`; if dirty without your edits, AST-compare against HEAD, then `git checkout -- <file>`. Never commit the churn.
