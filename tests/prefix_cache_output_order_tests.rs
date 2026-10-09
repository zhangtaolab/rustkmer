//! End-to-end order + query proofs for the prefix-cache merge route
//! (plan 03-15, closing CR-02 — 03-VERIFICATION.md gaps[2]).
//!
//! **What was broken pre-fix** (03-REVIEW.md CR-02):
//! `get_prefix_4mer` returned `kmer & 0xFF` — the LOW byte of the
//! right-aligned 2k-bit encoding (the LAST 4 bases) — while
//! `concatenate_final_output` loops buckets in index order `0..255` and each
//! bucket is internally ascending, so the output was ordered by
//! `(low_byte, kmer)`. That is not ascending u128 order — k-mer `0x010000`
//! (low byte `0x00`, bucket 0) was written BEFORE k-mer `0x0000FF` (low byte
//! `0xFF`, bucket 255) — yet the header claimed `sorted: true`
//! (prefix_cache_merge.rs's `concatenate_final_output`). Every consumer that
//! trusts the flag silently broke: `RKDatabase::query_kmer` switches to
//! binary search on the flag (format.rs), and `extract_prefix_optimized`
//! binary-searches sorted databases — exact-match queries returned `None` or
//! a wrong count, and prefix extraction silently missed k-mers.
//!
//! **What was broken pre-fix** (03-REVIEW.md CR-01, the open WR-03 root
//! cause — closed by plan 03-16): `split_files_by_prefix` chose each
//! record's bucket from `processed_kmer` (canonicalized via
//! `canonical_kmer_u128` when ANY input is canonical) but wrote the RAW
//! `entry.kmer` to the shard. On the opt-in mixed-canonical route the two
//! encodings of one k-mer met in one bucket as separate un-summed records,
//! and a raw key was emitted after smaller keys of later buckets — the
//! all-T key `0xFFFFFFFF` buckets by its canonical form `0x000000` (bucket
//! 0x00) but was written raw at the END of that bucket, ahead of bucket
//! 0x01's much smaller keys — non-ascending output under the same
//! `sorted: true` header CR-02 had just made truthful, silently wrong
//! `query_kmer` binary searches, and un-summed duplicate encodings of one
//! k-mer.
//!
//! **What these tests prove**, end-to-end through
//! `RKDatabase::merge_databases_to_path` with `use_prefix_cache`:
//!
//! 1. The merged output is GLOBALLY ascending by encoded u128 across the
//!    whole entries vector, its header truthfully carries `sorted: true`,
//!    `query_kmer` answers every oracle key exactly (the binary-search
//!    consumer proof), `extract_prefix_optimized` returns exactly the oracle
//!    subset for a chosen first-bases prefix, and content conservation holds
//!    (the same records with the same counts as the input oracle — plan
//!    03-13's guarantee, unchanged by the re-bucketing).
//! 2. Route parity of ANSWERS: the prefix-cache output's decoded (kmer,
//!    count) map equals the in-memory route's on the same inputs, and
//!    `query_kmer` agrees on every oracle key — no merge route produces a
//!    database that answers queries differently than another.
//! 3. Mixed-canonical correctness (CR-01/WR-03, plan 03-16): with one
//!    canonical and one NON-canonical input, the merged output is globally
//!    ascending (`windows(2)` over the whole entries vector), equals an
//!    input-only oracle built by canonicalizing every record through the
//!    production `canonical_kmer_u128` and summing counts (the two
//!    encodings of one k-mer meet in one bucket and SUM), answers every
//!    oracle key through `query_kmer`'s binary search (plus one
//!    asserted-absent negative), and carries `canonical: true` under
//!    ANY-input semantics — true iff at least one input is canonical, here
//!    pinned with input[0] NON-canonical.
//!
//! No `mod common;` — the fixtures are self-contained and mirror
//! `tests/prefix_cache_conservation_tests.rs`'s `use` list.

use rustkmer::database::format::RKDatabase;
use rustkmer::database::merge_config::MergeConfig;
use rustkmer::database::merge_config::MergeStrategy;
use rustkmer::database::prefix_query_optimized::extract_prefix_optimized;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::decode_kmer_u128;
use std::collections::BTreeMap;

