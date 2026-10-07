//! DENSE-03 (plan 03-03) — property-based dense differential.
//!
//! The fixed-input differential in `tests/dense_differential_tests.rs` proves
//! the `u64` and `u128` storage paths agree on the 12-cell D-13 matrix. That is
//! necessary but bounded: a fixed 360-base fixture exercises one shape of
//! k-mer distribution (deliberately repetitive, so many counts exceed 1). A
//! packing or canonicalization bug can hide in the input distribution it never
//! saw — homopolymer runs, windows that straddle sequence boundaries,
//! reverse-complement pairs, palindromes, k-mers at the exact width boundary.
//!
//! This binary closes that gap the same way Phase 2's `1`-vs-`N` differential
//! closed the ordering axis: generate the input, prove the two widths agree.
//! **D-05** — counting is integer addition, so a divergence is a bug, full stop.
//!
//! **D-04** applies here too and is the reason the assertion is written the way
//! it is: the `u64` and `u128` encoder families are decoded with their matching
//! decoders and compared as `HashMap<String, u32>`. No raw integer is ever
//! compared across widths.
//!
//! `mod common;` is deliberately omitted — proptest supplies the randomness and
//! the differential needs none of the `tests/common/` factories (same reasoning
//! as `tests/parallel_count_tests.rs`).

use proptest::prelude::*;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::{canonical_kmer, canonical_kmer_u128};
use rustkmer::kmer::encoding::{
    decode_kmer, decode_kmer_u128, encode_kmer_bytes, encode_kmer_bytes_u128,
};
use std::collections::HashMap;

/// k values that all sit on the **dense** side of the width boundary
/// (`k <= MAX_KMER_SIZE_IN_U64` = 32), so every generated k-mer exercises
/// `KmerKey::U64` storage. 15/21/31 span small, the common default, and the
/// largest dense width; k=32 is covered exhaustively by
/// `tests/dense_differential_tests.rs`.
const DENSE_K: &[usize] = &[15, 21, 31];

/// A DNA string over the alphabet the encoders accept, long enough that a
/// handful of k-mer windows exist for every k in `DENSE_K`.
fn dna_string() -> impl Strategy<Value = String> {
    proptest::collection::vec(
        prop::sample::select(vec![b'A', b'C', b'G', b'T']),
        1usize..=400,
    )
    .prop_map(|bases| String::from_utf8(bases).expect("ASCII alphabet is valid UTF-8"))
}

/// Count `input` through `KmerCounter` using the `u64` encoder family (dense
/// path), decoded back to a string-keyed map.
fn dense_map(k: usize, canonical: bool, input: &str) -> HashMap<String, u32> {
    let counter = KmerCounter::new(k, canonical, 256, 1).expect("k in 1..=64");
    let bytes = input.as_bytes();
    if bytes.len() < k {
        return HashMap::new();
    }
    for window in bytes.windows(k) {
        let encoded = encode_kmer_bytes(window).expect("ACGT alphabet and k <= 31");
        let kmer = if canonical {
            canonical_kmer(encoded, k).expect("reverse_complement_bits accepts k <= 32")
        } else {
            encoded
        };
        counter
            .increment(kmer as u128)
            .expect("u32::MAX overflow needs 4 billion identical increments");
    }
    counter
        .get_all_counts()
        .into_iter()
        .map(|(encoded, count)| (decode_kmer(encoded as u64, k), count))
        .collect()
}

/// Count `input` through `KmerCounter` using the `u128` encoder family (the
/// unchanged path; for k <= 31 the counter still stores `KmerKey::U64` keys),
/// decoded back to a string-keyed map with the matching decoder.
fn wide_encoded_map(k: usize, canonical: bool, input: &str) -> HashMap<String, u32> {
    let counter = KmerCounter::new(k, canonical, 256, 1).expect("k in 1..=64");
    let bytes = input.as_bytes();
    if bytes.len() < k {
        return HashMap::new();
    }
    for window in bytes.windows(k) {
        let encoded = encode_kmer_bytes_u128(window).expect("ACGT alphabet and k <= 31");
        let kmer = if canonical {
            canonical_kmer_u128(encoded, k).expect("reverse_complement_u128 accepts k <= 64")
        } else {
            encoded
        };
        counter
            .increment(kmer)
            .expect("u32::MAX overflow needs 4 billion identical increments");
    }
    counter
        .get_all_counts()
        .into_iter()
        .map(|(encoded, count)| (decode_kmer_u128(encoded, k), count))
        .collect()
}

