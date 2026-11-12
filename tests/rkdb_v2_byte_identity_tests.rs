//! OUT-02 — `.rkdb` v2 byte-identity for the new counting output path
//! (Phase 8, plan 08-02, Task 1).
//!
//! The Phase 5 goldens are the contract. Before this binary existed they were
//! only re-hashed, so a drift in the counting write path that happened to leave
//! the committed fixtures alone would go unnoticed. Here the same literal input
//! is counted by the real CLI, written by the new sort/stream path, and
//! compared byte-for-byte against three independent references:
//!
//! | Arm | Source | Independent of the code under test? |
//! |---|---|---|
//! | 1 | the real `rustkmer count` binary (t1 and t4) | no — this is the code under test |
//! | 2 | the committed pre-refactor fixture bytes in `tests/fixtures/` | yes — captured before the refactor, never regenerated |
//! | 3 | the frozen `RKDatabase::from_kmer_pairs(..).to_file_path(..)` writer | partly — `format.rs` is frozen and not the refactored path |
//! | 4 | a hand-built 16-byte-LE-key + 4-byte-LE-count data section | yes — the oracle's bytes with no production call in between |
//!
//! For all six sorted cells (k ∈ {21, 32, 64} × canonical on/off) the first
//! three whole-file arms must be pairwise sha256-equal, and arm 4 must equal the
//! new path's bytes after the frozen 42-byte header. For the six unsorted cells
//! only the record multiset and totals are asserted — never byte order — under a
//! header whose sorted flag is false.
//!
//! Sortedness is proven by ANSWERS, not by the header flag, in Task 2 of this
//! plan: both binary-search consumers are driven from the files produced here.
//!
//! Fixture integrity: the manifest's sha256 is pinned (`f010e42a…`), every one
//! of the 12 fixtures is re-hashed against its entry, and every write in this
//! binary is guarded to land outside `tests/fixtures/`. No generator is ever
//! invoked and no fixture is written or regenerated.
//!
//! IN-03: the 42-byte header's `total_kmers` is the RECORD COUNT, not the sum
//! of the records' counts. The distinction is asserted on the repeat-rich
//! golden input, where the two numbers differ, so an inverted meaning cannot
//! pass.

use std::collections::BTreeMap;
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use anyhow::{anyhow, bail, Context, Result};
use rustkmer::database::format::{DatabaseHeader, RKDatabase};
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};
use sha2::{Digest, Sha256};
use tempfile::TempDir;

/// The fixed golden input — MUST match `tests/golden_generate.rs::GOLDEN_INPUT`
/// and `tests/output_pipeline_tests.rs`, otherwise the compared k-mer sets
/// differ and the byte-identity claim is meaningless.
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// `.rkdb` v2 header length in bytes (magic 4 + version 2 + kmer_size 1 +
/// padding 3 + total_kmers 8 + flags 1 + padding 7 + data_offset 8 +
/// index_offset 8). Pinned here so a header that grows moves the data section
/// loudly instead of silently shifting the bytes this binary inspects.
const RKDB_V2_HEADER_BYTES: usize = 42;

/// Byte length of one `.rkdb` v2 record: 16-byte LE `u128` key + 4-byte LE
/// `u32` count.
const RKDB_V2_RECORD_BYTES: usize = 20;

/// sha256 of `tests/fixtures/golden_manifest.sha256` as committed (T-08-06).
/// A change here means the fixture contract moved and must fail loudly.
const GOLDEN_MANIFEST_SHA256: &str =
    "f010e42a213de6786ac67e2a6f9227485320e7ddfca4c6521cf019880786f25f";

/// The 12 committed golden fixtures (six sorted byte contract + six unsorted
/// content cells).
const GOLDEN_FIXTURES: &[&str] = &[
    "golden_k21_canon_sorted.rkdb",
    "golden_k21_canon_unsorted.rkdb",
    "golden_k21_noncanon_sorted.rkdb",
    "golden_k21_noncanon_unsorted.rkdb",
    "golden_k32_canon_sorted.rkdb",
    "golden_k32_canon_unsorted.rkdb",
    "golden_k32_noncanon_sorted.rkdb",
    "golden_k32_noncanon_unsorted.rkdb",
    "golden_k64_canon_sorted.rkdb",
    "golden_k64_canon_unsorted.rkdb",
    "golden_k64_noncanon_sorted.rkdb",
    "golden_k64_noncanon_unsorted.rkdb",
];

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Guard: every write in this binary must land in a `TempDir`. A path under
/// `tests/fixtures/` would violate T-08-06 (the goldens are never regenerated),
/// so it is a hard failure rather than a comment.
fn assert_not_fixture_path(path: &Path) {
    assert!(
        !path.starts_with(Path::new("tests/fixtures")),
        "this test binary must never write under tests/fixtures/ (got {})",
        path.display()
    );
}

