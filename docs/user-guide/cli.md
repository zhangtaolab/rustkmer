# Command Line Interface

Complete guide to using RustKmer's command line interface for k-mer counting and database operations.

## Overview

RustKmer provides a powerful command line interface (CLI) for all k-mer operations. The CLI is optimized for performance, supports batch processing, and integrates well with bioinformatics pipelines.

## Installation

```bash
# Install from crates.io
cargo install rustkmer

# Or build from source
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer
cargo build --release
```

## Basic Usage

```bash
# Count k-mers from a file (-k is required — there is no default k)
rustkmer count -i input.fa -k 21 -o output.rkdb

# Query a database (database path is positional)
rustkmer query database.rkdb "ATCGATCGATCGATCGATCG"

# Get help
rustkmer --help
rustkmer count --help
```

## Commands

### `count` - Count K-mers

Count k-mers from genomic sequence files and create databases.

#### Basic Counting
```bash
# Count k-mers (k is required — there is no default k)
rustkmer count -i genome.fa -k 21 -o genome_k21.rkdb

# Omit -o to print counting statistics without writing a database
rustkmer count -i genome.fa -k 31

# Use canonical k-mers (recommended for genomes)
rustkmer count -i genome.fa -k 21 --canonical -o genome_canonical.rkdb
```

#### Input Formats
```bash
# FASTA files
rustkmer count -i genome.fa -k 21 -o genome.rkdb
rustkmer count -i genome.fa.gz -k 21 -o genome.rkdb

# FASTQ files
rustkmer count -i reads.fq -k 21 -o reads.rkdb
rustkmer count -i reads.fq.gz -k 21 -o reads.rkdb

# Multiple files
rustkmer count -i chr1.fa -i chr2.fa -i chr3.fa -o genome.rkdb
```

#### Advanced Counting Options
```bash
# Specify thread count (--threads is long-only; default is all cores)
rustkmer count -i genome.fa -k 21 -o genome.rkdb --threads 8

# Enable verbose output
rustkmer count -i genome.fa -k 21 -o genome.rkdb --verbose

# Hash table size (--size takes a usize; default 1000000)
rustkmer count -i genome.fa -k 21 -o genome.rkdb --size 4000000

# Write human-readable text instead of the binary database
rustkmer count -i genome.fa -k 21 -o output.txt --format text

# Skip sorting for faster counting (sorted output is the default)
rustkmer count -i genome.fa -k 21 -o genome.rkdb --no-sort

# Filter by count thresholds (-L min, -U max)
rustkmer count -i genome.fa -k 21 -o genome.rkdb -L 2 -U 1000
```

#### Counting Examples
```bash
# Example 1: Basic genome analysis
rustkmer count \
  -i human_genome.fa \
  -k 21 \
  -o human_genome_k21.rkdb \
  --canonical \
  --threads 16 \
  --verbose

# Example 2: Large dataset processing
rustkmer count \
  -i large_dataset.fa.gz \
  -o large_dataset.rkdb \
  -k 31 \
  --canonical \
  --threads 32

# Example 3: Fast counting for testing
rustkmer count \
  -i test_data.fa \
  -o test_data.rkdb \
  -k 13 \
  --threads 4
```

### `query` - Query Databases

Query k-mer databases for exact matches and retrieve counts.

#### Basic Querying
```bash
# Single k-mer query (database path and k-mers are positional)
rustkmer query database.rkdb "ATCGATCGATCGATCGATCG"

# Multiple queries (space-separated positional k-mers)
rustkmer query database.rkdb "ATCGATCGATCGATCGATCG" "GCTAGCTAGCTAGCTAGCTAG"

# Query every k-mer of a sequence file
rustkmer query database.rkdb -s reads.fa

# Batch query from text file (one k-mer per line)
rustkmer query database.rkdb -b kmer_list.txt

# Interactive mode (reads k-mers from stdin)
rustkmer query database.rkdb -i
```

