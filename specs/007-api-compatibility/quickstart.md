# RustKmer Python API Compatibility Quick Start

**Generated**: 2025-12-02
**Purpose**: Quick guide for implementing unified RKDB database format compatibility

## Overview

This quick start guide provides step-by-step instructions for implementing unified .rkdb database format compatibility between RustKmer CLI and Python API, ensuring complete interoperability.

## Prerequisites

### System Requirements
- Rust 1.80+ stable channel
- Python 3.8+
- PyO3 0.23.4
- Git access to RustKmer repository

### Development Environment Setup
```bash
# Clone repository and switch to feature branch
git clone https://github.com/your-org/rustkmer.git
cd rustkmer
git checkout 007-api-compatibility

# Build Rust components
cargo build --release

# Install Python bindings
pip install maturin
maturin develop --release

# Verify installation
rustkmer --version
python -c "import rustkmer; print('Python API available')"
```

## Key Implementation Steps

### 1. Understand RKDB Format Structure

**Critical**: The Python API must use the exact same RKDB binary format as the CLI.

**Header Structure (42 bytes)**:
```
Offset  Size    Field        Value
0      4       magic        "RKDB"
4      2       version      1
6      1       kmer_size    k (1-127)
7      1       padding      0
8      2       padding      0
10     8       total_kmers  N
18     1       flags        bit flags
19     7       padding      0
26     8       data_offset  42
34     8       index_offset 0
```

**K-mer Entry (12 bytes)**:
```
Offset  Size    Field        Description
0      8       kmer         64-bit packed k-mer
8      4       count        32-bit count
```

### 2. Modify Python API save_to_database()

**File**: `src/python/kmer_counter.rs`

**Key Changes**:
```rust
// Replace directory creation with single .rkdb file
impl PyKmerCounter {
    pub fn save_to_database(&self, path: &str) -> PyResult<()> {
        // Validate path has .rkdb extension
        if !path.ends_with(".rkdb") {
            return Err(PyValueError::new_err("Database path must end with .rkdb"));
        }

        // Create database header
        let header = DatabaseHeader {
            magic: *b"RKDB",
            version: 1,
            kmer_size: self.k as u8,
            total_kmers: self.kmer_counts.len() as u64,
            flags: if self.canonical { 2 } else { 0 }, // canonical flag
            data_offset: 42,
            index_offset: 0,
        };

        // Write using CLI format
        let mut file = std::fs::File::create(path)
            .map_err(|e| PyIOError::new_err(format!("Failed to create database: {}", e)))?;

        header.write_to(&mut file)
            .map_err(|e| PyValueError::new_err(format!("Failed to write header: {}", e)))?;

        // Write k-mer entries
        for (kmer_str, count) in &self.kmer_counts {
            let kmer_bytes = encode_kmer(kmer_str, self.k)
                .map_err(|e| PyValueError::new_err(format!("Invalid k-mer {}: {}", kmer_str, e)))?;

            let entry = KmerEntry { kmer: kmer_bytes, count: *count as u32 };
            entry.write_to(&mut file)
                .map_err(|e| PyValueError::new_err(format!("Failed to write entry: {}", e)))?;
        }

        Ok(())
    }
}
```

### 3. Update Python API Database Class

**File**: `src/python/database.rs`

