//! Streaming merge for large database operations
//!
//! This module implements external sort-based merge for databases
//! that are too large to fit in memory.

use crate::database::format::{DatabaseHeader, KmerEntry, DATABASE_MAGIC, DATABASE_VERSION};
use crate::error::ProcessingError;
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::fs::File;
use std::io::{BufReader, BufWriter, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Streaming iterator for reading database entries in chunks
pub struct DatabaseStreamIterator {
    reader: BufReader<File>,
    remaining: u64,
    chunk_size: usize,
    current_pos: u64,
}

impl DatabaseStreamIterator {
    pub fn new(path: &Path, chunk_size: usize) -> Result<Self, ProcessingError> {
        let file = File::open(path).map_err(|e| {
            ProcessingError::io_error(format!(
                "Failed to open database '{}': {}",
                path.display(),
                e
            ))
        })?;

        let mut reader = BufReader::new(file);

        let header = DatabaseHeader::read_from(&mut reader).map_err(|e| {
            ProcessingError::io_error(format!("Failed to read database header: {}", e))
        })?;

        let actual_data_offset = if (40..=1000).contains(&header.data_offset) {
            header.data_offset
        } else {
            42
        };

        reader
            .seek(SeekFrom::Start(actual_data_offset))
            .map_err(|e| {
                ProcessingError::io_error(format!("Failed to seek to data section: {}", e))
            })?;

        Ok(Self {
            reader,
            remaining: header.total_kmers,
            chunk_size,
            current_pos: 0,
        })
    }

    pub fn header(&self) -> DatabaseHeader {
        DatabaseHeader {
            magic: *DATABASE_MAGIC,
            version: DATABASE_VERSION,
            kmer_size: 0,
            total_kmers: self.remaining,
            sorted: false,
            data_offset: 0,
            index_offset: 0,
            canonical: false,
            unique_kmers: self.remaining,
            file_size: 0,
        }
    }
}

impl Iterator for DatabaseStreamIterator {
    type Item = Result<Vec<KmerEntry>, ProcessingError>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.remaining == 0 {
            return None;
        }

        let to_read = std::cmp::min(self.chunk_size, self.remaining as usize);
        let mut chunk = Vec::with_capacity(to_read);

        for _ in 0..to_read {
            match KmerEntry::read_from(&mut self.reader) {
                Ok(entry) => chunk.push(entry),
                Err(e) => {
                    return Some(Err(ProcessingError::io_error(format!(
                        "Failed to read k-mer entry: {}",
                        e
                    ))))
                }
            }
        }

        self.remaining -= to_read as u64;
        self.current_pos += to_read as u64;

        Some(Ok(chunk))
    }
}

/// Temporary file manager for external merge operations
pub struct TempFileManager {
    temp_dir: PathBuf,
    files: Vec<PathBuf>,
    prefix: String,
    auto_cleanup: bool,
}

impl TempFileManager {
    pub fn new(temp_dir: PathBuf, operation: &str) -> Self {
        let prefix = format!("rustkmer_{}_{}", operation, std::process::id());
        Self {
            temp_dir,
            files: Vec::new(),
            prefix,
            auto_cleanup: true,
        }
    }

    pub fn with_cleanup(mut self, auto_cleanup: bool) -> Self {
        self.auto_cleanup = auto_cleanup;
        self
    }

    pub fn create_temp_file(&mut self) -> Result<(PathBuf, BufWriter<File>), ProcessingError> {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_micros();

        let file_name = format!("{}_{}.chunk", self.prefix, timestamp);
        let file_path = self.temp_dir.join(&file_name);

        let file = File::create(&file_path).map_err(|e| {
            ProcessingError::io_error(format!(
                "Failed to create temp file '{}': {}",
                file_path.display(),
                e
            ))
        })?;

        let writer = BufWriter::new(file);
        self.files.push(file_path.clone());

        Ok((file_path, writer))
    }

    pub fn cleanup(&self) {
        for file_path in &self.files {
            let _ = std::fs::remove_file(file_path);
        }
    }

    pub fn take_files(&mut self) -> Vec<PathBuf> {
        std::mem::take(&mut self.files)
    }
}

impl Drop for TempFileManager {
    fn drop(&mut self) {
        if self.auto_cleanup {
            self.cleanup();
        }
    }
}

/// External merge using sorted run-based approach
pub struct ExternalMerger {
    chunk_size: usize,
    temp_dir: PathBuf,
    temp_files: Vec<PathBuf>,
    merge_stats: StreamingMergeStats,
}

