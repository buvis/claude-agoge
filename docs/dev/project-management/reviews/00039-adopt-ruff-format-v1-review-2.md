---
prd: docs/dev/project-management/prds/wip/00039-adopt-ruff-format-v1.md
review: 2
date: 2026-11-25
head_sha: 0c7007600ffbbf45f087fa7041a66cf93ed75a48
codex_thread_id: 01a21121-5f06-7df2-86b9-6f01a2ece8fa
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 379ad886
  carl: 4eba70e9
---

# Review: 00039-adopt-ruff-format-v1 (cycle 2, incremental)

Diff range: `59a4c690cbef76cc70b3f026a31f8fbb0d0a2b41..0c7007600ffbbf45f087fa7041a66cf93ed75a48`

codex_rung_guard: not fired

pack: ok

Notes on this cycle's inputs:

- Incremental cycle: the diff is scoped to the cycle-1 rework. The only code
  change is `dev/bin/release-checks:12-13` (commit a4eeb1f); everything else in
  the range is autopilot state and review bookkeeping.
- `review-stage` ran the project gate `dev/bin/release-checks` this cycle: exit
  0, `All checks passed!`, `299 passed, 2 skipped` read from
  `docs/dev/tmp/gate-00039c2.log`. The CLI reported `counts unavailable` because
  the gate wraps pytest and emits no PASS/FAIL summary line of its own.
- The fail-first replay produced no findings: no test file changed in this range.
- The tautological-test scan flagged nothing.
- Bob resumed his cycle-1 codex thread (`--resume-thread`).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | dev/bin/release-checks:12 no longer matches the PRD's literal `uvx ruff` contract or its `rg -c "^uvx ruff "` acceptance check (now prints 0); the rework is justified but the PRD or a waiver should record it | dev/bin/release-checks:12 | 3 | ALICE, BLAKE, BOB |
| R2 | [1/4] | 🟡 | AGENTS.md:6 still recommends sandbox-failing `uvx ruff` commands although the settled R10 discard assumed the R3 fix would update it; the settled reason no longer holds | AGENTS.md:6 | 5 | ALICE |
| R3 | [1/4] | 🟡 | The ledger says the sandbox fix also updates `AGENTS.md`. The guide still directs agents to use `uvx` for both pre-commit Ruff commands, so that workflow still hits the tool-directory failure the rework addressed. | AGENTS.md:6 | 6 | BOB |
| R4 | [1/4] | ⚪ | Ruff is unpinned, as the PRD accepts. The CI job runs `pip install ruff` (latest) and `release-checks` fetches latest through uv. A ruff release that reflows the tree turns the gate red with no code change. Residual risk the PRD already names. | .github/workflows/test.yml:22 | general | BLAKE |
| R5 | [1/4] | ⚪ | `skills/run-agoge/scripts/conftest.py` is not in the PRD's file list. The task required formatting it and naming it in the report. It is already formatted and absent from the format commit's diff, so no violation, only a reporting obligation. | skills/run-agoge/scripts/conftest.py | Phase 0 | BLAKE |
| R6 | [1/4] | ⚪ | The review record changes the proposed format probe from valid, unformatted Python to a syntax error. A syntax error checks parser rejection and gives no evidence that the gate rejects valid formatting drift. | docs/dev/project-management/reviews/00039-adopt-ruff-format-v1-review-1.md:132 | general | BOB |
| R7 | [1/4] | ⚪ | Two dispatch IDs each have two successful completion records with different elapsed times. The log leaves the completion time ambiguous for both dispatches. | docs/dev/project-management/autopilot/dispatch-metrics.jsonl:873 | general | BOB |

No 🔴 CRITICAL and no 🟠 HIGH finding. Cycle 1's only HIGH (R3, the sandbox gate
failure) is resolved: three reviewers independently ran the reworked gate and it
passes.

### Auto-dismissed (ledger)

