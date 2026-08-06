# agoge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Every other review reads your diff. This one runs your product.

A code review can only find defects visible in the change. Agoge dispatches seven
specialists that start the thing, drive it, and report what actually happened —
with one rule holding the whole pack together: **a lane that did not run is never
a pass.**

## What's inside

| Component | What it does |
|---|---|
| `/run-agoge` | The master skill: recon, dispatch, status audit, dedup, one report |
| **olivia** | Recon. Inventories what is runnable and assigns each specialist an armed or unarmed strategy |
| **walter** | Journeys. Runs the product end to end and reports what breaks or cannot be executed |
| **heidi** | Integration and database. Exercises cross-component and external contracts |
| **judy** | UX. Drives a real interface and judges what the user is shown, told, and left guessing about |
| **wendy** | Release truth. Checks the changelog, docs and upgrade path against what the product does |
| **peggy** | Performance. Measures what real commands and endpoints cost, and reports numbers |
| **trudy** | Runtime security. Probes behaviour under hostile input, on your own projects only |

Triggers on "run agoge", "product QA", "QA this project", or `/run-agoge`.

## How a run goes

1. **Recon** writes a strategy profile to `dev/local/agoge-profile.md` in the
   target repo, naming the runnable surfaces and which lanes are worth arming.
2. **Only armed lanes dispatch.** An unarmed lane is reported, never run — that
   is the cost gate, and it is why a run over a repo with no browser does not pay
   for a browser lane.
3. **Every finding carries a status**: `verified`, `unverified`, `mocked` or
   `skipped`. Only `verified` is a defect. The master audits those claims against
   their own evidence and downgrades any that reason from the source instead of
   quoting a command and its output.
4. **One report** lands in `dev/local/audit-results/`, with a walkthrough packet
   per finding, plus a JSON sidecar.
5. **You decide.** An interactive run walks the packets one at a time. An
   unattended run writes them and stops — it never files its own findings as
   work, because a machine that opens tickets for itself has approved them on
   your behalf.

### The profile is yours to edit

`dev/local/agoge-profile.md` has a human-owned `## Pins and vetoes` section. The
machine never edits it; a refresh copies it through byte-identically. Veto a
specialist there and it never runs.

That section also carries the line that arms the security lane:

```
Authorization: this project is the operator's own or explicitly authorized.
```

Recon writes `Authorization: not asserted` and may not change it — whether a repo
is yours is not a fact an agent can establish. **Trudy refuses to run without an
assertion**, and only two human acts can make one: editing that line, or starting
the run with `--authorized <source>`, which is how an unattended loop asserts.
Either way the report records which act it was, so an invocation assertion can
never be mistaken for a hand-edited profile.

## Install

```
/plugin marketplace add buvis/claude-plugins
/plugin install agoge@buvis-plugins
```

## Update

```
/plugin update agoge@buvis-plugins
```

## Alternative: install directly from this repo

```
/plugin marketplace add buvis/claude-agoge
```

## What intentionally stays out

- **Batch-drain wiring.** The author's shell wrapper fires one unattended run per
  drained batch of work. That is dotfiles glue, not plugin material — a plugin
  cannot install shell functions. If you want the same thing, invoke
  `/run-agoge <repo> --authorized <your runner's name>` from your own automation.
- **The fixture gym.** The pack is calibrated against
  [buvis/agoge-gym](https://github.com/buvis/agoge-gym), a repo of deliberately
  seeded applications with a known defect manifest. It is the pack's eval, not
  part of the pack: seeds are answer-key vocabulary a real run must never see.

## Development

Hygiene tests for the roster and the contracts:

```
uv run --directory skills/run-agoge/scripts --with pytest python -m pytest -q
```

They pin what the pack promises: no specialist can modify the product it probes,
every lane states what it reports when it cannot run, each charter names the
playbook binding it, and no shipped file points at a path only the author's
machine has.

## Why "agoge"

The ἀγωγή was the Spartan training regime — the process that decided whether
someone was fit for the field. This one decides the same about software, and it
finds out the only way that counts: by making it run.

## License

MIT
