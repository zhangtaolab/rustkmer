//! The shared counting engine (Phase 7).
//!
//! **ENGINE-01 tracer slice.** One counting entry point for every surface:
//! the caller thread reads/decompresses/parses records, calls the ONE
//! [`for_each_window`] extractor, and routes each emitted key through
//! [`partition_of`] into a disjoint hash-range [`LocalKmerCounts`] table.
//! Because each key has exactly one partition, no shared table, lock, or
//! per-window atomic is touched while counting.
//!
//! This plan implements the **sequential path only**: the caller increments
//! directly into the partition tables, so `threads == 1` remains a true
//! single-thread measurement and spawns no worker thread. The persistent
//! producer/worker pipeline that consumes the same layout lands in 07-02; the
//! `threads` field is used here only to size [`PartitionLayout`].
//!
//! # Exactness contract
//!
//! - Per-key counts reuse [`LocalKmerCounts::increment`], so the verbatim
//!   `K-mer count overflow reached maximum value <max>` behavior is inherited,
//!   never reimplemented.
//! - Aggregate totals/uniques are **new summation sites** and use
//!   `checked_add`; overflow fails loud with the named verbatim messages
//!   instead of wrapping or saturating.
//! - The result feeds the frozen sorted `.rkdb` writer unchanged, so the
//!   on-disk bytes are identical across thread counts.
//!
//! No printing, no `unwrap`, no new dependencies.

use std::path::Path;

use crate::error::{KmerError, ProcessingError, ProcessingResult};
use crate::hash::filtering::{CountFilter, FilteringResult};
use crate::hash::local::LocalKmerCounts;
use crate::hash::table::KmerCounter;
use crate::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
use crate::kmer::extract::{for_each_window, WindowError, WindowSummary};

use super::partition::{partition_of, PartitionLayout};

/// Default encoded-key batch size handed to a worker (07-02).
pub const DEFAULT_KEYS_PER_BATCH: usize = 4096;

/// Default bounded-queue depth per worker (07-02).
pub const DEFAULT_QUEUE_BATCHES: usize = 8;

/// Default records per skip warning; preserves the legacy 4096-record chunk
/// warning frequency.
pub const DEFAULT_RECORDS_PER_WARNING_BATCH: usize = 4096;

/// Verbatim aggregate-total overflow message (new summation site).
const TOTAL_OVERFLOW_MESSAGE: &str = "Total k-mer count overflow during local reduction";

/// Verbatim aggregate-unique overflow message (new summation site).
const UNIQUE_OVERFLOW_MESSAGE: &str = "Unique k-mer count overflow during local reduction";

/// Skipped-window aggregate overflow message (new summation site).
const SKIPPED_OVERFLOW_MESSAGE: &str = "Skipped window count overflow during local reduction";

/// Sum u64 values with checked arithmetic, failing loud with `message`.
///
/// Every aggregate in the engine (per-file statistics, `flush`, `finish`)
/// goes through this helper: a new summation site must never wrap or
/// saturate.
///
/// # Arguments
/// * `values` - The per-partition `u64` inputs
/// * `message` - Verbatim fail-loud error text
///
/// # Returns
/// The exact sum.
///
/// # Errors
/// Returns `ProcessingError::new(message)` when the running sum would exceed
/// `u64::MAX`.
fn checked_sum<I>(values: I, message: &str) -> ProcessingResult<u64>
where
    I: IntoIterator<Item = u64>,
{
    let mut sum: u64 = 0;
    for value in values {
        sum = sum
            .checked_add(value)
            .ok_or_else(|| ProcessingError::new(message))?;
    }
    Ok(sum)
}

/// Engine construction parameters.
#[derive(Debug, Clone)]
pub struct EngineConfig {
    /// K-mer length (`1..=64`, validated by [`CountEngine::new`]).
    pub k: usize,
    /// Canonical mode (min of forward and reverse complement).
    pub canonical: bool,
    /// Resolved worker count; `1` selects the sequential path.
    pub threads: usize,
    /// Total pre-allocation hint (`--size`), divided across partitions.
    pub initial_capacity: usize,
    /// Encoded keys per batch (used by the 07-02 worker pipeline).
    pub keys_per_batch: usize,
    /// Bounded queue depth per worker (used by the 07-02 worker pipeline).
    pub queue_batches: usize,
    /// Records per skip-warning batch (preserves the legacy chunk wording).
    pub records_per_warning_batch: usize,
}

