//! Database functionality for k-mer storage and querying
//!
//! Provides efficient storage and retrieval of k-mer counts with
//! support for indexed binary format and high-performance query operations.

pub mod format;
pub mod index;
pub mod memory;
pub mod merge_config;
pub mod merge_error;
pub mod prefix_cache_merge;
pub mod prefix_query;
pub mod prefix_query_optimized;
pub mod query;
pub mod stats;
pub mod streaming_merge;
pub mod suffix_query;
pub mod temp_lifecycle;

pub use format::{DatabaseFormat, DatabaseHeader};
pub use index::DatabaseIndex;
pub use merge_config::{MergeConfig, MergeStats, MergeStrategy};
pub use prefix_cache_merge::ExternalSortMerger;
pub use query::DatabaseQuery;
pub use streaming_merge::{
    DatabaseStreamIterator, ExternalMerger, StreamingMergeIterator, TempFileManager,
};
