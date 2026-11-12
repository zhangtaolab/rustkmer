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

use rustkmer::count::{CountEngine, CountResult, EngineConfig, SequenceKind};
use rustkmer::hash::filtering::CountFilter;
use rustkmer::hash::table::KmerCounter;
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

/// Decode a reference map to the CLI text-output key space.
fn reference_text_map(
    encoded: &BTreeMap<u128, u32>,
    k: usize,
) -> BTreeMap<String, u32> {
    encoded
        .iter()
        .map(|(key, count)| {
            (
                rustkmer::kmer::encoding::decode_kmer_u128(*key, k),
                *count,
            )
        })
        .collect()
}

/// Captured stderr as text.
fn stderr_text(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

/// Parse the numeric value of every stderr line containing `label`.
fn stderr_values(output: &Output, label: &str) -> Vec<u64> {
    stderr_text(output)
        .lines()
        .filter(|line| line.contains(label))
        .map(|line| {
            line.rsplit_once(':')
                .map(|(_, value)| value.trim().parse::<u64>().expect("numeric stat"))
                .unwrap_or_else(|| panic!("malformed stat line: {line:?}"))
        })
        .collect()
}

/// Parse the numeric key of every `.rkdb` v2 record (42-byte header, then
/// 16-byte LE u128 + 4-byte LE u32 entries).
fn read_rkdb_keys(path: &Path) -> Vec<u128> {
    let bytes = fs::read(path).expect("read rkdb");
    assert!(bytes.len() >= 42, "rkdb file must carry the v2 header");
    assert_eq!(&bytes[0..4], b"RKDB", "frozen RKDB magic");
    assert_eq!(
        u16::from_le_bytes([bytes[4], bytes[5]]),
        2,
        "frozen RKDB version"
    );
    let mut keys = Vec::new();
    let mut offset = 42;
    while offset + 20 <= bytes.len() {
        let mut key_bytes = [0u8; 16];
        key_bytes.copy_from_slice(&bytes[offset..offset + 16]);
        keys.push(u128::from_le_bytes(key_bytes));
        offset += 20;
    }
    assert_eq!(offset, bytes.len(), "no trailing partial record");
    keys
}

/// Run the real CLI `count` command with the given thread count and format.
fn run_cli(input: &Path, k: usize, canonical: bool, threads: usize, format: &str, output: &Path) -> Output {
    run_cli_with(&[input], k, canonical, threads, format, output, &["-q"])
}

/// Run the real CLI with multiple inputs and extra flags (warnings, filters,
/// `--no-sort`), always writing to `output`.
fn run_cli_with(
    inputs: &[&Path],
    k: usize,
    canonical: bool,
    threads: usize,
    format: &str,
    output: &Path,
    extra_args: &[&str],
) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_rustkmer"));
    command.arg("count").arg("-k").arg(k.to_string()).arg("-i");
    for input in inputs {
        command.arg(input);
    }
    if canonical {
        command.arg("-C");
    }
    command
        .arg("--threads")
        .arg(threads.to_string())
        .arg("-o")
        .arg(output)
        .arg("--format")
        .arg(format);
    for arg in extra_args {
        command.arg(arg);
    }
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

// --- Task 2: exact statistics, per-key ownership, and the merge bridge ------

/// Count the fixture through the sequential engine and finish it.
fn count_fixture_with_engine(input: &Path, k: usize, canonical: bool) -> CountResult {
    let mut engine = CountEngine::new(EngineConfig::new(k, canonical, 1, 1024))
        .expect("valid k must construct the engine");
    engine
        .count_file(input, SequenceKind::Fastq)
        .expect("sequential engine count must succeed");
    engine.finish().expect("finish must succeed")
}

/// `CountResult::merge_into` must compose the disjoint partition tables into a
/// fresh `KmerCounter` through the already-tested `merge_local_counts` path,
/// producing a map and statistics identical to the reference.
#[test]
fn merge_into_matches_reference_counter() {
    let sequences = fixture_sequences();
    let dir = tempfile::tempdir().expect("tempdir for merge fixture");
    let input = dir.path().join("fixture.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    for k in [21usize, 32, 64] {
        for canonical in [false, true] {
            let result = count_fixture_with_engine(&input, k, canonical);
            let want = reference_map(&borrowed, k, canonical);

            let counter = KmerCounter::new(k, canonical, 1024, 1).expect("counter constructs");
            result
                .merge_into(&counter)
                .expect("merge_into must succeed on a fresh counter");
            let got: BTreeMap<u128, u32> = counter.get_all_counts().into_iter().collect();
            assert_eq!(
                got, want,
                "merge_into map diverged from the reference (k={k}, canonical={canonical})"
            );

            let want_total: u64 = want.values().map(|count| *count as u64).sum();
            assert_eq!(
                counter.total_kmers(),
                want_total,
                "merged counter total must equal the sum of counts"
            );
            assert_eq!(
                counter.unique_kmers(),
                want.len() as u64,
                "merged counter unique must equal the distinct-key count"
            );
        }
    }
}

/// Per-key lookup and pair iteration must agree with the reference map: every
/// reference key is found exactly once, an absent key returns `None`, and
/// `for_each_count` yields each pair exactly once.
#[test]
fn get_count_and_for_each_count_agree_with_the_map() {
    let sequences = fixture_sequences();
    let dir = tempfile::tempdir().expect("tempdir for lookup fixture");
    let input = dir.path().join("fixture.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    for k in [21usize, 32, 64] {
        for canonical in [false, true] {
            let result = count_fixture_with_engine(&input, k, canonical);
            let want = reference_map(&borrowed, k, canonical);

            for (key, count) in &want {
                assert_eq!(
                    result.get_count(*key),
                    Some(*count),
                    "get_count must find every reference key exactly once \
                     (k={k}, canonical={canonical}, key={key})"
                );
            }

            let mut visited: BTreeMap<u128, u32> = BTreeMap::new();
            result.for_each_count(|key, count| {
                assert!(
                    visited.insert(key, count).is_none(),
                    "for_each_count visited a key twice: {key}"
                );
            });
            assert_eq!(
                visited, want,
                "for_each_count must yield the reference map exactly once \
                 (k={k}, canonical={canonical})"
            );

            // A valid encoded key absent from the fixture must return None.
            // k = 64 spans the whole u128 key space, so cap the search there.
            let key_limit: u128 = if 2 * k >= 128 {
                u128::MAX
            } else {
                1u128 << (2 * k)
            };
            let mut absent: u128 = 0;
            while want.contains_key(&absent) {
                absent += 1;
                assert!(absent < key_limit, "the fixture cannot cover every key");
            }
            assert_eq!(
                result.get_count(absent),
                None,
                "get_count must return None for an unobserved key (k={k})"
            );
        }
    }
}

/// `stats()` and `filtering_stats()` must match `KmerCounter` semantics,
/// including the WR-01 denominator (`total_before` = successfully counted
/// k-mers) for `-L`/`-U` combinations.
#[test]
fn stats_and_filtering_match_counter_semantics() {
    let sequences = fixture_sequences();
    let dir = tempfile::tempdir().expect("tempdir for stats fixture");
    let input = dir.path().join("fixture.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    for k in [21usize, 64] {
        for canonical in [false, true] {
            let result = count_fixture_with_engine(&input, k, canonical);
            let want = reference_map(&borrowed, k, canonical);

            let stats = result.stats();
            let want_total: u64 = want.values().map(|count| *count as u64).sum();
            assert_eq!(
                stats.total_kmers, want_total,
                "total must be the sum of counts (k={k}, canonical={canonical})"
            );
            assert_eq!(
                stats.unique_kmers,
                want.len() as u64,
                "unique must be the distinct-key count"
            );
            let mut pair_count = 0u64;
            result.for_each_count(|_, _| pair_count += 1);
            assert_eq!(
                pair_count, stats.unique_kmers,
                "pair iteration must yield exactly `unique` pairs"
            );

            // Reference counter built by the production per-window path.
            let counter = KmerCounter::new(k, canonical, 1024, 1).expect("counter constructs");
            for (key, count) in &want {
                for _ in 0..*count {
                    counter
                        .increment(*key)
                        .expect("reference increments cannot overflow");
                }
            }

            let filters = [
                None,
                Some(CountFilter::new(None, None)),
                Some(CountFilter::new(Some(2), None)),
                Some(CountFilter::new(None, Some(3))),
                Some(CountFilter::new(Some(2), Some(5))),
            ];
            for filter in filters {
                let expected = counter.get_filtering_stats(&filter);
                let got = result.filtering_stats(&filter);
                assert_eq!(got.total_before, expected.total_before);
                assert_eq!(got.unique_before, expected.unique_before);
                assert_eq!(got.kept_after, expected.kept_after);
                assert_eq!(got.filtered_out, expected.filtered_out);
                assert!(
                    (got.kept_percentage() - expected.kept_percentage()).abs() < f64::EPSILON,
                    "kept percentage must match KmerCounter semantics (k={k}, filter={filter:?})"
                );

                let expected_pairs: BTreeMap<u128, u32> =
                    counter.get_filtered_kmers(&filter).into_iter().collect();
                let got_pairs: BTreeMap<u128, u32> =
                    result.filtered_pairs(&filter).into_iter().collect();
                assert_eq!(
                    got_pairs, expected_pairs,
                    "filtered_pairs must match get_filtered_kmers (k={k}, filter={filter:?})"
                );
            }
        }
    }
}

// --- Task 3: CLI behavior preservation at the engine/legacy boundary --------

/// Reads with an `N` at every position of a 64-base read, plus multi-`N` and
/// pure-ACGT reads.
fn n_position_sequences() -> Vec<Vec<u8>> {
    let base = mixed_sequence(64);
    let mut sequences = Vec::new();
    for position in 0..base.len() {
        let mut sequence = base.clone();
        sequence[position] = b'N';
        sequences.push(sequence);
    }
    sequences.push(
        b"NNNNNNNNNACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT".to_vec(),
    );
    sequences.push(
        b"ACGTACGTACGTACGTACGTNNNNNNNNNNACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC".to_vec(),
    );
    sequences.push(mixed_sequence(90));
    sequences
}

/// Repeated reads (so count filters see counts well above 1) plus `N` variants
/// whose windows are skipped.
fn repeated_sequences() -> Vec<Vec<u8>> {
    let base = mixed_sequence(80);
    let mut sequences: Vec<Vec<u8>> = (0..20).map(|_| base.clone()).collect();
    let mut single_n = base.clone();
    single_n[10] = b'N';
    sequences.push(single_n);
    let mut double_n = base.clone();
    double_n[40] = b'N';
    double_n[41] = b'N';
    sequences.push(double_n);
    sequences.push(b"NNNNNACGTACGTACGTACGTACGTACGTACGTACGT".to_vec());
    sequences
}

/// N-containing reads must produce exactly the skip-N reference map on both
/// the engine (`--threads 1`) and legacy (`--threads 4`) paths.
#[test]
fn n_containing_reads_match_skip_n_reference() {
    let sequences = n_position_sequences();
    let dir = tempfile::tempdir().expect("tempdir for N-read fixture");
    let input = dir.path().join("n_reads.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    for k in [21usize, 64] {
        for canonical in [false, true] {
            let text_t1 = dir.path().join(format!("n-k{k}-c{canonical}-t1.tsv"));
            let text_t4 = dir.path().join(format!("n-k{k}-c{canonical}-t4.tsv"));
            let t1 = run_cli(&input, k, canonical, 1, "text", &text_t1);
            let t4 = run_cli(&input, k, canonical, 4, "text", &text_t4);
            assert_cli_success(&t1, "N-reads t1");
            assert_cli_success(&t4, "N-reads t4");

            let want = reference_text_map(&reference_map(&borrowed, k, canonical), k);
            assert!(
                !want.is_empty(),
                "the fixture must emit at least one valid window (k={k})"
            );
            assert_eq!(
                read_text_counts(&text_t1),
                want,
                "--threads 1 engine map must match the skip-N reference \
                 (k={k}, canonical={canonical})"
            );
            assert_eq!(
                read_text_counts(&text_t4),
                want,
                "--threads 4 legacy map must match the skip-N reference \
                 (k={k}, canonical={canonical})"
            );
            assert_eq!(
                read_text_counts(&text_t1),
                read_text_counts(&text_t4),
                "both paths must agree on the N-containing reads"
            );
        }
    }
}

/// Multi-file cumulative statistics and the one-warning-per-4096-record-batch
/// behavior must be preserved, with the pinned warning wording.
#[test]
fn multi_file_stats_and_warnings_are_preserved() {
    let dir = tempfile::tempdir().expect("tempdir for multi-file fixture");

    // File A: 4097 poly-A records, with an N in the first AND last records so
    // both the full 4096-record batch and the trailing partial batch warn.
    let mut file_a_sequences = Vec::new();
    for index in 0..4097 {
        let mut sequence = vec![b'A'; 150];
        if index == 0 || index == 4096 {
            sequence[7] = b'N';
        }
        file_a_sequences.push(sequence);
    }
    let file_a = dir.path().join("a.fastq");
    write_fastq(&file_a, &file_a_sequences);

    // File B: poly-C, so its key set is disjoint from file A's and the
    // cumulative unique count is the sum of the separate-run uniques.
    let file_b_sequences: Vec<Vec<u8>> = (0..10).map(|_| vec![b'C'; 150]).collect();
    let file_b = dir.path().join("b.fastq");
    write_fastq(&file_b, &file_b_sequences);

    let combined_output = dir.path().join("combined.tsv");
    let combined = run_cli_with(
        &[&file_a, &file_b],
        21,
        false,
        1,
        "text",
        &combined_output,
        &["--show-warnings"],
    );
    assert_cli_success(&combined, "combined t1");

    let combined_stderr = stderr_text(&combined);
    let warning_count = combined_stderr
        .lines()
        .filter(|line| line.contains("Warning: Skipped"))
        .count();
    assert_eq!(
        warning_count, 2,
        "one warning per 4096-record batch with skips (full batch + trailing partial); \
         stderr:\n{combined_stderr}"
    );
    assert!(
        combined_stderr.contains("with invalid characters in chunk"),
        "the warning wording is pinned; stderr:\n{combined_stderr}"
    );

    let cumulative_totals = stderr_values(&combined, "Total k-mers processed");
    let cumulative_uniques = stderr_values(&combined, "Unique k-mers found");
    assert_eq!(cumulative_totals.len(), 2, "one cumulative stat line per file");
    assert_eq!(cumulative_uniques.len(), 2, "one cumulative stat line per file");
    assert!(
        cumulative_totals[1] >= cumulative_totals[0],
        "cumulative totals must be monotone"
    );
    assert!(
        cumulative_uniques[1] >= cumulative_uniques[0],
        "cumulative uniques must be monotone"
    );

    // Separate single-file runs: the elementwise sum must equal the cumulative
    // multi-file values, and the disjoint key sets make uniques additive.
    let only_a_output = dir.path().join("a.tsv");
    let only_a = run_cli_with(&[&file_a], 21, false, 1, "text", &only_a_output, &[]);
    assert_cli_success(&only_a, "file A alone");
    let only_b_output = dir.path().join("b.tsv");
    let only_b = run_cli_with(&[&file_b], 21, false, 1, "text", &only_b_output, &[]);
    assert_cli_success(&only_b, "file B alone");

    let a_totals = stderr_values(&only_a, "Total k-mers processed");
    let b_totals = stderr_values(&only_b, "Total k-mers processed");
    let a_uniques = stderr_values(&only_a, "Unique k-mers found");
    let b_uniques = stderr_values(&only_b, "Unique k-mers found");
    assert_eq!(a_totals.len(), 1);
    assert_eq!(b_totals.len(), 1);
    assert_eq!(a_uniques.len(), 1);
    assert_eq!(b_uniques.len(), 1);

    assert_eq!(cumulative_totals[0], a_totals[0]);
    assert_eq!(cumulative_totals[1], a_totals[0] + b_totals[0]);
    assert_eq!(cumulative_uniques[0], a_uniques[0]);
    assert_eq!(cumulative_uniques[1], a_uniques[0] + b_uniques[0]);
    assert_eq!(a_uniques[0], 1, "poly-A has one distinct k-mer");
    assert_eq!(b_uniques[0], 1, "poly-C has one distinct k-mer");

    let mut summed_map = read_text_counts(&only_a_output);
    for (key, count) in read_text_counts(&only_b_output) {
        *summed_map.entry(key).or_insert(0) += count;
    }
    assert_eq!(
        read_text_counts(&combined_output),
        summed_map,
        "multi-file output must be the elementwise sum of the separate runs"
    );
}

/// Text output is sorted by decoded k-mer, binary records are sorted by the
/// numeric key, and the `.rkdb` bytes match the legacy path.
#[test]
fn text_and_binary_output_order_is_unchanged() {
    let sequences = n_position_sequences();
    let dir = tempfile::tempdir().expect("tempdir for ordering fixture");
    let input = dir.path().join("ordering.fastq");
    write_fastq(&input, &sequences);

    let text_t1 = dir.path().join("order-t1.tsv");
    let text_t4 = dir.path().join("order-t4.tsv");
    let t1_text = run_cli(&input, 21, true, 1, "text", &text_t1);
    let t4_text = run_cli(&input, 21, true, 4, "text", &text_t4);
    assert_cli_success(&t1_text, "ordering text t1");
    assert_cli_success(&t4_text, "ordering text t4");
    assert_eq!(read_text_counts(&text_t1), read_text_counts(&text_t4));

    let content = fs::read_to_string(&text_t1).expect("read sorted text output");
    let sequences_in_file: Vec<&str> = content
        .lines()
        .filter(|line| !line.is_empty())
        .map(|line| line.split_once('\t').expect("tab-separated").0)
        .collect();
    let mut sorted_sequences = sequences_in_file.clone();
    sorted_sequences.sort_unstable();
    assert_eq!(
        sequences_in_file, sorted_sequences,
        "text output must be sorted by decoded k-mer"
    );

    let rkdb_t1 = dir.path().join("order-t1.rkdb");
    let rkdb_t4 = dir.path().join("order-t4.rkdb");
    let t1_bin = run_cli(&input, 21, true, 1, "binary", &rkdb_t1);
    let t4_bin = run_cli(&input, 21, true, 4, "binary", &rkdb_t4);
    assert_cli_success(&t1_bin, "ordering binary t1");
    assert_cli_success(&t4_bin, "ordering binary t4");

    let keys = read_rkdb_keys(&rkdb_t1);
    assert!(
        keys.windows(2).all(|pair| pair[0] < pair[1]),
        "binary records must be sorted by numeric key (unique keys ascend strictly)"
    );
    assert_eq!(
        sha256_hex(&fs::read(&rkdb_t1).expect("read t1 rkdb")),
        sha256_hex(&fs::read(&rkdb_t4).expect("read t4 rkdb")),
        "sorted .rkdb bytes must be identical across the engine and legacy paths"
    );
}

/// `-L`/`-U` combinations must keep the same keys and report the same
/// filtering statistics on both paths.
#[test]
fn count_filters_are_unchanged() {
    let sequences = repeated_sequences();
    let dir = tempfile::tempdir().expect("tempdir for filter fixture");
    let input = dir.path().join("filters.fastq");
    write_fastq(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    let cases: Vec<(Vec<&str>, CountFilter)> = vec![
        (vec!["-L", "2"], CountFilter::new(Some(2), None)),
        (vec!["-U", "3"], CountFilter::new(None, Some(3))),
        (
            vec!["-L", "2", "-U", "3"],
            CountFilter::new(Some(2), Some(3)),
        ),
    ];

    for (case_index, (extra, filter)) in cases.into_iter().enumerate() {
        let text_t1 = dir.path().join(format!("filter-{case_index}-t1.tsv"));
        let text_t4 = dir.path().join(format!("filter-{case_index}-t4.tsv"));
        let t1 = run_cli_with(&[&input], 21, false, 1, "text", &text_t1, &extra);
        let t4 = run_cli_with(&[&input], 21, false, 4, "text", &text_t4, &extra);
        assert_cli_success(&t1, "filter t1");
        assert_cli_success(&t4, "filter t4");

        let t1_map = read_text_counts(&text_t1);
        let t4_map = read_text_counts(&text_t4);
        assert_eq!(
            t1_map, t4_map,
            "filter {extra:?} must keep identical keys on both paths"
        );

        let want: BTreeMap<String, u32> = reference_text_map(
            &reference_map(&borrowed, 21, false),
            21,
        )
        .into_iter()
        .filter(|(_, count)| filter.passes(*count as u64))
        .collect();
        assert_eq!(t1_map, want, "filter {extra:?} must match the reference");

        let t1_stats = stderr_text(&t1);
        let t4_stats = stderr_text(&t4);
        for label in [
            "K-mers kept after filtering",
            "K-mers filtered out",
            "Filtering retention",
        ] {
            let t1_lines: Vec<&str> = t1_stats.lines().filter(|line| line.contains(label)).collect();
            let t4_lines: Vec<&str> = t4_stats.lines().filter(|line| line.contains(label)).collect();
            assert_eq!(
                t1_lines, t4_lines,
                "filtering statistic {label:?} must be identical on both paths"
            );
            assert!(!t1_lines.is_empty(), "filtering statistic {label:?} must be reported");
        }

        let kept = stderr_values(&t1, "K-mers kept after filtering");
        assert_eq!(kept.len(), 1);
        assert_eq!(
            kept[0], want.len() as u64,
            "reported kept-after count must equal the reference-filtered key count"
        );
    }
}

/// `--no-sort` must write the same multiset of pairs as the sorted run.
#[test]
fn no_sort_still_writes_the_same_set() {
    let sequences = repeated_sequences();
    let dir = tempfile::tempdir().expect("tempdir for no-sort fixture");
    let input = dir.path().join("no_sort.fastq");
    write_fastq(&input, &sequences);

    let sorted_output = dir.path().join("sorted.tsv");
    let unsorted_output = dir.path().join("unsorted.tsv");
    let sorted = run_cli(&input, 21, false, 1, "text", &sorted_output);
    let unsorted = run_cli_with(
        &[&input],
        21,
        false,
        1,
        "text",
        &unsorted_output,
        &["--no-sort", "-q"],
    );
    assert_cli_success(&sorted, "sorted run");
    assert_cli_success(&unsorted, "no-sort run");

    assert_eq!(
        read_text_counts(&sorted_output),
        read_text_counts(&unsorted_output),
        "--no-sort must write the same set of pairs (byte order may differ)"
    );
}
