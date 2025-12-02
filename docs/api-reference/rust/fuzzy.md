# Fuzzy

**Module**: `rustkmer::cli::commands::fuzzy`

## Overview

Fuzzy query CLI commands
This module implements the command-line interface for fuzzy k-mer queries,
supporting wildcard expansion, length normalization, and mutation tolerance.

## API Reference

### Fns

#### execute_fuzzy_query

```rust
pub fn execute_fuzzy_query(args: &FuzzyQueryArgs) -> Result<()> {
```

Execute fuzzy query command

#### execute_fuzzy_query_batch

```rust
pub fn execute_fuzzy_query_batch(args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Execute batch fuzzy query command

#### load_queries_from_file

```rust
fn load_queries_from_file(file_path: &PathBuf) -> Result<Vec<String>> {
```

Load queries from file

#### output_fuzzy_result

```rust
fn output_fuzzy_result(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
```

Output fuzzy query result

#### output_table_format

```rust
fn output_table_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
```

Output in table format

#### output_json_format

```rust
fn output_json_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
```

Output in JSON format

#### output_tsv_format

```rust
fn output_tsv_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
```

Output in TSV format

#### output_csv_format

```rust
fn output_csv_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
```

Output in CSV format

#### output_batch_results

```rust
fn output_batch_results(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Output batch results

#### output_batch_json

```rust
fn output_batch_json(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Output batch results in JSON format

#### output_batch_table

```rust
fn output_batch_table(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Output batch results in table format

#### output_batch_tsv

```rust
fn output_batch_tsv(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Output batch results in TSV format

#### output_batch_csv

```rust
fn output_batch_csv(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
```

Output batch results in CSV format

---

*Source: [`fuzzy.rs`](../../../cli/commands/fuzzy.rs)*