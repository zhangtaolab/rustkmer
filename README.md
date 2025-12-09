# RustKmer

[![Crates.io](https://img.shields.io/crates/v/rustkmer)](https://crates.io/crates/rustkmer)
[![Build Status](https://img.shields.io/github/workflow/status/your-username/rustkmer/CI)](https://github.com/your-username/rustkmer/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

高性能的k-mer计数和查询工具，使用Rust实现，专为现代生物信息学应用设计。相比Jellyfish实现**84倍性能提升**。

## 🚀 主要特性

### 🏆 性能优势
- **84倍查询性能提升**: 22,703 queries/sec vs Jellyfish 270 queries/sec (50k k-mers测试)
- **384-1526倍排序数据库提升**: 相比非排序数据库的查询性能
- **内存优化**: 高效的内存管理和缓存友好的数据结构
- **大规模处理**: 支持>100M k-mers的大型基因组数据集

### 🛠️ 核心功能
- **高性能计数**: 多线程并行k-mer计数
- **批量查询**: 高效的批量k-mer查询处理
- **排序数据库**: 二分搜索优化，无需预加载
- **Jellyfish兼容**: 命令行接口与jellyfish高度兼容
- **Python集成**: 完整的Python API和示例代码
- **压缩文件支持**: 自动处理.gz压缩的FASTA/FASTQ文件
- **跨平台**: 支持Linux、macOS和Windows
- **内存映射**: 高效的文件I/O操作

### 🔬 科学验证
- **100%准确性**: 与Jellyfish结果完全一致
- **大规模测试**: 基于OSA1 r7 assembly (381MB)的真实数据测试
- **性能分析**: 详细的性能基准测试和优化建议

## 📦 安装

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
python -c "from rustkmer import KmerCounter; print('✅ 安装成功!')"

# 5. 完成后退出虚拟环境
deactivate
```

**使用虚拟环境的优势:**
- 🛡️ **隔离性**: 避免与系统Python包冲突
- 🔄 **可重现**: 确保项目环境一致性
- 🧹 **清洁**: 易于删除或重建环境
- 👥 **协作**: 可与团队成员共享确切环境

### 现代Python + uv (超快安装) ⚡

[uv](https://github.com/astral-sh/uv) 是下一代Python包管理器，比pip快10-100倍：

```bash
# 1. 安装uv
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 创建新项目并安装RustKmer
uv init rustkmer-analysis
cd rustkmer-analysis
uv add rustkmer

# 3. 立即开始使用！
uv run python -c "from rustkmer import KmerCounter; print('✅ RustKmer就绪!')"

# 4. 创建分析脚本
echo 'from rustkmer import KmerCounter
counter = KmerCounter(k=21, canonical=True)
print("🧬 开始k-mer分析!")' > analysis.py

# 5. 运行分析
uv run python analysis.py
```

**选择uv的优势:**
- 🚀 **极速**: 比pip快10-100倍
- 🎯 **简单**: 一条命令完成环境设置
- 📦 **现代**: 内置项目管理和依赖管理
- 🔄 **可靠**: 更好的缓存和依赖解析

### 系统级Python安装

```bash
# 直接安装到系统（不推荐用于开发）
pip install rustkmer

# 或从源码构建
git clone https://github.com/your-username/rustkmer.git
cd rustkmer
pip install .
```

### 从源码编译 (CLI工具) 🦀

```bash
git clone https://github.com/your-username/rustkmer.git
cd rustkmer
cargo build --release
```

编译后的可执行文件位于 `target/release/rustkmer`。

### 系统要求

- Python 3.8+
- Rust 1.80+ (推荐使用stable版本)
- 足够的内存处理大型数据集
- 对于大型基因组文件，建议使用SSD存储

## 🔧 快速开始

### 基本用法

```bash
# 创建排序数据库（推荐，获得最佳性能）
rustkmer count -k 21 -t 8 --sort -o genome.rkdb genome.fa

# 单个查询
rustkmer query genome.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询（高性能）
rustkmer query genome.rkdb --sequence queries.fa -o results.txt

# 数据库信息
rustkmer info genome.rkdb

# 合并数据库
rustkmer merge -i genome1.rkdb genome2.rkdb -o merged.rkdb

```

### 🆕 大k-mer支持 (k > 32)

rustkmer现在支持大k-mer（k=33到64），使用u128编码：

```bash
# 使用k=33创建数据库
rustkmer count -k 33 -o large_kmer.rkdb sequences.fa

# 查询大k-mer
rustkmer query large_kmer.rkdb ACGTACGTACGTACGTACGTACGTACGTACGTG

# k=64（最大支持）
rustkmer count -k 64 -o k64_database.rkdb genome.fa

# Python API中使用大k-mer
python3 -c "
import rustkmer
counter = rustkmer.SimpleKmerCounter(k=48)
counter.add_sequence('ACGT' * 12)
counter.save('k48_database.rkdb')
"
```

#### 大k-mer特性：
- **支持范围**: k = 1 到 64
- **存储格式**: 使用16字节条目（k≤32为12字节），数据库大小增加约33%
- **性能影响**: 编码性能损失<10%，查询性能损失<5%
- **内存使用**: 用户可配置，无系统限制

### 性能关键发现

✅ **性能建议**: 使用批量查询获得最佳性能：

```bash
# 推荐：高性能批量查询
rustkmer query database.rkdb --sequence queries.fa -o results.txt
# 结果：22,703 queries/sec

# 单个查询（较慢，适合少量查询）
rustkmer query database.rkdb ATGCGATGCTAGCGCTAGCTA
```

### Python集成

```python
# 导入RustKmer Python模块
from rustkmer import KmerCounter, Database

# 创建k-mer计数器
counter = KmerCounter(k=21, canonical=True, threads=4)

# 处理文件（自动支持压缩格式）
counter.count_file("genome.fa")     # 常规FASTA文件
counter.count_file("genome.fa.gz")  # 压缩FASTA文件
counter.count_file("reads.fq.gz")   # 压缩FASTQ文件
counter.count_string("ACGTACGT")  # 从字符串计数

# 获取k-mer计数
count = counter.get_count("ATGCGATGCTAGCGCTAGCTA")
print(f"k-mer count: {count}")

# 获取统计信息
unique_count = counter.get_unique_count()
total_count = counter.get_total_count()
print(f"Unique k-mers: {unique_count}")
print(f"Total k-mers: {total_count}")

# 保存到数据库
counter.save_to_database("output.rkdb", False)

# 加载数据库
db = Database()
db.load("output.rkdb")

# 查询k-mer
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Query result: {result.count}, found: {result.found}")

# 获取数据库统计
stats = db.get_stats()
print(f"Database stats: k={stats.kmer_size}, total={stats.total_kmers}")
```

### Jellyfish兼容示例

```bash
# 与jellyfish相同的参数
rustkmer count -k 31 -m 4G -t 16 -s 100M -L 5 -U 1000 -C -o counts.rkdb reads.fastq

# 查询多个k-mers
rustkmer query counts.rkdb ATGCGATGCTAGCGCTAGCTA CGATCGATCGATCGATCGATCG

# 交互式查询
rustkmer query --interactive counts.rkdb
```

## 📚 详细文档

### 完整文档和示例

- 📖 **[用户指南](USER_GUIDE.md)** - 完整的使用指南和最佳实践
- 🚀 **[快速示例](examples/)** - 命令行和Python集成示例
- 📊 **[性能分析](specs/003-parallel-query/)** - 详细的性能测试报告

### 命令参考

#### `count` - k-mer计数

```bash
rustkmer count -k <KMER_SIZE> -o <OUTPUT> [OPTIONS] <INPUT>
```

**核心参数**:
- `-k, --kmer-size <SIZE>`: k-mer大小 (推荐: 21)
- `-t, --threads <THREADS>`: 线程数 (默认: CPU核心数)
- `-o, --output <FILE>`: 输出数据库文件 (必须)
- `--sort`: 创建排序数据库 (强烈推荐)
- `-C, --canonical`: 规范化k-mer计数
- `-s, --hash-size <SIZE>`: 哈希表大小 (例如: 2G, 500M)

**使用示例**:
```bash
# 基本计数
rustkmer count -k 21 -o genome.rkdb genome.fa

# 高性能排序数据库（推荐）
rustkmer count -k 21 -t 8 --sort -o genome_sorted.rkdb genome.fa

# 规范化计数
rustkmer count -k 21 -C --sort -o genome_canonical.rkdb genome.fa
```

#### `query` - k-mer查询（高性能推荐）

```bash
rustkmer query <DATABASE> [OPTIONS] [KMERS]...
```

**核心参数**:
- `--sequence <FILE>`: 从FASTA文件批量查询
- `-o, --output <FILE>`: 输出文件 (默认: stdout)
- `-i, --interactive`: 交互式查询模式
- `-l, --load`: 强制预加载数据库 (小数据库)
- `-L, --no-load`: 禁用预加载 (大数据库推荐)

**使用示例**:
```bash
# 单个查询
rustkmer query genome.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询（高性能）
rustkmer query genome.rkdb --sequence queries.fa -o results.txt

# 交互式查询
rustkmer query genome.rkdb -i
```

#### `info` - 数据库信息

```bash
rustkmer info <DATABASE>
```

#### `dump` - 数据库导出

```bash
rustkmer dump [OPTIONS] <DATABASE>
```

#### `merge` - 数据库合并

```bash
rustkmer merge -i <DB1> <DB2> [...] -o <OUTPUT> [OPTIONS]
```

**核心参数**:
- `-i, --input <FILES>`: 输入数据库文件 (至少2个)
- `-o, --output <FILE>`: 输出合并数据库文件 (必须)
- `-t, --threads <THREADS>`: 合并线程数 (默认: 自动检测)
- `--check-compatibility`: 仅检查兼容性，不执行合并
- `--temp-dir <DIR>`: 临时文件目录 (默认: 系统临时目录)

**兼容性要求**:
- 所有数据库必须具有相同的k-mer大小
- 所有数据库必须具有相同的canonical模式
- 不支持强制合并不兼容的数据库

**使用示例**:
```bash
# 基本合并
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb

# 多数据库合并
rustkmer merge -i *.rkdb -o all_merged.rkdb

# 检查兼容性
rustkmer merge -i db1.rkdb db2.rkdb --check-compatibility --verbose

# 详细输出合并
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb --verbose
```

### 性能优化指南

#### 🏆 最佳性能配置

1. **使用排序数据库**（最重要）:
   ```bash
   rustkmer count -k 21 --sort -o sorted.rkdb input.fa
   ```

2. **批量查询而非单个查询**:
   ```bash
   # ✅ 推荐：批量处理
   rustkmer query database.rkdb --sequence queries.fa

   # ❌ 避免：单个查询循环
   for kmer in $(cat queries.txt); do
       rustkmer query database.rkdb "$kmer"
   done
   ```

3. **内存管理**:
   ```bash
   # 小数据库 (<2GB): 预加载
   rustkmer query small_db.rkdb --load --sequence queries.fa

   # 大数据库 (>2GB): 内存映射
   rustkmer query large_db.rkdb --no-load --sequence queries.fa
   ```

### RKDB数据库格式

RustKmer使用自定义的RKDB (RustKmer Database) 二进制格式：

**文件结构**:
```
+------------------+
| Header (42 bytes)|
+------------------+
| K-mer Entry 1    |
| - 8 bytes: k-mer |
| - 4 bytes: count |
+------------------+
| K-mer Entry 2    |
| ...              |
+------------------+
```

**Header格式**:
- Magic Number (4 bytes): "RKDB"
- Version (2 bytes): 数据库版本
- K-mer Size (1 byte): k-mer长度
- Total K-mers (8 bytes): k-mer总数
- Flags (1 byte): 数据库标志 (排序、canonical等)
- Data Offset (8 bytes): 数据起始偏移
- Index Offset (8 bytes): 索引偏移 (将来使用)

**性能特点**:
- **排序数据库**: 支持磁盘二分搜索，无需预加载
- **未排序数据库**: 需要预加载到内存，适合频繁查询
- **内存映射**: 使用mmap高效访问大型文件

### 性能优化

#### 🏆 性能基准测试结果

**大规模测试 (50,000 21-mers)**:

| 工具 | 查询速度 | 处理时间 | 性能提升 |
|------|----------|----------|----------|
| **RustKmer** | 22,703 queries/sec | 2.20秒 | **84.1x** |
| Jellyfish | 270 queries/sec | ~185秒 | 基准 |

**数据库优化效果**:

| 数据库类型 | 查询速度 | 性能提升 |
|------------|----------|----------|
| **排序数据库** | 22,703 queries/sec | **384-1526x** |
| 非排序数据库 | 45 queries/sec | 基准 |

**关键发现**:
- ✅ 排序数据库提供巨大性能提升
- ✅ 批量查询比单个查询效率高数千倍
- ✅ 与Jellyfish 100%结果一致性

### 兼容性

#### 与Jellyfish的兼容性

**完全兼容的功能**:
- k-mer计数和基本参数
- canonical k-mer处理
- 计数过滤 (-L/-U 参数)
- FASTA/FASTQ输入格式
- 查询功能

**差异和改进**:
- 自定义RKDB格式 (更高效的查询)
- 排序数据库支持 (显著的性能提升)
- 更好的内存管理
- Rust实现的内存安全保证

## 🚀 快速示例

### 基本使用示例

```bash
# 运行基本示例
chmod +x examples/basic_usage.sh
./examples/basic_usage.sh

# 性能基准测试
chmod +x examples/performance_benchmark.sh
./examples/performance_benchmark.sh

# Python集成示例
python3 examples/python_integration.py
```

### 生产环境示例

```bash
# 1. 创建高性能排序数据库
rustkmer count -k 21 -t 8 --sort -o genome_k21.rkdb genome.fa

# 2. 批量查询分析
rustkmer query genome_k21.rkdb --sequence research_queries.fa -o results.txt

# 3. 结果统计分析
awk '$2 > 0' results.txt | wc -l  # 非零计数
sort -k2,2nr results.txt | head -10  # 最丰富k-mers

# 4. 合并多个数据库
rustkmer merge -i genome_k21_part1.rkdb genome_k21_part2.rkdb -o genome_k21_merged.rkdb
```

## 🧪 测试和验证

### 运行测试

```bash
# 编译和运行示例
cargo build --release
./examples/basic_usage.sh

# Python依赖安装
pip install -r examples/requirements.txt
python3 examples/python_integration.py
```

### 性能验证

我们进行了大规模性能测试，验证了以下关键发现：

1. **84倍性能提升**: 相比Jellyfish (50k k-mers测试)
2. **排序数据库优化**: 384-1526倍性能提升
3. **100%准确性**: 与Jellyfish结果完全一致
4. **批量查询优化**: 批量查询比单个查询效率高数千倍

详细测试报告见: [性能分析文档](specs/003-parallel-query/LARGE_SCALE_PERFORMANCE_ANALYSIS.md)

## 🐍 Python集成示例

### 基本Python API

```python
from rustkmer import KmerCounter, Database

# 创建k-mer计数器
counter = KmerCounter(k=21, canonical=True, threads=4)

# 处理文件（自动支持压缩格式）
counter.count_file("genome.fa")     # 常规FASTA文件
counter.count_file("genome.fa.gz")  # 压缩FASTA文件
counter.count_file("reads.fq.gz")   # 压缩FASTQ文件
counter.count_string("ACGTACGT")    # 从字符串计数

# 获取k-mer计数
count = counter.get_count("ATGCGATGCTAGCGCTAGCTA")
print(f"k-mer count: {count}")

# 获取统计信息
unique_count = counter.get_unique_count()
total_count = counter.get_total_count()
print(f"Unique k-mers: {unique_count}")
print(f"Total k-mers: {total_count}")

# 保存到数据库
counter.save_to_database("output.rkdb", False)

# 加载数据库
db = Database()
db.load("output.rkdb")

# 查询k-mer
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"Query result: {result.count}, found: {result.found}")

# 获取数据库统计
stats = db.get_stats()
print(f"Database stats: k={stats.kmer_size}, total={stats.total_kmers}")
```

### 高级分析示例

```python
from examples.python_integration import RustKmerAnalyzer

# 初始化分析器
analyzer = RustKmerAnalyzer('genome_k21.rkdb')

# 分布分析
df = analyzer.analyze_kmer_distribution(test_queries)

# 最丰富k-mers
top_kmers = analyzer.find_most_abundant_kmers(test_queries, top_n=10)

# 序列属性分析
properties = analyzer.analyze_sequence_properties(test_queries)

# 性能基准测试
performance = analyzer.benchmark_query_performance([100, 500, 1000])
```

### 安装Python依赖

```bash
pip install -r examples/requirements.txt
```

Python依赖包括: pandas, numpy, matplotlib (可选), seaborn (可选)

## 🔬 技术细节

### 算法实现

- **哈希表**: 使用自定义的高性能哈希表实现
- **并行处理**: 基于Rayon的work-stealing并行算法
- **内存管理**: 智能的内存分配和回收策略
- **文件I/O**: 内存映射和缓冲I/O优化

### 内存效率

- **k-mer编码**: 2-bit编码压缩DNA序列
- **紧凑存储**: 优化的数据结构布局
- **流式处理**: 支持超大文件的流式读取
- **垃圾回收优化**: 减少内存碎片

### 性能配置

```toml
# Cargo.toml 性能配置
[profile.release]
lto = true
codegen-units = 1
panic = "abort"
opt-level = 3
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 开发环境设置

```bash
# 安装开发依赖
cargo install cargo-watch cargo-flamegraph

# 运行开发服务器
cargo watch -x run

# 性能分析
cargo flamegraph --bin rustkmer -- count -k 21 input.fa
```

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- **Jellyfish**: 提供了优秀的k-mer计数工具和算法参考
- **Rust社区**: 提供了高性能的系统和生物信息学库
- **Rayon**: 出色的并行计算框架

## 📂 项目结构

```
rustkmer/
├── src/                    # Rust源代码
├── examples/               # 示例和教程
│   ├── basic_usage.sh      # 基本使用示例
│   ├── performance_benchmark.sh  # 性能基准测试
│   ├── python_integration.py    # Python API示例
│   └── requirements.txt    # Python依赖
├── specs/                  # 技术规范和性能分析
│   └── 003-parallel-query/ # 21-mer性能测试报告
├── USER_GUIDE.md          # 完整用户指南
└── README.md              # 项目说明
```

## 📞 联系方式

- 项目主页: https://github.com/your-username/rustkmer
- 问题报告: https://github.com/your-username/rustkmer/issues
- 文档: [USER_GUIDE.md](USER_GUIDE.md)

## 🏆 项目状态

✅ **已完成功能**:
- 高性能k-mer计数
- 批量k-mer查询
- 数据库合并功能
- 排序数据库优化
- Python API集成
- 完整的性能测试验证
- 与Jellyfish 100%兼容性

🚀 **性能指标**:
- 84倍查询性能提升 (vs Jellyfish)
- 22,703 queries/sec 处理能力
- 384-1526倍排序数据库优化
- 支持>100M k-mers大规模数据

---

**RustKmer**: 为现代生物信息学设计的高性能k-mer分析工具。通过大规模性能测试验证，相比传统工具实现显著性能提升，是生产环境k-mer分析的理想选择。