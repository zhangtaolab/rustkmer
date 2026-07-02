//! Phase 2 differential correctness test (PCOUNT-04) — commutativity of integer
//! addition makes 1-vs-N divergence a definitive concurrency bug.
//!
//! Plan 02-04 (decision D-10): this binary owns the pre-refactor count MAP
//! baseline capture. The capture generator (`capture_parallel_count_baseline`)
//! is `#[ignore]`d and run-once — it materialized the committed JSON
//! baselines under `tests/fixtures/parallel_count_baseline/` from the
//! pre-DashMap `KmerCounter` BEFORE plan 02-02 swapped `src/hash/table.rs`
//! to DashMap. The committed JSON is the D-10 ground truth; do NOT regenerate
//! it, or the differential loses its reference.
//!
//! Plan 02-05 (this file): the four differential/baseline/determinism/
//! precedence tests below are UN-ignored and asserting. Together they form the
//! PCOUNT-04 gate:
//!   - `differential_threads_1_vs_n` — 1-worker vs N-worker count-map equality
//!     across the D-13 matrix (the commutativity differential — any divergence
//!     is a lost-update / double-count bug).
//!   - `baseline_matches_current` — D-10 cross-check: post-refactor counts
//!     equal the committed pre-refactor JSON baselines.
//!   - `deterministic_sorted_output` — D-09: default-sorted output is
//!     byte-identical run-to-run despite sharded DashMap iteration
//!     non-determinism.
//!   - `test_thread_resolution` — PCOUNT-01: the D-07 precedence chain
//!     (`--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus`).
//!
//! Baseline format contract (captured by 02-04):
//!   each cell's count map is serialized as a `BTreeMap<u128, u32>` via
//!   `serde_json::to_string_pretty`, which stringifies the u128 keys. This
//!   file deserializes with `serde_json::from_str::<BTreeMap<String, u32>>()`
//!   and parses the keys back to u128. Keep this exact.

// `mod common;` was omitted by 02-04 (the differential stubs did not yet need
// the shared factories). 02-05 still does not need them — the differential
// compares BTreeMap<u128, u32> directly (the order-independent ground truth,
// per the plan-checker W-2 note), not via `databases_have_same_kmers` (which
// takes an `RKDatabase`). Left out so `clippy -D warnings` stays green.

use rustkmer::cli::commands::count::resolve_thread_count_from;
use rustkmer::error::ProcessingError;
use rustkmer::error::ProcessingResult;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use std::sync::Arc;

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

/// Count the fixed input with the given (k, canonical) via the current
/// `KmerCounter` (single-threaded — used by the baseline capture in 02-04
/// and by `baseline_matches_current` here).
///
/// Mirrors the per-record encode/canonicalize loop in
/// `golden_generate.rs::count_input`: for each overlapping k-mer window,
/// encode → optionally canonicalize → `counter.increment`. The returned
/// BTreeMap is sorted by u128 key, so the serialized JSON is byte-stable
/// run-to-run regardless of the HashMap's iteration order.
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

