//! K-mer encoding and decoding functions
//!
//! Provides efficient bit-packed encoding of DNA sequences for k-mer counting.

use crate::error::KmerError;

/// DNA base encoding constants
const A: u8 = 0; // A = 00
const C: u8 = 1; // C = 01
const G: u8 = 2; // G = 10
const T: u8 = 3; // T = 11

/// Maximum k-mer size that fits in a u64 (64 / 2 = 32)
pub const MAX_KMER_SIZE_IN_U64: usize = 32;

/// Maximum k-mer size that fits in a u128 (128 / 2 = 64)
pub const MAX_KMER_SIZE_IN_U128: usize = 64;

/// Encode a DNA sequence into a packed bit representation
///
/// # Arguments
/// * `sequence` - DNA sequence string (must contain only A, C, G, T)
///
/// # Returns
/// * `Ok(u64)` - Packed representation if valid
/// * `Err(KmerError)` - Error if invalid characters found
///
/// # Examples
/// ```
/// use rustkmer::kmer::encoding::encode_kmer;
///
/// let encoded = encode_kmer("ATGC").unwrap();
/// // ATGC -> 00111001 (A=00, T=11, G=10, C=01)
/// // Step by step: A(00)->0, T(11)->3, G(10)->14, C(01)->57
/// assert_eq!(encoded, 57);
/// ```
pub fn encode_kmer(sequence: &str) -> Result<u64, KmerError> {
    encode_kmer_bytes(sequence.as_bytes())
}

/// Encode a DNA sequence from byte slice into a packed bit representation
///
/// # Arguments
/// * `sequence` - DNA sequence as bytes (must contain only A, C, G, T, case insensitive)
///
/// # Returns
/// * `Ok(u64)` - Packed representation if valid
/// * `Err(KmerError)` - Error if invalid characters found
pub fn encode_kmer_bytes(sequence: &[u8]) -> Result<u64, KmerError> {
    if sequence.len() > MAX_KMER_SIZE_IN_U64 {
        return Err(KmerError::InvalidKmerSize(sequence.len() as u32));
    }

    let mut encoded = 0u64;
    let mut pos = sequence.len();

    for (i, &byte) in sequence.iter().enumerate() {
        let base = match byte.to_ascii_uppercase() {
            b'A' => A,
            b'C' => C,
            b'G' => G,
            b'T' => T,
            _ => {
                return Err(KmerError::InvalidCharacter {
                    pos: i,
                    char: char::from(byte),
                })
            }
        };

        // Shift to make room for 2 bits, then add the base
        encoded <<= 2;
        encoded |= base as u64;
        pos -= 1;
    }

    // Shift remaining bits to the left
    encoded <<= pos * 2;

    Ok(encoded)
}

/// Decode a packed k-mer back into a DNA sequence string
///
/// # Arguments
/// * `encoded` - Packed k-mer representation
/// * `length` - Length of the k-mer (number of bases)
///
/// # Returns
/// DNA sequence string
///
/// # Examples
/// ```
/// use rustkmer::kmer::encoding::{encode_kmer, decode_kmer};
///
/// let original = "ATGC";
/// let encoded = encode_kmer(original).unwrap();
/// let decoded = decode_kmer(encoded, original.len());
/// assert_eq!(decoded, original);
/// ```
pub fn decode_kmer(encoded: u64, length: usize) -> String {
    if length > MAX_KMER_SIZE_IN_U64 {
        return String::new();
    }

    let mut result = String::with_capacity(length);

    // Start from the most significant bits
    let bits_to_shift = (64 - (length * 2)) as u32;
    let mut encoded = encoded << bits_to_shift;

    for _ in 0..length {
        let base = (encoded >> 62) & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N', // Should not happen with valid encoding
        };
        result.push(char);
        encoded <<= 2;
    }

    result
}

/// Get the reverse complement of a packed k-mer
///
/// # Arguments
/// * `encoded` - Packed k-mer representation
/// * `length` - Length of the k-mer
///
/// # Returns
/// Packed reverse complement representation
pub fn reverse_complement(encoded: u64, length: usize) -> u64 {
    if length > MAX_KMER_SIZE_IN_U64 {
        return 0;
    }

    let mut rc = 0u64;

    // Process each base from right to left (reverse order)
    // Extract from least significant bits
    let mut temp_encoded = encoded;
    for _ in 0..length {
        // Extract the rightmost 2 bits (least significant base)
        let base = temp_encoded & 0b11;

        // Complement and add to result (building from left to right)
        let complement = 3 - base; // 3-base for complement (A<->T, C<->G, G<->C, T<->A)
        rc <<= 2;
        rc |= complement;

        // Shift to get next base (right shift removes the base we just processed)
        temp_encoded >>= 2;
    }

    rc
}

