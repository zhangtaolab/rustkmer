# Lib

**Module**: `rustkmer::lib`

## Overview

RustKmer Library
High-performance k-mer counting library for genomic data analysis.
This library provides the core functionality for counting k-mers in DNA sequences,
with support for multi-threading, memory-efficient storage, and multiple output formats.
# Examples
```rust
use rustkmer::{KmerCounter, Config};
let config = Config::new(31)  // 31-mers
.canonical(true)          // Count canonical k-mers
.threads(4);              // Use 4 threads
let mut counter = KmerCounter::new(config);
counter.process_file("genome.fa")?;
let counts = counter.get_all_counts();
# Ok::<(), Box<dyn std::error::Error>>(())
```

---

*Source: [`lib.rs`](../../../lib.rs)*