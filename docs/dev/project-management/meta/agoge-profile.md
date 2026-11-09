# Agoge profile: claude-agoge

## Surfaces

All commands run from the repo root. The product is a Claude Code plugin: markdown personas and prompts plus two stdlib-only Python helper scripts and their pytest suites. There is no application server, UI, or database.

**Change since the last recon (1d88753..c7da90f).** 34 product commits, `git diff --stat 1d88753 HEAD -- skills agents README.md CHANGELOG.md .claude-plugin dev .github`: 12 files, +1076/-66.
- `target_snapshot.py` (snapshot `VERSION` 1 -> 3): no hang on a fifo (non-regular files fingerprint as `special:<mode>`), drops inherited `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`/`GIT_OBJECT_DIRECTORY`/`GIT_ALTERNATE_OBJECT_DIRECTORIES`/`GIT_COMMON_DIR`/`GIT_NAMESPACE`, new violation kinds `worktree-head`, `submodule` (recursive snapshot of each initialized submodule) and `gitdir` (hashes every file in the common git dir outside a skip list: hooks, `info/exclude`, `info/attributes`, worktree config), rejects a `before.json` with a ref not under `refs/` or a non-hex oid, quotes non-UTF-8 bytes in `restore` as bash `$'...'`, hashes dirty files in 1 MiB chunks.
- `allocate_prd_number.py`: directory `flock` on `prds/` around scan-and-create, refuses a path that is not a git work-tree top level (strips the same GIT_* vars), refuses when `prds/backlog` resolves outside the repo, `SLUG_RE.fullmatch` (rejects trailing newline), every error is one `allocate_prd_number: <reason>` line with exit 2.
- `finding-contract.md`: lane git identity now uses a one-shot `env GIT_AUTHOR_NAME=... GIT_COMMITTER_NAME=...` prefix, because an exported identity beats `-c user.name`.
- `prd-emission.md`: emitted PRDs follow create-prd's minimal template; pinned by the new `test_prd_emission_contract.py`.
- README: the agoge-gym link is now plain text ("private, local fixture gym").
- CI comment softened to "Same tests ... (interpreter may differ)"; `dev/bin/release-checks` and CI both pass `-rs`.
- CHANGELOG `[Unreleased]` gained 14 Fixed entries. No version bump.

**Test suite (verified, runs green).**
- Command: `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs` (identical to `dev/bin/release-checks`).
- Result at HEAD c7da90f, run with `env PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`: `201 passed, 2 skipped in 17.10s` (was 167 passed, 1 skipped).
- Both skips are APFS rejecting non-UTF-8 names (`Errno 92`): `test_target_snapshot.py:646` (non-UTF-8 path round trip) and `test_target_snapshot.py:899` (restore command for a non-UTF-8 ref). Neither is exercised on this host.
- Suites in `skills/run-agoge/scripts/`: `test_agoge_authorization_gate.py`, `test_agoge_registry.py`, `test_allocate_prd_number.py`, `test_prd_emission_contract.py` (new), `test_run_integrity.py`, `test_scratch_contract.py`, `test_sidecar_contract.py`, `test_target_snapshot.py`.
- With the two flags above the run wrote nothing new into the checkout (`git status --short --ignored` unchanged; pre-existing ignored `.pytest_cache/`, `__pycache__/`, `.ruff_cache/`).

**CI (via `gh run list -R buvis/claude-agoge`).** `.github/workflows/test.yml`: `python -m pytest -q -rs` in `skills/run-agoge/scripts`, ubuntu-latest and macos-latest, Python 3.12 with pip pytest. The newest run is 42527213761 (2026-11-08, commit a24792f, success). **No CI run covers anything after a24792f**: local master is 97 commits ahead of `origin/master` (`git rev-list --left-right --count origin/master...HEAD` gives `0 97`, local tracking ref, not re-fetched). So the non-UTF-8 restore test (skipped here) has never run on Linux, and none of the 0.3.0..HEAD fixes after a24792f has CI evidence.

**CLI entry points (re-verified at this HEAD; local Python 3.15.2).**
- `python3 -I skills/run-agoge/scripts/target_snapshot.py {snapshot <repo> <out.json> | compare <repo> <before.json> [--allow <path>]...}`. `--help` works.
  - Exit 0 = unchanged, 1 = changed, 2 = cannot run (one `target_snapshot: <reason>` line).
  - Probed in a scratch repo: `snapshot` then `compare` gave exit 0. After writing `.git/hooks/pre-commit`, `compare` gave exit 1 with one `gitdir` violation, `path: hooks/pre-commit`, `before: null`.
  - Runs `git --no-optional-locks -C <repo> ...`; depends on the system `git`.
- `python3 -I skills/run-agoge/scripts/allocate_prd_number.py <repo> <slug>`.
  - Bare: usage line, exit 2.
  - Probed in a scratch repo: a subdirectory gave exit 2, `allocate_prd_number: <path> is not the top level of a git work tree`; slug `Bad Slug` gave exit 2, `allocate_prd_number: slug must be kebab-case, got 'Bad Slug'`; two valid calls created `00001-my-slug-v1.md` and `00002-other-slug-v1.md` in `prds/backlog/`.
  - It WRITES into `<repo>`. Point it only at a scratch repo.
