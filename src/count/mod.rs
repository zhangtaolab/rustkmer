//! The shared counting engine consumed by the CLI and (structurally) PyO3.
//!
//! Phase 7 replaces the per-chunk rayon `fill -> par_iter -> clear` hot loop
//! with one producer that extracts each window through
//! [`crate::kmer::extract::for_each_window`] and routes each key into exactly
//! one disjoint hash-range partition table. The producer sends partition-tagged
//! batches to N persistent OS workers over bounded per-worker queues; the
//! sequential path (`threads == 1`) counts on the caller thread with no queue
//! and no worker.

pub mod batch;
pub mod engine;
pub mod partition;

pub use batch::{CountBatch, WorkerStat};
pub use engine::{
    CountEngine, CountResult, EngineConfig, EngineStats, FileStats, SequenceKind,
    DEFAULT_KEYS_PER_BATCH, DEFAULT_QUEUE_BATCHES, DEFAULT_RECORDS_PER_WARNING_BATCH,
};
#[cfg(feature = "profiling")]
pub use engine::{EngineDiagnostics, WorkerDiagnostics};
pub use partition::{mix64, partition_of, PartitionLayout, MAX_PARTITIONS, MIN_PARTITIONS};
