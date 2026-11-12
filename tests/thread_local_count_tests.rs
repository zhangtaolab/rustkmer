//! PAR-02 proofs: per-worker thread-local accumulation + checked end-of-file
//! reduction (plan 06-02).
//!
//! The counting hot path must accumulate into a worker-private
//! [`LocalKmerCounts`] and reduce once per file, with count maps that are
//! **exactly** the maps the pre-change per-window shared-increment path
//! produced. Integer addition is commutative and associative, so any map
//! divergence is a real lost-update / double-count bug, not an ordering
//! artifact.
//!
//! Task 1 owns the end-to-end parity, width, fresh-local, and multi-file CLI
//! proofs. Task 2 extends this file with the full 1-vs-N / old-vs-new matrix,
//! fail-loud overflow, unique, and conservation proofs.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;

use rayon::prelude::*;
use rustkmer::error::ProcessingResult;
use rustkmer::hash::local::LocalKmerCounts;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};

/// Deterministic input sequences.
///
/// Every sequence is at least 64 bases so the same fixture exercises
/// `k = 21`, `32`, and `64` (the dense, dense-boundary, and wide widths). The
/// last sequence contains an `N`, which must be skipped as an invalid window
/// (and must not skew the count maps on either path).
fn input_sequences() -> Vec<&'static [u8]> {
    let sequences: Vec<&'static [u8]> = vec![
        b"ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
        b"TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        b"ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
        b"GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
        b"AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTT",
        b"GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAG",
        b"ACGTACGTACGTACGTACGTACGTACGTACGTNACGTACGTACGTACGTACGTACGTACGTACGT",
    ];
    for sequence in &sequences {
        assert!(
            sequence.len() >= 64,
            "fixture sequences must cover k=64 (got {} bases)",
            sequence.len()
        );
    }
    sequences
}

/// Count one sequence into a local accumulator, mirroring `count.rs`'s
/// `count_record_into`: encode failure (an `N` window) records a skip, canonical
/// failure skips the window without counting it, and a successful increment
/// goes through the local's checked semantics.
fn count_sequence_into(
    local: &mut LocalKmerCounts,
    seq: &[u8],
    k: usize,
    canonical: bool,
) -> ProcessingResult<()> {
    if seq.len() < k {
        return Ok(());
    }
    for window in seq.windows(k) {
        match encode_kmer_bytes_u128(window) {
            Ok(encoded) => {
                let final_kmer = if canonical {
                    match canonical_kmer_u128(encoded, k) {
                        Ok(canonical_kmer) => canonical_kmer,
                        Err(_) => continue,
                    }
                } else {
                    encoded
                };
                local.increment(final_kmer)?;
            }
            Err(_) => local.record_skipped(),
        }
    }
    Ok(())
}

/// The pre-PAR-02 reference path: every window increments the shared counter.
fn count_reference_path(
    sequences: &[&[u8]],
    k: usize,
    canonical: bool,
) -> ProcessingResult<BTreeMap<u128, u32>> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
    for seq in sequences {
        if seq.len() < k {
            continue;
        }
        for window in seq.windows(k) {
            match encode_kmer_bytes_u128(window) {
                Ok(encoded) => {
                    let final_kmer = if canonical {
                        match canonical_kmer_u128(encoded, k) {
                            Ok(canonical_kmer) => canonical_kmer,
                            Err(_) => continue,
                        }
                    } else {
                        encoded
                    };
                    counter.increment(final_kmer)?;
                }
                Err(_) => {}
            }
        }
    }
    Ok(counter.get_all_counts().into_iter().collect())
}

/// Count through per-worker locals with a dedicated rayon pool of `workers`.
///
/// Returns the counter so callers can assert the post-reduce statistics.
fn count_local_path(
    sequences: &[&[u8]],
    k: usize,
    canonical: bool,
    workers: usize,
) -> ProcessingResult<(Arc<KmerCounter>, BTreeMap<u128, u32>)> {
    let counter = Arc::new(KmerCounter::new(k, canonical, 4096, workers)?);
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(workers)
        .build()
        .expect("build local rayon pool");

    pool.install(|| -> ProcessingResult<()> {
        sequences.par_iter().try_for_each_init(
            || counter.local_handle(),
            |handle, seq| -> ProcessingResult<()> {
                let mut local = handle
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                count_sequence_into(&mut local, seq, k, canonical)
            },
        )
    })?;

    counter.reduce_local_counts()?;
    let map = counter.get_all_counts().into_iter().collect();
    Ok((counter, map))
}