/// Count `input` with N worker threads sharing one `Arc<KmerCounter>` via
/// `std::thread::scope`. Returns the count map as a `BTreeMap<u128, u32>`.
///
/// This is the 1-vs-N differential harness: each of the `num_workers` scoped
/// threads runs the encode/canonicalize/increment loop over a disjoint slice
/// of the input bytes (chunked by index range, NOT by re-slicing mid-k-mer —
/// each thread owns `[i*chunk_len .. (i+1)*chunk_len)` windows). DashMap's
/// sharded `entry().and_modify().or_insert_with()` gives atomic per-key
/// upserts, so concurrent increments from different threads cannot lose
/// updates or double-count (PCOUNT-04 invariant — RESEARCH Pattern 1).
///
/// `build_global` is one-call-per-process (rayon returns Err on a second
/// `ThreadPoolBuilder::build_global`), so we cannot drive the 1-vs-N
/// parallelism through `execute_count` in a single test process. Forcing it
/// at the unit level via `thread::scope` against the same `Arc<KmerCounter>`
/// exercises the exact same DashMap atomicity path the CLI's rayon workers
/// rely on — making this a real commutativity differential, not a subprocess
/// approximation.
///
/// IN-01: the `ScopedJoinHandle`s are now collected and joined so that a
/// worker `Err` (e.g. an `increment` failure or a future failure mode) is
/// propagated instead of silently swallowed. Previously the scope block
/// waited for threads to finish but discarded their results, so a worker
/// failure would produce a false-PASS on the differential.
fn count_input_with_workers(
    k: usize,
    canonical: bool,
    input: &str,
    num_workers: usize,
) -> ProcessingResult<BTreeMap<u128, u32>> {
    let counter = Arc::new(KmerCounter::new(k, canonical, 4096, 1)?);
    let bytes = input.as_bytes();

    if bytes.len() >= k {
        let total_windows = bytes.len() - k + 1;
        // At least 1 worker; clamp to total_windows so we don't spawn idle
        // threads when the input is tiny.
        let workers = num_workers.max(1).min(total_windows);
        let per_worker = total_windows.div_ceil(workers);

        std::thread::scope(|s| -> ProcessingResult<()> {
            let mut handles: Vec<std::thread::ScopedJoinHandle<ProcessingResult<()>>> =
                Vec::new();
            for worker_idx in 0..workers {
                let start = worker_idx * per_worker;
                let end = ((worker_idx + 1) * per_worker).min(total_windows);
                if start >= end {
                    continue;
                }
                let counter_ref = &counter;
                let bytes_ref = bytes;
                handles.push(s.spawn(move || -> ProcessingResult<()> {
                    for i in start..end {
                        let window = &bytes_ref[i..i + k];
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
                        counter_ref.increment(final_kmer)?;
                    }
                    Ok(())
                }));
            }

            // IN-01: join every handle inside the scope so the first worker
            // Err propagates. A panic inside a worker is surfaced via
            // `join().expect(..)` (no reasonable recovery from a panic in the
            // differential harness).
            for h in handles {
                h.join()
                    .expect("worker thread panicked in count_input_with_workers")?;
            }
            Ok(())
        })?;
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
// PCOUNT-04 / D-10 / D-09 / PCOUNT-01 differential gate (02-05)
// ======================================================================

/// PCOUNT-04: `count --threads 1` vs `count --threads N` must produce
/// identical count maps. k-mer counting is integer addition (commutative +
/// associative), so ANY per-k-mer divergence is, by construction, a
/// concurrency bug (lost update or double count) — never benign ordering.
///
/// Because `rayon::ThreadPoolBuilder::build_global` is one-call-per-process,
/// the 1-vs-N parallelism is driven at the unit level via `thread::scope`
/// against a shared `Arc<KmerCounter>` (see `count_input_with_workers`).
/// DashMap's sharded `entry().and_modify().or_insert_with()` is the exact
/// atomicity path the CLI's rayon workers rely on, so this is a real
/// commutativity differential, not a subprocess approximation.
#[test]
fn differential_threads_1_vs_n() -> anyhow::Result<()> {
    let n_workers = std::thread::available_parallelism()
        .map(|v| v.get())
        .unwrap_or(2);

    for cell in all_cells() {
        let map_1 = count_input_with_workers(
            cell.k,
            cell.canonical,
            BASELINE_INPUT,
            1,
        )?;
        let map_n = count_input_with_workers(
            cell.k,
            cell.canonical,
            BASELINE_INPUT,
            n_workers,
        )?;

        assert_eq!(
            map_1, map_n,
            "divergence at k={} canonical={} (concurrency bug): \
             1-worker map has {} entries, {}-worker map has {} entries",
            cell.k,
            cell.canonical,
            map_1.len(),
            n_workers,
            map_n.len(),
        );
    }

    Ok(())
}

/// D-10 cross-check: post-refactor counts MUST equal the committed
/// pre-refactor JSON baselines. For each D-13 cell, load the committed JSON
/// from `tests/fixtures/parallel_count_baseline/k{k}_{canon|noncanon}.json`
/// via `serde_json::from_str::<BTreeMap<String, u32>>()`, parse the stringified
/// u128 keys back to u128, and assert equality with the current
/// single-threaded count map. Catches any count drift introduced by the
/// DashMap swap.
#[test]
fn baseline_matches_current() -> Result<(), Box<dyn std::error::Error>> {
    let dir = Path::new("tests/fixtures/parallel_count_baseline");

    for cell in all_cells() {
        let fname = format!("k{}_{}.json", cell.k, canon_str(cell.canonical));
        let path = dir.join(&fname);
        let json = fs::read_to_string(&path).map_err(|e| {
            format!("failed to read baseline {}: {}", path.display(), e)
        })?;

        // 02-04 serialized BTreeMap<u128, u32>; serde_json stringifies the
        // u128 keys. Deserialize as BTreeMap<String, u32> then parse keys
        // back to u128 (the keys are decimal integer strings).
        let raw: BTreeMap<String, u32> = serde_json::from_str(&json)?;
        let expected: BTreeMap<u128, u32> = raw
            .into_iter()
            .map(|(k_str, v)| {
                let k_u128 = k_str
                    .parse::<u128>()
                    .expect("baseline JSON keys are decimal u128 strings");
                (k_u128, v)
            })
            .collect();

        let actual = count_input_to_map(cell.k, cell.canonical, BASELINE_INPUT)?;

        assert_eq!(
            actual, expected,
            "baseline drift at k={} canonical={}: current counts do not match \
             committed pre-refactor baseline (D-10 regression)",
            cell.k,
            cell.canonical,
        );
    }

    Ok(())
}

/// D-09: default-sort must produce deterministic output run-to-run even
/// though sharded DashMap iteration order is otherwise non-deterministic.
///
/// Counts the fixed input twice with two independent `KmerCounter` instances
/// (two independent sharded-iteration orderings), applies the default-sort
/// path (sort the `get_all_counts` Vec by kmer key — mirroring the
/// `should_sort = !*no_sort` path in `count.rs::output_binary_format`), and
/// asserts the two sorted `Vec<(u128, u32)>` are byte-identical.
#[test]
fn deterministic_sorted_output() -> ProcessingResult<()> {
    for cell in all_cells() {
        // Two independent counter instances -> two independent DashMap
        // iteration orderings from `get_all_counts`. The default-sort path
        // (sort by kmer key) must absorb that nondeterminism so the on-disk
        // output is reproducible run-to-run.
        let counter_a = KmerCounter::new(cell.k, cell.canonical, 4096, 1)?;
        let counter_b = KmerCounter::new(cell.k, cell.canonical, 4096, 1)?;

        for window in BASELINE_INPUT.as_bytes().windows(cell.k) {
            let kmer = encode_kmer_bytes_u128(window)?;
            let final_kmer = if cell.canonical {
                canonical_kmer_u128(kmer, cell.k)?
            } else {
                kmer
            };
            counter_a.increment(final_kmer)?;
            counter_b.increment(final_kmer)?;
        }

        let mut sorted_a = counter_a.get_all_counts();
        let mut sorted_b = counter_b.get_all_counts();
        // Mirror `count.rs::output_binary_format`'s sort key: `*a` (the u128
        // kmer). The default-sort path is `should_sort = !*no_sort`.
        sorted_a.sort_by_key(|(kmer, _)| *kmer);
        sorted_b.sort_by_key(|(kmer, _)| *kmer);

        assert_eq!(
            sorted_a, sorted_b,
            "non-deterministic sorted output at k={} canonical={} (D-09 regression): \
             default-sort must absorb sharded DashMap iteration nondeterminism",
            cell.k,
            cell.canonical,
        );
    }

    Ok(())
}

/// PCOUNT-01: `count --threads N` uses N threads; default uses num_cpus;
/// precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus`.
///
/// Exercises `resolve_thread_count_from` (the pure, env-mutation-free resolver
/// in `src/cli/commands/count.rs`) across the full D-07 precedence chain.
/// Testing the pure helper avoids `env::set_var` in-test (CONCERNS.md flags
/// the unsafe soundness issue on multi-threaded test runners). The helper
/// takes the env values as `Option<usize>` params, so the precedence is
/// verifiable without touching the process environment.
#[test]
fn test_thread_resolution() {
    // `--threads` wins over everything (highest precedence).
    assert_eq!(
        resolve_thread_count_from(Some(4), Some(8), Some(6), 12),
        4,
        "--threads must take precedence over env vars and num_cpus"
    );

    // `RUSTKMER_THREADS` wins when `--threads` is unset.
    assert_eq!(
        resolve_thread_count_from(None, Some(8), Some(6), 12),
        8,
        "RUSTKMER_THREADS must win over RAYON_NUM_THREADS and num_cpus"
    );

    // `RAYON_NUM_THREADS` is the lowest-precedence env tier.
    assert_eq!(
        resolve_thread_count_from(None, None, Some(6), 12),
        6,
        "RAYON_NUM_THREADS must be honored when both higher tiers are unset"
    );

    // All-cores fallback when nothing is set.
    assert_eq!(
        resolve_thread_count_from(None, None, None, 12),
        12,
        "default must be num_cpus when no flag/env is set"
    );

    // Invalid `--threads 0` falls through to the next tier (does not panic).
    assert_eq!(
        resolve_thread_count_from(Some(0), Some(8), None, 12),
        8,
        "--threads 0 must fall through to the next precedence tier, not panic"
    );

    // `num_cpus::get()` returning 0 (unsupported platform) clamps to 1.
    assert_eq!(
        resolve_thread_count_from(None, None, None, 0),
        1,
        "num_cpus=0 (unsupported platform) must clamp to 1"
    );
}
