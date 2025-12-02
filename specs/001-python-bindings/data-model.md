# Data Model: Python Bindings for RustKmer

**Date**: 2025-12-01
**Feature**: Python Bindings for RustKmer
**Phase**: Phase 1 - Design & Contracts

## Entity Overview

This document defines the core entities and their relationships for the Python bindings interface, derived from the functional requirements and existing RustKmer architecture.

## Core Entities

### 1. KmerCounter

**Purpose**: Main class for counting k-mers from sequences and files (FR-001, FR-002)

**Fields**:
```python
class KmerCounter:
    kmer_length: int           # Size of k-mers (1-127)
    canonical_mode: bool       # Whether to count canonical k-mers
    total_kmers: int          # Total unique k-mers counted
    total_count: int          # Total k-mer occurrences

    # Internal fields (read-only)
    _internal_counter: object  # Rust KmerCounter instance
    _thread_count: int        # Number of threads used
```

**Validation Rules**:
- `kmer_length` must be between 1 and 127 (from RustKmer constraints)
- `canonical_mode` is boolean and affects counting behavior
- Thread count must be between 1 and available CPU cores

**State Transitions**:
1. **Created** → **Counting**: When `count_sequence()` or `count_file()` called
2. **Counting** → **Complete**: When counting operation finishes
3. **Complete** → **Merged**: When `merge_counters()` called with another counter

**Methods**:
```python
def __init__(kmer_length: int, canonical_mode: bool = False,
             thread_count: int = None) -> None
def count_sequence(sequence: str) -> Dict[str, int]
def count_file(file_path: str, file_format: str = "auto") -> Dict[str, int]
def get_kmer_count(kmer: str) -> int
def get_all_counts() -> Dict[str, int]
def get_top_kmers(n: int) -> List[Tuple[str, int]]
def filter_by_count(min_count: int, max_count: int = None) -> Dict[str, int]
def merge(other_counter: 'KmerCounter') -> None
def get_stats() -> CounterStats
```

### 2. Database

**Purpose**: Object representing k-mer database with query capabilities (FR-003)

**Fields**:
```python
class Database:
    file_path: str           # Path to database file
    kmer_size: int          # K-mer size used in database
    total_kmers: int        # Number of k-mers in database
    is_canonical: bool      # Whether database uses canonical k-mers
    is_sorted: bool         # Whether database is sorted for binary search

    # Internal fields (read-only)
    _database: object       # Rust RKDatabase instance
    _memory_mapped: bool    # Whether database is memory-mapped
```

**Validation Rules**:
- `file_path` must exist and be a valid RKDB file
- `kmer_size` must match database metadata
- File format must be compatible RKDB version

**State Transitions**:
1. **Closed** → **Loading**: When `load()` called
2. **Loading** → **Open**: When database successfully loaded
3. **Open** → **Querying**: When query operations executed
4. **Open** → **Closed**: When `close()` called or object destroyed

**Methods**:
```python
def __init__(file_path: str, preload: bool = False) -> None
def load() -> None
def close() -> None
def query(kmer: str) -> int
def query_multiple(kmers: List[str]) -> Dict[str, int]
def get_kmer_size() -> int
def get_stats() -> DatabaseStats
```

### 3. QueryResult

**Purpose**: Object containing k-mer query results with metadata (FR-003)

**Fields**:
```python
class QueryResult:
    kmer: str               # The queried k-mer
    count: int              # K-mer count (0 if not found)
    found: bool             # Whether k-mer was found in database
    query_time: float       # Time taken for query in seconds

    # Optional for batch queries
    batch_kmers: List[str] = None    # All k-mers in batch query
    batch_counts: Dict[str, int] = None  # Results for batch query
    batch_time: float = 0.0          # Time for entire batch
```

**Validation Rules**:
- `count` must be non-negative integer
- `query_time` must be non-negative float
- If `batch_kmers` is present, `batch_counts` must contain all entries

