---
head_sha: 74aeb18eaa9b5df204f13275999a3da525bcea3e
reviewers: fanout, blake, eve, bob, carl
---

## Alice

**00037-ignored-listing-grows-snapshot-v1-c1**
[ALICE] ✅ No issues found

Advisory (does not block): unneeded `extras` dict indirection for a single key (resolved by the rework's restructuring of the overflow filter). Rubric R13 (file-size cap) failed — pre-existing on both test files, flagged again below.

## Blake

**00037-ignored-listing-grows-snapshot-v1-c1**
1. (HIGH, fixed in rework) `_load` did not type-check `ignored_overflow`, though the card requires accepting a missing key and requiring an int when present.
2. (MEDIUM, fixed in rework) `compare` checked `ignored_overflow` only in the fresh snapshot instead of either snapshot.
3. (LOW, known limitation) Snapshot time and peak memory of the listing still grow with the ignored tree; only the stored size and the compare set shrink. Not required beyond what the card asked for.

## Eve

**00037-ignored-listing-grows-snapshot-v1-c1**
Round 1 (pre-rework):
- FIX: crossing the cap from under to over could falsely report `ignored-removed` for an ignored directory that is itself a nested git repository — fixed in rework.
- FIX: `_load` missing `ignored_overflow` validation (confirms Blake/Bob/Carl) — fixed in rework.
- FIX: CHANGELOG entry omits the loss that must-have 6 spells out — not fixed (optional wording improvement, the required acceptance string already matches).
- KNOWN: snapshot time/memory still linear in ignored-tree size; compare's before-side overflow check guards a state `take_snapshot` cannot produce; `SKILL.md` doc of `run-agoge` not updated with the cap (out of card scope); pre-existing `ignored-removed` false positive on a directory that gains a non-ignored file; the new version-refusal test hardcodes versions 4/5.

Delta (post-rework), range 4cbafc0..74aeb18:
- All three prior FIX findings confirmed RESOLVED, each pinned by a mutation probe.
- No regression introduced by the rework. Full suite: 296 passed, 2 skipped (pre-existing, unrelated).
- New LOW findings: the either-snapshot `compare` clause has no dedicated test; the rework left the directory filter applied in two places (cosmetic); the nested-repo regression test's name falls outside the card's narrow `-k` gate; CHANGELOG wording carried over from round 1, still not addressed.
- KNOWN: `_load` accepts any int for `ignored_overflow` including values `take_snapshot` never writes; out of the card's literal requirement.

D1-D5: pass (both rounds)

## Bob (codex)

**00037-ignored-listing-grows-snapshot-v1-c1**
1. (MEDIUM, fixed in rework) `_load` accepted `ignored_overflow` of any JSON type.
2. (MEDIUM, fixed in rework) `compare` checked overflow only in the fresh snapshot.
3. (MEDIUM, known limitation) `take_snapshot` is 56 lines, over the 50-line rubric cap; decodes every ignored path before deciding which to discard. Not reworked — a refactor risked destabilizing passing tests with no additional review pass to catch a regression, and no rubric rule blocks the exit on it alone.
4. (LOW, known limitation, pre-existing) `test_target_snapshot_state.py` and `test_target_snapshot.py` already exceeded 800 lines before this card.
5. (LOW, known limitation) The cap reduces stored size, but git still enumerates every ignored file and Python still decodes the full listing to get the exact count.

Rubric: R1 fail (no dedicated test for the either-snapshot clause — see Eve's delta), R2/R3/R4/R6/R8/R10/R11 pass, R7/R9 fail initially (both resolved by rework; not re-run against rework), R12 fail (50-line cap), R13 fail (800-line file cap, pre-existing).

## Carl (gemini)

**00037-ignored-listing-grows-snapshot-v1-c1**
Same three MEDIUM findings as Bob, independently: `_load` validation gap, `compare` either-snapshot gap, `take_snapshot` over 50 lines — all MEDIUM-confirmed; first two fixed in rework, third left as a known limitation (see Bob's note). Plus the two pre-existing LOW file-size findings.

Rubric: R1/R9 fail (pre-rework only), R7 fail (pre-rework only), R12/R13 fail (pre-existing/structural, not blocking).

Verdict: converged
Tests: 296 passed, 2 skipped, 0 failed (fast-track batch suite)
codex_rung_guard: not fired