**Key Changes**:
```rust
#[pyclass]
pub struct PyRKDatabase {
    file_path: String,
    header: DatabaseHeader,
    mmap: Option<std::sync::Arc<MmapWrapper>>,
}

#[pymethods]
impl PyRKDatabase {
    #[new]
    fn new(file_path: String) -> PyResult<Self> {
        // Validate file extension
        if !file_path.ends_with(".rkdb") {
            return Err(PyValueError::new_err("Database file must end with .rkdb"));
        }

        // Open and read header
        let mut file = std::fs::File::open(&file_path)
            .map_err(|e| PyIOError::new_err(format!("Failed to open database: {}", e)))?;

        let header = DatabaseHeader::read_from(&mut std::io::BufReader::new(file))
            .map_err(|e| PyValueError::new_err(format!("Failed to read header: {}", e)))?;

        // Validate header
        header.validate()
            .map_err(|e| PyValueError::new_err(format!("Invalid database: {}", e)))?;

        // Use memory mapping for large files
        let mmap = if std::fs::metadata(&file_path)?.len() > 100_000_000 {
            Some(std::sync::Arc::new(MmapWrapper::new(&file_path)
                .map_err(|e| PyIOError::new_err(format!("Failed to create memory map: {}", e)))?))
        } else {
            None
        };

        Ok(PyRKDatabase {
            file_path,
            header,
            mmap,
        })
    }

    fn query(&self, kmer: &str) -> PyResult<u64> {
        // Validate k-mer length
        if kmer.len() != self.header.kmer_size as usize {
            return Err(PyValueError::new_err(format!(
                "K-mer length {} doesn't match database k-mer size {}",
                kmer.len(), self.header.kmer_size
            )));
        }

        // Encode k-mer
        let kmer_encoded = encode_kmer(kmer, self.header.kmer_size as usize)
            .map_err(|e| PyValueError::new_err(format!("Invalid k-mer: {}", e)))?;

        // Search using same algorithm as CLI
        if let Some(mmap_ref) = &self.mmap {
            self.query_with_mmap(mmap_ref, kmer_encoded)
        } else {
            self.query_with_file(&self.file_path, kmer_encoded)
        }
    }
}
```

### 4. Implement Essential Helper Functions

**File**: `src/python/helpers.rs`

```rust
// K-mer encoding (same as CLI)
pub fn encode_kmer(kmer: &str, k: usize) -> PyResult<u64> {
    if kmer.len() != k {
        return Err(PyValueError::new_err(format!("K-mer length mismatch")));
    }

    let mut encoded = 0u64;
    for (i, base) in kmer.chars().enumerate() {
        let bits = match base.to_ascii_uppercase() {
            'A' => 0b00,
            'C' => 0b01,
            'G' => 0b10,
            'T' => 0b11,
            _ => return Err(PyValueError::new_err(format!("Invalid DNA base: {}", base))),
        };
        encoded |= (bits as u64) << (2 * (k - 1 - i));
    }

    Ok(encoded)
}

// Memory mapping wrapper
pub struct MmapWrapper {
    _file: std::fs::File,
    mmap: memmap2::Mmap,
}

impl MmapWrapper {
    pub fn new(file_path: &str) -> std::io::Result<Self> {
        let file = std::fs::File::open(file_path)?;
        let mmap = unsafe { memmap2::MmapOptions::new().map(&file)? };
        Ok(Self { _file: file, mmap })
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.mmap
    }
}
```

## Testing Implementation

### 1. Compatibility Test Script

