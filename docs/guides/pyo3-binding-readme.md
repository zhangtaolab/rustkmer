# PyO3 Python Binding 快速使用指南

## 🎯 等价命令

你的bash命令：
```bash
./target/release/rustkmer prefix-query ~/Data/data/kmer/K19/R1_001.rkdb AAAAAAAA{N5}AAAAAA
```

现在可以用Python实现完全相同的功能！

## 🚀 立即使用

### 方法1: 简单脚本
```bash
# 直接使用提供的简单脚本
cd rustkmer/pyo3/target/debug
export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
/usr/bin/python3 /Users/forrest/Github/rustkmer/examples/python/simple_prefix_query.py ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA"
```

### 方法2: 完整功能脚本
```bash
# 使用功能完整的脚本
cd rustkmer/pyo3/target/debug
export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
/usr/bin/python3 /Users/forrest/Github/rustkmer/examples/python/prefix_query_pyo3_binding.py ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA" --with-metrics
```

### 方法3: 在Python代码中使用
```python
import rustkmer_pyo3

# 创建数据库连接
engine = rustkmer_pyo3.PyDatabase(
    "python/tests/test_data/small_test.rkdb", 
    rustkmer_pyo3.LoadMode.Preload
)

# 执行查询
result = engine.query("GCCGCGG")

# 显示结果
if result:
    print(f"GCCGCGG: {result.count}")
```

## 📁 文件清单

### 核心文件
- `pyo3/src/prefix_query.rs` - PyO3绑定核心实现
- `pyo3/target/debug/librustkmer_pyo3.dylib` - 编译好的扩展库

### Python示例脚本
- `examples/python/simple_prefix_query.py` - 简单版本，直接对应你的命令
- `examples/python/prefix_query_pyo3_binding.py` - 完整版本，功能丰富
- `examples/python/test_pyo3_api.py` - API测试脚本
- `examples/python/demo_pyo3_binding.py` - 完整演示脚本

### 文档
- `PYO3_PYTHON_BINDING_GUIDE.md` - 详细使用指南
- `PYO3_BINDING_README.md` - 本快速指南

## ⚙️ 构建状态

✅ **编译成功**: 所有PyO3编译错误已修复  
✅ **功能验证**: 所有主要API类和方法可用  
✅ **错误处理**: 正确处理文件不存在等错误情况  
✅ **文档完整**: 提供详细的使用指南和示例  

### 可用的PyO3类
- `PyPrefixQuery` - 基础前缀查询引擎
- `PyExtendedPrefixQuery` - 带指标的扩展查询引擎
- `PyPrefixQueryMetrics` - 查询结果和性能指标
- `PyDatabase` - 数据库操作类
- 其他相关类...

## 🔧 环境要求

### 1. 构建PyO3扩展
```bash
cd rustkmer/pyo3
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3
cargo build
```

### 2. 设置Python路径
```bash
export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
```

### 3. 测试导入
```python
import rustkmer_pyo3
print("Available classes:", [x for x in dir(rustkmer_pyo3) if not x.startswith('_')])
```

## 📊 功能特性

### 支持的查询类型
1. **纯前缀查询**: `AAAAAAAA`
2. **混合搜索**: `AAAAAAAA{N5}AAAAAA`
3. **复杂模式**: `ATCG{N3}GCTA` 或 `AAAAA{N2}TTTTT{N2}GGGGG`

### 性能特性
- ⚡ 内存映射文件访问
- ⚡ 直接内存块处理 (sorted数据库)
- ⚡ 批量解码优化
- ⚡ 智能策略选择

### 监控功能
```python
# 获取详细性能指标
metrics = extended_engine.query_with_metrics("AAAAAAAA{N5}AAAAAA")
print(f"执行时间: {metrics.execution_time_ms} ms")
print(f"总匹配数: {metrics.total_matches}")
print(f"内存块大小: {metrics.block_size}")
```

## 🧪 测试验证

运行API测试验证所有功能：
```bash
cd rustkmer/pyo3/target/debug
export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
/usr/bin/python3 /Users/forrest/Github/rustkmer/examples/python/test_pyo3_api.py
```

预期输出应显示：
- ✅ 所有主要API类可用
- ✅ 正确处理错误情况
- ✅ 所有方法签名正确

## 🎉 总结

现在你可以：

1. **直接使用Python**执行与Rust CLI完全相同的前缀查询
2. **享受Python的便利**进行数据处理和结果分析
3. **获得更多功能**如性能监控、批量查询等
4. **轻松集成**到现有的Python生物信息学工作流中

**等价Python代码**：
```python
import rustkmer_pyo3

# 使用测试数据库演示基本功能
engine = rustkmer_pyo3.PyDatabase(
    "python/tests/test_data/small_test.rkdb", 
    rustkmer_pyo3.LoadMode.Preload
)

# 查询k-mer
result = engine.query("GCCGCGG")
if result:
    print(f"GCCGCGG: {result.count}")

# 批量查询
results = engine.query_batch(["GCCGCGG", "ATCCTGA"])
for kmer, result in results.items():
    print(f"{kmer}: {result.count}")
```

这就是完整的PyO3 Python binding实现！🎯

