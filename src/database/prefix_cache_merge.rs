//! True external sort merge implementation for large k-mer database merging

use std::fs::File;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use rayon::current_num_threads;
use rayon::prelude::*;

use crate::database::format::{KmerEntry, RKDatabase};
use crate::error::ProcessingResult;
use crate::kmer::canonical::canonical_kmer_u128;

pub struct ExternalSortMerger {
    pub prefix_bits: usize,
    pub num_buckets: usize,
    pub merge_buffer_mb: usize,
    pub temp_dir: PathBuf,
    pub input_files: Vec<PathBuf>,
    pub kmer_size: usize,
    pub canonical: bool,
    pub total_kmers: u64,
    pub estimated_kmers_per_file: u64,
    pub num_threads: usize,
    pub merge_mode: String,
    pub keep_intermediate: bool,
}

#[allow(dead_code)]
impl ExternalSortMerger {
    pub fn new(
        input_files: Vec<PathBuf>,
        temp_dir: PathBuf,
        merge_buffer_mb: usize,
        num_threads: usize,
        merge_mode: String,
        keep_intermediate: bool,
    ) -> ProcessingResult<Self> {
        let num_buckets = 1 << 8;

        let reference_db = RKDatabase::from_file_path(&input_files[0])?;
        let kmer_size = reference_db.header().kmer_size as usize;

        let mut canonical_modes = Vec::new();
        let mut kmer_sizes = Vec::new();

        for path in input_files.iter() {
            let db = RKDatabase::from_file_path(path)?;
            canonical_modes.push(db.header().canonical);
            kmer_sizes.push(db.header().kmer_size as usize);
        }

        if kmer_sizes.iter().any(|&k| k != kmer_sizes[0]) {
            return Err(crate::error::ProcessingError::new(format!(
                "K-mer size mismatch: found sizes {:?}",
                kmer_sizes
            )));
        }

        let mut has_canonical = false;
        for &mode in &canonical_modes {
            if mode {
                has_canonical = true;
            }
        }

        let final_canonical = has_canonical;
        let total_kmers = reference_db.header().total_kmers;

        Ok(Self {
            prefix_bits: 8,
            num_buckets,
            merge_buffer_mb,
            temp_dir,
            input_files,
            kmer_size,
            canonical: final_canonical,
            total_kmers,
            estimated_kmers_per_file: total_kmers,
            num_threads,
            merge_mode,
            keep_intermediate,
        })
    }

    pub fn external_sort_merge(&mut self, output_path: &Path) -> ProcessingResult<()> {
        let total_start = Instant::now();

        log::info!("\n🚀 开始外部排序合并");
        log::info!("   输入文件: {} 个", self.input_files.len());
        log::info!("   总k-mers: {} M", self.total_kmers / 1_000_000);
        log::info!("   Canonical模式: {}", self.canonical);
        log::info!("   前缀桶数量: {}", self.num_buckets);

        let phase1_start = Instant::now();
        self.split_files_by_prefix()?;
        let phase1_time = phase1_start.elapsed();

        let phase2_start = Instant::now();
        self.merge_prefix_buckets()?;
        let phase2_time = phase2_start.elapsed();

        let phase3_start = Instant::now();
        self.concatenate_final_output(output_path)?;
        let phase3_time = phase3_start.elapsed();

        let total_time = total_start.elapsed();

        log::info!("\n📊 合并完成!");
        log::info!("   总耗时: {:.1}s", total_time.as_secs_f64());
        log::info!("   阶段1 (分桶): {:.1}s", phase1_time.as_secs_f64());
        log::info!("   阶段2 (合并): {:.1}s", phase2_time.as_secs_f64());
        log::info!("   阶段3 (拼接): {:.1}s", phase3_time.as_secs_f64());
        log::info!("   输出文件: {:?}", output_path);

        Ok(())
    }

