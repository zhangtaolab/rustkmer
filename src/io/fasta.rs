//! FASTA file parsing using the bio crate
//!
//! Provides efficient FASTA file reading and processing capabilities.

use std::io;
use std::path::Path;

use bio::io::fasta::Reader;
use bio::io::fasta::Record;

use crate::error::{ProcessingError, ProcessingResult};

/// FASTA file processor for efficient genomic data reading
pub struct FastaProcessor {
    /// File path
    file_path: String,
}

impl FastaProcessor {
    /// Create a new FASTA processor
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTA file
    ///
    /// # Returns
    /// New FastaProcessor instance
    pub fn new<P: AsRef<Path>>(file_path: P) -> Self {
        Self {
            file_path: file_path.as_ref().to_string_lossy().to_string(),
        }
    }

    /// Process a FASTA file with a callback function
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
        let file = io::BufReader::new(std::fs::File::open(&self.file_path).map_err(|e| {
            ProcessingError::with_context(
                format!("Failed to open FASTA file: {}", self.file_path),
                e,
            )
        })?);

        let reader = Reader::new(file);

        for record_result in reader.records() {
            let record = record_result.map_err(|e| {
                ProcessingError::with_context(
                    format!("Error reading FASTA record from file: {}", &self.file_path),
                    e,
                )
            })?;

            if let Err(e) = processor(&record) {
                log::error!("Error processing record {}: {}", record.id(), e);
                return Err(e);
            }
        }

        Ok(())
    }

    /// Read all sequences from a FASTA file
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
        let metadata = std::fs::metadata(&self.file_path).map_err(|e| {
            ProcessingError::with_context(
                format!("Failed to get file metadata: {}", self.file_path),
                e,
            )
        })?;

        Ok(metadata.len())
    }
}

/// Validate FASTA file format
///
/// # Arguments
/// * `file_path` - Path to FASTA file
///
/// # Returns
/// Validation result
pub fn validate_fasta_file<P: AsRef<Path>>(file_path: P) -> ProcessingResult<()> {
    let path = file_path.as_ref();

    if !path.exists() {
        return Err(ProcessingError::new(format!(
            "FASTA file does not exist: {:?}",
            path
        )));
    }

    // WR-01: route through the compression-aware opener so that `.fa.gz` /
    // `.fasta.gz` / `.fna.gz` / `.ffn.gz` inputs are decompressed before
    // being handed to bio's FASTA reader. Previously this opened the file
    // via plain `File::open`, which fed raw deflate bytes to bio and either
    // errored on a UTF-8 decode ("stream did not contain valid UTF-8") or
    // silently produced garbage records. The FASTQ sibling
    // `validate_fastq_file` already used `open_compressed`; this brings the
    // FASTA path to parity. (`CompressedFileReader` lives in `src/io/
    // fastq.rs` but the implementation is format-agnostic.)
    use crate::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
    let (file, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
            ProcessingError::with_context(format!("Failed to open FASTA file: {:?}", path), e)
        })?;

    let reader = Reader::new(file);
    let mut record_count = 0;

    for record_result in reader.records() {
        let record = record_result.map_err(|e| {
            ProcessingError::with_context(
                format!(
                    "Error reading FASTA record during validation: {:?}",
                    file_path.as_ref()
                ),
                e,
            )
        })?;

        record_count += 1;

        // Validate record structure
        if record.id().is_empty() {
            log::warn!("Warning: Record {} has empty ID", record_count);
        }

        if record.seq().is_empty() {
            log::warn!("Warning: Record {} has empty sequence", record_count);
        }

        // Stop after reading a few records for validation
        if record_count >= 10 {
            break;
        }
    }

    if record_count == 0 {
        return Err(ProcessingError::new("No valid FASTA records found in file"));
    }

    Ok(())
}

/// Count sequences in a FASTA file
///
/// # Arguments
/// * `file_path` - Path to FASTA file (supports `.gz` / `.bz2` / `.xz`)
///
/// # Returns
/// Number of sequences or error
pub fn count_sequences<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();

    // WR-03: route through the compression-aware opener so `.fa.gz` / `.bz2` /
    // `.xz` inputs are decompressed before bio's reader parses them. This is
    // the same fix WR-01 applied to `validate_fasta_file`.
    use crate::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
    let (file, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
            ProcessingError::with_context(format!("Failed to open FASTA file: {:?}", path), e)
        })?;

    let reader = Reader::new(file);
    let mut count = 0;

    for _ in reader.records() {
        count += 1;
    }

    Ok(count)
}

