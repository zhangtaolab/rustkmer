//! OUT-01 output-pipeline proofs (Phase 8, plan 08-01).
//!
//! The sorted `.rkdb` path now collects its pairs through a CONSUMING
//! `CountResult` API, sorts them in place with rayon's pdqsort family, and
//! streams the sorted slice through the frozen `format.rs` header/entry
//! writers. These tests pin the observable contract:
//!
//! * the k21/canonical/sorted golden input still emits the exact committed
//!   fixture bytes (`a5da813e…`) — byte identity is the only acceptable
//!   reason a golden hash may ever change;
//! * records are strictly ascending by the numeric encoded key and the
//!   record parse lands exactly on the file end;
//! * the 42-byte header's record count equals the number of records on disk,
//!   and the sum of their counts equals the CLI's reported total (IN-03);
//! * `--threads 1` and `--threads 4` emit byte-identical `.rkdb` files.
//!
//! Fixtures are read from `tests/fixtures/`, never written. The CLI binary is
//! `env!("CARGO_BIN_EXE_rustkmer")`, i.e. the real release-path executable
//! under test.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};
use sha2::{Digest, Sha256};

/// The fixed golden input — MUST match `tests/golden_generate.rs::GOLDEN_INPUT`
/// and `tests/golden_tests.rs`, otherwise the byte-identity comparison is
/// meaningless.
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// `tests/fixtures/golden_k21_canon_sorted.rkdb` (pre-refactor baseline).
const GOLDEN_K21_CANON_SORTED_SHA256: &str =
    "a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7";

/// Write a plain FASTA file with one record per sequence.
fn write_fasta(path: &Path, sequences: &[&str]) {
    let mut body = String::new();
    for (idx, sequence) in sequences.iter().enumerate() {
        body.push_str(&format!(">seq{idx}\n{sequence}\n"));
    }
    fs::write(path, body).expect("write FASTA fixture");
}

/// The golden input written to a temp FASTA (never `tests/fixtures/`).
fn golden_fasta(dir: &Path) -> PathBuf {
    let input = dir.join("golden_input.fa");
    write_fasta(&input, GOLDEN_INPUT);
    input
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Run the real CLI `count` command against `input`.
///
/// Every output-pipeline proof is canonical (`-C`), so the flag is fixed here
/// rather than threaded through as another parameter.
fn run_count(
    input: &Path,
    k: usize,
    threads: usize,
    format: &str,
    out: &Path,
    quiet: bool,
    extra: &[&str],
) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_rustkmer"));
    command
        .arg("count")
        .arg("-k")
        .arg(k.to_string())
        .arg("-i")
        .arg(input)
        .arg("-C")
        .arg("--threads")
        .arg(threads.to_string())
        .arg("-o")
        .arg(out)
        .arg("--format")
        .arg(format);
    if quiet {
        command.arg("-q");
    }
    for arg in extra {
        command.arg(arg);
    }
    command.output().expect("spawn rustkmer count")
}

fn assert_success(output: &Output, context: &str) {
    assert!(
        output.status.success(),
        "rustkmer count failed ({context}): status={:?}\nstderr:\n{}",
        output.status,
        String::from_utf8_lossy(&output.stderr)
    );
}

