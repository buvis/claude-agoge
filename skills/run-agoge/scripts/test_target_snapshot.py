"""Core snapshot and compare behavior: refs, HEAD, index, work tree, restore commands, input errors."""
import json
import os
import shlex
import shutil
import subprocess

import pytest

import target_snapshot
from snapshot_fixtures import (
    NOTES_V1, NOTES_V2, SHARED_PREFIX, _assert_exit2, _build_target, _compare,
    _copy_target, _git, _git_dir_state, _run, _sha, _snap, _write_packed_refs,
)

STAGED = SHARED_PREFIX + b"staged edit\n"

MALFORMED_SNAPSHOT_KEYS = [
    "repo", "config", "index", "head", "refs", "worktree_heads", "submodules",
    "dirty", "untracked_fingerprints", "gitdir", "worktrees", "untracked",
    "ignored",
]


@pytest.mark.parametrize("key", MALFORMED_SNAPSHOT_KEYS)
def test_snapshot_missing_field_is_rejected_by_name(tmp_path, template_target, key):
    target, env = _copy_target(template_target, tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    del snapshot[key]
    malformed = tmp_path / "snaps" / "missing-field.json"
    malformed.parent.mkdir(exist_ok=True)
    malformed.write_text(json.dumps(snapshot))
    result = _run(tmp_path, env, "compare", str(target), str(malformed))
    _assert_exit2(result)
    assert result.stdout == ""
    assert result.stderr.strip() == (
        f"target_snapshot: snapshot {malformed} is malformed: {key}"
    )


WRONG_TYPE_VALUES = {
    "repo": 1,
    "config": 1,
    "index": 1,
    "head": "x",
    "refs": "abc",
    "worktree_heads": "abc",
    "submodules": "abc",
    "dirty": "abc",
    "untracked_fingerprints": "abc",
    "gitdir": "abc",
    "worktrees": "abc",
    "untracked": "abc",
    "ignored": "abc",
}


@pytest.mark.parametrize("key", MALFORMED_SNAPSHOT_KEYS)
def test_snapshot_wrongly_typed_field_is_rejected_by_name(tmp_path, template_target, key):
    target, env = _copy_target(template_target, tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["untracked"] == ["scratch.txt"]

    data = {**snapshot, key: WRONG_TYPE_VALUES[key]}
    malformed = tmp_path / "snaps" / f"wrongtype-{key}.json"
    malformed.parent.mkdir(exist_ok=True)
    malformed.write_text(json.dumps(data))
    result = _run(tmp_path, env, "compare", str(target), str(malformed))
    _assert_exit2(result)
    assert result.stdout == "", key
    assert result.stderr.strip() == (
        f"target_snapshot: snapshot {malformed} is malformed: {key}"
    ), key


@pytest.mark.parametrize("value", ["x", True])
def test_snapshot_non_int_ignored_overflow_is_rejected_by_name(tmp_path, template_target, value):
    target, env = _copy_target(template_target, tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    malformed = tmp_path / "snaps" / "wrongtype-ignored_overflow.json"
    malformed.parent.mkdir(exist_ok=True)
    malformed.write_text(json.dumps({**snapshot, "ignored_overflow": value}))
    result = _run(tmp_path, env, "compare", str(target), str(malformed))
    _assert_exit2(result)
    assert result.stdout == ""
    assert result.stderr.strip() == (
        f"target_snapshot: snapshot {malformed} is malformed: ignored_overflow"
    )


def test_snapshot_untracked_fingerprints_missing_entry_is_rejected(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["untracked"] == ["scratch.txt"]

    fingerprints_missing_entry = dict(snapshot["untracked_fingerprints"])
    del fingerprints_missing_entry["scratch.txt"]
    data = {**snapshot, "untracked_fingerprints": fingerprints_missing_entry}
    malformed = tmp_path / "snaps" / "wrongtype-untracked_fingerprints-missing.json"
    malformed.parent.mkdir(exist_ok=True)
    malformed.write_text(json.dumps(data))
    result = _run(tmp_path, env, "compare", str(target), str(malformed))
    _assert_exit2(result)
    assert result.stdout == ""
    assert result.stderr.strip() == (
        f"target_snapshot: snapshot {malformed} is malformed: untracked_fingerprints"
    )


def test_snapshot_float_or_bool_version_is_rejected(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    for name, version in (("float", float(target_snapshot.VERSION)), ("bool", True)):
        malformed = tmp_path / "snaps" / f"version-{name}.json"
        malformed.parent.mkdir(exist_ok=True)
        malformed.write_text(json.dumps({**snapshot, "version": version}))
        result = _run(tmp_path, env, "compare", str(target), str(malformed))
        _assert_exit2(result)
        assert result.stdout == "", name
        assert result.stderr.strip() == (
            f"target_snapshot: snapshot {malformed} is not version {target_snapshot.VERSION}"
        ), name


def test_untouched_target_compares_unchanged(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_snapshot_and_compare_write_nothing_in_target(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_new_commit_on_current_branch_is_one_ref_violation_with_commit(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_new_tag_is_ref_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_moved_remote_tracking_ref_is_ref_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_branch_switch_is_head_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_moved_detached_head_is_head_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_deleted_ref_is_ref_violation_with_recreating_restore(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_staged_change_is_index_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_editing_already_modified_file_is_tracked_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_reverting_modified_file_is_tracked_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_removed_untracked_file_is_untracked_removed_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    (target / "scratch.txt").write_text("scratch\n")
    (target / "scratch.txt.keep").write_text("keep\n")
    before = _snap(tmp_path, target, env)
    (target / "scratch.txt").unlink()
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert report["status"] == "changed"
    assert report["violations"] == [{"kind": "untracked-removed", "path": "scratch.txt"}]
    assert report["touched"] == []


def test_new_untracked_file_is_touched_and_exits_zero(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_allowed_path_is_not_tracked_removed_or_touched(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_allow_directory_exempts_its_removed_contents(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    (target / ".gitignore").write_text("igndir/\n")
    _git(target, env, "add", ".gitignore")
    _git(target, env, "commit", "-q", "-m", "add gitignore")
    (target / "igndir").mkdir()
    (target / "igndir" / "f").write_text("f\n")
    (target / "igndir" / "sub").mkdir()
    (target / "igndir" / "sub" / "g").write_text("g\n")
    (target / "untdir").mkdir()
    (target / "untdir" / "f").write_text("f\n")
    (target / "untdir" / "sub").mkdir()
    (target / "untdir" / "sub" / "g").write_text("g\n")
    before = _snap(tmp_path, target, env)

    shutil.rmtree(target / "igndir")
    shutil.rmtree(target / "untdir")

    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    kinds = {v["kind"] for v in report["violations"]}
    assert "ignored-removed" in kinds
    assert "untracked-removed" in kinds

    for allow in (("igndir", "untdir"), ("igndir/", "untdir/")):
        code, report = _compare(tmp_path, target, before, env, allow=allow)
        assert code == 0
        assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_allow_prefix_matches_whole_components_only(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    (target / ".gitignore").write_text("igndir/\n")
    _git(target, env, "add", ".gitignore")
    _git(target, env, "commit", "-q", "-m", "add gitignore")
    (target / "igndir").mkdir()
    (target / "igndir" / "f").write_text("f\n")
    before = _snap(tmp_path, target, env)
    shutil.rmtree(target / "igndir")

    # "ign" is a prefix of "igndir" but not a whole path component: it must
    # not exempt anything under igndir.
    code, report = _compare(tmp_path, target, before, env, allow=("ign",))
    assert code == 1
    assert any(
        v["kind"] == "ignored-removed" and v.get("path", "").startswith("igndir")
        for v in report["violations"]
    )

    code, report = _compare(tmp_path, target, before, env, allow=("igndir",))
    assert code == 0
    assert report["violations"] == []

    # An exact file path exempts that file only, not a same-prefix sibling.
    before2 = _snap(tmp_path, target, env, name="before2.json")
    (target / "notes.txt").write_bytes(NOTES_V2)
    code, report = _compare(tmp_path, target, before2, env, allow=("notes.txt",))
    assert code == 0
    assert report["violations"] == []

    code, report = _compare(tmp_path, target, before2, env, allow=("notes",))
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("tracked", "notes.txt"),
    ]


def test_restore_commands_put_refs_back(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_tracked_dir_replaced_by_external_symlink_does_not_follow_traversal(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_compare_in_one_process_rechecks_swapped_directory(tmp_path, monkeypatch):
    target, env = _build_target(tmp_path)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sub = target / "sub"
    sub.mkdir()
    (sub / "child.txt").write_text("child v1\n")
    _git(target, env, "add", "-A")
    _git(target, env, "commit", "-q", "-m", "add sub/child.txt")
    (sub / "child.txt").write_text("child v2\n")

    before = target_snapshot.take_snapshot(os.path.realpath(target))

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "child.txt").write_text("not the real child\n")
    _git(target, env, "rm", "-q", "-r", "--cached", "sub")
    shutil.rmtree(sub)
    sub.symlink_to(outside)

    report = target_snapshot.compare(os.path.realpath(target), before, set())
    violations = {v["path"]: v for v in report["violations"] if v["kind"] == "tracked"}
    after = violations["sub/child.txt"]["after"]
    assert "external-symlink" in after
    assert _sha(b"not the real child\n") not in after


def test_fingerprint_of_very_deep_path_is_absent(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    real = os.path.realpath(repo)
    deep = "d/" * 3000 + "f.txt"
    assert target_snapshot._fingerprint(real, deep) == "absent"


def test_file_below_nested_external_symlink_is_external(tmp_path):
    repo = tmp_path / "target"
    (repo / "inner").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "sub").mkdir(parents=True)
    (outside / "sub" / "deep.txt").write_text("deep\n")
    (repo / "out-link").symlink_to(outside)
    (repo / "inner" / "out-nested").symlink_to(outside)
    real = os.path.realpath(repo)
    assert target_snapshot._fingerprint(real, "out-link/sub/deep.txt") == "external-symlink"
    assert target_snapshot._fingerprint(
        real, "inner/out-nested/sub/deep.txt"
    ) == "external-symlink"


def test_unusable_inputs_exit_2_with_prefixed_stderr(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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

    other, _ = _copy_target(template_target, tmp_path, name="other")
    other_snap = _snap(tmp_path, other, env, name="other.json")
    result = _run(tmp_path, env, "compare", str(target), str(other_snap))
    _assert_exit2(result)
    assert result.stdout == ""

    # Same basename, different real path: still another repo.
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    twin_a, _ = _copy_target(template_target, tmp_path, name="a/target")
    twin_b, _ = _copy_target(template_target, tmp_path, name="b/target")
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


def test_previous_version_snapshot_exits_2_with_one_line(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    before = _snap(tmp_path, target, env)
    snapshot = json.loads(before.read_text())
    assert snapshot["version"] == target_snapshot.VERSION
    assert target_snapshot.VERSION == 5

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


def test_repo_dir_with_trailing_space_round_trips(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path, name="target ")
    before = _snap(tmp_path, target, env)
    assert json.loads(before.read_text())["repo"] == os.path.realpath(target)
    code, report = _compare(tmp_path, target, before, env)
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}


def test_non_utf8_refs_round_trip_through_snapshot(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_non_utf8_paths_round_trip(tmp_path, template_target):
    repo_name = os.fsdecode(b"target-\xff")
    tracked_name = os.fsdecode(b"tracked-\xfe.txt")
    untracked_name = os.fsdecode(b"untracked-\xfd.txt")
    later_name = os.fsdecode(b"later-\xfc.txt")
    try:
        target, env = _copy_target(template_target, tmp_path, name=repo_name)
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


def test_unreadable_dirty_file_exits_2_with_one_line(tmp_path, template_target):
    if os.geteuid() == 0:
        pytest.skip("root reads files regardless of mode")
    target, env = _copy_target(template_target, tmp_path)
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


def test_unreadable_untracked_file_exits_2_with_one_line(tmp_path, template_target):
    if os.geteuid() == 0:
        pytest.skip("root reads files regardless of mode")
    target, env = _copy_target(template_target, tmp_path)
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


def test_fifo_in_place_of_tracked_file_does_not_hang(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    before = _snap(tmp_path, target, env)
    notes = target / "notes.txt"
    notes.unlink()
    os.mkfifo(notes)
    try:
        result = _run(tmp_path, env, "compare", str(target), str(before), timeout=10)
    except subprocess.TimeoutExpired:
        pytest.fail("compare hung on a tracked path replaced by a FIFO")
    assert result.returncode in (0, 1), result.stderr


def test_fifo_replaced_by_file_is_tracked_violation(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
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


def test_fingerprinting_many_files_stats_each_file_once(tmp_path, monkeypatch):
    repo = tmp_path / "target"
    leaves = [f"top{i}/leaf{i}" for i in range(4)]
    paths = []
    for leaf in leaves:
        (repo / leaf).mkdir(parents=True)
        for n in range(50):
            rel = f"{leaf}/file{n}.txt"
            (repo / rel).write_bytes(rel.encode())
            paths.append(rel)
    real = os.path.realpath(repo)
    calls = []
    real_lstat = os.lstat

    def counting_lstat(path, *args, **kwargs):
        calls.append(path)
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", counting_lstat)
    prints = {path: target_snapshot._fingerprint(real, path) for path in paths}
    monkeypatch.undo()
    assert len(calls) <= 200 + 2 * 4 + 10, len(calls)
    assert prints == {path: _sha(path.encode()) for path in paths}


def test_fingerprints_unchanged_by_symlink_cache(tmp_path):
    repo = tmp_path / "target"
    (repo / "inner").mkdir(parents=True)
    outside = tmp_path / "target-outside"
    outside.mkdir()
    (outside / "leak.txt").write_bytes(b"outside bytes\n")
    (repo / "a.txt").write_bytes(b"alpha\n")
    (repo / "b.txt").write_bytes(b"beta\n")
    (repo / "inner" / "c.txt").write_bytes(b"gamma\n")
    os.symlink("a.txt", repo / "link-a")
    os.symlink("b.txt", repo / "link-b")
    os.symlink(str(outside / "leak.txt"), repo / "link-out")
    os.symlink("inner", repo / "inner-link")
    os.symlink(str(outside), repo / "out-link")
    os.mkfifo(repo / "pipe")
    real = os.path.realpath(repo)
    fp = target_snapshot._fingerprint
    for _ in range(2):
        assert fp(real, "a.txt") == _sha(b"alpha\n")
        assert fp(real, "b.txt") == _sha(b"beta\n")
        assert fp(real, "link-a") == "link:" + _sha(b"a.txt")
        assert fp(real, "link-b") == "link:" + _sha(b"b.txt")
        assert fp(real, "link-out") == "link:" + _sha(os.fsencode(str(outside / "leak.txt")))
        assert fp(real, "out-link") == "link:" + _sha(os.fsencode(str(outside)))
        assert fp(real, "pipe") == "special:10000"
        assert fp(real, "inner") == "dir"
        assert fp(real, "missing.txt") == "absent"
        assert fp(real, "inner/missing.txt") == "absent"
        assert fp(real, "inner/c.txt") == _sha(b"gamma\n")
        assert fp(real, "inner-link/c.txt") == _sha(b"gamma\n")
        assert fp(real, "out-link/leak.txt") == "external-symlink"
        assert fp(real, "out-link/nothing.txt") == "external-symlink"


def test_fingerprint_of_unreadable_file_raises(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads files regardless of mode")
    repo = tmp_path / "target"
    repo.mkdir()
    locked = repo / "locked.txt"
    locked.write_bytes(b"secret\n")
    locked.chmod(0o000)
    try:
        with pytest.raises(target_snapshot.Fail, match="cannot read locked.txt: permission denied"):
            target_snapshot._fingerprint(os.path.realpath(repo), "locked.txt")
    finally:
        locked.chmod(0o644)


def _mib_pattern(seed):
    """1 MiB of non-uniform, deterministic bytes, distinct for different seeds."""
    return bytes((i + seed) % 256 for i in range(256)) * 4096


def test_file_at_cap_is_hashed_whole(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    big = repo / "big.bin"
    size = target_snapshot.SAMPLE_ABOVE
    big.touch()
    os.truncate(big, size)
    assert big.stat().st_size == size
    real = os.path.realpath(repo)
    assert target_snapshot._fingerprint(real, "big.bin") == _sha(b"\0" * size)


def test_file_above_cap_is_sampled(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    big = repo / "big.bin"
    size = target_snapshot.SAMPLE_ABOVE + 1
    mib = 1024 * 1024
    head = _mib_pattern(0)
    tail = _mib_pattern(128)
    with open(big, "wb") as handle:
        handle.write(head)
        handle.truncate(size)
        handle.seek(size - mib)
        handle.write(tail)
    assert big.stat().st_size == size
    real = os.path.realpath(repo)
    expected = f"sample:{size}:{_sha(head + tail)}"
    assert target_snapshot._fingerprint(real, "big.bin") == expected


def test_sampled_file_head_tail_and_size_edits_are_reported(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    big = target / "big.bin"
    size = target_snapshot.SAMPLE_ABOVE + 1
    with open(big, "wb") as handle:
        handle.write(b"h")
        handle.truncate(size)
    before = _snap(tmp_path, target, env)

    # A change to the first byte must be detected.
    with open(big, "r+b") as handle:
        handle.seek(0)
        handle.write(b"H")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("untracked-modified", "big.bin"),
    ]

    # Revert, then change the last byte: also detected.
    with open(big, "r+b") as handle:
        handle.seek(0)
        handle.write(b"h")
    with open(big, "r+b") as handle:
        handle.seek(size - 1)
        handle.write(b"T")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("untracked-modified", "big.bin"),
    ]

    # Revert, then append one byte: the size change alone is detected.
    with open(big, "r+b") as handle:
        handle.seek(size - 1)
        handle.write(b"\0")
    with open(big, "ab") as handle:
        handle.write(b"\0")
    code, report = _compare(tmp_path, target, before, env)
    assert code == 1
    assert [(v["kind"], v["path"]) for v in report["violations"]] == [
        ("untracked-modified", "big.bin"),
    ]


def test_untracked_mode_change_is_not_reported(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    scratch = target / "scratch.txt"
    scratch.write_text("scratch\n")
    scratch.chmod(0o644)
    before = _snap(tmp_path, target, env)
    scratch.chmod(0o755)
    try:
        code, report = _compare(tmp_path, target, before, env)
        assert code == 0
        assert report == {"status": "unchanged", "violations": [], "touched": []}
    finally:
        scratch.chmod(0o644)

    doc = " ".join(target_snapshot.__doc__.split())
    assert "Permission bits of untracked files are not checked; only content, file type and symlink target are." in doc


def test_untracked_file_replaced_by_fifo_reads_as_removed(tmp_path, template_target):
    target, env = _copy_target(template_target, tmp_path)
    scratch = target / "u.txt"
    scratch.write_text("scratch\n")
    before = _snap(tmp_path, target, env)
    scratch.unlink()
    os.mkfifo(scratch)
    try:
        result = _run(tmp_path, env, "compare", str(target), str(before), timeout=10)
    except subprocess.TimeoutExpired:
        pytest.fail("compare hung on an untracked path replaced by a FIFO")
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["violations"] == [{"kind": "untracked-removed", "path": "u.txt"}]

    code, report = _compare(tmp_path, target, before, env, allow=("u.txt",))
    assert code == 0
    assert report == {"status": "unchanged", "violations": [], "touched": []}

    doc = " ".join(target_snapshot.__doc__.split())
    assert (
        "An untracked path replaced by a fifo, socket or device reads as "
        "untracked-removed, because git does not list such files."
    ) in doc
