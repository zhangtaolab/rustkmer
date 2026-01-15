//! Suffix-based k-mer extraction functionality
//!
//! This module provides efficient suffix matching for k-mer databases,
//! allowing extraction of all k-mers that end with a specific suffix.

use crate::database::format::RKDatabase;
use crate::database::prefix_query::extract_kmers_by_prefix;
use crate::error::ProcessingResult;
use crate::kmer::encoding::decode_kmer_u128;

/// Result of a suffix query
#[derive(Debug, Clone)]
pub struct SuffixQueryResult {
    /// List of matching k-mers with their counts
    pub matches: Vec<(String, u64)>,
    /// Total number of matches found
    pub total_matches: usize,
    /// The suffix that was searched for
    pub suffix: String,
    /// Query execution time in milliseconds
    pub query_time_ms: u64,
}

/// Extract all k-mers that end with the given suffix
pub fn extract_kmers_by_suffix(
    database: &RKDatabase,
    suffix: &str,
) -> ProcessingResult<SuffixQueryResult> {
    use std::time::Instant;

    let start_time = Instant::now();

    // Validate suffix
    if suffix.is_empty() {
        return Err(crate::error::KmerError::InvalidParameters(
            "Suffix cannot be empty".to_string(),
        )
        .into());
    }

    // Validate that suffix contains only valid nucleotides
    if !suffix
        .chars()
        .all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G'))
    {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Suffix contains invalid characters: {}",
            suffix
        ))
        .into());
    }

    let suffix_upper = suffix.to_uppercase();
    let suffix_len = suffix_upper.len();
    let kmer_size = database.kmer_size();

    // Validate suffix length
    if suffix_len >= kmer_size {
        return Err(crate::error::KmerError::InvalidParameters(format!(
            "Suffix length ({}) must be less than k-mer size ({})",
            suffix_len, kmer_size
        ))
        .into());
    }

    // Get all k-mers from database
    let all_kmers = database.all_kmers()?;

    // Extract suffix matches
    let matches = extract_suffix_matches(&all_kmers, kmer_size, &suffix_upper)?;

    let query_time_ms = start_time.elapsed().as_millis() as u64;

    Ok(SuffixQueryResult {
        matches,
        total_matches: 0, // Will be set below
        suffix: suffix_upper,
        query_time_ms,
    })
}

/// Extract suffix matches from k-mer list
fn extract_suffix_matches(
    all_kmers: &[(u128, u32)],
    kmer_size: usize,
    suffix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    let mut matches = Vec::new();
    let _suffix_len = suffix.len();

    for &(encoded_kmer, count) in all_kmers {
        // Decode k-mer and check if it ends with suffix
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.ends_with(suffix) {
            matches.push((decoded_kmer, count as u64));
        }
    }

    Ok(matches)
}

/// Smart wildcard query based on N positions
pub fn smart_wildcard_query(
    database: &RKDatabase,
    pattern: &str,
) -> ProcessingResult<SmartWildcardResult> {
    use std::time::Instant;

    let start_time = Instant::now();

    // Find all N positions
    let n_positions: Vec<usize> = pattern
        .chars()
        .enumerate()
        .filter(|(_, c)| *c == 'N' || *c == 'n')
        .map(|(i, _)| i)
        .collect();

    if n_positions.is_empty() {
        // No wildcards, do exact query
        return do_exact_query(database, pattern, start_time);
    }

    let n_count = n_positions.len();
    let pattern_upper = pattern.to_uppercase();
    let total_variants = 4usize.pow(n_count as u32);

    // Decide strategy based on N positions
    let strategy = decide_query_strategy(&pattern_upper, &n_positions, total_variants)?;

    let matches = match strategy.strategy_type {
        StrategyType::PrefixMatching => {
            extract_with_prefix_strategy(database, &pattern_upper, &n_positions)?
        }
        StrategyType::SuffixMatching => {
            extract_with_suffix_strategy(database, &pattern_upper, &n_positions)?
        }
        StrategyType::HybridMatching => {
            extract_with_hybrid_strategy(database, &pattern_upper, &n_positions)?
        }
        StrategyType::VariantGeneration => {
            extract_with_variant_strategy(database, &pattern_upper, &n_positions, total_variants)?
        }
    };

    let query_time_ms = start_time.elapsed().as_millis() as u64;

    Ok(SmartWildcardResult {
        matches,
        strategy_used: strategy,
        total_matches: 0,
        pattern: pattern_upper,
        query_time_ms,
    })
}

