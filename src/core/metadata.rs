//! Database metadata management for JSON serialization and persistence

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

/// Error types for metadata operations
#[derive(Debug, Error)]
pub enum MetadataError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("JSON serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Invalid metadata: {0}")]
    InvalidMetadata(String),

    #[error("Version mismatch: expected {expected}, got {actual}")]
    VersionMismatch { expected: String, actual: String },

    #[error("Checksum validation failed")]
    ChecksumError,
}

/// Database metadata structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseMetadata {
    /// Metadata format version
    pub version: String,

    /// Database creation timestamp
    pub created_at: u64,

    /// Last modification timestamp
    pub modified_at: u64,

    /// k-mer size used for this database
    pub kmer_size: usize,

    /// Whether k-mers are stored in canonical form
    pub canonical: bool,

    /// Total number of k-mers processed (including duplicates)
    pub total_kmers: u64,

    /// Number of unique k-mers in the database
    pub unique_kmers: u64,

    /// Source files used to create this database
    pub source_files: Vec<String>,

    /// Database creation parameters
    pub parameters: DatabaseParameters,

    /// Performance statistics
    pub performance: PerformanceStats,

    /// Database format information
    pub format: FormatInfo,

    /// Additional custom metadata
    pub custom: HashMap<String, serde_json::Value>,
}

/// Database creation parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseParameters {
    /// Normalization method (canonical, none, etc.)
    pub normalization: String,

    /// Whether to use counting or just presence/absence
    pub counting_mode: String,

    /// Compression settings
    pub compression: CompressionSettings,

    /// Threading parameters
    pub threading: ThreadingParameters,

    /// Memory usage limits
    pub memory_limits: MemoryLimits,
}

impl Default for DatabaseParameters {
    fn default() -> Self {
        Self {
            normalization: "canonical".to_string(),
            counting_mode: "full".to_string(),
            compression: CompressionSettings::default(),
            threading: ThreadingParameters::default(),
            memory_limits: MemoryLimits::default(),
        }
    }
}

/// Compression settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionSettings {
    /// Whether compression is enabled
    pub enabled: bool,

    /// Compression algorithm
    pub algorithm: String,

    /// Compression level (0-9)
    pub level: u8,
}

impl Default for CompressionSettings {
    fn default() -> Self {
        Self {
            enabled: true,
            algorithm: "gzip".to_string(),
            level: 6,
        }
    }
}

/// Threading parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreadingParameters {
    /// Number of threads used
    pub thread_count: usize,

    /// Thread affinity settings
    pub thread_affinity: Option<String>,

    /// Parallel processing strategy
    pub parallel_strategy: String,
}

impl Default for ThreadingParameters {
    fn default() -> Self {
        Self {
            thread_count: std::thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(1),
            thread_affinity: None,
            parallel_strategy: "auto".to_string(),
        }
    }
}

/// Memory limits configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryLimits {
    /// Maximum memory usage in bytes
    pub max_memory_bytes: u64,

    /// Buffer size for streaming operations
    pub buffer_size: usize,

    /// Whether memory-mapped files are used
    pub use_mmap: bool,
}

impl Default for MemoryLimits {
    fn default() -> Self {
        Self {
            max_memory_bytes: 8 * 1024 * 1024 * 1024, // 8GB
            buffer_size: 1024 * 1024,                 // 1MB
            use_mmap: true,
        }
    }
}

/// Performance statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceStats {
    /// Time taken to create the database (seconds)
    pub creation_time_seconds: f64,

    /// Peak memory usage during creation (bytes)
    pub peak_memory_bytes: u64,

    /// Processing rate (k-mers per second)
    pub processing_rate: f64,

    /// Number of files processed
    pub files_processed: usize,

    /// Total input size in bytes
    pub input_size_bytes: u64,

    /// Total output size in bytes
    pub output_size_bytes: u64,

    /// Compression ratio
    pub compression_ratio: f64,
}

impl Default for PerformanceStats {
    fn default() -> Self {
        Self {
            creation_time_seconds: 0.0,
            peak_memory_bytes: 0,
            processing_rate: 0.0,
            files_processed: 0,
            input_size_bytes: 0,
            output_size_bytes: 0,
            compression_ratio: 1.0,
        }
    }
}

impl PerformanceStats {
    pub fn calculate_compression_ratio(&mut self) {
        if self.input_size_bytes > 0 {
            self.compression_ratio = self.input_size_bytes as f64 / self.output_size_bytes as f64;
        }
    }

    pub fn calculate_processing_rate(&mut self, total_kmers: u64) {
        if self.creation_time_seconds > 0.0 {
            self.processing_rate = total_kmers as f64 / self.creation_time_seconds;
        }
    }
}

