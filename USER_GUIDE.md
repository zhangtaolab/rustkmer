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
cargo run --release -- count -k 21 -t 8 --sort -o genome.rkdb genome.fa

# 查询单个k-mer
cargo run --release -- query genome.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询（推荐方式）
cargo run --release -- query genome.rkdb --sequence queries.fa -o results.txt

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

# 编译发布版本
cargo build --release

# 编译后的二进制文件位于
# Linux/macOS: target/release/rustkmer
# Windows: target/release/rustkmer.exe

# 可选：安装到系统路径
cargo install --path .
```

### Docker安装（可选）

```bash
# 构建Docker镜像
docker build -t rustkmer .

# 运行容器
docker run -v $(pwd):/data rustkmer count -k 21 -o /data/output.rkdb /data/input.fa
```

## 核心功能

### 1. K-mer计数 (count)

快速准确地从FASTA/FASTQ文件中计数k-mers。

```bash
# 基本计数
rustkmer count -k 21 -o output.rkdb input.fa

# 多线程计数
rustkmer count -k 21 -t 8 -o output.rkdb input.fa

# 创建排序数据库（推荐）
rustkmer count -k 21 --sort -o sorted.rkdb input.fa

# 规范化k-mer计数（考虑反向互补）
rustkmer count -k 21 -C -o canonical.rkdb input.fa
```

### 2. K-mer查询 (query)

高性能k-mer查询，支持批量处理。

```bash
# 查询单个k-mer
rustkmer query database.rkdb ATGCGATGCTAGCGCTAGCTA

# 批量查询（从FASTA文件）
rustkmer query database.rkdb --sequence queries.fa -o results.txt

# 从标准输入查询
echo -e "ATGCGATGCTAGCGCTAGCTA\nGCTAGCTAGCTAGCTAGCTAC" | rustkmer query database.rkdb -i

# 交互式查询模式
rustkmer query database.rkdb -i
```

### 3. 数据库管理

```bash
# 查看数据库信息
rustkmer info database.rkdb

# 转储数据库内容
rustkmer dump database.rkdb -o kmer_counts.txt

# 验证数据库完整性
rustkmer validate database.rkdb
```

## 命令行参考

### 全局选项

```bash
rustkmer [GLOBAL_OPTIONS] <COMMAND> [COMMAND_OPTIONS]

Global Options:
  -h, --help     显示帮助信息
  -V, --version  显示版本信息
  -q, --quiet    静默模式
  -v, --verbose  详细输出
```

### Count命令

```bash
rustkmer count [OPTIONS] -k <KMER_SIZE> -o <OUTPUT> <INPUT>

Options:
  -k, --kmer-size <KMER_SIZE>     k-mer大小 (必须) [default: 21]
  -t, --threads <THREADS>         线程数量 [default: 系统CPU核心数]
  -s, --hash-size <SIZE>          哈希表大小 (例如: 1G, 500M) [default: 2G]
  -o, --output <FILE>             输出数据库文件 (必须)
  -C, --canonical                 规范化k-mer计数
      --sort                      创建排序数据库 (推荐)
      --no-sort                   创建非排序数据库
      --memory-limit <SIZE>       内存使用限制
  -q, --quiet                     静默模式
  -v, --verbose                   详细输出

Examples:
  # 基本计数
  rustkmer count -k 21 -o genome.rkdb genome.fa

  # 多线程排序计数
  rustkmer count -k 21 -t 8 --sort -o genome_sorted.rkdb genome.fa

  # 规范化计数
  rustkmer count -k 31 -C -s 4G --sort -o genome_k31.rkdb genome.fa
```

### Query命令

```bash
rustkmer query [OPTIONS] <DATABASE> [KMERS]...

Options:
  -s, --sequence <FILE>            从序列文件查询k-mers
  -o, --output <FILE>              输出文件 (stdout)
  -i, --interactive                交互式模式
  -l, --load                       强制预加载数据库到内存
  -L, --no-load                    禁用预加载数据库

Examples:
  # 单个查询
  rustkmer query genome.rkdb ATGCGATGCTAGCGCTAGCTA

  # 批量查询
  rustkmer query genome.rkdb --sequence queries.fa -o results.txt

  # 交互式查询
  rustkmer query genome.rkdb -i
```


## 性能优化指南

### 数据库创建优化

**1. 使用排序数据库（强烈推荐）**

```bash
# ✅ 推荐：创建排序数据库
rustkmer count -k 21 --sort -o sorted.rkdb input.fa

