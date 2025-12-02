# Encoding

**Module**: `rustkmer::kmer::encoding`

## Overview

K-mer encoding and decoding functions
Provides efficient bit-packed encoding of DNA sequences for k-mer counting.

## API Reference

### Consts

#### A

```rust
const A: u8 = 0; // A = 00
```

DNA base encoding constants

#### MAX_KMER_SIZE_IN_U64

```rust
pub const MAX_KMER_SIZE_IN_U64: usize = 32;
```

Maximum k-mer size that fits in a u64 (64 / 2 = 32)

### Fns

#### encode_kmer

```rust
pub fn encode_kmer(sequence: &str) -> Result<u64, KmerError> {
```

Encode a DNA sequence into a packed bit representation

# Arguments
* `sequence` - DNA sequence string (must contain only A, C, G, T)

# Returns
* `Ok(u64)` - Packed representation if valid
* `Err(KmerError)` - Error if invalid characters found

# Examples
```
use rustkmer::kmer::encoding::encode_kmer;

let encoded = encode_kmer("ATGC").unwrap();
// ATGC -> 00110110 (A=00, T=11, G=10, C=01)
assert_eq!(encoded, 0b00110110);
```

#### encode_kmer_bytes

```rust
pub fn encode_kmer_bytes(sequence: &[u8]) -> Result<u64, KmerError> {
```

Encode a DNA sequence from byte slice into a packed bit representation

# Arguments
* `sequence` - DNA sequence as bytes (must contain only A, C, G, T, case insensitive)

# Returns
* `Ok(u64)` - Packed representation if valid
* `Err(KmerError)` - Error if invalid characters found

#### decode_kmer

```rust
pub fn decode_kmer(encoded: u64, length: usize) -> String {
```

Decode a packed k-mer back into a DNA sequence string

# Arguments
* `encoded` - Packed k-mer representation
* `length` - Length of the k-mer (number of bases)

# Returns
DNA sequence string

# Examples
```
use rustkmer::kmer::encoding::{encode_kmer, decode_kmer};

let original = "ATGC";
let encoded = encode_kmer(original).unwrap();
let decoded = decode_kmer(encoded, original.len());
assert_eq!(decoded, original);
```

#### reverse_complement

```rust
pub fn reverse_complement(encoded: u64, length: usize) -> u64 {
```

Get the reverse complement of a packed k-mer

# Arguments
* `encoded` - Packed k-mer representation
* `length` - Length of the k-mer

# Returns
Packed reverse complement representation

#### validate_sequence

```rust
pub fn validate_sequence(sequence: &str) -> bool {
```

Validate that a DNA sequence contains only valid characters

# Arguments
* `sequence` - DNA sequence string

# Returns
`true` if valid, `false` if contains invalid characters

#### has_ambiguous_bases

```rust
pub fn has_ambiguous_bases(sequence: &str) -> bool {
```

Check if a sequence contains ambiguous bases (N)

# Arguments
* `sequence` - DNA sequence string

# Returns
`true` if contains ambiguous bases, `false` if all valid

---

*Source: [`encoding.rs`](../../../kmer/encoding.rs)*