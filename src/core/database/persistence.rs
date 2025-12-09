//! Database persistence utilities for KmerCounter database saving and loading

use crate::core::metadata::{DatabaseMetadata, create_metadata, save_metadata, load_metadata, validate_metadata};
use std::collections::HashMap;
use std::fs;
use std::io::{self, Write, BufWriter, BufReader, Read, BufRead};
use std::path::Path;
// use std::time::{SystemTime, UNIX_EPOCH}; // Unused imports
use flate2::{read::GzDecoder, write::GzEncoder, Compression};
use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use sha2::{Sha256, Digest};
use thiserror::Error;

/// Error types for database persistence operations
#[derive(Debug, Error)]
pub enum PersistenceError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Metadata error: {0}")]
    MetadataError(#[from] crate::core::metadata::MetadataError),

    #[error("Invalid database format: {0}")]
    InvalidFormat(String),

    #[error("Version mismatch: expected {expected}, got {actual}")]
    VersionMismatch { expected: String, actual: String },

    #[error("Checksum validation failed")]
    ChecksumError,

    #[error("K-mer size mismatch: expected {expected}, got {actual}")]
    KmerSizeMismatch { expected: usize, actual: usize },

    #[error("Canonical mode mismatch: expected {expected}, got {actual}")]
    CanonicalMismatch { expected: bool, actual: bool },
}

/// Configuration for database persistence operations
#[derive(Debug, Clone)]
pub struct PersistenceConfig {
    pub compression_enabled: bool,
    pub compression_level: u8,
    pub checksum_enabled: bool,
    pub buffer_size: usize,
}

impl Default for PersistenceConfig {
    fn default() -> Self {
        Self {
            compression_enabled: true,
            compression_level: 6,
            checksum_enabled: true,
            buffer_size: 8192,
        }
    }
}

/// Save k-mer counts to a hybrid database format (JSON metadata + binary data)
pub fn save_kmer_database(
    kmer_counts: &HashMap<String, u64>,
    database_path: &Path,
    kmer_size: usize,
    canonical: bool,
    source_files: Vec<String>,
    config: PersistenceConfig,
) -> Result<(), PersistenceError> {
    // Create database directory if it doesn't exist
    fs::create_dir_all(database_path)?;

    // Create metadata
    let mut metadata = create_metadata(kmer_size, canonical, source_files);

    // Update statistics
    metadata.total_kmers = kmer_counts.values().sum();
    metadata.unique_kmers = kmer_counts.len() as u64;
    metadata.performance.creation_time_seconds = 0.0; // Not tracked in this context
    metadata.performance.files_processed = 1; // Single save operation

    // Generate data file path
    let data_file_path = database_path.join("data.rkdb");
    let data_file_path_compressed = database_path.join("data.rkdb.gz");

    // Save binary k-mer data
    let (data_size_bytes, actual_data_size) = if config.compression_enabled {
        save_kmer_data_compressed(kmer_counts, &data_file_path_compressed, config.buffer_size, config.compression_level)?
    } else {
        save_kmer_data_uncompressed(kmer_counts, &data_file_path, config.buffer_size)?
    };

    // Update metadata with file information
    metadata.performance.input_size_bytes = data_size_bytes;
    metadata.performance.output_size_bytes = actual_data_size;
    metadata.performance.calculate_compression_ratio();

    // Generate checksums if enabled
    if config.checksum_enabled {
        let checksums = generate_checksums(&[
            ("metadata.json", &database_path.join("metadata.json")),
            if config.compression_enabled {
                ("data.rkdb.gz", &data_file_path_compressed)
            } else {
                ("data.rkdb", &data_file_path)
            },
        ])?;

        save_checksums(database_path, &checksums)?;
    }

    // Save metadata
    let metadata_path = database_path.join("metadata.json");
    save_metadata(&metadata, &metadata_path)?;

    Ok(())
}

