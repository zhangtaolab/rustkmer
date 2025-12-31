# Prefix Query Usage Guide

## Overview

The `prefix-query` command provides efficient prefix-based k-mer extraction for sorted RKDB databases. It leverages memory block optimization to achieve significant performance improvements over traditional fuzzy-query methods for specific patterns.

## Quick Start

### Basic Usage

```bash
# Find all k-mers starting with "ATCG"
rustkmer prefix-query database.rkdb "ATCG"

# Save results to file
rustkmer prefix-query database.rkdb "ATCG" --output results.txt

# Use different output formats
rustkmer prefix-query database.rkdb "ATCG" --format json
rustkmer prefix-query database.rkdb "ATCG" --format csv
rustkmer prefix-query database.rkdb "ATCG" --format tsv
```

### Command Options

```
Usage: rustkmer prefix-query [OPTIONS] <DATABASE> <PREFIX>

Arguments:
  <DATABASE>  Path to RKDB database file
  <PREFIX>    Prefix sequence to match (must be A, T, C, G only)

Options:
  -f, --format <FORMAT>        Output format (table, json, csv, tsv) [default: table]
  -o, --output <OUTPUT>        Output file (stdout if not specified)
  -v, --verbose                Enable verbose output
  -q, --quiet                  Suppress non-error output
      --profile                Show performance profiling
  -L, --min-count <MIN_COUNT>  Minimum count threshold
  -U, --max-count <MAX_COUNT>  Maximum count threshold
  -h, --help                   Print help
```

## Examples

### Example 1: Basic Prefix Query

```bash
# Find all 19-mers starting with "ATG"
rustkmer prefix-query genome_database.rkdb "ATG"
```

**Output:**
```
K-mer                Count
ATGCGTACGTTAGCTA     15
ATGCGTACGTTAGCTG     23
ATGCGTACGTTAGCTT     8
...
```

### Example 2: JSON Output with Filtering

```bash
# Get results in JSON format with minimum count
rustkmer prefix-query database.rkdb "AAAAA" --format json --min-count 5
```

**Output:**
```json
{
  "query": {
    "prefix": "AAAAA",
    "database": "genome_database.rkdb"
  },
  "results": {
    "matches": [
      {"kmer": "AAAAATTTTT", "count": 15},
      {"kmer": "AAAAACCCCC", "count": 8}
    ],
    "total_matches": 2
  },
  "performance": {
    "memory_block": {
      "start_index": 1250,
      "end_index": 1350,
      "block_size": 100,
      "is_sorted": true
    }
  }
}
```

### Example 3: Performance Profiling

```bash
# Enable performance profiling for optimization analysis
rustkmer prefix-query database.rkdb "ATG" --profile
```

**Output:**
```
K-mer                Count
ATGCGTACGTTAGCTA     15
...

=== Performance Profile ===
Query time: 15.2ms
Matches found: 1,247
Memory block: [1250, 1300) - 50 k-mers
Database sorted: true
Optimization enabled: Yes
Performance gain: ~10-100x vs fuzzy-query for prefix patterns
```

### Example 4: CSV Output for Analysis

```bash
# Export results to CSV for further analysis
rustkmer prefix-query database.rkdb "AAAAA" --format csv --output results.csv
```

## Pattern Selection Guide

### When to Use Prefix Query

| Pattern Type | Example | Recommended Method |
|--------------|---------|-------------------|
| Pure Prefix | `AAAANNN` | `prefix-query` |
| Hybrid | `AAANNNAAA` | `prefix-query` (truncated) |
| Complex | `AANNNCCC` | `fuzzy-query` |
| Suffix | `NNNAAA` | `suffix-query` |

### Performance Expectations

- **Small databases (< 10K k-mers)**: Similar or slightly slower than fuzzy-query
- **Medium databases (10K - 1M k-mers)**: Comparable performance
- **Large databases (> 1M k-mers)**: 10-100x faster for appropriate patterns

