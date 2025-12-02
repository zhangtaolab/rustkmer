# Operations

**Module**: `rustkmer::kmer::operations`

## Overview

K-mer extraction and processing operations
Provides functions for extracting k-mers from DNA sequences with proper
validation and filtering according to requirements.

## API Reference

### Fns

#### extract_kmers

```rust
pub fn extract_kmers(sequence: &str, kmer_size: usize) -> Result<Vec<u64>, KmerError> {
```

Extract all k-mers from a DNA sequence using sliding window

# Arguments
* `sequence` - DNA sequence string
* `kmer_size` - Length of k-mers to extract

# Returns
* `Vec<u64>` - Vector of packed k-mer representations
* `Err(KmerError)` - Error if sequence is too short or invalid

# Examples
```
use rustkmer::kmer::operations::extract_kmers;

let kmers = extract_kmers("ATGCGAT", 3).unwrap();
assert_eq!(kmers.len(), 6); // "ATG", "TGC", "GCG", "CGA", "GAT", "ATG"
```

#### extract_kmers_filter_ambiguous

```rust
pub fn extract_kmers_filter_ambiguous(sequence: &str, kmer_size: usize) -> Vec<u64> {
```

Extract k-mers from a sequence, skipping those with ambiguous bases

This function implements the requirement to skip k-mers containing ambiguous bases (N)
rather than skipping the entire sequence.

# Arguments
* `sequence` - DNA sequence string
* `kmer_size` - Length of k-mers to extract

# Returns
Vector of packed k-mer representations, excluding any containing ambiguous bases

#### filter_sequence

```rust
pub fn filter_sequence(sequence: &str, kmer_size: usize) -> bool {
```

Filter a sequence by checking if it contains valid DNA and sufficient length

# Arguments
* `sequence` - DNA sequence string
* `kmer_size` - Minimum required length

# Returns
`true` if sequence is valid and long enough, `false` otherwise

#### count_extractable_kmers

```rust
pub fn count_extractable_kmers(sequence: &str, kmer_size: usize) -> usize {
```

Count the number of valid k-mers that can be extracted from a sequence

# Arguments
* `sequence` - DNA sequence string
* `kmer_size` - Length of k-mers

# Returns
Number of extractable k-mers (accounting for invalid regions)

#### analyze_sequence_quality

```rust
pub fn analyze_sequence_quality(sequence: &str) -> String {
```

Analyze sequence quality and provide statistics

# Arguments
* `sequence` - DNA sequence string

# Returns
String with quality statistics

#### reverse_complement_bits

```rust
pub fn reverse_complement_bits(kmer: u64, k: usize) -> Result<u64, KmerError> {
```

Compute reverse complement of a k-mer (bit manipulation)

# Arguments
* `kmer` - Packed k-mer representation
* `k` - K-mer length

# Returns
Reverse complement k-mer or error if k is too large

#### reverse_complement

```rust
pub fn reverse_complement(sequence: &str) -> String {
```

Compute reverse complement of a DNA sequence string

# Arguments
* `sequence` - DNA sequence string

# Returns
Reverse complement string

#### canonical_kmer

```rust
pub fn canonical_kmer(kmer_encoded: u64, k: usize) -> Result<u64, KmerError> {
```

Get canonical k-mer (lexicographically smaller of forward and reverse complement)

# Arguments
* `kmer_encoded` - Packed k-mer representation
* `k` - K-mer length

# Returns
Canonical k-mer encoding or error if k is too large

---

*Source: [`operations.rs`](../../../kmer/operations.rs)*