/// k-mer size shared by every synthetic input (16 bases -> 32-bit key; the
/// high byte of the key is the FIRST 4 bases under the fixed bucketing).
const K: u8 = 16;

/// A representative member of the crafted `0xAB`-high-byte family — its
/// decoded string's first two bases are the prefix the extraction proof
/// queries (0xAB = `1010 1011` -> first bases `GGGT`, prefix `"GG"`).
const PREFIX_FAMILY_REPRESENTATIVE: u128 = 0xAB1234;

/// The CR-02 discriminator pair: `0x0000FF` (low byte `0xFF`) vs `0x010000`
/// (low byte `0x00`). Under the pre-fix LOW-byte bucketing the smaller key
/// landed in bucket 255 and the larger in bucket 0, so the larger was
/// written FIRST — descending output on a header claiming `sorted: true`.
const DISCRIMINATOR_SMALL: u128 = 0x0000FF;
const DISCRIMINATOR_LARGE: u128 = 0x010000;

/// The 16-base all-T key at k=16 (2 bits per base × 16 = 32 bits, all `11`).
/// Its canonical form is the all-A key `0x000000`, so under ANY-canonical
/// bucketing it lands in bucket `0x00` while its RAW form is the largest
/// u32 — the CR-01 order discriminator, and one half of the meet-and-sum
/// pair (input B carries the canonical `0x000000` with a different count).
/// (The plan's shorthand `0xFFFFFF` names a 24-bit key — `AAAA` + twelve
/// `T`s — whose canonical form is `0x0000FF`, NOT `0x000000`; the all-T
/// intent requires the full-width `0xFFFFFFFF` literal.)
const ALL_T_RAW: u128 = 0xFFFF_FFFF;

/// A prefix-cache merge config (tiny inputs take the per-bucket hashmap
/// strategy under "auto" — irrelevant here: ordering is the concatenation
/// concern and every bucket writer emits ascending).
fn prefix_cache_config(temp_dir: &std::path::Path) -> MergeConfig {
    MergeConfig {
        use_prefix_cache: true,
        temp_dir: temp_dir.to_path_buf(),
        ..Default::default()
    }
}

/// Build the two input databases under `dir` and return their paths plus the
/// input-pairs-only oracle (a BTreeMap sum — it never calls any production
/// merge code).
///
/// canonical=false so the splitter's canonicalization is a no-op (the oracle
/// IS the raw pairs); sorted=true so each shard inherits an ascending run —
/// the requirement the heap/ordered bucket writers assume.
///
/// Input A spreads its high bytes across {0x00, 0x01, 0x40, 0x7F, 0x80,
/// 0xAB, 0xFF} — including the top-bit boundary pair 0x7F/0x80 and both
/// members of the CR-02 discriminator pair. Input B overlaps a subset of
/// A's keys with different counts (cross-file sums) and adds keys
/// interleaved in value between A's.
fn build_inputs(
    dir: &std::path::Path,
) -> anyhow::Result<(std::path::PathBuf, std::path::PathBuf, BTreeMap<u128, u32>)> {
    let a_keys: [u128; 30] = [
        0x000001,
        0x000002,
        0x000040,
        0x0000AB,
        DISCRIMINATOR_SMALL,
        DISCRIMINATOR_LARGE,
        0x010001,
        0x0100FF,
        0x018000,
        0x400000,
        0x401234,
        0x407777,
        0x40FFFF,
        0x7F0000,
        0x7F1234,
        0x7F8000,
        0x7FFFFF,
        0x800000,
        0x801111,
        0x80ABCD,
        0x80FFFF,
        0xAB0000,
        PREFIX_FAMILY_REPRESENTATIVE,
        0xAB7777,
        0xABF0F0,
        0xFF0000,
        0xFF00FF,
        0xFF1234,
        0xFF8000,
        0xFFFFFF,
    ];
    let a_pairs: Vec<(u128, u32)> = a_keys
        .iter()
        .enumerate()
        .map(|(i, &kmer)| (kmer, (i % 13 + 1) as u32))
        .collect();
    let a = RKDatabase::from_kmer_pairs(a_pairs.clone(), K, false, true)?;
    let a_path = dir.join("input_a.rkdb");
    a.to_file_path(&a_path)?;

    // Overlaps first (counts must SUM into A's), then keys interleaved in
    // value between A's — never adjacent to every A key, so a concatenation
    // that ignores global order cannot pass them off as sorted.
    let b_pairs: Vec<(u128, u32)> = vec![
        (DISCRIMINATOR_SMALL, 7),
        (DISCRIMINATOR_LARGE, 11),
        (0x400000, 9),
        (0x7FFFFF, 3),
        (PREFIX_FAMILY_REPRESENTATIVE, 5),
        (0x008051, 2),
        (0x408052, 4),
        (0xAB8053, 6),
        (0xFF4054, 8),
    ];
    let b = RKDatabase::from_kmer_pairs(b_pairs.clone(), K, false, true)?;
    let b_path = dir.join("input_b.rkdb");
    b.to_file_path(&b_path)?;

    let mut oracle: BTreeMap<u128, u32> = BTreeMap::new();
    for (kmer, count) in a_pairs.iter().chain(b_pairs.iter()) {
        *oracle.entry(*kmer).or_insert(0) += *count;
    }

    Ok((a_path, b_path, oracle))
}

