# Performance

**Module**: `rustkmer::fuzzy::performance`

## Overview

Performance optimization and metrics for fuzzy queries
This module provides performance monitoring, optimization strategies, and
resource management for fuzzy query operations.

## API Reference

### Structs

#### PerformanceMonitor

```rust
pub struct PerformanceMonitor {
```

Performance monitor for tracking operations

### Fns

#### new

```rust
pub fn new() -> Self {
```

Create a new performance monitor

#### checkpoint

```rust
pub fn checkpoint(&mut self, name: &str) {
```

Add a performance checkpoint

#### record_query

```rust
pub fn record_query(&mut self, query_time_ms: u64, success: bool) {
```

Record a database query

#### generate_metrics

```rust
pub fn generate_metrics(&self, variant_count: usize, result_count: usize) -> PerformanceMetrics {
```

Generate comprehensive performance metrics

#### extract_timing_breakdown

```rust
fn extract_timing_breakdown(&self) -> (u64, u64, u64) {
```

Extract timing breakdown from checkpoints

#### get_memory_usage_mb

```rust
fn get_memory_usage_mb() -> f64 {
```

Get current memory usage in MB

### Structs

#### PerformanceOptimizer

```rust
pub struct PerformanceOptimizer {
```

Performance optimizer for fuzzy queries

### Fns

#### new

```rust
pub fn new(config: PerformanceConfig) -> Self {
```

Create a new performance optimizer

#### optimal_batch_size

```rust
pub fn optimal_batch_size(&self, variant_count: usize) -> usize {
```

Get optimal batch size based on system characteristics

#### should_use_parallel

```rust
pub fn should_use_parallel(&self, variant_count: usize) -> bool {
```

Determine if parallel processing should be used

#### optimal_thread_count

```rust
pub fn optimal_thread_count(&self, variant_count: usize) -> usize {
```

Get optimal number of worker threads

#### check_memory_constraints

```rust
pub fn check_memory_constraints(&self, variant_count: usize) -> FuzzyResult<()> {
```

Check memory constraints

#### validate_config

```rust
pub fn validate_config(&self) -> FuzzyResult<()> {
```

Validate performance configuration

#### monitor

```rust
pub fn monitor(&mut self) -> Option<&mut PerformanceMonitor> {
```

Get performance monitor reference

#### take_monitor

```rust
pub fn take_monitor(&mut self) -> Option<PerformanceMonitor> {
```

Take the performance monitor (consumes it)

#### optimize_variant_order

```rust
pub fn optimize_variant_order(variants: &mut [String]) {
```

Optimize variant processing order for better cache performance

---

*Source: [`performance.rs`](../../../fuzzy/performance.rs)*