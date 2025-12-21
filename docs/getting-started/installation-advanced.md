# RustKmer 安装指南

本文档详细描述了RustKmer的安装过程和快速开始步骤。

## 目录

- [系统要求](#系统要求)
- [安装方式](#安装方式)
- [快速开始](#快速开始)
- [验证安装](#验证安装)
- [故障排除](#故障排除)
- [升级指南](#升级指南)

## 系统要求

### 最低要求

- **操作系统**: Linux (Ubuntu 18.04+, CentOS 7+), macOS (10.14+), Windows 10+
- **CPU**: 64位处理器，至少2核心
- **内存**: 4GB RAM (8GB+推荐用于大型数据集)
- **磁盘空间**: 2GB可用空间
- **Rust**: 1.80.0+ stable版本

### 推荐配置

- **CPU**: 8+核心，3.0GHz+
- **内存**: 16GB+ RAM
- **存储**: SSD硬盘，至少100GB可用空间
- **网络**: 稳定的互联网连接（下载依赖）

## 安装方式

### 方式1: 从源码编译（推荐）

#### 第一步: 安装Rust工具链

```bash
# 使用rustup安装Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 按照提示选择默认安装选项
source ~/.cargo/env

# 验证安装
rustc --version
cargo --version
```

#### 第二步: 克隆和编译RustKmer

```bash
# 克隆仓库
git clone https://github.com/your-repo/rustkmer.git
cd rustkmer

# 编译（推荐发布模式）
cargo build --release

# 验证编译
./target/release/rustkmer --version
```

#### 第三步: 安装到系统路径（可选）

```bash
# 安装到 ~/.cargo/bin
cargo install --path .

# 验证安装
rustkmer --version
```

### 方式2: 使用预编译二进制文件

#### 从GitHub Releases下载

1. 访问 [GitHub Releases](https://github.com/your-repo/rustkmer/releases) 页面
2. 根据您的操作系统下载对应的二进制文件：
   - Linux: `rustkmer-linux-x86_64.tar.gz`
   - macOS: `rustkmer-macos-x86_64.tar.gz`
   - Windows: `rustkmer-windows-x86_64.zip`

3. 解压并安装：

```bash
# Linux/macOS
tar -xzf rustkmer-*-x86_64.tar.gz
sudo mv rustkmer /usr/local/bin/

# Windows (使用PowerShell)
Expand-Archive rustkmer-windows-x86_64.zip
Move-Item rustkmer.exe $Env:LOCALAPPDATA\Programs\rustkmer\
```

### 方式3: 使用包管理器

#### Homebrew (macOS)

```bash
# 添加tap（如果需要）
brew tap your-repo/rustkmer

# 安装
brew install rustkmer
```

#### AUR (Arch Linux)

```bash
# 使用yay
yay -S rustkmer

# 或使用makepkg
git clone https://aur.archlinux.org/rustkmer.git
cd rustkmer
makepkg -si
```

## 快速开始

### 验证安装

```bash
# 检查版本和可用命令
rustkmer --help
rustkmer --version
```

### 第一个K-mer计数任务

```bash
# 创建一个简单的测试序列文件
cat > test.fa << EOF
>test_sequence
ATGCGATCGATCGATCGATCG
ATATATATATATATATATAT
GCGCGCGCGCGCGCGCGCGC
EOF

# 计数k-mer (k=3)
rustkmer count -k 3 -i test.fa -o test.rkdb

# 查询特定k-mer
rustkmer query test.rkdb ATG
rustkmer query test.rkdb ATA
rustkmer query test.rkdb GCG
```

### 性能测试

```bash
# 使用排序数据库获得更好性能
rustkmer count -k 21 --sort -i large_genome.fa -o sorted_genome.rkdb

# 测试前缀查询性能
rustkmer prefix-query sorted_genome.rkdb "ATCGATCG"
```

## Python绑定安装

### 安装PyO3绑定

```bash
cd rustkmer/pyo3

# 构建Python绑定
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3
cargo build

# 设置Python路径
export PYTHONPATH="$PWD/target/debug:$PYTHONPATH"

# 测试导入
python3 -c "import rustkmer_pyo3; print('PyO3绑定安装成功！')"
```

### 使用Python API

```python
import rustkmer_pyo3

# 加载数据库
db = rustkmer_pyo3.PyDatabase("test.rkdb")

# 查询k-mer
result = db.query_kmer("ATG")
if result:
    print(f"ATG count: {result.count}")

# 前缀查询
prefix_results = db.extract_by_prefix("ATG")
print(f"Found {len(prefix_results)} k-mers starting with ATG")
```

## 验证安装

### 功能测试

```bash
# 运行内置测试
rustkmer test

# 或手动验证核心功能
cd python/tests/test_data

# 测试基本查询
python3 example_usage.py
```

### 性能基准

```bash
# 运行性能基准测试
cd benchmarks
python3 prefix_query_performance.py
```

## 故障排除

### 常见问题

#### 1. 编译错误

**问题**: `error: failed to run custom build command for ...`

**解决**:
```bash
# 确保Rust版本是最新的
rustup update stable

# 清理构建缓存
cargo clean
cargo build --release
```

#### 2. 链接错误 (macOS)

**问题**: `ld: library not found for -l...`

**解决**:
```bash
# 设置正确的链接标志
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
cargo build
```

#### 3. 内存不足

**问题**: 编译时内存不足

**解决**:
```bash
# 减少并行编译任务
export CARGO_BUILD_JOBS=2
cargo build --release
```

#### 4. Python绑定导入失败

**问题**: `ModuleNotFoundError: No module named 'rustkmer_pyo3'`

**解决**:
```bash
# 检查Python路径设置
echo $PYTHONPATH

# 重新设置路径
export PYTHONPATH="/path/to/rustkmer/pyo3/target/debug:$PYTHONPATH"

# 检查动态库
ls pyo3/target/debug/librustkmer_pyo3.*
```

### 获取帮助

- **GitHub Issues**: [https://github.com/your-repo/rustkmer/issues](https://github.com/your-repo/rustkmer/issues)
- **文档**: 查看项目文档目录
- **日志**: 启用详细日志 `RUST_LOG=debug rustkmer ...`

## 升级指南

### 从源码升级

```bash
# 更新源码
git pull origin main

# 重新编译
cargo build --release

# 运行测试
cargo test
```

### 版本兼容性

- **数据库格式**: 1.x版本数据库向后兼容
- **CLI接口**: 1.x版本CLI接口向后兼容
- **Python API**: 可能会在次要版本中变化

### 迁移数据

如果需要迁移旧版本数据：

```bash
# 导出旧数据库
rustkmer dump old_database.rkdb --output old_data.txt

# 创建新数据库
rustkmer count -k 21 -i sequences.fa -o new_database.rkdb
```

---

## 下一步

安装完成后，建议：

1. 阅读 [用户指南](../user-guide/)
2. 查看 [示例文档](../examples/)
3. 运行性能基准测试
4. 加入社区讨论

**祝您使用愉快！** 🎉

