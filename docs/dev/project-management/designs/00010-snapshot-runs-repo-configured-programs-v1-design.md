# Design: target snapshot must not run programs the target's git config names

PRD: `docs/dev/project-management/prds/wip/00010-snapshot-runs-repo-configured-programs-v1.md`

## Architecture fit

`skills/run-agoge/scripts/target_snapshot.py` is the mechanical half of the
two-layer scratch defence (the prompt-level scratch contract is the other half).
It is stdlib-only and shells out to the `git` binary. Every git invocation in the
module goes through exactly one choke point, `_git` (line 65) - verified by
`rg "subprocess.run|\"git\"" target_snapshot.py`, whose only other hit is the
`restore` string built for the report, which is never executed. So the whole fix
lands inside that one function plus two small helpers beside it.

`_git` already carries the lineage of PRD 00012: it strips `_GIT_REPO_VARS`
(`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR`, `GIT_NAMESPACE`) from the
inherited environment so a caller cannot redirect the target. This design extends
the same doctrine - the inherited environment is untrusted, and so is the target
repo's own config - from "which repo" to "which programs".

The exit contract is unchanged and binding: 0 unchanged, 1 changed, 2 cannot run
with one `target_snapshot: <reason>` stderr line. A configuration-discovery
failure must reach exit 2 through the existing `Fail` exception, never exit 1.

## Module placement

Edits only; no new files.

| Path | Change |
|---|---|
| `skills/run-agoge/scripts/target_snapshot.py` | new module constants, new `_base_env`, `_config_env`, `_filter_overrides`, `_run_git`; `_git` rewritten to delegate; module docstring updated |
| `skills/run-agoge/scripts/test_target_snapshot.py` | new parameterized does-not-run suite plus positive controls |
| `CHANGELOG.md` | one `[Unreleased]` / `### Fixed` entry |

## Interfaces & contracts

New module-level constants, placed directly after `_GIT_REPO_VARS`:

```python
_GIT_CONFIG_COUNT_VARS = frozenset({"GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"})

_GIT_CONFIG_INDEXED_PREFIXES = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")

_STATIC_OVERRIDES: tuple[tuple[str, str], ...] = (
    ("core.fsmonitor", "false"),
)

_FILTER_PROPS = ("clean", "process", "required")

_FILTER_KEY_REGEX = r"^filter\..*\.(clean|process|required)$"

_filter_override_cache: dict[str, tuple[tuple[str, str], ...]] = {}
```

New functions, in this order, replacing the body of `_git`:

