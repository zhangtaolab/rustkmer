//! DENSE-03 (plan 03-03) — the sharp correctness tool: a `u64`-storage
//! counter versus a `u128`-storage counter on identical input.
//!
//! **D-05: the `u128`-vs-`u64` differential is the correctness proof for this
//! plan.** k-mer counting is integer addition — commutative and associative —
//! so any count divergence between the two storage widths on the same input is
//! a packing or canonicalization bug, not an ordering artifact. That is exactly
//! the DENSE-03 failure mode ("canonicalization stays correct under `u64`
//! packing"), and it is the Phase 2 `1`-vs-`N` thread differential (PCOUNT-04)
//! transplanted onto the width axis.
//!
//! **D-04: compare at the DECODED `(kmer_string, count)` level, never at the
//! raw-integer level.** The two encoder families are *not* guaranteed to produce
//! the same integer for the same biological k-mer — `encode_kmer_bytes` (u64)
//! and `encode_kmer_bytes_u128` (u128) each apply their own alignment, and
//! `decode_kmer` / `decode_kmer_u128` are only the respective inverses. An
//! `assert_eq!(u64_int, u128_int)` would therefore be asserting an incidental
//! implementation detail, and would fail (or, worse, pass for the wrong reason)
//! the moment either encoder's alignment changes. Every assertion in this file
//! decodes to k-mer strings first.
//!
//! Three independent references are used, so a divergence localizes:
//!
//! | Reference | What it is | Catches |
//! |---|---|---|
//! | `u128_reference_map` | pure `u128` encode → canonical → `BTreeMap` accumulator, **no `KmerCounter` involved** | counter-internal key collisions / lost counts |
//! | `u128_encoded_counter` | `KmerCounter` fed by the `u128` encoder (what production `count.rs` / `pyo3` do) | the D-13 reference pipeline |
//! | `u64_encoded_counter` | `KmerCounter` fed by the `u64` encoder (the dense path proper) | packing + canonicalization under `u64` |
//! | `golden_decoded_map` | the committed Phase 1/2 `.rkdb` fixtures (D-10 ground truth) | drift from the pre-refactor baseline |
//!
//! **D-13 coverage matrix carry-forward:** `k ∈ {21, 32, 64}` × canonical.
//! k=21 and k=32 select the `KmerKey::U64` storage width (DENSE-01); k=64
//! selects `KmerKey::U128` and is the *regression guard* proving the
//! pre-existing path is untouched.
//!
//! Test bodies use `anyhow::Result<()>` + `?` per the project's TESTING.md
//! convention (same as `tests/golden_tests.rs`).
//!
//! `mod common;` is deliberately omitted — the differential compares decoded
//! maps directly and needs none of the `RKDatabase` factories in
//! `tests/common/`. Same reasoning as `tests/parallel_count_tests.rs`.

use anyhow::Result;
use rustkmer::database::format::RKDatabase;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::{canonical_kmer, canonical_kmer_u128};
use rustkmer::kmer::encoding::{
    decode_kmer, decode_kmer_u128, encode_kmer_bytes, encode_kmer_bytes_u128,
};
use std::collections::{BTreeMap, HashMap};

/// Fixed, deterministic DNA input — MUST match
/// `tests/golden_generate.rs::GOLDEN_INPUT` character for character, otherwise
/// the k-mer sets differ and the golden-fixture comparison is meaningless.
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// Modelled hash/shard overhead per entry. Shared by both widths — it is not
/// part of the key/value payload this plan narrows, which is why DENSE-01's
/// "roughly half" is measured on the payload rather than the total.
const HASH_OVERHEAD_PER_ENTRY: usize = 24;
/// Modelled per-entry cost for the dense (`KmerKey::U64`) width: 24 + 8 + 4.
/// Mirrors `src/hash/table.rs::KmerCounter::memory_usage`.
const DENSE_BYTES_PER_ENTRY: usize = HASH_OVERHEAD_PER_ENTRY + 8 + 4;
/// Same, for the wide (`KmerKey::U128`) width: 24 + 16 + 4.
const WIDE_BYTES_PER_ENTRY: usize = HASH_OVERHEAD_PER_ENTRY + 16 + 4;

/// Which encoder family produced the integers in a count map.
///
/// Selects the *matching* decoder — the only correct pairing, because
/// `decode_kmer` inverts `encode_kmer_bytes` and `decode_kmer_u128` inverts
/// `encode_kmer_bytes_u128`. Decoding a `u128`-encoded integer with the `u64`
/// decoder is exactly the mistake D-04 forbids.
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
}

/// DENSE-03 helper (03-RESEARCH §Pattern 4): decode a counter's counts into a
/// `HashMap<String, u32>` keyed by **k-mer string**, never by raw integer.
///
/// `width` must describe how the counter was *populated*, not what width the
/// counter internally chose — the caller knows the encoder it used.
fn counter_to_decoded_map(counter: &KmerCounter, k: usize, width: Width) -> HashMap<String, u32> {
    decoded_map_from_pairs(&counter.get_all_counts(), k, width)
}

