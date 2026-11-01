# Decision Audit Log: 00003-fence-lane-scratch-work-out-of-target-v1

PRD: `00003-fence-lane-scratch-work-out-of-target-v1.md`
Started: 2026-11-01T21:22:58Z
Completed: 2026-11-01T21:22:58Z
Autonomous: 10  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R1 [2/4] High: scratch contract and recon's profile write give the recon lane contradictory instructions (finding-contract.md:84)

**Choice**: auto-fix (cycle 1 rework): add a narrow carve-out for the one dispatch-named profile output, keeping probe artifacts out of the target

**Rationale**: Additive doc text only, no signature or schema change; two reviewers (Alice, Bob) independently raised it

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R2 [2/4] Medium: test_scratch_contract_incident_preamble asserts only a non-zero exit, so any unrelated failure satisfies it (test_scratch_contract.py:877)

**Choice**: auto-fix (cycle 1 rework): pin the ceiling mechanism by asserting exit 128 or git's 'not a git repository' stderr

**Rationale**: Clear mechanical fix to a test assertion, raised by Alice and Blake

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R3, R5, R6, R7, R8 (single-voice Medium/Low) and R4 (PRD-mandated control test, raised as not a defect)

**Choice**: discard; each appended to the settled-decisions ledger

**Rationale**: R3/R5/R6/R7/R8 are single-voice [1/4] Medium or Low rows, which the gate discards rather than tasking; R4's replay pass is the control test's purpose, and R6's named paths are autopilot's own durable tracked store

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: The Scratch contract says "Everything you create goes under the path it prints ... Nothing goes inside the target", and SKILL.md pastes it verbatim into the recon prompt (item 7). Olivia's charter and the recon prompt require her to write the strategy profile into the target (docs/dev/project-management/meta/agoge-profile.md). The two instructions conflict, and a literal-minded recon lane could refuse to write the profile or write it to scratch. Add an explicit carve-out (for example "except the one file your dispatch prompt tells you to write") to the contract, or scope the sentence in the recon paste

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: test_scratch_contract_incident_preamble asserts only `returncode != 0` plus an unchanged snapshot. The design says the ceiling makes git fail with exit 128. Any unrelated non-zero exit (a typo in the extracted block, an unset variable) would pass as long as nothing moved. Assert `== 128`, or assert that stderr contains git's "not a git repository" message, so the test pins the ceiling mechanism and not just any failure

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R1 (cycle 2): the Scratch contract's recon carve-out deviates from appendix A2's verbatim text and no test pins it

**Choice**: discard

**Rationale**: single-voice [1/4]; the carve-out IS the cycle-1 R1 fix ([2/4] ALICE+BOB) and Alice and Carl verified it against the recon prompt's named profile path

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R2 (cycle 2): the new stderr assertion depends on git's English message; LC_ALL=C suggested

**Choice**: discard

**Rationale**: single-voice [1/4]; the test env already pins GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM and HOME, and its own finder calls it optional

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R3 (cycle 2): test_scratch_contract_mechanisms checks its tokens against the whole of finding-contract.md rather than the Scratch contract section

**Choice**: discard

**Rationale**: single-voice [1/4]; the whole-file token check is what the PRD's contract for test 1 specifies, so narrowing it would depart from the spec

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R4 (cycle 2): test 2 adds a stderr assertion the PRD did not ask for

**Choice**: discard

**Rationale**: single-voice [1/4]; the assertion is the cycle-1 R2 fix ([2/4] ALICE+BLAKE) and its own finder calls it harmless

### [autonomous] 2026-11-01T21:22:58Z

**Decision**: R5 (cycle 2, mech-check): test_scratch_contract_incident_preamble passes against the pre-change code

**Choice**: discard

**Rationale**: single-voice [1/4]; the replay base is cycle-1 head c37b74be where the contract and this test already existed and passed, so cycle 2 only tightened an assertion that already held there
