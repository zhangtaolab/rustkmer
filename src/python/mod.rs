//! Python bindings for RustKmer
//!
//! This module provides simplified PyO3 bindings for the RustKmer library,
//! focusing on the core functionality needed for API compatibility.

pub mod lib;
pub mod kmer_counter;

pub use lib::*;