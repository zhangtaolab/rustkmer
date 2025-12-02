# Fuzzy Query

**Module**: `rustkmer::python::fuzzy_query`

## Overview

Python bindings for FuzzyQuery operations

## API Reference

### Fns

#### validate

```rust
fn validate(&self) -> PyResult<bool> {
```

Validate the fuzzy query pattern

#### get_variant_count

```rust
fn get_variant_count(&self) -> PyResult<usize> {
```

Get the number of variants that will be generated

#### get_wildcard_count

```rust
fn get_wildcard_count(&self) -> PyResult<usize> {
```

Get the number of wildcards in the query

#### expand_wildcards

```rust
fn expand_wildcards(&self) -> PyResult<Vec<String>> {
```

Expand wildcards (N) to generate all possible k-mers

#### generate_mutations

```rust
fn generate_mutations(&self, target_kmer: &str) -> PyResult<Vec<String>> {
```

Generate mutations for a target k-mer within tolerance

#### execute

```rust
fn execute(&self, _database_path: &str) -> PyResult<PyFuzzyQueryResult> {
```

Execute fuzzy query against a database

#### get_query_string

```rust
fn get_query_string(&self) -> PyResult<String> {
```

Get the query string

#### get_kmer_size

```rust
fn get_kmer_size(&self) -> PyResult<usize> {
```

Get the k-mer size

#### get_mutation_tolerance

```rust
fn get_mutation_tolerance(&self) -> PyResult<usize> {
```

Get the mutation tolerance

#### get_k

```rust
fn get_k(&self) -> PyResult<usize> {
```

Get the k-mer size (alias for get_kmer_size)

#### get_max_distance

```rust
fn get_max_distance(&self) -> PyResult<usize> {
```

Get the max distance (alias for get_mutation_tolerance)

#### get_max_variants

```rust
fn get_max_variants(&self) -> PyResult<usize> {
```

Get max_variants as a method (backward compatibility)

#### set_max_variants

```rust
fn set_max_variants(&mut self, value: usize) -> PyResult<()> {
```

Set max_variants with validation (method version - backward compatibility)

#### is_valid

```rust
fn is_valid(&self) -> PyResult<bool> {
```

Check if the query is valid

#### __repr__

```rust
fn __repr__(&self) -> String {
```

Get a string representation

#### __str__

```rust
fn __str__(&self) -> String {
```

Get a string representation

---

*Source: [`fuzzy_query.rs`](../../../python/fuzzy_query.rs)*