//! Database format definitions and I/O operations
//!
//! Defines the binary format for storing k-mer databases with
//! efficient random access and compatibility with rustkmer tools.

use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use serde::{Deserialize, Serialize};
use std::io::{Read, Result as IoResult, Write};

/// Magic number for rustkmer database files
pub const DATABASE_MAGIC: &[u8; 4] = b"RKDB";

/// Database version
pub const DATABASE_VERSION: u16 = 2;

/// Lower bound (in MB) on the per-prefix-bucket merge buffer.
///
/// This value REPLACED a hard-coded 1 GB floor (`merge_buffer_mb.max(1024)`,
/// review finding IN-01). That floor silently overrode a user's
/// `--max-memory 256MB` by 4x, on exactly the path that flag exists to
/// constrain: `merge_buffer_mb` becomes the per-bucket byte threshold in
/// `prefix_cache_merge.rs`, so a user who asked for a 256 MB budget still
/// got up to 1 GB resident per bucket.
///
/// The old floor is not justified anywhere in the record, and the code review
/// treated it as *possibly deliberate* (a guard against a pathologically small
/// per-bucket buffer). The judgement here is that a memory-budget flag the
/// code silently overrides is a bug, and the "don't be pathologically small"
/// intent is preserved two ways: the floor is now 1 MB rather than 0, and when
/// it does raise a smaller configured value the merge logs one line naming both
/// numbers, so the adjustment is visible rather than silent.
///
/// MINIM-03 (4-prefix / 256-bucket granularity) is a v2 requirement and is
/// explicitly out of scope: this constant changes how the existing
/// `num_buckets = 1 << 8` is bounded, not how many buckets there are.
const PREFIX_CACHE_MIN_BUFFER_MB: usize = 1;

// ---------------------------------------------------------------------------
// Per-route admission model (review finding WR-01).
//
// Every constant below is DERIVED from the structures that route actually holds
// live at its peak. That derivation is the point: the pre-fix model was a bare
// 24-bytes-per-k-mer multiply with no derivation at all, and it was roughly a
// quarter of the peak it was supposed to bound — so a merge the gate admitted
// could still OOM. A constant nobody derived is how the 24 became wrong in the
// first place.
// ---------------------------------------------------------------------------

/// Per-k-mer admission cost charged to the IN-MEMORY route, in bytes: 96.
///
/// Derived from the three structures that dominate that route's peak, each of
/// which is exactly **32 bytes per element** on this target
/// (`u128 + u32` is 20 B of payload, padded to `u128`'s 16-byte alignment; the
/// `size_of` values are pinned by
/// `estimated_bytes_per_route_reflects_each_routes_peak` in
/// `tests/merge_routing_tests.rs`, as a floor and a drift alarm rather than as
/// this comment's evidence):
///   - 32 B — the `Vec<KmerEntry>` inside each loaded input `RKDatabase`, one
///     per input record,
///   - 32 B — the `hashbrown::HashMap<u128, u32>` accumulator, whose bucket is
///     a 32-byte `(u128, u32)` pair,
///   - 32 B — the `Vec<(u128, u32)>` drained out of that map.
///
/// # This constant makes NO direction claim about the true peak
///
/// `merge_databases_inmemory` does **not** hold all three for the same k-mer
/// at the same instant: the map is drained by `into_iter()` and its table is
/// freed at the end of that drain, before `from_kmer_pairs` allocates its
/// `Vec<KmerEntry>`. So the real peak is at most `32*N + 68*U` and at least
/// `32*N + 64*U` (N = total input record count, U = unique k-mer count), and
/// the two candidates differ by about 6%. **96 sits at neither extreme**: a
/// claim that it over- or under-states the peak would be arithmetic this
/// comment cannot support, because hashbrown's control bytes and load factor
/// are not modelled here at all.
///
/// The value is rounded UP from the dominant structure's own size because an
/// admission gate that errs toward streaming is safe, and one that errs toward
/// admitting is the bug this constant exists to fix. The instrument that will
/// actually measure the real peak is plan 03-10's `/proc/self/status` test, not
/// this arithmetic.
const INMEMORY_BYTES_PER_KMER: u64 = 96;

/// Per-k-mer cost REPORTED for the streaming route, in bytes: 32.
///
/// **Diagnostic only. This figure is never used to reject a route.** The
/// streaming route's resident set is one `chunk_size` buffer of `KmerEntry`
/// plus a heap of run heads — O(chunk), not O(N) — so any linear per-k-mer
/// figure is a conservative upper bound reported for operator visibility only.
/// Stated explicitly so nobody later mistakes it for a second admission test.
const STREAMING_BYTES_PER_KMER: u64 = 32;

/// Per-k-mer cost REPORTED for the prefix-cache route, in bytes: 32.
///
/// **Diagnostic only, same as [`STREAMING_BYTES_PER_KMER`].** One bucket is
/// resident at a time, bounded by the per-bucket `merge_buffer_mb` threshold —
/// again O(bucket), not O(N).
const PREFIX_CACHE_BYTES_PER_KMER: u64 = 32;

/// Database file header containing metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseHeader {
    /// Magic number for file identification
    pub magic: [u8; 4],
    /// Format version
    pub version: u16,
    /// K-mer size (1-127)
    pub kmer_size: u8,
    /// RECORD COUNT: the number of distinct k-mer RECORDS in the file, i.e.
    /// `entries.len()` — **not** the sum of their `count` fields.
    ///
    /// IN-03: this name collides with `KmerCounter::total_kmers()`
    /// (`src/hash/table.rs`), which is the SUM OF COUNTS — an `AtomicU64`
    /// bumped once per observation. Both meanings are live in one binary
    /// format, and `pyo3/tests/test_database_merge.py::_estimated_bytes` has
    /// to say in prose that it wants this one. Both sites now document which
    /// they are. Renaming either is a breaking public-API change and is
    /// deliberately NOT done here; see the plan's deferral note.
    ///
    /// This is also the field the admission-control model is built on
    /// ([`Self::estimate_total_kmers`] and
    /// [`Self::estimated_bytes_for_route`]), so reading the wrong meaning here
    /// scales the estimate by the average count — which is why the distinction
    /// is written down rather than left to the reader.
    pub total_kmers: u64,
    /// Whether k-mers are sorted for binary search
    pub sorted: bool,
    /// Offset to k-mer data section
    pub data_offset: u64,
    /// Offset to index section (if present)
    pub index_offset: u64,
    /// Whether canonical k-mers were used
    pub canonical: bool,

    /// Total unique k-mers (for compatibility)
    pub unique_kmers: u64,

    /// File size in bytes (for compatibility)
    pub file_size: u64,
}

impl Default for DatabaseHeader {
    fn default() -> Self {
        Self {
            magic: *DATABASE_MAGIC,
            version: DATABASE_VERSION,
            kmer_size: 0,
            total_kmers: 0,
            sorted: false,
            data_offset: 0,
            index_offset: 0,
            canonical: false,
            unique_kmers: 0,
            file_size: 0,
        }
    }
}

impl DatabaseHeader {
    /// Create a new database header
    pub fn new(kmer_size: u8, total_kmers: u64, canonical: bool) -> Self {
        // Standard header size is 42 bytes:
        // 4 (magic) + 2 (version) + 1 (kmer_size) + 1 (padding) + 2 (padding) +
        // 8 (total_kmers) + 1 (flags) + 7 (padding) + 8 (data_offset) + 8 (index_offset) = 42
        Self {
            magic: *DATABASE_MAGIC,
            version: DATABASE_VERSION,
            kmer_size,
            total_kmers,
            sorted: false,
            data_offset: 42,
            index_offset: 0,
            canonical,
            unique_kmers: total_kmers,
            file_size: 0,
        }
    }

    /// Write header to file
    pub fn write_to<W: Write>(&self, writer: &mut W) -> IoResult<()> {
        // Write magic number
        writer.write_all(&self.magic)?;
        // Write version
        writer.write_u16::<LittleEndian>(self.version)?;
        // Write k-mer size
        writer.write_u8(self.kmer_size)?;
        // Pad to 4-byte alignment
        writer.write_u8(0)?;
        writer.write_u16::<LittleEndian>(0)?;
        // Write total k-mers
        writer.write_u64::<LittleEndian>(self.total_kmers)?;
        // Write flags
        let flags: u8 = if self.sorted { 1 } else { 0 } | if self.canonical { 2 } else { 0 };
        writer.write_u8(flags)?;
        // Pad to 8-byte alignment (alignment padding to match read_from)
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
        writer.write_u8(0)?; // padding
                             // Write actual data
        writer.write_u64::<LittleEndian>(self.data_offset)?;
        writer.write_u64::<LittleEndian>(self.index_offset)?;

        Ok(())
    }

