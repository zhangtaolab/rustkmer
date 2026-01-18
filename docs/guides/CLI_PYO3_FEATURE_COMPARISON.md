# RustKmer CLI vs PyO3 Binding 功能对比分析

## 📊 概述

**CLI 实现的子命令**: 8 个  
**PyO3 实现的功能模块**: 6 个  
**核心功能缺失**: K-mer 计数工具不完整  
**部分功能缺失**: 统计、输出格式、批量操作等

---

## 🔴 完全缺失的功能

### 1. **count** - 完整的 K-mer 计数工具 ❌

**CLI 功能**:
- 从序列文件统计 k-mer 生成数据库
- 支持多文件输入和目录模式
- Canonical k-mer 模式
- 可配置哈希表大小
- Text/Binary 输出格式
- 可选排序

**PyO3 现状**:
- ✅ `PyKmerCounter` 类存在但**标记为简化状态**
- ✅ `add_kmer()`, `get_stats()`, `is_empty()` 方法存在
- ❌ 无法从文件读取序列
- ❌ 无 FASTA/FASTQ 解析功能
- ❌ 无法生成数据库文件
- ❌ 无批量处理能力

**影响**: 无法在 Python 中创建数据库，必须使用 CLI 工具

---

### 2. **dump** - 数据库导出功能 ❌

**CLI 功能**:
- `rustkmer dump database.rkdb -o output.txt`
- 快速导出二进制数据库为可读文本
- 每行一个 k-mer 和计数

**PyO3 现状**:
- ✅ `db.get_all_kmers()` - 返回所有 k-mer
- ✅ `db.dump(limit, offset)` - 支持分页
- ❌ 无法直接写入文件
- ❌ 无专用导出方法
- ❌ 需要手动遍历并写入

**影响**: 导出需要额外代码编写，不如 CLI 便捷

---

## 🟡 部分缺失的功能

### 3. **query** - 查询方式不完整 ⚠️

**CLI 功能**:
```bash
# 多种查询模式
rustkmer query database.rkdb AAAAAAA TTTTTTT      # 直接指定
rustkmer query database.rkdb -s sequence.fasta     # 从序列文件
rustkmer query database.rkdb -b batch.txt          # 批量文件
rustkmer query database.rkdb -i                    # 交互式模式
```

**PyO3 现状**:
```python
✅ db.query_exact(kmer)         # 单个查询
✅ db.query_exact_batch(kmers)   # 批量查询
❌ 从文件查询（需手动读取文件）
❌ 交互式查询（需自己实现）
```

**影响**: 文件查询和交互式查询需要额外开发

---

### 4. **stats** - 统计功能简化 ⚠️

**CLI 功能**:
```bash
# 多种输出格式
rustkmer stats database.rkdb -f text
rustkmer stats database.rkdb -f json
rustkmer stats database.rkdb -f csv
rustkmer stats database.rkdb -f tsv

# 详细选项
rustkmer stats database.rkdb --detailed
rustkmer stats database.rkdb --max-bins 1000
rustkmer stats database.rkdb --approximate
rustkmer stats database.rkdb --progress
```

**PyO3 现状**:
```python
stats = db.get_stats()
✅ stats.kmer_size
✅ stats.total_kmers
✅ stats.unique_kmers
✅ stats.file_size
✅ stats.is_sorted
✅ stats.canonical

❌ 无详细频率分布
❌ 无多种输出格式
❌ 无近似计算选项
❌ 无进度报告
```

**影响**: 无法获取频率分布等高级统计信息

---

### 5. **fuzzy-query** - 输出格式缺失 ⚠️

**CLI 功能**:
```bash
# 多种输出格式
rustkmer fuzzy-query database.rkdb "ANNNNNN" -f table
rustkmer fuzzy-query database.rkdb "ANNNNNN" -f json
rustkmer fuzzy-query database.rkdb "ANNNNNN" -f csv
rustkmer fuzzy-query database.rkdb "ANNNNNN" -f tsv
rustkmer fuzzy-query database.rkdb "ANNNNNN" -o output.txt
```