/// Save k-mer data in compressed format
fn save_kmer_data_compressed(
    kmer_counts: &HashMap<String, u64>,
    file_path: &Path,
    buffer_size: usize,
    compression_level: u8,
) -> Result<(u64, u64), PersistenceError> {
    let file = fs::File::create(file_path)?;
    let encoder = GzEncoder::new(file, Compression::new(compression_level as u32));
    let mut writer = BufWriter::with_capacity(buffer_size, encoder);

    // Write header information
    writer.write_u64::<LittleEndian>(kmer_counts.len() as u64)?;
    writer.write_u32::<LittleEndian>(21)?; // k-mer size placeholder - should be parameterized

    // Write k-mer data
    let _total_data_size = 12u64; // header size
    let mut uncompressed_size = 12u64;

    for (kmer, count) in kmer_counts {
        // Encode k-mer to bytes (simple encoding for now)
        let kmer_bytes = encode_kmer_to_bytes(kmer)?;

        writer.write_u32::<LittleEndian>(kmer_bytes.len() as u32)?;
        writer.write_all(&kmer_bytes)?;
        writer.write_u64::<LittleEndian>(*count)?;

        uncompressed_size += (4 + kmer_bytes.len() + 8) as u64;
    }

    writer.flush()?;
    drop(writer); // Ensure all data is written

    let compressed_size = fs::metadata(file_path)?.len();
    Ok((uncompressed_size, compressed_size))
}

/// Save k-mer data in uncompressed format
fn save_kmer_data_uncompressed(
    kmer_counts: &HashMap<String, u64>,
    file_path: &Path,
    buffer_size: usize,
) -> Result<(u64, u64), PersistenceError> {
    let file = fs::File::create(file_path)?;
    let mut writer = BufWriter::with_capacity(buffer_size, file);

    // Write header information
    writer.write_u64::<LittleEndian>(kmer_counts.len() as u64)?;
    writer.write_u32::<LittleEndian>(21)?; // k-mer size placeholder

    // Write k-mer data
    let mut total_size = 12u64; // header size

    for (kmer, count) in kmer_counts {
        let kmer_bytes = encode_kmer_to_bytes(kmer)?;

        writer.write_u32::<LittleEndian>(kmer_bytes.len() as u32)?;
        writer.write_all(&kmer_bytes)?;
        writer.write_u64::<LittleEndian>(*count)?;

        total_size += (4 + kmer_bytes.len() + 8) as u64;
    }

    writer.flush()?;
    drop(writer);

    Ok((total_size, total_size))
}

/// Load k-mer counts from a hybrid database format
pub fn load_kmer_database(
    database_path: &Path,
    config: &PersistenceConfig,
) -> Result<(HashMap<String, u64>, DatabaseMetadata), PersistenceError> {
    // Load and validate metadata
    let metadata_path = database_path.join("metadata.json");
    let metadata = load_metadata(&metadata_path)?;

    // Validate metadata
    validate_metadata(database_path)?;

    // Determine data file path
    let data_file_path = if config.compression_enabled {
        let compressed_path = database_path.join("data.rkdb.gz");
        if compressed_path.exists() {
            compressed_path
        } else {
            database_path.join("data.rkdb")
        }
    } else {
        database_path.join("data.rkdb")
    };

    // Load k-mer data
    let kmer_counts = if data_file_path.extension().map_or(false, |ext| ext == "gz") {
        load_kmer_data_compressed(&data_file_path, config.buffer_size)?
    } else {
        load_kmer_data_uncompressed(&data_file_path, config.buffer_size)?
    };

    // Validate against metadata
    if kmer_counts.len() != metadata.unique_kmers as usize {
        return Err(PersistenceError::InvalidFormat(
            format!("K-mer count mismatch: metadata reports {}, loaded {}",
                   metadata.unique_kmers, kmer_counts.len())
        ));
    }

    Ok((kmer_counts, metadata))
}

/// Load k-mer data from compressed format
fn load_kmer_data_compressed(
    file_path: &Path,
    buffer_size: usize,
) -> Result<HashMap<String, u64>, PersistenceError> {
    let file = fs::File::open(file_path)?;
    let decoder = GzDecoder::new(file);
    let mut reader = BufReader::with_capacity(buffer_size, decoder);

    load_kmer_data_from_reader(&mut reader)
}

/// Load k-mer data from uncompressed format
fn load_kmer_data_uncompressed(
    file_path: &Path,
    buffer_size: usize,
) -> Result<HashMap<String, u64>, PersistenceError> {
    let file = fs::File::open(file_path)?;
    let mut reader = BufReader::with_capacity(buffer_size, file);

    load_kmer_data_from_reader(&mut reader)
}