    /// Read header from file
    pub fn read_from<R: Read>(reader: &mut R) -> IoResult<Self> {
        let mut magic = [0u8; 4];
        reader.read_exact(&mut magic)?;

        if magic != *DATABASE_MAGIC {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Invalid database magic number",
            ));
        }

        let version = reader.read_u16::<LittleEndian>()?;
        if version != DATABASE_VERSION {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("Unsupported database version: {}", version),
            ));
        }

        let kmer_size = reader.read_u8()?;
        // Skip padding
        let _padding1 = reader.read_u8()?;
        let _padding2 = reader.read_u16::<LittleEndian>()?;

        let total_kmers = reader.read_u64::<LittleEndian>()?;
        let flags = reader.read_u8()?;
        let sorted = (flags & 1) != 0;
        let canonical = (flags & 2) != 0;

        // Skip padding (7 bytes to match write_to format)
        let _padding1 = reader.read_u8()?;
        let _padding2 = reader.read_u8()?;
        let _padding3 = reader.read_u8()?;
        let _padding4 = reader.read_u8()?;
        let _padding5 = reader.read_u8()?;
        let _padding6 = reader.read_u8()?;
        let _padding7 = reader.read_u8()?;

        let data_offset = reader.read_u64::<LittleEndian>()?;
        let index_offset = reader.read_u64::<LittleEndian>()?;

        Ok(Self {
            magic,
            version,
            kmer_size,
            total_kmers,
            sorted,
            data_offset,
            index_offset,
            canonical,
            unique_kmers: total_kmers, // Default to total_kmers for older format compatibility
            file_size: 0,              // Unknown until full file is read
        })
    }

    /// Validate header consistency
    ///
    /// Enforces the SPEC P3 invariant: the `.rkdb` v2 format has exactly one
    /// valid `data_offset` (42 — the canonical header size written by every
    /// writer in this crate). Any other value means the file is from an
    /// incompatible rustkmer version or corrupt, and must surface as an error
    /// rather than being silently clamped (which would read garbage k-mers).
    pub fn validate(&self) -> Result<(), String> {
        if self.kmer_size == 0 || self.kmer_size > 127 {
            return Err(format!("Invalid k-mer size: {}", self.kmer_size));
        }

        if self.data_offset != 42 {
            return Err(format!(
                "Invalid data offset: {} (expected 42 — the only canonical .rkdb v2 header size)",
                self.data_offset
            ));
        }

        if self.index_offset > 0 && self.index_offset <= self.data_offset {
            return Err("Invalid index offset".to_string());
        }

        Ok(())
    }
}

/// Represents a k-mer entry in the database
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KmerEntry {
    /// Packed k-mer representation (u128 for k≤64)
    pub kmer: u128,
    /// Count of this k-mer
    pub count: u32,
}

impl KmerEntry {
    /// Create a new k-mer entry
    pub fn new(kmer: u128, count: u32) -> Self {
        Self { kmer, count }
    }

    /// Write entry to binary format (16 bytes kmer + 4 bytes count)
    pub fn write_to<W: Write>(&self, writer: &mut W) -> IoResult<()> {
        writer.write_u128::<LittleEndian>(self.kmer)?;
        writer.write_u32::<LittleEndian>(self.count)
    }

    /// Read entry from binary format (16 bytes kmer + 4 bytes count)
    ///
    /// # Invariant: this is the exact inverse of [`Self::write_to`]
    ///
    /// The `.rkdb` v2 record layout is a 16-byte little-endian `u128` followed
    /// by a 4-byte little-endian `u32`. **Every** writer in this crate emits
    /// little-endian — [`Self::write_to`], the streaming chunk writer in
    /// `streaming_merge::ExternalMerger::sort_database`, and
    /// `count.rs`'s delegating write path — so this reader decodes
    /// little-endian and nothing else.
    ///
    /// The pre-fix reader carried an endianness heuristic: if the
    /// little-endian count came out above `1_000_000`, it was re-read as
    /// big-endian. That is **not** a compatibility feature, it is silent data
    /// corruption on valid input: every count above one million was returned
    /// byte-swapped (`2_000_000` -> `2_156_142_080`, `16_777_216` -> `1`).
    /// It also made the two merge routes disagree, because the in-memory route
    /// applied it once while the streaming route applied it twice (read ->
    /// little-endian chunk write -> read back), so the double swap cancelled
    /// by accident. Same input, same budget, different data depending only on
    /// which route the budget picked.
    ///
    /// There is **no legacy big-endian file to preserve**: the format is v2
    /// and has only ever been written little-endian by this crate. The one
    /// legacy fixture in the repo, `tests/fixtures/legacy_v2_offset42.rkdb`,
    /// round-trips through this same little-endian path. The re-introduced
    /// `u128` read is deliberately left as `read_u128::<LittleEndian>()`; it
    /// had no heuristic and was never part of the defect.
    ///
    /// Threat T-03-24. The counts that used to be corrupted are pinned by
    /// `kmer_entry_round_trips_counts_above_the_old_threshold` below and by
    /// `tests/merge_route_parity_tests.rs`.
    pub fn read_from<R: Read>(reader: &mut R) -> IoResult<Self> {
        let kmer = reader.read_u128::<LittleEndian>()?;

        let mut count_bytes = [0u8; 4];
        reader.read_exact(&mut count_bytes)?;
        let count = u32::from_le_bytes(count_bytes);

        Ok(Self { kmer, count })
    }
}

/// Database format types
#[derive(Debug, Clone)]
pub enum DatabaseFormat {
    /// Standard binary format (sorted k-mers)
    Standard,
    /// Indexed format with hash table for fast lookup
    Indexed,
    /// Compressed format (future implementation)
    Compressed,
}

impl DatabaseFormat {
    /// Get the file extension for this format
    pub fn extension(&self) -> &'static str {
        match self {
            DatabaseFormat::Standard => "rkdb",
            DatabaseFormat::Indexed => "rkdb",
            DatabaseFormat::Compressed => "rkdbz",
        }
    }
}

/// RustKmer Database - main structure for storing and querying k-mers
#[derive(Debug)]
pub struct RKDatabase {
    pub header: DatabaseHeader,
    pub entries: Vec<KmerEntry>,
    pub file_path: Option<std::path::PathBuf>,
}

impl RKDatabase {
    /// Create a new database with the given header
    pub fn new(header: DatabaseHeader) -> Self {
        Self {
            header,
            entries: Vec::new(),
            file_path: None,
        }
    }

    /// Get reference to the database header
    pub fn header(&self) -> &DatabaseHeader {
        &self.header
    }

    /// Load database from file path
    pub fn from_file_path(path: &std::path::Path) -> crate::error::ProcessingResult<Self> {
        use std::fs::File;
        use std::io::{BufReader, Seek, SeekFrom};

        let file_path = path.to_path_buf();
        let file =
            File::open(path).map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;

        let mut reader = BufReader::new(file);
        let header = DatabaseHeader::read_from(&mut reader)?;

        // Loud validation of data_offset (plan 01-03, foundry D-12 / SPEC P3):
        // the previous code silently rewrote any out-of-range data_offset to 42
        // and then read from that (possibly wrong) offset, which could surface
        // a tampered or corrupt file as silently-garbage k-mers. The .rkdb v2
        // format has exactly one valid data_offset (42 — the canonical header
        // size set by every writer in this crate). Anything else is an
        // incompatible/corrupt file and must surface as an error immediately.
        // The legacy fixture (tests/fixtures/legacy_v2_offset42.rkdb, D-12) has
        // data_offset = 42 and therefore reads without error.
        if header.data_offset != 42 {
            return Err(crate::error::ProcessingError::new(format!(
                "Unsupported data_offset {} (expected 42); file may be from an incompatible rustkmer version or corrupt",
                header.data_offset
            )));
        }
        let actual_data_offset = header.data_offset;

        // Seek to data section
        reader
            .seek(SeekFrom::Start(actual_data_offset))
            .map_err(|e| {
                crate::error::ProcessingError::io_error(format!(
                    "Failed to seek to data section: {}",
                    e
                ))
            })?;

        // Load k-mer entries
        let mut entries = Vec::with_capacity(header.total_kmers as usize);
        for _ in 0..header.total_kmers {
            let entry = KmerEntry::read_from(&mut reader).map_err(|e| {
                crate::error::ProcessingError::io_error(format!(
                    "Failed to read k-mer entry: {}",
                    e
                ))
            })?;
            entries.push(entry);
        }

        Ok(Self {
            header,
            entries,
            file_path: Some(file_path),
        })
    }

    /// Read ONLY the 42-byte `.rkdb` header of `path`, materializing no entries.
    ///
    /// # Cost
    ///
    /// O(42 bytes) per call, **not** O(entries). This is the same header-only
    /// read D-01 introduced for [`Self::estimate_total_kmers`], now also
    /// available to the merge strategies the estimator routes *into* — the
    /// over-budget path, whose entire purpose is to handle inputs that do not
    /// fit, cannot afford to load one.
    ///
    /// The `data_offset != 42` rejection below is deliberately the SAME check,
    /// with the SAME error text, that [`Self::from_file_path`] applies: a file
    /// this reader refuses is a file every other reader in the crate refuses,
    /// so an incompatible or corrupt file fails identically whether or not its
    /// body was going to be loaded.
    ///
    /// `pub` following the 03-01 precedent that made `estimate_total_kmers`
    /// public specifically so an integration test (an external crate) could
    /// assert the header-only property from outside.
    pub fn read_header_of(
        path: &std::path::Path,
    ) -> crate::error::ProcessingResult<DatabaseHeader> {
        use std::fs::File;
        use std::io::BufReader;

        let file =
            File::open(path).map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;
        let mut reader = BufReader::new(file);
        // Reads exactly 42 bytes and returns — no `KmerEntry` is created.
        let header = DatabaseHeader::read_from(&mut reader)?;

        // Identical rejection and message to `from_file_path` (see the
        // rationale comment there): the `.rkdb` v2 format has exactly one
        // valid data_offset, so anything else is incompatible/corrupt.
        if header.data_offset != 42 {
            return Err(crate::error::ProcessingError::new(format!(
                "Unsupported data_offset {} (expected 42); file may be from an incompatible rustkmer version or corrupt",
                header.data_offset
            )));
        }

        Ok(header)
    }

