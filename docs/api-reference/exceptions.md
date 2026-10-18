<!-- generated-by: gsd-doc-writer -->
# Exceptions

This page documents error handling in the `pyrustkmer` Python bindings. The bindings do not define a custom exception hierarchy — methods raise standard Python built-in exceptions, and a single `RustKmerError` class is exported as a structured error payload type.

## Standard Exceptions

All errors raised by `pyrustkmer` methods are Python built-ins, mapped from Rust error conditions at the PyO3 boundary. Catch the built-in types:

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(f"Database not found: {e}")
except ValueError as e:
    print(f"Invalid database: {e}")
```

### Exception Types

#### `ValueError`

Raised for invalid input or invalid file content. This is the most common exception and covers:

- Invalid constructor arguments — e.g. `PyCounter` k-mer length outside 1–64, or `threads` < 1
- K-mer length mismatches — querying a k-mer whose length differs from the database's k-mer size
- Invalid characters — k-mer/prefix characters outside `A`, `T`, `C`, `G` (fuzzy patterns additionally allow `N`)
- Unreadable input files for `PyCounter.add_from_fasta` / `add_from_fastq`
- Invalid parameters for `PyDatabase.merge` — empty input list, unknown `merge_mode`, unparseable `max_memory`

```python
from pyrustkmer import PyCounter

try:
    counter = PyCounter(99)  # k-mer length must be 1-64
except ValueError as e:
    print(e)
# Output contains: Invalid k-mer size: 99. Must be between 1 and 64
```

#### `FileNotFoundError`

Raised when a required file does not exist:

- `PyDatabase(path, load_mode)` when `path` is missing
- `PyDatabase.merge(...)` when one of the input databases is missing

```python
try:
    db = PyDatabase("/nonexistent/path/database.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(f"Database not found: {e}")
```

#### `RuntimeError`

Raised when an operation fails after validation — engine-level failures rather than bad input:

- Prefix/hybrid/pattern query engine failures on `PyDatabase`
- Fuzzy query execution failures or database reload failures on `PyFuzzyQuery`
- Merge failures on `PyDatabase.merge` (including the over-budget `merge_mode="memory"` rejection)
- Mid-export write failures on the `export_to_*` methods

```python
from pyrustkmer import PyFuzzyQuery

try:
    result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)
except RuntimeError as e:
    print(f"Fuzzy query failed: {e}")
```

#### `PermissionError`

Raised by the export methods (`export_to_file`, `export_to_json`, `export_to_csv`) when the output file cannot be created or written:

```python
try:
    db.export_to_file("/root/forbidden/output.txt")
except PermissionError as e:
    print(f"Cannot write output: {e}")
```

### Exception Map by Operation

| Operation | Exceptions |
|-----------|------------|
| `PyDatabase(path, load_mode)` | `FileNotFoundError`, `ValueError` |
| `PyDatabase.query_exact` / `query_exact_batch` / `exists` | `ValueError` |
| `PyDatabase.query_prefix` / `query_prefix_batch` / `query_hybrid` | `ValueError`, `RuntimeError` |
| `PyDatabase.extract_by_prefix` / `extract_by_pattern` / `parse_pattern` | `ValueError`, `RuntimeError` |
| `PyDatabase.dump` / `export_all_kmers` | `ValueError` |
| `PyDatabase.export_to_file` / `export_to_json` / `export_to_csv` | `PermissionError`, `RuntimeError` |
| `PyDatabase.merge(...)` | `ValueError`, `FileNotFoundError`, `RuntimeError` |
| `PyCounter(...)` | `ValueError` |
| `PyCounter.add_kmer` / `add_sequence` | `ValueError` |
| `PyCounter.add_from_fasta` / `add_from_fastq` | `ValueError` |
| `PyCounter.save_database` | `ValueError` |
| `PyCounter.get_count` | `ValueError` |
| `PyFuzzyQuery(db)` | `ValueError` |
| `PyFuzzyQuery.query_fuzzy` / `query_fuzzy_position` | `ValueError`, `RuntimeError` |
| `PyPrefixQuery(path)` / `PyExtendedPrefixQuery(path)` | `ValueError` |

## RustKmerError

`RustKmerError` is the single error class exported by the `pyrustkmer` module. It is a structured error payload with two string fields — not a Python `Exception` subclass, and it is not raised by the current bindings. It can be constructed directly for use as a uniform error representation in downstream code:

```python
from pyrustkmer import RustKmerError

