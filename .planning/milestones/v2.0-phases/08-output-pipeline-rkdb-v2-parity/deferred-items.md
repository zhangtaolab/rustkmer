# Deferred Items — Phase 8

Out-of-scope discoveries made during plan execution. Not fixed here per the
executor scope boundary (only defects directly caused by the executing task are
in scope).

## 08-02 (2026-11-13)

- **`cargo fmt --all --check` is red at HEAD on files this plan did not touch.**
  Reproduced with both stable and nightly rustfmt against the tree at
  `fbd34e5` + this plan's two commits. Reported files:
  `src/cli/commands/count.rs`, `src/count/engine.rs`, `src/count/mod.rs`,
  `src/database/prefix_cache_merge.rs`, `src/kmer/extract.rs`,
  `tests/count_engine_tests.rs`, `tests/window_extract_differential_tests.rs`.
  The new `tests/rkdb_v2_byte_identity_tests.rs` is rustfmt-clean; no source
  file was modified by this plan. Owner: the next plan that touches the CI
  format gate, or a dedicated formatting quick task.
  Resolved 2026-11-18: `cargo fmt --all --check` exits 0 at HEAD (verified
  2026-11-18); all seven named files are covered by the workspace check; the
  drift was cleared by quick task 261116-ks7 (commit ee742dc).
  status: resolved