impl EngineConfig {
    /// Build a config with the documented defaults (4096 keys/batch, 8 queue
    /// batches, 4096 records/warning batch).
    ///
    /// # Arguments
    /// * `k` - K-mer length (`1..=64`)
    /// * `canonical` - Canonical mode
    /// * `threads` - Resolved worker count (`1` = sequential)
    /// * `initial_capacity` - Total pre-allocation hint
    ///
    /// # Returns
    /// A config with the remaining fields defaulted.
    pub fn new(k: usize, canonical: bool, threads: usize, initial_capacity: usize) -> Self {
        Self {
            k,
            canonical,
            threads,
            initial_capacity,
            keys_per_batch: DEFAULT_KEYS_PER_BATCH,
            queue_batches: DEFAULT_QUEUE_BATCHES,
            records_per_warning_batch: DEFAULT_RECORDS_PER_WARNING_BATCH,
        }
    }
}

/// Input sequence format understood by [`CountEngine::count_file`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SequenceKind {
    /// FASTA records.
    Fasta,
    /// FASTQ records.
    Fastq,
}

/// Exact counters accumulated so far.
///
/// `total_kmers` is the **sum of counts** (IN-03), not a record count, and
/// `unique_kmers` is the number of distinct keys. `skipped_windows` counts
/// length-`k` windows containing a non-ACGT byte (they never advance the
/// total).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct EngineStats {
    /// Sum of all successful per-key counts.
    pub total_kmers: u64,
    /// Number of distinct keys.
    pub unique_kmers: u64,
    /// Windows skipped for containing a non-ACGT byte.
    pub skipped_windows: u64,
}

/// Per-file result: cumulative statistics plus the warning batches.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FileStats {
    /// Cumulative statistics after this file.
    pub stats: EngineStats,
    /// One entry per 4096-record batch that contained skipped windows; the
    /// CLI prints one warning per entry with the legacy wording.
    pub skipped_batches: Vec<u64>,
}

/// Exact counting result: the disjoint partition tables plus their layout.
///
/// Every key belongs to exactly one partition, so `for_each_count` yields each
/// `(key, count)` exactly once and the sorted `.rkdb` writer produces the same
/// bytes for any thread count.
#[derive(Debug)]
pub struct CountResult {
    /// Disjoint hash-range partition tables (empty tables included).
    tables: Vec<LocalKmerCounts>,
    /// Layout the tables were routed with.
    layout: PartitionLayout,
    /// K-mer length.
    k: usize,
    /// Canonical mode.
    canonical: bool,
    /// Statistics computed when the engine finished.
    stats: EngineStats,
}

impl CountResult {
    /// K-mer length this result was counted with.
    pub fn kmer_length(&self) -> usize {
        self.k
    }

    /// Whether the result is canonicalized.
    pub fn canonical_mode(&self) -> bool {
        self.canonical
    }

    /// Exact cumulative statistics.
    pub fn stats(&self) -> EngineStats {
        self.stats
    }

    /// Look up one encoded k-mer in its owning partition.
    ///
    /// # Arguments
    /// * `kmer` - Encoded (and canonicalized, when applicable) k-mer
    ///
    /// # Returns
    /// `Some(count)` when the key was observed, `None` otherwise.
    pub fn get_count(&self, kmer: u128) -> Option<u32> {
        let partition = partition_of(kmer, self.layout.partitions());
        self.tables
            .get(partition)
            .and_then(|table| table.get_count(kmer))
    }

    /// Visit every `(key, count)` pair exactly once.
    pub fn for_each_count<F>(&self, mut visit: F)
    where
        F: FnMut(u128, u32),
    {
        for table in &self.tables {
            for (kmer, count) in table.iter() {
                visit(kmer, count);
            }
        }
    }

