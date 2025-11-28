# RustKmer 模糊查询用户指南

## 概述

RustKmer 模糊查询功能提供了强大的容错 k-mer 搜索能力，支持通配符扩展、长度标准化和突变容忍度。本指南将详细介绍如何使用这些功能。

## 主要特性

### 🔍 通配符查询
- 支持 `N` 通配符，自动扩展为 A、T、C、G
- 支持多个通配符组合
- 智能组合爆炸保护（默认最多 10,000 个变体）

### 🧬 长度标准化
- 自动处理查询与数据库 k-mer 长度不匹配
- 短查询自动 N 填充
- 长查询智能截断

### ⚡ 突变容忍度
- 汉明距离计算
- 支持 1-2 个突变位点
- 高效的近似匹配算法

### 🚀 性能优化
- 并行处理支持
- 内存优化算法
- 性能监控和分析

## 快速开始

### 库 API 使用

```rust
use rustkmer::database::format::RKDatabase;
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine};

// 加载数据库
let database = RKDatabase::from_file_path("database.rkdb")?;

// 创建查询引擎
let engine = FuzzyQueryEngine::new(database);

// 基础查询
let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
let result = engine.execute_query(&query)?;

println!("总匹配数: {}", result.total_count);
for match_item in &result.individual_matches {
    println!("序列: {}, 计数: {}", match_item.sequence, match_item.count);
}
```

### 高级查询参数

```rust
// 自定义查询参数
let query = FuzzyQuery::with_params(
    "ATGCGATGCTAGCN",    // 查询字符串
    13,                   // k-mer 大小
    1,                    // 突变容忍度
    Some(5000),          // 最大变体数
    true,                // 启用并行处理
    1000,                // 批处理大小
);
```

## 详细功能说明

### 1. 通配符查询

通配符 `N` 可以匹配任意核苷酸（A、T、C、G）。

#### 单个通配符
```rust
let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
// 自动扩展为: ATGCGATGCTAGCA, ATGCGATGCTAGCT, ATGCGATGCTAGCC, ATGCGATGCTAGCG
```

#### 多个通配符
```rust
let query = FuzzyQuery::new("ATNNGATGCTAGC", 13, 0);
// 生成 4^2 = 16 个变体
```

#### 实际应用示例
- **未知碱基**: 当序列包含不确定的碱基时使用 N
- **简并碱基**: 处理测序不确定性
- **模式匹配**: 查找具有特定模式的序列

### 2. 长度标准化

自动调整查询长度以匹配数据库 k-mer 大小。

#### 查询过短（自动填充 N）
```rust
let query = FuzzyQuery::new("ATGCG", 13, 0);
// 自动扩展为: NNNNNATGCGNNNNN (长度 13)
```

#### 查询过长（智能截断）
```rust
let query = FuzzyQuery::new("ATGCGATGCTAGCATGCG", 13, 0);
// 智能截断为 13 个字符
```

#### 长度差限制
- 最大允许长度差: 3 个碱基
- 超过限制将返回错误

### 3. 突变容忍度

支持指定数量的碱基突变，基于汉明距离计算。

#### 单突变查询
```rust
let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 1);
// 查找与原始序列相差 1 个碱基的所有序列
```

#### 双突变查询
```rust
let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 2);
// 查找与原始序列相差 2 个碱基的所有序列
```

#### 突变限制
- 最大突变数: k/2（k 为 k-mer 大小）
- 例如：13-mer 最多支持 6 个突变

### 4. 组合查询

可以同时使用通配符和突变容忍度。

```rust
let query = FuzzyQuery::new("ATGCGATGCTN", 13, 1);
// 1. 先扩展通配符 N → A,T,C,G
// 2. 对每个变体应用 1 个突变容忍度
// 总变体数 = 4 × (13 × 3 + 1) = 160
```

## 性能优化

### 1. 组合爆炸保护

系统会自动限制生成的变体数量：
- 默认最大变体数: 10,000
- 超过限制时返回 `CombinatorialExplosion` 错误

### 2. 并行处理

```rust
let query = FuzzyQuery::with_params(
    query_string,
    kmer_size,
    mutation_tolerance,
    max_variants,
    true,  // 启用并行处理
    batch_size,
);
```