```python
def _base_env() -> dict[str, str]:
    """The inherited environment with every git repo and command-scope config
    variable removed.

    Drops `_GIT_REPO_VARS` (PRD 00012), `GIT_CONFIG_COUNT`,
    `GIT_CONFIG_PARAMETERS`, and every `GIT_CONFIG_KEY_<n>` /
    `GIT_CONFIG_VALUE_<n>`. Returns a new dict; `os.environ` is never mutated.
    """


def _inherited_config_pairs() -> tuple[tuple[str, str], ...]:
    """Inherited command-scope `(key, value)` pairs that are not filter keys.

    Reads `GIT_CONFIG_COUNT` from `os.environ` and returns the pairs at indices
    `0..count-1`, in index order, skipping any pair whose key matches
    `_FILTER_KEY_REGEX` case-insensitively on its first and last components and
    any index whose `GIT_CONFIG_KEY_<n>` is absent. A missing, empty or
    non-integer `GIT_CONFIG_COUNT`, or a negative one, yields `()`. A pair whose
    `GIT_CONFIG_VALUE_<n>` is absent is dropped together with its key, because
    git itself rejects that shape.
    """


def _config_env(overrides: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """`GIT_CONFIG_COUNT`/`KEY`/`VALUE` variables for one git invocation.

    Emits `_inherited_config_pairs()` first, then `overrides`, so the overrides
    sit at later indices and win (verified on git 2.56.0). `GIT_CONFIG_COUNT`
    is always set, to `len(pairs)`, even when that is `"0"`, so an inherited
    count can never leak through.
    """


def _run_git(
    repo: str,
    args: tuple[str, ...],
    overrides: tuple[tuple[str, str], ...],
    allow_fail: bool,
) -> subprocess.CompletedProcess:
    """Run one `git --no-optional-locks -C <repo> <args>` with `overrides`.

    The environment is `_base_env() | _config_env(overrides)`. Raises `Fail`
    on a non-zero exit unless `allow_fail`. This is the only `subprocess.run`
    in the module.
    """


def _filter_overrides(repo: str) -> tuple[tuple[str, str], ...]:
    """Config overrides that disable every filter driver effective in `repo`.

    Discovers effective filter keys with

        git config --includes --null --name-only --get-regexp
            ^filter\\..*\\.(clean|process|required)$

    run with `_STATIC_OVERRIDES` only (no scope flag, so local, global,
    system, worktree, included and matching conditional-include files all
    count). Output is split on NUL and decoded with `os.fsdecode`; each name is
    stripped of its `filter.` prefix and its final `.<prop>` suffix with
    `rsplit(".", 1)`, so a driver name containing `=`, spaces or dots survives
    whole. For each distinct driver name, in sorted order, yields

        (f"filter.{name}.clean", ""), (f"filter.{name}.process", ""),
        (f"filter.{name}.required", "false")

    Exit 1 (no matching key) yields `()`. Any other non-zero exit raises
    `Fail("git config filter discovery failed: <first stderr line>")`. Results
    are memoized in `_filter_override_cache` under `os.path.realpath(repo)`, so
    each repository - including each submodule, which has its own config -
    discovers independently and once.

    The result is the UNION of `repo`'s own discovered drivers and those of
    every initialized submodule, found recursively. This is required, not
    defensive: measured on git 2.56.0, a `filter.*.clean` declared ONLY in a
    submodule runs three times during the PARENT's `git status --porcelain`
    (the parent's submodule-dirtiness check runs status machinery inside the
    submodule), while the parent's own `git config` discovery cannot see that
    key at all. Per-repository discovery without the union therefore leaves the
    parent call running the submodule's program. Submodules are enumerated the
    way `take_snapshot` already does it - `ls-files --stage -z` entries starting
    `160000 ` whose `<path>/.git` exists on disk - through `_run_git` with
    `_STATIC_OVERRIDES` only, so the enumeration does not recurse into this
    function. An uninitialized submodule is skipped, as everywhere else.
    Disabling a driver a repository does not declare is harmless, so the union
    costs nothing but closes the parent-side path.
    """


def _git(repo: str, *args: str, allow_fail: bool = False) -> subprocess.CompletedProcess:
    """Unchanged signature and return value.

    Now equals
    `_run_git(repo, args, _STATIC_OVERRIDES + _filter_overrides(repo), allow_fail)`.
    """
```

**Config precedence, measured on git 2.56.0** (`/tmp/agoge-probe/probe2.sh`),
because two channels are now in play and the design depends on which wins:

- A command-line `-c` BEATS a `GIT_CONFIG_KEY_<n>` env pair for the same key.
  `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=zz.a GIT_CONFIG_VALUE_0=fromenv git -c zz.a=fromdashc config --get zz.a`
  prints `fromdashc`; `--get-all` prints `fromenv` then `fromdashc`, so `-c` is
  applied last and a single-valued read takes it.
- Within `GIT_CONFIG_COUNT`, the LATER index wins (the `filter.a=b` probe in
  `## Alternatives considered` item 2).

So `_dirty` KEEPS its `-c core.bigFileThreshold=1m` exactly as it is. That
setting is the peak-RSS guard PRD 00019 added, pinned by
`test_large_dirty_file_snapshot_peak_rss_under_48_mib`, and on the command line
it cannot be beaten by an inherited env pair at all. The filter and fsmonitor
overrides use the env transport because only it can express an `=`-containing
key; nothing needs both channels for one key.

Nothing else in the module changes shape: `_git`'s signature, its `Fail` message
format (`git <args[0]> failed: <detail>`), `VERSION` (stays `4`; the snapshot
JSON schema is untouched), and every exported behaviour stay as they are.

New test symbols in `test_target_snapshot.py`:

