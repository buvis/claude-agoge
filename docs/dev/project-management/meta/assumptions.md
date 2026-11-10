# Assumptions ledger — PRD 00010 rework cycle 1

## 6: [D1] skills/run-agoge/scripts/test_target_snapshot.py

Ivan (sonnet), test-suite split and helper reuse:

- The process-filter positive control tolerates git failing after the marker
  launches. It does not use a protocol-speaking filter, matching the existing
  process-filter test.
- The ignored-path and config tests belong in the state module.
- `test_inherited_non_filter_config_pair_still_takes_effect` belongs in the
  programs module, next to the inherited command-scope filter test.
- `test_inherited_git_dir_does_not_redirect_snapshot` belongs in the state
  module.
- `test_inherited_big_file_threshold_does_not_beat_module_override` belongs in
  the state module, with the peak-RSS tests.

Orchestrator:

- The finding's stated remedy for the 800-line violation (one split) does not
  reach the limit; a second split module, `test_target_snapshot_state.py`, was
  authorized so every module lands under 800 lines.
- The split-hygiene checker's two UNUSED lines for `NOTES_V1`/`NOTES_V2` are a
  single-file-checker artifact, not a defect: both names are imported and read
  by two other modules.