/// Write a plain FASTA file (one record per sequence) into `dir`.
fn write_fasta(dir: &Path, file_name: &str, sequences: &[&str]) -> PathBuf {
    let path = dir.join(file_name);
    assert_not_fixture_path(&path);
    let mut body = String::new();
    for (index, sequence) in sequences.iter().enumerate() {
        body.push_str(&format!(">seq{index}\n{sequence}\n"));
    }
    fs::write(&path, body).expect("write FASTA fixture");
    path
}

/// The golden input written to a temp FASTA (never `tests/fixtures/`).
fn golden_fasta(dir: &Path) -> PathBuf {
    write_fasta(dir, "golden_input.fa", GOLDEN_INPUT)
}

/// Run the real CLI `count` command.
///
/// `canonical` toggles `-C`; `sort` false adds `--no-sort`; `-q` keeps stderr
/// empty so a failing run's stderr is the only thing in the assertion message.
fn run_count(
    input: &Path,
    k: usize,
    canonical: bool,
    sort: bool,
    threads: usize,
    out: &Path,
) -> Output {
    assert_not_fixture_path(out);
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
        .arg("-q");
    if canonical {
        command.arg("-C");
    }
    if !sort {
        command.arg("--no-sort");
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

/// Describe where two blobs first differ, for an assertion message that is
/// actionable on its own. A silent byte drift is exactly the failure this
/// binary exists to catch, and a bare `assert_eq!` on two byte walls would not
/// say which arm moved.
fn describe_difference(produced: &[u8], reference: &[u8], section: &str) -> String {
    let shared = produced.len().min(reference.len());
    for (offset, (left, right)) in produced[..shared]
        .iter()
        .zip(reference[..shared].iter())
        .enumerate()
    {
        if left != right {
            return format!(
                "first difference at {section} byte {offset}: left arm 0x{left:02x}, \
                 right arm 0x{right:02x} (left arm {} bytes, right arm {} bytes)",
                produced.len(),
                reference.len()
            );
        }
    }
    format!(
        "the shared {shared}-byte prefix of the {section} is identical but the arms have \
         different lengths: left arm {} bytes, right arm {} bytes",
        produced.len(),
        reference.len()
    )
}

/// Assert two whole files are byte-identical, reporting the first differing
/// offset rather than two hex walls.
fn assert_whole_file_equal(
    left: &[u8],
    right: &[u8],
    left_label: &str,
    right_label: &str,
    context: &str,
) {
    let left_sha = sha256_hex(left);
    let right_sha = sha256_hex(right);
    assert!(
        left_sha == right_sha,
        "{context}: {left_label} ({left_sha}) and {right_label} ({right_sha}) are not \
         byte-identical\n{}",
        describe_difference(left, right, "whole-file")
    );
}

/// A parsed `.rkdb` v2 file: the header plus every record in file order.
struct ParsedRkdb {
    header: DatabaseHeader,
    records: Vec<(u128, u32)>,
}

/// Parse a `.rkdb` v2 file. Asserts the record stream is a whole number of
/// 20-byte records — a trailing partial record is corruption, never data.
fn parse_rkdb(path: &Path) -> Result<ParsedRkdb> {
    let bytes = fs::read(path).with_context(|| format!("read {}", path.display()))?;
    let (header, records) =
        parse_rkdb_bytes(&bytes).with_context(|| format!("parse {}", path.display()))?;
    Ok(ParsedRkdb { header, records })
}

fn parse_rkdb_bytes(bytes: &[u8]) -> Result<(DatabaseHeader, Vec<(u128, u32)>)> {
    if bytes.len() < RKDB_V2_HEADER_BYTES {
        bail!(
            "file is {} bytes — too short to hold a {RKDB_V2_HEADER_BYTES}-byte header",
            bytes.len()
        );
    }
    let header = DatabaseHeader::read_from(&mut Cursor::new(bytes))
        .map_err(|error| anyhow!("failed to read the v2 header: {error}"))?;
    if header.data_offset != RKDB_V2_HEADER_BYTES as u64 {
        bail!(
            "header data_offset is {} (expected {RKDB_V2_HEADER_BYTES})",
            header.data_offset
        );
    }
    let body = &bytes[RKDB_V2_HEADER_BYTES..];
    if body.len() % RKDB_V2_RECORD_BYTES != 0 {
        bail!(
            "data section is {} bytes, not a whole number of {RKDB_V2_RECORD_BYTES}-byte \
             records — trailing partial record",
            body.len()
        );
    }
    let records = body
        .chunks_exact(RKDB_V2_RECORD_BYTES)
        .map(|record| {
            let kmer = u128::from_le_bytes(record[..16].try_into().expect("16-byte key"));
            let count = u32::from_le_bytes(record[16..].try_into().expect("4-byte count"));
            (kmer, count)
        })
        .collect();
    Ok((header, records))
}

/// Build the independent oracle: for every sequence and every naive k-window,
/// encode the window and canonicalize it when the cell is canonical, summing
/// into a `BTreeMap` (ascending numeric key order for free).
///
/// This is the pre-refactor algorithm from `tests/golden_generate.rs` — it
/// never touches the counting engine, the pair collector, or the writer.
fn build_oracle(sequences: &[&str], k: usize, canonical: bool) -> Result<BTreeMap<u128, u32>> {
    let mut oracle: BTreeMap<u128, u32> = BTreeMap::new();
    for sequence in sequences {
        for (window_index, window) in sequence.as_bytes().windows(k).enumerate() {
            let encoded = encode_kmer_bytes_u128(window).with_context(|| {
                format!("encode the k={k} window at offset {window_index} of {sequence}")
            })?;
            let key = if canonical {
                canonical_kmer_u128(encoded, k).map_err(|error| anyhow!("canonicalize: {error}"))?
            } else {
                encoded
            };
            *oracle.entry(key).or_insert(0) += 1;
        }
    }
    Ok(oracle)
}

/// Ascending-by-key oracle pairs, the exact order a sorted `.rkdb` stores.
fn oracle_pairs(oracle: &BTreeMap<u128, u32>) -> Vec<(u128, u32)> {
    oracle.iter().map(|(&kmer, &count)| (kmer, count)).collect()
}

/// The hand-built data section: each oracle record as 16-byte LE key then
/// 4-byte LE count, ascending. No production call sits between the oracle and
/// these bytes — that is what makes this arm a reference (T-08-09).
fn hand_built_data_section(oracle: &BTreeMap<u128, u32>) -> Vec<u8> {
    let mut out = Vec::with_capacity(oracle.len() * RKDB_V2_RECORD_BYTES);
    for (&kmer, &count) in oracle {
        out.extend_from_slice(&kmer.to_le_bytes());
        out.extend_from_slice(&count.to_le_bytes());
    }
    out
}

fn cell_fixture_name(k: usize, canonical: bool, sorted: bool) -> String {
    format!(
        "golden_k{}_{}_{}.rkdb",
        k,
        if canonical { "canon" } else { "noncanon" },
        if sorted { "sorted" } else { "unsorted" }
    )
}

/// Read a committed fixture. This function only reads — the goldens are never
/// written, regenerated, or updated (T-08-06).
fn read_fixture(name: &str) -> Result<Vec<u8>> {
    let path = Path::new("tests/fixtures").join(name);
    fs::read(&path).with_context(|| format!("read committed fixture {}", path.display()))
}

/// Parse `tests/fixtures/golden_manifest.sha256` into a name -> hex map.
fn load_manifest() -> Result<BTreeMap<String, String>> {
    let text = fs::read_to_string("tests/fixtures/golden_manifest.sha256")
        .context("failed to read golden_manifest.sha256")?;
    let mut manifest = BTreeMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let mut parts = line.split_whitespace();
        let name = parts
            .next()
            .ok_or_else(|| anyhow!("manifest line missing name: {line:?}"))?;
        let hex = parts
            .next()
            .ok_or_else(|| anyhow!("manifest line missing sha256: {line:?}"))?;
        manifest.insert(name.to_string(), hex.to_string());
    }
    Ok(manifest)
}

// ---------------------------------------------------------------------------
// Task 1 — four-arm byte differential, unsorted content cells, fixture
// integrity, and the IN-03 record-count meaning
// ---------------------------------------------------------------------------

/// Six sorted cells: the new CLI bytes equal the committed pre-refactor
/// fixture, the frozen canonical writer, and the hand-built data section.
#[test]
fn new_count_path_matches_all_six_committed_sorted_goldens() -> Result<()> {
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            let dir = TempDir::new()?;
            let input = golden_fasta(dir.path());
            let oracle = build_oracle(GOLDEN_INPUT, k, canonical)?;
            let cell = format!(
                "k={k} canonical={canonical} sorted=true ({})",
                cell_fixture_name(k, canonical, true)
            );

            // Arm 1 — the real CLI, at two thread counts.
            let out_t1 = dir.path().join("new-path-t1.rkdb");
            let out_t4 = dir.path().join("new-path-t4.rkdb");
            let run_t1 = run_count(&input, k, canonical, true, 1, &out_t1);
            assert_success(&run_t1, &format!("{cell}, threads=1"));
            let run_t4 = run_count(&input, k, canonical, true, 4, &out_t4);
            assert_success(&run_t4, &format!("{cell}, threads=4"));
            let new_t1 = fs::read(&out_t1).context("read t1 output")?;
            let new_t4 = fs::read(&out_t4).context("read t4 output")?;
            assert_whole_file_equal(
                &new_t1,
                &new_t4,
                "new path at threads=1",
                "new path at threads=4",
                &format!("{cell}: the sorted output must be thread-count independent"),
            );

            // Arm 2 — the committed pre-refactor fixture.
            let fixture = read_fixture(&cell_fixture_name(k, canonical, true))?;

            // Arm 3 — the frozen canonical writer.
            let frozen_path = dir.path().join("frozen-writer.rkdb");
            let frozen_db =
                RKDatabase::from_kmer_pairs(oracle_pairs(&oracle), k as u8, canonical, true)?;
            frozen_db.to_file_path(&frozen_path)?;
            let frozen = fs::read(&frozen_path).context("read frozen-writer output")?;

            // Whole-file arms 1/2/3 must be pairwise sha256-equal.
            assert_whole_file_equal(
                &new_t4,
                &fixture,
                "new CLI path",
                "committed pre-refactor fixture",
                &format!(
                    "{cell}: write-path drift — the new path no longer emits the golden bytes"
                ),
            );
            assert_whole_file_equal(
                &new_t4,
                &frozen,
                "new CLI path",
                "frozen RKDatabase::from_kmer_pairs writer",
                &format!("{cell}: the new CLI path diverged from the frozen format.rs writer"),
            );
            assert_whole_file_equal(
                &fixture,
                &frozen,
                "committed pre-refactor fixture",
                "frozen RKDatabase::from_kmer_pairs writer",
                &format!("{cell}: the committed fixture and the frozen writer disagree"),
            );

            // Arm 4 — hand-built data section, compared after the frozen header.
            let hand_built = hand_built_data_section(&oracle);
            let new_data = &new_t4[RKDB_V2_HEADER_BYTES..];
            assert!(
                new_data == hand_built.as_slice(),
                "{cell}: the new path's data section differs from the hand-built oracle bytes\n{}",
                describe_difference(new_data, &hand_built, "data-section")
            );
        }
    }
    Ok(())
}

