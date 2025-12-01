//! Mutation tolerance using Hamming distance
//!
//! This module implements mutation tolerance by generating k-mer variants
//! within a specified Hamming distance from the original query.

use crate::fuzzy::{constants, FuzzyError, FuzzyResult};
use std::collections::HashSet;

/// Nucleotide bases for mutations
const NUCLEOTIDES: [char; 4] = ['A', 'T', 'C', 'G'];

/// Generate mutation variants for a k-mer
///
/// This function generates all k-mers within the specified Hamming distance
/// from the original sequence.
///
/// # Arguments
/// * `sequence` - Original k-mer sequence
/// * `mutation_distance` - Maximum Hamming distance (number of mutations)
///
/// # Returns
/// Vector of mutation variants (including original sequence)
///
/// # Examples
/// ```
/// use rustkmer::fuzzy::mutation::generate_mutation_variants;
///
/// let variants = generate_mutation_variants("ATGCGATGCTAGCG", 1).unwrap();
/// assert!(variants.len() > 13); // Original + single mutations
/// assert!(variants.contains(&"ATGCGATGCTAGCG".to_string())); // Original
/// ```
pub fn generate_mutation_variants(sequence: &str, mutation_distance: usize) -> FuzzyResult<Vec<String>> {
    if sequence.is_empty() {
        return Ok(vec![]);
    }

    // Validate mutation distance
    let max_distance = (sequence.len() as f64 * constants::MAX_MUTATION_RATIO) as usize;
    if mutation_distance > max_distance {
        return Err(FuzzyError::InvalidParameters(
            format!("Mutation distance too large (max: {})", max_distance),
        ));
    }

    // Estimate total variants to check combinatorial explosion
    let estimated_variants = estimate_mutation_variants(sequence.len(), mutation_distance);
    if estimated_variants > constants::DEFAULT_MAX_VARIANTS {
        return Err(FuzzyError::TooManyVariants {
            actual: estimated_variants,
            limit: constants::DEFAULT_MAX_VARIANTS,
        });
    }

    let mut variants = HashSet::new();
    variants.insert(sequence.to_string()); // Include original sequence

    // Generate variants using recursive approach
    generate_mutation_combinations(sequence, 0, mutation_distance, 0, &mut variants);

    let mut result: Vec<String> = variants.into_iter().collect();
    result.sort(); // Sort for consistent output
    Ok(result)
}

/// Generate mutation combinations recursively
fn generate_mutation_combinations(
    sequence: &str,
    start_pos: usize,
    remaining_mutations: usize,
    current_mutations: usize,
    variants: &mut HashSet<String>,
) {
    if current_mutations >= remaining_mutations {
        return;
    }

    let chars: Vec<char> = sequence.chars().collect();

    for pos in start_pos..chars.len() {
        let original_char = chars[pos];

        // Try each possible mutation at this position
        for &nucleotide in &NUCLEOTIDES {
            if nucleotide == original_char {
                continue; // Skip same nucleotide
            }

            // Create mutated sequence
            let mut mutated_chars = chars.clone();
            mutated_chars[pos] = nucleotide;
            let mutated_sequence: String = mutated_chars.iter().collect();

            // Add to variants
            variants.insert(mutated_sequence.clone());

            // Continue generating more mutations
            generate_mutation_combinations(
                &mutated_sequence,
                pos + 1,
                remaining_mutations,
                current_mutations + 1,
                variants,
            );
        }
    }
}

/// Calculate Hamming distance between two sequences
///
/// # Arguments
/// * `seq1` - First sequence
/// * `seq2` - Second sequence
///
/// # Returns
/// Hamming distance (number of differing positions)
///
/// # Panics
/// Panics if sequences have different lengths
pub fn hamming_distance(seq1: &str, seq2: &str) -> usize {
    if seq1.len() != seq2.len() {
        panic!("Sequences must have the same length for Hamming distance calculation");
    }

    seq1.chars()
        .zip(seq2.chars())
        .filter(|(c1, c2)| c1 != c2)
        .count()
}

/// Check if two sequences are within mutation tolerance
pub fn within_mutation_tolerance(seq1: &str, seq2: &str, tolerance: usize) -> bool {
    if seq1.len() != seq2.len() {
        return false;
    }

    hamming_distance(seq1, seq2) <= tolerance
}

/// Find all k-mers within mutation tolerance of a query
///
/// This function filters a list of k-mers to find those within the specified
/// Hamming distance from the query sequence.
pub fn find_mutation_matches(
    query: &str,
    candidates: &[String],
    tolerance: usize,
) -> Vec<(String, usize)> {
    candidates
        .iter()
        .filter_map(|candidate| {
            let distance = hamming_distance(query, candidate);
            if distance <= tolerance {
                Some((candidate.clone(), distance))
            } else {
                None
            }
        })
        .collect()
}

