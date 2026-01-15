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
git clone https://github.com/your-username/rustkmer.git
cd rustkmer

# 编译发布版本
cargo build --release

# 或者使用优化的编译配置
cargo build --release --features optimized
```

#### 第三步: 安装到系统路径

```bash
# 方法1: 创建符号链接
sudo ln -s $(pwd)/target/release/rustkmer /usr/local/bin/rustkmer

# 方法2: 复制到系统路径
sudo cp target/release/rustkmer /usr/local/bin/

# 方法3: 使用cargo安装
cargo install --path .
```

### 方式2: 使用Cargo直接安装

```bash
# 从crates.io安装（如果已发布）
cargo install rustkmer

# 从git仓库安装最新版本
cargo install --git https://github.com/your-username/rustkmer.git
```

### 方式3: 下载预编译二进制文件

#### Linux (x86_64)

```bash
# 下载最新版本
wget https://github.com/your-username/rustkmer/releases/latest/download/rustkmer-linux-x86_64.tar.gz

# 解压
tar -xzf rustkmer-linux-x86_64.tar.gz

# 安装
sudo cp rustkmer /usr/local/bin/
```

#### macOS (x86_64/ARM64)

```bash
# Intel Mac
wget https://github.com/your-username/rustkmer/releases/latest/download/rustkmer-macos-x86_64.tar.gz

# Apple Silicon Mac
wget https://github.com/your-username/rustkmer/releases/latest/download/rustkmer-macos-aarch64.tar.gz

# 解压并安装
tar -xzf rustkmer-macos-*.tar.gz
sudo cp rustkmer /usr/local/bin/
```

#### Windows (x86_64)

```powershell
# 使用PowerShell下载
Invoke-WebRequest -Uri "https://github.com/your-username/rustkmer/releases/latest/download/rustkmer-windows-x86_64.zip" -OutFile "rustkmer.zip"

# 解压
Expand-Archive rustkmer.zip -DestinationPath .

# 添加到PATH（可选）
$env:PATH += ";$(pwd)"
```

### 方式4: 使用包管理器

#### Homebrew (macOS)

```bash
# 如果还没有添加自定义tap
brew tap your-username/tap

# 安装rustkmer
brew install rustkmer
```

#### Conda

```bash
# 从bioconda安装
conda install -c bioconda rustkmer

# 或者从conda-forge
conda install -c conda-forge rustkmer
```

#### Docker

```bash
# 拉取镜像
docker pull rustkmer/rustkmer:latest

# 运行容器
docker run -v $(pwd):/data rustkmer/rustkmer:latest \
  count -k 21 -o /data/output.rkdb /data/input.fasta
```

## 快速开始

### 基本验证

```bash
# 检查版本
rustkmer --version

# 查看帮助
rustkmer --help

# 查看特定命令帮助
rustkmer count --help
rustkmer query --help
```

### 创建测试数据

```bash
# 创建测试FASTA文件
cat > test.fasta << 'EOF'
>seq1
ATGCGATGCTAGCGCTAGCTAGCTAGCTAGCTAGC
>seq2
CGATCGATCGATCGATCGATCGATCGATCGATCGA
>seq3
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT
EOF
```

### 运行第一个k-mer计数

```bash
# 基本计数
rustkmer count -k 21 -o test.rkdb test.fasta

# 查看结果
echo "Generated database:"
ls -la test.rkdb
```

### 查询k-mers

```bash
# 查询单个k-mer
rustkmer query test.rkdb ATGCGATGCTAGCGCTAGCTAG

# 查询多个k-mers
rustkmer query test.rkdb ATGCGATGCTAGCGCTAGCTAG CGATCGATCGATCGATCGATCG

# 交互式查询
rustkmer query --interactive test.rkdb
# 然后输入k-mers，每行一个，按Ctrl+D退出
```

### 数据库统计

```bash
# 查看数据库统计信息
rustkmer stats test.rkdb
```

### 导出数据

```bash
# 导出为文本格式
rustkmer dump -o test.txt test.rkdb

# 查看导出的内容
head test.txt
```

## 验证安装

### 运行测试套件

```bash
# 如果从源码安装
cd rustkmer
cargo test

# 运行集成测试
cargo test --release --test integration
```

### 性能基准测试

```bash
# 运行基准测试（需要安装criterion）
cargo bench

# 或者使用预构建的性能测试
rustkmer --run-benchmarks
```

### 系统集成测试

```bash
# 测试系统路径集成
which rustkmer
rustkmer --version

# 测试权限
rustkmer count -k 21 -o /tmp/test.rkdb /etc/hosts  # 应该成功
rustkmer count -k 21 -o /root/test.rkdb /etc/hosts  # 应该失败（权限）

