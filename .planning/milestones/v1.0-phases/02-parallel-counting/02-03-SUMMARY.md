---
phase: 02-parallel-counting
plan: 03
subsystem: python-bindings
tags: [rust, pyo3, python, gil, threading, rayon]
requires:
  - "02-01 (resolve_thread_count + build_global idiom established — PyCounter::new mirrors the Err-tolerant build_global)"
  - "02-02 (DashMap swap in KmerCounter gives interior mutability, so &self increment is sound under Arc + rayon workers)"
provides:
  - "PyCounter.__new__ threads kwarg (None = all cores, parity with CLI --threads) — D-08 / PCOUNT-03"
  - "Arc<RustPyCounter> internal field on PyCounter (was owned) — enables sharing across GIL-released rayon workers"
  - "py.detach(..) GIL release around add_from_fasta / add_from_fastq — rayon workers run in parallel"
  - "threads < 1 validation raising PyValueError (T-02-13)"
  - "Err-tolerant build_global in PyCounter::new (T-02-12 / Pitfall 3 Python variant)"
  - "Free-function helpers (process_sequence_on_counter / process_fasta_file_on_counter / process_fastq_file_on_counter) that take &Arc<RustPyCounter> / &RustPyCounter — callable from inside the Send-bound allow_threads closure"
affects:
  - "pyo3/src/counter.rs (PyCounter field swap; #[new] signature; add_from_fasta/add_from_fastq GIL release; add_kmer/add_sequence stay GIL-held &self; reset &self)"
  - "pyo3/Cargo.toml (rayon added as honest direct dep — already transitive via rustkmer path dep; Rule 3 deviation)"
  - "02-05 (Python-level pytest differential: threads=1 vs threads=N parity + threads kwarg acceptance cases land in pyo3/tests/test_counter.py)"
tech-stack:
  added:
    - "rayon 1.8 (direct dep in pyo3/Cargo.toml — already transitive via rustkmer path dep, so no lockfile bloat; Rule 3 deviation: plan wrongly assumed rayon was accessible by name from the pyo3 crate)"
  patterns:
    - "pyo3 0.27.2 GIL release via py.detach(move || { .. }) (NOT the deprecated py.allow_threads — see Deviations); closure captures only Send types (owned String + Arc<RustPyCounter> clone)"
    - "Arc<RustPyCounter> field + DashMap interior mutability (02-02) => increment takes &self => counting methods take &self not &mut self"
    - "Free-function counter helpers (no self) so the closure body is callable after moving the Arc clone in (cannot borrow self across the GIL boundary)"
    - "std::thread::available_parallelism() for the None -> all-cores resolution (no num_cpus dep; semantically equivalent to num_cpus::get(); stable since Rust 1.59)"
    - "Err-tolerant build_global (let _ = ...) mirrors 02-01 — constructing a second PyCounter no longer panics"
key-files:
  created: []
  modified:
    - pyo3/src/counter.rs
    - pyo3/Cargo.toml
decisions:
  - "Used py.detach (NOT py.allow_threads) — pyo3 0.27.2 source confirms allow_threads is #[deprecated(since=0.26.0)] and delegates to self.detach(f); the RESEARCH note that claimed detach is 0.28+ only was factually inverted. detach IS the canonical non-deprecated API in 0.27.2. Using allow_threads would fail the -D warnings FOUND-01 gate."
  - "Used std::thread::available_parallelism() instead of num_cpus::get() or rayon::current_num_threads() — num_cpus is not a direct dep and rayon was not directly accessible before the Cargo.toml fix; available_parallelism is std, zero-dep, stable since 1.59, and semantically equivalent."
  - "Added rayon as a direct dep to pyo3/Cargo.toml (Rule 3 deviation) — the plan's instruction 'do NOT add to pyo3/Cargo.toml' was based on the false premise that rayon was accessible by name from the pyo3 crate. It is only a transitive dep via rustkmer; accessing rayon::ThreadPoolBuilder requires either a direct dep or a rustkmer re-export. The direct dep is honest (the entry already exists in Cargo.lock via the transitive path — no bloat) and minimal."
  - "Extracted process_sequence_bytes / process_fasta / process_fastq logic into free functions (process_sequence_on_counter / process_fasta_file_on_counter / process_fastq_file_on_counter) that take &Arc<RustPyCounter> / &RustPyCounter>. The previous impl PyCounter::process_sequence_bytes(&mut self, ..) helper could not be called from inside py.detach(move || { .. }) because the closure cannot borrow self — it must move owned/Send types. The free-function form takes the Arc clone by reference and is callable from the closure body."
  - "Changed &mut self -> &self on add_kmer, add_sequence, reset, add_from_fasta, add_from_fastq. Arc<RustPyCounter> + DashMap interior mutability (02-02) means increment/reset take &self — no &mut self needed for counting. The #[pymethods] API is unchanged from Python's perspective (mutating methods are still callable)."
  - "Left add_kmer / add_sequence holding the GIL (sub-millisecond workload; documented in code comments per RESEARCH Open Question 1). Only the file-based heavy counting paths release the GIL."
