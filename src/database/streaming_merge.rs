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

/// Byte width of one k-mer record on disk: a 16-byte little-endian `u128`
/// followed by a 4-byte little-endian `u32`.
///
/// Sorted chunk files written by [`ExternalMerger::sort_database`] are bare
/// sequences of these records — no header, no record count — which is why the
/// ONLY way to tell a complete chunk from one truncated mid-record is to check
/// that its length is a whole multiple of `RECORD_SIZE` (see
/// [`ExternalMerger::merge_sorted_chunks`]). Pinned against a real encode by
/// `chunk_record_width_matches_the_pinned_constant` so a `.rkdb` v2 layout
/// change turns that check red instead of silently rejecting every chunk.
pub const RECORD_SIZE: u64 = 20;

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

        // Loud validation of data_offset (CR-01, plan 01-03, foundry D-12 / SPEC P3):
        // the .rkdb v2 format has exactly one valid data_offset (42). The
        // previous silent clamp (if outside 40..=1000, force to 42) could mask
        // a tampered/corrupt file as silently-garbage k-mers. Now any
        // non-canonical offset surfaces immediately, consistent with
        // `RKDatabase::from_file_path` and `DatabaseQuery::open`.
        if header.data_offset != 42 {
            return Err(ProcessingError::new(format!(
                "Unsupported data_offset {} (expected 42); file may be from an incompatible rustkmer version or corrupt",
                header.data_offset
            )));
        }

        reader
            .seek(SeekFrom::Start(header.data_offset))
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
    /// Monotonic per-manager counter used to make chunk file names unique.
    ///
    /// Chunk files used to be named from `SystemTime::now().as_micros()` alone.
    /// The system clock is not monotonic at microsecond granularity — several
    /// `create_temp_file` calls in a tight loop routinely land on the same
    /// microsecond — so `File::create` truncated and overwrote a sibling chunk.
    /// That silently destroyed sorted runs and dropped k-mers from the merged
    /// output (measured: 200 k-mers in → 5 out). The counter makes every chunk
    /// name unique within the process; the timestamp is kept for readability.
    next_file_id: u64,
}

impl TempFileManager {
    pub fn new(temp_dir: PathBuf, operation: &str) -> Self {
        let prefix = format!("rustkmer_{}_{}", operation, std::process::id());
        Self {
            temp_dir,
            files: Vec::new(),
            prefix,
            auto_cleanup: true,
            next_file_id: 0,
        }
    }

    pub fn with_cleanup(mut self, auto_cleanup: bool) -> Self {
        self.auto_cleanup = auto_cleanup;
        self
    }

    pub fn create_temp_file(&mut self) -> Result<(PathBuf, BufWriter<File>), ProcessingError> {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_micros())
            .unwrap_or(0);

        // `next_file_id` guarantees uniqueness; the timestamp is informational.
        let file_id = self.next_file_id;
        self.next_file_id += 1;

        let file_name = format!("{}_{}_{}.chunk", self.prefix, timestamp, file_id);
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

            // A chunk truncated mid-record has no 20-byte record boundary to
            // land on, so the iterator below would read its partial tail as a
            // clean end-of-run and silently drop that k-mer. Chunk files carry
            // no record count, so their length is the only evidence available —
            // and this is the only site that still has it, before any reading
            // begins. Threat T-03-27.
            let chunk_len = file.metadata().map(|m| m.len()).map_err(|e| {
                ProcessingError::io_error(format!(
                    "Failed to stat chunk file '{}': {}",
                    file_path.display(),
                    e
                ))
            })?;
            if chunk_len % RECORD_SIZE != 0 {
                return Err(ProcessingError::io_error(format!(
                    "Damaged chunk file '{}': length {} is not a whole multiple of the {}-byte \
                     record, so it was truncated mid-k-mer",
                    file_path.display(),
                    chunk_len,
                    RECORD_SIZE
                )));
            }

