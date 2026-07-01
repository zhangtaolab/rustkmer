//! Optimized prefix-based k-mer extraction for sorted databases
//!
//! This module provides memory-block based extraction for sorted databases,
//! avoiding individual k-mer decoding overhead.

use crate::database::format::RKDatabase;
use crate::error::ProcessingResult;
use crate::kmer::encoding::decode_kmer_u128;

/// Result of optimized prefix query
#[derive(Debug, Clone)]
pub struct OptimizedPrefixResult {
    /// List of matching k-mers with their counts
    pub matches: Vec<(String, u64)>,
    /// Memory block information for performance analysis
    pub memory_block: MemoryBlockInfo,
    /// Total number of matches found
    pub total_matches: usize,
    /// Query execution time in milliseconds
    pub query_time_ms: u64,
}

/// Memory block information
#[derive(Debug, Clone)]
pub struct MemoryBlockInfo {
    /// Start index in the sorted array
    pub start_index: usize,
    /// End index (exclusive) in the sorted array
    pub end_index: usize,
    /// Number of k-mers in the memory block
    pub block_size: usize,
    /// Whether the database is sorted
    pub is_sorted: bool,
}

/// Optimized prefix extraction for sorted databases
pub fn extract_prefix_optimized(
    database: &RKDatabase,
    prefix: &str,
) -> ProcessingResult<OptimizedPrefixResult> {
    use std::time::Instant;

    let start_time = Instant::now();

    let kmer_size = database.kmer_size();

    // Validate prefix length to prevent overflow
    if prefix.len() > kmer_size {
        return Ok(OptimizedPrefixResult {
            matches: vec![],
            memory_block: MemoryBlockInfo {
                start_index: 0,
                end_index: 0,
                block_size: 0,
                is_sorted: database.header.sorted,
            },
            total_matches: 0,
            query_time_ms: start_time.elapsed().as_millis() as u64,
        });
    }

    // Validate prefix
    if prefix.is_empty() {
        return Ok(OptimizedPrefixResult {
            matches: vec![],
            memory_block: MemoryBlockInfo {
                start_index: 0,
                end_index: 0,
                block_size: 0,
                is_sorted: database.header.sorted,
            },
            total_matches: 0,
            query_time_ms: start_time.elapsed().as_millis() as u64,
        });
    }

    let prefix_upper = prefix.to_uppercase();

    // Encode prefix to get search range
    let prefix_encoded = encode_prefix_to_range(&prefix_upper, kmer_size)?;

    // Get all k-mers from database
    let all_kmers = database.all_kmers()?;

    // Check if database is sorted
    let is_sorted = database.header.sorted;

    if !is_sorted {
        // Fallback to linear search for unsorted databases
        return extract_prefix_linear(&all_kmers, kmer_size, &prefix_upper, false, start_time);
    }

    // Optimized extraction for sorted databases
    extract_prefix_sorted_block(
        &all_kmers,
        &prefix_encoded,
        kmer_size,
        &prefix_upper,
        start_time,
    )
}

/// Extract prefix matches from sorted database using memory blocks
fn extract_prefix_sorted_block(
    all_kmers: &[(u128, u32)],
    prefix_range: &(u128, u128),
    kmer_size: usize,
    prefix: &str,
    start_time: std::time::Instant,
) -> ProcessingResult<OptimizedPrefixResult> {
    let mut matches = Vec::new();

    // Binary search for the first k-mer >= range_start
    let start_idx = match all_kmers.binary_search_by_key(&prefix_range.0, |&(kmer, _)| kmer) {
        Ok(idx) => idx,
        Err(idx) => idx,
    };

    // Find the end index (first k-mer > range_end)
    let end_idx = match all_kmers.binary_search_by_key(&prefix_range.1, |&(kmer, _)| kmer) {
        Ok(idx) => idx + 1, // Include the exact match
        Err(idx) => idx,    // First greater element
    };

    let block_size = end_idx - start_idx;

    // Pre-allocate memory for better performance
    matches.reserve(block_size.min(1000)); // Reasonable upper bound

    // Extract memory block and decode in batch
    if block_size > 0 {
        extract_memory_block_batch(
            &all_kmers[start_idx..end_idx],
            kmer_size,
            prefix,
            &mut matches,
        );
    }

    let query_time_ms = start_time.elapsed().as_millis() as u64;
    let total_matches = matches.len();

    Ok(OptimizedPrefixResult {
        matches,
        memory_block: MemoryBlockInfo {
            start_index: start_idx,
            end_index: end_idx,
            block_size,
            is_sorted: true,
        },
        total_matches,
        query_time_ms,
    })
}

