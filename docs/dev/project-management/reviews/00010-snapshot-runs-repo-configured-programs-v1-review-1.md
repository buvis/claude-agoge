---
prd: 00010-snapshot-runs-repo-configured-programs-v1.md
cycle: 1
head_sha: 7c872f23d05ba8311eca8591067191a045fa9ccb
codex_thread_id: 01a1c2dc-3a6d-7501-b699-2f6730e597ef
reviewers: alice,blake,bob,carl
---

# Review cycle 1 - 00010-snapshot-runs-repo-configured-programs-v1

Diff range: 8c1bf7baf23ddd822e75ccf5cbe01286a62ef5ea..7c872f23d05ba8311eca8591067191a045fa9ccb
Scope: full review (cycle 1), PRD work range

codex_rung_guard: not fired

Pack: ok
Fail-first replay: skipped (runner produced no results, exit 4: file or directory not found: skills/run-agoge/scripts/test_target_snapshot.py) - the replay lens is therefore absent this cycle; the tautological-shape lens ran.
Note on reviewer independence: Carl's transcript shows he read `docs/dev/tmp/bob-output-202611100035.txt` during his run, so his agreement with Bob on R3 and R1/R2 is not an independent voice. R3 was instead verified directly by this gate (see below).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | `test_snapshot_does_not_run_fsmonitor`, `test_snapshot_does_not_run_clean_filter`, `test_snapshot_does_not_run_clean_filter_named` and `test_snapshot_does_not_run_clean_filter_from_any_source` each inline the positive-control block (status, assert log non-empty, unlink). `_assert_program_ran` was extracted for exactly that block, and the first two tests also inline what `_capture_untouched` does. Use the helpers. | skills/run-agoge/scripts/test_target_snapshot.py:1148 | 3 | ALICE, BOB, CARL |
| R2 | [3/4] | 🟡 | Must-have says marker tests cover clean and process filters from local, global, included, conditional-include, worktree and submodule configuration. The source matrix `_FILTER_SOURCES` (test_target_snapshot.py:1547) configures only `filter.<x>.clean` through `_configure_filter`. The only process-filter marker test is local-only (`test_snapshot_does_not_run_required_process_filter`). The code treats clean and process identically, so the risk is low, but the matrix is incomplete. | skills/run-agoge/scripts/test_target_snapshot.py:1558 | 2 | BLAKE, BOB, CARL |
| R3 | [2/4] | 🟠 | `_base_env` preserves `GIT_CONFIG`, which can redirect `git config` discovery to an empty file while `git status` still reads repository filters. This leaves configured programs executable. Strip `GIT_CONFIG` and add a marker regression with an empty alternate config, proving the bare-status control fires and snapshot/compare suppress it. | skills/run-agoge/scripts/target_snapshot.py:98 | 3 | BOB, CARL |
| R4 | [2/4] | 🟡 | `test_target_snapshot.py` is 1936 lines against the 800-line limit. It was already about 1280 lines before this diff, which adds 654. Splitting the does-not-run suite into `test_target_snapshot_programs.py` would fix it. | skills/run-agoge/scripts/test_target_snapshot.py:1 | general | ALICE, BOB |
| R5 | [1/4] | 🟡 | Behavior added in `_base_env` and `_inherited_config_pairs` has no test. Untested: stripping of `GIT_CONFIG_PARAMETERS` (a second channel through which a caller can hand git a hostile `filter.*.clean`), case-insensitive matching of inherited filter keys (the `folded` branch), a negative or non-integer `GIT_CONFIG_COUNT`, and dropping of a pair with a missing KEY or VALUE. `rg` finds no `GIT_CONFIG_PARAMETERS` and no upper-case `FILTER.` key anywhere in the test file. Removing `GIT_CONFIG_PARAMETERS` from `_GIT_CONFIG_COUNT_VARS`, or replacing the fold with `folded = key`, would leave the suite green while reopening the hole. I did not run either mutation, so this rests on reading the code. Add one parametrized test that sends `FILTER.<drv>.CLEAN` through `GIT_CONFIG_COUNT` and a `filter.<drv>.clean` through `GIT_CONFIG_PARAMETERS`, each with a positive control. | skills/run-agoge/scripts/test_target_snapshot.py:1518 | 3 | ALICE |
| R6 | [1/4] | 🟡 | The submodule enumeration in `_filter_overrides` copies the one in `take_snapshot`. Both split `ls-files --stage -z` on NUL, test `b"160000 "`, take the path after the tab and check `<path>/.git`. Extract one `_initialized_submodules(repo)` helper. It would also bring `_filter_overrides` from exactly 50 lines (the limit) down to about 40. | skills/run-agoge/scripts/target_snapshot.py:200 | 3 | ALICE |
| R7 | [1/4] | 🟡 | `GIT_CONFIG_PARAMETERS` is dropped entirely rather than parsed. A caller's unrelated `-c` settings passed that way, for example from a git alias or hook that runs this script, are silently discarded. The PRD says unrelated effective settings must be preserved. Dropping it is the safe direction and matches the design contract, so I do not call it a defect. Pin it with the test above and record the limitation in the docstring or the design. | skills/run-agoge/scripts/target_snapshot.py:92 | 3 | ALICE |
| R8 | [1/4] | 🟡 | `test_inherited_non_filter_config_pair_still_takes_effect` is subsumed by `test_snapshot_does_not_run_inherited_command_scope_filter`. That test already asserts that `diff.ignoreSubmodules=all` takes effect against a baseline. It also passes against the pre-change code, because the old `_git` forwarded inherited pairs. Drop it or merge it. | skills/run-agoge/scripts/test_target_snapshot.py:1568 | 2 | ALICE |
| R9 | [1/4] | 🟡 | Task 2 asks for recursive-submodule coverage, but every submodule test is one level deep (`sub` under the target). Nothing nests a grandchild submodule, so the recursion in `_filter_overrides` is never pinned by a regression test. A later change could break it unnoticed; my probe shows it works today. | skills/run-agoge/scripts/test_target_snapshot.py:1704 | 2 | BLAKE |
| R10 | [1/4] | 🟡 | The supplied mechanical check identifies an either-or hedge in `test_every_gitdir_entry_is_checked_or_listed`. Replace it with the intended exact assertion in separate test maintenance; this existing test is unchanged by the PRD. | skills/run-agoge/scripts/test_target_snapshot.py:1023 | general | BOB, mech-check |
| R11 | [1/4] | ⚪ | `test_unreadable_included_config_exits_2_and_runs_nothing` calls `pytest.skip` when the user can read a mode-000 file, which is the case when run as root. In that environment the discovery-failure requirement goes unverified. The 2 skipped in this run were not attributed to specific tests. Acceptable, but name it. | skills/run-agoge/scripts/test_target_snapshot.py:1641 | 2 | ALICE |
| R12 | [1/4] | ⚪ | The computed `[MECH]` hedge in `test_every_gitdir_entry_is_checked_or_listed` is pre-existing and not part of this change. Listed for completeness. | skills/run-agoge/scripts/test_target_snapshot.py:1023 | general | ALICE |
| R13 | [1/4] | ⚪ | The environment is unbounded. A target with very many `filter.*` drivers could hit `E2BIG` and surface as `target_snapshot: unexpected OSError` instead of a reasoned line. The design review already recorded this as a non-blocker. | skills/run-agoge/scripts/target_snapshot.py:187 | 3 | ALICE |
| R14 | [1/4] | ⚪ | A filter name containing a space has no marker positive control. It cannot have one, because `.gitattributes` cuts a value at whitespace. The test documents this and substitutes a behavioural probe of the effective config through `target_snapshot._git`, plus a `check-attr` control. This is a justified deviation from "names containing spaces" but remains weaker than a marker test. | skills/run-agoge/scripts/test_target_snapshot.py:1621 | 2 | BLAKE |
| R15 | [1/4] | ⚪ | `GIT_CONFIG_PARAMETERS` (the old `-c` inheritance from a parent git process) is dropped wholesale and is not forwarded the way `GIT_CONFIG_COUNT` pairs are. Unrelated settings inherited that way are lost, which only partly meets "preserve unrelated effective settings". The old script already dropped these. It is safe, since dropping fails closed, and the docstring does not mention it. | skills/run-agoge/scripts/target_snapshot.py:75 | 3 | BLAKE |
| R16 | [1/4] | ⚪ | The error message for a path that is not a git repo changed. `_resolve_repo` now fails first in discovery's `ls-files`, so the reason reads "git ls-files failed" instead of "git rev-parse failed". It is still one line with exit 2. | skills/run-agoge/scripts/target_snapshot.py:204 | 3 | BLAKE |
| R17 | [1/4] | ⚪ | Submodule discovery relies on `os.path.exists(<path>/.git)`. A gitlink whose submodule was not initialized is skipped, which matches the documented "uninitialized is unchecked" policy. | skills/run-agoge/scripts/target_snapshot.py:208 | 3 | BLAKE |

