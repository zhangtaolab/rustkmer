//! FASTQ file parsing using the bio crate
//!
//! Provides efficient FASTQ file reading and processing capabilities with transparent compression support.

use std::io;
use std::path::Path;

use bio::io::fastq::Reader;
use bio::io::fastq::Record;

use crate::error::{KmerError, ProcessingError, ProcessingResult};

/// Compression types supported for FASTQ files
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompressionType {
    None,
    Gzip,
    Bzip2,
    Xz,
}

impl CompressionType {
    /// Detect compression type from file extension
    pub fn from_path(path: &Path) -> Self {
        if let Some(extension) = path.extension() {
            if let Some(ext_str) = extension.to_str() {
                match ext_str.to_lowercase().as_str() {
                    "gz" => return CompressionType::Gzip,
                    "bz2" => return CompressionType::Bzip2,
                    "xz" => return CompressionType::Xz,
                    _ => {}
                }
            }
        }
        CompressionType::None
    }

    /// Get the compression format name
    pub fn name(&self) -> &'static str {
        match self {
            CompressionType::None => "uncompressed",
            CompressionType::Gzip => "gzip",
            CompressionType::Bzip2 => "bzip2",
            CompressionType::Xz => "xz",
        }
    }
}

/// Trait for compressed file reading
pub trait CompressedFileReader {
    /// Open a file with transparent compression detection
    fn open_compressed(path: &Path) -> ProcessingResult<(Box<dyn io::BufRead>, CompressionType)>;
}

pub struct DefaultCompressedFileReader;

impl CompressedFileReader for DefaultCompressedFileReader {
    fn open_compressed(path: &Path) -> ProcessingResult<(Box<dyn io::BufRead>, CompressionType)> {
        let compression_type = CompressionType::from_path(path);

        let file = std::fs::File::open(path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open file: {:?}", path),
                e,
            ))?;

        let reader: Box<dyn io::BufRead> = match compression_type {
            CompressionType::None => {
                Box::new(io::BufReader::new(file))
            }
            CompressionType::Gzip => {
                let decoder = flate2::read::GzDecoder::new(file);
                Box::new(io::BufReader::new(decoder))
            }
            CompressionType::Bzip2 => {
                let decoder = bzip2::read::BzDecoder::new(file);
                Box::new(io::BufReader::new(decoder))
            }
            CompressionType::Xz => {
                let decoder = xz2::read::XzDecoder::new(file);
                Box::new(io::BufReader::new(decoder))
            }
        };

        Ok((reader, compression_type))
    }
}

/// FASTQ file processor for efficient genomic data reading with compression support
pub struct FastqProcessor {
    /// File path
    file_path: String,
    /// Compression type
    compression_type: CompressionType,
}

impl FastqProcessor {
    /// Create a new FASTQ processor
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTQ file
    ///
    /// # Returns
    /// New FastqProcessor instance
    pub fn new<P: AsRef<Path>>(file_path: P) -> Self {
        let path = file_path.as_ref();
        let compression_type = CompressionType::from_path(path);

        Self {
            file_path: path.to_string_lossy().to_string(),
            compression_type,
        }
    }

    /// Get the compression type
    pub fn compression_type(&self) -> CompressionType {
        self.compression_type
    }

    /// Check if the file is compressed
    pub fn is_compressed(&self) -> bool {
        self.compression_type != CompressionType::None
    }

