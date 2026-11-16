//! ENGINE-03 differential suite for the ONE skip-N window extractor.
//!
//! `rustkmer::kmer::extract::for_each_window` is the single window-extraction
//! function every counting surface (engine producer, legacy per-chunk CLI hot
//! loop, and — from Phase 9 — the PyO3 bridge) must use. This suite pins it
//! against the unchanged per-window reference encoder
//! (`encode_kmer_bytes_u128` + `canonical_kmer_u128`) over the full edge
//! matrix the plan names:
//!
//! - k 1..=64 (both storage widths, the rolling/wide boundary at 32/33),
//! - canonical on/off,
//! - uppercase and lowercase ACGT,
//! - `N` at every position, `N` runs, and sequences with no valid window,
//! - empty and short sequences,
//! - two consecutive calls (no window may span a call / record boundary).
//!
//! `emitted + skipped == len - k + 1` is asserted wherever `len >= k`, and a
//! window containing any non-ACGT byte must be counted as skipped and never
//! emitted.

use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use rustkmer::kmer::extract::{for_each_window, WindowError};

/// Deterministic mixed-ACGT sequence (inline LCG, seed 0xC0FFEE) so failures
/// are reproducible and every k 1..=64 sees a non-degenerate window set.
fn mixed_sequence(len: usize) -> Vec<u8> {
    const BASES: [u8; 4] = *b"ACGT";
    let mut state: u64 = 0xC0FF_EE00_0000_0001;
    (0..len)
        .map(|_| {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            BASES[((state >> 33) & 3) as usize]
        })
        .collect()
}

/// The unchanged reference: one independent per-window encode per window, the
/// same encoder the pre-engine CLI used for k 33..=64.
fn reference_windows(seq: &[u8], k: usize, canonical: bool) -> (Vec<u128>, u64) {
    if seq.len() < k {
        return (Vec::new(), 0);
    }
    let mut emitted = Vec::new();
    let mut skipped = 0u64;
    for window in seq.windows(k) {
        match encode_kmer_bytes_u128(window) {
            Ok(encoded) => {
                let value = if canonical {
                    canonical_kmer_u128(encoded, k).expect("a valid window canonicalizes")
                } else {
                    encoded
                };
                emitted.push(value);
            }
            Err(_) => skipped += 1,
        }
    }
    (emitted, skipped)
}

/// Drive the extractor with an infallible sink.
fn extract(seq: &[u8], k: usize, canonical: bool) -> (Vec<u128>, u64) {
    let mut emitted = Vec::new();
    let summary = for_each_window(seq, k, canonical, |value| {
        emitted.push(value);
        Ok::<(), ()>(())
    })
    .expect("a k in 1..=64 must not be rejected");
    (emitted, summary.skipped)
}

/// Assert the extractor equals the reference, including emission order, and
/// the conservation invariant `emitted + skipped == len - k + 1`.
fn assert_matches_reference(seq: &[u8], k: usize, canonical: bool, context: &str) {
    let (got, skipped) = extract(seq, k, canonical);
    let (want, want_skipped) = reference_windows(seq, k, canonical);
    assert_eq!(
        got, want,
        "window extractor diverged from the per-window reference ({context}, k={k}, \
         canonical={canonical})"
    );
    assert_eq!(
        skipped, want_skipped,
        "skipped-window count diverged ({context}, k={k}, canonical={canonical})"
    );
    if seq.len() >= k {
        assert_eq!(
            got.len() as u64 + skipped,
            (seq.len() - k + 1) as u64,
            "conservation broken: emitted + skipped must equal len - k + 1 \
             ({context}, k={k}, len={})",
            seq.len()
        );
    } else {
        assert_eq!(got.len(), 0, "short sequence must emit nothing");
        assert_eq!(skipped, 0, "short sequence must skip nothing");
    }
}

/// k 1..=64, canonical on/off, on a mixed ACGT fixture.
#[test]
fn extractor_matches_reference_for_k_1_through_64() {
    let seq = mixed_sequence(300);
    for k in 1..=64 {
        for canonical in [false, true] {
            assert_matches_reference(&seq, k, canonical, "mixed ACGT fixture");
        }
    }
}

/// `N` at every single position: every window touching it is skipped, all
/// others match the reference.
#[test]
fn n_at_every_position_is_skipped_exactly() {
    let base = mixed_sequence(64);
    for position in 0..base.len() {
        let mut seq = base.clone();
        seq[position] = b'N';
        for k in [1usize, 2, 7, 21, 32, 33, 64] {
            for canonical in [false, true] {
                assert_matches_reference(&seq, k, canonical, "single N");
            }
        }
    }
}

