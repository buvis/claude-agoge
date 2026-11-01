# Assumptions ledger — PRD 00003 (fence-lane-scratch-work-out-of-target)

## Task 1: Write test_scratch_contract.py

- Fixture's seed commit uses a file named README.md with content "seed\n" (task said "any file, any content").
- The lane_dir's placeholder .git/description file content is the standard git default text (task said "...", any content works since the test only checks dir/file structure, not content).
- Test 3's assertions check refs/heads/master SHA changed, refs/tags/v1.0.0 exists, and refs/remotes/origin/master SHA changed (parsed via a local for-each-ref line-split helper), matching the task's three named conditions.
- Test 5's two slices are text[dispatch_idx:recon_idx] and text[recon_idx:] (dispatch heading to recon heading, then recon heading onward) — disjoint, as required; content before the dispatch heading is in neither slice, which the task didn't require to be checked.
