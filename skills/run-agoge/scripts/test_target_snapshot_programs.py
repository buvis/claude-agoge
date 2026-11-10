"""Target-configured programs (filters, fsmonitor) that snapshot and compare must never run."""
import json
import os
import shlex
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

import target_snapshot
from snapshot_fixtures import (
    _add_submodule, _assert_exit2, _assert_scratch_ignored, _build_target, _compare,
    _git, _git_dir_state, _pair_env, _run, _snap,
)


def _marker(tmp_path, name="marker.sh"):
    """Write an executable marker script; return (script, log).

    The script appends one line naming its argv to the log and then copies
    stdin to stdout, so it is also a usable (identity) clean filter. It lives
    under `tmp_path`, never inside the target repo.
    """
    script = tmp_path / name
    log = tmp_path / f"{name}.log"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "ran: $*" >> {shlex.quote(str(log))}\n'
        "exec cat\n"
    )
    script.chmod(0o755)
    return script, log


def _driver(shape="plain"):
    """Mint a filter-driver name that no implementation can know in advance.

    A module that ships a literal table of driver names and discovers nothing
    neutralizes only the names its author saw. Every fixture below therefore
    names its driver at run time. The shapes keep the characters that make a
    name hard to round trip through a config key and an environment pair - an
    `=`, a dot, a space - and compose them with the random part.
    """
    tag = uuid4().hex[:8]
    return {
        "plain": f"drv-{tag}",
        "equals": f"a={tag}",
        "dots": f"dots.{tag}.name",
        "space": f"has {tag}",
    }[shape]


def _configure_filter(target, env, scope_args, driver, program, kind="clean"):
    """Map `*.txt` to `driver`, then point `filter.<driver>.<kind>` at `program`.

    The `.gitattributes` is committed before the config is set, so no filter
    runs while the fixture is being built.
    """
    (target / ".gitattributes").write_text(f"*.txt filter={driver}\n")
    _git(target, env, "add", ".gitattributes")
    _git(target, env, "commit", "-q", "-m", "map *.txt to a filter")
    _git(target, env, "config", *scope_args, f"filter.{driver}.{kind}", str(program))
    _git(target, env, "config", *scope_args, f"filter.{driver}.required", "true")


def _assert_program_ran(repo, env, log, subject, fails=False):
    """Positive control: a bare `git status` in `repo` must run its program.

    Without it an inert fixture - a wrong scope flag, a non-matching
    includeIf - would make a "never ran" assertion pass vacuously. The log is
    removed afterwards, so the assertions that follow start from no log.

    `fails=True` is for a process filter: the marker cannot speak git's
    long-running filter protocol, so git fails - but only after launching it,
    which is what the log line proves.
    """
    if fails:
        with pytest.raises(subprocess.CalledProcessError):
            _git(repo, env, "status", "--porcelain")
    else:
        _git(repo, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        f"fixture is inert: {subject} never ran"
    )
    log.unlink()


def _capture_untouched(repo, env, subject):
    """Capture `repo`'s own config bytes and `.git` state.

    Returns an asserter: calling it with the command's name re-reads both and
    fails if either moved, which is the promise that nothing is ever written
    inside <repo>. A submodule's `.git` is a file, so its real config is
    located with `rev-parse` instead of assumed at `<repo>/.git/config`.
    """
    config = Path(_git(repo, env, "rev-parse", "--absolute-git-dir")) / "config"
    config_before = config.read_bytes()
    state_before = _git_dir_state(repo)

    def assert_untouched(command):
        assert config.read_bytes() == config_before, (
            f"{command} rewrote {subject}'s own config to disable its program"
        )
        assert _git_dir_state(repo) == state_before, (
            f"{command} wrote inside {subject}'s .git"
        )

    return assert_untouched


def _assert_submodule_head(snapshot_path, head):
    """The snapshot must record the submodule's own HEAD commit.

    Never visiting the submodule at all would silence its program too, so the
    snapshot has to prove the submodule was really traversed.
    """
    submodules = json.loads(snapshot_path.read_text())["submodules"]
    assert submodules["sub"]["head"]["commit"] == head, (
        f"the snapshot does not record the submodule's own state: {submodules}"
    )