    /// Process a FASTQ file with a callback function
    ///
    /// # Arguments
    /// * `processor` - Function to process each sequence record
    ///
    /// # Returns
    /// Processing result
    pub fn process_file<F>(&self, mut processor: F) -> ProcessingResult<()>
    where
        F: FnMut(&Record) -> ProcessingResult<()>,
    {
        let (reader, compression_type) = DefaultCompressedFileReader::open_compressed(Path::new(&self.file_path))
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {} ({})", self.file_path, self.compression_type.name()),
                e,
            ))?;

        let mut fastq_reader = Reader::new(reader);

        for record_result in fastq_reader.records() {
            let record = record_result
                .map_err(|e| ProcessingError::with_context(
                    format!("Error reading FASTQ record from file: {} ({})", &self.file_path, compression_type.name()),
                    e
                ))?;

            if let Err(e) = processor(&record) {
                eprintln!("Error processing record {}: {}", record.id(), e);
                return Err(e);
            }
        }

        Ok(())
    }

    /// Process a FASTQ file with progress tracking
    ///
    /// # Arguments
    /// * `processor` - Function to process each sequence record
    /// * `progress_callback` - Optional progress callback (record_count, total_estimate)
    ///
    /// # Returns
    /// Processing result
    pub fn process_file_with_progress<F, G>(&self, mut processor: F, mut progress_callback: Option<G>) -> ProcessingResult<()>
    where
        F: FnMut(&Record) -> ProcessingResult<()>,
        G: FnMut(usize, Option<u64>) -> ProcessingResult<()>,
    {
        let (reader, compression_type) = DefaultCompressedFileReader::open_compressed(Path::new(&self.file_path))
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {} ({})", self.file_path, self.compression_type.name()),
                e,
            ))?;

        let mut fastq_reader = Reader::new(reader);
        let mut record_count = 0;

        // Get file size for progress estimation (only meaningful for uncompressed files)
        let total_size = if compression_type == CompressionType::None {
            self.file_size().ok()
        } else {
            None
        };

        for record_result in fastq_reader.records() {
            let record = record_result
                .map_err(|e| ProcessingError::with_context(
                    format!("Error reading FASTQ record from file: {} ({})", &self.file_path, compression_type.name()),
                    e
                ))?;

            if let Err(e) = processor(&record) {
                eprintln!("Error processing record {}: {}", record.id(), e);
                return Err(e);
            }

            record_count += 1;

            // Call progress callback if provided
            if let Some(ref mut callback) = progress_callback {
                if let Err(e) = callback(record_count, total_size) {
                    eprintln!("Error in progress callback: {}", e);
                    return Err(e);
                }
            }
        }

        Ok(())
    }

    /// Read all sequences from a FASTQ file
    ///
    /// # Returns
    /// Vector of sequence records
    pub fn read_all(&self) -> ProcessingResult<Vec<Record>> {
        let mut sequences = Vec::new();

        self.process_file(|record| {
            sequences.push(record.clone());
            Ok(())
        })?;

        Ok(sequences)
    }

    /// Get the file path
    pub fn file_path(&self) -> &str {
        &self.file_path
    }

    /// Check if file exists and is accessible
    pub fn file_exists(&self) -> bool {
        std::path::Path::new(&self.file_path).exists()
    }

    /// Get file size
    pub fn file_size(&self) -> ProcessingResult<u64> {
        let metadata = std::fs::metadata(&self.file_path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to get file metadata: {}", self.file_path),
                e,
            ))?;

        Ok(metadata.len())
    }

    /// Filter records based on minimum quality score
    ///
    /// # Arguments
    /// * `min_quality` - Minimum quality score (0-40 for Phred+33)
    ///
    /// # Returns
    /// Vector of records meeting quality threshold
    pub fn filter_by_quality(&self, min_quality: u8) -> ProcessingResult<Vec<Record>> {
        let mut filtered = Vec::new();

        self.process_file(|record| {
            // Check if all quality scores meet minimum
            let quality_ok = record.qual().iter().all(|q| *q >= min_quality);

            if quality_ok {
                filtered.push(record.clone());
            }

            Ok(())
        })?;

        Ok(filtered)
    }
}

/// Validate FASTQ file format
///
/// # Arguments
/// * `file_path` - Path to FASTQ file
///
/// # Returns
/// Validation result
pub fn validate_fastq_file<P: AsRef<Path>>(file_path: P) -> ProcessingResult<()> {
    let path = file_path.as_ref();

    if !path.exists() {
        return Err(ProcessingError::new(format!(
            "FASTQ file does not exist: {:?}",
            path
        )));
    }

    let compression_type = CompressionType::from_path(path);

    // Try to read the first few records to validate format
    let (reader, _) = DefaultCompressedFileReader::open_compressed(path)
        .map_err(|e| ProcessingError::with_context(
            format!("Failed to open FASTQ file: {:?} ({})", path, compression_type.name()),
            e,
        ))?;

    let mut reader = Reader::new(reader);
    let mut record_count = 0;

    for record_result in reader.records() {
        let record = record_result
            .map_err(|e| ProcessingError::with_context(
                format!("Error reading FASTQ record during validation: {:?} ({})", &path, compression_type.name()),
                e
            ))?;

        record_count += 1;

        // Validate record structure
        if record.id().is_empty() {
            eprintln!("Warning: Record {} has empty ID", record_count);
        }

        if record.seq().is_empty() {
            eprintln!("Warning: Record {} has empty sequence", record_count);
        }

        if record.qual().len() != record.seq().len() {
            eprintln!("Warning: Record {} has mismatched sequence/quality length", record_count);
        }

        // Stop after reading a few records for validation
        if record_count >= 10 {
            break;
        }
    }

    if record_count == 0 {
        return Err(ProcessingError::new(
            "No valid FASTQ records found in file"
        ));
    }

    Ok(())
}

/// Count sequences in a FASTQ file
///
/// # Arguments
/// * `file_path` - Path to FASTQ file
///
/// # Returns
/// Number of sequences or error
pub fn count_sequences<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();
    let compression_type = CompressionType::from_path(path);

    let (reader, _) = DefaultCompressedFileReader::open_compressed(path)
        .map_err(|e| ProcessingError::with_context(
            format!("Failed to open FASTQ file: {:?} ({})", path, compression_type.name()),
            e,
        ))?;

    let mut reader = Reader::new(reader);
    let mut count = 0;

    for _ in reader.records() {
        count += 1;
    }

    Ok(count)
}

