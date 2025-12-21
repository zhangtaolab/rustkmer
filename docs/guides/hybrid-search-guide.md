# Hybrid Search Usage Guide

## Overview

The hybrid search functionality extends the existing `prefix-query` command to support complex search patterns with specified head and tail sequences. This feature leverages RKDB sorting characteristics for efficient querying of patterns like `ATAC{N5}ACAC`.

## Basic Usage

### Hybrid Pattern Format

Hybrid search uses the following format: `PREFIX{N_COUNT}SUFFIX`

Where:
- `PREFIX`: Fixed sequence at the beginning (A, T, C, G only)
- `N_COUNT`: Number of wildcard positions (N or {N_number})
- `SUFFIX`: Fixed sequence at the end (A, T, C, G only)

### Examples

```bash
# Find 10-mers starting with "ATAC", followed by 5 wildcards, ending with "GTAC"
rustkmer prefix-query database.rkdb "ATAC{N5}GTAC"

# Shorthand notation for single N
rustkmer prefix-query database.rkdb "ATAC{N}GTAC"

# Different N counts
rustkmer prefix-query database.rkdb "ATG{N3}CGA"  # 3 wildcards
rustkmer prefix-query database.rkdb "ATG{N8}CGA"  # 8 wildcards
```

## Command Options

### New Parameters

```bash
# Pattern parameter (supports hybrid format)
--pattern "ATAC{N5}GTAC"

# Explicit prefix parameter (simple sequences only)
--prefix "ATAC"

# Enable hybrid search mode explicitly
--hybrid

# Output format options
--format table|json|csv|tsv

# Performance and filtering options
--profile          # Show performance profiling
--min-count N      # Minimum count threshold
--max-count N      # Maximum count threshold
--verbose          # Verbose output
--quiet            # Suppress non-error output
```

### Parameter Relationships

- `--pattern` and `--prefix` are mutually exclusive
- `--hybrid` requires `--pattern` to be specified
- Auto-detection: If `--pattern` contains `{`, hybrid mode is automatically enabled

## Usage Examples

### 1. Basic Hybrid Search

```bash
# Simple hybrid pattern
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA"

# With output formatting
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --format json
```

### 2. Performance Profiling

```bash
# Enable performance profiling
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --profile
```

**Output:**
```
K-mer                Count
ATGCGTACGTA          15
ATGCGTACGTC          23
...

=== Performance Profile ===
Query time: 12.5ms
Matches found: 1,247
Memory block: [1250, 1300) - 50 k-mers
Database sorted: true
Optimization enabled: Yes
Performance gain: ~10-50x vs fuzzy-query for hybrid patterns
```

### 3. Count Filtering

```bash
# Filter by minimum count
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --min-count 10

# Filter by count range
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --min-count 5 --max-count 100
```

### 4. Multiple Output Formats

```bash
# JSON format with detailed metadata
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --format json

# CSV format for spreadsheet analysis
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --format csv --output results.csv

# TSV format for text processing
rustkmer prefix-query genome_db.rkdb "ATG{N5}TGA" --format tsv
```

### 5. Batch Processing

```bash
# Process multiple patterns
for pattern in "ATG{N3}TGA" "CTG{N4}TAA" "GTG{N2}CCA"; do
    rustkmer prefix-query genome_db.rkdb "$pattern" --output "${pattern}_results.txt"
done
```

## Pattern Validation

### Valid Patterns

- `ATCG{N5}GCTA`: 4-prefix + 5-wildcards + 4-suffix = 13-mer
- `A{N}G`: 1-prefix + 1-wildcard + 1-suffix = 3-mer
- `{N10}GCTA`: 0-prefix + 10-wildcards + 4-suffix = 14-mer
- `ATCG{N}`: 4-prefix + 1-wildcard + 0-suffix = 5-mer

### Invalid Patterns

- `ATCN{N3}GCTA`: Contains invalid character 'N' in prefix
- `ATCG{N20}G`: N count exceeds k-mer size
- `ATCG{N-1}GCTA`: Negative N count
- `ATCG{Nabc}GCTA`: Non-numeric N count

## Algorithm Details

### Memory Block Optimization

Hybrid search leverages RKDB sorting characteristics:

1. **Prefix-based Binary Search**: Uses the fixed prefix to locate memory blocks efficiently
2. **Batch Processing**: Processes contiguous memory blocks instead of individual k-mers
3. **Suffix Filtering**: Filters results by suffix match
4. **Pattern Validation**: Validates complete pattern match including N positions

### Performance Characteristics

| Pattern Type | Example | Expected Speedup vs Fuzzy-Query |
|--------------|---------|--------------------------------|
| Simple Prefix | `AAAANNN` | 50-100x |
| Hybrid | `AAANNNAAA` | 10-50x |
| Suffix | `NNNAAA` | 1-5x |
| Complex | `AANNNCCC` | 5-20x |

### Memory Usage

- **Small Databases (< 10K k-mers)**: Overhead may not be justified
- **Medium Databases (10K - 1M k-mers)**: Moderate performance gains
- **Large Databases (> 1M k-mers)**: Significant performance improvements

## Comparison with Other Methods

### Hybrid Search vs Fuzzy-Query

| Feature | Hybrid Search | Fuzzy-Query |
|---------|---------------|-------------|
| Pattern Format | `ATAC{N5}GTAC` | `ATACNNNNNGTAC` |
| Optimization | Memory block access | Variant generation |
| Best Use Case | Large sorted databases | Complex patterns, small databases |
| Performance | 10-50x faster | Slower for simple patterns |
| Memory Usage | Lower | Higher for many variants |

