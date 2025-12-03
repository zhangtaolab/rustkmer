# RustKmer Python API

高性能的k-mer计数和查询工具，现已提供Python API！相比Jellyfish实现**84倍性能提升**。

## 🚀 安装

### Python包 + 虚拟环境 (强烈推荐)

使用虚拟环境安装，避免与系统包冲突：

```bash
# 1. 创建虚拟环境
python3 -m venv .venv

# 2. 激活虚拟环境
# Linux/macOS:
source .venv/bin/activate
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. 安装RustKmer
pip install rustkmer

# 4. 验证安装
python -c "from rustkmer import KmerCounter, Database; print('✅ 安装成功!')"

# 5. 完成后退出虚拟环境
deactivate
```

### 从源码构建

```bash
git clone https://github.com/yourusername/rustkmer.git
cd rustkmer
pip install .
```

## 🔧 快速开始

```python
from rustkmer import KmerCounter, Database

# 创建k-mer计数器
counter = KmerCounter(k=21, canonical=True, threads=4)

# 处理文件（自动支持压缩格式）
counter.count_file("genome.fa")     # 常规FASTA文件
counter.count_file("genome.fa.gz")  # 压缩FASTA文件
counter.count_file("reads.fq.gz")   # 压缩FASTQ文件
counter.count_string("ACGTACGTACGTACGTACGTACGTACGT")  # 从字符串计数

# 获取k-mer计数
count = counter.get_count("ATGCGATGCTAGCGCTAGCTA")
print(f"k-mer count: {count}")

# 获取统计信息
unique_count = counter.get_unique_count()
total_count = counter.get_total_count()
print(f"Unique k-mers: {unique_count}")
print(f"Total k-mers: {total_count}")

# 保存到数据库
counter.save_to_database("genome.rkdb", False)

# 加载数据库并查询
db = Database()
db.load("genome.rkdb")

# 查询k-mer
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Found: {result.found}, Count: {result.count}")

# 获取数据库统计
stats = db.get_stats()
print(f"Database: k={stats.kmer_size}, total={stats.total_kmers}")
```

## 📚 核心功能

- **高性能计数**: 多线程并行k-mer计数
- **自动压缩支持**: 自动处理.gz压缩的FASTA/FASTQ文件
- **数据库兼容**: 与CLI工具完全兼容的.rkdb数据库格式
- **内存优化**: 大数据库自动使用内存映射
- **线程安全**: 支持多线程并发访问

## 🐍 API 参考

### KmerCounter 类

高性能k-mer计数器，用于处理序列文件并生成数据库。

```python
counter = KmerCounter(k=21, canonical=False, threads=1)
```

**参数:**
- `k`: k-mer大小 (1-31，默认: 21)
- `canonical`: 是否使用canonical k-mers (默认: False)
- `threads`: 线程数 (默认: 1，自动检测CPU核心数)

**方法:**

#### count_file(file_path)
处理序列文件并计数k-mers。

```python
counter.count_file("genome.fa")      # FASTA文件
counter.count_file("reads.fq")       # FASTQ文件
counter.count_file("genome.fa.gz")   # 压缩FASTA文件
counter.count_file("reads.fq.gz")    # 压缩FASTQ文件
```

#### count_string(sequence)
从字符串计数k-mers。

```python
counter.count_string("ATGCGATGCTAGCGCTAGCTA")
```

#### get_count(kmer)
获取特定k-mer的计数。

```python
count = counter.get_count("ATGCGATGCTAGCGCTAGCTA")
print(f"Count: {count}")
```

#### get_unique_count()
获取唯一k-mer数量。

```python
unique_kmers = counter.get_unique_count()
```

#### get_total_count()
获取所有k-mer的总计数。

```python
total_kmers = counter.get_total_count()
```

#### save_to_database(file_path, compression)
保存计数结果到数据库文件。

```python
counter.save_to_database("output.rkdb", False)
```

**参数:**
- `file_path`: 输出数据库文件路径（必须以.rkdb结尾）
- `compression`: 是否压缩（当前版本忽略此参数）

### Database 类

k-mer数据库查询类，用于加载和查询.rkdb数据库文件。

```python
db = Database()           # 创建数据库对象
db.load("database.rkdb")  # 加载数据库文件
```

**方法:**

#### load(file_path)
从文件加载数据库。

```python
db = Database()
db.load("genome.rkdb")  # 文件必须存在且以.rkdb结尾
```

#### query(kmer)
查询单个k-mer。

```python
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Found: {result.found}")
print(f"Count: {result.count}")
```

**返回值:** `QueryResult`对象，包含：
- `found`: bool - 是否找到k-mer
- `count`: u32 - k-mer计数（如果found=True）

#### get_stats()
获取数据库统计信息。

```python
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Uses memory mapping: {stats.uses_memory_mapping}")
print(f"Canonical: {stats.canonical}")
```

**返回值:** `DatabaseStats`对象，包含：
- `kmer_size`: u8 - k-mer大小
- `total_kmers`: u64 - 总k-mer数量
- `uses_memory_mapping`: bool - 是否使用内存映射
- `canonical`: bool - 是否为canonical k-mers

