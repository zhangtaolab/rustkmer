# Metadata

**Module**: `rustkmer::core::metadata`

## Overview

Database metadata management for JSON serialization and persistence

## API Reference

### Fns

#### new

```rust
pub fn new(kmer_size: usize, canonical: bool) -> Self {
```

Create new database metadata with default values

#### update_timestamp

```rust
pub fn update_timestamp(&mut self) {
```

Update the modification timestamp

#### add_source_file

```rust
pub fn add_source_file(&mut self, file_path: &str) {
```

Add a source file

#### set_performance_stats

```rust
pub fn set_performance_stats(&mut self, stats: PerformanceStats) {
```

Set performance statistics

#### add_custom_metadata

```rust
pub fn add_custom_metadata(&mut self, key: String, value: serde_json::Value) {
```

Add custom metadata

#### validate

```rust
pub fn validate(&self) -> Result<(), MetadataError> {
```

Validate the metadata structure

#### generate_checksum

```rust
pub fn generate_checksum(&self) -> Result<String, MetadataError> {
```

Generate checksum for the metadata

#### get_metadata_path

```rust
pub fn get_metadata_path(database_dir: &Path) -> PathBuf {
```

Get metadata file path for a database directory

---

*Source: [`metadata.rs`](../../../core/metadata.rs)*