## Advanced Usage

### Combining with Other Tools

```bash
# Pipe results to other tools
rustkmer prefix-query database.rkdb "ATG" --quiet | head -10

# Use with grep for additional filtering
rustkmer prefix-query database.rkdb "ATG" --quiet | grep "count.*[5-9][0-9]"
```

### Batch Processing

```bash
# Process multiple prefixes
for prefix in ATG CTG GTG TTA TAA; do
    rustkmer prefix-query database.rkdb "$prefix" --output "${prefix}_results.txt"
done
```

### Performance Analysis

```bash
# Compare with fuzzy-query timing
time rustkmer prefix-query database.rkdb "ATG" --quiet
time rustkmer fuzzy-query database.rkdb "ATG" --quiet
```

## Error Handling

### Common Errors and Solutions

#### 1. Empty Prefix
```bash
$ rustkmer prefix-query database.rkdb ""
Error: Prefix cannot be empty
```

**Solution**: Provide a non-empty prefix sequence.

#### 2. Invalid Characters
```bash
$ rustkmer prefix-query database.rkdb "ATGN"
Error: Prefix contains invalid characters: ATGN. Only A, T, C, G are allowed.
```

**Solution**: Use only A, T, C, G characters.

#### 3. Prefix Too Long
```bash
$ rustkmer prefix-query database.rkdb "ATCGATCGATCGATCGATCG"
Error: Prefix length (20) must be less than k-mer size (19)
```

**Solution**: Ensure prefix is shorter than k-mer size.

#### 4. Database Not Found
```bash
$ rustkmer prefix-query nonexistent.rkdb "ATG"
Error: File not found: nonexistent.rkdb
```

**Solution**: Check database file path and existence.

## Performance Tips

### 1. Use Sorted Databases
- Ensure your RKDB database was created with `--sort` (default)
- Sorted databases enable binary search optimization

### 2. Choose Appropriate Patterns
- Pure prefixes: `AAAA`, `ATCG`, `GCGC`
- Hybrid patterns: `AAANNN` (use first part: `AAA`)
- Avoid complex patterns: use `fuzzy-query` instead

### 3. Enable Profiling
- Use `--profile` to analyze performance
- Monitor query time and memory block information

### 4. Consider Database Size
- Small databases: overhead may not be justified
- Large databases: significant performance gains expected

## Integration with Python API

### Using the Python Interface

```python
import rustkmer_pyo3

# Load database
db = rustkmer_pyo3.PyDatabase("database.rkdb")

# Extract by prefix
results = db.extract_by_prefix("ATG")

# Results format: {"kmer": "ATG...", "count": N}
for kmer, count in results.items():
    print(f"{kmer}: {count}")
```

## Troubleshooting

### Performance Issues

1. **Slow Performance**: 
   - Check if database is sorted
   - Verify prefix pattern is appropriate
   - Consider database size

2. **No Results**:
   - Verify prefix exists in database
   - Check count filtering parameters
   - Ensure prefix format is correct

3. **Memory Issues**:
   - Large databases may require more memory
   - Consider using `--quiet` to reduce output overhead

### Debug Mode

```bash
# Enable verbose output for debugging
rustkmer prefix-query database.rkdb "ATG" --verbose
```

This provides detailed information about:
- Database loading process
- Query optimization steps
- Memory block boundaries
- Performance metrics

## Summary

The `prefix-query` command is a powerful tool for efficient k-mer extraction when dealing with prefix patterns in sorted databases. It provides significant performance improvements for large-scale genomic analysis workflows, especially when dealing with repetitive sequences or specific motif searches.

Key benefits:
- **High Performance**: Optimized for large, sorted databases
- **Flexible Output**: Multiple format options
- **Comprehensive Filtering**: Count-based filtering
- **Performance Monitoring**: Built-in profiling
- **User-Friendly**: Intuitive CLI interface

For complex patterns or small databases, consider using `fuzzy-query` or other query methods for optimal results.
