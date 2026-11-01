# Dispatch agoge specialists by their namespaced agent names

Source: 2026-08-25, found while verifying the autopilot plugin extraction
(`~/.claude` PRD 00144). Autopilot had the identical defect and fixed it the
same day; this PRD carries that fix across to agoge.

## Overview

### Problem Statement

`skills/run-agoge/SKILL.md` names the seven specialists bare — the roster line
"`olivia`, `walter`, `heidi`, `judy`, `wendy`, `peggy`, `trudy` — dispatched by
`subagent_type`", and every dispatch instruction after it ("dispatch
**olivia**", step 3's armed fan-out).

The personas ship inside a plugin, and the harness registers a plugin's agents
under its namespace **only**. A bare `subagent_type: olivia` fails outright:

```
Agent type 'olivia' not found. Available agents: agoge:heidi, agoge:judy,
agoge:olivia, ... autopilot:rita, ...
```

Measured 2026-08-25 with the sibling case: `subagent_type: rita` failed exactly
this way while `autopilot:rita` was listed as available. agoge's roster appears
in the same live listing under `agoge:*`, so the same call fails the same way.
(Confirmed by mechanism and by the live agent listing; an agoge dispatch was not
itself executed.)

This was masked because plugin *skills* do resolve bare — `/run-autopilot` works
unnamespaced. Skills and agents differ, and the extraction plan assumed they did
not.

### Why it matters

The failure is quiet. Recon (olivia) fails to dispatch, so no specialist gets a
strategy row; the armed lanes never arm; the run still writes a report. Nothing
says "QA did not happen". The autopilot loop runs `/run-agoge` after every
successful batch drain and swallows QA failures by design, so a batch keeps
reporting a QA pass that did nothing.

### Success Metrics

- A live `/run-agoge` run dispatches olivia and at least one specialist without
  an `Agent type ... not found` error.
- `rg -n "subagent_type" skills/` shows no bare roster persona.
- The new registry test fails against the pre-fix text and passes after.

## Functional Decomposition

### Capability: every dispatch site names `agoge:<persona>`

The dispatch name is the persona stem namespaced. The registry conventions state
this once, as the rule, so a lane added later inherits it instead of rediscovering
it.

## Implementation Phases

### Phase 1: Repoint, pin, release

1. `skills/run-agoge/SKILL.md`: the roster line (21) and every dispatch
   instruction that names a persona as a dispatch target (84, 96-125, 304) use
   `agoge:<persona>`. Prose that merely *refers* to a specialist by name
   ("olivia's strategy row") stays as-is — only dispatch names change.
2. Wherever the pack documents its agent-registry conventions, state the rule:
   the frontmatter `name` is the file stem, and the dispatch name is
   `agoge:<name>`, because plugin-owned agents register under their namespace
   only.
3. `scripts/test_agoge_registry.py`: add a sweep asserting that no
   `subagent_type:` in `skills/` names a bare roster persona. Mirror
   `autopilot`'s `test_native_dispatch_names_are_namespaced`
   (`buvis/autopilot/skills/review-work-completion/scripts/test_agent_registry.py`)
   — it skips foreign packs' personas so the two suites do not police each other.
4. CHANGELOG entry under `### Fixed`.
5. Release and install. A plugin fix is not done until it ships (`~/.claude` PRD
   00118 precedent).

*Acceptance:* success metrics above; registry tests green.

## Test Strategy

- The sweep in step 3 is the regression test. Watch it fail against the current
  text before fixing, per `rules/testing.md`.
- Verification of the live dispatch needs a fresh session: agent registration is
  read at session start.

## Risks

- **Prose churn**: the persona names appear ~20 times in SKILL.md and most are
  references, not dispatch names. A blanket find-and-replace would namespace the
  prose too and read badly. Change dispatch sites only.
- **Verification needs a release plus a fresh session**, so the fix cannot be
  confirmed end-to-end in the session that writes it.