            let mut reader = BufReader::new(file);
            // EOF here means a zero-record chunk. `sort_database` only writes a
            // chunk after reading at least one entry, so an empty one is damage,
            // not an empty run: the pre-fix code was `if let Ok(entry) = ..`
            // with no else arm and let it contribute nothing to the merge while
            // reporting success.
            match KmerEntry::read_from(&mut reader) {
                Ok(entry) => heap.push(MergeItem {
                    kmer: entry.kmer,
                    count: entry.count,
                    file_index,
                }),
                Err(e) => {
                    return Err(ProcessingError::io_error(format!(
                        "Failed to read first entry of chunk file '{}': {}",
                        file_path.display(),
                        e
                    )))
                }
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
    /// A read failure observed while draining the heap, reported on the NEXT
    /// `next()` call rather than swallowed.
    ///
    /// The pre-fix refill was `if let Ok(next_entry) = KmerEntry::read_from(..)`
    /// with no else arm, so a mid-run read failure ended that run early and the
    /// iterator reported a clean, shorter merge. Silent truncation of a merge is
    /// exactly the defect class plan 03-01 found twice (200 k-mers in, 5 out).
    /// Threat T-03-26.
    pending_error: Option<ProcessingError>,
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
            pending_error: None,
        }
    }

    pub fn empty() -> Self {
        Self {
            heap: BinaryHeap::new(),
            file_readers: Vec::new(),
            _temp_files: Vec::new(),
            current_kmer: None,
            current_count: 0,
            pending_error: None,
        }
    }
}

impl Iterator for StreamingMergeIterator {
    type Item = Result<(u128, u32), ProcessingError>;

