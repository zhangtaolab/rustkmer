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

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

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

// --- Task 2: CLI-facing local path -----------------------------------------

/// Minimal RAII temp directory: removed on drop, even when an assertion fails.
struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("rustkmer-par03-{}-{}", std::process::id(), tag));
        let _ = fs::remove_dir_all(&path);
        fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn join(&self, name: &str) -> PathBuf {
        self.path.join(name)
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.path);
    }
}

/// Write four-line FASTQ records for the given sequences.
fn write_fastq(path: &Path, sequences: &[&[u8]]) {
    let mut body = String::new();
    for (idx, sequence) in sequences.iter().enumerate() {
        let sequence = std::str::from_utf8(sequence).expect("fixture is ASCII");
        body.push_str(&format!("@read{}\n", idx));
        body.push_str(sequence);
        body.push_str("\n+\n");
        body.push_str(&"I".repeat(sequence.len()));
        body.push('\n');
    }
    fs::write(path, body).expect("write FASTQ fixture");
}

/// Run the real CLI binary (the production hot loop) and write a text table.
fn run_cli_count(inputs: &[&Path], k: usize, canonical: bool, output: &Path) {
    let mut command = Command::new(env!("CARGO_BIN_EXE_rustkmer"));
    command.arg("count").arg("-k").arg(k.to_string()).arg("-i");
    for input in inputs {
        command.arg(input);
    }
    if canonical {
        command.arg("-C");
    }
    command
        .arg("-o")
        .arg(output)
        .arg("--format")
        .arg("text")
        .arg("-q");

    let result = command.output().expect("spawn rustkmer count");
    assert!(
        result.status.success(),
        "rustkmer count failed: status={:?}\nstderr:\n{}",
        result.status,
        String::from_utf8_lossy(&result.stderr)
    );
}

/// Parse a `SEQ<TAB>COUNT` text count table.
fn read_text_counts(path: &Path) -> BTreeMap<String, u32> {
    let content = fs::read_to_string(path).expect("read text count table");
    content
        .lines()
        .filter(|line| !line.is_empty())
        .map(|line| {
            let (sequence, count) = line
                .split_once('\t')
                .unwrap_or_else(|| panic!("malformed count line: {:?}", line));
            (
                sequence.to_string(),
                count.parse::<u32>().expect("parse count"),
            )
        })
        .collect()
}

/// The reference map, built with the unchanged per-window u128 encoder and
/// decoded to k-mer strings (the CLI text output's key space).
fn reference_text_counts(sequences: &[&[u8]], k: usize, canonical: bool) -> BTreeMap<String, u32> {
    let mut counts = BTreeMap::new();
    for sequence in sequences {
        if sequence.len() < k {
            continue;
        }
        for window in sequence.windows(k) {
            let Ok(encoded) = encode_kmer_bytes_u128(window) else {
                continue;
            };
            let value = if canonical {
                canonical_kmer_u128(encoded, k).expect("valid window canonicalizes")
            } else {
                encoded
            };
            *counts
                .entry(rustkmer::kmer::encoding::decode_kmer_u128(value, k))
                .or_insert(0) += 1;
        }
    }
    counts
}

/// **Task 2 end-to-end.** The real CLI hot loop (rolling encoder for k = 21/32,
/// u128 fallback for k = 64) must reproduce the per-window reference count map
/// exactly, in both canonical modes.
#[test]
fn cli_local_path_matches_reference_for_k_21_32_and_64() {
    let fixture = acgt_fixture();
    let sequences: Vec<&[u8]> = vec![
        &fixture[..120],
        &fixture[40..160],
        &fixture[80..],
        // A record shorter than k=64 must contribute nothing.
        b"ACGTACGTACGT",
    ];

    let dir = TempDir::new("cli-parity");
    let input = dir.join("par03.fastq");
    write_fastq(&input, &sequences);

    for k in [21usize, 32, 64] {
        for canonical in [false, true] {
            let output = dir.join(&format!("k{}-canonical-{}.tsv", k, canonical));
            run_cli_count(&[&input], k, canonical, &output);

            let got = read_text_counts(&output);
            let want = reference_text_counts(&sequences, k, canonical);

            assert_eq!(
                got, want,
                "CLI local path diverged from the per-window reference \
                 (k={}, canonical={})",
                k, canonical
            );
            assert!(!got.is_empty(), "fixture must produce k-mers (k={})", k);
        }
    }
}