error = RustKmerError("k-mer length mismatch", "InvalidQuery")
print(error.message)   # "k-mer length mismatch"
print(error.error_type)  # "InvalidQuery"
print(str(error))      # "InvalidQuery: k-mer length mismatch"
print(repr(error))     # "RustKmerError('InvalidQuery', 'k-mer length mismatch')"
```

**Attributes:**
- `message` (str): Human-readable description of the error
- `error_type` (str): Category label for the error

**Constructor:**
```python
RustKmerError(message: str, error_type: str)
```

Because `RustKmerError` is not an `Exception` subclass, do not use it in `except` clauses — catch the built-in types listed above.

## Error Handling Best Practices

### 1. Catch the Built-in Types

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("database.rkdb", LoadMode.Preload)
except FileNotFoundError:
    print("Database not found. Check the file path.")
except ValueError as e:
    print(f"Invalid database format or argument: {e}")
```

### 2. Distinguish Input Errors from Engine Failures

`ValueError` almost always means the input was rejected (fix the arguments); `RuntimeError` means the operation itself failed (inspect the message, which carries the underlying Rust error text):

```python
def safe_query(db, kmer):
    try:
        return db.query_exact(kmer)
    except ValueError as e:
        # Wrong length or invalid characters - fix the input
        print(f"Invalid k-mer: {e}")
        return None
    except RuntimeError as e:
        # Engine failure - the message carries the Rust error
        print(f"Query failed: {e}")
        return None
```

### 3. Match Exception Type to Recovery Strategy

```python
from pyrustkmer import PyDatabase

def open_database(db_path):
    """Open a database, with targeted error handling."""
    try:
        return PyDatabase(db_path, LoadMode.Preload)
    except FileNotFoundError:
        # Missing file - no point retrying with the same path
        raise
    except ValueError as e:
        # Wrong format - try the lazy loader as a fallback
        print(f"Preload failed ({e}); check whether the file is a valid .rkdb")
        raise
```

## Migration Notes

Earlier documentation described a large custom exception hierarchy (`DatabaseNotFoundError`, `InvalidKmerError`, `FuzzyQueryError`, `QueryError`, etc.). **That hierarchy does not exist in the `pyrustkmer` module.** If you have code catching those names, migrate it to the built-in types:

```python
# Old (does not work - these names are not exported)
# except DatabaseNotFoundError as e: ...
# except InvalidKmerError as e: ...

# Current
except FileNotFoundError as e: ...   # was DatabaseNotFoundError
except ValueError as e: ...          # was InvalidKmerError / KmerLengthError
except RuntimeError as e: ...        # was QueryError / FuzzyQueryError
```

Migration mapping:

| Previously documented name | Catch instead | When |
|---------------------------|---------------|------|
| `DatabaseNotFoundError` | `FileNotFoundError` | Database file missing |
| `InvalidDatabaseError` / `DatabaseCorruptedError` | `ValueError` | File is not a valid `.rkdb` |
| `InvalidKmerError` / `KmerLengthError` | `ValueError` | Bad k-mer length or characters |
| `QueryError` | `RuntimeError` | Query engine failure |
| `FuzzyQueryError` / `InvalidPositionMutationError` | `ValueError` or `RuntimeError` | Invalid pattern/config is `ValueError`; execution failure is `RuntimeError` |
| `RustKmerError` (as catch-all) | `ValueError`, `FileNotFoundError`, `RuntimeError`, `PermissionError` | See the operation map above |
