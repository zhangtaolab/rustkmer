//! Route-level conservation proofs for the prefix-cache streaming bucket
//! merge (plan 03-13, closing CR-01 + WR-03 — 03-VERIFICATION.md gaps[1]).
//!
//! **What was broken pre-fix** (03-REVIEW.md CR-01/WR-03): the per-bucket
//! streaming reader `read_batch_from_file_sync` cleared its buffer at every
//! call, read 8192-byte chunks until `bytes_read >= 4_000_000` (so the first
//! call consumes exactly `489 * 8192 = 4,005,888` bytes), and dropped the
//! trailing partial-record bytes (`4,005,888 mod 20 = 8`) — leaving the
//! `BufReader` mid-record so every subsequent record of that shard parsed
//! from a shifted offset. Separately, `merge_single_prefix_streaming`'s
//! peek-and-add branches consumed a within-file duplicate without removing
//! it from the buffer or re-queueing its file, stranding the rest of that
//! file's run. Read errors were swallowed as end-of-batch.
//!
//! **What these tests prove**, end-to-end through
//! `RKDatabase::merge_databases_to_path` with `use_prefix_cache` +
//! `merge_mode = "streaming"`:
//!
//! 1. A bucket shard larger than one ~4 MB batch is merged with EXACT
//!    conservation — the emitted (kmer, summed count) map equals an
//!    independently computed oracle, including cross-file duplicates and
//!    within-file duplicates.
//! 2. A mid-record-truncated input body makes the merge return `Err`, never
//!    `Ok` with silently lost records.
//!
//! No `mod common;` — the fixtures are self-contained and mirror
//! `tests/merge_routing_tests.rs`'s `use` list.

use rustkmer::database::format::RKDatabase;
use rustkmer::database::merge_config::MergeConfig;
use std::collections::BTreeMap;

/// k-mer size shared by every synthetic input (21 bases -> 42-bit key).
const K: u8 = 21;

/// The exact byte count the pre-fix reader consumed in its FIRST call:
/// 489 x 8192. `4_005_888 mod 20 = 8` — the dropped partial-record tail that
/// misaligned every later batch of the same shard.
const FIRST_BATCH_BYTES: u64 = 489 * 8192;

/// On-disk data mass of input A: 250,000 records x 20 B.
///
/// The vacuousness guard below asserts the real file exceeds this, which is
/// strictly above `FIRST_BATCH_BYTES` — a smaller fixture would let the
/// batch-boundary defect hide while every test stays green.
const INPUT_A_DATA_BYTES: u64 = 5_000_000;

/// A k-mer of the SHARED bucket: high byte of the 42-bit key `0xAB`, low
/// byte `0x00`.
///
/// The route buckets by ONE byte of the key (today the low byte —
/// `get_prefix_4mer` is `kmer & 0xFF`; plan 03-15 moves it to the HIGH byte
/// of the right-aligned key). Sharing BOTH bytes keeps every such record in
/// a single bucket under EITHER scheme, so this fixture stays a
/// single-bucket fixture after 03-15 flips the selection.
fn shared_bucket_kmer(i: u128) -> u128 {
    (0xAB_u128 << 34) | (i << 8)
}

/// A k-mer OUTSIDE the shared bucket under either bucketing scheme: high
/// byte `0xCD` (not `0xAB`), low byte `0x22` (not `0x00`).
fn other_bucket_kmer(j: u128) -> u128 {
    (0xCD_u128 << 34) | (j << 8) | 0x22
}

/// A prefix-cache merge config pinned to the streaming per-bucket strategy.
fn streaming_config(temp_dir: &std::path::Path) -> MergeConfig {
    MergeConfig {
        use_prefix_cache: true,
        merge_mode: "streaming".to_string(),
        temp_dir: temp_dir.to_path_buf(),
        ..Default::default()
    }
}

/// Decode a merged database into the observation this file asserts on: the
/// (kmer -> summed count) map. Summing (not collecting) makes the
/// conservation claim explicit — a record split across two output entries
/// with the same k-mer still has to produce the oracle's total, and the
/// record-COUNT assertion beside it catches the split.
fn decode_observations(db: &RKDatabase) -> BTreeMap<u128, u32> {
    let mut observed: BTreeMap<u128, u32> = BTreeMap::new();
    for entry in &db.entries {
        *observed.entry(entry.kmer).or_insert(0) += entry.count;
    }
    observed
}