**PyO3 现状**:
```python
✅ fuzzy = PyFuzzyQuery(db)
✅ result = fuzzy.query_fuzzy(pattern, max_mutations)
✅ result.matches, result.total_matches
✅ result.get_top_matches()
✅ result.get_matches_by_distance()

❌ 无格式化输出方法
❌ 无直接文件输出
❌ 需要手动格式化为 table/json/csv/tsv
```

**影响**: 需要额外代码来格式化和输出结果

---

### 6. **fuzzy-query-batch** - 无批量查询接口 ⚠️

**CLI 功能**:
```bash
# 专用批量查询
rustkmer fuzzy-query-batch database.rkdb -s queries.txt
rustkmer fuzzy-query-batch database.rkdb -s queries.txt -f json -o output.json
rustkmer fuzzy-query-batch database.rkdb -s queries.txt --progress
rustkmer fuzzy-query-batch database.rkdb -s queries.txt --fail-fast
```

**PyO3 现状**:
```python
# 需要手动实现批量查询
fuzzy = PyFuzzyQuery(db)

# 手动读取文件
with open('queries.txt') as f:
    queries = f.readlines()

# 手动批量处理
for query in queries:
    result = fuzzy.query_fuzzy(query.strip(), max_mutations)
    # 手动处理每个结果

❌ 无专用批量查询方法
❌ 无进度报告
❌ 无 fail-fast 选项
❌ 需要大量样板代码
```

**影响**: 批量查询需要大量手动实现代码

---

### 7. **merge** - 合并选项不完整 ⚠️

**CLI 功能**:
```bash
# 丰富的合并选项
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb

# 高级选项
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb \
    --check-compatibility              # 兼容性检查
    --max-memory "32GB"               # 内存控制
    --num-threads 8                   # 线程控制
    --use-prefix-cache                # 缓存策略
    --batch-size 100000               # 批量大小
    --merge-mode streaming            # 合并策略
    --keep-intermediate               # 保留中间文件
    --temp-dir /tmp/merge            # 临时目录
```

**PyO3 现状**:
```python
# 简单静态方法
PyDatabase.merge(["db1.rkdb", "db2.rkdb"], "merged.rkdb")

❌ 无兼容性检查
❌ 无内存控制
❌ 无线程控制
❌ 无缓存策略选择
❌ 无合并策略选择
❌ 无临时目录控制
❌ 无中间文件保留
```

**影响**: 大型数据库合并无法优化，可能出现内存不足

---

### 8. **prefix-query** - 格式化输出缺失 ⚠️

**CLI 功能**:
```bash
# 多种输出格式
rustkmer prefix-query database.rkdb -p AAA -f table
rustkmer prefix-query database.rkdb -p AAA -f json
rustkmer prefix-query database.rkdb -p AAA -f csv
rustkmer prefix-query database.rkdb -p AAA -f tsv
rustkmer prefix-query database.rkdb -p AAA -o output.txt
```

**PyO3 现状**:
```python
# 基本查询
query = PyPrefixQuery(database_path)
matches = query.query_prefix("AAA")

# 带指标的扩展查询
ext_query = PyExtendedPrefixQuery(database_path)
metrics = ext_query.query_prefix_metrics("AAA")

✅ matches dict
✅ metrics.execution_time_ms
✅ metrics.total_matches
✅ metrics.start_index, end_index

❌ 无格式化输出
❌ 无直接文件输出
```

**影响**: 需要手动格式化输出

---

## 🔹 特殊功能缺失

### 9. **过滤功能** - 计数范围过滤 ⚠️

**CLI 功能**:
```bash
# 查询时过滤
rustkmer query database.rkdb -i sequence.fasta --min-count 10 --max-count 1000

# 前缀查询时过滤
rustkmer prefix-query database.rkdb -p AAA --min-count 5 --max-count 500
```

