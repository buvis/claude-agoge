import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

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

NOTES_V1 = b"notes v1\n"
NOTES_V2 = b"notes v2\n"
STAGED = b"staged edit\n"


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


def _run(tmp_path, env, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path, env=env, capture_output=True, text=True,
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
    assert snapshot["version"] == 1
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
    _git(target, commit_env, "commit", "-q", "--allow-empty",
         "-m", "feat: second change", "-m", "body line")
    new = _git(target, env, "rev-parse", "HEAD")
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
        "reflog": "Cy Committer <cy@example.test> | commit: feat: second change",
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
    _git(target, env, "update-ref", "refs/remotes/origin/master", new)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    repo = shlex.quote(os.path.realpath(target))
    [violation] = report["violations"]
    assert violation["kind"] == "ref"
    assert violation["ref"] == "refs/remotes/origin/master"
    assert violation["before"] == old
    assert violation["after"] == new
    assert violation["commit"]["subject"] == "remote work"
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


def test_unusable_inputs_exit_2_with_prefixed_stderr(tmp_path):
    target, env = _build_target(tmp_path)
    inside = target / "snap.json"
    _assert_exit2(_run(tmp_path, env, "snapshot", str(target), str(inside)))
    assert not inside.exists()

    sibling = tmp_path / "target-out" / "snap.json"
    sibling.parent.mkdir()
    assert _run(tmp_path, env, "snapshot", str(target), str(sibling)).returncode == 0

    other, _ = _build_target(tmp_path, name="other")
    other_snap = _snap(tmp_path, other, env, name="other.json")
    result = _run(tmp_path, env, "compare", str(target), str(other_snap))
    _assert_exit2(result)
    assert result.stdout == ""

    unborn = tmp_path / "unborn"
    unborn.mkdir()
    _git(unborn, env, "init", "-q", "-b", "master")
    unborn_out = tmp_path / "snaps" / "unborn.json"
    _assert_exit2(_run(tmp_path, env, "snapshot", str(unborn), str(unborn_out)))
    assert not unborn_out.exists()
