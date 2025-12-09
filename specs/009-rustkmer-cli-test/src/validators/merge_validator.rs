//! Merge command validator for RustKmer CLI testing
//!
//! This module provides validation functionality for the merge command,
//! including database compatibility checks and merged result verification.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};
use crate::error::TestError;

/// Merge validation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeValidationResult {
    /// Whether the merge operation was successful
    pub success: bool,
    /// Source database files
    pub source_databases: Vec<String>,
    /// Output database file
    pub output_database: String,
    /// Validation errors
    pub errors: Vec<String>,
    /// Validation warnings
    pub warnings: Vec<String>,
    /// Performance metrics
    pub metrics: MergeMetrics,
}

/// Merge performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeMetrics {
    /// Total execution time in seconds
    pub execution_time_secs: f64,
    /// Size of output database in bytes
    pub output_size_bytes: u64,
    /// Total k-mers in merged database
    pub total_kmers: u64,
    /// Unique k-mers in merged database
    pub unique_kmers: u64,
    /// Memory usage during merge (if available)
    pub memory_usage_mb: Option<f64>,
}

/// Database compatibility info
#[derive(Debug, Clone)]
pub struct DatabaseCompatibility {
    /// Whether databases are compatible for merging
    pub compatible: bool,
    /// Common k-mer size across all databases
    pub kmer_size: Option<usize>,
    /// Compatibility issues
    pub issues: Vec<String>,
}

/// Merge validator configuration
#[derive(Debug, Clone)]
pub struct MergeValidatorConfig {
    /// Strict mode validation
    pub strict_mode: bool,
    /// Performance threshold in seconds
    pub performance_threshold_secs: f64,
    /// Whether to verify k-mer counts
    pub verify_counts: bool,
}

impl Default for MergeValidatorConfig {
    fn default() -> Self {
        Self {
            strict_mode: false,
            performance_threshold_secs: 300.0, // 5 minutes
            verify_counts: true,
        }
    }
}

/// Merge validator
pub struct MergeValidator {
    config: MergeValidatorConfig,
}

impl MergeValidator {
    /// Create a new merge validator
    pub fn new(config: MergeValidatorConfig) -> Self {
        Self { config }
    }

    /// Create a validator with default config
    pub fn default() -> Self {
        Self::new(MergeValidatorConfig::default())
    }

    /// Validate database compatibility for merging
    pub fn validate_compatibility(&self, database_paths: &[PathBuf]) -> Result<DatabaseCompatibility, TestError> {
        if database_paths.is_empty() {
            return Ok(DatabaseCompatibility {
                compatible: false,
                kmer_size: None,
                issues: vec!["No databases provided".to_string()],
            });
        }

        if database_paths.len() < 2 {
            return Ok(DatabaseCompatibility {
                compatible: false,
                kmer_size: None,
                issues: vec!["At least two databases required for merging".to_string()],
            });
        }

        let mut compatibility = DatabaseCompatibility {
            compatible: true,
            kmer_size: None,
            issues: Vec::new(),
        };

        // Check if all databases exist
        for path in database_paths {
            if !path.exists() {
                compatibility.compatible = false;
                compatibility.issues.push(format!("Database file does not exist: {:?}", path));
            }
        }

        // Try to determine k-mer size from filenames
        let mut kmer_sizes = Vec::new();
        for path in database_paths {
            if let Some(filename) = path.file_name().and_then(|n| n.to_str()) {
                if filename.contains("k21") {
                    kmer_sizes.push(21);
                } else if filename.contains("k31") {
                    kmer_sizes.push(31);
                } else if filename.contains("k63") {
                    kmer_sizes.push(63);
                } else if filename.contains("k64") {
                    kmer_sizes.push(64);
                } else {
                    kmer_sizes.push(0); // Unknown
                }
            }
        }

        // Check if all k-mer sizes are the same (excluding unknown)
        let known_sizes: Vec<_> = kmer_sizes.iter().filter(|&&s| s > 0).collect();
        if !known_sizes.is_empty() {
            let first_size = known_sizes[0];
            if !known_sizes.iter().all(|&&size| size == first_size) {
                compatibility.compatible = false;
                compatibility.issues.push(
                    "Databases have different k-mer sizes".to_string()
                );
            } else {
                compatibility.kmer_size = Some(*first_size);
            }
        }

        Ok(compatibility)
    }

