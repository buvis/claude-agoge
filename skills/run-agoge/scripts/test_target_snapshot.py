import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

import target_snapshot

SCRIPT = Path(__file__).resolve().parent / "target_snapshot.py"

TEST_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@test.local",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@test.local",
}

# A shared 20-byte prefix: the versions differ only after byte 16, so a
# fingerprint that hashes a prefix instead of the whole file cannot pass.
SHARED_PREFIX = b"x" * 20
NOTES_V1 = SHARED_PREFIX + b"v1\n"
NOTES_V2 = SHARED_PREFIX + b"v2\n"
STAGED = SHARED_PREFIX + b"staged edit\n"


def _env_for(tmp_path):
    return {**TEST_ENV, "HOME": str(tmp_path)}


def _git(target, env, *args):
    return subprocess.run(
        ["git", *args], cwd=target, env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _build_target(tmp_path, name="target"):
    env = _env_for(tmp_path)
    target = tmp_path / name
    target.mkdir()
    _git(target, env, "init", "-q", "-b", "master")
    (target / "README.md").write_text("seed\n")
    (target / "notes.txt").write_text("notes v0\n")
    (target / "notes.txt.orig").write_text("orig v0\n")
    _git(target, env, "add", "-A")
    _git(target, env, "commit", "-q", "-m", "init")
    _git(target, env, "update-ref", "refs/remotes/origin/master", "HEAD")
    _git(target, env, "tag", "v1.0")
    return target, env


def _run(tmp_path, env, *args, timeout=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=timeout,
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


def _snap(tmp_path, target, env, name="before.json"):
    out = tmp_path / "snaps" / name
    out.parent.mkdir(exist_ok=True)
    result = _run(tmp_path, env, "snapshot", str(target), str(out))
    assert result.returncode == 0, result.stderr
    return out


def _compare(tmp_path, target, before, env, allow=()):
    extra = [arg for path in allow for arg in ("--allow", path)]
    result = _run(tmp_path, env, "compare", str(target), str(before), *extra)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode, json.loads(result.stdout)


def _assert_exit2(result):
    assert result.returncode == 2
    lines = result.stderr.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("target_snapshot: ")
    assert "Traceback" not in result.stderr


def _git_dir_state(target):
    git_dir = target / ".git"
    state = {}
    for root, dirs, files in os.walk(git_dir):
        for name in dirs + files:
            path = Path(root) / name
            st = path.lstat()
            state[str(path.relative_to(git_dir))] = (st.st_mtime_ns, st.st_size)
    return state


def test_untouched_target_compares_unchanged(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    (target / "other.txt").write_text("other\n")
    head = _git(target, env, "rev-parse", "HEAD")
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["version"] == target_snapshot.VERSION
    assert snapshot["repo"] == os.path.realpath(target)
    assert snapshot["head"] == {"ref": "refs/heads/master", "commit": head}
    assert snapshot["refs"]["refs/heads/master"] == head
    assert snapshot["refs"]["refs/tags/v1.0"] == head
    assert snapshot["untracked"] == ["other.txt", "scratch.txt"]
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_snapshot_and_compare_write_nothing_in_target(tmp_path):
    target, env = _build_target(tmp_path)
    notes = target / "notes.txt"
    st = notes.stat()
    os.utime(notes, ns=(st.st_atime_ns, st.st_mtime_ns + 100_000_000_000))
    index_before = (target / ".git/index").read_bytes()
    git_state_before = _git_dir_state(target)
    before = _snap(tmp_path, target, env)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report["status"] == "unchanged"
    assert (target / ".git/index").read_bytes() == index_before
    assert _git_dir_state(target) == git_state_before


def test_new_commit_on_current_branch_is_one_ref_violation_with_commit(tmp_path):
    target, env = _build_target(tmp_path)
    old = _git(target, env, "rev-parse", "HEAD")
    before = _snap(tmp_path, target, env)
    commit_env = {
        **env,
        "GIT_AUTHOR_NAME": "Ada Author",
        "GIT_AUTHOR_EMAIL": "ada@example.test",
        "GIT_COMMITTER_NAME": "Cy Committer",
        "GIT_COMMITTER_EMAIL": "cy@example.test",
        "GIT_COMMITTER_DATE": "2026-03-04T05:06:07+02:00",
    }
    new = _git(target, commit_env, "commit-tree", "HEAD^{tree}", "-p", "HEAD",
               "-m", "feat: second change", "-m", "body line")
    # The reflog entry carries its own identity and message, distinct from the
    # commit's metadata, so a reflog value derived from the commit cannot match.
    reflog_env = {
        **env,
        "GIT_COMMITTER_NAME": "Rex Reflogger",
        "GIT_COMMITTER_EMAIL": "rex@example.test",
    }
    _git(target, reflog_env, "update-ref", "-m", "custom reflog message",
         "refs/heads/master", new, old)
    assert _git(target, env, "rev-parse", "HEAD") == new
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["status"] == "changed"
    repo = shlex.quote(os.path.realpath(target))
    assert report["violations"] == [{
        "kind": "ref",
        "ref": "refs/heads/master",
        "before": old,
        "after": new,
        "commit": {
            "author": "Ada Author <ada@example.test>",
            "committer": "Cy Committer <cy@example.test>",
            "date": "2026-03-04T05:06:07+02:00",
            "subject": "feat: second change",
        },
        "reflog": "Rex Reflogger <rex@example.test> | custom reflog message",
        "restore": f"git -C {repo} update-ref refs/heads/master {old} {new}",
    }]
    assert report["touched"] == []


def test_new_tag_is_ref_violation(tmp_path):
    target, env = _build_target(tmp_path)
    head = _git(target, env, "rev-parse", "HEAD")
    before = _snap(tmp_path, target, env)
    _git(target, env, "tag", "v2")
    _git(target, env, "tag", "v1.0.0")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    repo = shlex.quote(os.path.realpath(target))
    violations = report["violations"]
    assert [v["kind"] for v in violations] == ["ref", "ref"]
    assert [v["ref"] for v in violations] == ["refs/tags/v1.0.0", "refs/tags/v2"]
    for v in violations:
        assert v["before"] is None
        assert v["after"] == head
        assert v["commit"]["subject"] == "init"
        assert v["reflog"] is None
        assert v["restore"] == f"git -C {repo} update-ref -d {v['ref']} {head}"


def test_moved_remote_tracking_ref_is_ref_violation(tmp_path):
    target, env = _build_target(tmp_path)
    old = _git(target, env, "rev-parse", "refs/remotes/origin/master")
    before = _snap(tmp_path, target, env)
    new = _git(target, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "remote work")
    _git(target, env, "update-ref", "-m", "fetch origin: fast-forward",
         "refs/remotes/origin/master", new)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    repo = shlex.quote(os.path.realpath(target))
    [violation] = report["violations"]
    assert violation["kind"] == "ref"
    assert violation["ref"] == "refs/remotes/origin/master"
    assert violation["before"] == old
    assert violation["after"] == new
    assert violation["commit"]["subject"] == "remote work"
    assert violation["reflog"] == "Test User <test@test.local> | fetch origin: fast-forward"
    assert violation["restore"] == (
        f"git -C {repo} update-ref refs/remotes/origin/master {old} {new}"
    )


def test_branch_switch_is_head_violation(tmp_path):
    target, env = _build_target(tmp_path)
    head = _git(target, env, "rev-parse", "HEAD")
    _git(target, env, "branch", "feature")
    before = _snap(tmp_path, target, env)
    _git(target, env, "switch", "-q", "feature")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{
        "kind": "head",
        "before": {"ref": "refs/heads/master", "commit": head},
        "after": {"ref": "refs/heads/feature", "commit": head},
    }]


def test_moved_detached_head_is_head_violation(tmp_path):
    target, env = _build_target(tmp_path)
    head = _git(target, env, "rev-parse", "HEAD")
    _git(target, env, "checkout", "-q", "--detach", "HEAD")
    before = _snap(tmp_path, target, env)
    other = _git(target, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "detached work")
    _git(target, env, "checkout", "-q", "--detach", other)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{
        "kind": "head",
        "before": {"ref": None, "commit": head},
        "after": {"ref": None, "commit": other},
    }]


def test_deleted_ref_is_ref_violation_with_recreating_restore(tmp_path):
    target, env = _build_target(tmp_path)
    head = _git(target, env, "rev-parse", "HEAD")
    _git(target, env, "branch", "gone")
    before = _snap(tmp_path, target, env)
    _git(target, env, "branch", "-q", "-D", "gone")
    _git(target, env, "tag", "-d", "v1.0")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["status"] == "changed"
    real = os.path.realpath(target)
    violations = report["violations"]
    assert [v["ref"] for v in violations] == ["refs/heads/gone", "refs/tags/v1.0"]
    for v in violations:
        restore = v.pop("restore")
        assert v == {
            "kind": "ref",
            "ref": v["ref"],
            "before": head,
            "after": None,
            "reflog": None,
        }
        assert shlex.split(restore) == [
            "git", "-C", real, "update-ref", v["ref"], head, "",
        ]
        outside = tmp_path / "elsewhere"
        outside.mkdir(exist_ok=True)
        subprocess.run(["bash", "-c", restore], cwd=outside, env=env, check=True)
    assert _git(target, env, "rev-parse", "refs/heads/gone") == head
    assert _git(target, env, "rev-parse", "refs/tags/v1.0") == head

    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_staged_change_is_index_violation(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    (target / "README.md").write_bytes(STAGED)
    _git(target, env, "add", "README.md")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    violations = report["violations"]
    assert [v["kind"] for v in violations] == ["index", "tracked"]
    assert violations[0] == {"kind": "index"}
    assert violations[1] == {
        "kind": "tracked",
        "path": "README.md",
        "before": None,
        "after": f"M  {_sha(STAGED)}",
    }


def test_editing_already_modified_file_is_tracked_violation(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "notes.txt").write_bytes(NOTES_V1)
    (target / "notes.txt.orig").write_text("orig v1\n")
    before = _snap(tmp_path, target, env)
    (target / "notes.txt").write_bytes(NOTES_V2)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{
        "kind": "tracked",
        "path": "notes.txt",
        "before": f" M {_sha(NOTES_V1)}",
        "after": f" M {_sha(NOTES_V2)}",
    }]


def test_reverting_modified_file_is_tracked_violation(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "notes.txt").write_bytes(NOTES_V1)
    (target / "notes.txt.orig").write_text("orig v1\n")
    before = _snap(tmp_path, target, env)
    _git(target, env, "checkout", "-q", "--", "notes.txt")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["violations"] == [{
        "kind": "tracked",
        "path": "notes.txt",
        "before": f" M {_sha(NOTES_V1)}",
        "after": None,
    }]


def test_removed_untracked_file_is_untracked_removed_violation(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    (target / "scratch.txt.keep").write_text("keep\n")
    before = _snap(tmp_path, target, env)
    (target / "scratch.txt").unlink()
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["status"] == "changed"
    assert report["violations"] == [{"kind": "untracked-removed", "path": "scratch.txt"}]
    assert report["touched"] == []


def test_new_untracked_file_is_touched_and_exits_zero(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    before = _snap(tmp_path, target, env)
    (target / "zeta.txt").write_text("z\n")
    (target / "scratch.txt.new").write_text("n\n")
    (target / "sub").mkdir()
    (target / "sub/new.txt").write_text("s\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {
        "status": "unchanged",
        "violations": [],
        "touched": ["scratch.txt.new", "sub/new.txt", "zeta.txt"],
    }


def test_allowed_path_is_not_tracked_removed_or_touched(tmp_path):
    target, env = _build_target(tmp_path)
    (target / "notes.txt").write_bytes(NOTES_V1)
    (target / "notes.txt.orig").write_text("orig v1\n")
    (target / "scratch.txt").write_text("scratch\n")
    before = _snap(tmp_path, target, env)
    (target / "notes.txt").write_bytes(NOTES_V2)
    (target / "notes.txt.orig").write_text("orig v2\n")
    (target / "scratch.txt").unlink()
    (target / "new.txt").write_text("n\n")
    (target / "new.txt.extra").write_text("e\n")

    code, report = _compare(
        tmp_path, target, before, env, allow=("notes.txt", "scratch.txt", "new.txt"),
    )
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("tracked", "notes.txt.orig"),
    ]
    assert report["touched"] == ["new.txt.extra"]

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("tracked", "notes.txt"),
        ("tracked", "notes.txt.orig"),
        ("untracked-removed", "scratch.txt"),
    ]
    assert report["touched"] == ["new.txt", "new.txt.extra"]


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


def test_restore_commands_put_refs_back(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    _git(target, env, "tag", "v9")
    _git(target, env, "branch", "side")
    moved = _git(target, env, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "remote")
    _git(target, env, "update-ref", "refs/remotes/origin/master", moved)

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    violations = report["violations"]
    assert sorted(v["ref"] for v in violations) == [
        "refs/heads/side", "refs/remotes/origin/master", "refs/tags/v9",
    ]
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    for v in violations:
        subprocess.run(["bash", "-c", v["restore"]], cwd=outside, env=env, check=True)

    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_tracked_dir_replaced_by_external_symlink_does_not_follow_traversal(tmp_path):
    target, env = _build_target(tmp_path)
    sub = target / "sub"
    sub.mkdir()
    (sub / "child.txt").write_text("child v1\n")
    _git(target, env, "add", "-A")
    _git(target, env, "commit", "-q", "-m", "add sub/child.txt")
    before = _snap(tmp_path, target, env)

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "child.txt").write_text("not the real child\n")
    _git(target, env, "rm", "-q", "-r", "--cached", "sub")
    shutil.rmtree(sub)
    sub.symlink_to(outside)

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    violations = {v["path"]: v for v in report["violations"] if v["kind"] == "tracked"}
    assert violations["sub/child.txt"]["after"] != f" D {_sha((outside / 'child.txt').read_bytes())}"
    assert "external-symlink" in violations["sub/child.txt"]["after"]


def test_unusable_inputs_exit_2_with_prefixed_stderr(tmp_path):
    target, env = _build_target(tmp_path)
    inside = target / "snap.json"
    _assert_exit2(_run(tmp_path, env, "snapshot", str(target), str(inside)))
    assert not inside.exists()

    (target / "sub").mkdir()
    nested = target / "sub" / "snap.json"
    _assert_exit2(_run(tmp_path, env, "snapshot", str(target), str(nested)))
    assert not nested.exists()

    sibling = tmp_path / "target-out" / "snap.json"
    sibling.parent.mkdir()
    assert _run(tmp_path, env, "snapshot", str(target), str(sibling)).returncode == 0

    other, _ = _build_target(tmp_path, name="other")
    other_snap = _snap(tmp_path, other, env, name="other.json")
    result = _run(tmp_path, env, "compare", str(target), str(other_snap))
    _assert_exit2(result)
    assert result.stdout == ""

    # Same basename, different real path: still another repo.
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    twin_a, _ = _build_target(tmp_path, name="a/target")
    twin_b, _ = _build_target(tmp_path, name="b/target")
    twin_snap = _snap(tmp_path, twin_a, env, name="twin-a.json")
    result = _run(tmp_path, env, "compare", str(twin_b), str(twin_snap))
    _assert_exit2(result)
    assert result.stdout == ""

    missing = tmp_path / "snaps" / "missing.json"
    not_json = tmp_path / "snaps" / "not-json.json"
    not_json.write_text("{not json\n")
    wrong_version = tmp_path / "snaps" / "wrong-version.json"
    snapshot = json.loads(sibling.read_text())
    wrong_version.write_text(json.dumps({**snapshot, "version": target_snapshot.VERSION + 1}))
    for bad in (missing, not_json, wrong_version):
        result = _run(tmp_path, env, "compare", str(target), str(bad))
        _assert_exit2(result)
        assert result.stdout == ""

    unborn = tmp_path / "unborn"
    unborn.mkdir()
    _git(unborn, env, "init", "-q", "-b", "master")
    unborn_out = tmp_path / "snaps" / "unborn.json"
    _assert_exit2(_run(tmp_path, env, "snapshot", str(unborn), str(unborn_out)))
    assert not unborn_out.exists()


def test_previous_version_snapshot_exits_2_with_one_line(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["version"] == target_snapshot.VERSION
    assert target_snapshot.VERSION == 4

    # Control: the same keys re-serialized at the current version still compare.
    current = tmp_path / "snaps" / "current-version.json"
    current.write_text(json.dumps({**snapshot, "version": target_snapshot.VERSION}))
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}
    code, report = _compare(tmp_path, target, current, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}

    versionless = {key: value for key, value in snapshot.items() if key != "version"}
    old_shape = {
        key: value
        for key, value in snapshot.items()
        if key not in ("untracked_fingerprints", "ignored")
    }
    for name, data in (
        ("previous", {**snapshot, "version": target_snapshot.VERSION - 1}),
        ("older", {**snapshot, "version": target_snapshot.VERSION - 2}),
        ("newer", {**snapshot, "version": target_snapshot.VERSION + 1}),
        ("versionless", versionless),
        ("old-shape-v3", {**old_shape, "version": 3}),
    ):
        stale = tmp_path / "snaps" / f"{name}-version.json"
        stale.write_text(json.dumps(data))
        result = _run(tmp_path, env, "compare", str(target), str(stale))
        _assert_exit2(result)
        assert result.stdout == "", name


def test_text_keeps_filesystem_bytes_and_trailing_space():
    result = subprocess.CompletedProcess([], 0, stdout=b"/a/\xff b \n")
    assert target_snapshot._text(result) == "/a/\udcff b "


def test_repo_dir_with_trailing_space_round_trips(tmp_path):
    target, env = _build_target(tmp_path, name="target ")
    before = _snap(tmp_path, target, env)
    assert json.loads(before.read_text())["repo"] == os.path.realpath(target)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def _write_packed_refs(target, sha, *names):
    header = b"# pack-refs with: peeled fully-peeled sorted \n"
    lines = b"".join(sha.encode() + b" " + name + b"\n" for name in sorted(names))
    (target / ".git" / "packed-refs").write_bytes(header + lines)


def test_non_utf8_refs_round_trip_through_snapshot(tmp_path):
    target, env = _build_target(tmp_path)
    sha = _git(target, env, "rev-parse", "HEAD")
    first, second = b"refs/heads/\xff", b"refs/heads/\xfe"
    _write_packed_refs(target, sha, first)
    (target / ".git" / "HEAD").write_bytes(b"ref: " + first + b"\n")
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["head"] == {"ref": os.fsdecode(first), "commit": sha}
    assert snapshot["refs"][os.fsdecode(first)] == sha
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}

    _write_packed_refs(target, sha, first, second)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    [violation] = report["violations"]
    assert violation["kind"] == "ref"
    assert violation["ref"] == os.fsdecode(second)
    assert violation["before"] is None
    assert violation["after"] == sha


