# Python API Contract: RustKmer Python Bindings

**Version**: 1.0.0
**Date**: 2025-12-01
**Format**: Python API Specification

## Overview

This document defines the complete Python API contract for RustKmer Python bindings, covering all public classes, methods, and their signatures. The API is designed to be Pythonic while maintaining high performance through Rust backend.

## Core Module Structure

```python
# Main package structure
rustkmer/
├── __init__.py          # Public API exports
├── core.py              # Core classes (KmerCounter, Database)
├── fuzzy.py             # Fuzzy query functionality
├── sequence.py          # Sequence handling utilities
├── stats.py             # Statistics and result types
└── exceptions.py        # Custom exception classes
```

## Public API

### rustkmer.KmerCounter

**Purpose**: Main class for k-mer counting operations

#### Constructor

```python
def __init__(
    kmer_length: int,
    canonical_mode: bool = False,
    thread_count: int = None
) -> KmerCounter
```

**Parameters**:
- `kmer_length`: Size of k-mers (1-127)
- `canonical_mode`: Whether to count canonical k-mers (default: False)
- `thread_count`: Number of threads to use (default: CPU count)

**Raises**:
- `ValueError`: If kmer_length not in range 1-127
- `ValueError`: If thread_count < 1 or > CPU count

#### Methods

```python
def count_sequence(self, sequence: str) -> Dict[str, int]
```

Count k-mers in a DNA/RNA sequence.

**Parameters**:
- `sequence`: DNA/RNA sequence string

**Returns**:
- Dictionary mapping k-mers to their counts

**Raises**:
- `ValueError`: If sequence contains invalid characters
- `ValueError`: If sequence length < kmer_length

```python
def count_file(
    self,
    file_path: str,
    file_format: str = "auto"
) -> Dict[str, int]
```

Count k-mers in a FASTA/FASTQ file.

**Parameters**:
- `file_path`: Path to sequence file
- `file_format`: File format ("auto", "fasta", "fastq")

**Returns**:
- Dictionary mapping k-mers to their counts

**Raises**:
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If file format is invalid
- `SequenceError`: If sequence data is invalid

```python
def get_kmer_count(self, kmer: str) -> int
```

Get count for a specific k-mer.

**Parameters**:
- `kmer`: K-mer string to query

**Returns**:
- Count of the k-mer (0 if not found)

**Raises**:
- `ValueError`: If kmer length doesn't match counter

```python
def get_all_counts(self) -> Dict[str, int]
```

Get all k-mer counts.

**Returns**:
- Dictionary of all k-mers and their counts

```python
def get_top_kmers(self, n: int) -> List[Tuple[str, int]]
```

Get top N most frequent k-mers.

**Parameters**:
- `n`: Number of top k-mers to return

**Returns**:
- List of (kmer, count) tuples sorted by count descending

**Raises**:
- `ValueError`: If n < 1

```python
def filter_by_count(
    self,
    min_count: int,
    max_count: int = None
) -> Dict[str, int]
```

Filter k-mers by count range.

**Parameters**:
- `min_count`: Minimum count (inclusive)
- `max_count`: Maximum count (inclusive, optional)

**Returns**:
- Dictionary of k-mers within the specified count range

**Raises**:
- `ValueError`: If min_count < 0

```python
def merge(self, other_counter: 'KmerCounter') -> None
```

Merge another KmerCounter into this one.

**Parameters**:
- `other_counter`: Another KmerCounter to merge

**Raises**:
- `ValueError`: If kmer_length or canonical_mode don't match

```python
def get_stats(self) -> CounterStats
```

Get statistics for this counter.

**Returns**:
- CounterStats object with counting statistics

### rustkmer.Database

**Purpose**: Interface to RKDB k-mer databases

#### Constructor

```python
def __init__(self, file_path: str, preload: bool = False) -> Database
```

**Parameters**:
- `file_path`: Path to RKDB database file
- `preload`: Whether to preload database into memory

**Raises**:
- `FileNotFoundError`: If database file doesn't exist
- `DatabaseError`: If database file is invalid or corrupted

#### Context Manager

```python
def __enter__(self) -> Database
def __exit__(self, exc_type, exc_val, exc_tb) -> None
```

