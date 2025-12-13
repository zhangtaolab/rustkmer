# Research Report: Python Binding API for rustkmer

**Feature**: 001-python-binding
**Date**: 2025-01-13
**Purpose**: Research findings to resolve technical unknowns for implementation planning

## Research Topics

### 1. Subprocess Parallel Processing Strategy

**Question**: How can we efficiently handle parallel processing when using subprocess calls to CLI?

**Decision**: Implement thread pool for subprocess calls with controlled concurrency

**Rationale**:
- Python's subprocess module can be used with ThreadPoolExecutor for parallel CLI calls
- Each subprocess call is independent (different k-mers or database operations)
- Controlled concurrency prevents system overload
- asyncio + subprocess can also be considered for I/O-bound operations

**Implementation Approach**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

def parallel_query(database_path, kmer_list, max_workers=4):
    """Execute multiple queries in parallel using thread pool"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                subprocess.run,
                ['rustkmer', 'query', database_path, kmer],
                capture_output=True,
                text=True
            ): kmer
            for kmer in kmer_list
        }

        results = {}
        for future in as_completed(futures):
            kmer = futures[future]
            try:
                result = future.result()
                results[kmer] = parse_query_output(result.stdout)
            except Exception as e:
                results[kmer] = {'error': str(e)}

        return results
```

**Alternatives Considered**:
- multiprocessing.Pool: Heavier weight, better for CPU-bound tasks
- asyncio with subprocess: Better for I/O-bound, more complex implementation
- Sequential calls: Simpler but slower for batch operations

**Best Practices**:
- Limit concurrent processes to avoid system overload
- Use timeouts to prevent hanging
- Implement proper error handling and retry logic
- Consider memory usage for large batch operations

### 2. CLI Output Parsing Strategies

**Question**: What's the best approach to parse CLI output reliably?

**Decision**: Use structured output modes (JSON/TSV) when available, fallback to regex parsing

**Rationale**:
- JSON output is most reliable for parsing
- TSV is simple and efficient for tabular data
- Regex parsing should be last resort due to brittleness

**Implementation**:
```python
import json
import re

def parse_query_output(output, format='auto'):
    """Parse rustkmer query output"""
    if format == 'json' or (format == 'auto' and output.strip().startswith('{')):
        return json.loads(output)
    elif format == 'tsv' or '\t' in output:
        return parse_tsv(output)
    else:
        return parse_human_readable(output)

def parse_tsv(output):
    """Parse tab-separated values"""
    lines = output.strip().split('\n')
    if len(lines) >= 2:
        headers = lines[0].split('\t')
        values = lines[1].split('\t')
        return dict(zip(headers, values))
    return {}
```

### 3. Python Package Distribution Strategy

**Question**: How to distribute the Python package without requiring Rust compilation?

**Decision**: Include pre-compiled rustkmer binary as package data

**Rationale**:
- Users can install with pip without Rust toolchain
- Binary distribution ensures consistent performance
- Platform-specific wheels can include appropriate binaries

**Package Structure**:
```
python/
├── rustkmer/
│   ├── __init__.py
│   ├── database.py
│   └── bin/
│       ├── rustkmer-linux
│       ├── rustkmer-macos
│       └── rustkmer-windows.exe
├── pyproject.toml
└── README.md
```

### 4. Error Handling Patterns

**Decision**: Map subprocess errors to appropriate Python exceptions

**Implementation**:
```python
import subprocess
from pathlib import Path

class RustKmerError(Exception):
    """Base exception for rustkmer errors"""
    pass

class DatabaseNotFoundError(RustKmerError, FileNotFoundError):
    """Raised when database file doesn't exist"""
    pass

class InvalidKmerError(RustKmerError, ValueError):
    """Raised when k-mer sequence is invalid"""
    pass

def handle_subprocess_error(result, database_path, kmer=None):
    """Convert subprocess errors to Python exceptions"""
    if result.returncode != 0:
        error_msg = result.stderr.strip()

        if "No such file" in error_msg:
            raise DatabaseNotFoundError(f"Database not found: {database_path}")
        elif "Invalid k-mer" in error_msg:
            raise InvalidKmerError(f"Invalid k-mer: {kmer}")
        else:
            raise RustKmerError(f"rustkmer error: {error_msg}")
```

## Summary of Findings

1. **Parallel Processing**: Use ThreadPoolExecutor with controlled concurrency
2. **Output Parsing**: Prefer structured formats (JSON/TSV), implement robust fallbacks
3. **Distribution**: Package pre-compiled binaries for cross-platform compatibility
4. **Error Handling**: Map subprocess errors to meaningful Python exceptions

All technical unknowns have been resolved. The implementation can proceed with these researched approaches.