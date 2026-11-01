---
prd: docs/dev/project-management/prds/wip/00003-fence-lane-scratch-work-out-of-target-v1.md
review: 2
date: 2026-11-01
head_sha: a42a87ec7f4be7a325c6465936e36d68cd46cd58
codex_thread_id: 01a198ec-60b4-7892-9013-11cc81a7676b
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 23d43754
  carl: 4529029b
---

# Review: 00003-fence-lane-scratch-work-out-of-target-v1

Diff range: `c37b74be13433a79079991dc524a82c5dce68a1c..a42a87ec7f4be7a325c6465936e36d68cd46cd58` (incremental: the cycle-1 rework only)

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/claude-agoge`) - review degraded, not invalid.

## Review Summary

Reviewed: 8 completed tasks (6 plan tasks plus the two cycle-1 `[D1]` rework tasks)
PRDs checked: 00003-fence-lane-scratch-work-out-of-target-v1.md

Incremental cycle: both cycle-1 findings (R1 the recon/profile conflict, R2 the any-non-zero-exit assertion) were verified resolved by Alice, and Bob, resuming his own cycle-1 codex thread, raised nothing.

### Agent Status

- Alice: ✅ Available (consensus lens, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens, codex, resumed thread 01a198ec)
- Carl: ✅ Available (gemini via copilot backend, model gemini-3.8-flash)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟡 | The `## Scratch contract` section deviates from appendix A2's verbatim text. It adds "except the one file your dispatch prompt names you to write (recon's strategy profile)" to the "Nothing goes inside the target" rule. The carve-out is sensible, because olivia must write the profile into the target. But it is an unspecified exception to a fence the PRD makes absolute, and no test pins it. It is in the section that is pasted verbatim into every lane, so non-recon lanes also read the exception text. | skills/run-agoge/references/finding-contract.md:81 | general | BLAKE |
| R2 | [1/4] | ⚪ | The stderr assertion depends on git's English message text; a localized git could fail it spuriously. Optional: set `LC_ALL=C` in the test env | skills/run-agoge/scripts/test_scratch_contract.py:139 | 8 | ALICE |
| R3 | [1/4] | ⚪ | `test_scratch_contract_mechanisms` checks the tokens against the whole of `finding-contract.md`, not the `## Scratch contract` section. `read-only` or `--git-dir` could be satisfied by text elsewhere in the file, which weakens the test. | skills/run-agoge/scripts/test_scratch_contract.py:109 | general | BLAKE |
| R4 | [1/4] | ⚪ | Test 2 adds an assertion the PRD did not ask for, `"not a git repository" in result.stderr`. It makes the test stricter and is harmless. The control test (test 3) ignores the exit code, which matches the spec. | skills/run-agoge/scripts/test_scratch_contract.py:139 | general | BLAKE |
| R5 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_scratch_contract_incident_preamble | skills/run-agoge/scripts/test_scratch_contract.py | general | mech-check |

Consolidation note: `consolidate_findings.py` merged nothing this cycle (no two reviewers named the same defect). R5 is the fail-first replay's `[MECH]` line, absorbed as its own row: no consolidated row names that test as its subject (R2/R4 cite line 139 inside it, but about the added stderr assertion, not the replay fact).

### Auto-dismissed (ledger)

- [BLAKE] ⚪ Recon item 7 is separated from item 6 by a blank line, so it renders as a new list. This follows the PRD's "followed by a blank line" instruction and is cosmetic. | File: skills/run-agoge/SKILL.md:337 — single-voice

## Alice

Both prior findings resolved, no regressions. She ran `test_scratch_contract.py` (5 passed) and did not re-run the other modules.

- Cycle-1 R1 resolved: `finding-contract.md:81-83` now carries the carve-out "except the one file your dispatch prompt names you to write (recon's strategy profile)", and the recon prompt names that profile path at `SKILL.md:319`, so the carve-out matches what Olivia is actually told to write. The "stop and report `unverified`" rule for a scratch root inside the target is intact, and the `mechanisms` test tokens are all still present.
- Cycle-1 R2 resolved: `test_scratch_contract.py:139` now also asserts `"not a git repository" in result.stderr`, so the test pins the ceiling mechanism rather than any non-zero exit.
- One ⚪ (R2 above): the stderr assertion depends on git's English message; she did not check whether `_env_for` inherits `LANG`.
- Settled decisions: none re-raised.

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

One 🟡 (R1) and three ⚪ (R3, R4, and the ledger-dismissed recon-list item). Blake located every spec item himself: A1 at `finding-contract.md:3-9`; the A2 section with `mktemp -d`, the `set -eu` preamble, `GIT_CEILING_DIRECTORIES`, `--git-dir`/`--work-tree`, per-command lane identity and the read-only target (his R1 is the one deviation); A3's four edits at `SKILL.md:27`, `:98`, `:158`, `:337`; A4 as the last `## Rules` bullet in all seven charters; A5 applied with no `agoge-<lane>/` left in `browser-playbook.md`; A6 at `CHANGELOG.md:10-18`. The new test file carries the five required tests, the incident test runs the extracted preamble plus A7 and snapshots refs/index/status, and the control test checks master, `v1.0.0` and `origin/master` move. He ran the four scratch/sidecar/registry/authorization modules: 123 passed, and did not re-run `dev/bin/release-checks` (he read this cycle's test gate instead). No extra dependencies, flags or code beyond the spec; the three out-of-scope items are absent.

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

Resumed his cycle-1 codex thread and found nothing outstanding.

[BOB] ✅ No issues found

FIX:
- (none)

VERIFY:
- (none)

KNOWN:
- (none)

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

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Backend copilot, model gemini-3.8-flash. All clear after reading the context and the incremental diff, running the scratch-contract tests, the full scripts suite and `dev/bin/release-checks`, and reading the two changed regions (`test_scratch_contract.py:125-150`, `finding-contract.md:70-105`).

[CARL] ✅ No issues found

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

## Verification-check queue

No VERIFY items named an exact command this cycle (Bob's VERIFY bucket is empty and Eve did not run), so no queue file was written. Cycle 1 wrote none either, so nothing was carried forward.

Tests-line provenance: `review-stage`'s `## Test gate` block was not a counts line (`counts unavailable (suite run this cycle, exit 0, no PASS/FAIL/SKIP/EXIT summary line)`), so `autopilot verify --gate-command dev/bin/release-checks --cycle 2` was run once in the foreground. It also failed to parse a summary line (exit 3, gate exit 0, `recorded: false`), so the counts below were read from its log `docs/dev/tmp/gate-a42a87e.log`, whose only summary line is `136 passed in 0.38s`. The suite passed; the parser, not the suite, is what did not cooperate.

Verdict: 5 findings
Tests: 136 passed, 0 failed, 0 skipped (suite run this cycle)