**Relationships**:
- Created by `Database.query()` and `Database.query_multiple()`
- References the `Database` that generated it

### 4. FuzzyQuery

**Purpose**: Object for wildcard and mutation-tolerant queries (FR-004, FR-007)

**Fields**:
```python
class FuzzyQuery:
    query_string: str       # Query pattern with wildcards
    kmer_size: int          # Target k-mer size
    mutation_tolerance: int # Number of allowed mutations (0-3)
    max_variants: int       # Maximum variants to generate (default: 10000)

    # Internal fields (computed)
    _wildcard_count: int    # Number of wildcards in query
    _variant_count: int     # Number of variants that will be generated
    _is_valid: bool         # Whether query is valid
```

**Validation Rules**:
- `query_string` must contain only A, T, G, C, N characters
- `kmer_size` must be between 1 and 127
- `mutation_tolerance` must be between 0 and 3 (practical limit)
- `max_variants` must be reasonable (default 10000, warn if >1M)

**State Transitions**:
1. **Created** → **Validated**: When `validate()` called
2. **Validated** → **Expanded**: When variant expansion performed
3. **Expanded** → **Executed**: When query executed against database

**Methods**:
```python
def __init__(query_string: str, kmer_size: int,
             mutation_tolerance: int = 0, max_variants: int = 10000) -> None
def validate() -> bool
def get_variant_count() -> int
def expand_wildcards() -> List[str]
def generate_mutations(target_kmer: str) -> List[str]
```

### 5. FuzzyQueryResult

**Purpose**: Results from fuzzy query operations with match details

**Fields**:
```python
class FuzzyQueryResult:
    original_query: str           # Original query with wildcards
    matched_kmers: List[str]      # K-mers that matched
    counts: Dict[str, int]        # Counts for each matched k-mer
    match_type: str              # Type of match: "exact", "wildcard", "mutation"
    total_matches: int           # Total number of matches found
    query_time: float            # Time for fuzzy query execution
    variant_count: int           # Number of variants generated

    # For mutation tolerance queries
    mutations_applied: Dict[str, List[str]] = None  # Mutations applied
```

**Validation Rules**:
- `matched_kmers` and `counts` must have same keys
- `match_type` must be one of: "exact", "wildcard", "mutation"
- `variant_count` must be >= `total_matches`

### 6. Sequence

**Purpose**: Entity representing DNA/RNA sequences with validation (FR-001, FR-009)

**Fields**:
```python
class Sequence:
    sequence: str           # The DNA/RNA sequence
    length: int            # Length of sequence
    is_valid: bool         # Whether sequence contains only valid characters
    character_counts: Dict[str, int]  # Count of each character

    # Optional metadata
    description: str = None     # Sequence description (from FASTA header)
    source_file: str = None     # Source file if from file
    quality_scores: List[int] = None  # Quality scores for FASTQ
```

**Validation Rules**:
- `sequence` must contain only A, T, G, C, N, U characters
- `length` must be non-negative integer
- If `quality_scores` present, must match `sequence` length

**Methods**:
```python
def __init__(sequence: str, description: str = None,
             quality_scores: List[int] = None) -> None
def validate() -> bool
def get_kmers(k: int) -> List[str]
def reverse_complement() -> 'Sequence'
def filter_by_quality(min_quality: int) -> 'Sequence'
```

## Supporting Types

### 7. CounterStats

**Purpose**: Statistics for k-mer counting operations

**Fields**:
```python
@dataclass
class CounterStats:
    total_kmers: int         # Total unique k-mers
    total_count: int         # Total k-mer occurrences
    average_count: float     # Average k-mer count
    median_count: float      # Median k-mer count
    max_count: int          # Maximum k-mer count
    processing_time: float  # Time taken for counting operation
    memory_usage: int       # Memory used in bytes
```

### 8. DatabaseStats

**Purpose**: Statistics for database operations

