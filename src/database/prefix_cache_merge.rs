//! True external sort merge implementation for large k-mer database merging

use std::fs::File;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use rayon::current_num_threads;
use rayon::prelude::*;

use crate::database::format::{KmerEntry, RKDatabase};
use crate::database::temp_lifecycle::create_merge_temp_subdir;
use crate::error::ProcessingResult;
use crate::kmer::canonical::canonical_kmer_u128;

/// On-disk size of one `KmerEntry` record: `u128` k-mer (16 B) + `u32` count
/// (4 B), little-endian — the `.rkdb` v2 layout written by
/// `KmerEntry::write_to` (`format.rs`).
///
/// Every `try_into().unwrap()` byte-slice conversion below reads exactly this
/// many bytes, so the assumption is stated once here instead of being spelled
/// as a bare `20` at eight separate call sites (`.planning/codebase/CONCERNS.md`
/// "Fragile Area: prefix_cache_merge.rs").
const RECORD_SIZE: usize = 20;

/// Decode the `(kmer, count)` record starting at `offset` in `buf`.
///
/// `buf[offset..offset + RECORD_SIZE]` is split by field width, not by a bare
/// literal, so `RECORD_SIZE` above is the single source of truth for the layout.
fn read_record_at(buf: &[u8], offset: usize) -> (u128, u32) {
    debug_assert!(offset + RECORD_SIZE <= buf.len());
    let kmer = u128::from_le_bytes(buf[offset..offset + 16].try_into().unwrap());
    let count = u32::from_le_bytes(buf[offset + 16..offset + RECORD_SIZE].try_into().unwrap());
    (kmer, count)
}

/// WR-04: the ONE place that decides whether a bucket's shard files are
/// deleted after its merge attempt.
///
/// - A **successful** bucket releases its shards (`!keep_intermediate`): that
///   is the D-06 peak-disk optimization, and the shards are no longer needed.
/// - A **failed** bucket KEEPS them: the shards are the only remaining copy of
///   that bucket's k-mers, so they are the recovery path — deleting them
///   before the error surfaces (the D-06 edit's failure-path deletion, which
///   this replaces) destroyed the last chance to recover or retry the bucket.
/// - `keep_intermediate` keeps everything, as its name promises.
///
/// Generic over the success value because the per-bucket merge steps return
/// `Result<u64, anyhow::Error>` (the emitted-record count WR-04's integrity
/// accounting needs); only the `is_ok()` half participates in the decision.
fn should_remove_shards<T>(result: &Result<T, anyhow::Error>, keep_intermediate: bool) -> bool {
    !keep_intermediate && result.is_ok()
}

pub struct ExternalSortMerger {
    pub prefix_bits: usize,
    pub num_buckets: usize,
    pub merge_buffer_mb: usize,
    /// Parent directory the merge temp subdir is created under.
    pub temp_dir: PathBuf,
    pub input_files: Vec<PathBuf>,
    pub kmer_size: usize,
    pub canonical: bool,
    pub total_kmers: u64,
    pub estimated_kmers_per_file: u64,
    pub num_threads: usize,
    pub merge_mode: String,
    pub keep_intermediate: bool,
    /// D-06: the process-unique `rustkmer-merge-<rand>/` directory that owns
    /// every shard this merge writes.
    ///
    /// Holding the `TempDir` is the cleanup *guarantee*: its `Drop` removes the
    /// tree recursively on every unwind path (normal return, early `?` return,
    /// `panic = "unwind"`). `Option` so `Drop` can `take()` it when
    /// `keep_intermediate` asks for the shards to survive.
    merge_temp_subdir: Option<tempfile::TempDir>,
    /// D-06: every shard path this merge created, tracked so `Drop` can remove
    /// them explicitly before the `TempDir` removes the tree.
    shard_paths: Vec<PathBuf>,
    /// WR-04: total number of records the bucket phase's merge WRITERS emitted.
    ///
    /// Counted inside the write loops (`sorted_kmers.len()` in the hashmap
    /// writer, an increment per emitted record in the streaming writer) and
    /// `fetch_add`ed from the rayon bucket closure — never re-derived from a
    /// merged bucket file's on-disk size, which is what made the deleted
    /// `total_kmers_in_files` comparison a tautology. Read by
    /// [`Self::concatenate_final_output`] as one side of the bucket-phase vs
    /// concatenation conservation check (catches a zero-length or truncated
    /// merged bucket).
    merged_records_recorded: std::sync::atomic::AtomicU64,
    /// WR-04: the prefixes the bucket phase actually merged (declared
    /// non-empty), inserted inside the rayon closure at the top of each task —
    /// before any fallible work, so a bucket whose merge then fails is still
    /// recorded here.
    ///
    /// A `Mutex<BTreeSet<usize>>` (not a `BTreeSet`) because the closure runs
    /// on a rayon worker and cannot take `&mut self`; it lives on the merger
    /// (not as a closure-local) because `non_empty_prefixes` is moved into
    /// `into_par_iter()` and `concatenate_final_output(&self)` must be able to
    /// read the set. Compared against the concatenation's `buckets_seen`
    /// (catches a merged file MISSING from disk at concatenation time).
    non_empty_buckets_recorded: std::sync::Mutex<std::collections::BTreeSet<usize>>,
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

