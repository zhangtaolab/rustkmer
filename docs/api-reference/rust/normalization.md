# Normalization

**Module**: `rustkmer::fuzzy::normalization`

## Overview

Length normalization for k-mer queries
This module handles length normalization by padding or truncating queries
to match the database k-mer size using 'N' characters.

## API Reference

### Fns

#### generate_normalized_variants

```rust
pub fn generate_normalized_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
```

Normalize query length to match k-mer size

This function generates all possible normalized variants when the query
length differs from the target k-mer size.

# Arguments
* `query` - Original query string
* `kmer_size` - Target k-mer size

# Returns
Vector of normalized query strings

# Examples
```
use rustkmer::fuzzy::normalization::generate_normalized_variants;

// Query shorter than k-mer size (12mer for 13mer database)
let variants = generate_normalized_variants("ATGCGATGCTAG", 13).unwrap();
assert_eq!(variants.len(), 2); // N + query OR query + N
assert!(variants.contains(&"NATGCGATGCTAG".to_string()));
assert!(variants.contains(&"ATGCGATGCTAGN".to_string()));

// Query longer than k-mer size (15mer for 13mer database)
let variants = generate_normalized_variants("ATGCGATGCTAGCGT", 13).unwrap();
assert!(variants.len(), 3); // All possible 13mer substrings
```

#### generate_padded_variants

```rust
fn generate_padded_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
```

Generate padded variants when query is shorter than k-mer size

#### generate_truncated_variants

```rust
fn generate_truncated_variants(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
```

Generate truncated variants when query is longer than k-mer size

#### validate_normalization_params

```rust
pub fn validate_normalization_params(query: &str, kmer_size: usize) -> FuzzyResult<()> {
```

Validate length normalization parameters

#### estimate_normalization_variants

```rust
pub fn estimate_normalization_variants(query: &str, kmer_size: usize) -> usize {
```

Estimate the number of normalization variants that would be generated

#### would_exceed_normalization_limit

```rust
pub fn would_exceed_normalization_limit(query: &str, kmer_size: usize, max_variants: usize) -> bool {
```

Check if normalization would exceed variant limits

#### intelligent_normalization

```rust
pub fn intelligent_normalization(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
```

Apply intelligent length normalization

This function uses heuristics to determine the best normalization strategy
based on the query and database characteristics.

#### validate_and_normalize

```rust
pub fn validate_and_normalize(query: &str, kmer_size: usize) -> FuzzyResult<Vec<String>> {
```

Validate and normalize a query string

This is a convenience function that validates the query parameters
and returns normalized variants.

#### get_normalization_info

```rust
pub fn get_normalization_info(query: &str, kmer_size: usize) -> FuzzyResult<NormalizationInfo> {
```

Get normalization information for a query

---

*Source: [`normalization.rs`](../../../fuzzy/normalization.rs)*