# Fasta

**Module**: `rustkmer::io::fasta`

## Overview

FASTA file parsing using the bio crate
Provides efficient FASTA file reading and processing capabilities.

## API Reference

### Structs

#### FastaProcessor

```rust
pub struct FastaProcessor {
```

FASTA file processor for efficient genomic data reading

### Fns

#### read_all

```rust
pub fn read_all(&self) -> ProcessingResult<Vec<Record>> {
```

Read all sequences from a FASTA file

# Returns
Vector of sequence records

#### file_path

```rust
pub fn file_path(&self) -> &str {
```

Get the file path

#### file_exists

```rust
pub fn file_exists(&self) -> bool {
```

Check if file exists and is accessible

#### file_size

```rust
pub fn file_size(&self) -> ProcessingResult<u64> {
```

Get file size

---

*Source: [`fasta.rs`](../../../io/fasta.rs)*