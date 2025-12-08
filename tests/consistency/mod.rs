//! Consistency tests to verify u128 implementation matches u64 results
//!
//! This module provides utilities and test frameworks to ensure that
//! the u128 implementation produces identical results to the u64 implementation
//! for comparable inputs.

pub mod utils;
pub mod generators;
pub mod test_small_k;
pub mod test_ambiguous;
pub mod test_canonical;
pub mod test_full_pipeline;

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// Statistics from processing
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProcessingStats {
    pub total_sequences: u64,
    pub valid_kmers: u64,
    pub skipped_ambiguous: u64,
    pub skipped_too_short: u64,
    pub unique_kmers: u64,
    pub total_count: u64,
}

/// Comparison result between u64 and u128 implementations
#[derive(Debug, PartialEq)]
pub struct ComparisonResult {
    pub stats_match: bool,
    pub kmer_counts_match: bool,
    pub differences: Vec<String>,
}

impl ProcessingStats {
    /// Check if two stats are equal
    pub fn matches(&self, other: &Self) -> bool {
        self.total_sequences == other.total_sequences
            && self.valid_kmers == other.valid_kmers
            && self.skipped_ambiguous == other.skipped_ambiguous
            && self.skipped_too_short == other.skipped_too_short
            && self.unique_kmers == other.unique_kmers
            && self.total_count == other.total_count
    }
}

/// Compare k-mer counts from two implementations
pub fn compare_kmer_counts(
    u64_counts: &HashMap<String, u32>,
    u128_counts: &HashMap<String, u32>,
) -> bool {
    if u64_counts.len() != u128_counts.len() {
        return false;
    }

    for (kmer, count64) in u64_counts {
        match u128_counts.get(kmer) {
            Some(count128) => {
                if count64 != count128 {
                    return false;
                }
            }
            None => return false,
        }
    }

    true
}