    /// Validate merge operation results
    pub fn validate_merge(
        &self,
        source_databases: &[PathBuf],
        output_database: &PathBuf,
        execution_time_secs: f64,
    ) -> Result<MergeValidationResult, TestError> {
        let mut result = MergeValidationResult {
            success: true,
            source_databases: source_databases
                .iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect(),
            output_database: output_database.to_string_lossy().to_string(),
            errors: Vec::new(),
            warnings: Vec::new(),
            metrics: MergeMetrics {
                execution_time_secs,
                output_size_bytes: 0,
                total_kmers: 0,
                unique_kmers: 0,
                memory_usage_mb: None,
            },
        };

        // Check if output file was created
        if !output_database.exists() {
            result.success = false;
            result.errors.push("Output database file was not created".to_string());
            return Ok(result);
        }

        // Get file size
        if let Ok(metadata) = fs::metadata(output_database) {
            result.metrics.output_size_bytes = metadata.len();
        } else {
            result.warnings.push("Could not get output file metadata".to_string());
        }

        // Check performance
        if execution_time_secs > self.config.performance_threshold_secs {
            result.warnings.push(format!(
                "Merge operation took {:.2}s, exceeding threshold of {:.2}s",
                execution_time_secs, self.config.performance_threshold_secs
            ));
        }

        // Try to get statistics from output database
        if self.config.verify_counts {
            if let Some(stats) = self.get_database_stats(output_database)? {
                result.metrics.total_kmers = stats.get("total").unwrap_or(&0).clone();
                result.metrics.unique_kmers = stats.get("unique").unwrap_or(&0).clone();
            } else {
                result.warnings.push("Could not verify k-mer counts in merged database".to_string());
            }
        }

        // Validate that merged database contains data from sources
        if result.metrics.total_kmers == 0 && !result.errors.is_empty() {
            result.warnings.push("Merged database appears to be empty".to_string());
        }

        Ok(result)
    }

    /// Get statistics from a database file
    fn get_database_stats(&self, database_path: &Path) -> Result<Option<HashMap<String, u64>>, TestError> {
        // This would use the stats command when implemented
        // For now, return None
        Ok(None)
    }

    /// Generate a validation report
    pub fn generate_report(&self, results: &[MergeValidationResult]) -> String {
        let mut report = String::new();

        report.push_str("# Merge Validation Report\n\n");

        let total_tests = results.len();
        let successful_tests = results.iter().filter(|r| r.success).count();
        let success_rate = if total_tests > 0 {
            (successful_tests as f64 / total_tests as f64) * 100.0
        } else {
            0.0
        };

        report.push_str(&format!(
            "## Summary\n\n- Total tests: {}\n- Successful: {}\n- Failed: {}\n- Success rate: {:.1}%\n\n",
            total_tests,
            successful_tests,
            total_tests - successful_tests,
            success_rate
        ));

        // Performance summary
        if !results.is_empty() {
            let total_time: f64 = results.iter().map(|r| r.metrics.execution_time_secs).sum();
            let avg_time = total_time / total_tests as f64;
            let total_size: u64 = results.iter().map(|r| r.metrics.output_size_bytes).sum();

            report.push_str(&format!(
                "## Performance Summary\n\n- Average execution time: {:.2}s\n- Total output size: {} MB\n\n",
                avg_time,
                total_size / 1024 / 1024
            ));
        }

        // Detailed results
        report.push_str("## Detailed Results\n\n");

        for (i, result) in results.iter().enumerate() {
            report.push_str(&format!("### Test {}\n\n", i + 1));

            if result.success {
                report.push_str("✅ **PASSED**\n\n");
            } else {
                report.push_str("❌ **FAILED**\n\n");
            }

            report.push_str(&format!(
                "- Source databases: {}\n- Output database: {}\n- Execution time: {:.2}s\n- Output size: {} MB\n",
                result.source_databases.len(),
                Path::new(&result.output_database)
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("unknown"),
                result.metrics.execution_time_secs,
                result.metrics.output_size_bytes / 1024 / 1024
            ));

            if !result.errors.is_empty() {
                report.push_str("\n**Errors:**\n");
                for error in &result.errors {
                    report.push_str(&format!("- {}\n", error));
                }
                report.push_str("\n");
            }

            if !result.warnings.is_empty() {
                report.push_str("\n**Warnings:**\n");
                for warning in &result.warnings {
                    report.push_str(&format!("- {}\n", warning));
                }
                report.push_str("\n");
            }

            report.push_str("---\n\n");
        }

        report
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_validate_compatibility_no_databases() {
        let validator = MergeValidator::default();
        let result = validator.validate_compatibility(&[]).unwrap();

        assert!(!result.compatible);
        assert!(result.issues.iter().any(|i| i.contains("No databases")));
    }

    #[test]
    fn test_validate_compatibility_single_database() {
        let validator = MergeValidator::default();
        let temp_dir = tempdir().unwrap();
        let db_path = temp_dir.path().join("test.rkdb");

        let result = validator.validate_compatibility(&[db_path]).unwrap();

        assert!(!result.compatible);
        assert!(result.issues.iter().any(|i| i.contains("two databases")));
    }

    #[test]
    fn test_validate_compatibility_nonexistent() {
        let validator = MergeValidator::default();
        let db1 = PathBuf::from("/nonexistent/db1.rkdb");
        let db2 = PathBuf::from("/nonexistent/db2.rkdb");

        let result = validator.validate_compatibility(&[db1, db2]).unwrap();

        assert!(!result.compatible);
        assert_eq!(result.issues.len(), 2);
    }
}