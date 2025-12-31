//! Temporary file management utilities for testing

use std::fs;
use std::path::{Path, PathBuf};
use tempfile::{NamedTempFile, TempDir};
use thiserror::Error;
use rustkmer::database::format::RKDatabase;

/// Result type for temporary file operations
pub type TempFileResult<T> = Result<T, TempFileError>;

/// Error type for temporary file operations
#[derive(Debug, Error)]
pub enum TempFileError {
    #[error("Failed to create temporary file: {0}")]
    CreationFailed(String),
    #[error("Failed to write to temporary file: {0}")]
    WriteFailed(String),
    #[error("Failed to read from temporary file: {0}")]
    ReadFailed(String),
    #[error("Temporary file path not available")]
    PathNotAvailable,
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Temporary file manager for tests
pub struct TempFileManager {
    _temp_dir: Option<TempDir>,
    files: Vec<PathBuf>,
}

impl TempFileManager {
    /// Create a new temporary file manager with a dedicated temporary directory
    pub fn new() -> TempFileResult<Self> {
        let temp_dir = TempDir::new()
            .map_err(|e| TempFileError::CreationFailed(format!("Failed to create temp dir: {}", e)))?;

        Ok(Self {
            _temp_dir: Some(temp_dir),
            files: Vec::new(),
        })
    }

    /// Create a temporary file manager that uses the system temp directory
    pub fn new_with_system_temp() -> Self {
        Self {
            _temp_dir: None,
            files: Vec::new(),
        }
    }

    /// Create a temporary file with the given content
    pub fn create_temp_file(&mut self, content: &[u8], extension: &str) -> TempFileResult<PathBuf> {
        let temp_file = NamedTempFile::with_suffix(extension)
            .map_err(|e| TempFileError::CreationFailed(format!("Failed to create temp file: {}", e)))?;

        let path = temp_file.path().to_path_buf();

        // Write content
        fs::write(&path, content)
            .map_err(|e| TempFileError::WriteFailed(format!("Failed to write temp file: {}", e)))?;

        // Keep the temp file by not dropping temp_file
        temp_file.keep().map_err(|e| {
            // Try to remove the file if keep fails
            let _ = fs::remove_file(&path);
            TempFileError::CreationFailed(format!("Failed to keep temp file: {}", e))
        })?;

        self.files.push(path.clone());
        Ok(path)
    }

    /// Create a temporary file with text content
    pub fn create_temp_text_file(&mut self, content: &str, extension: &str) -> TempFileResult<PathBuf> {
        self.create_temp_file(content.as_bytes(), extension)
    }

    /// Create a temporary FASTA file
    pub fn create_temp_fasta(&mut self, sequences: &[(String, String)]) -> TempFileResult<PathBuf> {
        let mut fasta_content = String::new();
        for (header, sequence) in sequences {
            fasta_content.push_str(&format!(">{}\n{}\n", header, sequence));
        }

        self.create_temp_text_file(&fasta_content, ".fasta")
    }

    /// Create a temporary FASTQ file
    pub fn create_temp_fastq(&mut self, reads: &[(String, String, String)]) -> TempFileResult<PathBuf> {
        let mut fastq_content = String::new();
        for (header, sequence, quality) in reads {
            fastq_content.push_str(&format!("@{}\n{}\n+\n{}\n", header, sequence, quality));
        }

        self.create_temp_text_file(&fastq_content, ".fastq")
    }

    /// Save a database to a temporary file
    pub fn save_database_to_temp(&mut self, db: &RKDatabase) -> TempFileResult<PathBuf> {
        let temp_path = self.create_temp_file(&[], ".rkdb")?;

        db.to_file_path(&temp_path)
            .map_err(|e| TempFileError::WriteFailed(format!("Failed to save database: {}", e)))?;

        Ok(temp_path)
    }

    /// Create a temporary file with random binary data
    pub fn create_temp_binary(&mut self, size: usize) -> TempFileResult<PathBuf> {
        use rand::RngCore;
        let mut rng = rand::thread_rng();
        let mut data = vec![0u8; size];
        rng.fill_bytes(&mut data);

        self.create_temp_file(&data, ".bin")
    }

    /// Get the path of an existing temporary file by index
    pub fn get_file_path(&self, index: usize) -> Option<&PathBuf> {
        self.files.get(index)
    }

    /// Get all temporary file paths
    pub fn get_all_paths(&self) -> &[PathBuf] {
        &self.files
    }

    /// Read the content of a temporary file
    pub fn read_temp_file(&self, path: &Path) -> TempFileResult<Vec<u8>> {
        fs::read(path)
            .map_err(|e| TempFileError::ReadFailed(format!("Failed to read temp file: {}", e)))
    }

    /// Read the text content of a temporary file
    pub fn read_temp_text_file(&self, path: &Path) -> TempFileResult<String> {
        fs::read_to_string(path)
            .map_err(|e| TempFileError::ReadFailed(format!("Failed to read temp file text: {}", e)))
    }

    /// Get file size
    pub fn get_file_size(&self, path: &Path) -> TempFileResult<u64> {
        fs::metadata(path)
            .map_err(|e| TempFileError::ReadFailed(format!("Failed to get file metadata: {}", e)))
            .map(|m| m.len())
    }

    /// Check if a file exists
    pub fn file_exists(&self, path: &Path) -> bool {
        path.exists()
    }

    /// Count files managed
    pub fn file_count(&self) -> usize {
        self.files.len()
    }

