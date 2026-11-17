# Backlog review - claude-agoge - 2026-11-17

Verdict: GO (0 Blocking open after the apply pass)

14 PRDs, 00024-00037, all emitted by the agoge runs of 2026-11-15 and 2026-11-16. `wip/` and `hold/` are empty; there is no `discovery/` directory. Sequence numbers are unique across `prds/` and `intake/`.

## Map

| # | PRD | template | lines (pre-edit) | subsystem | depends on | lane | verdict |
|---|---|---|---|---|---|---|---|
| 00024 | snapshot-slow-many-untracked-files | minimal | 71 | target_snapshot `_fingerprint` | - | fast-track | FIX -> READY |
| 00025 | gitdir-walk-hangs-on-fifo | minimal | 88 | target_snapshot `_gitdir_files` | calls `_fingerprint` | fast-track | FIX -> READY |
| 00026 | untracked-files-hashed-in-full | minimal | 71 | target_snapshot `_fingerprint` | 00024 | fast-track | FIX -> READY |
| 00027 | allow-misses-removed-directory-contents | minimal | 70 | target_snapshot `compare` | - | fast-track | FIX -> READY |
| 00028 | test-suite-takes-65-seconds | minimal | 71 | snapshot test fixtures | - | solo (was fast-track) | FIX -> READY |
| 00029 | malformed-snapshot-passes-compare | minimal | 79 | target_snapshot `_load` | - | fast-track | FIX -> READY |
| 00030 | untracked-chmod-not-reported | minimal | 62 | target_snapshot docstring | - | fast-track | FIX -> READY |
| 00031 | fifo-replacement-reports-removed | minimal | 61 | target_snapshot docstring | - | fast-track | FIX -> READY |
| 00032 | changelog-omits-process-filters | minimal | 56 | CHANGELOG | - | solo (was fast-track) | FIX -> READY |
| 00033 | gpg-program-runs-on-compare | minimal | 62 | target_snapshot `_STATIC_OVERRIDES` | - | fast-track (classified) | FIX -> READY |
| 00034 | changelog-overstates-no-programs | minimal | 57 | CHANGELOG | 00032 | solo (classified) | FIX -> READY |
| 00035 | allocator-backlog-path-race | minimal | 62 | allocator `claim` | - | fast-track (classified) | FIX -> READY |
| 00036 | unreadable-untracked-error-wording | minimal | 60 | target_snapshot `_fingerprint` | 00025 (shared message path) | fast-track (classified) | FIX -> READY |
| 00037 | ignored-listing-grows-snapshot | minimal | 62 | target_snapshot `take_snapshot`, `compare` | 00027, 00029 (soft) | fast-track (classified) | FIX -> READY |

Lanes come from `autopilot` 0.10.0 `run-autopilot/cli/lane.py`, run over each file.

## Findings

### Blocking (all resolved by edits)