/// Six unsorted cells: same record multiset, same totals, under a header whose
/// sorted flag is false. Byte order is deliberately NOT asserted.
#[test]
fn unsorted_cells_carry_the_same_record_multiset() -> Result<()> {
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            let dir = TempDir::new()?;
            let input = golden_fasta(dir.path());
            let oracle = build_oracle(GOLDEN_INPUT, k, canonical)?;
            let cell = format!(
                "k={k} canonical={canonical} sorted=false ({})",
                cell_fixture_name(k, canonical, false)
            );

            let out = dir.path().join("new-path-unsorted.rkdb");
            let run = run_count(&input, k, canonical, false, 4, &out);
            assert_success(&run, &cell);
            let parsed = parse_rkdb(&out).with_context(|| format!("{cell}: parse output"))?;

            assert!(
                !parsed.header.sorted,
                "{cell}: a --no-sort run must write sorted=false into the header"
            );
            assert_eq!(
                parsed.header.canonical, canonical,
                "{cell}: the header canonical flag must match the run"
            );
            assert_eq!(
                parsed.header.total_kmers,
                oracle.len() as u64,
                "{cell}: IN-03 — header total_kmers is the RECORD COUNT, i.e. the number of \
                 distinct k-mers, not the sum of their counts"
            );
            assert_eq!(
                parsed.records.len(),
                oracle.len(),
                "{cell}: the unsorted file must hold exactly the oracle's distinct k-mers"
            );

            // Multiset of (decoded sequence, count), compared as sorted vectors
            // so a duplicated record cannot hide inside a map.
            let mut observed: Vec<(String, u32)> = parsed
                .records
                .iter()
                .map(|&(kmer, count)| (decode_kmer_u128(kmer, k), count))
                .collect();
            observed.sort();
            let mut expected: Vec<(String, u32)> = oracle
                .iter()
                .map(|(&kmer, &count)| (decode_kmer_u128(kmer, k), count))
                .collect();
            expected.sort();
            assert_eq!(
                observed, expected,
                "{cell}: the unsorted record multiset (decoded sequence, count) must equal the \
                 oracle's"
            );

            let observed_sum: u64 = parsed.records.iter().map(|&(_, count)| count as u64).sum();
            let oracle_sum: u64 = oracle.values().map(|&count| count as u64).sum();
            assert_eq!(
                observed_sum, oracle_sum,
                "{cell}: the sum of the unsorted records' counts must equal the oracle total"
            );
        }
    }
    Ok(())
}

