# RustKmer API 文档

本文档详细描述了RustKmer的内部API和数据结构，供开发者参考和扩展使用。

## 目录

- [核心模块](#核心模块)
- [数据库格式](#数据库格式)
- [错误处理](#错误处理)
- [CLI接口](#cli接口)
- [示例代码](#示例代码)

## 核心模块

### `rustkmer::kmer`

k-mer处理的核心模块，提供编码、解码和操作功能。

#### `encode_kmer_bytes`

```rust
pub fn encode_kmer_bytes(seq: &[u8]) -> Result<u64>
```

将DNA序列编码为64位整数。

**参数**:
- `seq`: DNA序列字节切片，只包含A、T、G、C

**返回值**:
- `Ok(u64)`: 编码后的k-mer值
- `Err(KmerError)`: 编码错误

**示例**:
```rust
use rustkmer::kmer::encoding::encode_kmer_bytes;

let kmer_val = encode_kmer_bytes(b"ATGC")?;
println!("Encoded k-mer: {:x}", kmer_val);
```

#### `canonical_kmer`

```rust
pub fn canonical_kmer(kmer: u64, k: usize) -> u64
```

计算canonical k-mer（lexicographically较小的正向或反向互补序列）。

**参数**:
- `kmer`: 编码的k-mer值
- `k`: k-mer长度

**返回值**:
- `u64`: canonical k-mer值

#### `reverse_complement`

```rust
pub fn reverse_complement(kmer: u64, k: usize) -> u64
```

计算k-mer的反向互补序列。

### `rustkmer::database`

数据库操作模块，提供RKDB格式的读写和查询功能。

#### `DatabaseHeader`

```rust
pub struct DatabaseHeader {
    pub magic: [u8; 4],      // "RKDB"
    pub version: u16,        // 数据库版本
    pub kmer_size: u8,       // k-mer长度
    pub total_kmers: u64,    // k-mer总数
    pub sorted: bool,        // 是否排序
    pub data_offset: u64,    // 数据偏移
    pub index_offset: u64,   // 索引偏移
    pub canonical: bool,     // 是否canonical模式
}
```

数据库头部信息结构。

#### `KmerDatabase`

```rust
pub struct KmerDatabase {
    header: DatabaseHeader,
    file: std::fs::File,
    mmap: Option<memmap2::Mmap>,
}
```

k-mer数据库的主要结构。

**方法**:

##### `new`

```rust
pub fn new<P: AsRef<Path>>(path: P) -> Result<Self>
```

创建新的数据库实例。

##### `query_kmer`

```rust
pub fn query_kmer(&self, kmer: &str) -> Result<Option<u32>>
```

查询单个k-mer的计数。

##### `query_kmers`

```rust
pub fn query_kmers(&self, kmers: &[String]) -> Result<Vec<(String, u32)>>
```

批量查询k-mers。

##### `binary_search`

```rust
fn binary_search(&self, target: u64) -> Result<Option<(u64, u32)>>
```

内部二分搜索函数（用于排序数据库）。

### `rustkmer::hash`

高效的哈希表实现，用于k-mer计数。

#### `KmerCounter`

```rust
pub struct KmerCounter {
    kmer_length: usize,
    canonical: bool,
    hash_table: HashMap<u64, u32>,
}
```

k-mer计数器结构。

**方法**:

##### `new`

```rust
pub fn new(k: usize, canonical: bool) -> Self
```

创建新的k-mer计数器。

##### `process_sequence`

```rust
pub fn process_sequence(&mut self, seq: &[u8]) -> Result<()>
```

处理单个DNA序列，提取并计数k-mers。

##### `get_filtered_kmers`

```rust
pub fn get_filtered_kmers(&self, filter: &Option<CountFilter>) -> Vec<(u64, u32)>
```

获取过滤后的k-mers。

#### `CountFilter`

```rust
pub struct CountFilter {
    pub min_count: Option<u32>,
    pub max_count: Option<u32>,
}
```

计数过滤器结构。

### `rustkmer::io`

输入输出处理模块，支持多种生物信息学文件格式。

#### `FastaProcessor`

```rust
pub struct FastaProcessor {
    kmer_length: usize,
    canonical: bool,
}
```

FASTA文件处理器。

#### `FastqProcessor`

```rust
pub struct FastqProcessor {
    kmer_length: usize,
    canonical: bool,
}
```

FASTQ文件处理器。

## 数据库格式

### RKDB格式详解

RKDB (RustKmer Database) 是专为高性能查询设计的二进制格式。

#### 文件结构

```
Offset 0: Header (42 bytes)
  0-3:   Magic "RKDB"
  4-5:   Version (u16)
  6:     K-mer size (u8)
  7-9:   Padding (3 bytes)
  10-17: Total k-mers (u64)
  18:    Flags (u8, bit 0: sorted, bit 1: canonical)
  19-25: Padding (7 bytes)
  26-33: Data offset (u64)
  34-41: Index offset (u64)

Offset 42+: K-mer entries
  Each entry: 12 bytes
    0-7:   K-mer (u64, little-endian)
    8-11:  Count (u32, little-endian)
```

#### 排序vs未排序

**排序数据库**:
- k-mers按编码值排序
- 支持二分搜索
- 无需预加载到内存
- 查询时间复杂度: O(log n)

**未排序数据库**:
- k-mers按处理顺序存储
- 需要线性搜索
- 建议预加载到内存
- 查询时间复杂度: O(n)

#### 示例代码

```rust
use rustkmer::database::{KmerDatabase, DatabaseHeader};
use std::fs::File;
use std::io::Write;
use byteorder::{LittleEndian, WriteBytesExt};

// 创建RKDB数据库
fn create_database(kmers: Vec<(u64, u32)>, output_path: &str) -> Result<()> {
    let mut file = File::create(output_path)?;

    // 写入header
    let header = DatabaseHeader {
        magic: *b"RKDB",
        version: 1,
        kmer_size: 21,
        total_kmers: kmers.len() as u64,
        sorted: true,
        data_offset: 42,
        index_offset: 0,
        canonical: true,
    };

    header.write_to(&mut file)?;

    // 写入k-mer数据
    for (kmer, count) in kmers {
        file.write_u64::<LittleEndian>(kmer)?;
        file.write_u32::<LittleEndian>(count)?;
    }

    Ok(())
}
```

## 错误处理

### 错误类型

```rust
#[derive(Debug, thiserror::Error)]
pub enum KmerError {
    #[error("Invalid k-mer sequence: {0}")]
    InvalidSequence(String),

    #[error("File read error: {0}")]
    FileReadError(String),

    #[error("File write error: {0}")]
    FileWriteError(String),

    #[error("Database format error: {0}")]
    DatabaseFormatError(String),

    #[error("Memory allocation error: {0}")]
    MemoryError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}
```

### 错误处理模式

```rust
use rustkmer::error::{KmerError, Result};

fn safe_kmer_operation() -> Result<()> {
    // 可能失败的操作
    let kmer = encode_kmer_bytes(b"ATGCN")?; // 会返回错误，因为包含'N'

    // 其他操作...
    Ok(())
}
```

## CLI接口

### 参数解析

RustKmer使用`clap`库进行命令行参数解析。

#### 主要命令结构

```rust
#[derive(Parser)]
pub struct Args {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    Count {
        #[arg(short, long)]
        kmer_size: usize,

        #[arg(short = 'm', long, value_parser = parse_memory)]
        memory: usize,

        #[arg(short, long)]
        threads: Option<usize>,

        #[arg(short, long)]
        output: String,

        #[arg(long, value_enum)]
        format: OutputFormat,

        #[arg(short = 'L', long)]
        lower_count: Option<u32>,

        #[arg(short = 'U', long)]
        upper_count: Option<u32>,

        #[arg(short, long)]
        canonical: bool,

        #[arg(short, long)]
        sort: bool,

        input_files: Vec<String>,
    },

    Query {
        database: String,

        #[arg(num_args = 0..)]
        kmers: Vec<String>,

        #[arg(short, long)]
        sequence: Option<String>,

        #[arg(short, long)]
        output: Option<String>,

        #[arg(short, long)]
        interactive: bool,

        #[arg(short, long)]
        load: bool,

        #[arg(short = 'L', long)]
        no_load: bool,
    },

    Dump {
        database: String,

        #[arg(short, long)]
        output: Option<String>,

        #[arg(long, value_enum)]
        format: DumpFormat,
    },

    Stats {
        database: String,
    },
}
```

#### 自定义解析器

```rust
fn parse_memory(arg: &str) -> Result<usize> {
    let arg = arg.to_uppercase();
    if arg.ends_with('G') {
        Ok(arg[..arg.len()-1].parse::<usize>()? * 1024 * 1024 * 1024)
    } else if arg.ends_with('M') {
        Ok(arg[..arg.len()-1].parse::<usize>()? * 1024 * 1024)
    } else if arg.ends_with('K') {
        Ok(arg[..arg.len()-1].parse::<usize>()? * 1024)
    } else {
        Ok(arg.parse::<usize>()?)
    }
}
```

## 示例代码

### 基本使用示例

```rust
use rustkmer::{KmerCounter, database::KmerDatabase};
use rustkmer::error::Result;

fn main() -> Result<()> {
    // 1. 创建k-mer计数器
    let mut counter = KmerCounter::new(21, true); // k=21, canonical模式

    // 2. 处理FASTA文件
    counter.process_fasta_file("genome.fasta")?;

    // 3. 创建数据库
    let kmers = counter.get_all_kmers();
    KmerDatabase::create_from_kmers(kmers, "output.rkdb")?;

    // 4. 查询数据库
    let db = KmerDatabase::new("output.rkdb")?;
    let count = db.query_kmer("ATGCGATGCTAGCGCTAGCTA")?;

    println!("K-mer count: {:?}", count);

    Ok(())
}
```

### 高级查询示例

```rust
use rustkmer::database::KmerDatabase;
use rustkmer::error::Result;

fn batch_query_example() -> Result<()> {
    let db = KmerDatabase::new("database.rkdb")?;

    let queries = vec![
        "ATGCGATGCTAGCGCTAGCTA".to_string(),
        "CGATCGATCGATCGATCGATCG".to_string(),
        "GCTAGCTAGCTAGCTAGCTAG".to_string(),
    ];

    // 批量查询
    let results = db.query_kmers(&queries)?;

    for (kmer, count) in results {
        println!("{}: {}", kmer, count);
    }

    Ok(())
}
```

### 自定义处理器示例

```rust
use rustkmer::{KmerCounter, kmer::encoding::encode_kmer_bytes};
use rustkmer::error::Result;

fn custom_sequence_processor() -> Result<()> {
    let mut counter = KmerCounter::new(31, false); // k=31, 非canonical

    // 手动处理序列
    let sequence = b"ATGCGATGCTAGCGCTAGCTAGCTAGCTAGCT";

    for i in 0..=(sequence.len() - 31) {
        let kmer_seq = &sequence[i..i+31];
        let encoded = encode_kmer_bytes(kmer_seq)?;

        counter.add_kmer(encoded);
    }

    println!("Processed {} k-mers", counter.total_kmers());

    Ok(())
}
```

### 错误处理示例

```rust
use rustkmer::error::{KmerError, Result};

fn robust_error_handling() -> Result<()> {
    match process_kmers() {
        Ok(_) => println!("Success!"),
        Err(KmerError::InvalidSequence(msg)) => {
            eprintln!("Invalid sequence found: {}", msg);
        },
        Err(KmerError::FileReadError(msg)) => {
            eprintln!("Failed to read file: {}", msg);
        },
        Err(err) => {
            eprintln!("Unexpected error: {}", err);
        }
    }

    Ok(())
}
```

### 性能优化示例

```rust
use rustkmer::database::KmerDatabase;
use rustkmer::error::Result;

fn performance_optimized_query() -> Result<()> {
    // 对于排序数据库，避免预加载
    let db = KmerDatabase::new("sorted_database.rkdb")?;

    // 批量查询比单个查询更高效
    let queries: Vec<String> = read_queries_from_file("queries.txt")?;
    let results = db.query_kmers(&queries)?;

    // 或者使用并行查询
    use rayon::prelude::*;
    let results: Vec<_> = queries
        .par_iter()
        .filter_map(|q| {
            db.query_kmer(q).ok().flatten()
                .map(|count| (q.clone(), count))
        })
        .collect();

    Ok(())
}
```

## 扩展开发

### 添加新的输出格式

```rust
use rustkmer::database::KmerDatabase;
use rustkmer::error::Result;

impl KmerDatabase {
    pub fn export_json(&self, output_path: &str) -> Result<()> {
        let kmers = self.dump_all_kmers()?;
        let json = serde_json::to_string_pretty(&kmers)?;

        std::fs::write(output_path, json)?;
        Ok(())
    }
}
```

### 实现新的统计功能

```rust
use rustkmer::database::KmerDatabase;
use rustkmer::error::Result;

impl KmerDatabase {
    pub fn calculate_statistics(&self) -> Result<DatabaseStats> {
        let kmers = self.dump_all_kmers()?;

        let counts: Vec<u32> = kmers.iter().map(|(_, c)| *c).collect();
        let total = counts.len();
        let sum: u64 = counts.iter().map(|c| *c as u64).sum();
        let max = counts.iter().max().unwrap_or(&0);
        let min = counts.iter().min().unwrap_or(&0);
        let avg = sum as f64 / total as f64;

        Ok(DatabaseStats {
            total_kmers: total,
            total_counts: sum,
            max_count: *max,
            min_count: *min,
            avg_count: avg,
        })
    }
}

pub struct DatabaseStats {
    pub total_kmers: usize,
    pub total_counts: u64,
    pub max_count: u32,
    pub min_count: u32,
    pub avg_count: f64,
}
```

---

这个API文档提供了RustKmer内部接口的详细说明，开发者可以基于这些信息进行扩展开发或集成到其他项目中。