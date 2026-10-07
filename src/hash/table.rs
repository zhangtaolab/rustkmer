//! Concurrent hash table for k-mer counting
//!
//! Provides a thread-safe hash table implementation optimized for k-mer counting
//! with minimal contention and efficient memory usage.

use dashmap::DashMap;

use super::filtering::{CountFilter, FilteringResult};
use crate::error::{KmerError, ProcessingError, ProcessingResult};
use crate::hash::key::KmerKey;
use crate::kmer::encoding::MAX_KMER_SIZE_IN_U64;

/// Modelled per-entry hash/shard overhead in [`KmerCounter::memory_usage`].
///
/// Unchanged by the DENSE-01 key narrowing: it is a property of the sharded hash
/// table, not of the key it stores, so it does not halve with the key.
const HASH_OVERHEAD_PER_ENTRY: usize = 24;

/// Modelled width of the dense `KmerKey::U64` storage key (DENSE-01).
const U64_KEY_BYTES: usize = 8;
/// Modelled width of the `KmerKey::U128` storage key.
const U128_KEY_BYTES: usize = 16;
/// Modelled width of the `u32` count value stored alongside every key.
const COUNT_BYTES: usize = 4;

/// Thread-safe k-mer counter with concurrent operations
#[derive(Debug)]
pub struct KmerCounter {
    /// Core hash table storing k-mer counts.
    ///
    /// Backed by `dashmap::DashMap` (Phase 2, PCOUNT-02): internally sharded
    /// (~4×num_cpus per-shard `RwLock`s), so increments spread across shards
    /// and throughput scales with core count without a single global lock.
    /// The `entry().and_modify().or_insert_with()` chain holds only the
    /// relevant shard lock for its lifetime → atomic per-key (RESEARCH
    /// Pattern 1), preserving the u32::MAX overflow semantics verbatim.
    ///
    /// **DENSE-01 (Phase 3, plan 03-03): the key is width-selected, not a bare
    /// `u128`.** For `kmer_length <= MAX_KMER_SIZE_IN_U64` (32) — the common
    /// case — keys are stored as `KmerKey::U64`, halving the per-k-mer keyed
    /// storage. For 33..=64 they stay `KmerKey::U128`, unchanged. The width is
    /// fixed for the counter's lifetime (chosen in `new`), so exactly one
    /// variant is ever populated and the discriminant costs nothing.
    ///
    /// **D-03: this is RAM-only.** No public signature changed (Phase 2 D-05
    /// carry-forward) — `increment`/`get_count` still take `u128` and
    /// `get_all_counts` still returns `Vec<(u128, u32)>`, converting through
    /// [`KmerKey::from_u128`] / [`KmerKey::to_u128`] at the boundary. The
    /// `.rkdb` v2 write path therefore sees the same 16-byte-u128 values it
    /// always did (DENSE-02 byte-identity).
    table: DashMap<KmerKey, u32>,
    /// Total k-mers successfully counted (excludes per-k-mer overflow
    /// attempts that return `Err` from `increment`). See WR-03.
    total_kmers: std::sync::atomic::AtomicU64,
    /// Number of unique k-mers
    unique_kmers: std::sync::atomic::AtomicU64,
    /// K-mer length for this counting session
    kmer_length: usize,
    /// Whether canonical mode is enabled
    canonical_mode: bool,
    /// Maximum count value (for overflow protection)
    max_count: u32,
}

impl KmerCounter {
    /// Create a new k-mer counter
    ///
    /// # Arguments
    /// * `kmer_length` - Length of k-mers to count
    /// * `canonical_mode` - Whether to count canonical k-mers
    /// * `initial_capacity` - Initial hash table capacity
    /// * `_num_threads` - Currently unused; thread-pool sizing is performed by
    ///   the caller via `rayon::ThreadPoolBuilder::build_global` (see
    ///   `execute_count` / `PyCounter::new`). Retained for API stability.
    ///
    /// # Returns
    /// New KmerCounter instance
    ///
    /// # Storage width (DENSE-01)
    /// `kmer_length <= MAX_KMER_SIZE_IN_U64` (32) selects the dense
    /// `KmerKey::U64` storage width; 33..=64 keeps `KmerKey::U128`. The width
    /// is derived from `kmer_length` on demand rather than cached in a
    /// `use_u64` field — `kmer_length` is immutable for the counter's lifetime,
    /// so a cached flag could only ever be redundant state capable of drifting
    /// out of agreement with the length it was derived from.
    pub fn new(
        kmer_length: usize,
        canonical_mode: bool,
        initial_capacity: usize,
        _num_threads: usize,
    ) -> ProcessingResult<Self> {
        if !(1..=64).contains(&kmer_length) {
            return Err(KmerError::InvalidKmerSize(kmer_length as u32).into());
        }

        Ok(Self {
            table: DashMap::<KmerKey, u32>::with_capacity(initial_capacity),
            total_kmers: std::sync::atomic::AtomicU64::new(0),
            unique_kmers: std::sync::atomic::AtomicU64::new(0),
            kmer_length,
            canonical_mode,
            max_count: u32::MAX,
        })
    }