/// Generate mutation variants using iterative approach
///
/// This method generates variants iteratively to avoid deep recursion
/// for sequences with high mutation tolerance.
pub fn generate_mutation_variants_iterative(sequence: &str, mutation_distance: usize) -> FuzzyResult<Vec<String>> {
    if sequence.is_empty() {
        return Ok(vec![]);
    }

    let max_distance = (sequence.len() as f64 * constants::MAX_MUTATION_RATIO) as usize;
    if mutation_distance > max_distance {
        return Err(FuzzyError::InvalidParameters(
            format!("Mutation distance too large (max: {})", max_distance),
        ));
    }

    let mut variants = HashSet::new();
    variants.insert(sequence.to_string());

    // Generate variants iteratively for each mutation level
    for _current_distance in 1..=mutation_distance {
        let mut new_variants = Vec::new();

        for existing_variant in &variants {
            let additional_variants = generate_single_mutations(existing_variant);
            new_variants.extend(additional_variants);
        }

        // Add new variants to the set
        for variant in new_variants {
            variants.insert(variant);
        }

        // Check combinatorial explosion
        if variants.len() > constants::DEFAULT_MAX_VARIANTS {
            return Err(FuzzyError::TooManyVariants {
                actual: variants.len(),
                limit: constants::DEFAULT_MAX_VARIANTS,
            });
        }
    }

    let mut result: Vec<String> = variants.into_iter().collect();
    result.sort();
    Ok(result)
}

/// Generate all single mutations for a sequence
fn generate_single_mutations(sequence: &str) -> Vec<String> {
    let chars: Vec<char> = sequence.chars().collect();
    let mut variants = Vec::new();

    for (pos, &original_char) in chars.iter().enumerate() {
        for &nucleotide in &NUCLEOTIDES {
            if nucleotide == original_char {
                continue;
            }

            let mut mutated_chars = chars.clone();
            mutated_chars[pos] = nucleotide;
            variants.push(mutated_chars.iter().collect::<String>());
        }
    }

    variants
}

/// Estimate the number of mutation variants
pub fn estimate_mutation_variants(sequence_length: usize, mutation_distance: usize) -> usize {
    if mutation_distance == 0 {
        return 1;
    }

    // Approximate calculation: sum_{i=0}^{mutation_distance} C(n, i) * 3^i
    // For performance, we use a simplified approximation
    let mut total = 1; // Original sequence

    for i in 1..=mutation_distance {
        // Simplified combination calculation
        let combinations = if i == 1 {
            sequence_length
        } else if i == 2 {
            sequence_length * (sequence_length - 1) / 2
        } else {
            // Approximate for higher orders
            sequence_length.pow(i as u32) / i.pow(i as u32)
        };

        total += combinations * 3_usize.pow(i as u32);
    }

    total
}

/// Check if mutation tolerance would exceed variant limits
pub fn would_exceed_mutation_limit(
    sequence_length: usize,
    mutation_distance: usize,
    max_variants: usize,
) -> bool {
    estimate_mutation_variants(sequence_length, mutation_distance) > max_variants
}

/// Validate mutation tolerance parameters
pub fn validate_mutation_params(sequence: &str, mutation_distance: usize, max_variants: Option<usize>) -> FuzzyResult<()> {
    // Validate sequence
    if !sequence.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
        return Err(FuzzyError::InvalidQuery(
            "Sequence contains invalid characters (only A,T,C,G allowed)".to_string(),
        ));
    }

    // Validate mutation distance
    let max_distance = (sequence.len() as f64 * constants::MAX_MUTATION_RATIO) as usize;
    if mutation_distance > max_distance {
        return Err(FuzzyError::InvalidParameters(
            format!("Mutation distance too large (max: {})", max_distance),
        ));
    }

    // Check combinatorial explosion
    if let Some(max_variants) = max_variants {
        if would_exceed_mutation_limit(sequence.len(), mutation_distance, max_variants) {
            return Err(FuzzyError::TooManyVariants {
                actual: estimate_mutation_variants(sequence.len(), mutation_distance),
                limit: max_variants,
            });
        }
    }

    Ok(())
}

