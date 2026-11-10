---
prd: docs/dev/project-management/prds/wip/00010-snapshot-runs-repo-configured-programs-v1.md
review: 2
date: 2026-11-10
head_sha: ad84d864f53d0543b9440b82c35034eed3d167ad
codex_thread_id: 01a1c2dc-3a6d-7501-b699-2f6730e597ef
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 10ac8ebf
  carl: 17101e9b
---

# Review cycle 2 - 00010-snapshot-runs-repo-configured-programs-v1

Diff range: `7c872f23d05ba8311eca8591067191a045fa9ccb..ad84d864f53d0543b9440b82c35034eed3d167ad`
Scope: incremental review (cycle 2), rework commits since cycle 1

codex_rung_guard: not fired

Pack: ok
Fail-first replay: 0 touched tests ran; 3 test files could not be collected at base (their tests fail there), so the replay lens is effectively absent again this cycle. The tautological-shape lens ran.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | `TEST_ENV` inherits the caller's `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_*` / `GIT_CONFIG_VALUE_*` command-scope pairs from `os.environ`, so an ambient `core.fsmonitor` override beats the repo-local one the fixture sets. `test_snapshot_does_not_run_fsmonitor` and `test_snapshot_does_not_run_submodule_only_fsmonitor` then fail on their positive control. Strip the command-scope family (and `GIT_CONFIG`) from `TEST_ENV`. | skills/run-agoge/scripts/snapshot_fixtures.py:11 | 6 | CARL, gate |
| R2 | [1/4] | 🟡 | `test_every_gitdir_entry_is_checked_or_listed` hedges with `or`: either outcome satisfies it. Pre-existing, untouched by this PRD's diff (it moved file in the cycle-1 split). | skills/run-agoge/scripts/test_target_snapshot_state.py:393 | general | mech-check |
| R3 | [1/4] | ⚪ | `test_snapshot_does_not_run_clean_filter_hidden_by_inherited_git_config` builds two untouched-asserters over the same repo when the source is `local` (`target` and `declaring` are the same repo), so the second adds nothing for that case. Harmless, cosmetic only | skills/run-agoge/scripts/test_target_snapshot_programs.py:534 | 5 | ALICE |
| R4 | [1/4] | ⚪ | The rewrite of the assumptions ledger replaced the recorded assumptions for tasks 1 to 3 and the cross-task corrections with the cycle-1 rework notes. That durable history is gone from the working file, though it stays in git history | docs/dev/project-management/meta/assumptions.md:1 | general | ALICE |
| R5 | [1/4] | ⚪ | Tests and fixtures sit in new files `skills/run-agoge/scripts/test_target_snapshot_programs.py` and `skills/run-agoge/scripts/snapshot_fixtures.py`. The spec's Location lists only `test_target_snapshot.py`. Behaviour is unaffected, and `-k` selection still works across files. | skills/run-agoge/scripts/test_target_snapshot_programs.py | 1-2 | BLAKE |
| R6 | [1/4] | ⚪ | `CHANGELOG.md:29` adds a second Fixed entry for the inherited `GIT_CONFIG` fix. The spec asked for one entry. It is a security-relevant extra, since an inherited `GIT_CONFIG` would hide drivers from discovery. | CHANGELOG.md | 4 | BLAKE |
| R7 | [1/4] | ⚪ | Inherited command-scope `filter.*` pairs are dropped rather than overridden to a disabled value. This is equivalent in effect, but the docstring says drivers are "disabled through command-scope configuration". | skills/run-agoge/scripts/target_snapshot.py:113 | 3 | BLAKE |
| R8 | [1/4] | ⚪ | A submodule path that is a symlink back to its parent would recurse in `_filter_overrides` and `take_snapshot`, because the cache is written only after the recursion. It ends in a `RecursionError`, caught as exit 2, so it fails closed. | skills/run-agoge/scripts/target_snapshot.py:214 | 3 | BLAKE |
| R9 | [1/4] | ⚪ | Residual risk is documented correctly and not overclaimed: `core.pager`, hooks, `diff.external`, `core.alternateRefsCommand` and credential helpers are not blocked (`skills/run-agoge/scripts/target_snapshot.py:31`). | skills/run-agoge/scripts/target_snapshot.py:31 | general | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] ⚪ `_base_env` removes `GIT_CONFIG_PARAMETERS` (the legacy `-c` propagation variable). `_inherited_config_pairs` only re-emits `GIT_CONFIG_COUNT` pairs. Settings an operator passed through that legacy variable are silently dropped, so "preserve unrelated effective settings" is not fully met. The behaviour is safe, because hostile filter keys there are dropped too, and the risk is low. | File: skills/run-agoge/scripts/target_snapshot.py:75 - single-voice

