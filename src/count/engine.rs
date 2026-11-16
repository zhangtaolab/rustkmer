//! The shared counting engine (Phase 7).
//!
//! **ENGINE-01.** One counting entry point for every surface: the caller
//! thread reads/decompresses/parses records, calls the ONE [`for_each_window`]
//! extractor, routes each emitted key through [`partition_of`], and accumulates
//! into disjoint hash-range [`LocalKmerCounts`] tables. Because each key has
//! exactly one partition, no shared table, lock, or per-window atomic is
//! touched while counting.
//!
//! Two execution shapes:
//!
//! - `threads == 1`: **sequential path** — the caller increments directly into
//!   the partition tables. No worker thread and no queue, so the t1 baseline is
//!   an honest single-thread measurement.
//! - `threads > 1`: **persistent worker pipeline** — exactly N named
//!   (`rustkmer-count-{i}`) OS threads, each owning the contiguous
//!   [`PartitionLayout::worker_range`] of partition tables and nothing else.
//!   Every worker has its own bounded `sync_channel` batch queue and its own
//!   acknowledgement channel. The producer keeps parsing while the workers
//!   count; the only coupling is bounded-queue backpressure. No worker ever
//!   runs on a rayon task (a blocking `recv` there could starve the pool), and
//!   there is no per-chunk fork-join barrier.
//!
//! # Flush protocol
//!
//! A file boundary flushes every non-empty routing buffer, sends one
//! `CountBatch::Flush { token }` to every worker, and collects one
//! `WorkerStat::Flush` acknowledgement per worker. Because a worker's batch
//! channel is FIFO, each acknowledgement is emitted only after every
//! previously sent batch for that worker has been counted; the verified
//! token plus checked `u64` sums produce the cumulative [`FileStats`].
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
//! # Error and shutdown contract
//!
//! A failed `send`, a failed acknowledgement `recv`, or a worker-returned error
//! stops production, drops every sender, joins every worker, and returns the
//! first worker error when one exists (otherwise the channel error). `finish`
//! joins in layout order and concatenates the workers' table vectors;
//! [`Drop`] joins any survivors so no worker thread can leak. Workers never
//! print, never call rayon, never `unwrap`, and return `ProcessingResult`.
//!
//! No new dependencies.

use std::ops::Range;
use std::path::Path;
use std::sync::mpsc::{sync_channel, Receiver, SyncSender};
use std::thread::JoinHandle;
#[cfg(feature = "profiling")]
use std::time::Instant;

use crate::error::{KmerError, ProcessingError, ProcessingResult};
use crate::hash::filtering::{CountFilter, FilteringResult};
use crate::hash::local::LocalKmerCounts;
use crate::hash::table::KmerCounter;
use crate::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
use crate::kmer::encoding::MAX_KMER_SIZE_IN_U64;
use crate::kmer::extract::{for_each_window, WindowError, WindowSummary};

use super::batch::{CountBatch, WorkerStat};
use super::partition::{partition_of, PartitionLayout};

/// Default encoded-key batch size handed to a worker.
pub const DEFAULT_KEYS_PER_BATCH: usize = 4096;

/// Default bounded-queue depth per worker.
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

/// Map an extractor error into the engine's error type.
fn map_window_error(error: WindowError<ProcessingError>) -> ProcessingError {
    match error {
        WindowError::InvalidK(invalid) => KmerError::InvalidKmerSize(invalid as u32).into(),
        WindowError::Emit(error) => error,
    }
}

/// Sum the per-partition totals/uniques with checked arithmetic.
fn checked_stats_for(
    tables: &[LocalKmerCounts],
    skipped_windows: u64,
) -> ProcessingResult<EngineStats> {
    let total_kmers = checked_sum(
        tables.iter().map(LocalKmerCounts::total_kmers),
        TOTAL_OVERFLOW_MESSAGE,
    )?;
    let unique_kmers = checked_sum(
        tables.iter().map(LocalKmerCounts::unique_kmers),
        UNIQUE_OVERFLOW_MESSAGE,
    )?;
    Ok(EngineStats {
        total_kmers,
        unique_kmers,
        skipped_windows,
    })
}

/// Sum the flush acknowledgements with checked arithmetic.
///
/// This is a new summation site (one ack per worker), so it must never wrap or
/// saturate: a seeded `u64::MAX` ack pair fails loud with the verbatim
/// aggregate messages.
fn reduce_worker_stats(stats: &[WorkerStat]) -> ProcessingResult<(u64, u64)> {
    let mut total: u64 = 0;
    let mut unique: u64 = 0;
    for stat in stats {
        let WorkerStat::Flush {
            total: worker_total,
            unique: worker_unique,
            ..
        } = stat;
        total = total
            .checked_add(*worker_total)
            .ok_or_else(|| ProcessingError::new(TOTAL_OVERFLOW_MESSAGE))?;
        unique = unique
            .checked_add(*worker_unique)
            .ok_or_else(|| ProcessingError::new(UNIQUE_OVERFLOW_MESSAGE))?;
    }
    Ok((total, unique))
}

/// Per-worker timing diagnostics, recorded only when this crate is built with
/// the `profiling` feature.
///
/// The values exist only after the workers are joined (`finish`), because a
/// worker reports them with its tables. Default builds contain none of the
/// timing calls and do not expose this type.
#[cfg(feature = "profiling")]
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct WorkerDiagnostics {
    /// Key batches processed by this worker (`Flush` barriers excluded).
    pub batches: u64,
    /// Accumulated wall time of this worker's increment loops.
    pub busy_nanos: u64,
}

