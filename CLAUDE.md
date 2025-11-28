# rustkmer Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-28

## Active Technologies
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), thiserror (error handling), anyhow (error handling), rayon (parallel processing), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files) (002-jellyfish-query-implementation)
- Custom binary database format (.rkdb) with indexed k-mer storage (002-jellyfish-query-implementation)
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), rayon (parallel processing), bio (FASTA parsing), memmap2 (memory-mapped files) (003-parallel-query)
- Binary database files (Jellyfish .jf format, RustKmer .rkdb format) (003-parallel-query)
- Rust 1.80+ stable channel + clap (CLI), serde (serialization), rayon (parallel processing), memmap2 (memory mapping), thiserror (error handling), anyhow (error handling) (004-fuzzy-query)
- RKDB binary database format (existing) + memory-mapped file access (004-fuzzy-query)

- Rust 1.80+ stable channel (latest stable for performance optimizations) + clap v4.0+ (CLI with derive macros), serde (serialization), thiserror (error handling), anyhow (error handling), rayon (parallel processing), criterion (benchmarks), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files) (001-jellyfish-rust-port)

## Project Structure

```text
src/
tests/
```

## Commands

cargo test [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] cargo clippy

## Code Style

Rust 1.80+ stable channel (latest stable for performance optimizations): Follow standard conventions

## Recent Changes
- 004-fuzzy-query: Added Rust 1.80+ stable channel + clap (CLI), serde (serialization), rayon (parallel processing), memmap2 (memory mapping), thiserror (error handling), anyhow (error handling)
- 003-parallel-query: Added Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), rayon (parallel processing), bio (FASTA parsing), memmap2 (memory-mapped files)
- 003-parallel-query: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
