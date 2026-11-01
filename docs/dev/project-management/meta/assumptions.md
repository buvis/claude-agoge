# Assumptions ledger — PRD 00003 (fence-lane-scratch-work-out-of-target)

## Task 1: Write test_scratch_contract.py

- Fixture's seed commit uses a file named README.md with content "seed\n" (task said "any file, any content").
- The lane_dir's placeholder .git/description file content is the standard git default text (task said "...", any content works since the test only checks dir/file structure, not content).
- Test 3's assertions check refs/heads/master SHA changed, refs/tags/v1.0.0 exists, and refs/remotes/origin/master SHA changed (parsed via a local for-each-ref line-split helper), matching the task's three named conditions.
- Test 5's two slices are text[dispatch_idx:recon_idx] and text[recon_idx:] (dispatch heading to recon heading, then recon heading onward) — disjoint, as required; content before the dispatch heading is in neither slice, which the task didn't require to be checked.

## Task 2: Write target_snapshot.py (snapshot + compare, stdlib only)

- `reflog show` on a ref with no reflog (for example a tag) exits 0 with empty output, so it is a required call and empty output maps to `None`. git 2.56.0 behaves this way: `test_new_tag_is_ref_violation` passes.
- `symbolic-ref` exits other than 0 or 1 are treated as failures (exit 2).
- The `"R" in xy or "C" in xy` check decides whether a status record carries an old-path field.
- Failure to write `<out.json>` (for example a missing parent directory) maps to exit 2. The tests do not cover this.
- A snapshot JSON that is not a dict maps to exit 2 together with the version check.
- `_fingerprint` uses `os.path.islink` / `exists` / `isdir` on `repo/path` without resolving parent-directory symlinks. Git does not track paths beyond a symlink.
- Compare prints its JSON with `indent=2`, and the snapshot file is also written with `indent=2`.
