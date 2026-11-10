import hashlib
import json
import os
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

# A shared 20-byte prefix: the versions differ only after byte 16, so a
# fingerprint that hashes a prefix instead of the whole file cannot pass.
SHARED_PREFIX = b"x" * 20
NOTES_V1 = SHARED_PREFIX + b"v1\n"
NOTES_V2 = SHARED_PREFIX + b"v2\n"


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


def _write_packed_refs(target, sha, *names):
    header = b"# pack-refs with: peeled fully-peeled sorted \n"
    lines = b"".join(sha.encode() + b" " + name + b"\n" for name in sorted(names))
    (target / ".git" / "packed-refs").write_bytes(header + lines)


def _add_submodule(tmp_path, target, env):
    sub_src, _ = _build_target(tmp_path, name="sub-src")
    _git(target, env, "-c", "protocol.file.allow=always",
         "submodule", "add", "-q", str(sub_src), "sub")
    _git(target, env, "commit", "-q", "-m", "add submodule")
    return target / "sub"


def _pair_env(env, *pairs):
    """`env` plus `pairs` carried over git's command-scope environment."""
    extra = {"GIT_CONFIG_COUNT": str(len(pairs))}
    for index, (key, value) in enumerate(pairs):
        extra[f"GIT_CONFIG_KEY_{index}"] = key
        extra[f"GIT_CONFIG_VALUE_{index}"] = str(value)
    return {**env, **extra}


def _assert_scratch_ignored(snapshot, dropped):
    """An inherited `core.excludesFile` must still make scratch.txt ignored."""
    assert "scratch.txt" not in snapshot["untracked"], (
        f"{dropped}: {snapshot['untracked']}"
    )
    assert "scratch.txt" in snapshot["ignored"], (
        f"{dropped}: {snapshot['ignored']}"
    )
