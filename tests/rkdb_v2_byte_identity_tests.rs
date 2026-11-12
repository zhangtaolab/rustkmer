//! OUT-02 — `.rkdb` v2 byte-identity for the new counting output path, and
//! sortedness proven through BOTH binary-search consumers (Phase 8, plan 08-02).
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
//! Sortedness is then proven by ANSWERS, not by the header flag (the v1.0
//! CR-02 precedent): `DatabaseQuery` binary-searches the disk file and the
//! preloaded vector, and `extract_prefix_optimized` returns exact oracle
//! subsets with exact contiguous block bounds. The negative control is an
//! unsorted `--no-sort` file: disk binary search must refuse with a named
//! unsorted-database error rather than answer wrongly, while the preloaded
//! linear route still answers the full oracle.
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

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use anyhow::{anyhow, bail, Context, Result};
use rustkmer::database::format::{DatabaseHeader, RKDatabase};
use rustkmer::database::prefix_query_optimized::extract_prefix_optimized;
use rustkmer::database::query::DatabaseQuery;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128, reverse_complement_u128};
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

/// Consumer-fixture k-mer size (the production target).
const CONSUMER_K: usize = 21;

/// Consumer-fixture sequence length. Comfortably above 500 sampled keys plus
/// 200 absent candidates, and small enough that the whole binary stays fast.
const CONSUMER_BASES: usize = 20_000;

/// Seed for the deterministic inline LCG that builds the consumer fixture. The
/// sequence must be reproducible across machines, so no OS PRNG is used.
const CONSUMER_SEED: u64 = 0x005E_ED00_0008_0201;

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

// ---------------------------------------------------------------------------
// Task 2 — both binary-search consumers and the frozen header literals
// ---------------------------------------------------------------------------

/// Deterministic inline LCG. No external crates and no OS PRNG, so the
/// consumer fixture is identical on every machine and every run.
fn next_lcg_state(state: &mut u64) -> u64 {
    *state = state
        .wrapping_mul(6_364_136_223_846_793_005)
        .wrapping_add(1_442_695_040_888_963_407);
    *state
}

/// A deterministic pseudo-random ACGT sequence of `length` bases.
fn pseudo_random_acgt(length: usize, seed: u64) -> String {
    let mut state = seed;
    let mut sequence = String::with_capacity(length);
    for _ in 0..length {
        let value = next_lcg_state(&mut state);
        let base = match (value >> 62) & 0b11 {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            _ => 'T',
        };
        sequence.push(base);
    }
    sequence
}

/// The 20,000-base consumer fixture written as ONE FASTA record, plus the
/// oracle built from the same sequence with the reference algorithm.
fn consumer_fixture(dir: &Path) -> Result<(PathBuf, BTreeMap<u128, u32>)> {
    let sequence = pseudo_random_acgt(CONSUMER_BASES, CONSUMER_SEED);
    let input = write_fasta(dir, "consumer_random.fa", &[sequence.as_str()]);
    let oracle = build_oracle(&[sequence.as_str()], CONSUMER_K, true)?;
    Ok((input, oracle))
}

/// Run the new CLI path at threads 1 and 4 into two temp files; return both
/// byte blobs (they must be identical).
fn run_consumer_fixture(input: &Path, dir: &Path) -> Result<(Vec<u8>, Vec<u8>)> {
    let out_t1 = dir.join("consumer-t1.rkdb");
    let out_t4 = dir.join("consumer-t4.rkdb");
    let t1 = run_count(input, CONSUMER_K, true, true, 1, &out_t1);
    assert_success(&t1, "consumer fixture, threads=1");
    let t4 = run_count(input, CONSUMER_K, true, true, 4, &out_t4);
    assert_success(&t4, "consumer fixture, threads=4");
    Ok((
        fs::read(&out_t1).context("read consumer t1 output")?,
        fs::read(&out_t4).context("read consumer t4 output")?,
    ))
}

/// Sample `sample` evenly spaced keys from an ascending key list.
fn sample_keys(keys: &[u128], sample: usize) -> Vec<u128> {
    assert!(
        keys.len() >= sample,
        "the oracle must hold at least {sample} keys to sample deterministically, got {}",
        keys.len()
    );
    (0..sample)
        .map(|index| keys[index * keys.len() / sample])
        .collect()
}