```python
def _marker(tmp_path, name="marker.sh") -> tuple[Path, Path]:
    """Write an executable marker script; return (script, log). The script
    appends one line naming its argv to the log and then copies stdin to
    stdout, so it is a usable clean filter."""


def _configure_filter(target, env, scope_args, driver, program) -> None:
    """Commit a `.gitattributes` mapping `*.txt` to `driver`, then set
    `filter.<driver>.clean` to `program` and `filter.<driver>.required` to true
    through `git config <scope_args>`."""


def test_snapshot_does_not_run_fsmonitor(tmp_path): ...
def test_snapshot_does_not_run_clean_filter(tmp_path): ...
```

plus the parameterized cases named in `## Test strategy outline`.

## Data flow

1. `main` -> `run` -> `_resolve_repo(repo_arg)` makes the first `_git` call.
2. `_git` asks `_filter_overrides(repo)`. On a cache miss that runs one
   `git config --get-regexp` through `_run_git` with the fsmonitor override
   only - config reading starts no filter and touches no index, so there is no
   recursion and no window where an unmitigated git call runs.
3. `_filter_overrides` returns the driver overrides; `_git` concatenates them
   after `_STATIC_OVERRIDES` and calls `_run_git`.
4. `_run_git` builds the environment: inherited non-filter command-scope pairs
   first, then fsmonitor, then the filter overrides. Later index wins, so a
   hostile inherited `filter.x.clean` is overwritten rather than merely ignored.
5. Every later call for the same repo hits the cache. `take_snapshot` recursion
   into a submodule passes the submodule's path, so step 2 repeats for that
   repository and discovers its own config - a filter declared only in the
   submodule is covered, and one declared only in the parent is not borrowed.
   **Correction, measured during task 2 (2026-11-10):** a submodule-only
   `filter.*.clean` ALSO runs during the PARENT's `git status` - the parent's
   submodule-dirtiness check runs status machinery inside the submodule, and the
   marker fired three times from `git -C parent status --porcelain`. The
   dispatch-2 review recorded the opposite and this section repeated it. The
   same is true of a submodule-only `core.fsmonitor`. Neither changes the
   design: command-scope config is process-wide, so `_STATIC_OVERRIDES` covers
   the parent-side fsmonitor path, and the parent's own discovery cannot see the
   submodule's filter keys, so per-repository discovery is still required - the
   parent call is simply covered by the submodule's own overrides only after the
   recursion reaches it, which is why BOTH paths are tested (items 6a and 6b).
6. A discovery failure raises `Fail` before any further git call, so `main`
   prints one line and returns 2.

## Reuse inventory

- `_GIT_REPO_VARS` + the env-filtering line in `_git` (`target_snapshot.py:66`)
  - the existing inherited-environment sanitization from PRD 00012. `_base_env`
  is its generalization and must keep stripping the same set; the new code adds
  to it rather than replacing it.
- `Fail` (`target_snapshot.py:55`) and `main`'s handler (line 347) - the
  one-line exit-2 contract. Discovery errors reuse it; no new exit path.
- `os.fsdecode` via `_text` (line 79) - the established "git output is
  filesystem bytes" rule. Discovery parses raw bytes and decodes per name the
  same way.
- `-c core.bigFileThreshold=1m` in `_dirty` (line 133) - the existing per-call
  config override, and a load-bearing one: it is the peak-RSS guard PRD 00019
  added, pinned by `_peak_rss` (`test_target_snapshot.py:77`) and
  `test_large_dirty_file_snapshot_peak_rss_under_48_mib`. Left on the command
  line unchanged: `-c` beats the env transport for the same key (measured, see
  `## Interfaces & contracts`), the two channels carry disjoint keys here, and
  moving it would be an unrelated edit.
- `TEST_ENV` / `_env_for` / `_build_target` / `_snap` / `_compare` /
  `_assert_exit2` (`test_target_snapshot.py:17-120`) - the whole fixture
  vocabulary the new tests build on. `TEST_ENV` already pins
  `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`, which is what makes
  a global-scope marker test possible (point `GIT_CONFIG_GLOBAL` at a real file
  instead).
- `test_inherited_git_dir_does_not_redirect_snapshot`
  (`test_target_snapshot.py:1055`) - the shape to copy for the inherited
  command-scope precedence test.