def test_non_utf8_paths_round_trip(tmp_path):
    repo_name = os.fsdecode(b"target-\xff")
    tracked_name = os.fsdecode(b"tracked-\xfe.txt")
    untracked_name = os.fsdecode(b"untracked-\xfd.txt")
    later_name = os.fsdecode(b"later-\xfc.txt")
    try:
        target, env = _build_target(tmp_path, name=repo_name)
        (target / tracked_name).write_bytes(NOTES_V1)
        _git(target, env, "add", "-A")
        _git(target, env, "commit", "-q", "-m", "add tracked")
        (target / tracked_name).write_bytes(NOTES_V2)
        (target / untracked_name).write_text("u\n")
    except OSError as exc:
        pytest.skip(f"filesystem rejects non-UTF-8 names: {exc}")
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["repo"] == os.path.realpath(target)
    assert tracked_name in snapshot["dirty"]
    assert snapshot["untracked"] == [untracked_name]
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}

    (target / tracked_name).write_bytes(STAGED)
    (target / later_name).write_text("l\n")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [("tracked", tracked_name)]
    assert report["touched"] == [later_name]


def test_unreadable_dirty_file_exits_2_with_one_line(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads files regardless of mode")
    target, env = _build_target(tmp_path)
    notes = target / "notes.txt"
    notes.write_bytes(NOTES_V1)
    notes.chmod(0o000)
    try:
        out = tmp_path / "snaps" / "unreadable.json"
        out.parent.mkdir()
        result = _run(tmp_path, env, "snapshot", str(target), str(out))
        _assert_exit2(result)
        assert "notes.txt" in result.stderr
        assert result.stdout == ""
        assert not out.exists()
    finally:
        notes.chmod(0o644)


def test_unreadable_untracked_file_exits_2_with_one_line(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads files regardless of mode")
    target, env = _build_target(tmp_path)
    notes = target / "notes.md"
    notes.write_bytes(NOTES_V1)
    notes.chmod(0o000)
    try:
        out = tmp_path / "snaps" / "unreadable-untracked.json"
        out.parent.mkdir()
        result = _run(tmp_path, env, "snapshot", str(target), str(out))
        _assert_exit2(result)
        assert "notes.md" in result.stderr
        assert result.stdout == ""
        assert not out.exists()
    finally:
        notes.chmod(0o644)


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


def test_fifo_in_place_of_tracked_file_does_not_hang(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    notes = target / "notes.txt"
    notes.unlink()
    os.mkfifo(notes)
    try:
        result = _run(tmp_path, env, "compare", str(target), str(before), timeout=10)
    except subprocess.TimeoutExpired:
        pytest.fail("compare hung on a tracked path replaced by a FIFO")
    assert result.returncode in (0, 1), result.stderr


def test_fifo_replaced_by_file_is_tracked_violation(tmp_path):
    target, env = _build_target(tmp_path)
    before = _snap(tmp_path, target, env)
    notes = target / "notes.txt"
    notes.unlink()
    os.mkfifo(notes)
    try:
        result = _run(tmp_path, env, "compare", str(target), str(before), timeout=10)
    except subprocess.TimeoutExpired:
        pytest.fail("compare hung on a tracked path replaced by a FIFO")
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    [violation] = [v for v in report["violations"] if v.get("path") == "notes.txt"]
    assert violation["kind"] == "tracked"
    assert violation["kind"] not in ("absent", "dir")


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


def _add_submodule(tmp_path, target, env):
    sub_src, _ = _build_target(tmp_path, name="sub-src")
    _git(target, env, "-c", "protocol.file.allow=always",
         "submodule", "add", "-q", str(sub_src), "sub")
    _git(target, env, "commit", "-q", "-m", "add submodule")
    return target / "sub"


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


def test_large_dirty_file_snapshot_peak_rss_under_48_mib(tmp_path):
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


def _configure_filter(target, env, scope_args, driver, program):
    """Map `*.txt` to `driver`, then point `filter.<driver>` at `program`.

    The `.gitattributes` is committed before the config is set, so no filter
    runs while the fixture is being built.
    """
    (target / ".gitattributes").write_text(f"*.txt filter={driver}\n")
    _git(target, env, "add", ".gitattributes")
    _git(target, env, "commit", "-q", "-m", "map *.txt to a filter")
    _git(target, env, "config", *scope_args, f"filter.{driver}.clean", str(program))
    _git(target, env, "config", *scope_args, f"filter.{driver}.required", "true")


def test_snapshot_does_not_run_fsmonitor(tmp_path):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path, name="fsmonitor.sh")
    _git(target, env, "config", "--local", "core.fsmonitor", str(script))

    # Positive control first: a bare `git status` must really run the hook.
    # Without it an inert fixture would make the assertions below pass
    # vacuously.
    _git(target, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        "fixture is inert: the target's core.fsmonitor never ran"
    )
    log.unlink()

    # The hook must be disabled through the module's own command-scope
    # configuration, never by rewriting the target's config: the module
    # promises nothing is ever written inside <repo>.
    config_before = (target / ".git" / "config").read_bytes()
    git_state_before = _git_dir_state(target)

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the target's fsmonitor hook: {log.read_text()!r}"
    )
    assert (target / ".git" / "config").read_bytes() == config_before, (
        "snapshot rewrote the target's own .git/config to disable the fsmonitor hook"
    )
    assert _git_dir_state(target) == git_state_before
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the target's fsmonitor hook: {log.read_text()!r}"
    )
    assert (target / ".git" / "config").read_bytes() == config_before, (
        "compare rewrote the target's own .git/config to disable the fsmonitor hook"
    )
    assert _git_dir_state(target) == git_state_before
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
    _git(target, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        "fixture is inert: the target's clean filter never ran"
    )
    log.unlink()

    # The driver must be disabled through the module's own command-scope
    # configuration. Rewriting the target's config would silence the marker
    # too, and would break the promise that nothing is written inside <repo>.
    config_before = (target / ".git" / "config").read_bytes()
    git_state_before = _git_dir_state(target)

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the target's clean filter: {log.read_text()!r}"
    )
    assert (target / ".git" / "config").read_bytes() == config_before, (
        f"snapshot rewrote the target's own .git/config to disable {driver!r}"
    )
    assert _git_dir_state(target) == git_state_before
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the target's clean filter: {log.read_text()!r}"
    )
    assert (target / ".git" / "config").read_bytes() == config_before, (
        f"compare rewrote the target's own .git/config to disable {driver!r}"
    )
    assert _git_dir_state(target) == git_state_before
    assert code == 0, report


