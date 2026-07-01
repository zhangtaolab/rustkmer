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

/// Database file header containing metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseHeader {
    /// Magic number for file identification
    pub magic: [u8; 4],
    /// Format version
    pub version: u16,
    /// K-mer size (1-127)
    pub kmer_size: u8,
    /// Total number of unique k-mers
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
    pub fn read_from<R: Read>(reader: &mut R) -> IoResult<Self> {
        let kmer = reader.read_u128::<LittleEndian>()?;

        // Fix for endianness issue: count might be written as big-endian
        let count_bytes = {
            let mut buf = [0u8; 4];
            reader.read_exact(&mut buf)?;
            buf
        };

        // Try little-endian first, if it gives a huge number, try big-endian
        let count_le = u32::from_le_bytes(count_bytes);
        let count_be = u32::from_be_bytes(count_bytes);

        // If little-endian gives an unreasonable count (> 1M), use big-endian
        let count = if count_le > 1_000_000 {
            count_be
        } else {
            count_le
        };

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

    /// - Memory is insufficient for the operation
    pub fn merge_databases(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<Self> {
        let total_kmers: u64 = input_paths
            .iter()
            .map(|path| {
                let db = Self::from_file_path(path)?;
                Ok(db.total_kmers())
            })
            .collect::<crate::error::ProcessingResult<Vec<_>>>()?
            .iter()
            .sum();

        let estimated_memory = total_kmers as usize * 24;

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

        // For streaming vs in-memory decision
        let use_streaming = Self::should_use_streaming(input_paths, config)?;

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

    fn should_use_streaming(
        input_paths: &[std::path::PathBuf],
        config: &crate::database::MergeConfig,
    ) -> crate::error::ProcessingResult<bool> {
        use crate::database::format::RKDatabase;

        let mut total_kmers = 0u64;

        for path in input_paths {
            let db = RKDatabase::from_file_path(path)?;
            total_kmers += db.total_kmers();
        }

        let estimated_memory = total_kmers as usize * 24;

        Ok(estimated_memory > config.max_memory_usage)
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

        let first_db = RKDatabase::from_file_path(&input_paths[0])?;
        let kmer_size = first_db.kmer_size();
        let canonical = first_db.is_canonical();

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

        Self::from_kmer_pairs(sorted_kmers, kmer_size as u8, canonical, true)
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

        // Validate compatibility
        let mut db_refs = Vec::new();
        for path in input_paths {
            let db = Self::from_file_path(path)?;
            db_refs.push(db);
        }
        let db_refs_slice: Vec<&Self> = db_refs.iter().collect();

        // Create external sort merger
        let merge_buffer_mb = config.max_memory_usage / 1024 / 1024; // Convert bytes to MB

        // Validate for external sort merge (allow mixed canonical modes)
        let (_kmer_size, _final_canonical) =
            Self::validate_compatibility_external_sort(&db_refs_slice, config.verbose)?;

        let mut merger = ExternalSortMerger::new(
            input_paths.to_vec(),
            config.temp_dir.clone(),
            merge_buffer_mb.max(1024), // At least 1GB buffer
            config.num_threads,
            config.merge_mode.clone(),
            config.keep_intermediate,
        )?;

        // Create temporary output path
        let temp_output = config.temp_dir.join("external_sort_merge_output.tmp");
        merger.external_sort_merge(&temp_output)?;

        let _elapsed = start_time.elapsed();

        // Read the merged result
        let result_db = Self::from_file_path(&temp_output)?;

        Ok(result_db)
    }

    /// Validate compatibility for external sort merge (allows mixed canonical modes)
    fn validate_compatibility_external_sort(
        db_refs: &[&Self],
        verbose: bool,
    ) -> crate::error::ProcessingResult<(u8, bool)> {
        let first_db = db_refs[0];
        let kmer_size = first_db.kmer_size();
        let canonical = first_db.is_canonical();

        if verbose {
            log::info!("Validating databases for external sort merge...");
        }

        let mut has_canonical = false;
        let mut has_non_canonical = false;

        for (i, db) in db_refs.iter().enumerate() {
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

            if db.is_canonical() {
                has_canonical = true;
            } else {
                has_non_canonical = true;
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

        let final_canonical = has_canonical;

        if verbose {
            if has_canonical && has_non_canonical {
                log::info!("  Mixed canonical modes detected - converting all to canonical mode");
            }
            log::info!("  Final merge mode: canonical={}", final_canonical);
        }

        Ok((kmer_size.try_into().unwrap(), final_canonical))
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
}