- Nothing found for a general config-neutralization helper. Greps tried, all
  over `skills/run-agoge/scripts/*.py`: `GIT_CONFIG`, `environ`, `_base_env`,
  `sanitiz`, `neutral`, `override`, `subprocess.run`, `"git"`, `fsmonitor`,
  `filter\.`, `def _git`. The `environ` hits are `allocate_prd_number.py:97`
  (its own env build, a different concern) and the test files' `TEST_ENV`. No
  shared helper exists and none is worth extracting for one call site.
  (`~/.claude/rules-library/rationalizations.md` was not consulted; the synonym
  sets used were my own: disable/neutralize/strip/sanitize/override x
  config/env/filter/fsmonitor.)

## Alternatives considered

1. **Command-line `-c` for every override.** Smallest diff: append
   `-c core.fsmonitor=false -c filter.<name>.clean=` to the argv. Rejected on
   evidence: `-c` takes one `key=value` word, so a driver named `a=b` is
   unrepresentable - git parses `filter.a=b.clean=` as key `filter.a` with
   value `b.clean=`. The PRD names equals-containing filter names as a
   must-have, and the parked branch's rejection (F12) was exactly this.
2. **Environment transport, chosen.** `GIT_CONFIG_COUNT`/`KEY_<n>`/`VALUE_<n>`
   keeps key and value in separate variables, so any byte except NUL survives
   in a name. Probed locally on git 2.56.0 (`/tmp/agoge-probe/probe.sh`):
   with `filter.a=b.clean` set in local config to a marker script, three
   `status` runs wrote three marker lines; with
   `GIT_CONFIG_COUNT=4` and an empty `GIT_CONFIG_VALUE` for
   `filter.a=b.clean`/`.process` plus `required=false`, `status` wrote no
   marker line and still reported `M f.txt`. Discovery with
   `--includes --null --name-only --get-regexp` listed `filter.a=b.clean` and
   `filter.a=b.required`. An inherited `filter.a=b.clean` at index 0 beaten by
   our empty value at index 1 also wrote no marker line, which pins the
   later-index-wins precedence this design relies on.
3. **Smallest version of the whole idea: disable fsmonitor only, and drop the
   filter half.** One constant, no discovery, no cache, no NUL parsing - maybe
   fifteen lines against roughly seventy. Rejected: the PRD's reproduction
   shows the clean filter firing after fsmonitor was unset, so half the
   demonstrated vector would survive and the docstring's "nothing runs in the
   target" claim would stay false. The extra size buys per-repository discovery
   (the only way to reach included, conditional-include and submodule-only
   drivers) and name fidelity for `=`/space/dot driver names.
4. **Replace `clean` with `cat` instead of emptying it.** Rejected outright by
   the PRD, and correctly: it still spawns a process, inherits whatever `cat`
   resolves to on `PATH`, and converts a security control into a dependency on
   an external binary.
