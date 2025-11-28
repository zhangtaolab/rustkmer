# Database Format Contract: .rkdb

**Version**: 1.0
**Date**: 2025-11-28
**Status**: Implemented

## Format Overview

The `.rkdb` (rustkmer database) format is a binary file format designed for efficient k-mer storage and retrieval with support for fast binary search operations.

## File Structure

### Header Section (Bytes 0-63)

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 4 | [u8; 4] | magic | File format identifier ("RKDB") |
| 4 | 2 | u16 | version | Format version (current: 1) |
| 6 | 1 | u8 | kmer_size | K-mer length (1-127) |
| 7 | 1 | u8 | flags | Bit flags (bit 0: sorted, bit 1: canonical) |
| 8 | 8 | u64 | total_kmers | Number of unique k-mers |
| 16 | 8 | u64 | data_offset | Offset to first k-mer entry |
| 24 | 8 | u64 | index_offset | Offset to index section (future) |
| 32 | 8 | u64 | reserved_1 | Reserved for future use |
| 40 | 8 | u64 | reserved_2 | Reserved for future use |
| 48 | 8 | u64 | reserved_3 | Reserved for future use |
| 56 | 8 | u64 | checksum | Header checksum (CRC64) |

### Data Section (data_offset to EOF)

| Entry | Size | Type | Description |
|-------|------|------|-------------|
| Each | 8 | u64 | kmer | Encoded k-mer sequence |
| Each | 4 | u32 | count | K-mer occurrence count |

**Total per entry**: 12 bytes

## K-mer Encoding

### Binary Encoding Scheme

- **Base Mapping**: 2 bits per base
  - `A` → `00`
  - `T` → `01`
  - `G` → `10`
  - `C` → `11`

- **Packing**: Left-aligned in 64-bit value
- **Endianness**: Little-endian byte order
- **Maximum Length**: 32 bases (fits in 64 bits)

### Encoding Example

For k-mer "ATGC" (k=4):
```
A(00) T(01) G(10) C(11) → 00011011
Packed: 0001101100000000...0000 (64 bits)
Value: 0x1B00000000000000 (little-endian)
```

### Canonical Encoding

When canonical flag is set:
- Store lexicographically smaller of k-mer and its reverse complement
- Enables strand-agnostic querying
- Reduces database size by up to 50%

## Flag Definitions

| Bit | Name | Description |
|-----|------|-------------|
| 0 | SORTED | K-mers are sorted for binary search |
| 1 | CANONICAL | K-mers stored in canonical form |
| 2-7 | RESERVED | Reserved for future use |

## Validation Rules

### Header Validation

1. **Magic Number**: Must be exactly "RKDB"
2. **Version**: Must be supported (currently only version 1)
3. **K-mer Size**: Must be between 1 and 127
4. **Checksum**: CRC64 must match calculated value
5. **Offsets**: Must be within file bounds
6. **Alignment**: Data offset must be 8-byte aligned

### Data Validation

1. **Entry Count**: Must match total_kmers in header
2. **K-mer Encoding**: All k-mers must be valid for kmer_size
3. **Sorting**: If sorted flag set, entries must be in ascending order
4. **Canonical**: If canonical flag set, all k-mers must be canonical

## Performance Characteristics

### Lookup Performance

- **Binary Search**: O(log n) time complexity
- **Memory Mapping**: OS-level caching for large files
- **Cache Locality**: Sequential access for batch queries
- **Seek Optimization**: Direct offset calculation

### Memory Requirements

- **Header**: 64 bytes fixed
- **Entries**: 12 bytes per unique k-mer
- **Index**: Future expansion (currently unused)
- **Working Memory**: Minimal for binary search

### File Size Estimates

| K-mers | Estimated Size |
|--------|---------------|
| 1,000 | ~12 KB |
| 100,000 | ~1.2 MB |
| 1,000,000 | ~12 MB |
| 10,000,000 | ~120 MB |
| 100,000,000 | ~1.2 GB |

## Implementation Guidelines

### Reading Database

```rust
// Pseudocode for database reading
fn read_database(path: &Path) -> Result<Database, Error> {
    let mut file = File::open(path)?;

    // Read and validate header
    let header = read_header(&mut file)?;
    header.validate()?;

    // Seek to data section
    file.seek(SeekFrom::Start(header.data_offset))?;

    // Read entries
    let mut entries = Vec::with_capacity(header.total_kmers as usize);
    for _ in 0..header.total_kmers {
        let kmer = file.read_u64::<LittleEndian>()?;
        let count = file.read_u32::<LittleEndian>()?;
        entries.push(KmerEntry { kmer, count });
    }

    Ok(Database { header, entries })
}
```

### Query Algorithm

```rust
// Binary search implementation
fn query_kmer(database: &Database, query: u64) -> Option<u32> {
    if !database.header.sorted {
        return linear_search(database, query);
    }

    let mut left = 0;
    let mut right = database.entries.len();

    while left < right {
        let mid = (left + right) / 2;
        match query.cmp(&database.entries[mid].kmer) {
            Ordering::Equal => return Some(database.entries[mid].count),
            Ordering::Less => right = mid,
            Ordering::Greater => left = mid + 1,
        }
    }

    None
}
```

## Error Handling

### Format Errors

| Error | Condition | Recovery |
|-------|-----------|----------|
| `InvalidMagic` | Magic number not "RKDB" | Fatal |
| `UnsupportedVersion` | Version not supported | Fatal |
| `CorruptedHeader` | Checksum mismatch | Fatal |
| `InvalidOffset` | Offset outside file bounds | Fatal |
| `TruncatedFile` | File ends unexpectedly | Fatal |

### Data Errors

| Error | Condition | Recovery |
|-------|-----------|----------|
| `InvalidKmer` | K-mer encoding invalid | Skip entry |
| `DuplicateKmer` | Duplicate k-mer found | Use last count |
| `UnsortedData` | Data not sorted when flag set | Linear search fallback |
| `CountOverflow` | Count exceeds u32::MAX | Cap at u32::MAX |

## Extensibility

### Version 2.0 Planning

**Potential Additions**:
- Compression support (LZ4, Zstd)
- Extended k-mer sizes (>32 bases)
- Index section implementation
- Metadata extensions
- Encryption support

**Backward Compatibility**:
- Version 1.0 readers must handle version 2.0+ gracefully
- New features must be optional
- Core format must remain stable

### Future Index Types

- **Hash Index**: O(1) lookup with higher memory usage
- **B-Tree Index**: Better range query support
- **Bloom Filter**: Fast "not found" checks
- **Compressed Index**: Reduced storage overhead

## Testing Requirements

### Format Tests

- Magic number validation
- Version compatibility testing
- Checksum verification
- Offset boundary testing
- Endianness validation

### Content Tests

- K-mer encoding/decoding accuracy
- Sorting verification
- Canonical k-mer handling
- Count validation
- Duplicate detection

### Performance Tests

- Binary search correctness
- Memory usage verification
- Large file handling
- Concurrent access testing
- Corruption recovery

## Tools and Utilities

### Database Creation

```bash
# Create database from k-mer counts
rustkmer count --output database.rkdb input.fa
```

### Database Validation

```bash
# Validate database format and integrity
rustkmer validate database.rkdb
```

### Database Information

```bash
# Display database statistics
rustkmer stats database.rkdb
```

### Database Conversion

```bash
# Convert between formats (future feature)
rustkmer convert --from jf --to rkdb input.jf output.rkdb
```