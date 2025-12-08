# Data Model: u128 Encoding Upgrade

**Date**: 2025-12-08
**Feature**: 008-u128-encoding

## Core Entities

### 1. Kmer

Represents a DNA sequence encoded as a 128-bit integer.

```rust
pub struct Kmer {
    value: u128,        // 128-bit encoded value
    k_size: u8,         // Length of k-mer (1-64)
}
```

**Fields**:
- `value`: 128-bit integer containing encoded DNA sequence (2 bits per base)
- `k_size`: Length of the original DNA sequence (1-64)

**Validation Rules**:
- k_size must be between 1 and 64
- Value must not use bits beyond 2 * k_size
- Only valid DNA bases (A, C, G, T) allowed

**State Transitions**:
```
DNA String → encode() → Kmer
Kmer → decode() → DNA String
Kmer → reverse_complement() → Kmer
Kmer → canonical() → Kmer (lexicographically smaller)
```

### 2. KmerEntry

Database entry storing a k-mer and its count.

```rust
pub struct KmerEntry {
    kmer: u128,        // 128-bit encoded k-mer
    count: u32,        // Occurrence count
}
```

**Fields**:
- `kmer`: 128-bit encoded k-mer value
- `count`: 32-bit unsigned integer for occurrence count

**Storage Layout**: 16 bytes total
- Bytes 0-15: kmer (little-endian u128)
- Bytes 16-19: count (little-endian u32)

### 3. DatabaseHeader

Metadata header for RKDB database files.

```rust
pub struct DatabaseHeader {
    magic: [u8; 4],        // "RKDB"
    version: u16,          // Format version (2 for u128)
    k_size: u8,            // K-mer size (1-64)
    flags: u8,             // Bit flags (canonical, sorted)
    total_kmers: u64,      // Total number of entries
    reserved: [u8; 8],     // Reserved for future use
}
```

**Flags**:
- Bit 0: Canonical representation enabled
- Bit 1: Entries sorted
- Bits 2-7: Reserved

### 4. KmerDatabase

Main database structure for storing and querying k-mers.

```rust
pub struct KmerDatabase {
    header: DatabaseHeader,
    entries: Mmap,         // Memory-mapped entries
    index: Option<BTreeMap<u128, usize>>,  // Optional index
}
```

**Operations**:
- `create(fasta_path: &str, k_size: u8) -> Result<Self>`
- `query(&self, kmer: &Kmer) -> Option<u32>`
- `query_batch(&self, kmers: &[Kmer]) -> Vec<Option<u32>>`
- `dump(&self, format: OutputFormat) -> Result<()>`

## Relationships

```
DatabaseHeader (1) ──► KmerDatabase (1)
    │                        │
    │                        ├─► KmerEntry (0..N)
    │                        │   └─► Kmer (1)
    │                        └─► Index (0..1)
    └─► controls ──────────────────┘
```

## Validation Rules

### Kmer Encoding
```rust
pub fn validate_kmer(value: u128, k_size: u8) -> Result<(), KmerError> {
    if k_size == 0 || k_size > 64 {
        return Err(KmerError::InvalidKSize(k_size));
    }

    let max_bits = k_size * 2;
    let mask = (1u128 << max_bits) - 1;

    if value & !mask != 0 {
        return Err(KmerError::Overflow);
    }

    Ok(())
}
```

### Database Format
```rust
pub fn validate_header(header: &DatabaseHeader) -> Result<(), DatabaseError> {
    if &header.magic != b"RKDB" {
        return Err(DatabaseError::InvalidMagic);
    }

    if header.version != 2 {
        return Err(DatabaseError::UnsupportedVersion(header.version));
    }

    if header.k_size == 0 || header.k_size > 64 {
        return Err(DatabaseError::InvalidKSize(header.k_size));
    }

    Ok(())
}
```

## Error Types

```rust
#[derive(Debug, thiserror::Error)]
pub enum KmerError {
    #[error("Invalid k-mer size: {0} (must be 1-64)")]
    InvalidKSize(u8),

    #[error("DNA sequence contains invalid characters")]
    InvalidSequence,

    #[error("K-mer value overflows for given k-size")]
    Overflow,

    #[error("Ambiguous bases (N) not allowed in k-mers")]
    AmbiguousBase,
}

#[derive(Debug, thiserror::Error)]
pub enum DatabaseError {
    #[error("Invalid database magic number")]
    InvalidMagic,

    #[error("Unsupported database version: {0}")]
    UnsupportedVersion(u16),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Database corrupted: {0}")]
    Corruption(String),
}
```

## Statistics Tracking

For maintaining consistency with u64 implementation:

```rust
#[derive(Debug, Clone)]
pub struct ProcessingStats {
    pub total_sequences: u64,
    pub valid_kmers: u64,
    pub skipped_ambiguous: u64,
    pub skipped_too_short: u64,
    pub unique_kmers: u64,
    pub total_count: u64,
}
```

## Performance Considerations

### Memory Layout
- Entries are 16 bytes (33% larger than u64 format)
- Sorted entries enable binary search (O(log n))
- Memory mapping enables efficient access without loading entire database

### Index Strategy
- Optional B-tree index for faster random access
- Trade-off: memory usage vs query speed
- Can be built on-demand for frequently queried databases

### Batch Processing
- Vectorized operations for multiple k-mers
- Reduces function call overhead
- Better cache locality

## Migration Path

Since backward compatibility is not required:
- New databases will use version 2 format
- No migration tools needed
- Clear error messages for old format versions