Support for `with` statement for automatic resource management.

#### Methods

```python
def load(self) -> None
```

Load database if not already loaded.

**Raises**:
- `DatabaseError`: If loading fails

```python
def close(self) -> None
```

Close database and release resources.

```python
def query(self, kmer: str) -> QueryResult
```

Query a single k-mer.

**Parameters**:
- `kmer`: K-mer to query

**Returns**:
- QueryResult object with count and metadata

**Raises**:
- `ValueError`: If kmer length doesn't match database
- `DatabaseError`: If query fails

```python
def query_multiple(self, kmers: List[str]) -> List[QueryResult]
```

Query multiple k-mers.

**Parameters**:
- `kmers`: List of k-mers to query

**Returns**:
- List of QueryResult objects

**Raises**:
- `ValueError`: If any kmer length doesn't match database

```python
def get_kmer_size(self) -> int
```

Get the k-mer size for this database.

**Returns**:
- K-mer size used in database

```python
def get_stats(self) -> DatabaseStats
```

Get database statistics.

**Returns**:
- DatabaseStats object with database information

### rustkmer.FuzzyQuery

**Purpose**: Fuzzy query with wildcards and mutation tolerance

#### Constructor

```python
def __init__(
    self,
    query_string: str,
    kmer_size: int,
    mutation_tolerance: int = 0,
    max_variants: int = 10000
) -> FuzzyQuery
```

**Parameters**:
- `query_string`: Query pattern (may contain N wildcards)
- `kmer_size`: Target k-mer size
- `mutation_tolerance`: Number of allowed mutations (0-3)
- `max_variants`: Maximum variants to generate

**Raises**:
- `ValueError`: If query_string contains invalid characters
- `ValueError`: If kmer_size not in range 1-127
- `ValueError`: If mutation_tolerance < 0 or > 3

#### Methods

```python
def validate(self) -> bool
```

Validate the fuzzy query.

**Returns**:
- True if query is valid, False otherwise

```python
def get_variant_count(self) -> int
```

Get the number of variants this query will generate.

**Returns**:
- Number of variants (may be 0 if invalid)

```python
def expand_wildcards(self) -> List[str]
```

Expand wildcards to generate all variants.

**Returns**:
- List of all variant sequences

**Raises**:
- `FuzzyQueryError`: If too many variants would be generated
- `FuzzyQueryError`: If query is invalid

```python
def generate_mutations(self, target_kmer: str) -> List[str]
```

Generate mutations of a target k-mer.

**Parameters**:
- `target_kmer: K-mer to generate mutations from

**Returns**:
- List of mutated sequences

**Raises**:
- `ValueError`: If target_kmer length doesn't match kmer_size

```python
def execute(self, database: Database) -> FuzzyQueryResult
```

Execute fuzzy query against a database.

**Parameters**:
- `database`: Database to query

**Returns**:
- FuzzyQueryResult with matches and metadata

**Raises**:
- `DatabaseError`: If query fails
- `FuzzyQueryError`: If query is invalid

### rustkmer.Sequence

**Purpose**: DNA/RNA sequence with validation

#### Constructor

```python
def __init__(
    self,
    sequence: str,
    description: str = None,
    quality_scores: List[int] = None
) -> Sequence
```

**Parameters**:
- `sequence`: DNA/RNA sequence
- `description`: Optional description (from FASTA header)
- `quality_scores`: Optional quality scores (from FASTQ)

**Raises**:
- `ValueError`: If sequence contains invalid characters
- `ValueError`: If quality_scores length doesn't match sequence

#### Methods

```python
def validate(self) -> bool
```

Validate the sequence.

**Returns**:
- True if valid, False otherwise

```python
def get_kmers(self, k: int) -> List[str]
```

Get all k-mers from this sequence.

**Parameters**:
- `k`: K-mer size

**Returns**:
- List of k-mers

**Raises**:
- `ValueError`: If k > sequence length

```python
def reverse_complement(self) -> 'Sequence'
```

Get reverse complement of this sequence.

**Returns**:
- New Sequence object with reverse complement

```python
def filter_by_quality(self, min_quality: int) -> 'Sequence'
```

Filter sequence by minimum quality score.

**Parameters**:
- `min_quality`: Minimum quality score

**Returns**:
- New Sequence object with filtered bases

**Raises**:
- `ValueError`: If no quality scores available

## Utility Functions

### rustkmer.count_kmers

```python
def count_kmers(
    sequence: str,
    k: int,
    canonical: bool = False
) -> Dict[str, int]
```

Convenience function for simple k-mer counting.

**Parameters**:
- `sequence`: DNA/RNA sequence
- `k`: K-mer size
- `canonical`: Whether to use canonical k-mers

**Returns**:
- Dictionary of k-mer counts

### rustkmer.create_database

```python
def create_database(
    output_path: str,
    k: int,
    input_files: List[str] = None,
    sequences: List[str] = None,
    canonical: bool = False,
    sorted: bool = True
) -> Database
```

Create a new k-mer database.

**Parameters**:
- `output_path`: Path for output database
- `k`: K-mer size
- `input_files`: List of input sequence files (optional)
- `sequences`: List of sequences (optional)
- `canonical`: Whether to use canonical k-mers
- `sorted`: Whether to sort database for faster queries

**Returns**:
- Database object for the created database

**Raises**:
- `ValueError`: If neither input_files nor sequences provided
- `FileNotFoundError`: If input files don't exist

## Result Types

### rustkmer.QueryResult

```python
@dataclass
class QueryResult:
    kmer: str
    count: int
    found: bool
    query_time: float
