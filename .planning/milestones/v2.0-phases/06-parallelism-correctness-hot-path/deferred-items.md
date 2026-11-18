# Phase 06 Deferred Items

Out-of-scope discoveries found during plan execution. Not fixed here; surfaced
so a later plan or quick task can pick them up.

## 06-02

- `src/database/prefix_cache_merge.rs:1382` is not `cargo fmt` clean at HEAD:
  rustfmt wants the `processed_kmers % 1_000_000 == 0 || last_report...`
  condition collapsed onto one line. Pre-existing drift, unrelated to PAR-02
  (the file is untouched by this plan); left alone per the scope boundary.
  The plan's verify gates (`cargo test --locked`, clippy 1.82 both crates) do
  not include `cargo fmt --check`.
  Resolved 2026-11-18: `cargo fmt --all --check` exits 0 at HEAD (verified
  2026-11-18); the drift was cleared by quick task 261116-ks7 (commit
  ee742dc).
  status: resolved
- `pyo3/src/counter.rs:197` is not `cargo fmt` clean at HEAD either (the
  `RustPyCounter::new(...)` call in `PyCounter::new`). Pre-existing and on a
  line this plan did not touch; left alone. The root `cargo fmt --check` gate
  does not cover the separate pyo3 crate.
  **Resolved in 06-03:** plan 06-03 edits `pyo3/src/counter.rs` for PAR-03 and
  its formatting pass normalized the pre-existing drift (`RustPyCounter::new`
  call and the two compressed-file openers). No behavior change.
  status: resolved