# ❌ 不推荐：非排序数据库
rustkmer count -k 21 --no-sort -o unsorted.rkdb input.fa
```

**性能差异**：排序数据库比非排序数据库快**384-1526倍**。

**2. 合理设置哈希表大小**

```bash
# 小基因组（<1GB）
rustkmer count -k 21 -s 1G --sort -o small.rkdb small.fa

# 大基因组（>1GB）
rustkmer count -k 21 -s 4G --sort -o large.rkdb large.fa

# 超大基因组（>10GB）
rustkmer count -k 21 -s 16G --sort -o huge.rkdb huge.fa
```

**3. 线程数设置**

```bash
# CPU核心数 <= 8
rustkmer count -k 21 -t $(nproc) --sort -o optimal.rkdb input.fa

# CPU核心数 > 8（通常8-12线程最优）
rustkmer count -k 21 -t 12 --sort -o optimal.rkdb input.fa
```

### 查询性能优化

**1. 批量查询优于单个查询**

```bash
# ✅ 推荐：批量查询
rustkmer query database.rkdb --sequence queries.fa -o results.txt

# ❌ 不推荐：循环单个查询
for kmer in $(cat queries.txt); do
    rustkmer query database.rkdb "$kmer"
done
```

**2. 内存管理**

```bash
# 小数据库（<2GB）：预加载到内存
rustkmer query small_db.rkdb --load --sequence queries.fa

# 大数据库（>2GB）：使用内存映射
rustkmer query large_db.rkdb --no-load --sequence queries.fa
```

**3. 查询文件格式优化**

```bash
# ✅ FASTA格式（推荐）
cat > queries.fa << EOF
>query_1
ATGCGATGCTAGCGCTAGCTA
>query_2
GCTAGCTAGCTAGCTAGCTAC
EOF

rustkmer query database.rkdb --sequence queries.fa
```

### 关键性能发现

**性能优化关键**：

- ✅ **使用批量查询获得最佳性能**
- ✅ **批量处理比单个查询快数千倍**
- ✅ **排序数据库提供显著性能提升**

**原因分析**：
1. k-mer查询是内存受限操作，不是CPU受限
2. 线程创建和同步开销超过查询处理时间
3. 多线程竞争内存带宽降低缓存效率

## 使用示例

### 示例1：基因组k-mer分析

```bash
#!/bin/bash
# genome_analysis.sh

# 1. 创建k=21的排序数据库
echo "Creating k=21 database..."
rustkmer count -k 21 -t 12 --sort -o genome_k21.rkdb genome.fa

# 2. 获取数据库统计信息
echo "Database information:"
rustkmer info genome_k21.rkdb

# 3. 查询特定k-mer
echo "Querying specific k-mers..."
rustkmer query genome_k21.rkdb ATGCGATGCTAGCGCTAGCTA
rustkmer query genome_k21.rkdb GCTAGCTAGCTAGCTAGCTAC

# 4. 批量查询分析
echo "Batch query analysis..."
rustkmer query genome_k21.rkdb --sequence research_kmers.fa -o results.txt

# 5. 分析结果
echo "Analysis complete. Results in results.txt"
echo "Total k-mers with counts > 0:"
awk '$2 > 0' results.txt | wc -l
```

### 示例2：比较不同k-mer大小

```bash
#!/bin/bash
# kmer_size_comparison.sh

GENOME="genome.fa"
K_SIZES=(21 31 51)

for k in "${K_SIZES[@]}"; do
    echo "Processing k=$k..."

    # 创建数据库
    rustkmer count -k "$k" -t 8 --sort -o "genome_k${k}.rkdb" "$GENOME"

    # 获取统计信息
    echo "=== k=$k Statistics ==="
    rustkmer info "genome_k${k}.rkdb"

    # 测试查询性能
    echo "Testing query performance..."
    time rustkmer query "genome_k${k}.rkdb" --sequence test_queries.fa > /dev/null
    echo ""
done
```

### 示例3：高通量查询流水线

```bash
#!/bin/bash
# high_throughput_pipeline.sh

INPUT_FASTA="genome.fa"
QUERY_FILE="large_query_set.fa"
OUTPUT_DIR="pipeline_results"
THREADS=12

mkdir -p "$OUTPUT_DIR"

echo "Starting high-throughput k-mer analysis pipeline..."