### Hybrid Search vs Prefix-Query

| Feature | Hybrid Search | Simple Prefix-Query |
|---------|---------------|---------------------|
| Pattern Support | Hybrid patterns | Prefix only |
| Algorithm | Prefix + suffix filtering | Pure prefix matching |
| Use Case | Complex head-tail patterns | Simple prefix extraction |
| Performance | Optimized for hybrid patterns | Optimized for prefixes |

## Error Handling

### Common Errors and Solutions

#### 1. Pattern Format Errors

```bash
# Invalid characters
$ rustkmer prefix-query db.rkdb "ATCN{N3}GCTA"
Error: Invalid characters in prefix: ATCN

# Solution: Use only A, T, C, G in prefix/suffix
```

#### 2. Size Mismatch

```bash
# Pattern longer than k-mer size
$ rustkmer prefix-query db.rkdb "ATCGATCG{N10}GCTA"
Error: Pattern length (18) does not match k-mer size (15)

# Solution: Adjust pattern to match database k-mer size
```

#### 3. Parameter Conflicts

```bash
# Conflicting parameters
$ rustkmer prefix-query db.rkdb --pattern "ATG{N5}TGA" --prefix "ATG"
Error: argument '--prefix' cannot be used with '--pattern'

# Solution: Use only one parameter type
```

#### 4. Empty Patterns

```bash
# Empty pattern
$ rustkmer prefix-query db.rkdb ""
Error: Pattern cannot be empty

# Solution: Provide valid pattern
```

## Best Practices

### 1. Pattern Design

- **Prefix Length**: Use longer prefixes (4+ bases) for better performance
- **Suffix Length**: Include meaningful suffixes when possible
- **N Count Balance**: Avoid too many wildcards (reduces filtering efficiency)

### 2. Performance Optimization

```bash
# Use sorted databases for optimal performance
rustkmer count --k 19 --input genome.fa --output genome.rkdb --sort

# Enable profiling to analyze performance
rustkmer prefix-query genome.rkdb "ATG{N5}TGA" --profile

# Use appropriate output formats for your use case
rustkmer prefix-query genome.rkdb "ATG{N5}TGA" --format json --quiet
```

### 3. Batch Operations

```bash
# Use shell scripting for multiple patterns
#!/bin/bash
patterns=("ATG{N3}TGA" "CTG{N4}TAA" "GTG{N2}CCA")
for pattern in "${patterns[@]}"; do
    rustkmer prefix-query genome.rkdb "$pattern" --output "${pattern}_results.txt" --quiet
done
```

## Integration Examples

### Python API

```python
import rustkmer_pyo3

# Load database
db = rustkmer_pyo3.PyDatabase("genome.rkdb")

# Extract by hybrid pattern
results = db.extract_by_prefix("ATG{N5}TGA")

# Process results
for kmer, count in results.items():
    print(f"{kmer}: {count}")
```

### Shell Scripting

```bash
#!/bin/bash
# Process multiple genomes with hybrid patterns

DATABASES=("human.rkdb" "mouse.rkdb" "rat.rkdb")
PATTERNS=("ATG{N3}TGA" "CTG{N4}TAA" "GTG{N2}CCA")

for db in "${DATABASES[@]}"; do
    for pattern in "${PATTERNS[@]}"; do
        output_file="${db%.*}_${pattern//[^A-Z0-9]/_}_results.txt"
        rustkmer prefix-query "$db" "$pattern" --output "$output_file" --quiet
    done
done
```

## Performance Monitoring

### Enable Detailed Profiling

```bash
rustkmer prefix-query genome.rkdb "ATG{N5}TGA" --profile --verbose
```

### Performance Metrics

- **Query Time**: Total execution time
- **Memory Block**: Range of k-mers processed
- **Match Count**: Number of matching k-mers found
- **Speedup Factor**: Performance improvement vs fuzzy-query

### Optimization Tips

1. **Database Size**: Larger databases benefit more from hybrid search
2. **Pattern Complexity**: Simpler patterns (fewer N's) perform better
3. **Database Sorting**: Ensure databases are sorted for optimal performance
4. **Memory Access**: Hybrid search optimizes memory block access patterns

## Troubleshooting

### Performance Issues

1. **Slow Performance**:
   - Check if database is sorted
   - Verify pattern complexity
   - Consider using simpler patterns

2. **No Results**:
   - Verify pattern exists in database
   - Check k-mer size compatibility
   - Ensure valid pattern format

3. **Memory Issues**:
   - Large databases may require more memory
   - Use `--quiet` to reduce output overhead

### Debug Mode

```bash
# Enable verbose output for debugging
rustkmer prefix-query genome.rkdb "ATG{N5}TGA" --verbose
```

This provides detailed information about:
- Database loading process
- Pattern parsing
- Memory block boundaries
- Performance metrics

## Summary

The hybrid search functionality provides a powerful and efficient way to search for complex k-mer patterns with specified head and tail sequences. By leveraging RKDB sorting characteristics and memory block optimization, it offers significant performance improvements over traditional fuzzy-query methods for appropriate patterns.

Key benefits:
- **Efficient Pattern Matching**: Optimized for hybrid head-tail patterns
- **Memory Block Access**: Leverages database sorting for fast queries
- **Flexible Format**: Support for various N count notations
- **Performance Monitoring**: Built-in profiling and optimization metrics
- **Easy Integration**: Seamless integration with existing workflows

For simple prefix patterns, use the basic prefix-query functionality. For complex patterns with scattered wildcards, consider using fuzzy-query for better results.
