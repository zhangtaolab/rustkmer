# Data Model: Complete Python Bindings for RustKmer

## Core Python Classes

### 1. KmerCounter

**Description**: Primary class for k-mer counting operations in FASTA/FASTQ files

**Attributes**:
```python
class KmerCounter:
    k: int                          # K-mer size (1-64)
    canonical: bool                 # Use canonical k-mers
    threads: int                    # Thread count (0 = auto)
    hash_size: int                  # Hash table size
    sort_output: bool               # Sort output by k-mer
    min_count: int                  # Minimum count filter
    max_count: Optional[int]        # Maximum count filter
    memory_limit: Optional[int]     # Memory limit in bytes
    verbose: bool                   # Verbose output
    quiet: bool                     # Quiet mode
```

**Methods**:
```python
def count_file(self, input_path: str, output_path: Optional[str] = None) -> Database
def count_files(self, input_paths: List[str], output_path: str) -> Database
def count_string(self, sequence: str) -> Dict[str, int]
def count_directory(self, path: str, recursive: bool = True) -> Database
def save_to_database(self, output_path: str, format: str = "binary") -> None
def get_database_stats(self) -> DatabaseStats
```

**Validation Rules**:
- k: must be between 1 and 64
- threads: must be non-negative integer
- min_count: must be positive if specified
- max_count: must be greater than min_count if both specified

### 2. Database

**Description**: Wrapper for RKDB database file operations and queries

**Attributes**:
```python
class Database:
    path: str                       # Database file path
    kmer_size: int                   # K-mer size from database
    total_kmers: int                 # Total k-mer count
    unique_kmers: int                # Unique k-mer count
    metadata: DatabaseMetadata       # Database header information
    _database_ptr: Optional[object]  # Internal Rust database pointer
```

**Methods**:
```python
def load(self, path: str, preload: bool = True) -> None
def query(self, kmer: str) -> int
def query_batch(self, kmers: List[str]) -> Dict[str, int]
def exists(self, kmer: str) -> bool
def get_kmers(self) -> Iterator[str]
def get_counts(self) -> Iterator[int]
def iter_kmers(self) -> Iterator[Tuple[str, int]]
def get_statistics(self, config: Optional[DatabaseStatsConfig] = None) -> DatabaseStats
def dump(self, output_path: str, format: str = "text", threshold: int = 0) -> None
def merge(self, other_databases: List[Database], output_path: str) -> Database
```

**Validation Rules**:
- kmer: must be valid DNA sequence (A, C, G, T only)
- length: must match database kmer_size
- format: must be one of ["text", "csv", "tsv", "json"]

### 3. FuzzyQuery

**Description**: Performs wildcard and mutation-tolerant k-mer searches

**Attributes**:
```python
class FuzzyQuery:
    database: Database              # Database to query
    max_mutations: int              # Maximum Hamming distance
    max_variants: int               # Maximum result variants
    parallel: bool                  # Enable parallel processing
    batch_size: int                 # Batch size for processing
    format: str                     # Output format
```

**Methods**:
```python
def query(self, pattern: str, max_results: Optional[int] = None) -> FuzzyQueryResult
def query_batch(self, patterns: List[str]) -> List[FuzzyQueryResult]
def set_max_distance(self, distance: int) -> None
def set_format(self, format: str) -> None
def enable_profiling(self) -> None
```

**Validation Rules**:
- pattern: must be valid DNA sequence with wildcards
- max_mutations: must be non-negative
- max_variants: must be positive
- format: must be one of ["table", "json", "tsv", "csv"]

### 4. DatabaseStats

**Description**: Contains database statistics and metadata

**Attributes**:
```python
class DatabaseStats:
    kmer_size: int                   # K-mer size
    total_kmers: int                 # Total k-mers counted
    unique_kmers: int                # Unique k-mer sequences
    coverage_estimate: float         # Genome coverage estimate
    histogram: Dict[int, int]        # Count frequency distribution
    percentiles: Dict[str, float]    # Statistical percentiles
    approximate_median: float        # Median estimate
    metadata: DatabaseMetadata       # Additional metadata
```

**Methods**:
```python
def calculate_histogram(self, max_bins: int = 1000) -> Dict[int, int]
def get_percentiles(self) -> Dict[str, float]
def get_coverage_estimate(self, genome_size: int) -> float
def export_frequency_distribution(self, output_path: str) -> None
```

### 5. QueryResult

**Description**: Single k-mer query result

**Attributes**:
```python
class QueryResult:
    kmer: str                       # K-mer sequence
    count: int                      # K-mer count
    exists: bool                    # Whether k-mer exists
    timestamp: Optional[datetime]   # Query timestamp
```

### 6. FuzzyQueryResult

**Description**: Fuzzy query result with match details

**Attributes**:
```python
class FuzzyQueryResult:
    query_pattern: str              # Original query pattern
    matches: List[FuzzyMatch]        # Matching k-mers
    total_matches: int              # Total number of matches
    max_distance_used: int          # Maximum distance applied
    query_time: float               # Query execution time
```