/// Batch extract and decode k-mers from memory block
fn extract_memory_block_batch(
    kmer_block: &[(u128, u32)],
    kmer_size: usize,
    prefix: &str,
    matches: &mut Vec<(String, u64)>,
) {
    // Batch decode all k-mers in the block
    let mut decoded_kmers = Vec::with_capacity(kmer_block.len());

    for &(encoded_kmer, count) in kmer_block {
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        decoded_kmers.push((decoded_kmer, count as u64));
    }

    // Filter matches (most should match due to range search)
    for (kmer, count) in decoded_kmers {
        if kmer.starts_with(prefix) {
            matches.push((kmer, count));
        }
    }
}

/// Fallback linear extraction for unsorted databases
fn extract_prefix_linear(
    all_kmers: &[(u128, u32)],
    kmer_size: usize,
    prefix: &str,
    is_sorted: bool,
    start_time: std::time::Instant,
) -> ProcessingResult<OptimizedPrefixResult> {
    let mut matches = Vec::new();

    for &(encoded_kmer, count) in all_kmers {
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.starts_with(prefix) {
            matches.push((decoded_kmer, count as u64));
        }
    }

    let query_time_ms = start_time.elapsed().as_millis() as u64;
    let total_matches = matches.len();

    Ok(OptimizedPrefixResult {
        matches,
        memory_block: MemoryBlockInfo {
            start_index: 0,
            end_index: all_kmers.len(),
            block_size: all_kmers.len(),
            is_sorted,
        },
        total_matches,
        query_time_ms,
    })
}

/// Optimized hybrid query for sorted databases
pub fn extract_hybrid_optimized(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<OptimizedPrefixResult> {
    use std::time::Instant;

    let start_time = Instant::now();
    let pattern_upper = pattern.to_uppercase();

    // Extract fixed prefix and suffix
    let start_n = n_positions.iter().min().copied().unwrap_or(0);
    let end_n = n_positions.iter().max().copied().unwrap_or(0);
    let prefix = &pattern_upper[..start_n];
    let suffix = &pattern_upper[end_n + 1..];

    // Get k-mer size for validation
    let kmer_size = database.kmer_size();
    let expected_length = start_n + n_positions.len() + suffix.len();

    if expected_length != kmer_size {
        return Err(crate::error::KmerError::InvalidParameters(
            format!("Pattern length ({}) does not match k-mer size ({}). Pattern: '{}', Prefix: '{}' ({} chars), Suffix: '{}' ({} chars), N positions: {} ({} positions)", 
                expected_length, kmer_size, pattern, prefix, prefix.len(), suffix, suffix.len(), n_positions.len(), n_positions.len())
        ).into());
    }

    // Validate prefix and suffix characters
    if !prefix.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Invalid characters in prefix: {}",
            prefix
        ))
        .into());
    }

    if !suffix.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Invalid characters in suffix: {}",
            suffix
        ))
        .into());
    }

    // Get all k-mers from database
    let all_kmers: Vec<(u128, u32)> = database
        .entries
        .iter()
        .map(|entry| (entry.kmer, entry.count))
        .collect();

    // Check if database is sorted by examining header metadata
    let is_sorted = database.header().sorted;

    if is_sorted {
        let mut matches = Vec::new();

        // Binary search for prefix range
        let (range_start, range_end) = encode_prefix_to_range(prefix, kmer_size)?;

        // Find start and end indices using binary search
        let start_idx = find_first_kmer_ge(&all_kmers, range_start);
        let end_idx = find_first_kmer_gt(&all_kmers, range_end);

        // Process memory block
        let kmer_block = &all_kmers[start_idx..end_idx];

        for &(encoded_kmer, count) in kmer_block {
            let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);

            // Check suffix match first (faster filtering)
            if !decoded_kmer.ends_with(suffix) {
                continue;
            }

            // Check complete pattern match
            if matches_pattern(&decoded_kmer, &pattern_upper, n_positions) {
                matches.push((decoded_kmer, count as u64));
            }
        }

        let query_time_ms = start_time.elapsed().as_millis() as u64;

        let total_matches = matches.len();

        Ok(OptimizedPrefixResult {
            matches,
            memory_block: MemoryBlockInfo {
                start_index: start_idx,
                end_index: end_idx,
                block_size: end_idx - start_idx,
                is_sorted: true,
            },
            total_matches,
            query_time_ms,
        })
    } else {
        // Fallback to linear search for unsorted databases
        let mut matches = Vec::new();

        for &(encoded_kmer, count) in &all_kmers {
            let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);

            if decoded_kmer.starts_with(prefix)
                && decoded_kmer.ends_with(suffix)
                && matches_pattern(&decoded_kmer, &pattern_upper, n_positions)
            {
                matches.push((decoded_kmer, count as u64));
            }
        }

        let query_time_ms = start_time.elapsed().as_millis() as u64;

        let total_matches = matches.len();

        Ok(OptimizedPrefixResult {
            matches,
            memory_block: MemoryBlockInfo {
                start_index: 0,
                end_index: all_kmers.len(),
                block_size: all_kmers.len(),
                is_sorted: false,
            },
            total_matches,
            query_time_ms,
        })
    }
}