#### Query Formats
```bash
# Query file format (one k-mer per line)
cat > queries.txt << EOF
ATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAG
TTTTTTTTTTTTTTTTTTTTT
CCCCCCCCCCCCCCCCCCCCCC
EOF

rustkmer query database.rkdb -b queries.txt

# Batch query format (one k-mer per line, supports comments)
cat > kmer_list.txt << EOF
# This is a comment and will be ignored
ATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAG

# Empty lines are also ignored
TTTTTTTTTTTTTTTTTTTTT
CCCCCCCCCCCCCCCCCCCCCC
EOF

rustkmer query database.rkdb -b kmer_list.txt
```

#### Output Formats
```bash
# Simple output (results print to stdout by default)
rustkmer query database.rkdb "ATCGATCGATCGATCGATCG"
# Output: ATCGATCGATCGATCGATCG: 42

# Write results to a file instead of stdout
rustkmer query database.rkdb -b queries.txt -o results.txt

# Force pre-loading of the database into memory (faster repeated lookups)
rustkmer query database.rkdb -b queries.txt -l

# Disable pre-loading (read entries from disk instead)
rustkmer query database.rkdb -b queries.txt -L
```

#### Query Examples
```bash
# Example 1: Basic gene analysis
rustkmer query \
  genome_database.rkdb \
  "ATCGATCGATCGATCGATCG"

# Example 2: High-throughput querying
rustkmer query \
  genome_database.rkdb \
  -b gene_kmers.txt \
  -l \
  -o results.txt

# Example 3: Batch query with multiple databases
for db in chr*.rkdb; do
  echo "Querying $db..."
  rustkmer query "$db" -b queries.txt -o "${db%.rkdb}_results.tsv"
done
```

### `fuzzy-query` - Fuzzy Search

Perform fuzzy k-mer searches with wildcards and distance constraints.

#### Basic Fuzzy Search
```bash
# Search with wildcards (N = any base) — database and query are positional
rustkmer fuzzy-query database.rkdb "ATCGATCGNATCGATCG"

# Search with mutation tolerance (maximum Hamming distance, -m/--mutations)
rustkmer fuzzy-query database.rkdb "ATCGATCGATCGATCGATCG" -m 2

# Cap the number of generated variants (-M/--max-variants)
rustkmer fuzzy-query database.rkdb "ATCGATCGATCGATCGATCG" -m 2 -M 1000
```

#### Fuzzy Search Options
```bash
# Search with pattern containing multiple wildcards
rustkmer fuzzy-query database.rkdb "ATNNGNCGATCG" -M 1000

# Tune the variant batch size (default 1000)
rustkmer fuzzy-query database.rkdb "ATCGATCGATCGATCGATCG" -m 3 -b 5000

# Position-specific mutations (e.g. "3,4,5:2" or "3,4,5:2;6,7:1")
rustkmer fuzzy-query database.rkdb "ATCGATCGATCGATCGATCG" --position-mutations "3,4,5:2"

# Output in different formats (table, json, tsv, csv)
rustkmer fuzzy-query database.rkdb "ATCGATCGATCGATCGATCG" -m 1 -f json
```

#### Fuzzy Examples
```bash
# Example 1: Pattern matching with ambiguity
rustkmer fuzzy-query genome.rkdb "ATCGATCGATCGATCGATCG" -m 1 -M 20 --verbose

# Example 2: Search for similar sequences
rustkmer fuzzy-query proteins.rkdb "ATCGATCGATCGATCGATCG" -m 2 -f json

# Example 3: High-throughput fuzzy search
rustkmer fuzzy-query metagenome.rkdb "ATNNGATCGATCG" -M 5000 -f json -o fuzzy_results.json
```

### `fuzzy-query-batch` - Batch Fuzzy Search

Run fuzzy queries for every line of a query file.

#### Basic Batch Search
```bash
# Query every line of queries.txt against the database
rustkmer fuzzy-query-batch database.rkdb -s queries.txt

# Defaults applied to every query in the file
rustkmer fuzzy-query-batch database.rkdb -s queries.txt --default-mutations 1

# JSON output written to a file
rustkmer fuzzy-query-batch database.rkdb -s queries.txt -f json -o results.json
```

The database path is positional; `-s/--sequence FILE` (one query per line) is required. Additional options: `--default-mutations`, `--default-max-variants`, `-b/--batch-size`, `-f/--format` (table, json, tsv, csv), `-o/--output`, `--fail-fast`, and `--include-headers`.

