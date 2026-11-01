import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

from test_scratch_contract import (
    CONTRACT_PATH,
    FENCE_RE,
    SKILL_PATH,
    _build_incident_fixture,
    _env_for,
    _refs,
)

SNAPSHOT_SCRIPT = Path(__file__).resolve().parent / "target_snapshot.py"
PROFILE_PATHS = (
    "docs/dev/project-management/meta/agoge-profile.md",
    "docs/dev/project-management/agoge-profile.md",
)
B4 = (
    "**The master checks.** It snapshots the target's HEAD, refs, index, tracked "
    "files, worktrees and local git config before recon and again before the "
    "lanes, and compares after each. Any change fails the whole run, and the "
    "report names it. Files the product itself writes into its checkout when you "
    "run it are listed, not failed."
)
DO_NOT_PUSH = (
    "Do not push this repository until you have run or rejected the restore "
    "commands above."
)


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _section(text, start, end):
    return text[text.index(start):text.index(end)]


def _find(pattern, text, pos):
    match = re.compile(pattern).search(text, pos)
    assert match, f"{pattern!r} not found after offset {pos}"
    return match


def test_run_integrity_wiring():
    text = SKILL_PATH.read_text()
    step1 = _section(text, "### 1. Resolve the target", "### 2. Profile")
    _find(r"target_snapshot\.py\s+snapshot\b[\s\S]{0,300}?start\.json", step1, 0)

    step3 = _section(text, "### 3. Dispatch the armed specialists", "### 4. Audit the statuses")
    recon = _find(r"target_snapshot\.py\s+compare\b[\s\S]{0,300}?start\.json", step3, 0)
    lanes_snap = _find(
        r"target_snapshot\.py\s+snapshot\b[\s\S]{0,300}?lanes\.json", step3, recon.end()
    )
    _find(r"target_snapshot\.py\s+compare\b[\s\S]{0,300}?lanes\.json", step3, lanes_snap.end())

    allowed = step3[recon.start():lanes_snap.start()]
    assert "--allow" in allowed
    for path in PROFILE_PATHS:
        assert re.search(re.escape(path) + r"(?![\w/.-])", allowed), path


def test_run_integrity_authoring():
    text = SKILL_PATH.read_text()
    step6 = _flat(_section(text, "### 6. Author, if the profile assigns it", "### 7. Report"))
    assert "a target comparison in step 3 did not exit 0" in step6
    assert re.search(r"\b(never|neither)\b[^.]*\bruns?\b[^.]*\brestore\b", _flat(text), re.I)


def test_run_integrity_contract():
    text = CONTRACT_PATH.read_text()
    scratch = _section(text, "## Scratch contract", "## Report contract")
    assert _flat(scratch).strip().endswith(B4)


def test_run_integrity_report():
    text = CONTRACT_PATH.read_text()
    markdown = _section(text, "### The markdown report", "### The walkthrough packet")
    item1 = _flat(_section(markdown, "1. **Summary header**", "2. **Findings**"))
    assert "Target integrity: unchanged" in item1
    assert "Target integrity: changed" in item1
    assert DO_NOT_PUSH in item1


def test_run_integrity_sidecar():
    text = CONTRACT_PATH.read_text()
    sidecar = _section(text, "### The JSON sidecar", "## Strategy profile contract")
    blocks = []
    for match in FENCE_RE.finditer(sidecar):
        try:
            blocks.append(json.loads(match.group(1)))
        except ValueError:
            continue
    integrity = [b["target_integrity"] for b in blocks if isinstance(b, dict) and "target_integrity" in b]
    assert integrity, "no sidecar JSON block carries target_integrity"
    block = integrity[0]
    for key in ("status", "violations", "touched"):
        assert key in block
    violation = block["violations"][0]
    for key in ("phase", "kind", "restore"):
        assert key in violation


def test_run_integrity_incident(tmp_path):
    fixture = _build_incident_fixture(tmp_path)
    env = _env_for(tmp_path)
    target = fixture["target"]
    start = tmp_path / "start.json"

    subprocess.run(
        [sys.executable, str(SNAPSHOT_SCRIPT), "snapshot", str(target), str(start)],
        env=env, check=True, capture_output=True, text=True,
    )
    before_refs = json.loads(start.read_text())["refs"]

    for cmd in (
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "chore(probe): seed scratch dotfiles"],
        ["git", "tag", "v1.0.0"],
        ["git", "update-ref", "refs/remotes/origin/master", "HEAD"],
    ):
        subprocess.run(cmd, cwd=target, env=env, check=True)

    result = subprocess.run(
        [sys.executable, str(SNAPSHOT_SCRIPT), "compare", str(target), str(start)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "changed"
    refs = [v for v in report["violations"] if v["kind"] == "ref"]
    assert sorted(v["ref"] for v in refs) == [
        "refs/heads/master",
        "refs/remotes/origin/master",
        "refs/tags/v1.0.0",
    ]

    for violation in refs:
        subprocess.run(shlex.split(violation["restore"]), env=env, check=True)
    after = subprocess.run(
        ["git", "--no-optional-locks", "for-each-ref"],
        cwd=target, env=env, capture_output=True, text=True, check=True,
    ).stdout
    assert _refs(after) == before_refs