# 1. 数据库创建（最耗时步骤）
echo "Step 1: Creating sorted k=21 database..."
time rustkmer count -k 21 -t "$THREADS" --sort -o "$OUTPUT_DIR/genome_k21.rkdb" "$INPUT_FASTA"

# 2. 数据库验证
echo "Step 2: Validating database..."
rustkmer info "$OUTPUT_DIR/genome_k21.rkdb" > "$OUTPUT_DIR/database_info.txt"

# 3. 高通量查询
echo "Step 3: Processing queries..."
time rustkmer query "$OUTPUT_DIR/genome_k21.rkdb" --sequence "$QUERY_FILE" -o "$OUTPUT_DIR/query_results.txt"

# 4. 结果分析
echo "Step 4: Analyzing results..."
echo "Total queries processed: $(grep -c '^>' "$QUERY_FILE")"
echo "Queries with non-zero counts: $(awk '$2 > 0' "$OUTPUT_DIR/query_results.txt" | wc -l)"
echo "Top 10 most abundant k-mers:"
sort -k2,2nr "$OUTPUT_DIR/query_results.txt" | head -10 > "$OUTPUT_DIR/top_kmers.txt"
cat "$OUTPUT_DIR/top_kmers.txt"

echo "Pipeline completed successfully!"
echo "Results saved in: $OUTPUT_DIR"
```

## Python集成

### 基本使用

```python
#!/usr/bin/env python3
# rustkmer_basic.py

from pyrustkmer import PyCounter, PyDatabase, LoadMode
from typing import List, Dict

# 1. 创建k-mer计数器
print("Creating k-mer counter...")
counter = PyCounter(k=21, canonical=True, threads=4)

# 2. 从文件计数k-mers
print("Counting k-mers from file...")
counter.count_file("genome.fa")
print(f"Unique k-mers: {counter.get_unique_count()}")
print(f"Total k-mers: {counter.get_total_count()}")

# 3. 保存到数据库
print("Saving to database...")
counter.save_to_database("genome.rkdb", sorted=True)

# 4. 加载数据库
print("Loading database...")
db = PyDatabase("genome.rkdb", load_mode=LoadMode.MemoryMapped)

# 5. 查询单个k-mer
print("Single query:")
result = db.query("ATGCGATGCTAGCGCTAGCTA")
print(f"K-mer: {result.kmer}")
print(f"Count: {result.count}")
print(f"Found: {result.found}")

# 6. 批量查询
print("\nBatch query:")
queries = [
    "ATGCGATGCTAGCGCTAGCTA",
    "GCTAGCTAGCTAGCTAGCTAC",
    "TAGCTAGCTAGCTAGCTAGCA"
]
results = db.query_batch(queries)
for result in results:
    print(f"{result.kmer}: {result.count} (found: {result.found})")

# 7. 获取数据库统计信息
print("\nDatabase statistics:")
stats = db.get_statistics()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Sorted: {stats.is_sorted}")
```

### 高级Python集成

```python
#!/usr/bin/env python3
# advanced_rustkmer.py

import pandas as pd
import numpy as np
from pyrustkmer import PyCounter, PyDatabase, LoadMode
from typing import List

class AdvancedRustKmerAnalyzer:
    """高级RustKmer分析器"""

    def __init__(self, database_path: str, load_mode=LoadMode.MemoryMapped):
        """初始化分析器"""
        self.database_path = database_path
        self.db = PyDatabase(database_path, load_mode=load_mode)
        self.cache = {}  # 简单查询缓存

    def analyze_kmer_distribution(self, queries: List[str]) -> pd.DataFrame:
        """分析k-mer分布"""
        import time
        start_time = time.time()

        # 批量查询
        results = self.db.query_batch(queries)

        # 转换为DataFrame
        data = [
            {'kmer': r.kmer, 'count': r.count, 'found': r.found}
            for r in results
        ]
        df = pd.DataFrame(data)

        # 添加统计信息
        df['log_count'] = np.log10(df['count'] + 1)

        end_time = time.time()
        print(f"Processed {len(queries)} k-mers in {end_time - start_time:.2f} seconds")
        print(f"K-mers with count > 0: {(df['count'] > 0).sum()}")
        print(f"Mean count: {df['count'].mean():.2f}")
        print(f"Median count: {df['count'].median():.2f}")

        return df

    def find_most_abundant_kmers(self, queries: List[str], top_n: int = 10) -> pd.DataFrame:
        """找到最丰富的k-mers"""
        results = self.db.query_batch(queries)
        sorted_results = sorted(results, key=lambda r: r.count, reverse=True)

        top_data = [
            {'rank': i+1, 'kmer': r.kmer, 'count': r.count}
            for i, r in enumerate(sorted_results[:top_n])
        ]
        return pd.DataFrame(top_data)

    def export_results_to_csv(self, results: pd.DataFrame, output_file: str) -> None:
        """导出结果到CSV"""
        # 排序
        df = results.sort_values('count', ascending=False)

        # 添加统计列
        df = df.reset_index(drop=True)
        df['rank'] = range(1, len(df) + 1)
        df['percentile'] = df['rank'] / len(df) * 100

        df.to_csv(output_file, index=False)
        print(f"Results exported to {output_file}")

