//! Canonical k-mer operations
//!
//! Implements canonical k-mer representation (forward/reverse complement lexicographically smaller).

use crate::error::ProcessingResult;
use crate::kmer::encoding::decode_kmer;
use crate::kmer::operations::reverse_complement_bits;

/// Get the canonical representation of a k-mer
///
/// The canonical k-mer is the lexicographically smaller of the forward k-mer
/// and its reverse complement.
///
/// # Arguments
/// * `kmer_encoded` - Packed k-mer representation
/// * `k` - K-mer length
///
/// # Returns
/// Canonical k-mer encoding
pub fn canonical_kmer(kmer_encoded: u64, k: usize) -> ProcessingResult<u64> {
    // Get reverse complement
    let rev_comp = reverse_complement_bits(kmer_encoded, k)?;

    // Return the lexicographically smaller
    Ok(if kmer_encoded <= rev_comp {
        kmer_encoded
    } else {
        rev_comp
    })
}

/// Check if a k-mer is already in canonical form
///
/// # Arguments
/// * `kmer_encoded` - Packed k-mer representation
/// * `k` - K-mer length
///
/// # Returns
/// True if the k-mer is canonical, false otherwise
pub fn is_canonical(kmer_encoded: u64, k: usize) -> ProcessingResult<bool> {
    let rev_comp = reverse_complement_bits(kmer_encoded, k)?;
    Ok(kmer_encoded <= rev_comp)
}

/// Get both forward and reverse complement sequences
///
/// # Arguments
/// * `kmer_encoded` - Packed k-mer representation
/// * `k` - K-mer length
///
/// # Returns
/// Tuple of (forward_sequence, reverse_complement_sequence)
pub fn get_both_orientations(kmer_encoded: u64, k: usize) -> ProcessingResult<(String, String)> {
    let forward = decode_kmer(kmer_encoded, k);
    let rev_comp_bits = reverse_complement_bits(kmer_encoded, k)?;
    let rev_comp = decode_kmer(rev_comp_bits, k);

    Ok((forward, rev_comp))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kmer::encoding::encode_kmer;

    #[test]
    fn test_canonical_kmer() {
        // Test with "ATGC" (k=4)
        // ATGC = 00 01 10 11 (in binary) = 0b001011 = 11
        let atgc_encoded = encode_kmer("ATGC").unwrap();
        let canonical = canonical_kmer(atgc_encoded, 4).unwrap();

        // GCAT (reverse complement) should be smaller
        // GCAT = 10 01 11 00 (in binary) = 0b10011100 = 156
        assert_eq!(canonical, atgc_encoded);
    }

    #[test]
    fn test_palindrome_kmer() {
        // Test with palindrome "ATAT"
        // ATAT reverse complement is ATAT, so it should be equal
        let atat_encoded = encode_kmer("ATAT").unwrap();
        let canonical = canonical_kmer(atat_encoded, 4).unwrap();
        assert_eq!(canonical, atat_encoded);
    }

    #[test]
    fn test_is_canonical() {
        let atgc_encoded = encode_kmer("ATGC").unwrap();
        assert!(is_canonical(atgc_encoded, 4).unwrap());

        // Test with non-canonical
        let gcat_encoded = encode_kmer("GCAT").unwrap();
        assert!(!is_canonical(gcat_encoded, 4).unwrap());
    }

    #[test]
    fn test_get_both_orientations() {
        let atgc_encoded = encode_kmer("ATGC").unwrap();
        let (forward, rev_comp) = get_both_orientations(atgc_encoded, 4).unwrap();

        assert_eq!(forward, "ATGC");
        assert_eq!(rev_comp, "GCAT");
    }
}