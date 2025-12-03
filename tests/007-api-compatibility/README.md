# RustKmer Python API Compatibility Tests

This directory contains test infrastructure for verifying Python API compatibility with Rust CLI.

## Directory Structure

- `test_data/`: Test datasets organized by size
  - `small/`: 1MB-100MB datasets for rapid iteration
  - `medium/`: 100MB-10GB datasets for validation testing
  - `large/`: >10GB datasets for performance testing

- `compatibility_framework/`: CLI vs Python comparison utilities
- `performance_benchmarks/`: Performance testing for <10% overhead validation

## Test Categories

1. **Database Format Consistency**: Bit-for-bit comparison of generated databases
2. **Query Interoperability**: Cross-platform query result validation
3. **Fuzzy Query Consistency**: Advanced query feature compatibility
4. **Performance Validation**: <10% overhead benchmarking

## Running Tests

```bash
# Run all compatibility tests
cargo test compatibility

# Run performance benchmarks
cargo bench compatibility

# Run specific test suite
python -m pytest tests/007-api-compatibility/compatibility_framework/
```