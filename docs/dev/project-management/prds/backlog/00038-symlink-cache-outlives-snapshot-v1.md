---
design: skip
default_model: opus
model_tier_rationale: equivalence obligation - fingerprints must stay byte-identical while the symlink walk is rewritten
---
# A cached symlink check outlives its snapshot, and a deep path raises RecursionError

Source: review 1 of PRD 00024 (`docs/dev/project-management/reviews/00024-snapshot-slow-many-untracked-files-v1-review-1.md`, rows by Eve, Alice, Blake and Bob) and the codex supplement (`docs/dev/project-management/reviews/00024-snapshot-slow-many-untracked-files-v1-codex-supplement.md`, one HIGH). This PRD closes three deferred records of batch 202611232314 (`docs/dev/project-management/autopilot/deferred/202611232314-deferred.json`): the process-lifetime symlink cache, the unpinned ancestor propagation and the unused `_name` binding.

## Problem

PRD 00024 made `_external_symlink_dir` in `target_snapshot.py` recursive and memoised it with `functools.lru_cache` for the life of the process. Two defects follow.

1. A process that fingerprints a path, has the path's directory replaced by a symlink that leaves the repo, and fingerprints the path again gets the cached answer "safe" and reads the file outside the repo. Measured 2026-11-24: in one process, a dirty tracked file under `sub/`, `take_snapshot`, `sub` replaced by a symlink to an outside directory, then `compare`; the `tracked` violation's `after` holds the sha256 of the outside file. No shipped command does this (one CLI call is one process and one snapshot), but PRD 00037 adds in-process tests that take a snapshot and compare, and any later caller that does the same reads outside the target.
2. A path more than about 1000 directories deep raises a RecursionError; `main` reports "unexpected RecursionError" and exits 2. The loop before PRD 00024 had no limit. Measured 2026-11-24: `_fingerprint(repo, "d/" * 3000 + "f.txt")` raises.

No test pins that a file two levels below an escaping symlink is `external-symlink`: with the parent recursion deleted, the suite stays green. Two asserts in `test_fingerprinting_many_files_stats_each_file_once` cannot fail on a script change.

Users hit: an operator whose target holds a very deep untracked tree (exit 2 in place of a result), and any in-process caller of `take_snapshot` followed by `compare`.

## Solution

Split the check. `_escaping_symlink(repo, rel_dir)` answers for one directory and carries the `lru_cache`. `_external_symlink_dir(repo, rel_dir)` walks the components of `rel_dir` top down in a loop and asks `_escaping_symlink` for each prefix: no recursion, no unused binding. `take_snapshot` calls `_escaping_symlink.cache_clear()` as its first statement, so each snapshot, and so each `compare`, checks every directory again, once. Fingerprints and the `lstat` budget of PRD 00024 do not change. Measured on this design 2026-11-24: 208 `lstat` calls for the 200-file layout of the existing count test, `absent` for the 3000-level path, `external-symlink` for both nested cases.

The first new test runs `take_snapshot` and `compare` in the test process, with the fixture's git environment applied through the `monkeypatch` fixture's setenv call (the approach PRD 00037 names). The other two call `target_snapshot._fingerprint` on a plain directory; `_fingerprint` reads no git state.

## Requirements

### Must have
- In one process, after a directory is replaced by a symlink that leaves the repo, `compare` reports `external-symlink` for a path under it and does not read the outside file.
- `_fingerprint` returns `absent` for a path 3000 directories deep that does not exist.
- A file two directory levels below an escaping symlink has the fingerprint `external-symlink`, for a top-level link and for a nested link.
- `test_fingerprinting_many_files_stats_each_file_once` keeps its `lstat` bound and passes; `test_fingerprints_unchanged_by_symlink_cache` passes unchanged.
- `CHANGELOG.md` `[Unreleased]` `### Fixed`: `- **run-agoge**: target snapshot fingerprints paths more than 1000 directories deep and checks directory symlinks again on every snapshot`.

### Nice to have
- None.

## Implementation

### Module: snapshot symlink check
- **Location**: `skills/run-agoge/scripts/target_snapshot.py`, `skills/run-agoge/scripts/test_target_snapshot.py`, `CHANGELOG.md`
- **Responsibility**: decide, once per directory and per snapshot, whether a path sits under a symlink that leaves the repo.
- **Exports**: none
- New symbols: `_escaping_symlink`, `test_compare_in_one_process_rechecks_swapped_directory`, `test_fingerprint_of_very_deep_path_is_absent`, `test_file_below_nested_external_symlink_is_external`
- **Risk**: `take_snapshot` calls itself for each submodule, so the cache is also cleared in the middle of a parent snapshot. That costs a few repeated `lstat` calls and changes no result.