#[derive(Debug, Clone, Default)]
pub struct StreamingMergeStats {
    pub total_kmers_read: u64,
    pub unique_kmers: u64,
    pub chunks_created: usize,
    pub read_time: std::time::Duration,
    pub sort_time: std::time::Duration,
    pub merge_time: std::time::Duration,
    pub write_time: std::time::Duration,
}

/// Represents a single item from a merge file
#[derive(Debug, Clone)]
pub struct MergeItem {
    kmer: u128,
    count: u32,
    file_index: usize,
}

impl PartialEq for MergeItem {
    fn eq(&self, other: &Self) -> bool {
        self.kmer == other.kmer
    }
}

impl Eq for MergeItem {}

impl PartialOrd for MergeItem {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for MergeItem {
    fn cmp(&self, other: &Self) -> Ordering {
        other.kmer.cmp(&self.kmer)
    }
}

impl ExternalMerger {
    pub fn new(chunk_size: usize, temp_dir: PathBuf) -> Self {
        Self {
            chunk_size,
            temp_dir,
            temp_files: Vec::new(),
            merge_stats: StreamingMergeStats::default(),
        }
    }

    /// Read and sort a single database into sorted chunks
    pub fn sort_database(&mut self, db_path: &Path) -> Result<(), ProcessingError> {
        let start_time = Instant::now();

        let mut temp_manager = TempFileManager::new(self.temp_dir.clone(), "sort");
        let stream_iter = DatabaseStreamIterator::new(db_path, self.chunk_size)?;

        let mut total_read = 0u64;

        for chunk_result in stream_iter {
            let mut chunk = chunk_result?;

            total_read += chunk.len() as u64;

            let sort_start = Instant::now();
            chunk.sort_by_key(|entry| entry.kmer);
            self.merge_stats.sort_time += sort_start.elapsed();

            let (_file_path, mut writer) = temp_manager.create_temp_file()?;

            let write_start = Instant::now();
            for entry in &chunk {
                entry.write_to(&mut writer).map_err(|e| {
                    ProcessingError::io_error(format!("Failed to write chunk: {}", e))
                })?;
            }
            writer
                .flush()
                .map_err(|e| ProcessingError::io_error(format!("Failed to flush chunk: {}", e)))?;
            self.merge_stats.write_time += write_start.elapsed();

            self.merge_stats.chunks_created += 1;
        }

        self.merge_stats.read_time += start_time.elapsed();
        self.merge_stats.total_kmers_read += total_read;

        let files = temp_manager.take_files();
        self.temp_files.extend(files);

        Ok(())
    }

    /// Merge all sorted chunks into a single sorted stream
    pub fn merge_sorted_chunks(&mut self) -> Result<StreamingMergeIterator, ProcessingError> {
        if self.temp_files.is_empty() {
            return Ok(StreamingMergeIterator::empty());
        }

        let start_time = Instant::now();

        let mut file_readers: Vec<BufReader<File>> = Vec::new();
        let mut heap: BinaryHeap<MergeItem> = BinaryHeap::new();

        for (file_index, file_path) in self.temp_files.iter().enumerate() {
            let file = File::open(file_path).map_err(|e| {
                ProcessingError::io_error(format!(
                    "Failed to open chunk file '{}': {}",
                    file_path.display(),
                    e
                ))
            })?;

            let mut reader = BufReader::new(file);
            let first_entry = KmerEntry::read_from(&mut reader);

            if let Ok(entry) = first_entry {
                heap.push(MergeItem {
                    kmer: entry.kmer,
                    count: entry.count,
                    file_index,
                });
            }

            file_readers.push(reader);
        }

        self.merge_stats.merge_time += start_time.elapsed();

        Ok(StreamingMergeIterator::new(
            heap,
            file_readers,
            self.temp_files.clone(),
        ))
    }

    pub fn stats(&self) -> &StreamingMergeStats {
        &self.merge_stats
    }
}

/// Streaming iterator that merges sorted chunks
pub struct StreamingMergeIterator {
    heap: BinaryHeap<MergeItem>,
    file_readers: Vec<BufReader<File>>,
    _temp_files: Vec<PathBuf>,
    current_kmer: Option<u128>,
    current_count: u32,
}

impl StreamingMergeIterator {
    pub fn new(
        heap: BinaryHeap<MergeItem>,
        file_readers: Vec<BufReader<File>>,
        temp_files: Vec<PathBuf>,
    ) -> Self {
        Self {
            heap,
            file_readers,
            _temp_files: temp_files,
            current_kmer: None,
            current_count: 0,
        }
    }

