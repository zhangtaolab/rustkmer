//! End-to-end **cross-plan composition gate** for Phase 03 (plan 03-04).
//!
//! Requirements covered:
//!   - **MERGE-01** — "Merge defaults to the streaming/external-sort path;
//!     human-scale merges no longer OOM."
//!   - **MERGE-02** — "Memory-budget admission control — estimate required
//!     memory, route to streaming when estimate exceeds budget."
//!   - **DENSE-02** — ".rkdb v2 stays byte-identical under dense storage."
//!   - **DENSE-03** — "Canonicalization and counts stay correct under `u64`
//!     packing."
//!
//! ## Why this binary exists
//!
//! Plan 03-01 (bounded merge dispatcher) and plan 03-03 (width-selected
//! dense width split) each shipped their own tests, but neither can see the other:
//!
//! | Plan | Test | Blind to |
//! |---|---|---|
//! | 03-01 | `tests/merge_routing_tests.rs` | where the input `.rkdb`'s entries came from — they are synthetic `u128` pairs |
//! | 03-03 | `tests/dense_differential_tests.rs` | the merge entirely — its "database" is an in-memory `HashMap<String, u32>` |
//!
//! Neither proves the **composition**: that counting `k <= 32` through the new
//! `u64` path and then merging the resulting `.rkdb` through the bounded
//! dispatcher yields the same data as the unchanged `u128` path. The trust
//! chain this binary exercises is exactly the plan's threat-model boundary
//! (T-03-13):
//!
//! ```text
//! KmerCounter (u64 in RAM) -> .rkdb v2 write (u128 on disk)
//!     -> merge_databases (bounded admission control, 03-01)
//!     -> .rkdb v2 read -> decoded (String, u32) map
//! ```
//!
//! A width-conversion bug *anywhere* in that chain surfaces here as a
//! decoded-map mismatch.
//!
//! ## Design notes
//!
//! **D-04 — compare at the DECODED `(String, u32)` level, never raw integers.**
//! `encode_kmer_bytes` (u64) left-aligns to bit 64; `encode_kmer_bytes_u128`
//! left-aligns to bit 128, so the same biological k-mer is a *different integer*
//! in each width family. Every comparison below decodes first, and always with
//! the decoder matching the encoder that produced the integer (RESEARCH
//! §Pattern 4).
//!
//! **D-05 — the u128 arm is the committed golden `.rkdb`, not a counter
//! re-run.** Phase 1 D-10 captured those fixtures from the pre-refactor `u128`
//! count path, so they are independent ground truth. The pre-merge equality
//! assertion then separates a count-stage bug from a merge-stage bug instead of
//! leaving the failure ambiguous between the two plans.
//!
//! **Exact count equality, never "non-empty".** Plan 03-01 shipped two latent
//! streaming-merge data-loss bugs (heap-refill strand, chunk-name collision)
//! that survived precisely because `test_merge_streaming_basic` only asserted
//! the result was non-empty — 200 k-mers in, 5 out. Every assertion in this
//! file pins the exact k-mer set, the exact per-k-mer counts, and the header's
//! `total_kmers` accounting.
//!
//! **Both merge routes are exercised.** `merge_databases` has three arms and
//! 03-01 made route selection budget-dependent, so a composition claim covering
//! only one route would be half a claim. Test 1 runs all four
//! (u64/u128 x in-memory/streaming) combinations and requires them to agree;
//! test 3 additionally asserts the streaming and in-memory routes return
//! identical data, which is the property that makes MERGE-02's hard route safe
//! to promote to default.
//!
//! `mod common;` is deliberately omitted — this binary needs none of the
//! `RKDatabase` factories in `tests/common/`, and pulling them in compiles ~20
//! unrelated helper tests into this binary. Same reasoning as
//! `tests/dense_differential_tests.rs`.

use anyhow::Result;
use rustkmer::database::format::{
    DatabaseHeader, KmerEntry, RKDatabase, DATABASE_MAGIC, DATABASE_VERSION,
};
use rustkmer::database::merge_config::MergeConfig;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer;
use rustkmer::kmer::encoding::{
    decode_kmer, decode_kmer_u128, encode_kmer_bytes, encode_kmer_bytes_u128,
};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// The `.rkdb` v2 fixed header size — the only `data_offset` any writer in this
/// crate emits (SPEC P3; enforced loudly by `DatabaseHeader::validate` and by
/// `RKDatabase::from_file_path`).
const RKDB_V2_HEADER_SIZE: u64 = 42;