**PyO3 现状**:
```python
# 无内置过滤功能
results = db.query_prefix("AAA")

# 需要手动过滤
filtered = {k: v for k, v in results.items() if 5 <= v <= 500}

❌ 无内置过滤参数
❌ 需要后处理
```

**影响**: 需要手动实现过滤逻辑

---

### 10. **交互式选择** - count 命令 ⚠️

**CLI 功能**:
```bash
# 交互式文件选择
rustkmer count -d /path/to/files --select
# 会提示选择哪些文件
```

**PyO3 现状**:
```python
❌ 完全缺失
```

**影响**: 无法实现交互式文件选择

---

### 11. **位置特定突变** - 参数简化 ⚠️

**CLI 功能**:
```bash
# 位置特定突变
rustkmer fuzzy-query database.rkdb "ANNNNNN" \
    --position-mutations "3,4,5:2;6,7:1"
# 表示在位置 3,4,5 允许 2 个突变，位置 6,7 允许 1 个突变
```

**PyO3 现状**:
```python
# 支持但格式不同
query.query_fuzzy_position(
    pattern="ANNNNNN",
    max_mutations=2,
    position_mutations="0,6:1"  # 格式: "positions:limit"
)

⚠️ 格式不如 CLI 灵活（无法指定多个位置组）
⚠️ 参数名称不同
```

**影响**: 参数格式不同，功能不如 CLI 灵活

---

### 12. **性能分析工具** - 缺少 profiling ⚠️

**CLI 功能**:
```bash
# 性能分析
rustkmer fuzzy-query database.rkdb "ANNNNNN" --profile
rustkmer prefix-query database.rkdb -p AAA --profile
```

**PyO3 现状**:
```python
# 部分支持
metrics = ext_query.query_prefix_metrics("AAA")
✅ metrics.execution_time_ms

❌ 无详细 profiling 数据
❌ 无内存使用统计
❌ 无详细性能指标
```

**影响**: 无法进行深入的性能分析

---

### 13. **进度跟踪** - 缺少进度条 ⚠️

**CLI 功能**:
```bash
# 进度条
rustkmer stats database.rkdb --progress
rustkmer fuzzy-query-batch database.rkdb -s queries.txt --progress
```

**PyO3 现状**:
```python
❌ 无进度报告功能
❌ 无法跟踪长时间操作
```

**影响**: 大型操作无进度反馈

---

## 📋 功能完整性对比表

| 功能类别 | CLI 支持 | PyO3 支持 | 缺失程度 |
|---------|---------|-----------|---------|
| **K-mer 计数** | ✅ 完整 | ⚠️ 简化版 | 🔴 高 |
| **精确查询** | ✅ 完整 | ✅ 完整 | 🟢 低 |
| **模糊查询** | ✅ 完整 | ✅ 完整 | 🟢 低 |
| **前缀查询** | ✅ 完整 | ✅ 完整 | 🟢 低 |
| **数据库合并** | ✅ 完整 | ⚠️ 基础版 | 🟡 中 |
| **统计信息** | ✅ 完整 | ⚠️ 基础版 | 🟡 中 |
| **数据库导出** | ✅ 完整 | ⚠️ 基础版 | 🟡 中 |
| **批量查询** | ✅ 完整 | ⚠️ 需手动 | 🟡 中 |
| **输出格式化** | ✅ 4种格式 | ❌ 需手动 | 🟡 中 |
| **文件 I/O** | ✅ 完整 | ❌ 需手动 | 🟡 中 |
| **进度跟踪** | ✅ 完整 | ❌ 缺失 | 🟡 中 |
| **性能分析** | ✅ 完整 | ⚠️ 基础版 | 🟡 中 |
| **交互式模式** | ✅ 支持 | ❌ 缺失 | 🟡 中 |
| **高级合并** | ✅ 完整 | ⚠️ 基础版 | 🟡 中 |

---

## 🎯 关键缺失功能总结

### 🔴 高优先级（严重影响功能）

1. **完整的 K-mer 计数工具**
   - 无法在 Python 中创建数据库
   - 无法从 FASTA/FASTQ 读取序列
   - 必须依赖 CLI 工具

