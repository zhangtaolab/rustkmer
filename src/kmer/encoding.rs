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

// ========== ROLLING 2-BIT ENCODER (PAR-03) ==========

/// Bit-parallel reverse complement of a right-aligned 2-bit-packed `u64` k-mer.
///
/// Valid for `length` in `1..=32`. The input is the right-aligned value the
/// encoders in this module produce (bits `0..2*length` significant, upper bits
/// ignored); the result is right-aligned in the same way and equals
/// [`reverse_complement_u128`] narrowed to `u64` for every `k` in `1..=32`.
///
/// The implementation complements every 2-bit pair (which turns base `b` into
/// `3 - b`), swaps adjacent 2-bit groups, swaps 4-bit groups, then reverses the
/// byte order. The final right shift discards the complement of the unused high
/// bits and right-aligns the k-mer.
///
/// This helper is the parity-tested primitive: the rolling hot path updates its
/// reverse-complement state incrementally instead of calling it per window.
///
/// # Arguments
/// * `encoded` - Right-aligned 2-bit-packed k-mer
/// * `length` - K-mer length (`1..=32`)
///
/// # Returns
/// The right-aligned 2-bit-packed reverse complement, or `0` when `length` is
/// outside `1..=32` (the shift below would otherwise be undefined).
///
/// # Examples
/// ```
/// use rustkmer::kmer::encoding::{encode_kmer, reverse_complement_u64};
///
/// let forward = encode_kmer("ATGC").unwrap();
/// assert_eq!(
///     reverse_complement_u64(forward, 4),
///     encode_kmer("GCAT").unwrap()
/// );
/// ```
#[inline]
pub fn reverse_complement_u64(encoded: u64, length: usize) -> u64 {
    if length == 0 || length > MAX_KMER_SIZE_IN_U64 {
        return 0;
    }

    let mut v = !encoded;
    v = ((v & 0x3333_3333_3333_3333) << 2) | ((v >> 2) & 0x3333_3333_3333_3333);
    v = ((v & 0x0F0F_0F0F_0F0F_0F0F) << 4) | ((v >> 4) & 0x0F0F_0F0F_0F0F_0F0F);
    v = v.swap_bytes();
    v >> (64 - 2 * length)
}

/// Rolling 2-bit encoder for k-mers of length 1 through 32 (PAR-03).
///
/// One pass over the sequence maintains a forward value and an incrementally
/// updated reverse-complement value; each emitted window costs O(1) instead of
/// the per-window O(k) encoder's re-scan.
///
/// # Value contract
///
/// For every emitted window the value equals the low `2*k` bits of
/// [`encode_kmer_bytes_u128`] over that window in forward mode, or the minimum
/// of that value and its [`reverse_complement_u128`] in canonical mode. Lowercase
/// bases are accepted (ASCII uppercase); k values of zero and above 32 are
/// rejected — callers must keep using the per-window u128 path there.
///
/// # Reset contract (T-06-11)
///
/// Any byte outside `A`, `C`, `G`, `T` (case-insensitive) resets the forward
/// value, the reverse-complement value, and the valid-run length. Each call to
/// [`Self::for_each`] / [`Self::try_for_each`] starts from a fresh state, so
/// invoking it once per record means no window can span an `N` or a record
/// boundary.
///
/// # Mask contract (T-06-07)
///
/// The forward value is masked to exactly `2*k` bits. `k = 32` uses
/// `u64::MAX` rather than computing `1 << 64`, which would overflow.
///
/// # Examples
/// ```
/// use rustkmer::kmer::encoding::{
///     encode_kmer_u128, reverse_complement_u128, RollingEncoder,
/// };
///
/// let encoder = RollingEncoder::new(4, true).unwrap();
/// let mut emitted = Vec::new();
/// let skipped = encoder.for_each(b"ATGC", |value| emitted.push(value));
///
/// assert_eq!(skipped, 0);
/// assert_eq!(emitted.len(), 1);
/// let forward = encode_kmer_u128("ATGC").unwrap();
/// let reverse = reverse_complement_u128(forward, 4);
/// assert_eq!(emitted[0], forward.min(reverse) as u64);
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RollingEncoder {
    /// K-mer length, validated to `1..=32` at construction.
    k: usize,
    /// Left shift that places the newest base's complement in the reverse value.
    shift: u32,
    /// Low `2*k`-bit mask (all ones for k = 32).
    mask: u64,
    /// Whether emitted windows are canonicalized.
    canonical: bool,
}

impl RollingEncoder {
    /// Build a rolling encoder for `k` in `1..=32`.
    ///
    /// # Arguments
    /// * `k` - K-mer length (`1..=32`)
    /// * `canonical` - Emit the canonical (minimum of forward and reverse
    ///   complement) value instead of the forward value
    ///
    /// # Returns
    /// A reusable encoder. Its [`Self::for_each`] / [`Self::try_for_each`]
    /// methods are stateless across calls, so one encoder can serve every
    /// record of a file.
    ///
    /// # Errors
    /// Returns [`KmerError::InvalidKmerSize`] when `k` is zero or greater than
    /// [`MAX_KMER_SIZE_IN_U64`]; those k values must use the per-window u128
    /// path.
    ///
    /// # Examples
    /// ```
    /// use rustkmer::kmer::encoding::RollingEncoder;
    ///
    /// assert!(RollingEncoder::new(0, false).is_err());
    /// assert!(RollingEncoder::new(33, false).is_err());
    /// assert!(RollingEncoder::new(32, true).is_ok());
    /// ```
    pub fn new(k: usize, canonical: bool) -> Result<Self, KmerError> {
        if k == 0 || k > MAX_KMER_SIZE_IN_U64 {
            return Err(KmerError::InvalidKmerSize(k as u32));
        }

        // Avoid the `1u64 << 64` overflow at the k = 32 boundary (T-06-07).
        let mask = if k == MAX_KMER_SIZE_IN_U64 {
            u64::MAX
        } else {
            (1u64 << (2 * k)) - 1
        };

        Ok(Self {
            k,
            shift: 2 * (k as u32 - 1),
            mask,
            canonical,
        })
    }

