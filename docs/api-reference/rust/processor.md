# Processor

**Module**: `rustkmer::parallel::processor`

## Overview

Parallel processing utilities for k-mer counting
Provides multi-threaded processing of sequence files.

## API Reference

### Structs

#### ParallelProcessor

```rust
pub struct ParallelProcessor {
```

Parallel sequence processor

### Fns

#### process_single_sequence

```rust
fn process_single_sequence(&self, sequence: &str) -> ProcessingResult<()> {
```

Process a single sequence

# Arguments
* `sequence` - DNA sequence

# Returns
Processing result

#### get_stats

```rust
pub fn get_stats(&self) -> crate::hash::table::CounterStats {
```

Get processing statistics

### Structs

#### WorkItem

```rust
pub struct WorkItem {
```

Work item for parallel processing

#### QueueProcessor

```rust
pub struct QueueProcessor {
```

Parallel processor using work queue

---

*Source: [`processor.rs`](../../../parallel/processor.rs)*