    /// Load database from file path with memory mapping
    pub fn from_file_path_mapped(path: &std::path::Path) -> crate::error::ProcessingResult<Self> {
        // For now, fall back to regular file reading
        // Memory mapping would be implemented here
        Self::from_file_path(path)
    }

    /// Read database from a reader
    pub fn read_from<R: std::io::Read>(reader: &mut R) -> crate::error::ProcessingResult<Self> {
        let header = DatabaseHeader::read_from(reader)?;

        // For non-seekable readers, we can't load k-mer entries
        // Create an empty database that will be populated if needed
        Ok(Self {
            header,
            entries: Vec::new(),
            file_path: None,
        })
    }

    /// Write database to file
    pub fn write_to_file(&self, path: &std::path::Path) -> crate::error::ProcessingResult<()> {
        use std::fs::File;
        use std::io::BufWriter;

        let file = File::create(path)
            .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;

        let mut writer = BufWriter::new(file);
        self.write_to(&mut writer)
    }

    /// Write database to a writer
    pub fn write_to<W: std::io::Write>(
        &self,
        writer: &mut W,
    ) -> crate::error::ProcessingResult<()> {
        self.header.write_to(writer)?;

        // Write k-mer entries
        for entry in &self.entries {
            entry.write_to(writer)?;
        }

        Ok(())
    }

    /// Get the k-mer size
    pub fn kmer_size(&self) -> usize {
        self.header.kmer_size as usize
    }

    /// Get the total number of k-mers
    pub fn size(&self) -> Option<u64> {
        Some(self.header.total_kmers)
    }

    /// Query a k-mer from the database
    pub fn query_kmer(&self, kmer: &str) -> Option<u64> {
        // Encode the query k-mer using u128 encoding
        let query_encoded = match crate::kmer::encoding::encode_kmer_u128(kmer) {
            Ok(encoded) => encoded,
            Err(_) => return None,
        };

        // Use binary search if the database is sorted
        if self.header.sorted {
            self.binary_search_kmer(query_encoded)
        } else {
            // Linear search for unsorted database
            self.linear_search_kmer(query_encoded)
        }
    }

    /// Binary search for a k-mer in a sorted database
    fn binary_search_kmer(&self, query_encoded: u128) -> Option<u64> {
        use std::cmp::Ordering;

        let mut left = 0;
        let mut right = self.entries.len();

        while left < right {
            let mid = left + (right - left) / 2;
            let mid_kmer = self.entries[mid].kmer;

            match query_encoded.cmp(&mid_kmer) {
                Ordering::Equal => return Some(self.entries[mid].count as u64),
                Ordering::Less => right = mid,
                Ordering::Greater => left = mid + 1,
            }
        }

        None
    }

    /// Linear search for a k-mer in an unsorted database
    fn linear_search_kmer(&self, query_encoded: u128) -> Option<u64> {
        for entry in &self.entries {
            if entry.kmer == query_encoded {
                return Some(entry.count as u64);
            }
        }
        None
    }

    /// Get all k-mers from the database as a vector
    pub fn all_kmers(&self) -> crate::error::ProcessingResult<Vec<(u128, u32)>> {
        let mut kmers = Vec::with_capacity(self.entries.len());
        for entry in &self.entries {
            kmers.push((entry.kmer, entry.count));
        }
        Ok(kmers)
    }

    /// Create an RKDatabase from k-mer pairs
    pub fn from_kmer_pairs(
        kmer_pairs: Vec<(u128, u32)>,
        kmer_size: u8,
        canonical: bool,
        sorted: bool,
    ) -> crate::error::ProcessingResult<Self> {
        let mut entries: Vec<KmerEntry> = kmer_pairs
            .into_iter()
            .map(|(kmer, count)| KmerEntry::new(kmer, count))
            .collect();

        if sorted && !entries.is_empty() {
            entries.sort_by_key(|entry| entry.kmer);
        }

        let header = DatabaseHeader {
            magic: *crate::database::format::DATABASE_MAGIC,
            version: crate::database::format::DATABASE_VERSION,
            kmer_size,
            total_kmers: entries.len() as u64,
            canonical,
            sorted,
            data_offset: 42, // Standard header size for version 2
            index_offset: 0,
            unique_kmers: entries.len() as u64,
            file_size: 0, // Will be calculated when writing
        };

        Ok(Self {
            header,
            entries,
            file_path: None,
        })
    }

    /// Save database to file path
    pub fn to_file_path(&self, path: &std::path::Path) -> crate::error::ProcessingResult<()> {
        self.write_to_file(path)?;
        Ok(())
    }

    /// Get k-mer size from header
    pub fn kmer_size_u8(&self) -> u8 {
        self.header.kmer_size
    }

    /// Get total k-mers from header
    pub fn total_kmers(&self) -> u64 {
        self.header.total_kmers
    }

    /// Check if database is canonical
    pub fn is_canonical(&self) -> bool {
        self.header.canonical
    }

    /// Merge multiple RKDB databases into a new one
    ///
    /// # Arguments
    /// * `input_paths` - Paths to the input database files
    /// * `config` - Configuration for the merge operation
    ///
    /// # Returns
    /// A new RKDatabase containing the merged k-mers
    ///
    /// # Errors
    /// Returns an error if:
    /// - Any input file cannot be read
    /// - Databases have incompatible k-mer sizes or canonical modes
    /// - Memory is insufficient for the operation
    pub fn validate_compatibility(
        databases: &[&RKDatabase],
    ) -> crate::error::ProcessingResult<(usize, bool)> {
        Self::validate_compatibility_verbose(databases, false)
    }

    /// Validate compatibility with optional verbose reporting
    pub fn validate_compatibility_verbose(
        databases: &[&RKDatabase],
        verbose: bool,
    ) -> crate::error::ProcessingResult<(usize, bool)> {
        if databases.is_empty() {
            return Err(crate::error::ProcessingError::new(
                "At least one database is required for validation",
            ));
        }

        let first_db = &databases[0];
        let kmer_size = first_db.kmer_size();
        let canonical = first_db.is_canonical();

        if verbose {
            log::info!("Validating compatibility for {} databases", databases.len());
            log::info!(
                "  Reference database: k-mer size={}, canonical={}",
                kmer_size,
                canonical
            );
        }

        // Validate all databases have the same k-mer size and canonical mode
        for (i, db) in databases.iter().enumerate().skip(1) {
            if db.kmer_size() != kmer_size {
                let mut msg = format!(
                    "Database {} has k-mer size {}, expected {}",
                    i + 1,
                    db.kmer_size(),
                    kmer_size
                );

                if verbose {
                    msg.push_str(&format!(
                        "\n  Database 1: k-mer size={}, canonical={}, k-mers={}",
                        kmer_size,
                        canonical,
                        first_db.header().total_kmers
                    ));
                    msg.push_str(&format!(
                        "\n  Database {}: k-mer size={}, canonical={}, k-mers={}",
                        i + 1,
                        db.kmer_size(),
                        db.is_canonical(),
                        db.header().total_kmers
                    ));
                    msg.push_str("\n  Hint: All databases must have the same k-mer size to merge");
                }

                return Err(crate::error::ProcessingError::new(msg));
            }
            if db.is_canonical() != canonical {
                let mut msg = format!(
                    "Database {} has canonical mode {}, expected {}",
                    i + 1,
                    db.is_canonical(),
                    canonical
                );

                if verbose {
                    msg.push_str(&format!(
                        "\n  Database 1: k-mer size={}, canonical={}, k-mers={}",
                        kmer_size,
                        canonical,
                        first_db.header().total_kmers
                    ));
                    msg.push_str(&format!(
                        "\n  Database {}: k-mer size={}, canonical={}, k-mers={}",
                        i + 1,
                        db.kmer_size(),
                        db.is_canonical(),
                        db.header().total_kmers
                    ));
                    msg.push_str(
                        "\n  Hint: All databases must have the same canonical mode to merge",
                    );
                    msg.push_str("\n  Canonical mode merges reverse complements together");
                    msg.push_str(
                        "\n  Note: Use --use-prefix-cache for flexible canonical mode merging",
                    );
                }

                return Err(crate::error::ProcessingError::new(msg));
            }

            if verbose {
                log::info!(
                    "  Database {}: compatible (k-mer size={}, canonical={})",
                    i + 1,
                    db.kmer_size(),
                    db.is_canonical()
                );
            }
        }

        if verbose {
            log::info!("All databases are compatible");
        }

        Ok((kmer_size, canonical))
    }

