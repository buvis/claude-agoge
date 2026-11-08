# Backlog review - claude-agoge - 2026-11-08

Verdict: GO (0 Blocking open after the apply pass)

All 17 PRDs came from the 2026-11-08 agoge run (`audit-results/agoge-2026-11-08.md`, findings 1-13 and 15-18). `wip/` and `hold/` are empty; no `discovery/` dir.

## Map

| # | PRD | template | lines (post-edit, ±3) | subsystem | depends on | verdict |
|---|---|---|---|---|---|---|
| 00007 | parallel-claims-share-prd-number | minimal | 63 | allocator | - | FIX -> READY |
| 00008 | integrity-check-misses-git-hooks | minimal | 66 | target_snapshot | - | FIX -> READY |
| 00009 | integrity-check-misses-untracked-edits | minimal | 64 | target_snapshot, SKILL.md | (00011 for FIFO safety, soft) | FIX -> READY |
| 00010 | snapshot-runs-repo-configured-programs | minimal | 61 | target_snapshot `_git` | - | FIX -> READY |
| 00011 | snapshot-hangs-on-fifo | minimal | 57 | target_snapshot `_fingerprint` | - | FIX -> READY |
| 00012 | inherited-git-dir-misreads-target | minimal | 57 | target_snapshot `_git` | - | FIX -> READY |
| 00013 | integrity-check-misses-worktrees-submodules | minimal | 66 | target_snapshot | - | FIX -> READY |
| 00014 | allocator-accepts-non-repo-path | minimal | 61 | allocator `main` | - | FIX -> READY |
| 00015 | allocator-follows-symlinked-prds | minimal | 57 | allocator `main` | - | FIX -> READY |
| 00016 | slug-trailing-newline-accepted | minimal | 58 | allocator | - | FIX -> READY |
| 00017 | crafted-snapshot-injects-restore-options | minimal | 58 | target_snapshot `_load` | - | FIX -> READY |
| 00018 | non-utf8-ref-restore-fails | minimal | 58 | target_snapshot restore | - | FIX -> READY |
| 00019 | snapshot-memory-grows-with-dirty-file | minimal | 59 | target_snapshot `_fingerprint` | - | FIX -> READY |
| 00020 | allocator-errors-print-traceback | minimal | 59 | allocator `main` | 00014 (CLI tests need `git init`) | FIX -> READY |
| 00021 | lane-git-identity-overridden | minimal | 60 | finding-contract.md | - | FIX -> READY |
| 00022 | readme-gym-link-404 | minimal | 55 | README | - | FIX -> READY |
| 00023 | ci-release-checks-suite-drift | minimal | 55 | dev tooling, CI | - | FIX -> READY |

## Findings

### Blocking (all resolved by edits)

- [all 17] A compliance: no `### Module:` block (Responsibility, Exports), no `### Dependencies`, no `### Nice to have`, no phase headings, and no task line carried an `Acceptance:` clause. -> fails as: wrong-TDD lock-in (plan-tasks invents acceptance). Fix: rewrote each one onto `minimal.md`. Each task now names its tests and gives a `pytest -k` or `rg` acceptance. Added `New symbols:` lines.
- [00008] B contract: "a test that pins the ignore list" could be read two ways: a tautology on a constant, or a check of a fresh `.git` against checked plus unchecked entries. The `VERSION` bump also breaks `test_untouched_target_compares_unchanged` (asserts `== 1`) and `test_unusable_inputs_exit_2_with_prefixed_stderr`, which writes `version: 2` as the "wrong" version and would load cleanly at v2. -> fails as: wrong-TDD lock-in and rework thrash. Fix: named `GITDIR_UNCHECKED` and `test_every_gitdir_entry_is_checked_or_listed`, set the violation shape, and added a premise-checked task that repoints both tests to `VERSION` / `VERSION + 1`.
- [00009] B contract: turning `untracked` into a map would break `test_non_utf8_paths_round_trip`, which asserts it is a list. The PRD also added snapshot fields with no version bump. -> fails as: rework thrash. Fix: a separate `untracked_fingerprints` key, an exact violation shape, and a `VERSION` bump.
- [00011] B contract: `special:<octal mode>` and "within a few seconds" were open to more than one reading. -> fails as: wrong-TDD lock-in. Fix: `f"special:{stat.S_IFMT(st.st_mode):o}"` (FIFO -> `special:10000`) and a 10 s subprocess timeout.
- [00018] B executability: "passes locally and on CI Linux" cannot pass on this macOS host. APFS rejects the loose ref file that `update-ref` writes, the same limit that skips `test_non_utf8_paths_round_trip`. -> fails as: rework thrash. Fix: probe-and-skip on macOS with the same reason text, run for real on CI Linux, and define `_shell_quote` exactly.
- [00019] B contract: "well under 64MB" is an adjective, and `RUSAGE_CHILDREN` in the pytest process carries every earlier child's peak. -> fails as: rework thrash or a vacuous pass. Fix: measure in a fresh wrapper process, assert < 48 MiB with unit normalization, and require the file be committed small then overwritten (so git does not hash it).
- [00022] B executability: `rg "github.com/buvis/agoge-gym"` over the repo can never come back empty, because `audit-results/agoge-2026-11-08.md` and the PRD itself quote the URL. -> fails as: rework thrash. Fix: scope it to `README.md skills agents`.
- [00023] B executability: the acceptance pinned `SKIPPED [1] test_target_snapshot.py:617`. Other PRDs in this batch add tests to that file, and 00018 adds a second macOS skip. -> fails as: rework thrash. Fix: assert a `SKIPPED` line with the reason text and no line number or count. The step-1 grounding `missing` row (bare file name) is gone.

### Non-blocking (applied)

