//! ENGINE-01 / ENGINE-03 proofs for the shared counting engine.
//!
//! Task 1 (tracer) proves the thin end-to-end slice: a direct
//! [`CountEngine::count_file`] at `threads = 1` reproduces the per-window
//! reference map exactly for the dense/wide/wide-boundary k values in both
//! canonical modes, and the real CLI at `--threads 1` (engine path) is
//! observationally identical to `--threads 4` (legacy per-chunk rayon path):
//! same text map, same sorted `.rkdb` bytes.
//!
//! Task 2 extends this file with the exactness/statistics/merge-bridge proofs
//! and Task 3 with the CLI-boundary behavior-preservation matrix.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use sha2::{Digest, Sha256};

/// Deterministic ACGT base stream (inline LCG) for fixture generation.
fn mixed_sequence(len: usize) -> Vec<u8> {
    const BASES: [u8; 4] = *b"ACGT";
    let mut state: u64 = 0x5EED_1234_ABCD_0001;
    (0..len)
        .map(|_| {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            BASES[((state >> 33) & 3) as usize]
        })
        .collect()
}

/// Multi-record fixture covering both storage widths, the rolling/wide
/// boundary, canonicalizable sequences, a lowercase record, an `N`-containing
/// record, and a record shorter than k.
fn fixture_sequences() -> Vec<Vec<u8>> {
    let mut sequences = vec![
        mixed_sequence(180),
        mixed_sequence(90),
        b"ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT".to_vec(),
        b"AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTT"
            .to_vec(),
        b"ACGTACGTACGTACGTACGTACGTACGTACGTNACGTACGTACGTACGTACGTACGTACGTACGTA".to_vec(),
        b"ACGT".to_vec(),
    ];
    // A lowercase record: the extractor accepts ASCII-lowercase ACGT.
    sequences.push(mixed_sequence(75).iter().map(u8::to_ascii_lowercase).collect());
    sequences
}

/// Write four-line FASTQ records for the given sequences.
fn write_fastq(path: &Path, sequences: &[Vec<u8>]) {
    let mut body = String::new();
    for (idx, sequence) in sequences.iter().enumerate() {
        let sequence = std::str::from_utf8(sequence).expect("fixture is ASCII");
        body.push_str(&format!("@read{idx}\n"));
        body.push_str(sequence);
        body.push_str("\n+\n");
        body.push_str(&"I".repeat(sequence.len()));
        body.push('\n');
    }
    fs::write(path, body).expect("write FASTQ fixture");
}

/// The unchanged per-window reference map (`encode_kmer_bytes_u128` +
/// `canonical_kmer_u128` over naive windows).
fn reference_map(sequences: &[&[u8]], k: usize, canonical: bool) -> BTreeMap<u128, u32> {
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
                canonical_kmer_u128(encoded, k).expect("a valid window canonicalizes")
            } else {
                encoded
            };
            *counts.entry(value).or_insert(0) += 1;
        }
    }
    counts
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Run the real CLI `count` command with the given thread count and format.
fn run_cli(input: &Path, k: usize, canonical: bool, threads: usize, format: &str, output: &Path) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_rustkmer"));
    command
        .arg("count")
        .arg("-k")
        .arg(k.to_string())
        .arg("-i")
        .arg(input);
    if canonical {
        command.arg("-C");
    }
    command
        .arg("--threads")
        .arg(threads.to_string())
        .arg("-o")
        .arg(output)
        .arg("--format")
        .arg(format)
        .arg("-q");
    command.output().expect("spawn rustkmer count")
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

fn assert_cli_success(output: &Output, context: &str) {
    assert!(
        output.status.success(),
        "rustkmer count failed ({context}): status={:?}\nstderr:\n{}",
        output.status,
        String::from_utf8_lossy(&output.stderr)
    );
}

