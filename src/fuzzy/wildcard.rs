//! Wildcard expansion for N nucleotides
//!
//! This module handles the expansion of wildcard characters (N) into all possible
//! nucleotides (A, T, C, G) with efficient algorithms for combinatorial explosion management.

use crate::fuzzy::{constants, FuzzyError, FuzzyResult};
use std::collections::HashSet;

/// Nucleotide bases
const NUCLEOTIDES: [char; 4] = ['A', 'T', 'C', 'G'];

/// Expand wildcards (N) in a query string to all possible combinations
///
/// # Arguments
/// * `query` - Query string possibly containing 'N' wildcards
///
/// # Returns
/// Vector of all concrete sequences without wildcards
///
/// # Examples
/// ```
/// use rustkmer::fuzzy::wildcard::expand_wildcards;
///
/// let variants = expand_wildcards("ATGCGATGCTAGCN").unwrap();
/// assert_eq!(variants.len(), 4);
/// assert!(variants.contains(&"ATGCGATGCTAGCA".to_string()));
/// assert!(variants.contains(&"ATGCGATGCTAGCT".to_string()));
/// assert!(variants.contains(&"ATGCGATGCTAGCC".to_string()));
/// assert!(variants.contains(&"ATGCGATGCTAGCG".to_string()));
/// ```
pub fn expand_wildcards(query: &str) -> FuzzyResult<Vec<String>> {
    let wildcard_positions: Vec<usize> = query
        .chars()
        .enumerate()
        .filter(|(_, c)| *c == 'N')
        .map(|(i, _)| i)
        .collect();

    if wildcard_positions.is_empty() {
        return Ok(vec![query.to_string()]);
    }

    // Check combinatorial explosion protection
    let combination_count = 4_usize.pow(wildcard_positions.len() as u32);
    if combination_count > constants::DEFAULT_MAX_VARIANTS {
        return Err(FuzzyError::TooManyVariants {
            actual: combination_count,
            limit: constants::DEFAULT_MAX_VARIANTS,
        });
    }

    let mut variants = Vec::with_capacity(combination_count);
    generate_wildcard_combinations(query, &wildcard_positions, 0, &mut variants);

    Ok(variants)
}

/// Generate all wildcard combinations recursively
fn generate_wildcard_combinations(
    query: &str,
    wildcard_positions: &[usize],
    current_index: usize,
    variants: &mut Vec<String>,
) {
    if current_index >= wildcard_positions.len() {
        // All wildcards processed, add the current combination
        variants.push(query.to_string());
        return;
    }

    let wildcard_pos = wildcard_positions[current_index];

    // Try each nucleotide at this position
    for &nucleotide in &NUCLEOTIDES {
        let mut query_chars: Vec<char> = query.chars().collect();
        query_chars[wildcard_pos] = nucleotide;
        let new_query: String = query_chars.iter().collect();

        // Recursively process remaining wildcards
        generate_wildcard_combinations(&new_query, wildcard_positions, current_index + 1, variants);
    }
}

/// Expand wildcards using an iterative approach (memory efficient)
///
/// This method generates variants iteratively to avoid deep recursion
/// for queries with many wildcards.
pub fn expand_wildcards_iterative(query: &str) -> FuzzyResult<Vec<String>> {
    let wildcard_positions: Vec<usize> = query
        .chars()
        .enumerate()
        .filter(|(_, c)| *c == 'N')
        .map(|(i, _)| i)
        .collect();

    if wildcard_positions.is_empty() {
        return Ok(vec![query.to_string()]);
    }

    // Check combinatorial explosion protection
    let combination_count = 4_usize.pow(wildcard_positions.len() as u32);
    if combination_count > constants::DEFAULT_MAX_VARIANTS {
        return Err(FuzzyError::TooManyVariants {
            actual: combination_count,
            limit: constants::DEFAULT_MAX_VARIANTS,
        });
    }

    let mut variants = vec![query.to_string()];

    // Process each wildcard position iteratively
    for &pos in &wildcard_positions {
        let mut new_variants = Vec::with_capacity(variants.len() * 4);

        for variant in variants {
            for &nucleotide in &NUCLEOTIDES {
                let mut chars: Vec<char> = variant.chars().collect();
                chars[pos] = nucleotide;
                new_variants.push(chars.iter().collect::<String>());
            }
        }

        variants = new_variants;
    }

    Ok(variants)
}

