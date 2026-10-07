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
pub use hash::{KmerCounter, KmerKey};