def test_snapshot_does_not_run_fsmonitor(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path, name="fsmonitor.sh")
    _git(target, env, "config", "--local", "core.fsmonitor", str(script))

    # Positive control first: a bare `git status` must really run the hook.
    _assert_program_ran(target, env, log, "the target's core.fsmonitor")

    # The hook must be disabled through the module's own command-scope
    # configuration, never by rewriting the target's config: the module
    # promises nothing is ever written inside <repo>.
    assert_untouched = _capture_untouched(target, env, "the target")

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the target's fsmonitor hook: {log.read_text()!r}"
    )
    assert_untouched("snapshot")
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the target's fsmonitor hook: {log.read_text()!r}"
    )
    assert_untouched("compare")
    assert code == 0, report


def test_snapshot_does_not_run_clean_filter(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    driver = _driver()
    _configure_filter(target, env, ["--local"], driver, script)
    # A same-size edit with a newer mtime: git cannot tell from stat alone
    # whether the content changed, so it runs the clean filter to find out.
    notes = target / "notes.txt"
    assert notes.read_bytes() == b"notes v0\n"
    notes.write_bytes(b"notes v1\n")

    # Positive control first, as above.
    _assert_program_ran(target, env, log, "the target's clean filter")

    # The driver must be disabled through the module's own command-scope
    # configuration. Rewriting the target's config would silence the marker
    # too, and would break the promise that nothing is written inside <repo>.
    assert_untouched = _capture_untouched(target, env, "the target")

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the target's clean filter: {log.read_text()!r}"
    )
    assert_untouched("snapshot")
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the target's clean filter: {log.read_text()!r}"
    )
    assert_untouched("compare")
    assert code == 0, report


# One setup per configuration source. Each takes the freshly built target and
# its environment, declares a `kind` (clean or process) filter for `driver`
# through its own scope,
# and returns the environment the snapshot must run with plus the repository
# whose config now declares the driver (the submodule, for the last one).
def _source_local(tmp_path, target, env, driver, script, kind):
    _configure_filter(target, env, ["--local"], driver, script, kind)
    return env, target


def _source_global(tmp_path, target, env, driver, script, kind):
    # TEST_ENV pins GIT_CONFIG_GLOBAL at /dev/null; point it at a real file so
    # `git config --global` has somewhere to write.
    env = {**env, "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig-global")}
    _configure_filter(target, env, ["--global"], driver, script, kind)
    return env, target


def _source_include_path(tmp_path, target, env, driver, script, kind):
    included = tmp_path / "included.cfg"
    _configure_filter(target, env, ["--file", str(included)], driver, script, kind)
    _git(target, env, "config", "--local", "include.path", str(included))
    return env, target


def _source_include_if(tmp_path, target, env, driver, script, kind):
    included = tmp_path / "conditional.cfg"
    _configure_filter(target, env, ["--file", str(included)], driver, script, kind)
    # Build the gitdir: pattern from the resolved path. git matches the
    # unresolved gitdir and then retries against the realpath, so both forms
    # work here, but the realpath is the deterministic one: on macOS pytest's
    # tmp_path sits under /var/folders, which resolves to /private/var/folders.
    real = os.path.realpath(str(target))
    _git(target, env, "config", "--local", f"includeIf.gitdir:{real}/.path", str(included))
    return env, target


def _source_worktree(tmp_path, target, env, driver, script, kind):
    _git(target, env, "config", "--local", "extensions.worktreeConfig", "true")
    _configure_filter(target, env, ["--worktree"], driver, script, kind)
    return env, target


def _source_submodule(tmp_path, target, env, driver, script, kind):
    sub = _add_submodule(tmp_path, target, env)
    _configure_filter(sub, env, ["--local"], driver, script, kind)
    return env, sub


_FILTER_SOURCES = {
    "local": _source_local,
    "global": _source_global,
    "include-path": _source_include_path,
    "include-if": _source_include_if,
    "worktree": _source_worktree,
    "submodule": _source_submodule,
}


