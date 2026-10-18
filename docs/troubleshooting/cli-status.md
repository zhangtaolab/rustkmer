# 📋 当前前缀、后缀和混合匹配的命令状况

## ✅ **现状：prefix-query 命令已实现**

目前CLI**已提供 `prefix-query` 命令**（定义于 `src/cli/args.rs` 的 `PrefixQuery` 变体，`src/main.rs` 已接入分发），支持高效前缀匹配和 `--hybrid` 混合模式；独立的后缀查询（suffix-query）与智能查询（smart-query）命令暂未提供。现有的相关命令是：

| 命令 | 功能 | 是否支持高效前缀/后缀匹配 |
|------|------|--------------------------|
| `prefix-query` | 高效前缀/混合模式查询 | ✅ 排序数据库范围定位，支持 `-p/--pattern`、`-x/--prefix`、`--hybrid` |
| `query` | 精确k-mer查询 | ❌ 仅支持精确匹配 |
| `fuzzy-query` | 模糊查询 (N通配符) | ❌ 生成所有变体，效率低 |
| `dump` | 数据库导出 | ❌ 导出全部数据 |

## 📝 **当前可用的 workaround**

前缀模式请直接使用已实现的 `rustkmer prefix-query <DATABASE> -p <PREFIX>`；以下workaround主要针对尚无专门命令的场景：

### 1. **使用 fuzzy-query (效率低)**
```bash
# AAAANNN 模式 - 实际会生成64个变体
rustkmer fuzzy-query database.rkdb "AAAANNN" -m 0

# NNNAAA 模式 - 实际会生成64个变体  
rustkmer fuzzy-query database.rkdb "NNNAAA" -m 0

# AAANNNAAA 模式 - 实际会生成64个变体
rustkmer fuzzy-query database.rkdb "AAANNNAAA" -m 0
```

#### 验证 fuzzy-query 的效率问题：
```bash
# 检查生成的变体数量
rustkmer fuzzy-query database.rkdb "AAAANNN" --profile -q
# 输出会显示: "Generated 64 variants" (效率低下)
```

### 2. **使用 dump + grep (效率极低)**
```bash
# 导出全部数据然后过滤 (不推荐，内存和时间消耗巨大)
rustkmer dump database.rkdb | grep "^AAAA" > prefix_matches.txt
rustkmer dump database.rkdb | grep "AAA$" > suffix_matches.txt
```

### 3. **临时Python脚本解决方案**
由于Python API集成还在完善中，可以创建临时脚本：
```python
# prefix_query_temp.py
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery, PyDatabase

def prefix_query(database_path, prefix):
    # 这里可以使用数据库的迭代查询功能
    # 暂时需要等待完整的API集成
    pass
```

## 🚀 **建议的新命令设计**

基于我们的高效算法实现，`prefix-query` 已落地，其余命令为建议设计：

### 命令1: prefix-query (✅ 已实现)
```bash
# 基本语法 (-p/--pattern 指定前缀模式)
rustkmer prefix-query <DATABASE> -p <PREFIX>

# 示例
rustkmer prefix-query database.rkdb -p "AAATT"
rustkmer prefix-query database.rkdb -p "AAATT" -f json -o results.txt

# 显式前缀 (-x/--prefix，与 -p 互斥)
rustkmer prefix-query database.rkdb -x "AAATT"

# 混合模式 (--hybrid 需配合 -p，支持 ATAC{N5}ACAC 这类内部通配符模式)
rustkmer prefix-query database.rkdb -p "ATAC{N5}ACAC" --hybrid
```

### 命令2: suffix-query  
```bash
# 基本语法
rustkmer suffix-query <DATABASE> <SUFFIX>

# 示例
rustkmer suffix-query database.rkdb "AAA"
rustkmer suffix-query database.rkdb "AAA" --verbose
```

### 命令3: hybrid-query
```bash
# 基本语法
rustkmer hybrid-query <DATABASE> <PATTERN>

# 示例 - 自动选择最优策略
rustkmer hybrid-query database.rkdb "AAANNNAAA"

# 强制使用特定策略
rustkmer hybrid-query database.rkdb "AAAANNN" --force-prefix
rustkmer hybrid-query database.rkdb "NNNAAA" --force-suffix
```

### 命令4: smart-query (推荐)
```bash
# 智能查询，自动选择最优策略
rustkmer smart-query <DATABASE> <PATTERN>

# 示例
rustkmer smart-query database.rkdb "AAANNNAAA"
rustkmer smart-query database.rkdb "AAANNNAAA" --profile
```

## 📈 **性能对比预期**

| 查询类型 | 当前方式 (fuzzy-query) | 新命令方式 | 效率提升 |
|----------|------------------------|------------|----------|
| **AAAANNN** | 生成64个变体，查询64次 | 前缀匹配，1次查询 | **64x** |
| **NNNAAA** | 生成64个变体，查询64次 | 后缀匹配，1次查询 | **64x** |
| **AAANNNAAA** | 生成64个变体，查询64次 | 混合匹配，1-2次查询 | **32x** |

## 🛠️ **实现状态总结**

### ✅ **已完成**
- Rust核心算法实现 (prefix_query.rs, prefix_query_optimized.rs, suffix_query.rs)
- 智能策略选择算法
- 性能分析和效率对比
- 前缀查询CLI命令 `prefix-query` (含 `--hybrid` 混合模式)

### 🔄 **进行中**
- Python API集成 (部分完成)

### ❌ **待实现**
- 后缀查询CLI命令
- 独立混合查询CLI命令 (混合查询功能已可通过 `prefix-query --hybrid` 使用)
- 智能查询CLI命令

## 💡 **临时解决方案**

在后缀、智能查询等其余CLI命令实现之前，可以通过以下方式体验高效算法：

1. **使用 prefix-query CLI 命令** (前缀与 `--hybrid` 混合模式已实现)
2. **使用Python API** (`extract_by_prefix`、`extract_by_pattern` 已可用)
3. **使用Rust测试代码** (临时验证)
4. **性能基准测试** (证明效率优势)

## 🎯 **结论**

**`prefix-query` CLI命令已经实现**（含 `--hybrid` 混合模式），后缀查询（suffix-query）和智能查询（smart-query）命令尚未提供，但对应核心算法已经在Rust层实现并验证高效。

**建议优先实现 `smart-query` 命令**，因为它能自动选择最优策略，对用户最友好。

## 📞 **下一步行动**

如需快速体验高效算法，可以：
1. 直接使用 `rustkmer prefix-query <DATABASE> -p <PREFIX>` (已实现)
2. 使用Python API (`extract_by_prefix`、`extract_by_pattern` 已可用)
3. 参与suffix-query、smart-query命令的开发实现