/// Find first k-mer with encoded value >= target
fn find_first_kmer_ge(kmers: &[(u128, u32)], target: u128) -> usize {
    kmers
        .binary_search_by(|&(encoded, _)| encoded.cmp(&target))
        .unwrap_or_else(|idx| idx)
}

/// Find first k-mer with encoded value > target
fn find_first_kmer_gt(kmers: &[(u128, u32)], target: u128) -> usize {
    kmers
        .binary_search_by(|&(encoded, _)| encoded.cmp(&target))
        .unwrap_or_else(|idx| {
            if idx < kmers.len() && kmers[idx].0 == target {
                idx + 1
            } else {
                idx
            }
        })
}

/// Check if kmer matches the wildcard pattern
fn matches_pattern(kmer: &str, pattern: &str, n_positions: &[usize]) -> bool {
    for &pos in n_positions {
        let kmer_char = kmer.chars().nth(pos);
        let pattern_char = pattern.chars().nth(pos);

        if pattern_char != Some('N') && kmer_char != pattern_char {
            return false;
        }
    }
    true
}

/// Parse hybrid pattern format (e.g., ATAC{N5}ACAC)
pub struct HybridPattern {
    pub prefix: String,
    pub suffix: String,
    pub n_count: usize,
    pub total_length: usize,
    pub n_positions: Vec<usize>,
}