/// Build `count` valid k-mers whose CANONICAL form is absent from the oracle.
/// Queries go through the canonicalizing `query_kmer`, so absence of the
/// canonical form is the property that must hold.
fn absent_query_keys(oracle: &BTreeMap<u128, u32>, k: usize, count: usize) -> Vec<String> {
    let mask = if 2 * k >= 128 {
        u128::MAX
    } else {
        (1u128 << (2 * k)) - 1
    };
    let mut state = 0x00D1_5EA5_E0F0_1234u64;
    let mut seen: BTreeSet<u128> = BTreeSet::new();
    let mut absent = Vec::with_capacity(count);
    while absent.len() < count {
        let high = next_lcg_state(&mut state) as u128;
        let low = next_lcg_state(&mut state) as u128;
        let raw = ((high << 64) | low) & mask;
        let canonical =
            canonical_kmer_u128(raw, k).expect("a masked 2k-bit value is a valid k-mer");
        if oracle.contains_key(&canonical) || !seen.insert(canonical) {
            continue;
        }
        absent.push(decode_kmer_u128(raw, k));
    }
    absent
}

/// The exact contiguous block a prefix selects in the ascending oracle list:
/// `start_index` is the first matching index, `end_index` one past the last
/// matching index, and for a no-match prefix both are the insertion point.
struct ExpectedPrefixBlock {
    start_index: usize,
    end_index: usize,
    matches: Vec<(String, u64)>,
}

fn expected_prefix_block(
    oracle_pairs: &[(u128, u32)],
    prefix: &str,
    k: usize,
) -> ExpectedPrefixBlock {
    let mut matches = Vec::new();
    let mut first_match: Option<usize> = None;
    let mut end_index = 0usize;
    let mut insertion_index: Option<usize> = None;

    for (index, &(kmer, count)) in oracle_pairs.iter().enumerate() {
        let decoded = decode_kmer_u128(kmer, k);
        if decoded.starts_with(prefix) {
            if first_match.is_none() {
                first_match = Some(index);
            }
            end_index = index + 1;
            matches.push((decoded, count as u64));
        } else if insertion_index.is_none() && decoded.as_str() > prefix {
            insertion_index = Some(index);
        }
    }

    let (start_index, end_index) = match first_match {
        Some(start) => (start, end_index),
        None => {
            let insertion = insertion_index.unwrap_or(oracle_pairs.len());
            (insertion, insertion)
        }
    };
    ExpectedPrefixBlock {
        start_index,
        end_index,
        matches,
    }
}

/// Eight prefix cases: four single bases, one 3-base and one 10-base prefix
/// taken from existing keys, one full-length key, and one prefix with no
/// matches. Order: A, C, G, T, 3-base, 10-base, full-length, no-match.
fn prefix_cases(oracle_pairs: &[(u128, u32)], k: usize) -> Vec<String> {
    assert!(
        oracle_pairs.len() >= 3,
        "the consumer oracle must hold at least three keys to derive prefix cases"
    );
    let middle = decode_kmer_u128(oracle_pairs[oracle_pairs.len() / 2].0, k);
    let third = decode_kmer_u128(oracle_pairs[oracle_pairs.len() / 3].0, k);

    let mut cases = vec![
        "A".to_string(),
        "C".to_string(),
        "G".to_string(),
        "T".to_string(),
        middle[..3].to_string(),
        third[..10].to_string(),
        middle,
    ];
    cases.push(no_match_prefix(oracle_pairs, k));
    cases
}

/// Find a deterministic 10-base ACGT prefix that matches no oracle key.
fn no_match_prefix(oracle_pairs: &[(u128, u32)], k: usize) -> String {
    const PREFIX_LEN: usize = 10;
    let decoded: Vec<String> = oracle_pairs
        .iter()
        .map(|&(kmer, _)| decode_kmer_u128(kmer, k))
        .collect();
    for candidate in 0u32..(1u32 << (2 * PREFIX_LEN)) {
        let mut prefix = String::with_capacity(PREFIX_LEN);
        for shift in (0..PREFIX_LEN).rev() {
            let digit = (candidate >> (2 * shift)) & 0b11;
            prefix.push(match digit {
                0 => 'A',
                1 => 'C',
                2 => 'G',
                _ => 'T',
            });
        }
        if !decoded.iter().any(|sequence| sequence.starts_with(&prefix)) {
            return prefix;
        }
    }
    unreachable!(
        "every {PREFIX_LEN}-base prefix appears in the oracle — the fixture cannot exercise the \
         no-match case"
    )
}