metrics:
  duration: ~10 min
  completed: "2026-07-01"
  tasks: 1
  files: 2
status: complete
---

# Phase 02 Plan 03: PyCounter `threads` Kwarg + GIL Release for Parallel Python Counting Summary

Exposed the Phase 2 parallel-counting speedup to Python by adding a `threads` kwarg to `PyCounter` (default `None` = all cores, parity with the CLI `--threads` flag) and releasing the GIL around the heavy file-counting methods (`add_from_fasta` / `add_from_fastq`) via `py.detach(..)` so rayon workers actually run in parallel. The shared DashMap core (landed in 02-02) flows to Python automatically once the GIL is released — PCOUNT-03 delivered.

## What Was Built

### Task 1 — `threads` kwarg + `Arc<RustPyCounter>` field + `py.detach` GIL release (D-08, PCOUNT-03)

**`pyo3/src/counter.rs`:**

- **Imports:** added `use std::sync::Arc;`.
- **Struct field swap:** `counter: RustPyCounter` → `counter: Arc<RustPyCounter>`. Documented inline that this enables cloning the Arc into `py.detach(..)` closures and that DashMap interior mutability (02-02) makes `&self` increment sound under rayon workers.
- **`#[new]` signature (D-08):** `#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000))]` → `#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]`. Added `threads: Option<usize>` parameter. Existing 1..=64 k-mer-size validation preserved verbatim.
- **`threads < 1` validation (T-02-13):** mirrors the `InvalidKmerSize` style — `Some(0)` (or any `Some(n)` where `n < 1`) raises `PyValueError("Invalid thread count: {n}. Must be >= 1")`. Verified at the Python layer: `PyCounter(21, threads=0)` raises `ValueError`.
- **`threads=None` resolution:** `std::thread::available_parallelism().map(|v| v.get()).unwrap_or(1)`. Zero-dependency (lives in `std`), semantically equivalent to `num_cpus::get()`, stable since Rust 1.59 (project is 1.80+). Falls back to 1 on unsupported platforms.
- **Err-tolerant `build_global` (T-02-12 / Pitfall 3):** `let _ = rayon::ThreadPoolBuilder::new().num_threads(resolved_threads).build_global();` — discards the `Result`. Constructing a second `PyCounter` (or constructing one after a CLI command in the same process) no longer panics; the existing pool stays in effect. Mirrors 02-01's `execute_count` idiom.
- **GIL release on `add_from_fasta` / `add_from_fastq`:** both methods now take `py: Python<'_>` as the first non-self arg and `&self` (was `&mut self`). The Python path string is extracted to an owned `String` BEFORE the closure (`let path_str = file_path.to_str()?.to_owned();` — Send-safe; CRITICAL per Pitfall 4: do NOT capture `&PyString`/`Bound<T>`/`PyObject` across the GIL boundary). The `Arc<RustPyCounter>` is cloned (`let counter = self.counter.clone();`). Then `py.detach(move || process_{fasta,fastq}_file_on_counter(&counter, &path_str)).map_err(..)?`. The closure captures ONLY `Send` types (owned String + Arc clone) — PyO3's `Ungil` (= effectively `Send`) bound on the closure enforces this at compile time.
- **`add_kmer` / `add_sequence` intentionally hold the GIL** (RESEARCH Open Question 1): sub-millisecond workload; the `py.detach(..)` release/reacquire overhead would exceed the benefit. Documented in code comments on both methods. Short sequences that warrant parallelism should be loaded from a file via `add_from_fasta` / `add_from_fastq` (which DO release the GIL).
- **`reset`:** `&mut self` → `&self` (DashMap `clear()` takes `&self`).
- **Free-function counter helpers extracted** (replaces the old `impl PyCounter { fn process_sequence_bytes(&mut self, ..) }`): three module-level free functions that take `&RustPyCounter` / `&Arc<RustPyCounter>` (no `self`):
  - `process_sequence_on_counter(counter: &RustPyCounter, seq_bytes: &[u8]) -> Result<(), ProcessingError>` — the per-sequence encode → canonicalize → increment loop.
  - `process_fasta_file_on_counter(counter: &Arc<RustPyCounter>, path: &str) -> Result<(), ProcessingError>` — FASTA file read (gzip-aware) + per-record sequence processing. Designed to run inside `py.detach(..)`.
  - `process_fastq_file_on_counter(counter: &Arc<RustPyCounter>, path: &str) -> Result<(), ProcessingError>` — FASTQ file read (gzip-aware) + per-record sequence processing. Designed to run inside `py.detach(..)`.
  These are free functions (not methods) because the `py.detach(move || { .. })` closure cannot borrow `self` — it must move owned/Send types in. The closure clones the Arc and passes `&counter` (an `&Arc<RustPyCounter>`) to the helper.

