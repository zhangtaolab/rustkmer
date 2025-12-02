# Database

**Module**: `rustkmer::python::database`

## Overview

Python bindings for Database operations

## API Reference

### Fns

#### simple_encode_kmer

```rust
fn simple_encode_kmer(&self, kmer: &str) -> u64 {
```

Simple k-mer encoding for testing purposes
TODO: Replace with real k-mer encoding when database module is integrated

#### simple_decode_kmer

```rust
fn simple_decode_kmer(&self, encoded: u64, length: usize) -> String {
```

Simple k-mer decoding for testing purposes
TODO: Replace with real k-mer decoding when database module is integrated

#### __enter__

```rust
fn __enter__(&self) -> PyResult<Self> {
```

Context manager entry

#### __exit__

```rust
fn __exit__(&self, _exc_type: PyObject, _exc_val: PyObject, _exc_tb: PyObject) -> PyResult<()> {
```

Context manager exit

#### query

```rust
fn query(&self, kmer: &str) -> PyResult<PyQueryResult> {
```

Query a single k-mer and return a QueryResult

#### query_multiple

```rust
fn query_multiple(&self, kmers: Vec<String>) -> PyResult<Vec<PyQueryResult>> {
```

Query multiple k-mers in batch

#### get_kmer_size

```rust
fn get_kmer_size(&self) -> PyResult<usize> {
```

Get the k-mer size from the database

#### get_k

```rust
fn get_k(&self) -> PyResult<usize> {
```

Get the k-mer size (alias for get_kmer_size)

#### get_stats

```rust
fn get_stats(&self) -> PyResult<PyDatabaseStats> {
```

Get database statistics

#### load

```rust
fn load(&mut self, file_path: &str, preload: bool) -> PyResult<()> {
```

Load a database from file

#### load_kmercounter_database

```rust
fn load_kmercounter_database(&mut self, database_path: String, preload: bool) -> PyResult<()> {
```

Load KmerCounter-created database with hybrid format

#### load_legacy_database

```rust
fn load_legacy_database(&mut self, file_path: &str, preload: bool) -> PyResult<()> {
```

Load legacy database file (placeholder implementation)

#### get_count

```rust
fn get_count(&self, kmer: &str) -> PyResult<u64> {
```

Get count for a specific k-mer (compatibility method)

#### get_all_counts

```rust
fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
```

Get all k-mer counts

#### get_metadata

```rust
fn get_metadata(&self) -> PyResult<PyObject> {
```

Get database metadata

#### close

```rust
fn close(&self) -> PyResult<()> {
```

Close the database

#### get_path

```rust
fn get_path(&self) -> Option<String> {
```

Get the database file path

#### is_open

```rust
fn is_open(&self) -> bool {
```

Check if database is open

#### is_preloaded

```rust
fn is_preloaded(&self) -> bool {
```

Check if database is preloaded into memory

#### __repr__

```rust
fn __repr__(&self) -> String {
```

Get a string representation

#### __str__

```rust
fn __str__(&self) -> String {
```

Get a string representation

---

*Source: [`database.rs`](../../../python/database.rs)*