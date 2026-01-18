# RustKmer User Guide

高性能的k-mer计数和查询工具，专为现代生物信息学应用设计。

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [核心功能](#核心功能)
- [命令行参考](#命令行参考)
- [性能优化指南](#性能优化指南)
- [使用示例](#使用示例)
- [Python集成](#python集成)
- [常见问题](#常见问题)

## 快速开始

### 基本使用

```bash
# 编译项目
cargo build --release

# 计数k-mers（推荐使用排序数据库）
./target/release/rustkmer count -k 21 -t 8 --sort -o genome.rkdb genome.fa

# 查询单个k-mer
./target/release/rustkmer query genome.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询（推荐方式）
./target/release/rustkmer query genome.rkdb --sequence queries.fa -o results.txt

# 使用测试数据验证功能
./target/release/rustkmer query python/tests/test_data/small_test.rkdb GCCGCGG
```

## 安装

### 系统要求

- **操作系统**: Linux, macOS, Windows
- **Rust版本**: 1.80+ (推荐使用最新稳定版)
- **内存**: 建议8GB+用于大型基因组
- **存储**: 足够空间存储数据库文件

### 编译安装

```bash
# 克隆项目
git clone https://github.com/your-repo/rustkmer.git
cd rustkmer

# 编译（推荐发布模式以获得最佳性能）
cargo build --release

# 运行测试
cargo test

# 安装（可选）
cargo install --path .
```

## 核心功能

### 1. K-mer计数

- **功能**: 从FASTA/FASTQ文件计数k-mer
- **特性**: 支持排序、并行处理、内存优化
- **输出**: 高效的二进制RKDB格式

```bash
# 基本计数
rustkmer count -k 21 -i genome.fa -o genome.rkdb

# 排序数据库（推荐，用于高效查询）
rustkmer count -k 21 --sort -i genome.fa -o genome_sorted.rkdb

# 统计k-mer频率
rustkmer count -k 21 --stats -i genome.fa -o genome.rkdb
```

### 2. K-mer查询

- **精确查询**: 快速查找特定k-mer
- **批量查询**: 支持多k-mer同时查询
- **模糊查询**: 支持N通配符匹配

```bash
# 单个查询
rustkmer query database.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询
rustkmer query database.rkdb --sequence queries.fa --output results.txt

# 模糊查询（N通配符）
rustkmer fuzzy-query database.rkdb "ATCGNNNGTAC" --max-mismatches 1
```

### 3. 前缀查询

- **高效前缀匹配**: 利用排序数据库快速查找
- **混合搜索**: 支持前缀+通配符+后缀模式
- **内存块优化**: 显著提升查询性能

```bash
# 纯前缀查询
rustkmer prefix-query database.rkdb "ATCGATCG"

# 混合搜索模式
rustkmer prefix-query database.rkdb "ATCG{N5}GTAC"

# 性能分析
rustkmer prefix-query database.rkdb "ATCG{N5}GTAC" --profile
```

### 4. 数据库操作

- **合并**: 多个数据库合并为单一文件
- **导出**: 转换为人类可读格式
- **统计**: 详细的数据库信息

```bash
# 合并数据库
rustkmer merge database1.rkdb database2.rkdb --output merged.rkdb

# 导出数据
rustkmer dump database.rkdb --output kmers.txt

# 数据库信息
rustkmer stats database.rkdb
```

## 命令行参考

### count - K-mer计数

```bash
rustkmer count [选项] -i <输入文件> -o <输出文件>

主要选项:
  -k, --kmer-size <K>           K-mer长度 (默认: 21)
  -t, --threads <N>             并行线程数 (默认: CPU核心数)
  --canonical                  使用规范k-mer (默认: false)
  --min-count <N>              最小k-mer计数过滤 (默认: 1)
  --max-count <N>              最大k-mer计数过滤
  --sort                       排序输出数据库 (推荐)
  --stats                      生成统计信息
  -i, --input <文件>            输入序列文件 (FASTA/FASTQ)
  -o, --output <文件>           输出RKDB文件
```

### query - K-mer查询

```bash
rustkmer query [选项] <数据库> [k-mer...]

主要选项:
  -s, --sequence <文件>         查询序列文件
  -o, --output <文件>           输出结果文件
  -f, --format <格式>           输出格式 (table/json/csv/tsv) (默认: table)
  --quiet                      静默模式 (默认: false)
  --verbose                    详细输出 (默认: false)
```

### fuzzy-query - 模糊查询

```bash
rustkmer fuzzy-query [选项] <数据库> <模式>

主要选项:
  -m, --max-mismatches <N>      最大错配数 (默认: 0)
  --max-variants <N>           最大变体数 (默认: 10000)
  --profile                    性能分析 (默认: false)
```

### prefix-query - 前缀查询

```bash
rustkmer prefix-query [选项] <数据库> <前缀>

主要选项:
  --format <格式>              输出格式 (table/json/csv/tsv) (默认: table)
  --output <文件>              输出文件
  --min-count <N>              最小计数过滤
  --max-count <N>              最大计数过滤
  --profile                    性能分析 (默认: false)
  --verbose                    详细输出 (默认: false)
  --quiet                      静默模式 (默认: false)
```

### merge - 数据库合并

```bash
rustkmer merge [选项] <数据库1> <数据库2>...

主要选项:
  -o, --output <文件>           合并后输出文件
  --stats                      显示统计信息
```

### dump - 数据库导出

```bash
rustkmer dump [选项] <数据库>

主要选项:
  -o, --output <文件>           输出文件 (默认: stdout)
  -f, --format <格式>           输出格式 (default/fasta/sequence) (默认: default)
  --min-count <N>              最小计数过滤
  --max-count <N>              最大计数过滤
```

### stats - 数据库统计

```bash
rustkmer stats [选项] <数据库>

主要选项:
  --json                       JSON格式输出 (默认: false)
  --verbose                    详细统计 (默认: false)
```

## 性能优化指南

### 1. 数据库排序

**强烈推荐**对大型基因组使用排序数据库：

```bash
# 创建排序数据库
rustkmer count -k 21 --sort -i genome.fa -o genome_sorted.rkdb

# 前缀查询在排序数据库上快10-100倍
rustkmer prefix-query genome_sorted.rkdb "ATCGATCG"
```

### 2. 线程优化

根据系统配置调整线程数：

```bash
# 自动检测CPU核心
rustkmer count -k 21 -t $(nproc) -i genome.fa -o genome.rkdb

# 内存限制时的线程设置
rustkmer count -k 31 -t 4 -i genome.fa -o genome.rkdb  # 内存友好
```

### 3. 内存使用优化

```bash
# 对于内存受限的系统
rustkmer count -k 21 --min-count 2 -i genome.fa -o genome.rkdb

# 分批处理大文件
split -l 1000000 large_genome.fa batch_
for file in batch_*; do
    rustkmer count -k 21 -i "$file" -o "batch_$(basename "$file").rkdb"
done
rustkmer merge batch_*.rkdb --output final.rkdb
```

## 使用示例

### 示例1: 人类基因组分析

```bash
# 1. 创建排序的21-mer数据库
rustkmer count -k 21 --sort -t 16 -i human_genome.fa -o human_k21.rkdb

# 2. 查询特定基因序列
rustkmer query human_k21.rkdb ATGCGATGCTAGCGCTAGCTA

# 3. 查找启动子区域
rustkmer prefix-query human_k21.rkdb "TATAAA"

# 4. 生成统计报告
rustkmer stats human_k21.rkdb --verbose
```

### 示例2: 宏基因组学分析

```bash
# 1. 计数多个样本
for sample in sample1.fa sample2.fa sample3.fa; do
    rustkmer count -k 21 --sort -i "$sample" -o "${sample%.fa}.rkdb"
done

# 2. 合并所有样本
rustkmer merge *.rkdb --output combined.rkdb

# 3. 查找共有k-mer
rustkmer prefix-query combined.rkdb "ATCGATCG" --min-count 3
```

### 示例3: 病毒基因组变异分析

```bash
# 1. 创建参考数据库
rustkmer count -k 19 --sort -i sars_cov2_ref.fa -o sars_k19.rkdb

# 2. 模糊查询变体
rustkmer fuzzy-query sars_k19.rkdb "ATCG{N5}GTAC" --profile

# 3. 前缀查询分析
rustkmer prefix-query sars_k19.rkdb "ATCG{N3}GTAC" --output variants.txt
```

## Python集成

### 安装Python绑定

```bash
cd rustkmer/pyo3
cargo build --release
export PYTHONPATH="$PWD/target/debug:$PYTHONPATH"
```

### 基本使用

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery, PyDatabase

# 加载数据库
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 精确查询
result = db.query_kmer("ATGCGATGCTAGCGCTAGCTA")
if result:
    print(f"Found: {result.count}")

# 前缀查询
prefix_results = db.extract_by_prefix("ATCGATCG")
print(f"Found {len(prefix_results)} k-mers starting with ATCGATCG")

# 混合搜索
hybrid_results = db.query_hybrid("ATCG{N5}GTAC")
```

### 批量处理

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery, PyDatabase
from pathlib import Path

# 批量查询多个序列
query_file = "queries.fa"
output_dir = Path("results")
output_dir.mkdir(exist_ok=True)

db = PyDatabase("genome.rkdb", LoadMode.Preload)
    # 读取查询序列
    with open(query_file) as f:
        queries = [line.strip() for line in f if line.startswith('>')]
    
    # 批量查询
    for query in queries:
        result = db.query_kmer(query)
        output_file = output_dir / f"{query}.txt"
        with open(output_file, 'w') as out:
            if result:
                out.write(f"{query}\t{result.count}\n")
```

## 常见问题

### Q: 内存不足怎么办？

**A**: 
1. 减少k-mer长度: `-k 19` instead of `-k 31`
2. 增加最小计数过滤: `--min-count 2`
3. 分批处理大文件
4. 减少线程数: `-t 4`

```bash
# 内存友好的计数
rustkmer count -k 19 --min-count 2 -t 4 -i large_genome.fa -o genome.rkdb
```

### Q: 查询速度太慢怎么办？

**A**: 
1. 使用排序数据库: `--sort` during counting
2. 对于前缀查询，使用排序数据库可提升10-100倍性能
3. 考虑使用更长的k-mer减少匹配数量

### Q: 数据库文件太大怎么办？

**A**: 
1. 使用更高的最小计数过滤
2. 考虑更大的k-mer长度
3. 压缩输出（RKDB格式本身已高度压缩）

```bash
# 创建紧凑的数据库
rustkmer count -k 25 --min-count 5 --sort -i genome.fa -o compact.rkdb
```

### Q: 如何验证数据库质量？

**A**: 
1. 查看统计信息: `rustkmer stats database.rkdb`
2. 检查k-mer分布
3. 验证已知序列

```bash
# 详细统计
rustkmer stats database.rkdb --verbose

# 导出部分数据进行手动验证
rustkmer dump database.rkdb --min-count 100 | head -100
```

### Q: 模糊查询生成了太多变体？

**A**: 
1. 检查模式复杂度: `AAAAA{N10}TTTTT` 会生成4^10个变体
2. 使用前缀查询替代: `ATCG{N3}GTAC` → `ATCG{N3}GTAC`
3. 设置变体上限: `--max-variants 1000`

---

## 支持和反馈

- **GitHub Issues**: 报告bug和功能请求
- **文档**: 查看在线文档获取更多信息
- **社区**: 参与讨论和分享使用经验

**版本**: 1.0.0  
**最后更新**: 2025-12-21

