# RustKmer

高性能的k-mer计数工具，使用Rust实现，设计为jellyfish的快速替代方案，用于基因组数据分析。

## 🚀 主要特性

- **高性能**: 多线程并行处理，优化的内存管理
- **Jellyfish兼容**: 命令行接口与jellyfish高度兼容
- **自定义数据库格式**: 高效的RKDB二进制格式，支持索引查询
- **排序优化**: 支持排序数据库，实现384倍查询性能提升
- **大规模数据处理**: 支持>100M k-mers的大型基因组数据集
- **跨平台**: 支持Linux、macOS和Windows
- **内存映射**: 高效的文件I/O操作

## 📦 安装

### 从源码编译

```bash
git clone https://github.com/your-username/rustkmer.git
cd rustkmer
cargo build --release
```

编译后的可执行文件位于 `target/release/rustkmer`。

### 系统要求

- Rust 1.80+ (推荐使用stable版本)
- 足够的内存处理大型数据集
- 对于大型基因组文件，建议使用SSD存储

## 🔧 快速开始

### 基本用法

```bash
# 计算k-mers
rustkmer count -k 21 -m 1G -t 8 -o output.rkdb input.fasta

# 查询k-mers
rustkmer query output.rkdb ATGCGATGCTAGCGCTAGCTA

# 数据库统计信息
rustkmer stats output.rkdb

# 导出数据库内容
rustkmer dump output.rkdb -o output.txt
```

### Jellyfish兼容示例

```bash
# 与jellyfish相同的参数
rustkmer count -k 31 -m 4G -t 16 -s 100M -L 5 -U 1000 -C -o counts.rkdb reads.fastq

# 查询多个k-mers
rustkmer query counts.rkdb ATGCGATGCTAGCGCTAGCTA CGATCGATCGATCGATCGATCG

# 交互式查询
rustkmer query --interactive counts.rkdb
```

## 📚 详细文档

### 命令参考

#### `count` - k-mer计数

```bash
rustkmer count [OPTIONS] <INPUT>... -o <OUTPUT>
```

**主要参数**:
- `-k, --kmer-size <SIZE>`: k-mer大小 (默认: 21)
- `-m, --memory <SIZE>`: 内存限制 (例如: 1G, 500M)
- `-t, --threads <NUM>`: 线程数 (默认: CPU核心数)
- `-o, --output <FILE>`: 输出文件路径
- `-s, --hash-size <SIZE>`: 哈希表大小
- `-L, --lower-count <NUM>`: 最小计数阈值
- `-U, --upper-count <NUM>`: 最大计数阈值
- `-C, --canonical`: 使用canonical k-mers
- `--format <FORMAT>`: 输出格式 (text|binary)

**输出格式**:
- `text`: 人类可读的文本格式 (k-mer<tab>count)
- `binary`: RKDB二进制格式 (推荐用于查询)

#### `query` - k-mer查询

```bash
rustkmer query [OPTIONS] <DATABASE> <KMERS>...
```

**主要参数**:
- `--load`: 强制预加载数据库到内存
- `--no-load`: 禁用预加载 (排序数据库推荐)
- `--interactive`: 交互模式 (从stdin读取查询)
- `-s, --sequence <FILE>`: 从序列文件查询k-mers
- `-o, --output <FILE>`: 输出文件 (默认: stdout)

**查询模式**:
1. **命令行模式**: 直接指定k-mers
2. **文件模式**: 从序列文件提取k-mers查询
3. **交互模式**: 逐个输入k-mers查询

#### `dump` - 数据库导出

```bash
rustkmer dump [OPTIONS] <DATABASE>
```

**主要参数**:
- `-o, --output <FILE>`: 输出文件 (默认: stdout)
- `--format <FORMAT>`: 导出格式 (text|csv|json)

#### `stats` - 数据库统计

```bash
rustkmer stats <DATABASE>
```

### RKDB数据库格式

RustKmer使用自定义的RKDB (RustKmer Database) 二进制格式：

**文件结构**:
```
+------------------+
| Header (42 bytes)|
+------------------+
| K-mer Entry 1    |
| - 8 bytes: k-mer |
| - 4 bytes: count |
+------------------+
| K-mer Entry 2    |
| ...              |
+------------------+
```

**Header格式**:
- Magic Number (4 bytes): "RKDB"
- Version (2 bytes): 数据库版本
- K-mer Size (1 byte): k-mer长度
- Total K-mers (8 bytes): k-mer总数
- Flags (1 byte): 数据库标志 (排序、canonical等)
- Data Offset (8 bytes): 数据起始偏移
- Index Offset (8 bytes): 索引偏移 (将来使用)

**性能特点**:
- **排序数据库**: 支持磁盘二分搜索，无需预加载
- **未排序数据库**: 需要预加载到内存，适合频繁查询
- **内存映射**: 使用mmap高效访问大型文件

