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
# Count k-mers from a file
rustkmer count -i input.fa -o output.rkdb

# Query a database
rustkmer query -d database.rkdb -q "ATCGATCGATCGATCGATCG"

# Get help
rustkmer --help
rustkmer count --help
```

## Commands

### `count` - Count K-mers

Count k-mers from genomic sequence files and create databases.

#### Basic Counting
```bash
# Count k-mers with default settings (k=21)
rustkmer count -i genome.fa -o genome_k21.rkdb

# Specify k-mer size
rustkmer count -i genome.fa -k 31 -o genome_k31.rkdb

# Use canonical k-mers (recommended for genomes)
rustkmer count -i genome.fa --canonical -o genome_canonical.rkdb
```

#### Input Formats
```bash
# FASTA files
rustkmer count -i genome.fa -o genome.rkdb
rustkmer count -i genome.fa.gz -o genome.rkdb

# FASTQ files
rustkmer count -i reads.fq -o reads.rkdb
rustkmer count -i reads.fq.gz -o reads.rkdb

# Multiple files
rustkmer count -i chr1.fa -i chr2.fa -i chr3.fa -o genome.rkdb
```

#### Advanced Counting Options
```bash
# Specify thread count
rustkmer count -i genome.fa -o genome.rkdb --threads 8

# Enable verbose output
rustkmer count -i genome.fa -o genome.rkdb --verbose

# Create sorted database for faster querying
rustkmer count -i genome.fa -o genome.rkdb --sorted

# Create indexed database for very fast querying
rustkmer count -i genome.fa -o genome.rkdb --indexed

# Compress database to save disk space
rustkmer count -i genome.fa -o genome.rkdb --compress
```

#### Counting Examples
```bash
# Example 1: Basic genome analysis
rustkmer count \
  -i human_genome.fa \
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
  --sorted \
  --compress \
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
# Single k-mer query
rustkmer query -d database.rkdb -q "ATCGATCGATCGATCGATCG"

# Query from file
rustkmer query -d database.rkdb -f queries.txt

# Batch query from text file (one k-mer per line)
rustkmer query database.rkdb --batch kmer_list.txt

# Multiple queries
rustkmer query -d database.rkdb -q "ATCGATCGATCGATCGATCG" -q "GCTAGCTAGCTAGCTAGCTAG"
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

rustkmer query -d database.rkdb -f queries.txt

# Batch query format (one k-mer per line, supports comments)
cat > kmer_list.txt << EOF
# This is a comment and will be ignored
ATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAG

# Empty lines are also ignored
TTTTTTTTTTTTTTTTTTTTT
CCCCCCCCCCCCCCCCCCCCCC
EOF

rustkmer query database.rkdb --batch kmer_list.txt
```

#### Output Formats
```bash
# Simple output (default)
rustkmer query -d database.rkdb -q "ATCGATCGATCGATCGATCG"
# Output: ATCGATCGATCGATCGATCG: 42

# Tab-separated output
rustkmer query -d database.rkdb -f queries.txt --output-format tsv

# JSON output
rustkmer query -d database.rkdb -f queries.txt --output-format json

# CSV output with headers
rustkmer query -d database.rkdb -f queries.txt --output-format csv --header
```

#### Query Examples
```bash
# Example 1: Basic gene analysis
rustkmer query \
  -d genome_database.rkdb \
  -q "ATCGATCGATCGATCGATCG" \
  --output-format json

# Example 2: High-throughput querying
rustkmer query \
  -d genome_database.rkdb \
  -f gene_kmers.txt \
  --output-format tsv \
  --threads 8

# Example 3: Batch query with multiple databases
for db in chr*.rkdb; do
  echo "Querying $db..."
  rustkmer query -d "$db" -f queries.txt -o "${db%.rkdb}_results.tsv"
