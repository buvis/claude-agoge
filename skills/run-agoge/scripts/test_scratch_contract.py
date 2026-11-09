import os
import re
import shlex
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CONTRACT_PATH = REPO_ROOT / "skills/run-agoge/references/finding-contract.md"
SKILL_PATH = REPO_ROOT / "skills/run-agoge/SKILL.md"
LANE = "heidi"  # names the fixture's lane-dir segment, matching the PRD's heidi example — its only use
AGENT_FILES = [
    REPO_ROOT / "agents/walter.md",
    REPO_ROOT / "agents/heidi.md",
    REPO_ROOT / "agents/judy.md",
    REPO_ROOT / "agents/wendy.md",
    REPO_ROOT / "agents/peggy.md",
    REPO_ROOT / "agents/trudy.md",
    REPO_ROOT / "agents/olivia.md",
]

TEST_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@test.local",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@test.local",
}

A7 = (
    'R="$LANE/t7/roots/heidi-repo"\n'
    'git -C "$R" add -A\n'
    'git -C "$R" commit -q -m "chore(probe): seed scratch dotfiles"\n'
    'git -C "$R" tag v1.0.0\n'
    'git -C "$R" update-ref refs/remotes/origin/master HEAD\n'
)

FENCE_RE = re.compile(r"```(?:[\w-]+)?\n(.*?)```", re.DOTALL)


def _env_for(tmp_path):
    return {**TEST_ENV, "HOME": str(tmp_path)}


def _snapshot(target, env):
    for_each_ref = subprocess.run(
        ["git", "--no-optional-locks", "for-each-ref"],
        cwd=target, env=env, capture_output=True, text=True, check=True,
    ).stdout
    ls_files = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=target, env=env, capture_output=True, text=True, check=True,
    ).stdout
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=target, env=env, capture_output=True, text=True, check=True,
    ).stdout
    return (for_each_ref, ls_files, status)


def _refs(for_each_ref_output):
    refs = {}
    for line in for_each_ref_output.splitlines():
        if not line:
            continue
        sha, _type, ref = line.split(None, 2)
        refs[ref] = sha
    return refs


def _build_incident_fixture(tmp_path):
    env = _env_for(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, env=env, check=True)
    (target / "README.md").write_text("seed\n")
    subprocess.run(["git", "add", "-A"], cwd=target, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=target, env=env, check=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/master", "HEAD"],
        cwd=target, env=env, check=True,
    )
    (target / "untracked.txt").write_text("scratch\n")

    lane_dir = target / "docs/dev/tmp/agoge" / LANE
    lane_dir.mkdir(parents=True)
    repo_git = lane_dir / "t7/roots/heidi-repo/.git"
    (repo_git / "info").mkdir(parents=True)
    (repo_git / "description").write_text(
        "Unnamed repository; edit this file to name it for gitweb.\n"
    )

    def snapshot():
        return _snapshot(target, env)

    return {"target": target, "lane_dir": lane_dir, "snapshot": snapshot}


def _extract_preamble_block(contract_text):
    for match in FENCE_RE.finditer(contract_text):
        block = match.group(1)
        if "GIT_CEILING_DIRECTORIES" in block:
            return block
    raise AssertionError("no fenced bash block containing GIT_CEILING_DIRECTORIES found")


def test_scratch_contract_mechanisms():
    text = CONTRACT_PATH.read_text()
    for token in ("mktemp -d", "set -eu", "GIT_CEILING_DIRECTORIES", "--git-dir", "read-only"):
        assert token in text


def test_scratch_contract_incident_preamble(tmp_path):
    fixture = _build_incident_fixture(tmp_path)
    env = _env_for(tmp_path)
    before = fixture["snapshot"]()

    contract_text = CONTRACT_PATH.read_text()
    preamble = _extract_preamble_block(contract_text)
    preamble = preamble.replace(
        "<the path mktemp printed>",
        shlex.quote(str(fixture["lane_dir"].resolve())),
    )
    script = preamble + "\n" + A7

    result = subprocess.run(
        ["bash", "-c", script],
        env={**env, "LANE": str(fixture["lane_dir"])},
        cwd=fixture["target"],
        capture_output=True,
        text=True,
    )

    after = fixture["snapshot"]()

    assert result.returncode != 0
    assert "not a git repository" in result.stderr
    assert before == after


