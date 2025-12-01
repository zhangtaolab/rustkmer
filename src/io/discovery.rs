//! File discovery and directory traversal for RustKmer
//!
//! This module provides functionality for discovering sequence files in directories,
//! with support for recursive traversal, file type filtering, and metadata collection.

use std::path::{Path, PathBuf};
use walkdir::{WalkDir, DirEntry};
use crate::error::KmerError;


/// File type enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FileType {
    Fasta,
    Fastq,
}

impl FileType {
    /// Get file type from file extension
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_lowercase().as_str() {
            "fa" | "fasta" | "fna" | "ffn" => Some(FileType::Fasta),
            "fq" | "fastq" => Some(FileType::Fastq),
            _ => None,
        }
    }

    /// Get supported extensions for this file type
    pub fn extensions(self) -> &'static [&'static str] {
        match self {
            FileType::Fasta => &["fa", "fasta", "fna", "ffn"],
            FileType::Fastq => &["fq", "fastq"],
        }
    }
}

/// Information about a discovered file
#[derive(Debug, Clone)]
pub struct FileInfo {
    pub path: PathBuf,
    pub size: u64,
    pub file_type: FileType,
    pub extension: String,
    pub is_compressed: bool,
}

impl FileInfo {
    /// Create file info from a directory entry
    pub fn from_entry(entry: &DirEntry) -> Result<Self, KmerError> {
        let path = entry.path();
        let metadata = entry.metadata()
            .map_err(|e| KmerError::Io(e.into()))?;

        if !metadata.is_file() {
            return Err(KmerError::ProcessingError("Path is not a file".to_string()));
        }

        let size = metadata.len();
        let file_name = path.file_name()
            .and_then(|name| name.to_str())
            .ok_or_else(|| KmerError::ProcessingError("Invalid file name".to_string()))?;

        // Handle double extensions like .fa.gz
        let (extension, is_compressed) = if let Some(stem) = file_name.strip_suffix(".gz") {
            if let Some(ext) = Path::new(stem).extension().and_then(|e| e.to_str()) {
                (ext.to_string(), true)
            } else {
                return Err(KmerError::ProcessingError("Invalid compressed file extension".to_string()));
            }
        } else {
            let ext = path.extension()
                .and_then(|e| e.to_str())
                .ok_or_else(|| KmerError::ProcessingError("Missing file extension".to_string()))?;
            (ext.to_string(), false)
        };

        let file_type = FileType::from_extension(&extension)
            .ok_or_else(|| KmerError::ProcessingError(format!("Unsupported file type: {}", extension)))?;

        Ok(FileInfo {
            path: path.to_path_buf(),
            size,
            file_type,
            extension,
            is_compressed,
        })
    }

    /// Get display name (file name with size)
    pub fn display_name(&self) -> String {
        let name = self.path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("invalid_name");

        let size_str = if self.size >= 1_000_000_000 {
            format!("{:.1}GB", self.size as f64 / 1_000_000_000.0)
        } else if self.size >= 1_000_000 {
            format!("{:.1}MB", self.size as f64 / 1_000_000.0)
        } else if self.size >= 1_000 {
            format!("{:.1}KB", self.size as f64 / 1_000.0)
        } else {
            format!("{}B", self.size)
        };

        format!("{} ({})", name, size_str)
    }
}

/// File discovery configuration
#[derive(Debug, Clone)]
pub struct DiscoveryConfig {
    /// Whether to search recursively
    pub recursive: bool,
    /// Maximum depth for recursive search (None = unlimited)
    pub max_depth: Option<usize>,
    /// Whether to follow symbolic links
    pub follow_symlinks: bool,
    /// Minimum file size to include (bytes)
    pub min_size: Option<u64>,
    /// Maximum file size to include (bytes)
    pub max_size: Option<u64>,
}

impl Default for DiscoveryConfig {
    fn default() -> Self {
        Self {
            recursive: true,
            max_depth: None,
            follow_symlinks: false,
            min_size: None,
            max_size: None,
        }
    }
}

/// File discovery engine
pub struct FileDiscovery {
    config: DiscoveryConfig,
}

impl FileDiscovery {
    /// Create new file discovery instance
    pub fn new(config: DiscoveryConfig) -> Self {
        Self { config }
    }