/// `.rkdb` v2 record size: 16-byte little-endian `u128` k-mer + 4-byte
/// little-endian `u32` count. The dense `u64` width is RAM-only — this must
/// never change (DENSE-02 / threat T-03-10).
const RKDB_V2_RECORD_SIZE: u64 = 20;

/// Modelled hash/shard overhead per entry, mirroring
/// `src/hash/table.rs::HASH_OVERHEAD_PER_ENTRY`.
const HASH_OVERHEAD_PER_ENTRY: usize = 24;
/// Modelled per-entry cost on the dense width: 24 + 8 + 4. This is a MODEL of
/// `KmerCounter::memory_usage`, not a measurement.
const DENSE_BYTES_PER_ENTRY: usize = HASH_OVERHEAD_PER_ENTRY + 8 + 4;
/// Stored key width for the dense table, read from the TYPE so the assertion
/// cannot drift from the representation it claims to observe.
const DENSE_STORED_KEY_BYTES: usize = std::mem::size_of::<u64>();

/// k used for the composition tests — inside the D-13 matrix and `<= 32`, so
/// the dense width is the one under test.
const K: usize = 21;

/// Fixed, deterministic DNA input. MUST match
/// `tests/golden_generate.rs::GOLDEN_INPUT` character for character: the u128
/// arm of this differential reads the committed golden `.rkdb`, which was
/// generated from exactly these six sequences.
///
/// Copy this array **programmatically**, never by hand — plan 03-03 lost a
/// cycle to a 2-character transcription slip in the same constant, and because
/// the fixture sequences are repetitive the slip still produces a
/// valid-looking k-mer set. Verify after any edit with:
///   diff <(sed -n '40,45p'   tests/golden_generate.rs          | sed 's/^ *//') \
///        <(sed -n '117,122p' tests/dense_merge_integration_tests.rs | sed 's/^ *//')
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// A budget no toy input approaches, so the in-memory fast path (D-02) is
/// taken deterministically. Used only with `merge_mode: "auto"` — with
/// `merge_mode: "memory"` an over-budget merge is *rejected* (D-02), which is
/// a different outcome from either route and would make `observed_route`
/// ambiguous.
const HUGE_BUDGET_BYTES: usize = 1024 * 1024 * 1024;

/// Which encoder family produced the integers in a count map.
///
/// Selects the *matching* decoder — `decode_kmer` inverts `encode_kmer_bytes`
/// and `decode_kmer_u128` inverts `encode_kmer_bytes_u128`. Decoding a
/// `u128`-encoded integer with the `u64` decoder is exactly the D-04 mistake.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Width {
    /// `encode_kmer_bytes` / `decode_kmer` — the dense path proper.
    U64,
    /// `encode_kmer_bytes_u128` / `decode_kmer_u128` — the unchanged path.
    U128,
}

impl Width {
    fn decode(self, encoded: u128, k: usize) -> String {
        match self {
            Width::U64 => decode_kmer(encoded as u64, k),
            Width::U128 => decode_kmer_u128(encoded, k),
        }
    }

    fn label(self) -> &'static str {
        match self {
            Width::U64 => "u64-path",
            Width::U128 => "u128-path",
        }
    }
}

/// What the u64-path count observed about itself, so the test can prove the
/// dense width was actually selected rather than assume it.
#[derive(Debug, Clone, Copy)]
struct DenseCountOutcome {
    /// Unique k-mers the counter ended up holding.
    unique_kmers: usize,
    /// Total k-mer windows fed in (i.e. the sum of all counts).
    total_windows: u64,
    /// `KmerCounter::stored_key_bytes()` — read from the LIVE `CounterTable`
    /// variant, so this observes the representation the counter actually holds
    /// rather than restating `kmer_length`. This replaced a
    /// `memory_usage()`-versus-model-constant assertion that stayed green under
    /// the "always store the wide variant" mutation (03-VERIFICATION.md
    /// §Nyquist BLOCKER-1).
    stored_key_bytes: usize,
    /// Whether the counter is on the dense storage path.
    uses_dense_storage: bool,
    /// `KmerCounter::memory_usage()` — a MODEL (24 B overhead + key + 4 B count),
    /// retained so the modelled arithmetic stays pinned; not the storage claim.
    modelled_bytes: usize,
}

