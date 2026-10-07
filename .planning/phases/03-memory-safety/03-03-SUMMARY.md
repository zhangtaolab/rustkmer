---
phase: 03-memory-safety
plan: 03
subsystem: hash
tags: [rust, kmer, dense-storage, u64, u128, dashmap, golden-baseline, differential, proptest]

requires:
  - phase: 03-memory-safety
    plan: 01
    provides: "`.rkdb` v2 on-disk format proven byte-identical (golden_tests 34/34) — the DENSE-02 ground truth this plan must preserve"
  - phase: 03-memory-safety
    plan: 02
    provides: "367-test green baseline + clippy -D warnings gate on both crates; src/hash/ untouched by the temp-lifecycle work"
  - phase: 02-parallel-counting
    provides: "Phase 2 D-05 internal-swap discipline (RwLock<HashMap> -> DashMap with a byte-identical public surface); PCOUNT-04 1-vs-N differential"
  - phase: 01-foundation-quality
    provides: "12 committed golden .rkdb fixtures + sha256 manifest (D-10); log:: facade + clippy gate"

provides:
  - "rustkmer::hash::KmerKey — width-selected DashMap key (U64(u64) for k<=32, U128(u128) for 33..=64) with from_u128/to_u128"
  - "KmerCounter.table is DashMap<KmerKey, u32>; storage width chosen at new() from kmer_length"
  - "memory_usage() branches on width (24+8+4 vs 24+16+4 per entry) and is therefore a direct observable of the selected variant"
  - "tests/dense_differential_tests.rs — 6 GREEN decoded-level differential tests across the D-13 matrix, three independent references each"
  - "tests/dense_proptest_tests.rs — 3 GREEN random-DNA DENSE-03 properties (256 cases each)"
  - "tests/golden_sha256_tests.rs — 2 GREEN DENSE-02 byte-identity tests over all 12 fixtures (GREEN pre-swap AND post-swap)"
  - "A proven (not merely asserted) narrowing guard: dense_narrowing_rejects_high_bits_on_the_u64_path — T-03-09"
affects: [03-04, 03-05, phase-04-benchmark]

actuals:
  tokens: 14759
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Width-selected enum key: one concrete `DashMap<KmerKey, u32>` instead of a parallel counter type or a generic-over-width counter — the enum's derived Hash/Eq make the existing `entry().and_modify().or_insert_with()` atomicity chain work verbatim"
    - "Conversion at the boundary in both directions (`from_u128` in, `to_u128` out) is what makes a RAM-only type swap possible with a byte-identical public surface"
    - "The golden-baseline comparison doubles as a transcription guard on the test fixture itself — it caught a 2-character drift in a hand-copied DNA constant immediately (see Deviations #1)"
    - "Decode-side pairing: every cross-width comparison decodes with the decoder matching the encoder that produced the integer, so D-04's 'never compare raw integers across widths' holds structurally, not by convention"

