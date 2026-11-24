# Decision Audit Log: 00028-test-suite-takes-65-seconds-v1

PRD: `00028-test-suite-takes-65-seconds-v1.md`
Started: 2026-11-24T23:53:59Z
Completed: 2026-11-24T23:53:59Z
Autonomous: 6  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: Two sites still use the per-test builder with no comment saying why, which the PRD requires ("say why in a comment"). `_source_submodule` calls `_add_submodule` per test, which costs about 1.2 s in each of the three parametrized cases that use it. `test_untouched_linked_worktree_and_submodule_compare_unchanged` copies `template_target` and then adds a submodule per test. Convert the second test to `template_target_with_submodule` plus the worktree add. For the first, either take the submodule template or add a comment giving the reason it can't.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: test_every_gitdir_entry_is_checked_or_listed hedges with or: either outcome satisfies it

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: Ten of fourteen cycle-1 findings discarded: four as duplicates of R1, two as duplicates of R10/R5, two low-severity refutations or restatements, and two against PRD text (the 40 s target is a stated guess; the T3 commit message records the baseline).

**Choice**: discarded with recorded reasons in the settled-decisions ledger

**Rationale**: Each discard has a verified reason: duplicate coverage by an accepted fix task, single-voice medium with the PRD's own exception already satisfied, or a requirement the PRD explicitly states is not binding.

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: R1 (cycle 2): the linked-worktree test still builds a submodule per test with no stay-on-builder comment

**Choice**: auto-fix via the converged cycle's tail sweep

**Rationale**: 3/4 consensus, PRD requires a conversion or a comment, and Carl probed the conversion working

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: R2-R7 (cycle 2): six single-voice or already-settled medium/low findings

**Choice**: discarded

**Rationale**: R2, R3, R4, R6, R7 are single-voice medium/low; R3 and R4 also restate cycle-1 settled calls; R5 is a computed replay fact expected of a behavior-preserving refactor

### [autonomous] 2026-11-24T23:53:59Z

**Decision**: R1's second site is untouched. `test_untouched_linked_worktree_and_submodule_compare_unchanged` still copies `template_target` and then calls `_add_submodule` per test (about 1.2 s). It has no stay-on-builder comment. The PRD requires one ("say why in a comment"). R1's fix task and the settled-decision text both promised to convert it or record why it cannot be, and the diff's one-hunk change to the state file only touched line 394. Fix: copy `template_target_with_submodule` and then run `git worktree add --detach`, or, if the worktree-before-submodule order matters, add a comment saying why.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [deferred] 2026-11-24T23:53:59Z

**Decision**: `test_target_snapshot.py` is 809 lines, over the 800-line cap. The cap was already flagged in the 00027 review, and this diff leaves the count unchanged, so the file stays over. Split the file or move tests out.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-24T23:53:59Z

**Decision**: Wall-time goal is not met in substance. HEAD took 55.18 s and the pre-change tree 56.99 s on the same machine, a gain of about 3%, which is noise level. The PRD target is under 40 s. The measured result suggests the time is dominated elsewhere, probably the python child process each test spawns, so the fix barely addresses the stated problem.

**Choice**: deferred

**Rationale**: deferred by review-close
