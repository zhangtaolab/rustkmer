# Matrix

**Module**: `rustkmer::hash::matrix`

## Overview

Matrix hash function for k-mer hashing
Provides efficient binary matrix multiplication for k-mer hash computation
for optimal distribution and collision resistance.

## API Reference

### Fns

#### new

```rust
pub fn new(kmer_length: usize) -> Self {
```

Create a new matrix hash function

# Arguments
* `kmer_length` - Length of k-mers

# Returns
New MatrixHashFunction instance

#### hash

```rust
pub fn hash(&self, kmer_encoded: u64) -> u64 {
```

Compute hash for a k-mer

# Arguments
* `kmer_encoded` - Packed k-mer representation

# Returns
Hash value

#### size

```rust
pub fn size(&self) -> usize {
```

Get matrix size

#### size_mask

```rust
pub fn size_mask(&self) -> u64 {
```

Get size mask

---

*Source: [`matrix.rs`](../../../hash/matrix.rs)*