/// Validate that a DNA sequence contains only valid characters
///
/// # Arguments
/// * `sequence` - DNA sequence string
///
/// # Returns
/// `true` if valid, `false` if contains invalid characters
pub fn validate_sequence(sequence: &str) -> bool {
    sequence
        .chars()
        .all(|ch| matches!(ch.to_ascii_uppercase(), 'A' | 'C' | 'G' | 'T'))
}

/// Check if a sequence contains ambiguous bases (N)
///
/// # Arguments
/// * `sequence` - DNA sequence string
///
/// # Returns
/// `true` if contains ambiguous bases, `false` if all valid
pub fn has_ambiguous_bases(sequence: &str) -> bool {
    !sequence
        .chars()
        .all(|ch| matches!(ch.to_ascii_uppercase(), 'A' | 'C' | 'G' | 'T'))
}

// ========== U128 ENCODING FUNCTIONS ==========

/// Encode a DNA sequence into a packed u128 representation
///
/// Supports k-mers up to length 64
///
/// # Arguments
/// * `sequence` - DNA sequence string (must contain only A, C, G, T)
///
/// # Returns
/// * `Ok(u128)` - Packed representation if valid
/// * `Err(KmerError)` - Error if invalid characters found
///
/// # Examples
/// ```
/// use rustkmer::kmer::encoding::encode_kmer_u128;
///
/// let encoded = encode_kmer_u128("ATGC").unwrap();
/// // ATGC -> 00111001 (A=00, T=11, G=10, C=01)
/// assert_eq!(encoded, 57);
/// ```
pub fn encode_kmer_u128(sequence: &str) -> Result<u128, KmerError> {
    encode_kmer_bytes_u128(sequence.as_bytes())
}

/// Encode a DNA sequence from byte slice into a packed u128 representation
///
/// # Arguments
/// * `sequence` - DNA sequence as bytes (must contain only A, C, G, T, case insensitive)
///
/// # Returns
/// * `Ok(u128)` - Packed representation if valid
/// * `Err(KmerError)` - Error if invalid characters found
pub fn encode_kmer_bytes_u128(sequence: &[u8]) -> Result<u128, KmerError> {
    if sequence.is_empty() || sequence.len() > MAX_KMER_SIZE_IN_U128 {
        return Err(KmerError::InvalidKmerSize(sequence.len() as u32));
    }

    let mut encoded: u128 = 0;
    let length = sequence.len();

    // Start from the most significant bits
    let bits_to_shift = (128 - (length * 2)) as u32;
    encoded <<= bits_to_shift;

    for &byte in sequence {
        let base = byte.to_ascii_uppercase();
        let value = match base {
            b'A' => A,
            b'C' => C,
            b'G' => G,
            b'T' => T,
            _ => {
                return Err(KmerError::InvalidCharacter {
                    pos: encoded.trailing_zeros() as usize / 2,
                    char: byte as char,
                });
            }
        };

        encoded = (encoded << 2) | (value as u128);
    }

    Ok(encoded)
}

/// Decode a packed u128 representation back to a DNA sequence
///
/// # Arguments
/// * `encoded` - Packed k-mer representation
/// * `length` - Length of the original k-mer
///
/// # Returns
/// The decoded DNA sequence
pub fn decode_kmer_u128(encoded: u128, length: usize) -> String {
    if length == 0 || length > MAX_KMER_SIZE_IN_U128 {
        return String::new();
    }

    let mut result = String::with_capacity(length);

    // Start from the most significant bits
    let bits_to_shift = (128 - (length * 2)) as u32;
    let mut encoded = encoded << bits_to_shift;

    for _ in 0..length {
        let base = (encoded >> 126) & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N', // Should not happen with valid encoding
        };
        result.push(char);
        encoded <<= 2;
    }

    result
}

/// Encode a DNA sequence using u64 if possible, otherwise u128
///
/// This function automatically chooses the appropriate encoding based on k-mer size.
/// For k ≤ 32, it uses u64 encoding. For k > 32, it uses u128 encoding.
///
/// # Arguments
/// * `sequence` - DNA sequence string (must contain only A, C, G, T)
///
/// # Returns
/// Tuple of (encoded_value, k_size, is_u128)
pub fn encode_kmer_auto(sequence: &str) -> (u128, u8, bool) {
    if sequence.len() <= MAX_KMER_SIZE_IN_U64 {
        let encoded_u64 = encode_kmer_u64(sequence).unwrap_or(0);
        (encoded_u64 as u128, sequence.len() as u8, false)
    } else {
        let encoded_u128 = encode_kmer_u128(sequence).unwrap_or(0);
        (encoded_u128, sequence.len() as u8, true)
    }
}