- `dev/bin/release`: needs sibling `../claude-plugins`, pulls, commits, tags. Do NOT run. `dev/bin/release-checks` is the pytest command above.

**Prompt and contract surface (read, not executable).** `skills/run-agoge/SKILL.md`, `skills/run-agoge/references/*.md` (finding contract with scratch contract; browser, data, perf, security, authoring and prd-emission playbooks), `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md`. Pinned only by the pytest hygiene suites; running the skill needs a live Claude Code session no lane can start.

**Dev server / built server:** none. No `package.json`, `pyproject.toml`, `Dockerfile`, `*.html` or `*.sql` in the tracked tree (`rg --files`). No port.

**Browser:** no browser surface. Playwright Chromium builds exist in `~/Library/Caches/ms-playwright` (chromium-1228/1234/1243, re-checked), but the product has no page to drive.

**Database:** none. State is git repositories and files.

**External services:** none called by the code. Scripts need local `git` and Python 3 (`uv` on PATH). `dev/bin/release` reaches `buvis/claude-plugins`; not lane-relevant. GitHub Actions readable through `gh`. create-prd's template, which `prd-emission.md` claims to follow, is local at `~/git/src/github.com/buvis/agent-skills/skills/create-prd/assets/minimal.md`.

**Notes (read from code, not probed; for the lanes).**
- `_gitdir_files` opens every file under the git dir outside the skip list with a plain `open()` and `read()`: no `lstat` regular-file check and no chunking. A fifo or a symlink-to-fifo in `.git/hooks/` or `.git/info/` may hang the snapshot (same class as the fixed tracked-file fifo bug), a symlink there is followed, and a huge file is read whole.
- Submodule snapshots recurse with no depth bound and nested submodule refs in `before.json` skip the new malformed-ref check (only top-level `refs` are validated; nested ones are only compared for equality).
- `allocate_prd_number.py` checks backlog containment in `main()` before `claim()` runs `mkdir(parents=True)`: a check-then-act window.
- The scratch contract pasted into this recon's dispatch prompt still gives the old `-c user.name` identity form; the product's `finding-contract.md` now mandates the `env` form. The dispatching master is using stale contract text.
- Working tree at recon: modified `docs/dev/project-management/autopilot/{ledger/,}loop-metrics.jsonl` and untracked `autopilot/reports/202611082330-*`, autopilot state, not product.
- Tags v0.1.0..v0.3.0; `plugin.json` and `marketplace.json` both 0.3.0; CHANGELOG top release `[0.3.0] - 2026-11-02` with a 15-entry `[Unreleased]` Fixed list.

## Per-specialist strategy

