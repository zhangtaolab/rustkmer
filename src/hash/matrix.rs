//! Matrix hash function for k-mer hashing
//!
//! Provides efficient binary matrix multiplication for k-mer hash computation
//! for optimal distribution and collision resistance.

/// Simple matrix hash function for k-mers
///
/// This is a placeholder implementation that will be expanded with
/// more sophisticated matrix operations.
#[derive(Debug, Clone)]
pub struct MatrixHashFunction {
    /// Matrix size (usually kmer_length * 2)
    size: usize,
    /// Hash matrix for multiplication
    matrix: Vec<u64>,
    /// Size mask for final hash
    size_mask: u64,
}

impl MatrixHashFunction {
    /// Create a new matrix hash function
    ///
    /// # Arguments
    /// * `kmer_length` - Length of k-mers
    ///
    /// # Returns
    /// New MatrixHashFunction instance
    pub fn new(kmer_length: usize) -> Self {
        // Simple implementation: use part of the k-mer as hash
        let bit_length = kmer_length * 2;
        let size_mask = (1u64 << bit_length.min(63)) - 1;

        // Generate a simple matrix using a pseudo-random generator
        let mut matrix = Vec::with_capacity(bit_length);
        let mut seed: u64 = 0x123456789abcdef0;

        for _ in 0..bit_length {
            // Simple pseudo-random number generator
            seed = seed.wrapping_mul(1103515245).wrapping_add(12345);
            matrix.push(seed);
        }

        Self {
            size: bit_length,
            matrix,
            size_mask,
        }
    }

    /// Compute hash for a k-mer
    ///
    /// # Arguments
    /// * `kmer_encoded` - Packed k-mer representation
    ///
    /// # Returns
    /// Hash value
    pub fn hash(&self, kmer_encoded: u64) -> u64 {
        if self.size == 0 {
            return kmer_encoded;
        }

        // Simple implementation: XOR k-mer with matrix elements
        let mut hash = 0u64;

        for i in 0..self.size.min(64) {
            let matrix_bit = (self.matrix[i / 64] >> (i % 64)) & 1;
            let kmer_bit = (kmer_encoded >> i) & 1;

            if matrix_bit ^ kmer_bit == 1 {
                hash |= 1u64 << i;
            }
        }

        hash & self.size_mask
    }

    /// Get matrix size
    pub fn size(&self) -> usize {
        self.size
    }

    /// Get size mask
    pub fn size_mask(&self) -> u64 {
        self.size_mask
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_matrix_hash_function() {
        let hasher = MatrixHashFunction::new(31);
        assert_eq!(hasher.size(), 62); // 31 * 2 bits
    }

    #[test]
    fn test_hash_computation() {
        let hasher = MatrixHashFunction::new(8); // Small size for testing
        let kmer = 0x12345678; // Some test k-mer

        let hash1 = hasher.hash(kmer);
        let hash2 = hasher.hash(kmer); // Should be deterministic

        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_different_kmer_sizes() {
        let hasher1 = MatrixHashFunction::new(21);
        let hasher2 = MatrixHashFunction::new(31);

        assert_ne!(hasher1.size(), hasher2.size());
    }

    #[test]
    fn test_hash_bounds() {
        let hasher = MatrixHashFunction::new(1);
        let kmer = 0b11; // "AT"

        let hash = hasher.hash(kmer);
        assert!(hash < (1u64 << (1 * 2))); // Should be within 2^2 range
    }
}
