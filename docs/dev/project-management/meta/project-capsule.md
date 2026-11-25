# Project Capsule: claude-agoge

Generated: 2026-11-25

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

### Batch 202611232314 (in progress)
- [x] 00024-snapshot-slow-many-untracked-files-v1.md (fast-track, 1 card)
- [x] 00025-gitdir-walk-hangs-on-fifo-v1.md (fast-track, 1 card)
- [x] 00026-untracked-files-hashed-in-full-v1.md (fast-track, 1 card)
- [x] 00027-allow-misses-removed-directory-contents-v1.md (fast-track, 1 card)
- [x] 00028-test-suite-takes-65-seconds-v1.md (full lane, 2 cycles)
- [x] 00029-malformed-snapshot-passes-compare-v1.md (fast-track, 1 cycle)
- [x] 00030-untracked-chmod-not-reported-v1.md (fast-track, 1 cycle)
- [x] 00031-fifo-replacement-reports-removed-v1.md (fast-track, 1 cycle)
- [x] 00032-changelog-omits-process-filters-v1.md (solo lane, 1 cycle)
- [x] 00033-gpg-program-runs-on-compare-v1.md (fast-track, 1 cycle)
- [x] 00034-changelog-overstates-no-programs-v1.md (solo lane, 1 cycle)
- [x] 00035-allocator-backlog-path-race-v1.md (fast-track, 1 cycle + rework)
- [x] 00036-unreadable-untracked-error-wording-v1.md (fast-track, 1 cycle)
- [x] 00037-ignored-listing-grows-snapshot-v1.md (fast-track, 1 cycle + rework)
- [x] 00038-symlink-cache-outlives-snapshot-v1.md (fast-track, 1 cycle + rework)
- [ ] 00039-adopt-ruff-format-v1.md (wip/, full lane: classified full, security_path; design: skip)
- [ ] 00040-gitdir-directory-symlink-unseen-v1.md (backlog/, 1 PRD remaining)

