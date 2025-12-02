# Filtering

**Module**: `rustkmer::hash::filtering`

## Overview

K-mer count filtering functionality
Provides filtering structures and logic for k-mer count thresholds.
Implements jellyfish-compatible -L/-U parameter behavior.

## API Reference

### Fns

#### new

```rust
pub fn new(min_count: Option<u64>, max_count: Option<u64>) -> Self {
```

Create a new count filter

# Arguments
* `min_count` - Optional minimum count threshold
* `max_count` - Optional maximum count threshold

# Returns
New CountFilter instance

#### passes

```rust
pub fn passes(&self, count: u64) -> bool {
```

Check if a count passes this filter

# Arguments
* `count` - Count to check

# Returns
true if count passes the filter, false otherwise

#### new

```rust
pub fn new(min_count: Option<u64>, max_count: Option<u64>) -> Self {
```

Create a new filter configuration with validation

# Arguments
* `min_count` - Optional minimum count threshold
* `max_count` - Optional maximum count threshold

# Returns
Validated CountFilterConfig

#### validate_parameters

```rust
fn validate_parameters(min_count: Option<u64>, max_count: Option<u64>) -> ValidationState {
```

Validate filtering parameters

# Arguments
* `min_count` - Optional minimum count threshold
* `max_count` - Optional maximum count threshold

# Returns
ValidationState with any errors found

#### is_valid

```rust
pub fn is_valid(&self) -> bool {
```

Check if the configuration is valid

# Returns
true if valid, false otherwise

#### get_errors

```rust
pub fn get_errors(&self) -> Vec<String> {
```

Get validation errors if any

# Returns
Vector of error messages, empty if valid

#### new

```rust
pub fn new(total_before: u64, unique_before: u64, kept_after: u64, filter: CountFilter) -> Self {
```

Create a new filtering result

# Arguments
* `total_before` - Total k-mers before filtering
* `unique_before` - Unique k-mers before filtering
* `kept_after` - K-mers kept after filtering
* `filter` - Filter that was applied

# Returns
New FilteringResult instance

#### has_filtering

```rust
pub fn has_filtering(&self) -> bool {
```

Check if any filtering was applied

# Returns
true if any k-mers were filtered out

#### kept_percentage

```rust
pub fn kept_percentage(&self) -> f64 {
```

Get filtering ratio as a percentage

# Returns
Percentage of k-mers kept (0.0 to 100.0)

---

*Source: [`filtering.rs`](../../../hash/filtering.rs)*