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