/// T-08-06: the manifest is pinned by hash, every fixture matches its entry,
/// and no code path in this binary writes under `tests/fixtures/`.
#[test]
fn golden_manifest_hash_and_fixtures_are_unmodified() -> Result<()> {
    // `read_fixture` is the only way this binary touches the fixtures and it
    // only calls `fs::read`; every write goes through `assert_not_fixture_path`.
    let manifest_bytes =
        fs::read("tests/fixtures/golden_manifest.sha256").context("read golden_manifest.sha256")?;
    assert_eq!(
        sha256_hex(&manifest_bytes),
        GOLDEN_MANIFEST_SHA256,
        "the golden manifest itself changed — the fixture contract is immutable; revert the drift \
         instead of re-pinning this hash"
    );

    let manifest = load_manifest()?;
    assert_eq!(
        manifest.len(),
        GOLDEN_FIXTURES.len(),
        "the manifest must cover exactly the {} golden fixtures",
        GOLDEN_FIXTURES.len()
    );
    for name in GOLDEN_FIXTURES {
        let expected = manifest.get(*name).ok_or_else(|| {
            anyhow!("golden fixture {name:?} is not present in golden_manifest.sha256")
        })?;
        let actual = sha256_hex(&read_fixture(name)?);
        assert_eq!(
            actual, *expected,
            "golden sha256 mismatch for {name}: committed bytes drifted from the pre-refactor \
             baseline — the goldens must never be regenerated to make a diff green"
        );
    }
    Ok(())
}

