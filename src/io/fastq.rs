//! FASTQ file parsing using the bio crate
//!
//! Provides efficient FASTQ file reading and processing capabilities with transparent compression support.

use std::io;
use std::path::Path;

use bio::io::fastq::Reader;
use bio::io::fastq::Record;

use crate::error::{ProcessingError, ProcessingResult};

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

        let file = std::fs::File::open(path).map_err(|e| {
            ProcessingError::with_context(format!("Failed to open file: {:?}", path), e)
        })?;

        let reader: Box<dyn io::BufRead> = match compression_type {
            CompressionType::None => Box::new(io::BufReader::new(file)),
            CompressionType::Gzip => {
                // Multi-member (concatenated) gzip files are common for
                // archive-downloaded FASTQ/FASTA inputs; a single-member
                // decoder silently stops at the first member's EOF.
                // MultiGzDecoder decodes all concatenated members. Its
                // output matches the single-member decoder's only when
                // nothing follows the final member; any trailing non-gzip
                // bytes (padded writes, appended text, a torn second
                // member) surface as a mid-stream io error instead of
                // being silently ignored — loud failure is deliberate.
                // Pinned by test_read_all_errors_on_trailing_garbage_after_gzip_member.
                let decoder = flate2::read::MultiGzDecoder::new(file);
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
        let (reader, compression_type) = DefaultCompressedFileReader::open_compressed(Path::new(
            &self.file_path,
        ))
        .map_err(|e| {
            ProcessingError::with_context(
                format!(
                    "Failed to open FASTQ file: {} ({})",
                    self.file_path,
                    self.compression_type.name()
                ),
                e,
            )
        })?;

        let fastq_reader = Reader::new(reader);

        for record_result in fastq_reader.records() {
            let record = record_result.map_err(|e| {
                ProcessingError::with_context(
                    format!(
                        "Error reading FASTQ record from file: {} ({})",
                        self.file_path,
                        compression_type.name()
                    ),
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

    /// Process a FASTQ file with progress tracking
    ///
    /// # Arguments
    /// * `processor` - Function to process each sequence record
    /// * `progress_callback` - Optional progress callback (record_count, total_estimate)
    ///
    /// # Returns
    /// Processing result
    pub fn process_file_with_progress<F, G>(
        &self,
        mut processor: F,
        mut progress_callback: Option<G>,
    ) -> ProcessingResult<()>
    where
        F: FnMut(&Record) -> ProcessingResult<()>,
        G: FnMut(usize, Option<u64>) -> ProcessingResult<()>,
    {
        let (reader, compression_type) = DefaultCompressedFileReader::open_compressed(Path::new(
            &self.file_path,
        ))
        .map_err(|e| {
            ProcessingError::with_context(
                format!(
                    "Failed to open FASTQ file: {} ({})",
                    self.file_path,
                    self.compression_type.name()
                ),
                e,
            )
        })?;

        let fastq_reader = Reader::new(reader);
        let mut record_count = 0;

        // Get file size for progress estimation (only meaningful for uncompressed files)
        let total_size = if compression_type == CompressionType::None {
            self.file_size().ok()
        } else {
            None
        };

        for record_result in fastq_reader.records() {
            let record = record_result.map_err(|e| {
                ProcessingError::with_context(
                    format!(
                        "Error reading FASTQ record from file: {} ({})",
                        self.file_path,
                        compression_type.name()
                    ),
                    e,
                )
            })?;

            if let Err(e) = processor(&record) {
                log::error!("Error processing record {}: {}", record.id(), e);
                return Err(e);
            }

            record_count += 1;

            // Call progress callback if provided
            if let Some(ref mut callback) = progress_callback {
                if let Err(e) = callback(record_count, total_size) {
                    log::error!("Error in progress callback: {}", e);
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
        let metadata = std::fs::metadata(&self.file_path).map_err(|e| {
            ProcessingError::with_context(
                format!("Failed to get file metadata: {}", self.file_path),
                e,
            )
        })?;

        Ok(metadata.len())
    }

    /// Filter records based on a minimum raw quality byte value
    ///
    /// The comparison is against the RAW Phred+33 ASCII byte value of each
    /// quality character, not the decoded Phred score: pass a threshold in
    /// the raw ASCII range (for Phred+33 data every real quality byte is at
    /// least 33, e.g. ASCII 55 corresponds to Q20). Passing a decoded Phred
    /// score instead would silently keep every record.
    ///
    /// # Arguments
    /// * `min_quality_ascii` - Minimum raw Phred+33 ASCII quality byte value
    ///   (worked example: 55 corresponds to Q20)
    ///
    /// # Returns
    /// Vector of records meeting quality threshold
    pub fn filter_by_quality(&self, min_quality_ascii: u8) -> ProcessingResult<Vec<Record>> {
        let mut filtered = Vec::new();

        self.process_file(|record| {
            // Check if all quality scores meet minimum
            let quality_ok = record.qual().iter().all(|q| *q >= min_quality_ascii);

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
    let (reader, _) = DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
        ProcessingError::with_context(
            format!(
                "Failed to open FASTQ file: {:?} ({})",
                path,
                compression_type.name()
            ),
            e,
        )
    })?;

    let reader = Reader::new(reader);
    let mut record_count = 0;

    for record_result in reader.records() {
        let record = record_result.map_err(|e| {
            ProcessingError::with_context(
                format!(
                    "Error reading FASTQ record during validation: {:?} ({})",
                    path,
                    compression_type.name()
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

        if record.qual().len() != record.seq().len() {
            log::warn!(
                "Warning: Record {} has mismatched sequence/quality length",
                record_count
            );
        }

        // Stop after reading a few records for validation
        if record_count >= 10 {
            break;
        }
    }

    if record_count == 0 {
        return Err(ProcessingError::new("No valid FASTQ records found in file"));
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

    let (reader, _) = DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
        ProcessingError::with_context(
            format!(
                "Failed to open FASTQ file: {} ({})",
                path.display(),
                compression_type.name()
            ),
            e,
        )
    })?;

    let reader = Reader::new(reader);
    let mut count = 0;

    // WR-16: bind each record Result and propagate failures instead of
    // tallying malformed/truncated records as sequences — the same error
    // contract `process_file` and `validate_fastq_file` already follow.
    for record_result in reader.records() {
        record_result.map_err(|e| {
            ProcessingError::with_context(
                format!("Error reading FASTQ record from file: {}", path.display()),
                e,
            )
        })?;
        count += 1;
    }

    Ok(count)
}

/// Get total sequence length in a FASTQ file
///
/// # Arguments
/// * `file_path` - Path to FASTQ file (supports `.gz` / `.bz2` / `.xz`)
///
/// # Returns
/// Total sequence length or error
pub fn total_sequence_length<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();
    let compression_type = CompressionType::from_path(path);

    // WR-15: route through the compression-aware opener so `.fastq.gz` /
    // `.bz2` / `.xz` inputs are decompressed before bio's reader parses
    // them — the same opener `process_file` and `count_sequences` use (and
    // the same fix WR-03 applied to the FASTA analogues).
    let (reader, _) = DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
        ProcessingError::with_context(
            format!(
                "Failed to open FASTQ file: {:?} ({})",
                path,
                compression_type.name()
            ),
            e,
        )
    })?;

    let reader = Reader::new(reader);
    let mut total_length = 0;

    for record_result in reader.records() {
        let record = record_result.map_err(|e| {
            ProcessingError::with_context(format!("Error reading FASTQ record: {:?}", path), e)
        })?;
        total_length += record.seq().len();
    }

    Ok(total_length)
}

/// Get average quality score in a FASTQ file
///
/// # Arguments
/// * `file_path` - Path to FASTQ file (supports `.gz` / `.bz2` / `.xz`)
///
/// # Returns
/// Mean of the raw Phred+33 ASCII quality bytes across all positions, or error
pub fn average_quality<P: AsRef<Path>>(file_path: P) -> ProcessingResult<f64> {
    let path = file_path.as_ref();
    let compression_type = CompressionType::from_path(path);

    // WR-15: route through the compression-aware opener so `.fastq.gz` /
    // `.bz2` / `.xz` inputs are decompressed before bio's reader parses
    // them — the same opener `process_file` and `count_sequences` use (and
    // the same fix WR-03 applied to the FASTA analogues).
    let (reader, _) = DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
        ProcessingError::with_context(
            format!(
                "Failed to open FASTQ file: {:?} ({})",
                path,
                compression_type.name()
            ),
            e,
        )
    })?;

    let reader = Reader::new(reader);
    let mut total_quality = 0u64;
    let mut total_positions = 0u64;

    for record_result in reader.records() {
        let record = record_result.map_err(|e| {
            ProcessingError::with_context(
                format!(
                    "Error reading FASTQ record for quality calculation: {:?}",
                    path
                ),
                e,
            )
        })?;

        for &qual in record.qual() {
            total_quality += qual as u64;
            total_positions += 1;
        }
    }

    if total_positions == 0 {
        return Err(ProcessingError::new(
            "No sequences found for quality calculation",
        ));
    }

    Ok(total_quality as f64 / total_positions as f64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::Builder;
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
        temp_file
            .write_all(b"@seq1\nATGCATGC\n+\nIIIIIIII\n@seq2\nGCTAGCTA\n+\nHHHHHHHHH\n")
            .unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        let sequences = processor.read_all().unwrap();

        assert_eq!(sequences.len(), 2);
        assert_eq!(sequences[0].id(), "seq1"); // bio crate returns ID without @ prefix
        assert_eq!(sequences[0].seq(), b"ATGCATGC");
        assert_eq!(sequences[0].qual(), b"IIIIIIII");
        assert_eq!(sequences[1].id(), "seq2"); // bio crate returns ID without @ prefix
        assert_eq!(sequences[1].seq(), b"GCTAGCTA");
        assert_eq!(sequences[1].qual(), b"HHHHHHHHH");
    }

    #[test]
    fn test_validate_fastq_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@valid_seq\nATGC\n+\nIIII\n@another_seq\nGCTA\n+\nHHHH\n")
            .unwrap();

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
        temp_file
            .write_all(b"@seq1\nATGC\n+\nIIII\n@seq2\nGCTA\n+\nHHHH\n@seq3\nATGCGAT\n+\nJJJJJJJ\n")
            .unwrap();

        let count = count_sequences(temp_file.path()).unwrap();
        assert_eq!(count, 3);
    }

    #[test]
    fn test_total_sequence_length() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@seq1\nATGCATGC\n+\nIIIIIIII\n@seq2\nGCTAGCTA\n+\nHHHHHHHH\n")
            .unwrap();

        let total_length = total_sequence_length(temp_file.path()).unwrap();
        assert_eq!(total_length, 16); // 8 + 8
    }

    #[test]
    fn test_average_quality() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@seq1\nATGC\n+\nIIII\n@seq2\nGCTA\n+\nHHHH\n")
            .unwrap();

        let avg_quality = average_quality(temp_file.path()).unwrap();
        // Average of raw ASCII values: I=73, H=72
        // (73*4 + 72*4) / 8 = 72.5
        assert!((avg_quality - 72.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_filter_by_quality() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@seq1\nATGC\n+\nIIII\n@seq2\nGCTA\n+\nHHHH\n@seq3\nNNNN\n+\nDDDD\n")
            .unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        let filtered = processor.filter_by_quality(70).unwrap();

        // Should include first two records (I=73, H=72), exclude third (D=68)
        assert_eq!(filtered.len(), 2);
        assert_eq!(filtered[0].id(), "seq1"); // bio crate returns ID without @ prefix
        assert_eq!(filtered[1].id(), "seq2");
    }

    #[test]
    fn test_read_all_sequences_concatenated_gzip_members() {
        // Regression: archive-downloaded .fastq.gz files are frequently
        // multi-member (concatenated) gzip streams. The compressed reader must
        // decode ALL members — a single-member decoder silently truncates the
        // input after the first member (observed on CRR2044018_r1.fq.gz, where
        // rustkmer counted 220,028 k-mers vs jellyfish's 4.4 B via `gzcat`).
        let member_a = b"@memA_seq1\nATGCATGC\n+\nIIIIIIII\n@memA_seq2\nGGCCTTAA\n+\nHHHHHHHH\n";
        let member_b = b"@memB_seq1\nTTACGGCA\n+\nJJJJJJJJ\n@memB_seq2\nCCGGAATT\n+\nKKKKKKKK\n@memB_seq3\nAAAATTTT\n+\nLLLLLLLL\n";

        fn gzip_bytes(payload: &[u8]) -> Vec<u8> {
            let mut encoder =
                flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
            encoder.write_all(payload).unwrap();
            encoder.finish().unwrap()
        }

        let mut concatenated = gzip_bytes(member_a);
        concatenated.extend_from_slice(&gzip_bytes(member_b));

        // Fixture sanity: exactly two independent gzip members (magic 1f 8b)
        // must be present, or this regression test proves nothing.
        let member_magic_count = concatenated.windows(2).filter(|w| w == b"\x1f\x8b").count();
        assert_eq!(
            member_magic_count, 2,
            "fixture must contain two gzip members"
        );

        // The file must be detected as gzip, so it needs the .gz extension.
        let mut temp_file = Builder::new().suffix(".gz").tempfile().unwrap();
        temp_file.write_all(&concatenated).unwrap();

        // Same read path the CLI uses: process_file -> open_compressed.
        let processor = FastqProcessor::new(temp_file.path());
        assert_eq!(processor.compression_type(), CompressionType::Gzip);
        let sequences = processor.read_all().unwrap();

        // Both members must be decoded: 2 records from A + 3 records from B.
        assert_eq!(sequences.len(), 5, "all records from BOTH gzip members");
        let ids: Vec<&str> = sequences.iter().map(|r| r.id()).collect();
        assert_eq!(
            ids,
            vec![
                "memA_seq1",
                "memA_seq2",
                "memB_seq1",
                "memB_seq2",
                "memB_seq3"
            ]
        );
        assert_eq!(sequences[2].seq(), b"TTACGGCA"); // first record of member B
        assert_eq!(sequences[2].qual(), b"JJJJJJJJ");
        assert_eq!(sequences[4].seq(), b"AAAATTTT"); // last record of member B
        assert_eq!(sequences[4].qual(), b"LLLLLLLL");
    }

    /// WR-15 regression: `total_sequence_length` and `average_quality` must
    /// transparently decompress gzipped inputs. Previously both helpers
    /// opened the raw file via plain `File::open`, so a `.fastq.gz` was
    /// parsed as deflate bytes and either errored opaquely or produced a
    /// garbage statistic — unlike every sibling FASTQ helper and the
    /// already-fixed FASTA analogues.
    #[test]
    fn test_total_length_and_average_quality_gzipped() {
        fn gzip_bytes(payload: &[u8]) -> Vec<u8> {
            let mut encoder =
                flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
            encoder.write_all(payload).unwrap();
            encoder.finish().unwrap()
        }

        // Two records with known content: quality lines of ASCII 'I' (73)
        // and 'H' (72), so the expected length sum and raw-ASCII mean are
        // exact.
        let payload = b"@seq1\nATGCATGC\n+\nIIIIIIII\n@seq2\nGCTAGCTA\n+\nHHHHHHHH\n";
        let mut temp_file = Builder::new().suffix(".gz").tempfile().unwrap();
        temp_file.write_all(&gzip_bytes(payload)).unwrap();

        // 8 + 8 = 16 decompressed bases.
        assert_eq!(
            total_sequence_length(temp_file.path()).unwrap(),
            16,
            "gzipped input must yield the exact decompressed length sum"
        );
        // (73*8 + 72*8) / 16 = 72.5 mean of raw Phred+33 ASCII bytes.
        let avg = average_quality(temp_file.path()).unwrap();
        assert!(
            (avg - 72.5).abs() < f64::EPSILON,
            "gzipped input must yield the exact decompressed raw-ASCII mean, got {avg}"
        );
    }

    /// WR-16 regression: a truncated final record (header + sequence only,
    /// no plus/quality lines) must make `count_sequences` return Err whose
    /// message carries the record-reading context naming the file — never
    /// Ok with the broken record tallied as a sequence.
    #[test]
    fn test_count_sequences_truncated_record_is_err() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@seq1\nATGC\n+\nIIII\n@broken\nATGC")
            .unwrap();

        let err = count_sequences(temp_file.path())
            .expect_err("a truncated final record must not be counted as Ok");
        let msg = err.to_string();
        assert!(
            msg.contains("Error reading FASTQ record from file"),
            "error must carry the record-reading context, got: {msg}"
        );
        assert!(
            msg.contains(temp_file.path().to_str().unwrap()),
            "error must name the offending file path, got: {msg}"
        );
    }

    /// WR-17 pin: `filter_by_quality` compares RAW Phred+33 ASCII byte
    /// values, not decoded Phred scores. ASCII 72/73 are Q39/Q40 and ASCII
    /// 43 is Q10; a threshold argument of 55 (the documented stand-in for
    /// Q20) must keep the former records and drop the latter.
    #[test]
    fn test_filter_by_quality_compares_raw_ascii_bytes() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"@q40\nATGC\n+\nIIII\n@q39\nATGC\n+\nHHHH\n@q10\nATGC\n+\n++++\n")
            .unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        let filtered = processor.filter_by_quality(55).unwrap();

        assert_eq!(
            filtered.len(),
            2,
            "threshold 55 (Q20 stand-in) keeps ASCII 73/72 records, drops ASCII 43"
        );
        assert_eq!(filtered[0].id(), "q40");
        assert_eq!(filtered[1].id(), "q39");
    }

    /// IN-12 pin: a `.fastq.gz` consisting of one valid gzip member followed
    /// by literal non-gzip trailing bytes must fail LOUDLY through the same
    /// process_file -> open_compressed path the CLI uses — the reader must
    /// not silently stop at the first member and swallow the garbage. The
    /// assertion checks this module's own record-reading context, never
    /// flate2-internal error wording (not stable across versions).
    #[test]
    fn test_read_all_errors_on_trailing_garbage_after_gzip_member() {
        fn gzip_bytes(payload: &[u8]) -> Vec<u8> {
            let mut encoder =
                flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
            encoder.write_all(payload).unwrap();
            encoder.finish().unwrap()
        }

        let member = b"@mem_seq1\nATGCATGC\n+\nIIIIIIII\n";
        let mut payload = gzip_bytes(member);
        payload.extend_from_slice(b"trailing garbage, not a gzip member");

        // The file must be detected as gzip, so it needs the .gz extension.
        let mut temp_file = Builder::new().suffix(".gz").tempfile().unwrap();
        temp_file.write_all(&payload).unwrap();

        let processor = FastqProcessor::new(temp_file.path());
        assert_eq!(processor.compression_type(), CompressionType::Gzip);

        let err = processor
            .read_all()
            .expect_err("trailing garbage after the final member must error loudly");
        let msg = err.to_string();
        assert!(
            msg.contains("Error reading FASTQ record from file"),
            "error must carry this module's record-reading context, got: {msg}"
        );
    }
}
