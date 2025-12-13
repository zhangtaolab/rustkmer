# Quickstart Guide: RustKmer Python API

**Feature**: 001-python-binding
**Version**: 0.1.0

## Installation

### Method 1: Install from PyPI (Recommended for users)

```bash
pip install rustkmer
```

### Method 2: Install from source (for development)

```bash
# Clone the repository
git clone https://github.com/your-org/rustkmer
cd rustkmer

# Install in development mode
# This creates a link from your Python environment to the source code
pip install -e ./python

# Or if you're at the repository root:
pip install -e .
```

**Development Mode (`pip install -e .`) 说明**：

- `-e` 或 `--editable` 标志创建一个"可编辑"安装
- 代码更改会立即反映在安装的包中，无需重新安装
- 适合开发和测试，可以实时修改代码
- 安装的是软链接，不是复制文件

**验证安装**：

```bash
# 测试安装
python -c "from rustkmer import Database; print('Installation successful!')"

# 查看安装位置
pip show rustkmer
```

**依赖要求**：
- Python 3.10 或更高版本
- rustkmer CLI 工具必须在 PATH 中（或包含在包中）

## Basic Usage

### Opening a Database

```python
from rustkmer import Database

# Open an existing database
db = Database("/path/to/database.rkdb")

# Use as context manager (recommended)
with Database("/path/to/database.rkdb") as db:
    # Database automatically closed
    pass
```

### Querying K-mers

```python
# Single query
result = db.query("ATCGATCGATCG")
print(f"Count: {result.count}")
print(f"Canonical: {result.canonical}")

# Check if k-mer exists
if result.is_present:
    print("K-mer found in database")

# Batch queries for better performance
kmers = ["ATCG", "GCTA", "CGAT", "TACG"]
results = db.query_batch(kmers, max_workers=4)

for kmer, result in results.items():
    print(f"{kmer}: {result.count}")
```

### Getting Database Statistics

```python
stats = db.stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Total counts: {stats.total_counts}")
print(f"Database file: {stats.file_size} bytes")
```

### Dumping K-mers

```python
# Dump first 1000 k-mers
for i, result in enumerate(db.dump(limit=1000)):
    if i % 100 == 0:
        print(f"Processed {i} k-mers...")
    print(f"{result.kmer}\t{result.count}")

# Dump with offset (skip first 1000)
for result in db.dump(limit=1000, offset=1000):
    print(result.kmer, result.count)

# Convert to list (caution with large databases)
results = list(db.dump(limit=1000))
print(f"Retrieved {len(results)} k-mers")
```

## Error Handling

```python
from rustkmer import (
    Database,
    DatabaseNotFoundError,
    InvalidKmerError,
    RustKmerError
)

try:
    db = Database("/nonexistent/file.rkdb")
except DatabaseNotFoundError as e:
    print(f"Database not found: {e}")

try:
    result = db.query("INVALID_KMER_X")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e}")

# General error handling
try:
    stats = db.stats()
except RustKmerError as e:
    print(f"Database error: {e}")
```

## Advanced Usage

### Working with Large Datasets

```python
import json
from rustkmer import Database

# Process large databases efficiently
def process_large_database(db_path, output_file):
    with Database(db_path) as db:
        stats = db.stats()
        print(f"Processing {stats.unique_kmers} k-mers...")

        with open(output_file, 'w') as f:
            for i, result in enumerate(db.dump()):
                if i % 10000 == 0:
                    print(f"Processed {i:,} k-mers")

                # Write as JSON lines
                json.dump(result.to_dict(), f)
                f.write('\n')
```

### Parallel Batch Queries

```python
from concurrent.futures import ThreadPoolExecutor
import itertools

def parallel_batch_query(db, kmer_lists, max_workers=8):
    """Query multiple batches in parallel"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(db.query_batch, kmer_batch)
            for kmer_batch in kmer_lists
        ]

        for future in futures:
            batch_results = future.result()
            results.append(batch_results)

    # Combine results
    return dict(itertools.chain.from_iterable(r.items() for r in results))

# Example usage
kmers = [f"ATCG{i}" for i in range(1000)]
batches = [kmers[i:i+100] for i in range(0, len(kmers), 100)]
results = parallel_batch_query(db, batches)
```

### Integration with Bioinformatics Tools

```python
import pandas as pd
from rustkmer import Database

def analyze_kmer_abundance(db_path, output_csv):
    """Export k-mer abundance to CSV for analysis"""
    with Database(db_path) as db:
        # Collect data
        data = []
        for result in db.dump(limit=100000):  # Limit for demo
            data.append({
                'kmer': result.kmer,
                'count': result.count,
                'gc_content': calculate_gc(result.kmer)
            })

        # Create DataFrame
        df = pd.DataFrame(data)

        # Basic statistics
        print(f"Mean count: {df['count'].mean():.2f}")
        print(f"Median count: {df['count'].median()}")
        print(f"Max count: {df['count'].max()}")

        # Save to CSV
        df.to_csv(output_csv, index=False)
        print(f"Saved {len(df)} k-mers to {output_csv}")

def calculate_gc(sequence):
    """Calculate GC content of DNA sequence"""
    gc = sum(1 for base in sequence.upper() if base in 'GC')
    return gc / len(sequence) * 100
```

## Performance Tips

1. **Use Batch Queries**: For multiple k-mers, use `query_batch()` instead of individual queries
2. **Process in Streams**: Use the iterator from `dump()` for large databases
3. **Limit Concurrency**: Adjust `max_workers` based on your system (default is 4)
4. **Cache Stats**: Database statistics are cached after first access

## Troubleshooting

### Common Issues

1. **"Database not found"**
   - Check file path and permissions
   - Ensure the file is a valid .rkdb format

2. **"Invalid k-mer" error**
   - K-mers must contain only A, T, C, G characters
   - K-mer length must match database k-mer size

3. **Performance issues**
   - Use batch queries for multiple k-mers
   - Increase max_workers for parallel processing
   - Check system resources (CPU, memory)

### Getting Help

```python
# Check database information
with Database(db_path) as db:
    print(f"Database: {db.path}")
    print(f"Loaded: {db.is_loaded}")
    print(f"K-mer size: {db.kmer_size}")

    # Validate with test query
    try:
        test_result = db.query("A" * db.kmer_size)
        print("Database accessible")
    except Exception as e:
        print(f"Database error: {e}")
```

## Development Guide

### 设置开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/rustkmer
cd rustkmer

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 3. 安装依赖（开发模式）
pip install -e .[dev]

# 4. 验证安装
pytest tests/  # 运行测试
```

### 开发工作流程

```bash
# 1. 修改代码
vim python/rustkmer/database.py

# 2. 运行测试
pytest tests/test_database.py -v

# 3. 使用开发版本测试
python examples/basic_usage.py

# 4. 提交更改
git add python/rustkmer/database.py
git commit -m "fix: 修复数据库查询问题"
```

### 构建和发布

```bash
# 构建 wheel 包
python -m build python/

# 本地测试安装
pip install dist/rustkmer-*.whl --force-reinstall

# 发布到 PyPI（需要权限）
python -m twine upload dist/*
```

## Next Steps

- Explore the [full API documentation](https://rustkmer.readthedocs.io/)
- Check out the [examples directory](../examples/)
- Learn about [performance optimization](performance-guide.md)
- Contribute to the project on [GitHub](https://github.com/your-org/rustkmer)