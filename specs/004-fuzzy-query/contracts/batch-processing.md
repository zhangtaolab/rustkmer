# API Contract: Batch Processing

**Feature**: Fuzzy Query Batch Processing
**Version**: 1.0.0
**Date**: 2025-11-28

## Batch Processing Interface

### Command: `fuzzy-query-batch`

```bash
rustkmer fuzzy-query-batch [OPTIONS] <DATABASE> <QUERY_FILE>
```

### Input File Format

#### Simple Query Format

```
# One query per line
ATGCGATGCTAGCN
ATGCGATGCTNGCN
ATGCGATGCNNNGC
ATGCGATGCTAGCG
```

#### Extended Query Format (with parameters)

```
# Query format: QUERY|mutations|max_variants
ATGCGATGCTAGCN|0|10000
ATGCGATGCTNGCN|1|50000
ATGCGATGCNNNGC|0|100000
ATGCGATGCTAGCG|2|25000
```

#### Comment and Metadata Format

```
# Comments start with #
# Metadata lines start with ##:
##:format=extended
##:default_mutations=1
##:default_max_variants=50000

# Regular queries
ATGCGATGCTAGCN
ATGCGATGCTNGCN|2|100000

# Section separator
---
##:section=experiment1
ATGCGATGCTAGCG|0|10000
ATNNGATGCTNGCN|1|50000
```

## Batch Processing Options

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `--format` | Input file format | `enum` | `simple` |
| `--default-mutations` | Default mutation tolerance | `usize` | `0` |
| `--default-max-variants` | Default max variants | `usize` | `10000` |
| `--fail-fast` | Stop on first error | `bool` | `false` |
| `--continue-on-error` | Continue processing after errors | `bool` | `true` |
| `--error-log` | File to log errors | `string` | stderr |
| `--progress` | Show progress bar | `bool` | `true` |
| `--progress-format` | Progress bar format | `enum` | `bar` |
| `--chunk-size` | Number of queries to process in parallel | `usize` | `100` |
| `--output-format` | Output format for results | `enum` | `table` |
| `--separate-files` | Output each query to separate file | `bool` | `false` |

### Format Options

- `simple`: One query per line
- `extended`: Query with parameters
- `json`: JSON array of queries
- `csv`: CSV format with headers

### Progress Format Options

- `bar`: Progress bar with percentage
- `simple`: Simple counter (Query 5/1000)
- `detailed`: Detailed progress with timing
- `none`: No progress output

## Input Specifications

### Simple Format

```bash
# Each line is a query
ATGCGATGCTAGCN
ATGCGATGCTNGCN
ATGCGATGCTAGCG
```

### Extended Format

```bash
# Format: QUERY|mutations|max_variants|batch_size|parallel
ATGCGATGCTAGCN|0|10000|1000|true
ATGCGATGCTNGCN|1|50000|2000|true
ATGCGATGCNNNGC|0|100000|500|false
```

### JSON Format

```json
[
  {
    "query": "ATGCGATGCTAGCN",
    "mutations": 0,
    "max_variants": 10000,
    "metadata": { "experiment": "exp1", "sample": "s1" }
  },
  {
    "query": "ATGCGATGCTNGCN",
    "mutations": 1,
    "max_variants": 50000,
    "metadata": { "experiment": "exp1", "sample": "s2" }
  }
]
```

### CSV Format

```csv
query,mutations,max_variants,batch_size,parallel,experiment,sample
ATGCGATGCTAGCN,0,10000,1000,true,exp1,s1
ATGCGATGCTNGCN,1,50000,2000,true,exp1,s2
```

## Output Specifications

### Table Format Output

```
# Query Batch Results
Database: database.rkdb
Total Queries: 1000
Processed: 1000
Errors: 0
Total Time: 2.34s

┌─────┬─────────────────────┬───────┬───────┬──────────┬──────────┬─────────┐
│ #   │ Query               │ Vars  │ Mut   │ Matches  │ Time(ms) │ Status  │
├─────┼─────────────────────┼───────┼───────┼──────────┼──────────┼─────────┤
│ 1   │ ATGCGATGCTAGCN       │ 4     │ 0     │ 15       │ 12       │ Success │
│ 2   │ ATGCGATGCTNGCN       │ 16    │ 0     │ 42       │ 45       │ Success │
│ 3   │ ATGCGATGCNNNGC       │ 64    │ 0     │ 8        │ 156      │ Success │
└─────┴─────────────────────┴───────┴───────┴──────────┴──────────┴─────────┘

Summary:
├─ Total Variants Generated: 84
├─ Total Matches Found: 65
├─ Average Query Time: 17ms
├─ Memory Usage: 45.2MB peak
└─ Cache Hit Rate: 23%
```

### JSON Format Output