/// Count the number of wildcards in a query
pub fn count_wildcards(query: &str) -> usize {
    query.chars().filter(|&c| c == 'N').count()
}

/// Estimate the number of variants that would be generated
pub fn estimate_wildcard_variants(query: &str) -> usize {
    4_usize.pow(count_wildcards(query) as u32)
}

/// Check if a query would exceed variant limits
pub fn would_exceed_wildcard_limit(query: &str, max_variants: usize) -> bool {
    estimate_wildcard_variants(query) > max_variants
}

/// Validate wildcard query parameters
pub fn validate_wildcard_query(query: &str, max_variants: Option<usize>) -> FuzzyResult<()> {
    // Check for invalid characters
    if !query.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
        return Err(FuzzyError::InvalidQuery(
            "Query contains invalid characters (only A,T,C,G,N allowed)".to_string(),
        ));
    }

    // Check combinatorial explosion
    if let Some(max_variants) = max_variants {
        if would_exceed_wildcard_limit(query, max_variants) {
            return Err(FuzzyError::TooManyVariants {
                actual: estimate_wildcard_variants(query),
                limit: max_variants,
            });
        }
    }

    Ok(())
}

/// Generate wildcard variants with streaming processing
///
/// This method processes variants in batches to reduce memory usage
/// for large wildcard expansions.
pub fn expand_wildcards_streaming(
    query: &str,
    batch_size: usize,
    mut processor: impl FnMut(&[String]) -> FuzzyResult<()>,
) -> FuzzyResult<()> {
    let _wildcard_count = count_wildcards(query);
    let total_variants = estimate_wildcard_variants(query);

    if total_variants > constants::DEFAULT_MAX_VARIANTS {
        return Err(FuzzyError::TooManyVariants {
            actual: total_variants,
            limit: constants::DEFAULT_MAX_VARIANTS,
        });
    }

    // Generate variants in batches
    let mut batch = Vec::with_capacity(batch_size);
    let mut generated = 0;

    // Use iterative generation with batch processing
    generate_wildcard_combinations_batched(query, 0, &mut batch, &mut generated, total_variants, batch_size, &mut processor)?;

    // Process any remaining variants in the last batch
    if !batch.is_empty() {
        processor(&batch)?;
    }

    Ok(())
}

/// Generate wildcard combinations in batches for memory efficiency
fn generate_wildcard_combinations_batched(
    query: &str,
    start_wildcard: usize,
    batch: &mut Vec<String>,
    generated: &mut usize,
    total_variants: usize,
    batch_size: usize,
    processor: &mut impl FnMut(&[String]) -> FuzzyResult<()>,
) -> FuzzyResult<()> {
    let query_chars: Vec<char> = query.chars().collect();
    let wildcard_positions: Vec<usize> = query_chars
        .iter()
        .enumerate()
        .filter(|(_, c)| **c == 'N')
        .map(|(i, _)| i)
        .collect();

    if start_wildcard >= wildcard_positions.len() {
        // No more wildcards to process, add this variant
        batch.push(query_chars.iter().collect::<String>());
        *generated += 1;

        // Process batch if full
        if batch.len() >= batch_size {
            processor(batch)?;
            batch.clear();
        }
        return Ok(());
    }

    let wildcard_pos = wildcard_positions[start_wildcard];

    // Try each nucleotide at this position
    for &nucleotide in &NUCLEOTIDES {
        let mut new_chars = query_chars.clone();
        new_chars[wildcard_pos] = nucleotide;
        let new_query: String = new_chars.iter().collect();

        generate_wildcard_combinations_batched(
            &new_query,
            start_wildcard + 1,
            batch,
            generated,
            total_variants,
            batch_size,
            processor,
        )?;
    }

    Ok(())
}

