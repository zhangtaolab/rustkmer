//! Length normalization for k-mer queries
//!
//! This module handles length normalization by padding or truncating queries
//! to match the database k-mer size using 'N' characters.

use crate::fuzzy::{FuzzyError, FuzzyResult};
use std::cmp::Ordering;

/// Normalize query length to match k-mer size
///
/// This function generates all possible normalized variants when the query
/// length differs from the target k-mer size.
///
/// # Arguments
/// * `query` - Original query string
/// * `kmer_size` - Target k-mer size
///
/// # Returns
/// Vector of normalized query strings
///
/// # Examples
/// ```
/// use rustkmer::fuzzy::normalization::generate_normalized_variants;
///
/// // Query shorter than k-mer size (12mer for 13mer database)
/// let variants = generate_normalized_variants("ATGCGATGCTAG", 13).unwrap();
/// assert_eq!(variants.len(), 2); // N + query OR query + N
/// assert!(variants.contains(&"NATGCGATGCTAG".to_string()));
/// assert!(variants.contains(&"ATGCGATGCTAGN".to_string()));
///
/// // Query longer than k-mer size (15mer for 13mer database)
/// let variants = generate_normalized_variants("ATGCGATGCTAGCGT", 13).unwrap();
/// assert!(variants.len(), 3); // All possible 13mer substrings
/// ```
pub fn generate_normalized_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
    let query_len = query.len();

    match query_len.cmp(&kmer_size) {
        Ordering::Equal => {
            // Already correct length
            Ok(vec![query.to_string()])
        }
        Ordering::Less => {
            // Query is shorter, need padding
            generate_padded_variants(query, kmer_size)
        }
        Ordering::Greater => {
            // Query is longer, need truncation
            generate_truncated_variants(query, kmer_size)
        }
    }
}

/// Generate padded variants when query is shorter than k-mer size
fn generate_padded_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
    let query_len = query.len();
    let padding_needed = kmer_size - query_len;

    // Check if padding difference is reasonable
    if padding_needed > 3 {
        return Err(FuzzyError::InvalidParameters(
            "Query is too short for k-mer size (max difference: 3)".to_string(),
        ));
    }

    let mut variants = Vec::new();

    // Generate all possible padding combinations
    // For simplicity, we use N padding at the beginning and/or end
    for front_padding in 0..=padding_needed {
        let back_padding = padding_needed - front_padding;

        let front_n = "N".repeat(front_padding);
        let back_n = "N".repeat(back_padding);
        let normalized = format!("{}{}{}", front_n, query, back_n);

        variants.push(normalized);
    }

    Ok(variants)
}

/// Generate truncated variants when query is longer than k-mer size
fn generate_truncated_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
    let query_len = query.len();
    let excess = query_len - kmer_size;

    // Check if truncation difference is reasonable
    if excess > 3 {
        return Err(FuzzyError::InvalidParameters(
            "Query is too long for k-mer size (max difference: 3)".to_string(),
        ));
    }

    let mut variants = Vec::new();

    // Generate all possible k-mer substrings
    for start in 0..=excess {
        let end = start + kmer_size;
        let normalized = &query[start..end];
        variants.push(normalized.to_string());
    }

    Ok(variants)
}

/// Validate length normalization parameters
pub fn validate_normalization_params(query: &str, kmer_size: usize) -> FuzzyResult<()> {
    let query_len = query.len();

    // Check k-mer size is reasonable
    if !(5..=31).contains(&kmer_size) {
        return Err(FuzzyError::InvalidParameters(
            "k-mer size must be between 5 and 31".to_string(),
        ));
    }

    // Check length difference constraints
    let length_diff = query_len.abs_diff(kmer_size);

    if length_diff > 3 {
        return Err(FuzzyError::InvalidParameters(
            "Query length differs too much from k-mer size (max difference: 3)".to_string(),
        ));
    }

    // Validate query characters
    if !query.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
        return Err(FuzzyError::InvalidQuery(
            "Query contains invalid characters (only A,T,C,G,N allowed)".to_string(),
        ));
    }

    Ok(())
}

/// Estimate the number of normalization variants that would be generated
pub fn estimate_normalization_variants(query: &str, kmer_size: usize) -> usize {
    let query_len = query.len();

    match query_len.cmp(&kmer_size) {
        Ordering::Equal => 1,
        Ordering::Less => {
            let padding_needed = kmer_size - query_len;
            padding_needed + 1 // All possible front/back padding combinations
        }
        Ordering::Greater => {
            let excess = query_len - kmer_size;
            excess + 1 // All possible substring start positions
        }
    }
}

