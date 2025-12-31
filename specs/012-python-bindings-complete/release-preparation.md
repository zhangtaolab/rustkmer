# 发布准备工作指南

**日期**: 2025-01-09
**版本**: 1.0

## 概述

本文档概述了RustKmer CLI（通过Cargo发布）和Python API（通过PyPI发布）的发布准备工作。

## 1. CLI发布准备（Cargo）

### 1.1 当前状态检查

```bash
# 检查Cargo.toml配置
cat Cargo.toml | grep -E "^(name|version|description|license|authors|repository)"

# 确保版本号语义化
# 当前格式：0.1.0
# 建议格式：0.3.0（基于当前已有011/012分支）
```

### 1.2 必需的发布前任务

1. **完善Cargo.toml**：
   - [ ] 添加完整的metadata（description、license、authors、repository）
   - [ ] 确保crate名称唯一（`rustkmer`已被占用，建议使用`rustkmer-cli`）
   - [ ] 添加keywords和categories
   - [ ] 配置readme属性指向README.md

2. **创建/更新文档**：
   - [ ] 完善README.md（安装说明、基本用法、示例）
   - [ ] 创建LICENSE文件
   - [ ] 添加CHANGELOG.md记录版本变更

3. **测试覆盖**：
   - [ ] 确保所有CLI命令有测试覆盖
   - [ ] 添加集成测试
   - [ ] 运行`cargo test --all-features`

4. **代码质量**：
   - [ ] `cargo clippy -- -D warnings`
   - [ ] `cargo fmt --check`
   - [ ] 检查文档注释完整性

### 1.3 发布配置

```toml
# Cargo.toml 建议配置
[package]
name = "rustkmer-cli"  # 注意：rustkmer可能已被占用
version = "0.3.0"
authors = ["Your Name <your.email@example.com>"]
edition = "2021"
description = "A fast k-mer counting tool for genomic data"
license = "MIT OR Apache-2.0"
repository = "https://github.com/zhangtaolab/rustkmer"
homepage = "https://github.com/zhangtaolab/rustkmer"
readme = "README.md"
keywords = ["bioinformatics", "genomics", "kmer", "fastq", "fasta"]
categories = ["command-line-utilities", "science"]

[[bin]]
name = "rustkmer"
path = "src/main.rs"

[features]
default = ["python"]
python = ["pyo3"]
```

## 2. Python API发布准备（PyPI）

### 2.1 构建系统配置

当前项目已使用maturin，这是正确的选择。需要完善：

```toml
# pyproject.toml 配置
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "rustkmer"
version = "0.3.0"  # 与CLI版本保持同步
description = "High-performance k-mer counting and querying for Python"
readme = "python/README.md"
requires-python = ">=3.10"
license = {text = "MIT OR Apache-2.0"}
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
keywords = ["bioinformatics", "genomics", "kmer", "sequencing"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Rust",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]

[project.urls]
Homepage = "https://github.com/zhangtaolab/rustkmer"
Documentation = "https://rustkmer.readthedocs.io/"
Repository = "https://github.com/zhangtaolab/rustkmer"
"Bug Tracker" = "https://github.com/zhangtaolab/rustkmer/issues"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "hypothesis>=6.0",
    "numpy>=1.21",
    "matplotlib>=3.5",
]

[tool.maturin]
python-source = "python"
module-name = "rustkmer._rustkmer"
features = ["pyo3/extension-module"]
```

### 2.2 Python包结构

```text
python/
├── rustkmer/
│   ├── __init__.py
│   ├── core.py
│   ├── database.py
│   ├── fuzzy.py
│   ├── stats.py
│   ├── utils.py
│   └── exceptions.py
├── tests/
│   ├── __init__.py
│   ├── test_kmer_counter.py
│   ├── test_database.py
│   ├── test_fuzzy.py
│   └── conftest.py
├── README.md
├── pyproject.toml
└── MANIFEST.in
```

### 2.3 发布前检查清单

1. **版本同步**：
   - [ ] CLI和Python包版本号保持一致
   - [ ] 更新CHANGELOG.md

2. **测试完整性**：
   - [ ] `pytest`测试全部通过
   - [ ] `maturin develop`本地测试成功
   - [ ] 多平台构建测试（Linux、macOS、Windows）

3. **文档完善**：
   - [ ] python/README.md完整
   - [ ] API文档自动生成（使用mkdocstrings）
   - [ ] 示例代码可运行

4. **构建优化**：
   - [ ] 配置CI自动构建多平台wheels
   - [ ] 优化二进制大小
   - [ ] 确保最小依赖

## 3. CI/CD配置

### 3.1 GitHub Actions工作流

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']

    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Build wheels
      uses: PyO3/maturin-action@v1
      with:
        args: --release --out dist

    - name: Test wheels
      run: |
        pip install dist/*.whl
        python -m pytest tests/

  publish-crate:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Publish to crates.io
      run: cargo publish --token ${{ secrets.CRATES_IO_TOKEN }}

  publish-pypi:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Publish to PyPI
      uses: PyO3/maturin-action@v1
      with:
        command: upload
        args: --non-interactive --skip-existing dist/*
      env:
        MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

### 3.2 版本管理策略

1. **语义化版本控制**：
   - 主版本号：不兼容的API更改
   - 次版本号：新功能（保持向后兼容）
   - 修订号：错误修复

2. **发布流程**：
   ```bash
   # 1. 更新版本号
   # 编辑 Cargo.toml 和 pyproject.toml
   # 编辑 python/rustkmer/__init__.py

   # 2. 更新CHANGELOG.md
   # 添加新版本的变化

   # 3. 创建标签
   git tag -a v0.3.0 -m "Release version 0.3.0"
   git push origin v0.3.0

   # 4. 触发CI自动发布
   ```

## 4. 用户文档和支持

### 4.1 安装说明

```bash
# CLI安装
cargo install rustkmer-cli

# Python API安装
pip install rustkmer
```

### 4.2 迁移指南

对于从源码安装的用户：

```bash
# 旧方式（源码安装）
git clone https://github.com/zhangtaolab/rustkmer
cd rustkmer
cargo build --release
export PATH=$PWD/target/release:$PATH
pip install maturin
maturin develop

# 新方式（包管理器）
cargo install rustkmer-cli
pip install rustkmer
```

## 5. 发布后的维护

1. **监控反馈**：
   - GitHub Issues
   - PyPI下载统计
   - crates.io下载统计

2. **持续改进**：
   - 定期发布补丁版本
   - 保持文档更新
   - 响应用户问题

3. **版本兼容性**：
   - 维护至少一个LTS版本
   - 提供迁移指南
   - 警告弃用功能

## 6. 紧急修复流程

1. 在主分支修复问题
2. 创建补丁分支（如`release-0.3.1`）
3. 更新版本号（0.3.0 → 0.3.1）
4. 创建新标签
5. 自动发布更新

## 建议的实施时间表

- **Week 1**: 完善Cargo.toml和pyproject.toml
- **Week 2**: 添加测试和文档
- **Week 3**: 设置CI/CD流水线
- **Week 4**: 进行alpha测试
- **Week 5**: 发布v0.3.0-alpha
- **Week 6-7**: 收集反馈并修复
- **Week 8**: 发布v0.3.0正式版