```json
{
  "batch_metadata": {
    "database": "database.rkdb",
    "total_queries": 1000,
    "processed_queries": 1000,
    "failed_queries": 0,
    "total_time_ms": 2340,
    "database_size": 1250000000
  },
  "query_results": [
    {
      "query_id": 1,
      "query_string": "ATGCGATGCTAGCN",
      "parameters": {
        "mutations": 0,
        "max_variants": 10000,
        "enable_parallel": true
      },
      "results": {
        "total_count": 15,
        "variants_generated": 4,
        "individual_matches": [
          {
            "sequence": "ATGCGATGCTAGCA",
            "count": 5,
            "match_type": "WildcardExpansion"
          }
        ],
        "query_time_ms": 12,
        "status": "Success"
      }
    }
  ],
  "performance_summary": {
    "total_variants_generated": 84,
    "total_matches_found": 65,
    "average_query_time_ms": 17,
    "peak_memory_mb": 45.2,
    "cache_hit_rate": 0.23,
    "parallel_efficiency": 0.87
  },
  "errors": []
}
```

### CSV Format Output

```csv
query_id,query_string,mutations,max_variants,variants_generated,total_matches,query_time_ms,status
1,ATGCGATGCTAGCN,0,10000,4,15,12,Success
2,ATGCGATGCTNGCN,0,10000,16,42,45,Success
3,ATGCGATGCNNNGC,0,10000,64,8,156,Success
```

## Error Handling and Recovery

### Error Types

| Error | Description | Recovery Action |
|-------|-------------|-----------------|
| InvalidQueryFormat | Query format is invalid | Skip query, log error |
| InvalidQueryCharacters | Query contains invalid characters | Skip query, log error |
| TooManyVariants | Query exceeds variant limit | Skip query, suggest increase limit |
| DatabaseError | Database access error | Retry 3 times, then skip |
| MemoryError | Insufficient memory | Reduce chunk size, retry |
| TimeoutError | Query timeout | Skip query, log timeout |

### Error Logging

When `--error-log` is specified:

```
2025-11-28 10:15:32 ERROR [Query 45] Invalid query 'ATGCGX': contains invalid character 'X'
2025-11-28 10:15:33 WARN  [Query 89] Query would generate 50000 variants (exceeds limit of 10000)
2025-11-28 10:15:34 ERROR [Query 123] Database timeout after 30s
```

### Recovery Strategies

#### Automatic Recovery

1. **Retry Logic**: Automatically retry failed database queries (up to 3 times)
2. **Chunk Size Adaptation**: Reduce chunk size on memory errors
3. **Progressive Fallback**: Disable parallel processing if it causes issues

#### User-Configurable Recovery

```bash
# Continue processing despite errors
rustkmer fuzzy-query-batch database.rkdb queries.txt --continue-on-error

# Stop on first error for debugging
rustkmer fuzzy-query-batch database.rkdb queries.txt --fail-fast

# Log errors to separate file
rustkmer fuzzy-query-batch database.rkdb queries.txt --error-log errors.log
```

## Performance Optimization

### Parallel Processing

#### Chunk-Based Processing

```bash
# Process 100 queries in parallel chunks
rustkmer fuzzy-query-batch database.rkdb queries.txt --chunk-size 100
```

#### Memory Management

```bash
# Limit memory usage by reducing chunk size
rustkmer fuzzy-query-batch database.rkdb queries.txt --chunk-size 10
```

#### Resource Limits

```bash
# Set custom limits
rustkmer fuzzy-query-batch database.rkdb queries.txt \
  --default-max-variants 50000 \
  --chunk-size 50 \
  --max-memory-mb 2048
```

### Caching Strategy

- **Query Result Cache**: Cache results for identical queries
- **Database Cache**: Maintain database index in memory
- **Variant Cache**: Cache generated variants for repeated queries

### Progress Monitoring

#### Real-time Progress

```
Processing Query 523/1000 (52.3%) [██████████████████████████████████████] 23.4/s ETA: 20s
Memory: 45.2MB | Cache: 23% | Errors: 0
```

#### Detailed Progress

```
=== Batch Processing Progress ===
Current Query: ATGCGATGCTNGCN (Query 523/1000)
├─ Generated: 16/16 variants
├─ Queried: 12/16 database lookups
└─ Found: 8 matches so far

Overall Statistics:
├─ Total Time: 2m 15.3s
├─ Queries/Second: 7.4
├─ Memory Usage: 45.2MB peak
├─ Cache Hit Rate: 23%
└─ Error Rate: 0.0%

Estimated Time Remaining: 20s
```

## Examples

### Basic Batch Processing

```bash
# Simple batch processing
rustkmer fuzzy-query-batch database.rkdb queries.txt

# With custom output
rustkmer fuzzy-query-batch database.rkdb queries.txt \
  --format json \
  --output results.json \
  --progress
```

### Advanced Batch Processing

```bash
# Extended format with custom parameters
rustkmer fuzzy-query-batch database.rkdb queries_extended.txt \
  --format extended \
  --default-mutations 1 \
  --default-max-variants 50000

# High-performance batch processing
rustkmer fuzzy-query-batch database.rkdb large_query_set.txt \
  --chunk-size 200 \
  --max-memory-mb 4096 \
  --progress-format detailed
```

### Error Handling and Recovery

```bash
# Robust batch processing with error handling
rustkmer fuzzy-query-batch database.rkdb queries.txt \
  --continue-on-error \
  --error-log batch_errors.log \
  --fail-fast

# Debug problematic queries
rustkmer fuzzy-query-batch database.rkdb queries.txt \
  --chunk-size 1 \
  --verbose
```

This contract provides comprehensive specifications for batch processing, ensuring scalability, reliability, and performance for large-scale fuzzy query operations.