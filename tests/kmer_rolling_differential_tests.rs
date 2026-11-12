//! PAR-03 differential proofs: the rolling 2-bit encoder must emit exactly the
//! values the per-window reference encoder emits, in the same order, with the
//! same skipped-window count.
//!
//! A rolling encoder that fails to mask to `2*k` bits or fails to reset its
//! valid run at a non-ACGT byte would silently emit stale-window / chimeric
//! k-mers (the Phase 5 N-read differential found 33 such keys). These tests
//! compare against `encode_kmer_bytes_u128` + `canonical_kmer_u128`, the
//! unchanged production reference, rather than against another rolling
//! implementation — a shared bug cannot hide in both.
//!
//! Task 1 owns the k 1-through-32 differential and the bit-parallel
//! reverse-complement parity. Task 3 extends this file to the full k
//! 1-through-64 edge matrix and the ignored release-build timing gate.

use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{
    encode_kmer_bytes_u128, reverse_complement_u128, reverse_complement_u64, RollingEncoder,
    MAX_KMER_SIZE_IN_U64,
};

/// Deterministic ACGT fixture: three different repeat patterns keep the window
/// content varied while staying byte-for-byte reproducible.
fn acgt_fixture() -> Vec<u8> {
    let mut sequence = Vec::new();
    for _ in 0..16 {
        sequence.extend_from_slice(b"ACGT");
    }
    for _ in 0..9 {
        sequence.extend_from_slice(b"GATTACA");
    }
    for _ in 0..4 {
        sequence.extend_from_slice(b"AAAACCCCGGGGTTTT");
    }
    assert!(sequence.len() > 128, "fixture must cover every k <= 64");
    sequence
}

/// The unchanged production per-window path: one fresh encode + canonicalize
/// per window. Invalid windows are skipped and counted.
fn reference_windows(seq: &[u8], k: usize, canonical: bool) -> (Vec<u64>, u64) {
    if seq.len() < k {
        return (Vec::new(), 0);
    }

    let mut emitted = Vec::with_capacity(seq.len() - k + 1);
    let mut skipped = 0u64;
    for window in seq.windows(k) {
        match encode_kmer_bytes_u128(window) {
            Ok(encoded) => {
                let value = if canonical {
                    canonical_kmer_u128(encoded, k).expect("valid window canonicalizes")
                } else {
                    encoded
                };
                debug_assert!(
                    value <= u64::MAX as u128,
                    "k <= 32 encoding must fit the low 64 bits"
                );
                emitted.push(value as u64);
            }
            Err(_) => skipped += 1,
        }
    }
    (emitted, skipped)
}

/// Collect the rolling encoder's emission sequence and skipped-window count.
fn rolling_windows(encoder: &RollingEncoder, seq: &[u8]) -> (Vec<u64>, u64) {
    let mut emitted = Vec::new();
    let skipped = encoder.for_each(seq, |value| emitted.push(value));
    (emitted, skipped)
}

#[test]
fn rolling_matches_reference_for_k_1_through_32() {
    let fixture = acgt_fixture();

    for k in 1..=32 {
        for canonical in [false, true] {
            let encoder = RollingEncoder::new(k, canonical).expect("k in 1..=32");
            let got = rolling_windows(&encoder, &fixture);
            let want = reference_windows(&fixture, k, canonical);

            assert_eq!(
                got.0, want.0,
                "rolling emission diverged from the per-window reference \
                 (k={}, canonical={})",
                k, canonical
            );
            assert_eq!(
                got.1, want.1,
                "rolling skipped count diverged (k={}, canonical={})",
                k, canonical
            );
            assert_eq!(got.1, 0, "a pure-ACGT fixture must skip nothing (k={})", k);
        }
    }
}