/// Check if normalization would exceed variant limits
pub fn would_exceed_normalization_limit(query: &str, kmer_size: usize, max_variants: usize) -> bool {
    estimate_normalization_variants(query, kmer_size) > max_variants
}

/// Apply intelligent length normalization
///
/// This function uses heuristics to determine the best normalization strategy
/// based on the query and database characteristics.
pub fn intelligent_normalization(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
    let query_len = query.len();
    let length_diff = query_len.abs_diff(kmer_size);

    // If lengths are equal, no normalization needed
    if query_len == kmer_size {
        return Ok(vec![query.to_string()]);
    }

    // If difference is small, use standard normalization
    if length_diff <= 1 {
        return generate_normalized_variants(query, kmer_size);
    }

    // For larger differences, apply heuristic selection
    if query_len < kmer_size {
        // Shorter query: prefer front padding for biological relevance
        let mut variants = Vec::new();

        // Try front padding first (more biologically relevant)
        let front_n = "N".repeat(kmer_size - query_len);
        variants.push(format!("{}{}", front_n, query));

        // Try end padding as alternative
        let back_n = "N".repeat(kmer_size - query_len);
        variants.push(format!("{}{}", query, back_n));

        // Try balanced padding if reasonable
        if kmer_size - query_len == 2 {
            variants.push(format!("N{}N", query));
        }

        Ok(variants)
    } else {
        // Longer query: prefer central substrings
        let variants = generate_truncated_variants(query, kmer_size)?;

        // Sort by biological relevance (center substrings first)
        let mut sorted_variants = variants;
        sorted_variants.sort_by(|a, b| {
            // Calculate how "central" each substring is
            let a_start = query.find(a).unwrap_or(0);
            let b_start = query.find(b).unwrap_or(0);

            let a_center_distance = (a_start as isize - (query_len as isize / 2)).abs();
            let b_center_distance = (b_start as isize - (query_len as isize / 2)).abs();

            a_center_distance.cmp(&b_center_distance)
        });

        Ok(sorted_variants)
    }
}

/// Validate and normalize a query string
///
/// This is a convenience function that validates the query parameters
/// and returns normalized variants.
pub fn validate_and_normalize(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
    validate_normalization_params(query, kmer_size)?;
    generate_normalized_variants(query, kmer_size)
}

/// Get normalization information for a query
pub fn get_normalization_info(query: &str, kmer_size: usize) -> FuzzyResult<NormalizationInfo> {
    let query_len = query.len();
    validate_normalization_params(query, kmer_size)?;

    let info = match query_len.cmp(&kmer_size) {
        Ordering::Equal => NormalizationInfo {
            original_length: query_len,
            target_length: kmer_size,
            normalization_type: NormalizationType::None,
            variants_count: 1,
            padding_front: 0,
            padding_back: 0,
            truncation_start: 0,
        },
        Ordering::Less => {
            let padding_needed = kmer_size - query_len;
            NormalizationInfo {
                original_length: query_len,
                target_length: kmer_size,
                normalization_type: NormalizationType::Padding,
                variants_count: padding_needed + 1,
                padding_front: padding_needed,
                padding_back: padding_needed,
                truncation_start: 0,
            }
        }
        Ordering::Greater => {
            let excess = query_len - kmer_size;
            NormalizationInfo {
                original_length: query_len,
                target_length: kmer_size,
                normalization_type: NormalizationType::Truncation,
                variants_count: excess + 1,
                padding_front: 0,
                padding_back: 0,
                truncation_start: excess,
            }
        }
    };

    Ok(info)
}

/// Information about how a query was normalized
#[derive(Debug, Clone)]
pub struct NormalizationInfo {
    pub original_length: usize,
    pub target_length: usize,
    pub normalization_type: NormalizationType,
    pub variants_count: usize,
    pub padding_front: usize,
    pub padding_back: usize,
    pub truncation_start: usize,
}

/// Type of normalization applied
#[derive(Debug, Clone, PartialEq)]
pub enum NormalizationType {
    None,
    Padding,
    Truncation,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_normalized_variants_equal_length() {
        let variants = generate_normalized_variants("ATGCGATGCTAGCG", 13).unwrap();
        assert_eq!(variants.len(), 1);
        assert_eq!(variants[0], "ATGCGATGCTAGCG");
    }

    #[test]
    fn test_generate_normalized_variants_shorter() {
        let variants = generate_normalized_variants("ATGCGATGCTAG", 13).unwrap();
        assert_eq!(variants.len(), 2);
        assert!(variants.contains(&"NATGCGATGCTAG".to_string()));
        assert!(variants.contains(&"ATGCGATGCTAGN".to_string()));
    }

