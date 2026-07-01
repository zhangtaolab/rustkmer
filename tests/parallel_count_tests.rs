//! Phase 2 differential correctness test (PCOUNT-04) — commutativity of integer
//! addition makes 1-vs-N divergence a definitive concurrency bug.
//!
//! Plan 02-04 (decision D-10): this binary owns the pre-refactor count MAP
//! baseline capture. The capture generator (`capture_parallel_count_baseline`)
//! is `#[ignore]]`d and run-once — it materializes the committed JSON
//! baselines under `tests/fixtures/parallel_count_baseline/` from the CURRENT
//! sequential `KmerCounter` BEFORE plan 02-02 swaps `src/hash/table.rs` to
//! DashMap. The committed JSON is the D-10 ground truth; do NOT regenerate it
//! after 02-02 lands, or the differential loses its reference.
//!
//! The differential test bodies (`differential_threads_1_vs_n`,
//! `deterministic_sorted_output`, `test_thread_resolution`) are compiling
//! stubs that are also `#[ignore]`d — they get fleshed in and un-ignored by
//! plan 02-05 once the dashmap + par_iter work is in. They must NOT make real
//! assertions against the pre-refactor code in a way that masks the real
//! checks 02-05 will add.
//!
//! Baseline format contract (02-05 consumes this):
//!   each cell's count map is serialized as a `BTreeMap<u128, u32>` via
//!   `serde_json::to_string_pretty`, which stringifies the u128 keys. 02-05
//!   deserializes with `serde_json::from_str::<BTreeMap<String, u32>>()` and
//!   parses the keys back to u128. Keep this exact.

// `mod common;` is the established header for tests/*.rs binaries (see
// `tests/round_trip_tests.rs:11`, `tests/golden_generate.rs`), but this
// binary's capture path doesn't currently need the shared factories — the
// D-10 baseline is captured from a fixed &str, not a synthesized database.
// Plan 02-05 will pull `mod common;` + the `TestResultExt` adapter back in
// when it fills in the differential stubs (which DO need the order-independent
// `databases_have_same_kmers` helper). Left out for now so `clippy -D
// warnings` stays green on this binary.

use rustkmer::error::ProcessingError;
use rustkmer::error::ProcessingResult;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

/// Fixed, deterministic DNA input used to seed every baseline cell.
///
/// Hardcoded on purpose (D-10 / D-13): the bytes must be reproducible across
/// machines and across the refactor, so the input cannot depend on the OS PRNG
/// or wall clock. The sequences are short, exercise distinct 2-bit codes
/// (A/C/G/T), and produce a handful of collisions (so some count values are
/// \> 1). This is the same input shape as `golden_generate.rs::GOLDEN_INPUT`
/// but kept as a single owned `&str` so the sliding-window loop is
/// straightforward.
const BASELINE_INPUT: &str = "\
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC\
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\
ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC\
GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT\
AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA\
GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT";

/// D-13 matrix cell: (k, canonical). Sorted is intentionally NOT a capture
/// axis — the baseline is a count MAP, which is order-independent by
/// construction (Pitfall 5: byte comparison of unsorted sharded output would
/// flake; comparing count maps sidesteps it entirely).
struct Cell {
    k: usize,
    canonical: bool,
}

fn all_cells() -> Vec<Cell> {
    let mut out = Vec::new();
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            out.push(Cell { k, canonical });
        }
    }
    out
}

fn canon_str(canonical: bool) -> &'static str {
    if canonical {
        "canon"
    } else {
        "noncanon"
    }
}

/// Count the fixed input with the given (k, canonical) via the CURRENT
/// sequential `KmerCounter` (num_threads = 1 is the pre-refactor baseline).
///
/// This helper is the heart of the D-10 baseline — it MUST use the current
/// sequential path unchanged. It mirrors the per-record encode/canonicalize
/// loop in `golden_generate.rs::count_input` (which itself mirrors the count
/// command's FASTA path): for each overlapping k-mer window, encode →
/// optionally canonicalize → `counter.increment`. The returned BTreeMap is
/// sorted by u128 key, so the serialized JSON is byte-stable run-to-run
/// regardless of the HashMap's iteration order.
fn count_input_to_map(
    k: usize,
    canonical: bool,
    input: &str,
) -> ProcessingResult<BTreeMap<u128, u32>> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
    let bytes = input.as_bytes();
    if bytes.len() >= k {
        for window in bytes.windows(k) {
            let kmer = encode_kmer_bytes_u128(window).map_err(|e| {
                ProcessingError::new(format!("encode failure: {}", e))
            })?;
            let final_kmer = if canonical {
                canonical_kmer_u128(kmer, k).map_err(|e| {
                    ProcessingError::new(format!("canonical failure: {}", e))
                })?
            } else {
                kmer
            };
            counter.increment(final_kmer)?;
        }
    }
    Ok(counter.get_all_counts().into_iter().collect::<BTreeMap<_, _>>())
}