done
```

### `fuzzy-query` - Fuzzy Search

Perform fuzzy k-mer searches with wildcards and distance constraints.

#### Basic Fuzzy Search
```bash
# Search with wildcards (N = any base)
rustkmer fuzzy-query \
  -d database.rkdb \
  -p "ATCGATCGNATCGATCG" \
  --max-matches 100

# Search with distance constraint
rustkmer fuzzy-query \
  -d database.rkdb \
  -p "ATCGATCGATCGATCGATCG" \
  --max-distance 2 \
  --max-matches 50
```

#### Fuzzy Search Options
```bash
# Search with pattern containing multiple wildcards
rustkmer fuzzy-query \
  -d database.rkdb \
  -p "ATNNGNCGATCG" \
  --max-matches 1000

# Exhaustive search (slower but complete)
rustkmer fuzzy-query \
  -d database.rkdb \
  -p "ATCGATCGATCGATCGATCG" \
  --max-distance 3 \
  --max-matches 1000 \
  --exhaustive

# Output in different formats
rustkmer fuzzy-query \
  -d database.rkdb \
  -p "ATCGATCGATCGATCGATCG" \
  --output-format json \
  --include-distance
```

#### Fuzzy Examples
```bash
# Example 1: Pattern matching with ambiguity
rustkmer fuzzy-query \
  -d genome.rkdb \
  -p "ATCGATCGATCGATCGATCG" \
  --max-distance 1 \
  --max-matches 20 \
  --verbose

# Example 2: Search for similar sequences
rustkmer fuzzy-query \
  -d proteins.rkdb \
  -p "ATCGATCGATCGATCGATCG" \
  --max-distance 2 \
  --exhaustive \
  --output-format json

# Example 3: High-throughput fuzzy search
rustkmer fuzzy-query \
  -d metagenome.rkdb \
  -p "ATNNGATCGATCG" \
  --max-matches 5000 \
  --threads 16 \
  -o fuzzy_results.json
```

### `info` - Database Information

Display information about k-mer databases.

#### Basic Info
```bash
# Show database information
rustkmer info -d database.rkdb

# Detailed information
rustkmer info -d database.rkdb --detailed

# Information for multiple databases
rustkmer info -d db1.rkdb -d db2.rkdb -d db3.rkdb
```

#### Info Examples
```bash
# Example 1: Quick database check
rustkmer info -d genome_k21.rkdb

# Example 2: Detailed analysis
rustkmer info -d genome_k31.rkdb --detailed

# Example 3: Batch database analysis
for db in *.rkdb; do
  echo "=== $db ==="
  rustkmer info -d "$db"
  echo
done
```

### `compare` - Compare Databases

Compare two k-mer databases and find similarities/differences.

#### Basic Comparison
```bash
# Compare two databases
rustkmer compare -d1 database1.rkdb -d2 database2.rkdb

# Comparison with statistics
rustkmer compare \
  -d1 genome1.rkdb \
  -d2 genome2.rkdb \
  --statistics \
  --output comparison_results.txt
```

#### Advanced Comparison
```bash
# Detailed comparison with threshold
rustkmer compare \
  -d1 sample1.rkdb \
  -d2 sample2.rkdb \
  --min-count 10 \
  --similarity-threshold 0.8 \
  --output detailed_comparison.txt

# Export common k-mers
rustkmer compare \
  -d1 control.rkdb \
  -d2 treatment.rkdb \
  --export-common common_kmers.txt

# Export unique k-mers
rustkmer compare \
  -d1 sample1.rkdb \
  -d2 sample2.rkdb \
  --export-unique1 unique_to_sample1.txt \
  --export-unique2 unique_to_sample2.txt
```

#### Compare Examples
```bash
# Example 1: Basic genome comparison
rustkmer compare \
  -d1 human_genome.rkdb \
  -d2 mouse_genome.rkdb \
  --statistics

# Example 2: Differential analysis
rustkmer compare \
  -d1 control_group.rkdb \
  -d2 treatment_group.rkdb \
  --min-count 50 \
  --export-common shared_kmers.txt \
  --export-unique2 treatment_specific.txt

