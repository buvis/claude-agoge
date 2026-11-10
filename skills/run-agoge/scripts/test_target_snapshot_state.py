"""Repository state beyond tracked content: gitdir, config, ignored paths, worktrees, submodules, fingerprints, large files."""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import target_snapshot
from snapshot_fixtures import (
    NOTES_V1, NOTES_V2, SCRIPT, _add_submodule, _assert_exit2, _assert_scratch_ignored,
    _build_target, _compare, _git, _pair_env, _run, _sha, _snap, _write_packed_refs,
)


_MAXRSS_RE = {
    "darwin": re.compile(r"^\s*(\d+)\s+maximum resident set size$", re.MULTILINE),
    "linux": re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)", re.MULTILINE),
}


def _peak_rss(tmp_path, env, *args, timeout=None):
    """Peak RSS, in bytes, of exactly one `target_snapshot.py` invocation.

    `resource.getrusage(RUSAGE_CHILDREN)` is cumulative over the whole test
    process's lifetime and cannot be reset, so it cannot isolate one call
    from another subprocess (e.g. the fixture's own `git add`) that ran
    earlier. `/usr/bin/time` reports the peak RSS of just the one process it
    wraps.
    """
    flag = "-l" if sys.platform == "darwin" else "-v"
    result = subprocess.run(
        ["/usr/bin/time", flag, sys.executable, str(SCRIPT), *args],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=timeout,
    )
    pattern = _MAXRSS_RE.get(sys.platform, _MAXRSS_RE["linux"])
    match = pattern.search(result.stderr)
    assert match, f"could not parse peak RSS from /usr/bin/time output:\n{result.stderr}"
    value = int(match.group(1))
    # ru_maxrss is bytes on Darwin, kilobytes on Linux; /usr/bin/time mirrors it.
    return value if sys.platform == "darwin" else value * 1024


def _commit_gitignore(target, env, *rules):
    (target / ".gitignore").write_text("".join(f"{rule}\n" for rule in rules))
    _git(target, env, "add", ".gitignore")
    _git(target, env, "commit", "-q", "-m", "ignore")


def test_overwritten_untracked_file_is_untracked_modified_violation(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "sub").mkdir()
    (target / "sub/keep.txt").write_text("k\n")
    _git(target, env, "add", "sub/keep.txt")
    _git(target, env, "commit", "-q", "-m", "sub")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside v1\n")
    (target / "link").symlink_to(outside)
    (target / "notes.md").write_bytes(NOTES_V1)
    # Nested, same size and same trailing bytes: only the first bytes change.
    (target / "sub/x.txt").write_bytes(b"head-v1" + b"y" * 30)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert set(snapshot["untracked_fingerprints"]) == {"link", "notes.md", "sub/x.txt"}
    (target / "notes.md").write_bytes(NOTES_V2)
    (target / "sub/x.txt").write_bytes(b"head-v2" + b"y" * 30)
    # The link's pointed-to file changes, the link itself does not.
    outside.write_text("outside v2\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert sorted((v["kind"], v["path"]) for v in report["violations"]) == [
        ("untracked-modified", "notes.md"),
        ("untracked-modified", "sub/x.txt"),
    ]
    assert report["touched"] == []

    (target / "link").unlink()
    (target / "link").symlink_to(tmp_path / "elsewhere.txt")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert sorted((v["kind"], v["path"]) for v in report["violations"]) == [
        ("untracked-modified", "link"),
        ("untracked-modified", "notes.md"),
        ("untracked-modified", "sub/x.txt"),
    ]


def test_deleted_ignored_file_is_ignored_removed_violation(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, ".env")
    (target / "sub").mkdir()
    (target / "sub/.gitignore").write_text("cache.bin\n")
    _git(target, env, "add", "sub/.gitignore")
    _git(target, env, "commit", "-q", "-m", "nested ignore")
    # Written before the snapshot: a later write would be a gitdir violation.
    (target / ".git/info").mkdir(exist_ok=True)
    (target / ".git/info/exclude").write_text("local.cfg\n")
    (target / ".env").write_text("SECRET=1\n")
    (target / "sub/cache.bin").write_text("c\n")
    (target / "local.cfg").write_text("l\n")
    before = _snap(tmp_path, target, env)
    (target / ".env").unlink()
    (target / "sub/cache.bin").unlink()
    (target / "local.cfg").unlink()
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert sorted((v["kind"], v["path"]) for v in report["violations"]) == [
        ("ignored-removed", ".env"),
        ("ignored-removed", "local.cfg"),
        ("ignored-removed", "sub/cache.bin"),
    ]