### Gate verification of R3 (the one 🟠)

This gate reproduced R3 directly rather than taking it on consensus, because
Carl had read Bob's output. Probe (`/tmp/gitconfig-probe/`): a scratch repo with
a local `filter.probe.clean` marker script and `*.txt filter=probe`.

```
discovery WITHOUT GIT_CONFIG            -> filter.probe.clean found, exit 0
discovery WITH GIT_CONFIG=<empty file>  -> no keys, exit 1 ("no matching key")
git status WITH GIT_CONFIG=<empty file> -> MARKER RAN (6 lines)
```

`_base_env` keeps `GIT_CONFIG`, and `_filter_overrides` treats discovery exit 1
as "this repo declares no filters". An inherited `GIT_CONFIG` therefore blinds
discovery while `git status` still honours the repository's own filter driver:
the PRD's central must-have ("a snapshot of a repo with clean-filter marker
scripts leaves no marker file") fails under that environment. The docstring at
`target_snapshot.py:92` asserts the opposite for the `GIT_CONFIG_*` redirect
family, and that reasoning does not hold for `GIT_CONFIG` itself, which `git
config` honours but `git status` ignores. CONFIRMED.

## Alice

Consensus lens, implementation-aware. No Critical or High issues; nine findings
(R1, R4, R5, R6, R7, R8, R11, R12, R13). She ran the full suite herself:
231 passed, 2 skipped.

R1: fail
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
R13: fail

## Blake

Blind lens, PRD-only. He located the implementation himself and built a
throwaway grandchild-submodule probe in `/tmp/blake00010`: the grandchild's
`filter.zz.clean` marker fired on a bare `git status` (positive control), and
`target_snapshot.py snapshot` on the parent left it absent. Recursion works but
is untested (R9). Findings: R2, R9, R14, R15, R16, R17.

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

Doubt lens + de-slop (codex). Raised the one 🟠 (R3) plus R1, R2, R4, R10.

FIX: R3, R2, R1. VERIFY: (none). KNOWN: R10, R4.

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini backend (copilot), frontend & design specialist, generalist here.
Findings: R3, R2, R1. His transcript shows he read Bob's output file mid-run, so
these three are echoes rather than independent votes; several of his own reads
(`target_snapshot.py`, one prior review file) and his test run were denied by
the non-interactive permission gate.

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

Verdict: 17 findings
Tests: 231 passed, 0 failed, 2 skipped (suite run this cycle)