#### Batch Examples
```bash
# Example: large query set with per-query defaults
rustkmer fuzzy-query-batch metagenome.rkdb \
  -s all_queries.txt \
  --default-mutations 2 \
  --default-max-variants 5000 \
  -b 200 \
  -f tsv \
  -o batch_results.tsv
```

### `dump` - Dump Database to Text

Dump the contents of a k-mer database to text format.

#### Basic Dump
```bash
# Dump database to stdout
rustkmer dump database.rkdb

# Dump database to a file
rustkmer dump database.rkdb -o database.txt
```

`dump` takes the database path as a positional argument; `-o/--output` is its only option.

#### Dump Examples
```bash
# Example 1: Quick database inspection
rustkmer dump genome_k21.rkdb | head

# Example 2: Batch conversion to text
for db in *.rkdb; do
  echo "=== $db ==="
  rustkmer dump "$db" -o "${db%.rkdb}.txt"
done
```

### `stats` - Database Statistics

Calculate statistics for a k-mer database.

#### Basic Stats
```bash
# Show database statistics (database path is positional)
rustkmer stats database.rkdb

# Detailed statistics including the frequency distribution
rustkmer stats database.rkdb --detailed

# Machine-readable output formats
rustkmer stats database.rkdb -f json
rustkmer stats database.rkdb -f csv
```

`stats` takes the database path as a positional argument. Additional options: `-f/--format` (text, json, csv, tsv), `-o/--output`, `--detailed`, `--max-bins`, `--approximate`, `-p/--progress`, and `--split-output` with `--freq-output`.

#### Stats Examples
```bash
# Example 1: Quick database check
rustkmer stats genome_k21.rkdb

# Example 2: Detailed analysis
rustkmer stats genome_k31.rkdb --detailed

# Example 3: Batch database analysis
for db in *.rkdb; do
  echo "=== $db ==="
  rustkmer stats "$db"
  echo
done
```

### `prefix-query` - Prefix Queries

Efficient prefix-based k-mer query for sorted databases.

#### Basic Prefix Query
```bash
# Match k-mers by sequence prefix (database path is positional)
rustkmer prefix-query database.rkdb -x ATCGAT

# Match a hybrid pattern with internal wildcards (e.g. ATAC{N5}ACAC)
rustkmer prefix-query database.rkdb -p "ATAC{N5}ACAC" --hybrid
```

`-p/--pattern` and `-x/--prefix` are mutually exclusive; `--hybrid` requires `-p`. Additional options: `-f/--format` (table, json, csv, tsv), `-o/--output`, `-L/--min-count`, `-U/--max-count`, `--profile`, `-v/--verbose`, and `-q/--quiet`.

#### Prefix Query Examples
```bash
# Example 1: Extract all k-mers sharing a prefix
rustkmer prefix-query genome.rkdb -x ATCGAT -f tsv

# Example 2: Hybrid pattern with count thresholds
rustkmer prefix-query metagenome.rkdb -p "ATAC{N5}ACAC" --hybrid -L 2 -f csv -o prefix_matches.csv
```

### `merge` - Merge Databases

Merge multiple k-mer databases into a single database.

#### Basic Merging
```bash
# Merge two databases (-i/--input takes at least two files)
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb

# Merge multiple databases
rustkmer merge \
  -i chr1.rkdb chr2.rkdb chr3.rkdb \
  -o complete_genome.rkdb
```

#### Merge Options
```bash
# Cap the memory budget for the merge (defaults to 50% of system memory)
rustkmer merge \
  -i sample1.rkdb sample2.rkdb \
  -o merged.rkdb \
  --max-memory 32GB

# Choose the merge strategy (auto, memory, or streaming)
rustkmer merge \
  -i part1.rkdb part2.rkdb \
  -o complete.rkdb \
  --merge-mode streaming

# Parallel merge threads (--num-threads; 0 = all cores)
rustkmer merge \
  -i batch1.rkdb batch2.rkdb \
  -o final.rkdb \
  --num-threads 8
```

