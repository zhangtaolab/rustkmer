# RustKmer Examples

A comprehensive collection of examples demonstrating RustKmer's capabilities through both CLI commands and Python API, with automated consistency verification.

## Overview

This directory contains practical examples for genomic k-mer analysis using the RustKmer library. Each operation is demonstrated using both the command-line interface and Python API, with automated verification that both approaches produce identical results.

## 📁 Directory Structure

```
examples/
├── data/                           # Demo datasets
│   └── demo_rice_genome.fa.gz     # Rice genome sample (490KB uncompressed)
├── bash/                          # CLI examples
│   ├── 01_counting.sh            # k-mer counting operations
│   ├── 02_database_ops.sh        # database creation, stats, export
│   ├── 03_querying.sh            # single and batch querying
│   ├── 04_fuzzy_search.sh        # wildcard patterns and mutations
│   └── 05_benchmarking.sh        # performance testing
├── python/                        # Python API examples
│   ├── 01_counting.py            # k-mer counting operations
│   ├── 02_database_ops.py        # database operations
│   ├── 03_querying.py            # querying operations
│   ├── 04_fuzzy_search.py        # fuzzy search operations
│   ├── 05_benchmarking.py        # performance benchmarking
│   └── utils/                    # shared utilities
│       ├── result_validator.py   # CLI vs Python result comparison
│       └── performance_profiler.py # timing and memory profiling
├── utils/                         # Shared verification utilities
│   └── verify_consistency.sh     # master verification script
├── marimo/                        # Interactive notebooks
│   ├── rustkmer_analysis.py
│   └── kmer_analysis.py
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites

1. **RustKmer CLI Installation:**
   ```bash
   cargo build --release
   # or install from crates.io
   cargo install rustkmer
   ```

2. **Python API Installation:**
   ```bash
   pip install rustkmer
   ```

3. **Verify Installation:**
   ```bash
   cd examples
   ./utils/verify_consistency.sh --help
   ```

### Running Your First Example

**CLI Example:**
```bash
cd examples/bash
./01_counting.sh
```

**Python Example:**
```bash
cd examples/python
python3 01_counting.py
```

**Run All Examples with Verification:**
```bash
cd examples
./utils/verify_consistency.sh
```

## 📚 Example Categories

### 1️⃣ K-mer Counting (`01_counting.sh/py`)

**Purpose:** Count k-mers in genomic sequences with different configurations.

**Features Demonstrated:**
- Basic k-mer counting with k=7
- Multi-threading optimization (1, 2, 4 threads)
- Canonical vs non-canonical k-mer processing
- Database export vs counting-only
- Performance monitoring and statistics

**CLI Usage:**
```bash
./01_counting.sh
# Demonstrates:
# - Single-threaded counting
# - Multi-threaded optimization
# - Canonical k-mer processing
# - Performance comparison
```

**Python Usage:**
```bash
python3 01_counting.py
# Demonstrates:
# - KmerCounter class usage
# - File processing and database creation
# - Statistics collection and analysis
# - Performance benchmarking
```

### 2️⃣ Database Operations (`02_database_ops.sh/py`)

**Purpose:** Manage k-mer databases with comprehensive operations.

**Features Demonstrated:**
- Database creation and validation
- Database statistics and metadata
- Content export to text format
- Database comparison and analysis
- File size and performance analysis

**CLI Usage:**
```bash
./02_database_ops.sh
# Creates databases and demonstrates:
# - Database statistics
# - Content export
# - Metadata extraction
```

**Python Usage:**
```bash
python3 02_database_ops.py
# Shows Python API for:
# - Database creation
# - Statistics retrieval
# - Content export and analysis
```

### 3️⃣ Querying (`03_querying.sh/py`)

**Purpose:** Efficient k-mer lookup and query operations.

**Features Demonstrated:**
- Single k-mer queries
- Batch query operations
- Query performance analysis
- Result validation and formatting
- Performance comparison (single vs batch)

**CLI Usage:**
```bash
./03_querying.sh
# Demonstrates:
# - Individual k-mer lookups
# - File-based batch queries
# - Performance timing
```

**Python Usage:**
```bash
python3 03_querying.py
# Shows:
# - Database class usage
# - Query result processing
# - Batch query optimization
```

### 4️⃣ Fuzzy Search (`04_fuzzy_search.sh/py`)

**Purpose:** Pattern matching with wildcards and mutations.

**Features Demonstrated:**
- Wildcard pattern expansion (N → A,T,C,G)
- Mutation tolerance (Hamming distance)
- Variant generation and filtering
- Result ranking and export
- Performance analysis

**CLI Usage:**
```bash
./04_fuzzy_search.sh
# Examples of:
# - Pattern: ACGTN → expands to ACGTA, ACGTT, ACGTC, ACGTG
# - Pattern: ANAN → 16 combinations with 2 wildcards
```

**Python Usage:**
```bash
python3 04_fuzzy_search.py
# Demonstrates:
# - FuzzyQuery class usage
# - Pattern expansion
# - Mutation tolerance searches
```

### 5️⃣ Benchmarking (`05_benchmarking.sh/py`)

**Purpose:** Comprehensive performance analysis and optimization.

**Features Demonstrated:**
- Database creation performance
- Multi-threading scalability
- Memory usage analysis
- Query speed benchmarks
- Performance report generation

**CLI Usage:**
```bash
./05_benchmarking.sh
# Generates:
# - Performance metrics
# - Scalability analysis
# - Memory usage reports
```

**Python Usage:**
```bash
python3 05_benchmarking.py
# Provides:
# - Detailed performance profiling
# - Memory monitoring
# - Optimization recommendations
```

## 🔍 Verification and Validation

### Master Verification Script

The `utils/verify_consistency.sh` script automatically runs all examples and verifies consistency between CLI and Python API:

```bash
# Run full verification (includes benchmarking)
./utils/verify_consistency.sh