    /// Increment the count for a k-mer
    ///
    /// # Arguments
    /// * `kmer_encoded` - Packed k-mer representation (u128 for k≤64)
    ///
    /// # Returns
    /// Result indicating success or error
    pub fn increment(&self, kmer_encoded: u128) -> ProcessingResult<()> {
        // CRITICAL (RESEARCH Pattern 1 / Pitfalls 1, 2, 6):
        // The `entry().and_modify(..).or_insert_with(..)` chain holds the
        // shard lock for the entry's whole lifetime, so the overflow check +
        // increment is ATOMIC per-key — no lost update, no double count under
        // concurrency (PCOUNT-04 invariant). Do NOT split this into
        // `get()` + `insert()` — that both loses atomicity (TOCTOU window →
        // lost updates) AND risks deadlock (dashmap docs.rs: "May deadlock if
        // called when holding any sort of reference into the map").
        //
        // `and_modify` takes `FnOnce(&mut V) -> ()` and CANNOT return a
        // `Result` (Pitfall 6). The flag-then-check pattern works around the
        // signature: mutate a local `overflow` flag inside the closure, then
        // inspect it AFTER the entry chain completes (the shard lock has been
        // released by then, so the early-return is safe). The overflow
        // message is preserved VERBATIM from the pre-refactor path
        // (table.rs:76-79) — PCOUNT-04 depends on byte-identical behavior.
        //
        // DENSE-01 (Phase 3): the key is narrowed to the storage width chosen
        // at `new()`. On the U64 path this is a `u128 as u64` truncation, which
        // is safe only because every production caller encodes through
        // `encode_kmer_bytes_u128` and that encoder leaves the upper 64 bits
        // zero for a k <= 32 window. `KmerKey::from_u128` asserts the invariant
        // with a `debug_assert!` (active under `cargo test`, elided in release —
        // zero cost, threat T-03-09), so a caller that ever fed a value with
        // high bits set fails loudly in dev/test instead of silently aliasing
        // two distinct k-mers onto one key.
        let key = KmerKey::from_u128(kmer_encoded, self.kmer_length);
        let mut overflow = false;
        self.table
            .entry(key)
            .and_modify(|count| {
                if *count == self.max_count {
                    overflow = true;
                } else {
                    *count += 1;
                }
            })
            .or_insert_with(|| {
                self.unique_kmers
                    .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                1
            });

        if overflow {
            return Err(ProcessingError::new(format!(
                "K-mer count overflow reached maximum value {}",
                self.max_count
            )));
        }

        // Only count successful increments. The previous code bumped
        // `total_kmers` BEFORE the entry chain, so a per-k-mer overflow
        // (returning `Err`) still inflated the total — a numeric-correctness
        // discrepancy flagged by WR-03. Moving the `fetch_add` below the
        // overflow check ensures `total_kmers()` reflects the number of
        // k-mers successfully counted.
        self.total_kmers
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    /// Get the count for a specific k-mer
    ///
    /// # Arguments
    /// * `kmer_encoded` - Packed k-mer representation (u128 for k≤64)
    ///
    /// # Returns
    /// Number of occurrences, or None if not found
    pub fn get_count(&self, kmer_encoded: u128) -> Option<u32> {
        // DENSE-01: build the same width-selected key `increment` would have
        // stored, so a lookup cannot miss because of an asymmetric conversion.
        let key = KmerKey::from_u128(kmer_encoded, self.kmer_length);
        self.table.get(&key).map(|r| *r)
    }

    /// Get all k-mer counts as a vector
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs
    ///
    /// DENSE-01 / D-03: dense `KmerKey::U64` keys are widened back to `u128`
    /// by zero-extension on the way out, so this signature and every byte that
    /// reaches the `.rkdb` writer are unchanged from the pre-Phase-3 counter.
    pub fn get_all_counts(&self) -> Vec<(u128, u32)> {
        self.table
            .iter()
            .map(|r| (r.key().to_u128(), *r.value()))
            .collect()
    }

    /// Get the top N most frequent k-mers
    ///
    /// # Arguments
    /// * `n` - Number of top k-mers to return
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs sorted by count descending
    pub fn get_top_n(&self, n: usize) -> Vec<(u128, u32)> {
        let mut pairs: Vec<(u128, u32)> = self
            .table
            .iter()
            .map(|r| (r.key().to_u128(), *r.value()))
            .collect();

        // Sort by count descending, then by kmer value for deterministic ordering
        pairs.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));

