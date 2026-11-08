# Agoge profile: claude-agoge

## Surfaces

All commands run from the repo root. The product is a Claude Code plugin: markdown personas and prompts plus two stdlib-only Python helper scripts and their pytest suites. There is no application server, UI, or database.

**Change since the last recon (035f5d2..1d88753).** No product code changed. `git diff --stat 035f5d2 HEAD -- skills agents README.md CHANGELOG.md .claude-plugin dev` is empty. The commits added `.github/workflows/test.yml` (CI), edited this profile and `project-capsule.md`, and added `.herdr/icon.svg` (a workspace icon, not a product surface).

**Test suite (verified, runs green).**
- Command: `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q`
- Result at HEAD 1d88753, run with `env PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider -rs`: `167 passed, 1 skipped in 15.81s`.
- The one skip is `test_target_snapshot.py:617`: the macOS filesystem rejects non-UTF-8 file names (`Errno 92`). The non-UTF-8 path round trip is not exercised on this host.
- Suites in `skills/run-agoge/scripts/`: `test_agoge_authorization_gate.py`, `test_agoge_registry.py`, `test_allocate_prd_number.py`, `test_run_integrity.py`, `test_scratch_contract.py`, `test_sidecar_contract.py`, `test_target_snapshot.py`.
- The same command is the release gate (`dev/bin/release-checks`).
- Side effect: a plain run writes `.pytest_cache/` and `__pycache__/` into the checkout (both gitignored; older copies already exist there, newest dated 2026-11-04). With `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` the run wrote nothing new (verified by timestamps).

**CI (verified via `gh run list -R buvis/claude-agoge`).** `.github/workflows/test.yml` runs `python -m pytest -q -rs` in `skills/run-agoge/scripts` on ubuntu-latest and macos-latest, Python 3.12, on push, PR and manual dispatch. Last run 42114677405 (2026-11-05, commit cf6c8c2): success. Ubuntu `168 passed`, so the non-UTF-8 round trip passes on Linux; macOS `167 passed, 1 skipped` (same skip as local). HEAD 1d88753 has no CI run listed yet.

**CLI entry points (both re-verified at this HEAD; local Python 3.15.2, git 2.56.0).**
- `python3 -I skills/run-agoge/scripts/target_snapshot.py {snapshot <repo> <out.json> | compare <repo> <before.json> [--allow <path>]...}`.
  - Exit 0 = unchanged, 1 = changed, 2 = cannot run (one `target_snapshot: <reason>` line on stderr).
  - `<repo>` must be the top level of a git work tree.
  - `<out.json>` must lie outside `<repo>`. Probed: an `<out.json>` inside the repo gave exit 2 with `... is inside the target repo`.
  - Probed against a scratch repo: `snapshot`, then `compare` gave exit 0 and `"unchanged"`. After editing a tracked file, `compare` gave exit 1 with a `tracked` violation.
  - It shells out to `git --no-optional-locks -C <repo> ...`, so it depends on the system `git`.
- `python3 -I skills/run-agoge/scripts/allocate_prd_number.py <repo> <slug>`.
  - Bare invocation prints usage and exits 2 (re-verified).
  - Probed against a scratch repo: it created `docs/dev/project-management/prds/backlog/00001-my-slug-v1.md` and printed the path.
  - It WRITES into `<repo>`. Point it only at a scratch repo, never the target.
- `dev/bin/release` and `dev/bin/release-checks`. `release` needs the sibling `../claude-plugins` repo and does `git pull`, commits and tags. Do NOT run it. `release-checks` is the pytest command above.

**Prompt and contract surface (read, not executable).**
- `skills/run-agoge/SKILL.md` (master orchestration).
- `skills/run-agoge/references/*.md` (finding contract with scratch contract, and the browser, data, perf, security, authoring and prd-emission playbooks).
- `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md`.
- These are exercised only through the pytest hygiene suites, which pin their text. Running the skill itself needs a Claude Code session, which no lane can start.

