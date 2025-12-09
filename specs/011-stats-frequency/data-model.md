# Data Model: Stats Command

**Feature**: Stats Command with K-mer Count Frequency Distribution
**Date**: December 9, 2025

## Core Entities

### DatabaseStatistics
The primary data structure for all statistics output.

```rust
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
    pub processing_time: Duration,
    pub memory_peak_bytes: u64,
}
```

### StatsConfiguration
Configuration for statistics calculation.

```rust
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
}
```

### StreamingStatsProcessor
Internal processor for calculating statistics in a streaming fashion.

```rust
pub struct StreamingStatsProcessor {
    /// TDigest for approximate quantile calculation
    tdigest: TDigest,

    /// Basic running statistics
    total_kmers: u64,
    unique_kmers: u64,
    min_count: u32,
    max_count: u32,
    sum_counts: u128, // Use u128 to prevent overflow

    /// Frequency histogram with size limit
    frequency_histogram: IndexMap<u32, u64>,

    /// Configuration
    config: StatsConfiguration,
}
```

## Entity Relationships

```
DatabaseStatistics
├── DatabaseMetadata
│   ├── database_file: PathBuf
│   ├── kmer_size: u8
│   ├── canonical: bool
│   └── sorted: bool
├── BasicStats
│   ├── total_kmers: u64
│   ├── unique_kmers: u64
│   ├── min_count: u32
│   ├── max_count: u32
│   ├── mean_count: f64
│   └── median_count: f64
├── FrequencyDistribution (optional)
│   └── Vec<(count: u32, frequency: u64)>
└── ProcessingMetadata
    ├── processing_time: Duration
    └── memory_peak_bytes: u64
```

## Data Flow

```
RKDB File
    ↓
DatabaseReader (memory-mapped)
    ↓
StreamingStatsProcessor
    ├── Basic statistics (O(1) memory)
    ├── TDigest for median (O(1) memory)
    └── Frequency histogram (bounded memory)
    ↓
DatabaseStatistics
    ↓
OutputFormatter (JSON/CSV/TSV/Text)
    ↓
Output (File or stdout)
```

## Validation Rules

### Input Validation
- Database file must exist and be readable
- Database must be valid RKDB format with u128 encoding
- K-mer size must be consistent with database format

### Output Validation
- All counts must be non-negative
- total_kmers >= unique_kmers
- min_count <= max_count
- mean_count must be between min_count and max_count
- median_count must be between min_count and max_count

### Configuration Validation
- max_bins must be between 1 and 100000
- Output format must be one of: text, json, csv, tsv
- Output directory must exist if output_path specified

## State Transitions

```
Initial
    ↓ (load database)
Loading
    ↓ (validate format)
Validating
    ↓ (process entries)
Processing
    ├── Success → Completed
    └── Error → Failed
```

## Memory Management

### StreamingStatsProcessor Memory Usage
- **Fixed overhead**: ~1KB
- **TDigest**: ~10KB (compression=100)
- **Frequency histogram**: O(max_bins) entries
  - Default (1000 bins): ~16KB
  - Maximum (100000 bins): ~1.6MB
- **Total typical usage**: <100KB

### Large Dataset Handling
For datasets with very large count ranges:
1. Use approximate statistics when `approximate = true`
2. Limit frequency distribution to `max_bins`
3. Fall back to two-pass algorithm if memory constraints detected

## Error Handling

### Error Types
```rust
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
}
```

### Error Recovery Strategies
- **File not found**: Provide helpful message with file path
- **Invalid format**: Suggest running `rustkmer check` command
- **Memory limit**: Suggest increasing `--max-bins` or using `--approximate`
- **Empty database**: Clear error message suggesting database creation

## Performance Considerations

### Time Complexity
- **Basic statistics**: O(N) where N is number of k-mers
- **Median (approximate)**: O(N) with TDigest
- **Median (exact)**: O(N log N) fallback for small datasets
- **Frequency distribution**: O(N + M) where M = max_count

### Space Complexity
- **Streaming mode**: O(max_bins) where max_bins is configurable
- **Memory-mapped I/O**: O(1) additional memory for file access
- **Output buffering**: O(output_size) temporary

### Optimization Points
1. **Parallel processing**: Use rayon for CPU-bound operations
2. **Memory access**: Leverage memmap2 for efficient file reading
3. **Batching**: Process entries in batches for better cache locality
4. **Early termination**: Stop processing if only basic stats needed