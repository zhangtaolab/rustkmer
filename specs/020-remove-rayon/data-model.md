# Data Model: RustKmer Sequential Processing

**Date**: 2025-12-13
**Feature**: Remove Rayon Library and Parallel Processing Support
**Branch**: 020-remove-rayon

## Overview

This document describes the data models and structures used in rustkmer after the removal of Rayon parallel processing. The data model remains unchanged from the parallel version, as the removal of parallel processing only affects the execution strategy, not the data structures themselves.

## Core Entities

### 1. K-mer

**Description**: A k-mer is a substring of length k from a biological sequence (DNA/RNA).

**Attributes**:
- `sequence`: String representation (ACGT characters)
- `length`: usize (k value, 1-64)
- `encoded`: u128 (binary encoding for efficient storage and comparison)
- `canonical`: bool (whether this is the canonical form of the k-mer and its reverse complement)

**Relationships**:
- Multiple k-mers can be derived from a single sequence
- Each k-mer has exactly one canonical representation
- K-mers are stored in HashMap with counts

**Validation Rules**:
- Length must be between 1 and 64 bases
- Only A, C, G, T, N characters allowed (N treated specially)
- Encoded representation must be consistent across operations

### 2. K-mer Counter

**Description**: Accumulates counts of k-mers from input sequences.

**Attributes**:
- `k`: usize (k-mer length)
- `canonical`: bool (whether to store canonical k-mers only)
- `counts`: HashMap<u128, u32> (k-mer encoding to count mapping)
- `total_kmers`: u64 (total k-mers processed)

**Relationships**:
- Contains multiple K-mer entities
- Can be persisted to RKDB format
- Can be merged with other counters

**State Transitions**:
```
Empty -> Counting -> Complete
  ↓         ↓           ↓
      Adding sequences and incrementing counts
```

**Sequential Processing**:
- Sequences are processed one at a time
- K-mers are extracted sequentially from each sequence
- Counts are incremented in order (no parallel updates)

### 3. RKDB Database

**Description**: Binary database format for storing k-mer counts with efficient random access.

**Attributes**:
- `header`: DatabaseHeader (metadata)
- `data`: Vec<(u128, u32)> (sorted k-mer count pairs)
- `index`: Option<BTreeMap<u128, usize>> (optional index for fast lookups)
- `mmap`: Option<Mmap> (memory-mapped file for large databases)

**Relationships**:
- Produced by KmerCounter
- Consumed by Query operations
- Can be merged with other databases

**State Transitions**:
```
Unloaded -> Loading -> Loaded -> Querying
   ↓          ↓          ↓          ↓
    Load from file into memory or mmap
```

**Sequential Processing**:
- File reading is sequential
- Queries are processed one at a time
- Binary search operations are sequential (no parallel lookups)

### 4. Database Header

**Description**: Metadata for RKDB database files.

**Attributes**:
- `magic`: [u8; 4] (file identifier, b"RKDB")
- `version`: u16 (format version, currently 2)
- `kmer_size`: u8 (k-mer length)
- `total_kmers`: u64 (total unique k-mers)
- `sorted`: bool (whether data is sorted)
- `canonical`: bool (whether canonical k-mers were used)
- `data_offset`: u64 (offset to k-mer data section)
- `index_offset`: u64 (offset to index section)

**Validation Rules**:
- Magic number must match "RKDB"
- Version must be supported (currently 2)
- K-mer size must be 1-64
- File offsets must be valid

### 5. Query Result

**Description**: Result of a k-mer query operation.

**Attributes**:
- `kmer`: String (k-mer sequence)
- `count`: u32 (k-mer count in database)
- `exists`: bool (whether k-mer was found)
- `encoding`: u128 (encoded k-mer for verification)

**Relationships**:
- References a specific K-mer
- Associated with a specific RKDB Database

**Sequential Processing**:
- Each query is processed independently
- Results are returned in query order
- No parallel aggregation needed

### 6. Fuzzy Query Pattern