**Fields**:
```python
@dataclass
class DatabaseStats:
    file_size: int           # Database file size in bytes
    kmer_count: int         # Number of k-mers in database
    kmer_size: int          # K-mer size
    is_canonical: bool      # Whether canonical k-mers used
    is_sorted: bool         # Whether database is sorted
    load_time: float        # Time to load database
    memory_usage: int       # Memory usage if loaded
```

## Entity Relationships

### Primary Relationships

```
KmerCounter ── creates ──> Dict[str, int] (k-mer counts)
     │                         │
     └─── merges ──> KmerCounter │
                                │
Database ── queries ──> QueryResult │
     │                         │
     └─── fuzzy_queries ──> FuzzyQueryResult
                                │
Sequence ── provides ──> KmerCounter
     │
     └─── contains ──> List[str] (k-mers)

FuzzyQuery ── operates on ──> Database
     │
     └─── generates ──> List[str] (variants)
```

### Data Flow Patterns

1. **Counting Workflow**:
   ```
   Sequence/File → KmerCounter → Dict[str, int] → analysis
                                    ↓
                              CounterStats → validation
   ```

2. **Query Workflow**:
   ```
   Database + kmer → QueryResult → count + metadata
   ```

3. **Fuzzy Query Workflow**:
   ```
   FuzzyQuery → variant expansion → Database queries → FuzzyQueryResult
   ```

## Validation Constraints

### Cross-Entity Constraints

1. **K-mer Size Consistency**: All entities in a workflow must use compatible k-mer sizes
2. **Canonical Mode Consistency**: Mixing canonical and non-canonical data requires explicit conversion
3. **File Format Compatibility**: Database format must match creation parameters
4. **Memory Limits**: Total memory usage must not exceed system constraints

### Error Handling Patterns

- **Validation Errors**: Raise ValueError with descriptive message
- **File Errors**: Raise FileNotFoundError or IOError as appropriate
- **Compatibility Errors**: Raise RuntimeError with mismatch details
- **Resource Errors**: Raise MemoryError for memory limit violations

## Performance Considerations

### Memory Management

1. **Large Databases**: Use memory-mapped access for databases >100MB
2. **Batch Operations**: Prefer batch queries over individual queries
3. **Streaming**: Use streaming for large sequence files
4. **Pre-allocation**: Pre-allocate results for known-size operations

### Optimization Hints

1. **Database Preloading**: Preload frequently accessed databases
2. **Parallel Processing**: Use available CPU cores for counting operations
3. **Caching**: Cache query results when appropriate
4. **Lazy Loading**: Load data only when needed

## Evolution Considerations

### Extensibility

1. **New Database Formats**: Database interface supports multiple backends
2. **Additional Query Types**: FuzzyQuery interface allows extension
3. **New File Formats**: Sequence class supports multiple format handlers
4. **Advanced Statistics**: Stats classes can be extended with additional metrics

### Backward Compatibility

1. **Database Format**: Maintain compatibility with existing .rkdb files
2. **API Stability**: Use semantic versioning for API changes
3. **Configuration**: Support legacy configuration options
4. **Migration Paths**: Provide utilities for format migration

## Implementation Notes

### Python-Specific Considerations

1. **Type Hints**: All entities use Python type hints for IDE support
2. **Data Classes**: Use `@dataclass` for simple data containers
3. **Context Managers**: Implement `__enter__`/`__exit__` for resource management
4. **Iterators**: Implement iterator protocol for large result sets

### Rust Integration Points

1. **Zero-Copy Operations**: Use PyBytes/PySlice for efficient data transfer
2. **Error Mapping**: Map Rust errors to appropriate Python exceptions
3. **Thread Safety**: Ensure GIL release for long-running operations
4. **Memory Management**: Proper cleanup of Rust resources

This data model provides a comprehensive foundation for implementing Python bindings that are both Pythonic and maintain the performance characteristics of the underlying Rust implementation.