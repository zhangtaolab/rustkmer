<!-- generated-by: gsd-doc-writer -->
# Fuzzy Query

**Module**: `pyrustkmer` (crate `rustkmer-pyo3`, `fuzzy_query` module)

## Overview

PyFuzzyQuery — Python wrapper for RustKmer fuzzy query functionality.

This module provides Python classes that wrap the Rust fuzzy query
capabilities for pattern matching with wildcards (`N`) and mutations
(Hamming-distance tolerance, including position-specific mutation configs).
It defines:

- `PyFuzzyQuery` — the query engine, constructed from a `PyDatabase`
- `PyFuzzyResult` — the complete result of one fuzzy query
- `PyFuzzyMatch` — a single matched k-mer

Queries are executed by reloading the `.rkdb` file into an
`RKDatabase` and running the core `FuzzyQueryEngine` (sequential
processing, batch size 1000).

## API Reference

### Structs

#### PyFuzzyMatch

```rust
#[pyclass]
#[derive(Clone, Debug)]
pub struct PyFuzzyMatch {
    pub kmer: String,
    pub count: u64,
    pub distance: Option<usize>,
    pub match_type: String,
    pub mutation_positions: Vec<usize>,
}
```

Individual fuzzy match result: the matched k-mer sequence, its count in the
database, the Hamming distance from the query pattern (if applicable), a
match-type string (`"exact"`, `"wildcard_expansion[...]"`,
`"mutation_tolerance[...]"`, `"length_normalization"`), and the positions
involved in mutations.

#### PyFuzzyResult

```rust
#[pyclass]
pub struct PyFuzzyResult {
    pub query_kmer: String,
    pub exact_match: Option<PyFuzzyMatch>,
    pub matches: Vec<PyFuzzyMatch>,
    pub total_matches: usize,
    pub mutation_tolerance: u32,
    pub query_time_ms: u64,
    pub has_position_mutations: bool,
}
```

Complete fuzzy query result: the original query pattern, the exact match (if
found), all fuzzy matches, totals, the mutation tolerance used, execution
time in milliseconds, and whether position-specific mutations were used.

#### PyFuzzyQuery

```rust
#[pyclass]
pub struct PyFuzzyQuery {
    database_path: String,
    kmer_size: usize,
}
```

High-performance fuzzy k-mer query engine for Python. Constructed from a
`PyDatabase`; stores the database path and k-mer size, and reloads the
database on each query.

### Fns

#### PyFuzzyQuery::new

```rust
#[new]
fn new(database: &PyDatabase) -> PyResult<Self> {
```

Create a new fuzzy query engine from a loaded `PyDatabase`. Reads the
database path, loads the Rust `RKDatabase` to determine the k-mer size.
Raises `ValueError` if the database cannot be loaded
("Failed to load database for fuzzy queries: ...").

#### PyFuzzyQuery::query_fuzzy

```rust
#[pyo3(signature = (pattern, max_mutations, max_results=None))]
fn query_fuzzy(&self, pattern: &Bound<'_, PyString>, max_mutations: u32, max_results: Option<usize>) -> PyResult<PyFuzzyResult> {
```

Perform a fuzzy query with wildcard (`N`) and mutation support
(unified-naming version). Validates that the pattern length equals the
database k-mer size and that only `A`, `T`, `C`, `G`, `N` are used; raises
`ValueError` otherwise. Raises `RuntimeError` if the database cannot be
reloaded or the query execution fails.

#### PyFuzzyQuery::query_fuzzy_position

```rust
#[pyo3(signature = (pattern, max_mutations, position_mutations, max_results=None))]
fn query_fuzzy_position(&self, pattern: &Bound<'_, PyString>, max_mutations: u32, position_mutations: &str, max_results: Option<usize>) -> PyResult<PyFuzzyResult> {
```

Perform a fuzzy query with position-specific mutations
(unified-naming version). `position_mutations` is a configuration string
parsed by `PositionMutationConfig::parse`; an invalid configuration raises
`ValueError` ("Invalid position mutation configuration: ...").

#### PyFuzzyQuery::fuzzy_query

```rust
#[pyo3(signature = (pattern, max_mutations, max_results=None))]
fn fuzzy_query(&self, pattern: &Bound<'_, PyString>, max_mutations: u32, max_results: Option<usize>) -> PyResult<PyFuzzyResult> {
```

Perform fuzzy query with wildcard and mutation support.
Deprecated since 2.0.0 — use `query_fuzzy()` instead.

#### PyFuzzyQuery::fuzzy_query_with_position_mutations

```rust
#[pyo3(signature = (pattern, max_mutations, position_mutations, max_results=None))]
fn fuzzy_query_with_position_mutations(&self, pattern: &Bound<'_, PyString>, max_mutations: u32, position_mutations: &str, max_results: Option<usize>) -> PyResult<PyFuzzyResult> {
```

Perform fuzzy query with position-specific mutations.
Deprecated since 2.0.0 — use `query_fuzzy_position()` instead.

#### PyFuzzyQuery.kmer_size (property)

```rust
#[getter]
fn kmer_size(&self) -> usize {
```

Get the database k-mer size.

#### PyFuzzyResult::get_matches_by_distance

```rust
fn get_matches_by_distance(&self, distance: u32) -> Vec<PyFuzzyMatch> {
```

Get matches filtered by a specific Hamming distance.

#### PyFuzzyResult::get_top_matches

```rust
fn get_top_matches(&self, limit: usize) -> Vec<PyFuzzyMatch> {
```

Get top matches by count (most frequent k-mers).

#### PyFuzzyResult::to_json

```rust
fn to_json(&self) -> PyResult<String> {
```

Serialize the result to a JSON string.

#### PyFuzzyResult::to_csv

```rust
fn to_csv(&self) -> PyResult<String> {
```

Serialize the result to CSV (header `kmer,count,distance,match_type,mutation_positions`,
plus `#`-prefixed metadata lines).

#### PyFuzzyResult::to_tsv

```rust
fn to_tsv(&self) -> PyResult<String> {
```

Serialize the result to TSV (same layout as CSV with tab separators).

#### PyFuzzyResult properties

```rust
#[getter] fn query_kmer(&self) -> &str
#[getter] fn exact_match(&self) -> Option<PyFuzzyMatch>
#[getter] fn matches(&self) -> Vec<PyFuzzyMatch>
#[getter] fn total_matches(&self) -> usize
#[getter] fn mutation_tolerance(&self) -> u32
#[getter] fn query_time_ms(&self) -> u64
#[getter] fn has_position_mutations(&self) -> bool
```

#### PyFuzzyMatch properties

```rust
#[getter] fn kmer(&self) -> &str
#[getter] fn count(&self) -> u64
#[getter] fn distance(&self) -> Option<usize>
#[getter] fn mutation_positions(&self) -> Vec<usize>
#[getter] fn match_type(&self) -> &str
```

#### PyFuzzyMatch::\_\_repr\_\_

```rust
fn __repr__(&self) -> String {
```

Returns
`PyFuzzyMatch(kmer='...', count=..., distance=..., mutation_positions=..., match_type='...')`.

#### PyFuzzyResult::\_\_repr\_\_

```rust
fn __repr__(&self) -> String {
```

Returns
`PyFuzzyResult(query='...', total_matches=..., mutation_tolerance=..., query_time_ms=...)`.

---

*Source: [`fuzzy_query.rs`](../../../pyo3/src/fuzzy_query.rs)*