/// Parse a `.rkdb` v2 file: `(header record count, [(key, count)])`.
///
/// Header layout (42 bytes): magic 0..4, version 4..6, kmer size 6,
/// padding 7..10, total_kmers 10..18, flags 18, padding 19..26,
/// data_offset 26..34, index_offset 34..42. Records are 16-byte LE u128 keys
/// plus 4-byte LE u32 counts. Asserts the magic, version, the canonical data
/// offset, and that the record parse lands EXACTLY on the file end.
fn read_rkdb(path: &Path) -> (u64, Vec<(u128, u32)>) {
    let bytes = fs::read(path).expect("read rkdb");
    assert!(
        bytes.len() >= 42,
        "rkdb file must carry the 42-byte v2 header"
    );
    assert_eq!(&bytes[0..4], b"RKDB", "frozen RKDB magic");
    assert_eq!(
        u16::from_le_bytes([bytes[4], bytes[5]]),
        2,
        "frozen RKDB version"
    );
    let record_count = u64::from_le_bytes(
        bytes[10..18]
            .try_into()
            .expect("header total_kmers is 8 bytes"),
    );
    let data_offset = u64::from_le_bytes(
        bytes[26..34]
            .try_into()
            .expect("header data_offset is 8 bytes"),
    );
    assert_eq!(data_offset, 42, "the only canonical .rkdb v2 header size");

    let mut records = Vec::new();
    let mut offset = data_offset as usize;
    while offset + 20 <= bytes.len() {
        let key = u128::from_le_bytes(
            bytes[offset..offset + 16]
                .try_into()
                .expect("record key is 16 bytes"),
        );
        let count = u32::from_le_bytes(
            bytes[offset + 16..offset + 20]
                .try_into()
                .expect("record count is 4 bytes"),
        );
        records.push((key, count));
        offset += 20;
    }
    assert_eq!(
        offset,
        bytes.len(),
        "the record parse must land exactly on the file end"
    );
    (record_count, records)
}

/// The sorted `.rkdb` for the committed golden input is byte-identical to the
/// committed pre-refactor fixture.
#[test]
fn sorted_rkdb_output_reproduces_the_committed_k21_canon_golden() {
    let dir = tempfile::tempdir().expect("tempdir for golden output");
    let input = golden_fasta(dir.path());
    let out = dir.path().join("golden-k21-canon-sorted.rkdb");

    let output = run_count(&input, 21, 4, "binary", &out, true, &[]);
    assert_success(&output, "golden k21 canonical sorted");

    let bytes = fs::read(&out).expect("read sorted golden output");
    assert_eq!(
        sha256_hex(&bytes),
        GOLDEN_K21_CANON_SORTED_SHA256,
        "the consuming/par-sorted write path must emit the committed golden bytes"
    );
}

/// Records in a sorted `.rkdb` are strictly ascending by numeric key.
#[test]
fn sorted_rkdb_records_are_strictly_ascending() {
    let dir = tempfile::tempdir().expect("tempdir for ascending check");
    let input = dir.path().join("repeats.fa");
    write_fasta(
        &input,
        &[
            "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
            "ACACACACACACACACACACACACACACACACACACACACACACACACACAC",
            "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACA",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        ],
    );
    let out = dir.path().join("repeats.rkdb");

    let output = run_count(&input, 21, 4, "binary", &out, true, &[]);
    assert_success(&output, "strictly-ascending fixture");

    let (_header_count, records) = read_rkdb(&out);
    assert!(!records.is_empty(), "fixture must produce records");
    assert!(
        records.windows(2).all(|pair| pair[0].0 < pair[1].0),
        "sorted .rkdb records must be strictly ascending by numeric key"
    );
}

/// The header's record count equals the number of records on disk, and the
/// sum of the counts equals the CLI's reported `Total k-mers:` total (IN-03).
#[test]
fn header_record_count_equals_the_number_of_records_on_disk() {
    let dir = tempfile::tempdir().expect("tempdir for header count");
    let input = golden_fasta(dir.path());
    let out = dir.path().join("header-count.rkdb");

    // No `-q`: the reported total is printed on stderr.
    let output = run_count(&input, 21, 4, "binary", &out, false, &[]);
    assert_success(&output, "header record count");

    let stderr = String::from_utf8_lossy(&output.stderr);
    let reported_total: u64 = stderr
        .lines()
        .find_map(|line| line.trim().strip_prefix("Total k-mers: "))
        .expect("a non-quiet run must report `Total k-mers:`")
        .trim()
        .parse()
        .expect("the reported total is numeric");

    let (header_count, records) = read_rkdb(&out);
    assert_eq!(
        header_count,
        records.len() as u64,
        "the header record count must equal the records parsed from disk"
    );
    let sum_of_counts: u64 = records.iter().map(|(_, count)| *count as u64).sum();
    assert_eq!(
        sum_of_counts, reported_total,
        "the sum of the on-disk counts must equal the CLI's reported total"
    );
}