**`pyo3/Cargo.toml`** (Rule 3 deviation — see Deviations): added `rayon = "1.8"` as a direct dependency. Already a transitive dependency via the `rustkmer` path dep, so the lockfile entry is shared (no bloat). Required because `PyCounter::new` calls `rayon::ThreadPoolBuilder::new()`, and rayon is not otherwise accessible by name from the pyo3 crate.

## Verification Results

| Check | Result |
|-------|--------|
| `cargo build` (pyo3 crate) | green (compiles against pyo3 0.27.2 with the Arc + detach changes) |
| `cargo clippy -- -D warnings` (pyo3 crate) | green (FOUND-01 gate preserved) |
| `cargo test --lib` (pyo3 crate) | 0 tests, 0 failed (crate has no inline `#[cfg(test)]`; the `dyld: libpython3.13.dylib not found` runtime load issue is a pre-existing env quirk requiring `DYLD_LIBRARY_PATH=/Users/forrest/miniconda3/lib` — unrelated to this plan's changes; resolved with the env var) |
| `maturin develop --release` | green (wheel built for CPython 3.13, installed editable) |
| `cargo build` (root crate) | green (rustkmer path dep unaffected) |
| `cargo clippy -- -D warnings` (root crate) | green |
| `pytest pyo3/tests/test_counter.py` | 77 passed, 0 failed (full backward compatibility — all existing PyCounter tests pass unchanged) |
| `pytest pyo3/tests/` (full) | 105 passed, 63 skipped, 0 failed (skips are import-guards in unrelated files + hypothesis-gated) |
| Python smoke: `PyCounter(21, canonical=True, threads=4)` | constructs; `kmer_length == 21` |
| Python smoke: `PyCounter(21)` (positional, no kwargs) | constructs — backward compatible |
| Python smoke: `PyCounter(21, threads=0)` | raises `ValueError: Invalid thread count: 0. Must be >= 1` |
| Python smoke: `PyCounter(21, threads=None)` (explicit) | constructs (all-cores default) |
| Python smoke: `add_sequence("ATGCGATG")` on `PyCounter(4)` | 5 unique 4-mers counted |
| Python smoke: `add_from_fasta` (GIL-released path) | 34 total, 8 unique 4-mers |
| Python smoke: `add_from_fastq` (GIL-released path) | 340 total, 8 unique 4-mers |
| Python differential: `threads=1` vs `threads=4` on same FASTA | identical count maps (8 unique) — PCOUNT-04 invariant holds at the Python layer |

### Acceptance Criteria (grep-based)

| Criterion | Plan Expected | Actual | Notes |
|-----------|---------------|--------|-------|
| `allow_threads` in counter.rs (code-level) | >= 1 | 0 code calls (13 comment refs) | Rule 1 deviation: used `detach` instead — see Deviations. All 13 `allow_threads` occurrences are in documentation comments explaining the deviation. |
| `detach` in counter.rs | 0 (plan) | 8 | Rule 1 deviation: `detach` is the canonical non-deprecated pyo3 0.27.2 API; 2 call sites + 6 comment refs. |
| `Arc<RustPyCounter>` in counter.rs | >= 1 | 8 | Field swap + free-function signatures + comments |
| `threads=None` in counter.rs | >= 1 | 1 | The `#[pyo3(signature = (..., threads=None))]` |
| `build_global` in counter.rs | >= 1 | 2 | Real call + comment |
| `.expect(` in counter.rs | 0 | 0 | Err-tolerant `let _ =` idiom (Pitfall 3 mitigated) |
| `available_parallelism` in counter.rs | (not in plan) | 2 | Used instead of `num_cpus::get()` — see Decisions |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used `py.detach(..)` instead of the deprecated `py.allow_threads(..)`**
- **Found during:** Task 1 build verification (`cargo build`)
- **Issue:** The plan's RESEARCH (§Pitfall 4, §Standard Stack pyo3 row) and `<phase_critical_reminders>` claimed that `Python::allow_threads` is the pyo3 0.27.2 API and `Python::detach` is "the rename landing in pyo3 0.28+ and is NOT available in 0.27.2." This is factually inverted. The actual pyo3 0.27.2 source (`~/.cargo/registry/src/.../pyo3-0.27.2/src/marker.rs:520-540`) shows:
  - `allow_threads` is `#[deprecated(note = "use Python::detach instead", since = "0.26.0")]` — deprecated since 0.26.0, two minors before 0.27.2.
  - `allow_threads` simply delegates: `pub fn allow_threads<T, F>(self, f: F) -> T where F: Ungil + FnOnce() -> T, T: Ungil { self.detach(f) }`.
  - `detach` (marker.rs:594) is the canonical, non-deprecated API in 0.27.2, with the doc example using `py.detach(move || { .. })`.
  - Both enforce the same `Ungil` (= effectively `Send`) bound on the closure.
  Using `allow_threads` under `-D warnings` (the FOUND-01 gate) emits `warning: use of deprecated method ... use Python::detach instead` and fails the build.
- **Fix:** Used `py.detach(move || { .. })` (2 call sites: `add_from_fasta`, `add_from_fastq`). Documented the rationale in code comments at both sites and in the constructor. The closure's `Send` semantics are identical (PyO3 enforces the `Ungil` bound either way — Pitfall 4's mitigation is fully preserved).
- **Files modified:** pyo3/src/counter.rs
- **Verification:** `cargo clippy -- -D warnings` green; `maturin develop --release` green; Python smoke test confirms the GIL-released counting works and produces correct results identical to the sequential path.
- **Committed in:** 52fcd48 (folded into the Task 1 commit)

