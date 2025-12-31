# Quick Start: PyO3 Fuzzy Query

Get up and running with PyO3 fuzzy query functionality for rustkmer in minutes.

## Prerequisites

- Python 3.10+
- Rust toolchain (1.80+)
- rustkmer database (.rkdb file)
- PyO3 development environment

## Installation

### 1. Build PyO3 Extension

```bash
# Navigate to PyO3 directory
cd pyo3

# Set Python environment (adjust path as needed)
export PYO3_PYTHON=$(which python3)
export PYTHON_SYS_EXECUTABLE=$(which python3)

# Build in development mode
cargo build

# Or build in release mode (requires Python dev headers)
cargo build --release
```

### 2. Install Python Package

```bash
# From project root
pip install -e .
```

## Basic Usage

### Load Database Once

```python
from rustkmer_pyo3 import PyDatabase, PyFuzzyQuery, LoadMode

# Load database - this happens once
db = PyDatabase("my_genome.rkdb", LoadMode.Preload)
print(f"Database loaded: {db.kmer_size}-mers")
```

### N-Wildcard Queries

```python
# Create fuzzy query engine (shares the same database)
fuzzy = PyFuzzyQuery(db)

# Query with N wildcards
pattern = "GANNNGA"  # G + A + 3 N's + G + A
result = fuzzy.fuzzy_query(pattern, max_mutations=0)

print(f"Pattern: {pattern}")
print(f"Found {result.total_matches} matches")
print(f"Mutation tolerance: {result.mutation_tolerance}")

# Show first few matches
for match in result.matches[:5]:
    print(f"  {match.kmer}: {match.count} (distance={match.distance})")
```

### Mutation Tolerance

```python
# Allow mutations alongside wildcards
result = fuzzy.fuzzy_query("GANNNGA", max_mutations=1)

print(f"With 1 mutation tolerance: {result.total_matches} matches")

# Analyze by distance
for distance in range(result.mutation_tolerance + 1):
    matches_at_distance = result.get_matches_by_distance(distance)
    print(f"  Distance {distance}: {len(matches_at_distance)} matches")
```

### Position-Specific Mutations

```python
# Configure position-specific constraints
fuzzy.set_position_mutations("2,3,4:1")  # Positions 2,3,4 allow max 1 mutation total

pattern = "GATCGATCGATCG"
result = fuzzy.fuzzy_query(pattern, max_mutations=3)

print(f"Pattern: {pattern}")
print(f"Position-constrained query: {result.total_matches} matches")
```

## Common Patterns

### Performance Comparison

```python
import time
from rustkmer import Database  # Subprocess version for comparison

# PyO3 version
start = time.time()
db_pyo3 = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy_pyo3 = PyFuzzyQuery(db_pyo3)
result_pyo3 = fuzzy_pyo3.fuzzy_query("GANNNNNNNNGA", max_mutations=1)
pyo3_time = time.time() - start

# Subprocess version
start = time.time()
db_subprocess = Database("genome.rkdb")
result_subprocess = db_subprocess.fuzzy_query("GANNNNNNNNGA", mutations=1)
subprocess_time = time.time() - start

print(f"PyO3: {pyo3_time:.3f}s")
print(f"Subprocess: {subprocess_time:.3f}s")
print(f"Speedup: {subprocess_time/pyo3_time:.1f}x")
```

### Batch Processing

```python
# Process multiple patterns efficiently
patterns = [
    "GANNNGA",
    "ATCNNNCT", 
    "GCTNNNGA",
    "ATANNNTA"
]

results = []
for pattern in patterns:
    result = fuzzy.fuzzy_query(pattern, max_mutations=1)
    results.append((pattern, result))

# Analyze results
for pattern, result in results:
    print(f"{pattern}: {result.total_matches} matches")
```

### Top Results Analysis

```python
# Get most frequent matches
result = fuzzy.fuzzy_query("GANNNGA", max_mutations=2)

# Top 10 by count
top_matches = result.get_top_matches(10)
print("Top 10 most frequent matches:")
for i, match in enumerate(top_matches, 1):
    print(f"  {i}. {match.kmer}: {match.count} (distance={match.distance})")

# Filter by exact matches
exact_matches = result.get_matches_by_distance(0)
if exact_matches:
    print(f"Exact matches: {len(exact_matches)}")
    for match in exact_matches:
        print(f"  {match.kmer}: {match.count}")
```

## Troubleshooting

### Build Issues

**Problem**: Python linking errors in release mode
```bash
# Solution: Install Python development headers
# Ubuntu/Debian:
sudo apt-get install python3-dev

# macOS:
brew install python@3.11

# Then rebuild:
export PYO3_PYTHON=$(which python3)
cargo build --release
```

**Problem**: PyO3 module not found
```python
# Check if module loads
try:
    from rustkmer_pyo3 import PyDatabase, PyFuzzyQuery
    print("PyO3 module loaded successfully")
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the extension is built and installed")
```

### Runtime Issues

**Problem**: Database loading fails
```python
# Check database file exists and is readable
from pathlib import Path
db_path = "my_genome.rkdb"
if not Path(db_path).exists():
    print(f"Database file not found: {db_path}")
if not Path(db_path).is_file():
    print(f"Path is not a file: {db_path}")
```

**Problem**: Invalid pattern errors
```python
# Valid patterns: A, T, C, G, N only
# Valid lengths: Must match database k-mer size

try:
    result = fuzzy.fuzzy_query("INVALID_PATTERN", max_mutations=1)
except Exception as e:
    print(f"Pattern error: {e}")
    # Fix pattern and retry
```

**Problem**: Memory issues with large wildcards
```python
# Large numbers of N's can cause memory issues
# Solution: Use position mutations or reduce wildcards

# Instead of:
result = fuzzy.fuzzy_query("NNNNNNNNNN", max_mutations=0)  # 4^10 = 1M variants

# Use:
fuzzy.set_position_mutations("2,3,4:1")  # Constrain mutations
result = fuzzy.fuzzy_query("GNNNNNNNNNG", max_mutations=3)
```

## Performance Tips

### 1. Database Loading Strategy

```python
# Preload mode: Fastest queries, higher memory usage
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# Memory-mapped mode: Balanced memory/performance  
db = PyDatabase("genome.rkdb", LoadMode.MemoryMapped)

# Lazy mode: Lowest memory, slower queries
db = PyDatabase("genome.rkdb", LoadMode.Lazy)
```

### 2. Efficient Wildcard Usage

```python
# Limit wildcard expansion
result = fuzzy.fuzzy_query("GANNNGA", max_mutations=1, max_results=1000)

# Use position mutations for targeted searches
fuzzy.set_position_mutations("4:1;8:1")  # Only specific positions mutable
```

### 3. Result Processing

```python
# Process results efficiently
result = fuzzy.fuzzy_query("GANNNGA", max_mutations=2)

# Don't load all results if you only need counts
exact_count = len(result.get_matches_by_distance(0))

# Get top results without processing all matches
top_5 = result.get_top_matches(5)
```

## Examples Repository

See the complete demo script for more examples:

```bash
python demo_pyo3_fuzzy_query.py
```

This script demonstrates:
- N-wildcard pattern matching
- Mutation tolerance
- Position-specific mutations  
- Performance comparisons
- Error handling
- Real-world use cases

## Next Steps

1. **Explore Advanced Features**: Position mutations, batch processing
2. **Performance Optimization**: Choose appropriate database loading mode
3. **Integration**: Incorporate into existing bioinformatics workflows
4. **Scaling**: Handle large databases and complex patterns efficiently

For detailed API documentation, see [python-api.md](contracts/python-api.md).