# RustKmer

[![Rust](https://img.shields.io/badge/rust-1.80+-orange.svg)](https://www.rust-lang.org)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://rustkmer.github.io)

**World-class performance for k-mer counting and genomic analysis**

RustKmer is a high-performance k-mer counting library written in Rust with Python bindings. It provides exceptional speed and memory efficiency for processing large genomic datasets, delivering up to 14,772x performance improvements over traditional tools.

## ✨ Key Features

- **🚀 Blazing Fast**: Up to 14,772x faster than traditional tools (3.9M queries/sec)
- **🧪 Memory Efficient**: Minimal memory footprint with streaming processing (<2MB overhead)
- **🔍 Advanced Querying**: Support for exact and fuzzy k-mer searches with wildcards
- **🐍 Python Native**: First-class Python bindings for seamless integration
- **📱 Cross-Platform**: Works on Linux, macOS, and Windows
- **⚡ Production Ready**: Extensively tested with real-world genomic data (374M k-mers validated)

## 🚀 Quick Start

### Installation

```bash
# Rust (from crates.io)
cargo install rustkmer

# Python (from PyPI)
pip install rustkmer
```

### Basic Usage

#### Rust
```rust
use rustkmer::KmerCounter;

let mut counter = KmerCounter::new(21, true);
counter.add_from_fasta("genome.fa.gz")?;
println!("Total k-mers: {}", counter.get_stats().total_kmers));
```

#### Python
```python
from pyrustkmer import PyCounter, LoadMode

counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")
print(f"Total k-mers: {counter.get_stats().total_kmers)}")
```

### Command Line
```bash
# Count k-mers from a FASTA file
rustkmer count -k 21 -i genome.fa.gz -o genome_k21.rkdb

# Query k-mers from a database
rustkmer query -d genome_k21.rkdb -q queries.txt

# Fuzzy search with wildcards
rustkmer fuzzy-query -d genome_k21.rkdb -q "AATN" -m 1
```

## 📖 Documentation

### 📚 Getting Started
- **[Installation](installation.md)** - Installation guide for Python API
- **[Advanced Installation](getting-started/installation-advanced.md)** - Detailed installation for developers
- **[Quick Start Guide](getting-started/first-steps.md)** - Get started in 5 minutes

### 👥 User Guide
- **[User Guide](guides/user-guide.md)** - Comprehensive usage guide
- **[Querying](user-guide/querying.md)** - K-mer query operations
- **[Counting k-mers](user-guide/counting-kmers.md)** - K-mer counting guide
- **[Performance Tips](user-guide/performance-tips.md)** - Optimization guide

### 🔧 Guides
- **[PyO3 Binding Guide](guides/pyo3-binding-guide.md)** - Complete Python API guide
- **[PyO3 Quick Reference](guides/pyo3-binding-readme.md)** - Quick start for Python users
- **[Prefix Query Guide](guides/prefix-query-guide.md)** - Efficient prefix-based querying
- **[Hybrid Search Guide](guides/hybrid-search-guide.md)** - Advanced search patterns

### 🔍 API Reference
- **[API Overview](api-reference/overview.md)** - Complete API documentation
- **[Database API](api-reference/database.md)** - Database operations
- **[Query API](api-reference/query.md)** - Query operations
- **[Fuzzy Query](api-reference/fuzzyquery.md)** - Fuzzy search API
- **[Statistics](api-reference/stats.md)** - Database statistics

### 💡 Implementation & Development
- **[Algorithm Implementation](dev-guide/algorithm-implementation.md)** - Core algorithms detailed
- **[Memory Optimization](performance/memory-optimization.md)** - Performance optimization techniques
- **[CLI Design](dev-guide/cli-design.md)** - Command-line interface design
- **[Development Guidelines](dev-guide/agents.md)** - Development standards
- **[Project History](dev-guide/claude.md)** - Development timeline

### 🔧 Implementation Reports
- **[Prefix Query Report](implementation/prefix-query-report.md)** - Implementation details
- **[Bug Fixes](implementation/bug-fixes.md)** - Known issues and fixes
- **[Hybrid Search Fixes](implementation/hybrid-search-fixes.md)** - Search improvements

### 🚨 Troubleshooting
- **[CLI Status](troubleshooting/cli-status.md)** - Current command availability
- **[N-position Demo](troubleshooting/n-position-demo.md)** - Efficiency analysis
- **[Prefix Extraction Demo](troubleshooting/prefix-extraction-demo.md)** - Feature demonstration

### 📊 Performance
- **[Memory Optimization](performance/memory-optimization.md)** - Memory efficiency techniques
- **[Performance Analysis](PERFORMANCE.md)** - Benchmark results

### 📖 Examples
- **[Basic Usage](examples/basic-usage.md)** - Simple examples
- **[Fuzzy Search](examples/fuzzy-search.md)** - Wildcard examples
- **[Batch Processing](examples/batch-processing.md)** - Large-scale processing
- **[Advanced Examples](examples/advanced.md)** - Complex use cases

### 🎓 Tutorials
- **[Basic Workflow](tutorials/basic-workflow.md)** - Step-by-step tutorial
- **[Large Genomes](tutorials/large-genomes.md)** - Handling big data
- **[Integration Guide](tutorials/integration.md)** - Workflow integration

## 🏆 Performance

RustKmer delivers world-class performance validated with real genomic datasets:

| Metric | RustKmer | Traditional Tools | Improvement |
|--------|----------|------------------|-------------|
| Query Speed | 3,986,981/sec | 270/sec | **14,772x** |
| Memory Usage | <2MB | 10-100MB | **10-100x** |
| Large Files | 374M k-mers | Limited | **Significant** |
| Python Integration | Native | Unsupported | **Unique** |

*Based on benchmarks with real genomic datasets including Oryza sativa genome assembly*

## 🧬 Use Cases

### Genomic Research
- Large-scale k-mer analysis for genome assembly
- Metagenomic classification and abundance estimation
- Genome similarity and distance calculations
- K-mer-based genome sketching

### Bioinformatics Pipelines
- Integration with existing analysis workflows
- High-throughput sequencing data processing
- Real-time k-mer counting during sequencing
- Database creation for downstream analysis

### Data Science
- Machine learning feature extraction from genomic data
- Statistical analysis of k-mer distributions
- Comparative genomics studies
- Population genetics applications

## 🔬 Advanced Features

### Fuzzy Querying
```python
# Search with wildcards (N = any base)
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("genome.rkdb", LoadMode.Preload)

# Fuzzy search using PyFuzzyQuery class
fuzzy = PyFuzzyQuery(db)
results = fuzzy.query_fuzzy("ATNNGTANN", max_distance=2)

# The fuzzy search finds k-mers matching the pattern within the specified distance
for result in results:
    print(f"K-mer: {result.kmer}, Count: {result.count}, Distance: {result.distance}")
```

### Batch Processing
```python
# Process large files efficiently
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("large_genome.fa.gz")  # Streaming processing

# Get top k-mers
top_kmers = counter.get_top_kmers(1000)
```

### Memory Optimization
```python
# Memory-mapped database access for large datasets
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("huge_db.rkdb", LoadMode.MemoryMapped)  # Uses memory mapping
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](contributing.md) for details.

### Development Setup
```bash
git clone https://github.com/rustkmer/rustkmer
cd rustkmer
cargo build
cargo test
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Rust for performance and safety
- Python bindings powered by PyO3
- Inspired by the need for high-performance genomic analysis tools
- Tested with real genomic data from various research projects

---

**Ready to accelerate your genomic analysis?** [Get started now!](getting-started/)