**Dev server / built server:** none. `rg --files --hidden` finds no `package.json`, `pyproject.toml`, `Dockerfile`, `*.html` or `*.sql`; the only `*.svg` is `.herdr/icon.svg`. No listening port.

**Browser:** no browser surface. The repo has no web UI, no HTML and no Node project. Playwright Chromium builds may exist in the host cache (`~/Library/Caches/ms-playwright`, seen at the last recon, not re-checked), but nothing in the product has a page to drive.

**Database:** none. No schema, fixtures or seed path. The only state is git repositories and files.

**External services:** none called by the code. The scripts need only the local `git` binary and Python 3 (`uv` is on PATH). `dev/bin/release` reaches `buvis/claude-plugins` over git remote, and the README names `buvis/agoge-gym` as the eval repo. Neither is relevant to a lane. GitHub Actions is reachable read-only through `gh`.

**Notes.**
- Working tree clean at recon (`git status --short` empty; ignored entries are caches and autopilot state).
- Git tags: v0.1.0 through v0.3.0. `plugin.json` and `marketplace.json` both say 0.3.0. CHANGELOG has `[Unreleased]` (one Fixed entry, non-UTF-8 handling in `target_snapshot`) above `[0.3.0] - 2026-11-02`. The CI workflow (e95d42f, `ops`) has no CHANGELOG entry, which the changelog rule does not require for CI-only changes.

## Per-specialist strategy

| Specialist | Verdict | Tactics / reason |
|---|---|---|
| walter | armed | Run the two helper CLIs as a user would, end to end, in a scratch root only. (1) Build a scratch git repo, then `target_snapshot.py snapshot`, mutate it (edit tracked file, add/remove untracked file, commit, move a ref, add a worktree, change local config), then `compare` and check the exit code and violation kinds. Also try `--allow`, a missing or foreign snapshot file, an `<out.json>` inside the repo, a repo subdirectory, a non-repo, and an empty repo with no commit. (2) `allocate_prd_number.py` against scratch repos: empty repo, existing numbered PRDs in each lifecycle dir, concurrent callers (parallel runs must yield distinct numbers), bad slugs. (3) Run the full pytest command with `env PYTHONDONTWRITEBYTECODE=1 ... -p no:cacheprovider -rs` and report the count (baseline 167 passed, 1 skipped). |
| heidi | armed | No database. Surface is the git contract: `target_snapshot.py` against real git state in scratch repos. Cases: symlinked and external-symlink ancestors, submodules, detached HEAD, renamed or copied paths in the index, files with spaces and trailing spaces, unreadable files (expects exit 2, one line), packed and annotated-tag refs, linked worktrees, local config changes. Also probe the path contract between `SKILL.md` prompts and the scripts (arguments the master passes versus what the scripts accept). All repos go under the scratch root; use `--git-dir`/`--work-tree` per the scratch contract. |
| judy | unarmed | No UX surface: no web UI, no HTML or Node project (`rg --files --hidden` finds none), so no browser target. The only interfaces are two argparse CLIs whose usage and error text walter already exercises. |
| wendy | armed | Release truth, with files to check. (1) `CHANGELOG.md` `[Unreleased]` entry versus actual behaviour: non-UTF-8 paths cannot be created on this APFS host, so emulate with git objects in a scratch repo (report `mocked`) and cite the CI Linux job (`gh run view 42114677405 -R buvis/claude-agoge --log`, ubuntu `168 passed`) as the real-disk evidence; confirm exit 2 with one diagnostic line on an unreadable file. (2) Version agreement: `.claude-plugin/plugin.json` 0.3.0, `.claude-plugin/marketplace.json` 0.3.0, `CHANGELOG.md` top released version 0.3.0, git tag v0.3.0 (`git tag --list`, `git log`). (3) README claims versus `SKILL.md` and scripts: the profile path, the `--authorized <source>` flow, "Recon writes `Authorization: not asserted`", the seven-specialist roster against `agents/`, and the Development test command. (4) The CI workflow comment says it is the "Same suite as dev/bin/release-checks": compare the two commands (CI uses pip pytest on Python 3.12, release-checks uses `uv run --with pytest`). (5) Every command or path quoted in README and CHANGELOG resolves. |
| peggy | armed | One real cost surface: `target_snapshot.py` runs on the master's target at least three times per run (snapshot, then two compares), on arbitrary repos. Time `snapshot` and `compare` on scratch repos of growing size (for example 1k, 10k, 50k tracked files, plus many untracked files and many dirty tracked files, since each dirty path is hashed). Report wall time and scaling, not just one number. Also time `allocate_prd_number.py` with several thousand existing PRD files, and time the full pytest suite (local baseline 15.8s at this HEAD, 11s at the last recon; CI ubuntu 4.1s, macOS 13.7s). |
| trudy | armed | Decided on surface alone. Hostile-input surface exists. `target_snapshot.py` and `allocate_prd_number.py` take paths and a slug from outside, and `target_snapshot.py` runs `git -C <repo>` over an untrusted repository. Probe inside the scratch root only. (1) `allocate_prd_number.py`: slug traversal (`../x`, absolute paths, NUL, newline, uppercase, unicode), a symlinked `docs/dev/project-management/prds` or `discovery` directory pointing outside the repo, and symlinked repo arguments. (2) `target_snapshot.py`: a repo whose local config sets `core.fsmonitor`, `core.hooksPath` or `core.pager` to a scratch marker script (does merely snapshotting execute it?). Also hostile file and ref names (newlines, leading dashes, option-like names), a symlink inside the repo pointing outside (fingerprint must not follow it), an `<out.json>` path that resolves into the repo via symlink, and a crafted `before.json` (wrong `repo`, huge or malformed content, restore-command injection through ref names, since `restore` strings are built with `shlex.quote`). Marker scripts and canaries live only in the scratch root. Dispatch is gated at dispatch time by the `Authorization:` line or `--authorized`; this row does not depend on it. |

