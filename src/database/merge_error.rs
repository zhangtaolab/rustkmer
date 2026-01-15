//! Comprehensive error handling for merge operations
//!
//! This module provides detailed error types for database merge operations,
//! enabling better error reporting and recovery suggestions.

use std::error::Error;
use thiserror::Error;

/// Comprehensive error types for merge operations
#[derive(Debug, Error)]
pub enum MergeError {
    /// No input databases provided
    #[error("No input databases provided. At least one database is required for merge operation.")]
    EmptyInput,

    /// Database compatibility issues
    #[error("Database compatibility error: {details}")]
    IncompatibleDatabase {
        details: String,
        #[source]
        source: Option<Box<dyn Error + Send + Sync>>,
    },

    /// I/O error during database operations
    #[error("I/O error accessing database '{path}': {message}")]
    IOError {
        path: String,
        message: String,
        #[source]
        source: std::io::Error,
    },

    /// Memory allocation error during merge
    #[error(
        "Insufficient memory for merge operation. Required: {required}MB, Available: {available}MB"
    )]
    InsufficientMemory { required: u64, available: u64 },

    /// K-mer count overflow during merge
    #[error("K-mer count overflow for k-mer {kmer:X}. Current count: {current}, Additional: {additional}")]
    CountOverflow {
        kmer: u128,
        current: u32,
        additional: u32,
    },

    /// Invalid database format
    #[error("Invalid database format in '{path}': {reason}")]
    InvalidFormat { path: String, reason: String },

    /// Merge operation interrupted
    #[error("Merge operation interrupted: {reason}")]
    Interrupted { reason: String },

    /// Temporary file operation failed
    #[error("Temporary file operation failed: {operation} on '{path}': {error}")]
    TempFileError {
        operation: String,
        path: String,
        error: String,
    },

    /// Concurrent modification detected
    #[error("Concurrent modification detected on database '{path}' during merge")]
    ConcurrentModification { path: String },

    /// Configuration error
    #[error("Invalid merge configuration: {details}")]
    Configuration { details: String },
}

impl MergeError {
    /// Check if this is a recoverable error
    pub fn is_recoverable(&self) -> bool {
        match self {
            MergeError::EmptyInput => false,
            MergeError::IncompatibleDatabase { .. } => true,
            MergeError::IOError { .. } => true,
            MergeError::InsufficientMemory { .. } => true,
            MergeError::CountOverflow { .. } => false,
            MergeError::InvalidFormat { .. } => false,
            MergeError::Interrupted { .. } => true,
            MergeError::TempFileError { .. } => true,
            MergeError::ConcurrentModification { .. } => false,
            MergeError::Configuration { .. } => true,
        }
    }

    /// Get recovery suggestions for this error
    pub fn recovery_suggestions(&self) -> Vec<String> {
        match self {
            MergeError::EmptyInput => vec![
                "Provide At least one input database for merge operation".to_string(),
                "Use 'rustkmer merge --help' to see usage examples".to_string(),
            ],

            MergeError::IncompatibleDatabase { details, .. } => {
                let mut suggestions = vec![
                    "Ensure all databases have the same k-mer size".to_string(),
                    "Ensure all databases have the same canonical mode setting".to_string(),
                    "Use 'rustkmer stats <database>' to check database parameters".to_string(),
                ];

                if details.contains("k-mer size") {
                    suggestions.push("Create new databases with matching k-mer sizes".to_string());
                }

                if details.contains("canonical") {
                    suggestions.push("Use --canonical or --no-canonical consistently".to_string());
                }

                suggestions
            }

            MergeError::IOError { path, .. } => vec![
                format!("Check if database file '{}' exists and is readable", path),
                "Verify file permissions and disk space".to_string(),
            ],

            MergeError::InsufficientMemory {
                required,
                available,
            } => vec![
                format!(
                    "Free up memory: need {}MB but only {}MB available",
                    required, available
                ),
                "Try merging smaller databases or use --force to enable streaming mode".to_string(),
                "Close other applications to free memory".to_string(),
            ],

            MergeError::CountOverflow {
                kmer,
                current,
                additional,
            } => vec![
                format!(
                    "K-mer {kmer:X} has count {} which would overflow with additional {}",
                    current, additional
                ),
                "Consider using larger integer types or filter out high-count k-mers".to_string(),
            ],

            MergeError::InvalidFormat { path, reason } => vec![
                format!("Database '{}' appears to be corrupted: {}", path, reason),
                "Try recreating the database from source data".to_string(),
                "Verify the file was not truncated during transfer".to_string(),
            ],

            MergeError::Interrupted { reason } => vec![
                format!("Operation was interrupted: {}", reason),
                "Check disk space and system resources".to_string(),
                "The merge can be resumed if temporary files are preserved".to_string(),
            ],

            MergeError::TempFileError {
                operation,
                path,
                error,
            } => vec![
                format!("{} failed on '{}': {}", operation, path, error),
                "Check temporary directory permissions".to_string(),
                "Ensure sufficient disk space for temporary files".to_string(),
            ],

            MergeError::ConcurrentModification { path } => vec![
                format!("Database '{}' was modified during merge", path),
                "Retry the merge operation when no other processes are accessing the databases"
                    .to_string(),
                "Consider using file locking to prevent concurrent access".to_string(),
            ],

            MergeError::Configuration { details } => vec![
                format!("Fix configuration: {}", details),
                "Use 'rustkmer merge --help' to see valid options".to_string(),
            ],
        }
    }

    /// Get a user-friendly error message with context
    pub fn user_friendly_message(&self) -> String {
        let base = self.to_string();

        if self.is_recoverable() {
            let suggestions = self.recovery_suggestions();
            if !suggestions.is_empty() {
                format!(
                    "{}\n\nRecovery suggestions:\n{}",
                    base,
                    suggestions
                        .iter()
                        .map(|s| format!("  • {}", s))
                        .collect::<Vec<_>>()
                        .join("\n")
                )
            } else {
                base
            }
        } else {
            base
        }
    }
}

/// Result type for merge operations
pub type MergeResult<T> = Result<T, MergeError>;

/// Convert from standard processing error
impl From<crate::error::ProcessingError> for MergeError {
    fn from(err: crate::error::ProcessingError) -> Self {
        MergeError::InvalidFormat {
            path: "unknown".to_string(),
            reason: err.to_string(),
        }
    }
}

/// Convert from I/O error
impl From<std::io::Error> for MergeError {
    fn from(err: std::io::Error) -> Self {
        MergeError::IOError {
            path: "unknown".to_string(),
            message: err.to_string(),
            source: err,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_recoverable_errors() {
        assert!(MergeError::IncompatibleDatabase {
            details: "test".to_string(),
            source: None,
        }
        .is_recoverable());

        assert!(!MergeError::CountOverflow {
            kmer: 0,
            current: u32::MAX,
            additional: 1,
        }
        .is_recoverable());
    }

    #[test]
    fn test_recovery_suggestions() {
        let error = MergeError::EmptyInput;
        let suggestions = error.recovery_suggestions();
        assert!(!suggestions.is_empty());
        assert!(suggestions[0].contains("At least one"));
    }
}