- [00024-00027, 00029-00031, 00033, 00035-00037] B contract: on the fast-track lane the card's Goal is the `## Problem` section plus the task lines, and nothing else from the PRD (`fast-track/scripts/cards_from_prd.py` `_render`; the test author "reads the card and nothing else", `references/spec-card.md`). Formats, messages, thresholds and test bodies sat only in Solution, Requirements and Test Strategy. Evidence that this bites: the staged card of done PRD 00011 (`docs/dev/tmp/fast-track-00011-...-c1-card.md`) lacked `special:10000`, the implementor returned a bare `special`, and the one rework round went on restoring the PRD's format; 00009 and 00010 were parked on their first fast-track pass. -> fails as: wrong-TDD lock-in. Fix: every task line now carries its exact contract (names, formats, message text, thresholds, what each test asserts).
- [00025, 00026, 00029, 00035, 00037] B contract: the test task said "Add the N tests named above". The names sat in the Module block, which the card does not carry, while the gates select by name with `pytest -k`. -> fails as: wrong-TDD lock-in, then stall (a `-k` filter that selects nothing exits 5 at the gate). Fix: tests named in the task line.
- [00025, 00029] B executability: the second task's acceptance read "the same `pytest -k` selection passes". The renderer takes each backticked command as a gate, so both cards carried a bare `pytest -k` gate, which exits with a usage error. -> fails as: stall (`stopped: gate 2`, PRD parked in `hold/`). Fix: the full command is written out; each card now renders one gate.
- [00030, 00031] B executability: both tests pin current behaviour and pass before the change. Fast-track stops a card whose new test is green before the implementation (`stopped: tests-green-before-implementation`). -> fails as: stall. Fix: the test also asserts the new docstring sentence (whitespace collapsed), the test task comes first, and the exact sentence is in the PRD.
- [00030] C path rule: the Solution told the implementor to fix the walter row of `meta/agoge-profile.md`. The row sits under `## Per-specialist strategy`, so the PRD's own condition is met, but the file is not in `Location` and no task names it. -> fails as: stall (the implementor cannot write the file) or rework thrash (a reviewer reads the instruction as unmet). Fix: instruction removed from the PRD; the profile edit is a follow-up below.
- [00028] B executability: `lane: fast-track` on a test-only refactor. The card has no failing test to start from, and a test author who adds one breaks the PRD's own "pass and skip counts equal the baseline". -> fails as: stall or rework thrash. Fix: `lane: solo`. The session does the conversion itself; `snapshot_fixtures.py` counts as a production path, so the build escalates to the full review, which is the wanted outcome. The literal `241 passed, 2 skipped` is now the recorded baseline (create-prd metric rule).
- [00033, 00035, 00036, 00037] B executability: the CHANGELOG line was folded into the implementation task without the literal `CHANGELOG.md`, so each card rendered `changelog: none`, which tells the lane to leave the file alone. -> fails as: rework thrash (a `fix` commit without its entry; the one rework round spent on it). Fix: a separate `Add the CHANGELOG entry` task with an `rg` acceptance, as 00024-00029 have.
- [00037] E cross-invalidation: the `VERSION` bump breaks `assert target_snapshot.VERSION == 4` in `test_target_snapshot.py:419` (the only literal; `rg -n "VERSION == 4" skills` verified). That file was not in `Location`, so it was outside the card's allowlist. -> fails as: stall (red suite the implementor cannot fix). Fix: path added, with a premise-checked task.
- [00037] B contract: the compare rule did not cover a tree that crosses the cap between snapshot and compare. Read one way, a snapshot at 20000 ignored files compared after a lane adds one (`__pycache__`, a build) reports every file named before as `ignored-removed`. It also left open whether `ignored_overflow` is always written; `test_ignored_contents_are_never_read` pins the exact key set. -> fails as: wrong-TDD lock-in. Fix: `ignored_overflow` is written only above the cap; when either snapshot carries it, only before entries ending in `/` are checked; new test `test_ignored_listing_crossing_cap_reports_no_file_removals`; `_load` interplay with 00029 stated. The "under 1 MB" must-have cannot be tested with a patched cap and is now an expected effect.
- [00034] H goal reversal: the new 0.3.1 line added `gpg` to the list of programs the snapshot no longer runs. 0.3.1 did not ship the gpg fix (00033 lands it under `[Unreleased]`), so the PRD wrote a false claim into released notes, which the release lane (wendy) exists to catch. -> fails as: goal reversal. Fix: `gpg` dropped from that line without condition; the dependency on 00033 is gone; the edit works on either form of the line.
- [00026] B executability: "must snapshot in under 1.5 s ... Timing is a manual check". -> fails as: unattended hang or rework thrash (a "must" nobody can verify). Fix: reworded as an expected effect, not a requirement.

### Non-blocking (applied)