    /// Collect every `(key, count)` pair.
    pub fn into_pairs(self) -> Vec<(u128, u32)> {
        self.collect_pairs()
    }

    /// Collect every `(key, count)` pair through a borrow.
    fn collect_pairs(&self) -> Vec<(u128, u32)> {
        let capacity: usize = self.tables.iter().map(LocalKmerCounts::key_count).sum();
        let mut pairs = Vec::with_capacity(capacity);
        for table in &self.tables {
            pairs.extend(table.iter());
        }
        pairs
    }

    /// Collect the pairs that pass `filter`, with the same semantics as
    /// [`KmerCounter::get_filtered_kmers`].
    ///
    /// # Arguments
    /// * `filter` - Optional count filter (`None` keeps every pair)
    ///
    /// # Returns
    /// The kept `(key, count)` pairs.
    pub fn filtered_pairs(&self, filter: &Option<CountFilter>) -> Vec<(u128, u32)> {
        let mut pairs = self.collect_pairs();
        if let Some(filter) = filter {
            pairs.retain(|(_, count)| filter.passes(*count as u64));
        }
        pairs
    }

    /// Filtering statistics with the same semantics as
    /// [`KmerCounter::get_filtering_stats`], including the WR-01 denominator
    /// (`total_before` = successfully counted k-mers).
    ///
    /// # Arguments
    /// * `filter` - Optional count filter (`None` reports everything kept)
    ///
    /// # Returns
    /// A [`FilteringResult`] built from the exact engine statistics.
    pub fn filtering_stats(&self, filter: &Option<CountFilter>) -> FilteringResult {
        let unique_before = self.stats.unique_kmers;
        match filter {
            Some(filter) => {
                let kept_after = self
                    .tables
                    .iter()
                    .flat_map(|table| table.iter())
                    .filter(|(_, count)| filter.passes(*count as u64))
                    .count() as u64;
                FilteringResult::new(
                    self.stats.total_kmers,
                    unique_before,
                    kept_after,
                    filter.clone(),
                )
            }
            None => FilteringResult::new(
                self.stats.total_kmers,
                unique_before,
                unique_before,
                CountFilter::default(),
            ),
        }
    }

    /// Merge every partition table into an existing [`KmerCounter`].
    ///
    /// This is the Phase 9 PyO3 bridge: it reuses the already-tested
    /// [`KmerCounter::merge_local_counts`] path (checked per-key `u32` sums,
    /// atomic compare-exchange total publication), so the public counter API
    /// and its overflow contract are preserved rather than duplicated.
    ///
    /// # Arguments
    /// * `counter` - Destination counter with matching k and canonical mode
    ///
    /// # Returns
    /// `Ok(())` when every table merged.
    ///
    /// # Errors
    /// Propagates the first per-key/aggregate overflow (verbatim message) from
    /// `merge_local_counts`; the counter is poisoned exactly as that method
    /// documents.
    pub fn merge_into(&self, counter: &KmerCounter) -> ProcessingResult<()> {
        use rayon::prelude::*;
        self.tables
            .par_iter()
            .try_for_each(|table| counter.merge_local_counts(table))
    }
}

/// Sequential counting engine over disjoint partition tables.
///
/// See the module docs for the exactness contract. The engine accumulates
/// across `count_file` calls, so multi-file totals are the running sum of every
/// file; `finish` consumes it into a [`CountResult`].
#[derive(Debug)]
pub struct CountEngine {
    /// Construction parameters.
    config: EngineConfig,
    /// Partition-to-worker layout (`P = min(256, max(64, threads))`).
    layout: PartitionLayout,
    /// One table per partition; each key has exactly one owner.
    tables: Vec<LocalKmerCounts>,
    /// Last cumulative statistics published by `count_file`/`flush`.
    last_stats: EngineStats,
    /// Cumulative skipped windows across files.
    skipped_windows: u64,
}