/// Load k-mer data from a generic reader
fn load_kmer_data_from_reader<R: ReadBytesExt>(
    reader: &mut R,
) -> Result<HashMap<String, u64>, PersistenceError> {
    let mut kmer_counts = HashMap::new();

    // Read header
    let num_kmers = reader.read_u64::<LittleEndian>()?;
    let _kmer_size = reader.read_u32::<LittleEndian>()?;

    // Read k-mer data
    for _ in 0..num_kmers {
        let kmer_len = reader.read_u32::<LittleEndian>()?;
        let mut kmer_bytes = vec![0u8; kmer_len as usize];
        reader.read_exact(&mut kmer_bytes)?;

        let kmer = decode_kmer_from_bytes(&kmer_bytes)?;
        let count = reader.read_u64::<LittleEndian>()?;

        kmer_counts.insert(kmer, count);
    }

    Ok(kmer_counts)
}

/// Simple k-mer to bytes encoding (can be replaced with more efficient encoding)
fn encode_kmer_to_bytes(kmer: &str) -> Result<Vec<u8>, PersistenceError> {
    Ok(kmer.as_bytes().to_vec())
}

/// Simple bytes to k-mer decoding (can be replaced with more efficient decoding)
fn decode_kmer_from_bytes(bytes: &[u8]) -> Result<String, PersistenceError> {
    String::from_utf8(bytes.to_vec())
        .map_err(|e| PersistenceError::InvalidFormat(format!("Invalid k-mer encoding: {}", e)))
}

/// Generate SHA256 checksums for specified files
fn generate_checksums(files: &[(&str, &Path)]) -> Result<Vec<(String, String)>, PersistenceError> {
    let mut checksums = Vec::new();

    for (name, path) in files {
        if !path.exists() {
            continue;
        }

        let mut hasher = Sha256::new();
        let mut file = fs::File::open(path)?;
        let mut buffer = [0; 8192];

        loop {
            let bytes_read = file.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }
            hasher.update(&buffer[..bytes_read]);
        }

        let checksum = format!("{:x}", hasher.finalize());
        checksums.push((name.to_string(), checksum));
    }

    Ok(checksums)
}

/// Save checksums to checksums.txt file
fn save_checksums(database_path: &Path, checksums: &[(String, String)]) -> Result<(), PersistenceError> {
    let checksums_path = database_path.join("checksums.txt");
    let mut file = fs::File::create(checksums_path)?;

    for (filename, checksum) in checksums {
        writeln!(file, "{}  {}", checksum, filename)?;
    }

    Ok(())
}

/// Load and validate checksums from checksums.txt file
pub fn validate_checksums(database_path: &Path) -> Result<bool, PersistenceError> {
    let checksums_path = database_path.join("checksums.txt");
    if !checksums_path.exists() {
        return Ok(true); // No checksums to validate
    }

    let file = fs::File::open(&checksums_path)?;
    let reader = io::BufReader::new(file);

    let mut stored_checksums = HashMap::new();
    for line in io::BufReader::new(reader).lines() {
        let line = line?;
        let parts: Vec<&str> = line.splitn(3, ' ').collect();
        if parts.len() >= 2 {
            stored_checksums.insert(parts[1].to_string(), parts[0].to_string());
        }
    }

    // Verify each file's checksum
    for (filename, expected_checksum) in stored_checksums.iter() {
        let file_path = database_path.join(filename);
        if !file_path.exists() {
            return Err(PersistenceError::ChecksumError);
        }

        let actual_checksums = generate_checksums(&[(&filename, &file_path)])?;
        if let Some((_, actual_checksum)) = actual_checksums.first() {
            if actual_checksum != expected_checksum {
                return Err(PersistenceError::ChecksumError);
            }
        }
    }

    Ok(true)
}

