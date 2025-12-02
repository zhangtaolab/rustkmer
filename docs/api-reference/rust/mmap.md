# Mmap

**Module**: `rustkmer::io::mmap`

## Overview

Memory-mapped file operations
Provides memory-mapped file reading for large genomic datasets.

## API Reference

### Fns

#### as_slice

```rust
pub fn as_slice(&self) -> &[u8] {
```

Get a slice of the memory-mapped data

# Returns
Slice of the file contents

#### len

```rust
pub fn len(&self) -> usize {
```

Get length of the mapped file

# Returns
File length in bytes

#### is_empty

```rust
pub fn is_empty(&self) -> bool {
```

Check if the file is empty

# Returns
True if file is empty

#### lines

```rust
pub fn lines(&self) -> impl Iterator<Item = &[u8]> + '_ {
```

Get an iterator over lines in the file

# Returns
Iterator over line slices

#### read_to_string

```rust
pub fn read_to_string(&self) -> Result<String, std::string::FromUtf8Error> {
```

Read file into a String (for smaller files)

# Returns
String containing file contents

---

*Source: [`mmap.rs`](../../../io/mmap.rs)*