- [BLAKE] ⚪ `AGENTS.md` tells implementors to run `uvx ruff ...`, as the PRD mandates. In this sandbox `uvx` fails with "Could not create temporary file ... uv/tools", the same failure that made `release-checks` deviate. The documented command and the gate command now differ, so an agent in a similar sandbox following `AGENTS.md` will fail. | File: AGENTS.md:6 — single-voice; the sandbox-compatible command form is fixed under the HIGH finding R3, which updates AGENTS.md with it

Note: Alice and Bob re-raised the same substance as implementation-aware
reviewers (R2, R3), so the dismissal removed Blake's copy only, not the issue.

Decision-gate consolidation note: R2 (ALICE) and R3 (BOB) are one defect at the
same `AGENTS.md:6` line, which `consolidate_findings.py` left as two rows
because the wordings share no file suffix after stripping. The gate treats them
as one two-voice finding (ALICE, BOB), not two single-voice rows; Blake's
ledger-dismissed copy is a third independent sighting of the same line.

## Alice

Consensus lens, implementation-aware. Verified every cycle-1 finding and raised
two new ones (R1, R2 above).

- R3 (cycle 1's HIGH) is resolved: `dev/bin/release-checks:12-13` runs
  `uv run --with ruff ruff format --check skills/run-agoge/scripts` and
  `uv run --with ruff ruff check skills/run-agoge/scripts`, both above the
  pytest line. She ran both: `14 files already formatted`, `All checks passed!`.
- The committed script omits `--no-project`, which the cycle-1 record mentioned.
  The repo root has no `pyproject.toml`, so it makes no difference here.
- R1, R2, R4-R9 of cycle 1: settled or discarded, not re-raised.
- Regression check: the only code change since cycle 1 is those two lines; the
  pytest line is unchanged; no test function was touched.

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
R12: pass
R13: pass

## Blake

Blind lens, PRD-only. Four findings; one (AGENTS.md) was ledger-dismissed, the
others are R1, R4 and R5 above.

What he verified:

- `ruff.toml` matches the spec text line for line.
- Format commit 7567d3e touches 10 files, all in the spec's list, line-wrapping
  only; three listed files were already formatted.
- The format commit sits before the gate commits and is separate from them.
- `.github/workflows/test.yml` installs `pytest ruff` and runs both ruff steps
  above pytest with `working-directory: skills/run-agoge/scripts`.
- Commit types are `build`, `style` and `docs`, with no CHANGELOG entry.

B15 is his only failing rule: the gate script's literal command text deviates
from the PRD (the substance of R1).

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
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens (D1-D5) plus de-slop, codex, static-only, resumed cycle-1 thread.
Four findings (R1, R3, R6, R7 above).

R1: pass
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

FIX:

- Release command drift — dev/bin/release-checks:12 — Add `--no-project` to both Ruff invocations as specified by Task 6. Update Task 3's acceptance check to match the reworked commands.
- Incomplete sandbox fix — AGENTS.md:6 — Use the same `uv run --no-project --with ruff ruff` command form for both pre-commit commands.
- Inaccurate review record — docs/dev/project-management/reviews/00039-adopt-ruff-format-v1-review-1.md:132 — Restore the original valid but unformatted `review_ruff_probe=[1,2]` probe in the record of the prior review.

VERIFY:

- (none)

KNOWN:

- Duplicate dispatch completions — docs/dev/project-management/autopilot/dispatch-metrics.jsonl:873 and its ledger copy contain the same duplicates. Choosing which event is authoritative belongs to dispatch telemetry, outside the Ruff rework.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini (copilot backend), frontend & design specialist, generalist here. No
issues found.

He reproduced the old failure himself (`uvx ruff format --check` exit 2,
`Operation not permitted` on `~/.local/share/uv/tools`), ran the reworked
`dev/bin/release-checks` to completion, and inspected commit a4eeb1f.

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
R12: pass
R13: pass

Verdict: 7 findings
Tests: 299 passed, 2 skipped (suite run this cycle)
