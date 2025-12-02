# RustKmer Python Bindings

High-performance k-mer counting, database queries, and fuzzy search for genomic data analysis - now available in Python!

## 🚀 Installation

### From PyPI (Recommended)

```bash
pip install rustkmer
```

### From Source

```bash
git clone https://github.com/yourusername/rustkmer.git
cd rustkmer
pip install .
```

## 🔧 Quick Start

```python
import rustkmer
from rustkmer import KmerCounter, Database, FuzzyQuery

# Create k-mer counter
counter = KmerCounter(k=21, canonical=True)

# Create database
db = Database(k=21)
db.insert("ATGCGATGCTAGCGCTAGCTA", 42)
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Count: {result}")

# Fuzzy search
fq = FuzzyQuery(k=21, max_distance=1)
fuzzy_result = fq.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Fuzzy matches: {fuzzy_result.get_match_count()}")
```

## 📚 Features

- **High Performance**: Rust-powered backend for maximum speed
- **Memory Efficient**: Optimized data structures and algorithms
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Python 3.8+**: Support for all modern Python versions

### Core Classes

- `KmerCounter`: Count k-mers in sequences
- `Database`: Store and query k-mer databases
- `FuzzyQuery`: Search for similar k-mers with mismatches

## 🐍 API Reference

### KmerCounter

```python
counter = KmerCounter(k=21, canonical=False, threads=None)
```

**Parameters:**
- `k`: k-mer size (default: 21)
- `canonical`: Use canonical k-mers (default: False)
- `threads`: Number of threads (default: auto-detect)

**Methods:**
- `get_k()`: Get k-mer size
- `is_canonical()`: Check if using canonical k-mers
- `process_fasta(filename)`: Process FASTA file
- `process_fastq(filename)`: Process FASTQ file
- `get_count(kmer)`: Get count for specific k-mer
- `get_all_counts()`: Get all k-mer counts

### Database

```python
db = Database(k=21)
```

**Methods:**
- `get_k()`: Get k-mer size
- `query(kmer)`: Query single k-mer
- `query_batch(kmers)`: Query multiple k-mers
- `insert(kmer, count)`: Insert k-mer with count
- `insert_batch(data)`: Insert multiple k-mers
- `save()`: Save database to disk
- `get_stats()`: Get database statistics

### FuzzyQuery

```python
fq = FuzzyQuery(k=21, max_distance=1)
```

**Parameters:**
- `k`: k-mer size
- `max_distance`: Maximum edit distance (default: 1)

**Methods:**
- `get_k()`: Get k-mer size
- `get_max_distance()`: Get maximum distance
- `query(sequence)`: Perform fuzzy query
- `query_batch(queries)`: Query multiple sequences
- `validate_kmer(kmer)`: Validate k-mer sequence

## 🔧 Requirements

- **Python 3.11+**: Modern Python with type annotation support
- **Rust 1.70+**: For building from source (optional for wheels)

## 🧪 Testing

Run tests with pytest:

```bash
pip install pytest
pytest tests/
```

## 📖 Examples

See the [examples/](examples/) directory for more detailed usage examples:

- Basic k-mer counting
- Database operations
- Fuzzy search patterns
- Performance benchmarks

## 🔬 Advanced Usage

### Performance Tips

1. **Use canonical k-mers** for reduced memory usage
2. **Batch operations** for better performance
3. **Choose appropriate k-mer size** for your use case

### Error Handling

```python
from rustkmer import KmerError, DatabaseError, FuzzyQueryError

try:
    result = db.query("INVALID_KMER")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## 🤝 Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/yourusername/rustkmer.git
cd rustkmer

# Install development dependencies
pip install maturin[patchelf] pytest
pip install -e .  # Editable install

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [PyO3](https://pyo3.rs/) for Python-Rust interoperability
- Inspired by existing k-mer counting tools like Jellyfish
- Performance optimized with [Rust](https://www.rust-lang.org/)

## 📞 Support

- 📖 [Documentation](https://rustkmer.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/yourusername/rustkmer/issues)
- 💬 [Discussions](https://github.com/yourusername/rustkmer/discussions)

---

**RustKmer Python**: High-performance genomic k-mer analysis in Python! 🧬🚀