/// The 42-byte header literals, the strict ascending record order, the exact
/// record-count meaning, and the t1/t4 byte identity — all on files produced
/// by the new counting path.
#[test]
fn header_bytes_match_the_frozen_v2_literals() -> Result<()> {
    let dir = TempDir::new()?;
    let (input, oracle) = consumer_fixture(dir.path())?;
    let (t1, t4) = run_consumer_fixture(&input, dir.path())?;

    assert_whole_file_equal(
        &t1,
        &t4,
        "new path at threads=1",
        "new path at threads=4",
        "the 20,000-base consumer fixture must be byte-identical across thread counts",
    );

    for (label, bytes) in [("threads=1", &t1), ("threads=4", &t4)] {
        assert!(
            bytes.len() >= RKDB_V2_HEADER_BYTES,
            "{label}: file is {} bytes — too short for the v2 header",
            bytes.len()
        );

        // Frozen raw literals, byte by byte, at their exact offsets.
        assert_eq!(&bytes[0..4], b"RKDB", "{label}: frozen magic");
        assert_eq!(
            u16::from_le_bytes([bytes[4], bytes[5]]),
            2,
            "{label}: frozen version"
        );
        assert_eq!(bytes[6], CONSUMER_K as u8, "{label}: kmer_size");
        assert_eq!(
            &bytes[7..10],
            &[0u8; 3],
            "{label}: the three padding bytes after kmer_size must be zero"
        );
        let total_kmers = u64::from_le_bytes(
            bytes[10..18]
                .try_into()
                .expect("header total_kmers is 8 bytes"),
        );
        assert_eq!(
            bytes[18], 3,
            "{label}: the flags byte must be 3 (sorted bit 1 + canonical bit 2)"
        );
        assert_eq!(
            &bytes[19..26],
            &[0u8; 7],
            "{label}: the seven padding bytes after the flags must be zero"
        );
        let data_offset = u64::from_le_bytes(
            bytes[26..34]
                .try_into()
                .expect("header data_offset is 8 bytes"),
        );
        assert_eq!(data_offset, 42, "{label}: frozen data_offset");
        let index_offset = u64::from_le_bytes(
            bytes[34..42]
                .try_into()
                .expect("header index_offset is 8 bytes"),
        );
        assert_eq!(index_offset, 0, "{label}: frozen index_offset");

        // The same literals through the production header reader.
        let header = DatabaseHeader::read_from(&mut Cursor::new(bytes.as_slice()))
            .map_err(|error| anyhow!("{label}: read header: {error}"))?;
        assert_eq!(header.magic, *b"RKDB", "{label}: header.magic");
        assert_eq!(header.version, 2, "{label}: header.version");
        assert_eq!(
            header.kmer_size, CONSUMER_K as u8,
            "{label}: header.kmer_size"
        );
        assert!(header.sorted, "{label}: header.sorted must be set");
        assert!(header.canonical, "{label}: header.canonical must be set");
        assert_eq!(header.data_offset, 42, "{label}: header.data_offset");
        assert_eq!(header.index_offset, 0, "{label}: header.index_offset");

        // Records: strictly ascending, parse lands exactly on the file end
        // (`parse_rkdb_bytes` rejects a trailing partial record), and the
        // header count is the RECORD COUNT.
        let (_, records) =
            parse_rkdb_bytes(bytes).with_context(|| format!("{label}: parse records"))?;
        assert!(
            records.windows(2).all(|pair| pair[0].0 < pair[1].0),
            "{label}: sorted .rkdb records must be strictly ascending by encoded key"
        );
        assert_eq!(
            total_kmers,
            records.len() as u64,
            "{label}: header total_kmers must equal the on-disk record count"
        );
        assert_eq!(
            records.len(),
            oracle.len(),
            "{label}: the file must hold exactly the oracle's distinct k-mers"
        );
        assert_eq!(
            header.total_kmers,
            records.len() as u64,
            "{label}: the read-back header agrees with the raw bytes"
        );
    }
    Ok(())
}