/// Decode a raw count map to `k-mer string -> count` (D-04 discipline: compare
/// decoded k-mers, never raw integers).
fn decode_map(map: &BTreeMap<u128, u32>, k: usize) -> BTreeMap<String, u32> {
    map.iter()
        .map(|(encoded, count)| (decode_kmer_u128(*encoded, k), *count))
        .collect()
}

#[test]
fn local_path_matches_reference_path_end_to_end() -> anyhow::Result<()> {
    let sequences = input_sequences();
    for &canonical in &[true, false] {
        let (counter, local_map) = count_local_path(&sequences, 21, canonical, 4)?;
        let reference_map = count_reference_path(&sequences, 21, canonical)?;

        assert_eq!(
            decode_map(&local_map, 21),
            decode_map(&reference_map, 21),
            "PAR-02: local accumulation diverged from the pre-change per-window path \
             (k=21, canonical={})",
            canonical
        );

        // The per-file reduction must leave the shared table holding exactly the
        // merged local contents, with nonzero totals.
        let expected_total: u64 = local_map.values().map(|count| *count as u64).sum();
        assert!(expected_total > 0, "fixture must produce k-mers");
        assert_eq!(
            counter.total_kmers(),
            expected_total,
            "shared total must equal the sum of the merged local counts"
        );
        assert_eq!(
            counter.unique_kmers(),
            local_map.len() as u64,
            "shared unique count must equal the merged distinct keys"
        );
    }
    Ok(())
}

#[test]
fn local_width_matches_counter_width() -> anyhow::Result<()> {
    for &(k, expect_dense) in &[(21usize, true), (64usize, false)] {
        let counter = KmerCounter::new(k, false, 16, 1)?;
        let local = counter.new_local_counts();

        assert_eq!(
            local.uses_dense_storage(),
            expect_dense,
            "k={} local width must match the counter's width selection",
            k
        );
        assert_eq!(
            local.uses_dense_storage(),
            counter.uses_dense_storage(),
            "k={} local and counter must agree on the live storage width",
            k
        );
        assert_eq!(
            local.stored_key_bytes(),
            counter.stored_key_bytes(),
            "k={} local and counter must agree on the stored key width",
            k
        );
    }
    Ok(())
}

#[test]
fn reduce_drains_and_hands_out_fresh_locals_for_the_next_file() -> anyhow::Result<()> {
    let counter = KmerCounter::new(21, false, 4096, 1)?;
    let sequences = input_sequences();

    // File 1: count through this thread's local handle, then reduce.
    let first_handle = counter.local_handle();
    {
        let mut local = first_handle
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        for seq in &sequences {
            count_sequence_into(&mut local, seq, 21, false)?;
        }
    }
    counter.reduce_local_counts()?;
    let first_total = counter.total_kmers();
    assert!(first_total > 0, "file 1 must produce a nonzero total");
    assert_eq!(
        first_total,
        counter.get_all_counts().iter().map(|(_, c)| *c as u64).sum::<u64>(),
        "after the reduce, the shared total must match the shared table"
    );

    // The next handle request on the same worker must create a FRESH local:
    // the drained one has advanced out of the registry generation, which is what
    // prevents a multi-file run from double-counting file 1 into file 2.
    let second_handle = counter.local_handle();
    {
        let local = second_handle
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        assert_eq!(
            local.total_kmers(),
            0,
            "a post-reduce handle must be a fresh, empty local (generation advanced)"
        );
        assert_eq!(local.key_count(), 0, "post-reduce handle must hold no keys");
        assert_eq!(local.skipped(), 0, "post-reduce handle must hold no skips");
    }

    // File 2: count the same sequences again and reduce; totals must add exactly.
    {
        let mut local = second_handle
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        for seq in &sequences {
            count_sequence_into(&mut local, seq, 21, false)?;
        }
    }
    counter.reduce_local_counts()?;
    assert_eq!(
        counter.total_kmers(),
        first_total * 2,
        "file 2 must add exactly its own counts (no reuse of the drained local)"
    );
    Ok(())
}

