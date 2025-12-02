# Count

**Module**: `rustkmer::cli::commands::count`

## Overview

Count command implementation
Implements the k-mer counting functionality.

## API Reference

### Fns

#### execute_count

```rust
pub fn execute_count(args: &Args) -> ProcessingResult<()> {
```

Execute the count command

#### decode_kmer

```rust
fn decode_kmer(kmer: u64, k: usize) -> String {
```

Decode a k-mer from encoded format back to DNA sequence

---

*Source: [`count.rs`](../../../cli/commands/count.rs)*