/// Engine timing diagnostics, recorded only when this crate is built with the
/// `profiling` feature.
///
/// `wall_nanos` covers the engine's lifetime (construction through `finish`).
/// `producer_nanos` covers the caller-thread producer work (file open, record
/// parsing, extraction, routing, sends, and flush waits). On the sequential
/// path `workers` is empty and both times cover the whole run.
#[cfg(feature = "profiling")]
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct EngineDiagnostics {
    /// Wall time across the engine's lifetime.
    pub wall_nanos: u64,
    /// Time the caller thread spent producing and waiting on flush barriers.
    pub producer_nanos: u64,
    /// One entry per worker, in worker order.
    pub workers: Vec<WorkerDiagnostics>,
}

/// Worker return value: tables plus per-worker diagnostics when profiling.
#[cfg(feature = "profiling")]
type WorkerReturn = (Vec<LocalKmerCounts>, WorkerDiagnostics);

/// Worker return value: tables only in default builds (the 07-02 signature).
#[cfg(not(feature = "profiling"))]
type WorkerReturn = Vec<LocalKmerCounts>;

/// Join result: tables plus per-worker diagnostics when profiling.
#[cfg(feature = "profiling")]
type JoinReturn = (Vec<LocalKmerCounts>, Vec<WorkerDiagnostics>);

/// Join result: tables only in default builds (the 07-02 signature).
#[cfg(not(feature = "profiling"))]
type JoinReturn = Vec<LocalKmerCounts>;

