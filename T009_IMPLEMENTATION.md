# T009: Memory Mapping Implementation for Large Database Files

## Overview

This implementation adds memory mapping functionality to the RustKmer Python API for optimized performance with large database files (>100MB). The implementation automatically detects when to use memory mapping and maintains full compatibility with the existing `DatabaseQuery` interface.

## Features

### 1. Automatic Memory Mapping Detection
- **Threshold**: 100MB file size threshold for automatic memory mapping
- **Detection**: `MemoryMappedDatabase::should_use_mmap()` checks file size
- **Fallback**: Regular `DatabaseQuery` for smaller files

### 2. Memory Mapping Wrapper (`MemoryMappedDatabase`)
- **Thread Safety**: Implements `Send + Sync` for multi-threaded access
- **Resource Management**: Uses `Arc<Mmap>` for safe shared access
- **Binary Search**: Efficient k-mer lookup using binary search on sorted databases

### 3. Enhanced SimpleDatabase Class
- **Dual Mode**: Supports both memory-mapped and regular database access
- **Transparent Switching**: Automatic mode selection based on file size
- **Manual Control**: `reload()` method for forcing specific modes

### 4. Interface Compatibility
- **Drop-in Replacement**: Existing Python code works without changes
- **Same Methods**: `query()`, `query_multiple()`, `get_stats()` maintain same signatures
- **Enhanced Stats**: Includes `uses_memory_mapping` field

## Implementation Details

### Core Components

```rust
// Memory mapping threshold (100MB)
const MMAP_THRESHOLD: u64 = 100 * 1024 * 1024;

// Thread-safe memory mapping wrapper
struct MemoryMappedDatabase {
    mmap: Arc<Mmap>,                    // Memory-mapped file data
    header: DatabaseHeader,            // Database metadata
    file_path: String,                 // File reference
}
```

### Enhanced Database Structure

```rust
pub struct SimpleDatabase {
    query: Option<DatabaseQuery>,           // Regular database access
    mmap_db: Option<Arc<MemoryMappedDatabase>>, // Memory-mapped access
    // ... other fields
    uses_mmap: bool,                        // Current mode flag
}
```

### Key Methods

#### Memory Mapping Detection
```rust
fn should_use_mmap(file_path: &str) -> Result<bool, PyErr> {
    let metadata = std::fs::metadata(file_path)?;
    Ok(metadata.len() > MMAP_THRESHOLD)
}
```

#### Binary Search in Memory-Mapped Data
```rust
fn query_kmer(&self, kmer_seq: &str) -> Result<Option<u32>, PyErr> {
    // Validate and encode k-mer
    // Binary search across memory-mapped entries
    // Direct memory access without I/O overhead
}
```

## Usage Examples

### Basic Usage (Automatic)
```python
import rustkmer

# Database automatically uses memory mapping if file >100MB
db = rustkmer.Database()
db.load("large_database.rkdb")

# Queries work the same regardless of memory mapping mode
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(result.count)
```

### Manual Control
```python
# Check if memory mapping is being used
stats = db.get_stats()
print(f"Uses memory mapping: {stats.uses_memory_mapping}")

# Force enable/disable memory mapping
db.reload(force_mmap=True)   # Force enable
db.reload(force_mmap=False)  # Force disable
db.reload()                  # Auto-detect again
```

### Batch Queries
```python
kmers = ["ATGCGATGCTAGCGCTAGCTA", "TGCGATGCTAGCGCTAGCTAG", ...]
results = db.query_multiple(kmers)

for result in results:
    print(f"{result.kmer}: {result.count}")
```

## Performance Benefits

### Memory Mapping Advantages
1. **Reduced Memory Usage**: Pages loaded on demand, not entire file
2. **OS-Level Caching**: Leverages operating system file caching
3. **Faster Random Access**: Direct memory access without system calls
4. **Better I/O Patterns**: Only accessed portions are loaded

### Benchmarks
- **Large Files**: Significant performance improvement for files >100MB
- **Random Access**: Binary search in memory-mapped data
- **Concurrent Access**: Thread-safe for multi-threaded Python applications

## Thread Safety

### Implementation
- `MemoryMappedDatabase` implements `Send + Sync`
- `Arc<Mmap>` ensures safe shared access across threads
- Read-only access prevents data races

### Python GIL Considerations
- Memory mapping operations don't block GIL
- Allows concurrent queries from multiple Python threads
- Safe for use with Python's `threading` module

## Error Handling

### Memory Mapping Errors
- File access errors → `PyIOError`
- Invalid database format → `PyValueError`
- Memory mapping failure → `PyIOError`
- Unsorted databases (not supported) → `PyNotImplementedError`

### Fallback Behavior
- Automatic fallback to regular `DatabaseQuery` on memory mapping failures
- Graceful degradation ensures application stability
- Clear error messages for debugging

## Compatibility

### Backward Compatibility
- Existing Python code requires no changes
- All existing methods maintain same signatures
- Enhanced statistics include additional `uses_memory_mapping` field

### Database Format
- Works with existing `.rkdb` database format
- Requires sorted databases for binary search
- Supports canonical and non-canonical k-mers

## Testing

### Test Coverage
- Automatic memory mapping detection
- Large file simulation
- Interface compatibility
- Thread safety
- Error handling

### Test Script
```bash
python test_memory_mapping.py
```

## Dependencies

### Required Crates
- `memmap2 = "0.9"` - Memory mapping functionality
- Existing dependencies remain unchanged

### Python Requirements
- Python 3.8+ (as specified in project requirements)
- PyO3 0.23.4+ (already configured)

## Future Enhancements

### Potential Improvements
1. **Adaptive Threshold**: Configurable memory mapping threshold
2. **Write Support**: Memory-mapped writing for database updates
3. **Compression**: On-the-fly decompression for compressed databases
4. **Caching**: LRU cache for frequently accessed k-mers
5. **Async Support**: Async query interface for high-throughput applications

### Monitoring
- Performance metrics collection
- Memory usage tracking
- Cache hit/miss statistics

## Conclusion

This T009 implementation successfully adds memory mapping capabilities to the RustKmer Python API while maintaining full compatibility with existing code. The automatic detection ensures optimal performance for large database files without requiring changes to user code, while manual control provides flexibility for advanced use cases.

The thread-safe design makes it suitable for multi-threaded applications, and the comprehensive error handling ensures robust operation in production environments.