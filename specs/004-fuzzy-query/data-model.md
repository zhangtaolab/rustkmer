# Data Model: Fuzzy Query System

**Feature**: Fuzzy Query with Wildcard Support
**Date**: 2025-11-28
**Status**: Draft

## Core Entities

### 1. FuzzyQuery

Represents a fuzzy query request with all parameters needed for expansion and matching.

```rust
pub struct FuzzyQuery {
    /// The input query string (may contain 'N' wildcards)
    pub query_string: String,

    /// Target k-mer size for the database
    pub kmer_size: usize,

    /// Maximum allowed Hamming distance for mutations
    pub mutation_tolerance: usize,

    /// Maximum number of variants to generate (combinatorial explosion protection)
    pub max_variants: Option<usize>,

    /// Whether to enable parallel processing
    pub enable_parallel: bool,

    /// Batch size for processing variants
    pub batch_size: usize,
}
```

**Validation Rules**:
- `query_string`: Must contain only A,T,C,G,N characters, length 1-1000
- `kmer_size`: Must be positive integer, typically 5-31 for biological k-mers
- `mutation_tolerance`: Must be 0 <= value <= kmer_size/2
- `max_variants`: Default 10,000, must be >= 1
- `batch_size`: Must be >= 1, recommended 100-1000

### 2. QueryExpansion

Represents the generated set of concrete k-mers to be queried, including metadata about how they were generated.

```rust
pub struct QueryExpansion {
    /// List of concrete k-mer sequences without wildcards
    pub concrete_kmers: Vec<String>,

    /// How the k-mers were generated
    pub expansion_method: ExpansionMethod,

    /// Total number of combinations generated
    pub combination_count: usize,

    /// Original query string
    pub original_query: String,

    /// Performance metadata
    pub generation_time_ms: u64,
}

pub enum ExpansionMethod {
    /// Only wildcard expansion (N → A,T,C,G)
    WildcardOnly { wildcard_count: usize },

    /// Only mutation tolerance (Hamming distance)
    MutationOnly { mutation_distance: usize },

    /// Both wildcard expansion and mutation tolerance
    Combined {
        wildcard_count: usize,
        mutation_distance: usize
    },

    /// Length normalization (padding/truncating)
    LengthNormalization {
        original_length: usize,
        target_length: usize
    },
}
```

**Validation Rules**:
- `concrete_kmers`: All strings must be length `kmer_size`, contain only A,T,C,G
- `combination_count`: Must match `concrete_kmers.len()`
- `generation_time_ms`: Must be realistic (< 60000ms for performance)

### 3. FuzzyResult

Represents the aggregated result from fuzzy query operations with detailed match information.

```rust
pub struct FuzzyResult {
    /// Total count of all matching k-mers
    pub total_count: u64,

    /// Individual matches with their counts and query metadata
    pub individual_matches: Vec<KmerMatch>,

    /// Query metadata and performance information
    pub query_metadata: QueryMetadata,

    /// Success/failure status
    pub status: QueryStatus,
}

pub struct KmerMatch {
    /// The matching k-mer sequence
    pub sequence: String,

    /// Count of this k-mer in the database
    pub count: u64,

    /// How this match relates to the original query
    pub match_type: MatchType,

    /// Hamming distance from original query (if applicable)
    pub hamming_distance: Option<usize>,
}

pub enum MatchType {
    /// Exact match to original query
    Exact,

    /// Generated from wildcard expansion
    WildcardExpansion { wildcard_positions: Vec<usize> },

    /// Generated from mutation tolerance
    MutationTolerance { mutation_positions: Vec<usize> },

    /// Generated from length normalization
    LengthNormalization,
}

pub struct QueryMetadata {
    /// Original query parameters
    pub query_params: FuzzyQuery,

    /// Number of variants generated and queried
    pub variants_generated: usize,

    /// Total query execution time in milliseconds
    pub query_time_ms: u64,

    /// Database size (number of k-mers)
    pub database_size: Option<u64>,

    /// Memory usage statistics
    pub memory_usage_mb: Option<f64>,
}

pub enum QueryStatus {
    /// Query completed successfully
    Success,

    /// Query failed due to combinatorial explosion
    CombinatorialExplosion,

    /// Query failed due to invalid parameters
    InvalidParameters,

    /// Query failed due to database error
    DatabaseError,

    /// Query cancelled by user
    Cancelled,
}
```

