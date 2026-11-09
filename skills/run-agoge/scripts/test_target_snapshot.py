import hashlib
import json
import os
import resource
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

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

    before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    result = _run(tmp_path, env, "compare", str(target), str(before))
    assert result.returncode == 1, result.stderr
    after_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

    # ru_maxrss is bytes on Darwin, kilobytes on Linux.
    unit = 1 if sys.platform == "darwin" else 1024
    peak_rss = after_rss * unit
    # ru_maxrss on RUSAGE_CHILDREN is the max over all reaped children in
    # this process's lifetime, not just this one call, so a smaller
    # before-value only strengthens the assertion; it is captured for
    # documentation/debugging, not subtracted.
    assert before_rss * unit <= peak_rss
    assert peak_rss < budget, (
        f"subprocess peak RSS {peak_rss} bytes exceeded {budget} byte budget"
    )
