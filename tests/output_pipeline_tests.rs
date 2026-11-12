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

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

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
fn run_count(
    input: &Path,
    k: usize,
    canonical: bool,
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
        .arg("--threads")
        .arg(threads.to_string())
        .arg("-o")
        .arg(out)
        .arg("--format")
        .arg(format);
    if canonical {
        command.arg("-C");
    }
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

    let output = run_count(&input, 21, true, 4, "binary", &out, true, &[]);
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

    let output = run_count(&input, 21, true, 4, "binary", &out, true, &[]);
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
    let output = run_count(&input, 21, true, 4, "binary", &out, false, &[]);
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

    let t1 = run_count(&input, 21, true, 1, "binary", &out_t1, true, &[]);
    assert_success(&t1, "sorted t1");
    let t4 = run_count(&input, 21, true, 4, "binary", &out_t4, true, &[]);
    assert_success(&t4, "sorted t4");

    assert_eq!(
        fs::read(&out_t1).expect("read t1 output"),
        fs::read(&out_t4).expect("read t4 output"),
        "sorted .rkdb bytes must be identical across thread counts"
    );
}