# One setup per configuration source. Each takes the freshly built target and
# its environment, declares a clean filter for `driver` through its own scope,
# and returns the environment the snapshot must run with plus the repository
# whose config now declares the driver (the submodule, for the last one).
def _source_local(tmp_path, target, env, driver, script):
    _configure_filter(target, env, ["--local"], driver, script)
    return env, target


def _source_global(tmp_path, target, env, driver, script):
    # TEST_ENV pins GIT_CONFIG_GLOBAL at /dev/null; point it at a real file so
    # `git config --global` has somewhere to write.
    env = {**env, "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig-global")}
    _configure_filter(target, env, ["--global"], driver, script)
    return env, target


def _source_include_path(tmp_path, target, env, driver, script):
    included = tmp_path / "included.cfg"
    _configure_filter(target, env, ["--file", str(included)], driver, script)
    _git(target, env, "config", "--local", "include.path", str(included))
    return env, target


def _source_include_if(tmp_path, target, env, driver, script):
    included = tmp_path / "conditional.cfg"
    _configure_filter(target, env, ["--file", str(included)], driver, script)
    # Build the gitdir: pattern from the resolved path. git matches the
    # unresolved gitdir and then retries against the realpath, so both forms
    # work here, but the realpath is the deterministic one: on macOS pytest's
    # tmp_path sits under /var/folders, which resolves to /private/var/folders.
    real = os.path.realpath(str(target))
    _git(target, env, "config", "--local", f"includeIf.gitdir:{real}/.path", str(included))
    return env, target


