//! Memory-mapped file operations
//!
//! Provides memory-mapped file reading for large genomic datasets.

use memmap2::{Mmap, MmapOptions};
use std::fs::File;
use std::io::Read;
use std::path::Path;

use crate::error::{ProcessingError, ProcessingResult};

/// Memory-mapped file reader for efficient large file processing
#[derive(Debug)]
pub struct MemoryMappedFile {
    mmap: Mmap,
}

impl MemoryMappedFile {
    /// Open a file as memory-mapped
    ///
    /// # Arguments
    /// * `path` - Path to the file
    ///
    /// # Returns
    /// MemoryMappedFile instance or error
    pub fn open<P: AsRef<Path>>(path: P) -> ProcessingResult<Self> {
        let file = File::open(path)?;
        let mmap = unsafe { MmapOptions::new().map(&file)? };

        Ok(Self { mmap })
    }

    /// Get a slice of the memory-mapped data
    ///
    /// # Returns
    /// Slice of the file contents
    pub fn as_slice(&self) -> &[u8] {
        &self.mmap
    }

    /// Get length of the mapped file
    ///
    /// # Returns
    /// File length in bytes
    pub fn len(&self) -> usize {
        self.mmap.len()
    }

    /// Check if the file is empty
    ///
    /// # Returns
    /// True if file is empty
    pub fn is_empty(&self) -> bool {
        self.mmap.is_empty()
    }

    /// Get an iterator over lines in the file
    ///
    /// # Returns
    /// Iterator over line slices
    pub fn lines(&self) -> impl Iterator<Item = &[u8]> + '_ {
        self.as_slice().split(|&b| b == b'\n')
    }

    /// Read file into a String (for smaller files)
    ///
    /// # Returns
    /// String containing file contents
    pub fn read_to_string(&self) -> Result<String, std::string::FromUtf8Error> {
        String::from_utf8(self.as_slice().to_vec())
    }
}

/// Read a file into memory (with fallback for small files)
///
/// # Arguments
/// * `path` - Path to the file
///
/// # Returns
/// String containing file contents
pub fn read_file_to_string<P: AsRef<Path>>(path: P) -> ProcessingResult<String> {
    let path = path.as_ref();

    // Try memory-mapped first for efficiency
    if let Ok(mmap_file) = MemoryMappedFile::open(path) {
        mmap_file.read_to_string().map_err(|e| {
            ProcessingError::with_context(format!("Failed to read file as UTF-8: {:?}", path), e)
        })
    } else {
        // Fallback to regular file reading
        let mut contents = String::new();
        let mut file = File::open(path).map_err(|e| {
            ProcessingError::with_context(format!("Failed to open file: {:?}", path), e)
        })?;

        file.read_to_string(&mut contents).map_err(|e| {
            ProcessingError::with_context(format!("Failed to read file: {:?}", path), e)
        })?;

        Ok(contents)
    }
}

/// Get file size efficiently
///
/// # Arguments
/// * `path` - Path to the file
///
/// # Returns
/// File size in bytes
pub fn file_size<P: AsRef<Path>>(path: P) -> ProcessingResult<u64> {
    let path_ref = path.as_ref();
    let metadata = std::fs::metadata(path_ref).map_err(|e| {
        ProcessingError::with_context(format!("Failed to get file metadata: {:?}", path_ref), e)
    })?;

    Ok(metadata.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_memory_mapped_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file
            .write_all(b"ATGCATGCATGC\nATGCATGCATGC\n")
            .unwrap();

        let mmap_file = MemoryMappedFile::open(temp_file.path()).unwrap();
        assert_eq!(mmap_file.len(), 26); // 12 + 1 + 12 + 1

        let content = mmap_file.read_to_string().unwrap();
        assert_eq!(content, "ATGCATGCATGC\nATGCATGCATGC\n");
    }

    #[test]
    fn test_file_lines() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all(b"line1\nline2\nline3\n").unwrap();

        let mmap_file = MemoryMappedFile::open(temp_file.path()).unwrap();
        let lines: Vec<_> = mmap_file.lines().collect();

        assert_eq!(lines.len(), 4); // Includes empty line at end
        assert_eq!(lines[0], b"line1");
        assert_eq!(lines[1], b"line2");
        assert_eq!(lines[2], b"line3");
        assert_eq!(lines[3], b"");
    }

    #[test]
    fn test_read_file_to_string() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all(b"ATGCATGC").unwrap();

        let content = read_file_to_string(temp_file.path()).unwrap();
        assert_eq!(content, "ATGCATGC");
    }

    #[test]
    fn test_file_size() {
        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all(b"ATGCATGC").unwrap();

        let size = file_size(temp_file.path()).unwrap();
        assert_eq!(size, 8);
    }
}