    #[test]
    fn test_generate_normalized_variants_much_shorter() {
        let variants = generate_normalized_variants("ATGCGATGCT", 13).unwrap();
        assert_eq!(variants.len(), 4); // 3 chars shorter, so 4 padding combinations
        assert!(variants.contains(&"NNNATGCGATGCT".to_string()));
        assert!(variants.contains(&"NNATGCGATGCTN".to_string()));
        assert!(variants.contains(&"NATGCGATGCTNN".to_string()));
        assert!(variants.contains(&"ATGCGATGCTNNN".to_string()));
    }

    #[test]
    fn test_generate_normalized_variants_longer() {
        let variants = generate_normalized_variants("ATGCGATGCTAGCGT", 13).unwrap();
        assert_eq!(variants.len(), 3); // 2 chars longer, so 3 possible substrings
        assert!(variants.contains(&"ATGCGATGCTAGC".to_string()));
        assert!(variants.contains(&"TGCGATGCTAGCG".to_string()));
        assert!(variants.contains(&"GCGATGCTAGCGT".to_string()));
    }

    #[test]
    fn test_validate_normalization_params() {
        // Valid parameters
        assert!(validate_normalization_params("ATGCGATGCTAG", 13).is_ok());

        // Invalid k-mer size
        assert!(validate_normalization_params("ATGCGATGCTAG", 2).is_err());
        assert!(validate_normalization_params("ATGCGATGCTAG", 50).is_err());

        // Length difference too large
        assert!(validate_normalization_params("ATGCG", 13).is_err());
        assert!(validate_normalization_params("ATGCGATGCTAGCGTGCATGCGAT", 13).is_err());

        // Invalid characters
        assert!(validate_normalization_params("ATGCGXATGCTAG", 13).is_err());
    }

    #[test]
    fn test_estimate_normalization_variants() {
        assert_eq!(estimate_normalization_variants("ATGCGATGCTAGCG", 13), 1);
        assert_eq!(estimate_normalization_variants("ATGCGATGCTAG", 13), 2);
        assert_eq!(estimate_normalization_variants("ATGCGATGCT", 13), 4);
        assert_eq!(estimate_normalization_variants("ATGCGATGCTAGCGT", 13), 3);
    }

    #[test]
    fn test_intelligent_normalization() {
        // Shorter query with small difference
        let variants = intelligent_normalization("ATGCGATGCTAG", 13).unwrap();
        assert_eq!(variants.len(), 2);
        assert!(variants.contains(&"NATGCGATGCTAG".to_string()));
        assert!(variants.contains(&"ATGCGATGCTAGN".to_string()));

        // Shorter query with larger difference
        let variants = intelligent_normalization("ATGCGATGCT", 13).unwrap();
        assert_eq!(variants.len(), 3); // Reduced variants with heuristics

        // Longer query
        let variants = intelligent_normalization("ATGCGATGCTAGCGT", 13).unwrap();
        assert_eq!(variants.len(), 3);
        // Center substring should be first (more biologically relevant)
        assert_eq!(variants[0], "ATGCGATGCTAGC");
    }

    #[test]
    fn test_get_normalization_info() {
        let info = get_normalization_info("ATGCGATGCTAG", 13).unwrap();
        assert_eq!(info.original_length, 12);
        assert_eq!(info.target_length, 13);
        assert_eq!(info.normalization_type, NormalizationType::Padding);
        assert_eq!(info.variants_count, 2);
        assert_eq!(info.padding_front, 1);
        assert_eq!(info.padding_back, 1);

        let info = get_normalization_info("ATGCGATGCTAGCGT", 13).unwrap();
        assert_eq!(info.original_length, 15);
        assert_eq!(info.target_length, 13);
        assert_eq!(info.normalization_type, NormalizationType::Truncation);
        assert_eq!(info.variants_count, 3);
        assert_eq!(info.truncation_start, 2);
    }

    #[test]
    fn test_validate_and_normalize() {
        let variants = validate_and_normalize("ATGCGATGCTAG", 13).unwrap();
        assert_eq!(variants.len(), 2);

        // Should fail validation
        assert!(validate_and_normalize("ATGCGXATGCTAG", 13).is_err());
    }

    #[test]
    fn test_would_exceed_normalization_limit() {
        assert!(!would_exceed_normalization_limit("ATGCGATGCTAG", 13, 10));
        assert!(!would_exceed_normalization_limit("ATGCGATGCT", 13, 10));
        assert!(would_exceed_normalization_limit("ATGCG", 13, 2)); // Would need 4 variants
    }
}