def _source_worktree(tmp_path, target, env, driver, script):
    _git(target, env, "config", "--local", "extensions.worktreeConfig", "true")
    _configure_filter(target, env, ["--worktree"], driver, script)
    return env, target


def _source_submodule(tmp_path, target, env, driver, script):
    sub = _add_submodule(tmp_path, target, env)
    _configure_filter(sub, env, ["--local"], driver, script)
    return env, sub


_FILTER_SOURCES = {
    "local": _source_local,
    "global": _source_global,
    "include-path": _source_include_path,
    "include-if": _source_include_if,
    "worktree": _source_worktree,
    "submodule": _source_submodule,
}


@pytest.mark.parametrize("source", list(_FILTER_SOURCES))
def test_snapshot_does_not_run_clean_filter_from_any_source(tmp_path, source):
    target, env = _build_target(tmp_path)
    script, log = _marker(tmp_path)
    driver = _driver()
    env, declaring = _FILTER_SOURCES[source](tmp_path, target, env, driver, script)
    # Same-size edit with a newer mtime, so git must run the clean filter to
    # decide whether the content changed.
    (declaring / "notes.txt").write_bytes(b"notes v1\n")

    # Positive control first, in the repository that declares the driver: an
    # inert fixture (wrong scope flag, non-matching includeIf) would otherwise
    # make the assertions below pass vacuously.
    _git(declaring, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        f"fixture is inert: the {source} clean filter never ran"
    )
    log.unlink()

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the {source} clean filter: {log.read_text()!r}"
    )
    if source == "submodule":
        # Not running the submodule's driver because the submodule was never
        # visited is not a pass: the snapshot must carry its state.
        submodules = json.loads(before.read_text())["submodules"]
        assert submodules["sub"]["head"]["commit"] == _git(declaring, env, "rev-parse", "HEAD"), (
            f"the snapshot does not record the submodule's own state: {submodules}"
        )
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the {source} clean filter: {log.read_text()!r}"
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
    _git(target, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        f"fixture is inert: the clean filter named {driver!r} never ran"
    )
    log.unlink()

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
    with pytest.raises(subprocess.CalledProcessError):
        _git(target, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        "fixture is inert: the target's process filter never launched"
    )
    log.unlink()

    out = tmp_path / "snaps" / "before.json"
    out.parent.mkdir(exist_ok=True)
    result = _run(tmp_path, env, "snapshot", str(target), str(out))
    assert not log.exists(), (
        f"snapshot ran the target's process filter: {log.read_text()!r}"
    )
    # A `required` driver whose command is disabled must not make status fail:
    # exit 0 or 1, never 2.
    assert result.returncode == 0, result.stderr
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
    _git(sub, env, "status", "--porcelain")
    assert sub_log.exists() and sub_log.read_text().strip(), (
        "fixture is inert: the submodule's own clean filter never ran"
    )
    assert not parent_log.exists(), (
        f"git applied the parent's filter inside the submodule: {parent_log.read_text()!r}"
    )
    _git(target, env, "status", "--porcelain")
    assert parent_log.exists() and parent_log.read_text().strip(), (
        "fixture is inert: the parent's own clean filter never ran"
    )
    sub_log.unlink()
    parent_log.unlink()

    # Both drivers must be disabled through the module's own command-scope
    # configuration, in the parent and in the submodule alike, without a byte
    # written inside either repository.
    sub_git_dir = Path(_git(sub, env, "rev-parse", "--absolute-git-dir"))
    sub_head = _git(sub, env, "rev-parse", "HEAD")
    parent_config_before = (target / ".git" / "config").read_bytes()
    sub_config_before = (sub_git_dir / "config").read_bytes()
    git_state_before = _git_dir_state(target)

    before = _snap(tmp_path, target, env)
    assert not sub_log.exists(), (
        f"snapshot ran the submodule's clean filter: {sub_log.read_text()!r}"
    )
    assert not parent_log.exists(), (
        f"snapshot ran the parent's clean filter: {parent_log.read_text()!r}"
    )
    # Never visiting the submodule at all would silence its driver too, so
    # the snapshot has to prove the submodule was really traversed.
    submodules = json.loads(before.read_text())["submodules"]
    assert submodules["sub"]["head"]["commit"] == sub_head, (
        f"the snapshot does not record the submodule's own state: {submodules}"
    )
    assert (target / ".git" / "config").read_bytes() == parent_config_before, (
        f"snapshot rewrote the parent's own .git/config to disable {parent_driver!r}"
    )
    assert (sub_git_dir / "config").read_bytes() == sub_config_before, (
        f"snapshot rewrote the submodule's own config to disable {sub_driver!r}"
    )
    assert _git_dir_state(target) == git_state_before
    code, report = _compare(tmp_path, target, before, env)
    assert not sub_log.exists(), (
        f"compare ran the submodule's clean filter: {sub_log.read_text()!r}"
    )
    assert not parent_log.exists(), (
        f"compare ran the parent's clean filter: {parent_log.read_text()!r}"
    )
    assert (target / ".git" / "config").read_bytes() == parent_config_before, (
        f"compare rewrote the parent's own .git/config to disable {parent_driver!r}"
    )
    assert (sub_git_dir / "config").read_bytes() == sub_config_before, (
        f"compare rewrote the submodule's own config to disable {sub_driver!r}"
    )
    assert _git_dir_state(target) == git_state_before
    assert code == 0, report


