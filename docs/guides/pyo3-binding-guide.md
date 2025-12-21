# PyO3 Python Binding 使用指南

本指南展示如何使用 PyO3 Python binding 来执行前缀查询，等价于 Rust 命令行工具的功能。

## 📋 概述

PyO3 Python binding 提供了完整的 Python 接口来使用 RustKmer 的前缀查询功能，包括：

- ✅ 纯前缀查询 (如: `AAAAAAAA`)
- ✅ 混合搜索模式 (如: `AAAAAAAA{N5}AAAAAA`)
- ✅ 批量查询
- ✅ 性能指标监控
- ✅ 详细的错误处理

## 🚀 快速开始

### 1. 构建 PyO3 扩展

```bash
cd rustkmer/pyo3

# 清理环境变量
unset VIRTUAL_ENV
unset CONDA_PREFIX

# 设置构建标志
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3

# 构建
cargo build

# 设置 Python 路径
export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
```

### 2. 测试导入

```python
import rustkmer_pyo3
print("Available classes:", [x for x in dir(rustkmer_pyo3) if not x.startswith('_')])
```

## 📖 使用示例

### 基础用法

#### 基本数据库操作:
```python
import rustkmer_pyo3

# 创建数据库连接
engine = rustkmer_pyo3.PyDatabase(
    "python/tests/test_data/small_test.rkdb", 
    rustkmer_pyo3.LoadMode.Preload
)

# 单个k-mer查询
result = engine.query("GCCGCGG")
if result:
    print(f"找到: {result.count}")

# 批量查询
batch_results = engine.query_batch(["GCCGCGG", "ATCCTGA", "AAAAAAA"])
for kmer, result in batch_results.items():
    print(f"{kmer}: {result.count}")
```

### 完整示例脚本

#### 1. 简单版本 (`simple_prefix_query.py`)

```bash
# 直接对应你的命令
python3 simple_prefix_query.py ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA"
```

#### 2. 完整版本 (`prefix_query_pyo3_binding.py`)

```bash
# 带详细选项的版本
python3 prefix_query_pyo3_binding.py ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA" --with-metrics
```

## 🔧 API 详细说明

### PyDatabase 类

#### 初始化
```python
engine = rustkmer_pyo3.PyDatabase(database_path, load_mode)
```

#### 可用的加载模式
```python
import rustkmer_pyo3

# 预加载模式（推荐用于小数据库）
engine = rustkmer_pyo3.PyDatabase("database.rkdb", rustkmer_pyo3.LoadMode.Preload)

# 内存映射模式（推荐用于大数据库）
engine = rustkmer_pyo3.PyDatabase("database.rkdb", rustkmer_pyo3.LoadMode.MemoryMapped)

# 懒加载模式
engine = rustkmer_pyo3.PyDatabase("database.rkdb", rustkmer_pyo3.LoadMode.Lazy)
```

#### 主要方法

##### 1. 单个k-mer查询
```python
result = engine.query("GCCGCGG")
# 返回: PyQueryResult对象，包含count属性
if result:
    print(f"找到: {result.count}")
```

##### 2. 批量查询
```python
results = engine.query_batch(["GCCGCGG", "ATCCTGA", "AAAAAAA"])
# 返回: 包含所有查询结果的字典
for kmer, result in results.items():
    print(f"{kmer}: {result.count}")
```

##### 3. 数据库信息
```python
print(f"数据库路径: {engine.path}")
print(f"K-mer大小: {engine.kmer_size}")
print(f"加载模式: {engine.load_mode}")

# 获取详细统计信息
stats = engine.get_stats()
print(f"总k-mers: {stats.total_kmers}")
print(f"唯一k-mers: {stats.unique_kmers}")
```

### PyDatabase 高级功能

#### 性能监控
```python
import time

# 监控查询性能
start_time = time.time()
result = engine.query("GCCGCGG")
end_time = time.time()

print(f"查询时间: {(end_time - start_time)*1000:.2f} ms")

# 内存使用监控
memory_usage = engine.get_memory_usage()
print(f"内存使用: {memory_usage}")
```

#### 数据库属性
```python
# 检查数据库状态
print(f"是否已加载: {engine.is_loaded}")
print(f"数据库路径: {engine.path}")
print(f"K-mer大小: {engine.kmer_size}")
print(f"加载模式: {engine.load_mode}")

# 获取所有k-mers（注意：仅用于小数据库）
all_kmers = engine.get_all_kmers()
print(f"数据库中共有 {len(all_kmers)} 个k-mers")
```

## 🎯 模式语法

### 前缀模式
```
AAAAAAAA          # 查找以 AAAAAAAA 开头的 k-mers
ATCGATCG          # 查找以 ATCGATCG 开头的 k-mers
```

### 混合模式
```
AAAAAAAA{N5}AAAAAA      # 前缀 AAAAAAAA + 5个N + 后缀 AAAAAA
ATCG{N3}GCTA           # 前缀 ATCG + 3个N + 后缀 GCTA
A{N2}T{N2}C{N2}G        # 多个N组
```

