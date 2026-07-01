//! Concurrent hash table for k-mer counting
//!
//! Provides a thread-safe hash table implementation optimized for k-mer counting
//! with minimal contention and efficient memory usage.

use dashmap::DashMap;

use super::filtering::{CountFilter, FilteringResult};
use crate::error::{KmerError, ProcessingError, ProcessingResult};

/// Thread-safe k-mer counter with concurrent operations
#[derive(Debug)]
pub struct KmerCounter {
    /// Core hash table storing k-mer counts (u128 for k≤64 support).
    ///
    /// Backed by `dashmap::DashMap` (Phase 2, PCOUNT-02): internally sharded
    /// (~4×num_cpus per-shard `RwLock`s), so increments spread across shards
    /// and throughput scales with core count without a single global lock.
    /// The `entry().and_modify().or_insert_with()` chain holds only the
    /// relevant shard lock for its lifetime → atomic per-key (RESEARCH
    /// Pattern 1), preserving the u32::MAX overflow semantics verbatim.
    table: DashMap<u128, u32>,
    /// Total k-mers processed
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
    /// * `num_threads` - Number of threads for concurrent processing
    ///
    /// # Returns
    /// New KmerCounter instance
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
            table: DashMap::<u128, u32>::with_capacity(initial_capacity),
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
        self.total_kmers
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

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
        let mut overflow = false;
        self.table
            .entry(kmer_encoded)
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
        self.table.get(&kmer_encoded).map(|r| *r)
    }

    /// Get all k-mer counts as a vector
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs
    pub fn get_all_counts(&self) -> Vec<(u128, u32)> {
        self.table.iter().map(|r| (*r.key(), *r.value())).collect()
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
            .map(|r| (*r.key(), *r.value()))
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
            .map(|r| (*r.key(), *r.value()))
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
    pub fn memory_usage(&self) -> usize {
        // Estimate: each entry uses ~24 bytes (HashMap overhead) + 20 bytes for (u128, u32)
        self.table.len() * (24 + 20)
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
        let mut merged_unique: u64 = 0;

        for (kmer, count) in other_counts {
            // Mirror `increment`'s flag-then-check (Pitfall 6): `and_modify`
            // is `FnOnce(&mut V) -> ()` and cannot return `Result`. The shard
            // lock is held for the entry's whole lifetime, so the
            // overflow-check + add is atomic per-key (no TOCTOU window).
            let mut overflow = false;
            self.table
                .entry(kmer)
                .and_modify(|existing| {
                    if *existing > u32::MAX - count {
                        overflow = true;
                    } else {
                        *existing += count;
                    }
                })
                .or_insert_with(|| {
                    merged_unique += 1;
                    count
                });

            if overflow {
                return Err(ProcessingError::new("Count overflow during merge"));
            }
        }

        // Update statistics
        self.total_kmers
            .fetch_add(other.total_kmers(), std::sync::atomic::Ordering::Relaxed);
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
                        counter_ref.increment(kmer).expect("increment must not overflow");
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
        assert_eq!(counter.unique_kmers(), 1, "only one unique k-mer was touched");
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
        // `table` field is in scope.)
        counter.table.insert(kmer, u32::MAX);

        // The next increment must hit the overflow guard and return Err with
        // the verbatim "K-mer count overflow reached maximum value 4294967295"
        // message (PCOUNT-04 — byte-identical to the pre-refactor path).
        let result = counter.increment(kmer);
        assert!(result.is_err(), "increment at u32::MAX must error, not wrap");
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
    }
}
