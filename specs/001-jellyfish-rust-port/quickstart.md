# Quickstart Guide: RustKmer Count Implementation

**Purpose**: Get started with rustkmer count development and testing
**Target Audience**: Developers implementing the k-mer counting functionality
**Last Updated**: 2025-11-28

## Development Environment Setup

### Prerequisites
- Rust 1.80+ stable toolchain
- Git for version control
- Access to test data directory: `/Users/forrest/Temp/demodata/`
- jellyfish installed for validation (optional but recommended)

### Initial Project Setup

```bash
# Navigate to project root
cd /Users/forrest/GitHub/rustkmer

# Initialize Rust project (if not already done)
cargo init --name rustkmer

# Add required dependencies
cargo add clap --features derive
cargo add serde
cargo add thiserror
cargo add anyhow
cargo add rayon
cargo add criterion
cargo add bio
cargo add memmap2
cargo add smallvec
cargo add hashbrown

# Add development dependencies
cargo add --dev criterion
cargo add --dev tempfile
```

### Project Structure

The project follows this directory structure:
```
src/
├── lib.rs              # Library entry point
├── main.rs             # CLI application
├── cli/                # Command-line interface
├── kmer/               # K-mer operations
├── hash/               # Hash table implementation
├── io/                 # File I/O operations
├── parallel/           # Multi-threading
├── output/             # Output formatting
└── error.rs            # Error types
```

## Implementation Workflow

### Phase 1: Core K-mer Operations

1. **Implement K-mer Encoding** (`src/kmer/encoding.rs`)
   ```rust
   // 2-bit encoding: A=00, C=01, G=10, T=11
   pub fn encode_kmer(sequence: &str) -> Result<u64, KmerError> {
       // Implementation here
   }

   pub fn decode_kmer(encoded: u64, length: usize) -> String {
       // Implementation here
   }
   ```

2. **Canonical K-mer Logic** (`src/kmer/canonical.rs`)
   ```rust
   pub fn canonical_kmer(encoded: u64, length: usize) -> u64 {
       let reverse_complement = reverse_complement(encoded, length);
       std::cmp::min(encoded, reverse_complement)
   }
   ```

### Phase 2: Hash Table Implementation

1. **Concurrent Hash Table** (`src/hash/table.rs`)
   ```rust
   use hashbrown::HashMap;
   use std::sync::RwLock;

   pub struct KmerCounter {
       table: RwLock<HashMap<u64, u32>>,
       kmer_length: usize,
   }
   ```

2. **Overflow Storage** (`src/hash/overflow.rs`)
   ```rust
   // Disk-based storage for when memory is insufficient
   pub struct DiskOverflow {
       temp_files: Vec<PathBuf>,
   }
   ```

### Phase 3: File I/O and Processing

1. **FASTA/FASTQ Parsing** (`src/io/fasta.rs`, `src/io/fastq.rs`)
   ```rust
   use bio::io::fasta;
   use memmap2::Mmap;

   pub fn process_fasta_file<P: AsRef<Path>>(path: P) -> Result<Vec<String>, IoError> {
       // Implementation using bio crate
   }
   ```

2. **Memory-Mapped Processing** (`src/io/mmap.rs`)
   ```rust
   pub fn memory_map_file<P: AsRef<Path>>(path: P) -> Result<Mmap, std::io::Error> {
       // Implementation for large file processing
   }
   ```

### Phase 4: CLI Interface

1. **Command-line Arguments** (`src/cli/args.rs`)
   ```rust
   use clap::Parser;

   #[derive(Parser)]
   pub struct CountCommand {
       #[arg(short = 'k', long = "kmer-size", default_value = "31")]
       pub kmer_size: usize,

       #[arg(short = 'C', long = "canonical")]
       pub canonical: bool,

       #[arg(short = 't', long = "threads")]
       pub threads: Option<usize>,

       // ... other arguments
   }
   ```

2. **Main Count Logic** (`src/cli/commands/count.rs`)
   ```rust
   pub fn execute_count_command(args: CountCommand) -> Result<(), anyhow::Error> {
       // Main k-mer counting implementation
   }
   ```

### Phase 5: Multi-threading

1. **Parallel Processing** (`src/parallel/processor.rs`)
   ```rust
   use rayon::prelude::*;

   pub fn count_kmers_parallel(sequences: &[String], k: usize) -> KmerCounter {
       sequences
           .par_iter()
           .flat_map(|seq| extract_kmers(seq, k))
           .fold(KmerCounter::new, |mut counter, kmer| {
               counter.increment(kmer);
               counter
           })
           .reduce(KmerCounter::new, |mut acc, other| {
               acc.merge(other);
               acc
           })
   }
   ```

