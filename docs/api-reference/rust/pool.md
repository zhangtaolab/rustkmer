# Pool

**Module**: `rustkmer::parallel::pool`

## Overview

Thread pool utilities for parallel processing
Provides a reusable thread pool for k-mer counting operations.

## API Reference

### Traits

#### Task

```rust
pub trait Task: Send + Sync + 'static {
```

A task that can be executed by the thread pool

### Fns

#### execute

```rust
fn execute(self: Box<Self>) -> ProcessingResult<()>;
```

Execute the task

### Structs

#### ThreadPool

```rust
pub struct ThreadPool {
```

Thread pool for parallel task execution

### Fns

#### new

```rust
pub fn new(size: usize) -> ProcessingResult<Self> {
```

Create a new thread pool

# Arguments
* `size` - Number of threads in the pool

# Returns
New ThreadPool instance

#### size

```rust
pub fn size(&self) -> usize {
```

Get the number of threads in the pool

#### shutdown

```rust
pub fn shutdown(mut self) {
```

Shutdown the thread pool

### Structs

#### Worker

```rust
struct Worker {
```

Worker thread in the thread pool

### Fns

#### new

```rust
fn new(id: usize, receiver: Arc<Mutex<Receiver<Box<dyn Task>>>>) -> ProcessingResult<Self> {
```

Create a new worker thread

# Arguments
* `id` - Worker ID
* `receiver` - Shared receiver for tasks

# Returns
New Worker instance

### Structs

#### SequenceCountTask

```rust
pub struct SequenceCountTask {
```

Simple task for counting k-mers in a sequence

#### ThreadPoolBuilder

```rust
pub struct ThreadPoolBuilder {
```

Builder for thread pool

### Fns

#### new

```rust
pub fn new() -> Self {
```

Create a new thread pool builder

#### size

```rust
pub fn size(mut self, size: usize) -> Self {
```

Set the thread pool size

#### build

```rust
pub fn build(self) -> ProcessingResult<ThreadPool> {
```

Build the thread pool

### Structs

#### SimpleTask

```rust
struct SimpleTask {
```

Simple test task

---

*Source: [`pool.rs`](../../../parallel/pool.rs)*