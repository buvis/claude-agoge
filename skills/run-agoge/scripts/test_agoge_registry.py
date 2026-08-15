"""Hygiene for the agoge specialist roster.

    uv run --with pytest pytest test_agoge_registry.py

These assertions stand in for plugin-dev's `validate-agent.sh`, which PRD 00100
names as the gate. That script cannot serve as one: under `set -euo pipefail` it
runs `((warning_count++))`, which evaluates to the pre-increment value `0` and so
returns exit status 1, aborting the script at its FIRST warning. It fails 00109's
shipped `rita.md` the same way. The error-level checks it means to enforce -
name, description, model, color, a non-empty second-person system prompt - are
asserted here instead, where they run and keep running.

Two of its warnings are declined on purpose: `<example>` blocks and a "Use this
agent when" opening would both blow the 120-character description budget the
registry convention imposes, because descriptions land in the boot prefix.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Both anchors are relative to this file, never to $HOME. The roster sits beside
# the skill in either layout - `~/.claude/{agents,skills/run-agoge}` personally,
# `<plugin>/{agents,skills/run-agoge}` once PRD 00103 extracts it - so the same
# expression resolves in both. A `Path.home()` anchor would have shipped with the
# plugin and then validated the INSTALLER's personal agents instead of the
# plugin's own: green on a machine carrying a stale copy, and green on one
# carrying no copy at all only by accident.
AGENTS_DIR = Path(__file__).resolve().parents[3] / "agents"
REFERENCES = Path(__file__).resolve().parent.parent / "references"

RECON = "olivia"
SPECIALISTS = ("walter", "heidi", "judy", "wendy", "peggy", "trudy")
ROSTER = (RECON, *SPECIALISTS)

# Four are pasted into a lane's dispatch prompt; authoring is the master's own.
PLAYBOOKS = ("browser", "data", "perf", "security", "authoring")

# Which playbook a lane must acknowledge in its own body.
HARNESS_LANES = {
    "judy": "browser",
    "walter": "browser",
    "heidi": "data",
    "peggy": "perf",
    "trudy": "security",
}

# Paths that exist only on the author's machine. PRD 00103 ships this tree as a
# public plugin, where each of these is a pointer an installer cannot follow.
EXTRACTION_FORBIDDEN = ("/Users/", "~/.claude", "work/references/", "rules/")

DESCRIPTION_MAX = 120
VALID_COLORS = {"blue", "cyan", "green", "yellow", "magenta", "red"}
VALID_MODELS = {"inherit", "sonnet", "opus", "haiku", "fable"}

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)


def _parse(name: str) -> tuple[dict[str, str], str]:
    text = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    assert match, f"{name}.md must open with a --- frontmatter block"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, match.group(2)


@pytest.fixture(scope="module")
def registry() -> dict[str, tuple[dict[str, str], str]]:
    return {name: _parse(name) for name in ROSTER}


def test_the_roster_anchor_is_relative_to_this_skill_not_to_home() -> None:
    """A `$HOME` anchor would make this suite validate the INSTALLER's own
    agents rather than the plugin's - and since most installers do have a
    `~/.claude/agents/`, it would not even fail cleanly: it would check the
    wrong roster and report on files this plugin never shipped.

    Cross-checked against `REFERENCES`, which is derived by a different
    expression, so re-anchoring `AGENTS_DIR` to `$HOME` fails here rather than
    quietly agreeing with a copy of its own definition.
    """
    assert AGENTS_DIR.parent == REFERENCES.parents[2], (
        f"the roster at {AGENTS_DIR} is not a sibling of the skills tree at "
        f"{REFERENCES.parents[2]}; it must travel with the plugin, not with $HOME"
    )
    assert AGENTS_DIR.is_dir(), f"roster not found beside the skill at {AGENTS_DIR}"


def test_every_specialist_has_a_file() -> None:
    missing = [name for name in ROSTER if not (AGENTS_DIR / f"{name}.md").is_file()]
    assert not missing, f"missing agoge agent files: {missing}"


def test_roster_is_recon_plus_six_specialists() -> None:
    assert len(ROSTER) == 7
    assert len(set(ROSTER)) == 7, "duplicate persona name in the roster"


@pytest.mark.parametrize("name", ROSTER)
def test_name_matches_the_filename(registry, name: str) -> None:
    fields, _ = registry[name]
    assert fields.get("name") == name, "the name IS the dispatch name"


@pytest.mark.parametrize("name", ROSTER)
def test_description_fits_the_boot_prefix_budget(registry, name: str) -> None:
    fields, _ = registry[name]
    description = fields.get("description", "")
    assert description, f"{name}.md needs a description"
    assert len(description) <= DESCRIPTION_MAX, (
        f"{name}.md description is {len(description)} chars; it lands in the "
        f"boot prefix, so {DESCRIPTION_MAX} is a budget, not a style rule"
    )


@pytest.mark.parametrize("name", ROSTER)
def test_model_and_color_are_declared_and_valid(registry, name: str) -> None:
    """The two fields validate-agent.sh treats as errors."""
    fields, _ = registry[name]
    assert fields.get("model") in VALID_MODELS, f"{name}.md: {fields.get('model')!r}"
    assert fields.get("color") in VALID_COLORS, f"{name}.md: {fields.get('color')!r}"


@pytest.mark.parametrize("name", ROSTER)
def test_tools_is_declared(registry, name: str) -> None:
    """An absent `tools` key inherits everything, Edit and Write included."""
    fields, _ = registry[name]
    assert "tools" in fields, f"{name}.md omits `tools`"


@pytest.mark.parametrize("name", SPECIALISTS)
def test_no_specialist_can_modify_the_product(registry, name: str) -> None:
    """A prober that can edit the thing it probes invalidates its own result."""
    fields, _ = registry[name]
    tools = {tool.strip() for tool in fields["tools"].split(",")}
    assert not tools & {"Edit", "Write", "NotebookEdit"}, (
        f"{name}.md carries {sorted(tools)}; only olivia writes, and only the profile"
    )


def test_olivia_alone_may_write_and_only_the_profile(registry) -> None:
    fields, _ = registry[RECON]
    tools = {tool.strip() for tool in fields["tools"].split(",")}
    assert "Write" in tools, "olivia writes the strategy profile"
    assert "Edit" not in tools, (
        "a profile refresh rewrites the file whole; Edit would only widen what "
        "she can change in a target repo she is supposed to observe"
    )


@pytest.mark.parametrize("name", ROSTER)
def test_body_carries_no_personal_paths(registry, name: str) -> None:
    """Extraction-clean: PRD 00103 lifts these files into a released plugin."""
    _, body = registry[name]
    for forbidden in ("/Users/", "~/.claude", "dev/local"):
        assert forbidden not in body, f"{name}.md body names {forbidden}"


@pytest.mark.parametrize("name", ROSTER)
def test_body_is_a_second_person_system_prompt(registry, name: str) -> None:
    _, body = registry[name]
    assert body.strip(), f"{name}.md has an empty system prompt"
    assert re.search(r"\bYou are\b", body), f"{name}.md should address the agent"


@pytest.mark.parametrize("playbook", PLAYBOOKS)
def test_every_playbook_exists_and_says_something(playbook: str) -> None:
    path = REFERENCES / f"{playbook}-playbook.md"
    assert path.is_file(), f"missing {path.name}"
    assert len(path.read_text(encoding="utf-8").strip()) > 500, (
        f"{path.name} is too thin to be doctrine"
    )


@pytest.mark.parametrize("playbook", PLAYBOOKS)
def test_playbooks_are_extraction_clean(playbook: str) -> None:
    """PRD 00103 lifts these into a released plugin, verbatim.

    A playbook is pasted into a dispatch prompt, so a reference to a file only
    this machine has is worse than useless: the agent cannot open it and does
    not know that it could not.
    """
    text = (REFERENCES / f"{playbook}-playbook.md").read_text(encoding="utf-8")
    for forbidden in EXTRACTION_FORBIDDEN:
        assert forbidden not in text, f"{playbook}-playbook.md names {forbidden}"


def _shipped_markdown() -> list[Path]:
    """Every markdown file the plugin carries, including the repo-root ones.

    README and CHANGELOG were outside this sweep until 2026-08-07, while the
    README claimed "no shipped file points at a path only the author's machine
    has". A personal path added to the README would have shipped green against a
    test that never read it, so the claim now covers what it says it covers.
    """
    root = REFERENCES.parents[2]
    return [
        REFERENCES.parent / "SKILL.md",
        *sorted(REFERENCES.glob("*.md")),
        *sorted(p for p in (root / "README.md", root / "CHANGELOG.md") if p.is_file()),
    ]


@pytest.mark.parametrize("path", _shipped_markdown(), ids=lambda p: p.name)
def test_every_shipped_file_is_extraction_clean(path: Path) -> None:
    """Widened past the playbooks on 2026-08-06, during the extraction itself.

    It could not be widened before: `finding-contract.md` cited
    `rules/communication.md` for the walkthrough packet, and `SKILL.md` cited a
    sibling personal skill for the roster conventions. Both are now inlined, so
    the whole shipped surface can hold the line the playbooks already held.

    `dev/local/` is deliberately NOT forbidden here. It is a repo-relative
    contract path - where the profile and the reports live inside the TARGET
    repo - so it travels correctly to any installer. What does not travel is a
    path only the author's machine has.
    """
    text = path.read_text(encoding="utf-8")
    for forbidden in EXTRACTION_FORBIDDEN:
        assert forbidden not in text, (
            f"{path.name} names {forbidden}, which an installer cannot open and "
            "will not be told it cannot open"
        )


@pytest.mark.parametrize("playbook", PLAYBOOKS)
def test_playbooks_stay_inside_the_dispatch_budget(playbook: str) -> None:
    """One playbook plus recon output plus the contract must fit in 50KB."""
    size = (REFERENCES / f"{playbook}-playbook.md").stat().st_size
    assert size < 10_000, f"{playbook}-playbook.md is {size} bytes; keep it lean"


@pytest.mark.parametrize("name,playbook", sorted(HARNESS_LANES.items()))
def test_each_harness_lane_points_at_its_playbook(registry, name, playbook) -> None:
    """A pasted playbook a charter never mentions reads as optional context."""
    _, raw = registry[name]
    body = " ".join(raw.split())  # these bodies wrap at 80; the phrase may not
    assert f"{playbook} playbook" in body, (
        f"{name}.md must tell its agent the {playbook} playbook is binding"
    )


def test_only_the_master_authors(registry) -> None:
    """The authoring playbook is never dispatched, so no charter may claim it."""
    for name in ROSTER:
        _, raw = registry[name]
        body = " ".join(raw.split()).lower()
        assert "authoring playbook" not in body, (
            f"{name}.md points at the authoring playbook; every specialist is "
            "pinned read-and-run, so the master authors and they do not"
        )


@pytest.mark.parametrize("name", SPECIALISTS)
def test_every_specialist_states_its_honesty_rule(registry, name: str) -> None:
    """The contract's whole point: a lane that did not run never reads as a pass.

    Each charter has to carry the rule in its own body, because the body is the
    system prompt and is all the agent has before its dispatch prompt arrives.
    """
    _, body = registry[name]
    assert re.search(r"unverified|skipped|mocked|refused", body), (
        f"{name}.md must say what it reports when it cannot run its surface"
    )


# ── The authorization gate (PRD 00117) ────────────────────────────────────────
#
# The gate is stated in four places that must agree: trudy's charter, the
# security playbook, the profile contract, and the skill's dispatch step. These
# assertions are what stops one of the four drifting out of step with the rest.
#
# What they are NOT, established by mutation rather than assumed: appending "an
# unattended loop dispatch is exempt from this gate" to trudy's charter - the
# exact inversion of the rule - leaves every one of them green. They check that
# a phrase is present, so they catch a deletion and miss a contradiction. Read
# them as drift detectors, not as a guard on the gate's semantics.

SKILL = REFERENCES.parent / "SKILL.md"


def _text(path) -> str:
    """Collapsed to one line: these files wrap at 80, so a phrase may not be."""
    return " ".join(path.read_text(encoding="utf-8").split())


def test_trudy_requires_a_named_source_not_just_an_assertion(registry) -> None:
    """An unsourced assertion is one nothing can attribute to a human."""
    _, raw = registry["trudy"]
    body = " ".join(raw.split())
    assert "names the human act" in body, (
        "trudy.md must require the assertion to name its source; without that "
        "the machine's own claim is indistinguishable from the operator's"
    )
    assert "counts as absent" in body, (
        "trudy.md must say what an unsourced assertion is treated as, or the "
        "requirement is advice rather than a gate"
    )


def test_the_gate_still_fails_closed_everywhere_it_is_stated() -> None:
    """Widening who may assert must not weaken what happens with no assertion."""
    for path in (AGENTS_DIR / "trudy.md", REFERENCES / "security-playbook.md"):
        assert "run nothing" in _text(path), f"{path.name} lost its refusal instruction"
    # The prose above is advisory; this is the row the master actually acts on.
    # Deleting it while widening the gate would leave no skip instruction at all.
    skill = _text(SKILL)
    assert "do not dispatch her" in skill, (
        "the resolution table's no-assertion row must still refuse the dispatch"
    )
    assert "authorization not asserted" in skill, (
        "a skipped security lane must carry its reason into the report"
    )


def test_the_security_playbook_names_both_routes() -> None:
    """A pasted playbook is all the lane has; a route missing here is unusable."""
    text = _text(REFERENCES / "security-playbook.md")
    assert "strategy profile" in text, "the playbook must name the profile route"
    assert "authorization argument" in text, (
        "the playbook must name the invocation route, or a lane authorized that "
        "way reads its own prompt as unauthorized and skips"
    )


def test_the_profile_contract_keeps_recon_out_of_the_assertion() -> None:
    """The widened gate must not become a licence for the machine to assert."""
    text = _text(REFERENCES / "finding-contract.md")
    assert "The machine never edits this section" in text
    assert "not a fact an agent can establish" in text
    assert "Two human acts can assert, and only two" in text, (
        "the contract must bound the routes; an open-ended list invites a third"
    )


def test_the_skill_documents_the_flag_and_its_resolution_order() -> None:
    text = _text(SKILL)
    assert "--authorized <source>" in text, "the argument must be documented"
    assert "The profile wins over the invocation" in text, (
        "with two asserting routes the skill has to say which one decides"
    )
    assert "empty source is an error" in text, (
        "asserting anonymously is the one failure this gate cannot tolerate"
    )
    assert "itself another flag" in text, (
        "`--authorized --refresh-profile` must be the empty-source error, not a "
        "source named after the next flag"
    )


def test_an_authorization_unarmed_verdict_does_not_gate_the_security_lane() -> None:
    """Found by running it: recon marks trudy `unarmed` when the profile says
    `not asserted`, which collides with step 3's "dispatch only armed lanes".
    Left unstated, the invocation route arms her only when whoever runs the
    skill happens to read past the cost gate.

    Assertions here are load-bearing tokens, not whole sentences: the first
    version pinned two exact sentences, which meant correcting the rule forced
    editing the test that guards it.
    """
    text = _text(SKILL)
    assert "verdict about *surface*" in text, (
        "step 3 must distinguish a surface verdict from an authorization one"
    )
    assert "A surface `unarmed` still stands" in text, (
        "the exception must not void a surface verdict too — a repo with nothing "
        "to run does not become probeable because a flag was passed"
    )
    assert "If the row gives no reason" in text, (
        "an unexplained row has to fall to the safe side, or the exception "
        "swallows the cost gate"
    )


def test_recon_decides_the_security_lane_on_surface_alone() -> None:
    """The root cause of the two findings above, fixed where it starts: recon
    decides trudy's row on surface alone, and the Authorization line is not
    recon's to act on.
    """
    text = _text(SKILL)
    assert "trudy is armed or unarmed on surface alone" in text
    assert "never decides her row" in text, (
        "recon must be told the Authorization line is not hers to act on"
    )


def test_the_report_records_which_act_authorized_the_probe() -> None:
    """A reader must tell an invocation assertion from a hand-edited profile."""
    text = _text(REFERENCES / "finding-contract.md")
    assert '"authorization"' in text, "the sidecar shape must carry the route"
    assert "which human act authorized it" in text, (
        "the markdown summary must name the route too; the sidecar alone is not "
        "what a human reads"
    )


def test_a_tacticsless_row_can_never_dispatch_trudy() -> None:
    """Part 5's exception can arm trudy from a row whose stated reason is the
    `Authorization:` default rather than a surface fact. `finding-contract.md`
    defines an `unarmed` row as carrying the reason, not tactics — but part 2 of
    every dispatch prompt is built from that specialist's row, its tactics and
    the exact commands recon established. Arm that row anyway and the strategy
    section is empty: trudy probes blind while the report says the lane ran
    armed.
    """
    text = _text(SKILL)
    assert "populated tactics" in text, (
        "the exception must require the row to carry populated tactics before "
        "arming trudy, or an authorization-reason row with none dispatches her "
        "blind"
    )
    assert "stale profile" in text, (
        "when tactics are absent the skip reason must name the stale profile — "
        "reusing 'authorization not asserted' would misreport why the lane "
        "did not run"
    )
    # `--refresh-profile` already appears four times elsewhere in the skill
    # (Arguments, step 2, and twice in the `--authorized --refresh-profile`
    # error case), so a file-wide `in text` check would pass even if the skip
    # reason never mentions the flag. Bind proximity instead: the flag has to
    # sit in the same sentence or two as the reason it fixes, not just
    # somewhere in the document.
    stale_idx = text.find("stale profile")
    window = text[stale_idx : stale_idx + 300]
    assert "--refresh-profile" in window, (
        "the skip reason must point at --refresh-profile within a sentence or "
        "two of naming the stale profile, or an operator reading the reason "
        "has no fix to reach for — the flag mentioned elsewhere in the file "
        "(Arguments, step 2, the --authorized error) does not count"
    )


def test_the_asserted_by_label_cannot_drift_between_emitter_and_consumers() -> None:
    """SKILL.md's resolution table is the only place that emits `Asserted by:
    profile (<path>)` / `Asserted by: invocation (<name>)`. trudy.md and the
    security playbook are pasted-in consumers that instruct the agent to look
    for exactly that line and treat anything without it as absent.

    Reword the label on one side and trudy reads her own authorized prompt as
    unsourced and refuses - the lane goes dark on every run with the whole
    suite green otherwise. The label stays physically duplicated across all
    three files on purpose (a pasted playbook cannot cite a file the running
    agent cannot open), so this is what makes that duplication safe.
    """
    for path in (SKILL, AGENTS_DIR / "trudy.md", REFERENCES / "security-playbook.md"):
        text = _text(path)
        assert "Asserted by: profile (" in text, (
            f"{path.name} lost the profile-route `Asserted by:` label"
        )
        assert "Asserted by: invocation (" in text, (
            f"{path.name} lost the invocation-route `Asserted by:` label"
        )


def test_the_authorized_source_is_bounded_to_a_shell_word_shape() -> None:
    """R3: `<source>` is passed verbatim into trudy's dispatch prompt, and her
    authorization gate is prose a model reads, not code - an unconstrained
    source could itself carry an instruction into that prompt rather than
    just naming who authorized her.

    The fix names the allowed shape exactly: a single shell-word-shaped token
    of letters, digits, dash and underscore, rejected otherwise on the same
    path as the two errors already documented (empty source, source that is
    itself another flag). Pinned on the character-class words themselves, not
    the sentence they sit in - none of `shell-word`, `single`, `letters`,
    `digits`, `dash` or `underscore` occurs anywhere in the file today, so
    this cannot pass on a phrase left over from something else.
    """
    text = _text(SKILL)
    assert "shell-word" in text, (
        "the skill must name the token family --authorized <source> is "
        "bounded to, or the shape bound is undocumented"
    )
    assert "single" in text, (
        "the bound must rule out more than one token (a source with a space "
        "in it), or free text is still an allowed shape and can still carry "
        "an instruction into trudy's prose gate"
    )
    for token_class in ("letters", "digits", "dash", "underscore"):
        assert token_class in text, (
            f"the allowed source shape must name {token_class!r}; leaving it "
            "unstated leaves a character free that an implementor might "
            "permit, and that character could carry an instruction into "
            "trudy's prose authorization gate"
        )


def test_a_vetoed_but_authorized_run_records_the_overruled_source() -> None:
    """R4: today's sidecar enum is `profile`, `invocation` or `none` - a run
    where trudy is vetoed *and* `--authorized <source>` was passed has no
    value to land in. `none` is wrong: an authorization was passed and
    overruled. The contract must widen the enum to include `vetoed` and record
    the overruled source alongside it, in both surfaces that carry the route:
    the JSON sidecar and the markdown summary header.

    Found by two reviewers independently, in two different files - Alice on
    the sidecar, Blake on the report, same gap. A test binding only one
    surface leaves the other open, so this checks both.
    """
    text = _text(REFERENCES / "finding-contract.md")

    # Sidecar: `route` is `profile`, `invocation` or `none` today (the exact
    # anchor is unique in the file). `vetoed` occurs once elsewhere in this
    # doc (the summary-header's lane-status list, "armed, unarmed or vetoed"),
    # far before this offset, so finding it inside this window is new, not a
    # word the file already happened to contain.
    sidecar_idx = text.find("`route` is `profile`")
    assert sidecar_idx != -1, "the sidecar's route-enum sentence moved or was reworded"
    sidecar_window = text[sidecar_idx : sidecar_idx + 250]
    assert "vetoed" in sidecar_window, (
        "the sidecar's `route` enum is still `profile`, `invocation` or "
        "`none`; a vetoed-but-authorized run has no route value to record"
    )
    assert "overruled" in sidecar_window, (
        "the sidecar must record the overruled source on the vetoed route, "
        "or the JSON still can't show which act was passed and overruled"
    )

    # Markdown header: the security-lane authorization sentence names which
    # human act authorized the probe, but says nothing today about a vetoed
    # run that was also authorized.
    header_idx = text.find("which human act authorized it")
    assert header_idx != -1, "the header's authorization sentence moved or was reworded"
    header_window = text[header_idx : header_idx + 300]
    assert "overruled" in header_window, (
        "the markdown summary header must also name the overruled source for "
        "a vetoed-but-authorized run; the sidecar alone is not what a human "
        "reads, and this is the one route with no audit trail today"
    )


def test_no_ambiguous_reading_of_the_gate_contradicts_the_fail_closed_default() -> None:
    """R7: this prose is executed by a model, so a second reading is a real
    branch, not a style nit. Two spots read two ways today, both verbatim
    from the source PRD.

    The Arguments bullet calls an empty-or-missing `<source>` an error. On
    one parse "missing" covers the flag never being passed at all - the
    exact case the `none` row (skip trudy, finish the run) and 00117's R4
    require NOT to be an error. The fix must name the flag-passed-with-no-
    value case and the flag-not-passed-at-all case separately, not leave
    "missing" to cover both.

    The profile row fires only when the `Authorization:` line "is asserted
    (not `not asserted`)", and says nothing about a line that is not there
    at all. The fix must state that an absent line and an empty-value line
    both resolve fail-closed, not just imply it through what "asserted"
    excludes.
    """
    text = _text(SKILL)

    # Wording 1: the `--authorized <source>` bullet under Arguments.
    args_anchor = "assert, at invocation, that the target is the operator's own"
    args_idx = text.find(args_anchor)
    assert args_idx != -1, "the --authorized <source> bullet moved or was reworded"
    args_window = text[args_idx : args_idx + 500]
    assert "no value" in args_window, (
        "the bullet must name a flag passed WITH NO VALUE as its own case "
        "and keep it an error, or a reworded 'missing' still reads as "
        "covering this case too"
    )
    assert "not passed" in args_window, (
        "the bullet must name the flag NOT BEING PASSED AT ALL as a "
        "separate case, or a reader still cannot tell it from the error "
        "case above it - contradicting the `none` row, which skips trudy "
        "and finishes the run for exactly this case"
    )

    # Wording 2: the profile row of the part-5 resolution table, plus the
    # prose under it - the whole span the fix could land in.
    profile_anchor = (
        "the profile's `Authorization:` line is asserted (not `not asserted`)"
    )
    profile_idx = text.find(profile_anchor)
    assert profile_idx != -1, (
        "the profile row's asserted condition moved or was reworded"
    )
    section_end = text.find("Keep each prompt under 50 000 bytes")
    assert section_end != -1, "part 5's closing sentence moved or was reworded"
    profile_window = text[profile_idx:section_end]
    assert "absent" in profile_window, (
        "an ABSENT `Authorization:` line must be named as its own case, or "
        "a reader cannot tell whether no line at all counts as asserted"
    )
    assert "empty value" in profile_window, (
        "a line with an EMPTY VALUE must be named as its own case, distinct "
        "from an absent line, or the two collapse back into one another"
    )
    assert "fail closed" in profile_window or "fail-closed" in profile_window, (
        "the row (or the prose under it) must say both the absent and "
        "empty-value cases resolve fail-closed, not just that they fall "
        "outside 'asserted'"
    )


def test_skill_step_7_names_every_authorization_route_the_contract_declares() -> None:
    """finding-contract.md's `route` enum is the source of truth for what the
    sidecar's `authorization.route` may hold; SKILL.md step 7 is the
    procedure the running agent actually executes to write the report. Add a
    route to the contract's enum without teaching step 7 to name it, and an
    agent following step 7 still writes only the old outcomes - the emitter
    and the contract disagree, and the new route has no instruction telling
    the agent to record it or what `source` carries alongside it.

    Scoped to the authorization-recording sentence itself, not the whole
    step - step 7's summary-header bullet already says "armed, unarmed or
    vetoed" about lane status, unrelated to this enum, and a section-wide
    check would pass on `vetoed` for that reason alone regardless of whether
    the route work was ever done.
    """
    contract = _text(REFERENCES / "finding-contract.md")
    enum_idx = contract.find("`route` is `profile`")
    assert enum_idx != -1, "the contract's route-enum sentence moved or was reworded"
    semi_idx = contract.find(";", enum_idx)
    routes = [
        r for r in re.findall(r"`(\w+)`", contract[enum_idx:semi_idx]) if r != "route"
    ]
    assert routes, "could not extract route values from the contract's enum sentence"

    skill = _text(SKILL)
    auth_idx = skill.find("how the security lane was authorized")
    auth_end = skill.find("### 8. Close")
    assert auth_idx != -1 and auth_end != -1, (
        "the authorization-recording sentence or step 7's closing boundary moved"
    )
    auth_text = skill[auth_idx:auth_end]

    for route in routes:
        assert route in auth_text, (
            f"the authorization-recording sentence in step 7 never names the "
            f"{route!r} route the contract declares; an agent following it to "
            "write the report has no instruction to record that route, so it "
            "writes the wrong value"
        )
    assert "overruled" in auth_text, (
        "the sentence must say what `source` carries on the vetoed route "
        "(the overruled source), or an agent following it has no "
        "instruction for that field on a vetoed-but-authorized run"
    )


def _route_enum_continuation(text: str) -> str:
    """Text from the route-enum's closing `;` to the next paragraph.

    Anchored on `` `route` is `profile` `` and its first `;`, the same pair
    `test_skill_step_7_names_every_authorization_route_the_contract_declares`
    relies on staying put - so this helper never asks that opening to move or
    reword, and only reads what follows it.
    """
    enum_idx = text.find("`route` is `profile`")
    assert enum_idx != -1, "the contract's route-enum sentence moved or was reworded"
    semi_idx = text.find(";", enum_idx)
    assert semi_idx != -1, "the enum clause lost its closing semicolon"
    end = text.find("`fixture` names", semi_idx)
    assert end != -1, "the paragraph boundary after the source rule moved"
    return text[semi_idx:end]


def test_vetoed_route_names_the_overruled_invocation_token_as_source() -> None:
    """A veto overruling `--authorized <source>` still has a real token to
    report. If the vetoed-route clause does not tie the recorded token to the
    overruled invocation specifically, a vetoed-but-invocation-authorized run
    cannot be told apart from a vetoed-but-profile-authorized one, and the one
    route with an audit trail today loses it.
    """
    window = _route_enum_continuation(_text(REFERENCES / "finding-contract.md"))
    overruled_idx = window.find("overruled")
    assert overruled_idx != -1, "the vetoed route's overruled-source rule is gone"
    # Scoped to the clause itself (up to its own comma or period), not a
    # character count: `invocation` already names the *invocation route's*
    # own source earlier in this same sentence, so a plain "both words
    # anywhere in the span" check is true today for the wrong reason. The
    # clause boundary is the sentence's own punctuation, not a guessed gap.
    ends = [
        i
        for i in (window.find(",", overruled_idx), window.find(".", overruled_idx))
        if i != -1
    ]
    clause = window[overruled_idx : (min(ends) if ends else len(window))]
    assert "invocation" in clause, (
        "the vetoed-route clause must name the overruled token as the "
        "invocation's; today `invocation` only names the invocation route's "
        "own source, not what a veto on it overruled"
    )


def test_vetoed_route_source_is_absent_when_the_profile_line_was_overruled() -> None:
    """A veto that overrides the profile's `Authorization:` line overrules a
    path, not a token - there is nothing legal for `source` to hold. Without
    a rule naming this case, a profile-overruled veto reads as if it carries
    a `source` value the same way an invocation-overruled one does.
    """
    window = _route_enum_continuation(_text(REFERENCES / "finding-contract.md"))
    # Scoped to the vetoed-route clause itself (its own sentence), not the
    # whole span: `profile` and `absent` both already occur in the plain
    # profile-route bullet earlier in this sentence, unrelated to a veto
    # overruling it. A span-wide check would stay green even with the
    # profile-overruled disjunct deleted from the vetoed-route clause.
    clause_start = window.find("vetoed route")
    assert clause_start != -1, "the vetoed-route clause is gone"
    clause_end = window.find(".", clause_start)
    assert clause_end != -1, "the vetoed-route clause's closing period is gone"
    clause = window[clause_start:clause_end]
    assert "profile" in clause, (
        "the vetoed-route clause never names the profile-overruled case"
    )
    assert "absent" in clause or "no `source`" in clause, (
        "a profile-overruled veto must leave `source` absent, or the "
        "distinction from an invocation-overruled veto has no textual signal"
    )


def test_a_veto_with_nothing_asserted_is_the_none_route_not_vetoed() -> None:
    """A veto only overrules an assertion that was actually made. With no
    `--authorized` token and no profile `Authorization:` line, there is
    nothing to overrule, so the run reads as unauthorized, not overruled.
    Without this rule both readings of `vetoed` stay legal, and a reader
    cannot tell a genuinely overruled run from one never authorized at all.
    """
    window = _route_enum_continuation(_text(REFERENCES / "finding-contract.md"))
    accepted = ("nothing to overrule", "no assertion", "nothing was asserted")
    assert any(phrase in window for phrase in accepted), (
        "the contract never states that a veto with no assertion at all takes "
        f"the `none` route rather than `vetoed`; accepted phrasings: {accepted}"
    )
