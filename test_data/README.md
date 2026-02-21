# RustKmer 统一测试数据

## 📁 目录结构

```
test_data/
├── README.md                    # 本文档
├── databases/                   # 数据库文件 (RKDB 格式)
│   ├── tiny_test.rkdb        # 7.8KB, 396 唯一 k-mers (k=7)
│   ├── small_test.rkdb        # 84KB, 4,091 唯一 k-mers (k=7)
│   ├── medium_test.rkdb       # 156KB, 16,827 唯一 k-mers (k=7)
│   ├── large_test.rkdb        # 160KB, 6,851 唯一 k-mers (k=7)
│   ├── small_test_k33_C.rkdb  # 93KB, 4,091 唯一 k-mers (k=33)
│   ├── test_256_prefix.rkdb  # 256 个前缀测试
│   ├── test_256_prefix_2.rkdb # 256 个前缀测试 (版本 2)
│   ├── test_prefix.rkdb      # 前缀查询测试
│   └── perf_test.rkdb        # 性能测试
├── sequences/                   # 序列文件 (FASTA 格式)
│   ├── tiny_test.fasta        # 747B, 10 个序列 (20-100bp)
│   ├── small_test.fasta       # 7.6KB, 50 个序列 (50-200bp)
│   ├── medium_test.fasta       # 33KB, 100 个序列 (100-500bp)
│   ├── large_test.fasta        # 119KB, 200 个序列 (200-1000bp)
│   ├── k33_test.fasta         # 273B, 5 个 K=33 序列
│   ├── k48_test.fasta         # 413B, 未知
│   ├── k64_test.fasta         # 561B, 未知
│   └── ambiguous_test.fasta   # 308B, 3 个含 N 序列
├── kmers/                       # K-mer JSON 测试数据
│   ├── basic_kmers.json      # 760B, k=21/31 基本测试集
│   ├── edge_cases.json        # 912B, 边界情况测试
│   ├── invalid_sequences.json # 619B, 无效序列测试
│   ├── canonical_pairs.json   # 1.1KB, Canonical k-mer 对
│   └── large_dataset.json    # 未知, 大规模数据集
└── scripts/                      # 测试数据生成脚本
    ├── generate_test_data.py  # 生成随机 FASTA 数据
    └── example_usage.py      # API 使用示例
```

---

## 🎯 设计目标

这个统一的测试数据目录旨在：

1. **数据集中管理**：所有测试数据集中在一个位置
2. **语言无关**：同时支持 Rust CLI 和 Python bindings
3. **CI/CD 友好**：便于自动化测试和性能基准
4. **版本控制**：所有测试数据可追踪和管理
5. **模块化组织**：按类型分类便于查找

---

## 📊 数据文件详情

### 数据库文件 (databases/)

| 文件名 | 大小 | K-mer | 唯一 k-mers | 用途 |
|--------|------|-------|-------------|------|
| `tiny_test.rkdb` | 7.8KB | 7 | 396 | 快速单元测试 |
| `small_test.rkdb` | 84KB | 7 | 4,091 | 小规模功能测试 |
| `medium_test.rkdb` | 156KB | 7 | 16,827 | 中规模性能测试 |
| `large_test.rkdb` | 160KB | 7 | 6,851 | 大规模压力测试 |
| `small_test_k33_C.rkdb` | 93KB | 33 | 4,091 | K=33 边界测试 |
| `test_256_prefix.rkdb` | 未知 | 7 | 256 | 前缀查询测试 |
| `test_256_prefix_2.rkdb` | 未知 | 7 | 256 | 前缀查询测试 v2 |
| `test_prefix.rkdb` | 未知 | 7 | 未知 | 前缀查询测试 |
| `perf_test.rkdb` | 未知 | 7 | 未知 | 性能基准测试 |

**特点**：
- ✅ 所有数据库都是 canonical 模式
- ✅ 所有数据库都是排序的（优化前缀查询性能）
- ✅ K=7 适用于大多数测试场景
- ✅ K=33 用于边界情况测试
- ✅ 随机生成，避免测试数据泄露

### 序列文件 (sequences/)

| 文件名 | 大小 | 序列数 | 序列长度范围 | 用途 |
|--------|------|--------|--------------|------|
| `tiny_test.fasta` | 747B | 10 | 20-100bp | 极速测试 |
| `small_test.fasta` | 7.6KB | 50 | 50-200bp | 基础功能测试 |
| `medium_test.fasta` | 33KB | 100 | 100-500bp | 集成测试 |
| `large_test.fasta` | 119KB | 200 | 200-1000bp | 性能测试 |
| `k33_test.fasta` | 273B | 5 | K=33 | K=33 测试 |
| `k48_test.fasta` | 413B | 未知 | K=48 | K=48 测试 |
| `k64_test.fasta` | 561B | 未知 | K=64 | K=64 边界测试 |
| `ambiguous_test.fasta` | 308B | 3 | 含 N | 模糊查询测试 |