/// Database format information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormatInfo {
    /// Database format name
    pub format_name: String,

    /// Format version
    pub format_version: String,

    /// Endianness of binary data
    pub endianness: String,

    /// Checksum algorithm used
    pub checksum_algorithm: String,

    /// File layout description
    pub layout: FileLayout,
}

impl Default for FormatInfo {
    fn default() -> Self {
        Self {
            format_name: "rkdb".to_string(),
            format_version: "1.0".to_string(),
            endianness: "little".to_string(),
            checksum_algorithm: "sha256".to_string(),
            layout: FileLayout::default(),
        }
    }
}

/// File layout description
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileLayout {
    /// Name of metadata file
    pub metadata_file: String,

    /// Name of main data file
    pub data_file: String,

    /// Optional index file name
    pub index_file: Option<String>,

    /// Additional auxiliary files
    pub auxiliary_files: Vec<String>,
}

impl Default for FileLayout {
    fn default() -> Self {
        Self {
            metadata_file: "metadata.json".to_string(),
            data_file: "data.rkdb".to_string(),
            index_file: Some("index.rkdb".to_string()),
            auxiliary_files: vec!["checksums.txt".to_string()],
        }
    }
}

impl DatabaseMetadata {
    /// Create new database metadata with default values
    pub fn new(kmer_size: usize, canonical: bool) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        Self {
            version: "1.0".to_string(),
            created_at: now,
            modified_at: now,
            kmer_size,
            canonical,
            total_kmers: 0,
            unique_kmers: 0,
            source_files: Vec::new(),
            parameters: DatabaseParameters::default(),
            performance: PerformanceStats::default(),
            format: FormatInfo::default(),
            custom: HashMap::new(),
        }
    }

    /// Update the modification timestamp
    pub fn update_timestamp(&mut self) {
        self.modified_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
    }

    /// Add a source file
    pub fn add_source_file(&mut self, file_path: &str) {
        self.update_timestamp();
        if !self.source_files.contains(&file_path.to_string()) {
            self.source_files.push(file_path.to_string());
        }
    }

    /// Set performance statistics
    pub fn set_performance_stats(&mut self, stats: PerformanceStats) {
        self.update_timestamp();
        self.performance = stats;
    }

    /// Add custom metadata
    pub fn add_custom_metadata(&mut self, key: String, value: serde_json::Value) {
        self.update_timestamp();
        self.custom.insert(key, value);
    }

    /// Validate the metadata structure
    pub fn validate(&self) -> Result<(), MetadataError> {
        if self.version.is_empty() {
            return Err(MetadataError::InvalidMetadata(
                "Version cannot be empty".to_string(),
            ));
        }

        if self.kmer_size == 0 {
            return Err(MetadataError::InvalidMetadata(
                "k-mer size must be > 0".to_string(),
            ));
        }

        if self.kmer_size > 127 {
            return Err(MetadataError::InvalidMetadata(
                "k-mer size must be <= 127".to_string(),
            ));
        }

        if self.total_kmers < self.unique_kmers {
            return Err(MetadataError::InvalidMetadata(
                "Total k-mers cannot be less than unique k-mers".to_string(),
            ));
        }

        // Validate format info
        if self.format.format_name.is_empty() {
            return Err(MetadataError::InvalidMetadata(
                "Format name cannot be empty".to_string(),
            ));
        }

        Ok(())
    }

    /// Generate checksum for the metadata
    pub fn generate_checksum(&self) -> Result<String, MetadataError> {
        let json_str = serde_json::to_string(self)?;
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(json_str.as_bytes());
        Ok(format!("{:x}", hasher.finalize()))
    }
}

/// Metadata schema for validation and migration
#[derive(Debug, Clone)]
pub struct MetadataSchema {
    current_version: String,
    supported_versions: Vec<String>,
}

impl MetadataSchema {
    pub fn new() -> Self {
        Self {
            current_version: "1.0".to_string(),
            supported_versions: vec!["1.0".to_string()],
        }
    }

    pub fn validate_version(&self, metadata: &DatabaseMetadata) -> Result<(), MetadataError> {
        if !self.supported_versions.contains(&metadata.version) {
            return Err(MetadataError::VersionMismatch {
                expected: self.current_version.clone(),
                actual: metadata.version.clone(),
            });
        }
        Ok(())
    }

    pub fn current_version(&self) -> &str {
        &self.current_version
    }
}

impl Default for MetadataSchema {
    fn default() -> Self {
        Self::new()
    }
}

/// Create new metadata with automatic configuration
pub fn create_metadata(
    kmer_size: usize,
    canonical: bool,
    source_files: Vec<String>,
) -> DatabaseMetadata {
    let mut metadata = DatabaseMetadata::new(kmer_size, canonical);

    for file in source_files {
        metadata.add_source_file(&file);
    }

    // Detect optimal threading parameters
    metadata.parameters.threading = ThreadingParameters::default();

    metadata
}

