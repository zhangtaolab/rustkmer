# rustkmer Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-28

## Active Technologies
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), thiserror (error handling), anyhow (error handling), rayon (parallel processing), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files)
- Custom binary database format (.rkdb) with indexed k-mer storage
- Rust 1.80+ stable channel + clap v4.0+ (CLI), serde (serialization), rayon (parallel processing), bio (FASTA parsing), memmap2 (memory-mapped files)
- Binary RKDB format for database storage
- Rust 1.80+ stable channel + clap (CLI), serde (serialization), rayon (parallel processing), memmap2 (memory mapping), thiserror (error handling), anyhow (error handling)
- RKDB binary database format (existing) + memory-mapped file access
- Rust 1.80+ stable + Python 3.8+ + PyO3 (Rust-Python bindings), setuptools-rust, serde, thiserror, anyhow, rayon
- Existing RKDB binary database format + memory-mapped file access
- Rust 1.80+ stable channel + PyO3 0.23.4 (Python bindings), serde 1.0 (serialization), thiserror 2.0 (error handling), rayon 1.10 (parallel processing), clap 4.5 (CLI), bio 2.0 (genomics), memmap2 0.9 (memory mapping)
- Hybrid JSON + binary .rkdb format for database persistence, memory-mapped files for large datasets
- Rust 1.80+ stable + Python 3.8+ via PyO3 0.23.4 + PyO3 (Python bindings), serde (serialization), thiserror (error handling), rayon (parallel processing), clap (CLI), bio (genomics)
- Single binary .rkdb files (RKDB format) - unified storage for both CLI and Python API
- Rust 1.80+ stable + PyO3 0.23.4, clap, serde, byteorder, rayon, criterion
- Binary RKDB files with memory-mapped access
- Binary RKDB files with memory-mapped access (version 2 format)
- Rust 1.80+ stable channel + clap v4.0+, serde, thiserror, anyhow, rayon, criterion, bio, memmap2
- Rust 1.80+ stable channel + clap 4.5 (CLI), serde 1.0 (serialization), rayon 1.10 (parallel processing), memmap2 0.9 (memory mapping)
- Binary RKDB format (custom k-mer database format)
- Binary RKDB (.rkdb) files with custom database forma
- Rust 1.80+ (stable) + Python 3.10+ + PyO3 0.23.4, serde, thiserror, anyhow, rayon, clap, bio, memmap2
- RKDB二进制格式文件（自定义k-mer数据库格式）
- Rust 1.80+ (stable) + Python 3.10+ via PyO3 0.23.4 + PyO3, serde, thiserror, rayon, memmap2
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), serde 1.0 (serialization)
- Binary RKDB files (custom k-mer database format)
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), serde 1.0+ (序列化), thiserror 2.0.17 (错误处理), clap 4.5.53 (CLI)
- 二进制RKDB文件（自定义k-mer数据库格式）
- Rust 1.80+ stable, Python 3.10+ + PyO3 0.27.2 (Python bindings), pytest 8.4+ (testing), subprocess (CLI invocation)
- Python 3.10+ + mkdocs, mkdocstrings[python], mkdocs-material theme
- Documentation files in `docs/` directory
- Python 3.10+ (for the API), Rust 1.80+ (existing CLI) + subprocess (Python standard library), pytest for testing
- Binary .rkdb files (existing format)
- Rust 1.80+ (stable) + Python 3.10+ via PyO3 0.27.2
- Rust 1.80+ (stable) + Python 3.10+ via subprocess
- Rust 1.80+ stable channel (latest stable for performance optimizations) + clap v4.0+ (CLI with derive macros), serde (serialization), thiserror (error handling), anyhow (error handling), rayon (parallel processing), criterion (benchmarks), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files)

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
- 001-python-fuzzy-query: Added Rust 1.80+ (stable) + Python 3.10+ via subprocess
- 001-python-fuzzy-query: Added Rust 1.80+ (stable) + Python 3.10+ via PyO3 0.27.2
- 001-python-binding: Added Python 3.10+ (for the API), Rust 1.80+ (existing CLI) + subprocess (Python standard library), pytest for testing


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->