    /// Clean up all temporary files immediately
    pub fn cleanup(&mut self) -> TempFileResult<()> {
        for path in &self.files {
            if path.exists() {
                fs::remove_file(path)
                    .map_err(|e| TempFileError::CreationFailed(format!("Failed to remove temp file: {}", e)))?;
            }
        }
        self.files.clear();
        Ok(())
    }
}

impl Drop for TempFileManager {
    fn drop(&mut self) {
        // Best effort cleanup - don't panic if cleanup fails
        let _ = self.cleanup();
    }
}

/// Convenience function to create a temporary directory
pub fn create_temp_dir() -> TempFileResult<TempDir> {
    TempDir::new()
        .map_err(|e| TempFileError::CreationFailed(format!("Failed to create temp directory: {}", e)))
}

/// Convenience function to create a temporary file with content
pub fn create_temp_file_with_content(content: &[u8], suffix: &str) -> TempFileResult<PathBuf> {
    let mut manager = TempFileManager::new_with_system_temp();
    manager.create_temp_file(content, suffix)
}

/// Convenience function to create multiple temporary files
pub fn create_multiple_temp_files(contents: &[&[u8]], suffix: &str) -> TempFileResult<Vec<PathBuf>> {
    let mut manager = TempFileManager::new_with_system_temp();
    let mut paths = Vec::new();

    for content in contents {
        paths.push(manager.create_temp_file(content, suffix)?);
    }

    Ok(paths)
}

/// Macro for quickly creating temporary files in tests
#[macro_export]
macro_rules! temp_file {
    ($content:expr) => {
        create_temp_file_with_content($content.as_bytes(), ".tmp")
    };
    ($content:expr, $suffix:expr) => {
        create_temp_file_with_content($content.as_bytes(), $suffix)
    };
}

/// Macro for creating temporary FASTA files
#[macro_export]
macro_rules! temp_fasta {
    ($($header:expr => $seq:expr),*) => {{
        let sequences = vec![$(($header.to_string(), $seq.to_string())),*];
        let mut manager = TempFileManager::new_with_system_temp();
        manager.create_temp_fasta(&sequences)
    }};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_temp_file_manager_creation() {
        let manager = TempFileManager::new();
        assert!(manager.is_ok());
        assert_eq!(manager.unwrap().file_count(), 0);
    }

    #[test]
    fn test_create_temp_text_file() {
        let mut manager = TempFileManager::new_with_system_temp();
        let content = "Hello, World!";
        let path = manager.create_temp_text_file(content, ".txt").unwrap();

        assert!(manager.file_exists(&path));
        let read_content = manager.read_temp_text_file(&path).unwrap();
        assert_eq!(read_content, content);
    }

    #[test]
    fn test_create_temp_binary_file() {
        let mut manager = TempFileManager::new_with_system_temp();
        let data = vec![1, 2, 3, 4, 5];
        let path = manager.create_temp_file(&data, ".bin").unwrap();

        assert!(manager.file_exists(&path));
        let read_data = manager.read_temp_file(&path).unwrap();
        assert_eq!(read_data, data);
    }

    #[test]
    fn test_create_temp_fasta() {
        let mut manager = TempFileManager::new_with_system_temp();
        let sequences = vec![
            ("seq1".to_string(), "ATCG".to_string()),
            ("seq2".to_string(), "GCTA".to_string()),
        ];

        let path = manager.create_temp_fasta(&sequences).unwrap();
        let content = manager.read_temp_text_file(&path).unwrap();

        assert!(content.contains(">seq1"));
        assert!(content.contains("ATCG"));
        assert!(content.contains(">seq2"));
        assert!(content.contains("GCTA"));
    }

    #[test]
    fn test_create_temp_fastq() {
        let mut manager = TempFileManager::new_with_system_temp();
        let reads = vec![
            ("read1".to_string(), "ATCG".to_string(), "IIII".to_string()),
            ("read2".to_string(), "GCTA".to_string(), "IIII".to_string()),
        ];

        let path = manager.create_temp_fastq(&reads).unwrap();
        let content = manager.read_temp_text_file(&path).unwrap();

        assert!(content.contains("@read1"));
        assert!(content.contains("ATCG"));
        assert!(content.contains("+"));
        assert!(content.contains("IIII"));
    }

    #[test]
    fn test_file_size() {
        let mut manager = TempFileManager::new_with_system_temp();
        let content = "Hello, World!";
        let path = manager.create_temp_text_file(content, ".txt").unwrap();

        let size = manager.get_file_size(&path).unwrap();
        assert_eq!(size, content.len() as u64);
    }

    #[test]
    fn test_multiple_files() {
        let mut manager = TempFileManager::new_with_system_temp();

        let path1 = manager.create_temp_text_file("Content 1", ".txt").unwrap();
        let path2 = manager.create_temp_text_file("Content 2", ".txt").unwrap();

        assert_eq!(manager.file_count(), 2);
        assert!(manager.file_exists(&path1));
        assert!(manager.file_exists(&path2));

        let paths = manager.get_all_paths();
        assert_eq!(paths.len(), 2);
    }

    #[test]
    fn test_cleanup() {
        let mut manager = TempFileManager::new_with_system_temp();
        let path = manager.create_temp_text_file("Test", ".txt").unwrap();

        assert!(manager.file_exists(&path));
        manager.cleanup().unwrap();
        assert_eq!(manager.file_count(), 0);
        assert!(!manager.file_exists(&path));
    }

    #[test]
    fn test_convenience_functions() {
        let path = temp_file!("test content", ".txt").unwrap();
        assert!(path.exists());

        let fasta_path = temp_fasta!("header1" => "ATCG", "header2" => "GCTA").unwrap();
        assert!(fasta_path.exists());
    }

    #[test]
    fn test_create_multiple_temp_files() {
        let contents = vec!["content1".as_bytes(), "content2".as_bytes(), "content3".as_bytes()];
        let paths = create_multiple_temp_files(&contents, ".txt").unwrap();

        assert_eq!(paths.len(), 3);
        for path in &paths {
            assert!(path.exists());
        }
    }
}