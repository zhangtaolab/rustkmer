//! Core fuzzy query engine and types
//!
//! This module defines the main data structures and engine for executing fuzzy queries
//! against k-mer databases.

use crate::database::format::RKDatabase;
use crate::fuzzy::{constants, expansion, PerformanceMetrics, FuzzyError, FuzzyResult};
pub type FuzzyQueryResult<T> = Result<T, crate::fuzzy::FuzzyError>;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::time::Instant;

/// Configuration for position-specific mutation limits
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PositionMutationConfig {
    /// Multiple position groups with independent limits
    pub groups: Vec<PositionMutationGroup>,
    /// Global mutation limit across all groups (optional)
    pub global_max_mutations: Option<usize>,
}

/// A single group of positions with shared mutation limits
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionMutationGroup {
    /// Positions where mutations are allowed (0-based, sorted, unique)
    pub positions: Vec<usize>,
    /// Maximum number of mutations allowed in this group
    pub max_mutations: usize,
    /// Optional group name for debugging/logging
    #[serde(skip)]
    pub group_name: Option<String>,
}

impl PositionMutationConfig {
    /// Parse from string format like "3,4,5:2;6,7:1" or "4-7:1;10,12:2"
    pub fn parse(input: &str) -> FuzzyResult<Self> {
        let mut config = PositionMutationConfig::default();

        if input.trim().is_empty() {
            return Ok(config);
        }

        for (group_idx, group_str) in input.split(';').enumerate() {
            let group_str = group_str.trim();
            if group_str.is_empty() {
                continue;
            }

            let (positions_str, limit_str) = group_str
                .split_once(':')
                .ok_or_else(|| FuzzyError::InvalidParameters(
                    format!("Invalid group format '{}', expected 'positions:limit'", group_str)
                ))?;

            let mut positions = Vec::new();
            
            for s in positions_str.split(',') {
                let trimmed = s.trim();
                if trimmed.is_empty() {
                    return Err(FuzzyError::InvalidParameters(
                        format!("Group '{}': empty position specified", group_str)
                    ));
                }

                // Check if it's a range like "4-7"
                if let Some((start_str, end_str)) = trimmed.split_once('-') {
                    if let (Ok(start), Ok(end)) = (start_str.parse::<usize>(), end_str.parse::<usize>()) {
                        if start <= end {
                            positions.extend(start..=end);
                            continue;
                        }
                    }
                    // Invalid range format
                    return Err(FuzzyError::InvalidParameters(
                        format!("Group '{}': invalid range format '{}'", group_str, trimmed)
                    ));
                }

                // Single position parsing
                if let Ok(pos) = trimmed.parse::<usize>() {
                    positions.push(pos);
                } else {
                    return Err(FuzzyError::InvalidParameters(
                        format!("Group '{}': invalid position '{}'", group_str, trimmed)
                    ));
                }
            }

            // Validate that we have at least one position
            if positions.is_empty() {
                return Err(FuzzyError::InvalidParameters(
                    format!("Group '{}': no valid positions specified", group_str)
                ));
            }

            let max_mutations: usize = limit_str.trim()
                .parse()
                .map_err(|_| FuzzyError::InvalidParameters(
                    format!("Invalid mutation limit '{}'", limit_str.trim())
                ))?;

            config.groups.push(PositionMutationGroup {
                positions,
                max_mutations,
                group_name: Some(format!("group_{}", group_idx)),
            });
        }

        Ok(config)
    }

    /// Validate all groups
    pub fn validate(&self, sequence_length: usize) -> FuzzyResult<()> {
        let mut all_positions = HashSet::new();

        for (idx, group) in self.groups.iter().enumerate() {
            // Validate positions are within bounds
            for &pos in &group.positions {
                if pos >= sequence_length {
                    return Err(FuzzyError::InvalidParameters(
                        format!("Group {}: Position {} exceeds sequence length {} (valid: 0-{})",
                               idx, pos, sequence_length, sequence_length - 1)
                    ));
                }
            }

            // Check for overlap with previous groups
            for &pos in &group.positions {
                if !all_positions.insert(pos) {
                    return Err(FuzzyError::InvalidParameters(
                        format!("Group {}: Position {} already used in another group", idx, pos)
                    ));
                }
            }

            // Validate mutation limit
            if group.max_mutations > group.positions.len() {
                return Err(FuzzyError::InvalidParameters(
                    format!("Group {}: Max mutations ({}) cannot exceed number of positions ({})",
                           idx, group.max_mutations, group.positions.len())
                ));
            }
        }

        Ok(())
    }
}

/// Main fuzzy query configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzyQuery {
    /// The input query string (may contain 'N' wildcards)
    pub query_string: String,

    /// Target k-mer size for the database
    pub kmer_size: usize,

    /// Maximum allowed Hamming distance for mutations
    pub mutation_tolerance: usize,

    /// Maximum number of variants to generate (combinatorial explosion protection)
    pub max_variants: Option<usize>,

    /// Whether to enable parallel processing (deprecated - always uses sequential processing)
    pub enable_parallel: bool,

    /// Batch size for processing variants
    pub batch_size: usize,

    /// Position-specific mutation constraints (optional)
    pub position_mutations: Option<PositionMutationConfig>,
}

