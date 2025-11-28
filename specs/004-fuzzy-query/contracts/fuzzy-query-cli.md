# API Contract: Fuzzy Query CLI

**Feature**: Fuzzy Query with Wildcard Support
**Version**: 1.0.0
**Date**: 2025-11-28

## Command Interface

### Main Command: `fuzzy-query`

```bash
rustkmer fuzzy-query [OPTIONS] <DATABASE> <QUERY>
```

#### Required Arguments

- `<DATABASE>`: Path to RKDB database file
- `<QUERY>`: Query string (may contain 'N' wildcards)

#### Optional Arguments

| Option | Short | Description | Type | Default |
|--------|-------|-------------|------|---------|
| `--mutations` | `-m` | Maximum Hamming distance for mutations | `usize` | `0` |
| `--max-variants` | `M` | Maximum number of variants to generate | `usize` | `10000` |
| `--parallel` | `-p` | Enable parallel processing | `bool` | `true` |
| `--batch-size` | `-b` | Batch size for processing variants | `usize` | `1000` |
| `--output` | `-o` | Output file path | `string` | stdout |
| `--format` | `-f` | Output format | `enum` | `table` |
| `--verbose` | `-v` | Enable verbose output | `bool` | `false` |
| `--quiet` | `-q` | Suppress non-error output | `bool` | `false` |
| `--profile` | | Show performance profiling | `bool` | `false` |
| `--help` | `-h` | Show help message | | |

#### Format Options

- `table`: Human-readable table format
- `json`: Machine-readable JSON format
- `tsv`: Tab-separated values
- `csv`: Comma-separated values

### Batch Query Command: `fuzzy-query-batch`

```bash
rustkmer fuzzy-query-batch [OPTIONS] <DATABASE> <QUERY_FILE>
```

#### Required Arguments

- `<DATABASE>`: Path to RKDB database file
- `<QUERY_FILE>`: File containing queries (one per line)

#### Optional Arguments

Same as `fuzzy-query` plus:

| Option | Short | Description | Type | Default |
|--------|-------|-------------|------|---------|
| `--include-headers` | | Include header row in CSV/TSV output | `bool` | `false` |
| `--progress` | | Show progress bar for batch processing | `bool` | `true` |
| `--fail-fast` | | Stop on first error | `bool` | `false` |

## Input Specifications

### Query File Format (for batch queries)

```
# Lines starting with # are comments
ATGCGATGCTAGCN  # Single wildcard
ATGCGATGCTNGCN  # Two wildcards
ATGCGATGCTAGCG  # Exact match
```

**Constraints**:
- One query per line (excluding comments)
- Queries may contain A,T,C,G,N characters only
- Empty lines are ignored
- Maximum line length: 1000 characters

### Query String Validation

```bash
# Valid queries
ATGCGATGCTAGCN    # Single wildcard
ATNNGATGCTAGCG    # Two wildcards
ATGCGATGCTAGCG    # Exact match
N                 # Single wildcard (length 1)

# Invalid queries (will produce validation errors)
ATGCGXATGCTAGC    # Invalid character X
                  # Empty string
ATGCGATGCTAGCGATGCGATGCTAGCGATGCGATGCTAGCGATGCGATGCTAGC  # Too long
```

## Output Specifications

### Table Format (default)

```
Query: ATGCGATGCTAGCN
Mutations: 0
Variants Generated: 4
Total Matches: 15
Query Time: 23ms

┌─────────────────────┬───────┬─────────┬─────────────────┐
│ Sequence            │ Count │ Type    │ Hamming Distance │
├─────────────────────┼───────┼─────────┼─────────────────┤
│ ATGCGATGCTAGCA      │ 5     │ Wildcard│ 0               │
│ ATGCGATGCTAGCT      │ 3     │ Wildcard│ 0               │
│ ATGCGATGCTAGCC      │ 4     │ Wildcard│ 0               │
│ ATGCGATGCTAGCG      │ 3     │ Exact   │ 0               │
└─────────────────────┴───────┴─────────┴─────────────────┘
```