5. **Preserve inherited command-scope config untouched.** Rejected as unsafe:
   an inherited `filter.x.clean` is as hostile as a repo-local one. Dropping
   all of it (the parked branch's shape) was rejected as too blunt - it would
   silently discard the operator's unrelated `-c` settings. The chosen middle
   re-emits inherited non-filter pairs in order and appends ours after them.

## Risks & edge cases

- **Scope.** This closes the two demonstrated vectors (fsmonitor and filter
  drivers). It does not and must not claim that every git-configured program is
  blocked: `core.pager`, `core.hooksPath` hooks, `diff.external`,
  `core.alternateRefsCommand`, `core.sshCommand` and credential helpers are
  either unreachable from the read-only commands this module runs or not
  covered. The module docstring must say "does not run the target's fsmonitor
  or clean/process filters", not "runs nothing".
- **Disabling a clean filter changes `status` output.** With git-lfs or any
  normalizing filter disabled, a file whose worktree bytes differ from the
  filtered blob reads as modified, so `dirty` can list more paths. Direction is
  safe (over-reporting a violation, never under-reporting) and the probe above
  shows it concretely. `test_untouched_target_compares_unchanged` must still
  pass unchanged for an ordinary repo with no filters configured, which the
  PRD requires as "snapshot output for an ordinary repo is unchanged".
- **A `required` filter that is now disabled.** `required=false` is set
  alongside, so `status` cannot fail the way it would with a required filter
  whose command is empty. Covered by an explicit test.
- **Driver name containing NUL** is impossible in a config key, so NUL remains
  a safe record separator.
- **A filter key with a value but no readable config file** (unreadable global
  config, a broken `include.path`): discovery exits non-zero with something
  other than 1, which fails closed to exit 2. That is deliberately stricter
  than today, where the same broken config would surface at the first real git
  call anyway.
- **Cache keyed on `realpath`.** Two paths to one repository share an entry,
  which is correct. The cache lives for one process only; `snapshot` and
  `compare` are separate invocations, so there is no cross-run staleness.
- **Uninitialized submodules** are unchanged: `take_snapshot` only recurses
  when `<path>/.git` exists, so no discovery runs for them.
- **Likely next changes after this PRD.** (a) Another config-driven vector gets
  reported (a pager or hook path) - it becomes one more entry in
  `_STATIC_OVERRIDES`, which already holds two keys and needs no rename.
  (b) A caller wants the snapshot to respect a specific filter (git-lfs) -
  that would need an opt-in flag and is deliberately boxed out here; the
  override is unconditional by design. (c) Another script in the pack needs the
  same hardening (`allocate_prd_number.py` has its own `subprocess.run`) - the
  helpers above are private to this module and would have to be extracted
  first; no shared module is created now because one call site does not justify
  one.

## Test strategy outline

All tests live in `test_target_snapshot.py` and run marker scripts written under
`tmp_path`, never inside the target repo. Every executable case asserts the
**positive control first** - the marker log must be non-empty when the mitigation
is bypassed - then asserts the log is absent after `snapshot` and `compare`.
The control bypass runs a bare `git status` in the target through the test's own
`_git` helper, so it proves the fixture really is executable without depending on
the parked branch.

**The control is per case, not per suite, and it is mandatory.** Items 3, 4 and 6
are the three tests that stand in for the three defects which parked the previous
attempt (omitted includes, equals-named bypass, omitted submodule filters), and a
negative-only assertion passes green when the fixture is inert - a wrong scope
flag, a `.gitattributes` naming a different driver, a non-matching `includeIf`.
So each parameterized case must, in its own body and in this order: (1) run a
bare `git status` in the repository whose config declares the driver and assert
the marker log is non-empty, (2) delete the log, (3) run `snapshot` and
`compare` and assert the log is still absent. A case that cannot make its control
fire is a broken fixture and must fail, not pass.

**Fixture trap for `includeIf "gitdir:"`.** Build the pattern from
`os.path.realpath(str(tmp_path))`, never from `tmp_path` itself. On macOS pytest's
`tmp_path` sits under `/var/folders/...`, whose real path is
`/private/var/folders/...`, and git matches `gitdir:` against the resolved path -
so a pattern built from the unresolved path silently never matches and the case
would pass vacuously. (The same trap applies to `/tmp`, which resolves to
`/private/tmp`.) The item-3 control above is what catches this if it is missed.

1. `test_snapshot_does_not_run_fsmonitor` - local `core.fsmonitor` set to the
   marker. Control: bare `git status` writes marker lines. Then `snapshot` and
   `compare` leave no marker file. Fails on unmodified `target_snapshot.py`.
2. `test_snapshot_does_not_run_clean_filter` - local `filter.trudy.clean`, a
   committed `.gitattributes` mapping `*.txt`, and a same-size edit with a newer
   mtime (the PRD's reproduction). Same control-then-assert shape.
3. Parameterized over configuration source, one case each: `--local`,
   `--global` (via a real `GIT_CONFIG_GLOBAL` file), an `include.path` file, a
   matching `includeIf "gitdir:"` conditional include, `--worktree` (with
   `extensions.worktreeConfig` enabled), and a submodule's own local config.
   Each case runs its own positive control first, per the preamble.
4. Parameterized over driver name: `trudy`, `a=b`, `has space`, `dots.in.name`.
   Each case runs its own positive control first: the marker must fire on a bare
   `git status` for that exact driver name, which is what proves the override
   round trip - not merely the absence of a marker afterwards.
5. `process` filter as well as `clean`, and a `required=true` driver, asserting
   exit 0/1 rather than exit 2 (the disabled filter must not make status fail).
6. Submodule isolation: a filter configured only in the submodule must not run
   during the recursive snapshot; a filter configured only in the parent must
   not be applied inside the submodule. The control fires the submodule-only
   driver with a bare `git -C <sub> status` first. One further case: only the
   submodule sets `core.fsmonitor`, and only the parent is snapshotted - the
   hook fires during the parent's own `git status` (measured: a submodule-only
   `core.fsmonitor` wrote the marker from the parent's status, and the
   `core.fsmonitor=false` override suppressed it), so this covers the
   command-scope path rather than the recursion.
7. Inherited command-scope precedence: `GIT_CONFIG_COUNT`/`KEY_0`/`VALUE_0`
   naming a marker as `filter.x.clean` in the caller's environment runs no
   marker, and in the same shape a benign inherited pair still takes effect,
   proving non-filter settings are preserved. The benign key must be one the
   module never sets itself AND whose effect is observable through the commands
   this module actually runs, asserted against a no-pair baseline. Measured
   working choice: `diff.ignoreSubmodules=all`, which suppresses ` M <sub>` from
   `_dirty`'s own `status --porcelain=v1 -z --untracked-files=no` (empty output
   versus ` M sub`); `core.excludesFile` is the second option, observable
   through `ls-files --others --exclude-standard`. Do NOT use
   `status.showUntrackedFiles` - `_dirty` passes `--untracked-files=no` on the
   command line, which beats it, so the assertion would be unfalsifiable
   (measured: output byte-identical with and without the pair). Do NOT use
   `core.fsmonitor`, which `_STATIC_OVERRIDES` deliberately overrides, or
   `core.bigFileThreshold`, which `_dirty` sets on the command line. A
   companion case asserts the opposite for an inherited
   `core.bigFileThreshold=4g`: the module's own `-c 1m` still wins, so the
   peak-RSS guard survives a hostile or careless caller.
