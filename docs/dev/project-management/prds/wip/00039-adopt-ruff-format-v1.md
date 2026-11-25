---
design: skip
default_model: sonnet
model_tier_rationale: tool-run reformat and exact text edits; sonnet and not haiku because the release gate changes
---
# Interactive sessions reformat the Python scripts, and the result is never committed

Source: follow-up of the PRD 00024 run, decided by the user on 2026-11-24 (option "adopt ruff in the repo"). Earlier record: review 1 of PRD 00024, Alice's last row (`docs/dev/project-management/reviews/00024-snapshot-slow-many-untracked-files-v1-review-1.md`).

## Problem

The repo has no formatter config. In an interactive session the loupe plugin runs `ruff check --fix` and `ruff format` on each edited Python file at the end of the turn, with the operator's own ruff settings (every lint rule, 88 columns). The scripts under `skills/run-agoge/scripts` were never formatted that way, so each touched file is rewritten in full. The rewrite stays uncommitted. Reviewers then report differences that are not in the commit (two lanes did in review 1 of PRD 00024), and one rewrite changed code (`functools.lru_cache(maxsize=None)` to `functools.cache`). The unattended loop is not affected, because it turns the autofix off.

Users hit: every maintainer or agent that edits a script in an interactive session.

## Solution

Make the committed tree equal to the formatter's output and keep it so. Add a `ruff.toml` at the repo root with ruff's default lint rule set, so the autofix stops applying the operator's wider rules here. Format the scripts once, in a commit that holds only formatter output. Check the format and the lint in `dev/bin/release-checks` and in CI, so a later commit cannot drift. Add an `AGENTS.md` that tells an implementor to format before a commit; the unattended lanes give that file to the implementor.

`test_agoge_authorization_gate.py` imports the pytest fixture `registry` from `test_agoge_registry.py` and uses it as a test argument. Ruff reports that as F401 and F811, and the F401 fix deletes the import and breaks the tests. The config ignores the two rules for that one file.

This PRD runs after every lower-numbered PRD in the backlog: those PRDs cite literal source lines, and a reformat before them can break their premises.

## Requirements

### Must have
- `uvx ruff format --check skills/run-agoge/scripts` exits 0.
- `uvx ruff check skills/run-agoge/scripts` exits 0, and `test_agoge_authorization_gate.py` still imports `registry`.
- The format commit changes no behaviour: the full suite passes after it.
- `dev/bin/release-checks` and the CI workflow fail on an unformatted script.
- No `CHANGELOG.md` entry: the commits are `style`, `build`, `ci` and `docs`.

### Nice to have
- None.

## Implementation

### Module: formatter config and gate
- **Location**: `ruff.toml`, `AGENTS.md`, `dev/bin/release-checks`, `.github/workflows/test.yml`
- **Responsibility**: define the format and the lint rules, check them where releases and pushes are checked, and tell implementors the command.
- **Exports**: none
- New symbols: none
- **Risk**: ruff is not pinned. A ruff release that changes the format makes the gate fail until someone formats again; set `required-version` in `ruff.toml` when that happens.

### Module: formatted scripts
- **Location**: `skills/run-agoge/scripts/allocate_prd_number.py`, `skills/run-agoge/scripts/snapshot_fixtures.py`, `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_agoge_authorization_gate.py`, `skills/run-agoge/scripts/test_agoge_registry.py`, `skills/run-agoge/scripts/test_allocate_prd_number.py`, `skills/run-agoge/scripts/test_prd_emission_contract.py`, `skills/run-agoge/scripts/test_run_integrity.py`, `skills/run-agoge/scripts/test_scratch_contract.py`, `skills/run-agoge/scripts/test_sidecar_contract.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot_programs.py`, `skills/run-agoge/scripts/test_target_snapshot_state.py`
- **Responsibility**: hold the formatter's output and nothing else from this PRD.
- **Exports**: none
- **Risk**: one large diff; `git blame` then points at the format commit for most lines.