/// Task 1 requires the boundary k values to be exercised explicitly, not only
/// as members of the `1..=32` loop above.
#[test]
fn explicit_edge_k_values_match_reference() {
    let fixture = acgt_fixture();
    let lowercase: Vec<u8> = fixture.iter().map(u8::to_ascii_lowercase).collect();

    let mut with_ns = fixture.clone();
    with_ns[0] = b'N';
    with_ns[40] = b'n';
    with_ns[41] = b'N';
    let last = with_ns.len() - 1;
    with_ns[last] = b'N';

    for k in [1usize, 21, 31, 32] {
        for canonical in [false, true] {
            for seq in [&fixture, &lowercase, &with_ns] {
                let encoder = RollingEncoder::new(k, canonical).expect("k in 1..=32");
                let got = rolling_windows(&encoder, seq);
                let want = reference_windows(seq, k, canonical);

                assert_eq!(
                    got, want,
                    "explicit k={} differential failed (canonical={})",
                    k, canonical
                );
            }
        }
    }
}

#[test]
fn rolling_skipped_count_matches_reference_on_invalid_bytes() {
    let base = acgt_fixture();

    for k in 1..=32 {
        let positions = [
            0usize,
            1,
            17,
            base.len() / 2,
            base.len() - 2,
            base.len() - 1,
        ];
        for &position in &positions {
            for run_length in [1usize, 2, 3] {
                let mut seq = base.clone();
                for offset in 0..run_length {
                    if let Some(byte) = seq.get_mut(position + offset) {
                        *byte = b'N';
                    }
                }

                let encoder = RollingEncoder::new(k, false).expect("k in 1..=32");
                let got = rolling_windows(&encoder, &seq);
                let want = reference_windows(&seq, k, false);

                assert_eq!(
                    got, want,
                    "invalid-byte differential failed (k={}, position={}, run={})",
                    k, position, run_length
                );

                let total_windows = seq.len() - k + 1;
                assert_eq!(
                    got.0.len() + got.1 as usize,
                    total_windows,
                    "every window must be either emitted or skipped (k={})",
                    k
                );
            }
        }
    }
}

#[test]
fn bit_parallel_reverse_complement_matches_scalar_u128() {
    let fixture = acgt_fixture();

    for k in 1..=32 {
        for window in fixture.windows(k) {
            let encoded = encode_kmer_bytes_u128(window).expect("ACGT window encodes");
            let scalar = reverse_complement_u128(encoded, k);
            let parallel = reverse_complement_u64(encoded as u64, k);
            assert_eq!(
                parallel as u128, scalar,
                "bit-parallel reverse complement diverged (k={}, window={:?})",
                k, window
            );
        }

        // Extremes: all-zero and all-ones 2*k-bit values.
        let all_ones = if k == 32 {
            u64::MAX
        } else {
            (1u64 << (2 * k)) - 1
        };
        assert_eq!(
            reverse_complement_u64(0, k) as u128,
            reverse_complement_u128(0, k),
            "all-A window must complement to all-T (k={})",
            k
        );
        assert_eq!(
            reverse_complement_u64(all_ones, k) as u128,
            reverse_complement_u128(all_ones as u128, k),
            "all-T window must complement to all-A (k={})",
            k
        );
    }

    // Out-of-range lengths must not shift by 64+.
    assert_eq!(reverse_complement_u64(0, 0), 0);
    assert_eq!(reverse_complement_u64(0, MAX_KMER_SIZE_IN_U64 + 1), 0);
}

#[test]
fn rolling_encoder_rejects_out_of_range_k() {
    for k in [0usize, 33, 64, usize::MAX] {
        assert!(
            RollingEncoder::new(k, false).is_err(),
            "k={} must not be routed to the rolling path",
            k
        );
    }

    assert!(RollingEncoder::new(1, false).is_ok());
    assert!(RollingEncoder::new(32, true).is_ok());
    assert_eq!(
        RollingEncoder::new(32, false).expect("k=32").mask(),
        u64::MAX,
        "k=32 must use the all-ones mask, never a 64-bit shift"
    );
}
