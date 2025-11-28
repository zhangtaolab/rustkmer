# RustKmer Project Overview

**Project Purpose**: High-performance k-mer counting tool in Rust, designed as a fast alternative to jellyfish for genomic data analysis.

**Tech Stack**:
- **Language**: Rust 1.80+ stable channel
- **CLI Framework**: clap v4.5 with derive macros
- **Error Handling**: thiserror 2.0, anyhow 1.0
- **Parallel Processing**: rayon 1.10
- **Bioinformatics**: bio 2.0 for FASTA/FASTQ parsing
- **Memory Management**: memmap2 0.9 for memory-mapped files
- **Serialization**: serde 1.0 with derive, bincode 1.3
- **Binary I/O**: byteorder 1.5
- **Performance**: smallvec 1.13, hashbrown 0.14, parking_lot 0.12
- **Utilities**: num_cpus 1.16, indicatif 0.17, niffler 2.5, flate2 1.0, log 0.4
- **Testing**: criterion 0.5 for benchmarks, tempfile 3.12, proptest 1.5

**Code Style & Conventions**:
- Follow Rust standard conventions and idiomatic patterns
- Comprehensive error handling with Result/Option types
- Module-based architecture with clear separation of concerns
- Performance-optimized with release profile (LTO, codegen-units = 1, panic = abort)
- Comprehensive documentation with rustdoc comments
- Memory-efficient design for large genomic datasets

**Project Structure**:
```
src/
├── main.rs              # Application entry point
├── lib.rs               # Library root with exports
├── cli/                 # Command-line interface
│   ├── args.rs          # CLI argument definitions
│   └── commands/        # Command implementations
├── database/            # Database functionality (query feature)
│   ├── format.rs        # Database format definitions
│   └── query.rs         # Query engine implementation
├── kmer/                # K-mer processing
├── io/                  # Input/output operations
├── hash/                # Hash table implementations
├── parallel/            # Parallel processing
└── error/               # Error definitions
tests/                   # Unit and integration tests
```

**Key Development Commands**:
- Build: `cargo build --release`
- Test: `cargo test`
- Lint: `cargo clippy`
- Format: `cargo fmt`
- Run: `cargo run -- <args>`
- Benchmark: `cargo bench`

**Entry Points**:
- Main CLI: `cargo run -- --help`
- Specific commands: `cargo run -- count --help`, `cargo run -- query --help`

**Available Commands**:
- `count`: Count k-mers from sequences (implemented)
- `query`: Query k-mer counts from databases (implemented)
- `stats`: Database statistics (placeholder)
- `dump`: Dump database contents (placeholder)

**Current Features**:
- Multi-threaded k-mer counting
- Canonical k-mer handling
- Multiple input/output formats
- Custom binary database format (.rkdb)
- Jellyfish-compatible query interface
- Memory-mapped file operations
- Efficient binary search queries

**Special Guidelines**:
- Performance optimization is critical for large genomic datasets
- Memory efficiency must support datasets >100M k-mers
- Cross-platform compatibility (Linux, macOS, Windows)
- Jellyfish compatibility for easy migration
- Thread-safe operations for parallel processing