/// Save metadata to JSON file
pub fn save_metadata<P: AsRef<Path>>(
    metadata: &DatabaseMetadata,
    path: P,
) -> Result<(), MetadataError> {
    // Validate before saving
    metadata.validate()?;

    // Create pretty-printed JSON
    let json_str = serde_json::to_string_pretty(metadata)?;

    // Write to file
    std::fs::write(path, json_str)?;

    Ok(())
}

/// Load metadata from JSON file
pub fn load_metadata<P: AsRef<Path>>(path: P) -> Result<DatabaseMetadata, MetadataError> {
    let json_str = std::fs::read_to_string(path)?;
    let metadata: DatabaseMetadata = serde_json::from_str(&json_str)?;

    // Validate loaded metadata
    metadata.validate()?;

    Ok(metadata)
}

/// Validate metadata file and return validation results
pub fn validate_metadata<P: AsRef<Path>>(path: P) -> Result<ValidationResult, MetadataError> {
    let metadata = load_metadata(path)?;
    let schema = MetadataSchema::default();

    let mut result = ValidationResult::new();

    // Check version compatibility
    if let Err(e) = schema.validate_version(&metadata) {
        result.add_error(format!("Version validation failed: {}", e));
    }

    // Validate metadata structure
    if let Err(e) = metadata.validate() {
        result.add_error(format!("Structure validation failed: {}", e));
    }

    // Additional custom validations
    if metadata.kmer_size > 63 {
        result.add_warning("Large k-mer size (>63) may impact performance".to_string());
    }

    if metadata.total_kmers == 0 {
        result.add_warning("No k-mers recorded in database".to_string());
    }

    if metadata.performance.creation_time_seconds == 0.0 {
        result.add_warning("No performance metrics available".to_string());
    }

    Ok(result)
}

/// Validation result structure
#[derive(Debug, Clone)]
pub struct ValidationResult {
    is_valid: bool,
    errors: Vec<String>,
    warnings: Vec<String>,
}

impl Default for ValidationResult {
    fn default() -> Self {
        Self::new()
    }
}

impl ValidationResult {
    pub fn new() -> Self {
        Self {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    pub fn add_error(&mut self, error: String) {
        self.is_valid = false;
        self.errors.push(error);
    }

    pub fn add_warning(&mut self, warning: String) {
        self.warnings.push(warning);
    }

    pub fn is_valid(&self) -> bool {
        self.is_valid
    }

    pub fn errors(&self) -> &[String] {
        &self.errors
    }

    pub fn warnings(&self) -> &[String] {
        &self.warnings
    }
}

/// Get metadata file path for a database directory
pub fn get_metadata_path(database_dir: &Path) -> PathBuf {
    database_dir.join("metadata.json")
}

/// Check if metadata file exists
pub fn metadata_exists<P: AsRef<Path>>(database_dir: P) -> bool {
    get_metadata_path(database_dir.as_ref()).exists()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_metadata_creation() {
        let metadata = create_metadata(21, true, vec!["test.fa".to_string()]);

        assert_eq!(metadata.kmer_size, 21);
        assert!(metadata.canonical);
        assert_eq!(metadata.source_files.len(), 1);
        assert!(metadata.validate().is_ok());
    }

    #[test]
    fn test_metadata_serialization() {
        let metadata = create_metadata(
            31,
            false,
            vec!["test1.fq".to_string(), "test2.fq".to_string()],
        );

        let json_str = serde_json::to_string(&metadata).unwrap();
        let deserialized: DatabaseMetadata = serde_json::from_str(&json_str).unwrap();

        assert_eq!(metadata.kmer_size, deserialized.kmer_size);
        assert_eq!(metadata.canonical, deserialized.canonical);
        assert_eq!(metadata.source_files, deserialized.source_files);
    }

    #[test]
    fn test_metadata_save_load() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("metadata.json");

        let original = create_metadata(15, true, vec!["test.fa".to_string()]);
        save_metadata(&original, &file_path).unwrap();

        let loaded = load_metadata(&file_path).unwrap();
        assert_eq!(original.kmer_size, loaded.kmer_size);
        assert_eq!(original.canonical, loaded.canonical);
        assert_eq!(original.source_files, loaded.source_files);
    }

    #[test]
    fn test_metadata_validation() {
        let mut metadata = create_metadata(21, true, vec![]);

        // Valid metadata
        assert!(metadata.validate().is_ok());

        // Invalid k-mer size
        metadata.kmer_size = 0;
        assert!(metadata.validate().is_err());

        metadata.kmer_size = 128;
        assert!(metadata.validate().is_err());

        // Invalid k-mer counts
        metadata.kmer_size = 21;
        metadata.total_kmers = 10;
        metadata.unique_kmers = 20;
        assert!(metadata.validate().is_err());
    }
}
