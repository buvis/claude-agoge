import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EMISSION_PATH = REPO_ROOT / "skills/run-agoge/references/prd-emission.md"

# create-prd's minimal.md headings, in order, plus agoge's Test Strategy
# carrying the finding's evidence. The autopilot loop parses these literally.
EXPECTED_HEADINGS = [
    "## Problem",
    "## Solution",
    "## Requirements",
    "### Must have",
    "### Nice to have",
    "## Implementation",
    "### Module:",
    "### Dependencies",
    "## Test Strategy",
    "## Tasks",
    "### Phase 0:",
    "## Success Criteria",
]


def _skeleton() -> str:
    text = EMISSION_PATH.read_text()
    assert "## The PRD shape" in text, "prd-emission.md must have a '## The PRD shape' section"
    section = text.split("## The PRD shape", 1)[1]
    match = re.search(r"````markdown\n(.*?)````", section, re.DOTALL)
    assert match, "the PRD shape section must carry the skeleton in a ````markdown fence"
    return match.group(1)


def test_emitted_prd_skeleton_follows_minimal_template_headings():
    headings = [
        line
        for line in _skeleton().splitlines()
        if line.startswith("## ") or line.startswith("### ")
    ]
    starts = [next((h for h in EXPECTED_HEADINGS if line.startswith(h)), line) for line in headings]
    assert starts == EXPECTED_HEADINGS


def test_emitted_prd_skeleton_carries_acceptance_and_new_symbols():
    skeleton = _skeleton()
    assert re.search(r"^- \[ \] .+ - Acceptance: ", skeleton, re.MULTILINE)
    assert re.search(r"^- New symbols: ", skeleton, re.MULTILINE)
    assert re.search(r"^default_model: ", skeleton, re.MULTILINE)


def test_emission_drops_the_old_rpg_section_names():
    text = EMISSION_PATH.read_text()
    for stale in ("Target Users", "Functional Decomposition", "Structural Decomposition"):
        assert stale not in text