@pytest.mark.parametrize("kind", ["clean", "process"])
@pytest.mark.parametrize("source", list(_FILTER_SOURCES))
def test_snapshot_does_not_run_filter_from_any_source(tmp_path, source, kind):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    driver = _driver()
    env, declaring = _FILTER_SOURCES[source](tmp_path, target, env, driver, script, kind)
    # Same-size edit with a newer mtime, so git must run the filter to
    # decide whether the content changed.
    (declaring / "notes.txt").write_bytes(b"notes v1\n")

    # Positive control first, in the repository that declares the driver: an
    # inert fixture (wrong scope flag, non-matching includeIf) would otherwise
    # make the assertions below pass vacuously.
    _assert_program_ran(
        declaring, env, log, f"the {source} {kind} filter", fails=kind == "process",
    )

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the {source} {kind} filter: {log.read_text()!r}"
    )
    if source == "submodule":
        # Not running the submodule's driver because the submodule was never
        # visited is not a pass: the snapshot must carry its state.
        _assert_submodule_head(before, _git(declaring, env, "rev-parse", "HEAD"))
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the {source} {kind} filter: {log.read_text()!r}"
    )
    assert code == 0, report


@pytest.mark.parametrize("shape", ["plain", "equals", "dots"])
def test_snapshot_does_not_run_clean_filter_named(tmp_path, shape):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    driver = _driver(shape)
    _configure_filter(target, env, ["--local"], driver, script)
    (target / "notes.txt").write_bytes(b"notes v1\n")

    # Positive control first: the marker must fire for this exact driver name,
    # which is what proves the override has to round trip the name.
    _assert_program_ran(target, env, log, f"the clean filter named {driver!r}")

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the clean filter named {driver!r}: {log.read_text()!r}"
    )
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the clean filter named {driver!r}: {log.read_text()!r}"
    )
    assert code == 0, report


def test_snapshot_handles_clean_filter_named_with_a_space(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    driver = _driver("space")
    _configure_filter(target, env, ["--local"], driver, script)
    (target / "notes.txt").write_bytes(b"notes v1\n")

    # This name cannot have a marker control. A .gitattributes value ends at
    # the first whitespace, so `*.txt filter=has space` sets the attribute to
    # `has` and git never reaches the space-named driver; measured on git
    # 2.56.0, `filter=has\ space` yields `has\` and `filter='has space'` is
    # rejected as an invalid attribute name. The controls that do exist: the
    # key really is set under the exact name, and the discovery command the
    # module relies on sees it.
    assert _git(target, env, "check-attr", "filter", "--", "notes.txt").endswith(": has")
    names = _git(
        target, env, "config", "--includes", "--name-only",
        "--get-regexp", r"^filter\..*\.(clean|process|required)$",
    )
    assert f"filter.{driver}.clean" in names.splitlines()

    # No marker can fire for this name, so "exit 0 and no log" alone would
    # also pass for a module that silently skips every name it cannot print.
    # Bind to intent instead: ask git, through the module's own single git
    # entry point, what this driver's effective configuration is. Whatever
    # `_git` adds to an invocation is what every snapshot command sees, so an
    # empty `clean`, an empty `process` and a non-required driver here mean
    # the program can no longer run.
    for key, allowed in (("clean", ("",)), ("process", ("",)), ("required", ("", "false"))):
        probe = target_snapshot._git(
            str(target), "config", "--get", f"filter.{driver}.{key}", allow_fail=True,
        )
        value = probe.stdout.decode(errors="replace").strip()
        assert value in allowed, (
            f"the module's own git environment leaves filter.{driver}.{key}={value!r} "
            f"in force, so a driver named with a space is never disabled"
        )

    before = _snap(tmp_path, target, env)
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"the clean filter named {driver!r} ran: {log.read_text()!r}"
    )
    assert code == 0, report


def test_snapshot_does_not_run_required_process_filter(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path, name="process.sh")
    driver = _driver()
    (target / ".gitattributes").write_text(f"*.txt filter={driver}\n")
    _git(target, env, "add", ".gitattributes")
    _git(target, env, "commit", "-q", "-m", "map *.txt to a process filter")
    _git(target, env, "config", "--local", f"filter.{driver}.process", str(script))
    _git(target, env, "config", "--local", f"filter.{driver}.required", "true")
    (target / "notes.txt").write_bytes(b"notes v1\n")

    # Positive control: the marker cannot speak git's long-running filter
    # protocol, so git fails - but only after launching it, which is what the
    # log line proves.
    _assert_program_ran(
        target, env, log, "the target's process filter", fails=True,
    )

    # `_snap` asserts the snapshot exited 0, which is the other half of the
    # promise here: a `required` driver whose command is disabled must not make
    # status fail.
    out = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the target's process filter: {log.read_text()!r}"
    )
    code, report = _compare(tmp_path, target, out, env)
    assert not log.exists(), (
        f"compare ran the target's process filter: {log.read_text()!r}"
    )
    assert code == 0, report