/// Merge two databases and save the result
pub fn merge_databases(
    db1_path: &Path,
    db2_path: &Path,
    output_path: &Path,
    config: &PersistenceConfig,
) -> Result<DatabaseMetadata, PersistenceError> {
    // Load both databases
    let (mut counts1, mut metadata1) = load_kmer_database(db1_path, config)?;
    let (counts2, metadata2) = load_kmer_database(db2_path, config)?;

    // Validate compatibility
    if metadata1.kmer_size != metadata2.kmer_size {
        return Err(PersistenceError::KmerSizeMismatch {
            expected: metadata1.kmer_size,
            actual: metadata2.kmer_size,
        });
    }

    if metadata1.canonical != metadata2.canonical {
        return Err(PersistenceError::CanonicalMismatch {
            expected: metadata1.canonical,
            actual: metadata2.canonical,
        });
    }

    // Merge counts
    for (kmer, count) in counts2 {
        *counts1.entry(kmer).or_insert(0) += count;
    }

    // Update metadata for merged database
    metadata1.total_kmers = counts1.values().sum();
    metadata1.unique_kmers = counts1.len() as u64;
    metadata1.update_timestamp();

    // Merge source files
    metadata1.source_files.extend(metadata2.source_files.clone());

    // Create output directory
    fs::create_dir_all(output_path)?;

    // Save merged database
    save_kmer_database(&counts1, output_path, metadata1.kmer_size, metadata1.canonical,
                      metadata1.source_files.clone(), config.clone())?;

    Ok(metadata1)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use tempfile::tempdir;

    #[test]
    fn test_save_load_database() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("test_db");

        let mut kmer_counts = HashMap::new();
        kmer_counts.insert("ATGC".to_string(), 10);
        kmer_counts.insert("CGAT".to_string(), 5);

        let config = PersistenceConfig::default();

        // Save database
        save_kmer_database(&kmer_counts, &db_path, 4, false, vec!["test.fa".to_string()], config.clone()).unwrap();

        // Load database
        let (loaded_counts, metadata) = load_kmer_database(&db_path, &config).unwrap();

        assert_eq!(loaded_counts.len(), kmer_counts.len());
        assert_eq!(metadata.kmer_size, 4);
        assert!(!metadata.canonical);

        for (kmer, expected_count) in &kmer_counts {
            assert_eq!(loaded_counts.get(kmer), Some(expected_count));
        }
    }

    #[test]
    fn test_compression() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("compressed_db");

        let mut kmer_counts = HashMap::new();
        for i in 0..1000 {
            kmer_counts.insert(format!("ATGC{}", i), i);
        }

        let compressed_config = PersistenceConfig {
            compression_enabled: true,
            compression_level: 9,
            ..Default::default()
        };

        let uncompressed_config = PersistenceConfig {
            compression_enabled: false,
            ..Default::default()
        };

        // Save compressed
        let compressed_path = dir.path().join("compressed");
        save_kmer_database(&kmer_counts, &compressed_path, 8, true, vec![], compressed_config).unwrap();

        // Save uncompressed
        let uncompressed_path = dir.path().join("uncompressed");
        save_kmer_database(&kmer_counts, &uncompressed_path, 8, true, vec![], uncompressed_config).unwrap();

        // Compare sizes
        let compressed_size = fs::metadata(compressed_path.join("data.rkdb.gz")).unwrap().len();
        let uncompressed_size = fs::metadata(uncompressed_path.join("data.rkdb")).unwrap().len();

        assert!(compressed_size < uncompressed_size, "Compression should reduce file size");
    }

    #[test]
    fn test_merge_databases() {
        let dir = tempdir().unwrap();
        let db1_path = dir.path().join("db1");
        let db2_path = dir.path().join("db2");
        let output_path = dir.path().join("merged");

        let config = PersistenceConfig::default();

        // Create first database
        let mut counts1 = HashMap::new();
        counts1.insert("ATGC".to_string(), 10);
        counts1.insert("CGAT".to_string(), 5);
        save_kmer_database(&counts1, &db1_path, 4, false, vec!["db1.fa".to_string()], config.clone()).unwrap();

        // Create second database with overlapping k-mers
        let mut counts2 = HashMap::new();
        counts2.insert("ATGC".to_string(), 3);  // Overlapping with db1
        counts2.insert("GCTA".to_string(), 7);  // New k-mer
        save_kmer_database(&counts2, &db2_path, 4, false, vec!["db2.fa".to_string()], config.clone()).unwrap();

        // Merge databases
        let merged_metadata = merge_databases(&db1_path, &db2_path, &output_path, &config).unwrap();

        // Verify merged result
        let (merged_counts, _) = load_kmer_database(&output_path, &PersistenceConfig::default()).unwrap();

        assert_eq!(merged_counts.get("ATGC"), Some(&13)); // 10 + 3
        assert_eq!(merged_counts.get("CGAT"), Some(&5));  // From db1 only
        assert_eq!(merged_counts.get("GCTA"), Some(&7));  // From db2 only
        assert_eq!(merged_metadata.source_files.len(), 2);  // Both source files
    }
}