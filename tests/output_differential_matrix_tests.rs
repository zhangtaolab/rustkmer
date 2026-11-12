//! OUT-03 old-vs-new and 1-vs-N differential matrix (Phase 8, plan 08-03).
//!
//! The post-refactor output pipeline (consuming pair collection, in-place
//! parallel unstable sort, streaming through the frozen `.rkdb` writer) is only
//! trustworthy if EVERY cell of the k x canonical x threads matrix reproduces
//! the pre-refactor reference algorithm exactly. This binary enumerates the
//! matrix explicitly and, per cell:
//!
//! * builds the old arm with the naive per-window algorithm
//!   (`encode_kmer_bytes_u128` + optional `canonical_kmer_u128`) into a
//!   `BTreeMap<u128, u32>` — an encode error is a skipped window, which is how
//!   the reference represents skip-N semantics;
//! * parses the CLI's text output (run without `-q`, so its statistics lines
//!   are readable) and asserts the map and both reported statistics equal the
//!   reference;
//! * parses the CLI's binary output and asserts the records decode to exactly
//!   the reference map, the keys are strictly ascending, and the record parse
//!   lands exactly on the file end;
//! * asserts the header record count equals the reference map length and the
//!   sum of the record counts equals the reference total;
//! * writes the SAME reference map through the frozen
//!   `RKDatabase::from_kmer_pairs(..).to_file_path(..)` writer and asserts the
//!   old-path bytes equal the new-path bytes;
//! * asserts `--threads 1` and `--threads 4` produced byte-identical binary
//!   and text files.
//!
//! A focused N-semantics test pins the skip-N contract on a random record with
//! one internal `N`: the reference, the text arm, and the binary arm agree, the
//! observed total is exactly the N-free window count, and the distinct-key
//! count is strictly below the naive window count.
//!
//! Task 2 extends this file with the output-boundary disjointness and
//! conservation proptest. Fixtures are generated in temp directories; nothing
//! under `tests/fixtures/` is ever read or written.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use std::process::{Command, Output};

use rustkmer::database::format::RKDatabase;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};

/// Deterministic ACGT base stream (inline LCG) for fixture generation.
fn lcg_bases(len: usize, seed: u64) -> Vec<u8> {
    const BASES: [u8; 4] = *b"ACGT";
    let mut state = seed;
    (0..len)
        .map(|_| {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            BASES[((state >> 33) & 3) as usize]
        })
        .collect()
}

/// The record with one internal `N`, shared by the matrix fixture and the
/// focused N-semantics test. The `N` sits at index 45, far enough from both
/// edges that exactly `k` windows contain it for every k in the matrix.
fn n_bearing_record() -> Vec<u8> {
    let mut record = lcg_bases(90, 0x005E_ED00_0008_0301);
    record[45] = b'N';
    record
}

/// Multi-record fixture: two random records, a period-4 repeat, a repeat-rich
/// record (counts above 1), one lowercase record, one record with an internal
/// `N`, and one record shorter than every k in the matrix.
fn matrix_sequences() -> Vec<Vec<u8>> {
    let lowercase = lcg_bases(96, 0x005E_ED00_0008_0302)
        .iter()
        .map(u8::to_ascii_lowercase)
        .collect();
    vec![
        lcg_bases(180, 0x005E_ED00_0008_0303),
        lcg_bases(120, 0x005E_ED00_0008_0304),
        b"ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT".to_vec(),
        b"AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTT"
            .to_vec(),
        lowercase,
        n_bearing_record(),
        b"ACGT".to_vec(),
    ]
}

/// Write one plain FASTA record per sequence.
fn write_fasta(path: &Path, sequences: &[Vec<u8>]) {
    let mut body = Vec::new();
    for (idx, sequence) in sequences.iter().enumerate() {
        body.extend_from_slice(format!(">seq{idx}\n").as_bytes());
        body.extend_from_slice(sequence);
        body.push(b'\n');
    }
    fs::write(path, body).expect("write FASTA fixture");
}

/// The unchanged per-window reference map: an encode error is a skipped window
/// (this is how the reference implements skip-N), otherwise the encoded (and
/// optionally canonicalized) window is accumulated.
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

/// Decode a reference map to the CLI text-output key space.
fn decode_reference_map(encoded: &BTreeMap<u128, u32>, k: usize) -> BTreeMap<String, u32> {
    encoded
        .iter()
        .map(|(&key, &count)| (decode_kmer_u128(key, k), count))
        .collect()
}

/// Parse the numeric value of every stderr line containing `label`.
fn stderr_values(output: &Output, label: &str) -> Vec<u64> {
    String::from_utf8_lossy(&output.stderr)
        .lines()
        .filter(|line| line.contains(label))
        .map(|line| {
            line.rsplit_once(':')
                .map(|(_, value)| value.trim().parse::<u64>().expect("numeric stat"))
                .unwrap_or_else(|| panic!("malformed stat line: {line:?}"))
        })
        .collect()
}