/// Count `GOLDEN_INPUT` with the **`u64` encoder family** — the dense path
/// proper, i.e. what `k <= 32` selects inside `KmerCounter` after 03-03 — and
/// write the result as a real `.rkdb` using the same write path
/// `src/cli/commands/count.rs::output_binary_format` uses.
///
/// The write path is replicated rather than delegated to
/// `RKDatabase::from_kmer_pairs` on purpose: `count.rs` builds its own
/// `DatabaseHeader` literal and writes entries via `KmerEntry::write_to`, and
/// this binary is asserting about *what the count command actually emits*.
/// `KmerEntry::write_to` is a little-endian `u128` + a little-endian `u32`, so
/// the counter's `u64` keys cross the wire zero-extended — the DENSE-02
/// widening this plan requires be visible.
fn count_via_u64_path_then_write_rkdb(
    out_path: &Path,
    k: usize,
    canonical: bool,
) -> Result<DenseCountOutcome> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;

    let mut windows_fed: u64 = 0;
    for seq in GOLDEN_INPUT {
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let encoded = encode_kmer_bytes(window)?;
            let kmer = if canonical {
                canonical_kmer(encoded, k)?
            } else {
                encoded
            };
            // `kmer` is a u64; the widening is the public API contract, and the
            // counter narrows it straight back to the dense `u64` width.
            counter.increment(kmer as u128)?;
            windows_fed += 1;
        }
    }

    let mut kmers = counter.get_all_counts();
    let unique_kmers = kmers.len();
    // D-09: sorted output is the count command's default.
    kmers.sort_by_key(|(a, _)| *a);

    let kmer_count = kmers.len();
    let file = std::fs::File::create(out_path)?;
    let mut writer = std::io::BufWriter::new(file);

    // --- mirrors src/cli/commands/count.rs::output_binary_format ---
    let header = DatabaseHeader {
        magic: *DATABASE_MAGIC,
        version: DATABASE_VERSION,
        kmer_size: k as u8,
        total_kmers: kmer_count as u64,
        sorted: true,
        data_offset: 42,
        index_offset: 0,
        canonical: counter.canonical_mode(),
        unique_kmers: kmer_count as u64,
        file_size: 0,
    };
    header.write_to(&mut writer)?;
    for (kmer, count) in kmers {
        KmerEntry::new(kmer, count).write_to(&mut writer)?;
    }
    std::io::Write::flush(&mut writer)?;

    Ok(DenseCountOutcome {
        unique_kmers,
        total_windows: windows_fed,
        stored_key_bytes: counter.stored_key_bytes(),
        uses_dense_storage: counter.uses_dense_storage(),
        modelled_bytes: counter.memory_usage(),
    })
}

/// Copy a committed Phase 1/2 golden `.rkdb` into `dest` and return the path.
///
/// D-10 carry-forward: the fixtures are the pre-refactor `u128`-path baselines,
/// used as ground truth and **never regenerated**.
fn golden_u128_db(k: usize, canonical: bool, sorted: bool, dest: &Path) -> Result<PathBuf> {
    let mode = if canonical { "canon" } else { "noncanon" };
    let order = if sorted { "sorted" } else { "unsorted" };
    let src = PathBuf::from(format!(
        "tests/fixtures/golden_k{}_{}_{}.rkdb",
        k, mode, order
    ));
    std::fs::copy(&src, dest)
        .map_err(|e| anyhow::anyhow!("copy {} -> {}: {}", src.display(), dest.display(), e))?;
    Ok(dest.to_path_buf())
}

/// Load a `.rkdb` from disk and decode it into a string-keyed count map
/// (DENSE-03 / D-04). `width` describes how the file's integers were produced,
/// which the caller always knows.
fn decoded_map_from_rkdb(path: &Path, k: usize, width: Width) -> Result<HashMap<String, u32>> {
    let db = RKDatabase::from_file_path(path)?;
    Ok(decoded_map_from_pairs(&db.all_kmers()?, k, width))
}

fn decoded_map_from_pairs(pairs: &[(u128, u32)], k: usize, width: Width) -> HashMap<String, u32> {
    pairs
        .iter()
        .map(|(encoded, count)| (width.decode(*encoded, k), *count))
        .collect()
}