    /// K-mer length this encoder emits.
    pub fn k(&self) -> usize {
        self.k
    }

    /// Whether emitted windows are canonicalized.
    pub fn canonical_mode(&self) -> bool {
        self.canonical
    }

    /// The low `2*k`-bit mask applied to the forward value.
    ///
    /// Exposed for the differential suite's k = 32 all-ones assertion.
    pub fn mask(&self) -> u64 {
        self.mask
    }

    /// Emit every valid window of `seq`, ignoring emit errors (none possible).
    ///
    /// See [`Self::try_for_each`] for the fallible form and the shared
    /// semantics.
    ///
    /// # Returns
    /// The number of windows skipped because they contained a non-ACGT byte.
    ///
    /// # Examples
    /// ```
    /// use rustkmer::kmer::encoding::RollingEncoder;
    ///
    /// let encoder = RollingEncoder::new(3, false).unwrap();
    /// let mut values = Vec::new();
    /// let skipped = encoder.for_each(b"ACGTNACG", |value| values.push(value));
    ///
    /// // Length 8, k = 3 -> 6 windows: ACG, CGT, GTN, TNA, NAC, ACG.
    /// // The three windows containing the N are skipped.
    /// assert_eq!(values.len(), 3);
    /// assert_eq!(skipped, 3);
    /// ```
    pub fn for_each<F>(&self, seq: &[u8], mut emit: F) -> u64
    where
        F: FnMut(u64),
    {
        match self.emit_windows(seq, |value| -> Result<(), core::convert::Infallible> {
            emit(value);
            Ok(())
        }) {
            Ok(skipped) => skipped,
            Err(never) => match never {},
        }
    }

    /// Emit every valid window of `seq` into a fallible sink.
    ///
    /// A window is emitted only after `k` consecutive valid bases have been
    /// seen. Any other byte resets the forward value, the reverse value, and the
    /// valid-run length first.
    ///
    /// # Arguments
    /// * `seq` - Raw sequence bytes; uppercase and lowercase ACGT are accepted
    /// * `emit` - Called once per valid window, in left-to-right order
    ///
    /// # Returns
    /// `Ok(skipped)` where `skipped` is the number of length-`k` windows that
    /// contained at least one non-ACGT byte: `(len - k + 1) - emitted`, or `0`
    /// when the sequence is shorter than `k`.
    ///
    /// # Errors
    /// Propagates the first error returned by `emit` and stops the pass.
    ///
    /// # Examples
    /// ```
    /// use rustkmer::kmer::encoding::RollingEncoder;
    ///
    /// let encoder = RollingEncoder::new(3, false).unwrap();
    /// let mut values = Vec::new();
    /// let skipped: Result<u64, ()> = encoder.try_for_each(b"ACGTNACG", |value| {
    ///     values.push(value);
    ///     Ok(())
    /// });
    ///
    /// // Length 8, k = 3 -> 6 windows; 3 contain the N -> 3 emitted.
    /// assert_eq!(values.len(), 3);
    /// assert_eq!(skipped.unwrap(), 3);
    /// ```
    #[inline]
    pub fn try_for_each<E, F>(&self, seq: &[u8], emit: F) -> Result<u64, E>
    where
        F: FnMut(u64) -> Result<(), E>,
    {
        self.emit_windows(seq, emit)
    }

    /// Shared rolling pass: returns the skipped-window count or the sink's error.
    #[inline]
    fn emit_windows<E, F>(&self, seq: &[u8], mut emit: F) -> Result<u64, E>
    where
        F: FnMut(u64) -> Result<(), E>,
    {
        let k = self.k;
        let mask = self.mask;
        let shift = self.shift;

        let mut forward: u64 = 0;
        let mut reverse: u64 = 0;
        let mut valid: usize = 0;
        let mut emitted: u64 = 0;

        for &byte in seq {
            let base = match byte.to_ascii_uppercase() {
                b'A' => 0u64,
                b'C' => 1u64,
                b'G' => 2u64,
                b'T' => 3u64,
                _ => {
                    // T-06-11: never let a window span an invalid byte.
                    forward = 0;
                    reverse = 0;
                    valid = 0;
                    continue;
                }
            };

            forward = ((forward << 2) | base) & mask;
            reverse = (reverse >> 2) | ((3 - base) << shift);

            // Saturate at k: once a full valid run exists every further valid
            // base completes another window, and `valid` can never overflow.
            if valid < k {
                valid += 1;
            }
            if valid == k {
                let value = if self.canonical {
                    forward.min(reverse)
                } else {
                    forward
                };
                emit(value)?;
                emitted += 1;
            }
        }

        let total_windows = if seq.len() >= k {
            (seq.len() - k + 1) as u64
        } else {
            0
        };
        debug_assert!(emitted <= total_windows);
        Ok(total_windows - emitted)
    }
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