    /// Discover files in a directory
    pub fn discover(&self, directory: &Path) -> Result<Vec<FileInfo>, KmerError> {
        if !directory.exists() {
            return Err(KmerError::FileNotFound(format!("Directory does not exist: {}", directory.display())));
        }

        if !directory.is_dir() {
            return Err(KmerError::InvalidArgument(format!("Path is not a directory: {}", directory.display())));
        }

        let mut walkdir = WalkDir::new(directory);

        if !self.config.recursive {
            walkdir = walkdir.max_depth(1);
        } else if let Some(max_depth) = self.config.max_depth {
            walkdir = walkdir.max_depth(max_depth);
        }

        if self.config.follow_symlinks {
            walkdir = walkdir.follow_links(true);
        }

        let mut files = Vec::new();
        let mut total_size = 0u64;
        let mut file_counts = std::collections::HashMap::new();

        for entry in walkdir.into_iter() {
            let entry = entry.map_err(|e| {
                KmerError::Io(e.into())
            })?;

            // Skip directories and hidden files
            if !entry.file_type().is_file() {
                continue;
            }

            let file_name = entry.file_name();
            if file_name.to_string_lossy().starts_with('.') {
                continue; // Skip hidden files
            }

            // Try to create file info, skip unsupported files
            match FileInfo::from_entry(&entry) {
                Ok(file_info) => {
                    // Apply size filters
                    if let Some(min_size) = self.config.min_size {
                        if file_info.size < min_size {
                            continue;
                        }
                    }

                    if let Some(max_size) = self.config.max_size {
                        if file_info.size > max_size {
                            continue;
                        }
                    }

                    total_size += file_info.size;
                    *file_counts.entry(file_info.file_type).or_insert(0) += 1;
                    files.push(file_info);
                }
                Err(_) => {
                    // Skip unsupported files silently
                    continue;
                }
            }
        }

        // Sort files by path for consistent ordering
        files.sort_by(|a, b| a.path.cmp(&b.path));

        println!("[INFO] Found {} files in {}:", files.len(), directory.display());
        for (file_type, count) in file_counts {
            let type_name = match file_type {
                FileType::Fasta => "FASTA",
                FileType::Fastq => "FASTQ",
            };
            let extensions: Vec<&str> = file_type.extensions().to_vec();
            println!("  • {} {} files ({})", count, type_name, extensions.join(", "));
        }

        if total_size > 0 {
            let size_str = if total_size >= 1_000_000_000 {
                format!("{:.1}GB", total_size as f64 / 1_000_000_000.0)
            } else if total_size >= 1_000_000 {
                format!("{:.1}MB", total_size as f64 / 1_000_000.0)
            } else if total_size >= 1_000 {
                format!("{:.1}KB", total_size as f64 / 1_000.0)
            } else {
                format!("{}B", total_size)
            };
            println!("  • Total size: {}", size_str);
        }

        Ok(files)
    }

    /// Get summary statistics for discovered files
    pub fn get_summary(&self, files: &[FileInfo]) -> FileSummary {
        let mut total_size = 0u64;
        let mut file_counts = std::collections::HashMap::new();
        let mut compressed_count = 0;

        for file in files {
            total_size += file.size;
            *file_counts.entry(file.file_type).or_insert(0) += 1;
            if file.is_compressed {
                compressed_count += 1;
            }
        }

        FileSummary {
            total_files: files.len(),
            total_size,
            file_counts,
            compressed_count,
        }
    }
}

/// Summary statistics for discovered files
#[derive(Debug)]
pub struct FileSummary {
    pub total_files: usize,
    pub total_size: u64,
    pub file_counts: std::collections::HashMap<FileType, usize>,
    pub compressed_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_file_type_from_extension() {
        assert_eq!(FileType::from_extension("fa"), Some(FileType::Fasta));
        assert_eq!(FileType::from_extension("fasta"), Some(FileType::Fasta));
        assert_eq!(FileType::from_extension("fq"), Some(FileType::Fastq));
        assert_eq!(FileType::from_extension("fastq"), Some(FileType::Fastq));
        assert_eq!(FileType::from_extension("txt"), None);
    }

    #[test]
    fn test_file_type_extensions() {
        assert!(FileType::Fasta.extensions().contains(&"fa"));
        assert!(FileType::Fasta.extensions().contains(&"fasta"));
        assert!(FileType::Fastq.extensions().contains(&"fq"));
        assert!(FileType::Fastq.extensions().contains(&"fastq"));
    }

    #[test]
    fn test_display_name() {
        let file_info = FileInfo {
            path: PathBuf::from("/test/file.fa"),
            size: 1024 * 1024, // 1MB
            file_type: FileType::Fasta,
            extension: "fa".to_string(),
            is_compressed: false,
        };

        assert!(file_info.display_name().contains("file.fa"));
        assert!(file_info.display_name().contains("1.0MB"));
    }

    #[test]
    fn test_discovery_config_default() {
        let config = DiscoveryConfig::default();
        assert!(config.recursive);
        assert!(config.max_depth.is_none());
        assert!(!config.follow_symlinks);
        assert!(config.min_size.is_none());
        assert!(config.max_size.is_none());
    }
}