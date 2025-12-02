# Canonical

**Module**: `rustkmer::kmer::canonical`

## Overview

Canonical k-mer operations
Implements canonical k-mer representation (forward/reverse complement lexicographically smaller).

## API Reference

### Fns

#### canonical_kmer

```rust
pub fn canonical_kmer(kmer_encoded: u64, k: usize) -> ProcessingResult<u64> {
```

Get the canonical representation of a k-mer

The canonical k-mer is the lexicographically smaller of the forward k-mer
and its reverse complement.

# Arguments
* `kmer_encoded` - Packed k-mer representation
* `k` - K-mer length

# Returns
Canonical k-mer encoding

#### is_canonical

```rust
pub fn is_canonical(kmer_encoded: u64, k: usize) -> ProcessingResult<bool> {
```

Check if a k-mer is already in canonical form

# Arguments
* `kmer_encoded` - Packed k-mer representation
* `k` - K-mer length

# Returns
True if the k-mer is canonical, false otherwise

#### get_both_orientations

```rust
pub fn get_both_orientations(kmer_encoded: u64, k: usize) -> ProcessingResult<(String, String)> {
```

Get both forward and reverse complement sequences

# Arguments
* `kmer_encoded` - Packed k-mer representation
* `k` - K-mer length

# Returns
Tuple of (forward_sequence, reverse_complement_sequence)

---

*Source: [`canonical.rs`](../../../kmer/canonical.rs)*