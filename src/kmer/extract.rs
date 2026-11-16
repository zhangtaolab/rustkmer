//! The ONE skip-N k-mer window extractor shared by every counting surface.
//!
//! **ENGINE-03 / D2.** Before Phase 7 the CLI and the PyO3 bindings each had
//! their own window loop, so an `N`/record-boundary/canonicalization fix had to
//! land twice (and the Python surface additionally pre-filtered `N`s). This
//! module is the single implementation: [`for_each_window`] emits every valid
//! window of one sequence with the CLI's skip-N semantics — a window
//! containing any non-ACGT byte is skipped and counted, never emitted, and
//! every call starts from a fresh state so no window can span a record
//! boundary.
//!
//! The implementation deliberately reuses the already differential-tested
//! primitives instead of re-deriving them:
//!
//! - `k <= 32`: [`RollingEncoder`] (one O(1) pass per record, masked to
//!   `2*k` bits, reset at every non-ACGT byte);
//! - `k 33..=64`: the per-window [`encode_kmer_bytes_u128`] reference path
//!   plus [`canonical_kmer_u128`] when canonical mode is on.
//!
//! The fallible sink lets a counting caller abort on a per-key overflow
//! exactly as the pre-engine hot loop did.

use crate::kmer::canonical::canonical_kmer_u128;
use crate::kmer::encoding::{encode_kmer_bytes_u128, RollingEncoder, MAX_KMER_SIZE_IN_U64};

/// Summary of one [`for_each_window`] pass.
///
/// `emitted + skipped` equals the number of length-`k` windows in the
/// sequence (`len - k + 1`) whenever `len >= k`; both are zero otherwise.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct WindowSummary {
    /// Number of windows handed to the sink.
    pub emitted: u64,
    /// Number of length-`k` windows that contained a non-ACGT byte.
    pub skipped: u64,
}

/// Failure modes of [`for_each_window`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WindowError<E> {
    /// The requested k-mer length is outside `1..=64`.
    InvalidK(usize),
    /// The sink rejected a window; the payload is the sink's error.
    Emit(E),
}

/// Emit every valid k-mer window of `seq` with the shared skip-N semantics.
///
/// This is the only window-extraction loop in the counting codebase: the
/// engine producer, the legacy per-chunk CLI hot loop, and (from Phase 9) the
/// PyO3 bindings all call it. Any window containing a byte outside `A`, `C`,
/// `G`, `T` (case-insensitive) is skipped and counted in
/// [`WindowSummary::skipped`]; every call starts fresh, so no window spans a
/// record boundary.
///
/// # Arguments
/// * `seq` - Raw sequence bytes (uppercase and lowercase ACGT accepted)
/// * `k` - K-mer length, validated to `1..=64`
/// * `canonical` - Emit `min(forward, reverse_complement)` values instead of
///   the forward encoding
/// * `emit` - Called once per valid window, in left-to-right order
///
/// # Returns
/// [`WindowSummary`] with the emitted and skipped window counts.
///
/// # Errors
/// * [`WindowError::InvalidK`] when `k` is zero or greater than
///   [`MAX_KMER_SIZE_IN_U128`](crate::kmer::encoding::MAX_KMER_SIZE_IN_U128)
///   (64).
/// * [`WindowError::Emit`] with the first error returned by `emit`; emission
///   stops immediately.
///
/// # Examples
/// ```
/// use rustkmer::kmer::extract::for_each_window;
///
/// let mut windows = Vec::new();
/// let summary = for_each_window(b"ACGTNACG", 3, false, |value| {
///     windows.push(value);
///     Ok::<(), ()>(())
/// })
/// .expect("k = 3 is valid");
///
/// // Length 8, k = 3 -> 6 windows; the three containing the N are skipped.
/// assert_eq!(windows.len(), 3);
/// assert_eq!(summary.emitted, 3);
/// assert_eq!(summary.skipped, 3);
/// ```
#[inline]
pub fn for_each_window<E, F>(
    seq: &[u8],
    k: usize,
    canonical: bool,
    mut emit: F,
) -> Result<WindowSummary, WindowError<E>>
where
    F: FnMut(u128) -> Result<(), E>,
{
    if !(1..=64).contains(&k) {
        return Err(WindowError::InvalidK(k));
    }

    if k <= MAX_KMER_SIZE_IN_U64 {
        // PAR-03 rolling path: one O(1) pass, already masked and reset at
        // every invalid byte. The `InvalidK` branch is unreachable for the
        // 1..=32 range routed here; map it rather than unwrap.
        let encoder = RollingEncoder::new(k, canonical).map_err(|_| WindowError::InvalidK(k))?;
        let mut emitted = 0u64;
        let skipped = encoder.try_for_each(seq, |value| {
            emit(value as u128).map_err(WindowError::Emit)?;
            emitted += 1;
            Ok(())
        })?;
        return Ok(WindowSummary { emitted, skipped });
    }

    // k 33..=64: the per-window u128 reference encoder.
    if seq.len() < k {
        return Ok(WindowSummary::default());
    }

    let mut emitted = 0u64;
    let mut skipped = 0u64;
    for window in seq.windows(k) {
        match encode_kmer_bytes_u128(window) {
            Ok(encoded) => {
                let value = if canonical {
                    match canonical_kmer_u128(encoded, k) {
                        Ok(canonical_value) => canonical_value,
                        // Unreachable for a validated k in 1..=64; count the
                        // window as skipped so the summary invariant holds
                        // instead of panicking.
                        Err(_) => {
                            skipped += 1;
                            continue;
                        }
                    }
                } else {
                    encoded
                };
                emit(value).map_err(WindowError::Emit)?;
                emitted += 1;
            }
            Err(_) => skipped += 1,
        }
    }
    Ok(WindowSummary { emitted, skipped })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_k_is_rejected_before_touching_the_sequence() {
        for k in [0usize, 65] {
            let outcome = for_each_window(b"ACGT", k, false, |_: u128| Ok::<(), ()>(()));
            assert_eq!(outcome, Err(WindowError::InvalidK(k)));
        }
    }

    #[test]
    fn wide_path_skips_n_windows_and_emits_the_rest() {
        // k = 33 forces the per-window u128 branch.
        let mut seq = vec![b'A'; 80];
        seq[40] = b'N';
        let mut emitted = 0u64;
        let summary = for_each_window(&seq, 33, true, |_| {
            emitted += 1;
            Ok::<(), ()>(())
        })
        .expect("k = 33 is valid");
        assert_eq!(summary.emitted, emitted);
        // Windows start at 0..=47 and cover [s, s + 32]; the N at index 40
        // is inside the windows starting at 8..=40 (33 of them).
        assert_eq!(summary.skipped, 33);
        assert_eq!(summary.emitted, 15);
        assert_eq!(summary.emitted + summary.skipped, seq.len() as u64 - 33 + 1);
    }

    #[test]
    fn wide_path_emits_nothing_for_short_sequence() {
        let summary =
            for_each_window(b"ACGT", 33, false, |_: u128| Ok::<(), ()>(())).expect("k = 33");
        assert_eq!(summary, WindowSummary::default());
    }
}
