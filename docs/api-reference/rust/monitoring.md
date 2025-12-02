# Monitoring

**Module**: `rustkmer::core::monitoring`

## Overview

Performance monitoring infrastructure with conditional compilation
This module provides low-overhead performance monitoring that can be
enabled/disabled at compile time using the "profiling" feature flag.

## API Reference

### Fns

#### new

```rust
pub fn new(operation_name: String) -> Self {
```

Create a new performance timer

#### with_collector

```rust
pub fn with_collector(operation_name: String, collector: Arc<Mutex<MetricsCollector>>) -> Self {
```

Create a new performance timer with metrics collector

#### finish

```rust
pub fn finish(self) -> Duration {
```

Finish timing and record the duration

#### elapsed

```rust
pub fn elapsed(&self) -> Duration {
```

Get elapsed time without finishing

---

*Source: [`monitoring.rs`](../../../core/monitoring.rs)*