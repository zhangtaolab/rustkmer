# PyO3统一接口计划和文档修订

## 📋 项目概述

基于当前PyO3存在多个独立查询类（PyDatabase、PyPrefixQuery、PyFuzzyQuery）导致内存浪费和API不统一的问题，制定统一接口方案。

**重要提醒**：确保包含`query_hybrid`功能，支持混合模式查询（如"AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"）

## 🎯 主要目标

1. **统一接口**：将所有查询功能集成到PyDatabase类
2. **内存优化**：只加载一次数据库，共享给所有查询类型
3. **API标准化**：统一参数格式和返回值结构
4. **功能完整**：确保query_hybrid等所有现有功能在统一接口中可用
5. **文档更新**：修订PyO3绑定指南和示例代码
6. **向后兼容**：保持现有API的兼容性

## 📊 现状分析

### 当前问题
- **内存冗余**：每个查询类独立加载数据库（3×内存占用）
- **接口分散**：PyDatabase、PyPrefixQuery、PyFuzzyQuery使用不同API
- **功能缺失**：PyPrefixQuery缺少LoadMode选择
- **文档分散**：API使用说明分布在多个文档中

### 现有功能分析
```python
# 当前PyPrefixQuery的使用方式
engine = rustkmer_pyo3.PyPrefixQuery("/path/to/database.rkdb")
results = engine.query_hybrid("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
```

**关键功能**：
- ✅ `query_prefix()` - 前缀查询
- ✅ `query_hybrid()` - 混合模式查询（支持{N}语法）
- ✅ `parse_pattern()` - 解析混合模式
- ✅ `database_info()` - 数据库信息

## 🛠️ 实施计划

### 阶段1：代码架构重构

#### 1.1 扩展PyDatabase类功能
- **目标文件**：`pyo3/src/database.rs`
- **新增方法**：
  - `query_prefix()` - 前缀查询
  - `query_hybrid()` - 混合模式查询（关键功能）
  - `fuzzy_query()` - 模糊查询
  - `query_prefix_batch()` - 批量前缀查询
  - `query_hybrid_batch()` - 批量混合查询
  - `fuzzy_query_batch()` - 批量模糊查询
  - `parse_pattern()` - 解析混合模式

#### 1.2 统一数据库加载机制
```rust
// PyDatabase结构体需要包含RKDatabase实例
pub struct PyDatabase {
    // 现有字段...
    pub rk_database: Option<RKDatabase>,  // 共享的数据库实例
}
```

#### 1.3 实现query_hybrid功能
```rust
#[pymethods]
impl PyDatabase {
    /// 混合模式查询（等价于PyPrefixQuery.query_hybrid）
    fn query_hybrid(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let pattern_str = pattern.to_string().to_uppercase();
        
        // 使用共享的数据库实例
        if let Some(ref db) = self.rk_database {
            let result = match extract_hybrid_by_pattern(db, &pattern_str) {
                Ok(result) => result,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Hybrid query failed: {}", e)
                    ));
                }
            };
            
            let matches_map: HashMap<String, String> = result.matches.into_iter()
                .map(|(kmer, count)| (kmer, count.to_string()))
                .collect();
            Ok(matches_map)
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ))
        }
    }
    
    /// 解析混合模式（不执行查询）
    fn parse_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        let pattern_str = pattern.to_string().to_uppercase();
        
        let result = match parse_hybrid_pattern(&pattern_str) {
            Ok(pattern) => {
                let mut info = HashMap::new();
                info.insert("prefix".to_string(), pattern.prefix);
                info.insert("suffix".to_string(), pattern.suffix);
                info.insert("n_count".to_string(), pattern.n_count.to_string());
                info.insert("total_length".to_string(), pattern.total_length.to_string());
                info.insert("n_positions".to_string(), format!("{:?}", pattern.n_positions));
                info
            }
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Pattern parsing failed: {}", e)
                ));
            }
        };
        
        Ok(result)
    }
}
```

### 阶段2：API接口标准化