key-files:
  created:
    - src/hash/key.rs
    - tests/dense_differential_tests.rs
    - tests/dense_proptest_tests.rs
    - tests/golden_sha256_tests.rs
  modified:
    - src/hash/table.rs
    - src/hash/mod.rs
    - src/lib.rs
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "KmerKey is a `pub` re-export from both `hash` and the crate root (`rustkmer::KmerKey`), matching the existing `pub use hash::KmerCounter` convenience re-export — the differential tests need it from an external test crate, the same reason 03-01 made estimate_total_kmers pub"
  - "The narrowing `debug_assert!` lives inside `KmerKey::from_u128`, not in `increment`. The plan put it in `increment`; `get_count` and `merge` narrow at the same boundary too, so a single assertion covers all three call sites instead of leaving two unguarded. `increment` therefore still trips it (it routes through `from_u128`), satisfying the plan's behavior spec with strictly wider coverage"
  - "No `use_u64: bool` field. The plan offered 'store a flag OR derive on demand'; `kmer_length` is immutable for the counter's lifetime, so a cached flag could only ever be redundant state capable of disagreeing with the length it was derived from. A private `key_bytes()` helper derives it at the one place that needs it"
  - "The width constants are named module-level consts (HASH_OVERHEAD_PER_ENTRY / U64_KEY_BYTES / U128_KEY_BYTES / COUNT_BYTES) instead of inline magic numbers, so `memory_usage()` and `key_bytes()` cannot drift apart"
  - "DENSE-01's 'roughly half' is asserted on the keyed PAYLOAD (20 B -> 12 B, ratio 0.6), not on the overhead-inclusive total (36/44 = 0.818). The plan's own formula mandates the 24-byte overhead on both widths, which makes its proposed [0.4, 0.7] band unreachable on the total. Asserting the band on the payload is the honest reading and is what the test does — see Deviations #2"
  - "The differential uses THREE independent references per cell (counter-free u128 oracle, production u128-encoder counter, committed golden .rkdb), not two. A single two-way comparison would not localize a failure to 'the counter' vs 'the encoders'"
  - "The k=64 cells additionally assert that `encode_kmer_bytes` REJECTS a 64-mer, proving k=64 exercises a genuinely distinct width rather than being a second dense case in disguise"
  - "The T-03-09 guard test is gated on `#[cfg(debug_assertions)]`: the release profile sets `panic = \"abort\"`, so a release-mode run would abort the process instead of panicking catchably and there is no sound way to assert the guard there"

patterns-established:
  - "A proven mitigation beats an asserted one: the plan asked for a `debug_assert!` and this plan ships a `#[should_panic]` test that proves it fires, plus a width-scoping test proving it does NOT fire on the u128 path (a blanket rejection of large k-mers would be its own bug)"
  - "Golden-baseline assertions catch fixture-transcription drift in the test itself — running a differential against ground truth turns out to guard the test author as much as the code under test"

requirements-completed: [DENSE-01, DENSE-02, DENSE-03]