        pairs.into_iter().take(n).collect()
    }

    /// Filter k-mers by count range
    ///
    /// # Arguments
    /// * `min_count` - Minimum count (inclusive)
    /// * `max_count` - Maximum count (inclusive)
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs within the specified range
    pub fn filter_by_count(&self, min_count: u32, max_count: u32) -> Vec<(u128, u32)> {
        self.table
            .iter()
            .filter(|r| *r.value() >= min_count && *r.value() <= max_count)
            .map(|r| (r.key().to_u128(), *r.value()))
            .collect()
    }

    /// Get k-mers with filtering applied using CountFilter
    ///
    /// # Arguments
    /// * `filter` - Optional count filter to apply
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs after filtering
    pub fn get_filtered_kmers(&self, filter: &Option<CountFilter>) -> Vec<(u128, u32)> {
        let all_kmers = self.get_all_counts();

        match filter {
            Some(f) => all_kmers
                .into_iter()
                .filter(|(_, count)| {
                    let count_u64 = *count as u64;
                    f.passes(count_u64)
                })
                .collect(),
            None => all_kmers,
        }
    }

    /// Get filtering statistics
    ///
    /// # Arguments
    /// * `filter` - Optional count filter to analyze
    ///
    /// # Returns
    /// FilteringResult with statistics
    ///
    /// # Denominator note (WR-01)
    /// `total_before` reflects the post-WR-03 `total_kmers` semantics: the
    /// number of k-mers **successfully** counted, excluding per-k-mer overflow
    /// attempts that returned `Err` from `increment`. On a saturating input
    /// (one or more k-mers hit `u32::MAX`), `total_before` is therefore
    /// smaller than the raw number of input k-mer windows. Any retention
    /// percentage derived from this value (`FilteringResult::kept_percentage`)
    /// is computed against the "successful k-mers" denominator, not the raw
    /// input-window count. This is arguably the more useful numerator for
    /// retention reporting, but it differs from the pre-WR-03 ("attempts")
    /// denominator; the shift is intentional and documented here so callers
    /// comparing pre/post stats on saturating inputs are not surprised.
    pub fn get_filtering_stats(&self, filter: &Option<CountFilter>) -> FilteringResult {
        let all_kmers = self.get_all_counts();
        let total_before = self.total_kmers.load(std::sync::atomic::Ordering::Relaxed);
        let unique_before = all_kmers.len() as u64;

        match filter {
            Some(f) => {
                let kept_after = all_kmers
                    .iter()
                    .filter(|(_, count)| {
                        let count_u64 = *count as u64;
                        f.passes(count_u64)
                    })
                    .count() as u64;

                FilteringResult::new(total_before, unique_before, kept_after, f.clone())
            }
            None => FilteringResult::new(
                total_before,
                unique_before,
                unique_before,
                CountFilter::default(),
            ),
        }
    }

    /// Get total number of k-mers processed
    pub fn total_kmers(&self) -> u64 {
        self.total_kmers.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// Get number of unique k-mers found
    pub fn unique_kmers(&self) -> u64 {
        self.unique_kmers.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// Get k-mer length
    pub fn kmer_length(&self) -> usize {
        self.kmer_length
    }

    /// Check if canonical mode is enabled
    pub fn canonical_mode(&self) -> bool {
        self.canonical_mode
    }

    /// Reset the counter to empty state
    pub fn reset(&self) {
        self.table.clear();
        self.total_kmers
            .store(0, std::sync::atomic::Ordering::Relaxed);
        self.unique_kmers
            .store(0, std::sync::atomic::Ordering::Relaxed);
    }

    /// Get current memory usage estimate
    ///
    /// # Returns
    /// Estimated memory usage in bytes
    ///
    /// # DENSE-01 (Phase 3)
    /// The per-entry model now branches on the stored key width: 24 B modelled
    /// hash/shard overhead + 8 B `KmerKey::U64` key + 4 B `u32` count for k ≤ 32,
    /// and 24 + 16 + 4 for the `KmerKey::U128` width. The keyed *payload* is
    /// what this plan halves (20 B → 12 B, i.e. 0.6×); the 24 B overhead is a
    /// modelled constant common to both widths and is not part of the payload.
    ///
    /// Because the value is derived from the key width, it doubles as an
    /// observable of which `KmerKey` variant `new()` selected — the property
    /// `tests/dense_differential_tests.rs` asserts directly.
    pub fn memory_usage(&self) -> usize {
        self.table.len() * (HASH_OVERHEAD_PER_ENTRY + self.key_bytes() + COUNT_BYTES)
    }

    /// Modelled bytes for one k-mer key at this counter's storage width.
    ///
    /// DENSE-01: 8 for the dense `KmerKey::U64` width (k ≤ 32), 16 for the
    /// `KmerKey::U128` width (k > 32). Derived from `kmer_length` on demand —
    /// see `new` for why no `use_u64` flag is cached.
    fn key_bytes(&self) -> usize {
        if self.kmer_length <= MAX_KMER_SIZE_IN_U64 {
            U64_KEY_BYTES
        } else {
            U128_KEY_BYTES
        }
    }

    /// Get statistics for the counter
    ///
    /// # Returns
    /// Statistics struct with current counts
    pub fn get_stats(&self) -> CounterStats {
        CounterStats {
            total_kmers: self.total_kmers.load(std::sync::atomic::Ordering::Relaxed),
            unique_kmers: self.unique_kmers.load(std::sync::atomic::Ordering::Relaxed),
            kmer_length: self.kmer_length,
            canonical_mode: self.canonical_mode,
        }
    }

    /// Get all k-mers as a vector (alias for get_all_counts)
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs
    pub fn get_all_kmers(&self) -> Vec<(u128, u32)> {
        self.get_all_counts()
    }

    /// Get k-mer length (alias for kmer_length)
    pub fn get_kmer_length(&self) -> usize {
        self.kmer_length
    }

    /// Merge counts from another KmerCounter
    ///
    /// On success, `total_kmers` / `unique_kmers` are updated to reflect the
    /// merged contents.
    ///
    /// **Overflow poisoning (WR-02):** if any per-k-mer merge would overflow
    /// (`existing + count > u32::MAX`), `merge` returns
    /// [`ProcessingError`]("Count overflow during merge"). Rolling back the
    /// partial DashMap mutation would require cloning the whole table before
    /// the loop (prohibitively expensive for genome-scale counters), so the
    /// counter is left **poisoned**: all k-mers processed before the
    /// overflowing one have already been merged into `self.table`, and the
    /// `total_kmers` / `unique_kmers` atomics are updated incrementally to
    /// stay consistent with the (partial) table contents. Callers that
    /// recover from this `Err` and continue to use `self` will see correct
    /// statistics for the partial merge, but should treat the counter as
    /// tainted (the missing post-overflow k-mers are lost). The recommended
    /// recovery is to discard the poisoned counter.
    ///
    /// **Thread safety (WR-04):** the DashMap table is safe under concurrent
    /// `increment`, but `merge` MUST NOT run concurrently with `increment` or
    /// another `merge` on the same `KmerCounter`. `merge` takes `&self` so
    /// the compiler permits it, but the per-loop-iteration atomic-publish of
    /// `total_kmers` / `unique_kmers` (the WR-02 fix) is only guaranteed to
    /// stay consistent with the table contents when observed single-threaded:
    /// a concurrent `increment` that completes during `merge`'s loop can land
    /// its own `fetch_add` between `merge`'s local accumulator and the final
    /// `fetch_add`, transiently under-reporting `total_kmers()` relative to
    /// the table. The values eventually converge (addition commutes), but the
    /// transient window is observable. The recommended pattern is to merge
    /// into a counter that is not currently being incremented, or to hold an
    /// external mutex around `merge`.
    ///
    /// # Arguments
    /// * `other` - Another KmerCounter to merge from
    ///
    /// # Returns
    /// Result indicating success or error
    pub fn merge(&self, other: &KmerCounter) -> ProcessingResult<()> {
        if self.kmer_length != other.kmer_length {
            return Err(ProcessingError::new(format!(
                "Cannot merge counters with different k-mer lengths: {} vs {}",
                self.kmer_length, other.kmer_length
            )));
        }

        if self.canonical_mode != other.canonical_mode {
            return Err(ProcessingError::new(
                "Cannot merge counters with different canonical modes",
            ));
        }

        let other_counts = other.get_all_counts();

        // WR-02: update total_kmers / unique_kmers incrementally inside the
        // loop so the atomics stay consistent with the table contents at every
        // per-k-mer boundary. Previously both atomics were updated only after
        // the loop completed successfully, so an overflow mid-loop returned
        // `Err` but left `self.table` mutated and the atomics reporting the
        // pre-merge values — an internally inconsistent state.
        let mut merged_unique: u64 = 0;
        let mut merged_total: u64 = 0;

        for (kmer, count) in other_counts {
            // Mirror `increment`'s flag-then-check (Pitfall 6): `and_modify`
            // is `FnOnce(&mut V) -> ()` and cannot return `Result`. The shard
            // lock is held for the entry's whole lifetime, so the
            // overflow-check + add is atomic per-key (no TOCTOU window).
            //
            // DENSE-01: `other_counts` are widened back to `u128` by
            // `get_all_counts`, so re-narrow them with the *same* width rule
            // `increment` used. `merge` already rejected a differing
            // `kmer_length` above, so `self` and `other` necessarily agree on
            // the width and this round-trip (`U64 -> u128 -> U64`) is exact.
            let key = KmerKey::from_u128(kmer, self.kmer_length);
            let mut overflow = false;
            let mut delta_total: u64 = 0;
            self.table
                .entry(key)
                .and_modify(|existing| {
                    if *existing > u32::MAX - count {
                        overflow = true;
                    } else {
                        *existing += count;
                        delta_total = count as u64;
                    }
                })
                .or_insert_with(|| {
                    merged_unique += 1;
                    delta_total = count as u64;
                    count
                });

            if overflow {
                // Publish the partial atomics before returning so the
                // poisoned counter's stats match its (partial) contents.
                self.total_kmers
                    .fetch_add(merged_total, std::sync::atomic::Ordering::Relaxed);
                self.unique_kmers
                    .fetch_add(merged_unique, std::sync::atomic::Ordering::Relaxed);
                return Err(ProcessingError::new("Count overflow during merge"));
            }
            merged_total += delta_total;
        }

        // Publish the accumulated totals on success.
        self.total_kmers
            .fetch_add(merged_total, std::sync::atomic::Ordering::Relaxed);
        self.unique_kmers
            .fetch_add(merged_unique, std::sync::atomic::Ordering::Relaxed);

        Ok(())
    }
}

/// Statistics for a KmerCounter
#[derive(Debug, Clone)]
pub struct CounterStats {
    /// Total number of k-mers processed
    pub total_kmers: u64,
    /// Number of unique k-mers found
    pub unique_kmers: u64,
    /// K-mer length
    pub kmer_length: usize,
    /// Whether canonical mode is enabled
    pub canonical_mode: bool,
}

/// Builder for KmerCounter with configuration options
pub struct KmerCounterBuilder {
    kmer_length: usize,
    canonical_mode: bool,
    initial_capacity: Option<usize>,
    max_count: u32,
}

impl KmerCounterBuilder {
    /// Create a new builder
    pub fn new(kmer_length: usize) -> Self {
        Self {
            kmer_length,
            canonical_mode: false,
            initial_capacity: None,
            max_count: u32::MAX,
        }
    }

    /// Enable canonical mode
    pub fn canonical(mut self, canonical: bool) -> Self {
        self.canonical_mode = canonical;
        self
    }

    /// Set initial hash table capacity
    pub fn capacity(mut self, capacity: usize) -> Self {
        self.initial_capacity = Some(capacity);
        self
    }

    /// Set maximum count value
    pub fn max_count(mut self, max: u32) -> Self {
        self.max_count = max;
        self
    }

    /// Build the KmerCounter
    pub fn build(self) -> ProcessingResult<KmerCounter> {
        let capacity = self.initial_capacity.unwrap_or(1000);
        KmerCounter::new(self.kmer_length, self.canonical_mode, capacity, 1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_increment() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter.increment(0x12345678).unwrap();
        assert_eq!(counter.get_count(0x12345678), Some(1));
        assert_eq!(counter.total_kmers(), 1);
        assert_eq!(counter.unique_kmers(), 1);
    }

    #[test]
    fn test_multiple_increments() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter.increment(0x12345678).unwrap();
        counter.increment(0x12345678).unwrap();
        counter.increment(0x87654321).unwrap();

        assert_eq!(counter.get_count(0x12345678), Some(2));
        assert_eq!(counter.get_count(0x87654321), Some(1));
        assert_eq!(counter.total_kmers(), 3);
        assert_eq!(counter.unique_kmers(), 2);
    }

    #[test]
    fn test_top_n() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter.increment(0x1).unwrap(); // count 1
        counter.increment(0x2).unwrap();
        counter.increment(0x2).unwrap();
        counter.increment(0x3).unwrap();
        counter.increment(0x3).unwrap();
        counter.increment(0x3).unwrap();

        let top = counter.get_top_n(2);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0], (0x3, 3)); // Highest count
        assert_eq!(top[1], (0x2, 2)); // Second highest
    }

    #[test]
    fn test_filter_by_count() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter.increment(0x1).unwrap(); // count 1
        counter.increment(0x2).unwrap();
        counter.increment(0x2).unwrap();
        counter.increment(0x3).unwrap();
        counter.increment(0x3).unwrap();
        counter.increment(0x3).unwrap();
        counter.increment(0x4).unwrap();
        counter.increment(0x4).unwrap();

        let filtered = counter.filter_by_count(2, 2);
        assert_eq!(filtered.len(), 2);
        // Check that both entries have count 2 (order may vary)
        assert!(filtered.contains(&(0x2, 2)));
        assert!(filtered.contains(&(0x4, 2)));
    }

    #[test]
    fn test_merge() {
        let counter1 = KmerCounter::new(31, false, 1000, 1).unwrap();
        let counter2 = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter1.increment(0x1).unwrap();
        counter1.increment(0x2).unwrap();

        counter2.increment(0x2).unwrap();
        counter2.increment(0x3).unwrap();

        counter1.merge(&counter2).unwrap();

        assert_eq!(counter1.get_count(0x1), Some(1));
        assert_eq!(counter1.get_count(0x2), Some(2));
        assert_eq!(counter1.get_count(0x3), Some(1));
        assert_eq!(counter1.total_kmers(), 4);
        assert_eq!(counter1.unique_kmers(), 3);
    }

    #[test]
    fn test_merge_different_lengths() {
        let counter1 = KmerCounter::new(31, false, 1000, 1).unwrap();
        let counter2 = KmerCounter::new(21, false, 1000, 1).unwrap();

        let result = counter1.merge(&counter2);
        assert!(result.is_err());
    }

    /// WR-02 regression: when `merge` hits a per-k-mer overflow mid-loop,
    /// the counter's `total_kmers` / `unique_kmers` atomics must reflect the
    /// partial mutation that already landed in `self.table` (poisoned-but-
    /// internally-consistent). Before WR-02 the atomics were updated only
    /// after the loop completed successfully, so an overflow return left the
    /// table mutated but the stats reporting the pre-merge values.
    ///
    /// Setup: `counter1` holds `0x1 -> u32::MAX`. `counter2` holds
    /// `0x1 -> 1` (will overflow when added) and `0x2 -> 1` (will succeed
    /// if processed before the overflow). Because `get_all_counts` iteration
    /// order is unspecified, we assert the *weaker* invariant: after the
    /// `Err` return, the per-atomic value must equal the sum of `count`s
    /// that were actually merged into `self.table` — i.e. it must be
    /// consistent with `self.get_all_counts().map(|(_, c)| c as u64).sum()`.
    #[test]
    fn test_merge_overflow_poisons_consistently() {
        let counter1 = KmerCounter::new(31, false, 1000, 1).unwrap();
        let counter2 = KmerCounter::new(31, false, 1000, 1).unwrap();

        // Seed counter1's kmer at the ceiling.
        // Seed counter1's kmer at the ceiling. The private `table` field is
        // keyed by `KmerKey` since DENSE-01, and this counter was built with
        // k=31 (<= 32), so the seed must go through the same width selection
        // `increment` uses — hence `from_u128(kmer, kmer_length)`.
        counter1.table.insert(KmerKey::from_u128(0x1, 31), u32::MAX);
        // Manually keep counter1's atomics in sync with the seed for a fair
        // starting point (the table field is private but in-scope from this
        // child module).
        counter1
            .total_kmers
            .store(u32::MAX as u64, std::sync::atomic::Ordering::Relaxed);
        counter1
            .unique_kmers
            .store(1, std::sync::atomic::Ordering::Relaxed);

        // counter2 has a kmer that will overflow (0x1 += 1) and a fresh one
        // that will succeed (0x2 -> 1).
        counter2.increment(0x1).unwrap();
        counter2.increment(0x2).unwrap();

        let result = counter1.merge(&counter2);
        assert!(result.is_err(), "merge that overflows must return Err");
        let msg = format!("{}", result.unwrap_err());
        assert!(
            msg.contains("Count overflow during merge"),
            "expected verbatim overflow message; got: {}",
            msg
        );

        // WR-02 invariant: the atomics must agree with the actual table
        // contents. Whatever the iteration order, the sum of counts in
        // `self.table` and `self.total_kmers()` must match.
        let table_total: u64 = counter1
            .get_all_counts()
            .iter()
            .map(|(_, c)| *c as u64)
            .sum();
        assert_eq!(
            counter1.total_kmers(),
            table_total,
            "after poisoned merge, total_kmers must equal the sum of \
             counts in self.table (WR-02): got total={} table_sum={}",
            counter1.total_kmers(),
            table_total
        );
        let table_unique = counter1.get_all_counts().len() as u64;
        assert_eq!(
            counter1.unique_kmers(),
            table_unique,
            "after poisoned merge, unique_kmers must equal the number of \
             entries in self.table (WR-02)"
        );

        // The overflow target must NOT have advanced past the ceiling.
        assert_eq!(counter1.get_count(0x1), Some(u32::MAX));
    }

    #[test]
    fn test_reset() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        counter.increment(0x12345678).unwrap();
        assert_eq!(counter.total_kmers(), 1);

        counter.reset();
        assert_eq!(counter.total_kmers(), 0);
        assert_eq!(counter.unique_kmers(), 0);
        assert_eq!(counter.get_count(0x12345678), None);
    }

    #[test]
    fn test_builder() {
        let counter = KmerCounterBuilder::new(21)
            .canonical(true)
            .capacity(1000)
            .max_count(10000)
            .build()
            .unwrap();

        assert_eq!(counter.kmer_length(), 21);
        assert!(counter.canonical_mode());
    }

    /// PCOUNT-02 / PCOUNT-04 (VALIDATION.md Wave 0): concurrent increments
    /// on the same k-mer must produce a count equal to the number of
    /// increments — the commutativity property at unit scale. Any divergence
    /// is a lost-update / double-count bug (RESEARCH Pitfall 1), since integer
    /// addition is commutative and associative.
    ///
    /// Uses `std::thread::scope` (Rust 1.63+; project is 1.80+) to spawn N
    /// threads that share the SAME `&KmerCounter` (DashMap gives interior
    /// mutability so `increment` takes `&self`). The sharded `entry()` upsert
    /// holds only the relevant shard lock for each increment → atomic per-key.
    ///
    /// DENSE-01 note: this counter is built with k=31, so `increment` narrows
    /// the argument into the `KmerKey::U64` storage width. The literal is a
    /// 64-bit value (16 hex digits), so it is a representable k ≤ 32 k-mer and
    /// satisfies the narrowing invariant `KmerKey::from_u128` asserts. A literal
    /// with bits above bit 63 would now be a programming error and would trip
    /// that assert (threat T-03-09) — which is the point.
    #[test]
    fn test_increment_atomic_under_concurrency() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();
        const THREADS: usize = 8;
        const INCREMENTS_PER_THREAD: usize = 1000;
        let kmer: u128 = 0xCAFE_BABE_DEAD_BEEF;

        std::thread::scope(|s| {
            for _ in 0..THREADS {
                // `counter` borrows are `&` — DashMap's interior mutability
                // makes the concurrent `increment` calls sound.
                let counter_ref = &counter;
                s.spawn(move || {
                    for _ in 0..INCREMENTS_PER_THREAD {
                        counter_ref
                            .increment(kmer)
                            .expect("increment must not overflow");
                    }
                });
            }
        });

        assert_eq!(
            counter.get_count(kmer),
            Some((THREADS * INCREMENTS_PER_THREAD) as u32),
            "concurrent increments must not lose updates or double-count (PCOUNT-04)"
        );
        assert_eq!(
            counter.total_kmers(),
            (THREADS * INCREMENTS_PER_THREAD) as u64,
            "total_kmers atomic must match the sum of all increments"
        );
        assert_eq!(
            counter.unique_kmers(),
            1,
            "only one unique k-mer was touched"
        );
    }

    /// PCOUNT-04 (VALIDATION.md Wave 0): the u32::MAX overflow guard must
    /// still fire per-k-mer with the EXACT verbatim message preserved from
    /// the pre-refactor path (table.rs:76-79). The flag-then-check pattern
    /// inside `and_modify` preserves this byte-for-byte.
    ///
    /// Rather than looping `u32::MAX` times (4 billion iterations — too slow),
    /// the test seeds the k-mer at `u32::MAX` directly via the private `table`
    /// field (accessible because the test module is a child of the module
    /// that owns `KmerCounter`). The next `increment` then hits the
    /// `*count == self.max_count` branch inside `and_modify`, sets the
    /// `overflow` flag, and the post-entry-chain check returns the verbatim
    /// error.
    #[test]
    fn test_overflow_preserved() {
        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();
        let kmer: u128 = 0xBAD_F00D;

        // Seed the k-mer at the saturation ceiling WITHOUT 4 billion increments.
        // (The test module is a child of `table`'s module, so the private
        // `table` field is in scope. DENSE-01: the field is keyed by
        // `KmerKey`, so the seed must use the same width selection `increment`
        // uses — k=31 selects `KmerKey::U64`.)
        counter.table.insert(KmerKey::from_u128(kmer, 31), u32::MAX);

        // The next increment must hit the overflow guard and return Err with
        // the verbatim "K-mer count overflow reached maximum value 4294967295"
        // message (PCOUNT-04 — byte-identical to the pre-refactor path).
        let result = counter.increment(kmer);
        assert!(
            result.is_err(),
            "increment at u32::MAX must error, not wrap"
        );
        let msg = format!("{}", result.unwrap_err());
        assert!(
            msg.contains("K-mer count overflow reached maximum value"),
            "overflow message must contain the verbatim prefix; got: {}",
            msg
        );
        assert!(
            msg.contains(&u32::MAX.to_string()),
            "overflow message must contain the max value ({}) ; got: {}",
            u32::MAX,
            msg
        );

        // The count must NOT have advanced past the ceiling (no silent wrap).
        assert_eq!(
            counter.get_count(kmer),
            Some(u32::MAX),
            "saturated k-mer count must remain at u32::MAX, not wrap"
        );

        // WR-03 regression: a per-k-mer overflow attempt must NOT inflate
        // `total_kmers`. Before WR-03, `increment` bumped `total_kmers`
        // unconditionally at the top of the function, so this overflow attempt
        // would have reported `total_kmers == 1` despite the increment
        // failing and the per-k-mer count not advancing.
        assert_eq!(
            counter.total_kmers(),
            0,
            "a failed (overflow) increment must not inflate total_kmers (WR-03)"
        );
    }

    /// WR-01 regression: after the WR-03 fix moved `total_kmers.fetch_add`
    /// below the overflow check, the `total_before` denominator that
    /// `get_filtering_stats` feeds into `FilteringResult::new` / `kept_percentage`
    /// reflects "successful k-mers" rather than "attempted k-mers". This test
    /// pins the post-overflow filtering-stats behavior so the semantic shift
    /// is locked in and documented.
    ///
    /// Setup: seed one k-mer at the `u32::MAX` ceiling, then attempt one more
    /// increment on it (which overflows and returns `Err`, so `total_kmers`
    /// does NOT advance). Also successfully increment a second, distinct
    /// k-mer. The post-overflow `total_kmers` is therefore 1 (only the
    /// successful increment on the second k-mer), NOT 2 (the two attempts).
    /// A `CountFilter` of `min_count = 1` keeps both unique k-mers, so
    /// `kept_after == 2` and `unique_before == 2`, but `total_before == 1`.
    #[test]
    fn test_filtering_stats_after_overflow_uses_success_denominator() {
        use crate::hash::CountFilter;

        let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

        // Seed 0x1 at the ceiling so the next increment on it overflows.
        // DENSE-01: `table` is keyed by `KmerKey`; k=31 selects `U64`.
        counter.table.insert(KmerKey::from_u128(0x1, 31), u32::MAX);
        counter
            .total_kmers
            .store(u32::MAX as u64, std::sync::atomic::Ordering::Relaxed);
        counter
            .unique_kmers
            .store(1, std::sync::atomic::Ordering::Relaxed);

        // Overflow attempt on 0x1 (returns Err, must NOT advance total_kmers).
        let overflow_result = counter.increment(0x1);
        assert!(overflow_result.is_err());

        // Successful increment on a distinct k-mer 0x2 (advances total_kmers
        // by 1 and unique_kmers by 1).
        counter.increment(0x2).unwrap();

        // After overflow: total_kmers = u32::MAX (seed) + 1 (the 0x2 success),
        // NOT + 2 (the 0x2 success + the failed 0x1 attempt).
        assert_eq!(
            counter.total_kmers(),
            u32::MAX as u64 + 1,
            "total_kmers must reflect successful increments only (WR-03)"
        );

        // The filtering-stats denominator is `total_kmers` (WR-01): on a
        // saturating input it is the "successful k-mers" count, not the raw
        // input-window count. Pin the value so a future change to the
        // denominator semantics triggers this test.
        let filter = CountFilter::new(Some(1), None);
        let stats = counter.get_filtering_stats(&Some(filter));

        assert_eq!(
            stats.unique_before, 2u64,
            "both seeded k-mers (0x1 at ceiling, 0x2 at 1) are present"
        );
        assert_eq!(
            stats.kept_after, 2u64,
            "min_count=1 keeps both k-mers (0x1 has count u32::MAX >= 1)"
        );
        assert_eq!(
            stats.total_before, counter.total_kmers(),
            "FilteringResult::total_before must equal the post-WR-03 total_kmers (WR-01 denominator)"
        );
    }

    /// Threat T-03-09 (Tampering): the `u128 -> u64` narrowing in `increment` must
    /// not silently truncate a value that does not fit the dense width.
    ///
    /// `KmerKey::from_u128` guards that with a `debug_assert!` — compiled out in
    /// release (zero cost, D-03 zero-extension discipline), active in `cargo
    /// test`. This test proves the guard actually fires, rather than merely
    /// asserting it in a comment: without it, a caller that encoded a k-mer with
    /// bits above bit 64 would alias two distinct k-mers onto one key and merge
    /// their counts silently.
    ///
    /// Gated on `debug_assertions` because the release profile sets
    /// `panic = "abort"` — a release-mode run of this test would abort the
    /// process instead of panicking catchably, so there is no sound way to assert
    /// it there. The guard is a development/test-time invariant by design.
    #[cfg(debug_assertions)]
    #[test]
    #[should_panic(
        expected = "u64 storage width selected for kmer_length 21 but the encoded value has bits set above bit 64"
    )]
    fn dense_narrowing_rejects_high_bits_on_the_u64_path() {
        // k=21 selects `KmerKey::U64`; `u128::MAX` cannot fit a u64.
        let _ = KmerKey::from_u128(u128::MAX, 21);
    }

    /// The other half of T-03-09: the same value is *legitimate* on the wide
    /// path, so the guard must not fire there — it is width-scoped, not a
    /// blanket rejection of large k-mers.
    #[test]
    fn dense_narrowing_guard_does_not_fire_on_the_u128_path() {
        assert_eq!(
            KmerKey::from_u128(u128::MAX, 64),
            KmerKey::U128(u128::MAX),
            "k=64 must store the full u128 with no narrowing"
        );
    }

    /// A round-trip through the two conversions must be lossless for every k-mers
    /// a given width is allowed to represent — this is the property that makes
    /// the `.rkdb` write path byte-identical (D-03 / DENSE-02).
    #[test]
    fn dense_key_round_trip_is_lossless_on_both_widths() {
        for &k in &[1usize, 15, 21, 31, 32] {
            let value = 0x0123_4567_89AB_CDEFu64 as u128;
            assert_eq!(
                KmerKey::from_u128(value, k).to_u128(),
                value,
                "k={} must round-trip a representable u64 k-mer exactly",
                k
            );
        }
        for &k in &[33usize, 64] {
            let value = u128::MAX - 12345;
            assert_eq!(
                KmerKey::from_u128(value, k).to_u128(),
                value,
                "k={} must round-trip a full-width u128 k-mer exactly",
                k
            );
        }
    }

    /// DENSE-01 (plan 03-03): a k ≤ 32 counter must model its per-key storage
    /// at the dense `u64` width — 8-byte key — while a k > 32 counter keeps the
    /// 16-byte `u128` key. `memory_usage()` is derived from the stored key
    /// width, so its value is a direct observation of which `KmerKey` variant
    /// `new()` selected.
    #[test]
    fn dense_counter_memory_usage_halved_for_k21() {
        const N: usize = 4096;
        // 24 B modelled hash/shard overhead, shared by both widths.
        const OVERHEAD: usize = 24;
        // key + count payload: 8 + 4 dense, 16 + 4 wide.
        const DENSE_PAYLOAD: usize = 8 + 4;
        const WIDE_PAYLOAD: usize = 16 + 4;

        let dense = KmerCounter::new(21, false, N, 1).unwrap();
        let wide = KmerCounter::new(64, false, N, 1).unwrap();
        for i in 0..N {
            // Distinct k-mers on both sides, so both tables hold N entries.
            let kmer = i as u128;
            dense.increment(kmer).unwrap();
            wide.increment(kmer).unwrap();
        }
        assert_eq!(dense.unique_kmers(), N as u64);
        assert_eq!(wide.unique_kmers(), N as u64);

        let dense_usage = dense.memory_usage();
        let wide_usage = wide.memory_usage();

        // The modelled per-entry cost follows the key width.
        assert_eq!(
            dense_usage,
            N * (OVERHEAD + DENSE_PAYLOAD),
            "a k=21 counter must model 8-byte keys (DENSE-01), i.e. {} bytes/entry",
            OVERHEAD + DENSE_PAYLOAD
        );
        assert_eq!(
            wide_usage,
            N * (OVERHEAD + WIDE_PAYLOAD),
            "a k=64 counter must keep 16-byte keys, i.e. {} bytes/entry",
            OVERHEAD + WIDE_PAYLOAD
        );

        // DENSE-01's "roughly half": compare the *keyed payload* — the part of
        // the entry this plan actually shrinks — rather than the total, because
        // the 24-byte hash/shard overhead is common to both widths and does not
        // narrow. Asserting half on the total would be measuring a constant
        // this plan does not touch.
        let dense_payload = dense_usage - N * OVERHEAD;
        let wide_payload = wide_usage - N * OVERHEAD;
        let payload_ratio = dense_payload as f64 / wide_payload as f64;
        assert!(
            (0.4..=0.7).contains(&payload_ratio),
            "DENSE-01: k<=32 keyed payload must be roughly half the u128 payload \
             (expected ~0.6 for 12/20 bytes; got {})",
            payload_ratio
        );

        // And the reported total must strictly decrease, by exactly the 8 bytes
        // per key that 16 -> 8 saves.
        assert!(
            dense_usage < wide_usage,
            "the dense counter must report strictly lower memory usage"
        );
        assert_eq!(
            wide_usage - dense_usage,
            N * 8,
            "the saving must be exactly the 8-byte per-key key shrink"
        );
    }
}
