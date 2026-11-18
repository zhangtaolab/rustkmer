---
phase: 06-parallelism-correctness-hot-path
plan: 03
subsystem: counting/hot-path
tags: [rolling-encoder, reverse-complement, differential, par-03, timing-gate, pyo3]

requires:
  - phase: 06-parallelism-correctness-hot-path
    plan: 02
    provides: "LocalKmerCounts per-worker accumulation + checked per-file reduction; the single per-record hot-loop site"
  - phase: 06-parallelism-correctness-hot-path
    plan: 01
    provides: "working --threads and true single-thread baselines for plan 06-04"
  - phase: 05-measurement-regression-harness
    provides: "microbench probe-verified rolling algorithm (190.8 vs 70.9 ns/window) and the 33-chimeric-k-mer N-read evidence"
provides:
  - "RollingEncoder: O(1)-per-window forward and canonical emission for k 1..=32, masked to 2k bits, state reset at every non-ACGT byte and every call"
  - "reverse_complement_u64: bit-parallel reverse complement for right-aligned u64 k-mers, parity-tested against the scalar u128 implementation"
  - "CLI hot loop: rolling path for k <= 32, unchanged u128 per-window path for 33..=64, exact skipped-window accounting"
  - "PyO3 per-sequence file helper: same split, one local per file call and one merge"
  - "Differential suite: ordered emission + skipped counts for k 1..=64 edge matrix, decoded local-map equality, and an ignored release timing gate (ratio 0.452)"
affects: [06-04, 07, 09]

actuals:
  tokens: 13121
  tasks: 3
  commits: 3
  plan_head_before: 1e53e7b753e02629d4e2ff08b1c3019669b819a8
  plan_head_after: b01f81ca97fd626dc7c6e245c1461cd18360ae42

tech-stack:
  added: []
  patterns:
    - "Rolling state is function-local: every for_each/try_for_each call starts from zero, so record boundaries reset by construction"
    - "Valid-run counter saturates at k (never grows), making the emit predicate overflow-free"
    - "k=32 mask is u64::MAX rather than a 1<<64 shift; all mask/shift edges are asserted by the differential"
    - "Differential compares against the unchanged u128 per-window encoder, never against another rolling implementation"

key-files:
  created:
    - "tests/kmer_rolling_differential_tests.rs"
  modified:
    - "src/kmer/encoding.rs"
    - "src/kmer/canonical.rs"
    - "src/cli/commands/count.rs"
    - "pyo3/src/counter.rs"
    - "pyo3/tests/test_counter.py"

key-decisions:
  - "RollingEncoder is a Copy value with k/mask/shift precomputed; the hot loop constructs it per record (a handful of instructions) instead of threading a mutable encoder across rayon chunks"
  - "The rolling pass is a fallible sink (try_for_each) so LocalKmerCounts::increment failures propagate without a per-window error branch in the caller; for_each is the infallible wrapper"
  - "Each rolling call returns its skipped-window count (total windows minus emitted), letting both surfaces add exactly the reference skip total to the local accumulator"
  - "canonical.rs re-exports RollingEncoder rather than duplicating it: forward and reverse-complement state must stay in one implementation"
  - "add_sequence/add_kmer stay on their unchanged shared-increment, per-window path (plan scope: only the file helper feeds the local accumulator and inherits the rolling win)"

requirements-completed: [PAR-03]

