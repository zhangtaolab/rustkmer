//! u128 Encoding Validation Module
//!
//! This module provides comprehensive validation for u128 k-mer encoding
//! supporting all k-mer lengths from 1 to 64 bases.

use crate::kmer::encoding::{encode_kmer_u128, decode_kmer_u128, reverse_complement_u128};
use crate::kmer::canonical::canonical_kmer_u128;
use crate::error::KmerError;

/// Maximum k-mer size supported by u128 encoding
pub const MAX_KMER_SIZE: usize = 64;

/// Validate u128 encoding for all supported k-mer lengths (1-64)
pub fn validate_u128_encoding_all_lengths() -> Result<Vec<ValidationResult>, KmerError> {
    let mut results = Vec::new();

    for k in 1..=MAX_KMER_SIZE {
        let result = validate_kmer_length(k)?;
        results.push(result);
    }

    Ok(results)
}

/// Validate encoding/decoding consistency for a specific k-mer length
pub fn validate_kmer_length(k: usize) -> Result<ValidationResult, KmerError> {
    // Test sequences for this length
    let test_sequences = generate_test_sequences(k);
    let mut all_passed = true;
    let mut failed_tests = Vec::new();

    for sequence in &test_sequences {
        if let Err(e) = validate_encoding_decoding_roundtrip(sequence) {
            all_passed = false;
            failed_tests.push(format!("Sequence '{}' (k={}): {}", sequence, k, e));
        }
    }

    // Test canonical property for even and odd lengths
    if let Err(e) = validate_canonical_property(k) {
        all_passed = false;
        failed_tests.push(format!("Canonical validation (k={}): {}", k, e));
    }

    Ok(ValidationResult {
        kmer_length: k,
        total_sequences_tested: test_sequences.len(),
        all_passed,
        failed_tests,
    })
}

/// Validate that encoding and then decoding returns the original sequence
fn validate_encoding_decoding_roundtrip(sequence: &str) -> Result<(), KmerError> {
    let encoded = encode_kmer_u128(sequence)?;
    let decoded = decode_kmer_u128(encoded, sequence.len());

    if decoded.to_uppercase() == sequence.to_uppercase() {
        Ok(())
    } else {
        Err(KmerError::InvalidCharacter {
            pos: 0,
            char: 'm', // Using 'm' to indicate mismatch
        })
    }
}

/// Validate canonical property: a k-mer should be <= its reverse complement
fn validate_canonical_property(k: usize) -> Result<(), KmerError> {
    // Test with a few known sequences
    let test_cases = vec!["A".repeat(k), "C".repeat(k), "G".repeat(k), "T".repeat(k)];

    for sequence in test_cases {
        let encoded = encode_kmer_u128(&sequence)?;
        let canonical = canonical_kmer_u128(encoded, k)
            .map_err(|_| KmerError::InvalidCharacter { pos: 0, char: 'c' })?;
        let rev_comp = reverse_complement_u128(encoded, k);

        // Canonical should be the smaller of the two
        if canonical != encoded.min(rev_comp) {
            return Err(KmerError::InvalidCharacter {
                pos: 0,
                char: 'c', // Using 'c' to indicate canonical error
            });
        }
    }

    Ok(())
}

/// Generate test sequences for a given k-mer length
fn generate_test_sequences(k: usize) -> Vec<String> {
    let mut sequences = Vec::new();

    // Edge cases
    if k <= 64 {
        sequences.push("A".repeat(k));
        sequences.push("C".repeat(k));
        sequences.push("G".repeat(k));
        sequences.push("T".repeat(k));
    }

    // Mixed patterns
    if k >= 2 {
        sequences.push("AC".repeat(k / 2) + &"AC"[..k % 2]);
        sequences.push("GT".repeat(k / 2) + &"GT"[..k % 2]);
    }

    if k >= 4 {
        sequences.push("ATCG".repeat(k / 4) + &"ATCG"[..k % 4]);
    }

    // Random-like pattern for diversity
    let base_pattern = "ATGCATGC";
    sequences.push(base_pattern.chars().cycle().take(k).collect());

    sequences
}

/// Result of validation for a specific k-mer length
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub kmer_length: usize,
    pub total_sequences_tested: usize,
    pub all_passed: bool,
    pub failed_tests: Vec<String>,
}

/// Comprehensive validation report
#[derive(Debug, Clone)]
pub struct ValidationReport {
    pub max_kmer_length: usize,
    pub total_lengths_tested: usize,
    pub results: Vec<ValidationResult>,
    pub summary: ValidationSummary,
}

impl ValidationReport {
    /// Generate a comprehensive validation report
    pub fn generate() -> Result<Self, KmerError> {
        let results = validate_u128_encoding_all_lengths()?;
        let total_lengths_tested = results.len();
        let max_kmer_length = MAX_KMER_SIZE;

        let all_passed = results.iter().all(|r| r.all_passed);
        let failed_lengths = results.iter().filter(|r| !r.all_passed).count();
        let total_sequences_tested = results.iter().map(|r| r.total_sequences_tested).sum();
        let total_failures = results.iter().map(|r| r.failed_tests.len()).sum();

        let summary = ValidationSummary {
            all_passed,
            failed_lengths,
            total_sequences_tested,
            total_failures,
        };

        Ok(ValidationReport {
            max_kmer_length,
            total_lengths_tested,
            results,
            summary,
        })
    }

    /// Print a formatted summary of the validation results
    pub fn print_summary(&self) {
        println!("=== u128 Encoding Validation Report ===");
        println!("Max k-mer length supported: {}", self.max_kmer_length);
        println!("Total lengths tested: {}", self.total_lengths_tested);
        println!("Total sequences tested: {}", self.summary.total_sequences_tested);
        println!("Total failures: {}", self.summary.total_failures);

        if self.summary.all_passed {
            println!("✅ All validations passed!");
        } else {
            println!("❌ {} length(s) had failures", self.summary.failed_lengths);

            for result in &self.results {
                if !result.all_passed {
                    println!("  k={} ({} failed tests):", result.kmer_length, result.failed_tests.len());
                    for failure in &result.failed_tests {
                        println!("    - {}", failure);
                    }
                }
            }
        }
    }
}

/// Summary of validation results
#[derive(Debug, Clone)]
pub struct ValidationSummary {
    pub all_passed: bool,
    pub failed_lengths: usize,
    pub total_sequences_tested: usize,
    pub total_failures: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_basic_lengths() {
        let report = ValidationReport::generate().unwrap();
        assert_eq!(report.max_kmer_length, 64);
        assert!(report.total_lengths_tested > 0);
    }

    #[test]
    fn test_encoding_decoding_consistency() {
        let test_cases = vec![
            ("A", 1),
            ("ATCG", 4),
            ("ATCGATCGATCGATCGATCGATCGATCGATCG", 32),
            ("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", 36),
        ];

        for (sequence, expected_k) in test_cases {
            let encoded = encode_kmer_u128(sequence).unwrap();
            let decoded = decode_kmer_u128(encoded, sequence.len());
            assert_eq!(decoded.to_uppercase(), sequence.to_uppercase());
            assert_eq!(sequence.len(), expected_k);
        }
    }

    #[test]
    fn test_canonical_property() {
        let sequence = "ATCGATCG";
        let k = sequence.len();
        let encoded = encode_kmer_u128(sequence).unwrap();
        let canonical = canonical_kmer_u128(encoded, k).unwrap();
        let rev_comp = reverse_complement_u128(encoded, k);

        assert_eq!(canonical, encoded.min(rev_comp));
    }
}