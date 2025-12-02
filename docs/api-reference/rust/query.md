# Query

**Module**: `rustkmer::database::query`

## Overview

Database query functionality
Provides fast k-mer lookup from rustkmer databases with support
for various query modes and efficient binary search.

## API Reference

### Fns

#### load_entries

```rust
fn load_entries(file: &mut BufReader<File>, header: &DatabaseHeader) -> ProcessingResult<Vec<KmerEntry>> {
```

Load all k-mer entries into memory

#### query_kmer

```rust
pub fn query_kmer(&mut self, kmer_seq: &str) -> ProcessingResult<Option<u32>> {
```

Query a single k-mer count

# Arguments
* `kmer_seq` - The k-mer sequence to query

# Returns
The count of the k-mer, or None if not found

#### query_from_memory

```rust
fn query_from_memory(&self, encoded_kmer: u64) -> ProcessingResult<Option<u32>> {
```

Query from in-memory cache

#### query_from_disk

```rust
fn query_from_disk(&mut self, encoded_kmer: u64) -> ProcessingResult<Option<u32>> {
```

Query from disk using binary search

#### read_entry_at

```rust
fn read_entry_at(&mut self, index: u64) -> ProcessingResult<KmerEntry> {
```

Read entry at specific position

#### query_multiple

```rust
pub fn query_multiple(&mut self, kmer_seqs: &[String]) -> ProcessingResult<Vec<(String, u32)>> {
```

Query multiple k-mers

# Arguments
* `kmer_seqs` - Vector of k-mer sequences to query

# Returns
Vector of (kmer, count) pairs, with 0 for missing k-mers

#### get_info

```rust
pub fn get_info(&self) -> &DatabaseHeader {
```

Get database information

#### size_bytes

```rust
pub fn size_bytes(&self) -> u64 {
```

Get database size estimate

#### new

```rust
pub fn new(database: &'a RKDatabase) -> Self {
```

Create a new k-mer query interface

#### query

```rust
pub fn query(&mut self, kmer: &str) -> crate::error::ProcessingResult<QueryResult> {
```

Query a single k-mer

#### query_multiple

```rust
pub fn query_multiple(&mut self, kmers: &[String]) -> crate::error::ProcessingResult<Vec<QueryResult>> {
```

Query multiple k-mers

---

*Source: [`query.rs`](../../../database/query.rs)*