/// Render the k-mers that differ between two decoded maps, with both values, so
/// a failure names the offending k-mer instead of dumping two multi-hundred
/// entry maps.
fn decoded_map_differs(
    label: &str,
    left: &HashMap<String, u32>,
    right: &HashMap<String, u32>,
) -> String {
    let mut keys: Vec<&String> = left.keys().chain(right.keys()).collect();
    keys.sort_unstable();
    keys.dedup();
    let mut report = format!(
        "{}: {} side has {} k-mers, {} side has {}; differences:",
        label,
        left.len(),
        left.len(),
        right.len(),
        keys.len()
    );
    let mut shown = 0usize;
    for key in keys {
        let a = left.get(key);
        let b = right.get(key);
        if a != b {
            report.push_str(&format!("\n  {}: left={:?} right={:?}", key, a, b));
            shown += 1;
            if shown == 5 {
                report.push_str("\n  ...");
                break;
            }
        }
    }
    if shown == 0 {
        report.push_str("\n  (no per-k-mer difference found — sizes differ only)");
    }
    report
}

/// Assert two decoded maps are equal, with a report that localizes the
/// divergence rather than printing hundreds of entries.
fn assert_decoded_maps_equal(
    label: &str,
    left: &HashMap<String, u32>,
    right: &HashMap<String, u32>,
) {
    assert!(left == right, "{}", decoded_map_differs(label, left, right));
}

/// A `MergeConfig` with the routing-relevant fields pinned.
fn merge_config(temp_dir: &Path, max_memory_usage: usize, merge_mode: &str) -> MergeConfig {
    MergeConfig {
        max_memory_usage,
        merge_mode: merge_mode.to_string(),
        temp_dir: temp_dir.to_path_buf(),
        // Small chunk size so the streaming route genuinely engages its chunk
        // writer + multi-way heap merge even on toy inputs.
        chunk_size: 8,
        ..Default::default()
    }
}

/// Merge the same input twice, so identical inputs are doubled. Doubling makes
/// the merge's count-summing behaviour observable instead of a no-op.
fn merge_two_copies(path: &Path, config: &MergeConfig, label: &str) -> Result<RKDatabase> {
    let inputs = [path.to_path_buf(), path.to_path_buf()];
    RKDatabase::merge_databases(&inputs, config)
        .map_err(|e| anyhow::anyhow!("{} merge of {} failed: {}", label, path.display(), e))
}

/// Which merge implementation `merge_databases` actually dispatched to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Route {
    /// `merge_databases_inmemory` — never touches `config.temp_dir`.
    InMemory,
    /// `merge_databases_streaming` — must create sorted chunk files there.
    Streaming,
}

impl Route {
    fn label(self) -> &'static str {
        match self {
            Route::InMemory => "in-memory",
            Route::Streaming => "streaming",
        }
    }
}

/// Observe — never assume — which merge route a config will take.
///
/// Behavioral probe inherited verbatim from `tests/merge_routing_tests.rs`
/// (plan 03-01's module docstring): `merge_databases` returns an `RKDatabase`,
/// not a strategy tag, so route selection is observed by pointing `temp_dir`
/// at a **nonexistent** directory. The streaming path must create a chunk file
/// there (`Err`); the in-memory path never touches `temp_dir` (`Ok`).
///
/// This helper is only sound for `merge_mode: "auto"`. With
/// `merge_mode: "memory"` an over-budget merge returns `Err` from the D-02
/// *reject* rather than from a temp-file failure, and the two are
/// indistinguishable by outcome alone — so the in-memory arm always pairs
/// `HUGE_BUDGET_BYTES` with `"auto"`.
///
/// **This helper is not optional.** An earlier draft of this file hard-coded
/// `max_memory_usage: 1024` and assumed that cleared the budget; with the
/// golden input's 20 unique k-mers the estimate is only 960 bytes, so every
/// "streaming" arm silently ran the *in-memory* path and the composition claim
/// was vacuous. A mutation test (drop the first k-mer the streaming merge
/// emits — the exact bug class 03-01 found) passed against it. Derive the
/// budget from the input and prove the route, never assume either.
fn observed_route(inputs: &[PathBuf], config: &MergeConfig) -> Route {
    let probe = MergeConfig {
        temp_dir: config
            .temp_dir
            .join("rustkmer_route_probe_this_dir_does_not_exist"),
        ..config.clone()
    };
    match RKDatabase::merge_databases(inputs, &probe) {
        Ok(_) => Route::InMemory,
        Err(_) => Route::Streaming,
    }
}

/// Assert `config` dispatches to `expected`, using the behavioral probe above.
fn assert_route(label: &str, inputs: &[PathBuf], config: &MergeConfig, expected: Route) {
    let actual = observed_route(inputs, config);
    assert_eq!(
        actual,
        expected,
        "{}: merge must take the {} route, but the temp_dir probe observed the {} \
         route — every assertion below would be vacuous on the wrong path",
        label,
        expected.label(),
        actual.label()
    );
}

