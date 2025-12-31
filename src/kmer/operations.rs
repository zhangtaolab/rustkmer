//! K-mer extraction and processing operations
//!
//! Provides functions for extracting k-mers from DNA sequences with proper
//! validation and filtering according to requirements.

use crate::error::KmerError;
use crate::kmer::encoding::{encode_kmer, has_ambiguous_bases};

/// Extract all k-mers from a DNA sequence using sliding window
///
/// # Arguments
/// * `sequence` - DNA sequence string
/// * `kmer_size` - Length of k-mers to extract
///
/// # Returns
/// * `Vec<u64>` - Vector of packed k-mer representations
/// * `Err(KmerError)` - Error if sequence is too short or invalid
///
/// # Examples
/// ```
/// use rustkmer::kmer::operations::extract_kmers;
///
/// let kmers = extract_kmers("ATGCGAT", 3).unwrap();
/// assert_eq!(kmers.len(), 6); // "ATG", "TGC", "GCG", "CGA", "GAT", "ATG"
/// ```
pub fn extract_kmers(sequence: &str, kmer_size: usize) -> Result<Vec<u64>, KmerError> {
    if kmer_size == 0 {
        return Err(KmerError::InvalidKmerSize(0));
    }

    let sequence_len = sequence.len();
    if sequence_len < kmer_size {
        return Err(KmerError::SequenceTooShort {
            length: sequence_len,
            min_required: kmer_size,
            kmer_size,
        });
    }

    // Skip sequences with ambiguous bases according to requirements
    if has_ambiguous_bases(sequence) {
        return Ok(Vec::new());
    }

    let mut kmers = Vec::with_capacity(sequence_len - kmer_size + 1);

    // Extract k-mers using sliding window
    for i in 0..=sequence_len - kmer_size {
        let kmer_str = &sequence[i..i + kmer_size];
        match encode_kmer(kmer_str) {
            Ok(encoded) => kmers.push(encoded),
            Err(e) => {
                // Log the error but continue processing other k-mers
                eprintln!("Warning: Skipping k-mer at position {}: {}", i, e);
            }
        }
    }

    Ok(kmers)
}

/// Extract k-mers from a sequence, skipping those with ambiguous bases
///
/// This function implements the requirement to skip k-mers containing ambiguous bases (N)
/// rather than skipping the entire sequence.
///
/// # Arguments
/// * `sequence` - DNA sequence string
/// * `kmer_size` - Length of k-mers to extract
///
/// # Returns
/// Vector of packed k-mer representations, excluding any containing ambiguous bases
pub fn extract_kmers_filter_ambiguous(sequence: &str, kmer_size: usize) -> Vec<u64> {
    let sequence_len = sequence.len();
    if sequence_len < kmer_size {
        return Vec::new();
    }

    let mut kmers = Vec::new();

    for i in 0..=sequence_len - kmer_size {
        let kmer_str = &sequence[i..i + kmer_size];

        // Check for ambiguous bases in this k-mer
        if has_ambiguous_bases(kmer_str) {
            continue; // Skip k-mer with ambiguous bases
        }

        if let Ok(encoded) = encode_kmer(kmer_str) {
            kmers.push(encoded);
        }
    }

    kmers
}

/// Filter a sequence by checking if it contains valid DNA and sufficient length
///
/// # Arguments
/// * `sequence` - DNA sequence string
/// * `kmer_size` - Minimum required length
///
/// # Returns
/// `true` if sequence is valid and long enough, `false` otherwise
pub fn filter_sequence(sequence: &str, kmer_size: usize) -> bool {
    // Check minimum length requirement
    if sequence.len() < kmer_size {
        return false;
    }

    // Check for valid DNA characters (allow lowercase)
    sequence.chars().all(|ch| {
        let ch = ch.to_ascii_uppercase();
        matches!(ch, 'A' | 'C' | 'G' | 'T')
    })
}

/// Count the number of valid k-mers that can be extracted from a sequence
///
/// # Arguments
/// * `sequence` - DNA sequence string
/// * `kmer_size` - Length of k-mers
///
/// # Returns
/// Number of extractable k-mers (accounting for invalid regions)
pub fn count_extractable_kmers(sequence: &str, kmer_size: usize) -> usize {
    let sequence_len = sequence.len();
    if sequence_len < kmer_size {
        return 0;
    }

    let mut count = 0;

    for i in 0..=sequence_len - kmer_size {
        let kmer_str = &sequence[i..i + kmer_size];

        // Count only k-mers without ambiguous bases
        if !has_ambiguous_bases(kmer_str) {
            count += 1;
        }
    }

    count
}