**Create**: `tests/test_compatibility.rs`

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;
    use tempfile::TempDir;

    #[test]
    fn test_database_format_compatibility() {
        let temp_dir = TempDir::new().unwrap();
        let fasta_path = temp_dir.path().join("test.fa");
        let cli_db = temp_dir.path().join("test_cli.rkdb");
        let py_db = temp_dir.path().join("test_py.rkdb");

        // Create test FASTA file
        std::fs::write(&fasta_path, ">test\nACGTACGTACGTACGT\nTGCATGCATGCATGC\n").unwrap();

        // Create database with CLI
        let status = Command::new("target/release/rustkmer")
            .args(&["count", "-k", "7", "-i", fasta_path.to_str().unwrap(), "-o", cli_db.to_str().unwrap()])
            .status()
            .expect("Failed to run CLI count command");
        assert!(status.success());

        // Create database with Python API
        let py_code = format!(
            r#"
import rustkmer

counter = rustkmer.KmerCounter(k=7, canonical=False)
counter.count_file("{}")
counter.save_to_database("{}")
"#,
            fasta_path.display(),
            py_db.display()
        );
        let status = Command::new("python")
            .arg("-c")
            .arg(&py_code)
            .status()
            .expect("Failed to run Python code");
        assert!(status.success());

        // Compare file sizes (should be identical)
        let cli_size = std::fs::metadata(&cli_db).unwrap().len();
        let py_size = std::fs::metadata(&py_db).unwrap().len();
        assert_eq!(cli_size, py_size, "Database files must have identical size");

        // Compare binary content
        let cli_content = std::fs::read(&cli_db).unwrap();
        let py_content = std::fs::read(&py_db).unwrap();
        assert_eq!(cli_content, py_content, "Database content must be identical");
    }

    #[test]
    fn test_cross_platform_querying() {
        let temp_dir = TempDir::new().unwrap();
        let fasta_path = temp_dir.path().join("test.fa");
        let db_path = temp_dir.path().join("test.rkdb");

        // Create test database with CLI
        std::fs::write(&fasta_path, ">test\nACGTACGTACGTACGT\n").unwrap();
        let status = Command::new("target/release/rustkmer")
            .args(&["count", "-k", "7", "-i", fasta_path.to_str().unwrap(), "-o", db_path.to_str().unwrap()])
            .status()
            .unwrap();

        // Query with CLI
        let cli_output = Command::new("target/release/rustkmer")
            .args(&["query", db_path.to_str().unwrap(), "ACGTACG"])
            .output()
            .expect("Failed to run CLI query");
        let cli_count: u32 = String::from_utf8_lossy(&cli_output.stdout)
            .trim()
            .split('\t')
            .nth(1)
            .unwrap()
            .parse()
            .unwrap();

        // Query with Python API
        let py_code = format!(
            r#"
import rustkmer

db = rustkmer.Database("{}")
result = db.query("ACGTACG")
if result.found:
    count = result.count
else:
    count = 0
print(count)
"#,
            db_path.display()
        );
        let py_output = Command::new("python")
            .arg("-c")
            .arg(&py_code)
            .output()
            .expect("Failed to run Python query");
        let py_count: u32 = String::from_utf8_lossy(&py_output.stdout)
            .trim()
            .parse()
            .unwrap();

        assert_eq!(cli_count, py_count, "Query results must be identical");
    }
}
```

### 2. Run Tests

```bash
# Run Rust tests
cargo test --test compatibility

# Run Python tests
python -m pytest tests/python/test_compatibility.py

# Run full compatibility test suite
./scripts/test_compatibility.sh
```

## Verification Checklist

### Phase 1: Database Format Compatibility
- [ ] Python API creates .rkdb files (not directories)
- [ ] Binary header matches CLI format exactly
- [ ] K-mer encoding matches CLI algorithm
- [ ] File byte-for-byte identical for same input

### Phase 2: Query Compatibility
- [ ] CLI can query Python-generated databases
- [ ] Python API can query CLI-generated databases
- [ ] Query results are 100% identical
- [ ] Performance overhead <10%

### Phase 3: Feature Parity
- [ ] All CLI features available in Python API
- [ ] Error handling matches CLI behavior
- [ ] Parameter interfaces consistent
- [ ] Documentation and examples updated

## Common Issues and Solutions

### Issue: "Invalid UTF-8 sequence" Error with CLI
**Solution**: Python API should handle N characters gracefully, while CLI has stricter validation.

### Issue: Database Size Differences
**Solution**: Ensure both use identical padding and byte ordering in header and entries.

### Issue: Performance Overhead >10%
**Solution**: Use memory mapping and GIL release for intensive operations.

## Next Steps

1. **Implement Changes**: Apply the code modifications outlined above
2. **Run Tests**: Execute the compatibility test suite
3. **Validate Results**: Ensure all tests pass with <10% overhead
4. **Update Documentation**: Update API documentation and examples
5. **Deploy**: Merge changes and release new version

This quick start provides the essential steps needed to implement unified RKDB database format compatibility while ensuring complete interoperability between RustKmer CLI and Python API.