### 3. 批处理优化

```rust
// 适当的批处理大小可以提升性能
let query = FuzzyQuery::with_params(
    query_string,
    kmer_size,
    mutation_tolerance,
    max_variants,
    enable_parallel,
    1000,  // 批处理大小
);
```

## 结果解释

### 查询结果结构

```rust
pub struct FuzzyQueryResultData {
    pub total_count: u64,                    // 总匹配数
    pub individual_matches: Vec<KmerMatch>,   // 具体匹配
    pub query_metadata: QueryMetadata,        // 查询元数据
    pub status: QueryStatus,                  // 查询状态
}
```

### 匹配类型

```rust
pub enum MatchType {
    Exact,                                     // 精确匹配
    WildcardExpansion { wildcard_positions: Vec<usize> }, // 通配符扩展
    MutationTolerance { mutation_positions: Vec<usize> }, // 突变容忍
    LengthNormalization,                        // 长度标准化
}
```

### 查询元数据

```rust
pub struct QueryMetadata {
    pub query_params: FuzzyQuery,           // 查询参数
    pub variants_generated: usize,          // 生成的变体数
    pub query_time_ms: u64,                // 查询耗时(毫秒)
    pub database_size: Option<u64>,         // 数据库大小
    pub memory_usage_mb: Option<f64>,       // 内存使用(MB)
}
```

## 错误处理

### 常见错误类型

1. **InvalidQuery**: 查询字符串无效
   ```
   Error: Invalid query string: Query contains invalid characters (only A,T,C,G,N allowed)
   ```

2. **TooManyVariants**: 生成的变体过多
   ```
   Error: Too many variants generated: 65536 (limit: 10000)
   ```

3. **InvalidParameters**: 参数无效
   ```
   Error: Invalid parameters: Query is too short for k-mer size (max difference: 3)
   ```

### 错误处理示例

```rust
match engine.execute_query(&query) {
    Ok(result) => {
        println!("查询成功: {} 个匹配", result.total_count);
    }
    Err(rustkmer::fuzzy::FuzzyError::TooManyVariants { actual, limit }) => {
        println!("变体过多: {} (限制: {})", actual, limit);
    }
    Err(e) => {
        println!("查询失败: {}", e);
    }
}
```

## CLI 使用指南

### 命令语法

```bash
rustkmer fuzzy-query [OPTIONS] <DATABASE> <QUERY>
```

### 参数说明

#### 必需参数
- `<DATABASE>`: 数据库文件路径
- `<QUERY>`: 查询字符串（可包含 N 通配符）

#### 可选参数

- `-m, --mutations <MUTATIONS>`: 突变容忍度 [默认: 0]
- `-M, --max-variants <MAX_VARIANTS>`: 最大变体数 [默认: 10000]
- `-p, --parallel`: 启用并行处理
- `-b, --batch-size <BATCH_SIZE>`: 批处理大小 [默认: 1000]
- `-f, --format <FORMAT>`: 输出格式 [table|json|tsv|csv]
- `-o, --output <OUTPUT>`: 输出文件
- `-v, --verbose`: 详细输出
- `-q, --quiet`: 静默模式
- `--profile`: 性能分析

### 使用示例

#### 基础通配符查询
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN"
```

#### 突变容忍查询
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCA" --mutations 1
```

#### JSON 输出
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --format json
```

#### 保存到文件
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --output results.txt
```

#### 性能分析
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --profile
```

## 最佳实践

### 1. 查询设计

#### 避免过度模糊
```rust
// ❌ 避免：太多通配符
let query = FuzzyQuery::new("NNNNNNNNNNNNN", 13, 0); // 4^13 = 67M 变体

// ✅ 推荐：适度的模糊
let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0); // 4 个变体
```

#### 合理设置突变容忍度
```rust
// ❌ 避免：突变过多
let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 7); // 超过 k/2

// ✅ 推荐：适度突变
let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 1); // 单突变
```

### 2. 性能优化

#### 批处理大小
- 小查询 (<1000 变体): batch_size = 500
- 中等查询 (1000-10000 变体): batch_size = 1000
- 大查询 (>10000 变体): batch_size = 2000

#### 并行处理
- 大数据库 (>1M k-mers): 启用并行
- 小数据库 (<100k k-mers): 可禁用并行

### 3. 内存管理

#### 监控内存使用
```rust
let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
let result = engine.execute_query(&query)?;

