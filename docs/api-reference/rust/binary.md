# Binary

**Module**: `rustkmer::output::binary`

## Overview

Binary output format for k-mer counts
Provides efficient binary serialization of k-mer counting results.

## API Reference

### Fns

#### new

```rust
pub fn new(stats: &CounterStats) -> Self {
```

Create a new binary header

#### to_bytes

```rust
pub fn to_bytes(&self) -> Vec<u8> {
```

Serialize header to bytes

#### from_bytes

```rust
pub fn from_bytes(bytes: &[u8]) -> ProcessingResult<Self> {
```

Parse header from bytes

#### calculate_file_size

```rust
pub fn calculate_file_size(num_kmers: usize) -> usize {
```

Calculate binary file size

# Arguments
* `num_kmers` - Number of k-mers

# Returns
Expected file size in bytes

---

*Source: [`binary.rs`](../../../output/binary.rs)*