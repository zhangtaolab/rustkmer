# PyO3 Binding 统一命名方案

## 统一命名原则

### 核心原则
1. **统一使用 `query_xxx` 格式** - 动词在前，更符合Python API设计习惯
2. **按功能模块化命名** - 清晰表达查询类型和特性
3. **保持向后兼容** - 提供别名机制避免破坏现有代码

### 命名模式
```
query_[类型]_[特性]
- query: 统一前缀
- [类型]: exact, prefix, hybrid, fuzzy
- [特性]: batch, optimized, metrics, position
```

## 详细命名迁移方案

### PyDatabase类方法重命名

#### 精确查询 (Exact Query)
```rust
// 当前 → 建议
query() → query_exact()              // 保持原名但推荐使用新名
query_batch() → query_exact_batch()  // 批量精确查询
```

#### 前缀查询 (Prefix Query)
```rust
// 当前 → 建议  
extract_by_prefix() → query_prefix()                    // 移除冗余方法
query_prefix_optimized() → query_prefix()               // 优化版本作为主方法
query_prefix_optimized_string() → query_prefix_string() // 保留字符串版本
query_prefix_batch() → query_prefix_batch()             // 保持不变
```

#### 混合查询 (Hybrid Query)
```rust
// 当前 → 建议
extract_by_pattern() → query_hybrid()        // 移除冗余方法  
query_hybrid() → query_hybrid()              // 保持不变
query_hybrid_batch() → query_hybrid_batch()  // 保持不变
```

#### 模糊查询 (Fuzzy Query)
```rust
// 当前 → 建议
fuzzy_query() → query_fuzzy()                           // 统一命名
fuzzy_query_with_position_mutations() → query_fuzzy_position() // 简化命名
```

### PyFuzzyQuery类方法重命名

```rust
// 当前 → 建议
fuzzy_query() → query_fuzzy()                           // 统一命名
fuzzy_query_with_position_mutations() → query_fuzzy_position() // 简化命名
```

### PyPrefixQuery类方法重命名

```rust
// 当前 → 建议
query_prefix() → query_prefix()           // 保持不变
query_hybrid() → query_hybrid()           // 保持不变  
query_with_metrics() → query_prefix_metrics() // 更明确
batch_query() → query_prefix_batch_metrics()  // 统一命名
```

### PyExtendedPrefixQuery类方法重命名

```rust
// 当前 → 建议
query_with_metrics() → query_prefix_metrics()           // 更明确
query_hybrid_with_metrics() → query_hybrid_metrics()    // 更明确
query_with_metrics_string() → query_prefix_metrics_string() // 更明确
batch_query() → query_prefix_batch_metrics()            // 统一命名
```

## 向后兼容性方案

### 1. 别名机制
```rust
#[deprecated(since = "2.0.0", note = "Use `query_exact()` instead")]
fn query(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
    self.query_exact(kmer)
}

#[deprecated(since = "2.0.0", note = "Use `query_exact_batch()` instead")]
fn query_batch(&self, kmers: Vec<String>) -> PyResult<HashMap<String, PyQueryResult>> {
    self.query_exact_batch(kmers)
}
```

### 2. 文档更新
- 更新所有示例代码使用新命名
- 在文档中明确标注废弃方法
- 提供迁移指南

### 3. 渐进式迁移
- 第一阶段：添加新方法，标记旧方法为废弃
- 第二阶段：在主要版本更新中移除旧方法
- 第三阶段：清理和优化

## 实施计划

### 阶段1: 设计完成 ✅
- [x] 分析当前命名问题
- [x] 设计统一命名方案
- [x] 制定向后兼容策略

### 阶段2: 实现新命名
- [ ] 在各个类中添加新的统一命名方法
- [ ] 实现向后兼容别名
- [ ] 添加deprecation警告

### 阶段3: 文档和示例
- [ ] 更新所有文档使用新命名
- [ ] 更新示例代码
- [ ] 创建迁移指南

### 阶段4: 清理和发布
- [ ] 移除废弃方法（主要版本更新）
- [ ] 性能测试和优化
- [ ] 发布新版本

## 预期收益

1. **更清晰的API** - 统一命名降低学习成本
2. **更好的可维护性** - 一致性命名便于代码维护
3. **更专业的用户体验** - 符合Python生态系统命名规范
4. **减少混淆** - 消除命名不一致带来的困惑
