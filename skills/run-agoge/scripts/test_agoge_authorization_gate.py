"""Authorization-gate tests, split out of test_agoge_registry.py (PRD 00121).

    uv run --with pytest pytest test_agoge_authorization_gate.py

The gate is stated in four places that must agree: trudy's charter, the
security playbook, the profile contract, and the skill's dispatch step. These
assertions are what stops one of the four drifting out of step with the rest.

Split from test_agoge_registry.py once that file crossed the 800-line
ceiling - a pure file-boundary move, no behavior change. `AGENTS_DIR`,
`REFERENCES` and the `registry` fixture stay defined in test_agoge_registry.py
(tests there still need them) and are imported here rather than duplicated.
"""

from __future__ import annotations

import re

from test_agoge_registry import AGENTS_DIR, REFERENCES, registry

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
    """Recon marks trudy `unarmed` when the profile says `not asserted`, which
    collides with step 3's "dispatch only armed lanes". Left unstated, the
    invocation route arms her only when whoever runs the skill happens to
    read past the cost gate.
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


def test_the_profile_routes_asserted_by_label_cannot_drift() -> None:
    """SKILL.md's resolution table is the only place that emits `Asserted by:
    profile (<path>)`. trudy.md and the security playbook are pasted-in
    consumers that instruct the agent to look for exactly that line and
    treat anything without it as absent.

    Reword the profile-route label on one side and trudy reads her own
    authorized prompt as unsourced and refuses - the lane goes dark on every
    run with the whole suite green otherwise. The label stays physically
    duplicated across all three files on purpose (a pasted playbook cannot
    cite a file the running agent cannot open).

    The payload is `<path>` in all three since PRD 00001: the profile resolves
    meta-first with a root fallback, so SKILL.md cannot know the value when it
    is authored either - it substitutes the path that resolved at dispatch
    time, exactly as the two pasted-in consumers already assumed. What this
    test binds is that all three describe the line's shape with the same
    placeholder.
    """
    pattern = re.compile(r"Asserted by: profile \(([^)]*)\)")

    for path in (SKILL, AGENTS_DIR / "trudy.md", REFERENCES / "security-playbook.md"):
        match = pattern.search(_text(path))
        assert match, f"{path.name} lost the profile-route `Asserted by:` label"
        assert match.group(1) == "<path>", (
            f"{path.name}'s profile-route payload must describe the line's "
            "shape as `<path>`, the same placeholder the other consumer uses"
        )


def test_the_invocation_routes_asserted_by_label_cannot_drift() -> None:
    """SKILL.md's resolution table is the only place that emits `Asserted by:
    invocation (<name>)`. trudy.md and the security playbook are pasted-in
    consumers that instruct the agent to look for exactly that line and
    treat anything without it as absent.

    Reword the invocation-route label on one side and trudy reads her own
    authorized prompt as unsourced and refuses - the lane goes dark on every
    run with the whole suite green otherwise. The label stays physically
    duplicated across all three files on purpose (a pasted playbook cannot
    cite a file the running agent cannot open).

    The payload is not identical across all three by design: SKILL.md
    substitutes `<source>`, naming its own `--authorized <source>` flag,
    while the two consumers describe the line's shape generically (`<name>`)
    instead of quoting the emitter, since a pasted playbook is authored
    before any run and cannot know the value. What is actually bindable, and
    what this test binds, is SKILL.md's payload against its known literal,
    and the two consumers' payloads against each other.
    """
    pattern = re.compile(r"Asserted by: invocation \(([^)]*)\)")

    skill_match = pattern.search(_text(SKILL))
    assert skill_match, "SKILL.md lost the invocation-route `Asserted by:` label"
    assert skill_match.group(1) == "<source>", (
        "SKILL.md's invocation-route payload must stay `<source>`, matching "
        "its own `--authorized <source>` flag"
    )

    for path in (AGENTS_DIR / "trudy.md", REFERENCES / "security-playbook.md"):
        match = pattern.search(_text(path))
        assert match, f"{path.name} lost the invocation-route `Asserted by:` label"
        assert match.group(1) == "<name>", (
            f"{path.name}'s invocation-route payload must describe the "
            "line's shape as `<name>`, the same placeholder the other "
            "consumer uses"
        )


def test_the_authorized_source_is_bounded_to_a_shell_word_shape() -> None:
    """`<source>` is passed verbatim into trudy's dispatch prompt, and her
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
    """Today's sidecar enum is `profile`, `invocation` or `none` - a run
    where trudy is vetoed *and* `--authorized <source>` was passed has no
    value to land in. `none` is wrong: an authorization was passed and
    overruled. The contract must widen the enum to include `vetoed` and record
    the overruled source alongside it, in both surfaces that carry the route:
    the JSON sidecar and the markdown summary header.

    A test binding only one surface leaves the other open, so this checks
    both.
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


def test_the_arguments_bullet_separates_no_value_from_not_passed_at_all() -> None:
    """This prose is executed by a model, so a second reading is a real
    branch, not a style nit. The Arguments bullet calls an empty-or-missing
    `<source>` an error. On one parse "missing" covers the flag never being
    passed at all - the exact case the `none` row (skip trudy, finish the
    run) requires NOT to be an error. The fix must name the
    flag-passed-with-no-value case and the flag-not-passed-at-all case
    separately, not leave "missing" to cover both.
    """
    text = _text(SKILL)

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


def test_the_profile_row_treats_an_absent_or_empty_authorization_line_as_fail_closed() -> (
    None
):
    """This prose is executed by a model, so a second reading is a real
    branch, not a style nit. The profile row fires only when the
    `Authorization:` line "is asserted (not `not asserted`)", and says
    nothing about a line that is not there at all. The fix must state that
    an absent line and an empty-value line both resolve fail-closed, not
    just imply it through what "asserted" excludes.
    """
    text = _text(SKILL)

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


def test_the_normal_dispatch_rule_gates_on_tactics_not_only_the_exception() -> None:
    """A row with no tactics can never dispatch trudy, without qualification.
    The tactics guard lives inside "One exception, and only one" - the block for
    an `unarmed` row re-armed by an authorization. An `armed` row with empty
    tactics never enters that block: it reaches dispatch on the normal path,
    which says nothing about tactics today.

    Scoped to the text before the exception begins, not the whole step:
    "tactics" already appears later (part 2 of the prompt is built from "its
    tactics"), so a step-wide `in` check would pass for a sentence that
    describes the bug rather than gates it. A bare `"tactics" in slice` check
    is also not enough: a purely descriptive sentence ("built from its
    tactics") added to this same paragraph would satisfy it while an armed
    tacticsless row still dispatches. The slice must state a refusal, not
    just mention the word.
    """
    text = _text(SKILL)
    start = text.find("### 3. Dispatch the armed specialists")
    end = text.find("One exception, and only one, and it turns on the reason.")
    assert start != -1 and end != -1, "step 3's heading or exception opener moved"
    normal_path = text[start:end]
    assert "tactics" in normal_path, (
        "the normal dispatch rule never mentions tactics; an armed row with "
        "empty tactics reaches dispatch untouched by the tactics guard"
    )
    refusal_forms = ("skipped", "do not dispatch", "never dispatch", "refuse")
    assert any(form in normal_path for form in refusal_forms), (
        "the normal dispatch rule mentions tactics but states no refusal, so "
        f"it reads as description rather than a gate; accepted forms: "
        f"{refusal_forms}"
    )


def test_the_exception_path_states_its_own_tactics_rule() -> None:
    """The test above binds the normal path's tactics guard; this one binds
    the exception's own. 00118 moved "populated tactics" / "stale profile" /
    "--refresh-profile" out of this paragraph and into step 3's normal-path
    sentence, so a file-wide `in text` check for those phrases now passes on
    the normal-path sentence alone — deleting this whole "A third way..."
    paragraph leaves the suite green. But the exception re-arms a row marked
    `unarmed`, which the normal-path wording never reaches: only this
    paragraph says the re-armed row still owes tactics, not just a reason.

    Scoped to just this paragraph, not the whole file: "inherits the tactics
    rule above" and "trudy probes blind" only occur here, so isolating the
    slice (rather than a file-wide `in` check, which is what let the bug
    through) is what proves the guarantee lives in this paragraph and not
    merely somewhere in the document.
    """
    text = _text(SKILL)
    start = text.find("A third way the exception fails closed")
    end = text.find("Dispatch every armed specialist")
    assert start != -1 and end != -1, (
        "the exception's own tactics paragraph or the next step's opener moved"
    )
    paragraph = text[start:end]
    assert "inherits the tactics rule above, not just the reason" in paragraph, (
        "the exception must say it inherits the tactics rule, not just the "
        "reason, or a re-armed unarmed row skips the tactics gate entirely"
    )
    assert (
        "defines an `unarmed` row as carrying the reason, not tactics" in paragraph
    ), (
        "the paragraph must cite finding-contract.md's definition of what an "
        "`unarmed` row carries, or the tactics requirement reads as unsourced"
    )
    assert (
        "trudy probes blind while the report claims the lane ran armed" in paragraph
    ), (
        "the paragraph must state what arming a tacticsless row costs, or the "
        "rule reads as advisory rather than a gate"
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


def test_vetoed_route_source_is_absent_when_both_the_profile_and_invocation_assert() -> (
    None
):
    """A vetoed trudy authorized both ways at once - the profile's
    `Authorization:` line asserted and `--authorized <source>` passed at
    invocation - has two precedents pulling different ways: this bullet's own
    rule naming the overruled invocation token as `source`, and part 5's
    "The profile wins over the invocation when both assert" precedence for the
    non-vetoed lane. A vetoed trudy never reaches part 5 ("step 3 already
    refused her before part 5 runs"), so step 7's own vetoed-route rule has to
    restate that precedence for itself, or a vetoed lane authorized both ways
    has no stated `source` outcome at all - two live rules, no tiebreaker.
    """
    text = _text(SKILL)
    vetoed_idx = text.find("`vetoed` (a veto overrode")
    assert vetoed_idx != -1, "the vetoed-route parenthetical moved or was reworded"
    clause_end = text.find(", or `none`", vetoed_idx)
    assert clause_end != -1, "the vetoed-route clause's boundary before `none` moved"
    clause = text[vetoed_idx:clause_end]

    # `both` is not a word this clause uses at all today - the combined case
    # (profile line AND `--authorized <source>` both asserting) has no rule
    # here, only the two single-route cases. Any of these phrasings would
    # newly name it. This is the check that actually fails today; the
    # `absent` check below cannot, on its own, since that word already names
    # the unrelated profile-line-alone case in this same clause - it is
    # `both` naming the combined case at all that carries the guarantee.
    both_phrases = (
        "both assert",
        "both are asserted",
        "both were asserted",
        "both routes assert",
        "both the profile and the invocation",
    )
    assert any(phrase in clause for phrase in both_phrases), (
        "the vetoed-route clause never names the case where the profile line "
        f"and `--authorized <source>` both assert; accepted phrasings: {both_phrases}"
    )
    assert "absent" in clause or "no `source`" in clause, (
        "the combined-assertion case must leave `source` absent - the "
        "profile-wins precedent from part 5 applies here too - or a vetoed "
        "lane authorized both ways has no stated `source` outcome"
    )


def test_the_profile_resolves_meta_first_with_a_root_fallback() -> None:
    """The profile is what the `profile` route asserts from, so where step 2
    looks for it is a gate fact (PRD 00001). `dev/local/meta/` is canonical
    since the 2026-08-23 keeper move; the root path stays readable because
    unmigrated repos still keep the profile there. Drop either half and one
    class of target repo loses its authorization source silently.
    """
    text = _text(SKILL)
    step = text[text.find("### 2. Profile") : text.find("### 3.")]
    assert step, "step 2 moved or was renamed"

    meta_idx = step.find("dev/local/meta/agoge-profile.md")
    assert meta_idx != -1, "step 2 stopped naming the canonical meta/ profile path"
    root_idx = step.find("dev/local/agoge-profile.md", meta_idx + 1)
    assert root_idx != -1, (
        "step 2 stopped naming the root fallback; an unmigrated target repo "
        "then has no profile and every armed lane loses its authorization"
    )
    assert "fall" in step[meta_idx:root_idx], (
        "step 2 names both paths but never says the root one is a fallback, so "
        "which one wins when both exist is undefined"
    )