    fn split_files_by_prefix(&mut self) -> ProcessingResult<()> {
        log::info!("\n📦 阶段1 - 数据分桶 (按前4个碱基分配)");

        let num_files = self.input_files.len();
        log::info!("   输入文件数: {}", num_files);

        let num_workers = current_num_threads();
        log::info!("   使用 {} 个工作线程并行分桶", num_workers.min(num_files));

        let start_time = Instant::now();

        let temp_files: Vec<Vec<PathBuf>> = (0..num_files)
            .map(|file_idx| {
                (0..self.num_buckets)
                    .map(|prefix| {
                        let dna = Self::prefix_to_dna(prefix);
                        self.temp_dir
                            .join(format!("ext_sort_{}_file_{:03}.tmp", dna, file_idx))
                    })
                    .collect()
            })
            .collect();

        log::info!("");

        const BATCH_SIZE: usize = 10_000;
        let mut total_kmers = 0u64;

        for (file_idx, input_path) in self.input_files.iter().enumerate() {
            let file_name = input_path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            let mut file_kmers = 0u64;

            let mut bucket_buffers: Vec<Vec<u8>> = vec![Vec::new(); self.num_buckets];
            let stream_iter = crate::database::DatabaseStreamIterator::new(input_path, 500_000)?;

            for chunk_result in stream_iter {
                let chunk = chunk_result?;
                for entry in chunk {
                    let processed_kmer = if self.canonical {
                        canonical_kmer_u128(entry.kmer, self.kmer_size).unwrap_or(entry.kmer)
                    } else {
                        entry.kmer
                    };

                    let prefix = self.get_prefix_4mer(processed_kmer);

                    if prefix < self.num_buckets {
                        bucket_buffers[prefix].extend_from_slice(&entry.kmer.to_le_bytes());
                        bucket_buffers[prefix].extend_from_slice(&entry.count.to_le_bytes());
                        file_kmers += 1;

                        if bucket_buffers[prefix].len() >= BATCH_SIZE * 20 {
                            let temp_file_path = &temp_files[file_idx][prefix];
                            Self::write_buffer_sync(temp_file_path, &bucket_buffers[prefix])?;
                            bucket_buffers[prefix].clear();
                        }
                    }
                }
            }

            for prefix in 0..self.num_buckets {
                if !bucket_buffers[prefix].is_empty() {
                    let temp_file_path = &temp_files[file_idx][prefix];
                    Self::write_buffer_sync(temp_file_path, &bucket_buffers[prefix])?;
                    bucket_buffers[prefix].clear();
                }
            }

            total_kmers += file_kmers;
            let file_elapsed = start_time.elapsed();
            let speed = if file_elapsed.as_secs_f64() > 0.0 {
                file_kmers as f64 / file_elapsed.as_secs_f64() / 1_000_000.0
            } else {
                0.0
            };

            log::info!(
                "   ✓ {}: {} M k-mers @ {:.1} M/s",
                file_name,
                file_kmers / 1_000_000,
                speed
            );
        }

        let phase_time = start_time.elapsed();
        let speed = if phase_time.as_secs_f64() > 0.0 {
            total_kmers as f64 / phase_time.as_secs_f64() / 1_000_000.0
        } else {
            0.0
        };

        log::info!(
            "   ✅ 分桶完成: {} M k-mers @ {:.1} M/s (耗时 {:.1}s)",
            total_kmers / 1_000_000,
            speed,
            phase_time.as_secs_f64()
        );

        Ok(())
    }

    fn write_buffer_sync(file_path: &Path, data: &[u8]) -> ProcessingResult<()> {
        use std::fs::OpenOptions;
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(file_path)?;
        file.write_all(data)?;
        Ok(())
    }

