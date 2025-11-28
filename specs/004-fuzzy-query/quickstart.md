# Quick Start Guide: Fuzzy Query System

**Feature**: Fuzzy Query with Wildcard Support
**Version**: 1.0.0
**Date**: 2025-11-28

## Overview

The RustKmer fuzzy query system enables flexible k-mer searching with wildcard support, length normalization, and mutation tolerance. This guide will help you get started quickly with the key features.

## Prerequisites

- Rust 1.80+ stable channel
- Built RKDB database with k-mer data
- Terminal/command line access

## Installation

```bash
# Clone the repository with fuzzy query feature
git clone -b 004-fuzzy-query https://github.com/your-org/rustkmer.git
cd rustkmer

# Build the project
cargo build --release

# The binary will be available at target/release/rustkmer
```

## Quick Start Examples

### 1. Basic Wildcard Query

```bash
# Query with single wildcard (N → A,T,C,G)
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN"

# Expected output:
# Query: ATGCGATGCTAGCN
# Variants Generated: 4
# Total Matches: 15
# ┌─────────────────────┬───────┬─────────┐
# │ Sequence            │ Count │ Type    │
# ├─────────────────────┼───────┼─────────┤
# │ ATGCGATGCTAGCA      │ 5     │ Wildcard│
# │ ATGCGATGCTAGCT      │ 3     │ Wildcard│
# │ ATGCGATGCTAGCC      │ 4     │ Wildcard│
# │ ATGCGATGCTAGCG      │ 3     │ Exact   │
# └─────────────────────┴───────┴─────────┘
```

### 2. Multiple Wildcards

```bash
# Query with two wildcards (16 combinations)
./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTAGCG"

# Query with three wildcards (64 combinations)
./target/release/rustkmer fuzzy-query database.rkdb "ATGCNATGCTNGCN"
```

### 3. Mutation Tolerance

```bash
# Allow 1 mutation (Hamming distance ≤ 1)
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCG" --mutations 1

# Allow 2 mutations
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCG" --mutations 2
```

### 4. Combined Wildcards + Mutations

```bash
# Wildcard expansion with mutation tolerance
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --mutations 1
```

### 5. Batch Processing

```bash
# Create a query file
cat > queries.txt << EOF
ATGCGATGCTAGCN
ATGCGATGCTNGCN
ATGCGATGCNNNGC
ATGCGATGCTAGCG
EOF

# Process all queries
./target/release/rustkmer fuzzy-query-batch database.rkdb queries.txt
```

## Common Use Cases

### Biological Sequence Analysis

```bash
# Find variants of a known motif
./target/release/rustkmer fuzzy-query genome.rkdb "ATGCGATGCTAGCN" --mutations 1

# Search with ambiguous bases (N = unknown)
./target/release/rustkmer fuzzy-query genome.rkdb "ATGCGATGCTNGCN"

# Handle sequence length differences
./target/release/rustkmer fuzzy-query genome.rkdb "ATGCGATGCTAG"  # 12-mer for 13-mer DB
```

### Performance Testing

```bash
# Single wildcard query with profiling
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --profile

# Batch processing with progress
./target/release/rustkmer fuzzy-query-batch database.rkdb queries.txt --progress

# High-performance settings
./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" \
  --max-variants 100000 --parallel --batch-size 2000
```

## Output Formats

### Table Format (Default)

Human-readable table with detailed match information.

```bash
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --format table
```

### JSON Format

Machine-readable format for programmatic use.

```bash
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --format json
```

### CSV Format

Tabular format for spreadsheet analysis.

```bash
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --format csv
```

## Performance Tips

### Memory Optimization

```bash
# Limit variant generation for memory efficiency
./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" --max-variants 1000

# Reduce batch size for large queries
./target/release/rustkmer fuzzy-query-batch database.rkdb queries.txt --chunk-size 10
```

### Speed Optimization

```bash
# Enable parallel processing (default)
./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" --parallel

# Increase batch size for better parallelism
./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" --batch-size 2000
```

### Large Database Handling

```bash
# Process in chunks for very large databases
./target/release/rustkmer fuzzy-query-batch large_database.rkdb queries.txt \
  --chunk-size 50 --progress-format detailed
```

## Troubleshooting

### Common Issues

1. **"Too many variants" Error**
   ```bash
   # Increase the limit
   ./target/release/rustkmer fuzzy-query database.rkdb "ATNNNNATGCTNGCN" --max-variants 1000000
   ```

2. **Memory Issues**
   ```bash
   # Reduce parallelism and batch size
   ./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" \
     --batch-size 100 --max-variants 5000
   ```

3. **Slow Performance**
   ```bash
   # Enable profiling to identify bottlenecks
   ./target/release/rustkmer fuzzy-query database.rkdb "ATNNGATGCTNGCN" --profile
   ```

### Getting Help

```bash
# Show help for fuzzy query
./target/release/rustkmer fuzzy-query --help

# Show help for batch processing
./target/release/rustkmer fuzzy-query-batch --help

# Enable verbose output for debugging
./target/release/rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --verbose
```

## Advanced Features

### Custom Query Parameters

```bash
# Extended format batch processing
cat > extended_queries.txt << EOF
##:format=extended
##:default_mutations=1
ATGCGATGCTAGCN|0|10000
ATGCGATGCTNGCN|2|50000
ATGCGATGCTAGCG|1|25000
EOF

./target/release/rustkmer fuzzy-query-batch database.rkdb extended_queries.txt --format extended
```

### Performance Benchmarking

```bash
# Create test queries
for i in {1..1000}; do
  echo "ATGCGATGCTAGCN" >> test_queries.txt
done

# Benchmark batch processing
time ./target/release/rustkmer fuzzy-query-batch database.rkdb test_queries.txt --profile
```

### Integration with Scripts

```bash
#!/bin/bash
# Example script for processing multiple databases

for db in *.rkdb; do
  echo "Processing $db..."
  ./target/release/rustkmer fuzzy-query-batch "$db" queries.txt \
    --format json \
    --output "results_${db%.rkdb}.json" \
    --progress
done
```

## Next Steps

1. **Explore Documentation**: Read the full specification in `spec.md`
2. **Run Tests**: Execute `cargo test` to verify installation
3. **Performance Tuning**: Use `--profile` to optimize for your data
4. **Integration**: Incorporate into your bioinformatics workflows

## Support

- Documentation: `specs/004-fuzzy-query/`
- Examples: `examples/`
- Issues: GitHub repository issues
- Performance: Use `--profile` flag for detailed metrics

This quick start guide covers the essential features of the fuzzy query system. For more advanced usage and detailed specifications, refer to the complete documentation.