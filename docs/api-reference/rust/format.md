# Format

**Module**: `rustkmer::database::format`

## Overview

Database format definitions and I/O operations
Defines the binary format for storing k-mer databases with
efficient random access and compatibility with rustkmer tools.

## API Reference

### Consts

#### DATABASE_MAGIC

```rust
pub const DATABASE_MAGIC: &[u8; 4] = b"RKDB";
```

Magic number for rustkmer database files

#### DATABASE_VERSION

```rust
pub const DATABASE_VERSION: u16 = 1;
```

Database version

### Fns

#### new

```rust
pub fn new(kmer_size: u8, total_kmers: u64, canonical: bool) -> Self {
```

Create a new database header

#### validate

```rust
pub fn validate(&self) -> Result<(), String> {
```

Validate header consistency

#### new

```rust
pub fn new(kmer: u64, count: u32) -> Self {
```

Create a new k-mer entry

#### extension

```rust
pub fn extension(&self) -> &'static str {
```

Get the file extension for this format

#### new

```rust
pub fn new(header: DatabaseHeader) -> Self {
```

Create a new database with the given header

#### header

```rust
pub fn header(&self) -> &DatabaseHeader {
```

Get reference to the database header

#### from_file_path

```rust
pub fn from_file_path(path: &std::path::Path) -> crate::error::ProcessingResult<Self> {
```

Load database from file path

#### from_file_path_mapped

```rust
pub fn from_file_path_mapped(path: &std::path::Path) -> crate::error::ProcessingResult<Self> {
```

Load database from file path with memory mapping

#### write_to_file

```rust
pub fn write_to_file(&self, path: &std::path::Path) -> crate::error::ProcessingResult<()> {
```

Write database to file

#### kmer_size

```rust
pub fn kmer_size(&self) -> usize {
```

Get the k-mer size

#### size

```rust
pub fn size(&self) -> Option<u64> {
```

Get the total number of k-mers

#### query_kmer

```rust
pub fn query_kmer(&self, kmer: &str) -> Option<u64> {
```

Query a k-mer from the database

#### binary_search_kmer

```rust
fn binary_search_kmer(&self, query_encoded: u64) -> Option<u64> {
```

Binary search for a k-mer in a sorted database

#### linear_search_kmer

```rust
fn linear_search_kmer(&self, query_encoded: u64) -> Option<u64> {
```

Linear search for a k-mer in an unsorted database

---

*Source: [`format.rs`](../../../database/format.rs)*