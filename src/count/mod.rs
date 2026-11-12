//! The shared counting engine consumed by the CLI and (structurally) PyO3.
//!
//! Phase 7 replaces the per-chunk rayon `fill -> par_iter -> clear` hot loop
//! with one producer that extracts each window through
//! [`crate::kmer::extract::for_each_window`] and routes each key into exactly
//! one disjoint hash-range partition table. The sequential path implemented by
//! this plan is the tracer slice; 07-02 adds the persistent worker pipeline
//! over the same layout and exactness contract.

pub mod engine;
pub mod partition;

pub use engine::{
    CountEngine, CountResult, EngineConfig, EngineStats, FileStats, SequenceKind,
    DEFAULT_KEYS_PER_BATCH, DEFAULT_QUEUE_BATCHES, DEFAULT_RECORDS_PER_WARNING_BATCH,
};
pub use partition::{mix64, partition_of, PartitionLayout, MAX_PARTITIONS, MIN_PARTITIONS};