    pub fn empty() -> Self {
        Self {
            heap: BinaryHeap::new(),
            file_readers: Vec::new(),
            _temp_files: Vec::new(),
            current_kmer: None,
            current_count: 0,
        }
    }
}

impl Iterator for StreamingMergeIterator {
    type Item = Result<(u128, u32), ProcessingError>;

    fn next(&mut self) -> Option<Self::Item> {
        while let Some(mut merge_item) = self.heap.pop() {
            match &self.current_kmer {
                None => {
                    self.current_kmer = Some(merge_item.kmer);
                    self.current_count = merge_item.count;
                }
                Some(current) if *current == merge_item.kmer => {
                    self.current_count = self.current_count.saturating_add(merge_item.count);
                }
                Some(_) => {
                    let result = (self.current_kmer.unwrap(), self.current_count);
                    self.current_kmer = Some(merge_item.kmer);
                    self.current_count = merge_item.count;
                    return Some(Ok(result));
                }
            }

            let reader = &mut self.file_readers[merge_item.file_index];
            if let Ok(next_entry) = KmerEntry::read_from(reader) {
                merge_item.kmer = next_entry.kmer;
                merge_item.count = next_entry.count;
                self.heap.push(merge_item);
            }
        }

        if let Some(kmer) = self.current_kmer.take() {
            return Some(Ok((kmer, self.current_count)));
        }

        None
    }
}

impl Drop for StreamingMergeIterator {
    fn drop(&mut self) {
        // Close all file readers first
        self.file_readers.clear();

        // Clean up temporary files
        for temp_file in &self._temp_files {
            if let Err(e) = std::fs::remove_file(temp_file) {
                log::warn!(
                    "Warning: Failed to remove temporary file {}: {}",
                    temp_file.display(),
                    e
                );
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_database_stream_iterator() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db_path = temp_dir.path().join("test.rkdb");

        let test_entries = [
            KmerEntry::new(0x1234, 10),
            KmerEntry::new(0x5678, 20),
            KmerEntry::new(0x9ABC, 30),
        ];

        let db = crate::database::format::RKDatabase::from_kmer_pairs(
            test_entries.iter().map(|e| (e.kmer, e.count)).collect(),
            31,
            false,
            false,
        )
        .unwrap();
        db.to_file_path(&db_path).unwrap();

        let mut iter = DatabaseStreamIterator::new(&db_path, 2).unwrap();
        let chunk1 = iter.next().unwrap().unwrap();
        assert_eq!(chunk1.len(), 2);
        let chunk2 = iter.next().unwrap().unwrap();
        assert_eq!(chunk2.len(), 1);
        assert!(iter.next().is_none());
    }

    #[test]
    fn test_temp_file_manager() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut manager = TempFileManager::new(temp_dir.path().to_path_buf(), "test");

        let (path, _writer) = manager.create_temp_file().unwrap();
        assert!(path.exists());
        assert_eq!(manager.files.len(), 1);

        let (_path2, _writer2) = manager.create_temp_file().unwrap();
        assert_eq!(manager.files.len(), 2);

        manager.cleanup();
        assert!(!path.exists());
    }

    #[test]
    fn test_external_merge() {
        let temp_dir = tempfile::tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");

        let entries1 = [
            KmerEntry::new(0x0010, 10),
            KmerEntry::new(0x0020, 20),
            KmerEntry::new(0x0030, 30),
        ];

        let db1 = crate::database::format::RKDatabase::from_kmer_pairs(
            entries1.iter().map(|e| (e.kmer, e.count)).collect(),
            31,
            false,
            false,
        )
        .unwrap();
        db1.to_file_path(&db1_path).unwrap();

        let mut merger = ExternalMerger::new(2, temp_dir.path().to_path_buf());
        merger.sort_database(&db1_path).unwrap();

        let mut merge_iter = merger.merge_sorted_chunks().unwrap();

        let result1 = merge_iter.next().unwrap().unwrap();
        assert_eq!(result1, (0x0010, 10));

        let result2 = merge_iter.next().unwrap().unwrap();
        assert_eq!(result2, (0x0020, 20));

        let result3 = merge_iter.next().unwrap().unwrap();
        assert_eq!(result3, (0x0030, 30));

        assert!(merge_iter.next().is_none());
    }
}