def test_scratch_contract_incident_control(tmp_path):
    fixture = _build_incident_fixture(tmp_path)
    env = {**_env_for(tmp_path), "LANE": str(fixture["lane_dir"])}
    target = fixture["target"]

    before = _refs(
        subprocess.run(
            ["git", "--no-optional-locks", "for-each-ref"],
            cwd=target, env=env, capture_output=True, text=True, check=True,
        ).stdout
    )

    subprocess.run(["bash", "-c", A7], env=env, cwd=target, capture_output=True, text=True)

    after = _refs(
        subprocess.run(
            ["git", "--no-optional-locks", "for-each-ref"],
            cwd=target, env=env, capture_output=True, text=True, check=True,
        ).stdout
    )

    assert after["refs/heads/master"] != before["refs/heads/master"]
    assert "refs/tags/v1.0.0" in after
    assert after["refs/remotes/origin/master"] != before["refs/remotes/origin/master"]


def _extract_scratch_contract_section(contract_text):
    start = contract_text.index("## Scratch contract")
    rest = contract_text[start + len("## Scratch contract"):]
    end = rest.index("\n## ")
    return contract_text[start:start + len("## Scratch contract") + end]


def test_scratch_contract_sets_identity_with_env():
    section = _extract_scratch_contract_section(CONTRACT_PATH.read_text())
    assert "env GIT_AUTHOR_NAME=agoge-" in section
    assert "-c user.name=" not in section
    assert "never `export` one" in section


def test_env_identity_beats_exported_author(tmp_path):
    section = _extract_scratch_contract_section(CONTRACT_PATH.read_text())
    match = re.search(r"`(env GIT_AUTHOR_NAME=agoge-<lane>[^`]*)`", section)
    assert match, "no env-prefixed git identity command found in scratch contract"
    template = match.group(1)

    scratch = tmp_path / "scratch"
    repo = "probe-repo"
    repo_dir = scratch / repo
    repo_dir.mkdir(parents=True)

    # The shell truly has an exported, inherited identity the command must beat.
    env = {
        **_env_for(tmp_path),
        "GIT_AUTHOR_NAME": "Operator Name",
        "GIT_COMMITTER_NAME": "Operator Name",
    }
    export_preamble = (
        'export GIT_AUTHOR_NAME="Operator Name"\n'
        'export GIT_COMMITTER_NAME="Operator Name"\n'
    )

    subprocess.run(["git", "init", "-q", str(repo_dir)], env=env, check=True)
    (repo_dir / "probe.txt").write_text("scratch\n")
    subprocess.run(
        ["git", "--git-dir", str(repo_dir / ".git"), "--work-tree", str(repo_dir), "add", "-A"],
        env=env, check=True,
    )

    command = (
        template
        .replace("<lane>", LANE)
        .replace("$SCRATCH", str(scratch))
        .replace("<repo>", repo)
        .replace("<command>", 'commit -q -m "chore(probe): seed scratch dotfiles"')
    )
    result = subprocess.run(
        ["bash", "-c", export_preamble + command],
        cwd=repo_dir, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    log_fields = subprocess.run(
        ["git", "--git-dir", str(repo_dir / ".git"), "log", "-1", "--format=%an%n%ae%n%cn%n%ce"],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    assert log_fields == [
        f"agoge-{LANE}", f"agoge-{LANE}@example.invalid",
        f"agoge-{LANE}", f"agoge-{LANE}@example.invalid",
    ]

    # Premise control: the OLD `-c user.name=` form (no `env` prefix) loses to
    # the exported identity, proving an export really does beat `-c` and that
    # this test would have failed against the old contract/command form.
    (repo_dir / "probe2.txt").write_text("scratch2\n")
    subprocess.run(
        ["git", "--git-dir", str(repo_dir / ".git"), "--work-tree", str(repo_dir), "add", "-A"],
        env=env, check=True,
    )
    old_command = (
        f'git --git-dir="{repo_dir}/.git" --work-tree="{repo_dir}" '
        f"-c user.name=agoge-{LANE} -c user.email=agoge-{LANE}@example.invalid "
        'commit -q -m "chore(probe): seed scratch dotfiles two"'
    )
    control_result = subprocess.run(
        ["bash", "-c", export_preamble + old_command],
        cwd=repo_dir, env=env, capture_output=True, text=True,
    )
    assert control_result.returncode == 0, control_result.stderr

    control_author = subprocess.run(
        ["git", "--git-dir", str(repo_dir / ".git"), "log", "-1", "--format=%an"],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert control_author == "Operator Name"


def test_scratch_contract_charter():
    for path in AGENT_FILES:
        text = path.read_text()
        normalized = re.sub(r"\s+", " ", text).lower()
        assert "scratch contract" in normalized


def test_scratch_contract_prompt():
    text = SKILL_PATH.read_text()
    dispatch_heading = "### 3. Dispatch the armed specialists"
    recon_heading = "## The recon prompt"
    dispatch_idx = text.index(dispatch_heading)
    recon_idx = text.index(recon_heading)
    dispatch_slice = text[dispatch_idx:recon_idx]
    recon_slice = text[recon_idx:]
    assert "## Scratch contract" in dispatch_slice
    assert "## Scratch contract" in recon_slice
