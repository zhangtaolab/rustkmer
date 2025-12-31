# Python API Contract: RustKmer

**Version**: 1.0
**Date**: 2025-01-09

## Module Structure

```python
rustkmer/
├── __init__.py          # Main module exports
├── core.py             # Core classes and enums
├── database.py         # Database operations
├── fuzzy.py            # Fuzzy query functionality
├── stats.py            # Statistics and analysis
├── utils.py            # Utility functions
└── exceptions.py       # Error definitions
```

## Core Classes

### 1. KmerCounter

```python
class KmerCounter:
    """High-performance k-mer counting for genomic sequences."""

    def __init__(
        self,
        k: int,
        canonical: bool = False,
        threads: int = 1,
        memory_limit: Optional[int] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> None:
        """
        Initialize k-mer counter.

        Args:
            k: K-mer length (1-31)
            canonical: Count canonical k-mers (both strands)
            threads: Number of threads for parallel processing
            memory_limit: Memory limit in MB
            progress_callback: Callback for progress updates

        Raises:
            KmerError: If k is not in valid range
            ConfigurationError: If threads or memory_limit invalid
        """

    def count_file(
        self,
        file_path: str,
        file_format: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Count k-mers from FASTA/FASTQ file.

        Args:
            file_path: Path to sequence file
            file_format: 'fasta', 'fastq', or auto-detect

        Returns:
            Dictionary mapping k-mers to counts

        Raises:
            FileNotFoundError: If file doesn't exist
            SequenceError: If file format invalid
            KmerError: If counting fails
        """

    def count_string(
        self,
        sequence: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, int]:
        """
        Count k-mers from sequence string.

        Args:
            sequence: DNA/RNA sequence
            progress_callback: Progress callback override

        Returns:
            Dictionary mapping k-mers to counts

        Raises:
            SequenceError: If sequence contains invalid characters
            KmerError: If counting fails
        """

    def save_to_database(
        self,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> 'Database':
        """
        Save counts to RKDB database.

        Args:
            output_path: Output database path
            progress_callback: Progress callback override

        Returns:
            Database object for saved data

        Raises:
            DatabaseError: If save fails
            KmerError: If counts invalid
        """

    def get_total_count(self) -> int:
        """Get total k-mer count including duplicates."""

    def get_unique_count(self) -> int:
        """Get number of unique k-mers."""

    def clear(self) -> None:
        """Clear all counted k-mers."""
```

### 2. Database

```python
class Database:
    """Access RKDB database files."""

    def __init__(self) -> None:
        """Create empty database object."""

    def load(
        self,
        file_path: str,
        force_mmap: Optional[bool] = None
    ) -> None:
        """
        Load database from file.

        Args:
            file_path: Path to RKDB file
            force_mmap: Force/disable memory mapping

        Raises:
            FileNotFoundError: If file doesn't exist
            DatabaseError: If format invalid or corrupted
        """

    def query(self, kmer: str) -> QueryResult:
        """
        Query k-mer count.

        Args:
            kmer: K-mer sequence

        Returns:
            QueryResult with count and metadata

        Raises:
            KmerError: If kmer invalid or wrong length
        """

    def batch_query(
        self,
        kmers: List[str],
        parallel: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[QueryResult]:
        """
        Query multiple k-mers.

        Args:
            kmers: List of k-mer sequences
            parallel: Use parallel processing
            progress_callback: Progress updates

        Returns:
            List of QueryResults

        Raises:
            KmerError: If any kmer invalid
        """

    def exists(self, kmer: str) -> bool:
        """Check if k-mer exists in database."""

    def get_stats(self) -> DatabaseStats:
        """Calculate database statistics."""

    def export(
        self,
        output_path: str,
        format: OutputFormat = OutputFormat.TSV,
        min_count: int = 1,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Export database to text format.

        Args:
            output_path: Output file path
            format: Export format
            min_count: Minimum count threshold
            progress_callback: Progress updates
        """

    @property
    def path(self) -> str:
        """Database file path."""

    @property
    def kmer_size(self) -> int:
        """K-mer length."""

    @property
    def total_kmers(self) -> int:
        """Total k-mer count."""

    @property
    def unique_kmers(self) -> int:
        """Unique k-mer count."""

    @property
    def canonical(self) -> bool:
        """Whether canonical k-mers stored."""

    def uses_memory_mapping(self) -> bool:
        """Check if using memory mapping."""

    def reload(self, force_mmap: Optional[bool] = None) -> None:
        """Reload database with different memory mapping setting."""
```

### 3. FuzzyQuery