impl FuzzyQuery {
    /// Create a new fuzzy query with default parameters
    pub fn new(query_string: &str, kmer_size: usize, mutation_tolerance: usize) -> Self {
        Self {
            query_string: query_string.to_string(),
            kmer_size,
            mutation_tolerance,
            max_variants: Some(constants::DEFAULT_MAX_VARIANTS),
            enable_parallel: false, // Always sequential processing
            batch_size: constants::DEFAULT_BATCH_SIZE,
            position_mutations: None,
        }
    }

    /// Create a fuzzy query with custom parameters
    pub fn with_params(
        query_string: &str,
        kmer_size: usize,
        mutation_tolerance: usize,
        max_variants: Option<usize>,
        _enable_parallel: bool, // Ignored - always uses sequential processing
        batch_size: usize,
    ) -> Self {
        Self {
            query_string: query_string.to_string(),
            kmer_size,
            mutation_tolerance,
            max_variants,
            enable_parallel: false, // Always sequential processing
            batch_size,
            position_mutations: None,
        }
    }

    /// Create a fuzzy query with position mutation constraints
    pub fn with_position_mutations(
        query_string: &str,
        kmer_size: usize,
        mutation_tolerance: usize,
        max_variants: Option<usize>,
        _enable_parallel: bool, // Ignored - always uses sequential processing
        batch_size: usize,
        position_mutations: Option<PositionMutationConfig>,
    ) -> Self {
        Self {
            query_string: query_string.to_string(),
            kmer_size,
            mutation_tolerance,
            max_variants,
            enable_parallel: false, // Always sequential processing
            batch_size,
            position_mutations,
        }
    }

    /// Validate the query parameters
    pub fn validate(&self) -> FuzzyResult<()> {
        // Validate query string characters
        if !self.query_string.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
            return Err(FuzzyError::InvalidQuery(
                "Query contains invalid characters (only A,T,C,G,N allowed)".to_string(),
            ));
        }

        // Validate query string length
        if self.query_string.is_empty() {
            return Err(FuzzyError::InvalidQuery("Query string cannot be empty".to_string()));
        }

        if self.query_string.len() > 1000 {
            return Err(FuzzyError::InvalidQuery(
                "Query string too long (max 1000 characters)".to_string(),
            ));
        }

        // Validate k-mer size
        if self.kmer_size == 0 {
            return Err(FuzzyError::InvalidParameters("k-mer size must be > 0".to_string()));
        }

        // Validate mutation tolerance (only if not using position mutations)
        if self.position_mutations.is_none() &&
           self.mutation_tolerance > (self.kmer_size as f64 * constants::MAX_MUTATION_RATIO) as usize {
            return Err(FuzzyError::InvalidParameters(
                "Mutation tolerance too high (max k/2)".to_string(),
            ));
        }

        // Validate batch size
        if self.batch_size == 0 {
            return Err(FuzzyError::InvalidParameters("Batch size must be > 0".to_string()));
        }

        // Validate position mutations if specified
        if let Some(ref position_config) = self.position_mutations {
            position_config.validate(self.query_string.len())?;
        }

        Ok(())
    }
}

/// Represents the aggregated result from fuzzy query operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzyQueryResultData {
    /// Total count of all matching k-mers
    pub total_count: u64,

    /// Individual matches with their counts and query metadata
    pub individual_matches: Vec<KmerMatch>,

    /// Query metadata and performance information
    pub query_metadata: QueryMetadata,

    /// Success/failure status
    pub status: QueryStatus,
}

/// Represents an individual k-mer match
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KmerMatch {
    /// The matching k-mer sequence
    pub sequence: String,

    /// Count of this k-mer in the database
    pub count: u64,

    /// How this match relates to the original query
    pub match_type: MatchType,

    /// Hamming distance from original query (if applicable)
    pub hamming_distance: Option<usize>,
}

/// Types of matches that can occur during fuzzy querying
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MatchType {
    /// Exact match to original query
    Exact,

    /// Generated from wildcard expansion
    WildcardExpansion { wildcard_positions: Vec<usize> },

    /// Generated from mutation tolerance
    MutationTolerance { mutation_positions: Vec<usize> },

    /// Generated from length normalization
    LengthNormalization,
}

/// Metadata about the query execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryMetadata {
    /// Original query parameters
    pub query_params: FuzzyQuery,

    /// Number of variants generated and queried
    pub variants_generated: usize,

    /// Total query execution time in milliseconds
    pub query_time_ms: u64,

    /// Database size (number of k-mers)
    pub database_size: Option<u64>,

    /// Memory usage statistics
    pub memory_usage_mb: Option<f64>,
}