/// A `merge_mode: "auto"` config whose budget is provably **below** what
/// `merge_databases` will estimate for `inputs`, so the MERGE-02 hard route
/// fires deterministically whatever size the fixture input happens to be.
///
/// The budget is derived from `RKDatabase::estimate_total_kmers` (the same
/// header-only estimator production uses) rather than hard-coded — see the
/// `observed_route` docstring for why a hard-coded constant was wrong here.
fn over_budget_config(temp_dir: &Path, inputs: &[PathBuf]) -> Result<MergeConfig> {
    let mut estimated_kmers: u64 = 0;
    for path in inputs {
        estimated_kmers = estimated_kmers.saturating_add(RKDatabase::estimate_total_kmers(path)?);
    }
    let estimated_bytes = estimated_kmers.saturating_mul(24);
    assert!(
        estimated_bytes > 0,
        "inputs must hold k-mers for the MERGE-02 hard route to be reachable"
    );
    Ok(merge_config(
        temp_dir,
        (estimated_bytes - 1) as usize,
        "auto",
    ))
}

/// MERGE-01 + MERGE-02 + DENSE-02 + DENSE-03 — the composition claim.
///
/// Counting `k=21` canonical through the dense `u64` path and merging the
/// resulting `.rkdb` must equal counting through the unchanged `u128` path
/// (here: the committed Phase 1/2 golden fixture) and merging that — on both
/// merge routes, with exact k-mer sets and exact counts.
#[test]
fn dense_count_then_merge_matches_u128_merge_k21() -> Result<()> {
    let dir = tempfile::tempdir()?;

    // --- Arm A: dense u64 path, written as a real .rkdb --------------------
    let a_path = dir.path().join("dense_u64_path.rkdb");
    let outcome = count_via_u64_path_then_write_rkdb(&a_path, K, true)?;

    assert!(
        outcome.unique_kmers > 0,
        "fixture input produced no k-mers — the differential would be vacuous"
    );
    // --- DENSE-01: the counting arm really stored 8-byte keys ------------------
    // Observed from the live table variant, so this turns RED if the dense
    // storage is ever reverted. The previous assertion here compared
    // `memory_usage()` against a model constant derived from the same
    // `kmer_length` branch and was green for any width.
    assert_eq!(
        outcome.stored_key_bytes, DENSE_STORED_KEY_BYTES,
        "k=21 must store 8-byte (u64) keys (DENSE-01); the whole composition claim \
         could otherwise pass against a counter that had silently reverted to \
         u128 keys"
    );
    assert!(
        outcome.uses_dense_storage,
        "k=21 must be on the dense storage path (DENSE-01)"
    );
    // The modelled arithmetic is still pinned, on the modelled bytes only —
    // `memory_usage()` is a model, not the storage observation.
    assert_eq!(
        outcome.modelled_bytes,
        outcome.unique_kmers * DENSE_BYTES_PER_ENTRY,
        "the modelled per-entry cost must stay {} bytes (24 overhead + 8 key + 4 count)",
        DENSE_BYTES_PER_ENTRY
    );

    // --- Arm B: committed u128 golden .rkdb (D-10 ground truth) -------------
    let b_path = golden_u128_db(K, true, true, &dir.path().join("u128_golden.rkdb"))?;

    // --- Stage 1: count only (pre-merge). Isolates the count stage. ---------
    let dense_only = decoded_map_from_rkdb(&a_path, K, Width::U64)?;
    let u128_only = decoded_map_from_rkdb(&b_path, K, Width::U128)?;
    assert_decoded_maps_equal(
        &format!(
            "dense {} count vs committed u128 golden .rkdb (pre-merge)",
            Width::U64.label()
        ),
        &dense_only,
        &u128_only,
    );

    let window_total: u64 = GOLDEN_INPUT
        .iter()
        .filter(|s| s.len() >= K)
        .map(|s| (s.len() - K + 1) as u64)
        .sum();
    let counted_total: u64 = dense_only.values().map(|c| *c as u64).sum();
    assert_eq!(
        counted_total, window_total,
        "every k-mer window fed in must be accounted for exactly once"
    );
    assert_eq!(
        outcome.total_windows, window_total,
        "the counter must have been fed one window per expected k-mer"
    );

    // --- Stage 2: composition through BOTH merge routes --------------------
    // The in-memory arm pairs a huge budget with `"auto"` so the route probe is
    // unambiguous; the streaming arm uses a budget *derived* from the inputs
    // so the MERGE-02 hard route fires whatever the fixture size is. Both are
    // then proved with `assert_route`.
    let dense_inputs = vec![a_path.clone(), a_path.clone()];
    let u128_inputs = vec![b_path.clone(), b_path.clone()];

    let in_memory_config = merge_config(dir.path(), HUGE_BUDGET_BYTES, "auto");
    assert_route(
        "dense in-memory",
        &dense_inputs,
        &in_memory_config,
        Route::InMemory,
    );

    let streaming_config = over_budget_config(dir.path(), &dense_inputs)?;
    assert_route(
        "dense streaming (MERGE-02 hard route)",
        &dense_inputs,
        &streaming_config,
        Route::Streaming,
    );
    assert_route(
        "u128 streaming (MERGE-02 hard route)",
        &u128_inputs,
        &over_budget_config(dir.path(), &u128_inputs)?,
        Route::Streaming,
    );

    let mut merged_maps: Vec<(&str, HashMap<String, u32>)> = Vec::new();
    for (label, path, config, width) in [
        ("dense in-memory", &a_path, &in_memory_config, Width::U64),
        ("u128 in-memory", &b_path, &in_memory_config, Width::U128),
        ("dense streaming", &a_path, &streaming_config, Width::U64),
        (
            "u128 streaming",
            &b_path,
            &over_budget_config(dir.path(), &u128_inputs)?,
            Width::U128,
        ),
    ] {
        let merged = merge_two_copies(path, config, label)?;
        let pairs = merged.all_kmers()?;
        merged_maps.push((label, decoded_map_from_pairs(&pairs, K, width)));
    }

    // Every arm must agree with every other arm: 4-way equality.
    for i in 0..merged_maps.len() {
        for j in (i + 1)..merged_maps.len() {
            assert_decoded_maps_equal(
                &format!(
                    "{} vs {} (T-03-13 cross-plan composition)",
                    merged_maps[i].0, merged_maps[j].0
                ),
                &merged_maps[i].1,
                &merged_maps[j].1,
            );
        }
    }

    // The merge must have actually done something: doubling identical inputs
    // sums every count, and the unique set is unchanged. Asserting exact
    // counts — not merely "non-empty" — is what 03-01's two data-loss bugs
    // taught this phase.
    let (label, merged_map) = &merged_maps[0];
    assert_eq!(
        merged_map.len(),
        dense_only.len(),
        "{}: merging two copies of the same db must not change the unique k-mer set",
        label
    );
    for (kmer_str, count) in &dense_only {
        assert_eq!(
            merged_map.get(kmer_str),
            Some(&(count * 2)),
            "{}: k-mer {} must carry its summed count {}",
            label,
            kmer_str,
            count * 2
        );
    }
    let merged_total: u64 = merged_map.values().map(|c| *c as u64).sum();
    assert_eq!(
        merged_total,
        window_total * 2,
        "{}: merged counts must sum to exactly twice the input window count — a dropped \
         or double-counted k-mer shows up here even when the maps happen to match",
        label
    );

    Ok(())
}

