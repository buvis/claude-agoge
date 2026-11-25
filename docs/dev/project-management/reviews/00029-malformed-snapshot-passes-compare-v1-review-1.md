---
head_sha: 8937b42ca1e038d98ea6c25823fd4bdc23127a09
reviewers: fanout,blake,eve,bob,carl
consensus_run_id: wf_861ec741-26a
---

## Fanout

**00029-malformed-snapshot-passes-compare-v1-c1**
[fast-track-00029-malformed-snapshot-passes-compare-v1-c1] 🟠 Type validation covers only 3 of 13 required fields, leaving most mistyped fields to crash or misreport | File: skills/run-agoge/scripts/target_snapshot.py | Task: fast-track-00029 — RESOLVED in rework (commit 8937b42)

## Blake

**00029-malformed-snapshot-passes-compare-v1-c1**
[BLAKE] 🟠 Task 2 asks for a type check on every top-level key. `_load` checked only 3 of the 13 — RESOLVED in rework (commit 8937b42)
[BLAKE] 🟡 `repo` was never type-checked as str, coerced via `str(data.get("repo"))` — RESOLVED in rework (the coercion was removed)
[BLAKE] 🟡 No parametrized wrong-type test over all 13 keys — RESOLVED in rework
[BLAKE] ⚪ `untracked` entry hashability not checked (pre-existing, out of scope)
[BLAKE] ⚪ Non-string ref value reaching `re.fullmatch` (pre-existing, out of scope)

## Eve

**00029-malformed-snapshot-passes-compare-v1-c1 (cycle 1, doubt)**
FIX: type table not implemented — RESOLVED in rework
FIX: wrong-type behavior unpinned (test gap) — RESOLVED in rework
FIX: CHANGELOG wording imprecise (surviving, LOW)
FIX: dead `mkdir(exist_ok=True)` guard (surviving, LOW)
KNOWN: element-type validation inside containers, nested submodule snapshots, key-list triplication, narrow `True`-version case — all out of scope per PRD

**00029-malformed-snapshot-passes-compare-v1-c1 (delta, scoped to rework commit 8937b42)**
FIX (MEDIUM): `untracked_fingerprints` wrong-type case cannot fail as written (membership check alone rejects it) — surviving, not reworked (Medium/Low, lane does not open a second round)
FIX (MEDIUM): `untracked_fingerprints`-missing-entry case moved to a test the card gate's `-k` filter does not select — surviving
FIX (LOW): no wrong-type case feeds a list where `refs` belongs — surviving
FIX (LOW): CHANGELOG wording differs from PRD Must-have text — surviving
FIX (LOW): dead `mkdir(exist_ok=True)` guard in four test functions — surviving
D1-D5: pass

## Bob

**00029-malformed-snapshot-passes-compare-v1-c1**
[BOB] 🟠 `_load` checks only presence for 10 required fields — RESOLVED in rework (commit 8937b42)
[BOB] 🟡 `untracked` list containing non-string entries raises TypeError — surviving (LOW, not reworked)
[BOB] 🟡 Fingerprint test covers missing entry but not dict-type check — surviving (LOW)
[BOB] 🟡 Test fixture directory recreated each loop iteration — surviving (LOW, style nit)

R1: fail(cycle1)->resolved, R2: pass, R3: pass, R4: pass, R6: pass, R7: fail(cycle1)->resolved, R8: pass, R9: fail(cycle1)->resolved, R10: fail(cycle1)->resolved, R11: pass, R12: pass, R13: pass
D1: pass, D2: pass, D3: pass, D4: pass, D5: pass

## Carl

**00029-malformed-snapshot-passes-compare-v1-c1**
[CARL] 🟠 Top-level snapshot keys not checked against their required types — RESOLVED in rework (commit 8937b42)
[CARL] 🟡 Replace fragmented isinstance checks with a type-mapping — adopted as part of the rework fix
[CARL] 🟡 test_target_snapshot.py exceeds 800-line guideline — surviving (LOW, pre-existing growth, not reworked)

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: fail(cycle1)->resolved, R8: pass, R9: fail(cycle1)->resolved, R10: pass, R11: pass, R12: pass, R13: fail (file-size guideline, surviving LOW)

Verdict: 5 findings
Tests: 282 passed, 0 failed, 2 skipped (fast-track batch suite)
codex_rung_guard: not fired