def test_snapshot_does_not_run_submodule_only_fsmonitor(tmp_path):
    target, env = _build_target(tmp_path)
    sub = _add_submodule(tmp_path, target, env)
    script, log = _marker(tmp_path, name="sub-fsmonitor.sh")
    _git(sub, env, "config", "--local", "core.fsmonitor", str(script))

    # Positive control: command-scope config is process-wide, so the
    # submodule's hook fires during the PARENT's own status, not only during
    # the recursion into the submodule.
    _git(target, env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        "fixture is inert: the submodule's core.fsmonitor never ran"
    )
    log.unlink()

    sub_git_dir = Path(_git(sub, env, "rev-parse", "--absolute-git-dir"))
    sub_head = _git(sub, env, "rev-parse", "HEAD")
    sub_config_before = (sub_git_dir / "config").read_bytes()

    before = _snap(tmp_path, target, env)
    assert not log.exists(), (
        f"snapshot ran the submodule's fsmonitor hook: {log.read_text()!r}"
    )
    submodules = json.loads(before.read_text())["submodules"]
    assert submodules["sub"]["head"]["commit"] == sub_head, (
        f"the snapshot does not record the submodule's own state: {submodules}"
    )
    assert (sub_git_dir / "config").read_bytes() == sub_config_before, (
        "snapshot rewrote the submodule's own config to disable its fsmonitor hook"
    )
    code, report = _compare(tmp_path, target, before, env)
    assert not log.exists(), (
        f"compare ran the submodule's fsmonitor hook: {log.read_text()!r}"
    )
    assert (sub_git_dir / "config").read_bytes() == sub_config_before, (
        "compare rewrote the submodule's own config to disable its fsmonitor hook"
    )
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
    hijack_env = {
        **env,
        "GIT_CONFIG_COUNT": "3",
        "GIT_CONFIG_KEY_0": "diff.ignoreSubmodules",
        "GIT_CONFIG_VALUE_0": "all",
        "GIT_CONFIG_KEY_1": f"filter.{driver}.clean",
        "GIT_CONFIG_VALUE_1": str(script),
        "GIT_CONFIG_KEY_2": "core.excludesFile",
        "GIT_CONFIG_VALUE_2": str(excludes),
    }

    _git(target, hijack_env, "status", "--porcelain")
    assert log.exists() and log.read_text().strip(), (
        f"fixture is inert: the inherited filter.{driver}.clean never ran"
    )
    log.unlink()

    before = _snap(tmp_path, target, hijack_env)
    assert not log.exists(), (
        f"snapshot ran an inherited command-scope filter: {log.read_text()!r}"
    )
    snapshot = json.loads(before.read_text())
    assert "sub" not in snapshot["dirty"], (
        f"the inherited diff.ignoreSubmodules=all was dropped: {snapshot['dirty']}"
    )
    assert "scratch.txt" not in snapshot["untracked"], (
        f"the inherited core.excludesFile was dropped: {snapshot['untracked']}"
    )
    assert "scratch.txt" in snapshot["ignored"], (
        f"the inherited core.excludesFile was dropped: {snapshot['ignored']}"
    )
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

    pair_env = {
        **env,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "diff.ignoreSubmodules",
        "GIT_CONFIG_VALUE_0": "all",
    }
    with_pair = _snap(tmp_path, target, pair_env, name="with-pair.json")
    dirty = json.loads(with_pair.read_text())["dirty"]
    assert "sub" not in dirty, (
        f"the inherited diff.ignoreSubmodules=all was dropped: {dirty}"
    )


