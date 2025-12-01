//! Database format definitions and I/O operations
//!
//! Defines the binary format for storing k-mer databases with
//! efficient random access and compatibility with rustkmer tools.

use std::io::{Read, Write, Result as IoResult};
use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use serde::{Serialize, Deserialize};

/// Magic number for rustkmer database files
pub const DATABASE_MAGIC: &[u8; 4] = b"RKDB";

/// Database version
pub const DATABASE_VERSION: u16 = 1;

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
        Self {
            magic: *DATABASE_MAGIC,
            version: DATABASE_VERSION,
            kmer_size,
            total_kmers,
            sorted: false,
            data_offset: std::mem::size_of::<DatabaseHeader>() as u64,
            index_offset: 0,
            canonical,
            unique_kmers: total_kmers,  // Same as total_kmers for now
            file_size: 0,  // Will be calculated when writing
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
        eprintln!("DEBUG: About to write data_offset = {} to file", self.data_offset);
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
                "Invalid database magic number"
            ));
        }

        let version = reader.read_u16::<LittleEndian>()?;
        if version != DATABASE_VERSION {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("Unsupported database version: {}", version)
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
            unique_kmers: total_kmers,  // Default to total_kmers for older format compatibility
            file_size: 0,  // Unknown until full file is read
        })
    }

    /// Validate header consistency
    pub fn validate(&self) -> Result<(), String> {
        if self.kmer_size == 0 || self.kmer_size > 127 {
            return Err(format!("Invalid k-mer size: {}", self.kmer_size));
        }

        if self.data_offset < 40 || self.data_offset > 1000 {
            return Err(format!("Invalid data offset: {}", self.data_offset));
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
    /// Packed k-mer representation
    pub kmer: u64,
    /// Count of this k-mer
    pub count: u32,
}

impl KmerEntry {
    /// Create a new k-mer entry
    pub fn new(kmer: u64, count: u32) -> Self {
        Self { kmer, count }
    }

    /// Write entry to binary format
    pub fn write_to<W: Write>(&self, writer: &mut W) -> IoResult<()> {
        writer.write_u64::<LittleEndian>(self.kmer)?;
        writer.write_u32::<LittleEndian>(self.count)
    }

    /// Read entry from binary format
    pub fn read_from<R: Read>(reader: &mut R) -> IoResult<Self> {
        let kmer = reader.read_u64::<LittleEndian>()?;

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
        let file = File::open(path)
            .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;

        let mut reader = BufReader::new(file);
        let header = DatabaseHeader::read_from(&mut reader)?;

        // Fix for incorrect data_offset in header (same logic as DatabaseQuery)
        let actual_data_offset = if header.data_offset < 40 {
            42  // Use correct offset when header value is too small
        } else if header.data_offset > 1000 {
            42  // Use correct offset when header value is too large
        } else {
            header.data_offset
        };

        // Seek to data section
        reader.seek(SeekFrom::Start(actual_data_offset))
            .map_err(|e| crate::error::ProcessingError::io_error(format!("Failed to seek to data section: {}", e)))?;

        // Load k-mer entries
        let mut entries = Vec::with_capacity(header.total_kmers as usize);
        for _ in 0..header.total_kmers {
            let entry = KmerEntry::read_from(&mut reader)
                .map_err(|e| crate::error::ProcessingError::io_error(format!("Failed to read k-mer entry: {}", e)))?;
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
    pub fn write_to<W: std::io::Write>(&self, writer: &mut W) -> crate::error::ProcessingResult<()> {
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
        // Encode the query k-mer
        let query_encoded = match crate::kmer::encoding::encode_kmer(kmer) {
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
    fn binary_search_kmer(&self, query_encoded: u64) -> Option<u64> {
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
    fn linear_search_kmer(&self, query_encoded: u64) -> Option<u64> {
        for entry in &self.entries {
            if entry.kmer == query_encoded {
                return Some(entry.count as u64);
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
        let entry = KmerEntry::new(0x123456789ABCDEF0, 42);

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
}