/// IN-03: on the repeat-rich golden input, the header's `total_kmers` is the
/// record count and the sum of counts is a different, larger number — so an
/// inverted meaning cannot pass.
#[test]
fn record_count_and_sum_of_counts_have_distinct_meaning() -> Result<()> {
    const K: usize = 21;
    let canonical = true;
    let dir = TempDir::new()?;
    let input = golden_fasta(dir.path());
    let oracle = build_oracle(GOLDEN_INPUT, K, canonical)?;

    let out = dir.path().join("in03-header-meaning.rkdb");
    let run = run_count(&input, K, canonical, true, 4, &out);
    assert_success(&run, "IN-03 k=21 canonical sorted");
    let parsed = parse_rkdb(&out)?;

    let record_count = oracle.len() as u64;
    let sum_of_counts: u64 = oracle.values().map(|&count| count as u64).sum();
    assert_ne!(
        record_count, sum_of_counts,
        "IN-03 fixture premise: the golden input must make the record count and the sum of counts \
         differ, otherwise the two meanings cannot be distinguished"
    );

    assert_eq!(
        parsed.header.total_kmers, record_count,
        "IN-03: header total_kmers must be the RECORD COUNT ({record_count}), not the sum of \
         counts ({sum_of_counts})"
    );
    assert_eq!(
        parsed.records.len() as u64,
        record_count,
        "IN-03: the on-disk record count must equal the oracle's distinct-k-mer count"
    );
    let on_disk_sum: u64 = parsed.records.iter().map(|&(_, count)| count as u64).sum();
    assert_eq!(
        on_disk_sum, sum_of_counts,
        "IN-03: the sum of the records' counts must equal the oracle's total observations \
         ({sum_of_counts})"
    );
    Ok(())
}