8. Discovery failure: make the discovery call fail with something other than
   "no match" (an `include.path` pointing at an unreadable file) and assert
   exit 2 with one `target_snapshot: ` line via `_assert_exit2`, and that no
   marker ran.
9. Regression: `test_untouched_target_compares_unchanged` and the existing
   suite pass unchanged; `uv run --directory skills/run-agoge/scripts --with
   pytest python -m pytest -q` and `dev/bin/release-checks` are the gates.

Before committing, `git status` the two touched scripts and AST-compare against
HEAD if they are dirty with changes I did not make (project memory: a formatter
leaves AST-identical churn in exactly these files).

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 5, question 2

Blocker fixed: re-emitting inherited command-scope pairs let a caller's
`core.bigFileThreshold` beat the module's own `-c`, defeating PRD 00019's
peak-RSS guard, and test 7 enshrined it. `core.bigFileThreshold=1m` moved into
`_STATIC_OVERRIDES` (renamed from `_FSMONITOR_OVERRIDES`), the `## Reuse
inventory` rationale corrected, and test 7's benign key changed plus a companion
case pinning that the module's `1m` beats an inherited `4g`.

Recorded, not fixed:

- non-blocker: `_filter_overrides`'s documented `Fail` message is unreachable
  unless it calls `_run_git(..., allow_fail=True)` and classifies the exit code
  itself; the `allow_fail` value it passes is unstated in
  `## Interfaces & contracts`.
- non-blocker: disabling normalizing filters makes `_dirty` whole-file-hash
  every newly-` M` path. On a git-lfs target (the operator's own global config
  declares `filter.lfs.clean/process/required`) that is a real cost; correctness
  is unaffected because both snapshots disable filters alike. No timing or RSS
  case is named for it.
- non-blocker: no bound on the discovered driver count; a config with very many
  `filter.*` drivers pushes the environment past `E2BIG` and surfaces as
  `target_snapshot: unexpected OSError: ...` from the generic handler rather
  than a reasoned line.
- non-blocker: `_FILTER_PROPS` is dead - `_FILTER_KEY_REGEX` and the literal
  override triple already encode the same three names.
