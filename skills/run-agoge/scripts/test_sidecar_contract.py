"""The JSON sidecar is something `agoge-gym`'s scorer can credit honestly.

`bin/score` in buvis/agoge-gym credits a seed only to a finding whose `title`
describes it, and reads each finding's `lanes` to tell a lane's own catch from
another lane's by-catch. The examples in `finding-contract.md` are what the
master copies when it writes a sidecar, so they must carry both, and the skill
must ask for both.
"""

from __future__ import annotations

import json
import re

from test_agoge_registry import AGENTS_DIR, REFERENCES

SKILL = REFERENCES.parent / "SKILL.md"
CONTRACT = REFERENCES / "finding-contract.md"

# The registry's specialists, plus the master's own interactive-run findings.
LANES = {path.stem for path in AGENTS_DIR.glob("*.md")} | {"master"}


def _section(text: str, heading: str, end: str) -> str:
    start = text.index(heading)
    return text[start : text.index(end, start + len(heading))]


def _sidecar_section() -> str:
    return _section(
        CONTRACT.read_text(encoding="utf-8"), "### The JSON sidecar", "\n## "
    )


def _example_findings() -> list[dict]:
    findings = []
    for block in re.findall(r"```json\n(.*?)```", _sidecar_section(), re.S):
        data = json.loads(block)
        if "findings" in data:
            findings.extend(data["findings"])
        elif "domain" in data:
            findings.append(data)
    return findings


def test_the_registry_is_where_lane_names_come_from() -> None:
    assert {"walter", "heidi", "judy", "wendy", "peggy", "trudy"} <= LANES


def test_every_example_finding_carries_a_title_and_its_lanes() -> None:
    findings = _example_findings()
    assert findings, "the sidecar section shows no example finding"
    for finding in findings:
        assert finding.get("title"), f"an example finding has no title: {finding}"
        lanes = finding.get("lanes")
        assert isinstance(lanes, list) and lanes, f"no `lanes` list: {finding}"
        assert set(lanes) <= LANES, f"{lanes} names a lane outside {sorted(LANES)}"


def test_the_contract_says_what_the_scorer_matches() -> None:
    section = _sidecar_section()
    assert "`title`" in section and "`lanes`" in section
    assert "ignored by matching" not in section, (
        "the scorer matches the title now; the contract must not say the extra "
        "keys are ignored"
    )


def test_step_7_asks_every_finding_for_a_title_and_its_lanes() -> None:
    step = _section(SKILL.read_text(encoding="utf-8"), "### 7. Report", "### 8.")
    assert "`title`" in step and "`lanes`" in step


def test_the_gym_bullet_points_at_the_arm_bin_arm_prints() -> None:
    """The gym arms outside its own tree and refuses `armed/` under it."""
    text = SKILL.read_text(encoding="utf-8")
    assert "armed/<fixture>" not in text
    assert "`bin/arm <fixture>` prints" in text