/// The `u128` reference pipeline with **no `KmerCounter` involved** — an
/// independent oracle, so a failure localizes to the counter rather than to a
/// bug shared by both counter pipelines.
fn u128_reference_map(k: usize, canonical: bool, input: &str) -> HashMap<String, u32> {
    let mut acc: std::collections::BTreeMap<u128, u32> = std::collections::BTreeMap::new();
    let bytes = input.as_bytes();
    if bytes.len() < k {
        return HashMap::new();
    }
    for window in bytes.windows(k) {
        let encoded = encode_kmer_bytes_u128(window).expect("ACGT alphabet and k <= 31");
        let kmer = if canonical {
            canonical_kmer_u128(encoded, k).expect("reverse_complement_u128 accepts k <= 64")
        } else {
            encoded
        };
        *acc.entry(kmer).or_insert(0) += 1;
    }
    acc.into_iter()
        .map(|(encoded, count)| (decode_kmer_u128(encoded, k), count))
        .collect()
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(256))]

    /// DENSE-03 / D-04 / D-05 on random DNA: the `u64`-encoder and
    /// `u128`-encoder pipelines must produce identical decoded `(String, u32)`
    /// maps, and both must agree with the counter-free `u128` oracle.
    #[test]
    #[ignore = "TODO(03-03 Task 2): un-ignore once the KmerKey swap lands"]
    fn dense_u64_matches_u128_on_random_dna(
        input in dna_string(),
        k_idx in 0usize..DENSE_K.len(),
        canonical in prop::bool::ANY,
    ) {
        let k = DENSE_K[k_idx];
        let dense = dense_map(k, canonical, &input);
        let wide = wide_encoded_map(k, canonical, &input);
        let reference = u128_reference_map(k, canonical, &input);

        prop_assert_eq!(
            &dense,
            &wide,
            "DENSE-03: u64-encoder and u128-encoder pipelines diverged at k={} canonical={} \
             on input of length {}",
            k, canonical, input.len()
        );
        prop_assert_eq!(
            &dense,
            &reference,
            "DENSE-03: the dense counter diverged from the counter-free u128 oracle at \
             k={} canonical={} on input of length {}",
            k, canonical, input.len()
        );
    }

    /// Every k-mer window fed in must be counted exactly once. This is the
    /// "counts sum to the input" invariant that survives even a hypothetical
    /// collision-pair bug which happened to keep the maps equal.
    #[test]
    #[ignore = "TODO(03-03 Task 2): un-ignore once the KmerKey swap lands"]
    fn dense_counts_sum_to_kmer_windows(
        input in dna_string(),
        k_idx in 0usize..DENSE_K.len(),
        canonical in prop::bool::ANY,
    ) {
        let k = DENSE_K[k_idx];
        let expected_total: usize = if input.len() < k {
            0
        } else {
            input.len() - k + 1
        };
        let total: u64 = dense_map(k, canonical, &input)
            .values()
            .map(|c| *c as u64)
            .sum();
        prop_assert_eq!(
            total as usize,
            expected_total,
            "counts must sum to the number of k-mer windows fed in (k={} canonical={})",
            k, canonical
        );
    }

    /// `get_count` (a point lookup) must agree with the aggregated map, and
    /// `get_all_counts` must not lose or duplicate entries on the way out of
    /// the `KmerKey` → `u128` widening.
    #[test]
    #[ignore = "TODO(03-03 Task 2): un-ignore once the KmerKey swap lands"]
    fn dense_point_lookup_matches_aggregated_map(
        input in dna_string(),
        k_idx in 0usize..DENSE_K.len(),
        canonical in prop::bool::ANY,
    ) {
        let k = DENSE_K[k_idx];
        let bytes = input.as_bytes();
        if bytes.len() < k {
            return Ok(());
        }
        let counter = KmerCounter::new(k, canonical, 256, 1).expect("k in 1..=64");
        let mut first_kmer: Option<u64> = None;
        for window in bytes.windows(k) {
            let encoded = encode_kmer_bytes(window).expect("ACGT alphabet and k <= 31");
            let kmer = if canonical {
                canonical_kmer(encoded, k).expect("reverse_complement_bits accepts k <= 32")
            } else {
                encoded
            };
            first_kmer.get_or_insert(kmer);
            counter.increment(kmer as u128).expect("no overflow in 256 cases");
        }

        let aggregated: HashMap<String, u32> = counter
            .get_all_counts()
            .into_iter()
            .map(|(encoded, count)| (decode_kmer(encoded as u64, k), count))
            .collect();

        let first = first_kmer.expect("input has at least one window");
        let string = decode_kmer(first, k);
        prop_assert_eq!(
            counter.get_count(first as u128),
            aggregated.get(&string).copied(),
            "get_count must agree with the aggregated decoded map (k={} canonical={})",
            k, canonical
        );
        // The same k-mer looked up twice must return the same count — the
        // `entry().and_modify().or_insert_with()` chain must not duplicate keys.
        prop_assert_eq!(
            aggregated.len(),
            counter.get_all_counts().len(),
            "get_all_counts must not duplicate entries (k={} canonical={})",
            k, canonical
        );
    }
}
