//! Database statistics module for k-mer analysis
//!
//! This module provides functionality to calculate comprehensive statistics
//! for RKDB databases including k-mer counts, frequency distributions,
//! and statistical measures.

use std::path::PathBuf;
use std::time::Duration;
use serde::{Serialize, Deserialize};
use thiserror::Error;
use std::collections::HashMap;

/// Statistics for a k-mer database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseStatistics {
    /// Path to the source database file
    pub database_file: PathBuf,

    /// K-mer size used in the database
    pub kmer_size: u8,

    /// Whether canonical k-mers were used during counting
    pub canonical: bool,

    /// Whether the database is sorted
    pub sorted: bool,

    /// Total number of k-mers (including duplicates)
    pub total_kmers: u64,

    /// Number of unique k-mer sequences
    pub unique_kmers: u64,

    /// Minimum k-mer count found
    pub min_count: u32,

    /// Maximum k-mer count found
    pub max_count: u32,

    /// Average count across all unique k-mers
    pub mean_count: f64,

    /// Median count (approximate for large datasets)
    pub median_count: f64,

    /// Frequency distribution (count -> number of k-mers with that count)
    /// Only included if requested via --detailed flag
    #[serde(skip_serializing_if = "Option::is_none")]
    pub frequency_distribution: Option<Vec<(u32, u64)>>,

    /// Processing metadata
    #[serde(serialize_with = "serialize_duration")]
    #[serde(deserialize_with = "deserialize_duration")]
    pub processing_time: Duration,
    pub memory_peak_bytes: u64,
}

/// Serialize Duration as milliseconds for CSV compatibility
fn serialize_duration<S>(duration: &Duration, serializer: S) -> std::result::Result<S::Ok, S::Error>
where
    S: serde::Serializer,
{
    let millis = duration.as_millis() as u64;
    serializer.serialize_u64(millis)
}

/// Deserialize Duration from milliseconds
fn deserialize_duration<'de, D>(deserializer: D) -> std::result::Result<Duration, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let millis = u64::deserialize(deserializer)?;
    Ok(Duration::from_millis(millis))
}

/// Configuration for statistics calculation
#[derive(Debug, Clone)]
pub struct StatsConfiguration {
    /// Output format for statistics
    pub output_format: OutputFormat,

    /// Whether to include detailed frequency distribution
    pub detailed: bool,

    /// Maximum number of bins for frequency distribution
    pub max_bins: usize,

    /// Use approximate median (faster, less memory)
    pub approximate: bool,

    /// Show progress bar during processing
    pub show_progress: bool,

    /// Output file path (None for stdout)
    pub output_path: Option<PathBuf>,

    /// Split output into separate files
    pub split_output: bool,

    /// Output file path for frequency distribution (when split_output is true)
    pub freq_output_path: Option<PathBuf>,
}

/// Output format options
#[derive(Debug, Clone)]
pub enum OutputFormat {
    Text,
    Json,
    Csv,
    Tsv,
}

/// Errors that can occur during statistics calculation
#[derive(Error, Debug)]
pub enum StatsError {
    #[error("Database file not found: {path}")]
    DatabaseNotFound { path: PathBuf },

    #[error("Invalid database format: {reason}")]
    InvalidFormat { reason: String },

    #[error("Database empty: no k-mers found")]
    EmptyDatabase,

    #[error("Memory limit exceeded: required {required}MB, limit {limit}MB")]
    MemoryLimitExceeded { required: u64, limit: u64 },

    #[error("I/O error: {source}")]
    Io {
        #[from]
        source: std::io::Error,
    },

    #[error("Serialization error: {format} - {source}")]
    Serialization {
        format: String,
        #[source]
        source: Box<dyn std::error::Error + Send + Sync>,
    },

    #[error("CSV error: {0}")]
    Csv(#[from] csv::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Result type for statistics operations
pub type Result<T> = std::result::Result<T, StatsError>;

/// Streaming statistics processor for memory-efficient calculation
pub struct StreamingStatsProcessor {
    /// TDigest for approximate quantile calculation
    tdigest: tdigest::TDigest,

    /// Basic running statistics
    total_kmers: u64,
    unique_kmers: u64,
    min_count: u32,
    max_count: u32,
    sum_counts: u128, // Use u128 to prevent overflow

    /// Frequency histogram with size limit
    frequency_histogram: HashMap<u32, u64>,

    /// Configuration
    config: StatsConfiguration,
}

impl StreamingStatsProcessor {
    /// Create a new streaming statistics processor
    pub fn new(config: StatsConfiguration) -> Self {
        Self {
            tdigest: tdigest::TDigest::default(),
            total_kmers: 0,
            unique_kmers: 0,
            min_count: u32::MAX,
            max_count: 0,
            sum_counts: 0,
            frequency_histogram: HashMap::new(),
            config,
        }
    }

    /// Add a k-mer count to the statistics
    pub fn add_count(&mut self, count: u32) -> Result<()> {
        self.total_kmers += count as u64;
        self.unique_kmers += 1;
        self.min_count = self.min_count.min(count);
        self.max_count = self.max_count.max(count);
        self.sum_counts += count as u128;

        // Add to TDigest for median calculation
        // Since TDigest doesn't have add for single values, we merge with a single-element vector
        self.tdigest = self.tdigest.merge_unsorted(vec![count as f64]);

        // Track histogram for frequency distribution (with memory limit)
        if count <= 1000 || self.frequency_histogram.len() < self.config.max_bins {
            *self.frequency_histogram.entry(count).or_insert(0) += 1;
        }

        Ok(())
    }

    /// Calculate the median count
    pub fn median(&self) -> f64 {
        self.tdigest.estimate_quantile(0.5)
    }

    /// Calculate mean count
    pub fn mean(&self) -> f64 {
        if self.unique_kmers == 0 {
            0.0
        } else {
            self.sum_counts as f64 / self.unique_kmers as f64
        }
    }

    /// Generate complete frequency distribution with zero-filling
    pub fn frequency_distribution(&self) -> Option<Vec<(u32, u64)>> {
        if !self.config.detailed {
            return None;
        }

        if self.unique_kmers == 0 {
            return None;
        }

        let mut distribution = Vec::new();

        // Fill from min_count to max_count
        for count in self.min_count..=self.max_count {
            let frequency = self.frequency_histogram.get(&count).copied().unwrap_or(0);
            distribution.push((count, frequency));
        }

        Some(distribution)
    }

    /// Finalize statistics and create DatabaseStatistics
    pub fn finalize(
        self,
        database_file: PathBuf,
        kmer_size: u8,
        canonical: bool,
        sorted: bool,
        processing_time: Duration,
    ) -> DatabaseStatistics {
        DatabaseStatistics {
            database_file,
            kmer_size,
            canonical,
            sorted,
            total_kmers: self.total_kmers,
            unique_kmers: self.unique_kmers,
            min_count: if self.unique_kmers > 0 { self.min_count } else { 0 },
            max_count: self.max_count,
            mean_count: self.mean(),
            median_count: self.median(),
            frequency_distribution: self.frequency_distribution(),
            processing_time,
            memory_peak_bytes: 0, // TODO: Track actual memory usage
        }
    }
}