# 使用示例
def advanced_example():
    """高级使用示例"""

    # 初始化
    analyzer = AdvancedRustKmerAnalyzer('genome_k21.rkdb')

    # 生成测试查询
    print("Generating test queries...")
    test_queries = [
        ''.join(np.random.choice(list('ATGC'), 21))
        for _ in range(10000)
    ]

    # 分析分布
    print("Analyzing k-mer distribution...")
    df = analyzer.analyze_kmer_distribution(test_queries)

    # 统计分析
    print("\nStatistical Analysis:")
    print(df['count'].describe())

    # 最丰富的k-mers
    print("\nTop 10 most abundant k-mers:")
    top_kmers = analyzer.find_most_abundant_kmers(test_queries, top_n=10)
    print(top_kmers)

    # 可视化（如果安装了matplotlib）
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 8))

        plt.subplot(2, 2, 1)
        plt.hist(df['count'], bins=50, log=True)
        plt.title('K-mer Count Distribution')
        plt.xlabel('Count')
        plt.ylabel('Frequency')

        plt.subplot(2, 2, 2)
        plt.hist(df['log_count'], bins=50)
        plt.title('Log K-mer Count Distribution')
        plt.xlabel('Log10(Count + 1)')
        plt.ylabel('Frequency')

        plt.subplot(2, 2, 3)
        plt.plot(df['rank'], df['count'])
        plt.title('K-mer Rank vs Count')
        plt.xlabel('Rank')
        plt.ylabel('Count')
        plt.xscale('log')
        plt.yscale('log')

        plt.subplot(2, 2, 4)
        plt.scatter(range(len(df)), sorted(df['count'], reverse=True), s=1)
        plt.title('K-mer Count Scatter Plot')
        plt.xlabel('Index')
        plt.ylabel('Count')
        plt.yscale('log')

        plt.tight_layout()
        plt.savefig('kmer_analysis.png', dpi=300)
        print("Visualization saved to kmer_analysis.png")

    except ImportError:
        print("Matplotlib not available, skipping visualization")

if __name__ == "__main__":
    advanced_example()
 ```

### 批量处理与性能优化

```python
#!/usr/bin/env python3
# batch_processing.py

import pandas as pd
import numpy as np
from pyrustkmer import PyCounter, PyDatabase, LoadMode
from typing import List
import time

class BatchProcessor:
    """高性能批量处理器"""

    def __init__(self, database_path: str, load_mode=LoadMode.MemoryMapped):
        """初始化处理器"""
        self.db = PyDatabase(database_path, load_mode=load_mode)

    def process_large_batch(self, queries: List[str],
                         batch_size: int = 10000) -> pd.DataFrame:
        """处理大规模查询批次"""
        print(f"Processing {len(queries)} queries in batches of {batch_size}...")

        all_results = []
        start_time = time.time()

        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(queries) + batch_size - 1) // batch_size

            print(f"  Processing batch {batch_num}/{total_batches}...")

            batch_start = time.time()
            results = self.db.query_batch(batch)
            batch_time = time.time() - batch_start

            # 转换为列表
            batch_data = [
                {'kmer': r.kmer, 'count': r.count, 'found': r.found}
                for r in results
            ]
            all_results.extend(batch_data)

            print(f"    Batch time: {batch_time:.2f}s, "
                  f"Queries/sec: {len(batch)/batch_time:.0f}")

        total_time = time.time() - start_time
        df = pd.DataFrame(all_results)

        print(f"\nTotal time: {total_time:.2f}s")
        print(f"Overall throughput: {len(queries)/total_time:.0f} queries/sec")
        print(f"Found k-mers: {(df['count'] > 0).sum()}")

        return df

    def filter_and_export(self, df: pd.DataFrame,
                       min_count: int = 10,
                       output_file: str = None) -> pd.DataFrame:
        """过滤和导出结果"""
        # 过滤
        filtered = df[df['count'] >= min_count].copy()

        # 排序
        filtered = filtered.sort_values('count', ascending=False)

        # 添加排名
        filtered = filtered.reset_index(drop=True)
        filtered['rank'] = range(1, len(filtered) + 1)

        if output_file:
            filtered.to_csv(output_file, index=False)
            print(f"Exported {len(filtered)} results to {output_file}")

        return filtered