### Dependencies
- snapshot symlink check: No dependencies (foundation)

## Tasks

### Phase 0: Fix
- [ ] Add three tests to `skills/run-agoge/scripts/test_target_snapshot.py`. `test_compare_in_one_process_rechecks_swapped_directory(tmp_path, monkeypatch)`: `target, env = _build_target(tmp_path)`, then `monkeypatch.setenv(key, value)` for every item of `env`; create `sub/child.txt` with `child v1\n`, `git add -A` and commit through `_git`, rewrite it to `child v2\n`; `before = target_snapshot.take_snapshot(os.path.realpath(target))` in the test process; create `tmp_path / "outside" / "child.txt"` with `not the real child\n`, run `_git(target, env, "rm", "-q", "-r", "--cached", "sub")`, `shutil.rmtree(sub)`, `sub.symlink_to(outside)`; `report = target_snapshot.compare(os.path.realpath(target), before, set())`; the `tracked` violation for `sub/child.txt` has an `after` that contains `external-symlink` and does not contain `_sha(b"not the real child\n")`. `test_fingerprint_of_very_deep_path_is_absent(tmp_path)`: an empty directory `tmp_path / "target"`; `target_snapshot._fingerprint(os.path.realpath(repo), "d/" * 3000 + "f.txt") == "absent"`. `test_file_below_nested_external_symlink_is_external(tmp_path)`: `repo / "inner"` exists, `outside / "sub" / "deep.txt"` exists outside the repo, `repo / "out-link"` and `repo / "inner" / "out-nested"` are symlinks to `outside`; `_fingerprint` gives `external-symlink` for `out-link/sub/deep.txt` and for `inner/out-nested/sub/deep.txt` - Acceptance: `pytest -k "rechecks_swapped_directory or very_deep_path"` fails on the unmodified script (the first with the outside sha in `after`, the second with a RecursionError); `pytest -k below_nested_external_symlink` passes on it.
- [ ] In `skills/run-agoge/scripts/target_snapshot.py`, replace `_external_symlink_dir` with two functions. `_escaping_symlink(repo: str, rel_dir: str) -> bool` under `@functools.lru_cache(maxsize=None)`: `check = os.path.join(repo, rel_dir)`; return `False` when `not os.path.islink(check)`; else return `os.path.commonpath([os.path.realpath(check), repo]) != repo`. `_external_symlink_dir(repo: str, rel_dir: str) -> bool`, not cached: start with `check = ""`; for each non-empty `part` of `rel_dir.split(os.sep)` set `check = os.path.join(check, part)` and return `True` when `_escaping_symlink(repo, check)`; return `False` after the loop. Add `_escaping_symlink.cache_clear()` as the first statement of `take_snapshot`. Do not change `_fingerprint`. Premise: `rg -n "_name = os.path.split" skills/run-agoge/scripts/target_snapshot.py` hits once, inside `_external_symlink_dir`; if it does not hit, stop and report (depends on: previous task) - Acceptance: `pytest -k "rechecks_swapped_directory or very_deep_path or below_nested_external_symlink or stats_each_file_once or unchanged_by_symlink_cache"` passes.
- [ ] In `test_fingerprinting_many_files_stats_each_file_once`, delete the two lines `assert len(paths) == 200` and `assert len(set(prints.values())) == 200`. Premise: `rg -c "== 200$" skills/run-agoge/scripts/test_target_snapshot.py` prints 2; if it prints another number, skip this task and report - Acceptance: `rg -c "== 200$" skills/run-agoge/scripts/test_target_snapshot.py` prints nothing and exits 1, and `pytest -k stats_each_file_once` passes.
- [ ] Add the CHANGELOG entry - Acceptance: `rg -F "checks directory symlinks again on every snapshot" CHANGELOG.md` hits under `[Unreleased]` `### Fixed`.

## Success Criteria

- `pytest -k "rechecks_swapped_directory or very_deep_path or below_nested_external_symlink or stats_each_file_once or unchanged_by_symlink_cache"` passes; the full suite passes under `dev/bin/release-checks`.