- [00026] E cross-invalidation with done PRD 00019: `_big_file_target` builds a 200 MiB file. Above the 64 MiB cap that file is sampled, so the two peak-RSS tests would keep passing while no longer exercising the chunked whole-file hash. Applied: the fixture shrinks to `SAMPLE_ABOVE` (premise-checked), `test_target_snapshot_state.py` added to `Location`. Sampling also reaches git-dir files once 00025 lands; stated in Risk.
- [00029] The table check must run before the `belongs to another repo` check or a missing `repo` never reads as malformed; `data["version"]` raised `KeyError` on a versionless file. The version test hard-coded 4, which 00037 bumps. Applied: order stated, `data.get`, tests derive from `target_snapshot.VERSION`.
- [00035] `resolved_backlog` is a local of `main`, not available in `claim()`, and ten tests call `claim(repo, slug)` directly. As written, comparing the fd with a path that follows the same swapped link proves nothing. Applied: `claim()` keeps its signature, takes `os.path.realpath(backlog)` after the open, requires it under `os.path.realpath(repo)`, and refuses with a string `SystemExit` that `main` already maps to exit 2. The `(guess)` marker is resolved (patch `claimed_numbers`).
- [00036] E: the catch sits in `_fingerprint`, which 00025 routes git-dir files through, so a mode-000 git-dir file gets 00036's wording. Applied: stated and accepted in 00036; 00025's test asserts only the file name and the absence of `unexpected`.
- [00025] B resource: the red run reads a `/dev/zero` symlink without bound until the test timeout. Applied: `timeout=2` for that case.
- [00024] Test Strategy asked for `cache_clear()` on a helper the PRD does not name. Applied: each test uses a fresh `tmp_path` repo, so the cache starts cold.
- [00027] "`compare --help` mentions directories" tightened to "prints the word `directory`".
- [00033, 00035-00037] "the project's full test gate" now reads `dev/bin/release-checks`, the term the other ten use.
- [00026, 00037] `SAMPLE_ABOVE` and `ignored_overflow` added to `New symbols:` (grounding rows).

### Rejected (false positives, with evidence)

- `ground_prd.py` `unresolved` rows that remain are not repo symbols; the resolver searches only the repo: `stat.S_ISLNK`, `stat.S_IMODE`, `os.truncate`, `os.fstat`, `st_dev`, `st_ino`, `O_NOFOLLOW`, `ELOOP`, `ENOTDIR`, `PermissionError`, `target_snapshot.__doc__` (Python); `monkeypatch`, `monkeypatch.setenv` (pytest); `gpg`, `gpg.program`, `gpgsig`, `log.showSignature` (git).
- `check_links.py` rows in backlog: 00035, two lines that name the probe file of the run's reproduction. They are reproduction output in a fenced block, not citations.
- [00027] `test_allow_exempts_ignored_children_by_exact_path` was checked against the new prefix rule: both assertions still hold (`a.txt` does not prefix `sub/a.txt` or `vault/a.txt`).
- [00035] `test_cli_follows_symlink_inside_repo` symlinks `prds`, not `backlog`, so `O_NOFOLLOW` on the last component does not break it.
- [00036] The two existing unreadable-file tests assert only the file name in stderr; the new wording keeps it.

### Questions

- None open. Assumptions the operator can change are listed under Decisions applied.

## Reshapes

- Considered, not applied: merging 00032 into 00034 (both edit the same CHANGELOG line, 00034 rewrites what 00032 produces). Three options. (1) Keep both, fix 00034, run both solo: no reshape, keeps one finding per PRD number as the run minutes record it; costs one extra solo session. (2) Merge into 00032 and hold 00034: saves that session; breaks the minutes' numbering and needs a hold. (3) Hold 00032 as superseded and make 00034 stand alone: same saving, same break. **Chosen: 1**, the 2026-11-08 precedent, and a solo docs session is cheap.
- Considered, not applied: renumbering 00028 to the tail so it converts the tests that 00029-00037 add. The gain is about a dozen tests; the cost is a number the two run reports already cite.

## Gaps

- **Emitter drift, third time.** `skills/run-agoge/references/prd-emission.md` produced the systemic findings above. Its task template has no CHANGELOG task (the four PRDs of 2026-11-16 lost theirs), it allows a task to say "the tests named above", and although it warns that "the test author sees only the task line" its template task lines carry no contract. It also emits pinning tests that pass before the change. The next agoge run will emit the same shapes. Not fixed here: it is product code with a contract test (`test_prd_emission_contract.py`), outside this gate. See Follow-up.
- **Untested doc edits on fast-track.** The docstring edits of 00026, 00027, 00033 and 00037 are in the task lines but no test pins them. The fast-track implementor sees only the failing tests; a reviewer who reads the card is the only catch. Residual risk: one rework round on any of the four.
- **Profile row.** The walter row of `meta/agoge-profile.md` expects `untracked-modified` for `chmod` and for a fifo replacement. After 00030 and 00031 both are documented otherwise, so the next run would raise them again.
- No fix-type PRD lacks a regression test. No producer or consumer hole.

