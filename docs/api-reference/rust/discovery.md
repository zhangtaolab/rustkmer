# Discovery

**Module**: `rustkmer::io::discovery`

## Overview

File discovery and directory traversal for RustKmer
This module provides functionality for discovering sequence files in directories,
with support for recursive traversal, file type filtering, and metadata collection.

## API Reference

### Fns

#### from_extension

```rust
pub fn from_extension(ext: &str) -> Option<Self> {
```

Get file type from file extension

#### extensions

```rust
pub fn extensions(self) -> &'static [&'static str] {
```

Get supported extensions for this file type

#### from_entry

```rust
pub fn from_entry(entry: &DirEntry) -> Result<Self, KmerError> {
```

Create file info from a directory entry

#### display_name

```rust
pub fn display_name(&self) -> String {
```

Get display name (file name with size)

### Structs

#### FileDiscovery

```rust
pub struct FileDiscovery {
```

File discovery engine

### Fns

#### new

```rust
pub fn new(config: DiscoveryConfig) -> Self {
```

Create new file discovery instance

#### discover

```rust
pub fn discover(&self, directory: &Path) -> Result<Vec<FileInfo>, KmerError> {
```

Discover files in a directory

#### get_summary

```rust
pub fn get_summary(&self, files: &[FileInfo]) -> FileSummary {
```

Get summary statistics for discovered files

---

*Source: [`discovery.rs`](../../../io/discovery.rs)*