    /// Estimate the number of k-mers an input `.rkdb` holds WITHOUT
    /// materializing any of its entries.
    ///
    /// This is the D-01 fix for the OOM-on-estimate bug. The pre-fix estimator
    /// called `RKDatabase::from_file_path(path)` per input purely to read
    /// `total_kmers` — which loads **every** entry into RAM, so on a
    /// human-scale merge the process exhausted memory *during the estimate*,
    /// before a merge strategy had even been chosen. The function whose whole
    /// job is to prevent OOM was itself the OOM.
    ///
    /// The fix reads the persisted `total_kmers` out of the 42-byte `.rkdb`
    /// header via [`DatabaseHeader::read_from`], which validates the magic
    /// bytes and format version before any field is trusted, and returns
    /// without touching a single `KmerEntry`. Cost is O(42 bytes) per input
    /// instead of O(entries).
    ///
    /// # Fallback
    ///
    /// If the header is unreadable (corrupt magic, unsupported version) **or**
    /// reports `total_kmers == 0` (an untrustworthy/legacy value), fall back to
    /// the file size: `(file_size - HEADER_SIZE) / RECORD_SIZE`. That is a
    /// coarse *upper* bound on the entry count, and over-estimating is the safe
    /// direction — it routes the merge to the streaming path conservatively
    /// rather than admitting an in-memory merge that would OOM (threat
    /// register T-03-01).
    ///
    /// A merely-unreadable header is not itself an error: a corrupt input
    /// still merges through the streaming path, which does its own per-chunk
    /// validation and surfaces the real corruption.
    ///
    /// # What routing the estimator through `read_header_of` changes
    ///
    /// **This is not a pure refactor, and the difference is a behaviour change
    /// worth stating plainly rather than describing as "semantics preserved
    /// exactly".** [`Self::read_header_of`] applies the `data_offset != 42`
    /// rejection that `from_file_path` applies, and this estimator previously
    /// did not. So a file whose header *parses* but carries any other
    /// `data_offset` moves from "header trusted, return its `total_kmers`" to
    /// "fall back to the file-size estimate, with a `log::warn!`".
    ///
    /// That is the **safe** direction, not a regression. `from_file_path`
    /// refuses such a file outright, so the old estimator was the more
    /// permissive of the two: it would trust a `data_offset` that no reader in
    /// the crate accepts, admit a merge on that estimate, and then have the
    /// merge fail on read. The `log::warn!` keeps the fallback visible, so an
    /// operator sees *why* the header was not trusted.
    ///
    /// Everything else is preserved exactly: a readable header with
    /// `total_kmers > 0` is trusted; an unreadable header **or**
    /// `total_kmers == 0` falls back to the file-size estimate with the same
    /// warning text.
    pub fn estimate_total_kmers(path: &std::path::Path) -> crate::error::ProcessingResult<u64> {
        // `.rkdb` v2 on-disk constants — 42-byte header, 20-byte entries.
        // Kept as local consts (not derived from the structs) so the fallback
        // arithmetic cannot silently drift if a struct field is ever added.
        const HEADER_SIZE: u64 = 42;
        const RECORD_SIZE: u64 = 20;

        let header_kmers = Self::read_header_of(path).map(|header| header.total_kmers);

        // On a bad header, over-estimate from the file size and let the merge
        // path surface any real corruption.
        let fallback = |reason: String| -> crate::error::ProcessingResult<u64> {
            let meta = std::fs::metadata(path)
                .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;
            let entries = meta.len().saturating_sub(HEADER_SIZE) / RECORD_SIZE;
            log::warn!(
                "Header unusable for {} ({}); falling back to file-size estimate ({} entries)",
                path.display(),
                reason,
                entries
            );
            Ok(entries)
        };

        match header_kmers {
            Ok(total) if total > 0 => Ok(total),
            // total_kmers == 0: the persisted value is untrustworthy.
            Ok(_) => fallback("total_kmers == 0".to_string()),
            Err(e) => fallback(e.to_string()),
        }
    }

    /// The admission-control estimate for one merge route, in bytes.
    ///
    /// This is the single place a route's per-k-mer cost is turned into a
    /// number. `merge_databases` calls it once, and the result is what the
    /// budget comparison, the D-02 reject message, and the routing log line all
    /// report — the pre-fix code computed the same quantity in two places with
    /// two literals, which is how they drifted apart.
    ///
    /// `route` selects the constant; see [`INMEMORY_BYTES_PER_KMER`] and its
    /// siblings for each value's derivation, and for what this model does and
    /// does not claim. `MergeStrategy::Hybrid` is charged the in-memory
    /// constant because the hybrid strategy starts in-memory and only falls
    /// back, so its first-resort peak is the in-memory one.
    ///
    /// Saturating: a crafted header claiming `u64::MAX` k-mers must produce
    /// `u64::MAX` bytes, never a wrapped small number that would slip under a
    /// budget and admit a merge the estimate was supposed to reject (threat
    /// T-03-32).
    ///
    /// `pub` so an integration test — an external crate — can assert the model
    /// itself, following the 03-01 precedent for `estimate_total_kmers`. It
    /// takes a route and returns a number; it deliberately does **not** return
    /// a strategy from `merge_databases`, which 03-01 declined in favour of
    /// the behavioural `temp_dir` probe. That discipline is unchanged.
    pub fn estimated_bytes_for_route(
        route: crate::database::MergeStrategy,
        total_kmers: u64,
    ) -> u64 {
        let per_kmer = match route {
            crate::database::MergeStrategy::InMemory => INMEMORY_BYTES_PER_KMER,
            crate::database::MergeStrategy::Streaming => STREAMING_BYTES_PER_KMER,
            crate::database::MergeStrategy::PrefixCache => PREFIX_CACHE_BYTES_PER_KMER,
            // Hybrid starts in-memory and only falls back, so its first-resort
            // peak is the in-memory one.
            crate::database::MergeStrategy::Hybrid => INMEMORY_BYTES_PER_KMER,
        };
        total_kmers.saturating_mul(per_kmer)
    }