## End state after this batch

The snapshot stats each untracked file once, samples files above 64 MiB, caps the ignored listing at 20000 names, and reads git-dir files through the same fingerprint, so a fifo, device or large file under `.git` no longer hangs or fills memory. `compare --allow` covers a directory, rejects a malformed snapshot by field name, and no longer runs the target's gpg program. Unreadable files are named without "unexpected". The allocator creates through a directory fd. The docstring states the mode-bit and special-file limits; the 0.3.1 changelog line states what is not covered. Snapshot `VERSION` goes 4 -> 5 (per-run files, no migration). Still open: the emitter (above); tests added by 00029-00037 stay on the per-test builder after 00028; two detection guarantees are weaker by design and documented (same-size mid-file edits above 64 MiB, single ignored files above the cap).

## Frontmatter tuning

| PRD | set | why |
|---|---|---|
| 00024 | `default_model: opus` (was sonnet) | create-prd 5.6: equivalence obligation on a rewritten function plus a cache; the edit is not given as exact text |
| 00028 | `lane: solo` (was fast-track) | Blocking finding above |
| 00032 | `lane: solo` (was fast-track) | names only `CHANGELOG.md`; the card render fails (`framework`), so fast-track fell back to the full loop for a three-word edit |
| 00033, 00035-00037 | no `lane:` (unchanged) | classifier gives fast-track, `card_sized` |
| 00034 | no `lane:` (unchanged) | classifier gives solo, `no_production_code` |

## Decisions applied

The agent adjudicated every item under the standing authorization: all changes are reversible text edits to backlog PRDs, with no merge, split, renumber or hold. No interactive walk was run.

Assumptions the operator can change:

1. 00037: `ignored_overflow` only above the cap, and no file-level check when either side overflowed.
2. 00034: no `gpg` in the 0.3.1 line.
3. 00030: the profile edit is out of the PRD.
4. 00028: solo lane with an expected escalation to the full review.
5. 00035: the realpath-under-repo check inside `claim()`.
6. 00026: `_big_file_target` shrinks to the cap.
7. 00024: opus.

After the apply pass:

- Lens A passes on all 14: every `minimal.md` heading is present in order (plus the emitter's `## Test Strategy`), every task line carries `Acceptance:`, frontmatter holds only recognized fields with valid values.
- `cards_from_prd.py` renders one card for each of the 11 fast-track PRDs. Each first gate is red on the unmodified code by construction; no bare `pytest -k` gate remains; each PRD that owes a CHANGELOG entry carries a `changelog:` task.
- `ground_prd.py`: only the false positives listed above remain. `check_links.py`: only the two 00035 reproduction lines remain in backlog.

Not done, stated plainly:

- The `autopilot:plan-tasks` budget rules (steps 4-4.7) were not consulted. No PRD is near the 150K per-task budget (largest is under 100 lines) and none takes the full lane by classification.
- The suite was run once to ground 00028: 241 passed, 2 skipped in 56.56 s (the PRD says 65 s, the 2026-11-16 run 58 s).
- No PRD claim about git behaviour (gpg under `log.showSignature`, fifos absent from `ls-files --others`) was re-run; both carry a quoted reproduction from the runs.

## Follow-up

1. Fix `prd-emission.md` so the next run emits the shape this review had to restore: contract in the task lines, tests named in the task line, a separate CHANGELOG task, and a failing-first assertion for a pinning test. Proposed: one PRD through `/create-prd`, or a direct edit with its contract test.
2. Fix the walter row in `docs/dev/project-management/meta/agoge-profile.md` after 00030 and 00031 land: `chmod` on an untracked file -> unchanged (documented); fifo replacement -> `untracked-removed` (documented). Proposed: `--refresh-profile` on the next run, then check the row.