coverage:
  - id: D1
    description: "Rolling emission equals the per-window reference as an ordered sequence for every k 1..=32, forward and canonical, with explicit k 1/21/31/32 cases"
    requirement: PAR-03
    verification:
      - kind: integration
        ref: "cargo test --locked --test kmer_rolling_differential_tests#rolling_matches_reference_for_k_1_through_32; #explicit_edge_k_values_match_reference"
        status: pass
    human_judgment: false
  - id: D2
    description: "Valid-run reset at every non-ACGT byte and at every record boundary; skipped-window counts match the reference on N runs, lowercase, empty/short sequences, and record pairs with k-1 spanning windows"
    requirement: PAR-03
    verification:
      - kind: integration
        ref: "cargo test --locked --test kmer_rolling_differential_tests#rolling_skipped_count_matches_reference_on_invalid_bytes; #full_edge_matrix_matches_reference_for_k_1_through_64"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bit-parallel reverse_complement_u64 equals the scalar u128 reverse complement narrowed to u64 for every k 1..=32 and at the all-zero/all-ones extremes; k=32 uses the all-ones mask with no overflowing shift"
    requirement: PAR-03
    verification:
      - kind: unit
        ref: "cargo test --locked --test kmer_rolling_differential_tests#bit_parallel_reverse_complement_matches_scalar_u128; #rolling_encoder_rejects_out_of_range_k"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLI counts through the rolling encoder for k <= 32 and the u128 per-window path for 33..=64, with decoded count maps equal to the reference"
    requirement: PAR-03
    verification:
      - kind: e2e
        ref: "cargo test --locked --test kmer_rolling_differential_tests#cli_local_path_matches_reference_for_k_21_32_and_64; #u128_fallback_edge_inputs_match_reference_and_cli (real CARGO_BIN_EXE_rustkmer at k 21/32/33/48/64)"
        status: pass
      - kind: integration
        ref: "python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only -> PARITY OK distinct=2400000 total=2400000"
        status: pass
    human_judgment: false
  - id: D5
    description: "PyCounter file counting uses the rolling path for k <= 32 and matches a pure-Python sliding-window reference for k 21/32/64, canonical on/off, lowercase and filtered Ns; add_sequence stays on the unchanged path and matches the same reference"
    requirement: PAR-03
    verification:
      - kind: integration
        ref: "maturin develop --release + python -m pytest pyo3/tests/test_counter.py -q (105 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The rolling path is at most 0.75x the per-window duration on a release-build corpus of at least 200000 windows"
    requirement: PAR-03
    verification:
      - kind: integration
        ref: "cargo test --release --locked --test kmer_rolling_differential_tests -- --ignored -> windows=260000 ratio=0.452"
        status: pass
    human_judgment: false

duration: 7 min
completed: 2026-11-12
status: complete
---

# Phase 06 Plan 03: Rolling Encoder & Bit-Parallel Reverse Complement Summary

**The counting hot path now encodes with a rolling 2-bit encoder: for every k 1..=32 the emitted sequence and skipped-window counts are byte-for-byte those of the unchanged per-window reference, k 33..=64 keeps the u128 path, and the release timing gate measures the rolling path at 0.452x per-window time (threshold 0.75).**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-12T12:27:41Z
- **Completed:** 2026-11-12T12:34:44Z
- **Tasks:** 3
- **Files modified:** 6 (5 modified, 1 created)

## Accomplishments

- **PAR-03 core (`src/kmer/encoding.rs`).** Added `RollingEncoder` for k 1..=32: one forward value and one incrementally updated reverse-complement value, forward/canonical emission, a `2*k`-bit mask with the k=32 all-ones special case, ASCII-uppercase acceptance, and reset of forward/reverse/valid-run on every non-ACGT byte. `try_for_each` returns the skipped-window count (`total windows - emitted`); `for_each` is the infallible wrapper.
- **Bit-parallel reverse complement.** `reverse_complement_u64` complements 2-bit pairs, swaps 2-bit and 4-bit groups, byte-swaps, and right-aligns; it equals `reverse_complement_u128` narrowed to u64 for every k 1..=32, and returns 0 out of range instead of shifting by 64+.
- **CLI wiring (`src/cli/commands/count.rs`).** `count_record_into` routes k <= 32 through `RollingEncoder` in the counter's canonical mode, feeds each value into the worker `LocalKmerCounts`, and adds the rolling skip count via `record_skipped()`; k 33..=64 is the untouched per-window u128 branch. No shared-state or `.rkdb` writer change.
- **PyO3 wiring (`pyo3/src/counter.rs`).** `process_sequence_into_local` uses the same split, still one local per file call and one checked merge. `add_sequence`/`add_kmer` remain on their documented shared-increment path; non-ACGT filtering is unchanged (no D2 behavior).
- **Proof suite (`tests/kmer_rolling_differential_tests.rs`).** 10 tests: k 1..=32 ordered differential (explicit k 1/21/31/32), N at every position, consecutive-N runs of 1/2/3/k-1/k/k+1, lowercase and mixed case, empty/short sequences, record-boundary pairs (with the k-1 spanning-window non-vacuity assertion), reverse-complement parity, out-of-range k rejection, decoded local-map equality for k {1,21,31,32,33,64} × canonical, k 33..=64 fallback parity through N at every position, end-to-end CLI equality at k 21/32/33/48/64, and the ignored release timing gate.
- **Python proof extension (`pyo3/tests/test_counter.py`).** A dedicated rolling-path parity class covers add_from_fastq and add_sequence for k 21/32/64 × canonical, with lowercase and filtered Ns, against a pure-Python sliding-window reference.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rolling encoder + bit-parallel reverse complement (tracer)** — `a1bcb28` (feat)
2. **Task 2: CLI and PyO3 hot-loop wiring** — `552b307` (feat)
3. **Task 3: Full k 1..=64 edge matrix + release timing gate** — `b01f81c` (test)

