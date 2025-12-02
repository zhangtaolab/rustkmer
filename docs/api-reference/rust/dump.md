# Dump

**Module**: `rustkmer::cli::commands::dump`

## Overview

Dump command implementation
Implements database inspection and conversion functionality.

## API Reference

### Fns

#### execute_dump

```rust
pub fn execute_dump(args: &Args) -> ProcessingResult<()> {
```

Execute the dump command

#### dump_database

```rust
fn dump_database(database_path: &str, output_path: Option<&str>) -> ProcessingResult<()> {
```

Dump database contents to text format

#### detect_database_format

```rust
fn detect_database_format(path: &Path) -> ProcessingResult<DatabaseFormat> {
```

Detect database format by reading file header

#### dump_rkdb_database

```rust
fn dump_rkdb_database(path: &Path, output_path: Option<&str>) -> ProcessingResult<()> {
```

Dump RKDB format database

#### dump_bincode_database

```rust
fn dump_bincode_database(path: &Path, output_path: Option<&str>) -> ProcessingResult<()> {
```

Dump bincode format database (legacy format)

#### decode_kmer_to_sequence

```rust
fn decode_kmer_to_sequence(kmer: u64, k: usize) -> String {
```

Decode a k-mer from encoded format back to DNA sequence

---

*Source: [`dump.rs`](../../../cli/commands/dump.rs)*