#### Merge Examples
```bash
# Example 1: Combine chromosome databases
rustkmer merge \
  -i chr1.rkdb chr2.rkdb chr3.rkdb chr4.rkdb chr5.rkdb \
  -o genome_complete.rkdb

# Example 2: Memory-bounded merge of batch processing results
rustkmer merge \
  -i batch1.rkdb batch2.rkdb batch3.rkdb \
  -o all_batches.rkdb \
  --max-memory 16GB \
  --merge-mode streaming \
  --verbose

# Example 3: Check compatibility before merging
rustkmer merge \
  -i sample1.rkdb sample2.rkdb sample3.rkdb \
  -o consensus.rkdb \
  --check-compatibility
```

## Command Options

There are no global options — each subcommand defines its own flags. The options most commonly needed across workflows are:

### Verbosity and Output
```bash
# Verbose output (available on count, merge, fuzzy-query, fuzzy-query-batch, prefix-query)
rustkmer count -i input.fa -k 21 -o output.rkdb --verbose

# Quiet mode (minimal output)
rustkmer count -i input.fa -k 21 -o output.rkdb --quiet
```

### Threading
```bash
# count: --threads (long-only flag; default is all cores)
rustkmer count -i input.fa -k 21 -o output.rkdb --threads 8

# Single-threaded counting
rustkmer count -i input.fa -k 21 -o output.rkdb --threads 1

# merge: --num-threads (0 = use all cores)
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb --num-threads 8
```

## Configuration via Environment

There is no `--config` flag. Thread count and logging are configured through environment variables:

```bash
# Thread precedence for count (highest wins):
# --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all available cores
RUSTKMER_THREADS=8 rustkmer count -i input.fa -k 21 -o output.rkdb
RAYON_NUM_THREADS=4 rustkmer count -i input.fa -k 21 -o output.rkdb

# Logging verbosity (rustkmer logs at the "info" level by default)
RUST_LOG=debug rustkmer count -i input.fa -k 21 -o output.rkdb
```

## Performance Tips

### Counting Performance
```bash
# Use optimal thread count
THREADS=$(nproc)
rustkmer count -i large_file.fa -k 21 -o output.rkdb --threads $THREADS

# Databases are sorted by default for better query performance
rustkmer count -i input.fa -k 21 -o output.rkdb

# Skip sorting when the counts are all you need (faster counting)
rustkmer count -i input.fa -k 21 -o output.rkdb --no-sort

# Choose appropriate k-mer size
rustkmer count -i input.fa -o output.rkdb -k 21  # Balanced
rustkmer count -i input.fa -o output.rkdb -k 13  # Faster, less memory
rustkmer count -i input.fa -o output.rkdb -k 31  # Slower, more specific
```

### Query Performance
```bash
# Batch queries for better performance
rustkmer query database.rkdb -b large_query_file.txt -l

# Avoid pre-loading for one-off lookups
rustkmer query database.rkdb "ATCGATCGATCGATCGATCG" -L

# Sorted databases (the counting default) enable fast queries
rustkmer count -i input.fa -k 21 -o sorted.rkdb
rustkmer query sorted.rkdb -b queries.txt
```

### Memory Usage
```bash
# Monitor memory usage with verbose output
rustkmer count -i large_file.fa -k 21 -o output.rkdb --verbose

# Use smaller k-mer sizes for memory efficiency
rustkmer count -i input.fa -o output.rkdb -k 13

# Process files in batches for very large datasets
for file in *.fa; do
  rustkmer count -i "$file" -k 21 -o "${file%.fa}.rkdb"
done
rustkmer merge -i *.rkdb -o merged.rkdb --max-memory 16GB
```

## Pipeline Integration

### Bash Scripting
```bash
#!/bin/bash
# pipeline.sh - Complete k-mer analysis pipeline

INPUT_DIR="data"
OUTPUT_DIR="results"
THREADS=16

mkdir -p "$OUTPUT_DIR"

echo "Starting k-mer analysis..."

# Step 1: Count k-mers for all samples
for file in "$INPUT_DIR"/*.fa; do
  sample=$(basename "$file" .fa)
  echo "Processing $sample..."

  rustkmer count \
    -i "$file" \
    -k 21 \
    -o "$OUTPUT_DIR/${sample}.rkdb" \
    --canonical \
    --threads "$THREADS" \
    --verbose
done

# Step 2: Create summary report
echo "Generating summary..."
{
  echo "Sample,K-mer Size,Total K-mers,Unique K-mers"
  for db in "$OUTPUT_DIR"/*.rkdb; do
    sample=$(basename "$db" .rkdb)
    stats=$(rustkmer stats "$db")
    # Extract key statistics from stats output
    echo "$sample,21,$(echo "$stats" | grep "Total" | cut -d: -f2 | tr -d ' '),$(echo "$stats" | grep "Unique" | cut -d: -f2 | tr -d ' ')"
  done
} > "$OUTPUT_DIR/summary.csv"

echo "Pipeline complete! Results in $OUTPUT_DIR"
```

