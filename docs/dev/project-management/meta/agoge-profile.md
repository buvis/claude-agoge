# Agoge profile: claude-agoge

## Surfaces

All commands run from the repo root. The product is a Claude Code plugin: markdown personas and prompts plus two stdlib-only Python helper scripts and their pytest suites. There is no application server, UI, or database.

**Change since the last recon (c7da90f..de4db0b).** 20 product commits (PRDs 00009 and 00010), `git diff --stat c7da90f HEAD -- skills agents README.md CHANGELOG.md .claude-plugin dev .github`: 7 files, +1650/-493. Only `target_snapshot.py`, its tests, `SKILL.md` and `CHANGELOG.md` changed; `allocate_prd_number.py`, `agents/`, `references/`, README, plugin manifests and CI are untouched.
- `target_snapshot.py`, snapshot `VERSION` 3 -> 4 (older snapshots are refused, exit 2):
  - Records `untracked_fingerprints` (one per untracked path, via `_fingerprint`: lstat, symlink target hash, `special:<mode>`, chunked sha256) and `ignored` (names only, from `git ls-files -o -i --exclude-standard` with and without `--directory`).
  - New violation kinds `untracked-modified` and `ignored-removed`; `--allow` exempts both. Edits inside ignored files are documented as not checked.
  - An unreadable untracked file (mode 000, other owner) makes `snapshot` and `compare` exit 2 (fail closed, documented).
  - Every git call now runs with `core.fsmonitor=false` and with `filter.<name>.clean=""`, `.process=""`, `.required=false` for every filter driver found by `git config --includes --null --name-only --get-regexp '^filter\..*\.(clean|process|required)$'`, unioned recursively over initialized submodules and memoized per realpath. Overrides go in through `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`, after inherited non-filter pairs, so they win.
  - The env now also drops `GIT_CONFIG`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS` and every `GIT_CONFIG_KEY_*`/`VALUE_*` (inherited pairs that are not filter keys are re-emitted). `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM` are kept on purpose.
  - The docstring states that `core.pager`, `core.hooksPath` hooks, `diff.external`, `core.alternateRefsCommand` and credential helpers are out of scope.
- New `snapshot_fixtures.py` (shared test helpers). `test_target_snapshot.py` was split into it plus `test_target_snapshot_state.py` and `test_target_snapshot_programs.py`.
- `SKILL.md` step 6 now names `untracked-modified` and `ignored-removed` and says edits inside ignored files still pass.
- CHANGELOG `[Unreleased]` gained 3 Fixed entries (now 18). No version bump: `plugin.json` and `marketplace.json` both 0.3.0.

**Test suite (verified, runs green).**
- Command: `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs` (identical to `dev/bin/release-checks`).
- Result at HEAD de4db0b, run with `env PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`: `241 passed, 2 skipped in 48.33s` (was 201 passed, 2 skipped in 17.10s; wall time almost tripled).
- Both skips are APFS rejecting non-UTF-8 names (`Errno 92`): `test_target_snapshot.py:502` (non-UTF-8 path round trip) and `test_target_snapshot_state.py:508` (restore command for a non-UTF-8 ref).
- Suites in `skills/run-agoge/scripts/`: `test_agoge_authorization_gate.py`, `test_agoge_registry.py`, `test_allocate_prd_number.py`, `test_prd_emission_contract.py`, `test_run_integrity.py`, `test_scratch_contract.py`, `test_sidecar_contract.py`, `test_target_snapshot.py`, `test_target_snapshot_state.py` (new), `test_target_snapshot_programs.py` (new).
- With the two flags the run wrote nothing new into the checkout (`git status --short --ignored` identical before and after; pre-existing ignored `.pytest_cache/`, `__pycache__/`, `.ruff_cache/`).

**CI (via `gh run list -R buvis/claude-agoge`).** `.github/workflows/test.yml`: `python -m pytest -q -rs` in `skills/run-agoge/scripts`, ubuntu-latest and macos-latest, Python 3.12. Newest run 42738497418 (2026-11-10, push of HEAD de4db0b "close PRD 00010", success, 1m15s). Local master and `origin/master` are level (`rev-list --left-right --count` gives `0 0`, local tracking ref, not re-fetched). So HEAD now has CI evidence on Linux. Not read: the per-job skip list, so whether the two non-UTF-8 tests actually ran on ubuntu is not established.

**CLI entry points (re-verified at this HEAD; local Python 3.15.2, git 2.56.0).**
- `python3 -I skills/run-agoge/scripts/target_snapshot.py {snapshot <repo> <out.json> | compare <repo> <before.json> [--allow <path>]...}`. `--help` works.
  - Exit 0 = unchanged, 1 = changed, 2 = cannot run (one `target_snapshot: <reason>` line).
  - Probed in a scratch repo with `filter.evil.clean = "touch <scratch>/MARK; cat"` on `*.txt`, a touched `a.txt`, an ignored dir, an ignored `x.log` and an untracked file. Control: plain `git status` created MARK. `snapshot` exit 0 and MARK not created; same with `GIT_CONFIG=/dev/null` exported. `compare` unchanged gave exit 0. After deleting `x.log` and rewriting the untracked file, `compare` gave exit 1 with `untracked-modified` (`untr`) and `ignored-removed` (`x.log`).
  - Runs `git --no-optional-locks -C <repo> ...`; depends on the system `git`.
- `python3 -I skills/run-agoge/scripts/allocate_prd_number.py <repo> <slug>`. Bare: usage line, exit 2 (re-checked). Code unchanged since c7da90f; the previous recon's scratch probes (subdir refusal, bad slug, two allocations) still describe it. It WRITES into `<repo>`. Point it only at a scratch repo.
- `dev/bin/release`: needs sibling `../claude-plugins`, pulls, commits, tags. Do NOT run. `dev/bin/release-checks` is the pytest command above.

**Prompt and contract surface (read, not executable).** `skills/run-agoge/SKILL.md`, `skills/run-agoge/references/*.md`, `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md`. Pinned only by the pytest hygiene suites; running the skill needs a live Claude Code session no lane can start.

**Dev server / built server:** none. No `package.json`, `pyproject.toml`, `Dockerfile`, `*.html` or `*.sql` in the tracked tree (unchanged paths since last recon). No port.

**Browser:** no browser surface. Playwright Chromium builds exist in `~/Library/Caches/ms-playwright` (chromium-1228/1234/1243, re-checked), but the product has no page to drive.

**Database:** none. State is git repositories and files.

**External services:** none called by the code. Scripts need local `git` and Python 3 (`uv` on PATH). `dev/bin/release` reaches `buvis/claude-plugins`; not lane-relevant. GitHub Actions readable through `gh`.

**Notes (read from code, not probed; for the lanes).**
- `_gitdir_files` is unchanged: plain `open()` + whole `read()` of every file under the common git dir outside the skip list, no `lstat` check, no chunking. A fifo or symlink-to-fifo in `.git/hooks/` or `.git/info/` may hang; a symlink is followed; a huge file is read whole. Still open from last recon.
- Submodule recursion still has no depth bound, now in two places (`take_snapshot` and `_filter_overrides`). Nested submodule refs in `before.json` still skip the malformed-ref check.
- The filter fix covers `clean`/`process`/`required` and `core.fsmonitor` only. It relies on `git config` discovery seeing every source git status sees; conditional includes (`includeIf "onbranch:"`, `"hasconfig:remote.*.url:"`, `gitdir:` against a worktree) and `GIT_CONFIG_GLOBAL`/`SYSTEM` redirects are the places that symmetry could break.
- Snapshot cost grew: every untracked file is now hashed and every ignored file name is listed (the non-`--directory` call walks into ignored trees such as `node_modules/`, `.venv/`) and stored in `before.json`.
- Fail-closed on an unreadable untracked file means a target with one such file cannot be snapshotted, so the run dispatches nobody.
- `allocate_prd_number.py`: backlog containment check in `main()` before `mkdir(parents=True)` in `claim()`, a check-then-act window. Unchanged.
- The scratch contract in this recon's dispatch prompt still gives the `-c user.name` identity form; `references/finding-contract.md:103-105` mandates the `env GIT_AUTHOR_NAME=...` form. The dispatching master still carries stale contract text.
- Working tree at recon: modified `docs/dev/project-management/autopilot/{ledger/,}loop-metrics.jsonl` and untracked `autopilot/reports/202611091445-*`, autopilot state, not product.

## Per-specialist strategy

| Specialist | Verdict | Tactics / reason |
|---|---|---|
| walter | armed | Run the two CLIs as a user would, scratch root only. (1) `target_snapshot.py` new journeys: snapshot, then (a) rewrite, truncate, chmod, replace-with-symlink and replace-with-fifo an untracked file -> `untracked-modified`; (b) delete an ignored file, an ignored file inside an ignored dir, a whole ignored dir, an empty ignored dir -> `ignored-removed`; (c) edit inside an ignored file -> must stay unchanged (documented); (d) `--allow` on each of those paths; (e) chmod 000 an untracked file before snapshot and before compare -> exit 2 with one line; (f) a `before.json` from VERSION 3 -> exit 2. Wrap every call in `timeout`. (2) Regression sweep of the older kinds (hooks, info/exclude, worktree-head, submodule, tracked fifo, subdir, non-repo, out.json inside repo). (3) `allocate_prd_number.py` smoke: valid slug, bad slug, subdir. (4) Full pytest command; baseline 241 passed, 2 skipped. |
| heidi | armed | No database; the surface is the git contract. (1) Filter discovery vs git: put `filter.<x>.clean` (marker-writing) in every source and confirm no marker: local, `config.worktree` with `extensions.worktreeConfig`, `include.path`, `includeIf "gitdir:"`, `includeIf "onbranch:"`, `includeIf "hasconfig:remote.*.url:"`, `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` pointing at scratch files, an inherited `GIT_CONFIG_COUNT` pair, `GIT_CONFIG_PARAMETERS` (`git -c`), a driver name with dots/spaces/`=`, mixed-case keys, and a filter declared only in a nested (2-level) submodule. Also `filter.<x>.process` (long-running protocol) and `required=true` with the driver missing. (2) Env isolation regression: exported `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_CONFIG` must not change the named repo's result. (3) Disabled filters: a normalizing filter (e.g. CRLF or `ident`-like) makes `dirty` list more paths than git; confirm snapshot and compare agree with each other so no false `tracked` violation appears on an untouched repo. (4) Ignored listing correctness: `.git/info/exclude`, `core.excludesFile`, negated patterns, ignored files inside submodules, linked worktree as `<repo>`. (5) VERSION 4 refusal of a v3 file. Use `env GIT_AUTHOR_NAME=agoge-heidi ...` identity per `finding-contract.md`. |
| judy | unarmed | No UX surface: no web UI, no HTML or Node project in the tracked tree, nothing for a browser to drive. The only interfaces are two CLIs whose usage and error text walter covers. |
| wendy | armed | (1) The 3 new `[Unreleased]` Fixed entries against behaviour at HEAD: overwritten untracked / deleted ignored detection, "no longer runs the repo's fsmonitor or clean filter programs" (check the wording vs code: `process` filters are also disabled, `core.pager`/`hooksPath`/`diff.external` are not, so the entry must not read as "runs no repo programs"), and the `GIT_CONFIG` entry including the quoted `only one config file at a time` error (reproduce on a pre-fix commit cloned into scratch, e.g. `git clone` then check out `c7da90f`). Spot-check the 15 older entries still hold. (2) `SKILL.md` step 6 text vs `compare()` kinds and the docstring list; `target_snapshot.py` docstring vs `compare()` (12 kinds). (3) README test command and roster vs the split suites and `agents/`. (4) Versions: plugin.json 0.3.0, marketplace.json 0.3.0, CHANGELOG top release 0.3.0, tag v0.3.0; snapshot `VERSION` 4 is internal, not a product version. (5) CI claim: run 42738497418 covers HEAD; read its logs with `gh run view 42738497418 --log -R buvis/claude-agoge` to see whether the two non-UTF-8 tests ran or skipped on ubuntu. Do not trigger CI. |
| peggy | armed | `target_snapshot.py` runs at least three times per agoge run on arbitrary repos and now also hashes every untracked file, lists every ignored file, and runs filter discovery (one extra `git config` and `ls-files --stage` per repo and submodule). Time `snapshot` and `compare` (and peak RSS with `/usr/bin/time -l`) on scratch repos with: 1k/10k/50k tracked files; 10k/100k untracked files; an ignored tree of 100k files (`node_modules`-like) and a few multi-GB ignored/untracked files; a large git dir (`.git/lfs`, `.git/rr-cache`, big hook); 1-3 submodule levels. Report scaling and `before.json` size, not one number. Compare against c7da90f (clone into scratch, check out) to show the regression from PRD 00009/00010. Suite time went 17.1s -> 48.3s locally; find the slow tests with `--durations=15`. |
| trudy | armed | Decided on surface alone: `target_snapshot.py` runs git over an untrusted repo and reads files in it; the allocator takes outside paths. Scratch root only, `timeout` on every call. (1) Program execution: confirm the documented out-of-scope vectors are not actually reached by the snapshot's git calls (`core.pager`, `core.hooksPath` + every hook, `diff.external`, `diff.<x>.textconv`, `core.alternateRefsCommand`, `credential.helper`, `core.sshCommand`, `gpg.program`, `uploadpack.packObjectsHook`) using marker files; then try to defeat the filter fix (driver hidden from `git config --get-regexp` but seen by status, include cycles, an include file unreadable during discovery, a submodule whose `.git` is a gitfile to an outside repo, a submodule added between discovery memoization and use). (2) `_gitdir_files`: fifo, symlink to fifo, symlink to `/dev/zero`, symlink outside the repo, unreadable file under `.git/hooks` or `.git/info`; expect exit 2 or clean result, not a hang. (3) New untracked fingerprinting: untracked fifo, symlink to `/dev/zero`, symlink to a secret outside the repo (is only the link target hashed?), huge sparse file. (4) Crafted `before.json`: missing `untracked_fingerprints` key or entry (KeyError path -> must be exit 2, not traceback), non-dict values, wrong `version`, malformed nested submodule refs, restore-string injection via ref names. (5) Allocator: symlinked path components and the containment-to-mkdir race. Gated at dispatch by `Authorization:` or `--authorized`, not by this row. |

## Mocking strategy

No external service is called by the code, so nothing needs a mock for the probes above. Not reachable or not run:
- `/run-agoge` itself (needs a live Claude Code session and subagent dispatch): do not simulate. Report full-pipeline claims as `unverified`.
- `dev/bin/release` (needs `../claude-plugins`, pulls, tags, pushes): do not run. Claims about it are `unverified`, not `mocked`.
- Non-UTF-8 file names and refnames: APFS rejects them. Emulate only with git objects/refs built in a scratch repo (`git update-index --cacheinfo` with a raw byte path, `git update-ref` with a raw byte name), and report `mocked`, not `verified`. Real-disk evidence can only come from the existing CI run logs (read, do not trigger).
- Files owned by another user: cannot be created without root. Use mode 000 as the stand-in and report owner-based cases as `mocked`.

## Authoring assignments

- Surface: `skills/run-agoge/scripts/` helpers. Runner: pytest via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs` (CI runs the same files with `python -m pytest -q -rs`). Snapshot tests go in `test_target_snapshot_state.py` (state and violation kinds) or `test_target_snapshot_programs.py` (programs the target configures), using the helpers in `snapshot_fixtures.py`; allocator tests in `test_allocate_prd_number.py`.
- Worth a regression test: any verified defect in `target_snapshot.py` (filter or fsmonitor execution through a missed config source, `gitdir` walk on non-regular or symlinked files, untracked/ignored detection, `before.json` validation, submodule recursion, env isolation, restore quoting) or `allocate_prd_number.py` (flock claim, containment race, slug validation).
- Doc-contract defects (prompt text, README, CHANGELOG, SKILL.md step 6, PRD template drift) go in the hygiene suites (`test_scratch_contract.py`, `test_agoge_registry.py`, `test_run_integrity.py`, `test_prd_emission_contract.py`).
- No specialist executes this. The master authors on a branch after the lanes report.

## Pins and vetoes

Authorization: this project is the operator's own or explicitly authorized.

## Freshness stamp

Last recon: 2026-11-10
Target HEAD: de4db0bf74d3c041265346028bfde29341d10f89