/// Query strategy types
#[derive(Debug, Clone)]
pub enum StrategyType {
    PrefixMatching,    // N at end, use prefix
    SuffixMatching,    // N at start, use suffix
    HybridMatching,    // N in middle, use prefix+suffix
    VariantGeneration, // N scattered, generate variants
}

/// Query strategy information
#[derive(Debug, Clone)]
pub struct QueryStrategy {
    pub strategy_type: StrategyType,
    pub efficiency_rating: String,
    pub description: String,
    pub estimated_variants: usize,
}

/// Decide the best query strategy
fn decide_query_strategy(
    pattern: &str,
    n_positions: &[usize],
    total_variants: usize,
) -> ProcessingResult<QueryStrategy> {
    let n_count = n_positions.len();
    let pattern_len = pattern.len();

    // If very few variants, variant generation might be efficient
    if total_variants <= 16 {
        return Ok(QueryStrategy {
            strategy_type: StrategyType::VariantGeneration,
            efficiency_rating: "⭐⭐⭐".to_string(),
            description: format!("Small variant count ({}) acceptable", total_variants),
            estimated_variants: total_variants,
        });
    }

    let start_n = min(n_positions);
    let end_n = max(n_positions);

    // Case 1: N all at the end
    if start_n == pattern_len - n_count {
        let prefix = &pattern[..start_n];
        return Ok(QueryStrategy {
            strategy_type: StrategyType::PrefixMatching,
            efficiency_rating: "⭐⭐⭐⭐⭐".to_string(),
            description: format!("N at end, use prefix matching: '{}'", prefix),
            estimated_variants: 0,
        });
    }

    // Case 2: N all at the beginning
    if end_n == n_count - 1 {
        let suffix = &pattern[n_count..];
        return Ok(QueryStrategy {
            strategy_type: StrategyType::SuffixMatching,
            efficiency_rating: "⭐⭐⭐⭐⭐".to_string(),
            description: format!("N at start, use suffix matching: '{}'", suffix),
            estimated_variants: 0,
        });
    }

    // Case 3: N in the middle
    if start_n > 0 && end_n < pattern_len - 1 {
        let prefix = &pattern[..start_n];
        let suffix = &pattern[end_n + 1..];

        return Ok(QueryStrategy {
            strategy_type: StrategyType::HybridMatching,
            efficiency_rating: "⭐⭐⭐⭐".to_string(),
            description: format!(
                "N in middle, hybrid: prefix='{}' suffix='{}'",
                prefix, suffix
            ),
            estimated_variants: 0,
        });
    }

    // Case 4: N scattered
    Ok(QueryStrategy {
        strategy_type: StrategyType::VariantGeneration,
        efficiency_rating: "⭐⭐".to_string(),
        description: format!(
            "N scattered, variant generation required ({} variants)",
            total_variants
        ),
        estimated_variants: total_variants,
    })
}

/// Result of smart wildcard query
#[derive(Debug, Clone)]
pub struct SmartWildcardResult {
    pub matches: Vec<(String, u64)>,
    pub strategy_used: QueryStrategy,
    pub total_matches: usize,
    pub pattern: String,
    pub query_time_ms: u64,
}

/// Helper functions for strategy execution
fn extract_with_prefix_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    let prefix_end = min(n_positions);
    let prefix = &pattern[..prefix_end];

    // Use existing prefix extraction
    let prefix_result = extract_kmers_by_prefix(database, prefix)?;

    // Filter to match the complete pattern
    let mut matches = Vec::new();
    for (kmer, count) in prefix_result.matches {
        if kmer.starts_with(prefix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }

    Ok(matches)
}

fn extract_with_suffix_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    let suffix_start = max(n_positions) + 1;
    let suffix = &pattern[suffix_start..];

    // Use suffix extraction
    let suffix_result = extract_kmers_by_suffix(database, suffix)?;

    // Filter to match the complete pattern
    let mut matches = Vec::new();
    for (kmer, count) in suffix_result.matches {
        if kmer.ends_with(suffix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }

    Ok(matches)
}

