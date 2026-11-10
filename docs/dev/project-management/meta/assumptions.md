# Implementor assumptions - 00010-snapshot-runs-repo-configured-programs-v1

## 1: Add the two failing does-not-run regression tests (fsmonitor, clean filter)

- Both tests end with `assert code == 0, report` for `compare` (snapshot and compare run back to back with no intervening edit, so an unchanged report is the correct post-fix outcome). That branch could not be executed, since verifying it requires the mitigation this task forbids writing; the current failure occurs before it. `_compare` already rejects exit 2, so a required-filter regression is covered either way.
- Marker scripts are POSIX `sh`, not Python: the design names `marker.sh`, and the Python-only rule in `~/.claude/rules/claude-tooling.md` governs Claude Code hooks, not test fixtures.
- The control uses `git status --porcelain` (no `--no-optional-locks`) through the existing `_git` helper, as the design's "bare `git status`" prescribes; `_git` leaves stdin inherited, which is pytest's `/dev/null` under default capture, so the marker script's `exec cat` sees immediate EOF.
- `_configure_filter` stages only `.gitattributes` (not `add -A`) to avoid touching the other fixture files; the design did not specify the add pathspec.
- Scope: only the two tests the dispatch names were written. The design's parameterized items 3-8 are task 2, not silently skipped work from task 1.

## 2: Parameterize does-not-run coverage

- `has space` keeps a case with a discovery-based control instead of the contract's marker control, because git cannot carry a space in a `.gitattributes` value (verified independently: `*.txt filter=has space` sets the attribute to `has`, and no quoting form works). A permanently red test was judged the wrong reading of "a broken fixture must fail".
- The process-filter control uses the existing `_marker` (which cannot speak git's long-running filter protocol) and treats git's own exit-128 failure plus a written marker line as proof of launch; the brief allowed either that or a protocol handshake.
- The item-7 benign-pair, `core.bigFileThreshold` and item-8 cases are named without `does_not_run`, so they are excluded from the `-k does_not_run` verify command and covered by the full-file run.
- `test_snapshot_does_not_run_clean_filter_named[trudy]` duplicates the `[local]` source case; kept so each contract axis is complete on its own.
- Source-setup helpers take a uniform `(tmp_path, target, env, driver, script)` signature, so some ignore `tmp_path` or `driver`.
## 3: Neutralize fsmonitor and every effective filter driver in `_git`

Implementor:
- `_filter_overrides` passes `allow_fail=False` for its submodule-enumeration `ls-files` call (the Contract fixes `allow_fail=True` only for discovery and is silent here). Consequence: a non-repo target's exit-2 reason can now read `git ls-files failed: ...` instead of `git rev-parse failed: ...`. `_assert_exit2` tolerates it and the suite confirms, but the user-visible reason for a bad repo path has changed.
- No recursion guard for a submodule whose realpath equals an ancestor's (the cache entry is written after the recursion); untested by the spec, left out per the simplicity rule.
- "Matches `_FILTER_KEY_REGEX` case-insensitively on its first and last components" implemented as: only keys with at least three dot-separated components are candidates, first and last folded to lowercase, subsection byte-exact.
- `re.match` rather than `re.fullmatch` for the filter-key test; identical for this anchored pattern.

Test author (strengthening round):
- A correct implementation performs config discovery through the module's `_git` seam, so the space-named-driver test probes the effective configuration via `target_snapshot._git` with no new public symbol. An implementation that built the neutralizing env elsewhere would fail that probe.
- A correct implementation's first git call is its own config discovery, so an unreadable `include.path` surfaces as a reason naming config rather than `git rev-parse failed`.
- `core.excludesFile` is a legitimate harmless inherited pair whose effect is observable in the snapshot's `untracked`/`ignored` lists.
- `_git_dir_state` (mtime+size walk of `.git`) is stable across a snapshot and compare on a repo with filters or an fsmonitor configured; confirmed against a reference implementation.
- Randomized driver names keep test ids readable via shape names (`plain`/`equals`/`dots`); `-k` selection matches function names, so selection is unaffected.

Style-fix round:
- The gate's "lines" means the inclusive `def`-to-last-body-line span, so the fix targeted <= 49 rather than exactly 50.
- Changing a failure message's wording while keeping its assertion is allowed; only deleting assertions was forbidden.
- `rev-parse --absolute-git-dir` + `/config` is the same file as `<target>/.git/config` for a normal repo, so one code path serves parent and submodule.
- `_capture_untouched(sub, ...)` includes `_git_dir_state(sub)`, which is `{}` both times because a submodule's `.git` is a file; the config-bytes half is the real assertion there.

## Cross-task corrections

- Two recorded design measurements were refuted during task 2 and independently re-verified by the orchestrator: a submodule-only `filter.*.clean` DOES run during the parent's `git status` (3 marker lines), and the item-8 unreadable-`include.path` case cannot be made to fail first because every git call exits 128, so the unmodified script already exits 2 at `_resolve_repo`. The design's `## Data flow` and task 3's contract were corrected: `_filter_overrides` must union the submodule drivers into the parent's overrides.