    /// - Memory is insufficient for the operation
    pub fn merge_databases(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<Self> {
        // WR-06 / threat T-03-35: hoisted to the TOP of the dispatcher.
        // `merge_databases_streaming` indexes `input_paths[0]` unconditionally,
        // so an empty input list panicked with an index-out-of-bounds before
        // any strategy-specific guard could run. One guard here covers all
        // three routes; the per-strategy guards are left in place as defence in
        // depth for any direct private-fn caller (removing them would be an
        // unrequested behaviour change for callers the plan does not own).
        if input_paths.is_empty() {
            return Err(crate::error::ProcessingError::new(
                "At least one input database is required",
            ));
        }

        // D-06 / MERGE-03: reclaim temp shards orphaned by a merge that could
        // not clean up after itself — SIGKILL, `panic = "abort"` (this project's
        // release profile), `process::exit`, power loss. RAII handles the
        // unwind cases; this handles the ones where `Drop` never runs.
        //
        // This is the single sweep call site for the whole merge subsystem, so
        // it covers all three strategies. It is deliberately placed BEFORE any
        // temp shard this merge creates, and is a no-op on a temp_dir that does
        // not exist yet.
        crate::database::temp_lifecycle::sweep_stale_merge_dirs(
            &config.temp_dir,
            crate::database::temp_lifecycle::DEFAULT_MERGE_TEMP_TTL,
        );

        // D-01: header-only estimate. The pre-fix loop called
        // `Self::from_file_path(path)` per input, materializing every entry
        // into RAM just to read `total_kmers` — OOMing during the estimate.
        //
        // The sum SATURATES (threat T-03-32). `.iter().sum()` panics on
        // overflow in a debug build, so two crafted headers each claiming just
        // over `u64::MAX / 2` k-mers would abort an admission gate — the one
        // component that must never be the thing that dies on hostile input.
        // `saturating_add` turns that into a saturated estimate, which the
        // budget comparison then correctly treats as over budget.
        let total_kmers = input_paths
            .iter()
            .map(|path| Self::estimate_total_kmers(path))
            .collect::<crate::error::ProcessingResult<Vec<_>>>()?
            .into_iter()
            .fold(0u64, |total, count| total.saturating_add(count));

        // WR-01: charge the route its real peak. This was a bare
        // 24-bytes-per-k-mer multiply with no derivation, modelling roughly a
        // quarter of what the in-memory route actually holds, so a merge the
        // gate admitted could still exhaust memory.
        let estimated_memory =
            Self::estimated_bytes_for_route(crate::database::MergeStrategy::InMemory, total_kmers);

        // Use prefix cache merge if enabled
        if config.use_prefix_cache {
            if config.verbose {
                log::info!(
                    "DEBUG: Using prefix cache merge for {} k-mers (estimated {} bytes)",
                    total_kmers,
                    estimated_memory
                );
            }
            return Self::merge_databases_prefix_cache(input_paths, config);
        }

        let over_budget = estimated_memory > config.max_memory_usage as u64;

        // D-02: an explicit `--merge-mode memory` that cannot fit the budget is
        // REJECTED with an actionable error rather than attempted and left to
        // OOM the process (MERGE-01's "no longer OOM" promise). The in-memory
        // path itself is retained — this only bounds when it may run.
        if config.merge_mode == "memory" && over_budget {
            return Err(crate::error::ProcessingError::new(format!(
                "merge_mode='memory' rejected: estimated memory ({} bytes for {} k-mers) exceeds \
                 max_memory ({} bytes); use merge_mode='streaming' (or 'auto') to merge within \
                 the memory budget",
                estimated_memory, total_kmers, config.max_memory_usage
            )));
        }

        // D-01: an explicit `--merge-mode streaming` always streams,
        // regardless of the estimate.
        let use_streaming = if config.merge_mode == "streaming" {
            if config.verbose {
                log::info!(
                    "DEBUG: Using streaming merge (explicit merge_mode='streaming') for {} k-mers (estimated {} bytes)",
                    total_kmers,
                    estimated_memory
                );
            }
            true
        } else {
            // D-01 hard route (MERGE-02): over budget under 'auto' (or any
            // other unrecognised mode, which is treated as 'auto') routes
            // unconditionally to streaming — no warn-and-continue in-memory
            // fallback. Within budget the existing selection is preserved,
            // which keeps the small-input in-memory fast path (D-02).
            let stream = Self::should_use_streaming(estimated_memory, config);
            if stream {
                // The first sentence is unchanged so any log-scraping consumer
                // (and the existing tests) keep working. The per-route figures
                // are appended because an operator who was just told "you got
                // streaming" also wants to know what that route costs and what
                // the in-memory route would have cost.
                log::info!(
                    "Routing to streaming merge: estimated {} bytes ({} k-mers) exceeds memory budget {} bytes \
                     (in-memory {} B/k-mer, streaming {} B/k-mer, prefix-cache {} B/k-mer)",
                    estimated_memory,
                    total_kmers,
                    config.max_memory_usage,
                    INMEMORY_BYTES_PER_KMER,
                    STREAMING_BYTES_PER_KMER,
                    PREFIX_CACHE_BYTES_PER_KMER
                );
            }
            stream
        };

        if use_streaming {
            if config.verbose {
                log::info!(
                    "DEBUG: Using streaming merge for {} k-mers (estimated {} bytes)",
                    total_kmers,
                    estimated_memory
                );
            }
            Self::merge_databases_streaming(input_paths, config)
        } else {
            if config.verbose {
                log::info!(
                    "DEBUG: Using in-memory merge for {} k-mers (estimated {} bytes)",
                    total_kmers,
                    estimated_memory
                );
            }
            Self::merge_databases_inmemory(input_paths, config)
        }
    }

    /// Admission-control predicate for the default (`auto`) merge mode.
    ///
    /// WR-01: this used to RE-DERIVE the estimate — reading each input's
    /// 42-byte header itself and multiplying by a second copy of the
    /// per-k-mer constant. Two sites computing the same quantity with two
    /// literals is exactly how they drifted, so the estimate is now computed
    /// once in [`Self::merge_databases`] and HANDED to this predicate, which is
    /// a pure comparison over a value it is given. The header reads are not
    /// lost: they still happen, in `merge_databases`, just once.
    fn should_use_streaming(estimated_memory: u64, config: &crate::database::MergeConfig) -> bool {
        estimated_memory > config.max_memory_usage as u64
    }

    fn merge_databases_streaming(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<Self> {
        use crate::database::format::RKDatabase;
        use crate::database::streaming_merge::ExternalMerger;
        use std::time::Instant;

        if config.verbose {
            log::info!("Using streaming merge for large datasets");
        }

        let start_time = Instant::now();

        // G2a / threat T-03-31: this is the OVER-BUDGET path — the one chosen
        // precisely because the inputs do not fit — and it used to
        // `from_file_path(&input_paths[0])` (materializing a whole input
        // database into RAM) purely to read `kmer_size` and `canonical`, two
        // fields of a 42-byte header. A 42-byte read is all that is needed.
        let header = RKDatabase::read_header_of(&input_paths[0])?;
        let kmer_size = header.kmer_size;
        let canonical = header.canonical;

        let mut merger = ExternalMerger::new(config.chunk_size, config.temp_dir.clone());

        for path in input_paths {
            if config.verbose {
                log::info!("Sorting database: {}", path.display());
            }
            merger.sort_database(path)?;
        }

        if config.verbose {
            log::info!("Merging sorted chunks...");
        }

        let merge_iter = merger.merge_sorted_chunks()?;
        let mut sorted_kmers: Vec<(u128, u32)> = Vec::new();

        for result in merge_iter {
            match result {
                Ok((kmer, count)) => sorted_kmers.push((kmer, count)),
                Err(e) => return Err(e),
            }
        }

        if config.verbose {
            let stats = merger.stats();
            log::info!("Streaming merge stats:");
            log::info!("  Total k-mers read: {}", stats.total_kmers_read);
            log::info!("  Chunks created: {}", stats.chunks_created);
            log::info!("  Read time: {:?}", stats.read_time);
            log::info!("  Sort time: {:?}", stats.sort_time);
            log::info!("  Merge time: {:?}", stats.merge_time);
            log::info!("  Write time: {:?}", stats.write_time);
            log::info!("  Total time: {:?}", start_time.elapsed());
        }

        Self::from_kmer_pairs(sorted_kmers, kmer_size, canonical, true)
    }

    fn merge_databases_inmemory(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<Self> {
        use hashbrown::hash_map::DefaultHashBuilder;
        use hashbrown::HashMap as HashMapBrown;
        use indicatif::{ProgressBar, ProgressStyle};
        use std::time::Instant;

        let _start_time = Instant::now();

        if input_paths.is_empty() {
            return Err(crate::error::ProcessingError::new(
                "At least one input database is required",
            ));
        }

        // Use hashbrown with AHasher for better performance
        type KmerMap = HashMapBrown<u128, u32, DefaultHashBuilder>;
        let mut all_kmers: KmerMap = KmerMap::default();

        // Variables are assigned now and used later - suppress false positive warnings
        #[allow(unused_assignments)]
        let mut kmer_size = None;
        #[allow(unused_assignments)]
        let mut canonical = None;
        let mut sorted = true;
        let mut _total_input_kmers = 0u64;

        // Create progress bar for loading databases
        let progress = if config.verbose && input_paths.len() > 1 {
            Some(ProgressBar::new(input_paths.len() as u64))
        } else {
            None
        };

        if let Some(ref pb) = progress {
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg}")
                    .unwrap()
                    .progress_chars("#>-")
            );
            pb.set_message("Loading databases...");
        }

        // Load all databases first
        let mut databases = Vec::with_capacity(input_paths.len());
        for path in input_paths {
            let db = Self::from_file_path(path)?;
            databases.push(db);
        }

        // Validate compatibility across all databases with verbose output if enabled
        let (kmer_size_val, canonical_val) = Self::validate_compatibility_verbose(
            &databases.iter().collect::<Vec<_>>(),
            config.verbose,
        )?;

        // Set the validated values
        kmer_size = Some(kmer_size_val);
        canonical = Some(canonical_val);

        // Now merge k-mers from all databases
        for (i, db) in databases.iter().enumerate() {
            // Get all k-mers from this database
            let db_kmers = db.all_kmers()?;

            // Merge k-mers with overflow protection
            for (kmer, count) in db_kmers {
                let entry = all_kmers.entry(kmer).or_insert(0);
                *entry = (*entry).saturating_add(count);
                _total_input_kmers += count as u64;
            }

            sorted = sorted && db.header().sorted;

            // Update progress
            if let Some(ref pb) = progress {
                let msg = format!("Loaded database {} ({})", i + 1, input_paths[i].display());
                pb.set_message(msg);
                pb.inc(1);
            }
        }

        if let Some(ref pb) = progress {
            pb.finish_with_message("All databases loaded");
        }

        // Create merged database
        let kmer_size = kmer_size.unwrap();
        let canonical = canonical.unwrap();

        // Progress for sorting phase
        let sort_progress = if config.verbose && all_kmers.len() > 10000 {
            let pb = ProgressBar::new(all_kmers.len() as u64);
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("{spinner:.green} [{elapsed_precise}] [{bar:40.red/yellow}] {pos}/{len} ({eta}) {msg}")
                    .unwrap()
                    .progress_chars("#>-")
            );
            pb.set_message("Sorting k-mers...");
            Some(pb)
        } else {
            None
        };

        // Convert to sorted vector with progress tracking
        let mut sorted_kmers: Vec<(u128, u32)> = Vec::with_capacity(all_kmers.len());

        if let Some(ref pb) = sort_progress {
            for (i, (kmer, count)) in all_kmers.into_iter().enumerate() {
                sorted_kmers.push((kmer, count));
                if i % 10000 == 0 {
                    pb.set_position(i as u64);
                }
            }
            pb.finish_with_message("Sorting...");
        } else {
            sorted_kmers = all_kmers.into_iter().collect();
        }

        // Sort the vector
        if let Some(ref pb) = sort_progress {
            pb.set_message("Sorting k-mers...");
        }
        sorted_kmers.sort_by_key(|(kmer, _)| *kmer);

        if let Some(ref pb) = sort_progress {
            pb.finish_with_message("Sorting complete");
        }

        // Create database
        Self::from_kmer_pairs(sorted_kmers, kmer_size as u8, canonical, sorted)
    }

