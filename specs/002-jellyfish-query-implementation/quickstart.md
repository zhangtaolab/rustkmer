# Quickstart Guide: Jellyfish Query Implementation

**Version**: 1.0
**Date**: 2025-11-28
**Status**: Implemented

## Overview

This guide provides quick start instructions for using the new jellyfish-compatible query functionality in rustkmer. The query feature allows fast k-mer lookups from efficiently indexed databases.

## Prerequisites

- Rust 1.80+ stable channel
- Completed rustkmer build with query functionality
- Optional: Sample genomic data for testing

## Basic Usage

### 1. Create a Database

First, you need a k-mer database created with rustkmer count:

```bash
# Count k-mers from a FASTA file
rustkmer count -k 21 -o genome_k21.rkdb genome.fa

# Example with existing data
rustkmer count -k 13 --canonical -o reads_k13.rkdb reads.fastq
```

### 2. Query Individual K-mers

```bash
# Query a single k-mer
rustkmer query genome_k21.rkdb ATGCGATGCTAGCGCTAGCTA

# Output:
# ATGCGATGCTAGCGCTAGCTA	42
```

### 3. Query Multiple K-mers

```bash
# Query multiple k-mers in one command
rustkmer query genome_k21.rkdb ATGCGATGCTAGC GCTAGCTAGATGC TGCAGCTAGCTGA

# Output:
# ATGCGATGCTAGC	15
# GCTAGCTAGATGC	23
# TGCAGCTAGCTGA	0
```

### 4. Query from Sequence File

```bash
# Query all k-mers from a FASTA file
rustkmer query -s query_sequences.fa genome_k21.rkdb

# Output:
# ATGCGATGCTAGCGCTAGCTA	42
# TGCGATGCTAGCGCTAGCTAG	38
# GCGATGCTAGCGCTAGCTAGC	31
# ...
```

### 5. Interactive Query Mode

```bash
# Start interactive mode
rustkmer query -i genome_k21.rkdb

# Then enter k-mers one by line:
ATGCGATGCTAGCGCTAGCTA
# ATGCGATGCTAGCGCTAGCTA	42

TGCGATGCTAGCGCTAGCTAG
# TGCGATGCTAGCGCTAGCTAG	38

# Press Ctrl+D to exit
```

## Advanced Usage

### Memory Management

```bash
# Force pre-loading database into memory (faster for repeated queries)
rustkmer query -l genome_k21.rkdb ATGCGATGCTAGC

# Disable pre-loading (use less memory)
rustkmer query -L genome_k21.rkdb ATGCGATGCTAGC
```

### Output Redirection

```bash
# Save results to file
rustkmer query genome_k21.rkdb ATGCGATGCTAGC -o results.txt

# Append to existing file
rustkmer query genome_k21.rkdb GCTAGCTAGATGC >> results.txt
```

### Pipeline Integration

```bash
# Generate k-mers from another tool and query them
echo -e "ATGC\nTGCG\nCGAT" | rustkmer query -i genome_k21.rkdb

# Process results with other tools
rustkmer query genome_k21.rkdb ATGCGATGCTAGC | grep -v "Invalid"
```

## Common Workflows

### 1. Validate K-mer Presence

```bash
#!/bin/bash
# Check if specific k-mers are present in your data

DATABASE="genome_k21.rkdb"
KMERS=("ATGCGATGCTAGCGCTAGCTA" "TGCGATGCTAGCGCTAGCTAG" "GCGATGCTAGCGCTAGCTAGC")

echo "Checking k-mers in $DATABASE:"
for kmer in "${KMERS[@]}"; do
    result=$(rustkmer query "$DATABASE" "$kmer" 2>/dev/null)
    if [[ $result == *"0"* ]] || [[ -z "$result" ]]; then
        echo "$kmer: NOT FOUND"
    else
        echo "$kmer: FOUND ($result)"
    fi
done
```

### 2. Batch Processing