- non-blocker: the first failing git call for a bad repo path becomes discovery,
  so the exit-2 reason changes from `git rev-parse failed: ...` to
  `git config filter discovery failed: ...`; no existing test breaks
  (`_assert_exit2` checks only the prefix and the single line).
- question: test-strategy items 3, 4 and 6 restate the negative assertion
  without the positive control the preamble mandates, so a fixture whose config
  never took effect would pass vacuously. Verified trap: `includeIf "gitdir:"`
  does not match `/tmp/...` on macOS, where `/tmp` resolves to `/private/tmp`.
- question: item 1 does not name the fixture state under which an fsmonitor hook
  actually fires (committed index, `core.untrackedCache`, the hook's exit
  protocol), so the control could silently become a no-op.

dispatch 2: codex unavailable, Claude fallback

Codex ran but could not read a single file - every local reader failed with
`sandbox-exec: sandbox_apply: Operation not permitted` (nested sandbox), and it
returned one `question` saying so and no review. Per the skill's codex-outage
rule the dispatch degraded to a fresh Claude reviewer with the identical prompt.
The same sandbox failure hit this repo's PRD 00019 twice.

dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 6, question 1

Blockers fixed:

1. The env-vs-`-c` precedence claim I added after dispatch 1 was INVERTED, and
   the probe behind it was malformed (`-c 'filter.a=b.clean=x'` parses as key
   `filter.a`, so that `-c` never set a filter). Re-probed with a well-formed
   key on git 2.56.0: `GIT_CONFIG_KEY_0=zz.a VALUE_0=fromenv git -c zz.a=fromdashc config --get zz.a`
   prints `fromdashc`, and `--get-all` prints `fromenv` then `fromdashc`. So
   `-c` BEATS the env transport for the same key. Consequence: `_dirty` KEEPS
   its `-c core.bigFileThreshold=1m` (reverting the dispatch-1 fix, which was
   built on the inverted fact); `_STATIC_OVERRIDES` holds `core.fsmonitor`
   alone; `## Interfaces & contracts` now records both measured precedence
   rules, and `## Reuse inventory` and test 7 were corrected to match. The
   later-index-wins rule inside `GIT_CONFIG_COUNT` is unaffected and still
   verified.
2. Test-strategy items 3, 4 and 6 were negative-only, so the three defects that
   parked the previous attempt could recur and still pass green on an inert
   fixture. The preamble now makes the positive control per case and mandatory,
   spells out the three-step order, states that a case which cannot make its
   control fire must fail, and records the `includeIf "gitdir:"` realpath trap
   with the `/var/folders` -> `/private/var/folders` pair pytest actually hits
   (the dispatch-1 note named the wrong `/tmp` pair). Item 6 gained the
   submodule-only `core.fsmonitor` case, since command-scope config applies
   process-wide and that path reaches a submodule without the recursion.

Recorded, not fixed:

- non-blocker: `VERSION` stays `4` while the `dirty` map's VALUES change on a
  normalizing-filter target, so a v4 snapshot taken before this change and
  compared after it can report `tracked` violations (exit 1) on an untouched
  repo. `target_snapshot.py:306` gates on version alone, and
  `test_previous_version_snapshot_exits_2_with_one_line` treats VERSION as the
  compatibility gate. Argument against bumping: `snapshot` and `compare` are
  always a same-build pair in agoge's own use. Planning should settle it.
- non-blocker: `## Data flow` step 4 says a hostile inherited `filter.x.clean`
  is "overwritten", while `## Interfaces & contracts` has
  `_inherited_config_pairs` DROP it. Both are safe; the two sections describe
  different mechanisms and should be reconciled.
- non-blocker: `_base_env`'s docstring over-promises - it keeps
  `GIT_CONFIG_GLOBAL`/`SYSTEM`/`NOSYSTEM` (deliberately: `TEST_ENV` needs
  them), `GIT_ATTR_SOURCE` and `GIT_TRACE2*`. The config-file redirects are
  safe because discovery reads through the same environment, but an inherited
  `GIT_TRACE2=<path inside the target>` would write inside the target, which
  contradicts the module docstring's "nothing is ever written inside <repo>".
  Out of scope for this PRD; worth its own item.
