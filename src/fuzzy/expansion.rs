//! Query expansion and variant generation
//!
//! This module handles the generation of concrete k-mer variants from fuzzy queries,
//! including wildcard expansion, mutation tolerance, and length normalization.

use crate::fuzzy::{mutation, normalization, wildcard, FuzzyError, FuzzyResult};
use serde::{Deserialize, Serialize};
use std::time::Instant;

/// Represents how k-mer variants were generated
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum ExpansionMethod {
    /// Only wildcard expansion (N → A,T,C,G)
    WildcardOnly { wildcard_count: usize },

    /// Only mutation tolerance (Hamming distance)
    MutationOnly { mutation_distance: usize },

    /// Both wildcard expansion and mutation tolerance
    Combined {
        wildcard_count: usize,
        mutation_distance: usize,
    },

    /// Length normalization (padding/truncating)
    LengthNormalization {
        original_length: usize,
        target_length: usize,
    },
}

/// Represents the generated set of concrete k-mers to be queried
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryExpansion {
    /// List of concrete k-mer sequences without wildcards
    pub concrete_kmers: Vec<String>,

    /// How the k-mers were generated
    pub expansion_method: ExpansionMethod,

    /// Total number of combinations generated
    pub combination_count: usize,

    /// Original query string
    pub original_query: String,

    /// Performance metadata
    pub generation_time_ms: u64,
}

/// Generate query expansion from a fuzzy query
pub fn generate_query_expansion(query: &crate::fuzzy::FuzzyQuery) -> FuzzyResult<QueryExpansion> {
    let start_time = Instant::now();
    let mut concrete_kmers = Vec::new();
    let (normalized_query, expansion_method) = if query.query_string.len() != query.kmer_size {
        let variants = normalization::generate_normalized_variants(&query.query_string, query.kmer_size)?;
        (
            variants,
            ExpansionMethod::LengthNormalization {
                original_length: query.query_string.len(),
                target_length: query.kmer_size,
            },
        )
    } else {
        let wildcard_count = query.query_string.chars().filter(|&c| c == 'N').count();
        (
            vec![query.query_string.clone()],
            ExpansionMethod::WildcardOnly { wildcard_count },
        )
    };

    // Step 2: Apply wildcard expansion to each normalized query
    for normalized in normalized_query {
        let wildcard_variants = wildcard::expand_wildcards(&normalized, query.max_variants)?;
        concrete_kmers.extend(wildcard_variants);
    }

    // Step 3: Apply mutation tolerance if requested
    if query.mutation_tolerance > 0 {
        let mut mutation_variants = Vec::new();

        for concrete in &concrete_kmers {
            let variants = mutation::generate_mutation_variants(concrete, query.mutation_tolerance, query.max_variants)?;
            mutation_variants.extend(variants);
        }

        concrete_kmers = mutation_variants;

        // Update expansion method to combined
        

        if let ExpansionMethod::WildcardOnly { wildcard_count } = expansion_method {
            ExpansionMethod::Combined {
                wildcard_count,
                mutation_distance: query.mutation_tolerance,
            }
        } else {
            expansion_method
        }
    } else {
        // No mutation tolerance, use initial expansion method
        expansion_method
    };

    // Calculate final expansion method
    let final_expansion_method = if query.mutation_tolerance > 0 {
        if let ExpansionMethod::WildcardOnly { wildcard_count } = expansion_method {
            ExpansionMethod::Combined {
                wildcard_count,
                mutation_distance: query.mutation_tolerance,
            }
        } else {
            expansion_method
        }
    } else {
        expansion_method
    };

    // Remove duplicates while preserving order
    concrete_kmers.sort();
    concrete_kmers.dedup();

    let combination_count = concrete_kmers.len();
    let generation_time_ms = start_time.elapsed().as_millis() as u64;

    Ok(QueryExpansion {
        concrete_kmers,
        expansion_method: final_expansion_method,
        combination_count,
        original_query: query.query_string.clone(),
        generation_time_ms,
    })
}

/// Generate variants for batch queries
pub fn generate_batch_expansions(
    queries: &[crate::fuzzy::FuzzyQuery],
) -> FuzzyResult<Vec<QueryExpansion>> {
    let mut expansions = Vec::with_capacity(queries.len());

    for query in queries {
        expansions.push(generate_query_expansion(query)?);
    }

    Ok(expansions)
}