### 7. FuzzyMatch

**Description**: Individual fuzzy query match

**Attributes**:
```python
class FuzzyMatch:
    kmer: str                       # Matching k-mer
    count: int                      # K-mer count
    distance: int                   # Hamming distance from query
    mutations: List[Tuple[int, str]] # Mutation positions and types
```

### 8. DatabaseMetadata

**Description**: Database file header and metadata

**Attributes**:
```python
class DatabaseMetadata:
    version: str                    # Database format version
    created_at: datetime            # Creation timestamp
    kmer_size: int                  # K-mer size
    canonical: bool                 # Canonical encoding used
    total_sequences: int            # Number of input sequences
    total_bases: int                # Total bases processed
    algorithm: str                  # Counting algorithm used
    parameters: Dict[str, Any]      # Algorithm parameters
```

## Configuration Classes

### 1. DatabaseStatsConfig

**Description**: Configuration for statistics calculation

**Attributes**:
```python
class DatabaseStatsConfig:
    format: str = "text"            # Output format
    detailed: bool = False           # Include frequency distribution
    max_bins: int = 1000            # Maximum histogram bins
    approximate_median: bool = False # Use approximate median
    progress_bar: bool = False       # Show progress
    split_output: bool = False       # Split output files
    freq_output_file: Optional[str] = None # Frequency output file
```

### 2. MergeConfig

**Description**: Configuration for database merge operations

**Attributes**:
```python
class MergeConfig:
    output_file: str                 # Output database path
    threads: int = 0                # Thread count (0 = auto)
    temp_dir: str = "/tmp"           # Temporary directory
    keep_intermediate: bool = False # Keep temporary files
    verbose: bool = False            # Verbose output
    check_compatibility: bool = True  # Check compatibility first
```

### 3. ExportConfig

**Description**: Configuration for data export operations

**Attributes**:
```python
class ExportConfig:
    format: OutputFormat            # Export format
    compression: CompressionFormat = NONE # Compression type
    min_count: Optional[int] = None  # Minimum count filter
    max_count: Optional[int] = None  # Maximum count filter
    include_metadata: bool = True    # Include database metadata
    parallel: bool = True            # Enable parallel export
```

## Enums

### 1. OutputFormat

```python
class OutputFormat(Enum):
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    TSV = "tsv"
```

### 2. CompressionFormat

```python
class CompressionFormat(Enum):
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
```

## State Transitions

### Database Lifecycle

```
[Unloaded] --load()--> [Loaded]
[Loaded] --query()--> [Querying]
[Querying] --result--> [Loaded]
[Loaded] --close()--> [Closed]
[Closed] --load()--> [Loaded]
```

### KmerCounter Lifecycle

```
[Initialized] --count_file()--> [Counting]
[Counting] --progress_callback--> [Counting]
[Counting] --complete()--> [Completed]
[Completed] --save_to_database()--> [Database Created]
[Database Created] --new_count()--> [Initialized]
```

## Relationships

### Composition Relationships

- `Database` contains `DatabaseMetadata`
- `DatabaseStats` contains `DatabaseMetadata`
- `FuzzyQuery` requires `Database`
- `FuzzyQueryResult` contains multiple `FuzzyMatch` objects
- `KmerCounter` creates `Database` objects
- `Database` can be merged with other `Database` objects

### Dependency Relationships

- `FuzzyQuery` depends on `Database` being loaded
- `DatabaseStats` depends on `Database` metadata
- Query operations depend on valid k-mer sequences
- Export operations depend on database file permissions

## Data Volume Considerations

### Memory Constraints

- `Database` objects use memory mapping for large files
- Query results are streamed for large datasets
- Batch operations have configurable chunk sizes
- Progress callbacks enable monitoring of long operations

### Performance Considerations

- K-mer lookup: O(1) average case
- Fuzzy query: O(4^mutations) worst case
- Batch queries: O(n) where n is number of k-mers
- Merge operations: O(total_kmers) + O(intermediate_storage)

## Validation Rules

### K-mer Sequence Validation

```python
def validate_kmer_sequence(kmer: str, kmer_size: int) -> bool:
    """Validate k-mer sequence format and length"""
    if len(kmer) != kmer_size:
        return False
    if not all(base in 'ACGT' for base in kmer):
        return False
    return True
```

### Database Format Validation

```python
def validate_database_format(file_path: str) -> bool:
    """Validate RKDB database file format"""
    # Check file header
    # Validate version compatibility
    # Verify k-mer size consistency
    return True
```

### Configuration Validation

```python
def validate_merge_config(config: MergeConfig, databases: List[Database]) -> bool:
    """Validate merge configuration compatibility"""
    # Check all databases have same k-mer size
    # Verify compatible versions
    # Validate output path permissions
    return True
```