2. **数据库导出功能**
   - 无便捷的导出方法
   - 需要手动实现

### 🟡 中优先级（影响使用便利性）

3. **批量查询接口**
   - 无专用批量查询方法
   - 需要大量样板代码

4. **多种输出格式**
   - 无格式化输出方法
   - 需要手动转换为 JSON/CSV/TSV

5. **高级统计功能**
   - 无频率分布
   - 无详细统计指标

6. **高级合并选项**
   - 无内存/线程控制
   - 无缓存策略选择

### 🟢 低优先级（影响有限）

7. **进度跟踪**
8. **性能分析**
9. **交互式模式**
10. **过滤功能优化**

---

## 💡 建议改进方向

### 短期改进（v0.4.0）
1. 实现 `PyKmerCounter` 的完整功能
2. 添加格式化输出方法（`to_json()`, `to_csv()` 等）
3. 实现数据库导出方法

### 中期改进（v0.5.0）
1. 添加批量查询接口
2. 实现高级统计（频率分布）
3. 添加进度回调支持
4. 扩展合并选项

### 长期改进（v1.0.0）
1. 完整的文件 I/O 支持
2. 交互式模式
3. 性能分析工具
4. 进度条集成

---

## 📚 CLI 子命令详细清单

### 1. count - K-mer 计数
```bash
rustkmer count -k 21 -i input.fasta -o output.rkdb
rustkmer count -k 31 -d /path/to/files --canonical
rustkmer count -k 25 -i file1.fa file2.fq -o output.rkdb --sort
```

### 2. query - K-mer 查询
```bash
rustkmer query database.rkdb AAAAAAA TTTTTTT
rustkmer query database.rkdb -s sequence.fasta
rustkmer query database.rkdb -b batch.txt -o results.txt
```

### 3. stats - 数据库统计
```bash
rustkmer stats database.rkdb
rustkmer stats database.rkdb --detailed -f json -o stats.json
rustkmer stats database.rkdb --approximate
```

### 4. dump - 数据库导出
```bash
rustkmer dump database.rkdb -o output.txt
```

### 5. fuzzy-query - 模糊查询
```bash
rustkmer fuzzy-query database.rkdb "ANNNNNN" -m 2
rustkmer fuzzy-query database.rkdb "ATA{N5}ACAC" --position-mutations "0,6:1"
```

### 6. fuzzy-query-batch - 批量模糊查询
```bash
rustkmer fuzzy-query-batch database.rkdb -s queries.txt -f json -o results.json
rustkmer fuzzy-query-batch database.rkdb -s queries.txt --progress
```

### 7. merge - 数据库合并
```bash
rustkmer merge -i db1.rkdb db2.rkdb -o merged.rkdb
rustkmer merge -i *.rkdb -o all.rkdb --use-prefix-cache
```

### 8. prefix-query - 前缀查询
```bash
rustkmer prefix-query database.rkdb -p AAA
rustkmer prefix-query database.rkdb -p "ATA{N5}ACAC" --hybrid
```

---

## 📖 PyO3 API 快速参考

### 核心类
```python
import pyrustkmer

# 数据库操作
db = pyrustkmer.PyDatabase("database.rkdb", pyrustkmer.LoadMode.Preload)
result = db.query_exact("AAAAAAA")
stats = db.get_stats()

# 模糊查询
fuzzy = pyrustkmer.PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ANNNNNN", max_mutations=2)

# 前缀查询
prefix = pyrustkmer.PyPrefixQuery("database.rkdb")
matches = prefix.query_prefix("AAA")

# 数据库合并
pyrustkmer.PyDatabase.merge(["db1.rkdb", "db2.rkdb"], "merged.rkdb")
```

### 当前限制
- ❌ 无法从 FASTA/FASTQ 创建数据库
- ❌ 无批量查询接口
- ❌ 无格式化输出方法
- ❌ 无进度跟踪

---

*文档生成时间: 2026-01-16*
*版本: 0.3.0*
