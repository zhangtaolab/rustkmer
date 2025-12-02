# Args

**Module**: `rustkmer::cli::args`

## Overview

CLI argument definitions for rustkmer
Provides command-line argument parsing using clap.

## API Reference

### Fns

#### create_count_filter

```rust
pub fn create_count_filter(&self) -> Option<crate::hash::CountFilter> {
```

Create a count filter from the command parameters

# Returns
Option<CountFilter> for the filtering parameters

#### validate_filtering

```rust
pub fn validate_filtering(&self) -> Result<(), Vec<String>> {
```

Validate filtering parameters for the Count command

# Returns
Result<(), Vec<String>> with validation errors if any

#### has_filtering

```rust
pub fn has_filtering(&self) -> bool {
```

Check if filtering is enabled for this command

# Returns
true if filtering parameters are specified

#### validate_input

```rust
pub fn validate_input(&self) -> Result<(), Vec<String>> {
```

Validate input parameters for the Count command

# Returns
Result<(), Vec<String>> with validation errors if any

#### is_directory_mode

```rust
pub fn is_directory_mode(&self) -> bool {
```

Check if directory processing is enabled

# Returns
true if directory parameter is specified

#### get_directory

```rust
pub fn get_directory(&self) -> Option<&str> {
```

Get directory path if directory mode is enabled

# Returns
Option<&str> with the directory path

#### is_select_mode

```rust
pub fn is_select_mode(&self) -> bool {
```

Check if interactive file selection is enabled

# Returns
true if select parameter is specified

#### is_recursive

```rust
pub fn is_recursive(&self) -> bool {
```

Check if recursive directory search is enabled

# Returns
true if recursive parameter is specified

---

*Source: [`args.rs`](../../../cli/args.rs)*