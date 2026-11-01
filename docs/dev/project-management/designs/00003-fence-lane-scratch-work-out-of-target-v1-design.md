# Design: Fence lane scratch work out of the target repo

## Architecture fit

Agoge's doctrine layer is prompt-carried, not code-carried (per the capsule's
Key Invariants): every rule a specialist must obey lives in
`skills/run-agoge/references/finding-contract.md` and is pasted verbatim into
dispatch prompts by `skills/run-agoge/SKILL.md`; the seven `agents/*.md`
charters hold no paths at all, only a pointer sentence. This PRD adds a fourth
contract (scratch) at that same layer: a new `## Scratch contract` section in
`finding-contract.md`, two paste-sites in `SKILL.md` (dispatch part 4, recon
item 7), and one `## Rules` bullet in each of the seven charters. No runtime
code changes — the fix is doctrine plus a regression test that runs the
doctrine's own bash as data to prove it stops the incident.

## Module placement

All edits, no new modules:

- `skills/run-agoge/references/finding-contract.md` — edit: replace the
  contracts-intro paragraph (A1), insert `## Scratch contract` before
  `## Report contract` (A2).
- `skills/run-agoge/SKILL.md` — edit: four pinpoint string replacements (A3,
  items 1-4).
- `skills/run-agoge/references/browser-playbook.md` — edit: one string
  replacement (A5), removing the browser-playbook's own now-superseded
  scratch-path guidance.
- `agents/walter.md`, `agents/heidi.md`, `agents/judy.md`, `agents/wendy.md`,
  `agents/peggy.md`, `agents/trudy.md`, `agents/olivia.md` — edit: append one
  `## Rules` bullet (A4) to each.
- `CHANGELOG.md` — edit: one `### Fixed` entry directly under `## [Unreleased]`
  — that section is currently empty (the file's most recent release, v0.2.0,
  already shipped and closed it), so this is the section's first entry, not
  an append after an existing `### Changed` list (A6).
- `skills/run-agoge/scripts/test_scratch_contract.py` — new file, five tests.

## Interfaces & contracts

**New file `skills/run-agoge/scripts/test_scratch_contract.py`**, pytest,
module-level constants and five test functions, run as

```
uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q test_scratch_contract.py [-k <filter>]
```

Repo-root paths are resolved as `Path(__file__).resolve().parents[3]` relative
to the test file (`skills/run-agoge/scripts/test_scratch_contract.py` →
`parents[0]`=`scripts`, `[1]`=`run-agoge`, `[2]`=`skills`, `[3]`=repo root) —
the same convention `test_agoge_registry.py` already uses in this directory
(confirm by reading its top-of-file constant before writing the new file so
the two files resolve identically).

```python
CONTRACT_PATH = REPO_ROOT / "skills/run-agoge/references/finding-contract.md"
SKILL_PATH = REPO_ROOT / "skills/run-agoge/SKILL.md"
LANE = "heidi"  # imported-by-filter token; test 2/3 use the literal lane dir name "heidi" for the mktemp-style subdir, matching the PRD's lane dir example
AGENT_FILES = [
    REPO_ROOT / "agents/walter.md",
    REPO_ROOT / "agents/heidi.md",
    REPO_ROOT / "agents/judy.md",
    REPO_ROOT / "agents/wendy.md",
    REPO_ROOT / "agents/peggy.md",
    REPO_ROOT / "agents/trudy.md",
    REPO_ROOT / "agents/olivia.md",
]
```

