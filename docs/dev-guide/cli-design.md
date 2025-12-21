# 🚀 建议的新CLI命令设计

## 1. Prefix Query Command - 前缀查询命令

### 命令名称：`prefix-query` 或 `prefix`

### 使用语法：
```bash
rustkmer prefix-query [OPTIONS] <DATABASE> <PREFIX>
```

### 参数说明：
- `<DATABASE>`: 数据库文件路径
- `<PREFIX>`: 要匹配的前缀序列
- `-f, --format <FORMAT>`: 输出格式 (table/json/tsv/csv)
- `-o, --output <FILE>`: 输出文件
- `-v, --verbose`: 详细输出
- `-q, --quiet`: 静默模式

### 使用示例：
```bash
# 基本前缀查询
rustkmer prefix-query database.rkdb "AAATT"

# 指定输出格式
rustkmer prefix-query database.rkdb "AAAA" --format json

# 保存到文件
rustkmer prefix-query database.rkdb "AAATT" --output results.txt

# 详细输出
rustkmer prefix-query database.rkdb "AAATT" --verbose
```

### 预期输出：
```
K-mer                Count
AAATTGAATCGATCGAT    1,234
AAATTTTAGCTAGCTA     567
AAATTCCGGAATTCCGG    890
...
```

---

## 2. Suffix Query Command - 后缀查询命令

### 命令名称：`suffix-query` 或 `suffix`

### 使用语法：
```bash
rustkmer suffix-query [OPTIONS] <DATABASE> <SUFFIX>
```

### 参数说明：
- `<DATABASE>`: 数据库文件路径
- `<SUFFIX>`: 要匹配的后缀序列
- 其他参数同 prefix-query

### 使用示例：
```bash
# 基本后缀查询
rustkmer suffix-query database.rkdb "AAA"

# 详细输出
rustkmer suffix-query database.rkdb "AAA" --verbose

# JSON格式输出
rustkmer suffix-query database.rkdb "AAA" --format json
```

### 预期输出：
```
K-mer                Count
ATCGATCGATCGAAA      2,345
GCTAGCTAGCTAAA       1,567
CCGGCCGGCCAAA        890
...
```

---

## 3. Hybrid Query Command - 混合查询命令

### 命令名称：`hybrid-query` 或 `hybrid`

### 使用语法：
```bash
rustkmer hybrid-query [OPTIONS] <DATABASE> <PATTERN>
```

### 参数说明：
- `<DATABASE>`: 数据库文件路径
- `<PATTERN>`: 包含N通配符的模式 (如: "AAANNNAAA")
- `--smart`: 启用智能策略选择 (默认)
- `--force-prefix`: 强制使用前缀匹配
- `--force-suffix`: 强制使用后缀匹配
- `--force-variants`: 强制使用变体生成
- 其他参数同 prefix-query

### 使用示例：
```bash
# 智能混合查询 (自动选择最优策略)
rustkmer hybrid-query database.rkdb "AAANNNAAA"

# 强制使用前缀匹配
rustkmer hybrid-query database.rkdb "AAAANNN" --force-prefix

# 强制使用后缀匹配
rustkmer hybrid-query database.rkdb "NNNAAA" --force-suffix

# 强制使用变体生成 (用于对比)
rustkmer hybrid-query database.rkdb "ANANANA" --force-variants

# 显示策略信息
rustkmer hybrid-query database.rkdb "AAANNNAAA" --verbose
```

### 预期输出：
```
🔍 Hybrid Query: AAANNNAAA
🎯 Strategy: Hybrid Matching (prefix="AA", suffix="AAA")
⚡ Efficiency: ⭐⭐⭐⭐ (5-20x faster than variants)

K-mer                Count
AAATTAGCTAGAAA       1,234
AAACCGGCTAGAAA       567
AAATTTCTAGAAA        890
...
```

---

## 4. Smart Wildcard Command - 智能通配符命令

### 命令名称：`smart-query` 或 `smart`

### 使用语法：
```bash
rustkmer smart-query [OPTIONS] <DATABASE> <PATTERN>
```

### 特性：
- 自动分析N位置
- 自动选择最优策略
- 显示性能分析
- 策略对比

### 使用示例：
```bash
# 智能查询 (自动选择策略)
rustkmer smart-query database.rkdb "AAAANNN"

# 显示详细性能分析
rustkmer smart-query database.rkdb "AAAANNN" --profile

# 对比不同策略
rustkmer smart-query database.rkdb "AAAANNN" --compare-all
```

### 预期输出：
```
🔍 Smart Wildcard Query: AAAANNN

📊 Strategy Analysis:
  N positions: [4, 5, 6] (at end)
  Total variants: 64
  Recommended: Prefix Matching
  Efficiency gain: 64x

⚡ Performance Comparison:
  Prefix Matching:  ✅ 0.005s  (RECOMMENDED)
  Suffix Matching:  ❌ Not applicable
  Hybrid Matching:  ❌ Not applicable  
  Variant Generation: ⚠️  0.320s  (64x slower)

🎯 Selected Strategy: Prefix Matching
📋 Results: 1,234 matches found

K-mer                Count
AAAATGCTAGCTAAT      1,234
AAAACCGTTACGGTAA     567
...
```

---

## 5. Batch Query Commands - 批量查询命令

### Prefix Batch:
```bash
rustkmer prefix-batch database.rkdb --prefix-file prefixes.txt
```

### Suffix Batch:
```bash
rustkmer suffix-batch database.rkdb --suffix-file suffixes.txt
```

### Smart Batch:
```bash
rustkmer smart-batch database.rkdb --pattern-file patterns.txt
```

---

## 📈 实现优先级

### Phase 1: 基础命令 (高优先级)
1. `prefix-query` - 最常用，前缀匹配
2. `suffix-query` - 与前缀查询对应
3. `hybrid-query` - 混合匹配核心功能

### Phase 2: 智能优化 (中优先级)
4. `smart-query` - 智能策略选择
5. 批量查询命令

### Phase 3: 高级功能 (低优先级)
6. 性能分析工具
7. 策略对比工具

---

## 🛠️ 实现方案

### Rust代码结构：
```
src/cli/commands/
├── prefix.rs       # 前缀查询实现
├── suffix.rs       # 后缀查询实现  
├── hybrid.rs       # 混合查询实现
├── smart.rs        # 智能查询实现
└── mod.rs         # 命令注册
```

### CLI参数扩展：
在 `src/cli/args.rs` 中添加新的 Commands 枚举项

### 主程序集成：
在 `src/main.rs` 中添加新的命令处理逻辑

---

## 🎯 预期效果

### 性能提升：
- **AAAANNN模式**: 64x 性能提升
- **NNNAAA模式**: 64x 性能提升  
- **AAANNNAAA模式**: 32x 性能提升

### 用户体验：
```bash
# 简单直观的命令
rustkmer prefix-query database.rkdb "AAATT"
rustkmer suffix-query database.rkdb "AAA"
rustkmer hybrid-query database.rkdb "AAANNNAAA"

# 智能自动选择
rustkmer smart-query database.rkdb "AAANNNAAA"
```

### 功能对比：

| 功能 | 当前方式 | 新命令方式 | 效率提升 |
|------|----------|------------|----------|
| AAAANNN | `fuzzy-query` (慢) | `prefix-query` (快) | **64x** |
| NNNAAA | `fuzzy-query` (慢) | `suffix-query` (快) | **64x** |
| AAANNNAAA | `fuzzy-query` (慢) | `hybrid-query` (快) | **32x** |

这个设计方案将充分发挥我们实现的高效算法优势，为用户提供直观、高效的CLI接口！