/// A direct sequential engine count must reproduce the reference map for
/// k in {21, 32, 64} x canonical on/off, with exact statistics.
#[test]
fn sequential_engine_map_matches_reference_across_k_and_canonical() {
    let sequences = fixture_sequences();
    let dir = tempfile::tempdir().expect("tempdir for engine fixture");
    let input: PathBuf = dir.path().join("fixture.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    for k in [21usize, 32, 64] {
        for canonical in [false, true] {
            let mut engine = CountEngine::new(EngineConfig::new(k, canonical, 1, 1024))
                .expect("valid k must construct the engine");
            let file_stats = engine
                .count_file(&input, SequenceKind::Fastq)
                .expect("sequential engine count must succeed");
            let result = engine.finish().expect("finish must succeed");
            let stats = result.stats();

            let want = reference_map(&borrowed, k, canonical);
            let got: BTreeMap<u128, u32> = result.into_pairs().into_iter().collect();
            assert_eq!(
                got, want,
                "engine map diverged from the reference (k={k}, canonical={canonical})"
            );

            let want_total: u64 = want.values().map(|count| *count as u64).sum();
            assert_eq!(
                stats.total_kmers, want_total,
                "engine total must be the sum of counts (k={k}, canonical={canonical})"
            );
            assert_eq!(
                stats.unique_kmers, want.len() as u64,
                "engine unique must be the distinct-key count (k={k}, canonical={canonical})"
            );
            assert_eq!(
                file_stats.stats.total_kmers, want_total,
                "per-file stats must match the final stats (k={k}, canonical={canonical})"
            );
            assert_eq!(
                file_stats.stats.skipped_windows,
                stats.skipped_windows,
                "per-file skipped windows must match the final stats"
            );
            assert!(!got.is_empty(), "fixture must produce k-mers (k={k})");
        }
    }
}

/// The real CLI at `--threads 1` (engine path) and `--threads 4` (legacy path)
/// must emit the same text map and byte-identical sorted `.rkdb` files.
#[test]
fn cli_t1_engine_matches_legacy_and_rkdb_sha256() {
    let sequences = fixture_sequences();
    let dir = tempfile::tempdir().expect("tempdir for CLI fixture");
    let input = dir.path().join("fixture.fastq");
    write_fastq(&input, &sequences);

    for k in [21usize, 64] {
        for canonical in [false, true] {
            let text_t1 = dir.path().join(format!("k{k}-c{canonical}-t1.tsv"));
            let text_t4 = dir.path().join(format!("k{k}-c{canonical}-t4.tsv"));
            let rkdb_t1 = dir.path().join(format!("k{k}-c{canonical}-t1.rkdb"));
            let rkdb_t4 = dir.path().join(format!("k{k}-c{canonical}-t4.rkdb"));

            let t1_text = run_cli(&input, k, canonical, 1, "text", &text_t1);
            let t4_text = run_cli(&input, k, canonical, 4, "text", &text_t4);
            assert_cli_success(&t1_text, "text t1");
            assert_cli_success(&t4_text, "text t4");

            assert_eq!(
                read_text_counts(&text_t1),
                read_text_counts(&text_t4),
                "--threads 1 (engine) text map must equal --threads 4 (legacy) \
                 (k={k}, canonical={canonical})"
            );

            let t1_bin = run_cli(&input, k, canonical, 1, "binary", &rkdb_t1);
            let t4_bin = run_cli(&input, k, canonical, 4, "binary", &rkdb_t4);
            assert_cli_success(&t1_bin, "binary t1");
            assert_cli_success(&t4_bin, "binary t4");

            let bytes_t1 = fs::read(&rkdb_t1).expect("read t1 rkdb");
            let bytes_t4 = fs::read(&rkdb_t4).expect("read t4 rkdb");
            assert_eq!(
                sha256_hex(&bytes_t1),
                sha256_hex(&bytes_t4),
                "sorted .rkdb bytes must be identical across the engine and legacy paths \
                 (k={k}, canonical={canonical})"
            );

            // The text map must also equal the reference map (decoded).
            let want = reference_map(
                &sequences.iter().map(Vec::as_slice).collect::<Vec<_>>(),
                k,
                canonical,
            );
            let want_text: BTreeMap<String, u32> = want
                .iter()
                .map(|(encoded, count)| {
                    (rustkmer::kmer::encoding::decode_kmer_u128(*encoded, k), *count)
                })
                .collect();
            assert_eq!(
                read_text_counts(&text_t1),
                want_text,
                "CLI t1 text map must equal the reference map (k={k}, canonical={canonical})"
            );
        }
    }
}
