---
prd: docs/dev/project-management/prds/wip/00039-adopt-ruff-format-v1.md
review: 1
date: 2026-11-25
head_sha: 59a4c690cbef76cc70b3f026a31f8fbb0d0a2b41
codex_thread_id: 01a21121-5f06-7df2-86b9-6f01a2ece8fa
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: b609bf28
  carl: 1986fed0
---

# Review: 00039-adopt-ruff-format-v1

Diff range: `cbabd0734237120a088cfda6c460bf6cc3403851..59a4c690cbef76cc70b3f026a31f8fbb0d0a2b41`

codex_rung_guard: not fired

pack: ok

Notes on this cycle's inputs:

- The project gate `dev/bin/release-checks` cannot run under this host's agent
  sandbox: `uvx ruff` needs to write `~/.local/share/uv/tools`, which the
  seatbelt profile denies (`Operation not permitted (os error 1)`). Its three
  steps were run with the mise-installed ruff instead and all passed. Carl
  raised that as finding R3.
- The fail-first replay was skipped: the replay runner resolved the test paths
  against `skills/run-agoge/scripts` and exited 4 (`file or directory not
  found`). No mechanical tautology finding was produced either (137 test
  functions checked, none flagged).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | ⚪ | Pre-existing over-50-line functions that the PRD forbids touching beyond formatting: take_snapshot (72 lines), compare (65), main (61), claim (52), test_env_identity_beats_exported_author (117) and others. No new function crosses the limit, but the reformat lengthened some of them. | skills/run-agoge/scripts/target_snapshot.py:402 | 2 | ALICE, BOB, CARL |
| R2 | [2/4] | ⚪ | Pre-existing file-size debt (deferred as 00041) is now larger after reformatting: test_target_snapshot.py is 1126 lines and test_target_snapshot_state.py is 1038, both over the 800-line cap. The 800-line cap is not met, but this PRD (format only, "no manual edits") cannot fix it. | skills/run-agoge/scripts/test_target_snapshot.py:1 | 2 | ALICE, CARL |
| R3 | [1/4] | 🟠 | dev/bin/release-checks fails with exit 2 under agent sandbox because uvx requires writable ~/.local/share/uv/tools | dev/bin/release-checks:12 | 3 | CARL |
| R4 | [1/4] | 🟡 | The project capsule still tells maintainers to discard formatter changes with `git checkout --`. That can discard Python edits along with the formatting and conflicts with the new commit instructions. | docs/dev/project-management/meta/project-capsule.md:51 | 5 | BOB |
| R5 | [1/4] | 🟡 | The supplied checks cover clean scripts. They do not exercise the new requirement that a format failure stops the release and CI gates before pytest. | dev/bin/release-checks:12 | general | BOB |
| R6 | [1/4] | ⚪ | Ruff is unpinned in dev/bin/release-checks (`uvx ruff`) and in CI (`pip install pytest ruff`), so a ruff release that reflows the tree turns both gates red. The PRD accepts this risk and the comment in ruff.toml names the remedy (`required-version`). Recorded only. | ruff.toml:1 | 3 | ALICE |
| R7 | [1/4] | ⚪ | The aggregate diff and task table do not establish that the required style commit contains only formatter output. | N/A | 2 | BOB |
| R8 | [1/4] | ⚪ | The existing snapshot loader passes ref values directly to `re.fullmatch`. A non-string value reaches the generic exception handler instead of the malformed-ref diagnostic. | skills/run-agoge/scripts/target_snapshot.py:639 | 2 | BOB |
| R9 | [1/4] | ⚪ | Two formatted test files still exceed 800 lines. Both already exceeded the limit before formatting. | skills/run-agoge/scripts/test_target_snapshot.py:1103 | 2 | BOB |
| R10 | [1/4] | ⚪ | AGENTS.md recommends uvx commands which fail with Operation not permitted under agent seatbelt sandbox | AGENTS.md:6 | 5 | CARL |

Consolidation note: `consolidate_findings.py` merged R2's two citations after
suffix stripping (`test_target_snapshot.py:1` ~ `:1126`).

## Alice

Consensus lens, implementation-aware. Three Low findings (R1, R2, R6 above).

Checks she ran:

- Formatter-only commit: `ast.dump` output is identical at base `cbabd07` and at
  HEAD for all 10 changed Python files, so commit 7567d3e changes no behaviour.
  No file in the PRD's Location list was left unformatted.
- Config and gate: `ruff.toml`, the `release-checks` lines, the `test.yml` steps
  and `AGENTS.md` match the PRD contract text byte for byte. The two ruff lines
  sit directly above the pytest line; `registry` is still imported in
  `test_agoge_authorization_gate.py`.
- Lint: `ruff check .` over the whole repo printed "All checks passed!", which
  covers the per-file ignore.

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail

## Blake

Blind lens, PRD-only. `[BLAKE] ✅ No issues found` — every acceptance criterion
of the spec verified independently.

Checks he ran: `ruff format --check` (14 files already formatted, the extra file
being `conftest.py`, already clean), `ruff check` clean, the `ruff.toml` seven
lines, `functools.lru_cache(maxsize=None)` still present at
`target_snapshot.py:290`, the `release-checks` and `test.yml` gate ordering, the
`AGENTS.md` shape with no duplicate config at the repo root, the five separate
ordered commits with no `CHANGELOG.md` touch, and narrow pytest runs (23 passed;
95 passed, 1 skipped). He did not rerun the full suite and did not confirm his
guess about the gate's exit 2.

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens (D1-D5) plus de-slop, codex, static-only. Six findings (R4, R5, R7,
R8, R9 above).

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail

FIX:
- Stale formatter instruction — `docs/dev/project-management/meta/project-capsule.md:51` — remove the old discard instruction and point maintainers to `AGENTS.md`.

VERIFY:
- Gate rejection path — in a disposable checkout, append a syntax error to `skills/run-agoge/scripts/conftest.py`, run `dev/bin/release-checks` and the CI test job, and confirm both stop at the format check with pytest unstarted. **not queued: command shape** (multi-step procedure, no single runnable command).
- Style commit isolation — locate `style(run-agoge): format scripts with ruff`, confirm its parent contains `ruff.toml`, re-apply ruff formatting to the parent's scripts and compare the patch byte for byte. **not queued: command shape** (multi-step procedure, no single runnable command).

KNOWN:
- Non-string ref diagnostic — `skills/run-agoge/scripts/target_snapshot.py:639` already behaves this way; changing snapshot validation exceeds the formatter-only scope.
- Function size — splitting `take_snapshot`, `compare` or the other oversized functions requires a separate refactor.
- File size — splitting `test_target_snapshot.py` and `test_target_snapshot_state.py` requires test reorganization beyond this PRD's scope.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini, frontend & design specialist, generalist here. Four findings (R3, R10,
plus the function- and file-size rows folded into R1 and R2).

He reproduced the gate failure himself (`dev/bin/release-checks` exit 2,
`uvx` cannot create its temporary file), confirmed AST identity across the
format commit, verified the CI workflow and the ruff settings resolution from
the subdirectory, and found that `uv run --with ruff ruff format --check
skills/run-agoge/scripts` works where `uvx ruff` does not.

R1: pass
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail

Verdict: 10 findings
Tests: 299 passed, 2 skipped (suite run this cycle)