    fn next(&mut self) -> Option<Self::Item> {
        // Report a refill failure observed on the previous call BEFORE draining
        // further. The iterator is then finished: the run it belonged to has
        // already been abandoned mid-drain, so there is no consistent point to
        // resume from and no partial run may be emitted beside the error.
        if let Some(err) = self.pending_error.take() {
            self.current_kmer = None;
            self.current_count = 0;
            self.heap.clear();
            return Some(Err(err));
        }

        while let Some(merge_item) = self.heap.pop() {
            let kmer = merge_item.kmer;
            let count = merge_item.count;

            // Advance this run's reader and re-queue its successor BEFORE
            // deciding what to emit.
            //
            // The emit branch below returns early, so a refill placed after
            // the match would be skipped on every k-mer boundary: the popped
            // item would be consumed for the emit and its successor would
            // never be read, silently truncating that run. Measured impact of
            // the old ordering: a 10-entry database merged to 2 k-mers, a
            // 200-entry database to 5. (plan 03-01's fix — preserved here.)
            let reader = &mut self.file_readers[merge_item.file_index];
            match KmerEntry::read_from(reader) {
                Ok(next_entry) => self.heap.push(MergeItem {
                    kmer: next_entry.kmer,
                    count: next_entry.count,
                    file_index: merge_item.file_index,
                }),
                // `UnexpectedEof` is how a run ends NORMALLY: the reader has
                // consumed exactly the chunk's records and there is no next one.
                // Treating it as damage would drop the final k-mer of every run
                // — and does: it turned a 3-entry merge into 2 results plus an
                // error. Mid-record truncation is caught earlier and exactly, by
                // the `len % RECORD_SIZE` check in `merge_sorted_chunks`, which
                // is the only place that can tell the two apart.
                Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => {}
                Err(e) => {
                    // Record the FIRST failure only: a second failure while
                    // draining the same run must never mask the one that
                    // explains where the data stopped being trustworthy.
                    //
                    // The popped `merge_item` is deliberately NOT re-queued and
                    // the heap / `current_kmer` / `current_count` are left
                    // untouched, so no k-mer is double-counted if a caller ever
                    // retries and no partial run is emitted beside the error.
                    if self.pending_error.is_none() {
                        self.pending_error = Some(ProcessingError::io_error(format!(
                            "Failed to read k-mer entry from chunk file '{}': {}",
                            self._temp_files[merge_item.file_index].display(),
                            e
                        )));
                    }
                    // Return IMMEDIATELY rather than falling through to the
                    // `match &self.current_kmer` emit arm: falling through
                    // would emit the half-accumulated run AND the error on a
                    // later call — a partial run beside the error, which is the
                    // exact ambiguity this rule exists to prevent.
                    return Some(Err(self
                        .pending_error
                        .take()
                        .expect("pending_error was just set")));
                }
            }

            match &self.current_kmer {
                None => {
                    self.current_kmer = Some(kmer);
                    self.current_count = count;
                }
                Some(current) if *current == kmer => {
                    self.current_count = self.current_count.saturating_add(count);
                }
                Some(_) => {
                    let result = (self.current_kmer.unwrap(), self.current_count);
                    self.current_kmer = Some(kmer);
                    self.current_count = count;
                    return Some(Ok(result));
                }
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

    /// `RECORD_SIZE` is the sole basis for the mid-record truncation check in
    /// `merge_sorted_chunks`. If it drifts from the real `.rkdb` v2 record
    /// width, every well-formed chunk is rejected (loud) or every damaged one is
    /// accepted (silent) — so pin it against an actual encode rather than
    /// against a restated literal.
    #[test]
    fn chunk_record_width_matches_the_pinned_constant() {
        let mut buf = Vec::new();
        KmerEntry::new(0x0123456789ABCDEF, u32::MAX)
            .write_to(&mut buf)
            .unwrap();
        assert_eq!(
            buf.len() as u64,
            RECORD_SIZE,
            "the pinned record width no longer matches what write_to emits — the \
             truncation check in merge_sorted_chunks cannot be trusted"
        );
    }

    /// Threat T-03-27: a chunk file truncated mid-record is DAMAGED INPUT and
    /// must surface as an `Err` naming the file. Chunk files carry no record
    /// count, so a partial tail would otherwise read as a clean end-of-run and
    /// silently drop that k-mer from the merged output.
    #[test]
    fn chunk_truncated_mid_record_is_reported_not_silently_dropped() {
        let temp_dir = tempfile::tempdir().unwrap();

        // Two whole records plus a 7-byte tail: 47 bytes, not a multiple of 20.
        let mut bytes = Vec::new();
        KmerEntry::new(0x0010, 10).write_to(&mut bytes).unwrap();
        KmerEntry::new(0x0020, 20).write_to(&mut bytes).unwrap();
        bytes.extend_from_slice(&[0u8; 7]);
        let damaged = temp_dir.path().join("damaged.chunk");
        std::fs::write(&damaged, &bytes).unwrap();

        let mut merger = ExternalMerger::new(2, temp_dir.path().to_path_buf());
        merger.temp_files.push(damaged.clone());

        let err = match merger.merge_sorted_chunks() {
            Ok(_) => panic!("a chunk truncated mid-record must not merge as a clean run"),
            Err(e) => e,
        };
        let msg = err.to_string();
        assert!(
            msg.contains("truncated mid-k-mer"),
            "the error must name the truncation, got: {}",
            msg
        );
        assert!(
            msg.contains("damaged.chunk"),
            "the error must name the offending chunk file, got: {}",
            msg
        );
    }

    /// A well-formed chunk of the same k-mers must still merge — the truncation
    /// check is not a blanket rejection.
    #[test]
    fn chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut bytes = Vec::new();
        KmerEntry::new(0x0010, 10).write_to(&mut bytes).unwrap();
        KmerEntry::new(0x0020, 20).write_to(&mut bytes).unwrap();
        let intact = temp_dir.path().join("intact.chunk");
        std::fs::write(&intact, &bytes).unwrap();

        let mut merger = ExternalMerger::new(2, temp_dir.path().to_path_buf());
        merger.temp_files.push(intact);

        let merged: Vec<(u128, u32)> = merger
            .merge_sorted_chunks()
            .unwrap()
            .map(|r| r.expect("a whole-record chunk must not produce an error"))
            .collect();
        assert_eq!(
            merged,
            vec![(0x0010, 10), (0x0020, 20)],
            "a whole-record chunk must merge to exactly its records — every \
             k-mer present, including the last"
        );
    }
}