def test_snapshot_does_not_run_submodule_only_clean_filter(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    sub_script, sub_log = _marker(tmp_path, name="sub-filter.sh")
    parent_script, parent_log = _marker(tmp_path, name="parent-filter.sh")
    sub_driver, parent_driver = _driver(), _driver()
    _configure_filter(sub, env, ["--local"], sub_driver, sub_script)
    _configure_filter(target, env, ["--local"], parent_driver, parent_script)
    (sub / "notes.txt").write_bytes(b"notes v1\n")
    (target / "notes.txt").write_bytes(b"notes v1\n")

    # Positive control, in the submodule itself: its own driver fires there,
    # and the parent's driver does not - a submodule reads neither its
    # parent's config nor its parent's attributes.
    _assert_program_ran(sub, env, sub_log, "the submodule's own clean filter")
    assert not parent_log.exists(), (
        f"git applied the parent's filter inside the submodule: {parent_log.read_text()!r}"
    )
    _assert_program_ran(target, env, parent_log, "the parent's own clean filter")
    # That status recursed into the submodule and ran its driver there again.
    sub_log.unlink(missing_ok=True)

    # Both drivers must be disabled through the module's own command-scope
    # configuration, in the parent and in the submodule alike, without a byte
    # written inside either repository.
    sub_head = _git(sub, env, "rev-parse", "HEAD")
    assert_sub_untouched = _capture_untouched(sub, env, "the submodule")
    assert_parent_untouched = _capture_untouched(target, env, "the parent")

    before = _snap(tmp_path, target, env)
    assert not sub_log.exists(), (
        f"snapshot ran the submodule's clean filter: {sub_log.read_text()!r}"
    )
    assert not parent_log.exists(), (
        f"snapshot ran the parent's clean filter: {parent_log.read_text()!r}"
    )
    _assert_submodule_head(before, sub_head)
    assert_sub_untouched("snapshot")
    assert_parent_untouched("snapshot")
    code, report = _compare(tmp_path, target, before, env)
    assert not sub_log.exists(), (
        f"compare ran the submodule's clean filter: {sub_log.read_text()!r}"
    )
    assert not parent_log.exists(), (
        f"compare ran the parent's clean filter: {parent_log.read_text()!r}"
    )
    assert_sub_untouched("compare")
    assert_parent_untouched("compare")
    assert code == 0, report


def test_snapshot_does_not_run_submodule_only_fsmonitor(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    script, log = _marker(tmp_path, name="sub-fsmonitor.sh")
    _git(sub, env, "config", "--local", "core.fsmonitor", str(script))

    # Positive control: command-scope config is process-wide, so the
    # submodule's hook fires during the PARENT's own status, not only during
    # the recursion into the submodule.
    _assert_program_ran(target, env, log, "the submodule's core.fsmonitor")

    sub_head = _git(sub, env, "rev-parse", "HEAD")
    assert_sub_untouched = _capture_untouched(sub, env, "the submodule")

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the submodule's fsmonitor hook: {log.read_text()!r}"
    )
    _assert_submodule_head(before, sub_head)
    assert_sub_untouched("snapshot")
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the submodule's fsmonitor hook: {log.read_text()!r}"
    )
    assert_sub_untouched("compare")
    assert code == 0, report


