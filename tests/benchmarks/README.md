# U128 Encoding Benchmarks

This directory contains benchmarks for measuring u128 encoding performance against u64 baseline.

## Running Benchmarks

```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench encoding_bench
cargo bench query_bench
cargo bench memory_bench
```

## Benchmarks

### encoding_bench.rs
- Tests u128 vs u64 encoding performance
- Measures encoding/decoding speed for k=1..64

### query_bench.rs
- Tests query performance with u128 k-mers
- Measures search speed for k=64 databases

### memory_bench.rs
- Tests memory usage patterns
- Measures memory consumption for large databases

## Performance Targets

- Encoding/Decoding: ≤110% of u64 time
- Query Operations: ≤105ms per query (≤5% slower)
- Database Size: Exactly 133% of u64 size