/// Decode a merged database into the (kmer -> summed count) map.
fn decode_observations(db: &RKDatabase) -> BTreeMap<u128, u32> {
    let mut observed: BTreeMap<u128, u32> = BTreeMap::new();
    for entry in &db.entries {
        *observed.entry(entry.kmer).or_insert(0) += entry.count;
    }
    observed
}

/// Build the mixed-canonical input pair under `dir` (03-16 / CR-01): input
/// A header `canonical=false` with RAW keys, input B header `canonical=true`
/// — plus the input-pairs-only oracle: every (kmer, count) folded through
/// the PRODUCTION `canonical_kmer_u128` with summed counts. The oracle never
/// calls any merge code.
///
/// Fixture honesty is ASSERTED (03-08 discipline), never commented into
/// existence: every input-B key is checked already-canonical (the header
/// flag alone does not make it so — `from_kmer_pairs` never canonicalizes);
/// at least one input-A raw key must canonicalize into a DIFFERENT high
/// byte than its raw form (the vacuousness guard — without such a record
/// the order assertion cannot discriminate); and the raw all-T key (count 3)
/// and input B's canonical `0x000000` (count 5) must fold into ONE summed
/// oracle entry — the two encodings of a single k-mer.
fn build_mixed_canonical_inputs(
    dir: &std::path::Path,
) -> anyhow::Result<(std::path::PathBuf, std::path::PathBuf, BTreeMap<u128, u32>)> {
    // RAW, non-canonical keys (header canonical=false; sorted=true so each
    // shard inherits an ascending run in RAW order — the honest pre-fix
    // input shape). ALL_T_RAW is the meet-and-sum/order discriminator; the
    // rest are 24-bit filler keys (high byte 0x00 at k=16) with distinct
    // counts.
    let a_pairs: Vec<(u128, u32)> = vec![
        (ALL_T_RAW, 3),
        (0xFF1234, 7),
        (0xAB8053, 4),
        (0x010000, 5),
        (0x0000AB, 6),
        (0x7F1234, 2),
    ];
    let a = RKDatabase::from_kmer_pairs(a_pairs.clone(), K, false, true)?;
    let a_path = dir.join("mixed_input_a.rkdb");
    a.to_file_path(&a_path)?;

    // Canonical keys (header canonical=true). 0x0100_0000 is a TRUE
    // high-byte-0x01 key at k=16 (a full 32-bit literal — the plan's
    // 24-bit literals `0x010000`/`0x400000` all have high byte 0x00, so
    // without it every record collapses into bucket 0x00 and the
    // concatenation boundary is never exercised); it makes bucket 0x01
    // non-empty so the raw all-T key's misplacement into bucket 0x00 is
    // RED-provable as an ORDER violation, not just a content one.
    let b_pairs: Vec<(u128, u32)> = vec![
        (0x000000, 5),
        (0x000001, 9),
        (0x010001, 11),
        (0x400000, 4),
        (0x0100_0000, 13),
    ];
    let b = RKDatabase::from_kmer_pairs(b_pairs.clone(), K, true, true)?;
    let b_path = dir.join("mixed_input_b.rkdb");
    b.to_file_path(&b_path)?;

    // The oracle: fold every input pair through the PRODUCTION
    // canonicalization, summing counts.
    let mut oracle: BTreeMap<u128, u32> = BTreeMap::new();
    for (kmer, count) in a_pairs.iter().chain(b_pairs.iter()) {
        *oracle
            .entry(canonical_kmer_u128(*kmer, K as usize)?)
            .or_insert(0) += *count;
    }

    // Fixture honesty guards.
    for (kmer, _) in &b_pairs {
        assert_eq!(
            canonical_kmer_u128(*kmer, K as usize)?,
            *kmer,
            "fixture honesty: input-B key {kmer:#010x} must already be canonical"
        );
    }
    let mut differing_high_bytes = 0usize;
    for (kmer, _) in &a_pairs {
        let canonical = canonical_kmer_u128(*kmer, K as usize)?;
        if (canonical >> 24) != (*kmer >> 24) {
            differing_high_bytes += 1;
        }
    }
    assert!(
        differing_high_bytes >= 1,
        "fixture honesty (the vacuousness guard): at least one input-A raw key \
         must canonicalize into a DIFFERENT high byte than its raw form"
    );
    assert_eq!(
        oracle.get(&0x000000),
        Some(&8),
        "fixture honesty: the raw all-T key (count 3) and input B's canonical \
         0x000000 (count 5) are two encodings of ONE k-mer — the oracle must \
         hold them SUMMED"
    );
    assert!(
        !oracle.contains_key(&ALL_T_RAW),
        "fixture honesty: the raw all-T encoding must not survive as its own \
         oracle key — it canonicalizes to 0x000000"
    );

    Ok((a_path, b_path, oracle))
}