/// Analyze sequence quality and provide statistics
///
/// # Arguments
/// * `sequence` - DNA sequence string
///
/// # Returns
/// String with quality statistics
pub fn analyze_sequence_quality(sequence: &str) -> String {
    let total_len = sequence.len();
    let valid_bases = sequence.chars()
        .filter(|ch| matches!(ch.to_ascii_uppercase(), 'A' | 'C' | 'G' | 'T'))
        .count();
    let invalid_bases = total_len - valid_bases;
    let ambiguous_count = sequence.chars()
        .filter(|ch| ch.eq_ignore_ascii_case(&'N'))
        .count();

    format!(
        "Length: {} | Valid: {} | Invalid: {} | Ambiguous (N): {} | Quality: {:.1}%",
        total_len,
        valid_bases,
        invalid_bases,
        ambiguous_count,
        if total_len > 0 {
            (valid_bases as f64 / total_len as f64) * 100.0
        } else {
            0.0
        }
    )
}

/// Compute reverse complement of a k-mer (bit manipulation)
///
/// # Arguments
/// * `kmer` - Packed k-mer representation
/// * `k` - K-mer length
///
/// # Returns
/// Reverse complement k-mer or error if k is too large
pub fn reverse_complement_bits(kmer: u64, k: usize) -> Result<u64, KmerError> {
    if k > 32 {
        return Err(KmerError::InvalidKmerSize(k as u32));
    }

    let mut result = 0u64;
    let mut input = kmer;

    for _ in 0..k {
        // Get the last 2 bits (one base)
        let base = input & 0b11;

        // Complement: A(00) -> T(11), C(01) -> G(10), G(10) -> C(01), T(11) -> A(00)
        let complement = base ^ 0b11;

        // Shift result left and add complemented base
        result <<= 2;
        result |= complement;

        // Shift input right to process next base
        input >>= 2;
    }

    Ok(result)
}

/// Compute reverse complement of a DNA sequence string
///
/// # Arguments
/// * `sequence` - DNA sequence string
///
/// # Returns
/// Reverse complement string
pub fn reverse_complement(sequence: &str) -> String {
    sequence
        .chars()
        .rev()
        .map(|ch| match ch.to_ascii_uppercase() {
            'A' => 'T',
            'T' => 'A',
            'G' => 'C',
            'C' => 'G',
            'N' => 'N', // Ambiguous base remains ambiguous
            _ => 'N',   // Invalid characters become N
        })
        .collect()
}

/// Get canonical k-mer (lexicographically smaller of forward and reverse complement)
///
/// # Arguments
/// * `kmer_encoded` - Packed k-mer representation
/// * `k` - K-mer length
///
/// # Returns
/// Canonical k-mer encoding or error if k is too large
pub fn canonical_kmer(kmer_encoded: u64, k: usize) -> Result<u64, KmerError> {
    let rev_comp = reverse_complement_bits(kmer_encoded, k)?;
    Ok(if kmer_encoded <= rev_comp {
        kmer_encoded
    } else {
        rev_comp
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_kmers_simple() {
        let sequence = "ATGCGAT";
        let kmers = extract_kmers(sequence, 3).unwrap();
        assert_eq!(kmers.len(), 5); // 7 - 3 + 1 = 5
    }

    #[test]
    fn test_extract_kmers_short_sequence() {
        let sequence = "AT";
        let result = extract_kmers(sequence, 3);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_kmers_zero_length() {
        let result = extract_kmers("", 3);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_kmers_filter_ambiguous() {
        let sequence = "ATGNCGAT";
        let kmers = extract_kmers_filter_ambiguous(sequence, 3);
        // Should skip k-mers containing N
        assert_eq!(kmers.len(), 3); // "ATG" and "CGA", "GAT"
    }

    #[test]
    fn test_filter_sequence_valid() {
        assert!(filter_sequence("ATGC", 3));
        assert!(!filter_sequence("AT", 3));
        assert!(!filter_sequence("ATXG", 3));
    }

    #[test]
    fn test_filter_sequence_case_insensitive() {
        assert!(filter_sequence("atgc", 3));
        assert!(filter_sequence("ATGC", 3));
    }

    #[test]
    fn test_count_extractable_kmers() {
        let sequence = "ATGCGAT";
        assert_eq!(count_extractable_kmers(sequence, 3), 5); // 7 - 3 + 1 = 5

        let sequence_with_amb = "ATGNCGAT"; // 8 chars, k=3, skip kmers with 'N'
        // Valid: ATG, CGA, GAT (skip TGN, GNC, NCG)
        assert_eq!(count_extractable_kmers(sequence_with_amb, 3), 3);
    }

    #[test]
    fn test_analyze_sequence_quality() {
        let quality = analyze_sequence_quality("ATGCNATG");
        assert!(quality.contains("Length: 8"));
        assert!(quality.contains("Ambiguous (N): 1"));
    }

    #[test]
    fn test_extract_kmers_with_lowercase() {
        let sequence = "atgc";
        let kmers = extract_kmers(sequence, 3).unwrap();
        assert_eq!(kmers.len(), 2);
    }

    #[test]
    fn test_edge_case_exact_length() {
        let sequence = "ATG";
        let kmers = extract_kmers(sequence, 3).unwrap();
        assert_eq!(kmers.len(), 1);
    }

    #[test]
    fn test_performance_large_sequence() {
        let sequence = "A".repeat(10000);
        let count = count_extractable_kmers(&sequence, 31);
        assert_eq!(count, 10000 - 31 + 1);
    }
}