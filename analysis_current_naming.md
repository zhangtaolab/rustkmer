# PyO3 Binding 命名不统一问题分析

## 当前混乱的命名模式

### PyDatabase类中的查询方法
```rust
// 精确查询相关
fn query()              // ✅ 统一
fn query_batch()        // ❌ 与其他不一致

// 前缀查询相关  
fn extract_by_prefix()      // ❌ 命名风格不同
fn query_prefix_optimized() // ✅ 统一
fn query_prefix_batch()     // ✅ 统一

// 混合查询相关
fn extract_by_pattern()     // ❌ 命名风格不同
fn query_hybrid()           // ✅ 统一
fn query_hybrid_batch()     // ✅ 统一

// 模糊查询相关
fn fuzzy_query()            // ❌ 命名风格不一致
```

### PyFuzzyQuery类中的方法
```rust
fn fuzzy_query()                           // ❌ 命名风格不一致
fn fuzzy_query_with_position_mutations()   // ❌ 命名风格不一致
```

### PyPrefixQuery类中的方法
```rust
fn query_prefix()         // ✅ 统一
fn query_hybrid()         // ✅ 统一
fn query_with_metrics()   // ✅ 统一
fn batch_query()          // ❌ 命名风格不一致
```

## 命名不统一的问题

1. **混用 `query_xxx` 和 `xxx_query` 格式**
2. **同功能在不同类中命名不一致**
3. **存在冗余方法** (`extract_by_*` vs `query_*`)
4. **批量操作命名不一致** (`query_batch` vs `batch_query`)

## 解决方案
采用统一的 `query_xxx` 命名格式，按功能模块化命名。