// --- Multi-file CLI differential -------------------------------------------

/// Minimal RAII temp directory: removed on drop, even when an assertion fails.
struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "rustkmer-par02-{}-{}",
            std::process::id(),
            tag
        ));
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
fn write_fastq(path: &Path, sequences: &[&str]) {
    let mut body = String::new();
    for (idx, sequence) in sequences.iter().enumerate() {
        body.push_str(&format!("@read{}\n", idx));
        body.push_str(sequence);
        body.push_str("\n+\n");
        body.push_str(&"I".repeat(sequence.len()));
        body.push('\n');
    }
    fs::write(path, body).expect("write FASTQ fixture");
}

/// Run the real CLI binary over `inputs` and write a text count table.
fn run_cli_count(inputs: &[&Path], k: usize, output: &Path) {
    let mut command = Command::new(env!("CARGO_BIN_EXE_rustkmer"));
    command.arg("count").arg("-k").arg(k.to_string()).arg("-i");
    for input in inputs {
        command.arg(input);
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

/// **Multi-file reduction contract (PAR-02).**
///
/// One combined `-i a b` invocation must produce the elementwise sum of the two
/// per-file invocations. A drained thread-local that was reused on file 2 would
/// re-add file 1's keys, making the combined map strictly larger — this test
/// pins the per-file reduce-and-release contract.
#[test]
fn multi_file_local_reduction_matches_per_file_sum() -> anyhow::Result<()> {
    const K: usize = 21;
    let dir = TempDir::new("multi-file");

    // File A and file B share one sequence and each own one unique sequence, so
    // the combined map's overlapping keys must sum while unique keys pass
    // through exactly once.
    let shared = "ACGTACGTACGTACGTACGTACGTACGTACGT";
    let file_a_sequences = [shared, "GATTACAGATTACAGATTACAGATTACAGATT"];
    let file_b_sequences = [shared, "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"];

    let file_a = dir.join("a.fastq");
    let file_b = dir.join("b.fastq");
    write_fastq(&file_a, &file_a_sequences);
    write_fastq(&file_b, &file_b_sequences);

    let combined_out = dir.join("combined.tsv");
    let a_out = dir.join("a.tsv");
    let b_out = dir.join("b.tsv");

    run_cli_count(&[&file_a, &file_b], K, &combined_out);
    run_cli_count(&[&file_a], K, &a_out);
    run_cli_count(&[&file_b], K, &b_out);

    let combined = read_text_counts(&combined_out);
    let a = read_text_counts(&a_out);
    let b = read_text_counts(&b_out);

    let mut union: Vec<&String> = a.keys().chain(b.keys()).collect();
    union.sort();
    union.dedup();

    assert_eq!(
        combined.len(),
        union.len(),
        "combined run must contain exactly the union of per-file k-mers"
    );

    for key in &union {
        let expected = a.get(*key).copied().unwrap_or(0) + b.get(*key).copied().unwrap_or(0);
        assert_eq!(
            combined.get(*key).copied(),
            Some(expected),
            "k-mer {:?}: combined count must equal the elementwise sum of the \
             per-file counts (a drained local reused across files would double-count)",
            key
        );
    }

    let combined_total: u64 = combined.values().map(|count| *count as u64).sum();
    let a_total: u64 = a.values().map(|count| *count as u64).sum();
    let b_total: u64 = b.values().map(|count| *count as u64).sum();
    assert_eq!(
        combined_total,
        a_total + b_total,
        "combined total must equal the sum of the per-file totals"
    );
    assert!(combined_total > 0, "fixture must produce k-mers");

    Ok(())
}