/// Remove duplicate variants (maintain order)
pub fn remove_duplicate_variants(variants: &mut Vec<String>) {
    let mut seen = HashSet::new();
    variants.retain(|variant| seen.insert(variant.clone()));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_expand_wildcards_single() {
        let variants = expand_wildcards("ATGCGATGCTAGCN").unwrap();
        assert_eq!(variants.len(), 4);

        let expected_variants = [
            "ATGCGATGCTAGCA",
            "ATGCGATGCTAGCT",
            "ATGCGATGCTAGCC",
            "ATGCGATGCTAGCG",
        ];

        for expected in &expected_variants {
            assert!(variants.contains(&expected.to_string()));
        }
    }

    #[test]
    fn test_expand_wildcards_multiple() {
        let variants = expand_wildcards("ATNNGATGCTAGCG").unwrap();
        assert_eq!(variants.len(), 16); // 4^2 = 16
    }

    #[test]
    fn test_expand_wildcards_none() {
        let variants = expand_wildcards("ATGCGATGCTAGCG").unwrap();
        assert_eq!(variants.len(), 1);
        assert_eq!(variants[0], "ATGCGATGCTAGCG");
    }

    #[test]
    fn test_expand_wildcards_iterative() {
        let variants_recursive = expand_wildcards("ATNNGATGCTAGCG").unwrap();
        let variants_iterative = expand_wildcards_iterative("ATNNGATGCTAGCG").unwrap();

        assert_eq!(variants_recursive.len(), variants_iterative.len());

        // Convert to sets for comparison (order may differ)
        let recursive_set: HashSet<String> = variants_recursive.into_iter().collect();
        let iterative_set: HashSet<String> = variants_iterative.into_iter().collect();
        assert_eq!(recursive_set, iterative_set);
    }

    #[test]
    fn test_count_wildcards() {
        assert_eq!(count_wildcards("ATGCGATGCTAGCN"), 1);
        assert_eq!(count_wildcards("ATNNGATGCTNGCN"), 3);
        assert_eq!(count_wildcards("ATGCGATGCTAGCG"), 0);
    }

    #[test]
    fn test_estimate_wildcard_variants() {
        assert_eq!(estimate_wildcard_variants("ATGCGATGCTAGCN"), 4);
        assert_eq!(estimate_wildcard_variants("ATNNGATGCTNGCN"), 64); // 4^3
        assert_eq!(estimate_wildcard_variants("ATGCGATGCTAGCG"), 1);
    }

    #[test]
    fn test_would_exceed_wildcard_limit() {
        assert!(would_exceed_wildcard_limit("ATNNNNATGCTNGCN", 1000)); // 4^6 = 4096 > 1000
        assert!(!would_exceed_wildcard_limit("ATNNGATGCTNGCN", 100)); // 4^3 = 64 <= 100
    }

    #[test]
    fn test_validate_wildcard_query() {
        // Valid query
        assert!(validate_wildcard_query("ATGCGATGCTAGCN", Some(100)).is_ok());

        // Invalid characters
        assert!(validate_wildcard_query("ATGCGXATGCTAGC", Some(100)).is_err());

        // Too many variants
        assert!(validate_wildcard_query("ATNNNNATGCTNGCN", Some(1000)).is_err());
    }

    #[test]
    fn test_remove_duplicate_variants() {
        let mut variants = vec![
            "ATGCGATGCTAGCA".to_string(),
            "ATGCGATGCTAGCT".to_string(),
            "ATGCGATGCTAGCA".to_string(), // Duplicate
            "ATGCGATGCTAGCC".to_string(),
        ];

        remove_duplicate_variants(&mut variants);
        assert_eq!(variants.len(), 3);
        assert!(variants.contains(&"ATGCGATGCTAGCA".to_string()));
        assert!(variants.contains(&"ATGCGATGCTAGCT".to_string()));
        assert!(variants.contains(&"ATGCGATGCTAGCC".to_string()));
    }

    #[test]
    fn test_expand_wildcards_combinatorial_explosion() {
        // This should fail due to too many variants
        let result = expand_wildcards("NNNNNNNNNN"); // 4^10 = 1,048,576 variants
        assert!(result.is_err());

        match result.unwrap_err() {
            FuzzyError::TooManyVariants { actual, limit } => {
                assert!(actual > limit);
            }
            _ => panic!("Expected TooManyVariants error"),
        }
    }

    #[test]
    fn test_expand_wildcards_streaming() {
        let mut processed_variants = Vec::new();
        let mut processor = |batch: &[String]| -> FuzzyResult<()> {
            for variant in batch {
                processed_variants.push(variant.clone());
            }
            Ok(())
        };

        expand_wildcards_streaming("ATNNGATGCTAGCG", 5, &mut processor).unwrap();

        // Should have processed all 16 variants
        assert_eq!(processed_variants.len(), 16);

        // All variants should be unique
        let unique_variants: HashSet<String> = processed_variants.into_iter().collect();
        assert_eq!(unique_variants.len(), 16);
    }
}