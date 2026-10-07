//! Width-selected k-mer counter key (Phase 3, plan 03-03).
//!
//! Implements **DENSE-01** ("k ≤ 32 stored as `u64` (8 bytes) instead of
//! `u128` — roughly half the counting memory for the common case") as a
//! width-selected key enum for `KmerCounter`'s `DashMap`. Implements
//! **RESEARCH Pattern 1** ("PackedKmer Width-Selection — Option A, enum key"),
//! which was chosen over a parallel `KmerCounterU64` type or a generic-over-width
//! counter because those two duplicate ~400 LOC of impl surface or push a `T`
//! bound into `KmerCounterBuilder` / `CounterStats` / the PyO3 `#[pyclass]`
//! (blast-radius analysis, 03-RESEARCH.md §Pattern 1).
//!
//! **D-03 (RAM-only).** This type is *internal storage only*. The `.rkdb` v2
//! on-disk format is untouched: `KmerEntry` remains a 16-byte little-endian
//! `u128` + 4-byte little-endian `u32` (20 B/record), and the write path
//! widens `KmerKey::U64(v)` back to `v as u128` via [`KmerKey::to_u128`]
//! (zero-extension). Readers therefore see byte-identical v2 files — which is
//! what makes **DENSE-02** ("transparent to existing readers") hold.
//!
//! **Phase 2 D-05 carry-forward.** No public counter signature changes: the
//! enum appears *inside* `src/hash/`, and `KmerCounter`'s
//! `new`/`increment`/`get_count`/`get_all_counts`/`merge` keep their
//! `u128`-typed external surface. Conversion happens at the boundary in both
//! directions — [`KmerKey::from_u128`] on the way in, [`KmerKey::to_u128`] on
//! the way out.

use crate::kmer::encoding::MAX_KMER_SIZE_IN_U64;

/// Width-selected key for [`crate::hash::KmerCounter`]'s `DashMap` (DENSE-01).
///
/// Within a single counter exactly one variant is ever populated — the width is
/// fixed at `KmerCounter::new` from `kmer_length` — so the discriminant never
/// adds live storage cost. The derived `Hash`/`Eq` discriminate by variant
/// before by inner value, which is what lets `DashMap<KmerKey, u32>` (and
/// therefore the `entry().and_modify(..).or_insert_with(..)` atomicity chain,
/// RESEARCH Pattern 1 / PCOUNT-04) work unchanged.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KmerKey {
    /// **Dense width** — `kmer_length <= MAX_KMER_SIZE_IN_U64` (i.e. k ≤ 32).
    ///
    /// The 8-byte form that halves keyed storage for the common case
    /// (DENSE-01). Values here are produced by `encode_kmer_bytes_u128` /
    /// `encode_kmer_bytes` for k ≤ 32, both of which leave the upper 64 bits
    /// zero, so `to_u128()` is a lossless zero-extension.
    U64(u64),
    /// **Wide width** — `33 <= kmer_length <= MAX_KMER_SIZE_IN_U128` (k ≤ 64).
    ///
    /// The pre-Phase-3 layout, unchanged. k-mer integers for k > 32 genuinely
    /// occupy the full 128 bits, so there is nothing to shrink.
    U128(u128),
}

impl KmerKey {
    /// Select the storage width for `kmer_length` and pack `value` into it.
    ///
    /// The width boundary is [`MAX_KMER_SIZE_IN_U64`] (32): k ≤ 32 → [`KmerKey::U64`],
    /// 33..=64 → [`KmerKey::U128`]. This is the single point where the
    /// `u128 -> u64` narrowing happens (threat **T-03-09**, Tampering).
    ///
    /// # Narrowing contract
    ///
    /// On the [`KmerKey::U64`] path the caller **must** have produced `value`
    /// from a k ≤ 32 k-mer, whose encoding is `< 2^64` by construction. That
    /// invariant is asserted here with `debug_assert!` (active in `cargo test`
    /// and debug builds, compiled out of release — zero runtime cost, per the
    /// plan's D-03 zero-extension discipline). In release the assertion is
    /// elided and the narrowing is trusted; every production caller
    /// (`src/cli/commands/count.rs`, `pyo3/src/counter.rs`) encodes via
    /// `encode_kmer_bytes_u128`, which returns `< 2^(2*k) <= 2^64` for k ≤ 32,
    /// so the invariant holds by construction rather than by input filtering.
    ///
    /// A violating value would silently alias a distinct k-mer onto an existing
    /// key and merge two counts — the exact DENSE-03 failure mode the decoded
    /// differential in `tests/dense_differential_tests.rs` exists to catch.
    pub fn from_u128(value: u128, kmer_length: usize) -> Self {
        if kmer_length <= MAX_KMER_SIZE_IN_U64 {
            debug_assert!(
                value <= u64::MAX as u128,
                "u64 storage width selected for kmer_length {} but the encoded value \
                 has bits set above bit 64 — narrowing would alias two distinct \
                 k-mers onto one key",
                kmer_length
            );
            KmerKey::U64(value as u64)
        } else {
            KmerKey::U128(value)
        }
    }

    /// Widen back to the public `u128` representation.
    ///
    /// [`KmerKey::U64`] zero-extends (`v as u128`); [`KmerKey::U128`] returns
    /// the value unchanged. This is the inverse of [`KmerKey::from_u128`] on
    /// any value that satisfies the narrowing contract above, and it is what
    /// keeps `get_all_counts() -> Vec<(u128, u32)>` and the `.rkdb` write path
    /// (D-03 / DENSE-02) byte-identical to the pre-Phase-3 counter.
    pub fn to_u128(&self) -> u128 {
        match self {
            KmerKey::U64(v) => *v as u128,
            KmerKey::U128(v) => *v,
        }
    }
}
