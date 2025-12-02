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

// Create a new counter
let mut counter = KmerCounter::new(21, true);

// Count k-mers from a file
counter.count_file("genome.fa.gz")?;

// Get statistics
let total = counter.get_total_count();
let unique = counter.get_unique_count();

println!("Total k-mers: {}, Unique k-mers: {}", total, unique);
```

For detailed API documentation, see the specific modules listed in the navigation.