/// Get total sequence length in a FASTA file
///
/// # Arguments
/// * `file_path` - Path to FASTA file (supports `.gz` / `.bz2` / `.xz`)
///
/// # Returns
/// Total sequence length or error
pub fn total_sequence_length<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();

    // WR-03: route through the compression-aware opener so `.fa.gz` / `.bz2` /
    // `.xz` inputs are decompressed before bio's reader parses them. This is
    // the same fix WR-01 applied to `validate_fasta_file`.
    use crate::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
    let (file, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
            ProcessingError::with_context(format!("Failed to open FASTA file: {:?}", path), e)
        })?;

    let reader = Reader::new(file);
    let mut total_length = 0;

    for record_result in reader.records() {
        let record = record_result.map_err(|e| {
            ProcessingError::with_context(format!("Error reading FASTA record: {:?}", path), e)
        })?;
        total_length += record.seq().len();
    }

    Ok(total_length)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_fasta_processor_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let processor = FastaProcessor::new(temp_file.path());
        assert_eq!(processor.file_path(), temp_file.path().to_string_lossy());
    }

    #[test]
    fn test_read_all_sequences() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b">seq1\nATGCATGC\n>seq2\nGCTAGCTA\n")
            .unwrap();

        let processor = FastaProcessor::new(temp_file.path());
        let sequences = processor.read_all().unwrap();

        assert_eq!(sequences.len(), 2);
        assert_eq!(sequences[0].id(), "seq1");
        assert_eq!(sequences[0].seq(), b"ATGCATGC");
        assert_eq!(sequences[1].id(), "seq2");
        assert_eq!(sequences[1].seq(), b"GCTAGCTA");
    }

    #[test]
    fn test_validate_fasta_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b">valid_seq\nATGC\n>another_seq\nGCTA\n")
            .unwrap();

        assert!(validate_fasta_file(temp_file.path()).is_ok());
    }

    #[test]
    fn test_validate_empty_file() {
        let temp_file = NamedTempFile::new().unwrap();
        // Don't write anything

        let result = validate_fasta_file(temp_file.path());
        assert!(result.is_err());
    }

    /// WR-01 regression: `validate_fasta_file` must transparently decompress
    /// gzipped inputs (`.fa.gz` etc.) before handing the bytes to bio's
    /// FASTA reader. Previously the validator opened the file via plain
    /// `File::open`, so a gzipped FASTA was parsed as raw deflate bytes and
    /// either errored on UTF-8 decode or accepted garbage records.
    #[test]
    fn test_validate_gzipped_fasta_file() {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::fs::File;

        // Write a gzipped FASTA to a temp file with a `.fa.gz` suffix so the
        // path matches what the CLI file-type router dispatches.
        let temp_dir = tempfile::tempdir().unwrap();
        let gz_path = temp_dir.path().join("input.fa.gz");
        let encoder = GzEncoder::new(File::create(&gz_path).unwrap(), Compression::default());
        let mut writer = io::BufWriter::new(encoder);
        writer
            .write_all(b">seq1\nATGCATGC\n>seq2\nGCTAGCTA\n")
            .unwrap();
        writer.flush().unwrap();
        drop(writer);

        // The compressed validator must accept the file exactly as the
        // uncompressed validator accepts the plain version.
        assert!(
            validate_fasta_file(&gz_path).is_ok(),
            "gzipped FASTA must validate after WR-01 fix"
        );
    }

    #[test]
    fn test_count_sequences() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b">seq1\nATGC\n>seq2\nGCTA\n>seq3\nATGCGAT\n")
            .unwrap();

        let count = count_sequences(temp_file.path()).unwrap();
        assert_eq!(count, 3);
    }

    #[test]
    fn test_total_sequence_length() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b">seq1\nATGCATGC\n>seq2\nGCTAGCTA\n")
            .unwrap();

        let total_length = total_sequence_length(temp_file.path()).unwrap();
        assert_eq!(total_length, 16); // 8 + 8
    }

    /// WR-03 regression: `count_sequences` and `total_sequence_length` must
    /// transparently decompress gzipped inputs. Previously both helpers used
    /// plain `File::open`, so a `.fa.gz` was parsed as raw deflate bytes and
    /// either errored on UTF-8 decode or silently produced wrong counts.
    #[test]
    fn test_count_sequences_and_total_length_gzipped() {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::fs::File;

        let temp_dir = tempfile::tempdir().unwrap();
        let gz_path = temp_dir.path().join("input.fa.gz");
        let encoder = GzEncoder::new(File::create(&gz_path).unwrap(), Compression::default());
        let mut writer = io::BufWriter::new(encoder);
        writer
            .write_all(b">seq1\nATGCATGC\n>seq2\nGCTAGCTA\n>seq3\nATGCGAT\n")
            .unwrap();
        writer.flush().unwrap();
        drop(writer);

        // Three records, total length 8 + 8 + 7 = 23.
        assert_eq!(count_sequences(&gz_path).unwrap(), 3);
        assert_eq!(total_sequence_length(&gz_path).unwrap(), 23);
    }
}