/// DENSE-02 — the merge **output** must still be a valid `.rkdb` v2 file.
///
/// `tests/golden_sha256_tests.rs` only covers fixtures captured *before* the
/// merge code ran. This asserts the layout of a file that went all the way
/// through count -> write -> merge -> write -> read, which is the composition
/// path the plan's threat model calls out.
#[test]
fn dense_merge_output_preserves_rkdb_v2_layout() -> Result<()> {
    let dir = tempfile::tempdir()?;

    let a_path = dir.path().join("dense_u64_path.rkdb");
    count_via_u64_path_then_write_rkdb(&a_path, K, true)?;

    let inputs = vec![a_path.clone(), a_path.clone()];
    let in_memory_config = merge_config(dir.path(), HUGE_BUDGET_BYTES, "auto");
    let streaming_config = over_budget_config(dir.path(), &inputs)?;

    // Both routes again — the layout claim must hold for whichever one the
    // dispatcher picks under a given budget, and neither may be assumed.
    for (label, config, expected_route) in [
        ("in-memory", &in_memory_config, Route::InMemory),
        ("streaming", &streaming_config, Route::Streaming),
    ] {
        assert_route(label, &inputs, config, expected_route);
        let merged = merge_two_copies(&a_path, config, label)?;
        let out_path = dir.path().join(format!("merged_{}.rkdb", label));
        merged.to_file_path(&out_path)?;

        // 1. Byte-level: magic + version straight out of the raw bytes, so a
        //    rewrite of the header literal cannot hide behind the Rust reader.
        let bytes = std::fs::read(&out_path)?;
        assert_eq!(
            bytes[0..4],
            DATABASE_MAGIC[..],
            "{}: merged output must start with the RKDB magic bytes",
            label
        );
        let version = u16::from_le_bytes([bytes[4], bytes[5]]);
        assert_eq!(
            version, DATABASE_VERSION,
            "{}: merged output must be .rkdb v{}",
            label, DATABASE_VERSION
        );

        // 2. Header-level, through the crate's own reader.
        let mut reader = std::io::Cursor::new(bytes.as_slice());
        let header = DatabaseHeader::read_from(&mut reader)?;
        assert_eq!(
            header.data_offset, RKDB_V2_HEADER_SIZE,
            "{}: .rkdb v2 has exactly one valid data_offset",
            label
        );
        assert_eq!(
            header.kmer_size, K as u8,
            "{}: merged output must preserve the k-mer size",
            label
        );
        assert_eq!(
            header.magic, *DATABASE_MAGIC,
            "{}: header magic mismatch",
            label
        );
        assert_eq!(
            header.version, DATABASE_VERSION,
            "{}: header version mismatch",
            label
        );

        // 3. Header accounting: total_kmers must equal the number of records
        //    actually present. This is the invariant a silent partial merge
        //    would violate (deferred item: the prefix-cache path returns Ok(())
        //    after bucket failures, so its header can undercount).
        let record_count = merged.all_kmers()?.len() as u64;
        assert_eq!(
            header.total_kmers, record_count,
            "{}: header total_kmers must equal the number of records present",
            label
        );
        assert_eq!(
            header.total_kmers,
            RKDatabase::estimate_total_kmers(&out_path)?,
            "{}: the MERGE-02 header-only estimator must agree with the record count — \
             it reads the header, so a disagreement means the header lies",
            label
        );

        // 4. Record size: 42 + 20 * n, exactly. Any widening/narrowing drift in
        //    the merge output breaks this immediately.
        assert_eq!(
            bytes.len() as u64,
            RKDB_V2_HEADER_SIZE + RKDB_V2_RECORD_SIZE * header.total_kmers,
            "{}: merged output must be {} + {} * {} bytes",
            label,
            RKDB_V2_HEADER_SIZE,
            RKDB_V2_RECORD_SIZE,
            header.total_kmers
        );

        // 5. Round-trip: every record must survive `from_file_path`, and the
        //    u64-origin keys must still be recoverable as u64 (zero-extension,
        //    not truncation).
        let reloaded = RKDatabase::from_file_path(&out_path)?;
        assert_eq!(
            reloaded.all_kmers()?,
            merged.all_kmers()?,
            "{}: merged output must round-trip through from_file_path unchanged",
            label
        );
        for (kmer, _) in reloaded.all_kmers()? {
            assert_eq!(
                kmer >> 64,
                0,
                "{}: merged output carries a k-mer with bits above bit 64 — the dense \
                 u64 -> u128 zero-extension drifted (DENSE-02)",
                label
            );
        }
    }

    Ok(())
}