impl CountEngine {
    /// Build a sequential engine, rejecting k outside `1..=64`.
    ///
    /// # Arguments
    /// * `config` - Engine parameters (see [`EngineConfig`])
    ///
    /// # Returns
    /// An engine with one empty partition table per [`PartitionLayout`]
    /// partition.
    ///
    /// # Errors
    /// Returns [`KmerError::InvalidKmerSize`] when `config.k` is zero or above
    /// 64.
    pub fn new(config: EngineConfig) -> ProcessingResult<Self> {
        if !(1..=64).contains(&config.k) {
            return Err(KmerError::InvalidKmerSize(config.k as u32).into());
        }

        let layout = PartitionLayout::new(config.threads);
        let per_partition_capacity = (config.initial_capacity / layout.partitions()).max(1);
        let tables = (0..layout.partitions())
            .map(|_| {
                LocalKmerCounts::with_capacity(config.k, config.canonical, per_partition_capacity)
            })
            .collect();

        Ok(Self {
            config,
            layout,
            tables,
            last_stats: EngineStats::default(),
            skipped_windows: 0,
        })
    }

    /// Count every record of one file through the shared extractor.
    ///
    /// The file is opened through [`DefaultCompressedFileReader`] so
    /// gzip/bzip2/xz (including multi-member gzip) and plain inputs share one
    /// decompression path. Each record calls [`for_each_window`] exactly once
    /// and routes every emitted key into its owning partition.
    ///
    /// # Arguments
    /// * `path` - Input sequence file
    /// * `kind` - Record format (`SequenceKind::Fasta` / `SequenceKind::Fastq`)
    ///
    /// # Returns
    /// Cumulative [`FileStats`] after this file, plus the one-entry-per-skip
    /// warning batches.
    ///
    /// # Errors
    /// Propagates open/read errors with the file path, and any per-key
    /// overflow from [`LocalKmerCounts::increment`] (verbatim message).
    pub fn count_file(&mut self, path: &Path, kind: SequenceKind) -> ProcessingResult<FileStats> {
        let (reader, _compression) = DefaultCompressedFileReader::open_compressed(path)
            .map_err(|error| {
                ProcessingError::with_context(
                    format!("Failed to open input file for counting: {}", path.display()),
                    error,
                )
            })?;

        let mut warning_batch = SkipWarningBatch::default();
        let mut file_skipped: u64 = 0;

        match kind {
            SequenceKind::Fasta => {
                let reader = bio::io::fasta::Reader::new(reader);
                for record_result in reader.records() {
                    let record = record_result.map_err(|error| {
                        ProcessingError::with_context(
                            format!("Error reading FASTA record from file: {}", path.display()),
                            error,
                        )
                    })?;
                    let summary = self.count_sequence(record.seq())?;
                    file_skipped = file_skipped
                        .checked_add(summary.skipped)
                        .ok_or_else(|| ProcessingError::new(SKIPPED_OVERFLOW_MESSAGE))?;
                    warning_batch.record(summary.skipped, self.config.records_per_warning_batch)?;
                }
            }
            SequenceKind::Fastq => {
                let reader = bio::io::fastq::Reader::new(reader);
                for record_result in reader.records() {
                    let record = record_result.map_err(|error| {
                        ProcessingError::with_context(
                            format!("Error reading FASTQ record from file: {}", path.display()),
                            error,
                        )
                    })?;
                    let summary = self.count_sequence(record.seq())?;
                    file_skipped = file_skipped
                        .checked_add(summary.skipped)
                        .ok_or_else(|| ProcessingError::new(SKIPPED_OVERFLOW_MESSAGE))?;
                    warning_batch.record(summary.skipped, self.config.records_per_warning_batch)?;
                }
            }
        }

        self.skipped_windows = self
            .skipped_windows
            .checked_add(file_skipped)
            .ok_or_else(|| ProcessingError::new(SKIPPED_OVERFLOW_MESSAGE))?;

        let stats = self.checked_stats()?;
        self.last_stats = stats;
        Ok(FileStats {
            stats,
            skipped_batches: warning_batch.finish(),
        })
    }

