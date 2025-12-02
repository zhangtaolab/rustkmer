# Kmer Counter

**Module**: `rustkmer::python::kmer_counter`

## Overview

Python bindings for KmerCounter

## API Reference

### Fns

#### encode_kmer

```rust
fn encode_kmer(kmer: &str) -> Result<u64, String> {
```

Encode a DNA k-mer into a compact 64-bit representation

#### decode_kmer

```rust
fn decode_kmer(encoded: u64, k: usize) -> Result<String, String> {
```

Decode a 64-bit representation back to a DNA k-mer

#### reverse_complement

```rust
fn reverse_complement(seq: &str) -> String {
```

Get reverse complement of a DNA sequence

#### canonical_kmer

```rust
fn canonical_kmer(kmer: &str, k: usize) -> Result<String, String> {
```

Get canonical k-mer (lexicographically smaller of sequence and reverse complement)

#### extract_kmers_filter_ambiguous

```rust
fn extract_kmers_filter_ambiguous(sequence: &str, k: usize) -> Vec<String> {
```

Extract k-mers from a sequence, filtering out those with ambiguous bases

#### get_k

```rust
fn get_k(&self) -> usize {
```

Get the k-mer size

#### is_canonical

```rust
fn is_canonical(&self) -> bool {
```

Check if counting canonical k-mers

#### get_kmer_count

```rust
fn get_kmer_count(&self, kmer: &str) -> PyResult<u64> {
```

Get count for a specific k-mer

#### get_count

```rust
fn get_count(&self, kmer: &str) -> PyResult<u64> {
```

Get count for a specific k-mer (alias for get_kmer_count)

#### get_all_counts

```rust
fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
```

Get all k-mer counts as a dictionary

#### merge

```rust
fn merge(&self, other_counter: &PyKmerCounter) -> PyResult<()> {
```

Merge another KmerCounter into this one

#### get_stats

```rust
fn get_stats(&self) -> PyResult<CounterStats> {
```

Get statistics for this counter

#### reset

```rust
fn reset(&self) -> PyResult<()> {
```

Reset the counter (clear all counts)

#### get_unique_count

```rust
fn get_unique_count(&self) -> usize {
```

Get the number of unique k-mers

#### get_total_count

```rust
fn get_total_count(&self) -> u64 {
```

Get the total count of all k-mers

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

*Source: [`kmer_counter.rs`](../../../python/kmer_counter.rs)*