# Example 3: Multiple sample comparison
rustkmer compare \
  -d1 sampleA.rkdb \
  -d2 sampleB.rkdb \
  --similarity-threshold 0.9 \
  --output similarity_report.txt \
  --detailed
```

### `merge` - Merge Databases

Merge multiple k-mer databases into a single database.

#### Basic Merging
```bash
# Merge two databases
rustkmer merge -d1 db1.rkdb -d2 db2.rkdb -o merged.rkdb

# Merge multiple databases
rustkmer merge \
  -d1 chr1.rkdb \
  -d2 chr2.rkdb \
  -d3 chr3.rkdb \
  -o complete_genome.rkdb
```

#### Merge Options
```bash
# Merge with specific k-mer size (must match)
rustkmer merge \
  -d1 sample1.rkdb \
  -d2 sample2.rkdb \
  -o merged.rkdb \
  -k 21

# Merge and sort result
rustkmer merge \
  -d1 part1.rkdb \
  -d2 part2.rkdb \
  -o complete.rkdb \
  --sort

# Merge with compression
rustkmer merge \
  -d1 batch1.rkdb \
  -d2 batch2.rkdb \
  -o final.rkdb \
  --compress
```

#### Merge Examples
```bash
# Example 1: Combine chromosome databases
rustkmer merge \
  -d1 chr1.rkdb -d2 chr2.rkdb -d3 chr3.rkdb \
  -d4 chr4.rkdb -d5 chr5.rkdb \
  -o genome_complete.rkdb \
  --sort

# Example 2: Merge batch processing results
rustkmer merge \
  -d1 batch1.rkdb \
  -d2 batch2.rkdb \
  -d3 batch3.rkdb \
  -o all_batches.rkdb \
  --compress \
  --verbose

# Example 3: Create consensus database
rustkmer merge \
  -d1 sample1.rkdb \
  -d2 sample2.rkdb \
  -d3 sample3.rkdb \
  -o consensus.rkdb \
  --sort \
  --threads 8
```

## Global Options

These options are available for all commands:

### Verbosity and Output
```bash
# Verbose output
rustkmer count -i input.fa -o output.rkdb --verbose

# Quiet mode (minimal output)
rustkmer count -i input.fa -o output.rkdb --quiet

# Progress bar
rustkmer count -i input.fa -o output.rkdb --progress
```

### Threading
```bash
# Auto-detect threads (default)
rustkmer count -i input.fa -o output.rkdb

# Specify thread count
rustkmer count -i input.fa -o output.rkdb --threads 8

# Single-threaded
rustkmer count -i input.fa -o output.rkdb --threads 1
```

### Configuration
```bash
# Use configuration file
rustkmer --config config.toml count -i input.fa -o output.rkdb

# Set working directory
rustkmer --working-dir /path/to/work count -i input.fa -o output.rkdb
```

## Configuration Files

Create a TOML configuration file to store default settings:

```toml
# rustkmer.toml
[general]
default_threads = 8
default_k = 21
working_directory = "/data/rustkmer"

[counting]
canonical = true
sort = true
compress = false

[querying]
default_output_format = "tsv"
include_zero_counts = false

[fuzzy_search]
max_default_distance = 2
max_default_matches = 100
```

Use configuration:
```bash
rustkmer --config rustkmer.toml count -i input.fa -o output.rkdb
```

## Performance Tips

### Counting Performance
```bash
# Use optimal thread count
THREADS=$(nproc)
rustkmer count -i large_file.fa -o output.rkdb --threads $THREADS

# Use sorted databases for better query performance
rustkmer count -i input.fa -o output.rkdb --sorted

# Use compression for storage efficiency
rustkmer count -i input.fa -o output.rkdb --compress

# Choose appropriate k-mer size
rustkmer count -i input.fa -o output.rkdb -k 21  # Balanced
rustkmer count -i input.fa -o output.rkdb -k 13  # Faster, less memory
rustkmer count -i input.fa -o output.rkdb -k 31  # Slower, more specific
```

### Query Performance
```bash
# Batch queries for better performance
rustkmer query -d database.rkdb -f large_query_file.txt --threads 8