/// CR-02, end-to-end: a prefix-cache-merged database is globally ascending
/// with a truthful `sorted` flag, answers every `query_kmer` and the prefix
/// extraction exactly per the oracle, and conserves content.
#[test]
fn prefix_cache_output_is_globally_sorted_and_queries_correctly() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;
    let (a_path, b_path, oracle) = build_inputs(dir.path())?;

    let out = work.path().join("merged_prefix_cache.rkdb");
    RKDatabase::merge_databases_to_path(
        &[a_path, b_path],
        &prefix_cache_config(work.path()),
        &out,
    )?;
    let db = RKDatabase::from_file_path(&out)?;

    // ORDER: strictly ascending across the WHOLE entries vector (keys are
    // distinct post-merge), and the header's sorted flag is truthful.
    // Pre-fix this fired on the discriminator pair: 0x010000 (bucket 0 under
    // low-byte bucketing) was written before 0x0000FF (bucket 255).
    assert!(
        db.entries.windows(2).all(|w| w[0].kmer < w[1].kmer),
        "prefix-cache output must be globally ascending by encoded u128"
    );
    assert!(
        db.header.sorted,
        "the header must not claim sorted: true unless it is"
    );

    // QUERY — the consumer proof: for every oracle (kmer, count), the
    // binary search `query_kmer` runs on the (now truthful) sorted flag
    // returns the exact oracle count. Pre-fix, binary_search_kmer over
    // non-ascending entries returned None or a wrong count for at least the
    // discriminator keys.
    for (kmer, count) in &oracle {
        let query_string = decode_kmer_u128(*kmer, K as usize);
        assert_eq!(
            db.query_kmer(&query_string),
            Some(*count as u64),
            "query_kmer must return the oracle count for k-mer {kmer:#010x} ({query_string})"
        );
    }
    // One negative: a well-formed k-mer absent from the oracle -> None.
    let absent = decode_kmer_u128(0x020000, K as usize);
    assert_eq!(
        db.query_kmer(&absent),
        None,
        "an absent k-mer must query to None"
    );

    // PREFIX EXTRACTION: the 2-base prefix of the crafted 0xAB family,
    // computed by decoding a representative member (never hand-copied).
    let representative = decode_kmer_u128(PREFIX_FAMILY_REPRESENTATIVE, K as usize);
    let prefix = representative[..2].to_string();
    let result = extract_prefix_optimized(&db, &prefix)?;
    let expected: std::collections::BTreeSet<(String, u64)> = oracle
        .iter()
        .filter(|(&kmer, _)| decode_kmer_u128(kmer, K as usize).starts_with(prefix.as_str()))
        .map(|(&kmer, &count)| (decode_kmer_u128(kmer, K as usize), count as u64))
        .collect();
    let observed: std::collections::BTreeSet<(String, u64)> =
        result.matches.iter().cloned().collect();
    assert_eq!(
        result.total_matches,
        expected.len(),
        "extract_prefix_optimized(\"{prefix}\") must find exactly the oracle subset"
    );
    assert_eq!(
        observed, expected,
        "extract_prefix_optimized(\"{prefix}\") matches must equal the oracle subset"
    );

    // CONTENT: conservation survived the re-bucketing — the same records
    // with the same counts as the input-only oracle.
    assert_eq!(
        decode_observations(&db),
        oracle,
        "content conservation: every output (kmer, summed count) must equal the oracle entry"
    );
    assert_eq!(
        db.header.total_kmers,
        oracle.len() as u64,
        "header total_kmers must equal the oracle's unique-k-mer count"
    );

    Ok(())
}