/// Legacy functions for u64 encoding (renamed for clarity)
pub fn encode_kmer_u64(sequence: &str) -> Result<u64, KmerError> {
    encode_kmer(sequence)
}

pub fn decode_kmer_u64(encoded: u64, length: usize) -> String {
    decode_kmer(encoded, length)
}

/// Get the reverse complement of a packed u128 k-mer
///
/// # Arguments
/// * `encoded` - Packed k-mer representation
/// * `length` - Length of the k-mer
///
/// # Returns
/// Packed reverse complement representation
pub fn reverse_complement_u128(encoded: u128, length: usize) -> u128 {
    if length > MAX_KMER_SIZE_IN_U128 {
        return 0;
    }

    let mut rc = 0u128;

    // Process each base from right to left (reverse order)
    // Extract from least significant bits
    let mut temp_encoded = encoded;
    for _ in 0..length {
        // Extract the rightmost 2 bits (least significant base)
        let base = temp_encoded & 0b11;

        // Complement and add to result (building from left to right)
        let complement = 3 - base; // 3-base for complement (A<->T, C<->G, G<->C, T<->A)
        rc <<= 2;
        rc |= complement;

        // Shift to get next base (right shift removes the base we just processed)
        temp_encoded >>= 2;
    }

    rc
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_decode_simple() {
        let sequence = "ATGC";
        let encoded = encode_kmer(sequence).unwrap();
        let decoded = decode_kmer(encoded, sequence.len());
        assert_eq!(decoded, sequence);
    }

    #[test]
    fn test_encode_decode_longer() {
        let sequence = "ATGCGATGCGATGCGATGCGATGCGATGCGATGC";
        // Use u128 encoding for sequences > 32 chars
        let encoded = encode_kmer_u128(sequence).unwrap();
        let decoded = decode_kmer_u128(encoded, sequence.len());
        assert_eq!(decoded, sequence);
    }

    #[test]
    fn test_reverse_complement() {
        let sequence = "ATGC";
        let encoded = encode_kmer(sequence).unwrap();
        let rc = reverse_complement(encoded, sequence.len());
        let rc_decoded = decode_kmer(rc, sequence.len());
        assert_eq!(rc_decoded, "GCAT");
    }

    #[test]
    fn test_invalid_character() {
        let result = encode_kmer("ATXG");
        assert!(result.is_err());
        if let Err(KmerError::InvalidCharacter { pos, char: c }) = result {
            assert_eq!(pos, 2);
            assert_eq!(c, 'X');
        } else {
            panic!("Expected InvalidCharacter error");
        }
    }

    #[test]
    fn test_too_long_kmer() {
        let long_seq = "A".repeat(33);
        let result = encode_kmer(&long_seq);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_sequence() {
        assert!(validate_sequence("ATGC"));
        assert!(validate_sequence("atgc"));
        assert!(!validate_sequence("ATXG"));
        assert!(validate_sequence("")); // Empty string is valid
    }

    #[test]
    fn test_has_ambiguous_bases() {
        assert!(!has_ambiguous_bases("ATGC"));
        assert!(has_ambiguous_bases("ATNG"));
        assert!(!has_ambiguous_bases("")); // Empty string has no ambiguous bases
    }

    #[test]
    fn test_canonical_property() {
        // Test that reverse complement of reverse complement equals original
        let sequence = "ATGCGAT";
        let encoded = encode_kmer(sequence).unwrap();
        let rc = reverse_complement(encoded, sequence.len());
        let rc_rc = reverse_complement(rc, sequence.len());
        assert_eq!(encoded, rc_rc);
    }

    #[test]
    fn test_bit_patterns() {
        // Test specific bit patterns
        let encoded_a = encode_kmer("A").unwrap();
        let encoded_t = encode_kmer("T").unwrap();
        let encoded_g = encode_kmer("G").unwrap();
        let encoded_c = encode_kmer("C").unwrap();

        // A = 00, T = 11, G = 10, C = 01
        assert_eq!((encoded_a & 0b11) as u8, A);
        assert_eq!((encoded_t & 0b11) as u8, T);
        assert_eq!((encoded_g & 0b11) as u8, G);
        assert_eq!((encoded_c & 0b11) as u8, C);
    }
}