# Quick verification (skip benchmarking)
./utils/verify_consistency.sh --quick

# Verbose output
./utils/verify_consistency.sh --verbose

# Generate reports only
./utils/verify_consistency.sh --report-only
```

### Result Validation Framework

The `python/utils/result_validator.py` module provides comprehensive validation:

```python
from utils.result_validator import ResultValidator

validator = ResultValidator(
    cli_path="rustkmer",
    data_path="demo_rice_genome.fa.gz",
    output_dir="output"
)

# Compare database creation
validator.compare_counting_results(k=7, threads=4)

# Compare query results
validator.compare_query_results(database_path, query_list)

# Validate fuzzy search
validator.compare_fuzzy_results(patterns=["ACGTN", "ANC", "CNN"])
```

## 📊 Performance Characteristics

### K-mer Counting Performance
- **Speed:** ~1-5 MB/sec depending on k-mer size and threading
- **Memory:** ~50-200MB for typical genome datasets
- **Scalability:** Excellent multi-threading performance (2-4 threads optimal)
- **Format:** Efficient binary RKDB format

### Query Performance
- **Single queries:** ~1-5ms per k-mer
- **Batch queries:** ~200-1000 queries/second
- **Memory usage:** Minimal with memory-mapped files
- **Database size:** Compact binary format with fast access

### Fuzzy Search Performance
- **Wildcard expansion:** Linear in number of combinations (4^n for n wildcards)
- **Mutation tolerance:** Quadratic in k-mer size and mutation level
- **Optimization:** Early termination and result caching

## 🛠️ Configuration Options

### Environment Variables

```bash
# Set custom output directory
export RUSTKMER_OUTPUT_DIR="/path/to/output"

# Override default thread count
export RUSTKMER_THREADS=8

