//! Hash-range partition routing for the shared counting engine.
//!
//! **ENGINE-01 (partition scheme, locked by 07-RESEARCH.md Q2).** Counting
//! accumulates into a fixed set of disjoint partition tables, one owner per
//! key. This module owns the routing function and the partition-to-worker
//! layout; the tables themselves are [`crate::hash::local::LocalKmerCounts`].
//!
//! Raw 2-bit-packed DNA keys are strongly structured: partitioning on the raw
//! top key bits was measured at **max/mean = 3.54** on the real 4M-read slice,
//! which would cap scaling with a 3.5x straggler partition. Folding the u128
//! key and running the splitmix64 finalizer measured **max/mean = 1.02** on
//! windows and **1.00** on distinct keys. The multiply-shift range mapping
//! avoids a division per window and is uniform for any partition count.
//!
//! Routing depends only on `(key, partitions)`, so counts never depend on the
//! thread count and the sorted `.rkdb` output is deterministic.

use std::ops::Range;

/// Minimum partition count (`P = min(MAX, max(MIN, threads))`).
pub const MIN_PARTITIONS: usize = 64;

/// Maximum partition count; keeps the table count bounded on huge hosts.
pub const MAX_PARTITIONS: usize = 256;

/// The splitmix64 finalizer: a strong, branch-free 64-bit mixer.
///
/// # Arguments
/// * `z` - Folded key value
///
/// # Returns
/// The mixed value. Deterministic and identical across platforms.
///
/// # Examples
/// ```
/// use rustkmer::count::partition::mix64;
///
/// assert_eq!(mix64(0), 0);
/// assert_ne!(mix64(1), mix64(2));
/// ```
#[inline]
pub fn mix64(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

/// Map an encoded k-mer key to exactly one partition in `0..partitions`.
///
/// The u128 key is folded with XOR, mixed with [`mix64`], then range-mapped
/// with the 64-bit multiply-shift trick (`(h * partitions) >> 64`), which is
/// uniform for any `partitions` and performs no division.
///
/// # Arguments
/// * `key` - Encoded (and canonicalized, when applicable) k-mer
/// * `partitions` - Partition count; must be non-zero
///
/// # Returns
/// The owning partition index in `0..partitions`.
///
/// # Examples
/// ```
/// use rustkmer::count::partition::partition_of;
///
/// // Deterministic and always in range.
/// let first = partition_of(0xDEAD_BEEF, 64);
/// let second = partition_of(0xDEAD_BEEF, 64);
/// assert_eq!(first, second);
/// assert!(first < 64);
/// ```
#[inline]
pub fn partition_of(key: u128, partitions: usize) -> usize {
    debug_assert!(partitions > 0, "partition count must be non-zero");
    let folded = (key as u64) ^ ((key >> 64) as u64);
    let mixed = mix64(folded);
    // Uniform range mapping for any P; the product fits u128 by construction.
    ((mixed as u128 * partitions as u128) >> 64) as usize
}

/// Partition count and static partition-to-worker ownership.
///
/// `P = min(256, max(64, workers))`: a fixed 64 partitions on the 16-core
/// target, decoupled from the worker count so the partition assignment is
/// identical across thread counts. Workers statically own contiguous partition
/// ranges (computed with ceil-division); when there are more workers than
/// partitions, a worker may own an empty range.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PartitionLayout {
    partitions: usize,
    workers: usize,
}

impl PartitionLayout {
    /// Build a layout for `workers` (clamped to at least one).
    ///
    /// # Arguments
    /// * `workers` - Resolved worker count; `0` is treated as `1`
    ///
    /// # Returns
    /// A layout with `partitions = min(256, max(64, workers))`.
    ///
    /// # Examples
    /// ```
    /// use rustkmer::count::PartitionLayout;
    ///
    /// assert_eq!(PartitionLayout::new(1).partitions(), 64);
    /// assert_eq!(PartitionLayout::new(16).partitions(), 64);
    /// assert_eq!(PartitionLayout::new(100).partitions(), 100);
    /// assert_eq!(PartitionLayout::new(1_000).partitions(), 256);
    /// ```
    pub fn new(workers: usize) -> Self {
        let workers = workers.max(1);
        let partitions = workers.clamp(MIN_PARTITIONS, MAX_PARTITIONS);
        Self {
            partitions,
            workers,
        }
    }

    /// Number of partition tables.
    pub fn partitions(&self) -> usize {
        self.partitions
    }

    /// Worker count this layout was built for.
    pub fn workers(&self) -> usize {
        self.workers
    }

    /// The single worker that owns `partition`.
    ///
    /// # Arguments
    /// * `partition` - Partition index in `0..partitions`
    ///
    /// # Returns
    /// The owning worker index in `0..workers`.
    pub fn owner_of(&self, partition: usize) -> usize {
        debug_assert!(partition < self.partitions);
        (partition / self.partitions_per_worker()).min(self.workers - 1)
    }

    /// The contiguous partition range owned by `worker`.
    ///
    /// Ranges are disjoint and together cover `0..partitions` exactly once.
    /// A worker beyond the partition count owns an empty range.
    ///
    /// # Arguments
    /// * `worker` - Worker index in `0..workers`
    ///
    /// # Returns
    /// The owned `Range<usize>`.
    pub fn worker_range(&self, worker: usize) -> Range<usize> {
        let per_worker = self.partitions_per_worker();
        let start = worker.saturating_mul(per_worker).min(self.partitions);
        let end = (worker + 1).saturating_mul(per_worker).min(self.partitions);
        start..end
    }