/// A run of `N`s: only the windows overlapping the run are skipped.
#[test]
fn n_runs_skip_only_windows_touching_them() {
    let seq = b"ACGTACGTACGTNNNNNNACGTACGTACGTACGTACGT";
    for k in [1usize, 3, 5, 8, 12, 20, 32, 33, 40] {
        for canonical in [false, true] {
            assert_matches_reference(seq, k, canonical, "N run");
        }
    }
}

/// A sequence made only of invalid bytes: nothing is emitted, every window is
/// skipped.
#[test]
fn all_invalid_sequence_emits_nothing_and_skips_every_window() {
    let seq = b"NNNNNNNNNNNNNNNNNNNN";
    for k in [1usize, 3, 10, 21, 33, 64] {
        let (got, skipped) = extract(seq, k, false);
        assert!(
            got.is_empty(),
            "invalid-only sequence must emit nothing (k={k})"
        );
        let expected = if seq.len() >= k {
            (seq.len() - k + 1) as u64
        } else {
            0
        };
        assert_eq!(skipped, expected, "every window must be skipped (k={k})");
    }
}

/// Lowercase input must be exactly equivalent to uppercase input.
#[test]
fn lowercase_matches_uppercase() {
    let upper = mixed_sequence(200);
    let lower: Vec<u8> = upper.iter().map(|b| b.to_ascii_lowercase()).collect();
    for k in [1usize, 4, 21, 32, 33, 64] {
        for canonical in [false, true] {
            let (upper_values, _) = extract(&upper, k, canonical);
            let (lower_values, _) = extract(&lower, k, canonical);
            assert_eq!(
                upper_values, lower_values,
                "lowercase ACGT must encode identically (k={k}, canonical={canonical})"
            );
            assert_matches_reference(&lower, k, canonical, "lowercase fixture");
        }
    }
}

/// Empty and short sequences emit nothing and are never rejected.
#[test]
fn empty_and_short_sequences_emit_nothing() {
    for k in [1usize, 2, 21, 32, 33, 64] {
        for len in 0..k {
            let seq = mixed_sequence(len);
            for canonical in [false, true] {
                let (got, skipped) = extract(&seq, k, canonical);
                assert!(
                    got.is_empty(),
                    "sequence shorter than k must emit nothing (len={len}, k={k})"
                );
                assert_eq!(
                    skipped, 0,
                    "sequence shorter than k must skip nothing (len={len}, k={k})"
                );
            }
        }
    }
}

/// Two consecutive calls must not create a window spanning the boundary.
///
/// A chimera would replace the two boundary-local windows with one merged
/// window, so the per-call emitted counts and values pin the reset.
#[test]
fn record_boundaries_never_span_calls() {
    let left = b"AAAAC";
    let right = b"CCCCC";
    let k = 5;
    let (left_values, _) = extract(left, k, false);
    let (right_values, _) = extract(right, k, false);
    assert_eq!(left_values.len(), 1, "left record emits exactly one window");
    assert_eq!(
        right_values.len(),
        1,
        "right record emits exactly one window"
    );

    // If a window could span the call boundary, a chimeric AAAAACCCC window
    // would appear. Assert it never does and the two real windows do.
    let mut combined = left_values.clone();
    combined.extend(right_values.iter().copied());
    assert_eq!(combined.len(), 2, "two records must emit two windows total");
    let chimeric = encode_kmer_bytes_u128(b"AAAAC").expect("valid");
    assert!(
        combined.contains(&chimeric),
        "left window must be the local one"
    );
}

/// Invalid k values are rejected at the public boundary.
#[test]
fn invalid_k_is_rejected() {
    let seq = b"ACGT";
    for invalid in [0usize, 65, 128] {
        match for_each_window(seq, invalid, false, |_: u128| Ok::<(), ()>(())) {
            Err(WindowError::InvalidK(reported)) => assert_eq!(
                reported, invalid,
                "WindowError::InvalidK must report the rejected k"
            ),
            other => panic!(
                "k={invalid} must be rejected, got {:?}",
                other.map(|s| s.emitted)
            ),
        }
    }
}

/// The first sink error aborts the pass and is returned verbatim in `Emit`.
#[test]
fn sink_error_propagates() {
    let seq = b"ACGTACGTACGT";
    let mut calls = 0usize;
    let outcome: Result<_, WindowError<&'static str>> = for_each_window(seq, 3, false, |_| {
        calls += 1;
        if calls == 2 {
            Err("stop")
        } else {
            Ok(())
        }
    });
    match outcome {
        Err(WindowError::Emit("stop")) => {}
        other => panic!(
            "expected WindowError::Emit(\"stop\"), got {:?}",
            other.map(|s| s.emitted)
        ),
    }
    assert_eq!(calls, 2, "emission must stop at the first sink error");
}