/// CR-01, end-to-end: a bucket shard larger than one ~4 MB batch is merged
/// through the full `use_prefix_cache` route with EXACT record and content
/// conservation.
///
/// Input A alone puts 250,000 records (5,000,000 bytes — more than the
/// 4,005,888-byte first batch) into ONE bucket, so its shard crosses a batch
/// boundary and, pre-fix, lost the 8-byte partial-record tail plus every
/// record after the misalignment. Input B adds cross-file duplicates (counts
/// must sum), within-file duplicate runs (the WR-03 stranding trigger), and
/// a few k-mers outside the shared bucket (so the merge spans >1 bucket).
///
/// Content is asserted pairwise, not order — global output ordering is
/// 03-15's gap, deliberately not claimed here.
#[test]
fn prefix_cache_streaming_merge_conserves_a_bucket_larger_than_one_batch() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    // Input A: 250,000 distinct k-mers, all in the shared bucket.
    // canonical=false so the splitter's canonicalization is a no-op (the
    // oracle is the raw pairs); sorted=true so each shard is an ascending
    // run, which the heap merge requires.
    let a_pairs: Vec<(u128, u32)> = (0..250_000u32)
        .map(|i| (shared_bucket_kmer(i as u128), i % 97 + 1))
        .collect();
    let a = RKDatabase::from_kmer_pairs(a_pairs.clone(), K, false, true)?;
    let a_path = dir.path().join("input_a.rkdb");
    a.to_file_path(&a_path)?;

    // Vacuousness guard: the fixture MUST cross a batch boundary. A shard at
    // or below the first batch's 4,005,888-byte consumption cannot exercise
    // the dropped-tail/misalignment defect and would keep this test green
    // while proving nothing.
    let a_data_bytes = std::fs::metadata(&a_path)?.len() - 42;
    assert_eq!(
        a_data_bytes, INPUT_A_DATA_BYTES,
        "input A's data mass drifted from the fixture's design"
    );
    assert!(
        a_data_bytes > 4_000_000,
        "vacuousness guard: input A's data ({a_data_bytes} bytes) must exceed one ~4 MB batch \
         (first batch consumes {FIRST_BATCH_BYTES} bytes)"
    );

    // Input B: ~50 records mixing the three duplicate shapes the merge must
    // survive, plus out-of-bucket keys.
    let mut b_pairs: Vec<(u128, u32)> = Vec::new();
    // Cross-file duplicates of A's keys — their counts must SUM into A's.
    for (i, count) in [(0_u128, 5_u32), (1_000, 7), (50_000, 11), (249_999, 3)] {
        b_pairs.push((shared_bucket_kmer(i), count));
    }
    // Within-file duplicate runs (the WR-03 trigger): the same key repeated
    // adjacently after the sort.
    b_pairs.push((shared_bucket_kmer(5), 2));
    b_pairs.push((shared_bucket_kmer(5), 3));
    b_pairs.push((shared_bucket_kmer(6), 4));
    b_pairs.push((shared_bucket_kmer(6), 1));
    b_pairs.push((shared_bucket_kmer(6), 2));
    // A few k-mers OUTSIDE the shared bucket, so the run spans >1 bucket.
    for j in 0..5u128 {
        b_pairs.push((other_bucket_kmer(j), j as u32 + 1));
    }
    let b = RKDatabase::from_kmer_pairs(b_pairs.clone(), K, false, true)?;
    let b_path = dir.path().join("input_b.rkdb");
    b.to_file_path(&b_path)?;

    // The oracle is computed from the input pair lists alone — it never
    // calls any production merge code.
    let mut oracle: BTreeMap<u128, u32> = BTreeMap::new();
    for (kmer, count) in a_pairs.iter().chain(b_pairs.iter()) {
        *oracle.entry(*kmer).or_insert(0) += *count;
    }

    let out = work.path().join("merged.rkdb");
    let summary = RKDatabase::merge_databases_to_path(
        &[a_path.clone(), b_path.clone()],
        &streaming_config(work.path()),
        &out,
    )?;

    let merged = RKDatabase::from_file_path(&out)?;
    assert_eq!(
        merged.entries.len(),
        oracle.len(),
        "record-count conservation: {} output records vs {} oracle records",
        merged.entries.len(),
        oracle.len()
    );
    assert_eq!(
        merged.header.total_kmers,
        oracle.len() as u64,
        "header total_kmers must equal the oracle's unique-k-mer count"
    );
    assert_eq!(
        summary.total_kmers,
        oracle.len() as u64,
        "the returned summary's total must match the oracle"
    );
    assert_eq!(
        decode_observations(&merged),
        oracle,
        "content conservation: every output (kmer, summed count) must equal the oracle entry"
    );

    Ok(())
}

/// CR-01's error half, at route level: an input whose HEADER is valid but
/// whose BODY is truncated mid-record must make the merge return `Err` —
/// never `Ok` with silently lost records.
///
/// The exact error text is deliberately not pinned: truncation is damage,
/// and damage may surface at any validating stage (the shard reader's IO
/// error, or the phase-1 entry reader that decodes the input, or the 03-11
/// integrity accounting) — all of which are `Err`. What this forbids is the
/// pre-fix failure shape: a read error treated as end-of-stream and reported
/// as a successful merge missing records.
#[test]
fn prefix_cache_streaming_merge_propagates_shard_read_errors() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    // A valid small input.
    let ok_pairs: Vec<(u128, u32)> = (0..50u32)
        .map(|i| (shared_bucket_kmer(i as u128), i + 1))
        .collect();
    let ok = RKDatabase::from_kmer_pairs(ok_pairs, K, false, true)?;
    let ok_path = dir.path().join("ok.rkdb");
    ok.to_file_path(&ok_path)?;

    // An input with a valid header but a body truncated mid-record: 500
    // whole records plus 10 orphan bytes of what was record 501 (the header
    // still declares all 1,000).
    let trunc_pairs: Vec<(u128, u32)> = (0..1_000u32)
        .map(|i| (shared_bucket_kmer(10_000 + i as u128), i + 1))
        .collect();
    let trunc = RKDatabase::from_kmer_pairs(trunc_pairs, K, false, true)?;
    let trunc_path = dir.path().join("truncated.rkdb");
    trunc.to_file_path(&trunc_path)?;

    const WHOLE_RECORDS_KEPT: u64 = 500;
    let truncated_len = 42 + 20 * WHOLE_RECORDS_KEPT + 10;
    let f = std::fs::OpenOptions::new().write(true).open(&trunc_path)?;
    f.set_len(truncated_len)?;
    drop(f);

    let out = work.path().join("merged.rkdb");
    let outcome = RKDatabase::merge_databases_to_path(
        &[ok_path, trunc_path],
        &streaming_config(work.path()),
        &out,
    );

    if let Ok(summary) = outcome {
        panic!(
            "a mid-record-truncated input body must fail the merge, not succeed with {} records \
             (silent truncation)",
            summary.total_kmers
        );
    }

    Ok(())
}