/// Get total sequence length in a FASTQ file
///
/// # Arguments
/// * `file_path` - Path to FASTQ file
///
/// # Returns
/// Total sequence length or error
pub fn total_sequence_length<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();

    let file = io::BufReader::new(
        std::fs::File::open(path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {:?}", path),
                e,
            ))?,
    );

    let mut reader = Reader::new(file);
    let mut total_length = 0;

    for record_result in reader.records() {
        let record = record_result
            .map_err(|e| ProcessingError::with_context(
                format!("Error reading FASTQ record: {:?}", path),
                e
            ))?;
        total_length += record.seq().len();
    }

    Ok(total_length)
}

/// Get average quality score in a FASTQ file
///
/// # Arguments
/// * `file_path` - Path to FASTQ file
///
/// # Returns
/// Average quality score or error
pub fn average_quality<P: AsRef<Path>>(file_path: P) -> ProcessingResult<f64> {
    let path = file_path.as_ref();

    let file = io::BufReader::new(
        std::fs::File::open(path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {:?}", path),
                e,
            ))?,
    );

    let mut reader = Reader::new(file);
    let mut total_quality = 0u64;
    let mut total_positions = 0u64;

    for record_result in reader.records() {
        let record = record_result
            .map_err(|e| ProcessingError::with_context(
                format!("Error reading FASTQ record for quality calculation: {:?}", path),
                e
            ))?;

        for &qual in record.qual() {
            total_quality += qual as u64;
            total_positions += 1;
        }
    }

    if total_positions == 0 {
        return Err(ProcessingError::new("No sequences found for quality calculation"));
    }

    Ok(total_quality as f64 / total_positions as f64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_fastq_processor_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let processor = FastqProcessor::new(temp_file.path());
        assert_eq!(processor.file_path(), temp_file.path().to_string_lossy());
    }

    #[test]
    fn test_read_all_sequences() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@seq1\nATGCATGC\nIIIIIIII\n@seq2\nGCTAGCTA\nHHHHHHHHH\n").unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        let sequences = processor.read_all().unwrap();

        assert_eq!(sequences.len(), 2);
        assert_eq!(sequences[0].id(), "@seq1");
        assert_eq!(sequences[0].seq(), "ATGCATGC");
        assert_eq!(sequences[0].qual(), "IIIIIIII");
        assert_eq!(sequences[1].id(), "@seq2");
        assert_eq!(sequences[1].seq(), "GCTAGCTA");
        assert_eq!(sequences[1].qual(), "HHHHHHHHH");
    }

    #[test]
    fn test_validate_fastq_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@valid_seq\nATGC\n+IIII\n@another_seq\nGCTA\n+HHHH\n").unwrap();

        assert!(validate_fastq_file(temp_file.path()).is_ok());
    }

    #[test]
    fn test_validate_empty_file() {
        let temp_file = NamedTempFile::new().unwrap();
        // Don't write anything

        let result = validate_fastq_file(temp_file.path());
        assert!(result.is_err());
    }

    #[test]
    fn test_count_sequences() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@seq1\nATGC\n+IIII\n@seq2\nGCTA\n+HHHH\n@seq3\nATGCGAT\n+JJJJJJJJ\n").unwrap();

        let count = count_sequences(temp_file.path()).unwrap();
        assert_eq!(count, 3);
    }

    #[test]
    fn test_total_sequence_length() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@seq1\nATGCATGC\n+IIIIII\n@seq2\nGCTAGCTA\n+HHHHHH\n").unwrap();

        let total_length = total_sequence_length(temp_file.path()).unwrap();
        assert_eq!(total_length, 15); // 8 + 7
    }

    #[test]
    fn test_average_quality() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@seq1\nATGC\n+IIII\n@seq2\nGCTA\n+HHHH\n").unwrap();

        let avg_quality = average_quality(temp_file.path()).unwrap();
        // Average of [40, 40, 40, 40, 40, 40] and [40, 40, 40, 40, 40, 40]
        assert!((avg_quality - 40.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_filter_by_quality() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all("@seq1\nATGC\n+IIII\n@seq2\nGCTA\n+HHHH\n@seq3\nNNNN\n+JJJJ\n").unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        let filtered = processor.filter_by_quality(39).unwrap();

        // Should include first two records (quality scores 40+), exclude third (quality scores 30+)
        assert_eq!(filtered.len(), 2);
        assert_eq!(filtered[0].id(), "@seq1");
        assert_eq!(filtered[1].id(), "@seq2");
    }
}