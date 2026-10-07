#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
//! RustKmer Library
//!
//! High-performance k-mer counting library for genomic data analysis.
//!
//! This library provides core functionality for counting k-mers in DNA sequences,
//! with support for memory-efficient storage and multiple output formats.
//!
//! # Examples
//!
//! ```rust,ignore
//! use rustkmer::KmerCounter;
//!
//! // Create a k-mer counter for 21-mers
//! let counter = KmerCounter::new(21, true, 1000000, 4).unwrap();
//! counter.count_file("genome.fa")?;
//! let counts = counter.get_all_counts();
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

pub mod cli;
pub mod config;
pub mod core;
pub mod database;
pub mod error;
pub mod fuzzy;
pub mod hash;
pub mod io;
pub mod kmer;
pub mod memory;
pub mod output;

// Re-export key types for convenience
pub use error::{KmerError, ProcessingError, ProcessingResult};
// Phase 3 plan 03-06: `KmerKey` is gone. The dense/wide width lives on the
// counter's private `CounterTable` (a `DashMap<u64,u32>` / `DashMap<u128,u32>`)
// rather than in a public key enum whose `u128` variant forced 16-byte
// alignment and a 32-byte key, which made counting memory for k <= 32 LARGER
// than the pre-Phase-3 `u128` counter. `KmerCounter` keeps its whole `u128`
// -typed surface (`new`/`increment`/`get_count`/`get_all_counts`/`merge`), so
// every call site below is unaffected.
pub use hash::KmerCounter;
