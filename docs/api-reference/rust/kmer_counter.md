<!-- generated-by: gsd-doc-writer -->
# Kmer Counter

**Module**: `pyrustkmer` (crate `rustkmer-pyo3`, `counter` module)

## Overview

PyCounter — Python wrapper for the RustKmer `KmerCounter`.

This module provides `PyCounter`, a Python interface to RustKmer's
high-performance k-mer counting functionality (backed by
`rustkmer::hash::KmerCounter` behind an `Arc`), plus the `PyCounterStats`
statistics object. It supports:

- Adding individual k-mers (`add_kmer`)
- Processing sequences from strings (`add_sequence`)
- Reading FASTA and FASTQ files with transparent `.gz` / `.bz2` / `.xz`
  compression (`add_from_fasta`, `add_from_fastq`) — the GIL is released
  during file processing so rayon workers run in parallel
- Saving results to the RKDB database format (`save_database`)
- Canonical k-mer counting (forward and reverse complement merged)

```python
from pyrustkmer import PyCounter

counter = PyCounter(21, canonical=True)
counter.add_sequence("ATGCGATGCATGCGATGCATGCGATGCAT")
counter.save_database("output.rkdb")
stats = counter.get_stats()
```

## API Reference

### Structs

#### PyCounter

```rust
#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    counter: Arc<RustPyCounter>,  // rustkmer::hash::KmerCounter
}
```

High-performance k-mer counter for Python.

#### PyCounterStats

```rust
#[pyclass]
pub struct PyCounterStats {
    pub total_kmers: u64,
    pub unique_kmers: u64,
    pub kmer_length: usize,
    pub canonical_mode: bool,
    pub memory_usage: usize,
}
```

Statistics for counter operations: total k-mers processed, number of unique
k-mers, k-mer length, whether canonical mode is enabled, and estimated
memory usage in bytes.

### Fns

#### PyCounter::new

```rust
#[new]
#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]
fn new(kmer_length: i64, canonical: bool, initial_capacity: usize, threads: Option<usize>) -> PyResult<Self> {
```

Create a new k-mer counter.

- `kmer_length` — length of k-mers to count (1-64)
- `canonical` — count canonical k-mers (forward and reverse complement merged)
- `initial_capacity` — initial hash table capacity (default 1000)
- `threads` — number of rayon worker threads for parallel counting
  (default `None` = all available cores); values `< 1` are rejected

Raises `ValueError` if `kmer_length` is not between 1 and 64, if
`threads < 1`, or if the underlying counter cannot be created. Configures
the global rayon thread pool once per process.

#### PyCounter::add_kmer

```rust
fn add_kmer(&self, kmer: &Bound<'_, PyString>) -> PyResult<()> {
```

Add a single k-mer to the counter. The string must contain only `A`, `C`,
`G`, `T` and match the counter's k-mer length; otherwise raises
`ValueError`.

#### PyCounter::add_sequence

```rust
fn add_sequence(&self, sequence: &Bound<'_, PyString>) -> PyResult<()> {
```

Extract and add k-mers from a sequence string. Invalid characters (`N`,
etc.) are filtered out before extraction; k-mers spanning invalid
characters are not counted. Sequences shorter than k are no-ops.

#### PyCounter::add_from_fasta

```rust
fn add_from_fasta(&self, py: Python<'_>, file_path: &Bound<'_, PyString>) -> PyResult<()> {
```

Read and process k-mers from a FASTA file. Automatically detects and
decompresses `.gz` / `.bz2` / `.xz` compression; headers are ignored and
invalid characters are skipped. Releases the GIL for the duration of the
file processing. Raises `ValueError` if the file cannot be read.

#### PyCounter::add_from_fastq

```rust
fn add_from_fastq(&self, py: Python<'_>, file_path: &Bound<'_, PyString>) -> PyResult<()> {
```

Read and process k-mers from a FASTQ file (4-line records; headers and
quality strings ignored). Same compression, GIL-release, and error behavior
as `add_from_fasta`.

#### PyCounter::save_database

```rust
fn save_database(&self, file_path: &Bound<'_, PyString>) -> PyResult<()> {
```

Save k-mer counts to a sorted RKDB (`.rkdb`) database file for fast
querying. Raises `ValueError` when saving an empty counter ("Cannot save
empty database. Add k-mers first.") or if the file cannot be written. The
result can be loaded with `PyDatabase("output.rkdb", LoadMode.Preload)`.

#### PyCounter::get_stats

```rust
fn get_stats(&self) -> PyCounterStats {
```

Get statistics for the counter (`total_kmers`, `unique_kmers`,
`kmer_length`, `canonical_mode`, `memory_usage`).

#### PyCounter::get_count

```rust
fn get_count(&self, kmer: &Bound<'_, PyString>) -> PyResult<u32> {
```

Get the count for a specific k-mer (0 if not found). In canonical mode the
query k-mer is canonicalized before lookup. Raises `ValueError` for
invalid characters or a length mismatch.

#### PyCounter::get_all_counts

```rust
fn get_all_counts(&self) -> PyResult<std::collections::HashMap<String, u32>> {
```

Get all k-mer counts as a dictionary mapping decoded k-mer strings to
their `u32` counts. In canonical mode the keys are canonical k-mers. May
use significant memory for large counters.

#### PyCounter::is_empty

```rust
fn is_empty(&self) -> bool {
```

True if no k-mers have been counted.

#### PyCounter::reset

```rust
fn reset(&self) {
```

Reset the counter, clearing all counted k-mers.

#### PyCounter properties

```rust
#[getter] fn kmer_length(&self) -> usize
#[getter] fn canonical(&self) -> bool
```

`kmer_length` — the k-mer length; `canonical` — whether canonical mode is
enabled.

#### PyCounter::\_\_repr\_\_

```rust
fn __repr__(&self) -> String {
```

Returns
`PyCounter(kmer_length=..., canonical=..., total_kmers=..., unique_kmers=...)`.

#### PyCounterStats properties

```rust
#[getter] fn total_kmers(&self) -> u64
#[getter] fn unique_kmers(&self) -> u64
#[getter] fn kmer_length(&self) -> usize
#[getter] fn canonical_mode(&self) -> bool
#[getter] fn memory_usage(&self) -> usize
```

#### PyCounterStats::\_\_repr\_\_

```rust
fn __repr__(&self) -> String {
```

Returns
`PyCounterStats(total_kmers=..., unique_kmers=..., kmer_length=..., canonical_mode=..., memory_usage=...)`.

---

*Source: [`counter.rs`](../../../pyo3/src/counter.rs)*