#### 2.1 统一使用方式
```python
# 新的统一接口
db = PyDatabase("database.rkdb", LoadMode.Preload)

# 精确查询
result = db.query("GCCGCGG")

# 前缀查询
prefix_result = db.query_prefix("GCC")

# 混合模式查询（关键功能）
hybrid_result = db.query_hybrid("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

# 模糊查询
fuzzy_result = db.fuzzy_query("GCCGCN", max_mutations=1)

# 模式解析
pattern_info = db.parse_pattern("GCC{N3}CGG")
```

#### 2.2 批量查询支持
```python
# 批量混合模式查询
batch_hybrid = db.query_hybrid_batch([
    "AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "ATCG{N5}ATCG",
    "GCC{N3}GCC"
])

# 批量精确查询
batch_exact = db.query_batch(["GCCGCGG", "ATGCGTA"])

# 批量前缀查询
batch_prefix = db.query_prefix_batch(["GCC", "ATG", "TTT"])
```

### 阶段3：文档和示例修订

#### 3.1 更新PyO3绑定指南
- **目标文件**：`docs/guides/pyo3-binding-guide.md`
- **重点更新**：
  - 混合模式查询语法和示例
  - query_hybrid方法的使用说明
  - LoadMode详细对比和选择建议
  - 内存使用优化指南

#### 3.2 重点修订示例代码
- **文件**：`examples/python/simple_prefix_query.py`
- **当前代码**：
```python
# 现有代码
engine = rustkmer_pyo3.PyPrefixQuery("/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb")
results = engine.query_hybrid("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
```
- **更新为**：
```python
# 统一接口
engine = rustkmer_pyo3.PyDatabase("/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb", 
                                   rustkmer_pyo3.LoadMode.Preload)
results = engine.query_hybrid("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
```

#### 3.3 创建统一示例
- **文件**：`examples/python/unified_query_example.py`
- **展示所有功能**：精确、前缀、混合、模糊查询

### 阶段4：迁移支持

#### 4.1 向后兼容适配器
```python
class PyPrefixQueryCompat:
    """兼容性适配器，支持现有PyPrefixQuery API"""
    
    def __init__(self, database_path: str, load_mode: LoadMode = LoadMode.Preload):
        self._db = PyDatabase(database_path, load_mode)
    
    def query_hybrid(self, pattern: str):
        return self._db.query_hybrid(pattern)
    
    def query_prefix(self, prefix: str):
        return self._db.query_prefix(prefix)
    
    def parse_pattern(self, pattern: str):
        return self._db.parse_pattern(pattern)
```

#### 4.2 迁移指南
```python
# 迁移指南示例
# 旧代码
engine = rustkmer_pyo3.PyPrefixQuery("database.rkdb")
results = engine.query_hybrid("AAAA{N5}AAAA")

# 新代码
engine = rustkmer_pyo3.PyDatabase("database.rkdb", rustkmer_pyo3.LoadMode.Preload)
results = engine.query_hybrid("AAAA{N5}AAAA")
```

## 📈 预期效果

### 功能完整性
- ✅ 所有现有功能在新接口中可用
- ✅ query_hybrid混合查询保持完整功能
- ✅ 批量查询功能增强

### 性能改进
- **内存使用**：减少66%（从3个实例到1个实例）
- **加载时间**：避免重复数据库加载
- **查询速度**：统一的查询优化

### 用户体验
- **API简化**：只需要学习一个主要类
- **代码简洁**：减少样板代码
- **功能完整**：所有高级功能都可用

## ⚠️ 关键注意事项

### query_hybrid功能确保
1. **语法支持**：确保{N}语法正确解析
2. **性能优化**：避免重复加载数据库
3. **错误处理**：保持现有的错误处理逻辑
4. **结果格式**：保持与现有API一致的结果格式

### 测试验证
1. **功能测试**：确保query_hybrid在新接口中工作正常
2. **性能测试**：验证内存和速度改进
3. **兼容性测试**：确保现有代码可以轻松迁移

## 🎯 成功标准

1. **功能完整性**：所有现有功能（包括query_hybrid）在新接口中可用
2. **性能改进**：内存使用减少50%以上
3. **文档完整性**：所有API都有完整文档和示例
4. **测试覆盖**：100%功能测试覆盖
5. **用户接受度**：示例代码简洁易懂，迁移成本低