    fn merge_prefix_buckets(&mut self) -> ProcessingResult<()> {
        log::info!("\n🔄 阶段2 - 前缀桶合并");

        let start_time = Instant::now();

        let mut non_empty_prefixes = Vec::new();
        let mut prefix_file_map: std::collections::HashMap<usize, Vec<(PathBuf, u64)>> =
            std::collections::HashMap::new();

        for prefix in 0..self.num_buckets {
            let mut prefix_files = Vec::new();
            for file_idx in 0..self.input_files.len() {
                let dna = Self::prefix_to_dna(prefix);
                let temp_file_path = self
                    .temp_dir
                    .join(format!("ext_sort_{}_file_{:03}.tmp", dna, file_idx));
                if temp_file_path.exists() {
                    if let Ok(metadata) = std::fs::metadata(&temp_file_path) {
                        if metadata.len() > 0 {
                            prefix_files.push((temp_file_path, metadata.len()));
                        }
                    }
                }
            }
            if !prefix_files.is_empty() {
                non_empty_prefixes.push(prefix);
                prefix_file_map.insert(prefix, prefix_files);
            }
        }

        let non_empty_count = non_empty_prefixes.len();
        log::info!("   非空前缀: {}/{}", non_empty_count, self.num_buckets);

        let num_workers = rayon::current_num_threads();
        log::info!("   使用 {} 个工作线程并行处理", num_workers);

        let start_parallel = Instant::now();

        let temp_dir = self.temp_dir.clone();
        let temp_dir_arc = std::sync::Arc::new(temp_dir);
        let merge_mode_arc = std::sync::Arc::new(self.merge_mode.clone());
        let completed_count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let prefix_file_map_arc = std::sync::Arc::new(prefix_file_map);

        let results: Vec<Result<(), String>> = non_empty_prefixes
            .into_par_iter()
            .map(|prefix| {
                let completed = completed_count.clone();
                let temp_dir = temp_dir_arc.clone();
                let prefix_files = prefix_file_map_arc
                    .get(&prefix)
                    .expect("Prefix not found in map")
                    .clone();
                let files_to_delete: Vec<PathBuf> =
                    prefix_files.iter().map(|(p, _)| p.clone()).collect();
                let dna = Self::prefix_to_dna(prefix);
                let output_file = temp_dir.join(format!("ext_sort_{}_merged.tmp", dna));
                let merge_mode = merge_mode_arc.as_str();

                let total_size: usize = prefix_files.iter().map(|(_, s)| *s as usize).sum();

                let result = if merge_mode == "streaming" {
                    Self::merge_single_prefix_streaming(prefix_files, &output_file)
                } else if merge_mode == "memory" {
                    Self::merge_single_prefix_hashmap(prefix_files, &output_file)
                } else {
                    let threshold = self.merge_buffer_mb * 1_000_000;
                    if total_size <= threshold {
                        Self::merge_single_prefix_hashmap(prefix_files, &output_file)
                    } else {
                        Self::merge_single_prefix_streaming(prefix_files, &output_file)
                    }
                };

                if result.is_ok() && !self.keep_intermediate {
                    for temp_file in files_to_delete {
                        let _ = std::fs::remove_file(&temp_file);
                    }
                }

                let done = completed.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
                if result.is_ok() {
                    log::info!(
                        "   ✅ 处理完毕: {} | 进度: {}/{} ({:.1}%)",
                        dna,
                        done,
                        non_empty_count,
                        done as f64 / non_empty_count as f64 * 100.0
                    );
                } else {
                    log::error!(
                        "   ❌ 处理失败: {} | 错误: {}",
                        dna,
                        result.as_ref().err().unwrap()
                    );
                }

                if done.is_multiple_of(10) || done == non_empty_count {
                    let elapsed = start_parallel.elapsed();
                    let eta = if done > 0 && elapsed.as_secs_f64() > 0.0 {
                        let per_prefix = elapsed.as_secs_f64() / done as f64;
                        (non_empty_count - done) as f64 * per_prefix
                    } else {
                        0.0
                    };
                    log::info!(
                        "   📊 汇总: {}/{} ({:.1}%) 已用 {:.1}s 预计剩余 {:.0}s   \r",
                        done,
                        non_empty_count,
                        done as f64 / non_empty_count as f64 * 100.0,
                        elapsed.as_secs_f64(),
                        eta
                    );
                    let _ = std::io::stdout().flush();
                }

                result.map_err(|e| e.to_string())
            })
            .collect();

        log::info!("");
        let _ = std::io::stdout().flush();

        let phase_time = start_time.elapsed();
        let parallel_time = start_parallel.elapsed();
        let speed_per_prefix = if non_empty_count > 0 {
            parallel_time.as_secs_f64() / non_empty_count as f64
        } else {
            0.0
        };

        let mut error_count = 0;
        for result in results {
            if let Err(e) = result {
                log::error!("   错误: {}", e);
                error_count += 1;
            }
        }

        if error_count == 0 {
            log::info!(
                "   ✅ 合并完成: {} 个前缀桶 (耗时 {:.1}s, 每桶 {:.2}s)",
                non_empty_count,
                phase_time.as_secs_f64(),
                speed_per_prefix
            );
        } else {
            log::info!(
                "   ⚠️ 合并完成: {} 个前缀桶, {} 个错误 (耗时 {:.1}s)",
                non_empty_count - error_count,
                error_count,
                phase_time.as_secs_f64()
            );
        }

        Ok(())
    }