## 🔧 系统要求

- **Python 3.8+**: 支持所有现代Python版本
- **操作系统**: Linux、macOS、Windows
- **内存**: 足够内存处理大型数据集
- **存储**: 对于大型基因组文件，建议使用SSD

## 🧪 测试

运行基本功能测试：

```python
from rustkmer import KmerCounter, Database

# 测试k-mer计数
counter = KmerCounter(k=7, canonical=False, threads=1)
counter.count_string("ACGTACGTACGTACGT")

print(f"Total k-mers: {counter.get_total_count()}")
print(f"Unique k-mers: {counter.get_unique_count()}")

# 测试数据库操作
counter.save_to_database("test.rkdb", False)

db = Database()
db.load("test.rkdb")

result = db.query("ACGTACGT")
print(f"Query result: {result.count}")

stats = db.get_stats()
print(f"Database k-mer size: {stats.kmer_size}")
```

## 📖 使用示例

### 基本k-mer计数和查询

```python
from rustkmer import KmerCounter, Database

# 1. 创建计数器
counter = KmerCounter(k=21, canonical=True, threads=4)

# 2. 处理FASTA文件
counter.count_file("genome.fa")

# 3. 获取统计信息
print(f"Unique k-mers: {counter.get_unique_count()}")
print(f"Total k-mers: {counter.get_total_count()}")

# 4. 保存数据库
counter.save_to_database("genome_k21.rkdb", False)

# 5. 加载数据库并查询
db = Database()
db.load("genome_k21.rkdb")

# 6. 查询特定k-mer
sequences = ["ATGCGATGCTAGCGCTAGCTA", "GCTAGCTAGCTAGCTAGCTAC"]
for seq in sequences:
    result = db.query(seq)
    print(f"{seq}: {result.count}")
```

### 批量处理多个文件

```python
from rustkmer import KmerCounter
import glob

# 创建计数器
counter = KmerCounter(k=31, canonical=True, threads=8)

# 处理所有FASTA文件
for file_path in glob.glob("data/*.fa.gz"):
    print(f"Processing {file_path}...")
    counter.count_file(file_path)

# 保存结果
counter.save_to_database("combined_k31.rkdb", False)

print(f"Total unique k-mers: {counter.get_unique_count()}")
```

### 大基因组数据处理

```python
from rustkmer import KmerCounter, Database
import os

# 对于大文件，使用更多线程
counter = KmerCounter(k=21, canonical=True, threads=16)

# 处理大基因组文件（自动支持gzip压缩）
large_genome = "large_genome.fa.gz"
if os.path.exists(large_genome):
    print(f"Processing large genome: {large_genome}")
    counter.count_file(large_genome)

    # 保存数据库
    db_path = "large_genome_k21.rkdb"
    counter.save_to_database(db_path, False)

    # 验证数据库
    db = Database()
    db.load(db_path)

    stats = db.get_stats()
    print(f"Database created: {stats.total_kmers:,} k-mers")
    print(f"Uses memory mapping: {stats.uses_memory_mapping}")
```

## 🔬 性能优化建议

### 选择合适的k-mer大小
- **小k-mers (15-21)**: 适用于短序列和查询应用
- **中等k-mers (21-31)**: 平衡特异性和敏感性，推荐用于大多数应用
- **大k-mers (31+)**: 适用于长序列和高度特异性应用

### 使用canonical k-mers
```python
# 推荐：使用canonical k-mers减半内存使用
counter = KmerCounter(k=21, canonical=True, threads=4)
```

### 多线程处理
```python
import multiprocessing

# 使用所有可用CPU核心
threads = multiprocessing.cpu_count()
counter = KmerCounter(k=21, canonical=True, threads=threads)
```

### 内存映射优化
对于大于100MB的数据库文件，Python API会自动使用内存映射，提供高效的随机访问而无需将整个数据库加载到内存中。

## 🔧 错误处理

```python
from rustkmer import KmerCounter, Database
import traceback

try:
    # 创建计数器
    counter = KmerCounter(k=21, canonical=False, threads=4)

    # 尝试处理不存在的文件
    counter.count_file("nonexistent.fa")
except Exception as e:
    print(f"Error processing file: {e}")

try:
    # 尝试加载不存在的数据库
    db = Database()
    db.load("nonexistent.rkdb")
except Exception as e:
    print(f"Error loading database: {e}")

try:
    # 数据库验证
    db = Database()
    db.load("database.rkdb")

    # 查询无效的k-mer
    result = db.query("INVALID_KMER")
except Exception as e:
    print(f"Query error: {e}")
```

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 使用 [PyO3](https://pyo3.rs/) 构建Python-Rust互操作性
- 灵感来自现有的k-mer计数工具如Jellyfish
- 使用 [Rust](https://www.rust-lang.org/) 进行性能优化

## 📞 支持

- 📖 [完整文档](USER_GUIDE.md)
- 🐛 [问题反馈](https://github.com/yourusername/rustkmer/issues)
- 💬 [讨论区](https://github.com/yourusername/rustkmer/discussions)

---

**RustKmer Python**: 为Python用户提供高性能基因组k-mer分析！🧬🚀