/// Decode `(encoded, count)` pairs into a string-keyed map (DENSE-03 / D-04).
fn decoded_map_from_pairs(pairs: &[(u128, u32)], k: usize, width: Width) -> HashMap<String, u32> {
    pairs
        .iter()
        .map(|(encoded, count)| (width.decode(*encoded, k), *count))
        .collect()
}

/// The `u128` reference pipeline: encode → canonicalize → accumulate into a
/// plain `BTreeMap`, deliberately **not** going through `KmerCounter`.
///
/// This is the independent oracle. If `KmerCounter` disagreed with it, the bug
/// is inside the counter's key handling rather than in the shared encoders.
fn u128_reference_map(k: usize, canonical: bool) -> Result<HashMap<String, u32>> {
    let mut acc: BTreeMap<u128, u32> = BTreeMap::new();
    for seq in GOLDEN_INPUT {
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let encoded = encode_kmer_bytes_u128(window)?;
            let kmer = if canonical {
                canonical_kmer_u128(encoded, k)?
            } else {
                encoded
            };
            *acc.entry(kmer).or_insert(0) += 1;
        }
    }
    Ok(decoded_map_from_pairs(
        &acc.into_iter().collect::<Vec<_>>(),
        k,
        Width::U128,
    ))
}

/// Feed `GOLDEN_INPUT` through a `KmerCounter` using the **`u128` encoder
/// family** — byte-for-byte the loop production runs in
/// `src/cli/commands/count.rs` and `pyo3/src/counter.rs`.
///
/// For k ≤ 32 this counter stores `KmerKey::U64` keys (the dense width); the
/// integers it is fed already fit in 64 bits because `encode_kmer_bytes_u128`
/// is called on a k ≤ 32 window.
fn u128_encoded_counter(k: usize, canonical: bool) -> Result<KmerCounter> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
    for seq in GOLDEN_INPUT {
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let encoded = encode_kmer_bytes_u128(window)?;
            let kmer = if canonical {
                canonical_kmer_u128(encoded, k)?
            } else {
                encoded
            };
            counter.increment(kmer)?;
        }
    }
    Ok(counter)
}

/// Feed `GOLDEN_INPUT` through a `KmerCounter` using the **`u64` encoder
/// family** — the dense path proper, and the one DENSE-03 is about.
///
/// Only valid for k ≤ 32 (`encode_kmer_bytes` rejects longer windows); the
/// stored keys are `KmerKey::U64` because `k <= MAX_KMER_SIZE_IN_U64`.
fn u64_encoded_counter(k: usize, canonical: bool) -> Result<KmerCounter> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
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
            // `kmer` is a `u64`; the widening is the public API contract and the
            // counter narrows it straight back to `KmerKey::U64`.
            counter.increment(kmer as u128)?;
        }
    }
    Ok(counter)
}

/// Load a committed Phase 1/2 golden `.rkdb` fixture and decode it to a
/// string-keyed count map. D-10 carry-forward: these are the pre-refactor
/// `u128`-path baselines, used as ground truth, never regenerated.
fn golden_decoded_map(k: usize, canonical: bool) -> Result<HashMap<String, u32>> {
    let mode = if canonical { "canon" } else { "noncanon" };
    let name = format!("golden_k{}_{}_sorted.rkdb", k, mode);
    let path = format!("tests/fixtures/{}", name);
    let db = RKDatabase::from_file_path(std::path::Path::new(&path))?;
    let pairs = db.all_kmers()?;
    Ok(decoded_map_from_pairs(&pairs, k, Width::U128))
}

fn canon_label(canonical: bool) -> &'static str {
    if canonical {
        "canon"
    } else {
        "noncanon"
    }
}

