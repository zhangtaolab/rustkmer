# Exception Hierarchy

This page documents the complete exception hierarchy used by the rustkmer Python API.

## Base Exception

### `RustKmerError`

Base exception for all rustkmer errors.

All rustkmer-specific exceptions inherit from this class, allowing users to catch all rustkmer errors with a single except clause while still enabling fine-grained error handling with specific exception types.

```python
try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except RustKmerError as e:
    print(f"rustkmer error occurred: {e}")
```

## Database Errors

Database errors inherit from `RustKmerError` and handle issues related to database file operations.

### `DatabaseError`

Base class for all database-related errors.

```python
try:
    db = PyDatabase("invalid.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except DatabaseError as e:
    print(f"Database error: {e}")
```

### `DatabaseNotFoundError`

Raised when a database file cannot be found at the specified path.

**Attributes:**
- `path`: The path that was attempted to be accessed

```python
try:
    db = PyDatabase("/nonexistent/path/database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except DatabaseNotFoundError as e:
    print(f"Database not found at: {e.path}")
    print(f"Error: {e}")
```

### `InvalidDatabaseError`

Raised when a file exists but is not a valid rustkmer database.

**Attributes:**
- `path`: The path to the invalid database file
- `reason`: Description of why the file is considered invalid

```python
try:
    db = PyDatabase("/path/to/wrong_format.txt", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except InvalidDatabaseError as e:
    print(f"Invalid database: {e.reason}")
    print(f"File path: {e.path}")
```

### `DatabaseCorruptedError`

Raised when a database file appears to be corrupted or unreadable.

**Attributes:**
- `path`: The path to the corrupted database file

```python
try:
    db = PyDatabase("/path/to/corrupted.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except DatabaseCorruptedError as e:
    print(f"Database corrupted: {e.path}")
    # Try to recover or use backup
```

## Query Errors

Query errors inherit from `RustKmerError` and handle issues related to database query operations.

### `QueryError`

Base class for all query-related errors.

```python
try:
    result = db.query_exact("INVALID")
except QueryError as e:
    print(f"Query failed: {e}")
```

### `InvalidKmerError`

Raised when an invalid k-mer sequence is provided.

**Attributes:**
- `kmer`: The invalid k-mer sequence
- `reason`: Description of why the k-mer is invalid

```python
try:
    result = db.query_exact("ATXG")  # Invalid character X
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e.kmer}")
    print(f"Reason: {e.reason}")
```

### `KmerLengthError`

Raised when k-mer length doesn't match database k-mer size.

**Attributes:**
- `expected_length`: The correct k-mer length for the database
- `actual_length`: The length of the provided k-mer

```python
try:
    result = db.query_exact("ATCG")  # Too short for k=31 database
except KmerLengthError as e:
    print(f"Expected length: {e.expected_length}")
    print(f"Actual length: {e.actual_length}")
    print(f"Invalid k-mer: {e.kmer}")
```

## Fuzzy Query Errors

Fuzzy query errors inherit from `QueryError` and handle issues specific to fuzzy query operations.

### `FuzzyQueryError`

Base exception for fuzzy query operations.

```python
try:
    result = fuzzy.query_fuzzy("ATCG", mutations=10)  # Too high
except FuzzyQueryError as e:
    print(f"Fuzzy query error: {e}")
```

### `InvalidMutationToleranceError`

Raised when mutation tolerance is out of valid range.

```python
try:
    result = fuzzy.query_fuzzy("ATCG", mutations=10)  # Too high
except InvalidMutationToleranceError as e:
    print("Mutation tolerance too high")
    print("Use a smaller value (0-5)")
```

### `InvalidPositionMutationError`

Raised when position-mutations parameter has invalid format or values.

**Attributes:**
- `position_config`: The invalid position mutation configuration string

```python
try:
    result = fuzzy.query_fuzzy("ATCG", position_mutations="invalid")
except InvalidPositionMutationError as e:
    print(f"Invalid format: {e.position_config}")
    print("Use format like '3,4:1' or '2-5:2'")
```

**Valid position-mutations formats:**
- `"3:1"` - Position 3 with max 1 mutation
- `"3,4,5:2"` - Positions 3,4,5 with max 2 mutations total
- `"4-7:1"` - Positions 4,5,6,7 with max 1 mutation
- `"3,4:1;6,7:2"` - Multiple independent groups

### `CombinatorialExplosionError`

Raised when fuzzy query would generate too many variants.

```python
try:
    result = fuzzy.query_fuzzy("ATCGATCGATCG", mutations=5)
except CombinatorialExplosionError as e:
    print("Too many variants would be generated")
    # Try reducing mutations or using max_variants parameter
    result = fuzzy.query_fuzzy("ATCGATCGATCG", mutations=3, max_variants=1000)
```

### `BatchQueryError`

Raised when batch fuzzy query encounters issues.

```python
try:
    results = db.fuzzy_query_batch(["ATCG", "GCTA", "INVALID"])
except BatchQueryError as e:
    print("Batch query failed")
    # Process queries individually to identify the problem
    for kmer in ["ATCG", "GCTA", "INVALID"]:
        try:
            result = fuzzy.query_fuzzy(kmer)
        except FuzzyQueryError as query_error:
            print(f"Query {kmer} failed: {query_error}")
```


### `ConfigurationError`

Raised when there's a configuration issue with the rustkmer package.

```python
try:
    db = PyDatabase("database.rkdb")
fuzzy = PyFuzzyQuery(db)  # May trigger config validation
except ConfigurationError as e:
    print(f"Configuration issue: {e}")
    print("Check rustkmer installation and environment")
```

## Error Handling Best Practices

### 1. Specific Error Handling

```python
# Handle specific errors appropriately
try:
    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
except DatabaseNotFoundError:
    print("Database not found. Check the file path.")
    sys.exit(1)
except InvalidDatabaseError:
    print("Invalid database format. The file may be corrupted.")
    sys.exit(1)
```

### 2. General Error Handling

```python
# Catch all rustkmer errors
try:
    result = fuzzy.query_fuzzy("ATCG", mutations=2)
except RustKmerError as e:
    print(f"rustkmer error: {e}")
    # Handle or log the error appropriately
```

### 3. Error Recovery Strategies

```python
def safe_query_with_retry(db, kmer, max_retries=3):
    """Query with retry logic for common errors."""
    for attempt in range(max_retries):
        try:
            return db.query_exact(kmer)
        except DatabaseNotFoundError:
            # File doesn't exist, no point retrying
            raise
        except QueryError as e:
            if attempt == max_retries - 1:
                raise
            print(f"Query attempt {attempt + 1} failed, retrying...")
            time.sleep(1)  # Wait before retry
    return None
```

## Migration Guide

### From Previous Versions

If you're upgrading from a version of rustkmer before 1.0:

1. **New Exception Hierarchy**: The exception hierarchy has been restructured for better organization.
2. **Additional Attributes**: Many exceptions now provide additional helpful attributes.
3. **Better Error Messages**: Error messages are more descriptive and actionable.

### Breaking Changes

- `DatabaseError` no longer inherits from `FileNotFoundError` directly
- `InvalidKmerError` no longer inherits from `ValueError` directly
- New position mutation related exceptions have been added

### Updated Imports

```python
# Old imports (pre-1.0)
from rustkmer.exceptions import DatabaseError, QueryError

# New imports (1.0+)
from rustkmer.exceptions import (
    DatabaseError, QueryError, InvalidKmerError,
    DatabaseNotFoundError, InvalidDatabaseError,
    FuzzyQueryError, InvalidMutationToleranceError,
    ConfigurationError
)
```