# Utils

**Module**: `rustkmer::python::utils`

## Overview

Utility functions for Python bindings

## API Reference

### Fns

#### elapsed

```rust
fn elapsed(&self) -> f64 {
```

Get elapsed time in seconds

#### elapsed_str

```rust
fn elapsed_str(&self) -> String {
```

Get elapsed time as string with units

#### finish

```rust
fn finish(&self) -> PyResult<f64> {
```

Log the elapsed time and return it

#### map_rust_error_to_py

```rust
pub fn map_rust_error_to_py(error: Box<dyn std::error::Error>) -> PyErr {
```

Map common Rust errors to appropriate Python exceptions

#### map_io_error_to_py

```rust
pub fn map_io_error_to_py(error: std::io::Error, context: &str) -> PyErr {
```

Convert IoError to DatabaseError

#### create_validation_error

```rust
pub fn create_validation_error(field: &str, value: &str, reason: &str) -> PyErr {
```

Convert validation errors with detailed context

#### create_kmer_error

```rust
pub fn create_kmer_error(kmer: &str, operation: &str, reason: &str) -> PyErr {
```

Convert k-mer related errors

#### create_database_error

```rust
pub fn create_database_error(operation: &str, path: Option<&str>, reason: &str) -> PyErr {
```

Convert database operation errors

#### create_sequence_error

```rust
pub fn create_sequence_error(sequence: &str, operation: &str, reason: &str) -> PyErr {
```

Convert sequence processing errors

### Structs

#### MemoryManager

```rust
pub struct MemoryManager {
```

Memory manager for tracking resource usage

### Fns

#### new

```rust
pub fn new() -> Self {
```

Create a new memory manager

#### allocate

```rust
pub fn allocate(&self, size: u64) -> Result<(), String> {
```

Allocate memory and update tracking

#### deallocate

```rust
pub fn deallocate(&self, size: u64) {
```

Deallocate memory and update tracking

#### current_usage

```rust
pub fn current_usage(&self) -> u64 {
```

Get current memory usage in bytes

#### peak_usage

```rust
pub fn peak_usage(&self) -> u64 {
```

Get peak memory usage in bytes

#### reset

```rust
pub fn reset(&self) {
```

Reset tracking statistics

#### get_memory_manager

```rust
pub fn get_memory_manager() -> &'static MemoryManager {
```

Get the global memory manager

#### allocate_tracked

```rust
pub fn allocate_tracked(size: u64) -> Result<(), String> {
```

Allocate memory with automatic tracking

#### deallocate_tracked

```rust
pub fn deallocate_tracked(size: u64) {
```

Deallocate memory with automatic tracking

### Structs

#### ResourceTracker

```rust
pub struct ResourceTracker {
```

Resource cleanup utility for Python objects

### Fns

#### new

```rust
pub fn new() -> Self {
```

Create a new resource tracker

#### register_allocation

```rust
pub fn register_allocation(&self) -> Result<(), String> {
```

Register a new object allocation

#### register_deallocation

```rust
pub fn register_deallocation(&self) {
```

Register a deallocation

#### current_objects

```rust
pub fn current_objects(&self) -> usize {
```

Get current object count

#### peak_objects

```rust
pub fn peak_objects(&self) -> usize {
```

Get peak object count

#### reset

```rust
pub fn reset(&self) {
```

Reset tracking statistics

#### get_resource_tracker

```rust
pub fn get_resource_tracker() -> &'static ResourceTracker {
```

Get the global resource tracker

#### register_object

```rust
pub fn register_object() -> Result<(), String> {
```

Register a Python object allocation

#### deallocate_object

```rust
pub fn deallocate_object() {
```

Register a Python object deallocation

### Structs

#### AutoResourceGuard

```rust
pub struct AutoResourceGuard {
```

RAII wrapper for automatic resource management

### Fns

#### new

```rust
pub fn new() -> Result<Self, String> {
```

Create a new resource guard

---

*Source: [`utils.rs`](../../../python/utils.rs)*