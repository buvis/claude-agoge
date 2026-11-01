# PRDs 00003 and 00005: release preparation

Batch: `202611012029`. Built with installed autopilot 0.10.0.
Source at batch completion: `7966c0d`.

## Result

- Both PRDs moved to `prds/done/` after two review cycles each.
- Every cycle ran Alice's consensus, Blake's PRD-only, and Bob's doubt/de-slop lenses in a fresh review session.
- Carl also reported in both 00003 cycles. His route failed authentication during 00005 and was recorded unavailable.
- Direct final gate: `dev/bin/release-checks` exited 0, **163 passed in 11.31s**.
- `git diff --check 6decbb8..7966c0d` passed.
- No extra worktrees or branches were created. Batch review scratch was moved outside the repo; the incoming handoff was retained.

## Remaining finding

PRD 00005 reached its two-cycle cap with a residual strict-decoding issue in
`target_snapshot.py`'s `_text()`: non-UTF-8 repository paths or ref names can
raise a traceback and exit 1 instead of the specified exit 2 diagnostic.
The cap policy deferred it, with a HIGH follow-up under
`prds/hold/00006-triage-text-in-skills-run-agoge-scripts-target-v1.md`.
Completion of the batch does not mean this finding is fixed.

## Runtime failures and evidence correction

The per-task reviewer helper repeatedly emitted this startup error:

> Permission deny rule: Write(**/dev/local/**) is not matched by file permission checks — only Edit(path) rules are.

Retries with the same session ID then reported that the ID was already in use.
Several generated build records label these failures `oauth_token_revoked` or
`oauth_revoked`; those labels are unsupported by the captured error above.
The mandatory PRD-level review lenses did run.

The drain's agoge launch emitted the same permission-rule error and produced no
QA report. Its child process was terminated, and the wrapper recorded rc 143.
The local snapshot comparison was unchanged while that failed child was alive.
After wrapper finalization, comparison detected only the expected `7966c0d`
commit and its index/status effects: loop metrics, the failed-QA log, and the
archived final state. This is not a successful product-QA run.

The installed autopilot verification parser also rejected pytest's ordinary
summary format: the test process exited 0, but `autopilot verify` exited 3 with
null counts. Final counts above come from the direct release-checks output.
These installed-plugin issues were reported without patching the frozen
`claude-autopilot` repository.

## Release and scoring

The incoming handoff expected 0.1.4. Entry verification instead found a clean
`6decbb8`, tagged `v0.2.0`, matching `origin/master`; installed agoge was also
0.2.0. That release predates this batch.

The requested `dev/bin/release minor` now means **0.2.0 → 0.3.0**. It publishes
a tag and updates the central marketplace, so it awaits explicit approval.
The marketplace checkout was clean at preparation time.

After publication, update the plugin with `/plugin update agoge@buvis-plugins`
(the shared release script prints this command), mirror the three requested
documentation files on an isolated agent-skills branch, run braid checks, and
score fresh CLI/web arms with the released plugin. No scored run was attempted.

PRD 00371 must not run in the now-frozen `buvis/claude-autopilot` repository.
Route that follow-up through `buvis/agent-plugins/plugins/autopilot` and its port
inventory. No other session's changes were edited.
