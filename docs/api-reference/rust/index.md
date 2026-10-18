# Rust API Reference

This section provides comprehensive documentation for all Rust APIs in RustKmer.

## Core Components

### KmerCounter
The main k-mer counting interface with support for:
- Exact k-mer counting
- Canonical k-mer processing
- Memory-efficient counting algorithms
- Large file processing capabilities

### Database Operations
Efficient database functionality for:
- Binary database storage (.rkdb format)
- High-speed querying operations
- Memory-mapped file access
- Fuzzy search capabilities

### Fuzzy Query
Advanced query functionality supporting:
- Pattern matching with wildcards
- Hamming distance calculations
- Substitution queries
- Performance-optimized search algorithms

### Command Line Interface
Complete CLI tool supporting all library features:
- Batch processing operations
- Multiple output formats
- Progress reporting and logging
- Cross-platform compatibility

## Performance Characteristics

RustKmer delivers world-class performance:

| Feature | Performance | Memory Usage |
|---------|-------------|--------------|
| Counting | ~1M k-mers/sec | <100MB for 1GB files |
| Querying | ~4M queries/sec | <2MB additional overhead |
| Database creation | Stream processing | Linear memory usage |

## Usage Examples

```rust
use rustkmer::KmerCounter;

// Create a new counter (k, canonical, initial capacity, threads)
let counter = KmerCounter::new(21, true, 1000000, 4)?;

// Count k-mers from a file
counter.count_file("genome.fa")?;

// Get statistics
let total = counter.total_kmers();
let unique = counter.unique_kmers();

println!("Total k-mers: {}, Unique k-mers: {}", total, unique);
```

For detailed API documentation, see the specific modules listed in the navigation.