/// Consumer one: `DatabaseQuery` answers every sampled oracle key, its reverse
/// complement, and returns `None` for absent keys — both from the disk binary
/// search and from the preloaded search.
#[test]
fn database_query_binary_search_answers_every_oracle_key_from_the_new_write_path() -> Result<()> {
    const SAMPLE: usize = 500;
    const ABSENT: usize = 200;

    let dir = TempDir::new()?;
    let (input, oracle) = consumer_fixture(dir.path())?;
    let out = dir.path().join("consumer-sorted.rkdb");
    let run = run_count(&input, CONSUMER_K, true, true, 4, &out);
    assert_success(&run, "DatabaseQuery consumer, sorted output");

    let oracle_keys: Vec<u128> = oracle.keys().copied().collect();
    let sampled = sample_keys(&oracle_keys, SAMPLE);
    let absent = absent_query_keys(&oracle, CONSUMER_K, ABSENT);

    // Fixture honesty: the sampled set and the absent set are the documented
    // sizes, and the reverse-complement arm is not vacuous (at least one
    // sampled key's reverse complement differs from the key itself).
    assert_eq!(sampled.len(), SAMPLE, "the deterministic sample size");
    assert_eq!(absent.len(), ABSENT, "the deterministic absent-key count");
    let non_palindromic = sampled
        .iter()
        .filter(|&&kmer| reverse_complement_u128(kmer, CONSUMER_K) != kmer)
        .count();
    assert!(
        non_palindromic > 0,
        "the reverse-complement arm must query at least one sequence that differs from its \
         key, otherwise the arm is vacuous"
    );

    // Disk binary search (preload = false).
    let mut disk = DatabaseQuery::open(&out, false)?;
    for &kmer in &sampled {
        let sequence = decode_kmer_u128(kmer, CONSUMER_K);
        assert_eq!(
            disk.query_kmer(&sequence)?,
            Some(oracle[&kmer]),
            "DatabaseQuery disk binary search returned the wrong count for oracle key \
             {kmer:#x} ({sequence})"
        );
    }
    for &kmer in &sampled {
        let reverse = reverse_complement_u128(kmer, CONSUMER_K);
        let sequence = decode_kmer_u128(reverse, CONSUMER_K);
        assert_eq!(
            disk.query_kmer(&sequence)?,
            Some(oracle[&kmer]),
            "DatabaseQuery disk binary search returned the wrong canonical count for the reverse \
             complement {sequence} of oracle key {kmer:#x}"
        );
    }
    for sequence in &absent {
        assert_eq!(
            disk.query_kmer(sequence)?,
            None,
            "DatabaseQuery disk binary search must return None for the absent k-mer {sequence}"
        );
    }

    // Preloaded search (preload = true): every oracle key plus the absent set.
    let mut memory = DatabaseQuery::open(&out, true)?;
    for (&kmer, &count) in &oracle {
        let sequence = decode_kmer_u128(kmer, CONSUMER_K);
        assert_eq!(
            memory.query_kmer(&sequence)?,
            Some(count),
            "DatabaseQuery preloaded binary search returned the wrong count for oracle key \
             {kmer:#x} ({sequence})"
        );
    }
    for sequence in &absent {
        assert_eq!(
            memory.query_kmer(sequence)?,
            None,
            "DatabaseQuery preloaded binary search must return None for the absent k-mer {sequence}"
        );
    }
    Ok(())
}

/// Negative control: an unsorted file must be REFUSED by disk binary search
/// (never answered wrongly), while the preloaded linear route still answers
/// the full oracle.
#[test]
fn disk_binary_search_refuses_an_unsorted_database() -> Result<()> {
    let dir = TempDir::new()?;
    let (input, oracle) = consumer_fixture(dir.path())?;
    let out = dir.path().join("consumer-unsorted.rkdb");
    let run = run_count(&input, CONSUMER_K, true, false, 4, &out);
    assert_success(&run, "DatabaseQuery consumer, unsorted output");

    let parsed = parse_rkdb(&out)?;
    assert!(
        !parsed.header.sorted,
        "the --no-sort file must carry sorted=false; otherwise this negative control is vacuous"
    );

    let probe_key = *oracle
        .keys()
        .next()
        .expect("the consumer oracle is non-empty");
    let probe_sequence = decode_kmer_u128(probe_key, CONSUMER_K);

    let mut disk = DatabaseQuery::open(&out, false)?;
    let error = disk
        .query_kmer(&probe_sequence)
        .expect_err("disk binary search on an unsorted database must refuse, not answer");
    let message = error.to_string();
    assert!(
        message.contains("unsorted database"),
        "the refusal must name the unsorted database (the wrong count must never be returned), \
         got: {message}"
    );

    // Preloaded mode answers the full oracle through the linear route.
    let mut memory = DatabaseQuery::open(&out, true)?;
    for (&kmer, &count) in &oracle {
        let sequence = decode_kmer_u128(kmer, CONSUMER_K);
        assert_eq!(
            memory.query_kmer(&sequence)?,
            Some(count),
            "DatabaseQuery preloaded LINEAR search must answer oracle key {kmer:#x} ({sequence}) \
             from the unsorted file"
        );
    }
    Ok(())
}