/// MERGE-01 + MERGE-02 — the bounded merge completes on synthetic over-budget
/// input and returns the exact result.
///
/// This is the end-to-end proof that 03-01's estimator + hard-route + streaming
/// path compose. It pins:
///   * the over-budget `auto` route completes (no OOM, no Err),
///   * every input k-mer survives with its summed count (no silent data loss),
///   * the header's `total_kmers` accounts for every record,
///   * and the streaming result equals the in-memory result for the same inputs
///     — the two routes are interchangeable, which is what makes the hard route
///     safe to promote to default.
#[test]
fn bounded_merge_completes_on_synthetic_over_budget_input() -> Result<()> {
    let dir = tempfile::tempdir()?;

    // Two tiny inputs with a deliberate overlap, on real k=21 k-mers.
    let kmers: [(&[u8], u32); 5] = [
        (b"ACGTACGTACGTACGTACGTA", 10),
        (b"TTTTTTTTTTTTTTTTTTTTT", 20),
        (b"GATCACAGGTGATCATACCTG", 30),
        (b"AAAACCCCGGGGTTTTAAAAT", 40),
        (b"CCCCGGGGATATCCCGGGGTG", 50),
    ];

    let mut a: Vec<(u128, u32)> = Vec::new();
    let mut b: Vec<(u128, u32)> = Vec::new();
    for (i, (seq, count)) in kmers.iter().enumerate() {
        let encoded = encode_kmer_bytes_u128(seq)?;
        // Overlap on even indices only; b contributes a halved count there.
        if i % 2 == 0 {
            a.push((encoded, *count));
            b.push((encoded, *count / 2));
        } else {
            a.push((encoded, *count));
        }
    }

    let db_a = RKDatabase::from_kmer_pairs(a, K as u8, false, true)?;
    let db_b = RKDatabase::from_kmer_pairs(b, K as u8, false, true)?;
    let path_a = dir.path().join("over_budget_a.rkdb");
    let path_b = dir.path().join("over_budget_b.rkdb");
    db_a.to_file_path(&path_a)?;
    db_b.to_file_path(&path_b)?;

    // The expected union, computed from the inputs rather than from the merge
    // output — so a merge bug cannot define its own expectation.
    let mut expected: HashMap<u128, u32> = HashMap::new();
    for (kmer, count) in db_a.all_kmers()? {
        *expected.entry(kmer).or_insert(0) += count;
    }
    for (kmer, count) in db_b.all_kmers()? {
        *expected.entry(kmer).or_insert(0) += count;
    }

    // MERGE-02 hard route: `auto` with a budget derived to be strictly under
    // the estimate for THESE inputs, then proved to have streamed. 5 tiny
    // k-mers estimate to ~240 bytes, so the hard-coded `1024` an earlier draft
    // used would have stayed under budget and silently taken the in-memory
    // path — this is the assertion that makes "over-budget" a fact rather than
    // a hope.
    let inputs = vec![path_a.clone(), path_b.clone()];
    let streaming = over_budget_config(dir.path(), &inputs)?;
    assert_route(
        "bounded over-budget merge",
        &inputs,
        &streaming,
        Route::Streaming,
    );
    let merged = RKDatabase::merge_databases(&[path_a.clone(), path_b.clone()], &streaming)
        .map_err(|e| {
            anyhow::anyhow!("over-budget auto merge must complete via streaming: {}", e)
        })?;
    let actual: HashMap<u128, u32> = merged.all_kmers()?.into_iter().collect();

    // Exact k-mer COUNT equality — not "non-empty".
    assert_eq!(
        actual.len(),
        expected.len(),
        "over-budget streaming merge must return the exact union of both inputs \
         (expected {} distinct k-mers, got {})",
        expected.len(),
        actual.len()
    );
    for (kmer, count) in &expected {
        assert_eq!(
            actual.get(kmer),
            Some(count),
            "k-mer {:#x} must survive the streaming merge with its summed count {} (got {:?})",
            kmer,
            count,
            actual.get(kmer)
        );
    }

    // Header accounting — the invariant a silent partial merge would break.
    assert_eq!(
        merged.header.total_kmers,
        actual.len() as u64,
        "merged header total_kmers must equal the number of records present"
    );
    assert_eq!(
        merged.header.data_offset, RKDB_V2_HEADER_SIZE,
        "merged output must be .rkdb v2"
    );
    let summed: u64 = actual.values().map(|c| *c as u64).sum();
    let expected_sum: u64 = expected.values().map(|c| *c as u64).sum();
    assert_eq!(
        summed, expected_sum,
        "merged counts must sum to the total of the input counts"
    );

    // The two permitted routes must be interchangeable — that equivalence is
    // exactly what makes MERGE-02's hard route safe to promote to default.
    let in_memory = merge_config(dir.path(), HUGE_BUDGET_BYTES, "auto");
    assert_route(
        "within-budget control",
        &inputs,
        &in_memory,
        Route::InMemory,
    );
    let merged_in_memory = RKDatabase::merge_databases(&[path_a, path_b], &in_memory)
        .map_err(|e| anyhow::anyhow!("within-budget in-memory merge must complete: {}", e))?;
    let actual_in_memory: HashMap<u128, u32> = merged_in_memory.all_kmers()?.into_iter().collect();
    assert_eq!(
        actual_in_memory, actual,
        "the streaming route and the in-memory route must return identical data — the \
         hard route is only safe because they are interchangeable"
    );

    Ok(())
}