# Use appropriate output format
rustkmer query -d database.rkdb -f queries.txt --output-format tsv  # Fast
rustkmer query -d database.rkdb -f queries.txt --output-format json  # Slower but more detailed

# Use sorted/indexed databases for frequent querying
rustkmer count -i input.fa -o indexed.rkdb --indexed
rustkmer query -d indexed.rkdb -f queries.txt
```

### Memory Usage
```bash
# Monitor memory usage with verbose output
rustkmer count -i large_file.fa -o output.rkdb --verbose

# Use smaller k-mer sizes for memory efficiency
rustkmer count -i input.fa -o output.rkdb -k 13

# Process files in batches for very large datasets
for file in *.fa; do
  rustkmer count -i "$file" -o "${file%.fa}.rkdb"
done
rustkmer merge *.rkdb -o merged.rkdb
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
    -o "$OUTPUT_DIR/${sample}.rkdb" \
    --canonical \
    --sorted \
    --threads "$THREADS" \
    --verbose
done

# Step 2: Create summary report
echo "Generating summary..."
{
  echo "Sample,K-mer Size,Total K-mers,Unique K-mers"
  for db in "$OUTPUT_DIR"/*.rkdb; do
    sample=$(basename "$db" .rkdb)
    info=$(rustkmer info -d "$db")
    # Extract key statistics from info output
    echo "$sample,21,$(echo "$info" | grep "Total" | cut -d: -f2 | tr -d ' '),$(echo "$info" | grep "Unique" | cut -d: -f2 | tr -d ' ')"
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
            -o {output} \
            --canonical \
            --sorted \
            --threads {threads}
        """

rule generate_summary:
    input:
        expand("results/{sample}.rkdb", sample=SAMPLES)
    output:
        "results/summary.csv"
    shell:
        """
        # Generate summary using rustkmer info
        echo "Sample,Total K-mers,Unique K-mers" > {output}
        for db in {input}; do
            sample=$(basename $db .rkdb)
            info=$(rustkmer info -d $db)
            echo "$sample,$(echo "$info" | grep "Total" | cut -d: -f2 | tr -d ' '),$(echo "$info" | grep "Unique" | cut -d: -f2 | tr -d ' ')" >> {output}
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
        -o ${fasta_file.baseName}.rkdb \
        --canonical \
        --sorted \
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
        info=\$(rustkmer info -d \$db)
        echo "\$sample,\$(echo "\$info" | grep "Total" | cut -d: -f2 | tr -d ' '),\$(echo "\$info" | grep "Unique" | cut -d: -f2 | tr -d ' ')" >> summary.csv
    done
    """
}
```

## Error Handling

### Common Errors and Solutions

#### File Not Found
```bash
# Error: Input file not found
rustkmer count -i missing.fa -o output.rkdb
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
rustkmer query -d corrupted.rkdb -q "ATCG"
# Solution: Recreate database or check integrity
rustkmer info -d corrupted.rkdb
```

#### Permission Errors
```bash
# Error: Permission denied
rustkmer count -i /protected/file.fa -o /protected/output.rkdb
# Solution: Check file permissions or use different directory
chmod 644 /protected/file.fa
rustkmer count -i /protected/file.fa -o ./output.rkdb
```

### Debug Mode
```bash
# Enable debug output
rustkmer count -i input.fa -o output.rkdb --verbose --debug

# Check database integrity
rustkmer info -d database.rkdb --detailed

# Test with small sample
rustkmer count -i small_test.fa -o test.rkdb --verbose
```

---

## Need More Help?

- **[Getting Started](../getting-started/)** - Installation and basic usage
- **[Performance Tips](performance-tips.md)** - Optimization strategies
- **[User Guide](index.md)** - Complete user guide
- **[API Reference](../api-reference/)** - Python API documentation