/// `--threads 1` and `--threads 4` produce byte-identical sorted `.rkdb`
/// files (unique keys make the order a strict total order).
#[test]
fn sorted_output_is_byte_identical_across_thread_counts() {
    let dir = tempfile::tempdir().expect("tempdir for thread identity");
    let input = golden_fasta(dir.path());
    let out_t1 = dir.path().join("sorted-t1.rkdb");
    let out_t4 = dir.path().join("sorted-t4.rkdb");

    let t1 = run_count(&input, 21, 1, "binary", &out_t1, true, &[]);
    assert_success(&t1, "sorted t1");
    let t4 = run_count(&input, 21, 4, "binary", &out_t4, true, &[]);
    assert_success(&t4, "sorted t4");

    assert_eq!(
        fs::read(&out_t1).expect("read t1 output"),
        fs::read(&out_t4).expect("read t4 output"),
        "sorted .rkdb bytes must be identical across thread counts"
    );
}

// --- Task 3: numeric-key text order and the order-equivalence proof ---------

/// Parse a `SEQ<TAB>COUNT` text count table; asserts no duplicate sequences.
fn read_text_map(path: &Path) -> BTreeMap<String, u32> {
    let content = fs::read_to_string(path).expect("read text output");
    let mut map = BTreeMap::new();
    for line in content.lines().filter(|line| !line.is_empty()) {
        let (sequence, count) = line
            .split_once('\t')
            .unwrap_or_else(|| panic!("malformed count line: {line:?}"));
        let previous = map.insert(
            sequence.to_string(),
            count.parse::<u32>().expect("numeric count"),
        );
        assert!(
            previous.is_none(),
            "text output repeats the sequence {sequence:?}"
        );
    }
    map
}

/// Re-encode a decoded ACGT sequence to its numeric key.
fn numeric_key(sequence: &str) -> u128 {
    encode_kmer_bytes_u128(sequence.as_bytes()).expect("decoded output is ACGT only")
}

/// The ordering predicate shared by the property test and its control.
fn sequences_are_non_decreasing(sequences: &[String]) -> bool {
    sequences.windows(2).all(|pair| pair[0] <= pair[1])
}

/// Text output is ordered by the numeric encoded key (which equals the
/// lexicographic order of the decoded sequences) for a repeat-rich fixture
/// that also contains an N-bearing record.
#[test]
fn text_output_is_sorted_by_numeric_key() {
    let dir = tempfile::tempdir().expect("tempdir for text order");
    let input = dir.path().join("text-order.fa");
    write_fasta(
        &input,
        &[
            "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
            "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAA",
            "ACGTACGTACGTNACGTACGTACGTACGTACGTACGTACGTACGTACGTA",
            "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAG",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        ],
    );
    let out = dir.path().join("text-order.tsv");

    let output = run_count(&input, 21, 4, "text", &out, true, &[]);
    assert_success(&output, "text numeric order");

    let content = fs::read_to_string(&out).expect("read text output");
    let sequences: Vec<&str> = content
        .lines()
        .filter(|line| !line.is_empty())
        .map(|line| {
            line.split_once('\t')
                .unwrap_or_else(|| panic!("malformed count line: {line:?}"))
                .0
        })
        .collect();
    assert!(!sequences.is_empty(), "fixture must produce k-mers");
    assert!(
        sequences.windows(2).all(|pair| pair[0] <= pair[1]),
        "text output must be lexicographically ascending"
    );
    let numeric: Vec<u128> = sequences.iter().map(|seq| numeric_key(seq)).collect();
    assert!(
        numeric.windows(2).all(|pair| pair[0] < pair[1]),
        "text output must be strictly ascending by numeric key (unique keys)"
    );
}