### JSON Format

```json
{
  "query": {
    "string": "ATGCGATGCTAGCN",
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
        "match_type": "WildcardExpansion",
        "wildcard_positions": [12],
        "hamming_distance": 0
      },
      {
        "sequence": "ATGCGATGCTAGCT",
        "count": 3,
        "match_type": "WildcardExpansion",
        "wildcard_positions": [12],
        "hamming_distance": 0
      }
    ]
  },
  "metadata": {
    "query_time_ms": 23,
    "database_size": 1250000000,
    "kmer_size": 13,
    "memory_usage_mb": 12.4
  },
  "status": "Success"
}
```

### CSV/TSV Format

```
query,sequence,count,match_type,hamming_distance
ATGCGATGCTAGCN,ATGCGATGCTAGCA,5,WildcardExpansion,0
ATGCGATGCTAGCN,ATGCGATGCTAGCT,3,WildcardExpansion,0
```

## Performance Profiling Output (when --profile used)

```
=== Performance Profile ===
Total Query Time: 23.4ms
├─ Variant Generation: 2.1ms (4 variants)
├─ Database Queries: 18.7ms (4 queries)
│  ├─ Avg per query: 4.7ms
│  └─ Cache hits: 1/4 (25%)
└─ Result Aggregation: 2.6ms

Memory Usage:
├─ Peak: 15.2MB
├─ Variants: 0.1MB
└─ Results: 0.3MB

Parallel Processing:
├─ Worker threads: 4
├─ Parallel efficiency: 87%
└─ Load balance score: 0.92
```

## Error Handling

### Error Codes and Messages

| Code | Description | Example Output |
|------|-------------|----------------|
| `E001` | Invalid database file | `Error E001: Cannot open database file: No such file or directory` |
| `E002` | Invalid query string | `Error E002: Invalid query 'ATGCGX': contains invalid character 'X'` |
| `E003` | Too many variants | `Error E003: Query would generate 65000 variants (exceeds limit of 10000). Use --max-variants to increase limit.` |
| `E004` | Database corruption | `Error E004: Database file appears to be corrupted: invalid header` |
| `E005` | Memory limit exceeded | `Error E005: Memory limit exceeded. Try reducing --mutations or --max-variants` |
| `E006` | Invalid parameter combination | `Error E006: Cannot specify both --quiet and --verbose` |

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Database error
- `4`: Memory/resource error
- `130`: User interrupt (Ctrl+C)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RUSTKMER_MAX_THREADS` | Maximum number of worker threads | `num_cpus::get()` |
| `RUSTKMER_MEMORY_LIMIT_MB` | Memory limit for operations | `1024` |
| `RUSTKMER_CACHE_SIZE` | Database cache size | `1000000` |
| `RUSTKMER_LOG_LEVEL` | Logging level | `warn` |

### Configuration File (optional)

Create `~/.rustkmer/config.toml`:

```toml
[fuzzy_query]
default_max_variants = 10000
default_batch_size = 1000
enable_parallel = true
memory_limit_mb = 1024

[performance]
cache_size = 1000000
max_threads = 8

[output]
default_format = "table"
include_metadata = true
```

## Examples

### Basic Wildcard Query

```bash
# Single wildcard query
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN"

# Two wildcards with custom limit
rustkmer fuzzy-query database.rkdb "ATNNGATGCTAGCG" --max-variants 100000

# Query with mutation tolerance
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCG" --mutations 1
```

### Batch Processing

```bash
# Process queries from file
rustkmer fuzzy-query-batch database.rkdb queries.txt

# Custom output format
rustkmer fuzzy-query-batch database.rkdb queries.txt --format json --output results.json

# With performance profiling
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --profile
```

### Advanced Usage

```bash
# Combination of wildcards and mutations
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --mutations 1 --max-variants 50000

# Parallel processing control
rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" --parallel --batch-size 500

# Verbose output for debugging
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --verbose --profile
```

This contract provides a comprehensive specification for the fuzzy query CLI interface, ensuring consistency, usability, and robust error handling.