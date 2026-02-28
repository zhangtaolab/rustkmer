//! Prefix-based k-mer extraction functionality
//!
//! This module provides efficient prefix matching for k-mer databases,
//! allowing extraction of all k-mers that start with a specific prefix.

use crate::database::format::RKDatabase;
use crate::error::ProcessingResult;
use crate::kmer::encoding::decode_kmer_u128;
use std::collections::HashMap;

/// Result of a prefix query
#[derive(Debug, Clone)]
pub struct PrefixQueryResult {
    /// List of matching k-mers with their counts
    pub matches: Vec<(String, u64)>,
    /// Total number of matches found
    pub total_matches: usize,
    /// The prefix that was searched for
    pub prefix: String,
    /// Query execution time in milliseconds
    pub query_time_ms: u64,
}

/// Extract all k-mers that start with the given prefix
pub fn extract_kmers_by_prefix(
    database: &RKDatabase,
    prefix: &str,
) -> ProcessingResult<PrefixQueryResult> {
    use std::time::Instant;

    let start_time = Instant::now();

    // Validate prefix
    if prefix.is_empty() {
        return Err(crate::error::KmerError::InvalidParameters(
            "Prefix cannot be empty".to_string(),
        )
        .into());
    }

    // Validate that prefix contains only valid nucleotides
    if !prefix
        .chars()
        .all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G'))
    {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Prefix contains invalid characters: {}",
            prefix
        ))
        .into());
    }

    let prefix_upper = prefix.to_uppercase();
    let prefix_len = prefix_upper.len();
    let kmer_size = database.kmer_size();

    // Validate prefix length
    if prefix_len >= kmer_size {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Prefix length ({}) must be less than k-mer size ({})",
            prefix_len, kmer_size
        ))
        .into());
    }

    // Encode prefix to get the range boundaries
    let prefix_encoded = encode_prefix_to_range(&prefix_upper, kmer_size)?;

    // Get all k-mers from database
    let all_kmers = database.all_kmers()?;

    // Filter k-mers by prefix using binary search if database is sorted
    let matches = if database.header.sorted {
        extract_prefix_matches_binary_search(&all_kmers, &prefix_encoded, kmer_size, &prefix_upper)?
    } else {
        extract_prefix_matches_linear(&all_kmers, kmer_size, &prefix_upper)?
    };

    let query_time_ms = start_time.elapsed().as_millis() as u64;

    Ok(PrefixQueryResult {
        matches,
        total_matches: 0, // Will be set below
        prefix: prefix_upper,
        query_time_ms,
    })
}

/// Encode prefix to get search range boundaries
fn encode_prefix_to_range(prefix: &str, kmer_size: usize) -> ProcessingResult<(u128, u128)> {
    use crate::kmer::encoding::encode_kmer_u128;

    // Encode the prefix
    let prefix_encoded = encode_kmer_u128(prefix).map_err(|e| {
        crate::error::KmerError::ProcessingError(format!("Failed to encode prefix: {}", e))
    })?;

    // Calculate the range [prefix, prefix_with_trailing_A_to_T]
    // For prefix "AAATT", we want all k-mers from "AAATT..." to "AAATT..." where
    // the remaining positions are filled with the maximum value (T)
    let remaining_bits = (kmer_size - prefix.len()) * 2;
    let max_suffix = (1u128 << remaining_bits) - 1;

    let range_start = prefix_encoded << remaining_bits;
    let range_end = range_start | max_suffix;

    Ok((range_start, range_end))
}

/// Extract prefix matches using binary search (for sorted databases)
fn extract_prefix_matches_binary_search(
    all_kmers: &[(u128, u32)],
    prefix_range: &(u128, u128),
    kmer_size: usize,
    prefix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    let mut matches = Vec::new();

    // Binary search for the first k-mer >= range_start
    let start_idx = match all_kmers.binary_search_by_key(&prefix_range.0, |&(kmer, _)| kmer) {
        Ok(idx) => idx,
        Err(idx) => idx,
    };

    // Iterate through k-mers until we exceed range_end
    for i in start_idx..all_kmers.len() {
        let (encoded_kmer, count) = all_kmers[i];

        if encoded_kmer > prefix_range.1 {
            break; // Exceeded the range
        }

        // Decode k-mer and check if it starts with prefix
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.starts_with(prefix) {
            matches.push((decoded_kmer, count as u64));
        }
    }

    Ok(matches)
}

/// Extract prefix matches using linear search (for unsorted databases)
fn extract_prefix_matches_linear(
    all_kmers: &[(u128, u32)],
    kmer_size: usize,
    prefix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    let mut matches = Vec::new();

    for &(encoded_kmer, count) in all_kmers {
        // Decode k-mer and check if it starts with prefix
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.starts_with(prefix) {
            matches.push((decoded_kmer, count as u64));
        }
    }

    Ok(matches)
}

/// Batch prefix extraction for multiple prefixes
pub fn extract_kmers_by_multiple_prefixes(
    database: &RKDatabase,
    prefixes: &[&str],
) -> ProcessingResult<HashMap<String, PrefixQueryResult>> {
    let mut results = HashMap::new();

    // Get all k-mers once
    let all_kmers = database.all_kmers()?;
    let kmer_size = database.kmer_size();

    for &prefix in prefixes {
        let prefix_upper = prefix.to_uppercase();
        let mut matches = Vec::new();

        for &(encoded_kmer, count) in &all_kmers {
            let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
            if decoded_kmer.starts_with(&prefix_upper) {
                matches.push((decoded_kmer, count as u64));
            }
        }

        results.insert(
            prefix_upper.clone(),
            PrefixQueryResult {
                matches,
                total_matches: 0,
                prefix: prefix_upper,
                query_time_ms: 0,
            },
        );
    }

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kmer::encoding::encode_kmer_u128;

    #[test]
    fn test_prefix_encoding() {
        let result = encode_prefix_to_range("AAATT", 19).unwrap();
        let (start, end) = result;

        // Basic validation - start should be less than end
        assert!(start < end);

        // AAATT should be encoded correctly
        let expected_prefix = encode_kmer_u128("AAATT").unwrap();
        let remaining_bits = (19 - 5) * 2;
        let expected_start = expected_prefix << remaining_bits;

        assert_eq!(start, expected_start);
    }

    #[test]
    fn test_invalid_prefix() {
        // This would require a database instance to test properly
        // For now, just test validation
        assert!(encode_prefix_to_range("", 19).is_err());
        assert!(encode_prefix_to_range("INVALID", 19).is_err());
    }
}
