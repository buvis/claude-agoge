# Project Capsule: claude-agoge

Generated: 2026-11-01

## Key Invariants

- A finding only counts if `status: verified`; `unverified`/`mocked`/`skipped` never fail a run. The master audits claimed evidence, not the specialist's prose.
- Specialists are personas (`agents/*.md`) with no path knowledge of their own — every path, contract and rule reaches them through the dispatch prompt (`skills/run-agoge/SKILL.md`). Keeping agent files path-free is deliberate: it keeps personas portable across invocation sites.
- An unarmed lane never dispatches — recon (`olivia`) decides armed/unarmed per specialist and that decision is the cost gate.
- Trudy (security lane) refuses to run without an explicit authorization assertion in the profile's `## Pins and vetoes` section or a `--authorized <source>` flag on invocation; recon itself can never assert authorization.
- The profile's `## Pins and vetoes` section is human-owned; a profile refresh must copy it through byte-identically.

## Architecture Decisions

- Prompts, not code, carry the contracts (finding contract, and as of this PRD a scratch contract) — this is why `skills/run-agoge/references/finding-contract.md` is injected verbatim into both the dispatch and recon prompts rather than referenced by path.
- Intake docs under `docs/dev/project-management/intake/processed/` record the originating incident/idea per PRD; PRD 00003 and PRD 00005 both derive from `00003-heidi-scratch-git-guard/idea.md` (00003 = contract/doctrine, 00005 = master's own verification check of the target).

## Component Boundaries

- `skills/run-agoge/SKILL.md` — master orchestration: recon dispatch, specialist dispatch, dedup, one report. Owns all paths referenced by prompts.
- `skills/run-agoge/references/finding-contract.md` — the contract text pasted into prompts (finding contract today; scratch contract added by this PRD).
- `skills/run-agoge/references/browser-playbook.md` — browser-probe guidance, references the scratch root.
- `agents/{walter,heidi,judy,wendy,peggy,trudy,olivia}.md` — seven specialist charters, each with a `## Rules` section; each must point at the scratch contract once this PRD lands.
- `skills/run-agoge/scripts/test_*.py` — pytest suites run via `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q ...`.

## Active Work

### Batch 202611012029
- [x] 00003-fence-lane-scratch-work-out-of-target-v1.md (2 cycles)
- [x] 00005-check-run-leaves-target-unchanged-v1.md (2 cycles)

Observations: PRD 00003 added a `## Scratch contract` section to `finding-contract.md`, wired it into the dispatch/recon prompts in `SKILL.md`, pointed every agent charter at it, and added a regression test (`test_scratch_contract.py`) pinning the documented preamble against the 2026-10-25 incident (a lane's scratch `git init` failing inside the target, then committing/tagging/moving refs in the product itself). Cycle 1 rework fixed a recon-vs-contract instruction conflict and a loose test assertion; cycle 2 found only single-voice findings, discarded per the gate. PRD 00005 (the master's own snapshot/compare check of the target as a second line of defense, via a new `target_snapshot.py`) landed the same way: cycle 1 rework fixed three highs (missing `os.fsdecode`, a masked compare exit code from a combined bash block, and fingerprinting following symlinked parent directories outside the target). Cycle 2 reached the rework cap with one unresolved high (a residual strict `.decode()` in `_text`, no regression per `git blame`) and deferred it rather than stalling; it is recorded in the batch deferred JSON and a hold triage stub (`00006-triage-text-in-skills-run-agoge-scripts-target-v1.md`) was minted for it. Carl (Gemini) was unavailable for cycle 1 and stayed latched unavailable for the rest of the batch.

## Related context

engram not invoked this pass (no topic query run yet — PRD title and branch name are available but engram step was skipped during catchup to keep this pass fast; nothing suggests prior related work beyond the sibling PRD 00005 and the processed intake doc already read above).

## GitHub State

- 0 open issues, 0 open PRs.
- Active branches (14d): `origin`, `origin/master` only.
- No releases listed via `gh` (repo likely tags releases via git tags consumed by CHANGELOG/release tooling rather than GitHub Releases — `chore: release v0.2.0` is the latest commit).
- No failing workflow runs on master; no recent runs shown.

## Project Health

CI green, no open PRs/issues, single active branch. Backlog has at least PRD 00003 (this one) and PRD 00005 queued in `wip`/`backlog`.
