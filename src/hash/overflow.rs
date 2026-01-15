//! Disk-based overflow storage for k-mer counting
//!
//! Provides temporary disk storage when hash table memory is insufficient.

use std::fs::{self, File};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};

use crate::error::{ProcessingError, ProcessingResult};

/// Disk overflow storage for k-mer counts
#[derive(Debug)]
pub struct DiskOverflow {
    /// Directory for overflow files
    temp_dir: PathBuf,
    /// Current file writer
    current_writer: Option<BufWriter<File>>,
    /// Current file number
    current_file: u32,
    /// Number of k-mers stored
    kmer_count: u64,
    /// Maximum records per file before creating a new file
    records_per_file: usize,
}

impl DiskOverflow {
    /// Create new disk overflow storage
    ///
    /// # Arguments
    /// * `temp_dir` - Directory for temporary files
    ///
    /// # Returns
    /// New DiskOverflow instance or error
    pub fn new<P: AsRef<Path>>(temp_dir: P) -> ProcessingResult<Self> {
        let temp_dir = temp_dir.as_ref().to_path_buf();

        // Create directory if it doesn't exist
        fs::create_dir_all(&temp_dir)?;

        Ok(Self {
            temp_dir,
            current_writer: None,
            current_file: 0,
            kmer_count: 0,
            records_per_file: 1_000_000, // 1 million records per file
        })
    }

    /// Store a k-mer count in overflow storage
    ///
    /// # Arguments
    /// * `kmer_encoded` - Packed k-mer representation
    /// * `count` - K-mer count
    ///
    /// # Returns
    /// Result indicating success or error
    pub fn store(&mut self, kmer_encoded: u64, count: u32) -> ProcessingResult<()> {
        // Initialize writer if needed
        if self.current_writer.is_none() {
            self.new_file()?;
        }

        if let Some(ref mut writer) = self.current_writer {
            // Write k-mer (8 bytes) and count (4 bytes)
            writer.write_all(&kmer_encoded.to_le_bytes())?;
            writer.write_all(&count.to_le_bytes())?;

            self.kmer_count += 1;

            // Check if we need a new file
            if self.kmer_count.is_multiple_of(self.records_per_file as u64) {
                self.close_current_file()?;
                self.current_file += 1;
            }
        }

        Ok(())
    }

    /// Create a new overflow file
    fn new_file(&mut self) -> ProcessingResult<()> {
        let file_path = self
            .temp_dir
            .join(format!("overflow_{:04}.dat", self.current_file));
        let file = File::create(&file_path)?;

        self.current_writer = Some(BufWriter::new(file));
        Ok(())
    }

    /// Close current overflow file
    fn close_current_file(&mut self) -> ProcessingResult<()> {
        if let Some(mut writer) = self.current_writer.take() {
            writer.flush()?;
            writer.get_mut().sync_all()?;
        }
        Ok(())
    }

    /// Close all files and cleanup
    pub fn close(&mut self) -> ProcessingResult<()> {
        self.close_current_file()?;
        Ok(())
    }

    /// Get total number of stored k-mers
    pub fn kmer_count(&self) -> u64 {
        self.kmer_count
    }

    /// Get approximate size in bytes
    pub fn size_bytes(&self) -> u64 {
        // Each record is 12 bytes (8 + 4)
        self.kmer_count * 12
    }

    /// Read back all stored k-mers (for testing/retrieval)
    ///
    /// # Returns
    /// Iterator over (kmer_encoded, count) pairs
    pub fn read_all(&self) -> impl Iterator<Item = ProcessingResult<(u64, u32)>> {
        let files = self.list_overflow_files();

        OverflowFileReader::new(files)
    }

    /// List all overflow files
    fn list_overflow_files(&self) -> Vec<PathBuf> {
        let mut files = Vec::new();

        if let Ok(entries) = fs::read_dir(&self.temp_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(name) = path.file_name() {
                    if let Some(name_str) = name.to_str() {
                        if name_str.starts_with("overflow_") && name_str.ends_with(".dat") {
                            files.push(path);
                        }
                    }
                }
            }
        }

        files.sort(); // Ensure consistent order
        files
    }
}

