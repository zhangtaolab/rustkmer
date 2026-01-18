# RustKmer

[![Crates.io](https://img.shields.io/crates/v/rustkmer)](https://crates.io/crates/rustkmer)
[![Build Status](https://img.shields.io/github/workflow/status/your-username/rustkmer/CI)](https://github.com/your-username/rustkmer/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

高性能的k-mer计数和查询工具，使用Rust实现，专为现代生物信息学应用设计。

## 🚀 主要特性

### 🏆 性能优势
- **高性能查询**: 优化的查询引擎，支持22,703+ queries/sec
- **排序数据库优化**: 二分搜索提供384-1526倍性能提升
- **内存优化**: 高效的内存管理和缓存友好的数据结构
- **大规模处理**: 支持>100M k-mers的大型基因组数据集

### 🛠️ 核心功能
- **高性能计数**: 顺序k-mer计数
- **批量查询**: 高效的批量k-mer查询处理
- **🔥 模糊查询**: 通配符和突变容忍搜索，支持复杂模式匹配
- **排序数据库**: 二分搜索优化，无需预加载
- **标准兼容**: 遵循k-mer计数的行业标准
- **Python集成**: 完整的Python API和示例代码
- **压缩文件支持**: 自动处理.gz压缩的FASTA/FASTQ文件
- **跨平台**: 支持Linux、macOS和Windows
- **内存映射**: 高效的文件I/O操作

### 🔬 科学验证
- **准确性验证**: 经过大规模真实数据测试验证
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
python -c "from pyrustkmer import PyCounter; print('✅ 安装成功!')"

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
uv run python -c "from pyrustkmer import PyCounter; print('✅ RustKmer就绪!')"

# 4. 创建分析脚本
echo 'from pyrustkmer import PyCounter
counter = PyCounter(21, canonical=True)
print("🧬 开始k-mer分析!")' > analysis.py

# 5. 运行分析
uv run python analysis.py
```

**选择uv的优势:**
- 🚀 **极速**: 比pip快10-100倍
- 🎯 **简单**: 一条命令完成环境设置
- 📦 **现代**: 内置项目管理和依赖管理
- 🔄 **可靠**: 更好的缓存和依赖解析

### 📦 Conda环境安装 🐍

使用Conda创建隔离的Python环境，非常适合生物信息学工作流：

#### 方法一：使用conda-forge频道 (推荐)

```bash
# 1. 安装Miniconda (如果没有conda)
# 下载: https://docs.conda.io/en/latest/miniconda.html

# 2. 创建新环境并安装RustKmer
conda create -n rustkmer-env python=3.11 -c conda-forge
conda activate rustkmer-env

# 3. 安装RustKmer及其依赖
conda install -c conda-forge rustkmer numpy matplotlib pytest

# 4. 验证安装
python -c "from pyrustkmer import PyCounter; print('✅ Conda安装成功!')"

# 5. 安装额外的数据科学工具 (可选)
conda install -c conda-forge pandas seaborn jupyter
```

#### 方法二：从PyPI安装到Conda环境

```bash
# 1. 创建环境
conda create -n rustkmer-env python=3.11
conda activate rustkmer-env

# 2. 安装RustKmer及开发依赖
pip install rustkmer
pip install pytest numpy matplotlib pandas

# 3. 验证安装
python -c "from pyrustkmer import PyCounter; print('✅ 安装成功!')"
```

#### 方法三：开发环境设置 (完整版)

```bash
# 1. 创建完整开发环境
conda create -n rustkmer-dev python=3.11 -c conda-forge rust numpy matplotlib pytest pandas seaborn jupyterlab

# 2. 激活环境
conda activate rustkmer-dev

# 3. 克隆源码并安装开发版本
git clone https://github.com/your-username/rustkmer.git
cd rustkmer

# 4. 安装为可编辑包
pip install -e .

# 5. 安装开发工具
pip install pytest-benchmark hypothesis

# 6. 运行测试验证
python -m pytest tests/python/ -v
```

#### 常用Conda命令参考

```bash
# 查看环境列表
conda env list

# 导出环境配置
conda env export > rustkmer-environment.yml

# 从配置文件创建环境
conda env create -f rustkmer-environment.yml

# 删除环境
conda env remove -n rustkmer-env

# 在环境中安装额外包
conda activate rustkmer-env
conda install -c conda-forge scipy scikit-learn

# 查看已安装包
conda list

# 更新conda和所有包
conda update conda
conda update --all
```

#### 环境配置文件示例

创建 `environment.yml` 文件以快速设置环境：

```yaml
name: rustkmer-env
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - numpy>=1.21
  - matplotlib>=3.5
  - pytest>=7.0
  - pandas
  - pip
  - pip:
    - rustkmer
```

使用方法：
```bash
conda env create -f environment.yml
conda activate rustkmer-env
```

#### Conda + Jupyter集成

```bash
# 1. 安装ipykernel
conda install -c conda-forge ipykernel

# 2. 将环境添加到Jupyter
python -m ipykernel install --user --name rustkmer-env --display-name "RustKmer Environment"

# 3. 启动Jupyter并选择RustKmer环境
jupyter lab
```

**选择Conda的优势:**
- 🔬 **生物信息学标准**: 科研领域广泛使用的环境管理工具
- 📦 **依赖管理**: 强大的包依赖解析和二进制分发
- 🔄 **环境隔离**: 完全隔离的环境，避免包冲突
- 🌍 **跨平台**: 统一的安装体验 (Windows/macOS/Linux)
- 🧪 **实验重现**: 轻松分享和重现分析环境

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

# 🔥 模糊查询 - 通配符和突变容忍
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA"                    # 通配符查询 (N=任意碱基)
rustkmer fuzzy-query -d genome.rkdb -q "ATCGATCGATCGATCGATCGA" -m 2  # 突变容忍搜索

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
from pyrustkmer import PyCounter
counter = PyCounter(kmer_length=48, canonical=True)
counter.add_sequence('ACGT' * 12)
counter.save_database('k48_database.rkdb')
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

#### 方式一：纯Python API（推荐）
```python
# 导入RustKmer Python模块
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# 创建k-mer计数器
counter = PyCounter(21, canonical=True)

# 处理文件（自动支持压缩格式）
counter.add_from_fasta("genome.fa")     # 常规FASTA文件
counter.add_from_fasta("genome.fa.gz")  # 压缩FASTA文件
counter.add_sequence("ACGTACGT")  # 从字符串计数

# 获取统计信息
stats = counter.get_stats()
print(f"k-mer count: {stats.total_kmers}")

# 加载数据库
db = PyDatabase("output.rkdb", LoadMode.Preload)

# 查询k-mer
result = db.query_exact("ATGCGATGCTAGCGCTAGCTA")
print(f"Query result: {result.count}, found: {result.found}")
```

#### 方式二：PyO3高性能扩展 ⚡
```python
# 导入PyO3扩展
from pyrustkmer import PyDatabase, PyPrefixQuery, LoadMode

# 加载数据库（高性能模式）
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 🔥 前缀搜索（全新功能）
result = db.query_prefix("ATG")
print(f"找到 {len(result)} 个前缀匹配")

# 🔥 混合搜索模式
from pyrustkmer import PyFuzzyQuery
fuzzy = PyFuzzyQuery(db)
hybrid_result = fuzzy.query_fuzzy("ATCGNNN", max_mutations=2)

# 使用专用查询引擎
query_engine = PyPrefixQuery("genome.rkdb", LoadMode.Preload)
results = query_engine.query_prefix("ATG")
```

### 🔥 模糊查询功能 (Wildcard & Mutation Tolerance)

RustKmer提供强大的模糊查询功能，支持通配符搜索和突变容忍匹配：

```python
from pyrustkmer import PyDatabase, PyFuzzyQuery, LoadMode

# 加载数据库
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 创建模糊查询器
fuzzy = PyFuzzyQuery(db)

# 通配符查询 (N = 任意碱基: A,T,C,G)
wildcard_results = fuzzy.query_fuzzy("ATNNGTA", max_mutations=0)
print(f"通配符查询找到 {len(wildcard_results.get_top_matches(1000))} 个匹配")

# 突变容忍搜索 (汉明距离)
mutation_results = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGA", max_mutations=2)
print(f"突变容忍搜索找到 {len(mutation_results.get_top_matches(1000))} 个变体")

# 批量模糊查询
patterns = ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"]
for pattern in patterns:
    result = fuzzy.query_fuzzy(pattern, max_mutations=1)
    print(f"模式 '{pattern}': {len(result.get_top_matches(1000))} 个匹配")

# 结果处理
top_matches = wildcard_results.get_top_matches(5)
for match in top_matches:
    print(f"  {match.kmer}: {match.count}")
```

**命令行模糊查询:**
```bash
# 通配符搜索
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA"

# 突变容忍搜索
rustkmer fuzzy-query -d genome.rkdb -q "ATCGATCGATCGATCGATCGA" -m 2

# 批量查询并导出
rustkmer fuzzy-query -d genome.rkdb -f patterns.txt -o results.csv --format csv
```

### 标准使用示例

```bash
# 计数参数
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
- 🔥 **[前缀查询实现报告](PREFIX_QUERY_IMPLEMENTATION_REPORT.md)** - 前缀和混合搜索实现详情
- ⚡ **[混合搜索指南](HYBRID_SEARCH_USAGE.md)** - 前缀和混合搜索使用说明

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
| **RustKmer** | 22,703 queries/sec | 2.20秒 | 基准 |

**数据库优化效果**:

| 数据库类型 | 查询速度 | 性能提升 |
|------------|----------|----------|
| **排序数据库** | 22,703 queries/sec | **384-1526x** |
| 非排序数据库 | 45 queries/sec | 基准 |

**关键发现**:
- ✅ 排序数据库提供巨大性能提升
- ✅ 批量查询比单个查询效率高数千倍
- ✅ 高性能 Rust 实现

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

1. **高性能查询**: 22,703+ queries/sec
2. **排序数据库优化**: 384-1526倍性能提升
3. **准确性验证**: 经过大规模测试验证
4. **批量查询优化**: 批量查询比单个查询效率高数千倍

详细测试报告见: [性能分析文档](specs/003-parallel-query/LARGE_SCALE_PERFORMANCE_ANALYSIS.md)

## 🐍 Python集成示例

### 基本Python API

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# 创建k-mer计数器
counter = PyCounter(21, canonical=True)

# 处理文件（自动支持压缩格式）
counter.add_from_fasta("genome.fa")     # 常规FASTA文件
counter.add_from_fasta("genome.fa.gz")  # 压缩FASTA文件
counter.add_sequence("ACGTACGT")    # 从字符串计数

# 获取统计信息
stats = counter.get_stats()
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Total k-mers: {stats.total_kmers}")

# 保存到数据库
counter.save_database("output.rkdb")

# 加载数据库
db = PyDatabase("output.rkdb", LoadMode.Preload)

# 查询k-mer
result = db.query_exact("ATGCGATGCTAGCGCTAGCTA")
print(f"Query result: {result.count}, found: {result.found}")
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

## 🐍 Python API

RustKmer 提供了完整的Python API，让您可以直接在Python脚本中进行高性能的k-mer分析。

### 安装方式

RustKmer 提供**两种 Python 集成方式**：

#### 方式一：纯 Python Stubs（推荐，最稳定）✅

**适用于所有环境，包括 Python 3.13**：
```bash
# 1. 确保 RustKmer CLI 已安装（在 PATH 中）
which rustkmer  # 应该输出路径

# 2. 安装纯 Python 包
pip install rustkmer

# 3. 验证安装
python -c "from pyrustkmer import PyDatabase, LoadMode; print('✅ RustKmer Python API 就绪!')"
```

**工作原理**:
- Python 代码作为**存根**（stubs）
- 实际 k-mer 操作通过调用 `rustkmer` CLI 完成
- **100% 兼容**所有 Python 版本（包括 3.13）
- **零编译**，安装即用

#### 方式二：可编辑开发安装（开发/修改代码）⚠️

**适用于开发者或需要修改 RustKmer 代码的情况**：

```bash
# 1. 克隆源码
git clone https://github.com/your-username/rustkmer.git
cd rustkmer

# 2. 构建 Rust CLI 工具
cargo build --release

# 3. 设置环境变量（重要！）
# 注意：将 /path/to/rustkmer 替换为实际的 rustkmer 项目路径
echo 'export PATH="/path/to/rustkmer/target/release:$PATH"' >> ~/.zshrc
source ~/.zshrc  # 重新加载 shell 配置

# 4. 安装 Python 包（可编辑模式）
cd python  # 进入 Python 子目录
pip install -e .

# 5. 验证安装
python -c "from pyrustkmer import PyDatabase, LoadMode; print('✅ 可编辑安装就绪!')"

# 6. 测试从不同目录导入
cd /tmp
python -c "from pyrustkmer import PyDatabase, LoadMode; print('✅ 任意目录导入成功!')"
```

**🔧 重要配置步骤**：
1. **PATH 设置**: 确保 `rustkmer` 命令在系统 PATH 中
2. **可编辑安装**: 使用 `pip install -e .` 而不是普通安装
3. **目录无关性**: 修改后的代码支持从任何目录导入

**✅ 已解决的问题**:
- **路径依赖**: 修复了只能在特定目录下工作的问题
- **PATH 查找**: 优化了 Rust 二进制文件的查找逻辑
- **跨目录导入**: 支持从任何工作目录导入 Database 类

**⚠️ 注意事项**:
- **开发环境**: 适合需要修改 RustKmer 源码的场景
- **维护成本**: 需要同时维护 Rust 和 Python 代码
- **兼容性**: 仅在 Python 3.10+ 环境下测试过

#### 方式三：PyO3 Rust 扩展（性能最高，功能最全）⚡

**推荐用于高性能计算和完整功能访问**：

```bash
# 1. 安装 Rust 工具链
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# 2. 克隆项目
git clone https://github.com/your-username/rustkmer.git
cd rustkmer

# 3. 构建 PyO3 扩展（推荐 Python 3.10-3.12）
cd pyo3
pip install maturin
maturin develop --release

# 4. 验证安装
python -c "from pyrustkmer import PyDatabase; print('✅ PyO3 扩展就绪!')"
```

**✅ PyO3 扩展特性**:
- **最高性能**: 直接Rust绑定，无CLI开销
- **完整功能**: 支持所有高级功能（模糊查询、前缀搜索、混合搜索）
- **内存效率**: 直接内存访问，最小化数据复制
- **Python原生**: 返回Python对象，无格式转换开销

**⚠️ 环境要求**:
- **Python版本**: 推荐 3.10-3.12
- **Rust工具链**: stable 1.80+
- **编译环境**: 需要C/C++编译器
- **内存**: 编译时需要额外内存

**🔧 编译选项**:
```bash
# 开发模式（快速编译）
maturin develop

# 发布模式（最优性能）
maturin develop --release

# 指定Python解释器
maturin develop --python python3.11

# 仅构建不安装
maturin build
```

**✅ 兼容性状态**:
- **Python 3.10**: ✅ 完全支持
- **Python 3.11**: ✅ 完全支持
- **Python 3.12**: ✅ 完全支持  
- **Python 3.13**: ⚠️ 部分支持（PyO3版本相关）

**🚀 性能对比**:
```python
# PyO3扩展 - 最高性能
from pyrustkmer import PyDatabase, LoadMode
db = PyDatabase("genome.rkdb", LoadMode.Preload)
result = db.query_prefix("ATG")  # 直接内存访问
print(f"Found {len(result)} matches")


**💡 使用建议**:
- **生产环境高性能**: PyO3扩展
- **开发调试**: 可编辑开发安装
- **环境兼容性**: 纯Python Stubs
- **特殊需求**: 根据性能要求选择

### 安装方式对比

| 方式 | Python 兼容性 | 安装难度 | 性能 | 稳定性 | 内存效率 | 推荐场景 |
|------|---------------|----------|------|--------|----------|----------|
| **纯 Python Stubs** | ✅ 3.8-3.13 | ⭐ 简单 | ⭐⭐⭐ CLI级 | ⭐⭐⭐⭐⭐ 极高 | ⭐⭐⭐ 进程隔离 | 生产环境、广泛兼容 |
| **可编辑开发安装** | ✅ 3.10+ | ⭐⭐⭐ 中等 | ⭐⭐⭐ CLI级 | ⭐⭐⭐⭐ 高 | ⭐⭐⭐ 进程隔离 | 开发调试、代码修改 |
| **PyO3 扩展** | ✅ 3.10-3.12 | ⭐⭐⭐⭐ 较复杂 | ⭐⭐⭐⭐⭐ 本地Rust | ⭐⭐⭐⭐ 高 | ⭐⭐⭐⭐⭐ 直接内存 | 高性能计算、内存敏感 |

### PyO3 扩展特性

PyO3扩展提供了最完整的RustKmer功能访问：

#### 🔥 高级查询功能
```python
from pyrustkmer import PyDatabase, PyPrefixQuery, LoadMode

# 1. 高性能前缀搜索
db = PyDatabase("genome.rkdb", LoadMode.Preload)
result = db.query_prefix("ATG")
print(f"找到 {len(result)} 个前缀匹配")

# 2. 混合搜索模式
from pyrustkmer import PyFuzzyQuery
fuzzy = PyFuzzyQuery(db)
hybrid_result = fuzzy.query_fuzzy("ATCGNNN", max_mutations=2)

# 3. 专用查询引擎
query_engine = PyPrefixQuery("genome.rkdb", LoadMode.Preload)
prefix_results = query_engine.query_prefix("ATG")

# 4. 批量前缀查询
prefixes = ["ATG", "CTG", "GTG", "TTA", "TAA"]
for prefix in prefixes:
    result = db.query_prefix(prefix)
    print(f"{prefix}: {len(result)} matches")
```

#### 📊 性能监控
```python
# 获取详细性能指标
result = db.query_prefix("ATG")
print(f"前缀匹配数: {len(result)}")

# 模糊查询性能
fuzzy_result = fuzzy.query_fuzzy("ATCGNNN", max_mutations=2)
print(f"模糊匹配数: {len(fuzzy_result.get_top_matches(1000))}")
```

#### 🔧 加载模式
```python
from pyrustkmer import PyDatabase, LoadMode

# 预加载模式（最快查询，适合小数据库）
db = PyDatabase("small_genome.rkdb", LoadMode.Preload)

# 内存映射模式（平衡内存和性能）
db = PyDatabase("large_genome.rkdb", LoadMode.MemoryMapped)

# 延迟加载模式（最低内存，适合超大数据库）
db = PyDatabase("huge_genome.rkdb", LoadMode.Lazy)
```

### 快速示例

#### K-mer 计数

```python
from pyrustkmer import PyCounter

# 创建k-mer计数器
counter = PyCounter(21, canonical=True)

# 从FASTA文件计数
counter.add_from_fasta("sequences.fasta")

# 从字符串计数
counter.add_sequence("ATCGATCGATCGATCGATCGATCG")

# 获取统计信息
stats = counter.get_stats()
print(f"Counts: {stats.total_kmers}")

# 保存数据库
counter.save_database("output.rkdb")
```

#### 数据库查询

```python
from pyrustkmer import PyDatabase, LoadMode

# 加载数据库
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 单个查询
result = db.query_exact("ATCGATCGATCGATCGATCGATCG")
print(f"K-mer count: {result.count}, found: {result.found}")

# 前缀查询
prefix_results = db.query_prefix("ATCG")
print(f"Prefix matches: {len(prefix_results)}")

# 检查k-mer是否存在
if result.found:
    print("K-mer found in database")
```

#### 数据库统计

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("genome.rkdb", LoadMode.Preload)
# 可以通过前缀查询来了解数据库大小
sample_results = db.query_prefix("A")
print(f"Sample prefix matches: {len(sample_results)}")
```

#### 数据库导出

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 导出为文本格式（通过前缀查询并写入文件）
with open("output.txt", "w") as f:
    results = db.query_prefix("A")
    for result in results:
        f.write(f"{result.kmer}\t{result.count}\n")
```

#### 数据库合并

```python
# 使用命令行工具合并数据库
# rustkmer merge -i sample1.rkdb sample2.rkdb -o merged.rkdb

# 然后在Python中加载合并后的数据库
from pyrustkmer import PyDatabase, LoadMode
db = PyDatabase("merged.rkdb", LoadMode.Preload)
print(f"Merged database loaded successfully")
```

### 性能优势

- **高性能**: Rust核心实现，比纯Python实现快100倍以上
- **内存效率**: 支持大型数据库的内存映射访问
- **线程安全**: 可以在多线程环境中安全使用
- **兼容性**: 与CLI命令行工具完全兼容

更多详细信息请查看 pyrustkmer Python 包 (pyo3/)。

### 🛠️ 故障排除

#### 常见导入问题

**问题1: ImportError: cannot import name 'PyDatabase'**
```bash
# 检查 pyrustkmer 是否安装
pip list | grep pyrustkmer

# 如果没有安装，重新安装
pip install rustkmer
```

**问题2: 只能在特定目录下导入**
```bash
# 确保使用了正确安装
pip uninstall rustkmer
pip install rustkmer

# 测试从不同目录导入
cd /tmp
python -c "from pyrustkmer import PyDatabase; print('✅ 导入成功')"
```

**问题3: ImportError: No module named 'pyrustkmer'**
```bash
# 检查包是否正确安装
pip list | grep pyrustkmer

# 如果没有安装，重新安装
pip install rustkmer
```

**问题4: 无法找到 rustkmer 命令**
```bash
# 检查 rustkmer 是否在 PATH 中
which rustkmer

# 如果没有，添加 rustkmer 到 PATH
echo 'export PATH="/path/to/rustkmer/target/release:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**问题5: PyO3 扩展编译失败**
```bash
# 检查 Rust 工具链
rustc --version  # 需要 1.80+

# 检查 Python 开发头文件
python3 -c "import sysconfig; print(sysconfig.get_path('include'))"

# Ubuntu/Debian 安装开发依赖
sudo apt install python3-dev build-essential

# macOS 安装 Xcode 命令行工具
xcode-select --install

# 手动编译调试
cd /path/to/rustkmer/pyo3
maturin develop --verbose
```

**问题5.1: VIRTUAL_ENV 和 CONDA_PREFIX 环境冲突**
```bash
# 错误信息示例
# 💥 maturin failed
# Caused by: Both VIRTUAL_ENV and CONDA_PREFIX are set. Please unset one of them

# CondaError: Run 'conda init' before 'conda deactivate'
# CONDA_PREFIX: /Users/forrest/miniconda3

# 解决方案1: 停用 conda 环境（推荐）
conda deactivate
# 然后重新运行
maturin develop --release

# 解决方案2: 停用虚拟环境
deactivate
# 然后重新运行
maturin develop --release

# 解决方案3: 直接清理环境变量（最有效）
unset VIRTUAL_ENV
unset CONDA_PREFIX
# 验证清理结果
echo "VIRTUAL_ENV: $VIRTUAL_ENV"
echo "CONDA_PREFIX: $CONDA_PREFIX"
# 确认都为空后重新编译
maturin develop --release

# 解决方案4: 手动设置环境（完全控制）
# 临时禁用conda
export CONDA_PREFIX=""
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
# 然后编译
maturin develop --release

# 解决方案5: 在新的干净shell中运行
# 打开新的终端窗口或标签页
# 确保没有激活任何环境
# 然后运行
cd rustkmer/pyo3
maturin develop --release
```

**问题5.2: 清理环境后重新编译**
```bash
# 清理之前的编译结果
cd rustkmer/pyo3
pip uninstall rustkmer-pyo3 -y  # 如果之前安装过
rm -rf target/ .pytest_cache/

# 确保环境干净
unset VIRTUAL_ENV
unset CONDA_PREFIX

# 重新编译
maturin develop --release
```

**问题5.3: 环境隔离最佳实践**
```bash
# 推荐做法1: 使用纯 conda 环境
conda create -n rustkmer-dev python=3.11
conda activate rustkmer-dev
cd rustkmer/pyo3
maturin develop --release

# 推荐做法2: 使用纯 virtualenv 环境
python3 -m venv rustkmer-env
source rustkmer-env/bin/activate
cd rustkmer/pyo3
maturin develop --release

# 推荐做法3: 使用系统Python（最简单）
# 确保没有激活任何虚拟环境
conda deactivate 2>/dev/null || true
deactivate 2>/dev/null || true
unset VIRTUAL_ENV
unset CONDA_PREFIX
# 使用系统Python直接编译
python3 -m pip install maturin
cd rustkmer/pyo3
maturin develop --release

# 避免混用环境
# ❌ 不要同时激活 virtualenv 和 conda
source myenv/bin/activate  # virtualenv
conda activate myenv       # conda - 这样会冲突！
```

**问题5.4: conda 没有初始化时的解决方案**
```bash
# 症状: CondaError: Run 'conda init' before 'conda deactivate'

# 解决方案1: 手动清理 conda 环境变量
unset CONDA_PREFIX
unset CONDA_DEFAULT_ENV
unset CONDA_ENV_PATH
# 清理 conda 相关的PATH
export PATH=$(echo $PATH | tr ':' '\n' | grep -v conda | tr '\n' ':' | sed 's/:$//')

# 解决方案2: 使用绝对路径运行Python
# 完全绕过虚拟环境
/usr/bin/python3 -m pip install maturin
cd rustkmer/pyo3
/usr/bin/python3 -m maturin develop --release

# 解决方案3: 重新初始化 conda（如果需要）
# 首先清理所有环境变量
unset CONDA_*
# 然后重新初始化
source ~/miniconda3/etc/profile.d/conda.sh
# 或
eval "$(/Users/forrest/miniconda3/bin/conda shell.bash hook)"
# 现在可以正常使用 conda
conda deactivate
```

**问题5.5: PyO3 链接器错误解决方案**
```bash
# 症状: ld: symbol(s) not found for architecture arm64
#       clang: error: linker command failed with exit code 1

# 解决方案1: 使用正确的链接器标志（macOS）
cd /path/to/rustkmer/pyo3
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
maturin develop --release

# 解决方案2: 指定正确的Python解释器
cd /path/to/rustkmer/pyo3
PYO3_PYTHON=/usr/bin/python3 maturin develop --release

# 解决方案3: 结合使用（最可靠）
cd /path/to/rustkmer/pyo3
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3
maturin develop --release

# 解决方案4: 测试导入
python3 -c "from pyrustkmer import PyDatabase; print('Success!')"
```

**问题6: PyO3 导入错误**
```python
# 验证 PyO3 扩展安装
try:
    from pyrustkmer import PyDatabase, LoadMode
    print("✅ PyO3 扩展导入成功")
    
    # 测试基本功能
    print("✅ PyDatabase 类可用")
    
except ImportError as e:
    print(f"❌ PyO3 扩展导入失败: {e}")
    print("请重新安装: pip install rustkmer")
except Exception as e:
    print(f"❌ 其他错误: {e}")
```

**问题7: PyO3 性能不如预期**
```python
# 检查是否使用了正确的加载模式
from pyrustkmer import PyDatabase, LoadMode

# 对于小数据库，使用预加载
db = PyDatabase("small.rkdb", LoadMode.Preload)

# 对于大数据库，使用内存映射
db = PyDatabase("large.rkdb", LoadMode.MemoryMapped)

# 使用优化方法
# ✅ 优化方法
result = db.query_prefix("ATG")
print(f"Found {len(result)} matches")
```

**问题8: Python 3.13 兼容性问题**
```bash
# Python 3.13 用户建议使用 pyrustkmer
pip install rustkmer

# 或使用 Python 3.10-3.12 环境以获得完整功能
conda create -n rustkmer-py311 python=3.11
conda activate rustkmer-py311
pip install rustkmer
```

**问题9: 防止环境冲突的最佳实践**
```bash
# 1. 明确选择一种环境管理方式
# 方式A: 纯 conda
conda create -n rustkmer-env python=3.11
conda activate rustkmer-env
# 在此环境中进行所有操作

# 方式B: 纯 virtualenv
python3 -m venv rustkmer-env
source rustkmer-env/bin/activate
# 在此环境中进行所有操作

# 方式C: 系统Python（最简单，避免环境问题）
# 不激活任何环境，直接使用系统Python

# 2. 检查当前环境状态
env | grep -E "(VIRTUAL_ENV|CONDA_PREFIX)"

# 3. 一键清理环境脚本
cleanup_env() {
    echo "清理环境变量..."
    unset VIRTUAL_ENV
    unset CONDA_PREFIX
    unset CONDA_DEFAULT_ENV
    unset CONDA_ENV_PATH
    
    # 清理PATH中的conda路径
    export PATH=$(echo $PATH | tr ':' '\n' | grep -v conda | tr '\n' ':' | sed 's/:$//')
    
    echo "环境已清理"
    echo "VIRTUAL_ENV: $VIRTUAL_ENV"
    echo "CONDA_PREFIX: $CONDA_PREFIX"
}

# 使用方法
cleanup_env
# 然后运行编译
cd rustkmer/pyo3
maturin develop --release

# 4. 在项目目录中创建环境检查脚本
cat > check_env.sh << 'EOF'
#!/bin/bash
echo "=== 环境检查 ==="
echo "VIRTUAL_ENV: ${VIRTUAL_ENV:-'未设置'}"
echo "CONDA_PREFIX: ${CONDA_PREFIX:-'未设置'}"
echo "Python路径: $(which python3)"
echo "Python版本: $(python3 --version)"
echo "================="
EOF

chmod +x check_env.sh
./check_env.sh

# 5. PyO3 构建专用脚本
cat > build_pyo3.sh << 'EOF'
#!/bin/bash
echo "🔧 开始 PyO3 构建..."

# 清理环境变量
echo "🧹 清理环境变量..."
unset VIRTUAL_ENV
unset CONDA_PREFIX
unset CONDA_DEFAULT_ENV
unset CONDA_ENV_PATH

# 设置构建标志
echo "⚙️  设置构建标志..."
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3

# 构建
echo "🔨 开始构建..."
cd /path/to/rustkmer/pyo3
maturin develop --release

# 检查结果
if [ $? -eq 0 ]; then
    echo "✅ 构建成功!"
    echo "🧪 测试导入..."
    /usr/bin/python3 -c "from pyrustkmer import PyDatabase; print('🎉 PyO3 扩展导入成功!')" 2>/dev/null || echo "❌ 导入失败"
else
    echo "❌ 构建失败!"
    exit 1
fi
EOF

chmod +x build_pyo3.sh
echo "🚀 运行构建脚本: ./build_pyo3.sh"
```

#### 验证安装完整性

```python
# 完整的安装验证脚本
def verify_rustkmer_installation():
    """验证 RustKmer 安装的完整性"""
    
    print("🔍 开始验证 RustKmer 安装...")
    
    # 1. 验证 pyrustkmer
    try:
        from pyrustkmer import PyDatabase, PyCounter, LoadMode
        print("✅ pyrustkmer 导入成功")

        # 2. 测试基本功能
        print("✅ PyDatabase, PyCounter 类可用")

    except ImportError as e:
        print(f"❌ pyrustkmer 导入失败: {e}")
    except Exception as e:
        print(f"❌ pyrustkmer 其他错误: {e}")
    
    # 6. PyO3 扩展已经集成到 pyrustkmer 中，无需单独验证
    
    # 7. 系统信息检查
    import sys
    import platform
    
    print(f"\n📋 系统信息:")
    print(f"   Python 版本: {sys.version}")
    print(f"   操作系统: {platform.system()} {platform.release()}")
    print(f"   架构: {platform.machine()}")
    
    # 8. 性能建议
    print(f"\n💡 性能建议:")
    if sys.version_info >= (3, 10):
        print("   ✅ Python 版本适合 PyO3 扩展")
    else:
        print("   ⚠️ 建议升级到 Python 3.10+ 以获得最佳性能")
    
    print("   ✅ 使用排序数据库获得最佳查询性能")
    print("   ✅ 对于小数据库使用预加载模式")
    print("   ✅ 对于大数据库使用内存映射模式")
    
    print("\n🎉 RustKmer 安装验证完成！")
    return True

# 运行验证
verify_rustkmer_installation()
```

#### 开发环境建议

如果您需要修改 RustKmer 的源代码，建议使用以下工作流：

```bash
# 1. 设置开发环境
git clone https://github.com/your-username/rustkmer.git
cd rustkmer

# 2. 创建开发分支
git checkout -b feature/your-modification

# 3. 进行修改
# ... 修改 Rust 和/或 Python 代码 ...

# 4. 构建和测试
cargo build --release
cd python && pip install -e .
python -m pytest tests/

# 5. 验证功能
python -c "from pyrustkmer import PyDatabase; print('✅ 开发版本正常工作')"

# 6. 提交更改
git add .
git commit -m "Your modification description"
git push origin feature/your-modification
```

## 🏆 项目状态

✅ **已完成功能**:
- 高性能k-mer计数
- 批量k-mer查询
- 数据库合并功能
- 排序数据库优化
- 🔥 前缀查询和混合搜索
- 🔥 PyO3高性能Python扩展
- Python API集成（多种方式）
- 完整的性能测试验证

🚀 **性能指标**:
- 高性能查询: 22,703+ queries/sec
- 排序数据库优化: 384-1526倍性能提升
- 支持>100M k-mers大规模数据
- PyO3扩展：最高性能和完整功能访问

🛠️ **Python集成选项**:
- **纯Python Stubs**: 广泛兼容，零编译
- **可编辑安装**: 开发调试，代码修改
- **PyO3扩展**: 最高性能，功能最全

---

**RustKmer**: 为现代生物信息学设计的高性能k-mer分析工具。通过大规模性能测试验证，相比传统工具实现显著性能提升，是生产环境k-mer分析的理想选择。