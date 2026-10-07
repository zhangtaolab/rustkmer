# Deferred Items — Phase 03 (Memory Safety)

## Deferred Items

- `cargo clippy --all-targets -- -D warnings` fails on 4 pre-existing
  `clippy::useless_borrows_in_formatting` errors in `src/io/fasta.rs` and
  `src/io/fastq.rs` (lines 153, 215, 342 + one in fasta.rs), introduced by a
  toolchain bump (local rustc 1.99.0; the Phase 1 clippy sweep ran on an
  older toolchain where this lint did not fire).
  status: open
  **What:** Not caused by plan 03-01 — those files are untouched by this phase's
  merge work. But plan 03-01 Task 2 lists `cargo clippy --all-targets -- -D warnings
  exits 0` as a blocking acceptance criterion, so the gate cannot pass while
  these stand. Tracked here and handled as a Rule 3 (blocking) fix inside Task 2
  rather than silently skipped.
  **How to reproduce:** `cargo clippy --all-targets -- -D warnings` from the repo root.

- `tests/merge_routing_tests.rs` declares `mod common;`, which compiles the
  shared `tests/common/{memory,performance,temp_files}.rs` helper modules into
  this test binary. That registers 20 extra `common::*::tests::*` test cases in
  `cargo test --test merge_routing_tests` output (they are the shared module's
  own unit tests, not merge-routing coverage).
  status: open
  **What:** Pre-existing convention — `tests/golden_tests.rs` and
  `tests/round_trip_tests.rs` do the same. Harmless (they pass), but it makes
  the per-target test count noisy. Not worth a deviation; a future cleanup could
  move the factories into a `common/factories.rs` submodule that carries no
  `#[cfg(test)]` tests.