### 模式解析示例
```python
pattern = "AAAAAAAA{N5}AAAAAA"
info = engine.parse_pattern(pattern)

print(f"原始模式: {pattern}")
print(f"前缀: '{info['prefix']}'")           # AAAAAAAA
print(f"后缀: '{info['suffix']}'")           # AAAAAA  
print(f"N数量: {info['n_count']}")           # 5
print(f"总长度: {info['total_length']}")     # 19
```

## 📊 性能特性

### 内存优化
- 使用内存映射文件访问
- 直接内存块处理 (sorted数据库)
- 批量解码优化

### 查询策略
- **前缀查询**: O(log n) 二分搜索 (sorted数据库)
- **混合查询**: 前缀范围 + 后缀过滤
- **智能策略**: 根据模式自动选择最优方法

### 性能监控
```python
metrics = extended_engine.query_with_metrics("AAAAAAAA{N5}AAAAAA")
print(f"""
查询性能指标:
- 执行时间: {metrics.execution_time_ms} ms
- 总匹配数: {metrics.total_matches}  
- 内存块起始: {metrics.start_index}
- 内存块结束: {metrics.end_index}
- 内存块大小: {metrics.block_size}
""")
```

## 🧪 实际使用示例

### 示例 1: 基础查询
```python
import rustkmer_pyo3

# 加载数据库
engine = rustkmer_pyo3.PyPrefixQuery("~/Data/data/kmer/K19/R1_001.rkdb")

# 查询以 AAAAAAAA 开头的 k-mers
prefix_results = engine.query_prefix_string("AAAAAAAA")
print(f"找到 {len(prefix_results)} 个以 AAAAAAAA 开头的 k-mers")

# 混合搜索
hybrid_results = engine.query_hybrid("AAAAAAAA{N5}AAAAAA")  
print(f"找到 {len(hybrid_results)} 个符合 AAAAAAAA{N5}AAAAAA 模式的 k-mers")
```

### 示例 2: 批量查询
```python
import rustkmer_pyo3

# 创建扩展引擎
extended_engine = rustkmer_pyo3.PyExtendedPrefixQuery("~/Data/data/kmer/K19/R1_001.rkdb")

# 批量查询多个模式
patterns = ["AAAAAAAA", "AAAAAAA{N5}AAAAAA", "ATCG{N3}GCTA"]
batch_results = extended_engine.batch_query(patterns)

# 分析结果
for pattern, metrics in batch_results.items():
    print(f"模式 '{pattern}':")
    print(f"  结果数: {metrics.total_matches}")
    print(f"  执行时间: {metrics.execution_time_ms} ms")
    
    # 显示前3个结果
    sample_results = list(metrics.results.items())[:3]
    for kmer, count in sample_results:
        print(f"    {kmer}: {count}")
```

### 示例 3: 性能比较
```python
import rustkmer_pyo3
import time

engine = rustkmer_pyo3.PyExtendedPrefixQuery("~/Data/data/kmer/K19/R1_001.rkdb")

# 比较不同查询的性能
patterns = [
    "A",           # 短前缀
    "AA",          # 中等前缀  
    "AAAAAAAA",    # 长前缀
    "AAAAAAAA{N5}AAAAAA"  # 混合模式
]

print("性能比较:")
print("-" * 60)
for pattern in patterns:
    start_time = time.time()
    metrics = engine.query_with_metrics(pattern)
    end_time = time.time()
    
    print(f"模式: {pattern:<20} | "
          f"结果: {metrics.total_matches:>6} | "
          f"时间: {metrics.execution_time_ms:>6.2f} ms")
```

## ⚠️ 错误处理

### 常见错误和解决方案

#### 1. 导入错误
```python
# 错误: ModuleNotFoundError: No module named 'rustkmer_pyo3'
# 解决: 确保 PYTHONPATH 设置正确
import os
os.environ['PYTHONPATH'] = '/path/to/rustkmer/pyo3/target/debug:' + os.environ.get('PYTHONPATH', '')
```

#### 2. 数据库文件不存在
```python
try:
    engine = rustkmer_pyo3.PyPrefixQuery("nonexistent.db")
except Exception as e:
    print(f"数据库加载失败: {e}")
```

#### 3. 无效模式
```python
try:
    results = engine.query_hybrid("INVALID{N-1}PATTERN")
except Exception as e:
    print(f"无效模式: {e}")
```

## 🔄 从命令行到 Python 的转换

### Rust 命令
```bash
./target/release/rustkmer prefix-query ~/Data/data/kmer/K19/R1_001.rkdb AAAAAAAA{N5}AAAAAA
```

### Python 等效代码
```python
import rustkmer_pyo3

# 创建查询引擎
engine = rustkmer_pyo3.PyPrefixQuery("~/Data/data/kmer/K19/R1_001.rkdb")

# 执行查询
results = engine.query_hybrid("AAAAAAAA{N5}AAAAAA")

# 处理结果
for kmer, count in results.items():
    print(f"{kmer}\t{count}")
```

## 📚 完整文档

更多详细信息请参考：
- `README.md` - 完整的项目文档
- `PREFIX_QUERY_USAGE_GUIDE.md` - 前缀查询详细指南
- `HYBRID_SEARCH_USAGE.md` - 混合搜索使用说明

## 🤝 贡献

如果你发现问题或有改进建议，请提交 issue 或 pull request。

---

**作者**: RustKmer Team  
**日期**: 2025-12-21  
**版本**: 1.0.0