**FASTA 格式示例**：
```fasta
>sequence_0001_length_74
GCCGCGGAGTCCTGTCCTGACATAAGCTATGCGACAGTATATGGCGCACTG
>sequence_0002_length_28
AATTCTCCTTATTGAGGAGCCATGCA
>sequence_0003_length_88
GTTAAGGGTAGCGTCGGTCTAGGCGATTAATGATATCATCCACGTTGACGAGTGCCGCGACCGGCCTATGGCACTCG
```

### K-mer JSON 文件 (kmers/)

| 文件名 | 大小 | 内容 | 用途 |
|--------|------|------|------|
| `basic_kmers.json` | 760B | k=21/31 基本测试集 | 核心功能测试 |
| `edge_cases.json` | 912B | 边界情况 | 边界情况测试 |
| `invalid_sequences.json` | 619B | 无效序列 | 错误处理测试 |
| `canonical_pairs.json` | 1.1KB | Canonical k-mer 对 | Canonical 模式测试 |
| `large_dataset.json` | 未知 | 大规模数据 | 性能和扩展测试 |

**basic_kmers.json 结构**：
```json
{
  "k21": [
    "ATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCT",
    ...
  ],
  "k31": [
    "ATCGATCGATCGATCGATCGATCGATC",
    ...
  ],
  "description": "Basic k-mer sequences for different k-mer sizes"
}
```

### 脚本文件 (scripts/)

| 文件名 | 用途 |
|--------|------|
| `generate_test_data.py` | 生成随机 FASTA 测试数据 |
| `example_usage.py` | API 使用示例 |

---

## 🔧 使用指南

### Rust CLI 使用

#### 查询测试
```bash
# 基础查询
rustkmer query test_data/databases/tiny_test.rkdb GCCGCGG ATCCTGA

# 模糊查询
rustkmer fuzzy-query test_data/databases/tiny_test.rkdb "ATCGNNN" --mutations 2

# 前缀查询
rustkmer prefix-query test_data/databases/tiny_test.rkdb -p AAA

# 统计信息
rustkmer stats test_data/databases/tiny_test.rkdb

# 导出数据库
rustkmer dump test_data/databases/tiny_test.rkdb -o output.txt
```

#### 从 FASTA 创建数据库
```bash
# 使用 tiny_test.fasta 创建数据库
rustkmer count -k 7 -i test_data/sequences/tiny_test.fasta \
  -o test_data/databases/test_tiny.rkdb \
  --canonical --sort

# 使用 large_test.fasta 创建大型数据库
rustkmer count -k 7 -i test_data/sequences/large_test.fasta \
  -o test_data/databases/test_large.rkdb \
  --canonical --sort
```

### Python Binding 使用 (v0.4.0+)

#### 查询测试
```python
from pyrustkmer import PyDatabase, LoadMode

# 加载测试数据库
db = PyDatabase("test_data/databases/tiny_test.rkdb", LoadMode.Preload)

# 查询 k-mer
result = db.query_exact("GCCGCGG")
print(f"Found: {result.found}, Count: {result.count}")

# 前缀查询
matches = db.query_prefix("AAA")
print(f"Prefix matches: {len(matches)}")
```

#### 模糊查询
```python
from pyrustkmer import PyDatabase, PyFuzzyQuery

db = PyDatabase("test_data/databases/tiny_test.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# 模糊查询
result = fuzzy.query_fuzzy("ATCGNNN", max_mutations=2)
print(f"Total matches: {result.total_matches}")

# 获取最佳匹配
top_matches = result.get_top_matches(10)
for match in top_matches:
    print(f"{match.kmer}: {match.count}")
```

#### K-mer 计数 (新功能 v0.4.0)
```python
from pyrustkmer import PyCounter

# 创建计数器
counter = PyCounter(kmer_length=7, canonical=True)

# 添加序列
counter.add_sequence("ATGCGATGCTAGCTAGCT")
stats = counter.get_stats()
print(f"Total: {stats.total_kmers}, Unique: {stats.unique_kmers}")

# 从 FASTA 文件计数
counter.add_from_fasta("test_data/sequences/tiny_test.fasta")
stats = counter.get_stats()
print(f"Processed {stats.total_kmers} k-mers")

# 保存为数据库
counter.save_database("test_data/databases/new_tiny.rkdb")
```

#### 数据库导出 (新功能 v0.4.0)
```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("test_data/databases/tiny_test.rkdb", LoadMode.Preload)

# 导出为文本
db.export_to_file("test_data/output.txt")

# 导出为 JSON
db.export_to_json("test_data/output.json")

# 导出为 CSV
db.export_to_csv("test_data/output.csv")
```

---

## 📊 数据统计总览

| 类别 | 文件数 | 总大小 | 唯一 k-mers |
|------|--------|--------|-------------|
| 数据库 | 10 | ~600KB | ~33,000+ |
| 序列 | 8 | ~130KB | - |
| K-mer JSON | 5 | ~4KB | - |
| 脚本 | 2 | ~4KB | - |
| **总计** | **25** | **~740KB** | **~33,000+** |

