# Wildcard

**Module**: `rustkmer::fuzzy::wildcard`

## Overview

Wildcard expansion for N nucleotides
This module handles the expansion of wildcard characters (N) into all possible
nucleotides (A, T, C, G) with efficient algorithms for combinatorial explosion management.

## API Reference

### Consts

#### NUCLEOTIDES

```rust
const NUCLEOTIDES: [char; 4] = ['A', 'T', 'C', 'G'];
```

Nucleotide bases

### Fns

#### expand_wildcards

```rust
pub fn expand_wildcards(query: &str) -> FuzzyResult<Vec<String>> {
```

Expand wildcards (N) in a query string to all possible combinations

# Arguments
* `query` - Query string possibly containing 'N' wildcards

# Returns
Vector of all concrete sequences without wildcards

# Examples
```
use rustkmer::fuzzy::wildcard::expand_wildcards;

let variants = expand_wildcards("ATGCGATGCTAGCN").unwrap();
assert_eq!(variants.len(), 4);
assert!(variants.contains(&"ATGCGATGCTAGCA".to_string()));
assert!(variants.contains(&"ATGCGATGCTAGCT".to_string()));
assert!(variants.contains(&"ATGCGATGCTAGCC".to_string()));
assert!(variants.contains(&"ATGCGATGCTAGCG".to_string()));
```

#### expand_wildcards_iterative

```rust
pub fn expand_wildcards_iterative(query: &str) -> FuzzyResult<Vec<String>> {
```

Expand wildcards using an iterative approach (memory efficient)

This method generates variants iteratively to avoid deep recursion
for queries with many wildcards.

#### count_wildcards

```rust
pub fn count_wildcards(query: &str) -> usize {
```

Count the number of wildcards in a query

#### estimate_wildcard_variants

```rust
pub fn estimate_wildcard_variants(query: &str) -> usize {
```

Estimate the number of variants that would be generated

#### would_exceed_wildcard_limit

```rust
pub fn would_exceed_wildcard_limit(query: &str, max_variants: usize) -> bool {
```

Check if a query would exceed variant limits

#### validate_wildcard_query

```rust
pub fn validate_wildcard_query(query: &str, max_variants: Option<usize>) -> FuzzyResult<()> {
```

Validate wildcard query parameters

#### remove_duplicate_variants

```rust
pub fn remove_duplicate_variants(variants: &mut Vec<String>) {
```

Remove duplicate variants (maintain order)

---

*Source: [`wildcard.rs`](../../../fuzzy/wildcard.rs)*