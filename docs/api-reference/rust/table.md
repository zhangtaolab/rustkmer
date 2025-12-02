# Table

**Module**: `rustkmer::hash::table`

## Overview

Concurrent hash table for k-mer counting
Provides a thread-safe hash table implementation optimized for k-mer counting
with minimal contention and efficient memory usage.

## API Reference

### Fns

#### new

```rust
pub fn new(kmer_length: usize, canonical_mode: bool, initial_capacity: usize, _num_threads: usize) -> ProcessingResult<Self> {
```

Create a new k-mer counter

# Arguments
* `kmer_length` - Length of k-mers to count
* `canonical_mode` - Whether to count canonical k-mers
* `initial_capacity` - Initial hash table capacity
* `num_threads` - Number of threads for concurrent processing

# Returns
New KmerCounter instance

#### increment

```rust
pub fn increment(&self, kmer_encoded: u64) -> ProcessingResult<()> {
```

Increment the count for a k-mer

# Arguments
* `kmer_encoded` - Packed k-mer representation

# Returns
Result indicating success or error

#### get_count

```rust
pub fn get_count(&self, kmer_encoded: u64) -> Option<u32> {
```

Get the count for a specific k-mer

# Arguments
* `kmer_encoded` - Packed k-mer representation

# Returns
Number of occurrences, or None if not found

#### get_all_counts

```rust
pub fn get_all_counts(&self) -> Vec<(u64, u32)> {
```

Get all k-mer counts as a vector

# Returns
Vector of (kmer_encoded, count) pairs

#### get_top_n

```rust
pub fn get_top_n(&self, n: usize) -> Vec<(u64, u32)> {
```

Get the top N most frequent k-mers

# Arguments
* `n` - Number of top k-mers to return

# Returns
Vector of (kmer_encoded, count) pairs sorted by count descending

#### filter_by_count

```rust
pub fn filter_by_count(&self, min_count: u32, max_count: u32) -> Vec<(u64, u32)> {
```

Filter k-mers by count range

# Arguments
* `min_count` - Minimum count (inclusive)
* `max_count` - Maximum count (inclusive)

# Returns
Vector of (kmer_encoded, count) pairs within the specified range

#### get_filtered_kmers

```rust
pub fn get_filtered_kmers(&self, filter: &Option<CountFilter>) -> Vec<(u64, u32)> {
```

Get k-mers with filtering applied using CountFilter

# Arguments
* `filter` - Optional count filter to apply

# Returns
Vector of (kmer_encoded, count) pairs after filtering

#### get_filtering_stats

```rust
pub fn get_filtering_stats(&self, filter: &Option<CountFilter>) -> FilteringResult {
```

Get filtering statistics

# Arguments
* `filter` - Optional count filter to analyze

# Returns
FilteringResult with statistics

#### total_kmers

```rust
pub fn total_kmers(&self) -> u64 {
```

Get total number of k-mers processed

#### unique_kmers

```rust
pub fn unique_kmers(&self) -> u64 {
```

Get number of unique k-mers found

#### kmer_length

```rust
pub fn kmer_length(&self) -> usize {
```

Get k-mer length

#### canonical_mode

```rust
pub fn canonical_mode(&self) -> bool {
```

Check if canonical mode is enabled

#### reset

```rust
pub fn reset(&self) {
```

Reset the counter to empty state

#### memory_usage

```rust
pub fn memory_usage(&self) -> usize {
```

Get current memory usage estimate

# Returns
Estimated memory usage in bytes

#### get_stats

```rust
pub fn get_stats(&self) -> CounterStats {
```

Get statistics for the counter

# Returns
Statistics struct with current counts

#### get_all_kmers

```rust
pub fn get_all_kmers(&self) -> Vec<(u64, u32)> {
```

Get all k-mers as a vector (alias for get_all_counts)

# Returns
Vector of (kmer_encoded, count) pairs

#### get_kmer_length

```rust
pub fn get_kmer_length(&self) -> usize {
```

Get k-mer length (alias for kmer_length)

#### merge

```rust
pub fn merge(&self, other: &KmerCounter) -> ProcessingResult<()> {
```

Merge counts from another KmerCounter

# Arguments
* `other` - Another KmerCounter to merge from

# Returns
Result indicating success or error

### Structs

#### KmerCounterBuilder

```rust
pub struct KmerCounterBuilder {
```

Builder for KmerCounter with configuration options

### Fns

#### new

```rust
pub fn new(kmer_length: usize) -> Self {
```

Create a new builder

#### canonical

```rust
pub fn canonical(mut self, canonical: bool) -> Self {
```

Enable canonical mode

#### capacity

```rust
pub fn capacity(mut self, capacity: usize) -> Self {
```

Set initial hash table capacity

#### max_count

```rust
pub fn max_count(mut self, max: u32) -> Self {
```

Set maximum count value

#### build

```rust
pub fn build(self) -> ProcessingResult<KmerCounter> {
```

Build the KmerCounter

---

*Source: [`table.rs`](../../../hash/table.rs)*