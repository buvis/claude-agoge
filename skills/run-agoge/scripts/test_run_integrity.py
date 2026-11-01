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


COMMENT_RE = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
BASH_FENCE_RE = re.compile(r"^```bash[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
# One shell word: <placeholder> chunks or plain characters, never a redirect,
# pipe, list operator or comment.
_WORD = r"(?:<[^<>\n]*>|[^\s<>|;&#`])+"
_SCRIPT = r'"?[^\s<>|;&#`"]*target_snapshot\.py"?'


def _invocation(verb, name, tail=""):
    return re.compile(rf"python3 {_SCRIPT} {verb} {_WORD} {_WORD}/{re.escape(name)}{tail}")


SNAP_START = _invocation("snapshot", "start.json")
COMPARE_START = _invocation("compare", "start.json", r"(?P<allows>(?: --allow [^\s<>|;&#`]+)+)")
SNAP_LANES = _invocation("snapshot", "lanes.json")
COMPARE_LANES = _invocation("compare", "lanes.json")
DISPATCH = "Dispatch every armed specialist **in one message**"
SKIP_SENTENCE = (
    "Skip the step, and say so in the report, when the profile assigns no "
    "authoring, no finding survived step 4 as `verified`, the target's tree is "
    "dirty, or a target comparison in step 3 did not exit 0."
)
RESTORE_BAN = (
    "**Never run a `restore` command the comparison prints.** It changes the "
    "operator's repository, and only the operator decides."
)


def _live(text):
    """The text with HTML comments removed: nothing inside one ever runs."""
    return COMMENT_RE.sub("", text)


def _commands(section):
    """(offset, command) for each logical line of each bash fence in section.

    Shell comments are dropped and backslash continuations joined, so a
    command is what the shell would run, not what a trailing comment says.
    """
    out = []
    for fence in BASH_FENCE_RE.finditer(section):
        offset, parts, start = fence.start(1), [], None
        for line in fence.group(1).splitlines(keepends=True):
            code = re.sub(r"(?:^|\s)#.*$", "", line.rstrip("\n")).rstrip()
            start = offset if start is None else start
            offset += len(line)
            if code.endswith("\\"):
                parts.append(code[:-1])
                continue
            parts.append(code)
            command = " ".join(" ".join(parts).split())
            if command:
                out.append((start, command))
            parts, start = [], None
    return out


def _sentence(phrase):
    """A regex for phrase opening a sentence or paragraph, any whitespace between words."""
    return r"(?:\A|[.!?:]\s+|\n\s*\n)\**" + r"\s+".join(map(re.escape, phrase.split()))


def _only(pattern, commands, where):
    hits = [(offset, m) for offset, cmd in commands if (m := pattern.fullmatch(cmd))]
    assert len(hits) == 1, f"{where}: {len(hits)} invocations match {pattern.pattern!r}"
    return hits[0]


def test_run_integrity_wiring():
    text = _live(SKILL_PATH.read_text())
    strict = (SNAP_START, COMPARE_START, SNAP_LANES, COMPARE_LANES)
    for _, cmd in _commands(text):
        if "target_snapshot" in cmd:
            assert any(p.fullmatch(cmd) for p in strict), f"loose invocation: {cmd}"

    step1 = _section(text, "### 1. Resolve the target", "### 2. Profile")
    _only(SNAP_START, _commands(step1), "step 1")
    assert re.search(_sentence("If the snapshot exits 2, stop before recon"), step1)

    step3 = _section(text, "### 3. Dispatch the armed specialists", "### 4. Audit the statuses")
    assert step3.count(DISPATCH) == 1, "step 3 must name the dispatch exactly once"
    dispatch = step3.index(DISPATCH)
    commands = _commands(step3)
    recon_at, recon = _only(COMPARE_START, commands, "step 3")
    snap_at, _ = _only(SNAP_LANES, commands, "step 3")
    lanes_at, _ = _only(COMPARE_LANES, commands, "step 3")
    assert recon_at < snap_at < dispatch < lanes_at, "lanes must be snapshot before dispatch, compared after"

    allows = re.findall(r"--allow (\S+)", recon.group("allows"))
    assert sorted(allows) == sorted(PROFILE_PATHS), allows

    stop = re.compile(_sentence("If it exits 1 or 2, dispatch nobody and go to step 7."))
    assert stop.search(step3[snap_at:dispatch]), "a failed recon comparison must stop dispatch"
    returned = re.compile(_sentence("When every lane has returned, compare again"))
    assert returned.search(step3[dispatch:lanes_at])
    fails = re.compile(_sentence("Exit 1 or 2 fails the run."))
    assert fails.search(step3, lanes_at), "a failed lanes comparison must fail the run"


def test_run_integrity_authoring():
    text = _live(SKILL_PATH.read_text())
    step6 = _flat(_section(text, "### 6. Author, if the profile assigns it", "### 7. Report"))
    assert re.search(_sentence(SKIP_SENTENCE), step6), "step 6 does not skip after a failed comparison"
    assert len(re.findall(r"\bcompar", step6, re.I)) == 1, "step 6 qualifies the comparison skip"

    step3 = _flat(_section(text, "### 3. Dispatch the armed specialists", "### 4. Audit the statuses"))
    assert re.search(_sentence(RESTORE_BAN), step3), "step 3 does not ban running a restore"
    assert not re.search(r"\bgit\s+restore\b|\bupdate-ref\b", text), "the skill runs a restore"


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
