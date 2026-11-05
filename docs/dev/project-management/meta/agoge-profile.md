# Agoge profile: claude-agoge

## Surfaces

All commands run from the repo root. The product is a Claude Code plugin: markdown personas and prompts plus two stdlib-only Python helper scripts and their pytest suites. There is no application server, UI, or database.

**Test suite (verified, runs green).**
- Command: `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q`
- Result at HEAD 035f5d2: `167 passed, 1 skipped in ~11s`.
- The one skip is `test_target_snapshot.py:617`: the macOS filesystem rejects non-UTF-8 file names (`Errno 92`). The non-UTF-8 path round-trip is therefore not exercised on this host.
- Suites in `skills/run-agoge/scripts/`: `test_agoge_authorization_gate.py`, `test_agoge_registry.py`, `test_allocate_prd_number.py`, `test_run_integrity.py`, `test_scratch_contract.py`, `test_sidecar_contract.py`, `test_target_snapshot.py`.
- The same command is the release gate (`dev/bin/release-checks`).
- Side effect: a plain run writes `.pytest_cache/` and `__pycache__/` into the checkout. Both are gitignored. To avoid it, use `PYTHONDONTWRITEBYTECODE=1` and add `-p no:cacheprovider` (verified: same 167 passed, 1 skipped).

**CLI entry points (both verified).**
- `python3 -I skills/run-agoge/scripts/target_snapshot.py {snapshot <repo> <out.json> | compare <repo> <before.json> [--allow <path>]...}`.
  - Exit 0 = unchanged, 1 = changed, 2 = cannot run (one `target_snapshot: <reason>` line on stderr).
  - `<repo>` must be the top level of a git work tree.
  - `<out.json>` must lie outside `<repo>`.
  - Probed against a scratch repo: `snapshot`, then `compare` gave exit 0 and `"unchanged"`. After editing a tracked file, `compare` gave exit 1 with a `tracked` violation.
  - It shells out to `git --no-optional-locks -C <repo> ...`, so it depends on the system `git`.
- `python3 -I skills/run-agoge/scripts/allocate_prd_number.py <repo> <slug>`.
  - Bare invocation prints usage and exits 2.
  - Probed against a scratch repo: it created `docs/dev/project-management/prds/backlog/00001-my-slug-v1.md` (empty file, atomic `O_CREAT|O_EXCL`) and printed the path.
  - It WRITES into `<repo>`. Point it only at a scratch repo, never the target.
- `dev/bin/release` and `dev/bin/release-checks`. `release` needs the sibling `../claude-plugins` repo and does `git pull`, commits and tags. Do NOT run it. `release-checks` is just the pytest command above.

**Prompt and contract surface (read, not executable).**
- `skills/run-agoge/SKILL.md` (master orchestration).
- `skills/run-agoge/references/*.md` (finding contract with scratch contract, and the browser, data, perf, security, authoring and prd-emission playbooks).
- `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md`.
- These are exercised only through the pytest hygiene suites, which pin their text. Running the skill itself needs a Claude Code session, which no lane can start.

**Dev server / built server:** none. No `package.json`, `pyproject.toml`, `Dockerfile`, and no listening port. `.github/workflows/test.yml` (added in e95d42f) runs the pytest suite on ubuntu and macOS; on Linux it ran 168 passed, 0 skipped, so the non-UTF-8 round trip passes there.

**Browser:** no browser surface. The repo has no web UI, no HTML, and no Node project. Chromium builds exist in the host's `~/Library/Caches/ms-playwright`, but nothing in the product has a page to drive.

**Database:** none. No schema, fixtures or seed path. The only state is git repositories and files.

**External services:** none called by the code. The scripts need only the local `git` binary and Python 3 (system 3.14.6 via mise; `uv` is on PATH). `dev/bin/release` reaches `buvis/claude-plugins` over git remote, and the README names `buvis/agoge-gym` as the eval repo. Neither is reachable or relevant to a lane.

**Notes.**
- Working tree was clean at recon (`git status --short` empty).
- Git tags: v0.1.0 through v0.3.0. `plugin.json` and `marketplace.json` both say 0.3.0. CHANGELOG has `[Unreleased]` with one Fixed entry (non-UTF-8 handling in `target_snapshot`) after `[0.3.0] - 2026-11-02`.

## Per-specialist strategy