- [00007] Design: the `.NNNNN.claim` marker leaves one hidden file per PRD in `backlog/` of every target repo forever. Deleting the marker reopens the race. Autopilot selection ignores non-`.md` names (`selection.py`), so this is clutter, not a selection break. Applied: `fcntl.flock` on the `prds` directory fd around scan and create, which leaves no file. `default_model: opus` because of the concurrency.
- [00010] `git config --local --get-regexp` skips `include.path` (includes are off for a scoped query), so a filter defined through an include would still run. Applied: query all scopes. This also neutralizes global filters such as git-lfs, which only adds dirty records (safe).
- [00014] As written, the check sat "before any mkdir" inside `claim`, which forces `git init` into ten `claim(tmp_path, ...)` tests. Applied: check in `main`; only `test_cli_prints_the_path_it_claimed` needs `git init`. Dropped the open "check prd-emission.md" hedge (verified: it passes an absolute top level).
- [00017] The open item "check what for-each-ref can emit" is answered: every key starts with `refs/`, and `HEAD` lives under the `head` key. Dropped `HEAD` and null from the rule.
- [00019] `hashlib.file_digest` needs Python 3.11. Applied: a chunked `iter(read(1 MiB))` loop of the same size that keeps 3.10.
- [00020] Defined the mapping (`OSError` and string `SystemExit` -> one line, exit 2, in `main`), so `test_a_bad_slug_is_refused_rather_than_normalized` stays unchanged.
- [00021] Dropped "check agent files for copies": `rg "user\.name" agents` is empty.
- [all] Frontmatter added. `lane: fast-track` + `design: skip` on the production fixes follows the 00006 precedent. 00007 keeps the full lane (concurrency). 00022/00023 use `lane: solo`. `default_model` per the create-prd 5.6 rubric: opus 00007, 00013, 00018; omitted (haiku ok) 00016, 00022, 00023; sonnet for the rest.

### Rejected (false positives, with evidence)

- `ground_prd.py` `unresolved` rows that remain: `FileExistsError`, `fcntl`, `flock`, `multiprocessing.Barrier`, `os.mkfifo`, `S_ISREG`, `UnicodeEncodeError`, `ru_maxrss`, `hashlib.file_digest` (stdlib); `GIT_DIR` and the other `GIT_*` variables, `FETCH_HEAD`, `ORIG_HEAD`, `COMMIT_EDITMSG`, `objects`, `branches`, `modules`, `core.fsmonitor`, `submodule` (git names); `SKIPPED` (pytest output). None is a repo symbol; the resolver only searches the repo.
- `check_links.py` rows in backlog: 00014 lines 31/33 and 00016 lines 7/31 quote reproduction output (paths in a scratch repo), not citations.

### Questions

- None open.

## Reshapes

- Considered, not applied: merging into allocator (00007, 00014-16, 00020), snapshot-coverage (00008, 00009, 00013), git-call hardening (00010-12, 00019) and restore/load (00017, 00018) groups. Kept separate for two reasons. First, `prd-emission.md` binds one accepted finding to one PRD number in the run minutes. Second, the fast-track lane (00006 precedent) cuts per-PRD ceremony to one pass. Same-subsystem PRDs already sit next to each other, mostly.

## Gaps

- **Emitter drift (root cause of the systemic Blocking finding):** `skills/run-agoge/references/prd-emission.md` maps findings onto RPG-style section names (Problem Statement, Target Users, Functional Decomposition...). These 17 PRDs follow neither that mapping nor `create-prd`'s `minimal.md`. The next agoge run will emit the same non-compliant shape. Candidate PRD: align the emission mapping with `minimal.md`, including Module, Dependencies, phase headings, per-task Acceptance and `default_model`. Not created here (this gate does not invent PRDs).
- Snapshot `VERSION` moves 1 -> 4 across 00008, 00009, 00013. That is fine for ephemeral per-run snapshots. No migration is needed.
- 00009 hashes untracked files. An untracked FIFO hangs until 00011 lands one PRD later in the same batch. This is safe because the batch runs in order.

## End state after this batch

The allocator serializes claims, refuses non-repo and escaping paths and newline slugs, and reports every failure as one line with exit 2. The integrity gate covers hooks and `.git/info`, untracked overwrites, ignored deletions, linked-worktree HEADs and submodules. Snapshots stop running repo-configured programs, ignore an inherited `GIT_DIR`, do not hang on FIFOs, hash in constant memory, reject malformed snapshot files, and print restore lines that work for non-UTF-8 refs (verified on Linux). The scratch contract names the lane in commits. Docs and the release gate stop overclaiming. Still missing: emitter compliance (gap above), and ignored-file edits plus submodule refs and config stay unchecked by design (documented).

## Frontmatter tuning

| PRD | set | why |
|---|---|---|
| 00007 | `design: skip`, `default_model: opus` | concurrency; full lane kept |
| 00008-00012, 00014, 00015, 00017, 00019-00021 | `lane: fast-track`, `design: skip`, `default_model: sonnet` | exact contracts, three paths, 00006 precedent |
| 00013, 00018 | `lane: fast-track`, `design: skip`, `default_model: opus` | invented predicate / byte-level quoting contract |
| 00016 | `lane: fast-track`, `design: skip`, no `default_model` | one-token fix |
| 00022, 00023 | `lane: solo`, `design: skip`, `catchup: skip`, no `default_model` | docs and dev tooling, no production path |

## Decisions applied

The agent adjudicated every item under standing authorization (all edits are reversible text edits; no merges, splits, renumbers or holds). The whole backlog was rewritten in place; after the apply pass, lens A passes on all 17 (every template heading present, every task carries `Acceptance:`), and the grounding re-run leaves only the false positives listed above.