    /// Publish cumulative statistics at a file boundary.
    ///
    /// # Returns
    /// The cumulative [`EngineStats`] across every file counted so far.
    ///
    /// # Errors
    /// Returns the verbatim aggregate-total/-unique overflow error when a sum
    /// would exceed `u64::MAX`.
    pub fn flush(&mut self) -> ProcessingResult<EngineStats> {
        let stats = self.checked_stats()?;
        self.last_stats = stats;
        Ok(stats)
    }

    /// Statistics published by the last `count_file`/`flush`.
    pub fn stats(&self) -> EngineStats {
        self.last_stats
    }

    /// Consume the engine into an exact [`CountResult`].
    ///
    /// # Returns
    /// The partition tables, their layout, and the checked cumulative
    /// statistics.
    ///
    /// # Errors
    /// Returns the verbatim aggregate overflow error when a sum would exceed
    /// `u64::MAX`.
    pub fn finish(mut self) -> ProcessingResult<CountResult> {
        let stats = self.checked_stats()?;
        self.last_stats = stats;
        Ok(CountResult {
            tables: self.tables,
            layout: self.layout,
            k: self.config.k,
            canonical: self.config.canonical,
            stats,
        })
    }

    /// Count one sequence through the shared extractor into the partitions.
    fn count_sequence(&mut self, seq: &[u8]) -> ProcessingResult<WindowSummary> {
        let k = self.config.k;
        let canonical = self.config.canonical;
        let partitions = self.layout.partitions();
        let tables = &mut self.tables;

        for_each_window(seq, k, canonical, |value| {
            let partition = partition_of(value, partitions);
            match tables.get_mut(partition) {
                Some(table) => table.increment(value),
                // Unreachable while `partition_of` is in range; fail loud
                // instead of panicking (release is `panic = "abort"`).
                None => Err(ProcessingError::new(format!(
                    "Partition {} is out of range for {} tables",
                    partition, partitions
                ))),
            }
        })
        .map_err(|error| match error {
            WindowError::InvalidK(invalid) => {
                ProcessingError::from(KmerError::InvalidKmerSize(invalid as u32))
            }
            WindowError::Emit(error) => error,
        })
    }

    /// Sum per-partition totals/uniques with checked arithmetic.
    fn checked_stats(&self) -> ProcessingResult<EngineStats> {
        let total_kmers = checked_sum(
            self.tables.iter().map(LocalKmerCounts::total_kmers),
            TOTAL_OVERFLOW_MESSAGE,
        )?;
        let unique_kmers = checked_sum(
            self.tables.iter().map(LocalKmerCounts::unique_kmers),
            UNIQUE_OVERFLOW_MESSAGE,
        )?;
        Ok(EngineStats {
            total_kmers,
            unique_kmers,
            skipped_windows: self.skipped_windows,
        })
    }
}

/// One file's skip-warning batches (one warning per 4096-record batch).
#[derive(Debug, Default)]
struct SkipWarningBatch {
    /// Records accumulated in the current batch.
    records: usize,
    /// Skipped windows accumulated in the current batch.
    skips: u64,
    /// Non-zero skip counts of completed batches.
    batches: Vec<u64>,
}

impl SkipWarningBatch {
    /// Fold one record's skipped-window count into the current batch, closing
    /// the batch at `records_per_batch`.
    fn record(&mut self, skipped: u64, records_per_batch: usize) -> ProcessingResult<()> {
        self.skips = self
            .skips
            .checked_add(skipped)
            .ok_or_else(|| ProcessingError::new(SKIPPED_OVERFLOW_MESSAGE))?;
        self.records += 1;
        if self.records >= records_per_batch.max(1) {
            self.close();
        }
        Ok(())
    }

    /// Close the current batch, retaining it only when it has skips.
    fn close(&mut self) {
        if self.records > 0 && self.skips > 0 {
            self.batches.push(self.skips);
        }
        self.records = 0;
        self.skips = 0;
    }

    /// Close the trailing partial batch and return every warning count.
    fn finish(mut self) -> Vec<u64> {
        self.close();
        self.batches
    }
}
