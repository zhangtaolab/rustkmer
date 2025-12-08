# Quickstart Guide: u128 K-mer Support

## Overview

This guide helps you get started with rustkmer's new u128 encoding, which supports k-mers up to 64 bases.

## Key Changes

- **Maximum k-mer size**: Now supports up to 64 bases (was 32)
- **Database format**: New version 2 format (not backward compatible)
- **Memory usage**: Increased by ~2x due to larger entries (20 bytes vs 12 bytes)

## Basic Usage

### Counting K-mers

```bash
# Count 40-mers (new capability!)
rustkmer count -k 40 -i sequences.fa -o output.rkdb

# Count 64-mers (maximum supported)
rustkmer count -k 64 -i long_sequences.fa -o max_kmer.rkdb

# Traditional sizes still work
rustkmer count -k 31 -i sequences.fa -o traditional.rkdb
```

### Querying Databases

```bash
# Query exact matches
rustkmer query -d output.rkdb "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"

# Fuzzy query with Hamming distance
rustkmer query -d output.rkdb --fuzzy --max-distance 2 "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
```

### Dumping Database Contents

```bash
# Dump as TSV
rustkmer dump -d output.rkdb -o results.tsv

# Dump as JSON
rustkmer dump -d output.rkdb -o results.json --format json
```

### Merging Databases

```bash
# Merge multiple databases
rustkmer merge -d db1.rkdb -d db2.rkdb -o merged.rkdb
```

## Migration from Old Version

Old databases (version 1) are not compatible. You must recreate them:

```bash
# Old command (will fail with new version)
rustkmer count -k 31 -i old_sequences.fa -o old_format.rkdb  # ERROR

# New command - recreate database
rustkmer count -k 31 -i old_sequences.fa -o new_format.rkdb  # OK
```

## Performance Considerations

- **Memory**: Expect ~2x memory usage for databases
- **Disk**: Database files will be ~67% larger (20 vs 12 bytes per entry)
- **Speed**: Slight performance decrease for large k-mers due to u128 operations

## Error Messages

You'll see clear error messages for unsupported operations:

```
Error: k-mer size 65 exceeds maximum supported size of 64
Error: Database format version 1 is not supported. Please recreate the database.
```

## Python API

```python
from rustkmer import KmerDatabase

# Create new database
db = KmerDatabase(k=40)
db.count_from_file("sequences.fa")

# Query
count = db.query("ACGTACGT" * 5)  # 40-mer

# Access raw counts
counts = db.get_all_counts()
```

## Getting Help

```bash
# General help
rustkmer --help

# Command-specific help
rustkmer count --help
rustkmer query --help
```