fn extract_with_hybrid_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    let start_n = min(n_positions);
    let end_n = max(n_positions);
    let prefix = &pattern[..start_n];
    let suffix = &pattern[end_n + 1..];

    // Get prefix matches
    let prefix_result = extract_kmers_by_prefix(database, prefix)?;

    // Filter for suffix and pattern match
    let mut matches = Vec::new();
    for (kmer, count) in prefix_result.matches {
        if kmer.ends_with(suffix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }

    Ok(matches)
}

fn extract_with_variant_strategy(
    _database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
    total_variants: usize,
) -> ProcessingResult<Vec<(String, u64)>> {
    if total_variants > 10000 {
        return Err(crate::error::KmerError::TooManyVariants {
            actual: total_variants,
            limit: 10000,
        }
        .into());
    }

    // Generate variants and query each
    let variants = generate_variants(pattern, n_positions)?;
    let matches = Vec::new();

    for _variant in variants {
        // Query this variant (implement k-mer query here)
        // For now, return empty - this would integrate with the database query
        // let result = database.query_kmer(&variant)?;
        // if let Some(count) = result {
        //     matches.push((variant, count as u64));
        // }
    }

    Ok(matches)
}

/// Helper functions
fn min(positions: &[usize]) -> usize {
    positions.iter().min().copied().unwrap_or(0)
}

fn max(positions: &[usize]) -> usize {
    positions.iter().max().copied().unwrap_or(0)
}

fn matches_pattern(kmer: &str, pattern: &str, n_positions: &[usize]) -> bool {
    for &pos in n_positions {
        if kmer.chars().nth(pos) != pattern.chars().nth(pos) {
            // Not an N position, must match exactly
            if pattern.chars().nth(pos) != Some('N') && pattern.chars().nth(pos) != Some('n') {
                return false;
            }
        }
    }
    true
}

fn generate_variants(pattern: &str, n_positions: &[usize]) -> ProcessingResult<Vec<String>> {
    let nucleotides = ['A', 'T', 'C', 'G'];
    let mut variants = Vec::new();

    fn backtrack(
        pattern: &str,
        n_positions: &[usize],
        nucleotides: &[char; 4],
        index: usize,
        current: &mut String,
        results: &mut Vec<String>,
    ) {
        if index >= n_positions.len() {
            results.push(current.clone());
            return;
        }

        let pos = n_positions[index];
        let original_char = pattern.chars().nth(pos).unwrap();

        for &nucleotide in nucleotides {
            current.replace_range(pos..=pos, &nucleotide.to_string());
            backtrack(
                pattern,
                n_positions,
                nucleotides,
                index + 1,
                current,
                results,
            );
        }

        // Restore original
        current.replace_range(pos..=pos, &original_char.to_string());
    }

    let mut current = pattern.to_string();
    backtrack(
        pattern,
        n_positions,
        &nucleotides,
        0,
        &mut current,
        &mut variants,
    );

    Ok(variants)
}

fn do_exact_query(
    _database: &RKDatabase,
    pattern: &str,
    start_time: std::time::Instant,
) -> ProcessingResult<SmartWildcardResult> {
    let matches = Vec::new(); // Would implement exact query here

    Ok(SmartWildcardResult {
        matches,
        strategy_used: QueryStrategy {
            strategy_type: StrategyType::VariantGeneration,
            efficiency_rating: "⭐⭐⭐⭐⭐".to_string(),
            description: "Exact match query".to_string(),
            estimated_variants: 1,
        },
        total_matches: 0,
        pattern: pattern.to_string(),
        query_time_ms: start_time.elapsed().as_millis() as u64,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strategy_decision() {
        // Test N at end
        let pattern = "AAAANNN";
        let n_positions = vec![4, 5, 6];
        let strategy = decide_query_strategy(pattern, &n_positions, 64).unwrap();

        match strategy.strategy_type {
            StrategyType::PrefixMatching => {
                assert!(strategy.description.contains("AAAA"));
            }
            _ => panic!("Expected prefix matching for AAAANNN"),
        }

        // Test N at start
        let pattern = "NNNAAA";
        let n_positions = vec![0, 1, 2];
        let strategy = decide_query_strategy(pattern, &n_positions, 64).unwrap();

        match strategy.strategy_type {
            StrategyType::SuffixMatching => {
                assert!(strategy.description.contains("AAA"));
            }
            _ => panic!("Expected suffix matching for NNNAAA"),
        }
    }
}
