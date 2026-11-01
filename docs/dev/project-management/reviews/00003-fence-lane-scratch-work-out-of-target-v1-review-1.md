---
prd: docs/dev/project-management/prds/wip/00003-fence-lane-scratch-work-out-of-target-v1.md
review: 1
date: 2026-11-01
head_sha: c37b74be13433a79079991dc524a82c5dce68a1c
codex_thread_id: 01a198ec-60b4-7892-9013-11cc81a7676b
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: bdb4557b
  carl: 12740f44
---

# Review: 00003-fence-lane-scratch-work-out-of-target-v1

Diff range: `6decbb8ad5771a105ee09c684610d2986f063c30..c37b74be13433a79079991dc524a82c5dce68a1c`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: repo not registered with gita) - review degraded, not invalid.

## Review Summary

Reviewed: 6 completed tasks
PRDs checked: 00003-fence-lane-scratch-work-out-of-target-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens, codex)
- Carl: ✅ Available (gemini via copilot backend, model gemini-3.8-flash)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟠 | The Scratch contract says "Everything you create goes under the path it prints ... Nothing goes inside the target", and SKILL.md pastes it verbatim into the recon prompt (item 7). Olivia's charter and the recon prompt require her to write the strategy profile into the target (docs/dev/project-management/meta/agoge-profile.md). The two instructions conflict, and a literal-minded recon lane could refuse to write the profile or write it to scratch. Add an explicit carve-out (for example "except the one file your dispatch prompt tells you to write") to the contract, or scope the sentence in the recon paste | skills/run-agoge/references/finding-contract.md:84 | 2 | ALICE, BOB |
| R2 | [2/4] | 🟡 | test_scratch_contract_incident_preamble asserts only `returncode != 0` plus an unchanged snapshot. The design says the ceiling makes git fail with exit 128. Any unrelated non-zero exit (a typo in the extracted block, an unset variable) would pass as long as nothing moved. Assert `== 128`, or assert that stderr contains git's "not a git repository" message, so the test pins the ceiling mechanism and not just any failure | skills/run-agoge/scripts/test_scratch_contract.py:877 | 1 | ALICE, BLAKE |
| R3 | [1/4] | 🟡 | test_scratch_contract_prompt slices run from the `### 3. Dispatch` heading to `## The recon prompt` (steps 3-9) and from `## The recon prompt` to the end of the file (including `## Notes`). The `"## Scratch contract"` check therefore does not pin dispatch part 4 or recon item 7 specifically. Any stray mention elsewhere in those wide slices satisfies it. Narrow the slices, for example to the "4. The `## Finding contract`" line and the "7. The `## Scratch contract`" list item | skills/run-agoge/scripts/test_scratch_contract.py:920 | 1 | ALICE |
| R4 | [2/4] | ⚪ | test_scratch_contract_incident_control passes against the pre-change code (the replay's [MECH] line). It is the PRD-mandated control proving the fixture reproduces the incident, so it is not a defect. Noted for the record | skills/run-agoge/scripts/test_scratch_contract.py:881 | 1 | ALICE, mech-check |
| R5 | [1/4] | ⚪ | The edits to SKILL.md (Dependencies line 27, step 2 line 98), browser-playbook.md:44 and CHANGELOG.md have no test pinning them. They are one-phrase doc edits verified by rg in the PRD, so the gap is acceptable. Line 98 now runs well past the file's wrap width ("scratch file outside the target *before* the"). Optionally re-wrap | skills/run-agoge/SKILL.md:98 | 4 | ALICE |
| R6 | [1/4] | ⚪ | The diff includes autopilot housekeeping that does not trace to the PRD: docs/dev/project-management/.gitignore, the duplicated dispatch-metrics.jsonl and loop-metrics.jsonl under both autopilot/ and autopilot/ledger/, assumptions.md and project-capsule.md. These are tooling artifacts, not product scope. Confirm they are meant to be committed | docs/dev/project-management/.gitignore | general | ALICE |
| R7 | [1/4] | ⚪ | The contract's "name the scratch repository in every git command that writes" does not say how to run `git init` itself. The `--git-dir` form does not obviously fit it. Optionally add an example such as `git init "$SCRATCH/<repo>"` under the preamble, so the `set -eu` plus ceiling failure mode is the documented one for init | skills/run-agoge/references/finding-contract.md:716 | 2 | ALICE |
| R8 | [1/4] | ⚪ | Recon item 7 sits after a blank line that separates it from item 6, so the numbered list is split in two. This follows A3 literally (insert before "She writes...", followed by a blank line) and is cosmetic. | skills/run-agoge/SKILL.md:337 | 5 | BLAKE |

Consolidation note: `consolidate_findings.py` merged R1 (Alice's `finding-contract.md:84` with Bob's `:79`) and R2 (Alice's `test_scratch_contract.py:877` with Blake's `:138`) after line-suffix stripping. The mechanical fail-first replay `[MECH]` line names the same test as R4 and was absorbed into that row.

## Alice

See the consolidated table (rows R1-R7). Alice ran the four test modules (123 tests at her run) and confirmed the A1-A6 text matches the PRD appendix, all seven charters carry the A4 bullet as the last `## Rules` bullet, no secrets/placeholders/debug statements remain, the longest function is 26 lines and the test file is 184 lines.

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

Two ⚪ observations (R2's shared finding and R8), both reported as non-defects. Blake located every spec item himself: A1 at `finding-contract.md:3-9`; A2 at `:66-111` before `## Report contract`, carrying the mktemp root, the `set -eu` plus `GIT_CEILING_DIRECTORIES` preamble, `--git-dir`/`--work-tree`, per-command lane identity and the read-only target; A3's four edits at `SKILL.md:27`, `:98`, `:158`, `:337`; A4 in all seven charters; A5 at `browser-playbook.md:44` with no `agoge-<lane>/` left anywhere in skills or agents; A6 as the `### Fixed` entry at `CHANGELOG.md:10-18`. He found the five specified tests present, the diff outside `docs/` touching exactly the 12 PRD-listed files, no scope creep, and the three out-of-scope items absent.

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

One 🟠 finding (R1): recon receives conflicting write instructions - the scratch contract requires every created file outside the target, while recon must write the profile inside it.

FIX:
- Recon's profile write conflicts with the scratch contract - skills/run-agoge/references/finding-contract.md:79 - Add a narrow exception for recon's designated profile output; keep probe artifacts outside the target and prohibit target git writes.

VERIFY:
- (none)

KNOWN:
- (none)

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

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Backend copilot, model gemini-3.8-flash. All clear after reading the context and diff and running the scratch-contract tests, the full scripts suite, `dev/bin/release-checks` and `git status`.

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

No VERIFY items named an exact command this cycle (Bob's VERIFY bucket is empty), so no queue file was written.

Verdict: 8 findings
Tests: 136 passed, 0 failed, 0 skipped (suite run this cycle)