**Validation Rules**:
- `total_count`: Must equal sum of all `individual_matches.count`
- `individual_matches`: All sequences must be unique
- `hamming_distance`: Must be 0 <= value <= kmer_size
- `query_time_ms`: Must be realistic for database size

### 4. PerformanceMetrics

Tracks performance metrics for optimization and monitoring.

```rust
pub struct PerformanceMetrics {
    /// Variant generation metrics
    pub variant_generation: VariantGenerationMetrics,

    /// Database query metrics
    pub database_queries: DatabaseQueryMetrics,

    /// Memory usage metrics
    pub memory_usage: MemoryUsageMetrics,

    /// Parallel processing metrics
    pub parallel_processing: ParallelProcessingMetrics,
}

pub struct VariantGenerationMetrics {
    /// Time to generate all variants
    pub total_generation_time_ms: u64,

    /// Number of variants generated
    pub variants_generated: usize,

    /// Generation rate (variants per second)
    pub generation_rate: f64,

    /// Peak memory usage during generation
    pub peak_memory_mb: f64,
}

pub struct DatabaseQueryMetrics {
    /// Total number of database queries executed
    pub total_queries: usize,

    /// Average query time per k-mer lookup
    pub avg_query_time_ms: f64,

    /// Number of queries that returned results
    pub successful_queries: usize,

    /// Database hit rate
    pub hit_rate: f64,
}

pub struct MemoryUsageMetrics {
    /// Peak memory usage during entire operation
    pub peak_memory_mb: f64,

    /// Memory used for storing variants
    pub variants_memory_mb: f64,

    /// Memory used for result storage
    pub results_memory_mb: f64,

    /// Memory efficiency score (results / memory)
    pub memory_efficiency: f64,
}

pub struct ParallelProcessingMetrics {
    /// Number of worker threads used
    pub worker_threads: usize,

    /// Parallel efficiency (speedup vs sequential)
    pub parallel_efficiency: f64,

    /// Load balancing score (0-1, higher is better)
    pub load_balance_score: f64,

    /// Thread contention metrics
    pub thread_contention_ms: u64,
}
```

## State Transitions

### Query Processing Flow

```
FuzzyQuery (input)
    ↓ validation
QueryExpansion (generation)
    ↓ database queries
FuzzyResult (aggregation)
    ↓ formatting
Output (human/machine readable)
```

### Error Handling States

```
Invalid Input → ValidationError → User-Friendly Error Message
Combinatorial Explosion → SafeTermination → Warning + Suggestions
Database Error → Retry → Fallback → Error Report
```

## Relationships

### Entity Relationships

- **FuzzyQuery** → 1:1 → **QueryExpansion** (generation)
- **QueryExpansion** → 1:N → **concrete_kmers** (generated sequences)
- **concrete_kmers** → 1:N → **FuzzyResult.individual_matches** (query results)
- **FuzzyQuery** → 1:1 → **FuzzyResult.query_metadata.query_params**
- **FuzzyResult** → 1:1 → **PerformanceMetrics** (tracking)

### Data Flow

1. User input creates **FuzzyQuery**
2. **FuzzyQuery** generates **QueryExpansion** with **concrete_kmers**
3. Each concrete k-mer is queried against database
4. Results are aggregated into **FuzzyResult**
5. **PerformanceMetrics** tracked throughout process

## Constraints and Invariants

### Business Rules

1. **Combinatorial Explosion Protection**: Maximum 10,000 variants unless explicitly overridden
2. **Memory Safety**: All operations must stay within specified memory limits
3. **Performance Guarantees**: Single wildcard queries must complete within specified time limits
4. **Data Integrity**: All k-mers must be valid DNA sequences (A,T,C,G only)

### Technical Constraints

1. **Thread Safety**: All concurrent operations must be thread-safe
2. **Error Handling**: All operations must return Result types with comprehensive error information
3. **Resource Limits**: Must respect system resource constraints and fail gracefully
4. **Backward Compatibility**: Must not break existing RKDB database functionality

This data model provides a comprehensive foundation for implementing robust fuzzy query functionality while maintaining performance, safety, and usability requirements.