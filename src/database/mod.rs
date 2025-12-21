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

pub use format::{DatabaseFormat, DatabaseHeader};
pub use query::DatabaseQuery;
pub use index::DatabaseIndex;
pub use merge_config::{MergeConfig, MergeStats, MergeStrategy};
pub use prefix_query::{PrefixQueryResult, extract_kmers_by_prefix, extract_kmers_by_multiple_prefixes};
pub use suffix_query::{SuffixQueryResult, extract_kmers_by_suffix, smart_wildcard_query, SmartWildcardResult, QueryStrategy, StrategyType};