impl Drop for DiskOverflow {
    fn drop(&mut self) {
        let _ = self.close();
    }
}

/// Iterator for reading overflow files
struct OverflowFileReader {
    files: Vec<PathBuf>,
    current_file: usize,
    current_reader: Option<std::io::BufReader<File>>,
    pos: u64,
}

impl OverflowFileReader {
    fn new(files: Vec<PathBuf>) -> Self {
        Self {
            files,
            current_file: 0,
            current_reader: None,
            pos: 0,
        }
    }

    fn advance_to_next_file(&mut self) -> ProcessingResult<bool> {
        // Close current reader
        self.current_reader = None;

        // Move to next file
        if self.current_file < self.files.len() {
            let file_path = &self.files[self.current_file];
            let file = File::open(file_path)?;
            self.current_reader = Some(std::io::BufReader::new(file));
            self.current_file += 1;
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

impl Iterator for OverflowFileReader {
    type Item = ProcessingResult<(u64, u32)>;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            // Open first file if needed
            if self.current_reader.is_none() && !self.files.is_empty() {
                if let Err(e) = self.advance_to_next_file() {
                    return Some(Err(ProcessingError::with_context(
                        "Failed to open overflow file",
                        e,
                    )));
                }
            }

            // Return None if no files left
            self.current_reader.as_ref()?;

            // Try to read from current file
            if let Some(ref mut reader) = self.current_reader {
                let mut buffer = [0u8; 12];

                match reader.read_exact(&mut buffer) {
                    Ok(_) => {
                        // Parse k-mer and count
                        let kmer = u64::from_le_bytes([
                            buffer[0], buffer[1], buffer[2], buffer[3], buffer[4], buffer[5],
                            buffer[6], buffer[7],
                        ]);
                        let count =
                            u32::from_le_bytes([buffer[8], buffer[9], buffer[10], buffer[11]]);

                        self.pos += 1;
                        return Some(Ok((kmer, count)));
                    }
                    Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => {
                        // End of current file, advance to next
                        match self.advance_to_next_file() {
                            Ok(true) => continue,     // Try next file
                            Ok(false) => return None, // No more files
                            Err(e) => {
                                return Some(Err(ProcessingError::with_context(
                                    "Error advancing files",
                                    e,
                                )))
                            }
                        }
                    }
                    Err(e) => {
                        return Some(Err(ProcessingError::with_context(
                            "Error reading overflow file",
                            e,
                        )));
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_disk_overflow_basic() {
        let temp_dir = TempDir::new().unwrap();
        let mut overflow = DiskOverflow::new(temp_dir.path()).unwrap();

        // Store some k-mers
        overflow.store(0x12345678, 10).unwrap();
        overflow.store(0x87654321, 20).unwrap();

        assert_eq!(overflow.kmer_count(), 2);

        overflow.close().unwrap();
    }

    #[test]
    fn test_disk_overflow_read_back() {
        let temp_dir = TempDir::new().unwrap();
        let mut overflow = DiskOverflow::new(temp_dir.path()).unwrap();

        // Store some k-mers
        overflow.store(0x12345678, 10).unwrap();
        overflow.store(0x87654321, 20).unwrap();
        overflow.close().unwrap();

        // Read them back
        let overflow_read = DiskOverflow::new(temp_dir.path()).unwrap();
        let pairs: Vec<_> = overflow_read.read_all().collect();

        assert_eq!(pairs.len(), 2);
        assert_eq!(pairs[0].as_ref().unwrap(), &(0x12345678, 10));
        assert_eq!(pairs[1].as_ref().unwrap(), &(0x87654321, 20));
    }

    #[test]
    fn test_overflow_size() {
        let temp_dir = TempDir::new().unwrap();
        let mut overflow = DiskOverflow::new(temp_dir.path()).unwrap();

        assert_eq!(overflow.size_bytes(), 0);

        overflow.store(0x12345678, 10).unwrap();
        assert_eq!(overflow.size_bytes(), 12);

        overflow.store(0x87654321, 20).unwrap();
        assert_eq!(overflow.size_bytes(), 24);
    }
}
