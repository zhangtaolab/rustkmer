# Data Model: RustKmer Python API Compatibility

**Generated**: 2025-12-02
**Purpose**: Define unified data structures for RKDB database format compatibility

## Core Entities

### 1. RKDB Database Header

**Source**: CLI specification in `/src/database/format.rs`

```rust
pub struct DatabaseHeader {
    pub magic: [u8; 4],           // "RKDB" magic number
    pub version: u16,              // Format version (1)
    pub kmer_size: u8,             // K-mer size (1-127)
    pub total_kmers: u64,          // Total unique k-mers
    pub flags: u8,                 // Bit flags (sorted=1, canonical=2)
    pub data_offset: u64,          // Offset to k-mer data (always 42)
    pub index_offset: u64,         // Offset to index (0 if none)
}
```

**Validation Rules**:
- Magic bytes must be exactly `b"RKDB"`
- Version must be 1 (current supported version)
- K-mer size must be between 1 and 127
- Data offset must be 42 bytes
- Total k-mers must be > 0 for valid databases

### 2. K-mer Entry

```rust
pub struct KmerEntry {
    pub kmer: u64,   // Packed 64-bit k-mer representation
    pub count: u32,  // 32-bit count with endianness detection
}
```

**Encoding Scheme**:
- DNA bases: A=00, C=01, G=10, T=11 (2 bits per base)
- Left-aligned 2-bit encoding in 64-bit integers
- Maximum k-mer size: 32 bases (fits in u64)

### 3. Database Flags

**Bit Flag Definitions**:
- Bit 0 (0x01): Sorted - k-mers stored in sorted order
- Bit 1 (0x02): Canonical - canonical k-mers only (forward/reverse complement min)

## Python API Data Structures

### 1. Unified Database Class

```python
@dataclass
class RKDatabase:
    file_path: str
    kmer_size: int
    total_kmers: int
    canonical: bool
    sorted: bool
    version: int
    created_at: Optional[datetime] = None
    file_size: Optional[int] = None
    # Memory mapping for large files
    _mmap: Optional[Any] = field(default=None, repr=False)
    _header: Optional[DatabaseHeader] = field(default=None, repr=False)
```

**Methods**:
- `__init__(file_path: str, use_mmap: bool = True)`
- `query(kmer: str) -> Optional[int]`
- `query_batch(kmers: List[str]) -> Dict[str, int]`
- `save(output_path: str) -> None`
- `get_stats() -> DatabaseStats`

### 2. K-mer Counter Class

```python
@dataclass
class KmerCounter:
    k: int
    canonical: bool = False
    threads: int = 1
    _kmer_counts: Dict[str, int] = field(default_factory=dict)
    _total_processed: int = 0
```

**Methods**:
- `count_file(file_path: str) -> Dict[str, int]`
- `count_sequence(sequence: str) -> Dict[str, int]`
- `save_to_database(file_path: str) -> None`
- `get_stats() -> CounterStats`

## Data Flow and State Transitions

### 1. Database Creation Flow

```
Input FASTA → K-mer Processing → Counter → Serialization → .rkdb File
    ↓              ↓               ↓         ↓            ↓
  Validation    Encoding      Counting   Header+Data  Verification
```

### 2. Database Query Flow

```
.rkdb File → Header Reading → Memory Mapping → Binary Search → Result
     ↓            ↓              ↓              ↓           ↓
  Validation   Metadata       Optimization   K-mer Lookup  Count
```

### 3. State Transitions

**Database States**:
- `UNLOADED`: File path known, header not read
- `LOADED`: Header read, structure validated
- `MAPPED`: Memory-mapped for efficient access
- `QUERYING`: Actively performing queries
- `CLOSED`: Resources released

## Validation Rules

### 1. Input Validation

**FASTA/FASTQ Files**:
- Must exist and be readable
- File size > 0
- Valid sequence characters (A,T,C,G,N for FASTA)
- Proper FASTA header format (`>sequence_id`)

**K-mer Parameters**:
- k-mer size: 1 ≤ k ≤ 31 (practical limit for 64-bit encoding)
- threads: 1 ≤ threads ≤ CPU cores
- canonical: boolean, affects k-mer counting method

### 2. Database Validation

**File Format Validation**:
- Magic bytes must be "RKDB"
- Version must be supported (currently 1)
- Header checksum validation
- Data offset must be 42
- File size must match expected size

**Content Validation**:
- Total k-mers must be ≥ 0
- K-mer size must be reasonable (1-31)
- All k-mer entries must be valid
- Counts must be positive integers

### 3. Query Validation

**K-mer Query Validation**:
- Length must match database k-mer size
- Characters must be valid DNA bases (A,T,C,G)
- Case insensitive (automatically converted to uppercase)

**Batch Query Validation**:
- List length > 0
- All k-mers must pass individual validation
- Memory usage estimation for large batches

## Error Handling

### 1. Database Serialization Errors

```python
class DatabaseError(Exception):
    """Base class for database-related errors"""
    pass

class InvalidFormatError(DatabaseError):
    """Database format is invalid or corrupted"""
    pass

class VersionMismatchError(DatabaseError):
    """Database version is not supported"""
    pass

class CorruptionError(DatabaseError):
    """Database file is corrupted"""
    pass
```

### 2. I/O Errors

```python
class FileIOError(DatabaseError):
    """File input/output operations failed"""
    pass

class PermissionError(DatabaseError):
    """Insufficient permissions for file operations"""
    pass

class DiskSpaceError(DatabaseError):
    """Insufficient disk space for database creation"""
    pass
```

### 3. Validation Errors

```python
class ValidationError(DatabaseError):
    """Input validation failed"""
    pass

class InvalidKmerError(ValidationError):
    """K-mer sequence is invalid"""
    pass

class InvalidParameterError(ValidationError):
    """Parameter value is out of valid range"""
    pass
```

## Performance Considerations

### 1. Memory Management

**Memory Mapping Threshold**:
- Files < 10MB: Load entirely into memory
- Files 10MB-100MB: Optional memory mapping
- Files > 100MB: Always use memory mapping

**Cache Strategy**:
- LRU cache for frequently accessed k-mers
- Header metadata always cached
- Query results cached for repeated queries

### 2. Batch Processing

**Optimal Batch Sizes**:
- Small batches: 100-1,000 k-mers (for rapid response)
- Medium batches: 1,000-10,000 k-mers (balanced performance)
- Large batches: 10,000-100,000 k-mers (maximum throughput)

**Parallel Processing**:
- Use Rayon for CPU-bound operations
- Thread-safe shared data structures
- GIL release for computationally intensive tasks

### 3. I/O Optimization

**File Operations**:
- Buffered I/O for all file reads/writes
- Sequential access patterns for database files
- Asynchronous I/O for large file operations

**Compression**:
- Optional LZ4 compression for large databases
- Transparent compression/decompression
- Performance vs. size trade-off configuration

## Integration Points

### 1. CLI Compatibility

**File Format**:
- Identical binary format to CLI databases
- Same header structure and byte ordering
- Compatible with all CLI tools

**Parameter Mapping**:
- Python parameters map directly to CLI equivalents
- Default values match CLI defaults
- Error messages consistent with CLI format

### 2. Python Ecosystem

**Scientific Computing**:
- NumPy integration for array operations
- Pandas DataFrame compatibility for bulk operations
- Matplotlib support for visualization

**Bioinformatics Tools**:
- Biopython sequence object compatibility
- FASTA/FASTQ parsing integration
- Common bioinformatics workflow support

This data model provides the foundation for implementing unified RKDB database format compatibility while maintaining Python-idiomatic interfaces and optimal performance characteristics.