    /// Ceil-division so every partition has exactly one owner.
    fn partitions_per_worker(&self) -> usize {
        self.partitions.div_ceil(self.workers)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Deterministic LCG so the distribution assertions are reproducible.
    fn next_key(state: &mut u64) -> u64 {
        *state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        *state
    }

    fn max_over_mean(counts: &[u64]) -> f64 {
        let max = *counts.iter().max().expect("non-empty partition histogram");
        let mean = counts.iter().sum::<u64>() as f64 / counts.len() as f64;
        assert!(mean > 0.0, "histogram must carry keys");
        max as f64 / mean
    }

    /// Splitmix routing must be uniform on random 64-bit keys.
    #[test]
    fn splitmix_routing_is_uniform_on_random_keys() {
        let partitions = 64;
        let mut histogram = vec![0u64; partitions];
        let mut state = 0x1234_5678_9ABC_DEF0;
        for _ in 0..65_536 {
            let key = next_key(&mut state) as u128;
            histogram[partition_of(key, partitions)] += 1;
        }
        let ratio = max_over_mean(&histogram);
        assert!(
            ratio < 1.35,
            "splitmix routing must be near-uniform on random keys (max/mean = {ratio:.3})"
        );
    }

    /// Structured 2-bit ACGT keys must also route near-uniformly once mixed
    /// (raw top bits measured 3.54 max/mean on real data).
    #[test]
    fn splitmix_routing_is_uniform_on_structured_acgt_keys() {
        use crate::kmer::encoding::encode_kmer_bytes_u128;

        const BASES: [u8; 4] = *b"ACGT";
        let partitions = 64;
        let mut histogram = vec![0u64; partitions];
        let mut state = 0xFEED_FACE_CAFE_BEEF_u64;
        let mut window = [b'A'; 21];
        for _ in 0..16_384 {
            for base in window.iter_mut() {
                let index = ((next_key(&mut state) >> 33) & 3) as usize;
                *base = BASES[index];
            }
            let key = encode_kmer_bytes_u128(&window).expect("ACGT only");
            histogram[partition_of(key, partitions)] += 1;
        }
        let ratio = max_over_mean(&histogram);
        assert!(
            ratio < 1.35,
            "structured ACGT keys must route near-uniformly (max/mean = {ratio:.3})"
        );
    }

    /// A constant key concentrates in one partition by construction; this is
    /// inherent to disjoint exact counting, not a mixer defect.
    #[test]
    fn constant_key_concentrates_in_one_partition_by_definition() {
        let partitions = 64;
        let mut histogram = vec![0u64; partitions];
        for _ in 0..1_000 {
            histogram[partition_of(0xAAAA_AAAA_AAAA_AAAA, partitions)] += 1;
        }
        let occupied = histogram.iter().filter(|count| **count > 0).count();
        assert_eq!(
            occupied, 1,
            "a constant key must land in exactly one partition"
        );
    }

    /// Routing is deterministic and in range for arbitrary (including
    /// non-power-of-two) partition counts.
    #[test]
    fn routing_is_in_range_and_deterministic_for_any_partition_count() {
        for partitions in [1usize, 2, 3, 63, 64, 100, 127, 255, 256] {
            for key in [0u128, 1, u128::MAX, 0x0123_4567_89AB_CDEF, u64::MAX as u128] {
                let first = partition_of(key, partitions);
                let second = partition_of(key, partitions);
                assert_eq!(first, second, "routing must be deterministic");
                assert!(
                    first < partitions,
                    "partition {first} out of range for P={partitions}"
                );
            }
        }
    }

    /// Worker ranges are contiguous, disjoint, cover `0..partitions` exactly
    /// once, and agree with `owner_of`.
    #[test]
    fn worker_ranges_cover_every_partition_exactly_once() {
        for workers in [1usize, 2, 3, 4, 7, 16, 64, 100, 300] {
            let layout = PartitionLayout::new(workers);
            let partitions = layout.partitions();
            let mut owner = vec![0usize; partitions];
            let mut previous_end = 0usize;
            for worker in 0..layout.workers() {
                let range = layout.worker_range(worker);
                assert_eq!(
                    range.start, previous_end,
                    "worker ranges must be contiguous (workers={workers})"
                );
                previous_end = range.end;
                for partition in range {
                    owner[partition] += 1;
                }
            }
            assert_eq!(
                previous_end, partitions,
                "ranges must cover every partition (workers={workers})"
            );
            for (partition, seen) in owner.iter().enumerate() {
                assert_eq!(
                    *seen, 1,
                    "partition {partition} must have exactly one owner (workers={workers})"
                );
                let expected_owner = layout.owner_of(partition);
                assert!(
                    layout.worker_range(expected_owner).contains(&partition),
                    "owner_of must agree with worker_range (workers={workers}, partition={partition})"
                );
            }
        }
    }

    /// The partition count formula clamps to `[64, 256]` and treats zero
    /// workers as one.
    #[test]
    fn partition_layout_clamps_to_documented_bounds() {
        assert_eq!(PartitionLayout::new(0).workers(), 1);
        assert_eq!(PartitionLayout::new(0).partitions(), 64);
        assert_eq!(PartitionLayout::new(1).partitions(), 64);
        assert_eq!(PartitionLayout::new(16).partitions(), 64);
        assert_eq!(PartitionLayout::new(100).partitions(), 100);
        assert_eq!(PartitionLayout::new(256).partitions(), 256);
        assert_eq!(PartitionLayout::new(1_000).partitions(), 256);
        assert_eq!(PartitionLayout::new(1_000).workers(), 1_000);
    }
}