### Gate verification of R1, and its severity

Carl raised R1 at 🟠 high. This gate reproduced it rather than taking it on one
voice, then adjudicated the severity down to 🟡 medium. Reproduction, run from
the project root:

```
GIT_CONFIG_COUNT=4 GIT_CONFIG_KEY_3=core.fsmonitor GIT_CONFIG_VALUE_3=false \
  uv run --no-project --with pytest python -m pytest -q \
  test_target_snapshot_programs.py -k fsmonitor
-> 2 failed, 26 deselected
```

Both failures are the `_assert_program_ran` positive control: "fixture is inert:
the target's core.fsmonitor never ran". The cause is real and confirmed -
`TEST_ENV = {**os.environ, ...}` (`snapshot_fixtures.py:10`) carries the
caller's command-scope pairs through, and command scope beats repo-local scope.

Why 🟡 and not 🟠:

- The product code is unaffected. `target_snapshot.py` strips exactly this
  family in `_base_env`; the defect is in the test fixture only.
- There is no silent false pass. The positive control is doing its job: it
  fails loudly, which is the behaviour the helper exists for.
- The root cause predates this PRD's work range. `TEST_ENV` already read
  `{**os.environ, ...}` at `8c1bf7baf23ddd822e75ccf5cbe01286a62ef5ea`; the
  cycle-1 file split moved the block verbatim into `snapshot_fixtures.py`.
- The project's own gate is green at HEAD (241 passed, 2 skipped), and this
  session's environment carries no `core.fsmonitor` pair.

It is swept rather than discarded: the gate's own confirmation is a second
voice, so the single-voice discard rule does not apply to it.

## Alice

Consensus lens, implementation-aware. Two ⚪ findings (R3, R4) and a
cycle-1 verification pass: R3 (the 🟠 `GIT_CONFIG` blind spot) resolved by
`_GIT_CONFIG_REDIRECT_VARS` with a new parametrized regression; R1 (inline
control blocks) resolved via `_assert_program_ran` / `_capture_untouched`; R2
(source matrix) resolved - 6 sources x 2 kinds; R4 (file size) resolved - 585,
606 and 668 lines plus a 127-line fixtures module, and she compared the old file
against the three new ones by AST to confirm every other test moved
byte-identical. ruff F401/F811 clean on the changed files. Counts reconcile:
231 + 6 + 4 = 241.

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

Blind lens, PRD-only. No Critical, High or Medium defects. He checked the
fsmonitor static override, the discovery command shape, driver disabling,
`GIT_CONFIG_COUNT` transport, inherited-setting preservation, per-repo
discovery caching and submodule union, the exit-2 failure contract, the
unchanged snapshot shape, the test matrix and the CHANGELOG line. Six ⚪
findings (R5, R6, R7, R8, R9, plus the ledger-dismissed
`GIT_CONFIG_PARAMETERS` one). Four things he could not confirm: the
parked-branch failure claim, real-git behaviour of an empty `process` value,
the mode-000 skip, and whether the new tests fail against the unmodified
script.

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

Doubt lens + de-slop (codex, resumed from his cycle-1 thread). No issues found.

FIX: (none). VERIFY: (none). KNOWN: (none).

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

Gemini backend (copilot). One finding, R1, which he found by running the suite
himself in an environment whose command-scope config set `core.fsmonitor`, and
which this gate then reproduced. Several of his probe shells were denied by the
non-interactive permission gate.

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

Verdict: 9 findings
Tests: 241 passed, 0 failed, 2 skipped (suite run this cycle)