| Specialist | Verdict | Tactics / reason |
|---|---|---|
| walter | armed | Run the two CLIs as a user would, scratch root only. (1) `target_snapshot.py` journey: snapshot a scratch repo, then each mutation the CHANGELOG now claims to catch, and compare: a hook added/edited in `.git/hooks`, `.git/info/exclude` and `.git/info/attributes` edits, worktree-local config, a linked worktree whose HEAD moves (`worktree-head`), a commit/edit/new file inside a checked-out submodule (`submodule`), a fifo in place of a tracked file (must report `tracked`, not hang; wrap in `timeout`), plus the old cases (`--allow`, missing or foreign snapshot, `<out.json>` inside repo, subdir, non-repo, empty repo). Confirm an uninitialized submodule is unchecked as documented. (2) `allocate_prd_number.py` journey: empty repo, existing PRDs in each lifecycle dir, concurrent callers with different slugs (distinct numbers), subdir/missing path/non-repo (exit 2, one line), bad slugs incl. trailing newline. (3) Full pytest command; baseline 201 passed, 2 skipped. |
| heidi | armed | No database; the surface is the git contract. (1) Env isolation: run both scripts with exported `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR` pointing at a second scratch repo; the result must describe the named repo only. Try vars outside the strip list too (`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`/`KEY_0`/`VALUE_0`, `GIT_CEILING_DIRECTORIES`) and report any that change snapshot output. (2) Git-dir edge cases: `.git` as a gitfile (linked worktree as `<repo>`, submodule as `<repo>`), `--git-common-dir` vs per-worktree dirs (does a change in `.git/worktrees/<wt>/config.worktree` register? `worktrees` is in the skip list), nested submodules, packed vs loose refs, detached HEAD in a linked worktree, prunable/locked worktrees. (3) Snapshot version bump: a v1 `before.json` must be refused with exit 2. (4) Path contract: what `SKILL.md` passes to both scripts vs what they accept. Use `env GIT_AUTHOR_NAME=agoge-heidi ...` identity per the current finding-contract. |
| judy | unarmed | No UX surface: no web UI, no HTML or Node project (`rg --files` finds none), nothing for a browser to drive. The only interfaces are two CLIs whose usage and error text walter covers. |
| wendy | armed | (1) Each of the 15 `[Unreleased]` Fixed entries against behaviour at HEAD: reproduce each claim in scratch (hooks/info/worktree-config detection, fifo, GIT_DIR, worktree-head, submodule incl. "uninitialized still unchecked", malformed refs, chunked hashing, allocator refusals, symlink containment, trailing newline, one-line exit 2, flock distinct numbers, lane identity env form in `finding-contract.md`, PRD shape). Non-UTF-8 restore quoting cannot run on APFS: emulate with git objects/refs in scratch and report `mocked`; note there is no Linux CI evidence because no run covers commits after a24792f. (2) `prd-emission.md` shape vs `~/git/src/github.com/buvis/agent-skills/skills/create-prd/assets/minimal.md`, heading by heading. (3) Versions: plugin.json 0.3.0, marketplace.json 0.3.0, CHANGELOG 0.3.0, tag v0.3.0. (4) CI comment "Same tests as dev/bin/release-checks (interpreter may differ)" vs the two commands. (5) README: gym text, profile path, `--authorized` flow, seven-specialist roster vs `agents/`, Development test command. (6) Docstring of `target_snapshot.py` lists violation kinds; check against `compare()`. |
| peggy | armed | `target_snapshot.py` runs at least three times per agoge run on arbitrary repos and now also walks and hashes the whole git dir (except skipped tops) and recurses into submodules. Time `snapshot` and `compare` on scratch repos with 1k/10k/50k tracked files, many untracked and dirty files, a large dirty file (confirm peak RSS stays bounded, `/usr/bin/time -l`), a git dir with many/large files under non-skipped paths (e.g. `.git/lfs`, `.git/rr-cache`, big hooks; `_gitdir_files` reads each whole), and 1-3 levels of submodules. Report scaling, not one number. Time `allocate_prd_number.py` with thousands of PRDs and N parallel callers (flock serializes). Suite baseline 17.1s locally. |
| trudy | armed | Decided on surface alone: both scripts take outside paths and slugs, and `target_snapshot.py` runs git over an untrusted repo and now reads every file in its git dir. Scratch root only. (1) `_gitdir_files`: a fifo, a symlink to a fifo, a symlink to `/dev/zero` or to a file outside the repo, and an unreadable file under `.git/hooks` or `.git/info`; expect exit 2 or a clean result, not a hang (always `timeout`). (2) Submodule recursion: a `.git` gitfile in a gitlink path pointing to an outside repo, self-referencing or deep nesting. (3) `before.json` crafted: malformed nested submodule refs, non-dict `refs`, huge file, wrong `version`; restore-string injection via ref names with quotes, `$'`, newlines, backslashes and non-UTF-8 bytes (check the `$'...'` quoting by running the restore string against a scratch repo). (4) Repo config: `core.fsmonitor`, `core.hooksPath`, `core.pager`, `diff.external`, `filter.*.clean` to a scratch marker; does snapshot execute it? (5) Allocator: symlinked `docs`, `project-management`, `prds`, `backlog` leaving the repo; swap a dir for a symlink between the containment check and `mkdir` (race loop); symlinked lifecycle dirs read by `claimed_numbers`; slug traversal, NUL, unicode. Gated at dispatch by `Authorization:` or `--authorized`, not by this row. |

## Mocking strategy

No external service is called by the code, so nothing needs a mock for the probes above. Not reachable or not run:
- `/run-agoge` itself (needs a live Claude Code session and subagent dispatch): do not simulate. Report full-pipeline claims as `unverified`.
- `dev/bin/release` (needs `../claude-plugins`, pulls, tags, pushes): do not run. Claims about it are `unverified`, not `mocked`.
- Non-UTF-8 file names and refnames: APFS rejects them. Emulate only with git objects/refs built in a scratch repo (`git update-index --cacheinfo` with a raw byte path, `git update-ref` with a raw byte name), and report `mocked`, not `verified`. No CI run covers HEAD, so there is no real-disk evidence for the restore-quoting fix; do not trigger CI.

## Authoring assignments

- Surface: `skills/run-agoge/scripts/` helpers. Runner: pytest via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs` (CI runs the same files with `python -m pytest -q -rs`). New tests go in `skills/run-agoge/scripts/test_*.py` beside the existing suites.
- Worth a regression test: any verified defect in `target_snapshot.py` (exit-code contract, `gitdir` walk on non-regular or symlinked files, submodule recursion, env isolation, `before.json` validation, restore quoting) or `allocate_prd_number.py` (flock claim, top-level and containment refusals, slug validation).
- Doc-contract defects (prompt text, README, CHANGELOG, PRD template drift) go in the hygiene suites (`test_scratch_contract.py`, `test_agoge_registry.py`, `test_run_integrity.py`, `test_prd_emission_contract.py`).
- No specialist executes this. The master authors on a branch after the lanes report.

## Pins and vetoes

Authorization: this project is the operator's own or explicitly authorized.

## Freshness stamp

Last recon: 2026-11-09
Target HEAD: c7da90f77df15e18795e5a871f4a5b1ce2e051ff