**Description**: Pattern for fuzzy k-mer matching with wildcards and mutations.

**Attributes**:
- `pattern`: String (e.g., "A*TG*C")
- `max_mismatches`: usize (Hamming distance tolerance)
- `wildcards`: Vec<usize> (positions of wildcard characters)
- `fixed_bases`: Vec<(usize, char)> (non-wildcard positions)

**Relationships**:
- Used to search RKDB Database
- Generates multiple Query Results

**Sequential Processing**:
- Pattern expansion is sequential
- Each candidate k-mer is checked sequentially
- Results are accumulated in order

## Data Flow

### Count Command Flow

```
Input FASTA/FASTQ
        ↓
Sequence Reader (bio crate)
        ↓
Sequential Sequence Processing
        ↓
K-mer Extractor (sliding window)
        ↓
Sequential K-mer Counting (HashMap)
        ↓
RKDB Database Writer
        ↓
Output .rkdb file
```

**Key Points**:
- Sequences processed one at a time
- K-mers extracted sequentially from each sequence
- Count updates are sequential (single-threaded HashMap)

### Query Command Flow

```
Input K-mers (stdin/file/CLI)
        ↓
Sequential K-mer List Processing
        ↓
RKDB Database Loader
        ↓
Sequential Binary Search (or hash lookup)
        ↓
Query Result Accumulator
        ↓
Output (text/JSON/TSV)
```

**Key Points**:
- K-mers processed in input order
- Each lookup is independent
- Results returned in same order as input

### Fuzzy-Query Command Flow

```
Input Pattern
        ↓
Pattern Parser
        ↓
Sequential Pattern Expansion (wildcards)
        ↓
Sequential Candidate Generation
        ↓
Sequential Matching against Database
        ↓
Result Filtering (by mismatches)
        ↓
Output Matches
```

**Key Points**:
- Pattern expansion is sequential
- Each candidate is checked independently
- Results sorted by match quality (optional)

## Storage Models

### In-Memory Storage

**K-mer Counter**:
```rust
HashMap<u128, u32>
```
- Key: Encoded k-mer (u128)
- Value: Count (u32)
- Access: O(1) average for increments
- Memory: ~16 bytes per unique k-mer

**Database Storage**:
```rust
Vec<(u128, u32)>  // Sorted by k-mer encoding
```
- Sorted for binary search
- Access: O(log n) for lookups
- Memory: ~16 bytes per k-mer + overhead

### File Storage (RKDB Format)

```
[Header: 64 bytes]
[Magic: 4 bytes] b"RKDB"
[Version: 2 bytes]
[K-mer size: 1 byte]
[Flags: 1 byte]
[Total k-mers: 8 bytes]
[Data offset: 8 bytes]
[Index offset: 8 bytes]
[Reserved: 32 bytes]

[Data Section]
[k-mer encoding: 16 bytes]
[Count: 4 bytes]
[Padding: 4 bytes]
... (repeated for all k-mers)

[Index Section] (optional)
[k-mer encoding: 16 bytes]
[Position: 8 bytes]
... (repeated for all k-mers)
```

**Sequential Access**:
- File reading is sequential (no random access needed)
- Memory mapping for large files (optional)
- Binary search within mmap region

## Validation Rules

### K-mer Validation

1. **Character Set**:
   - Allowed: A, C, G, T, N
   - Uppercase only (convert to uppercase)
   - Invalid characters rejected with error

2. **Length Constraints**:
   - Minimum: 1 base
   - Maximum: 64 bases (fits in u128)
   - All k-mers in a database must have same length

3. **Canonical Representation**:
   - If canonical mode: Store min(k-mer, reverse_complement(k-mer))
   - Else: Store k-mer as-is
   - Consistent across entire database

### Database Validation

1. **File Integrity**:
   - Magic number check
   - Version compatibility
   - Checksum validation (optional)