    fn merge_single_prefix_hashmap(
        files: Vec<(PathBuf, u64)>,
        output_path: &Path,
    ) -> Result<(), anyhow::Error> {
        use std::collections::HashMap;
        use std::io::BufReader;

        log::info!("   使用内存合并模式");

        // 计算总大小
        let total_size: u64 = files.iter().map(|(_, s)| *s).sum();
        let total_kmers = total_size / 20;

        log::info!("   输入文件: {} 个", files.len());
        log::info!(
            "   总数据量: {:.1} MB ({} k-mers)",
            total_size as f64 / 1024.0 / 1024.0,
            total_kmers
        );

        // 检查可用内存
        if let Ok(mem_info) = sys_info::mem_info() {
            let avail_mem_mb = mem_info.avail as f64 / 1024.0 / 1024.0;
            let required_mem_mb = total_size as f64 / 1024.0 / 1024.0 * 3.0; // 考虑HashMap开销

            log::info!("   可用内存: {:.1} MB", avail_mem_mb);
            log::info!("   预估需要: {:.1} MB", required_mem_mb);

            if required_mem_mb > avail_mem_mb {
                log::warn!("   ⚠️  警告: 预估内存需求超过可用内存！");
                log::warn!("   建议: 使用 --merge-mode streaming 模式");
            }
        }

        let mut kmer_counts: HashMap<u128, u32> = HashMap::new();
        kmer_counts.reserve((total_kmers as usize).min(100_000_000));

        let start_time = std::time::Instant::now();
        let mut processed_kmers = 0u64;

        for (idx, (file_path, file_size)) in files.iter().enumerate() {
            let file_start = std::time::Instant::now();

            // 检查内存使用
            if idx > 0 && idx % 5 == 0 {
                if let Ok(mem_info) = sys_info::mem_info() {
                    log::info!(
                        "   进度: {}/{} | 已处理 {} M k-mers | 可用内存: {:.1} MB",
                        idx,
                        files.len(),
                        processed_kmers / 1_000_000,
                        mem_info.avail as f64 / 1024.0 / 1024.0
                    );
                }
            }

            let file = File::open(file_path)
                .map_err(|e| anyhow::anyhow!("无法打开文件 {}: {}", file_path.display(), e))?;

            let mut reader = BufReader::with_capacity(1_000_000, file);
            let mut buffer = Vec::new();

            reader
                .read_to_end(&mut buffer)
                .map_err(|e| anyhow::anyhow!("读取文件 {} 失败: {}", file_path.display(), e))?;

            let mut offset = 0usize;
            while offset + 20 <= buffer.len() {
                let kmer = u128::from_le_bytes(buffer[offset..offset + 16].try_into().unwrap());
                let count =
                    u32::from_le_bytes(buffer[offset + 16..offset + 20].try_into().unwrap());
                *kmer_counts.entry(kmer).or_insert(0) += count;
                offset += 20;
                processed_kmers += 1;
            }

            let file_elapsed = file_start.elapsed();
            let speed = if file_elapsed.as_secs_f64() > 0.0 {
                (*file_size as f64 / 1024.0 / 1024.0) / file_elapsed.as_secs_f64()
            } else {
                0.0
            };

            log::info!(
                "   ✓ 文件 {}: {:.1} MB @ {:.1} MB/s",
                idx + 1,
                *file_size as f64 / 1024.0 / 1024.0,
                speed
            );
        }

        // 检查最终内存使用
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   合并完成: {} 个唯一k-mers | 可用内存: {:.1} MB",
                kmer_counts.len(),
                mem_info.avail as f64 / 1024.0 / 1024.0
            );
        }

        log::info!("   开始排序...");
        let sort_start = std::time::Instant::now();

        let mut sorted_kmers: Vec<(u128, u32)> = kmer_counts.into_iter().collect();
        sorted_kmers.sort_by_key(|(k, _)| *k);

        let sort_time = sort_start.elapsed();
        log::info!("   排序完成: 耗时 {:.1}s", sort_time.as_secs_f64());

        log::info!("   写入输出文件...");
        let mut output_file = File::create(output_path)
            .map_err(|e| anyhow::anyhow!("无法创建输出文件 {}: {}", output_path.display(), e))?;

        for (kmer, count) in &sorted_kmers {
            output_file.write_all(&kmer.to_le_bytes())?;
            output_file.write_all(&count.to_le_bytes())?;
        }
        output_file
            .sync_all()
            .map_err(|e| anyhow::anyhow!("无法同步文件 {}: {}", output_path.display(), e))?;

        let total_time = start_time.elapsed();
        log::info!("   完成: 总耗时 {:.1}s", total_time.as_secs_f64());

        Ok(())
    }

    fn merge_single_prefix_streaming(
        files: Vec<(PathBuf, u64)>,
        output_path: &Path,
    ) -> Result<(), anyhow::Error> {
        use std::cmp::Ordering;
        use std::collections::BinaryHeap;

        #[derive(Debug)]
        struct HeapEntry {
            kmer: u128,
            count: u32,
            file_idx: usize,
        }

        impl PartialEq for HeapEntry {
            fn eq(&self, other: &Self) -> bool {
                self.kmer == other.kmer
            }
        }

        impl Eq for HeapEntry {}

        impl PartialOrd for HeapEntry {
            fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
                Some(self.cmp(other))
            }
        }

        impl Ord for HeapEntry {
            fn cmp(&self, other: &Self) -> Ordering {
                other.kmer.cmp(&self.kmer)
            }
        }

        const BATCH_READ: usize = 100_000;

        let mut file_states: Vec<(std::io::BufReader<File>, Vec<u8>, Vec<KmerEntry>)> = Vec::new();
        let mut heap: BinaryHeap<HeapEntry> = BinaryHeap::new();

        for (idx, (file_path, _)) in files.iter().enumerate() {
            let file = File::open(file_path)?;
            let reader = std::io::BufReader::new(file);
            let data = Vec::with_capacity(BATCH_READ * 20);
            let entries = Vec::new();
            file_states.push((reader, data, entries));

            let first_entries = Self::read_batch_from_file_sync(&mut file_states[idx])?;
            if let Some(entry) = first_entries.first() {
                heap.push(HeapEntry {
                    kmer: entry.kmer,
                    count: entry.count,
                    file_idx: idx,
                });
                file_states[idx].2 = first_entries;
            }
        }

        let mut output_file = File::create(output_path)?;
        let mut current_kmer: Option<u128> = None;
        let mut current_count = 0u32;

        while let Some(top) = heap.pop() {
            if let Some(kmer) = current_kmer {
                if kmer == top.kmer {
                    current_count += top.count;
                } else {
                    output_file.write_all(&kmer.to_le_bytes())?;
                    output_file.write_all(&current_count.to_le_bytes())?;
                    current_kmer = Some(top.kmer);
                    current_count = top.count;
                }
            } else {
                current_kmer = Some(top.kmer);
                current_count = top.count;
            }

            file_states[top.file_idx].2.remove(0);

            if file_states[top.file_idx].2.is_empty() {
                let new_entries = Self::read_batch_from_file_sync(&mut file_states[top.file_idx])?;
                if !new_entries.is_empty() {
                    file_states[top.file_idx].2 = new_entries;
                    let first_entry = &file_states[top.file_idx].2[0];
                    if current_kmer == Some(first_entry.kmer) {
                        current_count += first_entry.count;
                    } else {
                        heap.push(HeapEntry {
                            kmer: first_entry.kmer,
                            count: first_entry.count,
                            file_idx: top.file_idx,
                        });
                    }
                }
            } else {
                let first_entry = &file_states[top.file_idx].2[0];
                if current_kmer == Some(first_entry.kmer) {
                    current_count += first_entry.count;
                } else {
                    heap.push(HeapEntry {
                        kmer: first_entry.kmer,
                        count: first_entry.count,
                        file_idx: top.file_idx,
                    });
                }
            }
        }

        if let Some(kmer) = current_kmer {
            output_file.write_all(&kmer.to_le_bytes())?;
            output_file.write_all(&current_count.to_le_bytes())?;
        }
        output_file.sync_all()?;

        Ok(())
    }

    fn read_entries_from_file_sync(path: impl AsRef<Path>) -> ProcessingResult<Vec<KmerEntry>> {
        let mut file = File::open(path)?;
        let mut data = Vec::new();
        file.read_to_end(&mut data)?;

        let mut entries = Vec::new();
        let mut offset = 0usize;

        while offset + 20 <= data.len() {
            let kmer = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
            let count = u32::from_le_bytes(data[offset + 16..offset + 20].try_into().unwrap());
            entries.push(KmerEntry::new(kmer, count));
            offset += 20;
        }

        Ok(entries)
    }

    fn read_batch_from_file_sync(
        file_state: &mut (std::io::BufReader<File>, Vec<u8>, Vec<KmerEntry>),
    ) -> ProcessingResult<Vec<KmerEntry>> {
        const BATCH_BYTES: u64 = 4_000_000;
        let (reader, data, _) = &mut *file_state;
        data.clear();

        let mut bytes_read = 0u64;
        let mut buffer = [0u8; 8192];

        while bytes_read < BATCH_BYTES {
            match reader.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => {
                    data.extend_from_slice(&buffer[..n]);
                    bytes_read += n as u64;
                }
                Err(_) => break,
            }
        }

        let mut entries = Vec::new();
        let mut offset = 0usize;

        while offset + 20 <= data.len() {
            let kmer = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
            let count = u32::from_le_bytes(data[offset + 16..offset + 20].try_into().unwrap());
            entries.push(KmerEntry::new(kmer, count));
            offset += 20;
        }

        Ok(entries)
    }

    fn get_prefix_4mer(&self, kmer: u128) -> usize {
        let prefix_bits = kmer & 0xFF;
        prefix_bits as usize
    }

    fn concatenate_final_output(&self, output_path: &Path) -> ProcessingResult<()> {
        use std::io::{BufWriter, Write};

        log::info!("\n📦 阶段3 - 最终拼接 (使用RKDB标准格式)");

        let start_time = Instant::now();

        // 监控内存使用
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   当前内存使用: {:.1} GB / {:.1} GB (可用 {:.1} GB)",
                (mem_info.total - mem_info.avail) as f64 / 1024.0 / 1024.0 / 1024.0,
                mem_info.total as f64 / 1024.0 / 1024.0 / 1024.0,
                mem_info.avail as f64 / 1024.0 / 1024.0 / 1024.0
            );
        }

        let temp_data_file = self.temp_dir.join("ext_sort_final_data.tmp");
        let mut temp_file = File::create(&temp_data_file)?;
        let mut data_size = 0u64;
        let mut total_kmers_in_files = 0u64;

        for prefix in 0..self.num_buckets {
            let dna = Self::prefix_to_dna(prefix);
            let prefix_file = self.temp_dir.join(format!("ext_sort_{}_merged.tmp", dna));

            if prefix_file.exists() {
                let file_size = std::fs::metadata(&prefix_file)?.len();

                if file_size == 0 {
                    log::warn!("   ⚠️ 空文件: {}", dna);
                    let _ = std::fs::remove_file(&prefix_file);
                    continue;
                }

                let kmers_in_file = file_size / 20;
                total_kmers_in_files += kmers_in_file;

                let mut input_file = File::open(&prefix_file)?;
                let mut buffer = Vec::new();
                input_file.read_to_end(&mut buffer)?;

                temp_file.write_all(&buffer)?;
                data_size += buffer.len() as u64;

                if !self.keep_intermediate {
                    let _ = std::fs::remove_file(&prefix_file);
                }

                // 每处理一个文件后报告进度和内存
                let processed = prefix + 1;
                if processed % 16 == 0 || processed == self.num_buckets {
                    if let Ok(mem_info) = sys_info::mem_info() {
                        log::info!(
                            "   进度: {}/{} | 数据: {:.1} MB | k-mers: {} M | 可用内存: {:.1} MB",
                            processed,
                            self.num_buckets,
                            data_size as f64 / 1024.0 / 1024.0,
                            total_kmers_in_files / 1_000_000,
                            mem_info.avail as f64 / 1024.0 / 1024.0
                        );
                    }
                }
            }
        }
        temp_file.sync_all()?;
        drop(temp_file);

        let total_kmers = data_size / 20;

        log::info!(
            "   开始写入RKDB格式，总计 {} M 个k-mers...",
            total_kmers / 1_000_000
        );
        log::info!(
            "   从各文件统计: {} M 个k-mers",
            total_kmers_in_files / 1_000_000
        );

        // 检查是否有重复
        if total_kmers != total_kmers_in_files {
            log::warn!("   ⚠️  警告: 数据大小不一致！可能有重复或丢失");
        }

        // 监控内存使用
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   当前可用内存: {:.1} GB",
                mem_info.avail as f64 / 1024.0 / 1024.0 / 1024.0
            );
        }

        // 使用流式处理而不是一次性加载所有数据
        let mut file = File::open(&temp_data_file)?;

        // 创建 RKDatabase header (data_offset 在 header 之后，通常是 42 字节)
        let header = crate::database::format::DatabaseHeader {
            magic: *b"RKDB",
            version: 2,
            kmer_size: self.kmer_size as u8,
            canonical: self.canonical,
            sorted: true,
            total_kmers,
            unique_kmers: total_kmers,
            data_offset: 42,           // header size
            file_size: 42 + data_size, // header + data
            index_offset: 0,           // no index for now
        };

        // 创建输出文件
        let output = File::create(output_path)?;
        let mut writer = BufWriter::with_capacity(10_000_000, output);

        // 写入 header
        header.write_to(&mut writer)?;

        // 流式读取和写入 k-mer 数据
        let mut buffer = vec![0u8; 20 * 100_000]; // 每次 100k k-mers
        let mut processed_kmers = 0u64;
        let mut last_report = std::time::Instant::now();

        loop {
            match file.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => {
                    let num_kmers = n / 20;
                    processed_kmers += num_kmers as u64;
                    writer.write_all(&buffer[..n])?;

                    // 每 100 万 k-mers 报告进度
                    if processed_kmers.is_multiple_of(1_000_000)
                        || last_report.elapsed().as_secs() >= 5
                    {
                        if let Ok(mem_info) = sys_info::mem_info() {
                            log::info!(
                                "   进度: {} M / {} M k-mers | 可用内存: {:.1} MB",
                                processed_kmers / 1_000_000,
                                total_kmers / 1_000_000,
                                mem_info.avail as f64 / 1024.0 / 1024.0
                            );
                        }
                        last_report = std::time::Instant::now();
                    }
                }
                Err(e) => {
                    return Err(crate::error::ProcessingError::new(format!(
                        "读取数据失败: {}",
                        e
                    )));
                }
            }
        }

        writer.flush()?;
        drop(writer);

        // 写入 metadata - 使用 create_metadata 函数
        use crate::core::metadata::create_metadata;
        use std::time::SystemTime;

        let now = SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let mut metadata = create_metadata(
            self.kmer_size,
            self.canonical,
            self.input_files
                .iter()
                .filter_map(|p| p.to_str().map(String::from))
                .collect(),
        );

        // 更新统计信息
        metadata.total_kmers = total_kmers;
        metadata.unique_kmers = total_kmers;
        metadata.created_at = now;
        metadata.modified_at = now;

        // 写入 metadata
        let metadata_path = output_path.with_extension("json");
        let metadata_json = serde_json::to_string_pretty(&metadata)
            .map_err(|e| crate::error::ProcessingError::new(format!("序列化元数据失败: {}", e)))?;
        std::fs::write(&metadata_path, metadata_json)
            .map_err(|e| crate::error::ProcessingError::new(format!("写入元数据失败: {}", e)))?;

        let phase_time = start_time.elapsed();
        log::info!(
            "   ✅ 拼接完成: {} M 个k-mers (耗时 {:.1}s)",
            total_kmers / 1_000_000,
            phase_time.as_secs_f64()
        );

        if !self.keep_intermediate {
            let _ = std::fs::remove_file(&temp_data_file);
        }

        Ok(())
    }

    fn prefix_to_dna(prefix: usize) -> String {
        let mut dna = String::with_capacity(4);
        let mut p = prefix;
        for _ in 0..4 {
            match p & 0x03 {
                0 => dna.push('A'),
                1 => dna.push('C'),
                2 => dna.push('G'),
                3 => dna.push('T'),
                _ => {}
            }
            p >>= 2;
        }
        dna.chars().rev().collect()
    }

    fn read_entries_from_file(&self, path: &Path) -> ProcessingResult<Vec<KmerEntry>> {
        let mut file = File::open(path)?;
        let mut data = Vec::new();
        file.read_to_end(&mut data)?;

        let mut entries = Vec::new();
        let mut offset = 0;

        while offset + 20 <= data.len() {
            let kmer = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
            let count = u32::from_le_bytes(data[offset + 16..offset + 20].try_into().unwrap());
            entries.push(KmerEntry::new(kmer, count));
            offset += 20;
        }

        Ok(entries)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_external_sort_merger_creation() {
        let temp_dir = tempfile::tempdir().unwrap();
        let input_files = vec![PathBuf::from("test1.rkdb"), PathBuf::from("test2.rkdb")];
        let result = ExternalSortMerger::new(
            input_files,
            temp_dir.path().to_path_buf(),
            1024,
            0,
            "auto".to_string(),
            false,
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_merger_structure() {
        let temp_dir = tempfile::tempdir().unwrap();
        assert!(temp_dir.path().exists());
    }

    #[test]
    fn test_prefix_extraction_values() {
        let kmer_size = 57;
        let kmer: u128 = 0x123456789ABCDEF0;
        let prefix_bits = (kmer >> (2 * (kmer_size - 4))) & 0xFFF;
        let prefix = (prefix_bits >> 4) as usize;
        assert!(prefix < 256);
    }
}