**Plan metadata:** (docs commit created after this summary)

## Files Created/Modified

- `src/kmer/encoding.rs` — `RollingEncoder` (new/for_each/try_for_each/mask) and `reverse_complement_u64`, with the rolling state machine documented against T-06-07/T-06-08/T-06-11.
- `src/kmer/canonical.rs` — re-exports `RollingEncoder` so canonical-aware call sites reach it through the canonical module.
- `src/cli/commands/count.rs` — `count_record_into` rolling branch, imports, and PAR-03 docs; fallback loop unchanged.
- `pyo3/src/counter.rs` — `process_sequence_into_local` rolling branch and imports; incidental rustfmt normalization of pre-existing drift in this touched file (see Deviations).
- `tests/kmer_rolling_differential_tests.rs` (new) — the full differential, CLI end-to-end checks, local-map matrix, and timing gate.
- `pyo3/tests/test_counter.py` — rolling-path parity class (12 new cases).

## Verify Evidence

- `cargo test --locked --test kmer_rolling_differential_tests` → **9 passed, 1 ignored** (the timing gate). Task 1 intermediate: **5 passed**; Task 2 intermediate: **6 passed**.
- `cargo test --locked --lib kmer::` → **28 passed, 0 failed**.
- `cargo test --release --locked --test kmer_rolling_differential_tests -- --ignored --nocapture` → `PAR-03 timing gate: windows=260000 per_window=3.841208ms rolling=1.734542ms ratio=0.452` → **1 passed** (threshold 0.75).
- `cargo build --release --locked` → OK. `python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only --out scripts/bench/scratch/par03_parity.json` → `PARITY OK distinct=2400000 total=2400000`; provenance validation → `PAR-03 CLI parity OK`.
- `maturin develop --release --manifest-path pyo3/Cargo.toml` → built/installed; `.venv311/bin/python -m pytest pyo3/tests/test_counter.py -q` → **105 passed** (93 existing + 12 new).
- Full suite `cargo test --locked` → **exit 0**: lib 242 passed; kmer_rolling_differential_tests 9 passed/1 ignored; thread_local_count_tests 9 passed; parallel_count_tests 4 passed; dense_differential_tests 6 passed; golden_tests 34 passed; thread_pool_size_tests 2 passed; doc-tests 13 passed/1 ignored.
- `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 (root) and same for `pyo3/Cargo.toml` → exit 0.
- `rustfmt --edition 2021 --check` over all five Rust files touched → clean.
- Edge matrix evidence: for k 1..=32, ordered emission and skipped counts equal the reference for N at every position of a 191-base fixture, consecutive N runs, lowercase/mixed case, empty and shorter-than-k, and record pairs (per-record emission vs `k-1` extra windows when naively concatenated). For k 33..=64 the rolling constructor is rejected and the u128 fallback maps/skips equal the reference; the real CLI at k 33/48/64 matches the reference text map.

## Decisions Made

- The rolling hot path constructs a `RollingEncoder` per record rather than carrying mutable state across a rayon chunk: `for_each` is stateless, so a record boundary can never leak state, and construction is a few instructions against hundreds of windows.
- `try_for_each` is generic over the sink error so `LocalKmerCounts::increment` failures propagate without a per-window branch; the CLI preserves its existing error text (`Failed to increment k-mer count: ...`).
- The skipped count is computed as `total windows - emitted`, which is exactly "windows containing a non-ACGT byte" and needs no extra counter in the hot loop.
- The differential deliberately references the unchanged u128 per-window encoder (not another rolling implementation) so a shared rolling bug cannot hide.
- The k 33..=64 proof is routed through the local accumulator and the real CLI, since the rolling encoder must reject those k values; encoder rejection + end-to-end map equality pins the routing boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CLI test helper placed `-C` between `-i` and its value**
- **Found during:** Task 2 (first run of `cli_local_path_matches_reference_for_k_21_32_and_64`)
- **Issue:** clap parsed `-C` as the next flag and reported `a value is required for '--input <INPUT>...'`; the canonical-true half of the matrix never ran.
- **Fix:** append all `-i` values first, then `-C`. The CLI itself was correct; only the test invocation was wrong.
- **Files modified:** `tests/kmer_rolling_differential_tests.rs`
- **Commit:** `552b307`

**2. [Rule 1 - Style] Incidental rustfmt normalization of pre-existing drift in `pyo3/src/counter.rs`**
- **Found during:** Task 2 formatting pass
- **Issue:** the file carried pre-existing rustfmt drift (line ~200 `RustPyCounter::new` call and the two compressed-file opener calls) that 06-02 had deferred as out of scope.
- **Fix:** formatting the touched file with `rustfmt` normalized those call sites; no behavior change. This resolves the `pyo3/src/counter.rs` entry previously recorded in `deferred-items.md` (the unrelated `src/database/prefix_cache_merge.rs` entry stands).
- **Files modified:** `pyo3/src/counter.rs`
- **Commit:** `552b307`

### Environment accommodations

- The plan's verify command sets `VIRTUAL_ENV` but the ambient shell also exports `CONDA_PREFIX`; maturin refuses both. Executed as `env -u CONDA_PREFIX VIRTUAL_ENV=... PATH=... maturin ...` (same accommodation as 06-02). No code or API impact.

**Total deviations:** 2 auto-fixed (1 test-invocation bug, 1 formatting normalization) + 1 environment accommodation. No plan-intent deviation; no production behavior beyond the planned rolling routing changed.

## Issues Encountered

- The full suite, release build, maturin rebuild, and both clippy gates were run after the final Task 3 commit; all green. Generated parity artifacts live under gitignored `scripts/bench/scratch/`.
- The timing gate skips itself with an explicit message when run with debug assertions (debug timings are not verdict-bearing), and prints the measured numbers so a release run is always auditable.

## User Setup Required

None - no external service configuration required. (Local `.venv311`, maturin, and jellyfish 2.3.1 were already present.)

## Known Stubs

None.

## Threat Flags

None. The plan's threat register is satisfied: **T-06-07** (2k-bit mask, k=32 all-ones special case, rolling rejection above 32, full k 1..=64 differential), **T-06-08** (both surfaces validate k 1..=64 before routing; rolling rejects out-of-range k; no overflowing shift is reachable), **T-06-11** (forward/reverse/valid-run cleared on every non-ACGT byte; state is function-local per record; N-at-every-position + consecutive-N + record-boundary differentials), **T-06-SC** (no dependency or manifest changes; all builds used `--locked`). No new network endpoints, auth paths, or schema changes; the `.rkdb` writer and output sorting were not touched.

## Next Phase Readiness

- Plan 06-04 can measure the post-06-02+06-03 hot path against the 06-01 baselines (synthetic 18.77 s / real slice 142.54 s); the release timing gate already shows the encode stage at 0.452x the per-window path.
- Phase 7 can lift `RollingEncoder` and `LocalKmerCounts` into the persistent-worker engine unchanged: the CLI/PyO3 wiring is two thin per-record functions.
- Phase 9's Python engine can reuse the same rolling helper; `add_sequence`'s per-window path remains the intentional comparison baseline.

---

*Phase: 06-parallelism-correctness-hot-path*
*Completed: 2026-11-12*

## Self-Check: PASSED