def test_deleted_ignored_dir_is_ignored_removed_violation(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "vault/")
    (target / "vault").mkdir()
    (target / "vault/a.txt").write_text("a\n")
    (target / "vault/b.txt").write_text("b\n")
    before = _snap(tmp_path, target, env)
    shutil.rmtree(target / "vault")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("ignored-removed", "vault/"),
        ("ignored-removed", "vault/a.txt"),
        ("ignored-removed", "vault/b.txt"),
    ]


def test_allow_exempts_untracked_modified_and_ignored_removed(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, ".env")
    (target / "notes.md").write_bytes(NOTES_V1)
    (target / ".env").write_text("SECRET=1\n")
    before = _snap(tmp_path, target, env)
    (target / "notes.md").write_bytes(NOTES_V2)
    (target / ".env").unlink()

    code, report = _compare(tmp_path, target, before, env, allow=("notes.md", ".env"))
    assert code == 0
    assert report["violations"] == []

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("untracked-modified", "notes.md"),
        ("ignored-removed", ".env"),
    ]


def test_deleted_child_of_ignored_dir_with_surviving_sibling_is_ignored_removed_violation(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "vault/")
    (target / "vault").mkdir()
    (target / "vault/a.txt").write_text("a\n")
    (target / "vault/b.txt").write_text("b\n")
    (target / "vault/sub").mkdir()
    (target / "vault/sub/deep.txt").write_text("d\n")
    before = _snap(tmp_path, target, env)
    (target / "vault/a.txt").unlink()
    (target / "vault/sub/deep.txt").unlink()
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert sorted((v["kind"], v["path"]) for v in report["violations"]) == [
        ("ignored-removed", "vault/a.txt"),
        ("ignored-removed", "vault/sub/deep.txt"),
    ]


def test_deleted_empty_ignored_dir_is_ignored_removed_violation(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "empty/")
    (target / "empty").mkdir()
    before = _snap(tmp_path, target, env)
    assert "empty/" in json.loads(before.read_text())["ignored"]
    (target / "empty").rmdir()
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{"kind": "ignored-removed", "path": "empty/"}]


