# rustkmer/types.py Usage Guide

This document explains the unified type definitions in `rustkmer/types.py`.

## Overview

The `types.py` module provides a centralized location for all type definitions used across the rustkmer Python API. It includes:

1. **QueryResult** - Unified query result type with `found` field
2. **DatabaseStats** - Unified database statistics with additional fields
3. **FuzzyMatch** - Simplified fuzzy match result type
4. **FuzzyResult** - Simplified fuzzy query result type
5. **CounterStats** - Statistics for k-mer counter operations
6. **LoadMode** - Database loading mode enumeration
7. **Exception Hierarchy** - All exceptions for convenience

## Usage

### Import from types module (Recommended)

For the most complete type definitions, import directly from `types` module:

```python
from rustkmer.types import QueryResult, DatabaseStats, FuzzyMatch, FuzzyResult, CounterStats, LoadMode, RustKmerError

# QueryResult with 'found' field
result = QueryResult("ATCG", 10, canonical="ATCG", found=True)
print(f"K-mer {result.kmer}: count={result.count}, found={result.found}")

# DatabaseStats with additional fields
stats = DatabaseStats(21, 1000000, 500000, 2097152, is_sorted=True, is_canonical=True)
print(f"Database: k={stats.kmer_size}, sorted={stats.is_sorted}")

# FuzzyMatch
match = FuzzyMatch("ATCG", 10, distance=0, match_type="exact")
print(f"Match: {match.kmer} (distance={match.distance})")

# FuzzyResult
fuzzy_result = FuzzyResult("ATCG", exact_match=match, matches=[match], total_matches=1)
print(f"Total matches: {fuzzy_result.total_matches}")

# CounterStats
counter_stats = CounterStats(500000, 1000000, 21, is_canonical=True)
print(f"Counter: unique={counter_stats.unique_kmers}")

# LoadMode
mode = LoadMode.PRELOAD
print(f"Load mode: {mode}")
```

### Import from rustkmer (Backward Compatible)

For backward compatibility, you can also import from the main `rustkmer` package:

```python
from rustkmer import QueryResult, DatabaseStats, FuzzyMatchResult, FuzzyQueryResult, LoadMode, RustKmerError
```

Note: This imports the existing types from their respective modules (query.py, stats.py, fuzzy_query.py).

## Type Details

### QueryResult

```python
@dataclass
class QueryResult:
    kmer: str
    count: int
    canonical: Optional[str] = None
    found: bool = False
```

**Additional field:** `found` - Whether the k-mer was found (not in original query.py)

**Methods:**
- `is_present` - Returns True if count > 0
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string
- `from_dict()` - Create from dictionary

### DatabaseStats

```python
@dataclass
class DatabaseStats:
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    file_size: int
    is_sorted: bool = False
    is_canonical: bool = False
```

**Additional fields:** `is_sorted`, `is_canonical`, `total_kmers` (not all in original stats.py)

**Methods:**
- `average_count` - Calculate average k-mer count
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string
- `from_dict()` - Create from dictionary

### FuzzyMatch

```python
@dataclass
class FuzzyMatch:
    kmer: str
    count: int
    distance: Optional[int] = None
    match_type: str = "exact"
```

**New simplified type** (not in fuzzy_query.py)

**Methods:**
- `is_exact_match` - Returns True if distance is 0
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string
- `from_dict()` - Create from dictionary

### FuzzyResult

```python
@dataclass
class FuzzyResult:
    query: str
    exact_match: Optional[FuzzyMatch] = None
    matches: List[FuzzyMatch] = field(default_factory=list)
    total_matches: int = 0
    mutation_tolerance: int = 0
    has_position_mutations: bool = False
```

**New simplified type** for easier use (not full FuzzyQueryResult)

**Methods:**
- `has_exact_match` - Check if exact match exists
- `fuzzy_matches` - Get non-exact matches
- `match_count` - Calculate total count of all matches
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string
- `from_dict()` - Create from dictionary

### CounterStats

```python
@dataclass
class CounterStats:
    unique_kmers: int
    total_kmers: int
    kmer_size: int
    is_canonical: bool = False
```

**New type** for counting operations

**Methods:**
- `average_count` - Calculate average k-mer count
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string
- `from_dict()` - Create from dictionary

### LoadMode