/// Consumer two: `extract_prefix_optimized` returns exactly the oracle subset,
/// in file order, with the exact contiguous block bounds — and the unsorted
/// file's linear fallback returns the same matches.
#[test]
fn prefix_query_answers_exactly_on_files_produced_by_the_new_write_path() -> Result<()> {
    let dir = TempDir::new()?;
    let (input, oracle) = consumer_fixture(dir.path())?;
    let sorted_out = dir.path().join("consumer-prefix-sorted.rkdb");
    let unsorted_out = dir.path().join("consumer-prefix-unsorted.rkdb");
    let sorted_run = run_count(&input, CONSUMER_K, true, true, 4, &sorted_out);
    assert_success(&sorted_run, "prefix consumer, sorted output");
    let unsorted_run = run_count(&input, CONSUMER_K, true, false, 4, &unsorted_out);
    assert_success(&unsorted_run, "prefix consumer, unsorted output");

    let oracle_pairs = oracle_pairs(&oracle);
    let cases = prefix_cases(&oracle_pairs, CONSUMER_K);
    assert_eq!(
        cases.len(),
        8,
        "the eight prefix cases are four single bases, one 3-base, one 10-base, one \
         full-length key, and one no-match prefix"
    );

    // Sorted consumer: exact matches, exact order, exact block bounds.
    let sorted_db = RKDatabase::from_file_path(&sorted_out)?;
    for (case_index, prefix) in cases.iter().enumerate() {
        let result = extract_prefix_optimized(&sorted_db, prefix)?;
        let expected = expected_prefix_block(&oracle_pairs, prefix, CONSUMER_K);
        // Fixture honesty: the first seven cases must exercise at least one
        // match; only the last case is the no-match case. A vacuously empty
        // expectation everywhere would let every equality below pass.
        if case_index + 1 == cases.len() {
            assert!(
                expected.matches.is_empty(),
                "prefix case {prefix:?} is the no-match case but the oracle holds {} matches",
                expected.matches.len()
            );
        } else {
            assert!(
                !expected.matches.is_empty(),
                "prefix case {prefix:?} must exercise at least one oracle match"
            );
        }
        assert!(
            result.memory_block.is_sorted,
            "prefix {prefix:?}: the sorted database must take the binary-search route"
        );
        assert_eq!(
            result.matches, expected.matches,
            "prefix {prefix:?}: extract_prefix_optimized must return exactly the oracle subset, \
             in file order"
        );
        assert_eq!(
            result.memory_block.start_index, expected.start_index,
            "prefix {prefix:?}: start_index must be the first matching index {}",
            expected.start_index
        );
        assert_eq!(
            result.memory_block.end_index, expected.end_index,
            "prefix {prefix:?}: end_index must be one past the last matching index {}",
            expected.end_index
        );
        assert_eq!(
            result.memory_block.block_size,
            expected.end_index - expected.start_index,
            "prefix {prefix:?}: block_size must equal end_index - start_index"
        );
        assert_eq!(
            result.total_matches,
            expected.matches.len(),
            "prefix {prefix:?}: total_matches must equal the oracle subset size"
        );
    }

    // Unsorted consumer: the linear fallback returns the same matches.
    let unsorted_db = RKDatabase::from_file_path(&unsorted_out)?;
    assert!(
        !unsorted_db.header.sorted,
        "the --no-sort file must carry sorted=false"
    );
    for prefix in &cases {
        let result = extract_prefix_optimized(&unsorted_db, prefix)?;
        let expected = expected_prefix_block(&oracle_pairs, prefix, CONSUMER_K);
        assert!(
            !result.memory_block.is_sorted,
            "prefix {prefix:?}: the unsorted database must report the linear route"
        );
        let observed: BTreeSet<(String, u64)> = result.matches.iter().cloned().collect();
        let expected_set: BTreeSet<(String, u64)> = expected.matches.iter().cloned().collect();
        assert_eq!(
            observed, expected_set,
            "prefix {prefix:?}: the unsorted linear fallback must return the same oracle subset"
        );
        assert_eq!(
            result.memory_block.start_index, 0,
            "prefix {prefix:?}: the linear route starts at index 0"
        );
        assert_eq!(
            result.memory_block.end_index,
            unsorted_db.entries.len(),
            "prefix {prefix:?}: the linear route covers every entry"
        );
        assert_eq!(
            result.memory_block.block_size,
            unsorted_db.entries.len(),
            "prefix {prefix:?}: the linear block size is the whole entry list"
        );
        assert_eq!(
            result.total_matches,
            expected.matches.len(),
            "prefix {prefix:?}: the unsorted route must find the oracle subset size"
        );
    }
    Ok(())
}
