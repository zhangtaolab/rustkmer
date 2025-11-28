//! FASTQ file parsing using the bio crate
//!
//! Provides efficient FASTQ file reading and processing capabilities.

use std::io;
use std::path::Path;

use bio::io::fastq::Reader;
use bio::io::fastq::Record;

use crate::error::{KmerError, ProcessingError, ProcessingResult};

/// FASTQ file processor for efficient genomic data reading
pub struct FastqProcessor {
    /// File path
    file_path: String,
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
        Self {
            file_path: file_path.as_ref().to_string_lossy().to_string(),
        }
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
        let file = io::BufReader::new(
            std::fs::File::open(&self.file_path)
                .map_err(|e| ProcessingError::with_context(
                    format!("Failed to open FASTQ file: {}", self.file_path),
                    e,
                ))?,
        );

        let mut reader = Reader::new(file);

        for record_result in reader.records() {
            let record = record_result
                .map_err(|e| ProcessingError::with_context(
                    format!("Error reading FASTQ record from file: {}", &self.file_path),
                    e
                ))?;

            if let Err(e) = processor(&record) {
                eprintln!("Error processing record {}: {}", record.id(), e);
                return Err(e);
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

    // Try to read the first few records to validate format
    let file = io::BufReader::new(
        std::fs::File::open(path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {:?}", path),
                e,
            ))?,
    );

    let mut reader = Reader::new(file);
    let mut record_count = 0;

    for record_result in reader.records() {
        let record = record_result
            .map_err(|e| ProcessingError::with_context(
                format!("Error reading FASTQ record during validation: {:?}", &path),
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

    let file = io::BufReader::new(
        std::fs::File::open(path)
            .map_err(|e| ProcessingError::with_context(
                format!("Failed to open FASTQ file: {:?}", path),
                e,
            ))?,
    );

    let mut reader = Reader::new(file);
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