def test_ignored_fifo_does_not_hang(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("os.mkfifo unavailable")
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "*.pipe")
    os.mkfifo(target / "x.pipe")
    os.mkfifo(target / "untracked.fifo")
    out = tmp_path / "snaps" / "fifo.json"
    out.parent.mkdir()
    result = _run(tmp_path, env, "snapshot", str(target), str(out), timeout=10)
    assert result.returncode == 0, result.stderr
    result = _run(tmp_path, env, "compare", str(target), str(out), timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["violations"] == []


def test_ignored_contents_are_never_read(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads mode-000 files")
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "secret.key", "vault/")
    (target / "secret.key").write_text("s\n")
    (target / "vault").mkdir()
    (target / "vault/a.txt").write_text("a\n")
    os.chmod(target / "secret.key", 0)
    try:
        before = _snap(tmp_path, target, env)
        code, report = _compare(tmp_path, target, before, env)
    finally:
        os.chmod(target / "secret.key", 0o600)
    assert code == 0
    assert report["violations"] == []
    snapshot = json.loads(before.read_text())
    assert isinstance(snapshot["ignored"], list)
    assert snapshot["ignored"] == ["secret.key", "vault/", "vault/a.txt"]
    assert set(snapshot["untracked_fingerprints"]) == set(snapshot["untracked"])
    assert set(snapshot) == {
        "version", "repo", "head", "refs", "config", "worktrees", "worktree_heads",
        "submodules", "index", "dirty", "untracked", "untracked_fingerprints",
        "ignored", "gitdir",
    }
    # The readable ignored file's content hash appears nowhere in the snapshot.
    assert _sha(b"a\n") not in before.read_text()


def test_allow_exempts_ignored_children_by_exact_path(tmp_path):
    target, env = _build_target(tmp_path)
    _commit_gitignore(target, env, "vault/", "empty/")
    (target / "vault").mkdir()
    (target / "vault/a.txt").write_text("a\n")
    (target / "vault/b.txt").write_text("b\n")
    (target / "empty").mkdir()
    (target / "sub").mkdir()
    (target / "sub/keep.txt").write_text("k\n")
    _git(target, env, "add", "sub/keep.txt")
    _git(target, env, "commit", "-q", "-m", "sub")
    (target / "a.txt").write_text("a\n")
    (target / "sub/a.txt").write_text("a\n")
    before = _snap(tmp_path, target, env)
    (target / "vault/a.txt").unlink()
    (target / "vault/b.txt").unlink()
    (target / "empty").rmdir()
    (target / "a.txt").write_text("changed\n")
    (target / "sub/a.txt").write_text("changed\n")
    code, report = _compare(
        tmp_path, target, before, env, allow=("vault/a.txt", "empty/", "a.txt", "sub/a.txt"),
    )
    assert code == 1
    assert report["violations"] == [{"kind": "ignored-removed", "path": "vault/b.txt"}]

    # Allowing `a.txt` exempts that exact path only, not other paths ending in it.
    code, report = _compare(tmp_path, target, before, env, allow=("a.txt",))
    assert code == 1
    assert sorted((v["kind"], v["path"]) for v in report["violations"]) == [
        ("ignored-removed", "empty/"),
        ("ignored-removed", "vault/a.txt"),
        ("ignored-removed", "vault/b.txt"),
        ("untracked-modified", "sub/a.txt"),
    ]


def test_added_remote_is_config_violation_without_url(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    url = "https://example.invalid/secret-repo-token.git"
    _git(target, env, "remote", "add", "upstream", url)
    result = _run(tmp_path, env, "compare", str(target), str(before))
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["violations"] == [{"kind": "config"}]
    assert url not in result.stdout + result.stderr
    assert "secret-repo-token" not in result.stdout + result.stderr


def test_changed_config_value_is_config_violation(tmp_path):
    target, env = _build_target(tmp_path)
    _git(target, env, "config", "user.email", "cy@example.test")
    before = _snap(tmp_path, target, env)
    # Same key, same number of entries, only the value differs.
    _git(target, env, "config", "user.email", "ada@example.test")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{"kind": "config"}]


def test_added_worktree_is_worktrees_violation(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    worktree = tmp_path / "wt"
    _git(target, env, "worktree", "add", "-q", "--detach", str(worktree), "HEAD")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = report["violations"]
    assert violation["kind"] == "worktrees"
    assert [os.path.realpath(p) for p in violation["before"]] == [
        os.path.realpath(target),
    ]
    assert sorted(os.path.realpath(p) for p in violation["after"]) == sorted(
        [os.path.realpath(target), os.path.realpath(worktree)]
    )


def test_swapped_worktree_is_worktrees_violation(tmp_path):
    target, env = _build_target(tmp_path)
    first = tmp_path / "wt-first"
    second = tmp_path / "wt-second"
    _git(target, env, "worktree", "add", "-q", "--detach", str(first), "HEAD")
    before = _snap(tmp_path, target, env)
    _git(target, env, "worktree", "remove", str(first))
    _git(target, env, "worktree", "add", "-q", "--detach", str(second), "HEAD")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = report["violations"]
    assert violation["kind"] == "worktrees"
    assert sorted(os.path.realpath(p) for p in violation["before"]) == sorted(
        [os.path.realpath(target), os.path.realpath(first)]
    )
    assert sorted(os.path.realpath(p) for p in violation["after"]) == sorted(
        [os.path.realpath(target), os.path.realpath(second)]
    )


def test_new_hook_is_gitdir_violation(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    hooks = target / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\necho pwned\n")
    hook.chmod(0o755)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert any(v["kind"] == "gitdir" for v in report["violations"])


def test_changed_info_exclude_is_gitdir_violation(tmp_path):
    target, env = _build_target(tmp_path)
    info = target / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "exclude").write_text("# seed\n")
    before = _snap(tmp_path, target, env)
    (info / "exclude").write_text("*.secret\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert any(v["kind"] == "gitdir" for v in report["violations"])


def test_changed_info_attributes_is_gitdir_violation(tmp_path):
    target, env = _build_target(tmp_path)
    info = target / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "attributes").write_text("# seed\n")
    before = _snap(tmp_path, target, env)
    (info / "attributes").write_text("*.txt text\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert any(v["kind"] == "gitdir" for v in report["violations"])


def test_new_hook_on_linked_worktree_is_gitdir_violation(tmp_path):
    target, env = _build_target(tmp_path)
    worktree = tmp_path / "wt"
    _git(target, env, "worktree", "add", "-q", "--detach", str(worktree), "HEAD")
    before = _snap(tmp_path, worktree, env)
    hooks = target / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\necho pwned\n")
    hook.chmod(0o755)
    code, report = _compare(tmp_path, worktree, before, env)
    assert code == 1
    assert any(v["kind"] == "gitdir" for v in report["violations"])


def test_every_gitdir_entry_is_checked_or_listed(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    gitdir = snapshot["gitdir"]
    git_dir = target / ".git"
    for root, _dirs, files in os.walk(git_dir):
        for name in files:
            path = Path(root) / name
            rel = str(path.relative_to(git_dir))
            top = rel.split(os.sep)[0]
            assert rel in gitdir or top in target_snapshot.GITDIR_UNCHECKED, rel


def test_inherited_git_dir_does_not_redirect_snapshot(tmp_path):
    target, env = _build_target(tmp_path)
    decoy, decoy_env = _build_target(tmp_path, name="decoy")
    (decoy / "decoy-marker.txt").write_text("decoy\n")
    _git(decoy, decoy_env, "add", "-A")
    _git(decoy, decoy_env, "commit", "-q", "-m", "decoy marker")
    target_head = _git(target, env, "rev-parse", "HEAD")
    decoy_head = _git(decoy, decoy_env, "rev-parse", "HEAD")
    assert target_head != decoy_head

    # A caller with GIT_DIR set in its environment (a git hook, some
    # wrappers) must not have it override the explicit `-C <repo>` target.
    hijack_env = {**env, "GIT_DIR": str(decoy / ".git")}
    out = tmp_path / "snaps" / "before.json"
    out.parent.mkdir(exist_ok=True)
    result = _run(tmp_path, hijack_env, "snapshot", str(target), str(out))

    assert result.returncode == 0, result.stderr
    snapshot = json.loads(out.read_text())
    assert snapshot["repo"] == os.path.realpath(target)
    assert snapshot["head"]["commit"] == target_head
    assert snapshot["head"]["commit"] != decoy_head


def _kinds(report):
    return [v["kind"] for v in report["violations"]]


def test_untouched_linked_worktree_and_submodule_compare_unchanged(tmp_path):
    target, env = _build_target(tmp_path)
    _git(target, env, "worktree", "add", "-q", "--detach", str(tmp_path / "wt"), "HEAD")
    _add_submodule(tmp_path, target, env)
    before = _snap(tmp_path, target, env)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_detached_linked_worktree_is_worktree_head_violation(tmp_path):
    target, env = _build_target(tmp_path)
    worktree = tmp_path / "wt"
    _git(target, env, "worktree", "add", "-q", "--detach", str(worktree), "HEAD")
    before = _snap(tmp_path, target, env)
    other = _git(worktree, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "wt work")
    _git(worktree, env, "checkout", "-q", "--detach", other)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["status"] == "changed"
    assert _kinds(report) == ["worktree-head"]


def test_submodule_commit_is_submodule_violation(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    before = _snap(tmp_path, target, env)
    _git(sub, env, "commit", "-q", "--allow-empty", "-m", "sub work")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert "submodule" in _kinds(report)


def test_submodule_untracked_file_is_submodule_violation(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    before = _snap(tmp_path, target, env)
    (sub / "planted.txt").write_text("planted\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert "submodule" in _kinds(report)


def test_malformed_ref_name_in_snapshot_exits_2(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    head = snapshot["refs"].pop("refs/heads/master")
    snapshot["refs"]["--stdin"] = head
    before.write_text(json.dumps(snapshot))
    result = _run(tmp_path, env, "compare", str(target), str(before))
    _assert_exit2(result)
    assert result.stdout == ""


def test_malformed_ref_value_in_snapshot_exits_2(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    snapshot["refs"]["refs/heads/master"] = "--no-deref"
    before.write_text(json.dumps(snapshot))
    result = _run(tmp_path, env, "compare", str(target), str(before))
    _assert_exit2(result)
    assert result.stdout == ""


def test_dirty_submodule_second_edit_is_submodule_violation(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    (sub / "notes.txt").write_bytes(NOTES_V1)
    before = _snap(tmp_path, target, env)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0, report
    (sub / "notes.txt").write_bytes(NOTES_V2)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert "submodule" in _kinds(report)


def test_restore_command_puts_non_utf8_ref_back(tmp_path):
    probe = tmp_path / os.fsdecode(b"probe-\xff")
    try:
        probe.write_text("probe\n")
    except OSError as exc:
        pytest.skip(f"filesystem rejects non-UTF-8 names: {exc}")

    target, env = _build_target(tmp_path)
    sha = _git(target, env, "rev-parse", "HEAD")
    bad_ref = b"refs/heads/bad-\xff"
    _write_packed_refs(target, sha, bad_ref)
    before = _snap(tmp_path, target, env)

    other = _git(target, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "move it")
    _write_packed_refs(target, other, bad_ref)

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = [v for v in report["violations"] if v["kind"] == "ref"]
    assert violation["ref"] == os.fsdecode(bad_ref)
    assert violation["restore"].isascii()

    outside = tmp_path / "elsewhere"
    outside.mkdir(exist_ok=True)
    subprocess.run(["bash", "-c", violation["restore"].encode("ascii")], cwd=outside, env=env, check=True)

    assert _git(target, env, "rev-parse", os.fsdecode(bad_ref)) == sha
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_utf8_restore_command_is_unchanged(tmp_path):
    target, env = _build_target(tmp_path)
    old = _git(target, env, "rev-parse", "HEAD")
    before = _snap(tmp_path, target, env)
    new = _git(target, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "second change")
    _git(target, env, "update-ref", "refs/heads/master", new, old)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = [v for v in report["violations"] if v["kind"] == "ref"]
    repo = shlex.quote(os.path.realpath(target))
    expected = " ".join(
        shlex.quote(a) for a in
        ["git", "-C", os.path.realpath(target), "update-ref", "refs/heads/master", old, new]
    )
    assert violation["restore"] == expected
    assert violation["restore"] == f"git -C {repo} update-ref refs/heads/master {old} {new}"


def _write_non_uniform_file(path, size):
    """Write `size` bytes of non-uniform content efficiently (no giant in-memory buffer)."""
    chunk = bytes(range(256)) * 4096  # 1 MiB, non-uniform, repeats every 256 KiB
    with open(path, "wb") as handle:
        written = 0
        while written < size:
            take = min(len(chunk), size - written)
            handle.write(chunk[:take])
            written += take


def test_fingerprint_matches_whole_file_sha256(tmp_path):
    target, env = _build_target(tmp_path)
    big = target / "big.bin"
    # Bigger than a typical 1 MiB chunk, with content that straddles any
    # chunk boundary non-uniformly, so a buggy chunked reimplementation
    # that mishandles boundaries would hash something other than the
    # whole file and fail this assertion.
    size = 5 * 1024 * 1024 + 777
    _write_non_uniform_file(big, size)
    _git(target, env, "add", "big.bin")
    _git(target, env, "commit", "-q", "-m", "add big.bin")
    before = _snap(tmp_path, target, env)

    with open(big, "ab") as handle:
        handle.write(b"tail edit\n")
    full_bytes = big.read_bytes()

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = [v for v in report["violations"] if v.get("path") == "big.bin"]
    assert violation["kind"] == "tracked"
    assert violation["after"] == f" M {hashlib.sha256(full_bytes).hexdigest()}"


def _big_file_target(tmp_path):
    """Target with a committed 200 MiB big.bin, snapshotted, then dirtied.

    The file is sparse (one seek, one byte), so the fixture itself stays
    cheap; the edit rewrites the first bytes in place, which keeps the size
    and so leaves the content as the only way to tell the file changed.
    Returns (target, env, snapshot path).
    """
    target, env = _build_target(tmp_path)
    big = target / "big.bin"
    size = 200 * 1024 * 1024
    with open(big, "wb") as handle:
        handle.seek(size - 1)
        handle.write(b"\0")
    _git(target, env, "add", "big.bin")
    _git(target, env, "commit", "-q", "-m", "add big.bin")
    before = _snap(tmp_path, target, env)

    with open(big, "r+b") as handle:
        handle.seek(0)
        handle.write(b"dirty")
    return target, env, before


def test_large_dirty_file_snapshot_peak_rss_under_48_mib(tmp_path):
    target, env, before = _big_file_target(tmp_path)

    budget = 48 * 1024 * 1024

    # resource.getrusage(RUSAGE_CHILDREN) is cumulative over every child this
    # pytest process has ever reaped, with no way to reset it. The fixture's
    # own `git add` of a 200 MiB file already drives that ceiling past the
    # budget (git mmaps/hashes the whole blob), before `compare` even runs,
    # so that counter cannot isolate this one subprocess's RSS. Wrap the
    # `compare` invocation in `/usr/bin/time` instead, which reports the
    # peak RSS of exactly that one child process.
    peak_rss = _peak_rss(tmp_path, env, "compare", str(target), str(before))
    assert peak_rss < budget, (
        f"subprocess peak RSS {peak_rss} bytes exceeded {budget} byte budget"
    )
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1, report


def test_inherited_big_file_threshold_does_not_beat_module_override(tmp_path):
    target, env, before = _big_file_target(tmp_path)

    # A second, harmless pair rides along in the same hostile environment.
    # Deleting the caller's inherited pairs would hold the RSS budget without
    # proving anything about command-line precedence, so this pair must still
    # take effect: `core.excludesFile` makes an otherwise untracked file
    # ignored, which the snapshot records.
    (target / "scratch.txt").write_text("scratch\n")
    excludes = tmp_path / "excludes"
    excludes.write_text("scratch.txt\n")
    assert "scratch.txt" in _git(
        target, env, "ls-files", "--others", "--exclude-standard"
    ).splitlines(), "fixture is inert: scratch.txt is not untracked to begin with"

    # A careless or hostile caller sets the threshold above the file size. The
    # module's own `-c core.bigFileThreshold=1m` is on the command line, which
    # beats the environment transport, so PRD 00019's peak-RSS guard survives.
    # Measured on git 2.56.0 for this fixture: ~8 MiB when 1m wins, ~207 MiB
    # when the inherited 4g wins.
    hostile_env = _pair_env(
        env, ("core.bigFileThreshold", "4g"), ("core.excludesFile", excludes),
    )
    budget = 48 * 1024 * 1024
    peak_rss = _peak_rss(tmp_path, hostile_env, "compare", str(target), str(before))
    assert peak_rss < budget, (
        f"an inherited core.bigFileThreshold=4g beat the module's own 1m: "
        f"peak RSS {peak_rss} bytes exceeded {budget} byte budget"
    )
    hostile = json.loads(_snap(tmp_path, target, hostile_env, name="hostile.json").read_text())
    _assert_scratch_ignored(
        hostile,
        "the inherited core.excludesFile was dropped instead of forwarded, so the "
        "threshold was beaten by deletion, not by precedence",
    )
    code, report = _compare(tmp_path, target, before, hostile_env)
    assert code == 1, report
