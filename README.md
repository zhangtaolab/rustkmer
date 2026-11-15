<!-- generated-by: gsd-doc-writer -->
# RustKmer

[![CI](https://github.com/zhangtaolab/rustkmer/actions/workflows/ci.yml/badge.svg)](https://github.com/zhangtaolab/rustkmer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-blue.svg)](Cargo.toml)
[![Rust](https://img.shields.io/badge/rust-1.82%2B-orange.svg)](https://www.rust-lang.org)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyo3/pyproject.toml)

RustKmer 是用 Rust 编写的高性能 k-mer 计数与查询工具包。它提供两个共享同一核心库的入口：命令行工具 `rustkmer`（基于 clap）和 Python 扩展模块 `pyrustkmer`（基于 PyO3）。两者读写同一种自定义二进制 `.rkdb` 格式，面向需要在基因组规模上计数、查询和合并 k-mer 的生物信息学用户。

- 支持 k = 1–64（k-mer 编码为 `u128`），可选用 canonical 形式计数
- 计数默认输出按 k-mer 排序的 `.rkdb` 数据库，支持磁盘二分搜索，无需整体预加载
- 支持通配符 `N`、汉明距离突变容忍和位置特异突变的模糊查询
- 支持前缀查询与混合模式查询（如前缀中夹带通配符）
- 合并支持显式内存预算：预算内走内存合并，超预算按策略路由到流式外部排序
- 自动读取 `.gz` / `.bz2` / `.xz` 压缩的 FASTA/FASTQ 输入
- 并行计数（rayon + 分片并发哈希表）和内存映射文件访问

## 系统要求

- Rust 1.82 或更高版本（`Cargo.toml` 的 `rust-version = "1.82"`）
- Python 3.11 或更高版本（仅构建/使用 `pyrustkmer` 时需要；`pyo3/pyproject.toml` 声明 `requires-python = ">=3.11"`）
- Linux、macOS 或 Windows；CI 在三个平台上运行根 crate 测试与 PyO3 wheel 构建
- 构建 Python 扩展还需要 `maturin >= 1.0, < 2.0` 和 C/C++ 工具链

## 安装

### 从源码构建 CLI

```bash
git clone https://github.com/zhangtaolab/rustkmer.git
cd rustkmer
cargo build --release
./target/release/rustkmer --version
```

如果希望把二进制安装到 Cargo 的 bin 目录：

```bash
cargo install --path .
```

### 从源码构建 Python 扩展

```bash
cd pyo3
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install 'maturin>=1.0,<2.0'
maturin develop --release
python -c "from pyrustkmer import PyCounter; print('pyrustkmer ready')"
```

`pyrustkmer` 的运行时依赖是 `numpy >= 1.21`，由 `pyo3/pyproject.toml` 声明。

### 从 PyPI 安装

```bash
pip install pyrustkmer
```

<!-- VERIFY: pyrustkmer 在 PyPI 上的发布状态无法仅从仓库内容确认；包名取自 pyo3/pyproject.toml 的 [project].name -->

## 快速开始

### CLI

```bash
# 1. 计数并生成默认排序的 RKDB 数据库
rustkmer count -k 21 --threads 8 -i genome.fa -o genome_k21.rkdb

# 2. 查询单个 k-mer
rustkmer query genome_k21.rkdb ATGCGATGCTAGCGCTAGCTA

# 3. 查看数据库统计
rustkmer stats genome_k21.rkdb
```

`count` 默认对输出排序（`--sort` 为保留的空操作别名）；如需更快的计数写入未排序数据库，使用 `--no-sort`。`-o` 可省略，此时只打印计数统计，不写出数据库文件。

### Python

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# 计数并保存为排序数据库
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa")
counter.add_sequence("ACGTACGTACGTACGTACGTACGT")
stats = counter.get_stats()
print(stats.unique_kmers, stats.total_kmers)
counter.save_database("genome_k21.rkdb")

# 加载数据库并查询
db = PyDatabase("genome_k21.rkdb", LoadMode.Preload)
result = db.query_exact("ATGCGATGCTAGCGCTAGCTA")
print(result.found, result.count)
```

## 使用示例

### 批量查询与模糊查询

```bash
# 从 FASTA 中提取 k-mer 并批量查询
rustkmer query genome_k21.rkdb --sequence queries.fa -o results.txt

# 从文本文件读取 k-mer（每行一个）
rustkmer query genome_k21.rkdb --batch kmers.txt

# 通配符查询：N 匹配 A/T/C/G（模式长度需与 k 一致，最多相差 3）
rustkmer fuzzy-query genome_k21.rkdb "ATNNGTACGTACGTACGTACG"

# 突变容忍查询（汉明距离上限 2）
rustkmer fuzzy-query genome_k21.rkdb "ATCGATCGATCGATCGATCGA" -m 2

# 批量模糊查询并输出 CSV
rustkmer fuzzy-query-batch genome_k21.rkdb -s patterns.txt -o results.csv -f csv --include-headers
```

模糊查询的模式长度需与数据库 k 值匹配：CLI 允许相差不超过 3（不足时用 `N` 补齐、超出时截断），Python 绑定要求严格相等。

### 前缀与混合查询

```bash
# 前缀查询（前缀长度必须小于 k）
rustkmer prefix-query genome_k21.rkdb -x ATG

# 使用 pattern 参数
rustkmer prefix-query genome_k21.rkdb -p ATG

# 混合模式：前缀中夹带 N 通配符
rustkmer prefix-query genome_k21.rkdb -p "ATAC{N5}ACAC" --hybrid
```

### 合并数据库

```bash
# 基本合并（至少两个输入）
rustkmer merge -i part1.rkdb part2.rkdb -o merged.rkdb

# 限制合并内存预算并显式选择流式合并
rustkmer merge -i part1.rkdb part2.rkdb -o merged.rkdb \
  --max-memory 32GB --merge-mode streaming
```

### Python：前缀查询与模糊查询

```python
from pyrustkmer import PyDatabase, PyFuzzyQuery, PyPrefixQuery, LoadMode

db = PyDatabase("genome_k21.rkdb", LoadMode.Preload)

# PyDatabase.query_prefix 返回 PyPrefixQueryResult
prefix = db.query_prefix("ATG")
print(prefix.total_matches, prefix.matches)

# 独立的查询引擎返回 dict[str, str]
engine = PyPrefixQuery("genome_k21.rkdb")
matches = engine.query_prefix("ATG")
print(len(matches))

# 模糊查询
fuzzy = PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ATNNGTACGTACGTACGTACG", max_mutations=0)
print(result.total_matches)
for match in result.get_top_matches(5):
    print(match.kmer, match.count)
```

`LoadMode` 提供三种加载方式：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `LoadMode.Preload` | 构建 `BTreeMap` k-mer 缓存，查询最快 | 小/中数据库、频繁查询 |
| `LoadMode.MemoryMapped` | 打开文件句柄、不构建 `BTreeMap` 缓存；数据库仍在构造时完整载入。精确查询在此模式下未实现，`query_exact` 返回 `found=False` | 数据库导出/遍历；需要精确查询时改用 `Preload` 或 `Lazy` |
| `LoadMode.Lazy` | 构建排序索引用于二分搜索 | 查询较少、超大数据库 |

## 命令参考

| 命令 | 作用 |
|------|------|
| `count` | 统计 FASTA/FASTQ 中的 k-mer 并写出 `.rkdb` 或文本 |
| `query` | 从数据库查询单个/批量 k-mer，或进入交互模式 |
| `stats` | 输出数据库统计信息（文本/JSON/CSV/TSV） |
| `dump` | 将数据库内容导出为文本 |
| `merge` | 合并多个兼容的 `.rkdb` 数据库 |
| `fuzzy-query` | 通配符/突变容忍的单条模糊查询 |
| `fuzzy-query-batch` | 从文件批量执行模糊查询 |
| `prefix-query` | 对排序数据库执行前缀或混合模式查询 |

### `count`

```bash
rustkmer count -k <K> -i <INPUT>... [-o <OUTPUT>] [OPTIONS]
```

- `-k, --k <SIZE>`：k-mer 大小，1–64
- `-i, --input <FILES>...`：输入文件，可多个；与 `-d, --directory` 互斥
- `-d, --directory <DIR>`：处理目录中的文件；`-s, --select` 交互选择文件；`--no-recursive` 关闭递归
- `-o, --output <FILE>`：输出文件；省略时只输出统计
- `-C, --canonical`：使用 canonical k-mer 计数
- `--size <SIZE>`：哈希表初始大小，默认 `1000000`
- `--format <binary|text>`：输出格式，默认 `binary`
- `--threads <N>`：并行线程数；优先级为 `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > 全部核心
- `-L, --min-count <N>` / `-U, --max-count <N>`：按计数过滤
- `--no-sort`：不排序输出；排序默认开启，`--sort` 是保留的空操作
- `-q, --quiet` / `-v, --verbose` / `--show-warnings`

### `query`

```bash
rustkmer query <DATABASE> [KMERS]... [OPTIONS]
```

- 位置参数 `KMERS...`：直接查询的 k-mer
- `-s, --sequence <FILE>`：从 FASTA 文件提取 k-mer 批量查询
- `-b, --batch <FILE>`：从文本文件读取 k-mer（每行一个）
- `-o, --output <FILE>`：输出文件，默认 stdout
- `-i, --interactive`：从 stdin 交互查询
- `-l, --load`：强制预加载；`-L, --no-load`：禁用预加载

### `stats`

```bash
rustkmer stats <DATABASE> [OPTIONS]
```

- `-f, --format <text|json|csv|tsv>`：输出格式，默认 `text`
- `-o, --output <FILE>`：输出文件
- `--detailed`：包含频率分布；`--max-bins <N>`：频率分布分箱上限
- `--approximate`：使用近似中位数以降低内存
- `--progress`：显示进度
- `--split-output`：拆分基础统计与频率分布；需配合 `--freq-output <FILE>`

### `dump`

```bash
rustkmer dump <DATABASE> [-o <FILE>]
```

### `merge`

```bash
rustkmer merge -i <DB1> <DB2> [...] -o <OUTPUT> [OPTIONS]
```

- `-i, --input <FILES>...`：至少两个输入数据库
- `-o, --output <FILE>`：输出数据库，必填
- `--max-memory <SIZE>`：内存预算，如 `32GB`、`1TB`
- `--merge-mode <auto|memory|streaming>`：合并策略，默认 `auto`
- `--use-prefix-cache`：启用前缀缓存合并路径
- `--batch-size <N>`：前缀缓存合并的缓冲刷写批量，默认 `100000`
- `--num-threads <N>`：线程数，`0` 表示全部核心
- `--temp-dir <DIR>`：流式合并临时目录
- `--check-compatibility`：只检查兼容性，不执行合并
- `--keep-intermediate`：保留中间文件用于调试
- `-v, --verbose` / `-q, --quiet`

合并要求所有输入具有相同的 k-mer 大小；canonical 设置默认也必须一致，但启用 `--use-prefix-cache` 时会跳过 canonical 检查，混合 canonical 的输入统一转换为 canonical 模式合并。

### `fuzzy-query`

```bash
rustkmer fuzzy-query <DATABASE> <QUERY> [OPTIONS]
```

- `<QUERY>`：可包含 `N` 通配符；长度与数据库 k 值最多相差 3（不足补 `N`、超出截断）
- `-m, --mutations <N>`：最大汉明距离，默认 `0`
- `-M, --max-variants <N>`：最大变体生成数，默认 `10000`
- `-b, --batch-size <N>`：批处理大小，默认 `1000`
- `--position-mutations <SPEC>`：位置特异突变，如 `"3,4,5:2"` 或 `"3,4,5:2;6,7:1"`
- `-f, --format <table|json|tsv|csv>`：输出格式，默认 `table`
- `-o, --output <FILE>`：输出文件
- `-v, --verbose` / `-q, --quiet` / `--profile`

### `fuzzy-query-batch`

```bash
rustkmer fuzzy-query-batch <DATABASE> -s <QUERIES> [OPTIONS]
```

- `-s, --sequence <FILE>`：查询文件，每行一个模式（必填）
- `--default-mutations <N>`：默认最大汉明距离，默认 `0`
- `--default-max-variants <N>`：默认最大变体数，默认 `10000`
- `-b, --batch-size <N>`：批处理大小，默认 `100`
- `-f, --format <table|json|tsv|csv>`
- `-o, --output <FILE>`
- `--include-headers`：CSV/TSV 输出包含表头
- `--fail-fast`：遇到首个错误即停止

### `prefix-query`

```bash
rustkmer prefix-query <DATABASE> (-p <PATTERN> | -x <PREFIX>) [OPTIONS]
```

- `-p, --pattern <PATTERN>`：要匹配的序列模式，可含 `{N5}` 形式
- `-x, --prefix <PREFIX>`：显式前缀（与 `-p` 互斥）
- `--hybrid`：混合搜索模式，需配合 `-p`；模式中含 `{` 时自动启用
- `-f, --format <table|json|csv|tsv>`：输出格式，默认 `table`
- `-o, --output <FILE>`
- `-L, --min-count <N>` / `-U, --max-count <N>`
- `--profile` / `-v, --verbose` / `-q, --quiet`

## RKDB 数据库格式

`.rkdb` 是固定布局的二进制文件，没有服务端进程，也不使用关系型数据库。

```
+------------------------------+
| Header (42 bytes)            |
+------------------------------+
| KmerEntry 1 (20 bytes)       |
| KmerEntry 2 (20 bytes)       |
| ...                          |
+------------------------------+
```

**头部（42 字节，小端）**

| 字段 | 大小 | 说明 |
|------|------|------|
| Magic | 4 字节 | `"RKDB"` |
| Version | 2 字节 | 当前为 `2` |
| K-mer size | 1 字节 | k 值 |
| Padding | 3 字节 | 4 字节对齐填充 |
| Total k-mers | 8 字节 | 记录条数（distinct entries），不是各 count 之和 |
| Flags | 1 字节 | bit 0 = 已排序，bit 1 = canonical |
| Padding | 7 字节 | 8 字节对齐填充 |
| Data offset | 8 字节 | 数据区起始偏移，规范值为 42 |
| Index offset | 8 字节 | 索引区偏移（当前保留） |

**记录（20 字节）**

| 字段 | 大小 | 说明 |
|------|------|------|
| k-mer | 16 字节 | 小端 `u128`；k ≤ 64 |
| Count | 4 字节 | 小端 `u32` 计数 |

排序数据库可按 k-mer 顺序做二分搜索；内存映射模式适合大于可用内存的数据库。读取端会校验头部：`data_offset` 不是规范值时视为不兼容或损坏文件。并发写同一个 `.rkdb` 路径没有文件锁保护，会导致数据损坏。

## 性能与基准测试

仓库内的基准测试工具位于 `scripts/bench/`，只依赖 Python 3 标准库。它通过操作系统 rusage（macOS 的 `/usr/bin/time -l` 或 Linux 的 `/usr/bin/time -v`）采集 release 二进制的 wall-clock 时间与峰值 RSS，并要求每次运行的 `distinct_kmers > 0`。

已提交的完整对比报告见 [docs/benchmark-report.md](docs/benchmark-report.md)，由已提交的结果 JSON 机械渲染。报告中的代表性数据（arm `count-A`）：

| 场景 | RustKmer | Jellyfish2 | 对比 |
|------|----------|------------|------|
| k=31 全量计数 | 494.19 s / 55.22 GiB | 843.02 s / 84.00 GiB | wall −41.4%，峰值 RSS −34.3% |
| k=21 全量计数 | 505.77 s / 49.27 GiB | 97.26 s / 46.84 GiB | wall +420.0%，RSS +5.2% |
| k=31 切片计数 | 16.17 s / 5.59 GiB | 22.90 s / 84.84 GiB | wall −29.4%，峰值 RSS −93.4% |

报告结论明确指出：RustKmer 在 k=31 全量计数上快于 Jellyfish2，在 k=21 全量计数上慢于 Jellyfish2；不同 k 值和规模下的结果并不一致。

本地运行：

```bash
# 合成输入上的正确性自检（约 1 分钟）
python3 scripts/bench/bench.py --mode synthetic --self-check

# 生成结果并与已提交基线比较
python3 scripts/bench/bench.py --mode synthetic --out results.json
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current results.json --wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory
```

CI 回归门禁（`.github/workflows/benchmark.yml`）在 `ubuntu-latest` 和 `macos-latest` 上运行：构建 release 二进制、测量合成输入、上传结果 artifact，再与该平台的已提交基线比较。当前阈值：wall +25% 为 advisory（打印并标记但不使门禁失败），峰值 RSS +15% 为硬门禁。`compare.py` 的退出码为 `0` 通过、`1` 回归、`2` 输入无效；基线按平台分开提交，跨平台比较会以退出码 `2` 拒绝。维护者流程见 [scripts/bench/README.md](scripts/bench/README.md)。

## 内存受限合并

`rustkmer merge` 支持显式内存预算（`--max-memory`，接受 `32GB`、`1TB` 等格式）和合并策略（`--merge-mode auto|memory|streaming`）：

- **默认预算**：未指定 `--max-memory` 时取系统总内存的 50%；Linux 读取 `/proc/meminfo` 的 `MemTotal`，不可用平台（包括 macOS）回退为 32GB。
- **只读头部估算**：路由前只读取每个输入的 42 字节头部（`total_kmers` 记录条数）估算内存，不扫描整个文件；头部不可读或 `total_kmers == 0` 时按文件大小回退估算（每条记录 20 字节）并输出警告。
- **`auto`（默认）**：估算超出预算时无条件路由到流式合并（外部排序），预算内的输入仍走内存快速路径。
- **`memory`**：强制内存合并；估算超出预算时直接报错拒绝，而不是冒险 OOM。
- **`streaming`**：始终流式合并，忽略估算。
- **临时文件**：流式合并按每块 5000 万 k-mer 分块外部排序，临时文件由 RAII 管理器清理，即使中途出错也会在析构时删除。
- **`--use-prefix-cache`**：启用带错误隔离的前缀缓存合并路径，配合 `--batch-size`、`--num-threads` 使用；在该路径下 `--merge-mode` 选择的是桶内策略而非顶层路由。

## 计数器内存布局

`KmerCounter`（`src/hash/table.rs`）按 k 值自动选择哈希表存储宽度：

| k 范围 | 内部存储 | 每个 (K, V) slot 大小 |
|--------|----------|----------------------|
| k ≤ 32 | `DashMap<u64, u32>`（dense） | 16 字节 |
| 33 ≤ k ≤ 64 | `DashMap<u128, u32>`（wide） | 32 字节 |

宽度在构造时根据 k 决定，对上层 API 透明：`get_all_counts` 等接口仍返回 `Vec<(u128, u32)>`，k ≤ 32 时在边界处窄化。相比统一使用 `u128` key，常见场景（k ≤ 32）的每 slot 内存占用约减半。

## Python API

`pyrustkmer` 由 `pyo3/src/lib.rs` 注册并导出以下主要类型（另有 `PyQueryResult`、`PyPrefixQueryResult`、`PyFuzzyResult`、`PyFuzzyMatch`、`PyDatabaseStats`、`PyCounterStats`、`PyPrefixQueryMetrics` 等查询结果/统计载荷类型）：

| 类型 | 作用 |
|------|------|
| `PyCounter` | 计数 k-mer，支持从序列、FASTA、FASTQ 读入并保存 `.rkdb` |
| `PyDatabase` | 加载数据库并执行精确、批量、前缀查询；`query_fuzzy` 为占位实现，模糊查询请用 `PyFuzzyQuery` |
| `PyFuzzyQuery` | 通配符/突变容忍查询引擎 |
| `PyPrefixQuery` | 前缀查询引擎；`query_prefix` 返回 `dict[str, str]` |
| `PyExtendedPrefixQuery` | 带性能指标的前缀/混合查询引擎 |
| `PyFormatter` | 查询结果格式化工具 |
| `LoadMode` | `Preload` / `MemoryMapped` / `Lazy` |
| `RustKmerError` | 自定义 Python 异常类型 |

常用方法：

- `PyCounter(kmer_length, canonical=False, initial_capacity=1000, threads=None)`；非法 k 值或线程数抛出 `ValueError`
- `counter.add_sequence(seq)`、`add_from_fasta(path)`、`add_from_fastq(path)`、`save_database(path)`、`get_stats()`
- `db.query_exact(kmer)` → `PyQueryResult`（`kmer`、`count`、`found`）
- `db.query_exact_batch(kmers)` → `dict[str, PyQueryResult]`
- `db.query_prefix(prefix)` → `PyPrefixQueryResult`（`total_matches`、`matches`、`query_time_ms`）
- `fuzzy.query_fuzzy(pattern, max_mutations)` → `PyFuzzyResult`（`total_matches`、`get_top_matches(limit)`）；`pattern` 长度必须严格等于数据库 k 值

Python 绑定测试位于 `pyo3/tests/`，运行方式：

```bash
cd pyo3
pytest
```

## 持续集成

`.github/workflows/ci.yml` 在针对 `dev`/`main` 的 pull request 和 push 上运行，覆盖 Ubuntu、macOS、Windows：

| Job | 内容 |
|-----|------|
| `fmt` | `cargo fmt --all --check` |
| `clippy-root` | Rust 1.82 下 `cargo clippy --locked --all-targets -- -D warnings` |
| `test-root` | `cargo test --locked` |
| `pyo3-build` | pyo3 crate 的 clippy 检查 + `maturin build`（wheel，Python 3.11） |
| `pyo3-pytest` | 安装 wheel 后运行 `pytest tests/ --cov=pyrustkmer --cov-fail-under=80` |

所有门禁 job 均未设置 `continue-on-error`，任一 job 失败都会导致 PR 失败。另有 `benchmark.yml`（性能回归门禁）和 `docs.yml`（MkDocs 文档站构建与 GitHub Pages 部署）。

本地运行同等的核心检查：

```bash
cargo fmt --all --check
cargo clippy --all-targets -- -D warnings
cargo test
cd pyo3 && cargo clippy --all-targets -- -D warnings && maturin build
```

## 文档

- [用户指南](USER_GUIDE.md)：完整使用指南与最佳实践
- [安装说明](INSTALL.md)：更多安装与环境配置方式
- [基准测试报告](docs/benchmark-report.md)：与 Jellyfish2 的对比结果
- [前缀查询指南](docs/guides/prefix-query-guide.md) / [混合搜索指南](docs/guides/hybrid-search-guide.md)
- [基准工具说明](scripts/bench/README.md)
- 文档站：<https://rustkmer.github.io>
- 示例脚本：`examples/bash/`、`examples/python/`、`examples/application/`

## 故障排除

**`maturin develop` 报 VIRTUAL_ENV 与 CONDA_PREFIX 冲突**

同时激活 virtualenv 和 conda 环境时 maturin 会拒绝构建。只保留一种环境，或清理变量后重试：

```bash
unset VIRTUAL_ENV
unset CONDA_PREFIX
cd pyo3
maturin develop --release
```

**Python 版本低于 3.11**

`pyo3/pyproject.toml` 要求 `requires-python = ">=3.11"`。用 `python3.11 -m venv .venv` 创建环境，或使用 conda 创建 `python=3.11` 环境。

**找不到 `rustkmer` 命令**

源码构建的二进制位于 `target/release/rustkmer`。将其加入 `PATH`，或运行 `cargo install --path .` 安装到 Cargo bin 目录。

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境、代码规范、分支与 PR 流程。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

## 项目结构

```
rustkmer/
├── src/              # Rust 核心库与 CLI（src/main.rs、src/cli/）
├── pyo3/             # PyO3 扩展 crate（模块名 pyrustkmer）
├── tests/            # Rust 集成/属性测试
├── examples/         # Bash、Python 与具体应用示例
├── scripts/bench/    # 基准测试与回归门禁工具
├── docs/             # MkDocs 文档源
└── README.md
```