### Snakemake Integration
```python
# Snakefile
rule all:
    input:
        "results/summary.csv"

rule count_kmers:
    input:
        "data/{sample}.fa"
    output:
        "results/{sample}.rkdb"
    threads: 8
    shell:
        """
        rustkmer count \
            -i {input} \
            -k 21 \
            -o {output} \
            --canonical \
            --threads {threads}
        """

rule generate_summary:
    input:
        expand("results/{sample}.rkdb", sample=SAMPLES)
    output:
        "results/summary.csv"
    shell:
        """
        # Generate summary using rustkmer stats
        echo "Sample,Total K-mers,Unique K-mers" > {output}
        for db in {input}; do
            sample=$(basename $db .rkdb)
            stats=$(rustkmer stats $db)
            echo "$sample,$(echo "$stats" | grep "Total" | cut -d: -f2 | tr -d ' '),$(echo "$stats" | grep "Unique" | cut -d: -f2 | tr -d ' ')" >> {output}
        done
        """
```

### Nextflow Integration
```groovy
// main.nf
process count_kmers {
    input:
    path fasta_file from samples_ch

    output:
    path "${fasta_file.baseName}.rkdb"

    cpus 8
    memory '16 GB'

    script:
    """
    rustkmer count \
        -i ${fasta_file} \
        -k 21 \
        -o ${fasta_file.baseName}.rkdb \
        --canonical \
        --threads ${task.cpus}
    """
}

process summarize_results {
    input:
    path db_files from count_kmers.out.collect()

    output:
    path "summary.csv"

    script:
    """
    echo "Sample,Total K-mers,Unique K-mers" > summary.csv
    for db in ${db_files}; do
        sample=\$(basename \$db .rkdb)
        stats=\$(rustkmer stats \$db)
        echo "\$sample,\$(echo "\$stats" | grep "Total" | cut -d: -f2 | tr -d ' '),\$(echo "\$stats" | grep "Unique" | cut -d: -f2 | tr -d ' ')" >> summary.csv
    done
    """
}
```

## Error Handling

### Common Errors and Solutions

#### File Not Found
```bash
# Error: Input file not found
rustkmer count -i missing.fa -k 21 -o output.rkdb
# Solution: Check file path and permissions
ls -la missing.fa
```

#### Memory Issues
```bash
# Error: Out of memory
rustkmer count -i huge_file.fa -o output.rkdb -k 31
# Solution: Use smaller k-mer size or more threads
rustkmer count -i huge_file.fa -o output.rkdb -k 13 --threads 32
```

#### Database Format Errors
```bash
# Error: Invalid database format
rustkmer query corrupted.rkdb "ATCG"
# Solution: Recreate database or check integrity
rustkmer stats corrupted.rkdb
```

#### Permission Errors
```bash
# Error: Permission denied
rustkmer count -i /protected/file.fa -k 21 -o /protected/output.rkdb
# Solution: Check file permissions or use different directory
chmod 644 /protected/file.fa
rustkmer count -i /protected/file.fa -k 21 -o ./output.rkdb
```

### Debug Mode
```bash
# Enable debug output (there is no --debug flag; use RUST_LOG)
RUST_LOG=debug rustkmer count -i input.fa -k 21 -o output.rkdb --verbose

# Check database statistics
rustkmer stats database.rkdb --detailed

# Test with small sample
rustkmer count -i small_test.fa -k 21 -o test.rkdb --verbose
```

---

## Need More Help?

- **[Getting Started](../getting-started/)** - Installation and basic usage
- **[Performance Tips](performance-tips.md)** - Optimization strategies
- **[User Guide](index.md)** - Complete user guide
- **[API Reference](../api-reference/)** - Python API documentation