# CLI API Contract: rustkmer u128 Support

## Command: count

Creates a k-mer database from FASTA/FASTQ files.

```bash
rustkmer count [OPTIONS] --output <FILE> <INPUT>
```

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--kmer-size` | `-k` | `<u8>` | 31 | K-mer size (1-64) |
| `--output` | `-o` | `<FILE>` | Required | Output database file |
| `--memory-limit` | | `<SIZE>` | None | Memory limit (e.g., 8GB) |
| `--canonical` | | | true | Store canonical k-mers |
| `--format` | | `<FORMAT>` | auto | Input format (auto/fasta/fastq) |
| `--verbose` | | | false | Verbose output |
| `--threads` | | `<NUM>` | Number of CPU cores | Thread count |

### Examples

```bash
# Basic usage with k=48
rustkmer count -k 48 -o output.rkdb input.fasta

# With memory limit
rustkmer count -k 64 -o large.rkdb huge.fa --memory-limit 16GB

# Verbose output
rustkmer count -k 32 -o db.rkdb input.fa --verbose
```

### Output

- Success: Creates RKDB file with u128 encoding
- Error: Returns non-zero exit code with descriptive message

## Command: query

Queries k-mers in a database.

```bash
rustkmer query [OPTIONS] --database <FILE> [KMER]...
```

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | `<FILE>` | Required | Database file |
| `--batch` | | `<FILE>` | None | Batch query from file |
| `--format` | | `<FORMAT>` | text | Output format (text/json/tsv) |
| `--max-concurrent` | | `<NUM>` | None | Max concurrent queries |
| `--memory-limit` | | `<SIZE>` | None | Memory limit for queries |

### Examples

```bash
# Single query
rustkmer query -d db.rkdb ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT

# Batch query
rustkmer query -d db.rkdb --batch queries.txt

# JSON output
rustkmer query -d db.rkdb ACGTACGT --format json
```

### Output Format

Text:
```
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT: 42
```

JSON:
```json
{
  "results": [
    {"kmer": "ACGTACGT...", "count": 42}
  ]
}
```

TSV:
```
kmer	count
ACGTACGT...	42
```

## Command: stats

Displays database statistics.

```bash
rustkmer stats [OPTIONS] --database <FILE>
```

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | `<FILE>` | Required | Database file |
| `--format` | | `<FORMAT>` | text | Output format (text/json) |

### Output Fields

- `kmer_size`: K-mer size used (1-64)
- `total_kmers`: Total number of k-mers
- `unique_kmers`: Number of unique k-mers
- `total_counts`: Sum of all counts
- `skipped_ambiguous`: Number of k-mers skipped due to N bases

## Command: dump

Dumps database contents.

```bash
rustkmer dump [OPTIONS] --database <FILE>
```

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | `<FILE>` | Required | Database file |
| `--format` | | `<FORMAT>` | text | Output format (text/json/tsv) |
| `--limit` | | `<NUM>` | None | Limit number of entries |
| `--min-count` | | `<NUM>` | 1 | Minimum count threshold |

## Error Handling

All commands return:
- Exit code 0: Success
- Exit code 1: General error
- Exit code 2: Invalid argument
- Exit code 3: File not found
- Exit code 4: Database format error
- Exit code 5: Memory limit exceeded

Error messages follow the format:
```
ERROR [E001]: Invalid k-mer size: 65 (must be 1-64)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RUSTKMER_THREADS` | Default thread count |
| `RUSTKMER_MEMORY` | Default memory limit |
| `RUSTKMER_LOG_LEVEL` | Log level (error/warn/info/debug) |

## Version Information

```bash
rustkmer --version
# rustkmer 2.0.0
# Features: u128-encoding, python-bindings
# Database format: RKDB v2