/// Convert an elapsed `Instant` into `u64` nanoseconds, saturating at the
/// representable maximum instead of panicking.
#[cfg(feature = "profiling")]
fn elapsed_nanos(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX)
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
    /// Encoded keys per batch before the producer hands one to a worker.
    pub keys_per_batch: usize,
    /// Bounded queue depth per worker (batches).
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
    /// Feature-gated timing captured at `finish`; absent from default builds.
    #[cfg(feature = "profiling")]
    diagnostics: Option<EngineDiagnostics>,
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

    /// Producer/worker timing captured when the engine finished.
    ///
    /// Present only when this crate is built with the `profiling` feature; the
    /// method does not exist in default builds. The diagnostics are read from
    /// the finished result because per-worker values are produced when the
    /// workers are joined.
    ///
    /// # Returns
    /// `Some(diagnostics)` for results produced by [`CountEngine::finish`];
    /// `None` for hand-constructed results (tests).
    #[cfg(feature = "profiling")]
    pub fn diagnostics(&self) -> Option<EngineDiagnostics> {
        self.diagnostics.clone()
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

    /// Collect every `(key, count)` pair by consuming the result.
    ///
    /// # Arguments
    /// * None
    ///
    /// # Returns
    /// One pair buffer holding every partition's entries exactly once.
    ///
    /// # Errors
    /// This method is infallible: pair collection has no error path.
    pub fn into_pairs(self) -> Vec<(u128, u32)> {
        self.into_filtered_pairs(&None)
    }

    /// Consuming filtered collection: drain every partition table into ONE
    /// pair buffer, then retain the pairs that pass `filter`.
    ///
    /// Each partition table is moved out of the result and dropped as it is
    /// drained, so a drained table's allocation is released before the next
    /// one is drained — at no instant does a second full copy of the entries
    /// exist beside the pair buffer. Filter semantics are identical to
    /// [`Self::filtered_pairs`] / [`KmerCounter::get_filtered_kmers`].
    ///
    /// # Arguments
    /// * `filter` - Optional count filter (`None` keeps every pair)
    ///
    /// # Returns
    /// The kept `(key, count)` pairs.
    ///
    /// # Errors
    /// This method is infallible: pair collection and filtering have no
    /// error path.
    pub fn into_filtered_pairs(self, filter: &Option<CountFilter>) -> Vec<(u128, u32)> {
        let capacity: usize = self.tables.iter().map(LocalKmerCounts::key_count).sum();
        let mut pairs = Vec::with_capacity(capacity);
        // `CountResult` has no `Drop` impl, so the table vector can be moved
        // out; each table is drained and dropped at the end of its iteration.
        for table in self.tables {
            table.into_pairs_into(&mut pairs);
        }
        if let Some(filter) = filter {
            pairs.retain(|(_, count)| filter.passes(*count as u64));
        }
        pairs
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

/// Sequential accumulation state: the caller thread owns every table.
#[derive(Debug)]
struct SequentialState {
    /// One table per partition.
    tables: Vec<LocalKmerCounts>,
}

/// Persistent-worker pipeline state.
#[derive(Debug)]
struct ParallelState {
    /// One bounded batch queue sender per worker (index = worker).
    senders: Vec<SyncSender<CountBatch>>,
    /// One acknowledgement receiver per worker (index = worker).
    acknowledgements: Vec<Receiver<WorkerStat>>,
    /// Join handles in worker order; joined exactly once.
    handles: Vec<JoinHandle<ProcessingResult<WorkerReturn>>>,
    /// Per-partition producer-side routing buffers.
    buffers: RoutingBuffers,
    /// Whether the workers have been joined (shutdown is idempotent).
    joined: bool,
}

/// Producer-side routing buffers, one per partition, width-matched to k.
#[derive(Debug)]
enum RoutingBuffers {
    /// `k <= 32`: `u64` keys per partition.
    Dense(Vec<Vec<u64>>),
    /// `k 33..=64`: `u128` keys per partition.
    Wide(Vec<Vec<u128>>),
}

/// Engine execution shape.
#[derive(Debug)]
enum EngineMode {
    /// Caller-thread counting (no queues, no worker threads).
    Sequential(SequentialState),
    /// One producer plus N persistent OS workers.
    Parallel(ParallelState),
}

/// Shared counting engine over disjoint partition tables.
///
/// See the module docs for the exactness, flush, and shutdown contracts. The
/// engine accumulates across `count_file` calls, so multi-file totals are the
/// running sum of every file; `finish` consumes it into a [`CountResult`].
#[derive(Debug)]
pub struct CountEngine {
    /// Construction parameters.
    config: EngineConfig,
    /// Partition-to-worker layout (`P = min(256, max(64, threads))`).
    layout: PartitionLayout,
    /// Sequential tables or the persistent worker pipeline.
    mode: EngineMode,
    /// Last cumulative statistics published by `count_file`/`flush`.
    last_stats: EngineStats,
    /// Cumulative skipped windows across files (producer-side, exact).
    skipped_windows: u64,
    /// Next file-boundary flush token.
    next_token: u64,
    /// Engine construction instant (profiling only).
    #[cfg(feature = "profiling")]
    started: Instant,
    /// Accumulated caller-thread producer time (profiling only).
    #[cfg(feature = "profiling")]
    producer_nanos: u64,
}

impl CountEngine {
    /// Build an engine, rejecting k outside `1..=64`.
    ///
    /// `threads == 1` builds the sequential path; `threads > 1` spawns exactly
    /// `threads` named persistent workers, each owning its contiguous partition
    /// range and its own bounded batch/ack channels.
    ///
    /// # Arguments
    /// * `config` - Engine parameters (see [`EngineConfig`])
    ///
    /// # Returns
    /// An engine with one empty partition table per [`PartitionLayout`]
    /// partition (distributed across the workers on the parallel path).
    ///
    /// # Errors
    /// Returns [`KmerError::InvalidKmerSize`] when `config.k` is zero or above
    /// 64, and a `ProcessingError` when a worker thread cannot be spawned (any
    /// already-spawned workers are joined first).
    pub fn new(config: EngineConfig) -> ProcessingResult<Self> {
        if !(1..=64).contains(&config.k) {
            return Err(KmerError::InvalidKmerSize(config.k as u32).into());
        }

        let layout = PartitionLayout::new(config.threads);
        let per_partition_capacity = (config.initial_capacity / layout.partitions()).max(1);

        if config.threads <= 1 {
            let tables = (0..layout.partitions())
                .map(|_| {
                    LocalKmerCounts::with_capacity(
                        config.k,
                        config.canonical,
                        per_partition_capacity,
                    )
                })
                .collect();
            return Ok(Self {
                config,
                layout,
                mode: EngineMode::Sequential(SequentialState { tables }),
                last_stats: EngineStats::default(),
                skipped_windows: 0,
                next_token: 0,
                #[cfg(feature = "profiling")]
                started: Instant::now(),
                #[cfg(feature = "profiling")]
                producer_nanos: 0,
            });
        }

        let tables = (0..layout.partitions())
            .map(|_| {
                LocalKmerCounts::with_capacity(config.k, config.canonical, per_partition_capacity)
            })
            .collect();
        Self::spawn_parallel(config, layout, tables)
    }

    /// Number of threads actually running the pipeline.
    ///
    /// Returns `0` on the sequential path (the caller thread does the work and
    /// spawns no worker) and the requested worker count on the parallel path.
    pub fn worker_count(&self) -> usize {
        match &self.mode {
            EngineMode::Sequential(_) => 0,
            EngineMode::Parallel(_) => self.layout.workers(),
        }
    }

    /// Spawn the persistent workers and build the parallel engine.
    ///
    /// `partition_tables` must hold exactly one table per layout partition in
    /// partition order; worker `i` receives the slice for
    /// `worker_range(i)`. If a spawn fails, the senders are dropped so every
    /// already-spawned worker exits, and those workers are joined before the
    /// error is returned.
    fn spawn_parallel(
        config: EngineConfig,
        layout: PartitionLayout,
        partition_tables: Vec<LocalKmerCounts>,
    ) -> ProcessingResult<Self> {
        let workers = layout.workers();
        if partition_tables.len() != layout.partitions() {
            return Err(ProcessingError::new(format!(
                "Counting engine partition table count {} does not match layout partitions {}",
                partition_tables.len(),
                layout.partitions()
            )));
        }

        let buffers = if config.k <= MAX_KMER_SIZE_IN_U64 {
            RoutingBuffers::Dense(
                (0..layout.partitions())
                    .map(|_| Vec::with_capacity(config.keys_per_batch.max(1)))
                    .collect(),
            )
        } else {
            RoutingBuffers::Wide(
                (0..layout.partitions())
                    .map(|_| Vec::with_capacity(config.keys_per_batch.max(1)))
                    .collect(),
            )
        };

        let mut remaining = partition_tables.into_iter();
        let mut senders: Vec<SyncSender<CountBatch>> = Vec::with_capacity(workers);
        let mut acknowledgements: Vec<Receiver<WorkerStat>> = Vec::with_capacity(workers);
        let mut handles: Vec<JoinHandle<ProcessingResult<WorkerReturn>>> =
            Vec::with_capacity(workers);

        for worker_index in 0..workers {
            let range = layout.worker_range(worker_index);
            let owned = range.end - range.start;
            let tables: Vec<LocalKmerCounts> = remaining.by_ref().take(owned).collect();
            if tables.len() != owned {
                senders.clear();
                for handle in handles {
                    let _ = handle.join();
                }
                return Err(ProcessingError::new(format!(
                    "Counting engine has no partition tables for worker {}",
                    worker_index
                )));
            }

            let (batch_sender, batch_receiver) = sync_channel::<CountBatch>(config.queue_batches);
            let (ack_sender, ack_receiver) = sync_channel::<WorkerStat>(1);
            let spawned = std::thread::Builder::new()
                .name(format!("rustkmer-count-{}", worker_index))
                .spawn(move || run_worker(worker_index, range, tables, batch_receiver, ack_sender));

            match spawned {
                Ok(handle) => {
                    senders.push(batch_sender);
                    acknowledgements.push(ack_receiver);
                    handles.push(handle);
                }
                Err(error) => {
                    // Dropping every sender disconnects the already-spawned
                    // workers; join them before returning so none leak.
                    senders.clear();
                    for handle in handles {
                        let _ = handle.join();
                    }
                    return Err(ProcessingError::new(format!(
                        "Failed to spawn counting worker {}: {}",
                        worker_index, error
                    )));
                }
            }
        }

        let leftover = remaining.count();
        if leftover != 0 {
            senders.clear();
            for handle in handles {
                let _ = handle.join();
            }
            return Err(ProcessingError::new(format!(
                "Counting engine layout left {} partition tables unowned",
                leftover
            )));
        }

        Ok(Self {
            config,
            layout,
            mode: EngineMode::Parallel(ParallelState {
                senders,
                acknowledgements,
                handles,
                buffers,
                joined: false,
            }),
            last_stats: EngineStats::default(),
            skipped_windows: 0,
            next_token: 0,
            #[cfg(feature = "profiling")]
            started: Instant::now(),
            #[cfg(feature = "profiling")]
            producer_nanos: 0,
        })
    }

    /// Count every record of one file through the shared extractor.
    ///
    /// The file is opened through [`DefaultCompressedFileReader`] so
    /// gzip/bzip2/xz (including multi-member gzip) and plain inputs share one
    /// decompression path. Each record calls [`for_each_window`] exactly once;
    /// on the parallel path every emitted key is routed to its owning partition
    /// and handed to that partition's worker in bounded batches. A file
    /// boundary flushes the routing buffers and takes one acknowledgement per
    /// worker.
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
    /// Propagates open/read errors with the file path, any per-key overflow
    /// from [`LocalKmerCounts::increment`] (verbatim message), and any
    /// worker/send/ack failure. Every failure joins all workers first.
    pub fn count_file(&mut self, path: &Path, kind: SequenceKind) -> ProcessingResult<FileStats> {
        let outcome = self.count_file_inner(path, kind);
        if outcome.is_err() {
            // Stop producing, drop every sender, and join every worker; no
            // error may leave a worker running behind a poisoned engine.
            let _ = self.join_workers();
        }
        outcome
    }

    /// Counting body shared by both execution shapes.
    fn count_file_inner(&mut self, path: &Path, kind: SequenceKind) -> ProcessingResult<FileStats> {
        #[cfg(feature = "profiling")]
        let producer_started = Instant::now();
        let (reader, _compression) =
            DefaultCompressedFileReader::open_compressed(path).map_err(|error| {
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

        // The producer section ends before the file-boundary flush, which
        // records its own wait in `flush_inner` (no double counting).
        #[cfg(feature = "profiling")]
        {
            self.producer_nanos = self
                .producer_nanos
                .saturating_add(elapsed_nanos(producer_started));
        }

        let stats = self.flush()?;
        Ok(FileStats {
            stats,
            skipped_batches: warning_batch.finish(),
        })
    }

    /// Publish cumulative statistics at a file boundary.
    ///
    /// On the parallel path this flushes the routing buffers and takes one
    /// acknowledgement per worker after every previously sent batch has been
    /// counted.
    ///
    /// # Returns
    /// The cumulative [`EngineStats`] across every file counted so far.
    ///
    /// # Errors
    /// Returns the verbatim aggregate overflow error when a sum would exceed
    /// `u64::MAX`, and any worker/send/ack failure. Every failure joins all
    /// workers first.
    pub fn flush(&mut self) -> ProcessingResult<EngineStats> {
        let outcome = self.flush_inner();
        if outcome.is_err() {
            let _ = self.join_workers();
        }
        outcome
    }

    /// Flush body shared by both execution shapes.
    fn flush_inner(&mut self) -> ProcessingResult<EngineStats> {
        #[cfg(feature = "profiling")]
        let flush_started = Instant::now();
        let outcome = match &mut self.mode {
            EngineMode::Sequential(state) => checked_stats_for(&state.tables, self.skipped_windows),
            EngineMode::Parallel(state) => {
                let token = self.next_token;
                self.next_token = self.next_token.wrapping_add(1);
                let layout = self.layout;
                let skipped_windows = self.skipped_windows;
                match state.flush_pipeline(token, layout, skipped_windows) {
                    Ok(stats) => Ok(stats),
                    Err(error) => {
                        // Prefer a worker's own error (e.g. the verbatim
                        // per-key overflow) over the channel symptom.
                        Err(self.worker_failure(error))
                    }
                }
            }
        };
        // A file-boundary flush is caller-thread work: buffered sends plus the
        // wait for every worker acknowledgement.
        #[cfg(feature = "profiling")]
        {
            self.producer_nanos = self
                .producer_nanos
                .saturating_add(elapsed_nanos(flush_started));
        }
        outcome
    }

    /// Statistics published by the last `count_file`/`flush`.
    pub fn stats(&self) -> EngineStats {
        self.last_stats
    }

    /// Consume the engine into an exact [`CountResult`].
    ///
    /// On the parallel path any residual buffered keys are flushed, every
    /// worker is joined, and the returned table vectors are concatenated in
    /// layout order (so the result is always in partition order).
    ///
    /// # Returns
    /// The partition tables, their layout, and the checked cumulative
    /// statistics.
    ///
    /// # Errors
    /// Returns the verbatim aggregate overflow error when a sum would exceed
    /// `u64::MAX`, or the first worker error.
    pub fn finish(mut self) -> ProcessingResult<CountResult> {
        #[cfg(feature = "profiling")]
        let mut worker_diagnostics: Vec<WorkerDiagnostics> = Vec::new();

        let (tables, stats) = match &mut self.mode {
            EngineMode::Sequential(state) => {
                let stats = checked_stats_for(&state.tables, self.skipped_windows)?;
                (std::mem::take(&mut state.tables), stats)
            }
            EngineMode::Parallel(_) => {
                // Flush residual buffers and take a final barrier so every
                // worker has consumed every batch before the join.
                self.flush()?;
                #[cfg(feature = "profiling")]
                {
                    let (joined_tables, diagnostics) = self.join_workers()?;
                    worker_diagnostics = diagnostics;
                    let stats = checked_stats_for(&joined_tables, self.skipped_windows)?;
                    (joined_tables, stats)
                }
                #[cfg(not(feature = "profiling"))]
                {
                    let joined_tables = self.join_workers()?;
                    let stats = checked_stats_for(&joined_tables, self.skipped_windows)?;
                    (joined_tables, stats)
                }
            }
        };
        self.last_stats = stats;

        #[cfg(feature = "profiling")]
        let diagnostics = {
            let wall_nanos = elapsed_nanos(self.started);
            let producer_nanos = match &self.mode {
                // The sequential run is entirely caller-thread work.
                EngineMode::Sequential(_) => wall_nanos,
                EngineMode::Parallel(_) => self.producer_nanos,
            };
            Some(EngineDiagnostics {
                wall_nanos,
                producer_nanos,
                workers: worker_diagnostics,
            })
        };

        Ok(CountResult {
            tables,
            layout: self.layout,
            k: self.config.k,
            canonical: self.config.canonical,
            stats,
            #[cfg(feature = "profiling")]
            diagnostics,
        })
    }

    /// Count one sequence through the shared extractor.
    fn count_sequence(&mut self, seq: &[u8]) -> ProcessingResult<WindowSummary> {
        let k = self.config.k;
        let canonical = self.config.canonical;
        let outcome = match &mut self.mode {
            EngineMode::Sequential(state) => {
                let partitions = self.layout.partitions();
                let tables = &mut state.tables;
                for_each_window(seq, k, canonical, |value| {
                    let partition = partition_of(value, partitions);
                    match tables.get_mut(partition) {
                        Some(table) => table.increment(value),
                        // Unreachable while `partition_of` is in range; fail
                        // loud instead of panicking (release is `panic = "abort"`).
                        None => Err(ProcessingError::new(format!(
                            "Partition {} is out of range for {} tables",
                            partition, partitions
                        ))),
                    }
                })
                .map_err(map_window_error)
            }
            EngineMode::Parallel(state) => {
                let layout = self.layout;
                let keys_per_batch = self.config.keys_per_batch.max(1);
                for_each_window(seq, k, canonical, |value| {
                    state.route_key(value, layout, keys_per_batch)
                })
                .map_err(map_window_error)
            }
        };

        match outcome {
            Ok(summary) => Ok(summary),
            Err(error) => {
                // A worker that died during the send is the real cause; join
                // before returning so the caller sees its error, if any.
                Err(self.worker_failure(error))
            }
        }
    }

    /// Join every worker, preferring a worker-returned error over `fallback`.
    fn worker_failure(&mut self, fallback: ProcessingError) -> ProcessingError {
        match self.join_workers() {
            Ok(_) => fallback,
            Err(error) => error,
        }
    }

    /// Drop every sender and join every worker exactly once.
    ///
    /// Returns the concatenated tables in layout order on success (plus the
    /// per-worker diagnostics in profiling builds), or the first worker error
    /// (including a worker panic, which is fatal only in release builds).
    /// Idempotent: a second call returns an empty result.
    fn join_workers(&mut self) -> ProcessingResult<JoinReturn> {
        let EngineMode::Parallel(state) = &mut self.mode else {
            #[cfg(feature = "profiling")]
            return Ok((Vec::new(), Vec::new()));
            #[cfg(not(feature = "profiling"))]
            return Ok(Vec::new());
        };
        if state.joined {
            #[cfg(feature = "profiling")]
            return Ok((Vec::new(), Vec::new()));
            #[cfg(not(feature = "profiling"))]
            return Ok(Vec::new());
        }
        state.joined = true;

        // Dropping every sender is what makes idle workers observe disconnect.
        state.senders.clear();

        let mut tables = Vec::new();
        #[cfg(feature = "profiling")]
        let mut worker_diagnostics: Vec<WorkerDiagnostics> = Vec::new();
        let mut first_error: Option<ProcessingError> = None;
        for handle in state.handles.drain(..) {
            match handle.join() {
                Ok(Ok(worker_return)) => {
                    if first_error.is_none() {
                        #[cfg(feature = "profiling")]
                        {
                            let (worker_tables, diagnostics) = worker_return;
                            tables.extend(worker_tables);
                            worker_diagnostics.push(diagnostics);
                        }
                        #[cfg(not(feature = "profiling"))]
                        {
                            tables.extend(worker_return);
                        }
                    }
                }
                Ok(Err(error)) => {
                    if first_error.is_none() {
                        first_error = Some(error);
                    }
                }
                Err(_panic) => {
                    if first_error.is_none() {
                        first_error = Some(ProcessingError::new(
                            "A counting worker terminated unexpectedly",
                        ));
                    }
                }
            }
        }

        match first_error {
            Some(error) => Err(error),
            None => {
                #[cfg(feature = "profiling")]
                {
                    Ok((tables, worker_diagnostics))
                }
                #[cfg(not(feature = "profiling"))]
                {
                    Ok(tables)
                }
            }
        }
    }
}

impl Drop for CountEngine {
    /// Never leak a worker: drop every sender (disconnect) and join.
    fn drop(&mut self) {
        let _ = self.join_workers();
    }
}

impl ParallelState {
    /// Route one encoded key into its partition buffer, sending a batch when
    /// the buffer reaches `keys_per_batch`.
    fn route_key(
        &mut self,
        value: u128,
        layout: PartitionLayout,
        keys_per_batch: usize,
    ) -> ProcessingResult<()> {
        let partition = partition_of(value, layout.partitions());
        let batch = match &mut self.buffers {
            RoutingBuffers::Dense(buffers) => {
                let Some(buffer) = buffers.get_mut(partition) else {
                    return Err(ProcessingError::new(format!(
                        "Partition {} is out of range for the dense routing buffers",
                        partition
                    )));
                };
                buffer.push(value as u64);
                if buffer.len() >= keys_per_batch {
                    Some(CountBatch::Dense {
                        partition: partition as u32,
                        keys: std::mem::take(buffer),
                    })
                } else {
                    None
                }
            }
            RoutingBuffers::Wide(buffers) => {
                let Some(buffer) = buffers.get_mut(partition) else {
                    return Err(ProcessingError::new(format!(
                        "Partition {} is out of range for the wide routing buffers",
                        partition
                    )));
                };
                buffer.push(value);
                if buffer.len() >= keys_per_batch {
                    Some(CountBatch::Wide {
                        partition: partition as u32,
                        keys: std::mem::take(buffer),
                    })
                } else {
                    None
                }
            }
        };

        match batch {
            Some(batch) => self.send_batch(partition, layout, batch),
            None => Ok(()),
        }
    }

    /// Send one batch to the worker that owns `partition`.
    ///
    /// A full queue blocks the producer (bounded backpressure); a disconnected
    /// receiver fails loud instead of silently dropping keys.
    fn send_batch(
        &mut self,
        partition: usize,
        layout: PartitionLayout,
        batch: CountBatch,
    ) -> ProcessingResult<()> {
        let worker = layout.owner_of(partition);
        let Some(sender) = self.senders.get(worker) else {
            return Err(ProcessingError::new(format!(
                "Counting worker {} has no queue for partition {}",
                worker, partition
            )));
        };
        sender.send(batch).map_err(|_| {
            ProcessingError::new(format!(
                "Counting worker {} disconnected while receiving a batch for partition {}",
                worker, partition
            ))
        })
    }

    /// Send every non-empty routing buffer as a batch.
    fn flush_buffers(&mut self, layout: PartitionLayout) -> ProcessingResult<()> {
        let pending: Vec<(usize, CountBatch)> = match &mut self.buffers {
            RoutingBuffers::Dense(buffers) => buffers
                .iter_mut()
                .enumerate()
                .filter_map(|(partition, buffer)| {
                    if buffer.is_empty() {
                        None
                    } else {
                        Some((
                            partition,
                            CountBatch::Dense {
                                partition: partition as u32,
                                keys: std::mem::take(buffer),
                            },
                        ))
                    }
                })
                .collect(),
            RoutingBuffers::Wide(buffers) => buffers
                .iter_mut()
                .enumerate()
                .filter_map(|(partition, buffer)| {
                    if buffer.is_empty() {
                        None
                    } else {
                        Some((
                            partition,
                            CountBatch::Wide {
                                partition: partition as u32,
                                keys: std::mem::take(buffer),
                            },
                        ))
                    }
                })
                .collect(),
        };

        for (partition, batch) in pending {
            self.send_batch(partition, layout, batch)?;
        }
        Ok(())
    }

    /// File-boundary flush: buffers, barrier, and checked ack reduction.
    fn flush_pipeline(
        &mut self,
        token: u64,
        layout: PartitionLayout,
        skipped_windows: u64,
    ) -> ProcessingResult<EngineStats> {
        self.flush_buffers(layout)?;

        for (worker, sender) in self.senders.iter().enumerate() {
            sender.send(CountBatch::Flush { token }).map_err(|_| {
                ProcessingError::new(format!(
                    "Counting worker {} disconnected before the file-boundary flush",
                    worker
                ))
            })?;
        }

        let mut stats = Vec::with_capacity(self.acknowledgements.len());
        for (worker, acknowledgement) in self.acknowledgements.iter().enumerate() {
            let stat = acknowledgement.recv().map_err(|_| {
                ProcessingError::new(format!(
                    "Counting worker {} disconnected before acknowledging the file-boundary flush",
                    worker
                ))
            })?;
            match &stat {
                WorkerStat::Flush { token: echoed, .. } if *echoed != token => {
                    return Err(ProcessingError::new(format!(
                        "Stale flush token from counting worker {}: expected {}, got {}",
                        worker, token, echoed
                    )));
                }
                _ => {}
            }
            stats.push(stat);
        }

        let (total_kmers, unique_kmers) = reduce_worker_stats(&stats)?;
        Ok(EngineStats {
            total_kmers,
            unique_kmers,
            skipped_windows,
        })
    }
}

/// The persistent worker loop: count owned batches until every sender drops.
///
/// Never prints, never calls rayon, never `unwrap`s. A per-key overflow or a
/// failed acknowledgement returns `Err`, which drops the receiver and makes the
/// producer's next send/recv fail loud.
fn run_worker(
    worker_index: usize,
    range: Range<usize>,
    mut tables: Vec<LocalKmerCounts>,
    receiver: Receiver<CountBatch>,
    acknowledgements: SyncSender<WorkerStat>,
) -> ProcessingResult<WorkerReturn> {
    #[cfg(feature = "profiling")]
    let mut diagnostics = WorkerDiagnostics::default();

    while let Ok(batch) = receiver.recv() {
        match batch {
            CountBatch::Dense { partition, keys } => {
                #[cfg(feature = "profiling")]
                let batch_started = Instant::now();
                let table = owned_table(&mut tables, &range, partition, worker_index)?;
                for key in keys {
                    table.increment(key as u128)?;
                }
                #[cfg(feature = "profiling")]
                {
                    diagnostics.batches = diagnostics.batches.saturating_add(1);
                    diagnostics.busy_nanos = diagnostics
                        .busy_nanos
                        .saturating_add(elapsed_nanos(batch_started));
                }
            }
            CountBatch::Wide { partition, keys } => {
                #[cfg(feature = "profiling")]
                let batch_started = Instant::now();
                let table = owned_table(&mut tables, &range, partition, worker_index)?;
                for key in keys {
                    table.increment(key)?;
                }
                #[cfg(feature = "profiling")]
                {
                    diagnostics.batches = diagnostics.batches.saturating_add(1);
                    diagnostics.busy_nanos = diagnostics
                        .busy_nanos
                        .saturating_add(elapsed_nanos(batch_started));
                }
            }
            CountBatch::Flush { token } => {
                let mut total: u64 = 0;
                let mut unique: u64 = 0;
                for table in &tables {
                    total = total
                        .checked_add(table.total_kmers())
                        .ok_or_else(|| ProcessingError::new(TOTAL_OVERFLOW_MESSAGE))?;
                    unique = unique
                        .checked_add(table.unique_kmers())
                        .ok_or_else(|| ProcessingError::new(UNIQUE_OVERFLOW_MESSAGE))?;
                }
                acknowledgements
                    .send(WorkerStat::Flush {
                        token,
                        total,
                        unique,
                    })
                    .map_err(|_| {
                        ProcessingError::new(format!(
                            "Counting worker {} could not deliver its flush acknowledgement",
                            worker_index
                        ))
                    })?;
            }
        }
    }
    #[cfg(feature = "profiling")]
    {
        Ok((tables, diagnostics))
    }
    #[cfg(not(feature = "profiling"))]
    {
        Ok(tables)
    }
}

/// Resolve the worker-owned table for `partition`, validating ownership.
fn owned_table<'a>(
    tables: &'a mut [LocalKmerCounts],
    range: &Range<usize>,
    partition: u32,
    worker_index: usize,
) -> ProcessingResult<&'a mut LocalKmerCounts> {
    let partition = partition as usize;
    let offset = partition
        .checked_sub(range.start)
        .filter(|offset| *offset < range.end - range.start);
    match offset.and_then(|offset| tables.get_mut(offset)) {
        Some(table) => Ok(table),
        None => Err(ProcessingError::new(format!(
            "Counting worker {} received a batch for partition {} outside its owned range {}..{}",
            worker_index, partition, range.start, range.end
        ))),
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::mpsc::{channel, Receiver as TestReceiver};
    use std::time::Duration;

    /// A direct aggregate-sum overflow must fail loud with the verbatim total
    /// message and never wrap or saturate.
    #[test]
    fn checked_sum_fails_loud_on_total_overflow() {
        let error = checked_sum([u64::MAX - 1, 2], TOTAL_OVERFLOW_MESSAGE)
            .expect_err("u64::MAX - 1 + 2 must overflow");
        assert_eq!(
            error.to_string(),
            "Total k-mer count overflow during local reduction",
            "the total-overflow message is part of the contract"
        );
    }

    /// Exact-maximum + 1 is an overflow for both aggregate messages.
    #[test]
    fn checked_sum_fails_loud_on_exact_max_plus_one() {
        let total_error = checked_sum([u64::MAX, 1], TOTAL_OVERFLOW_MESSAGE)
            .expect_err("u64::MAX + 1 must overflow");
        assert_eq!(total_error.to_string(), TOTAL_OVERFLOW_MESSAGE);

        let unique_error = checked_sum([u64::MAX, 1], UNIQUE_OVERFLOW_MESSAGE)
            .expect_err("u64::MAX + 1 must overflow");
        assert_eq!(
            unique_error.to_string(),
            "Unique k-mer count overflow during local reduction"
        );
    }

    /// The worker-ack reduction is a new summation site: two saturated acks
    /// must fail loud rather than wrap.
    #[test]
    fn reduce_worker_stats_fails_loud_on_aggregate_overflow() {
        let stats = [
            WorkerStat::Flush {
                token: 7,
                total: u64::MAX,
                unique: 0,
            },
            WorkerStat::Flush {
                token: 7,
                total: 1,
                unique: u64::MAX,
            },
        ];
        let error = reduce_worker_stats(&stats).expect_err("u64::MAX + 1 must overflow");
        assert_eq!(error.to_string(), TOTAL_OVERFLOW_MESSAGE);

        let stats = [
            WorkerStat::Flush {
                token: 7,
                total: 0,
                unique: u64::MAX,
            },
            WorkerStat::Flush {
                token: 7,
                total: 0,
                unique: 1,
            },
        ];
        let error = reduce_worker_stats(&stats).expect_err("u64::MAX + 1 must overflow");
        assert_eq!(error.to_string(), UNIQUE_OVERFLOW_MESSAGE);
    }

    /// `merge_into` must preserve the per-key verbatim overflow contract of
    /// `KmerCounter::merge_local_counts`: the failing merge leaves the
    /// counter's count at `u32::MAX`, never wraps.
    #[test]
    fn merge_into_preserves_verbatim_per_key_overflow() {
        let key: u128 = 0x1234_5678_9ABC;

        // Publish a saturated key through the already-tested counter path.
        let mut saturated = LocalKmerCounts::new(21, false);
        saturated.seed_count(key, u32::MAX);
        let counter = KmerCounter::new(21, false, 16, 1).expect("counter constructs");
        counter
            .merge_local_counts(&saturated)
            .expect("the first merge fits");

        // A fresh engine table holding one more observation of the same key.
        let mut one = LocalKmerCounts::new(21, false);
        one.increment(key).expect("first increment succeeds");
        let result = CountResult {
            tables: vec![one],
            layout: PartitionLayout::new(1),
            k: 21,
            canonical: false,
            stats: EngineStats {
                total_kmers: 1,
                unique_kmers: 1,
                skipped_windows: 0,
            },
            #[cfg(feature = "profiling")]
            diagnostics: None,
        };

        let error = result
            .merge_into(&counter)
            .expect_err("u32::MAX + 1 must overflow");
        assert_eq!(
            error.to_string(),
            "K-mer count overflow reached maximum value 4294967295",
            "merge_into must surface the counter's verbatim overflow message"
        );
        assert_eq!(
            counter.get_count(key),
            Some(u32::MAX),
            "a failed merge must not wrap the per-key count"
        );
    }

    /// Test-only constructor: build the parallel pipeline from pre-seeded
    /// partition tables so failure paths can be injected deterministically.
    fn new_parallel_with_tables(
        config: EngineConfig,
        partition_tables: Vec<LocalKmerCounts>,
    ) -> ProcessingResult<CountEngine> {
        let layout = PartitionLayout::new(config.threads);
        CountEngine::spawn_parallel(config, layout, partition_tables)
    }

    /// A worker seeded at the per-key ceiling must return the verbatim overflow
    /// error through the pipeline and must never hang, even with more batches
    /// queued behind the failing one.
    #[test]
    fn worker_overflow_returns_verbatim_error_without_hanging() {
        let k = 21usize;
        let threads = 2usize;
        let config = EngineConfig {
            k,
            canonical: false,
            threads,
            initial_capacity: 16,
            keys_per_batch: 1,
            queue_batches: 4,
            records_per_warning_batch: DEFAULT_RECORDS_PER_WARNING_BATCH,
        };

        let layout = PartitionLayout::new(threads);
        let mut tables: Vec<LocalKmerCounts> = (0..layout.partitions())
            .map(|_| LocalKmerCounts::new(k, false))
            .collect();
        // The all-A 21-mer encodes to 0; seed its owning partition at the
        // ceiling so the worker's first increment must fail.
        let overflow_key: u128 = 0;
        let owner = partition_of(overflow_key, layout.partitions());
        tables[owner].seed_count(overflow_key, u32::MAX);

        let dir = tempfile::tempdir().expect("tempdir for overflow fixture");
        let input = dir.path().join("overflow.fastq");
        let mut body = String::new();
        body.push_str("@overflow\n");
        body.push_str(&"A".repeat(k + 1));
        body.push_str("\n+\n");
        body.push_str(&"I".repeat(k + 1));
        body.push('\n');
        std::fs::write(&input, body).expect("write overflow fixture");

        let (sender, receiver): (_, TestReceiver<Result<(), String>>) = channel();
        let worker = std::thread::spawn(move || {
            let mut engine = new_parallel_with_tables(config, tables)
                .expect("parallel engine must construct from seeded tables");
            let outcome = engine
                .count_file(&input, SequenceKind::Fastq)
                .map(|_| ())
                .map_err(|error| error.to_string());
            let _ = sender.send(outcome);
        });

        let outcome = receiver
            .recv_timeout(Duration::from_secs(30))
            .expect("the overflow pipeline must return within the watchdog deadline");
        worker.join().expect("overflow test thread must finish");
        let error = outcome.expect_err("the seeded ceiling must surface an error");
        assert!(
            error.contains("K-mer count overflow reached maximum value 4294967295"),
            "the pipeline must surface the worker's verbatim overflow error, got: {error}"
        );
    }

    /// Dropping an engine must join every worker; the drop call returning is
    /// the assertion (a leaked or blocked worker would time out the watchdog).
    #[test]
    fn engine_drop_joins_workers() {
        let config = EngineConfig::new(21, false, 4, 16);
        let (sender, receiver): (_, TestReceiver<()>) = channel();
        let worker = std::thread::spawn(move || {
            let engine = CountEngine::new(config).expect("parallel engine must construct");
            assert_eq!(engine.worker_count(), 4, "four persistent workers expected");
            drop(engine);
            let _ = sender.send(());
        });
        receiver
            .recv_timeout(Duration::from_secs(10))
            .expect("Drop must join every worker without hanging");
        worker.join().expect("drop test thread must finish");
    }
}
