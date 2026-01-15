//! Binary output format for k-mer counts
//!
//! Provides efficient binary serialization of k-mer counting results.

use crate::error::{ProcessingError, ProcessingResult};
use crate::hash::table::CounterStats;
use std::io::Write;

/// Binary format header
#[derive(Debug, Clone)]
pub struct BinaryHeader {
    /// Magic number for format identification
    pub magic: [u8; 4],
    /// Format version
    pub version: u32,
    /// K-mer length
    pub kmer_length: u32,
    /// Number of unique k-mers
    pub unique_kmers: u64,
    /// Total k-mers processed
    pub total_kmers: u64,
    /// Whether canonical mode was used
    pub canonical_mode: u8,
    /// Reserved for future use
    pub reserved: [u8; 7],
}

impl BinaryHeader {
    /// Create a new binary header
    pub fn new(stats: &CounterStats) -> Self {
        Self {
            magic: *b"RSK1", // Rust K-mer format version 1
            version: 1,
            kmer_length: stats.kmer_length as u32,
            unique_kmers: stats.unique_kmers,
            total_kmers: stats.total_kmers,
            canonical_mode: stats.canonical_mode as u8,
            reserved: [0; 7],
        }
    }

    /// Serialize header to bytes
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(36);
        bytes.extend_from_slice(&self.magic);
        bytes.extend_from_slice(&self.version.to_le_bytes());
        bytes.extend_from_slice(&self.kmer_length.to_le_bytes());
        bytes.extend_from_slice(&self.unique_kmers.to_le_bytes());
        bytes.extend_from_slice(&self.total_kmers.to_le_bytes());
        bytes.push(self.canonical_mode);
        bytes.extend_from_slice(&self.reserved);
        bytes
    }

    /// Parse header from bytes
    pub fn from_bytes(bytes: &[u8]) -> ProcessingResult<Self> {
        if bytes.len() < 36 {
            return Err(ProcessingError::new("Header too short"));
        }

        let magic = [bytes[0], bytes[1], bytes[2], bytes[3]];
        if magic != *b"RSK1" {
            return Err(ProcessingError::new("Invalid magic number"));
        }

        let version = u32::from_le_bytes([bytes[4], bytes[5], bytes[6], bytes[7]]);
        if version != 1 {
            return Err(ProcessingError::new(format!(
                "Unsupported version: {}",
                version
            )));
        }

        let kmer_length = u32::from_le_bytes([bytes[8], bytes[9], bytes[10], bytes[11]]);
        let unique_kmers = u64::from_le_bytes([
            bytes[12], bytes[13], bytes[14], bytes[15], bytes[16], bytes[17], bytes[18], bytes[19],
        ]);
        let total_kmers = u64::from_le_bytes([
            bytes[20], bytes[21], bytes[22], bytes[23], bytes[24], bytes[25], bytes[26], bytes[27],
        ]);
        let canonical_mode = bytes[28];
        let reserved = [bytes[29], bytes[30], bytes[31], 0, 0, 0, 0];

        Ok(Self {
            magic,
            version,
            kmer_length,
            unique_kmers,
            total_kmers,
            canonical_mode,
            reserved,
        })
    }
}

/// Write k-mer counts in binary format
///
/// # Arguments
/// * `writer` - Output writer
/// * `kmer_counts` - Vector of (kmer, count) pairs
/// * `stats` - Statistics for the header
///
/// # Returns
/// Result indicating success or error
pub fn write_binary_format<W: Write>(
    mut writer: W,
    kmer_counts: &[(u64, u32)],
    stats: &CounterStats,
) -> ProcessingResult<()> {
    // Write header
    let header = BinaryHeader::new(stats);
    writer
        .write_all(&header.to_bytes())
        .map_err(|e| ProcessingError::with_context("Failed to write header", e))?;

    // Write k-mer counts
    for (kmer, count) in kmer_counts {
        writer
            .write_all(&kmer.to_le_bytes())
            .map_err(|e| ProcessingError::with_context("Failed to write k-mer", e))?;
        writer
            .write_all(&count.to_le_bytes())
            .map_err(|e| ProcessingError::with_context("Failed to write count", e))?;
    }

    Ok(())
}

/// Calculate binary file size
///
/// # Arguments
/// * `num_kmers` - Number of k-mers
///
/// # Returns
/// Expected file size in bytes
pub fn calculate_file_size(num_kmers: usize) -> usize {
    36 + (num_kmers * 12) // Header (36) + k-mer (8) + count (4)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hash::table::CounterStats;

    #[test]
    fn test_binary_header() {
        let stats = CounterStats {
            total_kmers: 1000,
            unique_kmers: 500,
            kmer_length: 21,
            canonical_mode: true,
        };

        let header = BinaryHeader::new(&stats);
        assert_eq!(&header.magic, b"RSK1");
        assert_eq!(header.version, 1);
        assert_eq!(header.kmer_length, 21);
        assert_eq!(header.unique_kmers, 500);
        assert_eq!(header.total_kmers, 1000);
        assert_eq!(header.canonical_mode, 1);
    }

    #[test]
    fn test_header_serialization() {
        let stats = CounterStats {
            total_kmers: 100,
            unique_kmers: 50,
            kmer_length: 13,
            canonical_mode: false,
        };

        let header = BinaryHeader::new(&stats);
        let bytes = header.to_bytes();

        // Check length
        assert_eq!(bytes.len(), 36); // 4 + 4 + 4 + 8 + 8 + 1 + 7 = 36

        // Parse back
        let parsed = BinaryHeader::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.kmer_length, 13);
        assert_eq!(parsed.unique_kmers, 50);
        assert_eq!(parsed.total_kmers, 100);
        assert_eq!(parsed.canonical_mode, 0);
    }

    #[test]
    fn test_invalid_magic_number() {
        let invalid_bytes = vec![0u8; 36];
        let result = BinaryHeader::from_bytes(&invalid_bytes);
        assert!(result.is_err());
    }

    #[test]
    fn test_calculate_file_size() {
        let size = calculate_file_size(1000);
        assert_eq!(size, 36 + 1000 * 12); // Header + 1000 * (8 + 4)
    }
}