Test functions (pytest discovers by `test_` prefix; names chosen so `-k`
substring filters select exactly the PRD's five groups):

- `test_scratch_contract_mechanisms()` — reads `CONTRACT_PATH`, asserts
  (`in` checks, no regex needed) the text contains each of `"mktemp -d"`,
  `"set -eu"`, `"GIT_CEILING_DIRECTORIES"`, `"--git-dir"`, `"read-only"`.
- `test_scratch_contract_incident_preamble(tmp_path)` — builds the fixture
  below, extracts the bash block, runs it, asserts non-zero exit and
  before/after snapshot equality.
- `test_scratch_contract_incident_control(tmp_path)` — same fixture, runs A7
  alone (no preamble), asserts the target changed (the control that proves
  test 2 is not vacuously passing).
- `test_scratch_contract_charter()` — for each path in `AGENT_FILES`, reads
  the file, whitespace-normalizes (collapse runs of whitespace to one space,
  `.lower()`), asserts the substring `"scratch contract"` is present.
- `test_scratch_contract_prompt()` — reads `SKILL_PATH`. A single
  `"## Scratch contract" in content` check cannot distinguish "both A3 paste
  sites landed" from "only one did", since the same string appearing once
  anywhere would satisfy it twice over. Instead: split the file on the
  `### 3. Dispatch the armed specialists` and `## The recon prompt` headings
  to get each section's own text, then assert `` "## Scratch contract" `` is
  present in the dispatch section (specifically after the numbered list item
  that begins `4. The `` — the step-4 paragraph A3 item 3 edits) and again,
  separately, in the recon-prompt section (after the `6. The instruction`
  paragraph, where A3 item 4 inserts the new item 7). Two independent
  presence checks over two disjoint slices, not the same string checked
  twice over the whole file.

**Fixture builder, shared by the incident and control tests** (a module-level
helper, not itself a test, named `_build_incident_fixture(tmp_path)` so pytest
does not collect it):

```python
def _build_incident_fixture(tmp_path: Path) -> dict:
    """Returns {"target": Path, "lane_dir": Path, "snapshot": Callable[[], tuple]}."""
```

Steps, matching the PRD's Phase 0 task 1 bullet 2 exactly:

1. `target = tmp_path / "target"`; `git init` it (quiet), with the env below.
2. One commit (any file, any content) so `HEAD` exists.
3. `git update-ref refs/remotes/origin/master HEAD` in the target — the
   pre-existing remote-tracking ref the incident's `update-ref` later moves.
4. One untracked file in the target's worktree (any name/content) — the
   PRD's "and one untracked file" fixture element; it is part of the
   before/after snapshot, not touched by either path, so its presence alone
   proves the snapshot function distinguishes "untouched" from "touched".
5. `lane_dir = target / "docs/dev/tmp/agoge/heidi"`; `lane_dir.mkdir(parents=True)`.
6. `(lane_dir / "t7/roots/heidi-repo/.git/info").mkdir(parents=True)`;
   `(lane_dir / "t7/roots/heidi-repo/.git/description").write_text("...")` —
   the refused-init leftover: a `.git` holding only `description` and an
   empty `info/`, nothing else (no `HEAD`, no `objects/`, no `refs/`).

**Environment for every git invocation in the test module** (module-level
`os.environ` overlay via `monkeypatch.setenv`, or passed explicitly to
`subprocess.run(..., env=...)`): `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_NOSYSTEM=1`, `HOME=<tmp_path>`, `GIT_AUTHOR_NAME=Test User`,
`GIT_AUTHOR_EMAIL=test@test.local`, `GIT_COMMITTER_NAME=Test User`,
`GIT_COMMITTER_EMAIL=test@test.local` — the PRD's exact env block, spelled out
as the concrete variable names git reads for "author and committer identity
... set through git's environment variables".

**Snapshot function** (returns a tuple of three strings, compared with `==`
before/after):

```python
def _snapshot(target: Path, env: dict) -> tuple[str, str, str]:
    """(for-each-ref, ls-files --stage, status --porcelain) output, each run with -z where the PRD names it."""
```

Exact commands, run with `cwd=target` and the shared `env`:
`git --no-optional-locks for-each-ref`, `git ls-files --stage -z`,
`git status --porcelain=v1 -z`.

**Building the preamble block under test** (test 2 only): read `CONTRACT_PATH`
text, extract the fenced bash block that contains `GIT_CEILING_DIRECTORIES`
(the A2 block with `set -eu` / `SCRATCH=` / `export GIT_CEILING_DIRECTORIES`)
via a regex over triple-backtick fences, replace the literal substring
`<the path mktemp printed>` with `shlex.quote(str(lane_dir))`, then append the
A7 commands text (test 2 and 3 both need A7; test 2 prepends the extracted
preamble to it, test 3 runs A7 alone). Run via
`subprocess.run(["bash", "-c", script], env={**env, "LANE": str(lane_dir)}, cwd=target)`.
Assert `result.returncode != 0` for test 2 (preamble present — the ceiling or
the `set -eu` stops the sequence before any write reaches the target) and the
snapshot tuple identical before/after. For test 3 (A7 alone, no preamble),
assert `refs/heads/master` moved (compare `git rev-parse refs/heads/master`
before/after), `git tag --list v1.0.0` is non-empty after, and
`refs/remotes/origin/master` moved — proving the fixture is capable of
reproducing the incident when the doctrine is absent, so test 2 passing is
not vacuous.

**No new runtime symbols.** `GIT_CEILING_DIRECTORIES` and `SCRATCH` are shell
variable names inside the doctrine prose (A2) and the test's extracted bash,
not Python/CLI symbols this design introduces.

## Data flow

No runtime data flow changes. The only "flow" is doctrine propagation at
dispatch time, already diagrammed in `SKILL.md` step 3 (five-part prompt
assembly) and the recon prompt section — this PRD adds a sixth doctrine block
(scratch contract) to the same two paste points, part 4 of dispatch and item 7
of recon, unchanged otherwise. The test module's only "flow" is: read contract
text → extract fenced bash → execute as a subprocess inside a throwaway
`tmp_path` git fixture → diff snapshots. Nothing in this PRD executes against
a real agoge run; the test is self-contained.

## Reuse inventory

- `skills/run-agoge/references/finding-contract.md` already defines three
  contracts in the exact structural pattern (intro paragraph naming the count
  + a `## <Name> contract` heading) this PRD's A1/A2 extend to four — reuse
  the existing heading/paragraph convention verbatim, do not invent a new
  shape.
- `skills/run-agoge/scripts/test_agoge_registry.py` already resolves the repo
  root from `Path(__file__).resolve().parents[N]` in this same `scripts/`
  directory — reuse its exact `parents[N]` depth (read the file to confirm
  `N`, do not recompute by hand) so the new test file's root resolution
  matches the sibling convention instead of drifting.
- The incident's own four commands are already given verbatim in the PRD as
  Appendix A7 — reuse that text exactly as the control/incident fixture body,
  do not reconstruct it from the narrative.
- `docs/dev/project-management/prds/backlog/00005-check-run-leaves-target-unchanged-v1.md`
  (line 331) already uses the same `mktemp -d "${TMPDIR:-/tmp}/agoge-master.XXXXXX"`
  idiom this PRD's A2 names for lanes — confirms the naming convention
  (`agoge-<lane>.XXXXXX`) is already established elsewhere in this PRD's sibling
  and should not be re-derived differently here.
- Searches run (verb/noun synonyms): `rg -n "mktemp|GIT_CEILING_DIRECTORIES|--git-dir" -g '*.md'`
  (found the sibling PRD 00005 usage and the intake doc above — confirms the
  idiom, finds no existing *implementation* of a scratch contract, which is
  expected since this PRD is the one introducing it); `rg -n "## Rules" -A 8`
  across all seven `agents/*.md` (read every existing Rules section to confirm
  none already mentions a scratch contract and to see the existing bullet
  style/voice to match in A4); `rg -n "test_" skills/run-agoge/scripts/` (found
  the three existing sibling test files, read `test_agoge_registry.py`'s root
  resolution above as the pattern to reuse).

## Alternatives considered

1. **Chosen: prompt-only doctrine + a bash-executed regression test.** Matches
   the existing architecture (doctrine lives in prompts, not code) and the
   PRD's own acceptance criteria verbatim. Cost: one new test file with a
   fixture builder (more code than the doctrine text itself).
2. **Smallest-diff alternative: skip the regression test, land A1-A6 only.**
   Would satisfy "every dispatch and charter carries the contract" but not the
   PRD's primary Success Metric (the incident command sequence demonstrably
   fails with the preamble and demonstrably succeeds without it). Rejected:
   the PRD's first Success Metric line is exactly this test; skipping it
   leaves the doctrine unverified prose, which is the class of bug intake
   00003 already found once (a document nobody tests is a document nobody
   trusts).
3. **Enforce the contract in code** (e.g. a wrapper that rejects any lane git
   command not prefixed with `--git-dir`): rejected per the capsule's own
   stated boundary — specialists are prompt-driven personas with no code path
   of their own to instrument, and the Risks section of the PRD itself
   accepts that "doctrine cannot force behaviour", deferring real enforcement
   to PRD 00005's master-side snapshot/compare check. Building enforcement
   here would duplicate PRD 00005's own scope.

The chosen design is the PRD's own prescribed shape; its extra size over
option 2 buys the one thing option 2 cannot: proof the documented preamble
actually stops the incident, not just that the words exist.

## Risks & edge cases

- **`set -eu` trips on an expected non-zero step inside the extracted
  preamble+A7 script**: the contract text already tells lanes to capture an
  expected failure with `|| rc=$?`; the test's own script (preamble + A7) is
  not expected to contain such a step, so this only matters if a future edit
  to A2's text changes the extracted block's behavior. Mitigate by asserting
  the specific commands used in the fixture, not a general exit code.
- **Regex-extracting the fenced bash block from prose is brittle** if A2's
  markdown is reformatted later (e.g. more than one bash fence added to the
  section). Mitigate by anchoring the extraction regex to the fence that
  contains the literal string `GIT_CEILING_DIRECTORIES`, not "the Nth fence",
  so a reordering does not silently extract the wrong block.
- **Likely next change 1**: PRD 00005 (master's own scratch + comparison of
  the *target*, not the lane) will want to reuse this PRD's snapshot-function
  idea (`for-each-ref` / `ls-files --stage -z` / `status --porcelain=v1 -z`)
  against the real target rather than a synthetic `tmp_path` fixture — keep
  `_snapshot()`'s three-command list exactly as specified above so PRD 00005
  can copy it verbatim instead of re-deriving the command set.
- **Likely next change 2**: a future specialist beyond the current seven will
  need the same `## Rules` bullet (A4) appended — keep A4's wording generic
  ("Your prompt carries a scratch contract...") so it needs no per-agent
  customization when that happens.
- **Likely next change 3**: if `browser-playbook.md` gains more scratch-path
  mentions beyond the one A5 touches, a later editor should grep for
  `agoge-<lane>/` (A5's acceptance check) rather than re-reading the whole
  file, since that is exactly the check this PRD's Phase 0 task 3 already
  specifies.
- **Boxed-in by this design**: none identified beyond what the PRD's own Risks
  section already states (doctrine cannot force behaviour; `TMPDIR` inside the
  target is a reported-unverified case, not a test case here).

## Test strategy outline

- `test_scratch_contract.py`, 5 tests, run via
  `uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q test_scratch_contract.py`.
- Written first; acceptance is that it collects 5 tests and `mechanisms`,
  `incident ... preamble` (test 2), `charter`, and `prompt` fail (nothing
  written yet) while `incident ... control` (test 3) passes immediately
  (it does not depend on any edit this PRD makes — it only proves the fixture
  itself reproduces the incident).
- After A1/A2 land: `pytest -q test_scratch_contract.py -k "mechanisms or incident"`
  passes (both `mechanisms` and both incident tests); also re-run the
  pre-existing `test_sidecar_contract.py` to prove the A1 paragraph edit did
  not disturb anything it depends on.
- After A5 lands: `rg -F -c 'agoge-<lane>/' skills/run-agoge/references/browser-playbook.md`
  finds nothing (exit 1 from `rg`, or a `0`-vs-missing count — treat "no
  match" as pass), and `pytest -q test_agoge_registry.py -k playbook` passes.
- After A3 lands: `pytest -q test_scratch_contract.py -k prompt` and
  `pytest -q test_agoge_authorization_gate.py` pass (the latter proves the
  dispatch-part/recon-prompt edits did not disturb the existing authorization
  gate tests that also read `SKILL.md`).
- After A4 lands (all seven charters): `pytest -q test_scratch_contract.py -k charter`
  and `pytest -q test_agoge_registry.py` pass.
- After A6 lands: `rg -F -c 'scratch contract' CHANGELOG.md` prints `1`, and
  `pytest -q test_agoge_registry.py -k extraction_clean` passes.
- Final gate: `dev/bin/release-checks` passes (the PRD's own Phase 2 exit
  criterion).

## Review log

- non-blocker: "module-level monkeypatch.setenv" (Interfaces & contracts,
  Environment section) is not a coherent pytest idiom — `monkeypatch` is
  function-scoped. Not fixed now; the alternative already named in the same
  sentence (`os.environ` overlay / explicit `env=` kwarg) is the one to build;
  drop the monkeypatch option when implementing.
- question: the `LANE = "heidi"` constant's comment ("imported-by-filter
  token") is unclear — its only actual use is naming the fixture's lane-dir
  segment. Not fixed now; a planner should read it as "the lane name used in
  the fixture path", nothing else.
- non-blocker: the fenced-bash-block extraction keys on `GIT_CEILING_DIRECTORIES`
  being unique within `finding-contract.md`, not scoped to the Scratch
  contract section specifically. True today; folds into the already-noted
  regex-brittleness risk if the file grows a second such block later.
- non-blocker: `## Interfaces & contracts` fully specifies the new test file
  but describes the A1-A6 markdown edits only by label; their literal text
  lives in the PRD appendix, not duplicated here. Not fixed now — design docs
  in this workflow are always read alongside their PRD.
- question: `shlex.quote(str(lane_dir))` quotes `tmp_path` without an explicit
  `.resolve()`; `GIT_CEILING_DIRECTORIES` wants a symlink-free absolute path.
  Not fixed now — low risk, and the failure mode is self-correcting (a bad
  ceiling would let git climb to the real target, so the incident reproduces
  and the non-zero-exit assertion fails loudly rather than silently passing).
- question: `test_scratch_contract_prompt()`'s two-way split on
  `### 3. Dispatch the armed specialists` / `## The recon prompt` yields
  wider slices than the prose implies (sections 3-9, and recon+`## Notes`),
  not just the two named sections. Not fixed now — the two paste sites still
  land in disjoint halves either way.
- dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 2, question 1
- dispatch 2 (claude-fallback): codex sandbox could not read the repo
  (`sandbox_apply: Operation not permitted`); degraded to a fresh Claude
  reviewer. cardinal-sin 0, blocker 0, non-blocker 1, question 2
result: ok