/// Validate expansion parameters
pub fn validate_expansion_params(
    query_length: usize,
    kmer_size: usize,
    mutation_tolerance: usize,
    max_variants: Option<usize>,
) -> FuzzyResult<()> {
    // Check length normalization constraints
    if query_length > kmer_size + 3 || query_length < kmer_size - 3 {
        return Err(FuzzyError::InvalidParameters(
            "Query length differs too much from k-mer size (max difference: 3)".to_string(),
        ));
    }

    // Check mutation tolerance constraints
    if mutation_tolerance > kmer_size / 2 {
        return Err(FuzzyError::InvalidParameters(
            "Mutation tolerance cannot exceed k-mer size / 2".to_string(),
        ));
    }

    // Check combinatorial explosion potential
    if let Some(max_variants) = max_variants {
        let wildcard_count = 0; // TODO: Calculate from query
        let estimated_variants = estimate_variant_count(wildcard_count, query_length, mutation_tolerance);

        if estimated_variants > max_variants {
            return Err(FuzzyError::TooManyVariants {
                actual: estimated_variants,
                limit: max_variants,
            });
        }
    }

    Ok(())
}

/// Estimate the number of variants that will be generated
pub fn estimate_variant_count(
    wildcard_count: usize,
    sequence_length: usize,
    mutation_tolerance: usize,
) -> usize {
    // Calculate wildcard expansion: 4^wildcard_count
    let wildcard_variants = 4_usize.pow(wildcard_count as u32);

    // Calculate mutation variants
    let mutation_variants = if mutation_tolerance == 0 {
        1
    } else {
        // Approximate: C(sequence_length, mutation_tolerance) * 3^mutation_tolerance
        // For performance, we use a simplified calculation
        sequence_length * mutation_tolerance * 3
    };

    // Total variants (rough estimate)
    wildcard_variants * mutation_variants
}

/// Check if an expansion would exceed limits
pub fn would_exceed_limits(
    wildcard_count: usize,
    sequence_length: usize,
    mutation_tolerance: usize,
    max_variants: usize,
) -> bool {
    estimate_variant_count(wildcard_count, sequence_length, mutation_tolerance) > max_variants
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fuzzy::FuzzyQuery;

    #[test]
    fn test_query_expansion_simple() {
        let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
        let expansion = generate_query_expansion(&query).unwrap();

        assert_eq!(expansion.original_query, "ATGCGATGCTAGCN");
        assert_eq!(expansion.combination_count, 4); // One wildcard = 4 variants
        assert!(expansion.concrete_kmers.contains(&"ATGCGATGCTAGCA".to_string()));
        assert!(expansion.concrete_kmers.contains(&"ATGCGATGCTAGCT".to_string()));
        assert!(expansion.concrete_kmers.contains(&"ATGCGATGCTAGCC".to_string()));
        assert!(expansion.concrete_kmers.contains(&"ATGCGATGCTAGCG".to_string()));
    }

    #[test]
    fn test_query_expansion_multiple_wildcards() {
        let query = FuzzyQuery::new("ATNNGATGCTAGCG", 13, 0);
        let expansion = generate_query_expansion(&query).unwrap();

        assert_eq!(expansion.combination_count, 16); // Two wildcards = 4^2 = 16
    }

    #[test]
    fn test_query_expansion_with_mutations() {
        let query = FuzzyQuery::new("ATGCGATGCTAGCG", 13, 1);
        let expansion = generate_query_expansion(&query).unwrap();

        // Should have many mutation variants
        assert!(expansion.combination_count > 13); // Original + 13 possible single mutations
    }

    #[test]
    fn test_estimate_variant_count() {
        // Single wildcard
        assert_eq!(estimate_variant_count(1, 13, 0), 4);

        // Two wildcards
        assert_eq!(estimate_variant_count(2, 13, 0), 16);

        // Single mutation
        assert!(estimate_variant_count(0, 13, 1) >= 13);
    }

    #[test]
    fn test_would_exceed_limits() {
        assert!(would_exceed_limits(3, 13, 0, 50)); // 4^3 = 64 > 50
        assert!(!would_exceed_limits(2, 13, 0, 20)); // 4^2 = 16 <= 20
    }

    #[test]
    fn test_validate_expansion_params() {
        // Valid parameters
        assert!(validate_expansion_params(13, 13, 0, Some(100)).is_ok());

        // Length difference too large
        assert!(validate_expansion_params(20, 13, 0, Some(100)).is_err());

        // Mutation tolerance too high
        assert!(validate_expansion_params(13, 13, 8, Some(100)).is_err());
    }
}