/// `--threads 1` and `--threads 4` produce byte-identical text output.
#[test]
fn text_output_is_byte_identical_across_thread_counts() {
    let dir = tempfile::tempdir().expect("tempdir for text identity");
    let input = golden_fasta(dir.path());
    let out_t1 = dir.path().join("text-t1.tsv");
    let out_t4 = dir.path().join("text-t4.tsv");

    let t1 = run_count(&input, 21, 1, "text", &out_t1, true, &[]);
    assert_success(&t1, "text t1");
    let t4 = run_count(&input, 21, 4, "text", &out_t4, true, &[]);
    assert_success(&t4, "text t4");

    assert_eq!(
        fs::read(&out_t1).expect("read t1 text"),
        fs::read(&out_t4).expect("read t4 text"),
        "text output bytes must be identical across thread counts"
    );
}

/// The text and binary outputs describe the same sequence -> count map.
#[test]
fn text_and_binary_maps_agree() {
    let dir = tempfile::tempdir().expect("tempdir for map agreement");
    let input = golden_fasta(dir.path());
    let text_out = dir.path().join("maps.tsv");
    let binary_out = dir.path().join("maps.rkdb");

    let text_run = run_count(&input, 21, 4, "text", &text_out, true, &[]);
    assert_success(&text_run, "text map");
    let binary_run = run_count(&input, 21, 4, "binary", &binary_out, true, &[]);
    assert_success(&binary_run, "binary map");

    let text_map = read_text_map(&text_out);
    let (_header_count, records) = read_rkdb(&binary_out);
    let binary_map: BTreeMap<String, u32> = records
        .into_iter()
        .map(|(key, count)| (decode_kmer_u128(key, 21), count))
        .collect();

    assert_eq!(
        text_map, binary_map,
        "text and .rkdb outputs must carry the same sequence -> count map"
    );
}

/// Sorting numerically then decoding yields non-decreasing sequences, and the
/// numeric order is the SAME permutation as sorting the decoded strings, for
/// every supported k in 1..=64 (deterministic seeded key sets).
#[test]
fn numeric_order_equals_decoded_order_for_every_k() {
    for k in 1..=64usize {
        let mask = if k == 64 {
            u128::MAX
        } else {
            (1u128 << (2 * k)) - 1
        };
        let mut state: u64 = 0x9E37_79B9_7F4A_7C15 ^ (k as u64);
        let mut keys: Vec<u128> = Vec::new();
        for _ in 0..256 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            let high = (state as u128) << 64;
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            keys.push((high | state as u128) & mask);
        }
        keys.sort_unstable();
        keys.dedup();
        assert!(
            keys.len() >= 2,
            "k={k}: the seeded generator must produce at least two distinct keys"
        );

        let decoded: Vec<String> = keys.iter().map(|&key| decode_kmer_u128(key, k)).collect();
        assert!(
            sequences_are_non_decreasing(&decoded),
            "k={k}: numeric key order diverged from decoded-sequence order"
        );

        let mut by_string: Vec<(String, u128)> =
            decoded.into_iter().zip(keys.iter().copied()).collect();
        by_string.sort_by(|a, b| a.0.cmp(&b.0));
        let string_order: Vec<u128> = by_string.into_iter().map(|(_, key)| key).collect();
        assert_eq!(
            string_order, keys,
            "k={k}: decoded-string order is a different permutation than numeric order"
        );
    }
}

/// Control: the ordering predicate must be FALSE for a deliberately reversed
/// order, so `numeric_order_equals_decoded_order_for_every_k` cannot pass
/// vacuously. The wrong order is constructed here, never in production code.
#[test]
fn inverted_order_control_fails() {
    let keys: Vec<u128> = (0u128..16).collect();
    let mut decoded: Vec<String> = keys.iter().map(|&key| decode_kmer_u128(key, 4)).collect();
    assert!(
        sequences_are_non_decreasing(&decoded),
        "the forward (numeric) order must satisfy the predicate"
    );
    decoded.reverse();
    assert!(
        !sequences_are_non_decreasing(&decoded),
        "the predicate must reject a reversed order"
    );
}
