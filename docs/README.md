# RustKmer Documentation

欢迎来到RustKmer文档中心！本文档提供了完整的项目信息、使用指南和技术细节。

## 📁 文档结构概览

```
docs/
├── 📖 index.md                    # 主页和快速导航
├── 📚 getting-started/            # 入门指南
│   ├── installation.md            # 基础安装
│   └── installation-advanced.md   # 高级安装
├── 👥 guides/                     # 使用指南
│   ├── user-guide.md             # 用户指南
│   ├── pyo3-binding-guide.md     # Python API指南
│   ├── pyo3-binding-readme.md    # Python快速参考
│   ├── prefix-query-guide.md     # 前缀查询指南
│   └── hybrid-search-guide.md    # 混合搜索指南
├── 🔍 api-reference/              # API参考
│   ├── overview.md               # API总览
│   ├── database.md               # 数据库API
│   └── query.md                  # 查询API
├── 💡 implementation/             # 实现报告
│   ├── prefix-query-report.md    # 前缀查询实现
│   ├── bug-fixes.md              # Bug修复记录
│   └── hybrid-search-fixes.md    # 混合搜索修复
├── 💾 performance/                # 性能优化
│   └── memory-optimization.md    # 内存优化
├── 🔧 dev-guide/                  # 开发者指南
│   ├── algorithm-implementation.md # 算法实现
│   ├── cli-design.md             # CLI设计
│   ├── agents.md                 # 开发规范
│   └── claude.md                 # 项目历史
├── 🚨 troubleshooting/           # 故障排除
│   ├── cli-status.md             # CLI状态
│   ├── n-position-demo.md        # N位置效率演示
│   └── prefix-extraction-demo.md # 前缀提取演示
├── 📖 examples/                   # 示例代码
│   ├── basic-usage.md            # 基础用法
│   ├── fuzzy-search.md           # 模糊搜索
│   └── batch-processing.md       # 批量处理
└── 🎓 tutorials/                  # 教程
    ├── basic-workflow.md         # 基础工作流
    └── integration.md            # 集成指南
```

## 🚀 快速导航

### 新用户
1. **[快速开始](getting-started/first-steps.md)** - 5分钟入门
2. **[安装指南](installation.md)** - 安装RustKmer
3. **[用户指南](guides/user-guide.md)** - 完整使用指南
4. **[基础示例](examples/basic-usage.md)** - 代码示例

### Python用户
1. **[PyO3绑定指南](guides/pyo3-binding-guide.md)** - Python API完整指南
2. **[PyO3快速参考](guides/pyo3-binding-readme.md)** - 快速API参考
3. **[Python示例](examples/)** - Python代码示例

### 高级用户
1. **[前缀查询指南](guides/prefix-query-guide.md)** - 高效前缀搜索
2. **[混合搜索指南](guides/hybrid-search-guide.md)** - 复杂模式搜索
3. **[内存优化](performance/memory-optimization.md)** - 性能优化
4. **[API参考](api-reference/)** - 完整API文档

### 开发者
1. **[算法实现](dev-guide/algorithm-implementation.md)** - 核心算法详解
2. **[CLI设计](dev-guide/cli-design.md)** - 命令行接口设计
3. **[实现报告](implementation/)** - 技术实现细节
4. **[开发规范](dev-guide/agents.md)** - 开发标准

## 🔧 技术栈

- **Rust 1.80+** - 核心高性能引擎
- **Python 3.10+** - PyO3绑定
- **自定义RKDB格式** - 高效数据库存储
- **内存映射** - 大数据集优化

## 📊 核心功能

### K-mer计数
- 高性能k-mer计数
- 规范k-mer支持
- 并行处理
- 内存优化

### 查询操作
- 精确查询
- 模糊查询（支持N通配符）
- 前缀查询（针对排序数据库优化）
- 混合查询（前后缀组合）
- 批量查询

### 数据库操作
- RKDB格式支持
- 内存映射访问
- 统计信息计算
- 数据库合并

## 🎯 快速开始

### 安装
```bash
# Rust安装
cargo install rustkmer

# Python安装
pip install rustkmer
```

### 基本使用
```bash
# 计数k-mers
rustkmer count -k 21 -i genome.fa -o genome.rkdb

# 查询k-mer
rustkmer query genome.rkdb ATGCGATGCTAGCGCTAGCTA

# 前缀查询
rustkmer prefix-query genome.rkdb --prefix ATG
```

### Python API
```python
from pyrustkmer import PyDatabase, LoadMode

# 创建数据库连接
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# 查询k-mer
result = db.query_exact("ATGCGATGCTAGCGCTAGCTA")
if result:
    print(f"找到: {result.count}")
```

## 🔍 搜索指南

在文档中搜索特定信息：

- **API方法** → 查看 [API参考](api-reference/)
- **安装问题** → 查看 [故障排除](troubleshooting/)
- **性能问题** → 查看 [性能指南](performance/)
- **代码示例** → 查看 [示例](examples/)
- **算法细节** → 查看 [实现指南](dev-guide/)

## 📞 获取帮助

- **GitHub Issues** - 报告问题和功能请求
- **文档问题** - 通过GitHub改善文档
- **性能问题** - 查看 [性能分析](PERFORMANCE.md)

## 🏷️ 文档标签

- 🆕 **新增** - 新添加的文档
- 🔧 **维护** - 需要更新的文档
- ✅ **验证** - 已验证的文档
- 📝 **草稿** - 待完善的文档

## 📈 文档统计

- **总文档数**: 25+ 个文件
- **代码示例**: 50+ 个
- **API方法**: 20+ 个
- **教程**: 5+ 个

---

**祝您使用愉快！如有问题，请查看 [故障排除指南](troubleshooting/) 或提交GitHub Issue。**