/// Parse a `SEQ<TAB>COUNT` text count table; asserts no duplicate sequences.
fn read_text_counts(path: &Path) -> BTreeMap<String, u32> {
    let content = fs::read_to_string(path).expect("read text count table");
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

/// Parse a `.rkdb` v2 file: `(header record count, [(key, count)])`.
///
/// Header layout (42 bytes): magic 0..4, version 4..6, kmer size 6,
/// padding 7..10, total_kmers 10..18, flags 18, padding 19..26,
/// data_offset 26..34, index_offset 34..42. Records are 16-byte LE u128 keys
/// plus 4-byte LE u32 counts. Asserts the magic, the version, the canonical
/// data offset, and that the record parse lands EXACTLY on the file end.
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
        "no trailing partial record: the parse must land exactly on the file end"
    );
    (record_count, records)
}

/// Run the real CLI `count` command with the given thread count and format.
fn run_count(
    input: &Path,
    k: usize,
    canonical: bool,
    threads: usize,
    format: &str,
    output: &Path,
    quiet: bool,
) -> Output {
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
        .arg(format);
    if quiet {
        command.arg("-q");
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

/// Write the ascending reference pairs through the frozen canonical writer —
/// the old arm, independent of the refactored counting/output path.
fn write_reference_rkdb(reference: &BTreeMap<u128, u32>, k: usize, canonical: bool, path: &Path) {
    let pairs: Vec<(u128, u32)> = reference
        .iter()
        .map(|(&key, &count)| (key, count))
        .collect();
    let database = RKDatabase::from_kmer_pairs(pairs, k as u8, canonical, true)
        .expect("the frozen writer accepts the reference pairs");
    database
        .to_file_path(path)
        .expect("write the reference .rkdb");
}

/// OUT-03 matrix: k in {21, 32, 64} x canonical in {true, false} x threads in
/// {1, 4}. Every cell must reproduce the pre-refactor reference map exactly in
/// both formats, the old writer arm must be byte-identical to the new path, and
/// the t1/t4 outputs must be byte-identical.
#[test]
fn old_vs_new_matrix_reproduces_the_reference_in_text_and_binary() {
    let dir = tempfile::tempdir().expect("tempdir for the differential matrix");
    let input = dir.path().join("matrix.fa");
    let sequences = matrix_sequences();
    write_fasta(&input, &sequences);
    let borrowed: Vec<&[u8]> = sequences.iter().map(Vec::as_slice).collect();

    let mut cells = 0usize;
    for k in [21usize, 32, 64] {
        for canonical in [true, false] {
            let reference = reference_map(&borrowed, k, canonical);
            assert!(
                !reference.is_empty(),
                "the matrix fixture must produce k-mers (k={k}, canonical={canonical})"
            );
            let reference_total: u64 = reference.values().map(|&count| count as u64).sum();
            assert!(
                reference_total > 0,
                "the reference total must be positive (k={k}, canonical={canonical})"
            );
            let reference_text = decode_reference_map(&reference, k);

            let mut text_bytes: Vec<Vec<u8>> = Vec::new();
            let mut binary_bytes: Vec<Vec<u8>> = Vec::new();
            for threads in [1usize, 4] {
                cells += 1;
                let label = format!("k={k} canonical={canonical} threads={threads}");

                // Text arm — NOT quiet, so `Total k-mers:` / `Unique k-mers:`
                // are printed and can be pinned to the reference.
                let text_out = dir
                    .path()
                    .join(format!("text-k{k}-c{canonical}-t{threads}.tsv"));
                let text_run = run_count(&input, k, canonical, threads, "text", &text_out, false);
                assert_success(&text_run, &format!("{label}, text format"));
                let totals = stderr_values(&text_run, "Total k-mers:");
                let uniques = stderr_values(&text_run, "Unique k-mers:");
                assert_eq!(
                    totals.len(),
                    1,
                    "{label}: the non-quiet run must report exactly one `Total k-mers:` line, \
                     got {totals:?}"
                );
                assert_eq!(
                    totals[0], reference_total,
                    "{label}: the reported total must equal the reference count sum"
                );
                assert_eq!(
                    uniques.len(),
                    1,
                    "{label}: the non-quiet run must report exactly one `Unique k-mers:` line, \
                     got {uniques:?}"
                );
                assert_eq!(
                    uniques[0],
                    reference.len() as u64,
                    "{label}: the reported unique count must equal the reference distinct keys"
                );
                let got_text = read_text_counts(&text_out);
                assert_eq!(
                    got_text, reference_text,
                    "{label}: the text map diverged from the pre-refactor reference"
                );
                text_bytes.push(fs::read(&text_out).expect("read text output"));

                // Binary arm — quiet, and parsed back record by record.
                let binary_out = dir
                    .path()
                    .join(format!("binary-k{k}-c{canonical}-t{threads}.rkdb"));
                let binary_run =
                    run_count(&input, k, canonical, threads, "binary", &binary_out, true);
                assert_success(&binary_run, &format!("{label}, binary format"));
                let (header_count, records) = read_rkdb(&binary_out);
                assert_eq!(
                    header_count,
                    reference.len() as u64,
                    "{label}: the header record count must equal the reference distinct keys"
                );
                assert_eq!(
                    records.len(),
                    reference.len(),
                    "{label}: the binary file must hold exactly one record per reference key \
                     (duplicates or lost keys are failures)"
                );
                let sum_of_counts: u64 = records.iter().map(|(_, count)| *count as u64).sum();
                assert_eq!(
                    sum_of_counts, reference_total,
                    "{label}: the sum of the on-disk counts must equal the reference total"
                );
                assert!(
                    records.windows(2).all(|pair| pair[0].0 < pair[1].0),
                    "{label}: sorted records must be strictly ascending by numeric key"
                );
                let got_binary: BTreeMap<u128, u32> = records.iter().copied().collect();
                assert_eq!(
                    got_binary, reference,
                    "{label}: the binary map diverged from the pre-refactor reference"
                );
                let new_bytes = fs::read(&binary_out).expect("read binary output");

                // Old arm — the same reference pairs through the frozen writer.
                let old_out = dir
                    .path()
                    .join(format!("old-k{k}-c{canonical}-t{threads}.rkdb"));
                write_reference_rkdb(&reference, k, canonical, &old_out);
                assert_eq!(
                    new_bytes,
                    fs::read(&old_out).expect("read old-arm output"),
                    "{label}: the old writer arm and the new output path must be byte-identical"
                );
                binary_bytes.push(new_bytes);
            }

            assert_eq!(
                text_bytes[0], text_bytes[1],
                "k={k} canonical={canonical}: threads=1 and threads=4 text output must be \
                 byte-identical"
            );
            assert_eq!(
                binary_bytes[0], binary_bytes[1],
                "k={k} canonical={canonical}: threads=1 and threads=4 binary output must be \
                 byte-identical"
            );
        }
    }

    assert_eq!(
        cells, 12,
        "the matrix must exercise exactly 12 cells (3 k values x 2 canonical modes x 2 thread \
         counts); a narrowed matrix is a blind spot"
    );
}

/// Focused skip-N semantics: for a random record with one internal `N`, the
/// reference (encode errors are skipped windows) and both CLI formats agree,
/// the total is exactly the N-free window count, and the distinct-key count is
/// strictly below the naive window count — so a regression that starts counting
/// N-bearing windows cannot pass.
#[test]
fn n_containing_record_skips_exactly_the_windows_that_cover_the_n() {
    let record = n_bearing_record();
    let dir = tempfile::tempdir().expect("tempdir for the N-semantics fixture");
    let input = dir.path().join("n-record.fa");
    write_fasta(&input, std::slice::from_ref(&record));

    for k in [21usize, 32] {
        let reference = reference_map(&[record.as_slice()], k, true);
        let naive_windows = (record.len() - k + 1) as u64;
        // The N is at index 45, at least k-1 bases from both ends, so exactly
        // k naive windows cover it.
        let valueless_windows = k as u64;
        let n_free_windows = naive_windows - valueless_windows;

        assert!(
            !reference.is_empty(),
            "k={k}: the N-free windows must produce k-mers, otherwise this arm is vacuous"
        );
        assert_eq!(
            reference.values().map(|&count| count as u64).sum::<u64>(),
            n_free_windows,
            "k={k}: the observed total must be exactly the N-free window count"
        );
        assert!(
            (reference.len() as u64) < naive_windows,
            "k={k}: the distinct-key count must be strictly below the naive window count"
        );

        let reference_text = decode_reference_map(&reference, k);

        let text_out = dir.path().join(format!("n-record-k{k}.tsv"));
        let text_run = run_count(&input, k, true, 4, "text", &text_out, true);
        assert_success(&text_run, &format!("k={k}, N-record text"));
        assert_eq!(
            read_text_counts(&text_out),
            reference_text,
            "k={k}: the text arm must skip exactly the N-bearing windows"
        );

        let binary_out = dir.path().join(format!("n-record-k{k}.rkdb"));
        let binary_run = run_count(&input, k, true, 4, "binary", &binary_out, true);
        assert_success(&binary_run, &format!("k={k}, N-record binary"));
        let (header_count, records) = read_rkdb(&binary_out);
        assert_eq!(
            header_count,
            reference.len() as u64,
            "k={k}: the header record count must equal the N-free distinct keys"
        );
        assert_eq!(
            records.iter().copied().collect::<BTreeMap<u128, u32>>(),
            reference,
            "k={k}: the binary arm must skip exactly the N-bearing windows"
        );
        assert!(
            records.windows(2).all(|pair| pair[0].0 < pair[1].0),
            "k={k}: the N-record output must still be strictly ascending"
        );
    }
}