/// Route parity of ANSWERS: the same two inputs merged through the in-memory
/// route produce a database whose decoded map equals the prefix-cache
/// output's, and `query_kmer` agrees on every oracle key — no merge route
/// answers queries differently than another (the MERGE-04-shaped guarantee
/// at the data level).
#[test]
fn prefix_cache_answers_match_the_inmemory_route() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;
    let (a_path, b_path, oracle) = build_inputs(dir.path())?;

    // The prefix-cache output.
    let out_prefix_cache = work.path().join("parity_prefix_cache.rkdb");
    RKDatabase::merge_databases_to_path(
        &[a_path.clone(), b_path.clone()],
        &prefix_cache_config(work.path()),
        &out_prefix_cache,
    )?;
    let prefix_cache_db = RKDatabase::from_file_path(&out_prefix_cache)?;

    // The in-memory output. Route-proof discipline (inherited from 03-04):
    // the budget is DERIVED from the estimator and asserted to exceed the
    // in-memory estimate first, so a shrunken fixture turns into a loud
    // failure instead of a silently vacuous routing arm.
    let total_kmers = [a_path.clone(), b_path.clone()]
        .iter()
        .map(|path| RKDatabase::estimate_total_kmers(path))
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .fold(0u64, u64::saturating_add);
    let estimated = RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, total_kmers);
    let budget = estimated.saturating_add(1) as usize;
    assert!(
        budget as u64 > estimated,
        "route-proof guard: the memory budget ({budget}) must exceed the in-memory estimate \
         ({estimated} bytes for {total_kmers} k-mers)"
    );
    let memory_config = MergeConfig {
        use_prefix_cache: false,
        merge_mode: "memory".to_string(),
        max_memory_usage: budget,
        temp_dir: work.path().to_path_buf(),
        ..Default::default()
    };
    let out_memory = work.path().join("parity_memory.rkdb");
    RKDatabase::merge_databases_to_path(&[a_path, b_path], &memory_config, &out_memory)?;
    let memory_db = RKDatabase::from_file_path(&out_memory)?;

    // Route parity of answers: identical decoded maps...
    assert_eq!(
        decode_observations(&prefix_cache_db),
        decode_observations(&memory_db),
        "the prefix-cache and in-memory routes must produce identical (kmer, count) maps"
    );
    // ...and identical query_kmer answers on every oracle key.
    for (kmer, count) in &oracle {
        let query_string = decode_kmer_u128(*kmer, K as usize);
        let from_prefix_cache = prefix_cache_db.query_kmer(&query_string);
        let from_memory = memory_db.query_kmer(&query_string);
        assert_eq!(
            from_prefix_cache, from_memory,
            "routes disagree on the answer for k-mer {kmer:#010x} ({query_string})"
        );
        assert_eq!(
            from_prefix_cache,
            Some(*count as u64),
            "both routes must return the oracle count for k-mer {kmer:#010x}"
        );
    }

    Ok(())
}

