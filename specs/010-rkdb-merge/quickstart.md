# RKDB Database Merge - Quickstart Guide

## Overview

The `rustkmer merge` command combines multiple RKDB k-mer databases into a single sorted database. It intelligently merges k-mers by summing counts for identical sequences and preserving unique k-mers from all inputs.

## Basic Usage

### Simple Merge

```bash
rustkmer merge -i db1.rkdb -i db2.rkdb -o merged.rkdb
```

### Merge Multiple Databases

```bash
rustkmer merge \
  -i sample1.rkdb \
  -i sample2.rkdb \
  -i sample3.rkdb \
  -o all_samples.rkdb
```

### With Progress Reporting

```bash
rustkmer merge \
  -i *.rkdb \
  -o combined.rkdb \
  --verbose
```

## Common Scenarios

### 1. Merging Sample Databases

Combine k-mer counts from different biological samples:

```bash
# Merge all human samples
rustkmer merge \
  -i human_sample1.rkdb \
  -i human_sample2.rkdb \
  -i human_sample3.rkdb \
  -o human_combined.rkdb \
  --verbose
```

### 2. Creating Reference Databases

Build a comprehensive reference from multiple datasets:

```bash
# Create pan-genome reference
rustkmer merge \
  -i ref_genome.rkdb \
  -i strain1_variants.rkdb \
  -i strain2_variants.rkdb \
  -o pan_genome.rkdb
```

### 3. Merging Large Datasets

For datasets that might exceed memory:

```bash
# Use custom temp directory and streaming mode
rustkmer merge \
  -i large_dataset1.rkdb \
  -i large_dataset2.rkdb \
  -o massive_combined.rkdb \
  --temp-dir /fast/tmp \
  --threads 8 \
  --verbose
```

## Command Options

### Required Options

| Option | Description | Example |
|--------|-------------|---------|
| `-i, --input` | Input database files (min 2) | `-i db1.rkdb -i db2.rkdb` |
| `-o, --output` | Output merged database | `-o merged.rkdb` |

### Optional Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-t, --threads` | Number of threads | Auto-detect | `--threads 4` |
| `--temp-dir` | Temporary directory | System temp | `--temp-dir /tmp` |
| `-v, --verbose` | Detailed output | Off | `--verbose` |
| `-q, --quiet` | Suppress output | Off | `--quiet` |
| `--keep-intermediate` | Keep temp files | Off | `--keep-intermediate` |

## Examples by Use Case

### Bioinformatics Workflow

```bash
#!/bin/bash
# Merge all sequencing runs for a project

PROJECT_DIR="/data/project_xyz"
OUTPUT_DIR="${PROJECT_DIR}/merged"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Find all RKDB files
RKDB_FILES=($(find "$PROJECT_DIR" -name "*.rkdb" -type f))

# Merge with progress reporting
rustkmer merge \
  "${RKDB_FILES[@]/#/-i }" \
  -o "$OUTPUT_DIR/project_combined.rkdb" \
  --verbose \
  --threads 8

echo "Merge complete. Output: $OUTPUT_DIR/project_combined.rkdb"
```

### Batch Processing

```bash
#!/bin/bash
# Merge databases by sample type

for sample_type in bacteria virus fungus; do
  echo "Merging $sample_type samples..."

  rustkmer merge \
    -i "${sample_type}"_*.rkdb \
    -o "${sample_type}_combined.rkdb" \
    --quiet

  echo "✓ ${sample_type} merged"
done
```

### Memory-Conscious Merge

```bash
#!/bin/bash
# Merge when memory is limited

# Get available memory in MB
AVAILABLE_MEM=$(( $(free -m | awk 'NR==2{print $7}') * 1024 * 1024 ))

# Use 40% of available memory
MAX_MEMORY=$((AVAILABLE_MEM * 4 / 10))

rustkmer merge \
  -i huge_db1.rkdb \
  -i huge_db2.rkdb \
  -i huge_db3.rkdb \
  -o merged_huge.rkdb \
  --temp-dir /fast/ssd/temp \
  --threads 2 \
  --verbose
```

## Troubleshooting

### Common Errors

#### 1. "Database compatibility error"
```bash
Error: Database '/path/to/db2.rkdb' has k-mer size 21, expected 31
```
**Solution**: Ensure all databases were created with the same k-mer size and canonical mode.

#### 2. "At least 2 input databases are required"
```bash
Error: At least 2 input databases are required for merging
```
**Solution**: Provide at least two input files with the `-i` flag.

#### 3. "Insufficient memory"
```bash
Warning: Insufficient memory for in-memory merge, falling back to streaming
```
**Solution**: This is automatically handled. Consider using `--temp-dir` on a fast SSD.

### Performance Tips

1. **Use SSD Storage**: Place temporary files on fast storage with `--temp-dir`
2. **Parallel Processing**: Use `--threads` equal to CPU cores for optimal performance
3. **Batch Similar Files**: Merge files with similar sizes together first
4. **Monitor Progress**: Use `--verbose` to track merge progress

## Best Practices

### Before Merging

1. **Verify Database Compatibility**:
   ```bash
   rustkmer stats db1.rkdb
   rustkmer stats db2.rkdb
   # Check that k-mer size and canonical mode match
   ```

2. **Check Disk Space**:
   ```bash
   du -h *.rkdb    # Check input sizes
   df -h .         # Check available space
   ```

3. **Validate Input Files**:
   ```bash
   rustkmer query *.rkdb AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA >/dev/null
   ```

### During Merging

1. **Use Verbose Mode** for large merges to monitor progress
2. **Set Thread Count** appropriately (usually equal to CPU cores)
3. **Use Custom Temp Directory** on fast storage for large datasets

### After Merging

1. **Verify the Result**:
   ```bash
   rustkmer stats merged.rkdb
   rustkmer query merged.rkdb ACGTACGTACGTACGTACGTACGTACGTACGT
   ```

2. **Check Data Integrity**:
   ```bash
   # Spot check some known k-mers
   rustkmer query merged.rkdb <known_kmer>
   ```

## Integration Examples

### With Snakemake

```python
rule merge_kmer_databases:
    input:
        expand("databases/{sample}.rkdb", sample=SAMPLES)
    output:
        "databases/combined.rkdb"
    threads: 8
    shell:
        """
        rustkmer merge {input} -o {output} --threads {threads} --verbose
        """
```

### With Nextflow

```groovy
process MERGE_DBS {
    tag "${sample_id}"
    cpus 8
    memory '32 GB'

    input:
    path rkdb_files from dbs_to_merge

    output:
    path "merged_${sample_id}.rkdb"

    """
    rustkmer merge ${rkdb_files.collect { "-i $it" }.join(' ')} \
        -o merged_${sample_id}.rkdb \
        --threads ${task.cpus} \
        --verbose
    """
}
```

## Resources

- [Full Documentation](../spec.md)
- [API Reference](contracts/merge-api.md)
- [Data Model](data-model.md)
- [Research Findings](research.md)