# Data Model: Jellyfish Query Implementation

**Date**: 2025-11-28
**Feature**: Jellyfish Query Implementation
**Status**: Implemented

## Overview

The data model for the jellyfish query implementation focuses on efficient storage and retrieval of k-mer counts with support for fast binary search operations and jellyfish-compatible interfaces.

## Core Entities

### 1. Database Header

**Purpose**: Metadata container for database validation and navigation

**Fields**:
- `magic: [u8; 4]` - File format identifier ("RKDB")
- `version: u16` - Format version (currently 1)
- `kmer_size: u8` - Length of k-mers in the database (1-127)
- `total_kmers: u64` - Total number of unique k-mers stored
- `sorted: bool` - Whether k-mers are sorted for binary search
- `data_offset: u64` - Byte offset to k-mer data section
- `index_offset: u64` - Byte offset to index section (future use)
- `canonical: bool` - Whether k-mers stored in canonical form

**Validation Rules**:
- Magic number must equal "RKDB"
- Version must be supported
- K-mer size must be between 1 and 127
- Data offset must be >= header size
- Total k-mers must be >= 0

**State Transitions**:
- Created: Header written when database is initialized
- Validated: Header validated when database is opened
- Updated: Metadata updated when database is modified

### 2. K-mer Entry

**Purpose**: Individual k-mer storage with associated count

**Fields**:
- `kmer: u64` - Encoded k-mer sequence (up to 32 bases)
- `count: u32` - Occurrence count of this k-mer

**Validation Rules**:
- K-mer encoding must be valid for specified k-mer size
- Count must be >= 0
- Maximum k-mer size: 32 bases (fits in 64 bits)

**Constraints**:
- When sorted: entries ordered by kmer value for binary search
- Memory layout: 12 bytes per entry (8 + 4)
- Alignment: Natural alignment for efficient access

### 3. Database Query

**Purpose**: Query engine for k-mer lookups with multiple access modes

**Configuration**:
- `file: BufReader<File>` - Database file handle
- `header: DatabaseHeader` - Parsed database metadata
- `memory_loaded: bool` - Whether database is preloaded
- `cached_entries: Option<Vec<KmerEntry>>` - In-memory cache

**Query Modes**:
- **Memory mode**: All entries loaded into RAM for fastest access
- **Disk mode**: Binary search on file with minimal memory usage
- **Mixed mode**: Intelligent caching based on query patterns

**Performance Characteristics**:
- Memory queries: O(1) lookup time
- Disk queries: O(log n) lookup with disk seeks
- Batch queries: Amortized cost per query

## Relationships

```
Database (1) ←→ (1) DatabaseHeader
Database (1) ←→ (N) KmerEntry
DatabaseQuery (1) ←→ (1) Database
DatabaseQuery (1) ←→ (0..N) KmerEntry (cached)
```

## Data Flow Patterns

### Query Flow
1. **Database Opening**:
   - Read and validate header
   - Determine query mode (memory vs disk)
   - Optional pre-load of entries

2. **K-mer Query**:
   - Encode query k-mer
   - Binary search in sorted entries
   - Return count or error

3. **Batch Query**:
   - Process multiple k-mers efficiently
   - Minimize file I/O for disk mode
   - Optimize for cache locality

### Database Creation Flow
1. **Header Creation**:
   - Initialize with metadata
   - Set magic number and version
   - Calculate offsets

2. **Entry Addition**:
   - Encode k-mers to 64-bit values
   - Sort by k-mer value
   - Write entries sequentially

## Storage Format

### File Layout
```
Offset 0:     DatabaseHeader (fixed size)
Offset N:     KmerEntry[0]      (12 bytes)
Offset N+12:  KmerEntry[1]      (12 bytes)
...
Offset N+12*M: KmerEntry[M]      (12 bytes)
```

### Binary Encoding
- **A/T/G/C**: 2 bits per base (00, 01, 10, 11)
- **Packing**: Left-aligned in 64-bit value
- **Padding**: Unused bits zero-padded
- **Endian**: Little-endian byte order

## Error Model

### Validation Errors
- **Invalid Magic Number**: File not a rustkmer database
- **Unsupported Version**: Database format too new/old
- **Corrupted Header**: Invalid metadata
- **Invalid K-mer Size**: Mismatch with query requirements

### Runtime Errors
- **File Not Found**: Database file missing
- **Permission Denied**: Cannot read database
- **I/O Error**: Disk read/write failure
- **Memory Error**: Insufficient memory for pre-loading

### Query Errors
- **Invalid K-mer**: Contains non-ATCG characters
- **Size Mismatch**: K-mer length doesn't match database
- **Encoding Error**: Failed to encode k-mer sequence
- **Not Found**: K-mer not present in database

## Performance Considerations

### Memory Usage
- **Header**: ~32 bytes
- **Per Entry**: 12 bytes
- **Cache**: Optional pre-load of all entries
- **Query Buffer**: Minimal for binary search

### I/O Patterns
- **Sequential reads**: For database loading
- **Random seeks**: For binary search queries
- **Read-ahead**: Optimized for batch queries
- **Memory mapping**: Optional for large databases

### Optimization Strategies
- **Binary search**: O(log n) lookup complexity
- **Cache warming**: Pre-load frequently accessed entries
- **Batch processing**: Minimize per-query overhead
- **Memory mapping**: OS-level caching for large files

## Extensibility

### Future Index Types
- **Hash Index**: O(1) lookup with higher memory usage
- **B-tree Index**: Better range query performance
- **Compressed Index**: Reduced storage overhead

### Additional Features
- **Compression**: Entry-level or block-level compression
- **Versioning**: Multiple database versions
- **Metadata**: Extended custom metadata fields
- **Encryption**: Secure database storage

## Compatibility

### Jellyfish Compatibility
- **Interface**: Same CLI argument patterns
- **Output**: Identical tab-separated format
- **Error Messages**: Compatible error reporting
- **File Formats**: Custom format (not jellyfish compatible)

### Future Interoperability
- **Import/Export**: Jellyfish database conversion
- **Standard Formats**: Support for industry formats
- **API Interface**: Programmatic access
- **Web Service**: HTTP API for remote queries