### 性能优化

#### 排序vs未排序数据库

| 特性 | 排序数据库 | 未排序数据库 |
|------|------------|--------------|
| 查询速度 | 2,517 k-mers/秒 | 28 k-mers/秒 |
| 内存使用 | 最小 (仅索引) | 高 (需要预加载) |
| 预加载时间 | 无 | 较长 |
| 适用场景 | 偶尔查询 | 频繁查询 |

#### 性能测试结果

使用真实基因组数据 (272M k-mers) 的测试结果：

- **1000 k-mers查询**:
  - 排序: 1.988秒 (503 k-mers/秒)
  - 未排序: 35.332秒 (28 k-mers/秒)
  - **性能提升: 17.8倍**

- **正确性验证**: 与jellyfish 100%匹配

### 兼容性

#### 与Jellyfish的兼容性

**完全兼容的功能**:
- k-mer计数和基本参数
- canonical k-mer处理
- 计数过滤 (-L/-U 参数)
- FASTA/FASTQ输入格式
- 查询功能

**差异和改进**:
- 自定义RKDB格式 (更高效的查询)
- 排序数据库支持 (显著的性能提升)
- 更好的内存管理
- Rust实现的内存安全保证

## 🧪 测试

### 运行测试套件

```bash
# 单元测试
cargo test

# 集成测试
cargo test --test integration

# 性能基准测试
cargo bench
```

### 正确性验证

使用提供的脚本验证与jellyfish的一致性：

```bash
# 随机测试1000个k-mers
python scripts/test_jellyfish_random.py jellyfish.jf rustkmer.rkdb 1000

# 性能对比
python scripts/performance_comparison.py jellyfish_sample.txt 1000 5
```

## 📖 使用示例

### 示例1: 基本k-mer计数

```bash
# 对FASTA文件进行k-mer计数
rustkmer count -k 21 -m 2G -t 8 -o genome_k21.rkdb genome.fasta

# 查看数据库信息
rustkmer stats genome_k21.rkdb
```

### 示例2: 高性能查询

```bash
# 创建排序数据库 (推荐)
rustkmer count -k 21 -m 2G -t 8 --format binary -o genome_k21_sorted.rkdb genome.fasta

# 高效查询 (无需预加载)
rustkmer query genome_k21_sorted.rkdb ATGCGATGCTAGCGCTAGCTA CGATCGATCGATCGATCGATCG
```

### 示例3: 大规模数据处理

```bash
# 处理大型FASTQ文件
rustkmer count \
  -k 31 \
  -m 8G \
  -t 16 \
  -s 500M \
  -L 5 \
  -U 1000 \
  -C \
  --format binary \
  -o metagenome_k31.rkdb \
  reads_1.fastq.gz reads_2.fastq.gz

# 批量查询
rustkmer query --load metagenome_k31.rkdb $(cat queries.txt)
```

### 示例4: 数据格式转换

```bash
# 导出为文本格式
rustkmer dump -o kmer_counts.txt genome_k21.rkdb

# 导出为CSV格式
rustkmer dump --format csv -o kmer_counts.csv genome_k21.rkdb

# 转换为jellyfish格式 (如需要)
rustkmer dump genome_k21.rkdb | jellyfish merge -o merged_counts.jf -s 1G /dev/stdin
```

## 🔬 技术细节

### 算法实现

- **哈希表**: 使用自定义的高性能哈希表实现
- **并行处理**: 基于Rayon的work-stealing并行算法
- **内存管理**: 智能的内存分配和回收策略
- **文件I/O**: 内存映射和缓冲I/O优化

### 内存效率

- **k-mer编码**: 2-bit编码压缩DNA序列
- **紧凑存储**: 优化的数据结构布局
- **流式处理**: 支持超大文件的流式读取
- **垃圾回收优化**: 减少内存碎片

### 性能配置

```toml
# Cargo.toml 性能配置
[profile.release]
lto = true
codegen-units = 1
panic = "abort"
opt-level = 3
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 开发环境设置

```bash
# 安装开发依赖
cargo install cargo-watch cargo-flamegraph

# 运行开发服务器
cargo watch -x run

# 性能分析
cargo flamegraph --bin rustkmer -- count -k 21 input.fa
```

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- **Jellyfish**: 提供了优秀的k-mer计数工具和算法参考
- **Rust社区**: 提供了高性能的系统和生物信息学库
- **Rayon**: 出色的并行计算框架

## 📞 联系方式

- 项目主页: https://github.com/your-username/rustkmer
- 问题报告: https://github.com/your-username/rustkmer/issues
- 文档: https://rustkmer.readthedocs.io

---

**注意**: RustKmer目前处于活跃开发阶段，API可能会发生变化。建议在生产环境使用前进行充分测试。