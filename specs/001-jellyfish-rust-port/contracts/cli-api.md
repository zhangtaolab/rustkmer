# CLI API Contract: K-mer Count Filtering Enhancement

**Version**: 1.1.0
**Date**: 2025-11-28
**Purpose**: Define command-line interface for k-mer count filtering functionality
**Requirement**: FR-008 - Handle sequence filtering based on minimum and maximum count thresholds

## Command Structure

```bash
rustkmer count [OPTIONS] <INPUT_FILES>...
```

### Required Arguments

- `<INPUT_FILES>...` - One or more FASTA/FASTQ files to process

### Options

#### Core Counting Options
- `-k, --kmer-size <SIZE>` - Length of k-mers to count (default: 31)
  - Type: `usize`
  - Range: 1-127
  - Validation: Must be positive integer

- `-C, --canonical` - Count canonical k-mers (lexicographically smaller of forward/reverse complement)
  - Type: `bool`
  - Default: false

#### Performance Options
- `-t, --threads <COUNT>` - Number of threads to use (default: number of CPU cores)
  - Type: `usize`
  - Range: 1-256
  - Validation: Cannot exceed available CPU cores

- `-s, --size <SIZE>` - Initial hash table size (e.g., 100M, 1G)
  - Type: `String`
  - Format: Number with suffix (K, M, G)
  - Examples: 100M, 1G, 2.5G

#### Output Options
- `-o, --output <FILE>` - Output file path (default: mer_counts.rk)
  - Type: `String`
  - Default: "mer_counts.rk"
  - Extension: .rk for binary, .txt for text

- `--text` - Generate human-readable text output instead of binary
  - Type: `bool`
  - Default: false

#### Filtering Options
- `-L, --lower-count <COUNT>` - Minimum count threshold
  - Type: `u32`
  - Default: 1
  - Range: 1-4294967295

- `-U, --upper-count <COUNT>` - Maximum count threshold
  - Type: `u32`
  - Default: 4294967295
  - Range: 1-4294967295

#### Progress Options
- `--timing` - Show detailed timing and performance statistics
  - Type: `bool`
  - Default: false

- `--progress` - Show progress bar during processing
  - Type: `bool`
  - Default: true for terminals, false for redirected output

#### Help Options
- `-h, --help` - Print help information
- `-V, --version` - Print version information

## Output Formats

### Binary Format (.rk files)

**File Header**:
```
MAGIC: "RK01" (4 bytes)
VERSION: u16 (2 bytes)
KMER_LENGTH: u8 (1 byte)
CANONICAL_MODE: u8 (1 byte, 0=false, 1=true)
TOTAL_KMERS: u64 (8 bytes)
UNIQUE_KMERS: u64 (8 bytes)
RESERVED: [u8; 20] (20 bytes padding)
```

**K-mer Entries** (variable number):
```
KMER_BITS: [u8] (packed, ceil(k*2/8) bytes)
COUNT: u32 (4 bytes, little-endian)
```

### Text Format (.txt files)

```
# rustkmer count results
# kmer_size: 31
# canonical: true
# total_kmers: 12345678
# unique_kmers: 987654
# generation_time: 2025-11-28T10:30:00Z

ATGCATGCATGCATGCATGCATGCATGCATGC    1234
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA    987
...
```

## Exit Codes

- `0` - Success
- `1` - General error (invalid arguments, I/O error)
- `2` - Memory error (insufficient memory, hash table overflow)
- `3` - File format error (invalid FASTA/FASTQ, corrupt file)
- `4` - Processing error (unexpected condition during counting)

## Error Messages

### Argument Validation Errors
- `Error: Invalid k-mer size '128'. Must be between 1 and 127`
- `Error: Invalid hash table size format 'abc'. Use format like '100M' or '1G'`
- `Error: Thread count 256 exceeds available CPU cores (12)`

### File Errors
- `Error: Cannot read input file 'input.fa': Permission denied`
- `Error: Cannot create output file 'output.rk': Disk full`
- `Error: Invalid FASTA format in file 'bad.fa' at line 123`

### Memory Errors
- `Error: Insufficient memory for hash table. Try smaller size or use disk-based overflow`
- `Error: Hash table overflow. Consider increasing size with --size option`

### Processing Errors
- `Error: No valid sequences found in input files`
- `Error: All sequences shorter than k-mer size (31)`

## Examples

### Basic Counting
```bash
rustkmer count -k 31 input.fa
# Output: mer_counts.rk (binary format)
```

### Canonical Counting with Multiple Files
```bash
rustkmer count -C -k 21 file1.fa file2.fq file3.fa
```

### Text Output with Filtering
```bash
rustkmer count -k 13 --text -L 10 -U 1000 input.fa
# Output: mer_counts.txt (text format, counts 10-1000)
```

### Performance Configuration
```bash
rustkmer count -k 31 -t 8 -s 2G -o big_counts.rk large_genome.fa
```

### Progress and Timing
```bash
rustkmer count -k 31 --timing --progress input.fa
# Shows detailed performance statistics
```

## Performance Expectations

### Processing Speed
- Target: Comparable to jellyfish on identical hardware
- Expected: 10-50 million bases per second per thread
- Scaling: 70%+ efficiency when doubling thread count

### Memory Usage
- Hash table: Approximately 16 bytes per unique k-mer
- Memory overhead: Under 2× configured hash table size
- Disk overflow: Graceful degradation when memory insufficient

### File I/O
- Input: Memory-mapped file reading for large files
- Output: Sequential writes with efficient buffering
- Temp files: Minimal usage, stored in temp directory

## Compatibility Requirements

### Input Formats
- FASTA: Standard format with header lines starting with '>'
- FASTQ: Standard format with '@' header, '+', and quality scores
- Mixed: Automatic detection and handling of mixed format files
- Compression: Support for gzip-compressed files (.fa.gz, .fq.gz)

### Output Compatibility
- Statistical results must exactly match jellyfish when using identical parameters
- Text format compatible with standard Unix text processing tools
- Binary format designed for fast reading by future rustkmer commands

### Platform Support
- Linux: Primary target, full feature support
- macOS: Supported with minor performance differences
- Windows: Supported with limitations in file I/O performance