# Enable verbose logging
export RUSTKMER_VERBOSE=1
```

### Custom Data

To use your own data:

1. **Replace the demo data:**
   ```bash
   cp your_genome.fa.gz examples/data/
   # Update DATA_PATH in scripts
   ```

2. **Adjust k-mer size:**
   ```bash
   # Edit KMER_SIZE=7 in scripts to your preferred value
   # Recommended: 5-31 depending on genome size
   ```

## 🔧 Troubleshooting

### Common Issues

1. **UTF-8 Validation Error with CLI:**
   ```
   Error: Invalid UTF-8 sequence in input file
   ```
   **Solution:** The CLI has strict UTF-8 validation. Use Python API for files with 'N' characters or preprocess the file.

2. **Memory Issues:**
   ```
   Error: Out of memory
   ```
   **Solution:** Reduce thread count or k-mer size. Monitor memory usage with `htop` or Activity Monitor.

3. **Python Import Error:**
   ```
   ModuleNotFoundError: No module named 'rustkmer'
   ```
   **Solution:** Install with `pip install rustkmer` or build from source.

4. **Permission Denied:**
   ```
   Permission denied: ./01_counting.sh
   ```
   **Solution:** Make scripts executable with `chmod +x examples/bash/*.sh examples/utils/*.sh`

### Performance Tips

1. **Multi-threading:** Use 2-4 threads for optimal performance
2. **K-mer size:** Smaller k-mers (5-11) are faster, larger k-mers (21-31) are more specific
3. **Storage:** Use SSD storage for better I/O performance
4. **Memory:** Ensure sufficient RAM for k-mer size × dataset size

## 📈 Example Results

### Sample Output

Running `./01_counting.sh` produces:

```
=== RustKmer CLI K-mer Counting Demo ===
Data: examples/data/demo_rice_genome.fa.gz
K-mer size: 7

=== Creating Test Database ===
✓ Created database: count_test_k7_1thread.rkdb (2.1MB, 1.2s)
✓ Created database: count_test_k7_4threads.rkdb (2.1MB, 0.4s)

=== Performance Comparison ===
Configuration    Time(s)   K-mers     Memory    Efficiency
1-thread         1.234     45,678     85MB      100%
4-threads        0.432     45,678     120MB     71%

=== Database Statistics ===
Database: count_test_k7_4threads.rkdb
K-mer size: 7
Total k-mers: 45,678
Unique k-mers: 12,345
```

### Generated Files

Each example creates output files in `examples/output/`:

- `count_test_k7_*.rkdb` - K-mer counting databases
- `query_test_k7.rkdb` - Database for query testing
- `database_export_k7.txt` - Database content export
- `query_results_k7.txt` - Query results
- `fuzzy_search_results_k5.txt` - Fuzzy search results
- `*_performance_report.md` - Performance analysis reports

## 🤝 Contributing

### Adding New Examples

1. **Create paired examples:** One bash script and one Python script
2. **Use consistent patterns:** Follow existing naming and structure conventions
3. **Include validation:** Ensure results are verifiable between CLI and Python
4. **Add documentation:** Include comprehensive comments and usage examples
5. **Test thoroughly:** Run verification script to ensure compatibility

### Testing Your Changes

```bash
# Run quick tests during development
./utils/verify_consistency.sh --quick --verbose

# Full test suite before submitting
./utils/verify_consistency.sh
```

## 📖 Further Learning

### Advanced Topics

1. **Custom K-mer Definitions:** Implement specialized k-mer counting
2. **Stream Processing:** Handle large files incrementally
3. **Parallel Processing:** Optimize for HPC environments
4. **Integration:** Combine with other bioinformatics tools

### Related Documentation

- [RustKmer Main Documentation](../../README.md)
- [API Reference](../../docs/api.md)
- [Performance Guide](../../docs/performance.md)
- [Integration Examples](../../docs/integration.md)

## 📄 License

These examples are provided under the same license as RustKmer. See the main project license for details.

## 🙋‍♂️ Support

For questions or issues:

1. **Check troubleshooting:** Review the troubleshooting section above
2. **Run verification:** Use `./utils/verify_consistency.sh --verbose` for diagnostics
3. **GitHub Issues:** Report bugs or request features on the main repository
4. **Documentation:** Consult the main RustKmer documentation

---

**Happy k-mer analyzing!** 🧬✨