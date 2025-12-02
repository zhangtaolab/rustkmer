# Mutation

**Module**: `rustkmer::fuzzy::mutation`

## Overview

Mutation tolerance using Hamming distance
This module implements mutation tolerance by generating k-mer variants
within a specified Hamming distance from the original query.

## API Reference

### Consts

#### NUCLEOTIDES

```rust
const NUCLEOTIDES: [char; 4] = ['A', 'T', 'C', 'G'];
```

Nucleotide bases for mutations

### Fns

#### generate_mutation_variants

```rust
pub fn generate_mutation_variants(sequence: &str, mutation_distance: usize) -> FuzzyResult<Vec<String>> {
```

Generate mutation variants for a k-mer

This function generates all k-mers within the specified Hamming distance
from the original sequence.

# Arguments
* `sequence` - Original k-mer sequence
* `mutation_distance` - Maximum Hamming distance (number of mutations)

# Returns
Vector of mutation variants (including original sequence)

# Examples
```
use rustkmer::fuzzy::mutation::generate_mutation_variants;

let variants = generate_mutation_variants("ATGCGATGCTAGCG", 1).unwrap();
assert!(variants.len() > 13); // Original + single mutations
assert!(variants.contains(&"ATGCGATGCTAGCG".to_string())); // Original
```

#### hamming_distance

```rust
pub fn hamming_distance(seq1: &str, seq2: &str) -> usize {
```

Calculate Hamming distance between two sequences

# Arguments
* `seq1` - First sequence
* `seq2` - Second sequence

# Returns
Hamming distance (number of differing positions)

# Panics
Panics if sequences have different lengths

#### within_mutation_tolerance

```rust
pub fn within_mutation_tolerance(seq1: &str, seq2: &str, tolerance: usize) -> bool {
```

Check if two sequences are within mutation tolerance

#### generate_mutation_variants_iterative

```rust
pub fn generate_mutation_variants_iterative(sequence: &str, mutation_distance: usize) -> FuzzyResult<Vec<String>> {
```

Generate mutation variants using iterative approach

This method generates variants iteratively to avoid deep recursion
for sequences with high mutation tolerance.

#### generate_single_mutations

```rust
fn generate_single_mutations(sequence: &str) -> Vec<String> {
```

Generate all single mutations for a sequence

#### estimate_mutation_variants

```rust
pub fn estimate_mutation_variants(sequence_length: usize, mutation_distance: usize) -> usize {
```

Estimate the number of mutation variants

#### validate_mutation_params

```rust
pub fn validate_mutation_params(sequence: &str, mutation_distance: usize, max_variants: Option<usize>) -> FuzzyResult<()> {
```

Validate mutation tolerance parameters

---

*Source: [`mutation.rs`](../../../fuzzy/mutation.rs)*