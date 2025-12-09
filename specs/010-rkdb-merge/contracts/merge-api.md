# Merge Command API Contract

**Version**: 1.0.0
**Date**: 2025-12-08

## Command Interface

### Basic Syntax

```bash
rustkmer merge [OPTIONS] --output <OUTPUT> --input <INPUT>...
```

### Required Arguments

| Flag | Long Form | Description | Type | Validation |
|------|-----------|-------------|------|------------|
| `-i` | `--input` | Input database files to merge | Vec<PathBuf> | Must exist, be readable, valid RKDB format |
| `-o` | `--output` | Output merged database file | PathBuf | Parent directory must exist, must not be input file |

### Optional Arguments

| Flag | Long Form | Description | Type | Default |
|------|-----------|-------------|------|---------|
| `-t` | `--threads` | Number of threads for merging | usize | 0 (auto-detect) |
| | `--temp-dir` | Temporary directory for operations | PathBuf | System temp directory |
| `-v` | `--verbose` | Enable verbose output | flag | false |
| `-q` | `--quiet` | Suppress non-error output | flag | false |
| | `--keep-intermediate` | Keep temporary files for debugging | flag | false |

### Argument Validation Rules

1. **Input Files**:
   - Minimum 2 files required
   - All files must have `.rkdb` extension
   - All files must exist and be readable
   - All files must have same k-mer size
   - All files must have same canonical mode

2. **Output File**:
   - Parent directory must exist and be writable
   - Cannot be the same as any input file
   - Must have `.rkdb` extension (added if missing)

## Programmatic API

### Core Functions

```rust
/// Merge multiple RKDB databases
pub fn merge_databases(
    input_paths: &[PathBuf],
    config: &MergeConfig,
) -> Result<RKDatabase, MergeError>

/// Execute merge command from CLI arguments
pub fn execute_merge(args: &MergeArgs) -> Result<(), anyhow::Error>
```

### Data Structures

```rust
/// CLI arguments for merge command
#[derive(Args, Debug)]
pub struct MergeArgs {
    pub input: Vec<PathBuf>,
    pub output: PathBuf,
    pub temp_dir: Option<PathBuf>,
    pub threads: usize,
    pub verbose: bool,
    pub quiet: bool,
    pub force: bool,
    pub keep_intermediate: bool,
}

/// Merge operation configuration
pub struct MergeConfig {
    pub max_memory_usage: usize,
    pub chunk_size: usize,
    pub temp_dir: PathBuf,
    pub use_streaming: bool,
    pub threads: usize,
}

/// Merge operation statistics
pub struct MergeStats {
    pub input_databases: Vec<String>,
    pub input_kmers: Vec<u64>,
    pub output_kmers: u64,
    pub unique_kmers: u64,
    pub merge_time: Duration,
    pub peak_memory: usize,
    pub strategy_used: MergeStrategy,
}
```

## Output Formats

### Standard Output (Normal Mode)

```
Merging 3 databases...
  1: /path/to/db1.rkdb
  2: /path/to/db2.rkdb
  3: /path/to/db3.rkdb
Validating database compatibility...
  ✓ Database '/path/to/db2.rkdb' is compatible
  ✓ Database '/path/to/db3.rkdb' is compatible
Starting merge operation...
Loading database 1/3: /path/to/db1.rkdb
  Merging 1000000 k-mers...
Loading database 2/3: /path/to/db2.rkdb
  Merging 1500000 k-mers...
Loading database 3/3: /path/to/db3.rkdb
  Merging 800000 k-mers...
Total unique k-mers after merge: 2100000
Total k-mer counts after merge: 3300000
Saving merged database to: /path/to/output.rkdb
Merge completed successfully!
  Total input databases: 3
  Output database: /path/to/output.rkdb
  K-mer size: 31
  Total k-mers: 3300000
  Time elapsed: 45.23s
  Canonical mode: true
  Sorted: true
```

### Quiet Mode (-q)

No output unless error occurs.

### Verbose Mode (-v)

Includes additional debugging information:
- Memory usage statistics
- Strategy selection reasoning
- Progress percentages for large operations
- Temporary file locations

### Error Output

All errors are printed to stderr with clear, actionable messages:

```
Error: Database compatibility error
  Database '/path/to/db2.rkdb' has k-mer size 21, expected 31
  Use --force to override compatibility checks (not recommended)
```

## Error Responses

| Error Code | Message Format | HTTP-like Status | Recovery |
|------------|----------------|------------------|----------|
| MERGE_001 | "At least 2 input databases are required" | 400 Bad Request | User action |
| MERGE_002 | "Database '{path}' not found" | 404 Not Found | User action |
| MERGE_003 | "Database '{path}' has k-mer size {size}, expected {expected}" | 422 Unprocessable | Use --force or fix input |
| MERGE_004 | "Insufficient memory: required {required}MB, available {available}MB" | 503 Service Unavailable | Auto-fallback to streaming |
| MERGE_005 | "K-mer count overflow for kmer {kmer:x}" | 500 Internal Server | Logging only |
| MERGE_006 | "I/O error: {message}" | 500 Internal Server | Retry possible |
| MERGE_007 | "Database corruption in {file}: {reason}" | 422 Unprocessable | Fix input file |

## Performance Requirements

### Response Time Targets

| Database Size | Target Merge Time | Memory Limit |
|---------------|------------------|--------------|
| < 1M k-mers | < 30 seconds | < 100MB |
| 1-10M k-mers | < 5 minutes | < 500MB |
| 10-100M k-mers | < 30 minutes | < 2GB |
| > 100M k-mers | < 2 hours | Streaming mode |

### Throughput Requirements

- Minimum: 10,000 k-mers/second processing rate
- Target: 50,000 k-mers/second with parallel processing
- Peak memory usage: < 3x unique k-mers in output

## Security Considerations

1. **Input Validation**: All inputs must be validated before processing
2. **Path Traversal**: Prevent access to files outside intended directories
3. **Resource Limits**: Enforce memory and CPU limits
4. **Temporary Files**: Secure creation and cleanup of temporary files

## Testing Requirements

### Unit Tests
- Test merge with identical k-mers
- Test merge with unique k-mers
- Test overflow handling
- Test error conditions

### Integration Tests
- CLI command with various argument combinations
- Large dataset performance tests
- Memory usage validation
- Error handling verification

### Property Tests
- Merge associativity: (A+B)+C = A+(B+C)
- Merge commutativity: A+B = B+A
- Identity property: A+empty = A