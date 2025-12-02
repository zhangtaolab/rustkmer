# Overflow

**Module**: `rustkmer::hash::overflow`

## Overview

Disk-based overflow storage for k-mer counting
Provides temporary disk storage when hash table memory is insufficient.

## API Reference

### Fns

#### store

```rust
pub fn store(&mut self, kmer_encoded: u64, count: u32) -> ProcessingResult<()> {
```

Store a k-mer count in overflow storage

# Arguments
* `kmer_encoded` - Packed k-mer representation
* `count` - K-mer count

# Returns
Result indicating success or error

#### new_file

```rust
fn new_file(&mut self) -> ProcessingResult<()> {
```

Create a new overflow file

#### close_current_file

```rust
fn close_current_file(&mut self) -> ProcessingResult<()> {
```

Close current overflow file

#### close

```rust
pub fn close(&mut self) -> ProcessingResult<()> {
```

Close all files and cleanup

#### kmer_count

```rust
pub fn kmer_count(&self) -> u64 {
```

Get total number of stored k-mers

#### size_bytes

```rust
pub fn size_bytes(&self) -> u64 {
```

Get approximate size in bytes

#### read_all

```rust
pub fn read_all(&self) -> impl Iterator<Item = ProcessingResult<(u64, u32)>> {
```

Read back all stored k-mers (for testing/retrieval)

# Returns
Iterator over (kmer_encoded, count) pairs

#### list_overflow_files

```rust
fn list_overflow_files(&self) -> Vec<PathBuf> {
```

List all overflow files

### Structs

#### OverflowFileReader

```rust
struct OverflowFileReader {
```

Iterator for reading overflow files

---

*Source: [`overflow.rs`](../../../hash/overflow.rs)*