/// Query execution status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum QueryStatus {
    /// Query completed successfully
    Success,

    /// Query failed due to combinatorial explosion
    CombinatorialExplosion,

    /// Query failed due to invalid parameters
    InvalidParameters,

    /// Query failed due to database error
    DatabaseError,

    /// Query cancelled by user
    Cancelled,
}

/// Main fuzzy query engine
pub struct FuzzyQueryEngine {
    database: RKDatabase,
}

impl FuzzyQueryEngine {
    /// Create a new fuzzy query engine with the given database
    pub fn new(database: RKDatabase) -> Self {
        Self { database }
    }

    /// Execute a fuzzy query and return results
    pub fn execute_query(&self, query: &FuzzyQuery) -> FuzzyQueryResult<FuzzyQueryResultData> {
        let start_time = Instant::now();

        // Validate query parameters
        query.validate()?;

        // Generate query expansion
        let expansion = expansion::generate_query_expansion(query)?;

        // Check combinatorial explosion protection
        if let Some(max_variants) = query.max_variants {
            if expansion.combination_count > max_variants {
                return Ok(FuzzyQueryResultData {
                    total_count: 0,
                    individual_matches: vec![],
                    query_metadata: QueryMetadata {
                        query_params: query.clone(),
                        variants_generated: expansion.combination_count,
                        query_time_ms: start_time.elapsed().as_millis() as u64,
                        database_size: self.database.size(),
                        memory_usage_mb: None,
                    },
                    status: QueryStatus::CombinatorialExplosion,
                });
            }
        }

        // Execute database queries for all variants
        let individual_matches = self.query_variants(&expansion.concrete_kmers)?;

        // Calculate total count
        let total_count: u64 = individual_matches.iter().map(|m| m.count).sum();

        // Calculate query time
        let query_time_ms = start_time.elapsed().as_millis() as u64;

        Ok(FuzzyQueryResultData {
            total_count,
            individual_matches,
            query_metadata: QueryMetadata {
                query_params: query.clone(),
                variants_generated: expansion.combination_count,
                query_time_ms,
                database_size: self.database.size(),
                memory_usage_mb: None, // TODO: Implement memory tracking
            },
            status: QueryStatus::Success,
        })
    }

    /// Execute multiple queries in batch
    pub fn execute_batch(&self, queries: &[FuzzyQuery]) -> FuzzyQueryResult<Vec<FuzzyQueryResultData>> {
        let mut results = Vec::with_capacity(queries.len());

        for query in queries {
            results.push(self.execute_query(query)?);
        }

        Ok(results)
    }

    /// Get performance metrics for the last query execution
    pub fn get_last_metrics(&self) -> Option<PerformanceMetrics> {
        // TODO: Implement performance tracking
        None
    }

    /// Query the database for a list of concrete k-mers
    fn query_variants(&self, variants: &[String]) -> FuzzyQueryResult<Vec<KmerMatch>> {
        let mut matches = Vec::new();

        for variant in variants {
            // For canonical databases, we need to check both the variant and its reverse complement
            let rc_variant = self.reverse_complement(variant);

            if let Some(count) = self.database.query_kmer(variant) {
                matches.push(KmerMatch {
                    sequence: variant.clone(),
                    count,
                    match_type: MatchType::Exact,
                    hamming_distance: None,
                });
            } else if let Some(count) = self.database.query_kmer(&rc_variant) {
                matches.push(KmerMatch {
                    sequence: variant.clone(),
                    count,
                    match_type: MatchType::Exact,
                    hamming_distance: None,
                });
            }
        }

        Ok(matches)
    }

    /// Get reverse complement of a DNA sequence
    fn reverse_complement(&self, seq: &str) -> String {
        seq.chars().rev().map(|c| match c {
            'A' => 'T',
            'T' => 'A',
            'C' => 'G',
            'G' => 'C',
            'N' => 'N',
            _ => c,
        }).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuzzy_query_creation() {
        let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
        assert_eq!(query.query_string, "ATGCGATGCTAGCN");
        assert_eq!(query.kmer_size, 13);
        assert_eq!(query.mutation_tolerance, 0);
    }

    #[test]
    fn test_fuzzy_query_validation() {
        // Valid query
        let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
        assert!(query.validate().is_ok());

        // Invalid characters
        let query = FuzzyQuery::new("ATGCGXATGCTAGC", 13, 0);
        assert!(query.validate().is_err());

        // Empty query
        let query = FuzzyQuery::new("", 13, 0);
        assert!(query.validate().is_err());

        // Too many mutations
        let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 10);
        assert!(query.validate().is_err());
    }

    #[test]
    fn test_kmer_match() {
        let kmer_match = KmerMatch {
            sequence: "ATGCGATGCTAGCA".to_string(),
            count: 5,
            match_type: MatchType::WildcardExpansion {
                wildcard_positions: vec![12],
            },
            hamming_distance: Some(0),
        };

        assert_eq!(kmer_match.sequence, "ATGCGATGCTAGCA");
        assert_eq!(kmer_match.count, 5);
    }
}