| Specialist | Verdict | Tactics / reason |
|---|---|---|
| walter | armed | Run the two helper CLIs as a user would, end to end, in a scratch root only. (1) Build a scratch git repo, then `target_snapshot.py snapshot`, mutate it (edit tracked file, add/remove untracked file, commit, move a ref, add a worktree, change local config), then `compare` and check the exit code and violation kinds. Also try `--allow`, a missing or foreign snapshot file, an `<out.json>` inside the repo, a repo subdirectory, a non-repo, and an empty repo with no commit. (2) `allocate_prd_number.py` against scratch repos: empty repo, existing numbered PRDs in each lifecycle dir, concurrent callers (parallel runs must yield distinct numbers), bad slugs. (3) Run the full pytest command and report the count. |
| heidi | armed | No database. Surface is the git contract: `target_snapshot.py` against real git state in scratch repos. Cases: symlinked and external-symlink ancestors, submodules, detached HEAD, renamed or copied paths in the index, files with spaces and trailing spaces, unreadable files (expects exit 2, one line), packed and annotated-tag refs, linked worktrees, local config changes. Also probe the path contract between `SKILL.md` prompts and the scripts (arguments the master passes versus what the scripts accept). All repos go under the scratch root; use `--git-dir`/`--work-tree` per the scratch contract. |
| judy | unarmed | No UX surface: no web UI, no HTML or Node project (so no browser target), and the only interfaces are two argparse CLIs whose usage and error text walter already exercises. |
| wendy | armed | Release truth, with files to check. (1) `CHANGELOG.md` `[Unreleased]` entry versus actual behaviour: run `target_snapshot.py` on a repo whose paths cannot be decoded as strict UTF-8 where the filesystem allows it (macOS rejects such names, so use a git ref or the test's own approach), and confirm exit 2 with one diagnostic line on an unreadable file. (2) Version agreement: `.claude-plugin/plugin.json` 0.3.0, `.claude-plugin/marketplace.json` 0.3.0, `CHANGELOG.md` top released version 0.3.0, git tag v0.3.0 (`git tag --list`, `git log`). (3) README claims versus `SKILL.md` and scripts: the profile path, the `--authorized <source>` flow, "Recon writes `Authorization: not asserted`", the seven-specialist roster against `agents/`, and the Development test command. (4) Every command or path quoted in README and CHANGELOG resolves. |
| peggy | armed | One real cost surface: `target_snapshot.py` runs on the master's target at least three times per run (snapshot, then two compares), on arbitrary repos. Time `snapshot` and `compare` on scratch repos of growing size (for example 1k, 10k, 50k tracked files, plus many untracked files and many dirty tracked files, since each dirty path is hashed). Report wall time and scaling, not just one number. Also time `allocate_prd_number.py` with several thousand existing PRD files, and time the full pytest suite (baseline about 11s). |
| trudy | armed | Decided on surface alone. Hostile-input surface exists. `target_snapshot.py` and `allocate_prd_number.py` take paths and a slug from outside, and `target_snapshot.py` runs `git -C <repo>` over an untrusted repository. Probe inside the scratch root only. (1) `allocate_prd_number.py`: slug traversal (`../x`, absolute paths, NUL, newline, uppercase, unicode), a symlinked `docs/dev/project-management/prds` or `discovery` directory pointing outside the repo, and symlinked repo arguments. (2) `target_snapshot.py`: a repo whose local config sets `core.fsmonitor`, `core.hooksPath` or `core.pager` to a scratch marker script (does merely snapshotting execute it?). Also hostile file and ref names (newlines, leading dashes, option-like names), a symlink inside the repo pointing outside (fingerprint must not follow it), an `<out.json>` path that resolves into the repo via symlink, and a crafted `before.json` (wrong `repo`, huge or malformed content, restore-command injection through ref names, since `restore` strings are built with `shlex.quote`). Marker scripts and canaries live only in the scratch root. Dispatch is gated at dispatch time by the `Authorization:` line or `--authorized`; this row does not depend on it. |

## Mocking strategy

No external service is called by the code, so there is nothing to mock for the probes above. Anything not reachable and not run:
- Running `/run-agoge` itself (needs a live Claude Code session and subagent dispatch): not mockable by a lane. Do not simulate it. Report any claim about full-pipeline behaviour as `unverified`.
- `dev/bin/release` (needs `../claude-plugins`, does a pull, tag and push): do not run. A lane may read it. Anything inferred about it is `unverified`, not `mocked`.
- Non-UTF-8 file names: this macOS filesystem rejects them, so the path is untestable on disk here. A lane may emulate it only with git objects built in a scratch repo (for example `git update-index --cacheinfo` with a raw byte path), and must report that as `mocked`, not `verified`.

## Authoring assignments

- Surface: the `skills/run-agoge/scripts/` helpers. Runner: pytest, via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q`. Place new tests as `skills/run-agoge/scripts/test_*.py` beside the existing suites.
- Worth a regression test: any verified defect in `target_snapshot.py` (exit-code contract, fingerprinting, symlink handling) or `allocate_prd_number.py` (atomic claim, slug validation, directory scan).
- Doc-contract defects (prompt text, README, charter drift) belong in the existing hygiene suites (`test_scratch_contract.py`, `test_agoge_registry.py`, `test_run_integrity.py`).
- No specialist executes this. The master authors on a branch after the lanes report.

## Pins and vetoes

Authorization: this project is the operator's own or explicitly authorized.

## Freshness stamp

Last recon: 2026-11-03
Target HEAD: 035f5d2a4888078ced5ab28f1c37c0fc5d4872fe