```python
class FuzzyQuery:
    """Fuzzy k-mer search with wildcards and mutations."""

    def __init__(
        self,
        database: Database,
        max_distance: int = 1,
        wildcards: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize fuzzy query.

        Args:
            database: Database to search
            max_distance: Maximum edit distance
            wildcards: Wildcard character mappings

        Raises:
            FuzzyQueryError: If configuration invalid
        """

    def search(
        self,
        pattern: str,
        max_results: Optional[int] = None
    ) -> FuzzyQueryResult:
        """
        Search for k-mers matching pattern.

        Args:
            pattern: Search pattern with wildcards
            max_results: Maximum number of results

        Returns:
            FuzzyQueryResult with matches

        Raises:
            FuzzyQueryError: If pattern invalid
        """

    def batch_search(
        self,
        patterns: List[str],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[FuzzyQueryResult]:
        """
        Search multiple patterns.

        Args:
            patterns: List of search patterns
            progress_callback: Progress updates

        Returns:
            List of FuzzyQueryResults
        """

    def find_similar(
        self,
        kmer: str,
        max_distance: Optional[int] = None
    ) -> FuzzyQueryResult:
        """
        Find k-mers similar to given k-mer.

        Args:
            kmer: Reference k-mer
            max_distance: Override max_distance

        Returns:
            FuzzyQueryResult with similar k-mers
        """
```

## Result Classes

### QueryResult

```python
@dataclass
class QueryResult:
    kmer: str
    count: int
    found: bool
    distance: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""

    def to_json(self) -> str:
        """Convert to JSON string."""

    def to_tsv(self) -> str:
        """Convert to TSV string."""
```

### FuzzyQueryResult

```python
@dataclass
class FuzzyQueryResult:
    query: str
    matches: List[FuzzyMatch]
    total_matches: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""

    def to_json(self) -> str:
        """Convert to JSON string."""

    def get_top_matches(self, n: int) -> List[FuzzyMatch]:
        """Get top n matches by count."""
```

### FuzzyMatch

```python
@dataclass
class FuzzyMatch:
    kmer: str
    count: int
    distance: int
```

### DatabaseStats

```python
@dataclass
class DatabaseStats:
    total_kmers: int
    unique_kmers: int
    max_count: int
    min_count: int
    mean_count: float
    median_count: float
    histogram: Dict[int, int]
    coverage_estimate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""

    def get_percentile(self, p: float) -> int:
        """Get count at percentile p (0-100)."""

    def plot_histogram(
        self,
        bins: int = 50,
        log_scale: bool = True
    ) -> Figure:
        """Plot count histogram (requires matplotlib)."""
```

## Utility Functions

```python
def merge_databases(
    input_paths: List[str],
    output_path: str,
    strategy: MergeStrategy = MergeStrategy.SUM,
    progress_callback: Optional[Callable[[float], None]] = None
) -> Database:
    """
    Merge multiple RKDB databases.

    Args:
        input_paths: List of input database paths
        output_path: Output database path
        strategy: Merge strategy for overlapping k-mers
        progress_callback: Progress updates

    Returns:
        Database object for merged data

    Raises:
        DatabaseError: If merge fails
        ValueError: If databases incompatible
    """

def set_verbosity(level: int) -> None:
    """
    Set global verbosity level.

    Args:
        level: 0=quiet, 1=normal, 2=verbose, 3=debug
    """

def get_version() -> str:
    """Get RustKmer version string."""

def get_system_info() -> Dict[str, Any]:
    """Get system information (CPU, memory, etc.)."""

# Resource management
def get_resource_stats() -> Dict[str, Any]:
    """Get current resource usage statistics."""

def cleanup_resources() -> None:
    """Force cleanup of allocated resources."""

# Performance utilities
class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start
        print(f"{self.name}: {self.duration:.3f}s")
```

## Configuration

```python
class Config:
    """Global configuration settings."""

    # Memory settings
    MMAP_THRESHOLD: int = 100 * 1024 * 1024  # 100MB
    DEFAULT_MEMORY_LIMIT: int = 1024  # 1GB

    # Performance settings
    DEFAULT_THREAD_COUNT: int = os.cpu_count()
    BATCH_QUERY_SIZE: int = 1000

    # Progress reporting
    PROGRESS_UPDATE_INTERVAL: float = 0.1  # 10%

    # Error handling
    STRICT_VALIDATION: bool = True
    LOG_ERRORS: bool = True
```

## Exceptions

```python
class RustKmerError(Exception):
    """Base exception for all RustKmer errors."""
    pass

class DatabaseError(RustKmerError):
    """Database operation errors."""
    pass

class KmerError(RustKmerError):
    """K-mer operation errors."""
    pass

class FuzzyQueryError(RustKmerError):
    """Fuzzy query errors."""
    pass

class SequenceError(RustKmerError):
    """Sequence processing errors."""
    pass

class ConfigurationError(RustKmerError):
    """Configuration errors."""
    pass

class ValidationError(RustKmerError):
    """Validation errors."""
    pass
```

## Type Aliases

```python
from typing import (
    Dict, List, Optional, Callable, Any, Union, Tuple,
    Iterator, Generator
)

# Progress callback type
ProgressCallback = Callable[[float, str], None]

# Query result types
QueryResults = List[QueryResult]
FuzzyResults = List[FuzzyQueryResult]

# Count results
KmerCounts = Dict[str, int]

# Histogram data
Histogram = Dict[int, int]
```