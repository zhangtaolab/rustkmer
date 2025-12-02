# Persistence

**Module**: `rustkmer::core::database::persistence`

## Overview

Database persistence utilities for KmerCounter database saving and loading

## API Reference

### Fns

#### encode_kmer_to_bytes

```rust
fn encode_kmer_to_bytes(kmer: &str) -> Result<Vec<u8>, PersistenceError> {
```

Simple k-mer to bytes encoding (can be replaced with more efficient encoding)

#### decode_kmer_from_bytes

```rust
fn decode_kmer_from_bytes(bytes: &[u8]) -> Result<String, PersistenceError> {
```

Simple bytes to k-mer decoding (can be replaced with more efficient decoding)

#### generate_checksums

```rust
fn generate_checksums(files: &[(&str, &Path)]) -> Result<Vec<(String, String)>, PersistenceError> {
```

Generate SHA256 checksums for specified files

#### save_checksums

```rust
fn save_checksums(database_path: &Path, checksums: &[(String, String)]) -> Result<(), PersistenceError> {
```

Save checksums to checksums.txt file

#### validate_checksums

```rust
pub fn validate_checksums(database_path: &Path) -> Result<bool, PersistenceError> {
```

Load and validate checksums from checksums.txt file

---

*Source: [`persistence.rs`](../../../core/database/persistence.rs)*