```

### rustkmer.FuzzyQueryResult

```python
@dataclass
class FuzzyQueryResult:
    original_query: str
    matched_kmers: List[str]
    counts: Dict[str, int]
    match_type: str
    total_matches: int
    query_time: float
    variant_count: int
    mutations_applied: Optional[Dict[str, List[str]]]
```

### rustkmer.CounterStats

```python
@dataclass
class CounterStats:
    total_kmers: int
    total_count: int
    average_count: float
    median_count: float
    max_count: int
    processing_time: float
    memory_usage: int
```

### rustkmer.DatabaseStats

```python
@dataclass
class DatabaseStats:
    file_size: int
    kmer_count: int
    kmer_size: int
    is_canonical: bool
    is_sorted: bool
    load_time: float
    memory_usage: int
```

## Exception Classes

### rustkmer.KmerError

```python
class KmerError(ValueError):
    """Base exception for k-mer related errors."""
    pass
```

### rustkmer.DatabaseError

```python
class DatabaseError(RuntimeError):
    """Exception for database-related errors."""
    pass
```

### rustkmer.FuzzyQueryError

```python
class FuzzyQueryError(ValueError):
    """Exception for fuzzy query related errors."""
    pass
```

### rustkmer.SequenceError

```python
class SequenceError(ValueError):
    """Exception for sequence-related errors."""
    pass
```

## Constants

### rustkmer.MAX_KMER_SIZE

```python
MAX_KMER_SIZE: int = 127  # Maximum supported k-mer size
```

### rustkmer.SUPPORTED_FORMATS

```python
SUPPORTED_FORMATS: List[str] = ["fasta", "fastq", "auto"]
```

## Type Aliases

```python
KmerCounts = Dict[str, int]
KmerList = List[str]
QualityScores = List[int]
```

## Performance Considerations

### Memory Usage

- Database objects use memory mapping for efficient access
- KmerCounter maintains in-memory hash table of k-mer counts
- Large sequence files are processed in streaming fashion

### Threading

- KmerCounter uses multiple threads for counting operations
- Database queries are single-threaded but very fast
- Thread count can be controlled via KmerCounter constructor

### Optimization Tips

1. Use `Database(preload=True)` for frequently accessed databases
2. Use batch queries (`query_multiple`) over individual queries
3. Set appropriate `max_variants` for fuzzy queries to avoid memory issues
4. Use canonical mode when reverse complement handling is needed

## Version Compatibility

- **Minimum Python Version**: 3.9
- **Recommended Python Version**: 3.11+
- **Database Format**: Compatible with existing RustKmer .rkdb files
- **File Formats**: FASTA and FASTQ with gzip compression support