// =====================================================================
// D-10 baseline capture (run-once, #[ignore]d — mirrors golden_generate.rs)
// =====================================================================

/// One-shot pre-refactor baseline capture (D-10). Run with:
///   `cargo test --test parallel_count_tests -- --ignored capture_parallel_count_baseline`
///
/// Writes one JSON file per D-13 cell to
/// `tests/fixtures/parallel_count_baseline/`. Each file is a pretty-printed
/// JSON object mapping the stringified u128 k-mer encoding to its u32 count,
/// with keys in sorted numeric order (BTreeMap).
///
/// DO NOT regenerate this baseline after plan 02-02 lands the dashmap swap.
/// The committed JSON is the ground truth the 02-05 differential asserts
/// against; regenerating it from post-refactor code would silently mask any
/// count regression (T-02-04).
#[test]
#[ignore = "one-shot pre-refactor baseline capture (D-10); run with --ignored"]
fn capture_parallel_count_baseline() -> Result<(), Box<dyn std::error::Error>> {
    let dir = Path::new("tests/fixtures/parallel_count_baseline");
    fs::create_dir_all(dir)?;

    for cell in all_cells() {
        let map = count_input_to_map(cell.k, cell.canonical, BASELINE_INPUT)?;

        // Serialize the BTreeMap<u128, u32> directly. serde_json emits each
        // u128 key as a JSON string (JSON object keys MUST be strings), and
        // because the map is a BTreeMap, keys land in NUMERIC order — not
        // lexicographic string order. That numeric ordering is the
        // acceptance-criterion contract and keeps the baseline
        // human-auditable. 02-05's deserialize path
        // (`serde_json::from_str::<BTreeMap<String, u32>>()` then parse keys
        // back to u128) is unaffected by the source-map ordering — it
        // rebuilds its own BTreeMap either way — but numeric order here
        // makes diffing two baselines trivial.
        let fname = format!("k{}_{}.json", cell.k, canon_str(cell.canonical));
        let path = dir.join(&fname);
        let json = serde_json::to_string_pretty(&map)?;
        fs::write(&path, json)?;
        eprintln!(
"wrote {} ({} kmers)",
            path.display(),
            map.len()
        );
    }

    Ok(())
}

// =====================================================================
// Differential stubs (lands in 02-05 once dashmap + par_iter are in)
// ======================================================================
//
// These compile today but make NO real assertions — they are `#[ignore]`d so
// the pre-refactor test gate stays green without masking the checks 02-05
// will add. Use `#[ignore]` with a clear reason string (not `#[should_panic]`)
// so a future `--ignored` run surfaces them as TODO markers, not as passing
// tests.

/// PCOUNT-04: `count --threads 1` vs `count --threads N` must produce
/// identical count maps. k-mer counting is integer addition (commutative +
/// associative), so ANY per-k-mer divergence is, by construction, a
/// concurrency bug (lost update or double count) — never benign ordering.
///
/// TODO(02-05): for each D-13 cell, count the fixed input with threads=1 and
/// threads=N, assert the two count maps are equal, and assert both equal the
/// committed baseline JSON captured above.
#[test]
#[ignore = "lands in 02-05 once dashmap + par_iter are in"]
fn differential_threads_1_vs_n() -> anyhow::Result<()> {
    // Intentionally a no-op stub. 02-05 will fill in the assertion and
    // un-ignore this test. Leaving it empty (not panicking) keeps the
    // pre-refactor `cargo test` gate green without masquerading as a
    // meaningful check.
    Ok(())
}

/// D-09: default-sort must produce deterministic output run-to-run even
/// though sharded DashMap iteration order is otherwise non-deterministic.
///
/// TODO(02-05): count the fixed input twice with threads=N, assert the two
/// sorted outputs are byte-identical (sort absorbs the iteration-order
/// nondeterminism).
#[test]
#[ignore = "lands in 02-05 once default-sort is wired through count.rs"]
fn deterministic_sorted_output() -> anyhow::Result<()> {
    let _ = all_cells();
    Ok(())
}

/// PCOUNT-01: `count --threads N` uses N threads; default uses num_cpus;
/// precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus`.
///
/// TODO(02-05): exercise `resolve_thread_count_from` across the precedence
/// chain (the unit-testable pure helper added by plan 02-01) and assert the
/// resolved count for each input source.
#[test]
#[ignore = "lands in 02-05 once thread-resolution plumbing is in"]
fn test_thread_resolution() -> anyhow::Result<()> {
    let _ = all_cells();
    Ok(())
}