```python
class LoadMode(Enum):
    PRELOAD = "preload"
    MEMORY_MAPPED = "mmap"
    LAZY = "lazy"
```

**Methods:**
- `from_string(value)` - Create LoadMode from string value

### Exception Hierarchy

All exceptions are imported for convenience:

```python
from rustkmer.types import (
    RustKmerError,        # Base exception
    DatabaseError,        # Database-related errors
    QueryError,           # Query-related errors
    InvalidKmerError,     # Invalid k-mer (inherits QueryError, ValueError)
    ConfigurationError,     # Configuration issues
    # ... and more specific exceptions
)
```

## Compatibility Notes

### Backward Compatibility

The types in `types.py` are designed to work alongside existing types:
- `QueryResult` from `types.py` has additional `found` field
- `DatabaseStats` from `types.py` has additional `is_sorted`, `is_canonical`, `total_kmers` fields
- `FuzzyMatch` and `FuzzyResult` are simplified versions for ease of use
- Full `FuzzyMatchResult`, `FuzzyQueryResult` remain available from `fuzzy_query` module

### Choosing Which to Use

**Use `rustkmer.types import` when:**
- You want the complete type definitions with all fields
- You need simplified `FuzzyMatch` and `FuzzyResult` types
- You're working with new code

**Use `rustkmer import` when:**
- You need backward compatibility with existing code
- You want to use the full `FuzzyMatchResult` class from `fuzzy_query`

## Examples

### Creating and Using QueryResult

```python
from rustkmer.types import QueryResult

# Create from values
result = QueryResult("ATCGATCG", 42, "ATCGATCG", True)
print(result)  # Output: ATCGATCG: 42

# Check if found
if result.is_present:
    print("K-mer found in database!")

# Serialize to JSON
json_str = result.to_json()
# Deserialize from JSON
restored = QueryResult.from_dict(eval(json_str))
```

### Creating and Using DatabaseStats

```python
from rustkmer.types import DatabaseStats

stats = DatabaseStats(
    kmer_size=21,
    total_kmers=1000000,
    unique_kmers=500000,
    file_size=2097152,
    is_sorted=True,
    is_canonical=True
)

print(f"Average count: {stats.average_count:.2f}")

# Serialize
json_data = stats.to_dict()
# Deserialize
restored = DatabaseStats.from_dict(json_data)
```

### Working with Fuzzy Queries

```python
from rustkmer.types import FuzzyMatch, FuzzyResult

# Create match
match = FuzzyMatch("ATCG", 10, distance=0, match_type="exact")

# Create fuzzy result
result = FuzzyResult(
    query="ATCG",
    exact_match=match,
    matches=[match],
    total_matches=1,
    mutation_tolerance=0
)

# Check properties
if result.has_exact_match:
    print("Exact match found!")

fuzzy_only = result.fuzzy_matches
print(f"Fuzzy matches: {len(fuzzy_only)}")
```

### Using LoadMode

```python
from rustkmer.types import LoadMode

# Create from enum
mode = LoadMode.PRELOAD
print(mode)  # Output: preload

# Create from string
mode = LoadMode.from_string("mmap")
print(mode)  # Output: MEMORY_MAPPED
```

### Handling Exceptions

```python
from rustkmer.types import RustKmerError, InvalidKmerError, DatabaseError

try:
    raise InvalidKmerError("ATXG")
except RustKmerError as e:
    print(f"Caught rustkmer error: {e}")

# Can catch more specific errors first
try:
    raise InvalidKmerError("ATXG")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e}")
except RustKmerError as e:
    print(f"Other rustkmer error: {e}")
```

## Testing

Run the verification script:

```bash
cd python
python3 -c "
from rustkmer.types import QueryResult, DatabaseStats, FuzzyMatch, FuzzyResult, CounterStats, LoadMode, RustKmerError
print('✅ All types imported successfully!')
"
```

## Benefits

1. **Unified API** - All types in one place, easier to remember and use
2. **Complete Type Hints** - All types have full type annotations
3. **Convenient Methods** - `to_dict()`, `to_json()`, `from_dict()` on all types
4. **Exception Convenience** - All exceptions available from one import
5. **Simplified Types** - `FuzzyMatch` and `FuzzyResult` are easier to use
6. **LoadMode Enum** - Type-safe database loading modes
