//! K-mer representation and operations
//!
//! Provides efficient k-mer encoding, decoding, and manipulation functions
//! for genomic sequence analysis.

pub mod canonical;
pub mod encoding;
pub mod operations;

pub use encoding::{encode_kmer, decode_kmer};
pub use canonical::canonical_kmer;