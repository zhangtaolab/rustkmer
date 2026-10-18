<!-- generated-by: gsd-doc-writer -->
# Database

**Module**: `pyrustkmer` (crate `rustkmer-pyo3`, `database` module)

## Overview

PyDatabase — Python wrapper for RustKmer database operations.

This module provides a Python class that wraps the Rust `RKDatabase`
functionality for querying `.rkdb` k-mer databases, together with its
supporting result/stats types and the `LoadMode` enum:

- `PyDatabase` — load a `.rkdb` file in Preload, MemoryMapped, or Lazy mode
  and run exact, prefix, hybrid-pattern, and fuzzy queries, dumps, merges,
  and exports
- `LoadMode` — loading strategy (`Preload`, `MemoryMapped`, `Lazy`)
- `PyQueryResult` — single k-mer lookup result
- `PyPrefixQueryResult` — optimized prefix-query result with memory-block info
- `PyDatabaseStats` — database header statistics

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("output.rkdb", LoadMode.Preload)
result = db.query_exact("ATGCGATGCATGCGATGCAT")
print(result.count, result.found)
```

## API Reference

### Structs

#### LoadMode

```rust
#[pyclass(eq, eq_int)]
#[derive(Clone, PartialEq)]
pub enum LoadMode {
    #[pyo3(name = "Preload")] Preload,
    #[pyo3(name = "MemoryMapped")] MemoryMapped,
    #[pyo3(name = "Lazy")] Lazy,
}
```

Database loading modes: `Preload` loads all k-mers into memory (fastest
queries, higher memory usage); `MemoryMapped` keeps a direct file handle
(balanced memory/performance); `Lazy` builds a sorted index for binary
search (lowest memory, slower queries).

#### PyQueryResult

```rust
#[pyclass]
pub struct PyQueryResult {
    pub kmer: String,
    pub count: u32,
    pub found: bool,
}
```

Query result for k-mer lookups: the k-mer sequence, the count found in the
database, and whether the k-mer was found.

#### PyPrefixQueryResult

```rust
#[pyclass]
pub struct PyPrefixQueryResult {
    pub matches: HashMap<String, String>,
    pub start_index: usize,
    pub end_index: usize,
    pub block_size: usize,
    pub is_sorted: bool,
    pub total_matches: usize,
    pub query_time_ms: u64,
}
```

Result of an optimized prefix query: matching k-mers with their counts,
memory block information for performance analysis, total match count, and
query execution time in milliseconds.

#### PyDatabaseStats

```rust
#[pyclass]
pub struct PyDatabaseStats {
    pub kmer_size: usize,
    pub total_kmers: u64,
    pub unique_kmers: u64,
    pub file_size: u64,
    pub is_sorted: bool,
    pub canonical: bool,
}
```

Database statistics read from the database header.

#### PyDatabase

```rust
#[pyclass]
pub struct PyDatabase {
    pub path: String,
    pub header: DatabaseHeader,
    pub load_mode: LoadMode,
    pub rk_database: Option<RKDatabase>,
    pub kmer_cache: Option<BTreeMap<u128, u32>>,   // Preload mode
    pub mmapped_file: Option<std::fs::File>,       // MemoryMapped mode
    pub entries: Option<Vec<KmerEntry>>,           // Lazy mode
    pub cached_entries: Option<Vec<(u128, u32)>>,  // sorted binary-search index
    pub is_loaded: bool,
    // ... additional internal buffer fields
}
```

High-performance k-mer database for Python.

### Fns

#### PyDatabase::new

```rust
#[new]
fn new(path: &Bound<'_, PyString>, load_mode: LoadMode) -> PyResult<Self> {
```

Load a k-mer database from a file with the specified loading mode. Raises
`FileNotFoundError` if the path does not exist and `ValueError` if the
database cannot be loaded. Python constructor:
`PyDatabase(path, load_mode)`.

#### PyDatabase::query_exact

```rust
#[pyo3(signature = (kmer))]
fn query_exact(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
```

Exact k-mer lookup (unified-naming version). Validates that the k-mer
length matches the database k-mer size and that only `A`, `T`, `C`, `G`
are used; canonicalizes the query when the database stores canonical
k-mers. Raises `ValueError` on mismatch or when the database is not
loaded. Note: in `MemoryMapped` mode the current implementation is
simplified and returns a count of 0 — use `Preload` or `Lazy` for lookups.

#### PyDatabase::query_exact_batch

```rust
#[pyo3(signature = (kmers))]
fn query_exact_batch(&self, kmers: Vec<String>) -> PyResult<HashMap<String, PyQueryResult>> {
```

Batch exact k-mer queries; returns a dict mapping each input k-mer string
to its `PyQueryResult`.

#### PyDatabase::query_fuzzy

```rust
#[pyo3(signature = (pattern, max_mutations))]
fn query_fuzzy(&self, pattern: &Bound<'_, PyString>, max_mutations: u32) -> PyResult<PyFuzzyResult> {
```

Fuzzy query (unified-naming version). Validates pattern length and
characters (`A`, `T`, `C`, `G`, `N`). Note: the current implementation
returns a placeholder empty result; use `PyFuzzyQuery` for full fuzzy
matching.

#### PyDatabase::query_prefix

```rust
#[pyo3(signature = (prefix))]
fn query_prefix(&self, prefix: &Bound<'_, PyString>) -> PyResult<PyPrefixQueryResult> {
```

Optimized prefix query (unified-naming version) over the shared
`RKDatabase`. An empty prefix returns an empty result; only `A`, `T`, `C`,
`G` are allowed. Raises `RuntimeError` if the underlying extraction fails.

#### PyDatabase::query_prefix_batch

```rust
#[pyo3(signature = (prefixes))]
fn query_prefix_batch(&self, prefixes: Vec<String>) -> PyResult<Vec<PyPrefixQueryResult>> {
```

Run `query_prefix` for a list of prefixes.

#### PyDatabase::query_hybrid

```rust
#[pyo3(signature = (pattern))]
fn query_hybrid(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
```

Hybrid pattern query (e.g. `ATAC{N5}ACAC`) returning a dict of matching
k-mers to counts. Raises `ValueError` if not loaded, `RuntimeError` if the
query fails.

#### PyDatabase::query_hybrid_batch

```rust
#[pyo3(signature = (patterns))]
fn query_hybrid_batch(&self, patterns: Vec<String>) -> PyResult<Vec<HashMap<String, String>>> {
```

Run `query_hybrid` for a list of patterns.

#### PyDatabase::query

```rust
#[pyo3(signature = (kmer))]
fn query(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
```

Perform a single k-mer lookup. Deprecated since 2.0.0 — use
`query_exact()` instead.

#### PyDatabase::query_batch

```rust
#[pyo3(signature = (kmers))]
fn query_batch(&self, kmers: Vec<String>) -> PyResult<HashMap<String, PyQueryResult>> {
```

Perform batch k-mer queries. Deprecated since 2.0.0 — use
`query_exact_batch()` instead.

#### PyDatabase::fuzzy_query

```rust
#[pyo3(signature = (pattern, max_mutations))]
fn fuzzy_query(&self, pattern: &Bound<'_, PyString>, max_mutations: u32) -> PyResult<PyFuzzyResult> {
```

Fuzzy query. Deprecated since 2.0.0 — use `query_fuzzy()` instead.

#### PyDatabase::query_prefix_optimized

```rust
#[pyo3(signature = (prefix))]
fn query_prefix_optimized(&self, prefix: &Bound<'_, PyString>) -> PyResult<PyPrefixQueryResult> {
```

Optimized prefix query. Deprecated since 2.0.0 — use `query_prefix()`
instead.

#### PyDatabase::exists

```rust
fn exists(&self, kmer: &Bound<'_, PyString>) -> PyResult<bool> {
```

Check whether a k-mer exists in the database.

#### PyDatabase::get_stats

```rust
fn get_stats(&self) -> PyDatabaseStats {
```

Get database statistics from the header (`kmer_size`, `total_kmers`,
`unique_kmers`, `file_size`, `is_sorted`, `canonical`).

#### PyDatabase::get_memory_usage

```rust
fn get_memory_usage(&self) -> HashMap<String, String> {
```

Get memory usage information for the active loading mode (cache size for
Preload, file handle state for MemoryMapped, loaded/cached entry counts
for Lazy).

#### PyDatabase::database_info

```rust
fn database_info(&self) -> HashMap<String, String> {
```

Get database info: path, k-mer size, loaded flag, total/unique k-mers,
and load mode.

#### PyDatabase::dump

```rust
#[pyo3(signature = (limit=None, offset=0))]
fn dump(&self, limit: Option<usize>, offset: usize, py: Python<'_>) -> PyResult<Py<PyList>> {
```

Dump database contents with pagination support. Returns a list of
`PyQueryResult` objects; `limit=None` dumps all entries, `offset` skips
leading entries.

#### PyDatabase::get_all_kmers

```rust
fn get_all_kmers(&self) -> PyResult<Vec<HashMap<String, String>>> {
```

Get all k-mers and counts (Preload cache) as a list of
`{"kmer": <hex-encoded>, "count": ...}` dicts. The k-mer is rendered as a
hex string of its encoded `u128` form. Raises `ValueError` if not loaded.

#### PyDatabase::extract_by_prefix

```rust
#[pyo3(signature = (prefix))]
fn extract_by_prefix(&self, prefix: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
```

Prefix extraction (linear-search API): reloads the database from disk and
runs the optimized extraction, returning a dict of matching k-mers to
counts. Empty prefix returns an empty dict; only `A`, `T`, `C`, `G` are
allowed.

#### PyDatabase::extract_by_pattern

```rust
#[pyo3(signature = (pattern))]
fn extract_by_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
```

Extract k-mers by hybrid pattern (supports formats like `ATAC{N5}ACAC`)
using the shared `RKDatabase` instance.

#### PyDatabase::get_entry_by_index

```rust
fn get_entry_by_index(&self, index: usize) -> PyResult<(u128, u32)> {
```

Direct file access to the entry at `index` — only available in
`MemoryMapped` mode. Reads the 16-byte little-endian encoded k-mer and
4-byte count at the entry offset and returns them as `(u128, u32)`.

#### PyDatabase::parse_pattern

```rust
#[pyo3(signature = (pattern))]
fn parse_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
```

Parse a hybrid pattern and return its components (`prefix`, `suffix`,
`n_count`, `total_length`, `n_positions`).

#### PyDatabase::parse_pattern_string

```rust
fn parse_pattern_string(&self, pattern: &str) -> PyResult<HashMap<String, String>> {
```

String-input variant of `parse_pattern`.

#### PyDatabase::force_lazy_mode

```rust
fn force_lazy_mode(&mut self) -> PyResult<()> {
```

Force lazy loading mode (similar to the CLI's `--no-load` option).

#### PyDatabase::merge

```rust
#[staticmethod]
#[pyo3(signature = (databases, output, *, max_memory=None, merge_mode="auto".to_string()))]
fn merge(databases: Vec<String>, output: String, max_memory: Option<String>, merge_mode: String) -> PyResult<()> {
```

Merge multiple `.rkdb` files into one output file (static method, called
as `PyDatabase.merge(databases, output, ...)`). Keyword-only arguments:
`max_memory` accepts a size string parsed with the CLI's own parser
(e.g. `"4GB"`); `merge_mode` must be one of `auto`, `memory`,
`streaming`. The merge is memory-bounded and streams the output directly
to disk — the merged database is never materialized in RAM. Raises
`ValueError` for an empty list, an invalid mode, or an unparseable memory
budget; `FileNotFoundError` for missing inputs; `RuntimeError` if the
merge operation fails.

#### PyDatabase::export_to_file

```rust
#[pyo3(signature = (output_path, limit=None, offset=0, progress_callback=None))]
fn export_to_file(&self, output_path: String, limit: Option<usize>, offset: usize, progress_callback: Option<PyObject>) -> PyResult<u64> {
```

Export k-mers to a tab-separated text file (`kmer\tcount` per line),
streaming per loading mode. Optional pagination (`limit`, `offset`) and a
`progress_callback(current, total)`. Returns the number of k-mers
exported. Raises `PermissionError` if the output file cannot be created.

#### PyDatabase::export_to_json

```rust
#[pyo3(signature = (output_path, limit=None, offset=0, progress_callback=None))]
fn export_to_json(&self, output_path: String, limit: Option<usize>, offset: usize, progress_callback: Option<PyObject>) -> PyResult<u64> {
```

Export k-mers to a JSON file as an array of `{"kmer": ..., "count": ...}`
objects. Same pagination/callback/return semantics as `export_to_file`.

#### PyDatabase::export_to_csv

```rust
#[pyo3(signature = (output_path, limit=None, offset=0, progress_callback=None))]
fn export_to_csv(&self, output_path: String, limit: Option<usize>, offset: usize, progress_callback: Option<PyObject>) -> PyResult<u64> {
```

Export k-mers to a CSV file. Same pagination/callback/return semantics as
`export_to_file`.

#### PyDatabase::export_all_kmers

```rust
#[pyo3(signature = (limit=None, offset=0))]
fn export_all_kmers(&self, limit: Option<usize>, offset: usize, py: Python<'_>) -> PyResult<Py<PyList>> {
```

Return all (paginated) k-mers as an in-memory list of `PyQueryResult`
objects. Use with caution for large databases.

#### PyDatabase::test_method

```rust
fn test_method(&self) -> String {
```

Simple connectivity test; returns `"Test method works!"`.

#### PyDatabase properties

```rust
#[getter] fn kmer_size(&self) -> usize
#[getter] fn path(&self) -> &str
#[getter] fn load_mode(&self) -> LoadMode
#[getter] fn is_loaded(&self) -> bool
#[getter] fn total_kmers(&self) -> u64
#[getter] fn unique_kmers(&self) -> u64
#[getter] fn canonical(&self) -> bool
```

Header-derived properties: k-mer size, file path, active `LoadMode`,
loaded flag, total and unique k-mer counts, and whether the database
stores canonical k-mers.

#### PyQueryResult methods and properties

```rust
#[getter] fn kmer(&self) -> &str
#[getter] fn count(&self) -> u32
#[getter] fn found(&self) -> bool
fn __repr__(&self) -> String
fn to_json(&self) -> PyResult<String>
fn to_csv(&self) -> PyResult<String>
fn to_tsv(&self) -> PyResult<String>
fn to_dict(&self, py: Python<'_>) -> PyResult<pyo3::PyObject>
```

Serialization helpers (`to_json`/`to_csv`/`to_tsv`/`to_dict`) plus a
`PyQueryResult(kmer='...', count=..., found=...)` repr.

#### PyPrefixQueryResult methods and properties

```rust
#[getter] fn matches(&self) -> HashMap<String, String>
#[getter] fn total_matches(&self) -> usize
#[getter] fn query_time_ms(&self) -> u64
#[getter] fn start_index(&self) -> usize
#[getter] fn end_index(&self) -> usize
#[getter] fn block_size(&self) -> usize
#[getter] fn is_sorted(&self) -> bool
fn __repr__(&self) -> String
fn to_json(&self) -> PyResult<String>
fn to_csv(&self) -> PyResult<String>
fn to_tsv(&self) -> PyResult<String>
fn to_table(&self) -> PyResult<String>
```

Serialization helpers, including a formatted `to_table` rendering with
memory-block metadata.

#### PyDatabaseStats methods and properties

```rust
#[getter] fn kmer_size(&self) -> usize
#[getter] fn total_kmers(&self) -> u64
#[getter] fn unique_kmers(&self) -> u64
#[getter] fn file_size(&self) -> u64
#[getter] fn is_sorted(&self) -> bool
#[getter] fn canonical(&self) -> bool
fn __repr__(&self) -> String
fn to_json(&self) -> PyResult<String>
fn to_csv(&self) -> PyResult<String>
fn to_tsv(&self) -> PyResult<String>
```

Header statistics with `metric,value` serialization helpers.

---

*Source: [`database.rs`](../../../pyo3/src/database.rs)*