### Dependencies
- formatter config and gate: No dependencies (foundation)
- formatted scripts: Depends on [formatter config and gate] for `ruff.toml`

## Tasks

### Phase 0: Format
- [ ] Create `ruff.toml` at the repo root with exactly these lines: a comment line `# Formatter defaults and ruff's default lint rules. Ruff is not pinned: set required-version if a release reflows the tree.`, then `[lint]`, then `select = ["E4", "E7", "E9", "F"]`, an empty line, `[lint.per-file-ignores]`, a comment line `# registry is a pytest fixture, imported to be used as a test argument.`, then `"skills/run-agoge/scripts/test_agoge_authorization_gate.py" = ["F401", "F811"]`. Premise: `rg --files -g ruff.toml -g .ruff.toml -g pyproject.toml .` prints nothing; if it prints a file, stop and report - Acceptance: `uvx ruff check skills/run-agoge/scripts` exits 0, and `rg -F "from test_agoge_registry import" skills/run-agoge/scripts/test_agoge_authorization_gate.py` still shows `registry` on that line.
- [ ] Run `uvx ruff format skills/run-agoge/scripts` and commit the result alone as `style(run-agoge): format scripts with ruff`. Premise: `git status --short skills/run-agoge/scripts` prints nothing before the run; if it prints a path, stop and report. If `rg --files -g "*.py" skills/run-agoge/scripts` lists a file that the Location above does not name, format it too and name it in the report (depends on: previous task) - Acceptance: `uvx ruff format --check skills/run-agoge/scripts` exits 0, and `uvx ruff check skills/run-agoge/scripts` exits 0.

### Phase 1: Gate
- [ ] In `dev/bin/release-checks`, insert two lines directly above the `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q -rs` line: `uvx ruff format --check skills/run-agoge/scripts` and `uvx ruff check skills/run-agoge/scripts` (depends on: Phase 0) - Acceptance: `rg -c "^uvx ruff " dev/bin/release-checks` prints 2.
- [ ] In `.github/workflows/test.yml`, change `- run: python -m pip install pytest` to `- run: python -m pip install pytest ruff`, and insert two steps above the pytest step, each with `working-directory: skills/run-agoge/scripts`: `- run: ruff format --check .` and `- run: ruff check .` (depends on: Phase 0) - Acceptance: `rg -F "pip install pytest ruff" .github/workflows/test.yml` hits, `rg -F "ruff format --check ." .github/workflows/test.yml` hits, and `rg -F -- "- run: ruff check ." .github/workflows/test.yml` hits.
- [ ] Create `AGENTS.md` at the repo root with a `# agoge` title, a `## Commands` section and two bullets: ``- All checks: `dev/bin/release-checks` `` and ``- Format before each commit that touches Python: `uvx ruff format skills/run-agoge/scripts`, then `uvx ruff check --fix skills/run-agoge/scripts`. `dev/bin/release-checks` and CI fail on an unformatted file.`` Premise: `rg --files -g AGENTS.md -g CLAUDE.md --max-depth 1 .` prints nothing; if it prints a file, add the two bullets to that file's commands section and do not create a second file - Acceptance: `rg -F "uvx ruff format skills/run-agoge/scripts" AGENTS.md` hits.

## Success Criteria

- `uvx ruff format --check skills/run-agoge/scripts` and `uvx ruff check skills/run-agoge/scripts` exit 0; the full suite passes under `dev/bin/release-checks`, which now runs both.

## Waiver

`dev/bin/release-checks` runs `uv run --with ruff ruff format --check` and `uv run --with ruff ruff check` instead of the `uvx ruff ...` form the Phase 1 task literally specified (commit `a4eeb1f`, "fix(release-checks): use sandbox-safe uv run invocation for ruff"). `uvx` fails under this host's sandbox profile; `uv run --with ruff ruff ...` is equivalent and sandbox-safe. The Phase 1 acceptance check `rg -c "^uvx ruff " dev/bin/release-checks` now prints 0 by design — the deviation is accepted, not a regression.