Observations: 00038 (fast-track, 1 cycle + rework, converged): fixed the symlink-ancestor cache outliving a single snapshot. Rework fixed the one confirmed HIGH finding (two stale `== 200` lstat-count assertions left in `test_target_snapshot.py` from an earlier PRD's fixture size, not removed per this PRD's task 3); 4 LOW findings left unfixed (stale docstring wording, a PRD-name/parameter mismatch, a redundant ternary, a minor test-hermeticity gap) and one pre-existing MEDIUM (redundant prefix-building ternary) deferred, none blocking. All five doubt-rubric checks (D1-D5) passed both cycle-1 and delta passes. Full suite 299 passed, 2 skipped. 00035 (fast-track, 1 review cycle, rework): closed the ancestor-directory TOCTOU in `claim()` — the containment check ran before `os.open` and `O_NOFOLLOW` guarded only the final path component, so an attacker swapping an intermediate directory (`prds/` or `backlog/`) between check and open could redirect a claimed PRD outside the repo. Rework pinned the backlog fd and added a post-open `os.fstat(fd)` vs `os.stat(realpath)` device/inode identity check, converted ELOOP/ENOTDIR to SystemExit instead of a raw OSError, and fixed the CHANGELOG acceptance phrase. All three findings confirmed by victor and verified fixed by Eve's round-2 delta review (reproduced live with symlink-swap probes, confirmed the fix holds with an in-memory removal test). Residual gaps recorded, not reworked (all LOW/MEDIUM, none blocking): the identity check itself is unpinned by a dedicated swap-then-restore-before-realpath test; a double ancestor swap (swap, restore, swap) still escapes — out of this PRD's specified mechanism and would break the supported in-repo `prds` symlink case; the allocator scans the backlog by path while locking/writing through the fd; redundant `O_NOFOLLOW` on candidate creation; `main()` still exceeds the 50-line limit (pre-existing). Full suite 288 passed, 2 skipped. 00032 (solo lane, 1 review pass, no findings survived): one-line CHANGELOG edit naming process filters alongside fsmonitor/clean; `review-fanout` workflow ran clean (no dimension findings, all 12 rubric rules pass); full suite 284 passed, 2 skipped (summary line parsed by eye, `autopilot verify` itself exited 3 - "gate exited 0, no parseable summary" - likely a summary-regex gap for this repo's pytest output shape, worth a look if it recurs). 00033 (fast-track, 1 review cycle, confirmed findings addressed): stopped `compare` from running the target repo's `gpg.program` on newly-signed refs. 00034 (solo lane, 1 review pass, no findings survived): CHANGELOG `[Unreleased]` note no longer overstates "no programs" coverage. 00024 stats each untracked file once and memoises the symlink-ancestor check (`_external_symlink_dir`, lru_cache). 3 MEDIUM items deferred to `autopilot/deferred/202611232314-deferred.json`: unpinned ancestor recursion test, process-lifetime cache (call `cache_clear()` in `take_snapshot`; matters for 00037), unused `_name` binding. 00025 fixed the git-dir walk hanging on a FIFO (fast-track lane, 1 review pass, no findings survived). 00026 samples large untracked files instead of hashing them whole (fast-track lane, 1 review pass, no findings survived). 00028 (full lane, 2 review cycles): tail-sweep converted the remaining per-test submodule builder site to the shared fixture; final suite 254 passed, 2 skipped, 47.61s. Two items deferred to `autopilot/deferred/202611232314-deferred.json` and minted as hold-triage stubs (00041, 00042): `test_target_snapshot.py` still over the 800-line cap, and the wall-time gain over the pre-change tree was noise-level (~3%), well short of the PRD's under-40s target - the dominant cost is likely the per-test python child process, not addressed by this PRD's changes. 00029 (fast-track, 1 review pass, no findings survived): rejects malformed or wrongly typed snapshot fields instead of letting compare pass on them; type-checks all 13 snapshot fields, not just 3. A formatter hook rewrites `skills/run-agoge/scripts/*.py` after edits; AST-check vs HEAD and `git checkout --` the churn. Codex sandbox fails here; pytest via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q`. 00030 (fast-track, 1 review pass): documents that permission bits of untracked files are not checked (docstring sentence) plus a pinning test; no CHANGELOG entry (docs+test only). All 5 lanes reported; 3 surviving findings, all MEDIUM/LOW (try/finally cleanup in the new test, pre-existing 800-line file-size debt, cosmetic sentence placement) — none CRITICAL/HIGH, so no victor dispatch and no rework round. The `review-fanout` workflow refused (`INVALID_ARGS: diff is required`, only `diff_path` was passed) and fell back to the native `autopilot:alice` subagent per the roster rule. 00031 (fast-track, 1 review pass): documents and pins that an ignored-but-tracked file replaced by a fifo reads as `touched-removed`, not silently dropped; the exact docstring sentence and a full-string test assertion were fixed before close across 2 consensus/blind findings. Residual gaps recorded, not reworked: the "device" third of the docstring claim is untested (needs root `mknod`); fifo/socket replacing an *ignored* file also reads as `removed` with no docstring coverage; a brand-new fifo/socket in the target is not reported at all (exit 0) - candidate for a future backlog item; `agoge-profile.md:49` still expects `untracked-modified` for this case (pre-existing, out of Files); `test_target_snapshot.py` now 947 lines, pre-existing 800-line cap breach. 00036 (fast-track, 1 review pass, no findings survived): `_fingerprint` now names the unreadable untracked file instead of letting a bare `PermissionError` propagate. 00037 (fast-track, 1 cycle + rework, converged): capped the ignored-listing cost in `take_snapshot`'s target snapshot at 20000 files, addressing the process-lifetime cache growth risk flagged as a deferred item back in 00024's review. All three prior FIX findings (`_load` validation gap, `compare` either-snapshot gap, `take_snapshot` over 50 lines) confirmed RESOLVED by mutation probe; the over-50-lines item left as a known pre-existing limitation. Two pre-existing LOW file-size findings noted, not reworked.

### Batch 202611091445 (closed)
- [x] 00009-integrity-check-misses-untracked-edits-v1.md (1 cycle)
- [x] 00010-snapshot-runs-repo-configured-programs-v1.md (2 cycles)

00010 retry: premise re-checked on master at `8c1bf7b` and it still holds - `_git` (`target_snapshot.py:65`) passes only `--no-optional-locks -C <repo>` and sanitizes `_GIT_REPO_VARS`; there is no `core.fsmonitor` or `filter.*` neutralization anywhere in the script. The prior attempt (parked branch `fast-track/00010-...-c1`, tip `d3dcc4a`, unmerged) was rejected for omitting include files, equals-named filters and submodule config. Full lane this time: design + full review gate.

00010 result: 2 review cycles, converged. Cycle 2's tail sweep fixed `TEST_ENV` in `skills/run-agoge/scripts/snapshot_fixtures.py` to strip the `GIT_CONFIG` command-scope family, so the fsmonitor positive controls stop failing under an inherited `core.fsmonitor` override. 1 LOW item deferred (either-or hedge in a test assertion, already resolved at review-close). `dev/bin/release-checks` green at close (241 passed, 2 skipped).

00009 retry: the prior attempt (parked branch `fast-track/00009-integrity-check-misses-untracked-edits-v1-c1`, tip `951401a`) failed review because `git ls-files -o -i --exclude-standard --directory` collapses ignored children into their parent dir, so deleting one child of `vault/` went unreported. The retry contract listed ignored paths as the union of the plain and `--directory` listings; implemented on master (the module had changed since: 00011 FIFO handling, 00019 chunked hashing, 00012/00013/00018). Cycle 1 converged with 2 medium tail-sweep fixes (VERSION-bump pinning test, unreadable-untracked-file exit-2 case); Pat reviewer unavailable both times (OAuth session expired), PRD-level review already covered the diff. Full suite green (212 passed, 2 skipped).

### Batch 202611082330 (closed)
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

Topic (2026-11-25): "Interactive sessions reformat the Python scripts, and the result is never committed" (00039 title). Repo and portfolio queries returned only this PRD's own sections (highest 0.0164), plus three unrelated transcript lines from other repos in the portfolio query — no prior design or decision notes on formatter adoption exist anywhere. `engram status --scope portfolio` exits 1 (expected, many repos stale): memory stale=6, transcripts stale=8 dead=9088, code stale=14, prd stale=0. `engram harvest` over this repo's `reviews/*.md` and `docs/dev/tmp/*review*.md` upserted every review/audit file that has a parseable shape; the `parse_failed` rows (most `docs/dev/tmp/review-*` scratch files, and most `*-audit.md` files) are expected — same as noted for the 00010 catchup below.

Earlier topic (2026-11-09, second catchup): "Taking a snapshot runs programs the repo's own git config names" (00010 title). Repo and portfolio queries returned identical hits, all inside this repo and all low-scoring:

- `docs/.../prds/wip/00010-...md:7-10` - 0.0328 - the PRD itself.
- `docs/.../prds/done/00012-inherited-git-dir-misreads-target-v1.md:30-36` - 0.0161 - nearest prior art: the other PRD that hardened `_git`'s environment, so its sanitization must be preserved.
- `skills/run-agoge/scripts/target_snapshot.py:170-215` - 0.0159 - `take_snapshot`, the call site.
- `docs/.../prds/wip/00010-...md:36-42` - 0.0156 - same PRD.
- `docs/.../prds/done/00012-...md:11-14` - 0.0154 - same PRD as above.

No prior design notes on git-config-driven program execution exist. `engram harvest` upserted all 20 `-review-1/2.md` files plus 3 audit logs; the other 18 `*-audit.md` files contain no decision blocks and fail to parse (expected). Staleness (`engram status --scope portfolio`, exit 1): memory stale=11, transcripts stale=6 dead=6597, code stale=1 dead=300, prd dead=168.

Earlier topic (2026-11-09): 00009's title; hits were only the PRD itself plus one unrelated agent-skills review line.

## GitHub State

- 0 open issues, 0 open PRs (re-checked 2026-11-25).
- Active branches (14d): `origin/master` only (last push 2026-11-17).
- No GitHub releases; versions are git tags.
- CI: `.github/workflows/test.yml` runs pytest. Last 5 `test` workflow runs on `master`/`v0.3.1` all `completed/success` (latest 2026-11-17); no failures recorded.

## Project Health

Healthy. CI green on both OSes. Unreleased fixes accumulate under `[Unreleased]` (00006 onward). Remaining risks: SIGKILL flake seen once and not reproduced; authorization asserted by the operator in the profile on 2026-11-05, so trudy can run.

## Project Memories

- Whole-file python reformatting (probably a loupe autofix hook) can leave AST-identical churn in `target_snapshot.py` and its test after edits or test runs. Before committing or reviewing, `git status`; if dirty without your edits, AST-compare against HEAD, then `git checkout -- <file>`. Never commit the churn.
