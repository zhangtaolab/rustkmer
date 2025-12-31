//! Database functionality for k-mer storage and querying
//!
//! Provides efficient storage and retrieval of k-mer counts with
//! support for indexed binary format and compatibility with
//! jellyfish-style queries.

pub mod format;
pub mod query;
pub mod index;
pub mod merge_config;
pub mod memory;
pub mod merge_error;
pub mod stats;
pub mod prefix_query;
pub mod prefix_query_optimized;
pub mod suffix_query;
pub mod streaming_merge;
pub mod prefix_cache_merge;

pub use format::{DatabaseFormat, DatabaseHeader};
pub use query::DatabaseQuery;
pub use index::DatabaseIndex;
pub use merge_config::{MergeConfig, MergeStats, MergeStrategy};
pub use streaming_merge::{ExternalMerger, StreamingMergeIterator, DatabaseStreamIterator, TempFileManager};
pub use prefix_cache_merge::ExternalSortMerger;