    /// Prefix cache merge implementation (memory-efficient with error isolation)
    fn merge_databases_prefix_cache(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<Self> {
        use crate::database::prefix_cache_merge::ExternalSortMerger;
        use std::time::Instant;

        let start_time = Instant::now();

        if input_paths.is_empty() {
            return Err(crate::error::ProcessingError::new(
                "At least one input database is required",
            ));
        }

        // Validate compatibility.
        //
        // G2a: this used to hold every input as a live `RKDatabase` in
        // `db_refs`, so the resident set was every input database, held all the
        // way through the final `from_file_path(&temp_output)` read — peak =
        // all inputs PLUS the full merged output. Compatibility validation only
        // needs three header fields, so the resident set is now
        // `Vec<DatabaseHeader>` (~42 bytes per input).
        let mut headers = Vec::with_capacity(input_paths.len());
        for path in input_paths {
            headers.push(Self::read_header_of(path)?);
        }

        // Create external sort merger
        let merge_buffer_mb = config.max_memory_usage / 1024 / 1024; // Convert bytes to MB
        if merge_buffer_mb < PREFIX_CACHE_MIN_BUFFER_MB {
            log::info!(
                "Prefix-cache per-bucket buffer raised from {} MB to the {} MB floor \
                 (set by the user's max_memory budget)",
                merge_buffer_mb,
                PREFIX_CACHE_MIN_BUFFER_MB
            );
        }

        // Validate for external sort merge (allow mixed canonical modes)
        let (_kmer_size, _final_canonical) =
            Self::validate_header_compatibility(&headers, config.verbose)?;

        let mut merger = ExternalSortMerger::new(
            input_paths.to_vec(),
            config.temp_dir.clone(),
            PREFIX_CACHE_MIN_BUFFER_MB.max(merge_buffer_mb),
            config.num_threads,
            config.merge_mode.clone(),
            config.keep_intermediate,
        )?;

        // The intermediate result goes INSIDE the merger's own process-unique
        // `rustkmer-merge-<rand>/` subdir, not loose in the shared
        // `config.temp_dir`. Two consequences, both of which close a recorded
        // deferred item:
        //
        //   1. The `TempDir`'s `Drop` now reclaims the intermediate result
        //      together with every shard. It used to be written to the shared
        //      temp dir under a FIXED name and never removed, so a
        //      dataset-sized file survived the merge that produced it — the
        //      disk-exhaustion half of MERGE-03 that `deferred-items.md`
        //      recorded as open.
        //   2. The fixed basename meant two concurrent prefix-cache merges
        //      sharing a `temp_dir` overwrote each other's output — threat
        //      T-03-06's class, and the reason the shards moved under a
        //      process-unique subdir in the first place.
        //
        // The `None` arm is the degenerate case where `Drop` already took the
        // `TempDir` (only possible once `keep_intermediate` is being honoured
        // during drop, i.e. after the merge finished). Falling back keeps the
        // merge working rather than panicking on an impossible state.
        let temp_output = match merger.merge_temp_subdir_path() {
            Some(dir) => dir.join("external_sort_merge_output.tmp"),
            None => config.temp_dir.join("external_sort_merge_output.tmp"),
        };
        merger.external_sort_merge(&temp_output)?;

        let _elapsed = start_time.elapsed();

        // Read the merged result
        let result_db = Self::from_file_path(&temp_output)?;

        Ok(result_db)
    }

    /// The external-sort compatibility rules, over headers rather than
    /// materialized databases.
    ///
    /// This function USED to be `validate_compatibility_external_sort(&[&Self],
    /// bool)` and it held the whole rule set inline. Splitting it this way is
    /// what lets the prefix-cache route validate a merge it has not loaded.
    /// The error strings are byte-identical to the pre-split version because
    /// `tests/merge_routing_tests.rs` and the PyO3 docstring both quote them.
    ///
    /// There is exactly ONE implementation of these rules. The database-taking
    /// form was removed rather than kept as an adapter: after this change it
    /// had no remaining caller, and a `#[allow(dead_code)]` shim retained
    /// "just in case" would be a second thing to keep correct for the next
    /// reader to mistake for a live path.
    fn validate_header_compatibility(
        headers: &[DatabaseHeader],
        verbose: bool,
    ) -> crate::error::ProcessingResult<(u8, bool)> {
        let first_header = &headers[0];
        let kmer_size = first_header.kmer_size;
        let canonical = first_header.canonical;

        if verbose {
            log::info!("Validating databases for external sort merge...");
        }

        let mut has_canonical = false;
        let mut has_non_canonical = false;

        for (i, header) in headers.iter().enumerate() {
            if header.kmer_size != kmer_size {
                let mut msg = format!(
                    "Database {} has k-mer size {}, expected {}",
                    i + 1,
                    header.kmer_size,
                    kmer_size
                );

                if verbose {
                    msg.push_str(&format!(
                        "\n  Database 1: k-mer size={}, canonical={}, k-mers={}",
                        kmer_size, canonical, first_header.total_kmers
                    ));
                    msg.push_str(&format!(
                        "\n  Database {}: k-mer size={}, canonical={}, k-mers={}",
                        i + 1,
                        header.kmer_size,
                        header.canonical,
                        header.total_kmers
                    ));
                    msg.push_str("\n  Hint: All databases must have the same k-mer size to merge");
                }

                return Err(crate::error::ProcessingError::new(msg));
            }

            if header.canonical {
                has_canonical = true;
            } else {
                has_non_canonical = true;
            }

            if verbose {
                log::info!(
                    "  Database {}: compatible (k-mer size={}, canonical={})",
                    i + 1,
                    header.kmer_size,
                    header.canonical
                );
            }
        }

        let final_canonical = has_canonical;

        if verbose {
            if has_canonical && has_non_canonical {
                log::info!("  Mixed canonical modes detected - converting all to canonical mode");
            }
            log::info!("  Final merge mode: canonical={}", final_canonical);
        }

        Ok((kmer_size, final_canonical))
    }
}

#[cfg(test)]
mod tests {
    use super::super::memory::{constraints, MemoryMonitor};
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_merge_memory_basic() {
        // Create test databases
        let db1 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 10), (0x5678, 20), (0x9ABC, 30)],
            31,
            false,
            true,
        )
        .unwrap();

        let db2 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 5), (0xDEF0, 15), (0x9ABC, 25)],
            31,
            false,
            true,
        )
        .unwrap();

        // Create temporary files
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");

        // Save databases
        db1.to_file_path(&db1_path).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        // Monitor memory usage
        let mut monitor = MemoryMonitor::new();

        // Configure merge with memory constraints
        let config = crate::database::MergeConfig {
            max_memory_usage: constraints::SMALL.max_usage,
            chunk_size: 100,
            temp_dir: temp_dir.path().to_path_buf(),
            use_streaming: false,
            use_prefix_cache: false,
            num_threads: 0,
            merge_mode: "auto".to_string(),
            keep_intermediate: false,
            verbose: false,
        };

        // Perform merge
        let merged_db = RKDatabase::merge_databases(&[db1_path, db2_path], &config)
            .expect("Merge should succeed");

        // Record final memory usage
        monitor.record_reading();

        // Validate merge results
        let all_kmers = merged_db.all_kmers().expect("Failed to get merged k-mers");
        assert!(!all_kmers.is_empty(), "Merged database should have k-mers");

        // Check specific k-mers were merged correctly
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();
        assert_eq!(kmer_map.get(&0x1234), Some(&15)); // 10 + 5
        assert_eq!(kmer_map.get(&0x5678), Some(&20));
        assert_eq!(kmer_map.get(&0x9ABC), Some(&55)); // 30 + 25
        assert_eq!(kmer_map.get(&0xDEF0), Some(&15));

        // Basic memory sanity check
        assert!(
            monitor.peak_usage() < constraints::SMALL.max_usage,
            "Memory usage should be within small constraint"
        );
    }

    #[test]
    fn test_merge_streaming_basic() {
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");

        let db1 = RKDatabase::from_kmer_pairs(
            vec![(0x0010, 10), (0x0020, 20), (0x0030, 30)],
            31,
            false,
            true,
        )
        .unwrap();

        let db2 = RKDatabase::from_kmer_pairs(
            vec![(0x0010, 5), (0x0040, 15), (0x0030, 25)],
            31,
            false,
            true,
        )
        .unwrap();

        db1.to_file_path(&db1_path).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        let config = crate::database::MergeConfig {
            max_memory_usage: 1024,
            chunk_size: 2,
            temp_dir: temp_dir.path().to_path_buf(),
            use_streaming: true,
            use_prefix_cache: false,
            num_threads: 0,
            merge_mode: "auto".to_string(),
            keep_intermediate: false,
            verbose: false,
        };

        let merged_db = RKDatabase::merge_databases(&[db1_path, db2_path], &config)
            .expect("Streaming merge should succeed");

        let all_kmers = merged_db.all_kmers().unwrap();
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();

        assert_eq!(kmer_map.get(&0x0010), Some(&15));
        assert_eq!(kmer_map.get(&0x0020), Some(&20));
        assert_eq!(kmer_map.get(&0x0030), Some(&55));
        assert_eq!(kmer_map.get(&0x0040), Some(&15));
    }

    #[test]
    fn test_database_header_serialization() {
        let header = DatabaseHeader::new(21, 1000000, true);

        let mut buffer = Vec::new();
        header.write_to(&mut buffer).unwrap();

        let mut reader = std::io::Cursor::new(buffer);
        let loaded_header = DatabaseHeader::read_from(&mut reader).unwrap();

        assert_eq!(header.kmer_size, loaded_header.kmer_size);
        assert_eq!(header.total_kmers, loaded_header.total_kmers);
        assert_eq!(header.canonical, loaded_header.canonical);
    }

    #[test]
    fn test_kmer_entry_serialization() {
        let entry = KmerEntry::new(0x0123456789ABCDEF0123456789ABCDEF0, 42);

        let mut buffer = Vec::new();
        entry.write_to(&mut buffer).unwrap();

        let mut reader = std::io::Cursor::new(buffer);
        let loaded_entry = KmerEntry::read_from(&mut reader).unwrap();

        assert_eq!(entry.kmer, loaded_entry.kmer);
        assert_eq!(entry.count, loaded_entry.count);
    }

    /// CR-01 / G3: the count field must round-trip EXACTLY at and above the
    /// threshold the pre-fix reader used to treat as "this must be big-endian".
    ///
    /// `write_to` always emits `write_u32::<LittleEndian>`. The pre-fix
    /// `read_from` applied an endianness heuristic — "if the little-endian read
    /// gives a count above one million, use the big-endian reading instead" —
    /// so every valid count above that threshold came back byte-swapped:
    /// `2_000_000` read back as `2_156_142_080` and `16_777_216` as `1`.
    ///
    /// This test is the DISCRIMINATING gate for the heuristic's deletion. A
    /// source grep cannot do the job: `u32::from_le_bytes` was already
    /// present inside the heuristic being deleted, so its count is unchanged by
    /// the fix and inert as evidence.
    #[test]
    fn kmer_entry_round_trips_counts_above_the_old_threshold() {
        for count in [999_999u32, 1_000_000, 1_000_001, 2_000_000, 16_777_216] {
            let entry = KmerEntry::new(0x1, count);

            let mut buffer = Vec::new();
            entry.write_to(&mut buffer).unwrap();

            let mut reader = std::io::Cursor::new(buffer);
            let loaded = KmerEntry::read_from(&mut reader).unwrap();

            assert_eq!(
                loaded.count, count,
                "count {} round-tripped as {} — the count field is being read with \
                 the wrong byte order",
                count, loaded.count
            );
            assert_eq!(loaded.kmer, entry.kmer);
        }
    }

    #[test]
    fn test_database_header_validation() {
        let mut header = DatabaseHeader::new(21, 1000, true);
        assert!(header.validate().is_ok());

        header.kmer_size = 0;
        assert!(header.validate().is_err());

        header.kmer_size = 128;
        assert!(header.validate().is_err());
    }

    mod validate_compatibility_tests {
        use super::*;

        #[test]
        fn test_validate_compatibility_empty() {
            let result = RKDatabase::validate_compatibility(&[]);
            assert!(result.is_err());
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("At least one database is required"));
        }

        #[test]
        fn test_validate_compatibility_single() {
            let db = RKDatabase::from_kmer_pairs(vec![(0x1234, 10)], 31, false, true).unwrap();

            let result = RKDatabase::validate_compatibility(&[&db]);
            assert!(result.is_ok());
            let (kmer_size, canonical) = result.unwrap();
            assert_eq!(kmer_size, 31);
            assert!(!canonical);
        }

        #[test]
        fn test_validate_compatibility_matching() {
            let db1 = RKDatabase::from_kmer_pairs(vec![(0x1234, 10)], 31, false, true).unwrap();

            let db2 = RKDatabase::from_kmer_pairs(vec![(0x5678, 20)], 31, false, true).unwrap();

            let result = RKDatabase::validate_compatibility(&[&db1, &db2]);
            assert!(result.is_ok());
            let (kmer_size, canonical) = result.unwrap();
            assert_eq!(kmer_size, 31);
            assert!(!canonical);
        }

        #[test]
        fn test_validate_compatibility_kmer_size_mismatch() {
            let db1 = RKDatabase::from_kmer_pairs(vec![(0x1234, 10)], 31, false, true).unwrap();

            let db2 = RKDatabase::from_kmer_pairs(
                vec![(0x5678, 20)],
                51, // Different k-mer size
                false,
                true,
            )
            .unwrap();

            let result = RKDatabase::validate_compatibility(&[&db1, &db2]);
            assert!(result.is_err());
            let error_msg = result.unwrap_err().to_string();
            assert!(error_msg.contains("k-mer size"));
            assert!(error_msg.contains("31"));
            assert!(error_msg.contains("51"));
        }

        #[test]
        fn test_validate_compatibility_canonical_mismatch() {
            let db1 = RKDatabase::from_kmer_pairs(
                vec![(0x1234, 10)],
                31,
                true, // canonical
                true,
            )
            .unwrap();

            let db2 = RKDatabase::from_kmer_pairs(
                vec![(0x5678, 20)],
                31,
                false, // non-canonical
                true,
            )
            .unwrap();

            let result = RKDatabase::validate_compatibility(&[&db1, &db2]);
            assert!(result.is_err());
            let error_msg = result.unwrap_err().to_string();
            assert!(error_msg.contains("canonical mode"));
            assert!(error_msg.contains("true"));
            assert!(error_msg.contains("false"));
        }

        #[test]
        fn test_validate_compatibility_multiple_mismatch() {
            let db1 = RKDatabase::from_kmer_pairs(vec![(0x1234, 10)], 31, true, true).unwrap();

            let db2 = RKDatabase::from_kmer_pairs(
                vec![(0x5678, 20)],
                51, // Different k-mer size
                true,
                true,
            )
            .unwrap();

            let db3 = RKDatabase::from_kmer_pairs(
                vec![(0x9ABC, 30)],
                31,
                false, // Different canonical mode
                true,
            )
            .unwrap();

            // Should fail on k-mer size mismatch first (database 2)
            let result = RKDatabase::validate_compatibility(&[&db1, &db2, &db3]);
            assert!(result.is_err());
            let error_msg = result.unwrap_err().to_string();
            assert!(error_msg.contains("k-mer size"));
        }

        #[test]
        fn test_validate_compatibility_all_compatible() {
            let dbs: Vec<RKDatabase> = vec![
                RKDatabase::from_kmer_pairs(vec![(0x1234, 10)], 31, true, true).unwrap(),
                RKDatabase::from_kmer_pairs(vec![(0x5678, 20)], 31, true, true).unwrap(),
                RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30)], 31, true, true).unwrap(),
                RKDatabase::from_kmer_pairs(vec![(0xDEF0, 40)], 31, true, true).unwrap(),
            ];

            let db_refs: Vec<&RKDatabase> = dbs.iter().collect();
            let result = RKDatabase::validate_compatibility(&db_refs);
            assert!(result.is_ok());
            let (kmer_size, canonical) = result.unwrap();
            assert_eq!(kmer_size, 31);
            assert!(canonical);
        }
    }

    /// D-01 / MERGE-02 admission-control unit tests.
    ///
    /// The routing logic is size-independent (`sum(total_kmers) * per_kmer >
    /// max_memory_usage`), so it is proven here at toy scale rather than at
    /// human scale, and the header-only property is proven structurally: a
    /// file whose header promises far more entries than its body holds can
    /// still be estimated, which a materializing reader could never do.
    mod merge_admission_control {
        use super::*;
        use std::fs::File;
        use std::io::{Seek, SeekFrom, Write};
        use std::path::PathBuf;

        /// `.rkdb` v2 header: total_kmers is the u64 at byte offset 10.
        const TOTAL_KMERS_OFFSET: u64 = 10;
        const HEADER_SIZE: u64 = 42;
        const RECORD_SIZE: u64 = 20;

        fn write_db(dir: &std::path::Path, name: &str, n: u64) -> PathBuf {
            let kmers: Vec<(u128, u32)> =
                (0..n).map(|i| ((i as u128) << 1, (i as u32) + 1)).collect();
            let db = RKDatabase::from_kmer_pairs(kmers, 31, true, true).unwrap();
            let path = dir.join(name);
            db.to_file_path(&path).unwrap();
            path
        }

        /// Overwrite the header's `total_kmers` and truncate the body away.
        fn truncate_body(dir: &std::path::Path, name: &str, n: u64, declared: u64) -> PathBuf {
            let path = write_db(dir, name, n);
            let mut f = File::options().read(true).write(true).open(&path).unwrap();
            f.seek(SeekFrom::Start(TOTAL_KMERS_OFFSET)).unwrap();
            f.write_all(&declared.to_le_bytes()).unwrap();
            f.set_len(HEADER_SIZE).unwrap();
            f.flush().unwrap();
            path
        }

        /// The estimator reads the persisted header value without touching the
        /// body — the D-01 fix, asserted directly.
        #[test]
        fn estimate_total_kmers_reads_header_only() {
            let dir = tempdir().unwrap();

            // 5 billion declared k-mers over an empty body: materializing this
            // would need ~100 GB of RAM, reading the header needs 42 bytes.
            let path = truncate_body(dir.path(), "truncated.rkdb", 8, 5_000_000_000);
            let estimated = RKDatabase::estimate_total_kmers(&path).unwrap();
            assert_eq!(estimated, 5_000_000_000);

            // A well-formed file returns exactly its own entry count.
            let ok = write_db(dir.path(), "ok.rkdb", 37);
            assert_eq!(RKDatabase::estimate_total_kmers(&ok).unwrap(), 37);
        }

        /// `total_kmers == 0` is untrustworthy; the estimate must come from the
        /// file size and must not under-estimate.
        #[test]
        fn estimate_total_kmers_falls_back_to_file_size() {
            let dir = tempdir().unwrap();
            let path = truncate_body(dir.path(), "zeroed.rkdb", 25, 0);
            let len = std::fs::metadata(&path).unwrap().len();
            let expected = len.saturating_sub(HEADER_SIZE) / RECORD_SIZE;
            assert_eq!(RKDatabase::estimate_total_kmers(&path).unwrap(), expected);
        }

        /// A corrupt header must not hard-fail the merge: the estimator
        /// over-estimates from the file size so the merge routes conservatively
        /// (threat register T-03-01).
        #[test]
        fn estimate_total_kmers_tolerates_corrupt_header() {
            let dir = tempdir().unwrap();
            let path = write_db(dir.path(), "corrupt.rkdb", 10);
            {
                let mut f = File::options().write(true).open(&path).unwrap();
                f.seek(SeekFrom::Start(0)).unwrap();
                f.write_all(b"XXXX").unwrap();
                f.flush().unwrap();
            }
            let len = std::fs::metadata(&path).unwrap().len();
            assert_eq!(
                RKDatabase::estimate_total_kmers(&path).unwrap(),
                len.saturating_sub(HEADER_SIZE) / RECORD_SIZE
            );
        }

        /// The admission predicate flips exactly at the budget boundary, and
        /// does so from header metadata alone.
        ///
        /// Named `should_use_streaming` so the plan's
        /// `cargo test --lib -- --exact should_use_streaming` verification
        /// command actually selects it.
        ///
        /// WR-01: `should_use_streaming` no longer derives the estimate itself
        /// — `merge_databases` owns the single number and hands it over. This
        /// test therefore re-derives it the way production does, from the
        /// 42-byte headers, so the header-only property it used to cover
        /// directly is still covered.
        #[test]
        fn should_use_streaming() {
            let dir = tempdir().unwrap();
            let a = write_db(dir.path(), "a.rkdb", 100);
            let b = write_db(dir.path(), "b.rkdb", 100);
            let paths = [a, b];

            let total: u64 = paths
                .iter()
                .map(|p| RKDatabase::estimate_total_kmers(p).unwrap())
                .sum();
            assert_eq!(
                total, 200,
                "premise: the two headers carry 100 records each"
            );
            // 200 k-mers * 96 B/k-mer = 19200 bytes estimated.
            let estimated = RKDatabase::estimated_bytes_for_route(
                crate::database::MergeStrategy::InMemory,
                total,
            );
            assert_eq!(estimated, 19_200);

            let tight = crate::database::MergeConfig {
                max_memory_usage: 1024,
                ..Default::default()
            };
            assert!(
                RKDatabase::should_use_streaming(estimated, &tight),
                "19200 bytes must exceed a 1024-byte budget"
            );

            let loose = crate::database::MergeConfig {
                max_memory_usage: 1_000_000,
                ..Default::default()
            };
            assert!(
                !RKDatabase::should_use_streaming(estimated, &loose),
                "19200 bytes must fit a 1 MB budget"
            );

            // A header promising 5 billion k-mers over an empty body still
            // yields a verdict — the pre-fix estimator would have tried to
            // materialize those entries and died here.
            let bomb = truncate_body(dir.path(), "bomb.rkdb", 4, 5_000_000_000);
            let bomb_estimated = RKDatabase::estimated_bytes_for_route(
                crate::database::MergeStrategy::InMemory,
                RKDatabase::estimate_total_kmers(&bomb).unwrap(),
            );
            assert!(
                RKDatabase::should_use_streaming(bomb_estimated, &loose),
                "a 5e9 k-mer header must be admitted as over budget without materializing"
            );
        }

        /// WR-01 / threat T-03-32 — the `total_kmers` sum SATURATES.
        ///
        /// This is the one test in the plan that is red in a DEBUG build before
        /// the fix: `.iter().sum::<u64>()` on two headers each claiming more
        /// than `u64::MAX / 2` k-mers panics with "attempt to add with
        /// overflow". An admission gate that aborts on a crafted header is the
        /// worst possible place to panic — it is the component whose entire job
        /// is to survive hostile input.
        ///
        /// The test drives the real public entry point rather than the fold, so
        /// it also proves the saturated figure reaches the D-02 message rather
        /// than being recomputed correctly somewhere and lost in between.
        #[test]
        fn summing_two_near_max_headers_saturates_instead_of_panicking() {
            let dir = tempdir().unwrap();
            // 2^63 each; the pair sums to 2^64, i.e. one past u64::MAX.
            let bomb = u64::MAX / 2 + 1;
            let a = truncate_body(dir.path(), "near_max_a.rkdb", 4, bomb);
            let b = truncate_body(dir.path(), "near_max_b.rkdb", 4, bomb);

            // Premise: both headers really do claim that, read header-only.
            assert_eq!(RKDatabase::estimate_total_kmers(&a).unwrap(), bomb);
            assert_eq!(RKDatabase::estimate_total_kmers(&b).unwrap(), bomb);

            let config = crate::database::MergeConfig {
                // Generous, and still far below the saturated estimate.
                max_memory_usage: 1_000_000_000_000,
                merge_mode: "memory".to_string(),
                temp_dir: dir.path().to_path_buf(),
                ..Default::default()
            };

            // The call must RETURN, not abort. Pre-fix this panicked inside the
            // `.iter().sum()` fold on the first addition that overflowed.
            let result = RKDatabase::merge_databases(&[a, b], &config);

            match result {
                Ok(_) => panic!(
                    "a saturated estimate of {bomb} k-mers must exceed a 1 TB budget, so the \
                     merge cannot have succeeded"
                ),
                Err(e) => {
                    let msg = e.to_string();
                    assert!(
                        msg.contains(&u64::MAX.to_string()),
                        "the rejection must name the SATURATED byte figure ({}), not a wrapped \
                         one; got: {}",
                        u64::MAX,
                        msg
                    );
                    assert!(
                        msg.contains("merge_mode='memory' rejected"),
                        "the rejection must be the D-02 over-budget reject; got: {}",
                        msg
                    );
                }
            }
        }

        /// D-02: explicit `merge_mode = "memory"` over budget is rejected with
        /// an actionable message instead of being attempted in-memory.
        #[test]
        fn memory_mode_over_budget_is_rejected() {
            let dir = tempdir().unwrap();
            let a = write_db(dir.path(), "a.rkdb", 100);
            let b = write_db(dir.path(), "b.rkdb", 100);

            let config = crate::database::MergeConfig {
                max_memory_usage: 1024,
                merge_mode: "memory".to_string(),
                temp_dir: dir.path().to_path_buf(),
                ..Default::default()
            };
            let err = RKDatabase::merge_databases(&[a.clone(), b.clone()], &config).unwrap_err();
            let msg = err.to_string();
            assert!(
                msg.contains("memory"),
                "message must name the mode: {}",
                msg
            );
            assert!(
                msg.contains("streaming"),
                "message must point at the streaming mode: {}",
                msg
            );

            // Within budget the same explicit mode still merges.
            let ok_config = crate::database::MergeConfig {
                max_memory_usage: 1_000_000,
                ..config.clone()
            };
            let merged = RKDatabase::merge_databases(&[a, b], &ok_config).unwrap();
            // Both inputs carry the SAME 100 k-mers, so the union is 100
            // unique k-mers with summed counts (200 total input observations).
            assert_eq!(merged.total_kmers(), 100);
            // Input k-mer i carries count `i + 1` in BOTH files, so the merged
            // count is exactly `2 * (i + 1)`.
            let merged_kmers: std::collections::HashMap<u128, u32> =
                merged.all_kmers().unwrap().into_iter().collect();
            for i in 0..100u128 {
                assert_eq!(
                    merged_kmers.get(&(i << 1)).copied(),
                    Some(2 * (i as u32 + 1)),
                    "k-mer {} must carry the summed count of both inputs",
                    i
                );
            }
        }
    }
}