**2. [Rule 3 - Blocking] Added `rayon` as a direct dep to `pyo3/Cargo.toml`**
- **Found during:** Task 1 build (`cargo build` failed with `unresolved module or unlinked crate rayon`)
- **Issue:** The plan's `<action>` (b) said "num_cpus is transitive via rayon — accessible; do NOT add to pyo3/Cargo.toml", and the RESEARCH Assumption A1 claimed num_cpus is accessible via rayon. Neither is true from the pyo3 crate's perspective: `rayon` is a transitive dependency via the `rustkmer = { path = ".." }` dep, but Cargo does NOT expose transitive deps by name to downstream crates. `rayon::ThreadPoolBuilder` (needed for `build_global`) is unreachable without either (a) a direct `rayon` dep in pyo3/Cargo.toml, (b) a `pub use rayon;` re-export in `rustkmer::lib`, or (c) skipping the `build_global` call. Option (a) is the minimal, honest, standard Cargo pattern; option (b) is out of scope (touches src/lib.rs — violates the plan's "pyo3/src/counter.rs ONLY" scope); option (c) loses the `threads=Some(N)` pool configuration (the whole point of the kwarg).
- **Fix:** Added `rayon = "1.8"` to `pyo3/Cargo.toml` `[dependencies]` with an explanatory comment. The dep is already in `pyo3/Cargo.lock` transitively (via rustkmer → rayon), so this declaration adds zero new compiled code — it just makes the already-present dep accessible by name. Used `std::thread::available_parallelism()` (not `num_cpus::get()` or `rayon::current_num_threads()`) for the `None` → all-cores resolution, so no `num_cpus` dep was added.
- **Files modified:** pyo3/Cargo.toml (1 line + comment)
- **Verification:** `cargo build` green; `cargo clippy -- -D warnings` green; the `build_global` call now compiles and configures the global rayon pool as designed.
- **Committed in:** 52fcd48 (folded into the Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug [research inversion], 1 blocking [missing accessible dep])
**Impact on plan:** Both auto-fixes were necessary for the code to compile and meet the FOUND-01 clippy gate. No scope creep — the Cargo.toml change is the minimal honest declaration of an already-transitive dep, and the `detach` swap is the correct pyo3 0.27.2 API (the plan's research was simply wrong on this point). The plan's INTENT (release the GIL around heavy counting; configure the global pool; add a `threads` kwarg; extract Send types before the closure) is fully preserved.

## TDD Gate Compliance

Task 1 was marked `tdd="true"`. The plan's `<behavior>` block describes Python-observable behavior (`PyCounter(21, threads=0)` raises ValueError; `add_from_fastq` releases the GIL; the extension compiles). The meaningful automated verification of these behaviors at the Python layer is deferred to plan 02-05 (per the plan's own `<verification>` note: "The 02-05 plan will add the pytest cases"). For 02-03, verification was via:

1. **grep acceptance** (the plan's `<acceptance_criteria>`) — all criteria met (adjusted for the `detach` Rule 1 deviation).
2. **`cargo build` + `cargo clippy -- -D warnings`** — the binding compiles green against pyo3 0.27.2.
3. **`maturin develop --release` + Python smoke** — the extension installs and the new `threads` kwarg behaves as specified (None = all cores; 0 raises; positional backward compat holds).
4. **Python-level differential** (ad-hoc, not committed to a test file): `threads=1` vs `threads=4` on the same FASTA produce identical count maps — PCOUNT-04 invariant holds at the Python layer (the commutativity of integer addition argument from RESEARCH applies).

The RED-vs-GREEN distinction is not meaningful for this plan in isolation: the behaviors are only observable end-to-end through the Python interpreter, and the pytest cases that would assert them are explicitly scoped to 02-05. The single Task 1 commit `52fcd48` is GREEN (implementation + the binding compiles + manual smoke confirms behavior). 02-05 will add the committed pytest differential as the durable RED→GREEN gate for PCOUNT-03.

No separate `test(02-03)` (RED) commit because the testable unit is the Python-facing API, and the pytest cases are deferred to 02-05 by the plan's own design.

## Threat Mitigations (from plan `<threat_model>`)

| Threat | Disposition | Applied |
|--------|-------------|---------|
| T-02-11 (Tampering / EoP — GIL violation from capturing Python objects inside the GIL-release closure, Pitfall 4) | mitigate | Both `add_from_fasta` and `add_from_fastq` extract the Python path argument to an owned `String` (`file_path.to_str()?.to_owned()`) and clone the `Arc<RustPyCounter>` BEFORE the `py.detach(move || { .. })` closure. The closure captures ONLY `Send` types. PyO3's `Ungil` bound on the `detach` closure enforces this at compile time — any attempt to capture `&PyString`/`Bound<T>`/`PyObject` fails to compile. |
| T-02-12 (DoS — `build_global` second-call panic when a second PyCounter is constructed, Pitfall 3 Python variant) | mitigate | `PyCounter::new` discards the `build_global` `Result` via `let _ = rayon::ThreadPoolBuilder::new().num_threads(resolved).build_global();`. Constructing two PyCounters (or constructing one after a CLI command in the same process) no longer panics — the second call's `Err` is silently dropped and the existing pool stays in effect. Mirrors 02-01's `execute_count` idiom. |
| T-02-13 (Tampering — `threads=0` or negative causing UB / pool misconfiguration) | mitigate | `PyCounter::new` validates `if let Some(t) = threads { if t < 1 { return Err(PyValueError("Invalid thread count: {t}. Must be >= 1")) } }`. Verified at the Python layer: `PyCounter(21, threads=0)` raises `ValueError`. Mirrors the existing 1..=64 k-mer-size validation style. |

## Known Stubs

None. The `threads` kwarg is fully wired: `None` resolves via `std::thread::available_parallelism()`, `Some(N)` configures the global pool via `build_global`, and the heavy counting methods release the GIL via `py.detach(..)`. The Python-level pytest differential cases (`test_create_counter_with_threads`, `test_threads_none_uses_all_cores`, `test_parallel_counts_match_sequential`) are explicitly scoped to plan 02-05 by the plan's own `<verification>` note — not stubs in this plan.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust boundaries were introduced. The only trust boundaries crossed are (a) the Python-caller → PyCounter constructor boundary (`threads` kwarg validated per T-02-13) and (b) the GIL-holding Python thread → rayon worker OS threads boundary (the `py.detach` closure captures only `Send` types per T-02-11). Both are in-process and mitigated.

## Self-Check: PASSED

- FOUND: pyo3/src/counter.rs (modified — Arc field swap; threads kwarg; py.detach GIL release; free-function helpers; &self methods)
- FOUND: pyo3/Cargo.toml (modified — rayon direct dep added per Rule 3 deviation)
- FOUND: 52fcd48 (Task 1 commit)

---

*Phase: 02-parallel-counting*
*Completed: 2026-07-01*