## Testing Strategy

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kmer_encoding() {
        assert_eq!(encode_kmer("ATCG"), Ok(0b00110011));
    }

    #[test]
    fn test_canonical_kmer() {
        let forward = encode_kmer("ATCG").unwrap();
        let reverse = encode_kmer("CGAT").unwrap();
        assert_eq!(canonical_kmer(forward, 4), canonical_kmer(reverse, 4));
    }
}
```

### Integration Tests

```rust
// tests/integration/count_tests.rs
use std::process::Command;

#[test]
fn test_basic_counting() {
    let output = Command::new("cargo")
        .args(&["run", "count", "-k", "13", "test/fixtures/small.fa"])
        .output()
        .expect("Failed to execute command");

    assert!(output.status.success());
}
```

### Validation Tests

```rust
// tests/integration/validation.rs
#[test]
fn test_jellyfish_compatibility() {
    // Run both jellyfish and rustkmer on same input
    // Compare statistical results for exact match
}
```

## Performance Testing

### Benchmark Setup

```rust
// benches/performance.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_kmer_counting(c: &mut Criterion) {
    let test_sequence = include_str!("../tests/fixtures/large_sequence.fa");

    c.bench_function("count_kmers_31", |b| {
        b.iter(|| {
            count_kmers(black_box(test_sequence), 31)
        })
    });
}

criterion_group!(benches, bench_kmer_counting);
criterion_main!(benches);
```

### Running Benchmarks

```bash
# Run performance benchmarks
cargo bench

# Compare with baseline
cargo bench --baseline main

# Generate HTML report
cargo bench -- --output-format html
```

## Testing Data Setup

### Validation Data

```bash
# Create symlinks to test data (avoid git tracking)
mkdir -p tests/fixtures
ln -s /Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa tests/fixtures/
ln -s /Users/forrest/Temp/demodata/fasta/small_test.fa tests/fixtures/
```

### Temporary Files

```rust
// Use temp directory for test outputs
let temp_dir = "/Users/forrest/Temp/demodata/test_output/";
std::fs::create_dir_all(temp_dir)?;
```

## Validation Process

### Jellyfish Comparison

```bash
# Test with small k-mer size first
jellyfish count -m 13 -s 100M -o jellyfish_13.jf tests/fixtures/small_test.fa
cargo run -- count -k 13 -s 100M -o rustkmer_13.rk tests/fixtures/small_test.fa

# Test canonical mode
jellyfish count -C -m 13 -s 100M -o jellyfish_13_C.jf tests/fixtures/small_test.fa
cargo run -- count -C -k 13 -s 100M -o rustkmer_13_C.rk tests/fixtures/small_test.fa
```

### Full Validation

```bash
# Progress to larger k-mer sizes
cargo run -- count -k 21 -C tests/fixtures/osa1_r7.asm.fa

# Compare results programmatically
python scripts/compare_results.py jellyfish_13.jf rustkmer_13.rk
```

## Development Workflow

### Code Quality

```bash
# Format code
cargo fmt

# Run linter
cargo clippy -- -D warnings

# Run all tests
cargo test

# Run with sanitizers (nightly Rust)
RUSTFLAGS="-Z sanitizer=address" cargo +nightly test
```

### Documentation

```bash
# Generate documentation
cargo doc --open

# Check documentation coverage
cargo doc --document-private-items
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/kmer-implementation

# Commit changes
git add .
git commit -m "Implement k-mer encoding and basic counting"

# Push and create PR
git push origin feature/kmer-implementation
```

## Common Issues and Solutions

### Memory Issues
- **Problem**: Hash table grows too large
- **Solution**: Implement disk overflow storage or configurable size limits

### Performance Bottlenecks
- **Problem**: Single-threaded processing is slow
- **Solution**: Use Rayon for parallel processing

### Compatibility Issues
- **Problem**: Results don't match jellyfish exactly
- **Solution**: Check edge case handling (ambiguous bases, short sequences)

### Build Errors
- **Problem**: Missing dependencies or version conflicts
- **Solution**: Use `cargo update` and check Cargo.toml versions

## Next Steps

1. Implement core k-mer operations and unit tests
2. Add hash table with overflow support
3. Implement file I/O using bio crate
4. Add multi-threading with Rayon
5. Create comprehensive test suite
6. Validate against jellyfish on test data
7. Performance benchmark and optimization
8. Documentation and release preparation

## Resources

- [Rust Bioinformatics Working Group](https://github.com/rust-bio/rust-bio)
- [Jellyfish Documentation](https://github.com/gmarcais/Jellyfish)
- [Rust Performance Book](https://nnethercote.github.io/perf-book/)
- [Rayon Parallelism Guide](https://docs.rs/rayon/)