/// Parse hybrid pattern from string
pub fn parse_hybrid_pattern(pattern: &str) -> ProcessingResult<HybridPattern> {
    let pattern_upper = pattern.to_uppercase();

    // Check for hybrid format with {N...}
    if let Some(nested_brace_pos) = pattern_upper.find('{') {
        let prefix_part = &pattern_upper[..nested_brace_pos];
        let remainder = &pattern_upper[nested_brace_pos + 1..];

        if let Some(closing_brace_pos) = remainder.find('}') {
            let n_part = &remainder[..closing_brace_pos];
            let suffix_part = &remainder[closing_brace_pos + 1..];

            // Parse N count
            if !n_part.starts_with('N') {
                return Err(crate::error::KmerError::InvalidParameters(format!(
                    "Invalid hybrid pattern format: expected N in {{}} section, got {}",
                    n_part
                ))
                .into());
            }

            let n_count_str = &n_part[1..];
            let n_count = if n_count_str.is_empty() {
                1 // {N} means single N
            } else {
                n_count_str.parse::<usize>().map_err(|_| {
                    crate::error::KmerError::InvalidParameters(format!(
                        "Invalid N count in pattern: {}",
                        n_count_str
                    ))
                })?
            };

            let prefix = prefix_part.to_string();
            let suffix = suffix_part.to_string();
            let total_length = prefix.len() + n_count + suffix.len();

            // Calculate N positions correctly - only the actual N character positions
            let n_positions: Vec<usize> = {
                let mut positions = Vec::new();
                let pattern_with_n = format!("{}{}{}", prefix, "N".repeat(n_count), suffix);
                for (i, c) in pattern_with_n.chars().enumerate() {
                    if c == 'N' {
                        positions.push(i);
                    }
                }
                positions
            };

            // Validate characters
            if !prefix.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
                return Err(crate::error::KmerError::InvalidParameters(format!(
                    "Invalid characters in prefix: {}",
                    prefix
                ))
                .into());
            }

            if !suffix.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
                return Err(crate::error::KmerError::InvalidParameters(format!(
                    "Invalid characters in suffix: {}",
                    suffix
                ))
                .into());
            }

            // Additional validation for reasonable pattern length
            if total_length == 0 {
                return Err(crate::error::KmerError::InvalidParameters(
                    "Pattern cannot be empty".to_string(),
                )
                .into());
            }

            // Store pattern for later validation against database k-mer size
            return Ok(HybridPattern {
                prefix,
                suffix,
                n_count,
                total_length,
                n_positions,
            });
        }
    }

    // If no hybrid format, treat as simple prefix
    if pattern_upper
        .chars()
        .all(|c| matches!(c, 'A' | 'T' | 'C' | 'G'))
    {
        return Ok(HybridPattern {
            prefix: pattern_upper.clone(),
            suffix: String::new(),
            n_count: 0,
            total_length: pattern_upper.len(),
            n_positions: Vec::new(),
        });
    }

    Err(
        crate::error::KmerError::InvalidParameters(format!("Invalid pattern format: {}", pattern))
            .into(),
    )
}

/// Extract k-mers using hybrid search pattern
pub fn extract_hybrid_by_pattern(
    database: &RKDatabase,
    pattern: &str,
) -> ProcessingResult<OptimizedPrefixResult> {
    let hybrid_pattern = parse_hybrid_pattern(pattern)?;

    // If no wildcards, use simple prefix query
    if hybrid_pattern.n_count == 0 {
        return extract_prefix_optimized(database, &hybrid_pattern.prefix);
    }

    // Generate the expanded pattern for algorithm use
    let expanded_pattern = format!(
        "{}{}{}",
        hybrid_pattern.prefix,
        "N".repeat(hybrid_pattern.n_count),
        hybrid_pattern.suffix
    );

    // Use hybrid optimization with expanded pattern
    extract_hybrid_optimized(database, &expanded_pattern, &hybrid_pattern.n_positions)
}

/// Encode prefix to range (same as before)
fn encode_prefix_to_range(prefix: &str, kmer_size: usize) -> ProcessingResult<(u128, u128)> {
    use crate::kmer::encoding::encode_kmer_u128;

    let prefix_encoded = encode_kmer_u128(prefix).map_err(|e| {
        crate::error::KmerError::ProcessingError(format!("Failed to encode prefix: {}", e))
    })?;

    let remaining_bits = (kmer_size - prefix.len()) * 2;
    let max_suffix = (1u128 << remaining_bits) - 1;

    let range_start = prefix_encoded << remaining_bits;
    let range_end = range_start | max_suffix;

    Ok((range_start, range_end))
}

#[cfg(test)]
mod tests {
    use super::*;

    use crate::kmer::encoding::encode_kmer_u128;

    #[test]
    fn test_memory_block_extraction() {
        // This would test the memory block extraction
        // with a mock sorted database
    }

    #[test]
    fn test_prefix_range_encoding() {
        let result = encode_prefix_to_range("AAATT", 19).unwrap();
        let (start, end) = result;

        assert!(start < end);

        let expected_prefix = encode_kmer_u128("AAATT").unwrap();
        let remaining_bits = (19 - 5) * 2;
        let expected_start = expected_prefix << remaining_bits;

        assert_eq!(start, expected_start);
    }
}