coverage:
  - id: D1
    description: "DENSE-01: k <= 32 k-mers are stored as u64 keys, roughly halving the counting memory for the common case"
    requirement: DENSE-01
    verification:
      - kind: unit
        ref: "src/hash/table.rs::tests::dense_counter_memory_usage_halved_for_k21"
        status: pass
      - kind: integration
        ref: "tests/dense_differential_tests.rs#dense_u64_matches_u128_k21_canon (asserts memory_usage == n * 36, i.e. the U64 width is actually selected)"
        status: pass
      - kind: integration
        ref: "tests/dense_differential_tests.rs#dense_u64_matches_u128_k32_canon"
        status: pass
      - kind: integration
        ref: "tests/dense_differential_tests.rs#dense_u64_matches_u128_k21_noncanon"
        status: pass
      - kind: integration
        ref: "tests/dense_differential_tests.rs#dense_u64_matches_u128_k32_noncanon"
        status: pass
    human_judgment: false
  - id: D2
    description: "DENSE-02: dense storage is transparent to existing readers — .rkdb v2 stays byte-identical (16 B u128 + 4 B u32 per record, zero-extension on the write path)"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#golden_rkdb_sha256_unchanged_post_dense"
        status: pass
      - kind: integration
        ref: "tests/golden_tests.rs (34/34, unchanged from the 03-02 baseline)"
        status: pass
      - kind: unit
        ref: "src/hash/table.rs::tests::dense_key_round_trip_is_lossless_on_both_widths"
        status: pass
    human_judgment: false
  - id: D3
    description: "DENSE-03: canonicalization and counts stay correct under u64 packing — u64-path counts equal u128-path counts at the DECODED (String, u32) level"
    requirement: DENSE-03
    verification:
      - kind: integration
        ref: "tests/dense_differential_tests.rs (6/6 across k in {21,32,64} x canonical, each cell vs three independent references)"
        status: pass
      - kind: integration
        ref: "tests/dense_proptest_tests.rs (3/3, 256 random DNA cases each)"
        status: pass
    human_judgment: false
  - id: D4
    description: "T-03-09 mitigation: the u128 -> u64 narrowing cannot silently truncate a value with bits above bit 64"
    requirement: DENSE-01
    verification:
      - kind: unit
        ref: "src/hash/table.rs::tests::dense_narrowing_rejects_high_bits_on_the_u64_path (#[should_panic], proves the guard fires)"
        status: pass
      - kind: unit
        ref: "src/hash/table.rs::tests::dense_narrowing_guard_does_not_fire_on_the_u128_path (proves the guard is width-scoped, not a blanket rejection)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase 2 D-05 carry-forward: the public KmerCounter surface is byte-identical — pyo3 and count.rs compile unchanged"
    requirement: DENSE-01
    verification:
      - kind: other
        ref: "grep -nE 'pub fn (new|increment|get_count|get_all_counts)' src/hash/table.rs — all four still u128-typed"
        status: pass
      - kind: other
        ref: "(cd pyo3 && cargo build --release)"
        status: pass
      - kind: other
        ref: "(cd pyo3 && cargo clippy --all-targets -- -D warnings)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Phase 2 PCOUNT-04 NOT regressed: concurrent increment atomicity survives the key swap"
    requirement: DENSE-03
    verification:
      - kind: unit
        ref: "src/hash/table.rs::tests::test_increment_atomic_under_concurrency"
        status: pass
      - kind: unit
        ref: "src/hash/table.rs::tests::test_overflow_preserved (verbatim u32::MAX overflow message)"
        status: pass
      - kind: integration
        ref: "tests/parallel_count_tests.rs (4/4 + differential_threads_1_vs_n)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Phase 1 D-13 carry-forward: the coverage matrix k in {21,32,64} x canonical spans both widths"
    requirement: DENSE-03
    verification:
      - kind: integration
        ref: "tests/dense_differential_tests.rs — 6 cells; k=21/k=32 on KmerKey::U64, k=64 on KmerKey::U128"
        status: pass
    human_judgment: false
  - id: D8
    description: "Real (not modelled) memory reduction at human-genome scale"
    requirement: DENSE-01
    verification: []
    human_judgment: true
    rationale: "`memory_usage()` is a MODEL, not a measurement — the 24-byte-per-entry hash/shard overhead is an inherited constant (see Deferred Items). The key-width halving is proven exactly; the total-RSS effect is not, because CI has no human-scale dataset and swapping the model for a measurement needs an allocator hook or an empirical heap delta. Phase 4's benchmark against CRR1936095 is where a human should confirm the real number, and it is also where the query/read path (still u128) would show up as residual cost."

commits: 2
plan_head_before: 4317c6981811e02780fde346b2a4fb04838e8938
plan_head_after: f3d0c67c20767e6097db3bd1d49aa5a271ac92b6

duration: 10min
completed: 2026-10-07
status: complete
---

# Phase 3 Plan 3: Dense u64 Counter Key (Width-Selected `KmerKey`) Summary

**The counting hot path now stores k ≤ 32 k-mers in 8-byte keys instead of 16-byte ones — half the keyed memory for the common case — while the `.rkdb` files it writes are byte-for-byte what they were before, and the public API never moved.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-07T02:44:50Z
- **Completed:** 2026-10-07T02:55:07Z
- **Tasks:** 2
- **Files modified:** 7 (+ `deferred-items.md`)

## Accomplishments