# 使用示例
def batch_processing_example():
    """批量处理示例"""

    # 初始化
    processor = BatchProcessor('genome_k21.rkdb')

    # 生成大规模测试数据
    print("Generating large-scale test data...")
    large_queries = [
        ''.join(np.random.choice(list('ATGC'), 21))
        for _ in range(100000)  # 10万查询
    ]

    # 批量处理
    print("\nStarting batch processing...")
    results_df = processor.process_large_batch(large_queries, batch_size=5000)

    # 过滤和导出
    print("\nFiltering and exporting...")
    filtered = processor.filter_and_export(
        results_df,
        min_count=5,
        output_file='filtered_results.csv'
    )

    # 显示统计
    print(f"\nResults summary:")
    print(f"  Total queries: {len(large_queries)}")
    print(f"  Unique k-mers found: {(results_df['count'] > 0).sum()}")
    print(f"  After filtering (count >= 5): {len(filtered)}")
    print(f"  Top 5 most abundant:")
    print(filtered.head(5).to_string(index=False))

if __name__ == "__main__":
    batch_processing_example()
```

## 常见问题

### Q1: 排序数据库vs非排序数据库的性能差异？

**A**: 性能差异巨大，排序数据库快384-1526倍：
```bash
# 排序数据库（推荐）
rustkmer count -k 21 --sort -o sorted.rkdb input.fa

# 非排序数据库（不推荐）
rustkmer count -k 21 --no-sort -o unsorted.rkdb input.fa
```

**原因**：排序数据库使用二分查找(O(log n))，非排序数据库使用线性查找(O(n))。

### Q2: 如何选择合适的k-mer大小？

**A**: 根据应用场景选择：
- **k=21**: 适用于大多数应用，平衡特异性和敏感度
- **k=31**: 适用于复杂基因组，提高特异性
- **k=51**: 适用于高度重复基因组，避免模糊匹配

### Q3: 内存使用如何优化？

**A**: 根据数据大小调整：
```bash
# 小基因组(<1GB)
rustkmer count -k 21 -s 1G --sort -o output.rkdb input.fa

# 大基因组(1-10GB)
rustkmer count -k 21 -s 4G --sort -o output.rkdb input.fa

# 超大基因组(>10GB)
rustkmer count -k 21 -s 16G --sort -o output.rkdb input.fa
```

### Q4: 如何处理超大文件？

**A**: 分块处理策略：
```bash
# 分割大文件
split -l 1000000 huge_input.fa chunk_

# 分别处理每个块
for chunk in chunk_*; do
    rustkmer count -k 21 --sort -o "${chunk}.rkdb" "$chunk"
done

# 合并数据库（如果支持）
rustkmer merge -o merged.rkdb chunk_*.rkdb
```

### Q5: 如何验证结果准确性？

**A**: 交叉验证方法：
```bash
# 使用rustkmer创建数据库
rustkmer count -k 21 --sort -o output.rkdb input.fa

# 查询验证
rustkmer query output.rkdb ATGCGATGCTAGCGCTAGCTA
```

### Q6: 数据库文件大小？

**A**: 取决于基因组大小和k-mer数量：
- **人类基因组(~3GB)**: k=21排序数据库约3-4GB
- **细菌基因组(~5MB)**: k=21排序数据库约50-100MB
- **估算公式**: 约1-1.5倍原始FASTA文件大小

---

更多技术细节和性能基准测试，请参考：
- [性能分析报告](specs/003-parallel-query/LARGE_SCALE_PERFORMANCE_ANALYSIS.md)
- [21-mer多线程性能分析](specs/003-parallel-query/21MER_PERFORMANCE_ANALYSIS.md)
- [性能优化建议](specs/003-parallel-query/PERFORMANCE_RECOMMENDATIONS.md)