# Data Model: 21-mer Performance Testing

**Branch**: `003-parallel-query` | **Date**: 2025-11-28

## Overview

This document defines the data structures and entities used for 21-mer performance comparison testing between jellyfish and rustkmer to determine multi-threading benefits for larger k-mer sizes.

## Core Entities

### 1. TestConfiguration

Represents the configuration for a performance comparison test run.

**Fields**:
- `test_id`: String (unique identifier)
- `dataset_path`: String (path to OSA1 r7 assembly)
- `kmer_size`: Integer (21 for this comparison)
- `query_count`: Integer (10,000 queries)
- `random_seed`: Integer (42 for reproducibility)
- `output_directory`: String (base path for all outputs)
- `timestamp`: DateTime (test execution timestamp)

**Validation Rules**:
- `kmer_size` must be between 1 and 127
- `query_count` must be positive
- `dataset_path` must exist and be readable
- `output_directory` must be writable

### 2. DatabaseInfo

Stores information about generated databases for comparison.

**Fields**:
- `database_id`: String (unique identifier)
- `tool_name`: String ("jellyfish" or "rustkmer")
- `database_type`: String ("single-threaded" or "multi-threaded")
- `file_path`: String (path to database file)
- `kmer_count`: Integer (total k-mers in database)
- `file_size_bytes`: Integer (database file size)
- `creation_time_ms`: Integer (database creation time)
- `creation_parameters`: Map<String, String> (command-line parameters)

**Validation Rules**:
- `file_path` must exist
- `kmer_count` must be positive
- `file_size_bytes` must be positive

### 3. QuerySet

Represents the set of k-mers used for performance testing.

**Fields**:
- `query_set_id`: String (unique identifier)
- `queries`: Array<String> (10,000 k-mer sequences)
- `generation_method`: String ("deterministic_random")
- `random_seed`: Integer (42)
- `created_at`: DateTime (generation timestamp)

**Validation Rules**:
- All queries must be valid DNA sequences (A, C, G, T only)
- All queries must have length 21
- Must contain exactly 10,000 queries
- No duplicate queries allowed

### 4. PerformanceResult

Stores performance metrics for a single test execution.

**Fields**:
- `result_id`: String (unique identifier)
- `test_configuration_id`: String (reference to TestConfiguration)
- `database_info_id`: String (reference to DatabaseInfo)
- `query_set_id`: String (reference to QuerySet)
- `tool_name`: String ("jellyfish", "rustkmer_query", "rustkmer_queryx")
- `thread_count`: Integer (threads used)
- `execution_time_ms`: Integer (total execution time)
- `queries_per_second`: Float (throughput metric)
- `memory_peak_kb`: Integer (peak memory usage)
- `cpu_percent`: Float (CPU utilization percentage)
- `cache_misses`: Integer (cache performance metric)
- `context_switches`: Integer (system overhead)
- `kmer_encoding_size`: Integer (bits per k-mer, 42 for 21-mers)
- `database_cache_efficiency`: Float (cache hit ratio for database operations)

**Validation Rules**:
- `execution_time_ms` must be positive
- `queries_per_second` must be positive
- `memory_peak_kb` must be positive
- `thread_count` must be positive

### 5. QueryResult

Stores individual query results for accuracy validation.

**Fields**:
- `query_result_id`: String (unique identifier)
- `performance_result_id`: String (reference to PerformanceResult)
- `query_sequence`: String (21-mer sequence)
- `expected_count`: Integer (baseline count from jellyfish)
- `actual_count`: Integer (count from tested tool)
- `is_correct`: Boolean (accuracy validation)
- `query_time_ms`: Float (individual query time, optional)

**Validation Rules**:
- `query_sequence` must be valid DNA sequence of length 21
- Counts must be non-negative integers
- `is_correct` must match count comparison

## Relationships

```
TestConfiguration (1) -----> (N) DatabaseInfo
TestConfiguration (1) -----> (1) QuerySet
DatabaseInfo (1) -----> (N) PerformanceResult
QuerySet (1) -----> (N) PerformanceResult
PerformanceResult (1) -----> (N) QueryResult
```

## State Transitions

### Test Execution Workflow

1. **Configuration Created**
   - Validate all input parameters
   - Create output directory structure

2. **Database Generation**
   - Generate jellyfish database
   - Generate rustkmer database
   - Validate database integrity

3. **Query Set Generation**
   - Create deterministic random queries
   - Validate query sequences

4. **Performance Testing**
   - Execute jellyfish benchmark
   - Execute rustkmer single-threaded benchmark
   - Execute rustkmer multi-threaded benchmark

5. **Result Validation**
   - Compare query results for accuracy
   - Generate performance analysis

## Data Formats

### Input Files

- **FASTA**: OSA1 r7 assembly format
- **Query File**: Plain text, one 21-mer per line
- **Configuration**: JSON format for test parameters

### Output Files

- **Performance Logs**: Structured text with system metrics
- **Query Results**: TSV format (k-mer, count, tool_name)
- **Summary Report**: JSON with comprehensive analysis

## File Organization

```
/Users/forrest/Temp/demodata/
├── test_runs/
│   └── {test_id}/
│       ├── configuration.json
│       ├── databases/
│       │   ├── jellyfish_21mer.jf
│       │   └── rustkmer_21mer_sorted.rkdb
│       ├── queries/
│       │   └── random_10k.txt
│       ├── results/
│       │   ├── jellyfish_performance.json
│       │   ├── rustkmer_single_performance.json
│       │   ├── rustkmer_multi_performance.json
│       │   └── query_comparison.tsv
│       └── logs/
│           ├── jellyfish_timing.log
│           ├── rustkmer_single_timing.log
│           └── rustkmer_multi_timing.log
```

## Data Integrity

### Validation Rules

1. **Referential Integrity**: All foreign keys must reference existing entities
2. **Uniqueness**: All IDs must be unique within their scope
3. **Data Consistency**: Performance results must match expected ranges
4. **File Integrity**: All referenced files must exist and be valid

### Accuracy Validation

- Query results must be identical across all tools
- Performance metrics must be within reasonable bounds
- Database statistics must be consistent
- File sizes must match expectations

## Performance Considerations

### Memory Management

- Query sets loaded in chunks for large datasets
- Performance results streamed to disk during execution
- Database file handles managed efficiently
- Memory usage monitored throughout testing

### Scalability

- Supports different k-mer sizes
- Configurable query counts
- Multiple dataset support
- Extensible to additional tools

This data model provides a comprehensive foundation for reproducible, accurate performance comparison testing between jellyfish and rustkmer.