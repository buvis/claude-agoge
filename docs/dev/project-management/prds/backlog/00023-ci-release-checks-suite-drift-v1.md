---
lane: solo
design: skip
catchup: skip
model_tier_rationale: one flag and one comment; haiku acceptable, so default_model is omitted
---
# CI claims to run the same suite as release-checks but uses another Python, and release-checks hides the macOS skip

Source: agoge run 2026-11-08, finding 18 of 18 (LOW, verified, lane wendy), `docs/dev/project-management/audit-results/agoge-2026-11-08.md`.

## Problem

`.github/workflows/test.yml` says it runs the "Same suite as dev/bin/release-checks". CI runs `python -m pytest -q -rs` on Python 3.12. `dev/bin/release-checks` runs `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q` on whatever Python uv picks (3.15.2 locally), without `-rs`. A release cut on macOS passes with the non-UTF-8 test skipped, and the only trace of the skip is an `s` in the progress line.

## Solution

Add `-rs` to the pytest command in `dev/bin/release-checks`. Reword the comment at the top of `.github/workflows/test.yml` from "Same suite as dev/bin/release-checks" to "Same tests as dev/bin/release-checks (interpreter may differ)".

## Requirements

### Must have
- `dev/bin/release-checks` output lists each skip with its reason.
- The CI comment no longer claims the same suite.

### Nice to have
- None.

## Implementation

### Module: dev-tooling
- **Location**: `dev/bin/release-checks`, `.github/workflows/test.yml`
- **Responsibility**: make the release gate show skips and stop the CI comment overclaiming.
- **Exports**: none
- **Risk**: the interpreter split stays. Dev-tooling change, no CHANGELOG entry required.

### Dependencies
- dev-tooling: No dependencies (foundation)

## Test Strategy

Run `dev/bin/release-checks` on macOS and confirm the summary has a `SKIPPED` line whose reason contains `filesystem rejects non-UTF-8 names`. Do not pin the line number or the skip count; other PRDs in this batch add tests and macOS skips. Reproduction from the run:

```
CI: python -m pip install pytest; python -m pytest -q -rs on CPython (3.12.16) (ubuntu) and (3.12.10) (macos)
release-checks: uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q (no -rs), resolves to 3.15.2, pytest 9.2.0
no .python-version or pyproject.toml pins the interpreter
```

## Tasks

### Phase 0: Fix
- [ ] Add `-rs` to release-checks; reword the CI comment - Acceptance: `rg -n "pytest -q -rs" dev/bin/release-checks` hits; `rg -n "Same suite as" .github/workflows/test.yml` exits 1; on macOS, `dev/bin/release-checks` output contains `SKIPPED` and `filesystem rejects non-UTF-8 names`.

## Success Criteria

- release-checks prints the skip reason and passes.