- non-blocker: a submodule's own `core.fsmonitor` fires during the PARENT's
  `git status` (measured). The design is correct for a reason it does not
  state - command-scope config is process-wide. Item 6 now tests it; the
  `## Data flow` prose still attributes submodule coverage to the recursion
  alone.
- non-blocker (second report): `_filter_overrides` must pass
  `allow_fail=True` and classify the exit code itself, or its documented `Fail`
  message is unreachable. Measured codes: 1 = no match, 6 = invalid key
  pattern, 128 = malformed `include.path` target. An implementor must not read
  6 as "no match".
- non-blocker (second report): `_FILTER_PROPS` is dead.
- question: resolved in-doc by the item-2 fix above (the `includeIf` realpath
  pair).

dispatch 3: codex unavailable, Claude fallback

dispatch 3 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 3, question 1

This was the verification pass. It re-measured both dispatch-2 blocker fixes and
confirmed them: `-c` beats the env transport (`--get` -> `fromdashc`), the later
`GIT_CONFIG_COUNT` index wins, every named configuration source (local, a real
`GIT_CONFIG_GLOBAL`, `include.path`, `includeIf "gitdir:"`, `--worktree` with
`extensions.worktreeConfig`, a submodule's own config) is reachable by the single
unscoped discovery command, discovery itself runs no marker, the `=`-named driver
round trip neutralizes cleanly (` M f.txt`, exit 0, no marker), the exit-code
classification is right, the `realpath` cache collapses `repo_arg` and `real` to
one entry, and no other program vector (`core.pager`, `diff.external`, textconv,
`trailer.*.cmd`, `core.alternateRefsCommand`, hooks) is reachable from the
read-only commands this module runs.

Blocker fixed: item 7's "benign inherited pair" named `status.showUntrackedFiles`,
whose effect `_dirty`'s own `--untracked-files=no` beats, so the assertion could
not fail - the same vacuity class dispatch 2's blocker 2 closed, relocated into
the one case the marker-script control does not cover. Item 7 now requires a key
observable through this module's commands, asserted against a no-pair baseline,
and names the measured candidates (`diff.ignoreSubmodules=all`,
`core.excludesFile`) plus the keys to avoid.

Recorded, not fixed:

- non-blocker: the recorded `includeIf "gitdir:"` realpath trap is a false
  premise - git matches the unresolved gitdir and then retries against the
  realpath, so both path forms match (measured). The mandated action (build from
  `os.path.realpath`) still yields a working fixture and the per-case control
  catches an inert one, so nothing downstream is wrong; the paragraph's
  justification should be corrected at implementation time.
- non-blocker: the v4-across-builds hazard is live on this machine, not
  hypothetical - the operator's global config declares
  `filter.lfs.clean/process/required`, so every target discovers and disables
  lfs. The decision (bump `VERSION` to 5, or record that `snapshot`/`compare`
  are contractually a same-build pair) belongs in `## Risks & edge cases`, not
  in this log. Carried to planning.
- non-blocker: `_filter_overrides`'s `allow_fail=True` plumbing is still
  unstated and `_FILTER_PROPS` is still dead. Both are caught by test items 8
  and 9 (with `allow_fail=False` the ordinary exit-1 no-filter case would turn
  every repo into exit 2), so they are implementation details, not design gaps.
- question: `## Data flow` step 4 ("overwritten") and
  `_inherited_config_pairs` ("skipped, never re-emitted") describe two
  mechanisms for the same hostile inherited pair. Both hold - dropped at
  re-emission, and in any case beaten by the later-indexed override - and the
  prose should say so.

Confirmed by dispatch 2 against live probes, and worth keeping: the NUL +
`rsplit(".", 1)` parse round-trips `a=b`, `has space`, `dots.in.name`,
`endsdot.`, `foo.clean` and `Up` (case: first and last components lowercased,
subsection preserved); a newline is not representable in a subsection at all;
`git config --get-regexp` runs no filter and no fsmonitor even when expanding an
inherited `include.path`; a submodule-only filter does NOT leak into the
parent's status; and the command-scope overrides never appear in
`git config --local --list`, so they cannot inject a spurious `config`
violation.