2. **Data Consistency**:
   - All k-mers have same length (matches header)
   - K-mers are sorted (if sorted flag set)
   - Counts are non-negative
   - No duplicate k-mers (if sorted)

3. **Size Constraints**:
   - Total k-mers matches actual data
   - Offsets point to valid sections
   - File size matches header

## Error Handling

### Sequential Processing Errors

**Sequence Processing**:
- Invalid FASTA/FASTQ format: Return error with line number
- Empty sequences: Skip with warning
- Invalid characters: Reject with error message

**K-mer Counting**:
- K-mer too long: Error (exceeds 64 bases)
- Memory exhaustion: Error with suggestion to use smaller k or streaming
- Hash collision: Handle gracefully (rare with u128)

**Database Operations**:
- File not found: Error with path
- Permission denied: Error with filename
- Corrupted database: Error with details
- Version mismatch: Error with version info

### Error Recovery

**Sequential Processing**:
- Continue on non-critical errors (skip invalid sequences)
- Log warnings for recoverable issues
- Fail fast on critical errors (corruption, permission)

**Best Practices**:
- Use Result<T, E> for all fallible operations
- Provide descriptive error messages
- Include context (file name, line number, etc.)
- Suggest recovery actions where possible

## Performance Characteristics

### Time Complexity

**Counting**:
- O(n) where n = total bases in input
- Each base processed exactly once
- K-mer extraction: O(1) per base (sliding window)

**Querying**:
- Single query: O(log m) where m = unique k-mers in database
- Batch of q queries: O(q log m)
- Sequential processing: No speedup from parallelization

**Fuzzy Query**:
- Pattern with w wildcards: O(4^w * m)
- Sequential matching: Each candidate checked independently
- Early termination possible (max mismatches)

### Space Complexity

**Counting**:
- O(u) where u = unique k-mers
- HashMap: ~16 bytes per unique k-mer
- Total memory: O(u * 16 bytes)

**Querying**:
- O(1) additional space (just loading database)
- Memory-mapped files don't count toward RSS
- Sequential access pattern is cache-friendly

## Migration Notes

### From Parallel to Sequential

**What Changed**:
- Replaced `par_iter()` with `iter()`
- Replaced `par_chunks()` with `chunks()`
- Removed `rayon` dependency from Cargo.toml

**What Stayed the Same**:
- All data structures unchanged
- All file formats unchanged
- All CLI interfaces unchanged
- All output formats unchanged

**Benefits**:
- Simpler code (no thread synchronization)
- Predictable memory usage
- Easier debugging
- Smaller binary size
- No race conditions

**Trade-offs**:
- Slower on multi-core systems for large datasets
- Cannot utilize available CPU cores
- May see 2-10x slowdown on large files
- But: Performance was already sequential (parallel was unused)

## Testing Data Models

### Unit Test Coverage

**K-mer Model**:
- Encoding/decoding round-trip
- Canonical representation calculation
- Invalid character rejection
- Length validation

**Counter Model**:
- Single sequence counting
- Multiple sequence aggregation
- Empty sequence handling
- Memory efficiency

**Database Model**:
- Header serialization/deserialization
- Data section I/O
- Binary search correctness
- Memory mapping (optional)

**Query Model**:
- Single k-mer lookup
- Batch query processing
- Result accuracy
- Ordering preservation

### Property-Based Testing

**K-mer Properties**:
- Encoding is injective (no collisions)
- Canonical is involutive (canonical(canonical(k)) = canonical(k))
- Length is preserved after encoding

**Counter Properties**:
- Count is monotonic (never decreases)
- Total k-mers = sum of all counts
- Merging is associative and commutative

**Database Properties**:
- Sorted order is preserved after serialization
- Binary search finds correct k-mers
- Memory-mapped data matches file content

## Conclusion

The data model remains stable after removing Rayon parallel processing. The sequential execution model actually simplifies the mental model and eliminates concerns about thread safety, race conditions, and non-deterministic ordering. All existing data structures, validation rules, and error handling patterns remain valid and applicable.