/// The full DENSE-03 assertion set for one (k, canonical) cell where k ≤ 32, so
/// both storage widths are live.
///
/// Every comparison is between **decoded** maps (D-04).
fn assert_dense_cell_matches(k: usize, canonical: bool) -> Result<()> {
    let label = format!("k={} {}", k, canon_label(canonical));

    // --- 0. The counter really is on the dense width ----------------------------
    // `memory_usage()` is derived from the stored key width, so this is a
    // direct observation of which `KmerKey` variant the counter selected at
    // `new()`. Without it, a regression to the u128 key would still pass every
    // decoded-map assertion below while silently un-doing DENSE-01.
    let dense_counter = u64_encoded_counter(k, canonical)?;
    let n = dense_counter.get_all_counts().len();
    assert!(
        n > 0,
        "{}: fixture input produced no k-mers — differential would be vacuous",
        label
    );
    assert_eq!(
        dense_counter.memory_usage(),
        n * DENSE_BYTES_PER_ENTRY,
        "{}: k <= 32 must select the KmerKey::U64 storage width (DENSE-01), \
         i.e. {} bytes/entry",
        label,
        DENSE_BYTES_PER_ENTRY
    );

    let u128_counter = u128_encoded_counter(k, canonical)?;
    assert_eq!(
        u128_counter.memory_usage(),
        n * DENSE_BYTES_PER_ENTRY,
        "{}: the production (u128-encoder) path must also land in the dense \
         KmerKey::U64 width for k <= 32 (DENSE-01)",
        label
    );

    // --- 1. counter internals vs the independent u128 oracle -------------------
    let reference = u128_reference_map(k, canonical)?;
    let dense_map = counter_to_decoded_map(&dense_counter, k, Width::U64);
    let dense_via_u128_encoder = counter_to_decoded_map(&u128_counter, k, Width::U128);

    assert_eq!(
        dense_map.len(),
        reference.len(),
        "{}: u64-path unique-k-mer count differs from the u128 reference",
        label
    );
    assert_eq!(
        dense_map, reference,
        "{}: u64 path decoded map must equal the u128 reference decoded map (DENSE-03)",
        label
    );
    assert_eq!(
        dense_via_u128_encoder, reference,
        "{}: KmerCounter fed by the u128 encoder must equal the u128 reference (DENSE-03)",
        label
    );

    // --- 2. THE differential: u64 path vs u128 path ----------------------------
    assert_eq!(
        dense_map, dense_via_u128_encoder,
        "{}: u64-storage and u128-encoder pipelines must produce identical \
         decoded (String, u32) maps (DENSE-03 / D-04 / D-05)",
        label
    );

    // --- 3. aggregate sanity: every k-mer window is accounted for -------------
    let total: u64 = dense_map.values().map(|c| *c as u64).sum();
    let expected_total: u64 = GOLDEN_INPUT
        .iter()
        .filter(|s| s.len() >= k)
        .map(|s| (s.len() - k + 1) as u64)
        .sum();
    assert_eq!(
        total, expected_total,
        "{}: counts must sum to the number of k-mer windows fed in — a lost or \
         double-counted k-mer shows up here even if the maps happened to match",
        label
    );
    assert_eq!(
        dense_counter.total_kmers(),
        expected_total,
        "{}: total_kmers atomic must match the number of windows",
        label
    );
    assert_eq!(
        dense_counter.unique_kmers(),
        n as u64,
        "{}: unique_kmers atomic must match the number of map entries",
        label
    );

    // --- 4. Phase 1/2 golden ground truth (D-10) -------------------------------
    let golden = golden_decoded_map(k, canonical)?;
    assert_eq!(
        dense_via_u128_encoder, golden,
        "{}: the dense counter's decoded output must equal the committed Phase 1/2 \
         golden .rkdb baseline (D-10 carry-forward / DENSE-03)",
        label
    );

    Ok(())
}

/// The regression guard for the wide width: k=64 has no dense path (k > 32), so
/// these cells prove the `KmerKey::U128` variant is byte-for-byte the old
/// behavior. A bug here would mean the swap regressed the pre-existing path.
fn assert_wide_cell_unchanged(k: usize, canonical: bool) -> Result<()> {
    let label = format!("k={} {}", k, canon_label(canonical));

    let counter = u128_encoded_counter(k, canonical)?;
    let n = counter.get_all_counts().len();
    assert!(n > 0, "{}: fixture input produced no k-mers", label);
    assert_eq!(
        counter.memory_usage(),
        n * WIDE_BYTES_PER_ENTRY,
        "{}: k > 32 must select the KmerKey::U128 storage width, i.e. {} bytes/entry",
        label,
        WIDE_BYTES_PER_ENTRY
    );

    // The u64 encoder genuinely cannot represent a 64-mer — this is what makes
    // k=64 the regression guard rather than a second dense case.
    assert!(
        encode_kmer_bytes(&GOLDEN_INPUT[0].as_bytes()[..k]).is_err(),
        "{}: encode_kmer_bytes must reject a {}-mer (MAX_KMER_SIZE_IN_U64 = 32), \
         otherwise k=64 is not exercising a distinct width",
        label,
        k
    );

    let wide_map = counter_to_decoded_map(&counter, k, Width::U128);
    let reference = u128_reference_map(k, canonical)?;
    assert_eq!(
        wide_map, reference,
        "{}: the u128-storage path must be unchanged by the KmerKey swap (DENSE-03)",
        label
    );

    let golden = golden_decoded_map(k, canonical)?;
    assert_eq!(
        wide_map, golden,
        "{}: the u128-storage path must still match the committed Phase 1/2 golden \
         baseline (D-10 carry-forward)",
        label
    );

    Ok(())
}

// --- D-13 matrix: the u64 cells (dense path) ---

#[test]
fn dense_u64_matches_u128_k21_canon() -> Result<()> {
    assert_dense_cell_matches(21, true)
}

#[test]
fn dense_u64_matches_u128_k21_noncanon() -> Result<()> {
    assert_dense_cell_matches(21, false)
}

#[test]
fn dense_u64_matches_u128_k32_canon() -> Result<()> {
    assert_dense_cell_matches(32, true)
}

#[test]
fn dense_u64_matches_u128_k32_noncanon() -> Result<()> {
    assert_dense_cell_matches(32, false)
}

// --- D-13 matrix: the u128 cells (regression guard) ---

#[test]
fn dense_u128_unchanged_k64_canon() -> Result<()> {
    assert_wide_cell_unchanged(64, true)
}

#[test]
fn dense_u128_unchanged_k64_noncanon() -> Result<()> {
    assert_wide_cell_unchanged(64, false)
}