def test_inherited_big_file_threshold_does_not_beat_module_override(tmp_path):
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
    hostile_env = {
        **env,
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.bigFileThreshold",
        "GIT_CONFIG_VALUE_0": "4g",
        "GIT_CONFIG_KEY_1": "core.excludesFile",
        "GIT_CONFIG_VALUE_1": str(excludes),
    }
    budget = 48 * 1024 * 1024
    peak_rss = _peak_rss(tmp_path, hostile_env, "compare", str(target), str(before))
    assert peak_rss < budget, (
        f"an inherited core.bigFileThreshold=4g beat the module's own 1m: "
        f"peak RSS {peak_rss} bytes exceeded {budget} byte budget"
    )
    hostile = json.loads(_snap(tmp_path, target, hostile_env, name="hostile.json").read_text())
    assert "scratch.txt" not in hostile["untracked"], (
        f"the inherited core.excludesFile was dropped instead of forwarded, so the "
        f"threshold was beaten by deletion, not by precedence: {hostile['untracked']}"
    )
    assert "scratch.txt" in hostile["ignored"], (
        f"the inherited core.excludesFile was dropped instead of forwarded, so the "
        f"threshold was beaten by deletion, not by precedence: {hostile['ignored']}"
    )
    code, report = _compare(tmp_path, target, before, hostile_env)
    assert code == 1, report


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
