# API Reference

This section provides comprehensive API documentation for both Rust and Python interfaces of RustKmer. Whether you're integrating RustKmer into a Rust application or using the Python bindings for bioinformatics workflows, you'll find detailed documentation for all available functions, classes, and methods.

## Quick Navigation

### Rust API
- **[KmerCounter](rust/counter.md)** - Core k-mer counting functionality
- **[Database](rust/database.md)** - Database operations and storage
- **[Fuzzy Query](rust/fuzzy.md)** - Pattern matching and fuzzy search
- **[CLI](rust/cli.md)** - Command-line interface

### Python API
- **[KmerCounter](python/kmercounter.md)** - Python k-mer counting interface
- **[Database](python/database.md)** - Python database operations
- **[Examples](python/examples.md)** - Python usage examples

## Language Bindings

### Rust Library
The Rust library provides the highest performance and most comprehensive feature set:

```rust
use rustkmer::KmerCounter;

let mut counter = KmerCounter::new(21, true);
counter.count_file("genome.fa.gz")?;
println!("Total k-mers: {}", counter.get_total_count());
```

### Python Bindings
Python bindings offer easy integration with bioinformatics workflows:

```python
from rustkmer import KmerCounter

counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")
print(f"Total k-mers: {counter.get_total_count()}")
```

## Core Concepts

### K-mer Counting
- **k-mer**: A sequence of length k from DNA/RNA sequences
- **Canonical k-mer**: The lexicographically smaller of a k-mer and its reverse complement
- **Counting**: Tallying occurrences of each k-mer in a dataset

### Database Format
- **RKDB**: RustKmer Database format for efficient storage and retrieval
- **Memory-mapped**: Fast access without loading entire database into memory
- **Sorted vs Unsorted**: Optimized for different query patterns

### Fuzzy Querying
- **Wildcard patterns**: Support for N (any base) and custom patterns
- **Hamming distance**: Allowable substitutions in matches
- **Performance optimized**: Efficient algorithms for large-scale searches

## Performance Characteristics

| Operation | Rust Performance | Python Performance | Notes |
|-----------|------------------|-------------------|-------|
| Counting | ~1M k-mers/sec | ~1M k-mers/sec | Similar performance |
| Querying | ~4M queries/sec | ~3.5M queries/sec | Minimal overhead |
| Fuzzy Query | ~100K queries/sec | ~80K queries/sec | Pattern matching overhead |
| Memory Usage | Minimal | Minimal | Efficient implementations |

## Error Handling

### Rust Error Types
```rust
use rustkmer::{KmerError, KmerResult};

fn process_file() -> KmerResult<()> {
    // Your code here
    Ok(())
}
```

### Python Exceptions
```python
from rustkmer import KmerError

try:
    counter.count_file("invalid_file.fa")
except KmerError as e:
    print(f"Error: {e}")
```

## Thread Safety

- **Rust**: All operations are thread-safe when used properly
- **Python**: Global interpreter lock (GIL) protects most operations
- **Performance**: Multi-threading available through parallel features

## Version Compatibility

- **Rust**: Requires Rust 1.80+ stable
- **Python**: Supports Python 3.8+
- **Cross-platform**: Linux, macOS, Windows

## Getting Help

- **Examples**: See the [Tutorials](../tutorials/) section
- **Troubleshooting**: Check the [Appendix](../appendix/troubleshooting.md)
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and contribute

For detailed documentation of specific APIs, use the navigation sidebar to explore the Rust and Python API references.