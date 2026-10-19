# Fastq

**Module**: `rustkmer::io::fastq`

## Overview

FASTQ file parsing using the bio crate
Provides efficient FASTQ file reading and processing capabilities with transparent compression support.

## API Reference

### Fns

#### from_path

```rust
pub fn from_path(path: &Path) -> Self {
```

Detect compression type from file extension

#### name

```rust
pub fn name(&self) -> &'static str {
```

Get the compression format name

### Traits

#### CompressedFileReader

```rust
pub trait CompressedFileReader {
```

Trait for compressed file reading

### Fns

#### open_compressed

```rust
fn open_compressed(path: &Path) -> ProcessingResult<(Box<dyn io::BufRead>, CompressionType)>;
```

Open a file with transparent compression detection

### Structs

#### FastqProcessor

```rust
pub struct FastqProcessor {
```

FASTQ file processor for efficient genomic data reading with compression support

### Fns

#### compression_type

```rust
pub fn compression_type(&self) -> CompressionType {
```

Get the compression type

#### is_compressed

```rust
pub fn is_compressed(&self) -> bool {
```

Check if the file is compressed

#### read_all

```rust
pub fn read_all(&self) -> ProcessingResult<Vec<Record>> {
```

Read all sequences from a FASTQ file

# Returns
Vector of sequence records

#### file_path

```rust
pub fn file_path(&self) -> &str {
```

Get the file path

#### file_exists

```rust
pub fn file_exists(&self) -> bool {
```

Check if file exists and is accessible

#### file_size

```rust
pub fn file_size(&self) -> ProcessingResult<u64> {
```

Get file size

#### filter_by_quality

```rust
pub fn filter_by_quality(&self, min_quality_ascii: u8) -> ProcessingResult<Vec<Record>> {
```

Filter records based on a minimum raw quality byte value

The comparison is against the RAW Phred+33 ASCII byte value of each
quality character, not the decoded Phred score: pass a threshold in
the raw ASCII range (for Phred+33 data every real quality byte is at
least 33, e.g. ASCII 55 corresponds to Q20). Passing a decoded Phred
score instead would silently keep every record.

# Arguments
* `min_quality_ascii` - Minimum raw Phred+33 ASCII quality byte value
  (worked example: 55 corresponds to Q20)

# Returns
Vector of records meeting quality threshold

---

*Source: [`fastq.rs`](../../../src/io/fastq.rs)*