```bash
#!/bin/bash
# Process multiple query files

DATABASE="genome_k21.rkdb"
QUERY_DIR="queries/"
OUTPUT_DIR="results/"

mkdir -p "$OUTPUT_DIR"

for query_file in "$QUERY_DIR"/*.fa; do
    basename=$(basename "$query_file" .fa)
    echo "Processing $query_file..."
    rustkmer query -s "$query_file" "$DATABASE" -o "$OUTPUT_DIR/${basename}_results.txt"
done

echo "Batch processing complete. Results in $OUTPUT_DIR"
```

### 3. Performance Testing

```bash
#!/bin/bash
# Test query performance

DATABASE="genome_k21.rkdb"
TEST_KMER="ATGCGATGCTAGCGCTAGCTA"
ITERATIONS=10000

echo "Performance test: $ITERATIONS queries"
time for i in $(seq 1 $ITERATIONS); do
    rustkmer query "$DATABASE" "$TEST_KMER" > /dev/null
done
```

## Error Handling

### Common Errors and Solutions

**Error: "Database file not found"**
```bash
# Solution: Check file path and existence
ls -la genome_k21.rkdb
rustkmer query /full/path/to/genome_k21.rkdb ATGCGATGCTAGC
```

**Error: "Invalid mer 'XYZ'"**
```bash
# Solution: Check k-mer sequence contains only A,T,G,C
echo "ATGCGATGCTAGC" | grep -E "^[ATCGatcg]+$"
rustkmer query database.rkdb ATGCGATGCTAGC
```

**Error: "Invalid database magic number"**
```bash
# Solution: Verify file is a valid .rkdb database
rustkmer stats database.rkdb
# Or recreate the database
rustkmer count -k 21 -o database.rkdb input.fa
```

### Debugging Tips

```bash
# Check database information
rustkmer stats database.rkdb

# Test with a simple k-mer
rustkmer query database.rkdb AAAAAAAAAAAAAAAAAAAAA

# Use verbose mode (if available)
rustkmer query database.rkdb ATGCGATGCTAGC --verbose

# Validate database integrity
# rustkmer validate database.rkdb  # (future feature)
```

## Performance Tips

### For Large Databases

```bash
# Use memory pre-loading for repeated queries
rustkmer query -l large_database.rkdb kmer1

# Process k-mers in batches for better cache locality
echo -e "kmer1\nkmer2\nkmer3" | rustkmer query -i database.rkdb
```

### For Memory-Constrained Systems

```bash
# Disable pre-loading to reduce memory usage
rustkmer query -L database.rkdb kmer1

# Process smaller chunks of data
rustkmer query -s small_chunk.fa database.rkdb
```

## Integration Examples

### With Jellyfish Workflows

```bash
# Use rustkmer query as drop-in replacement for jellyfish query
# Original: jellyfish query database.jf ATGCGATGCTAGC
# Replacement:
rustkmer query database.rkdb ATGCGATGCTAGC

# Convert jellyfish database to rustkmer format (future feature)
# rustkmer convert --from jf --to rkdb database.jf database.rkdb
```

### With Bioinformatics Pipelines

```bash
# Example: Filter sequences by k-mer presence
rustkmer query -s sequences.fa database.rkdb | \
    awk '$2 > 10 {print $1}' | \
    seqtk subseq sequences.fa - > filtered_sequences.fa
```

## Troubleshooting

### Getting Help

```bash
# Show command help
rustkmer query --help

# Show version and build information
rustkmer --version

# Check all available commands
rustkmer --help
```

### Reporting Issues

If you encounter issues:

1. Check rustkmer version: `rustkmer --version`
2. Verify database file: `rustkmer stats database.rkdb`
3. Test with simple data: Create a small test database
4. Check system resources: `df -h` and `free -h`

## Next Steps

- Explore advanced options with `rustkmer query --help`
- Read the full [CLI API contract](contracts/cli-api.md)
- Learn about the [database format](contracts/database-format.md)
- Check the [data model](data-model.md) for technical details
- Review the [research findings](research.md) for implementation details

## References

- [rustkmer GitHub Repository](https://github.com/yourusername/rustkmer)
- [Jellyfish Documentation](https://github.com/gmarcais/Jellyfish)
- [K-mer Counting Best Practices](https://doi.org/10.1093/bioinformatics/bti632)