//! Fuzzy Query Module
//!
//! This module provides comprehensive fuzzy query capabilities for k-mer databases,
//! including wildcard expansion, length normalization, and mutation tolerance.
//!
//! # Features
//!
//! - **Wildcard Expansion**: N → A,T,C,G expansion with configurable limits
//! - **Length Normalization**: Automatic padding/truncating to match database k-mer size
//! - **Mutation Tolerance**: Hamming distance-based approximate matching
//! - **Performance Optimization**: Parallel processing and memory-efficient algorithms
//!
//! # Example Usage
//!
//! ```rust
//! use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine};
//!
//! // Create a fuzzy query with wildcard support
//! let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
//! // FuzzyQueryEngine requires a valid database path
//! // let engine = FuzzyQueryEngine::new("/path/to/database")?;
//! // let results = engine.execute_query(&query)?;
//! ```

pub mod expansion;
pub mod mutation;
pub mod normalization;
pub mod performance;
pub mod query;
pub mod wildcard;

// Re-export main types for convenience
pub use expansion::{ExpansionMethod, QueryExpansion};
pub use performance::{DatabaseQueryMetrics, PerformanceMetrics, VariantGenerationMetrics};
pub use query::{
    FuzzyQuery, FuzzyQueryEngine, FuzzyQueryResult, FuzzyQueryResultData, KmerMatch, MatchType,
    QueryMetadata, QueryStatus,
};

use thiserror::Error;

/// Comprehensive error type for fuzzy query operations
#[derive(Error, Debug)]
pub enum FuzzyError {
    #[error("Invalid query string: {0}")]
    InvalidQuery(String),

    #[error("Too many variants generated: {actual} (limit: {limit})")]
    TooManyVariants { actual: usize, limit: usize },

    #[error("Memory limit exceeded: {usage_mb}MB (limit: {limit_mb}MB)")]
    MemoryLimitExceeded { usage_mb: f64, limit_mb: f64 },

    #[error("Database error: {0}")]
    DatabaseError(String),

    #[error("Performance constraint violation: {0}")]
    PerformanceConstraint(String),

    #[error("Invalid parameters: {0}")]
    InvalidParameters(String),

    #[error("Query cancelled by user")]
    Cancelled,

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Result type alias for fuzzy query operations
pub type FuzzyResult<T> = Result<T, FuzzyError>;

/// Constants for fuzzy query operations
pub mod constants {
    /// Default maximum number of variants to generate
    pub const DEFAULT_MAX_VARIANTS: usize = 10_000;

    /// Default batch size for processing
    pub const DEFAULT_BATCH_SIZE: usize = 1_000;

    /// Maximum allowed mutation distance (k/2)
    pub const MAX_MUTATION_RATIO: f64 = 0.5;

    /// Memory limit threshold in MB
    pub const DEFAULT_MEMORY_LIMIT_MB: f64 = 1024.0;

    /// Performance timeout in seconds
    pub const DEFAULT_TIMEOUT_SECONDS: u64 = 300;

    /// Parallel processing threshold
    pub const PARALLEL_THRESHOLD: usize = 100;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuzzy_error_display() {
        let err = FuzzyError::InvalidQuery("Invalid character".to_string());
        assert!(err.to_string().contains("Invalid query string"));
    }

    #[test]
    fn test_constants() {
        assert!(constants::DEFAULT_MAX_VARIANTS > 0);
        assert!(constants::DEFAULT_BATCH_SIZE > 0);
        assert!(constants::MAX_MUTATION_RATIO > 0.0);
        assert!(constants::MAX_MUTATION_RATIO <= 1.0);
    }
}