- **`KmerKey` (`src/hash/key.rs`)** — `U64(u64)` for k ≤ 32, `U128(u128)` for 33..=64. `from_u128(value, kmer_length)` selects the width; `to_u128()` widens back by zero-extension. Derived `Hash + Eq` means the existing `entry().and_modify().or_insert_with()` chain works verbatim, so **per-key atomicity (PCOUNT-04) and the `u32::MAX` overflow semantics are untouched** — no `get()`+`insert()` split, no TOCTOU window, no deadlock risk.
- **`KmerCounter.table` is `DashMap<KmerKey, u32>`.** Width is chosen at `new()` and derived on demand (`key_bytes()`) rather than cached in a `use_u64` flag that could drift from the immutable `kmer_length`.
- **Public API is byte-identical.** `increment(u128)`, `get_count(u128)`, `get_all_counts() -> Vec<(u128, u32)>`, `get_top_n`, `filter_by_count`, `merge` all keep their signatures. `src/cli/commands/count.rs` and `pyo3/src/counter.rs` were not modified and both crates compile clean.
- **DENSE-02 is proven, not assumed.** All 12 committed `.rkdb` fixtures still hash to their Phase 1/2 manifest values — and `tests/golden_sha256_tests.rs` was **GREEN before the swap landed too**, which is what makes the post-swap pass a differential rather than a tautology. `golden_tests` stays 34/34.
- **DENSE-03 is proven at the decoded level with three independent references per cell**, across the D-13 matrix and 256 random-DNA proptest cases. All comparisons go through the decoder matching the encoder that produced the integer, so D-04's "never compare raw integers across widths" holds structurally.
- **The T-03-09 narrowing guard is proven, not asserted.** `dense_narrowing_rejects_high_bits_on_the_u64_path` is a `#[should_panic]` test that shows the `debug_assert!` actually fires, and `dense_narrowing_guard_does_not_fire_on_the_u128_path` shows the guard is width-scoped rather than a blanket rejection of large k-mers.
- **13 new tests, 0 `#[ignore]`d.** 6 differential + 3 proptest + 2 golden-sha256 + 4 lib.

## Task Commits

1. **Task 1: `KmerKey` enum + Wave-0 dense test scaffolds (RED)** — `ed9048c` (test)
2. **Task 2: `DashMap<KmerKey, u32>` swap + width-aware increment/memory_usage/get_all_counts (GREEN)** — `f3d0c67` (feat)

## Files Created/Modified

- `src/hash/key.rs` (new) — `KmerKey` + `from_u128` / `to_u128`, with the narrowing contract and its rationale documented
- `src/hash/table.rs` — key swap; width-aware `increment`/`get_count`/`get_all_counts`/`get_top_n`/`filter_by_count`/`merge`; `memory_usage()` + new `key_bytes()`; four named width constants; 4 new lib tests; 3 existing private-field test seeds updated to `KmerKey::from_u128(..)`
- `src/hash/mod.rs`, `src/lib.rs` — `pub mod key;` + `KmerKey` re-export
- `tests/dense_differential_tests.rs` (new) — 6 decoded-level differential tests, 3 references per cell
- `tests/dense_proptest_tests.rs` (new) — 3 random-DNA DENSE-03 properties
- `tests/golden_sha256_tests.rs` (new) — DENSE-02 byte-identity over all 12 fixtures
- `.planning/phases/03-memory-safety/deferred-items.md` — 3 new entries (see below)

## Decisions Made