if let Some(memory_mb) = result.query_metadata.memory_usage_mb {
    println!("内存使用: {:.2} MB", memory_mb);
}
```

## 高级用法

### 1. 自定义性能限制

```rust
// 创建严格限制的查询
let query = FuzzyQuery::with_params(
    "ATGCGATGCTAGCN",
    13,
    1,
    Some(1000),  // 限制变体数
    true,
    500,        // 较小批处理大小
);
```

### 2. 批量查询

```rust
let queries = vec![
    FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0),
    FuzzyQuery::new("TTGCGATGCTAGCN", 13, 1),
    FuzzyQuery::new("GCGATGCTAGCATN", 13, 0),
];

let results = engine.execute_batch(&queries)?;
```

### 3. 性能分析

```rust
// 启用性能监控
let query = FuzzyQuery::with_params(
    query_string,
    kmer_size,
    mutation_tolerance,
    max_variants,
    enable_parallel,
    batch_size,
);

let result = engine.execute_query(&query)?;
println!("查询时间: {}ms", result.query_metadata.query_time_ms);
println!("变体生成数: {}", result.query_metadata.variants_generated);
```

## 故障排除

### 常见问题

#### 1. 查询超时
**症状**: 查询时间过长
**解决方案**:
- 减少通配符数量
- 降低突变容忍度
- 减小 max_variants 限制

#### 2. 内存不足
**症状**: Out of memory 错误
**解决方案**:
- 减小 batch_size
- 启用并行处理
- 减少 max_variants

#### 3. 组合爆炸
**症状**: TooManyVariants 错误
**解决方案**:
- 减少 N 通配符数量
- 降低突变容忍度
- 增加 max_variants 限制（谨慎使用）

#### 4. 无匹配结果
**症状**: total_count = 0
**可能原因**:
- 数据库中没有匹配的序列
- 查询条件过于严格
- k-mer 长度不匹配

### 调试技巧

#### 1. 详细日志
```rust
use log::info;

let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
info!("查询参数: {:?}", query);

let result = engine.execute_query(&query)?;
info!("查询结果: {} 匹配", result.total_count);
```

#### 2. 性能分析
```bash
rustkmer fuzzy-query database.rkdb "ATGCGATGCTAGCN" --profile --verbose
```

#### 3. 渐进式查询
```rust
// 先用简单查询测试
let simple_query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 0);
let simple_result = engine.execute_query(&simple_query)?;

// 再用复杂查询
let complex_query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 1);
let complex_result = engine.execute_query(&complex_query)?;
```

## 性能基准

### 典型性能指标

| 查询类型 | 变体数 | 查询时间 | 内存使用 |
|---------|--------|----------|----------|
| 精确匹配 | 1 | <1ms | 最小 |
| 单通配符 | 4 | <10ms | 最小 |
| 双通配符 | 16 | <50ms | 最小 |
| 三通配符 | 64 | <200ms | 最小 |
| 单突变 | 14 | <20ms | 最小 |
| 单通配符+单突变 | 60 | <100ms | 最小 |
| 双通配符+单突变 | 240 | <500ms | 中等 |

### 性能调优建议

1. **小查询**: 使用默认设置即可
2. **中等查询**: 启用并行处理
3. **大查询**: 调整批处理大小和变体限制

## 总结

RustKmer 模糊查询提供了强大而灵活的 k-mer 搜索能力，支持多种查询模式和高性能处理。通过合理使用通配符、突变容忍度和性能优化选项，可以满足各种生物信息学应用需求。

### 关键要点

- 🔧 **灵活配置**: 支持多种查询参数组合
- ⚡ **高性能**: 并行处理和内存优化
- 🛡️ **安全防护**: 组合爆炸保护机制
- 📊 **详细分析**: 完整的性能监控和结果分析
- 🚀 **易于使用**: 简洁的 API 和 CLI 接口

通过本指南，您应该能够充分利用 RustKmer 模糊查询功能，为您的生物信息学研究提供强大的序列搜索能力。