---

## 🎯 测试场景映射

### 功能测试
- ✅ **基础查询**: `tiny_test.rkdb` - 396 个 k-mer
- ✅ **前缀查询**: `test_prefix.rkdb` - 前缀匹配测试
- ✅ **模糊查询**: `ambiguous_test.fasta` - 通配符测试
- ✅ **Canonical 模式**: 所有数据库 - 正向/反向互补合并

### 性能测试
- ✅ **小规模**: `small_test.rkdb` - 4,091 k-mers
- ✅ **中规模**: `medium_test.rkdb` - 16,827 k-mers
- ✅ **大规模**: `large_test.rkdb` - 6,851 k-mers
- ✅ **性能基准**: `perf_test.rkdb` - 专用性能测试

### 边界测试
- ✅ **K=33 边界**: `small_test_k33_C.rkdb` - 最大 K=33 的奇数
- ✅ **K=48**: `k48_test.fasta` - 中等 K 长度
- ✅ **K=64**: `k64_test.fasta` - 最大支持 K 长度
- ✅ **无效序列**: `invalid_sequences.json` - 错误处理
- ✅ **边界情况**: `edge_cases.json` - 全 A, 全 T 等

---

## 🚀 CI/CD 集成建议

### GitHub Actions 示例

```yaml
name: Test with Unified Data
on: [push, pull_request]

jobs:
  rust-cli-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build RustKmer
        run: cargo build --release
      - name: Run CLI tests
        run: |
          ./target/release/rustkmer query test_data/databases/tiny_test.rkdb GCCGCGG
          ./target/release/rustkmer stats test_data/databases/tiny_test.rkdb

  python-binding-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build PyO3 bindings
        run: cd pyo3 && maturin develop --release
      - name: Run Python tests
        run: |
          pytest tests/ --data-dir=test_data/
```

---

## 📝 维护建议

### 添加新测试数据

1. **数据库文件**：
   ```bash
   # 放入 test_data/databases/
   rustkmer count -k 7 -i sequences/new.fasta -o test_data/databases/new.rkdb
   ```

2. **序列文件**：
   ```bash
   # 放入 test_data/sequences/
   # 使用 scripts/generate_test_data.py 生成
   ```

3. **更新文档**：在 README.md 中记录新文件的用途

### 版本控制

- ✅ 提交测试数据文件到 Git
- ✅ 大文件（>1MB）考虑使用 Git LFS
- ✅ 在 commit message 中说明数据用途

### 清理策略

- 定期清理临时生成的数据库
- 保留核心测试数据库（tiny, small, medium, large）
- 清理过期的性能测试数据

---

## 🔍 快速参考

### 最常用的测试数据

| 场景 | 数据文件 | CLI 命令 |
|------|---------|----------|
| 快速单元测试 | `databases/tiny_test.rkdb` | `rustkmer query ...` |
| 性能基准测试 | `databases/large_test.rkdb` | `rustkmer query ...` |
| K-mer 计数测试 | `sequences/tiny_test.fasta` | `rustkmer count ...` |
| 模糊查询测试 | `sequences/ambiguous_test.fasta` | 创建数据库后测试 |
| Canonical 模式测试 | 任意数据库 | `rustkmer stats` 检查 canonical 字段 |

### K-mer 大小对照

| K-mer | 数据库文件 | JSON 文件 | 序列文件 |
|-------|----------|----------|----------|
| 7 | ✅ 所有主要数据库 | - | ✅ tiny/small/medium/large |
| 21 | - | ✅ basic_kmers.json (k21) | - |
| 31 | - | ✅ basic_kmers.json (k31) | - |
| 33 | ✅ small_test_k33_C.rkdb | - | ✅ k33_test.fasta |
| 48 | - | - | ✅ k48_test.fasta |
| 64 | - | - | ✅ k64_test.fasta |

---

## 📋 文件清单

### 完整文件列表

```
test_data/
├── README.md
├── databases/
│   ├── tiny_test.rkdb
│   ├── small_test.rkdb
│   ├── medium_test.rkdb
│   ├── large_test.rkdb
│   ├── small_test_k33_C.rkdb
│   ├── test_256_prefix.rkdb
│   ├── test_256_prefix_2.rkdb
│   ├── test_prefix.rkdb
│   └── perf_test.rkdb
├── sequences/
│   ├── tiny_test.fasta
│   ├── small_test.fasta
│   ├── medium_test.fasta
│   ├── large_test.fasta
│   ├── k33_test.fasta
│   ├── k48_test.fasta
│   ├── k64_test.fasta
│   └── ambiguous_test.fasta
├── kmers/
│   ├── basic_kmers.json
│   ├── edge_cases.json
│   ├── invalid_sequences.json
│   ├── canonical_pairs.json
│   └── large_dataset.json
└── scripts/
    ├── generate_test_data.py
    └── example_usage.py
```

---

*最后更新: 2026-01-16*
*版本: v0.4.0*
*目的: 统一测试数据管理，支持 Rust CLI 和 Python bindings*