- **The narrowing `debug_assert!` lives in `KmerKey::from_u128`, not in `increment`.** The plan put it in `increment`; `get_count` and `merge` narrow at the same boundary, so one assertion covers all three call sites. `increment` still trips it (it routes through `from_u128`), so the plan's behavior spec is met with strictly wider coverage — and a future fourth narrowing site gets the guard for free.
- **No `use_u64: bool`.** The plan allowed "store a flag OR derive on demand". `kmer_length` is immutable for the counter's lifetime, so a cached flag is redundant state whose only possible behavior is disagreeing with the length it came from. Derived it is.
- **DENSE-01's "roughly half" is measured on the keyed payload, not the total.** 20 B → 12 B is 0.6×; the overhead-inclusive total is 36/44 = 0.818× because the plan's own formula puts the same 24-byte modelled overhead on both widths. The test asserts the band `[0.4, 0.7]` on the payload *and* the exact modelled totals *and* that the saving is exactly 8 B/key — all derived from the real `memory_usage()` output, none of it a tautology about constants. See Deviations #2.
- **Three references per cell, not two.** A counter-free `u128` oracle (no `KmerCounter` in the loop) plus the production `u128`-encoder counter plus the committed golden `.rkdb`. A single two-way comparison would not tell you whether a divergence is in the counter or in the shared encoders.
- **The k=64 cells assert that `encode_kmer_bytes` rejects a 64-mer.** Without that, "k=64 exercises a distinct width" is an assumption; with it, the regression guard is self-validating.
- **The T-03-09 test is `#[cfg(debug_assertions)]`-gated** because the release profile sets `panic = "abort"` — a release run would abort the process instead of panicking catchably, so there is no sound way to assert the guard there.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A 2-character transcription drift in the differential's copy of `GOLDEN_INPUT`**
- **Found during:** Task 2, first GREEN run — all 6 differential tests failed on the golden comparison with exactly one entry differing (`"CACACAC…CACACA"`: 19 vs 17).
- **Issue:** I hand-copied `GOLDEN_INPUT` from `tests/golden_generate.rs` when transcribing the plan's read_first list. Sequence 3 came out 68 characters instead of 66. Because the fixture is repetitive, a 2-character slip still produces a valid-looking k-mer set — every other entry matched, and the only visible symptom was one k-mer's count being off by 2.
- **Fix:** Spliced the generator's array body in programmatically instead of by transcription, and verified byte-identity by diffing the extracted literals. Also had to loosen the plan's prescribed `counter_to_decoded_map(counter, k, width_is_u64: bool)` signature to an explicit `Width` enum, because the decoder must be selected by *how the counter was populated*, not by a bool the caller could plausibly get backwards.
- **Files modified:** `tests/dense_differential_tests.rs`
- **Verification:** all 6 GREEN; `GOLDEN_INPUT` diffed byte-identical against the generator's.
- **Committed in:** `f3d0c67`
- **Worth noting:** the D-10 golden baseline caught this in the test author's own fixture, which is the strongest available evidence that reusing the baselines (rather than regenerating them, as a "clean up the test" instinct would suggest) was the right call.

**2. [Rule 3 - Blocking] The plan's `[0.4, 0.7]` ratio band is unreachable on the formula the same plan mandates**
- **Found during:** Task 2, designing the DENSE-01 assertion
- **Issue:** The `<behavior>` block specifies `memory_usage()` returns `len * (24 + 12)` on the u64 path and `len * (24 + 20)` on the u128 path — a ratio of 36/44 = **0.818**. It then asks the test to "assert the ratio is in [0.4, 0.7]". Those two instructions cannot both hold: the band brackets 12/20 = 0.6, i.e. the ratio computed on the **key+count payload** with the shared 24-byte overhead excluded. The additive constant cancels in the payload ratio but not in the total.
- **Fix:** Kept the formula (it is the concrete, checkable spec, and it preserves the pre-Phase-3 `len * 44` value for k > 32 exactly). Wrote the test to assert the `[0.4, 0.7]` band on the keyed payload, both exact modelled totals, and that the saving is exactly 8 B/key — every value read back from the real `memory_usage()` output.
- **Files modified:** `src/hash/table.rs`, `tests/dense_differential_tests.rs`
- **Verification:** `dense_counter_memory_usage_halved_for_k21` GREEN; k=64 counters still report `n * 44`, matching pre-Phase-3 behaviour.
- **Committed in:** `f3d0c67`

