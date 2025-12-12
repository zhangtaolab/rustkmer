# rustkmer Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-28

## Active Technologies
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), thiserror (error handling), anyhow (error handling), rayon (parallel processing), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files) (002-jellyfish-query-implementation)
- Custom binary database format (.rkdb) with indexed k-mer storage (002-jellyfish-query-implementation)
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), rayon (parallel processing), bio (FASTA parsing), memmap2 (memory-mapped files) (003-parallel-query)
- Binary database files (Jellyfish .jf format, RustKmer .rkdb format) (003-parallel-query)
- Rust 1.80+ stable channel + clap (CLI), serde (serialization), rayon (parallel processing), memmap2 (memory mapping), thiserror (error handling), anyhow (error handling) (004-fuzzy-query)
- RKDB binary database format (existing) + memory-mapped file access (004-fuzzy-query)
- Rust 1.80+ (stable) + Python 3.8+ + PyO3 (Rust-Python bindings), setuptools-rust, serde, thiserror, anyhow, rayon (001-python-bindings)
- Existing RKDB binary database format + memory-mapped file access (001-python-bindings)
- Rust 1.80+ stable channel + PyO3 0.23.4 (Python bindings), serde 1.0 (serialization), thiserror 2.0 (error handling), rayon 1.10 (parallel processing), clap 4.5 (CLI), bio 2.0 (genomics), memmap2 0.9 (memory mapping) (005-python-api-improvements)
- Hybrid JSON + binary .rkdb format for database persistence, memory-mapped files for large datasets (005-python-api-improvements)
- Rust 1.80+ stable + Python 3.8+ via PyO3 0.23.4 + PyO3 (Python bindings), serde (serialization), thiserror (error handling), rayon (parallel processing), clap (CLI), bio (genomics) (007-api-compatibility)
- Single binary .rkdb files (RKDB format) - unified storage for both CLI and Python API (007-api-compatibility)
- Rust 1.80+ stable + PyO3 0.23.4, clap, serde, byteorder, rayon, criterion (008-u128-encoding)
- Binary RKDB files with memory-mapped access (008-u128-encoding)
- Binary RKDB files with memory-mapped access (version 2 format) (008-u128-encoding)
- Rust 1.80+ stable channel + clap v4.0+, serde, thiserror, anyhow, rayon, criterion, bio, memmap2 (009-rustkmer-cli-test)
- Rust 1.80+ stable channel + clap v4.5 (CLI), serde 1.0 (serialization), rayon 1.10 (parallel processing), memmap2 0.9 (memory mapping) (010-rkdb-merge)
- Binary RKDB format (custom k-mer database format) (010-rkdb-merge)
- Binary RKDB (.rkdb) files with custom database forma (010-rkdb-merge)
- Rust 1.80+ (stable) + Python 3.10+ + PyO3 0.23.4, serde, thiserror, anyhow, rayon, clap, bio, memmap2 (012-python-bindings-complete)
- RKDB二进制格式文件（自定义k-mer数据库格式） (012-python-bindings-complete)
- Rust 1.80+ stable with Python 3.10+ via PyO3 0.23 + PyO3, serde, thiserror, rayon, memmap2 (012-python-bindings-complete)
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), serde 1.0 (serialization) (012-python-bindings-complete)
- Binary RKDB files (custom k-mer database format) (012-python-bindings-complete)
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), serde 1.0+ (序列化), thiserror 2.0.17 (错误处理), clap 4.5.53 (CLI) (012-python-bindings-complete)
- 二进制RKDB文件（自定义k-mer数据库格式） (012-python-bindings-complete)
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), pytest 8.4+ (testing), subprocess (CLI invocation) (012-python-bindings-complete)
- Python 3.10+ + mkdocs, mkdocstrings[python], mkdocs-material theme (012-python-bindings-complete)
- Documentation files in `docs/` directory (012-python-bindings-complete)
- Python 3.10+ with PyO3 0.27.2 bindings to Rust 1.80+ + pytest 9.0+, pytest-benchmark, hypothesis, numpy, matplotlib (012-python-bindings-complete)

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
- 012-python-bindings-complete: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 012-python-bindings-complete: Added Python 3.10+ with PyO3 0.27.2 bindings to Rust 1.80+ + pytest 9.0+, pytest-benchmark, hypothesis, numpy, matplotlib
- 012-python-bindings-complete: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