        // G2a / threat T-03-31: this constructor used to call
        // `RKDatabase::from_file_path` on the first input AND then on every
        // input again in the loop below — loading every input database twice,
        // and using the first one only for its header. Both now read 42 bytes
        // via `read_header_of`; the body is never touched.
        //
        // Note also that `read_record_at` above was already a plain
        // `u32::from_le_bytes` with no endianness heuristic: the prefix-cache
        // path never carried the `count_le`/`count_be` fallback that plan 03-07
        // deleted from `KmerEntry::read_from`. The reader, not this file, was
        // the outlier.
        let first_header = RKDatabase::read_header_of(&input_files[0])?;
        let kmer_size = first_header.kmer_size as usize;

        let mut canonical_modes = Vec::new();
        let mut kmer_sizes = Vec::new();

        for path in input_files.iter() {
            let header = RKDatabase::read_header_of(path)?;
            canonical_modes.push(header.canonical);
            kmer_sizes.push(header.kmer_size as usize);
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
        let total_kmers = first_header.total_kmers;

        // D-06: every shard this merge writes lives under its own
        // `rustkmer-merge-<rand>/` subdir instead of loose in the shared
        // `temp_dir`. Two consequences, both load-bearing:
        //   - the `TempDir` gives RAII cleanup on every unwind path, and
        //   - an orphan left by a SIGKILL / `panic = "abort"` / power loss is
        //     unambiguously identifiable, so the next merge can sweep it.
        // If this fails, the merger is never constructed, so nothing to clean up.
        let merge_temp_subdir = create_merge_temp_subdir(&temp_dir)?;

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
            merge_temp_subdir: Some(merge_temp_subdir),
            shard_paths: Vec::new(),
            merged_records_recorded: std::sync::atomic::AtomicU64::new(0),
            non_empty_buckets_recorded: std::sync::Mutex::new(std::collections::BTreeSet::new()),
        })
    }

    /// D-06: the directory this merge's shards are written into.
    ///
    /// Falls back to the parent `temp_dir` only in the degenerate state where
    /// the `TempDir` was already taken by `keep_intermediate`, which can only
    /// happen during `Drop` (after the merge has finished).
    fn shard_dir(&self) -> &Path {
        match self.merge_temp_subdir.as_ref() {
            Some(dir) => dir.path(),
            None => self.temp_dir.as_path(),
        }
    }

    /// The process-unique merge temp subdir, or `None` once it has been taken.
    ///
    /// Exposed so tests can observe *where* a merge's shards live without
    /// reaching into private state.
    pub fn merge_temp_subdir_path(&self) -> Option<&Path> {
        self.merge_temp_subdir.as_ref().map(|dir| dir.path())
    }

    pub fn external_sort_merge(&mut self, output_path: &Path) -> ProcessingResult<()> {
        let total_start = Instant::now();

        log::info!("\n🚀 Starting external sort merge");
        log::info!("   Input files: {}", self.input_files.len());
        log::info!("   Total k-mers: {} M", self.total_kmers / 1_000_000);
        log::info!("   Canonical mode: {}", self.canonical);
        log::info!("   Prefix bucket count: {}", self.num_buckets);

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

        log::info!("\n📊 Merge complete!");
        log::info!("   Total time: {:.1}s", total_time.as_secs_f64());
        log::info!("   Phase 1 (bucketing): {:.1}s", phase1_time.as_secs_f64());
        log::info!("   Phase 2 (merge): {:.1}s", phase2_time.as_secs_f64());
        log::info!(
            "   Phase 3 (concatenate): {:.1}s",
            phase3_time.as_secs_f64()
        );
        log::info!("   Output file: {:?}", output_path);

        Ok(())
    }

    fn split_files_by_prefix(&mut self) -> ProcessingResult<()> {
        log::info!("\n📦 Phase 1 - data bucketing (by first 4 bases)");

        let num_files = self.input_files.len();
        log::info!("   Input file count: {}", num_files);

        let num_workers = current_num_threads();
        log::info!(
            "   Using {} worker threads for parallel bucketing",
            num_workers.min(num_files)
        );

        let start_time = Instant::now();

        let temp_files: Vec<Vec<PathBuf>> = (0..num_files)
            .map(|file_idx| {
                (0..self.num_buckets)
                    .map(|prefix| {
                        let dna = Self::prefix_to_dna(prefix);
                        self.shard_dir()
                            .join(format!("ext_sort_{}_file_{:03}.tmp", dna, file_idx))
                    })
                    .collect()
            })
            .collect();

        // D-06: register every path the merge could write so `Drop` can remove
        // it on any exit. Paths that were never created are harmless —
        // `remove_file` on a missing file is a no-op.
        self.shard_paths
            .extend(temp_files.iter().flatten().cloned());

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

                        if bucket_buffers[prefix].len() >= BATCH_SIZE * RECORD_SIZE {
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
            "   ✅ Bucketing complete: {} M k-mers @ {:.1} M/s (took {:.1}s)",
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
        log::info!("\n🔄 Phase 2 - prefix bucket merge");

        let start_time = Instant::now();

        let mut non_empty_prefixes = Vec::new();
        let mut prefix_file_map: std::collections::HashMap<usize, Vec<(PathBuf, u64)>> =
            std::collections::HashMap::new();

        for prefix in 0..self.num_buckets {
            let mut prefix_files = Vec::new();
            for file_idx in 0..self.input_files.len() {
                let dna = Self::prefix_to_dna(prefix);
                let temp_file_path = self
                    .shard_dir()
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
        log::info!(
            "   Non-empty prefixes: {}/{}",
            non_empty_count,
            self.num_buckets
        );

        let num_workers = rayon::current_num_threads();
        log::info!(
            "   Using {} worker threads for parallel processing",
            num_workers
        );

        let start_parallel = Instant::now();

        // Capture what the rayon closure needs by value. Reading `self` from
        // inside the closure would force `ExternalSortMerger: Sync` and borrow
        // the whole merger across the parallel section.
        let shard_dir = self.shard_dir().to_path_buf();
        let merge_buffer_mb = self.merge_buffer_mb;
        let keep_intermediate = self.keep_intermediate;

        let temp_dir_arc = std::sync::Arc::new(shard_dir);
        let merge_mode_arc = std::sync::Arc::new(self.merge_mode.clone());
        let completed_count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let prefix_file_map_arc = std::sync::Arc::new(prefix_file_map);

        // WR-04 integrity accounting, initialized BEFORE the rayon fan-out and
        // captured by value (as `Arc`s, the same reason :357-359 gives for not
        // reading `self` inside the closure):
        //   - `merged_records_recorded` accumulates the records the bucket
        //     phase's merge WRITERS emitted (post-dedup — a bucket collapsing
        //     duplicate k-mers emits one record per surviving k-mer);
        //   - `non_empty_buckets_recorded` holds the prefixes this phase
        //     actually merged, inserted at the top of each task BEFORE any
        //     fallible work.
        // Both are published onto the merger after the fan-out so
        // `concatenate_final_output(&self)` can compare them against values
        // derived from the concatenation phase — the two sides of WR-04's
        // replacement for the deleted tautological check.
        let merged_records_recorded =
            std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let non_empty_buckets_recorded =
            std::sync::Arc::new(std::sync::Mutex::new(std::collections::BTreeSet::new()));

        let results: Vec<Result<u64, String>> = non_empty_prefixes
            .into_par_iter()
            .map(|prefix| {
                // WR-04: declared-non-empty BEFORE any fallible work, so a
                // bucket whose merge then fails still counts as merged here —
                // that is what lets the set comparison in
                // `concatenate_final_output` catch its merged file going
                // missing, independently of the record counter.
                non_empty_buckets_recorded
                    .lock()
                    .unwrap_or_else(|e| e.into_inner())
                    .insert(prefix);

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
                    let threshold = merge_buffer_mb * 1_000_000;
                    if total_size <= threshold {
                        Self::merge_single_prefix_hashmap(prefix_files, &output_file)
                    } else {
                        Self::merge_single_prefix_streaming(prefix_files, &output_file)
                    }
                };

                // WR-04: shard deletion is decided in ONE place —
                // [`should_remove_shards`]. A successful bucket releases its
                // shards to keep peak disk down (the D-06 optimization); a
                // failed bucket KEEPS them because they are the only copy of
                // k-mers that are about to be lost, and their paths are logged
                // so an operator can recover from them. The previous
                // unconditional-on-failure-path deletion here is exactly what
                // destroyed the recovery data before the error was swallowed.
                if should_remove_shards(&result, keep_intermediate) {
                    for temp_file in files_to_delete {
                        let _ = std::fs::remove_file(&temp_file);
                    }
                } else if result.is_err() {
                    let preserved: Vec<String> = files_to_delete
                        .iter()
                        .map(|p| {
                            std::fs::canonicalize(p)
                                .map(|abs| abs.display().to_string())
                                .unwrap_or_else(|_| p.display().to_string())
                        })
                        .collect();
                    log::error!(
                        "   ❌ Prefix {}: bucket merge failed — {} shard file(s) \
                         PRESERVED on disk for recovery: [{}]",
                        dna,
                        preserved.len(),
                        preserved.join(", ")
                    );
                }

                // WR-04: count what the WRITER emitted. Never read the merged
                // file back — deriving the count from its size would be the
                // deleted tautology with new variable names.
                if let Ok(emitted) = result.as_ref() {
                    merged_records_recorded.fetch_add(*emitted, std::sync::atomic::Ordering::SeqCst);
                }

                let done = completed.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
                if let Ok(emitted) = result.as_ref() {
                    log::info!(
                        "   ✅ Processed: {} | merged {} records | progress: {}/{} ({:.1}%)",
                        dna,
                        emitted,
                        done,
                        non_empty_count,
                        done as f64 / non_empty_count as f64 * 100.0
                    );
                } else {
                    log::error!(
                        "   ❌ Processing failed: {} | error: {}",
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
                        "   📊 Summary: {}/{} ({:.1}%) elapsed {:.1}s ETA {:.0}s   \r",
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

        // WR-04: publish the bucket-phase accounting onto the merger so the
        // concatenation phase can compare against it. Until this runs, the
        // fields hold their constructor zero values.
        self.merged_records_recorded.store(
            merged_records_recorded.load(std::sync::atomic::Ordering::SeqCst),
            std::sync::atomic::Ordering::SeqCst,
        );
        *self
            .non_empty_buckets_recorded
            .lock()
            .unwrap_or_else(|e| e.into_inner()) = non_empty_buckets_recorded
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clone();

        let mut error_count = 0;
        for result in results {
            if let Err(e) = result {
                log::error!("   error: {}", e);
                error_count += 1;
            }
        }

        if error_count == 0 {
            log::info!(
                "   ✅ Merge complete: {} prefix buckets (took {:.1}s, {:.2}s per bucket)",
                non_empty_count,
                phase_time.as_secs_f64(),
                speed_per_prefix
            );
        } else {
            log::error!(
                "   ⚠️ Merge aborted: {} of {} prefix buckets failed (took {:.1}s)",
                error_count,
                non_empty_count,
                phase_time.as_secs_f64()
            );
        }

        // WR-04: a bucket failure ABORTS the merge instead of being swallowed.
        //
        // This deliberately changes merge OUTCOMES: a merge that previously
        // "succeeded" with a partial bucket set — producing a valid-looking
        // `.rkdb` whose `total_kmers` reflected only the buckets that happened
        // to succeed — now fails loudly, so `concatenate_final_output` never
        // runs on partial output and `merge_databases_prefix_cache`'s `?`
        // propagates the error unchanged to the CLI and to PyO3. This was
        // deferred from 03-02 precisely because it is a behavioural decision;
        // it belongs to this gap-closure plan (see deferred-items.md's
        // `merge_prefix_buckets` entry).
        if error_count > 0 {
            return Err(crate::error::ProcessingError::new(format!(
                "prefix-cache merge failed: {} of {} non-empty prefix buckets failed; shard \
                 files of the failed buckets were PRESERVED for recovery under '{}'",
                error_count,
                non_empty_count,
                self.shard_dir().display()
            )));
        }

        Ok(())
    }

    /// Merge one prefix bucket's shards in memory, returning the number of
    /// records the write loop EMITTED (`sorted_kmers.len()`).
    ///
    /// WR-04: the count is what the writer had in hand before writing — never
    /// re-read from the merged file — so `merge_prefix_buckets` can
    /// `fetch_add` it onto `merged_records_recorded` as the bucket phase's
    /// side of the conservation check in `concatenate_final_output`.
    fn merge_single_prefix_hashmap(
        files: Vec<(PathBuf, u64)>,
        output_path: &Path,
    ) -> Result<u64, anyhow::Error> {
        use std::collections::HashMap;
        use std::io::BufReader;

        log::info!("   Using in-memory merge mode");

        // Compute total size
        let total_size: u64 = files.iter().map(|(_, s)| *s).sum();
        let total_kmers = total_size / RECORD_SIZE as u64;

        log::info!("   Input files: {}", files.len());
        log::info!(
            "   Total data: {:.1} MB ({} k-mers)",
            total_size as f64 / 1024.0 / 1024.0,
            total_kmers
        );

        // Check available memory
        if let Ok(mem_info) = sys_info::mem_info() {
            let avail_mem_mb = mem_info.avail as f64 / 1024.0 / 1024.0;
            let required_mem_mb = total_size as f64 / 1024.0 / 1024.0 * 3.0; // account for HashMap overhead

            log::info!("   Available memory: {:.1} MB", avail_mem_mb);
            log::info!("   Estimated required: {:.1} MB", required_mem_mb);

            if required_mem_mb > avail_mem_mb {
                log::warn!("   ⚠️  Warning: estimated memory exceeds available memory!");
                log::warn!("   Suggestion: use --merge-mode streaming");
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
                        "   Progress: {}/{} | processed {} M k-mers | available memory: {:.1} MB",
                        idx,
                        files.len(),
                        processed_kmers / 1_000_000,
                        mem_info.avail as f64 / 1024.0 / 1024.0
                    );
                }
            }

            let file = File::open(file_path).map_err(|e| {
                anyhow::anyhow!("Failed to open file {}: {}", file_path.display(), e)
            })?;

            // WR-08 discipline, applied to the shard reader too: decode in
            // fixed-size blocks (`RECORD_SIZE * 100_000`, the file's one
            // block-size convention) instead of `read_to_end`, carrying any
            // partial-record tail into the next block. Behaviour is
            // identical — the same records are decoded, trailing bytes
            // shorter than one record are ignored exactly as before — but
            // the transient buffer no longer scales with the shard's size.
            let mut reader = BufReader::with_capacity(1_000_000, file);
            let mut block = vec![0u8; RECORD_SIZE * 100_000];
            let mut pending: Vec<u8> = Vec::new();

            loop {
                match reader.read(&mut block) {
                    Ok(0) => break,
                    Ok(n) => {
                        pending.extend_from_slice(&block[..n]);
                        let mut offset = 0usize;
                        while offset + RECORD_SIZE <= pending.len() {
                            let (kmer, count) = read_record_at(&pending, offset);
                            *kmer_counts.entry(kmer).or_insert(0) += count;
                            offset += RECORD_SIZE;
                            processed_kmers += 1;
                        }
                        pending.drain(..offset);
                    }
                    Err(e) => {
                        return Err(anyhow::anyhow!(
                            "Failed to read file {}: {}",
                            file_path.display(),
                            e
                        ));
                    }
                }
            }

            let file_elapsed = file_start.elapsed();
            let speed = if file_elapsed.as_secs_f64() > 0.0 {
                (*file_size as f64 / 1024.0 / 1024.0) / file_elapsed.as_secs_f64()
            } else {
                0.0
            };

            log::info!(
                "   ✓ file {}: {:.1} MB @ {:.1} MB/s",
                idx + 1,
                *file_size as f64 / 1024.0 / 1024.0,
                speed
            );
        }

        // Check final memory usage
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   Merge complete: {} unique k-mers | available memory: {:.1} MB",
                kmer_counts.len(),
                mem_info.avail as f64 / 1024.0 / 1024.0
            );
        }

        log::info!("   Sorting...");
        let sort_start = std::time::Instant::now();

        let mut sorted_kmers: Vec<(u128, u32)> = kmer_counts.into_iter().collect();
        sorted_kmers.sort_by_key(|(k, _)| *k);

        let sort_time = sort_start.elapsed();
        log::info!("   Sort complete: took {:.1}s", sort_time.as_secs_f64());

        log::info!("   Writing output file...");
        let mut output_file = File::create(output_path).map_err(|e| {
            anyhow::anyhow!(
                "Failed to create output file {}: {}",
                output_path.display(),
                e
            )
        })?;

        for (kmer, count) in &sorted_kmers {
            output_file.write_all(&kmer.to_le_bytes())?;
            output_file.write_all(&count.to_le_bytes())?;
        }
        output_file
            .sync_all()
            .map_err(|e| anyhow::anyhow!("Failed to sync file {}: {}", output_path.display(), e))?;

        let total_time = start_time.elapsed();
        log::info!("   Done: total time {:.1}s", total_time.as_secs_f64());

        // WR-04: the writer's own count — `sorted_kmers.len()` was in hand
        // before the write loop ran, and the merged file is never read back.
        Ok(sorted_kmers.len() as u64)
    }

    /// Merge one prefix bucket's shards with a streaming k-way heap merge,
    /// returning the number of records the write loop EMITTED.
    ///
    /// WR-04: same contract as [`Self::merge_single_prefix_hashmap`] — the
    /// count comes from the writer itself (one increment per emitted record),
    /// never from the merged file's size.
    fn merge_single_prefix_streaming(
        files: Vec<(PathBuf, u64)>,
        output_path: &Path,
    ) -> Result<u64, anyhow::Error> {
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
            let data = Vec::with_capacity(BATCH_READ * RECORD_SIZE);
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
        // WR-04: the writer's own emitted-record count, incremented at every
        // record write below and returned — never derived from the file.
        let mut records_emitted = 0u64;

        while let Some(top) = heap.pop() {
            if let Some(kmer) = current_kmer {
                if kmer == top.kmer {
                    current_count += top.count;
                } else {
                    output_file.write_all(&kmer.to_le_bytes())?;
                    output_file.write_all(&current_count.to_le_bytes())?;
                    records_emitted += 1;
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
            records_emitted += 1;
        }
        output_file.sync_all()?;

        Ok(records_emitted)
    }

    fn read_entries_from_file_sync(path: impl AsRef<Path>) -> ProcessingResult<Vec<KmerEntry>> {
        let mut file = File::open(path)?;
        let mut data = Vec::new();
        file.read_to_end(&mut data)?;

        let mut entries = Vec::new();
        let mut offset = 0usize;

        while offset + RECORD_SIZE <= data.len() {
            let (kmer, count) = read_record_at(&data, offset);
            entries.push(KmerEntry::new(kmer, count));
            offset += RECORD_SIZE;
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

        while offset + RECORD_SIZE <= data.len() {
            let (kmer, count) = read_record_at(data, offset);
            entries.push(KmerEntry::new(kmer, count));
            offset += RECORD_SIZE;
        }

        Ok(entries)
    }

    fn get_prefix_4mer(&self, kmer: u128) -> usize {
        let prefix_bits = kmer & 0xFF;
        prefix_bits as usize
    }

    fn concatenate_final_output(&self, output_path: &Path) -> ProcessingResult<()> {
        use std::io::{BufWriter, Write};

        log::info!("\n📦 Phase 3 - final concatenation (using RKDB standard format)");

        let start_time = Instant::now();

        // Monitor memory usage
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   Current memory usage: {:.1} GB / {:.1} GB (available {:.1} GB)",
                (mem_info.total - mem_info.avail) as f64 / 1024.0 / 1024.0 / 1024.0,
                mem_info.total as f64 / 1024.0 / 1024.0 / 1024.0,
                mem_info.avail as f64 / 1024.0 / 1024.0 / 1024.0
            );
        }

        let temp_data_file = self.shard_dir().join("ext_sort_final_data.tmp");
        let mut temp_file = File::create(&temp_data_file)?;
        let mut data_size = 0u64;
        let mut total_kmers_in_files = 0u64;
        // WR-04: the prefixes this concatenation loop actually REACHED — one
        // side of the set comparison below. Inserted for every prefix whose
        // `prefix_file` exists, INCLUDING the `continue`d zero-length ones
        // (the insert happens before the zero-length check), which is exactly
        // why a zero-length bucket is NOT this check's catch — that prefix
        // lands in both sets and equality holds. The zero-length case is
        // caught by `merged_records_recorded` instead.
        let mut buckets_seen: std::collections::BTreeSet<usize> = std::collections::BTreeSet::new();
        // WR-08: one fixed-size copy block, the SAME size the final
        // streaming write below uses (`RECORD_SIZE * 100_000`), so there is
        // one block-size convention in this file, not two. No allocation in
        // this function scales with the size of the largest bucket.
        let mut copy_block = vec![0u8; RECORD_SIZE * 100_000];

        for prefix in 0..self.num_buckets {
            let dna = Self::prefix_to_dna(prefix);
            let prefix_file = self
                .shard_dir()
                .join(format!("ext_sort_{}_merged.tmp", dna));

            if prefix_file.exists() {
                buckets_seen.insert(prefix);

                let file_size = std::fs::metadata(&prefix_file)?.len();

                if file_size == 0 {
                    log::warn!("   ⚠️ empty file: {}", dna);
                    let _ = std::fs::remove_file(&prefix_file);
                    continue;
                }

                let kmers_in_file = file_size / RECORD_SIZE as u64;
                total_kmers_in_files += kmers_in_file;

                let mut input_file = File::open(&prefix_file)?;

                // WR-08: copy in fixed-size blocks instead of `read_to_end` —
                // the prefix-cache path is advertised as memory-efficient, so
                // its peak must be bounded by one block, not by the largest
                // single bucket. `data_size` accumulates the bytes ACTUALLY
                // written (`n`), which is what the integrity comparison above
                // and the `file_size` header field are derived from.
                loop {
                    match input_file.read(&mut copy_block) {
                        Ok(0) => break,
                        Ok(n) => {
                            temp_file.write_all(&copy_block[..n])?;
                            data_size += n as u64;
                        }
                        Err(e) => {
                            return Err(crate::error::ProcessingError::new(format!(
                                "Failed to read merged bucket '{}': {}",
                                prefix_file.display(),
                                e
                            )));
                        }
                    }
                }

                if !self.keep_intermediate {
                    let _ = std::fs::remove_file(&prefix_file);
                }

                // Report progress and memory after each file
                let processed = prefix + 1;
                if processed % 16 == 0 || processed == self.num_buckets {
                    if let Ok(mem_info) = sys_info::mem_info() {
                        log::info!(
                            "   Progress: {}/{} | data: {:.1} MB | k-mers: {} M | available memory: {:.1} MB",
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

        let total_kmers = data_size / RECORD_SIZE as u64;

        log::info!(
            "   Writing RKDB format, {} M k-mers total...",
            total_kmers / 1_000_000
        );
        log::info!(
            "   Counted from files: {} M k-mers",
            total_kmers_in_files / 1_000_000
        );

        // WR-04: the comparison that used to live here —
        // `if total_kmers != total_kmers_in_files` — could NEVER fire:
        // `total_kmers` derived from the bytes the concatenation wrote and
        // `total_kmers_in_files` from `metadata().len()` on the SAME merged
        // bucket files, so the two sides were computed from identical inputs.
        // It could not even see a zero-length bucket (that bucket is
        // `continue`d above and contributes to both sides equally). Do not
        // "restore" it. `total_kmers_in_files` survives only as a diagnostic
        // log line above.
        //
        // The replacement is a conservation check between the BUCKET PHASE
        // and the CONCATENATION, with the two sides derived from different
        // phases, so neither can cancel the other:
        //
        //   1. `merged_records_recorded` (records the bucket phase's merge
        //      WRITERS emitted) vs `total_kmers` (records this reader copied).
        //      A short `write_all`, a truncated bucket file, or a bucket that
        //      had input records but emitted a zero-length file makes them
        //      disagree — this is the zero-length/truncation detector.
        //   2. `non_empty_buckets_recorded` (prefixes the bucket phase
        //      merged) vs `buckets_seen` (prefixes this loop consumed). Its
        //      genuine independent catch is a merged file MISSING from disk
        //      at concatenation time: the loop body never runs for that
        //      prefix, so the sets differ. It does NOT catch the zero-length
        //      case on its own (see `buckets_seen` above).
        //
        // Disjoint inputs are explicitly NOT required here: these checks
        // compare the bucket phase against the concatenation, and duplicate
        // suppression inside a bucket (`HashMap<u128, u32>` in the hashmap
        // writer, run-accumulation in the streaming writer) is correct
        // behaviour, not loss. Do NOT fold the Phase-1 input record total
        // into this comparison — that WOULD require disjoint inputs and
        // would `Err` on every ordinary overlapping merge. The
        // input-vs-output conservation claim is a separate, disjoint-inputs
        // test (`prefix_cache_merge_conserves_the_total_kmer_count`).
        let declared = self
            .non_empty_buckets_recorded
            .lock()
            .unwrap_or_else(|e| e.into_inner());
        if self
            .merged_records_recorded
            .load(std::sync::atomic::Ordering::SeqCst)
            != total_kmers
        {
            return Err(crate::error::ProcessingError::new(format!(
                "prefix-cache merge integrity failure: the bucket phase's merge writers emitted \
                 {} records but the concatenation copied {} ({} of {} prefix buckets declared \
                 non-empty); a zero-length or truncated merged bucket can cause this",
                self.merged_records_recorded
                    .load(std::sync::atomic::Ordering::SeqCst),
                total_kmers,
                declared.len(),
                self.num_buckets
            )));
        }
        if buckets_seen != *declared {
            let never_consumed: Vec<usize> =
                declared.difference(&buckets_seen).copied().collect();
            let undeclared: Vec<usize> =
                buckets_seen.difference(&declared).copied().collect();
            return Err(crate::error::ProcessingError::new(format!(
                "prefix-cache merge integrity failure: prefixes {:?} were merged by the bucket \
                 phase but their merged files were never consumed by the concatenation \
                 (unexpectedly seen prefixes: {:?}); a merged file missing from disk can cause \
                 this",
                never_consumed, undeclared
            )));
        }

        // Monitor memory usage
        if let Ok(mem_info) = sys_info::mem_info() {
            log::info!(
                "   Current available memory: {:.1} GB",
                mem_info.avail as f64 / 1024.0 / 1024.0 / 1024.0
            );
        }

        // Use streaming rather than loading all data at once
        let mut file = File::open(&temp_data_file)?;

        // Build RKDatabase header (data_offset follows header, typically 42 bytes)
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

        // Create output file
        let output = File::create(output_path)?;
        let mut writer = BufWriter::with_capacity(10_000_000, output);

        // Write header
        header.write_to(&mut writer)?;

        // Stream-read and write k-mer data
        let mut buffer = vec![0u8; RECORD_SIZE * 100_000]; // 100k k-mers per batch
        let mut processed_kmers = 0u64;
        let mut last_report = std::time::Instant::now();

        loop {
            match file.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => {
                    let num_kmers = n / RECORD_SIZE;
                    processed_kmers += num_kmers as u64;
                    writer.write_all(&buffer[..n])?;

                    // Report progress every 1 million k-mers
                    if processed_kmers.is_multiple_of(1_000_000)
                        || last_report.elapsed().as_secs() >= 5
                    {
                        if let Ok(mem_info) = sys_info::mem_info() {
                            log::info!(
                                "   Progress: {} M / {} M k-mers | available memory: {:.1} MB",
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
                        "Failed to read data: {}",
                        e
                    )));
                }
            }
        }

        writer.flush()?;
        drop(writer);

        // Write metadata - use the create_metadata helper
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

        // Update statistics
        metadata.total_kmers = total_kmers;
        metadata.unique_kmers = total_kmers;
        metadata.created_at = now;
        metadata.modified_at = now;

        // Write metadata
        let metadata_path = output_path.with_extension("json");
        let metadata_json = serde_json::to_string_pretty(&metadata).map_err(|e| {
            crate::error::ProcessingError::new(format!("Failed to serialize metadata: {}", e))
        })?;
        std::fs::write(&metadata_path, metadata_json).map_err(|e| {
            crate::error::ProcessingError::new(format!("Failed to write metadata: {}", e))
        })?;

        let phase_time = start_time.elapsed();
        log::info!(
            "   ✅ Concatenation complete: {} M k-mers (took {:.1}s)",
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

        while offset + RECORD_SIZE <= data.len() {
            let (kmer, count) = read_record_at(&data, offset);
            entries.push(KmerEntry::new(kmer, count));
            offset += RECORD_SIZE;
        }

        Ok(entries)
    }
}

/// D-06 / MERGE-03: RAII cleanup for the prefix-cache merge.
///
/// Mirrors `streaming_merge.rs::TempFileManager::Drop`. Before this impl the
/// shards were removed only on the success branch, so every other exit — an
/// early `?` return, a logic-error panic, a dropped future — leaked them.
///
/// Two mechanisms, deliberately layered:
///   1. each tracked shard is `remove_file`d best-effort (belt), then
///   2. the `merge_temp_subdir` [`tempfile::TempDir`] field is dropped, which
///      removes the whole tree recursively (suspenders) and also covers any
///      shard this struct never got to track.
///
/// Rust runs this body *before* dropping fields, so the explicit removals
/// happen first and `TempDir` cleans up whatever is left.
///
/// What this still cannot cover: `panic = "abort"`, SIGKILL, `process::exit`,
/// power loss — `Drop` does not run at all. That is precisely why
/// [`crate::database::temp_lifecycle::sweep_stale_merge_dirs`] exists.
impl Drop for ExternalSortMerger {
    fn drop(&mut self) {
        if self.keep_intermediate {
            // `keep()` disarms the TempDir's cleanup and hands the path back, so
            // the shards survive for inspection. This leak is the documented
            // meaning of `--keep-intermediate`; the next merge's sweep will
            // eventually reclaim it (threat T-03-05).
            if let Some(dir) = self.merge_temp_subdir.take() {
                let path = dir.keep();
                log::info!(
                    "Keeping merge temp dir (--keep-intermediate): {}",
                    path.display()
                );
            }
            return;
        }

        for shard in &self.shard_paths {
            let _ = std::fs::remove_file(shard);
        }

        if let Some(dir) = self.merge_temp_subdir.take() {
            // `close()` rather than letting the field drop silently: it reports
            // the removal error instead of swallowing it like `Drop` does.
            if let Err(e) = dir.close() {
                log::warn!(
                    "Failed to remove merge temp dir '{}': {}",
                    self.shard_dir().display(),
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

    /// WR-04 truth table for the one-place shard-removal decision:
    /// success releases the shards (D-06 peak-disk optimization), failure and
    /// `keep_intermediate` both preserve them (the recovery path).
    #[test]
    fn should_remove_shards_truth_table() {
        let ok = Ok::<u64, anyhow::Error>(42);
        let err = Err::<u64, anyhow::Error>(anyhow::anyhow!("bucket merge failed"));

        // Success + no keep -> release (peak-disk optimization applies).
        assert!(should_remove_shards(&ok, false));
        // Failure + no keep -> PRESERVE (WR-04: shards are the recovery path).
        assert!(!should_remove_shards(&err, false));
        // keep_intermediate preserves everything, either way.
        assert!(!should_remove_shards(&ok, true));
        assert!(!should_remove_shards(&err, true));
    }

    /// Build two small real `.rkdb` inputs (valid 42-byte headers) under
    /// `dir`, so `ExternalSortMerger::new` can read them.
    fn write_two_real_inputs(dir: &Path) -> Vec<PathBuf> {
        let mut paths = Vec::new();
        for idx in 0..2u128 {
            let kmers: Vec<(u128, u32)> = (0..50u32)
                .map(|i| (idx * 10_000 + i as u128 + 1, i + 1))
                .collect();
            let db = RKDatabase::from_kmer_pairs(kmers, 21, true, true).expect("build database");
            let path = dir.join(format!("unit_input_{}.rkdb", idx));
            db.write_to_file(&path).expect("write database");
            paths.push(path);
        }
        paths
    }

    /// WR-04 (behavioural half): a bucket whose merge fails must make
    /// `merge_prefix_buckets` return `Err` naming the failed/total bucket
    /// counts, and the failed bucket's shard files must SURVIVE on disk —
    /// the recovery path the D-06 failure-path deletion destroyed.
    ///
    /// Failure is forced deterministically, without permissions and without a
    /// race: a DIRECTORY is planted at prefix 0's shard path
    /// (`ext_sort_AAAA_file_000.tmp`). `merge_prefix_buckets` selects buckets
    /// by `metadata().len() > 0` and a directory's `len()` is non-zero, so
    /// bucket 0 is selected; `merge_single_prefix_hashmap` then either fails
    /// to open it or fails on `read_to_end` with `EISDIR` — either way the
    /// bucket returns `Err`. A directory is used rather than a `chmod 000`
    /// gate because the crate must not depend on the test running as a
    /// non-root user: a root-run `chmod` gate would pass vacuously.
    #[test]
    fn failed_bucket_aborts_the_merge_with_err() {
        let parent = tempfile::tempdir().unwrap();
        let inputs = write_two_real_inputs(parent.path());

        let mut merger = ExternalSortMerger::new(
            inputs,
            parent.path().to_path_buf(),
            1024,
            1,
            "memory".to_string(),
            false,
        )
        .expect("merger over real inputs");
        let subdir = merger
            .merge_temp_subdir_path()
            .expect("merger owns a temp subdir")
            .to_path_buf();

        let shard_path = subdir.join("ext_sort_AAAA_file_000.tmp");
        std::fs::create_dir_all(&shard_path).expect("plant the failing shard");

        let outcome = merger.merge_prefix_buckets();

        let err = outcome.expect_err("a failed bucket must abort the merge, not be swallowed");
        let message = err.to_string();
        assert!(
            message.contains("1 of 1"),
            "the error must name failed out of total bucket counts, got: {message}"
        );
        assert!(
            message.contains("PRESERVED"),
            "the error must point at the preserved shards, got: {message}"
        );
        // The assertion that distinguishes `should_remove_shards` returning
        // false for `Err` from a sweep-everything implementation: the failed
        // bucket's shard is still on disk.
        assert!(
            shard_path.exists(),
            "the failed bucket's shard must survive for recovery: {}",
            shard_path.display()
        );
    }

    /// The complementary branch: after a real successful
    /// `merge_prefix_buckets`, the buckets' input shards are GONE — the D-06
    /// peak-disk optimization still works through `should_remove_shards`.
    #[test]
    fn successful_bucket_releases_its_shards() {
        let parent = tempfile::tempdir().unwrap();
        let inputs = write_two_real_inputs(parent.path());

        let mut merger = ExternalSortMerger::new(
            inputs,
            parent.path().to_path_buf(),
            1024,
            1,
            "memory".to_string(),
            false,
        )
        .expect("merger over real inputs");
        let subdir = merger
            .merge_temp_subdir_path()
            .expect("merger owns a temp subdir")
            .to_path_buf();

        merger
            .split_files_by_prefix()
            .expect("phase 1 buckets the inputs");
        merger
            .merge_prefix_buckets()
            .expect("a merge over valid inputs must succeed");

        let leftover_shards: Vec<String> = std::fs::read_dir(&subdir)
            .into_iter()
            .flatten()
            .flatten()
            .filter(|entry| {
                let name = entry.file_name();
                let name = name.to_string_lossy();
                name.starts_with("ext_sort_") && name.contains("_file_")
            })
            .map(|entry| entry.path().display().to_string())
            .collect();
        assert!(
            leftover_shards.is_empty(),
            "successful buckets must release their input shards, found: {:?}",
            leftover_shards
        );
    }
}
