//! K-mer representation and operations
//!
//! Provides efficient k-mer encoding, decoding, and manipulation functions
//! for genomic sequence analysis.
//!
//! NOTE: Python bindings (FR-005) use u128-only encoding for all k-mers (1-64).
//! Legacy u64 encoding functions are kept for backward compatibility with existing CLI tools.

pub mod canonical;
pub mod encoding;
pub mod operations;

/// u128 encoding validation module
pub mod validation;

pub use canonical::canonical_kmer;
pub use encoding::{
    decode_kmer, decode_kmer_u128, decode_kmer_u64, encode_kmer, encode_kmer_u128, encode_kmer_u64,
};

/// A k-mer that can be encoded as either u64 (k≤32) or u128 (k≤64)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Kmer {
    /// The encoded value (u64 for k≤32, u128 for k>32)
    value: u128,
    /// The k-mer size (1-64)
    k_size: u8,
}

impl Kmer {
    /// Create a new k-mer with the given value and size
    pub fn new(value: u128, k_size: u8) -> Self {
        Self { value, k_size }
    }

    /// Get the encoded value
    pub fn value(&self) -> u128 {
        self.value
    }

    /// Get the k-mer size
    pub fn k_size(&self) -> u8 {
        self.k_size
    }

    /// Check if this k-mer can be represented in u64 (k≤32)
    pub fn fits_in_u64(&self) -> bool {
        self.k_size <= 32
    }

    /// Get u64 value if possible (returns None for k>32)
    pub fn as_u64(&self) -> Option<u64> {
        if self.fits_in_u64() {
            Some(self.value as u64)
        } else {
            None
        }
    }
}