**3. [Rule 1 - Bug] Three pre-existing tests seeded the private `table` field with raw `u128` keys**
- **Found during:** Task 2 compile
- **Issue:** `test_overflow_preserved`, `test_merge_overflow_poisons_consistently`, and `test_filtering_stats_after_overflow_uses_success_denominator` all do `counter.table.insert(kmer, u32::MAX)` to seed a k-mer at the saturation ceiling without 4 billion increments. After the key swap the field is `DashMap<KmerKey, u32>`, so those inserts no longer typecheck — and seeding the *wrong* variant would have silently created an entry `increment` never reads, making the overflow test vacuous.
- **Fix:** Routed each seed through `KmerKey::from_u128(kmer, 31)`, the same width selection `increment` uses.
- **Files modified:** `src/hash/table.rs`
- **Verification:** all three GREEN; `test_overflow_preserved` still asserts the verbatim overflow message.
- **Committed in:** `f3d0c67`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 3 blocking plan inconsistency)
**Impact on plan:** No scope creep. Two were bugs in code/tests this plan touched; the third was an internal contradiction in the plan's own spec, resolved in favour of the checkable formula with the intent-preserving assertion. Nothing was left unverified.

## Issues Encountered

- The plan's `<verify>` commands use `/Users/forrest/GitHub/rustkmer` (a macOS path); this executor runs on Linux at `/home/forrest/Github/rustkmer`. All commands were run with the path adapted — no behavioral difference (same as 03-01 and 03-02).
- `cargo` is not on the default `PATH` here; `export PATH="$HOME/.cargo/bin:$PATH"` is needed per invocation (same as 03-02).
- The repo had no `user.name`/`user.email` configured, so the first commit aborted with "Author identity unknown". Set them **locally** (not `--global`) to the identity already on every existing commit, so this plan's commits match the repo's history rather than introducing a new author.
- **`rustfmt src/lib.rs` follows `mod` declarations** and silently reformatted `src/cli/commands/count.rs` — a file with pre-existing drift that 03-01/03-02 explicitly deferred. Reverted, and the hazard is now written into `deferred-items.md` so whoever finally runs `cargo fmt` is warned.
- I initially truncated `0xCAFE_BABE_DEAD_BEEF` in `test_increment_atomic_under_concurrency`, assuming it was a 128-bit literal that could not survive the k=31 narrowing. It is 16 hex digits — 64 bits — so it was always representable. clippy's `unusual_byte_groupings` lint caught the truncation; the constant is now unchanged from its original value, with a comment recording *why* the width is safe.
- `cargo test --test dense_differential_tests -- --exact` (as literally written in the plan's `<verify>`) selects zero tests, because `--exact` filters on a name that was not supplied. Ran the meaningful equivalent instead (`cargo test --test dense_differential_tests`) — a `<verification>` entry in its own right.

## Known Stubs

None. All 13 new tests are GREEN with 0 `#[ignore]`d, and no `TODO`/`FIXME`/`todo!()` or unwired data source remains in this plan's files. The 3 `#[ignore]`d tests in the repo (`golden_generate`, `parallel_count_tests`'s baseline capture, one property test) are pre-existing run-once generators from Phases 1–2, untouched here.

`cargo fmt --all --check` still reports drift in `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs`. Both are pre-existing and out of scope — but note this plan **closed the third instance**: `src/hash/table.rs` previously had drift and is now rustfmt-clean, because 03-03 edits it for the key swap.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **DENSE-01/02/03 are all closed with machine-checked evidence**, and the k=64 path is provably untouched. 03-04 (dense correctness + v2 compat) inherits a substantially complete story here: the differential and the byte-identity gate both already exist and pass. If 03-04's plan assumed it would author them, that work is now done — 03-04 should focus on what remains uncovered rather than rebuilding these.
- **03-05 (MERGE-04, `PyDatabase.merge`) is unblocked and unaffected.** The pyo3 crate compiles and clippy-gates clean against the swapped counter, and `pyo3/src/counter.rs:505`'s `memory_usage()` consumer keeps working (it will report the smaller dense figure — correct, but see the modelling caveat below).
- **`memory_usage()` returns a model, not a measurement.** Callers — including the Python `PyCounterStats.memory_usage` — will see the dense figure, but the 24-byte-per-entry overhead is an inherited constant. Anything that needs a real memory number should get it from Phase 4's benchmark, not from this method.
- **For downstream planners:** the dense width lives only in `KmerCounter`. `merge_databases_inmemory`'s `HashMapBrown<u128, u32>` accumulator and the `RKDatabase` read path still use `u128`, so an in-memory *merge* of two k=21 databases does not yet get the memory win. Logged in `deferred-items.md` with a suggested follow-up shape.
- **`KmerCounter` gained no new public API**, only a private `key_bytes()` and module-level width constants. `KmerKey` is newly public — treat it as internal storage detail unless you are writing a dense-aware test.

