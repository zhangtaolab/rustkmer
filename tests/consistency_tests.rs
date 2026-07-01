//! Integration tests for consistency
//!
//! This file serves as the entry point for consistency tests.
//! Note: Actual consistency tests are needed to verify u64/u128 implementation compatibility.

mod consistency;

#[test]
fn consistency_tests_placeholder() {
    // Placeholder: actual u64/u128 consistency coverage lives under
    // tests/consistency/* (pulled in via `mod consistency;` above).
    // The placeholder exists so this target registers at least one test.
    let _ = "u64/u128 consistency coverage is provided by tests/consistency/";
}

/// Backstop test for the SPEC "concurrency | R2" edge: the rayon-parallel
/// prefix-cache merge path emits `log::info!`/`log::warn!`/`log::error!` calls
/// from inside parallel workers (`prefix_cache_merge.rs::merge_prefix_buckets`).
/// This test guards the invariant that logging on the rayon path does not
/// interleave-corrupt k-mer counts — the merged result must equal the exact
/// union of the inputs (counts summed per unique k-mer).
///
/// `env_logger` is thread-safe by construction, so this is a regression guard,
/// not a live-lock assertion: if a future refactor breaks the merge-count
/// invariant under parallel logging (e.g. by sharing a buffer across workers),
/// this test catches it. Held out per SPEC edge coverage (non-inferable).
#[test]
fn test_parallel_merge_logging_preserves_counts() {
    use rustkmer::database::format::RKDatabase;
    use rustkmer::database::merge_config::MergeConfig;
    use std::collections::HashMap;

    // Build 3 small databases with OVERLAPPING k-mer sets so the merge exercises
    // the count-summing path (not just disjoint union). The exact counts are
    // chosen to be deterministic and < 1M (avoids the KmerEntry::read_from
    // endianness heuristic per RESEARCH.md Pitfall 9).
    //
    // db_a: { (kmer=10, count=5), (kmer=20, count=7), (kmer=30, count=3) }
    // db_b: { (kmer=20, count=4), (kmer=30, count=2), (kmer=40, count=9) }
    // db_c: { (kmer=10, count=1), (kmer=30, count=6), (kmer=50, count=8) }
    //
    // Expected merged union (counts summed):
    //   kmer=10 -> 5+1 = 6
    //   kmer=20 -> 7+4 = 11
    //   kmer=30 -> 3+2+6 = 11
    //   kmer=40 -> 9
    //   kmer=50 -> 8
    let kmers_a = vec![(10u128, 5u32), (20, 7), (30, 3)];
    let kmers_b = vec![(20u128, 4u32), (30, 2), (40, 9)];
    let kmers_c = vec![(10u128, 1u32), (30, 6), (50, 8)];

    let db_a = RKDatabase::from_kmer_pairs(kmers_a.clone(), 21, true, true).unwrap();
    let db_b = RKDatabase::from_kmer_pairs(kmers_b.clone(), 21, true, true).unwrap();
    let db_c = RKDatabase::from_kmer_pairs(kmers_c.clone(), 21, true, true).unwrap();

    // Compute the EXPECTED merged result directly (independent of the merge path).
    let mut expected: HashMap<u128, u32> = HashMap::new();
    for (k, c) in kmers_a.iter().chain(kmers_b.iter()).chain(kmers_c.iter()) {
        *expected.entry(*k).or_insert(0) += *c;
    }
    assert_eq!(expected.len(), 5, "expected-union setup: 5 unique k-mers");

    // Persist the inputs to temp .rkdb files (merge reads from disk).
    let tmp = tempfile::tempdir().expect("temp dir for parallel-merge backstop");
    let path_a = tmp.path().join("db_a.rkdb");
    let path_b = tmp.path().join("db_b.rkdb");
    let path_c = tmp.path().join("db_c.rkdb");
    db_a.to_file_path(&path_a).expect("write db_a");
    db_b.to_file_path(&path_b).expect("write db_b");
    db_c.to_file_path(&path_c).expect("write db_c");

    // Configure the PREFIX-CACHE merge path — the one whose
    // `merge_prefix_buckets` runs `non_empty_prefixes.into_par_iter()` and emits
    // `log::info!`/`log::error!` from inside each parallel worker. Setting
    // `use_prefix_cache: true` selects this path in `RKDatabase::merge_databases`.
    let config = MergeConfig {
        use_prefix_cache: true,
        temp_dir: tmp.path().to_path_buf(),
        // Force the in-memory (hashmap) sub-path per prefix bucket — this is the
        // sub-path whose worker closure contains the migrated log:: callsites
        // (prefix_cache_merge.rs:317-355).
        merge_mode: "memory".to_string(),
        // verbose so the log:: callsites in format.rs are also exercised.
        verbose: true,
        ..Default::default()
    };

    let input_paths = vec![path_a, path_b, path_c];
    let merged = RKDatabase::merge_databases(&input_paths, &config)
        .expect("prefix-cache merge must succeed on valid overlapping inputs");

    // Assert exact count preservation: every expected k-mer is present with the
    // exact summed count, and no extra/missing k-mers were introduced by
    // interleave-corruption on the parallel logging path.
    let merged_kmers: HashMap<u128, u32> = merged
        .all_kmers()
        .expect("read merged kmers")
        .into_iter()
        .collect();

    assert_eq!(
        merged_kmers.len(),
        expected.len(),
        "merged k-mer count must match expected union (no drops/duplicates from parallel logging)"
    );
    for (kmer, expected_count) in &expected {
        let actual = merged_kmers
            .get(kmer)
            .unwrap_or_else(|| panic!("k-mer {} missing from merged result", kmer));
        assert_eq!(
            actual, expected_count,
            "k-mer {} count corrupted on parallel-merge logging path: got {}, expected {}",
            kmer, actual, expected_count
        );
    }
}
