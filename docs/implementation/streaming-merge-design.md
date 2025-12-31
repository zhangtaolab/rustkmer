# 流式 Merge 方案设计

## 背景
当前 `merge_databases` 将所有数据库完全加载到内存，无法处理大数据库。

## 目标
实现流式 merge，支持处理超出内存限制的大型数据库。

## 核心思路
1. **分块读取**：从每个输入数据库分批读取 k-mers（基于 chunk_size）
2. **临时排序**：每块读取后排序并写入临时文件
3. **外部合并**：使用堆排序算法合并所有有序的临时文件
4. **去重聚合**：合并时对相同 k-mer 的计数求和

## 数据库格式
- Header: 42 字节
- KmerEntry: 20 字节 (16 字节 kmer + 4 字节 count)

## 架构设计

### 1. DatabaseStreamIterator
分块迭代器，按 chunk_size 从数据库读取 k-mers

### 2. SortedChunkWriter
读取一块 k-mers，排序后写入临时文件

### 3. ExternalMerge
使用最小堆合并多个有序文件流

### 4. TempFileManager
管理临时文件的创建、合并和清理

## 实现步骤

### Step 1: 流式读取器
```rust
pub struct DatabaseStreamIterator {
    reader: BufReader<File>,
    remaining: u64,
    chunk_size: usize,
}

impl Iterator for DatabaseStreamIterator {
    type Item = Result<Vec<KmerEntry>>;
    // 每次读取 chunk_size 个 KmerEntry
}
```

### Step 2: 外部排序合并
```rust
pub struct ExternalMerger {
    temp_files: Vec<PathBuf>,
    chunk_size: usize,
    temp_dir: PathBuf,
}

impl ExternalMerger {
    pub fn merge_sorted_files(&self) -> Result<Vec<KmerEntry>>;
}
```

### Step 3: 集成到 merge_databases
根据内存限制自动选择策略：
- 小数据集 → InMemory
- 大数据集 → Streaming (ExternalMerge)

## 性能优化
1. 批量读写减少 I/O 次数
2. 使用 `BinaryHeap` 进行高效的多路合并
3. 临时文件使用缓冲写入
4. 支持并行处理不同数据库的分块读取

## 内存估算
- 每个 k-mer: 20 字节
- chunk_size = 1M → 20MB/块
- 堆合并: N 个临时文件各 1 个元素
- 总内存: chunk_size + N * 20 字节
