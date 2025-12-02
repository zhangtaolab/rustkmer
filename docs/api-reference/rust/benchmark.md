# Benchmark

**Module**: `rustkmer::cli::commands::benchmark`

## Overview

Comprehensive performance benchmarking command
Provides systematic performance testing and comparison capabilities
for RustKmer against Jellyfish across multiple dimensions.

## API Reference

### Structs

#### BenchmarkRunner

```rust
pub struct BenchmarkRunner {
```

Benchmark configuration and execution

### Fns

#### run_benchmark

```rust
pub fn run_benchmark(&self) -> ProcessingResult<()> {
```

Execute comprehensive benchmarking

#### find_test_files

```rust
fn find_test_files(&self) -> ProcessingResult<Vec<PathBuf>> {
```

Find test files in the data directory

#### find_or_create_databases

```rust
fn find_or_create_databases(&self, test_files: &[PathBuf]) -> ProcessingResult<Vec<PathBuf>> {
```

Find existing databases or create them

#### benchmark_file_reading

```rust
fn benchmark_file_reading(&self, file_path: &Path) -> ProcessingResult<BenchmarkResult> {
```

Benchmark file reading performance

#### generate_test_queries

```rust
fn generate_test_queries(&self, count: usize) -> Vec<String> {
```

Generate test queries

#### generate_fuzzy_queries

```rust
fn generate_fuzzy_queries(&self, count: usize) -> Vec<String> {
```

Generate fuzzy queries with wildcards

#### generate_summary

```rust
fn generate_summary(&self, results: &[BenchmarkResult], total_time: Duration) -> BenchmarkSummary {
```

Generate summary statistics

#### save_results

```rust
fn save_results(&self, results: &[BenchmarkResult], summary: &BenchmarkSummary) -> ProcessingResult<()> {
```

Save results to files

#### generate_visualizations

```rust
fn generate_visualizations(&self, _results: &[BenchmarkResult]) -> ProcessingResult<()> {
```

Generate visualizations

#### print_summary

```rust
fn print_summary(&self, summary: &BenchmarkSummary) {
```

Print benchmark summary

#### csv_headers

```rust
fn csv_headers() -> Vec<String> {
```

CSV headers for serialization

#### execute_benchmark

```rust
pub fn execute_benchmark(args: &crate::cli::args::Commands) -> ProcessingResult<()> {
```

Execute benchmark command

---

*Source: [`benchmark.rs`](../../../cli/commands/benchmark.rs)*