# 测试大文件处理
wget https://example.com/large_genome.fasta.gz
rustkmer count -k 21 -o large_output.rkdb large_genome.fasta.gz
```

## 故障排除

### 常见问题

#### 1. Rust编译错误

**错误信息**: `error: linker 'cc' not found`

**解决方案**:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install gcc

# macOS
xcode-select --install
```

#### 2. 内存不足

**错误信息**: `fatal runtime error: out of memory`

**解决方案**:
```bash
# 减少内存使用
rustkmer count -k 21 -m 512MB -o small.rkdb small.fasta

# 使用交换空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 3. 权限问题

**错误信息**: `Permission denied`

**解决方案**:
```bash
# 检查文件权限
ls -la rustkmer
chmod +x rustkmer

# 安装到用户目录（无需sudo）
mkdir -p ~/.local/bin
cp rustkmer ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

#### 4. 依赖库问题

**错误信息**: `libssl.so.1.1: cannot open shared object file`

**解决方案**:
```bash
# Ubuntu/Debian
sudo apt-get install libssl-dev pkg-config

# CentOS/RHEL
sudo yum install openssl-devel pkgconfig

# macOS
brew install openssl
export OPENSSL_DIR=$(brew --prefix openssl)
```

#### 5. 网络连接问题

**错误信息**: `failed to get ... from registry`

**解决方案**:
```bash
# 使用国内镜像源
mkdir -p ~/.cargo
cat > ~/.cargo/config.toml << 'EOF'
[source.crates-io]
replace-with = 'ustc'

[source.ustc]
registry = "https://mirrors.ustc.edu.cn/crates.io-index"
EOF
```

### 性能问题诊断

#### CPU使用率低

```bash
# 检查线程配置
rustkmer count -k 21 -t 4 -o test.rkdb test.fasta  # 明确指定线程数

# 检查系统负载
htop
iostat -x 1
```

#### 内存使用高

```bash
# 监控内存使用
/usr/bin/time -v rustkmer count -k 21 test.fasta -o test.rkdb

# 限制内存使用
ulimit -v 4294967296  # 4GB虚拟内存限制
```

### 日志和调试

#### 启用详细日志

```bash
# 设置日志级别
RUST_LOG=debug rustkmer count -k 21 test.fasta -o test.rkdb

# 或使用环境变量
export RUST_LOG=info
rustkmer count -k 21 test.fasta -o test.rkdb
```

#### 使用调试模式

```bash
# 编译调试版本
cargo build

# 使用gdb调试
gdb target/debug/rustkmer
(gdb) set args count -k 21 test.fasta -o test.rkdb
(gdb) run
```

## 升级指南

### 从源码升级

```bash
cd rustkmer
git pull origin main
cargo build --release
sudo cp target/release/rustkmer /usr/local/bin/
```

### 使用Cargo升级

```bash
# 从crates.io升级
cargo install rustkmer --force

# 从git仓库升级
cargo install --git https://github.com/your-username/rustkmer.git --force
```

### 数据库兼容性

RustKmer保持向后兼容性，但建议在新版本发布时：

```bash
# 备份旧数据库
cp old_database.rkdb old_database.rkdb.backup

# 测试新版本
rustkmer --version
rustkmer query old_database.rkdb ATGCGATGCTAGCGCTAGCTAG

# 如果需要，重新创建数据库
rustkmer count -k 21 -o new_database.rkdb input.fasta
```

## 高级配置

### 环境变量

```bash
# 设置默认内存限制
export RUSTKMER_DEFAULT_MEMORY=4G

# 设置默认线程数
export RUSTKMER_DEFAULT_THREADS=$(nproc)

# 设置缓冲区大小
export RUSTKMER_BUFFER_SIZE=16777216  # 16MB

# 启用性能监控
export RUSTKMER_PROFILE=1
```

### 配置文件

```bash
# 创建配置文件
mkdir -p ~/.config/rustkmer
cat > ~/.config/rustkmer/config.toml << 'EOF'
[default]
kmer_size = 21
memory = "2G"
threads = 4
canonical = true
format = "binary"

[performance]
buffer_size = 16777216
compression_level = 6
[logging]
level = "info"
file = "~/.local/share/rustkmer/rustkmer.log"
EOF
```

### 集群配置

```bash
# SLURM作业脚本示例
cat > rustkmer_job.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=rustkmer
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=24:00:00

module load rust

rustkmer count \
  -k 21 \
  -t $SLURM_CPUS_PER_TASK \
  -m 30G \
  --format binary \
  --canonical \
  --sort \
  -o output.rkdb \
  input.fasta
EOF

sbatch rustkmer_job.sh
```

---

现在您已经成功安装了RustKmer！如果遇到任何问题，请查看[故障排除](#故障排除)部分或访问项目的GitHub页面获取更多帮助。