/// CR-01/WR-03 (03-16), end-to-end: a MIXED-canonical input pair (input[0]
/// NON-canonical with raw keys, input[1] canonical) merged through the
/// prefix-cache route produces globally ascending output under a truthful
/// `sorted: true` header, content equal to the input-only canonicalizing
/// oracle (the two encodings of one k-mer SUMMED into one record), exact
/// `query_kmer` answers for every oracle key through the binary-search
/// path (plus one asserted-absent negative), and a `canonical: true` header
/// under ANY-input semantics.
#[test]
fn mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;
    let (a_path, b_path, oracle) = build_mixed_canonical_inputs(dir.path())?;

    let out = work.path().join("merged_prefix_cache_mixed_order.rkdb");
    RKDatabase::merge_databases_to_path(
        &[a_path, b_path],
        &prefix_cache_config(work.path()),
        &out,
    )?;
    let db = RKDatabase::from_file_path(&out)?;

    // ORDER: strictly ascending across the WHOLE entries vector, and the
    // header's sorted flag is truthful. Pre-fix this fired on the raw all-T
    // key: bucketed into bucket 0x00 by its canonical form 0x000000 but
    // WRITTEN raw as 0xFFFFFFFF, it was emitted at the end of bucket 0x00 —
    // ahead of bucket 0x01's and bucket 0x40's much smaller keys.
    assert!(
        db.entries.windows(2).all(|w| w[0].kmer < w[1].kmer),
        "mixed-canonical prefix-cache output must be globally ascending by encoded u128"
    );
    assert!(
        db.header.sorted,
        "the header must not claim sorted: true unless it is"
    );

    // CONTENT: conservation through canonicalization — the raw all-T record
    // and input B's canonical 0x000000 record meet in one bucket and SUM.
    // Pre-fix this failed with the two encodings as separate un-summed
    // records (0xFFFFFFFF/3 and 0x000000/5 where the oracle holds 8).
    assert_eq!(
        decode_observations(&db),
        oracle,
        "content conservation: every output (kmer, summed count) must equal the \
         canonicalizing input-only oracle"
    );
    assert_eq!(
        db.header.total_kmers,
        oracle.len() as u64,
        "header total_kmers must equal the oracle's unique-k-mer count"
    );

    // QUERY — the consumer proof: for every oracle key, `query_kmer`'s
    // binary search (header sorted: true) returns the exact oracle count.
    // Every oracle key IS canonical, so the decoded query string encodes to
    // the stored orientation.
    for (kmer, count) in &oracle {
        let query_string = decode_kmer_u128(*kmer, K as usize);
        assert_eq!(
            db.query_kmer(&query_string),
            Some(*count as u64),
            "query_kmer must return the oracle count for k-mer {kmer:#010x} ({query_string})"
        );
    }

    // One negative: a well-formed candidate whose canonical form is ASSERTED
    // absent from the oracle must query to None.
    let absent_candidate = 0x020000u128;
    let absent_canonical = canonical_kmer_u128(absent_candidate, K as usize)?;
    assert!(
        !oracle.contains_key(&absent_canonical),
        "negative-query guard: the candidate's canonical form must be absent from the oracle"
    );
    assert_eq!(
        db.query_kmer(&decode_kmer_u128(absent_canonical, K as usize)),
        None,
        "an absent canonical k-mer must query to None"
    );

    // HEADER: ANY-input canonical semantics — the output flag is true iff
    // at least one input is canonical. Input[0] (A) here is NON-canonical,
    // so this pin cannot pass by coincidence of input order.
    assert!(
        db.header.canonical,
        "mixed-canonical output header must be canonical (ANY-input semantics; \
         input[0] is NON-canonical)"
    );

    Ok(())
}
