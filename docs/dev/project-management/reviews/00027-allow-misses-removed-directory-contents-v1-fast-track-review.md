# Fast-track review: 00027-allow-misses-removed-directory-contents-v1-c1

## Consolidated findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/5] | 🟡 | The tests only check the directory exemption for removals (ignored-removed, untracked-removed). `_allowed` now also guards the tracked, untracked-modified and touched checks (skills/run-agoge/scripts/target_snapshot.py:466, skills/run-agoge/scripts/target_snapshot.py:473, skills/run-agoge/scripts/target_snapshot.py:480), but no test allows a directory and changes a tracked file, edits an untracked file or creates a new file under it. If any of those three checks went back to exact matching (`path not in allow`, `- allow`), the full suite would still pass. Add one case to `test_allow_directory_exempts_its_removed_contents` or a sibling test: allow `d`, then modify a tracked `d/x`, edit an untracked `d/y` and create `d/z`. The case should expect exit 0 and `touched == []`. | skills/run-agoge/scripts/test_target_snapshot.py:317 | 1 | CONSENSUS, BLIND, CODEX |
| R2 | [3/5] | ⚪ | `_allowed` does not quite follow the spec at skills/run-agoge/scripts/target_snapshot.py:429. The spec says to strip one trailing `/` from both the path and each entry. The code uses `entry.rstrip("/")`, which removes every trailing slash, and never strips the path. In practice the result is the same, because a path `igndir/` from `ls-files --directory` still matches through `startswith(entry + "/")`. The only difference: `--allow igndir//` now matches, where the spec would not. | skills/run-agoge/scripts/target_snapshot.py:429 | 2 | CONSENSUS, BLIND, CODEX |
| R3 | [3/5] | ⚪ | The docstring edit was not re-wrapped. Line 16 runs to about 93 characters, while the rest of the paragraph wraps at about 78. | skills/run-agoge/scripts/target_snapshot.py:16 | 2 | CONSENSUS, BLIND, CODEX |
| R4 | [1/5] | 🟡 | File size exceeds the 800-line limit (809 lines) | skills/run-agoge/scripts/test_target_snapshot.py:809 | 1 | GEMINI |
| R5 | [1/5] | ⚪ | The empty removed ignored directory case (recorded as `igndir/`) is not directly covered by a dedicated assertion, though a direct call confirms the code handles it. | skills/run-agoge/scripts/test_target_snapshot.py:317 | 1 | BLIND |
| R6 | [1/5] | ⚪ | _allowed does not strip trailing slash from path as specified in task | skills/run-agoge/scripts/target_snapshot.py:428 | 2 | GEMINI |

No CRITICAL or HIGH findings; Verify, Rework and Delta were all skipped per the exit rule.

## Per-lane detail

- **Consensus (Alice, fallback subagent — workflow script was missing on disk)**: raised R1, R2, R3 at MEDIUM/LOW. R1 (consensus): fail; all other rubric rules pass.
- **Blind (Blake)**: raised R3 equivalent, R5, and a sibling-coverage note folded into R1/R5. All B1-B19 rubric lines pass.
- **Doubt (Eve)**: raised the same directory-coverage gap (R1) as FIX, plus one VERIFY (re-run `dev/bin/release-checks`, done below) and two KNOWN items (spec-wording deviation, informational `touched` edge case for a path later replaced by a directory). D1-D5 all pass.
- **Codex (Bob)**: codex-run.sh was blocked by its own PreToolUse fact-forcing gate and returned no usable review (all R/D lines `fail` by refusal, not by finding a defect). Retried as a `general-purpose` Task subagent reading the same rendered prompt via the Read tool (the sanctioned CLI-unavailable substitution, spending no retry budget). That substitute found no issues and could not execute tests (static sandbox), flagging R1 as not statically verifiable.
- **Gemini (Carl)**: ran gates and the full suite directly. Raised R4 (file-size limit) and R6 (slash-stripping deviation, same as R2). R13 marked fail because of the 809-line file size; R1-R12 pass.

## Verify

Skipped: no CRITICAL or HIGH findings were raised.

## Exit

**Outcome: committed.** Two commits land on `master`:
- `test(run-agoge): add tests for allow-directory exemption` (6f5d24d)
- `fix(run-agoge): target compare --allow exempts directory contents` (aca127f)

No findings survived to block the exit; the MEDIUM/LOW findings above do not rework or block per the fast-track exit rule and are recorded here for follow-up.

Gates:
- `pytest -k allow_directory_exempts` — exit 0 (1 passed)
- `pytest -k "allow_directory or allow_prefix"` — exit 0 (2 passed)

Batch suite (`suite: batch`): `dev/bin/release-checks` — 254 passed, 2 skipped (pre-existing, environment-only: filesystem rejects non-UTF-8 names), exit 0.

## Dispatch counts

```
fast-track:alice 1
fast-track:blake 1
fast-track:bob 2
fast-track:carl 1
fast-track:eve 1
fast-track:fanout 1
fast-track:ivan 1
fast-track:tess 1
```

(`fast-track:fanout` is the failed Workflow attempt, closed as `error`; `fast-track:alice` is the fallback consensus lane. `fast-track:bob` shows 2: the failed codex CLI attempt, closed `error`, and the successful general-purpose substitute.)

## Lanes that did not report as dispatched

- **fast-track:fanout** (review-fanout.workflow.js): the workflow script file was missing at `~/.claude/workflows/review-fanout.workflow.js` when first invoked via `Workflow({args: ...})` without `scriptPath`; the second attempt with the correct `scriptPath` also failed (`Workflow script file not found`). Fell back to the `autopilot:alice` subagent per the lane's own fallback rule.
- **fast-track:bob** (codex CLI): `codex-run.sh` ran but codex's own PreToolUse "Fact-Forcing Gate" hook blocked every `cat` it tried, so it returned no usable review. Substituted a `general-purpose` Task subagent reading the same prompt via `Read`, per the sanctioned "codex unavailable" substitution — this did not spend the one-retry budget.