## Deferred Items

See `.planning/phases/03-memory-safety/deferred-items.md`. New in this plan:
- `cargo fmt --all --check` drift in `src/cli/commands/count.rs` + `tests/parallel_count_tests.rs` (carried; `src/hash/table.rs` instance now closed), plus a warning that `rustfmt src/lib.rs` sweeps in `count.rs` as a side effect
- `memory_usage()` is a modelled estimate — the DENSE-01 halving is provable against the keyed payload but not against the overhead-inclusive total, and no measurement replaces the model yet
- The dense `u64` width is not applied to the in-memory merge accumulator or the `RKDatabase` read path (out of scope per 03-CONTEXT's discretion note; suggested fix sketched)

---

## Self-Check: PASSED

- Commits verified present in history: `ed9048c`, `f3d0c67` ✓
- Files verified on disk: `src/hash/key.rs`, `tests/dense_differential_tests.rs`, `tests/dense_proptest_tests.rs`, `tests/golden_sha256_tests.rs`, `src/hash/table.rs`, `src/hash/mod.rs`, `src/lib.rs` ✓
- `commits: 2` is MEASURED via `git rev-list --count 4317c69..HEAD` (ledger written to `.git/gsd-plan-head-before-03-03` before the first commit) ✓
- Task 1 acceptance criteria re-run: `src/hash/key.rs` has the derived `U64(u64)|U128(u128)` enum + both helpers ✓; `pub mod key;` + re-export ✓; `cargo check --lib` 0 ✓; `dense_differential_tests` / `dense_proptest_tests` / `golden_sha256_tests` all compile ✓; **golden_sha256 GREEN pre-swap** ✓; inline `#[cfg(test)]` DENSE-01 stub present and `#[ignore]`d ✓; clippy 0 ✓
- Task 2 acceptance criteria re-run: `DashMap<KmerKey, u32>` ✓; all four public signatures still `u128` ✓; `cargo test --test dense_differential_tests` 6/6, 0 ignored ✓; `dense_proptest_tests` 3/3, 0 ignored ✓; `golden_sha256_tests` 2/2 ✓; `cargo test --lib dense_counter_memory` ✓; `parallel_count_tests` 4/4 + `differential_threads_1_vs_n` ✓; `cargo test --lib` 221/221 ✓; `cargo build --release` ✓; `(cd pyo3 && cargo build --release)` ✓; clippy `-D warnings` clean on **both** crates ✓; no raw-integer cross-width comparison in the differential ✓
- Full `cargo test` green: 221 lib + 34 golden + 26 merge_cleanup + 25 merge_routing + 23 round_trip + 20 mod + 6 dense_differential + 5 cjk + 4 parallel_count + 3 dense_proptest + 3 legacy + 2 golden_sha256 + 2 consistency + 8 property, 0 failures ✓
- `golden_tests.rs` 34/34 + `golden_sha256_tests.rs` 2/2 — `.rkdb` v2 on-disk format untouched (D-10 / DENSE-02 preserved across the swap) ✓
- `cargo fmt --all --check`: every file this plan touched is rustfmt-clean; only the two documented pre-existing files drift ✓

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*