/// Generate mutation variants with batch processing
///
/// This method processes variants in batches to reduce memory usage
/// for large mutation tolerances.
pub fn generate_mutation_variants_batched(
    sequence: &str,
    mutation_distance: usize,
    batch_size: usize,
    mut processor: impl FnMut(&[String]) -> FuzzyResult<()>,
) -> FuzzyResult<()> {
    validate_mutation_params(sequence, mutation_distance, None)?;

    let all_variants = generate_mutation_variants(sequence, mutation_distance)?;

    // Process in batches
    for chunk in all_variants.chunks(batch_size) {
        processor(chunk)?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hamming_distance() {
        assert_eq!(hamming_distance("ATGCG", "ATGCG"), 0);
        assert_eq!(hamming_distance("ATGCG", "TTGCG"), 1);
        assert_eq!(hamming_distance("ATGCG", "TTGCC"), 2);
        assert_eq!(hamming_distance("ATGCG", "TTGCA"), 3);
    }

    #[test]
    fn test_within_mutation_tolerance() {
        assert!(within_mutation_tolerance("ATGCG", "ATGCG", 0));
        assert!(within_mutation_tolerance("ATGCG", "TTGCG", 1));
        assert!(!within_mutation_tolerance("ATGCG", "TTGCC", 1));
        assert!(within_mutation_tolerance("ATGCG", "TTGCC", 2));
    }

    #[test]
    fn test_generate_mutation_variants_zero() {
        let variants = generate_mutation_variants("ATGCGATGCTAGCG", 0).unwrap();
        assert_eq!(variants.len(), 1);
        assert_eq!(variants[0], "ATGCGATGCTAGCG");
    }

    #[test]
    fn test_generate_mutation_variants_single() {
        let variants = generate_mutation_variants("ATGCG", 1).unwrap();
        assert!(variants.len() > 1);
        assert!(variants.contains(&"ATGCG".to_string())); // Original

        // Should contain all single mutations
        let expected_single_mutations = [
            "TTGCG", "CTGCG", "GTGCG", "AAGCG", "ACGCG", "AGGCG", "ATTGCG", "ATCCG", "ATGGCG", "ATGAG",
            "ATGCC", "ATGCA",
        ];

        for expected in &expected_single_mutations {
            assert!(variants.contains(&expected.to_string()));
        }
    }

    #[test]
    fn test_generate_mutation_variants_iterative() {
        let variants_recursive = generate_mutation_variants("ATGCG", 1).unwrap();
        let variants_iterative = generate_mutation_variants_iterative("ATGCG", 1).unwrap();

        // Should have the same number of variants
        assert_eq!(variants_recursive.len(), variants_iterative.len());

        // Convert to sets for comparison
        let recursive_set: HashSet<String> = variants_recursive.into_iter().collect();
        let iterative_set: HashSet<String> = variants_iterative.into_iter().collect();
        assert_eq!(recursive_set, iterative_set);
    }

    #[test]
    fn test_estimate_mutation_variants() {
        assert_eq!(estimate_mutation_variants(13, 0), 1);
        assert!(estimate_mutation_variants(13, 1) >= 13); // Original + 13 single mutations
        assert!(estimate_mutation_variants(13, 2) > estimate_mutation_variants(13, 1));
    }

    #[test]
    fn test_validate_mutation_params() {
        // Valid parameters
        assert!(validate_mutation_params("ATGCGATGCTAGCG", 1, None).is_ok());

        // Invalid characters
        assert!(validate_mutation_params("ATGCGXATGCTAGC", 1, None).is_err());

        // Mutation distance too large
        assert!(validate_mutation_params("ATGCGATGCTAGCG", 10, None).is_err());

        // Would exceed variant limits
        assert!(validate_mutation_params("ATGCGATGCTAGCG", 5, Some(100)).is_err());
    }

    #[test]
    fn test_find_mutation_matches() {
        let query = "ATGCGATGCTAGCG";
        let candidates = vec![
            "ATGCGATGCTAGCG".to_string(), // Exact match
            "TTGCGATGCTAGCG".to_string(), // 1 mutation
            "ATGCCATGCTAGCG".to_string(), // 1 mutation
            "TTGCCATGCTAGCG".to_string(), // 2 mutations
            "GCGATATGCTAGCA".to_string(), // Many mutations
        ];

        // With tolerance 1
        let matches_1 = find_mutation_matches(query, &candidates, 1);
        assert_eq!(matches_1.len(), 3);

        // With tolerance 2
        let matches_2 = find_mutation_matches(query, &candidates, 2);
        assert_eq!(matches_2.len(), 4);

        // Check distances
        let match_distances: Vec<_> = matches_1.iter().map(|(_, dist)| *dist).collect();
        assert!(match_distances.iter().all(|&d| d <= 1));
    }

    #[test]
    fn test_would_exceed_mutation_limit() {
        assert!(!would_exceed_mutation_limit(13, 1, 100)); // ~40 variants
        assert!(would_exceed_mutation_limit(13, 5, 1000)); // Many more variants
    }

    #[test]
    fn test_generate_mutation_variants_batched() {
        let mut processed_variants = Vec::new();
        let mut processor = |batch: &[String]| -> FuzzyResult<()> {
            for variant in batch {
                processed_variants.push(variant.clone());
            }
            Ok(())
        };

        generate_mutation_variants_batched("ATGCG", 1, 10, &mut processor).unwrap();

        // Should have processed all variants
        assert!(processed_variants.len() > 1);
        assert!(processed_variants.contains(&"ATGCG".to_string()));
    }

    #[test]
    #[should_panic(expected = "Sequences must have the same length")]
    fn test_hamming_distance_different_lengths() {
        hamming_distance("ATGC", "ATGCG");
    }
}