## Mocking strategy

No external service is called by the code, so there is nothing to mock for the probes above. Anything not reachable and not run:
- Running `/run-agoge` itself (needs a live Claude Code session and subagent dispatch): not mockable by a lane. Do not simulate it. Report any claim about full-pipeline behaviour as `unverified`.
- `dev/bin/release` (needs `../claude-plugins`, does a pull, tag and push): do not run. A lane may read it. Anything inferred about it is `unverified`, not `mocked`.
- Non-UTF-8 file names: this macOS filesystem rejects them, so the path is untestable on disk here. A lane may emulate it only with git objects built in a scratch repo (for example `git update-index --cacheinfo` with a raw byte path), and must report that as `mocked`, not `verified`. The CI Linux job is the real-disk evidence; cite it by run id, do not re-trigger CI.

## Authoring assignments

- Surface: the `skills/run-agoge/scripts/` helpers. Runner: pytest, via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q` (CI runs the same files with `python -m pytest -q -rs`). Place new tests as `skills/run-agoge/scripts/test_*.py` beside the existing suites so CI picks them up.
- Worth a regression test: any verified defect in `target_snapshot.py` (exit-code contract, fingerprinting, symlink handling) or `allocate_prd_number.py` (atomic claim, slug validation, directory scan).
- Doc-contract defects (prompt text, README, charter drift) belong in the existing hygiene suites (`test_scratch_contract.py`, `test_agoge_registry.py`, `test_run_integrity.py`).
- No specialist executes this. The master authors on a branch after the lanes report.

## Pins and vetoes

Authorization: this project is the operator's own or explicitly authorized.

## Freshness stamp

Last recon: 2026-11-08
Target HEAD: 1d8875307f74ec865518623ae67e73a21e5097ee