def test_snapshot_does_not_run_inherited_command_scope_filter(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    _git(sub, env, "commit", "-q", "--allow-empty", "-m", "sub work")
    script, log = _marker(tmp_path)
    driver = _driver()
    (target / ".gitattributes").write_text(f"*.txt filter={driver}\n")
    _git(target, env, "add", ".gitattributes")
    _git(target, env, "commit", "-q", "-m", "map *.txt to a filter")
    (target / "notes.txt").write_bytes(b"notes v1\n")
    (target / "scratch.txt").write_text("scratch\n")
    excludes = tmp_path / "excludes"
    excludes.write_text("scratch.txt\n")

    # Baseline with no inherited pair at all: the dirty submodule shows up in
    # `dirty`, and scratch.txt counts as untracked rather than ignored. Both
    # effects below are therefore the pairs' doing, not the fixture's.
    baseline = json.loads(_snap(tmp_path, target, env, name="baseline.json").read_text())
    assert "sub" in baseline["dirty"]
    assert "scratch.txt" in baseline["untracked"]

    # The driver lives nowhere in the target's config: the caller's own
    # command-scope environment declares it, between two harmless pairs. The
    # module must override the one hostile key and keep the rest; throwing
    # away the caller's inherited configuration is not a way out.
    hijack_env = _pair_env(
        env,
        ("diff.ignoreSubmodules", "all"),
        (f"filter.{driver}.clean", script),
        ("core.excludesFile", excludes),
    )

    _assert_program_ran(target, hijack_env, log, f"the inherited filter.{driver}.clean")

    before = _snap(tmp_path, target, hijack_env)
    assert not log.exists(), (
        f"snapshot ran an inherited command-scope filter: {log.read_text()!r}"
    )
    snapshot = json.loads(before.read_text())
    assert "sub" not in snapshot["dirty"], (
        f"the inherited diff.ignoreSubmodules=all was dropped: {snapshot['dirty']}"
    )
    _assert_scratch_ignored(snapshot, "the inherited core.excludesFile was dropped")
    code, report = _compare(tmp_path, target, before, hijack_env)
    assert not log.exists(), (
        f"compare ran an inherited command-scope filter: {log.read_text()!r}"
    )
    assert code == 0, report


def test_inherited_non_filter_config_pair_still_takes_effect(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    _git(sub, env, "commit", "-q", "--allow-empty", "-m", "sub work")

    # `diff.ignoreSubmodules=all` is observable through _dirty's own
    # `status --porcelain=v1 -z --untracked-files=no`: it suppresses the
    # ` M sub` entry the no-pair baseline records.
    baseline = _snap(tmp_path, target, env, name="baseline.json")
    assert "sub" in json.loads(baseline.read_text())["dirty"]

    pair_env = _pair_env(env, ("diff.ignoreSubmodules", "all"))
    with_pair = _snap(tmp_path, target, pair_env, name="with-pair.json")
    dirty = json.loads(with_pair.read_text())["dirty"]
    assert "sub" not in dirty, (
        f"the inherited diff.ignoreSubmodules=all was dropped: {dirty}"
    )


def test_unreadable_included_config_exits_2_and_runs_nothing(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    _configure_filter(target, env, ["--local"], _driver(), script)
    (target / "notes.txt").write_bytes(b"notes v1\n")

    unreadable = tmp_path / "unreadable.cfg"
    unreadable.write_text('[filter "zz"]\n\tclean = /bin/false\n')
    _git(target, env, "config", "--local", "include.path", str(unreadable))
    unreadable.chmod(0o000)
    if os.access(unreadable, os.R_OK):
        pytest.skip("this user can read a mode-000 file, so the include cannot fail")

    # Config discovery cannot run, which must fail closed to exit 2 with one
    # line - never exit 1, and never a silent "no filters configured".
    out = tmp_path / "snaps" / "before.json"
    out.parent.mkdir(exist_ok=True)
    result = _run(tmp_path, env, "snapshot", str(target), str(out))
    _assert_exit2(result)
    assert not out.exists()
    assert not log.exists(), (
        f"a git call ran the target's clean filter before failing: {log.read_text()!r}"
    )
    # Exit 2 alone cannot tell "discovery failed closed" from "the module
    # never discovers anything and git happened to die first", so pin the
    # reason to config discovery. git's own detail names the unreadable file
    # and never the word "config"; everything before the first quote is the
    # module's own reason, so the file path cannot satisfy this.
    reason = result.stderr.splitlines()[0].split("'")[0]
    assert "config" in reason.lower(), (
        f"the exit-2 reason does not name config discovery: {result.stderr!r}"
    )
