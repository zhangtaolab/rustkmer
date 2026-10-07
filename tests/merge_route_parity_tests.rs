//! MERGE-02 route parity above the old endianness threshold — closes gap
//! **G3** (code-review finding **CR-01**).
//!
//! ## The gap
//!
//! `KmerEntry::write_to` always emits a 4-byte **little-endian** count, while
//! the pre-fix `KmerEntry::read_from` carried an endianness heuristic: if the
//! little-endian read produced a count above `1_000_000`, it re-read the same
//! four bytes as big-endian. On valid input that is not a compatibility
//! feature — it is silent data corruption. Measured, by the phase verifier:
//!
//! ```text
//! true =    999999  ->    999999  OK
//! true =   1000001  -> 1094848256  CORRUPTED
//! true =   2000000  -> 2156142080  CORRUPTED
//! true =  16777216  ->         1  CORRUPTED
//! ```
//!
//! Phase 3 made the corruption **route-dependent**. The in-memory merge read
//! each input once (one swap). The streaming merge read the input (swap 1),
//! wrote the sorted chunk back little-endian, and read the chunk out again
//! (swap 2) — so the double swap cancelled *by accident* and the streaming
//! route happened to be right. The same input under the same budget therefore
//! produced different data depending only on which route the budget picked:
//!
//! ```text
//! true = 2000000   in-memory = 2156142080   streaming = 2000000   *** DISAGREE ***
//! ```
//!
//! Note `16_777_216` was wrong on **both** routes, so a parity test alone
//! cannot catch it — an equality assertion between two equally-wrong routes is
//! green. Every test below therefore also pins the exact expected count.
//!
//! ## Why this binary exists in Rust and not Python
//!
//! `pyo3/tests/test_database_merge.py::test_streaming_and_inmemory_routes_produce_identical_data`
//! already expresses exactly this contract — and is a correct test — but it
//! could never reach the bug, because every fixture count it builds is far
//! below `1_000_000`. It is **deliberately not modified by this plan**: the
//! `pyrustkmer.so` installed in the project venv is a prebuilt artifact, so a
//! Python test run would assert against code that no longer exists on disk —
//! a green that means nothing. Extending the Python fixture set becomes
//! meaningful only once the `pyo3/pyproject.toml` `python-source`
//! misconfiguration (recorded in `deferred-items.md`) is fixed and the
//! extension is rebuilt from source. Until then this file is the only
//! executable evidence for that contract.
//!
//! `mod common;` is deliberately omitted — this binary builds its fixtures
//! directly so the counts it needs are stated literally at the call site
//! rather than buried in a shared factory. Same reasoning as
//! `tests/dense_differential_tests.rs`.
//!
//! No `unsafe`, no pyo3, no new dependencies.

use anyhow::Result;
use rustkmer::database::format::{KmerEntry, RKDatabase};
use rustkmer::database::merge_config::MergeConfig;
use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};
use std::collections::BTreeMap;
use std::io::Cursor;
use std::path::{Path, PathBuf};

/// Decoded k-mer map — the D-04 comparison unit. Never a raw integer: the
/// `u128` encoder and decoder are only guaranteed to invert each other.
type DecodedMap = BTreeMap<String, u32>;

/// k used by the route-parity fixtures — inside the D-13 matrix.
const K: usize = 21;

/// `.rkdb` v2 record size: 16-byte little-endian `u128` k-mer + 4-byte
/// little-endian `u32` count. This is the byte-identity DENSE-02 protects and
/// `record_layout_is_exactly_twenty_bytes_little_endian` asserts field by
/// field — the golden-hash test alone cannot catch a layout change, because it
/// re-hashes static Phase-1 files (the WR-03 finding, closed in plan 03-08).
const RKDB_V2_RECORD_SIZE: usize = 20;

/// The k-mer values crossed with the threshold counts, below.
///
/// `0` and `1` are the ordinary small-count cases; `2^32` and `u128::MAX`
/// probe the k-mer field's own extremes, so a failure localizes to the field
/// that actually broke. `4_000_000_000` and `u32::MAX` probe counts a
/// human-scale count can genuinely reach (a short, highly repetitive read
/// overruns a million occurrences easily).
const KMER_VALUES: [u128; 4] = [0, 1, 1u128 << 32, u128::MAX];

/// Counts that straddle the deleted `1_000_000` heuristic from both sides,
/// plus every value the phase verifier recorded as being corrupted.
///
/// `999_999` and `1_000_000` are the boundary pair — the old heuristic fired
/// on `> 1_000_000`, so `1_000_000` itself was read correctly and the very
/// first corrupted value was `1_000_001`. Pinning the boundary is what makes a
/// re-introduced off-by-one visible.
const THRESHOLD_COUNTS: [u32; 9] = [
    0,
    1,
    999_999,
    1_000_000,
    1_000_001,
    2_000_000,
    16_777_216,
    4_000_000_000,
    u32::MAX,
];

/// Encode one entry and decode it straight back — the exact inverse pair
/// `KmerEntry` is responsible for.
fn round_trip(kmer: u128, count: u32) -> Result<KmerEntry> {
    let mut buf = Vec::with_capacity(RKDB_V2_RECORD_SIZE);
    KmerEntry::new(kmer, count).write_to(&mut buf)?;
    Ok(KmerEntry::read_from(&mut Cursor::new(buf))?)
}

/// CR-01's behavioural half: `write_to` → `read_from` must be the identity on
/// `(kmer, count)` for every k-mer value crossed with every threshold count.
///
/// This is the DISCRIMINATING gate for the heuristic's deletion — it was
/// observed RED against the pre-fix reader, reading `1_000_001` back as
/// `1_094_848_256`, `2_000_000` as `2_156_142_080` and `16_777_216` as `1`. A
/// source grep cannot do this job: `u32::from_le_bytes` was already present
/// *inside* the heuristic being deleted, so its occurrence count was 1 both
/// before and after the fix.
#[test]
fn write_to_read_from_round_trip_is_exact_at_and_above_the_old_threshold() -> Result<()> {
    let mut checked = 0usize;
    for &kmer in KMER_VALUES.iter() {
        for &count in THRESHOLD_COUNTS.iter() {
            let decoded = round_trip(kmer, count)?;
            assert_eq!(
                (decoded.kmer, decoded.count),
                (kmer, count),
                "k-mer {:#x} / count {} round-tripped as k-mer {:#x} / count {} — the \
                 count field is being read with the wrong byte order, or the \
                 record width has drifted",
                kmer,
                count,
                decoded.kmer,
                decoded.count
            );
            checked += 1;
        }
    }
    assert_eq!(
        checked,
        KMER_VALUES.len() * THRESHOLD_COUNTS.len(),
        "not every (kmer, count) pair was exercised — the matrix shrank and the \
         round-trip claim is weaker than it claims to be"
    );
    Ok(())
}

/// DENSE-02's structural half: the `.rkdb` v2 record is exactly 20 bytes —
/// 16 little-endian k-mer bytes then 4 little-endian count bytes, no padding
/// and nothing extra.
///
/// `tests/golden_sha256_tests.rs` re-hashes *static* Phase-1 fixtures, so it
/// stays green even if the writer's layout drifts; only an assertion against a
/// freshly encoded record can observe the drift (the WR-03 finding).
#[test]
fn record_layout_is_exactly_twenty_bytes_little_endian() -> Result<()> {
    for &kmer in KMER_VALUES.iter() {
        for &count in THRESHOLD_COUNTS.iter() {
            let mut buf = Vec::with_capacity(RKDB_V2_RECORD_SIZE);
            KmerEntry::new(kmer, count).write_to(&mut buf)?;

            assert_eq!(
                buf.len(),
                RKDB_V2_RECORD_SIZE,
                "k-mer {:#x} / count {} encoded to {} bytes, not {} — the .rkdb v2 \
                 record layout has drifted",
                kmer,
                count,
                buf.len(),
                RKDB_V2_RECORD_SIZE
            );
            assert_eq!(
                &buf[0..16],
                &kmer.to_le_bytes()[..],
                "k-mer {:#x} did not occupy bytes 0..16 as little-endian",
                kmer
            );
            assert_eq!(
                &buf[16..20],
                &count.to_le_bytes()[..],
                "count {} did not occupy bytes 16..20 as little-endian",
                count
            );
        }
    }
    Ok(())
}

/// The single value the verifier recorded as becoming `2_156_142_080`.
///
/// `16_777_216` is `2^24`, so its big-endian reading is `1` — the value is
/// small enough to look plausible and survives a naive "is the count
/// reasonable?" sanity check. The slice below is written by hand rather than
/// through `write_to`, so it asserts the reader against literal bytes rather
/// than against the writer it is supposed to invert.
#[test]
fn a_hand_written_little_endian_record_reads_back_as_itself() -> Result<()> {
    // Case 1 — the plan's literal tuple: k-mer 2,000,000 with a SMALL count.
    //
    // HONESTY NOTE: this case is NOT a discriminator. The heuristic fired on
    // the COUNT field, and a count of 5 never exceeds the threshold, so this
    // half is green against the pre-fix reader too. It is kept because it
    // pins the field ORDER from literal bytes — that the count occupies
    // 16..20 and not, say, 0..4 — which the round-trip matrix above cannot see
    // (it validates the reader against the writer, and would pass if BOTH
    // swapped the field order consistently).
    let mut small = Vec::with_capacity(RKDB_V2_RECORD_SIZE);
    small.extend_from_slice(&2_000_000u128.to_le_bytes());
    small.extend_from_slice(&5u32.to_le_bytes());
    let decoded_small = KmerEntry::read_from(&mut Cursor::new(small))?;
    assert_eq!(
        (decoded_small.kmer, decoded_small.count),
        (2_000_000u128, 5u32),
        "a hand-written record with a small count read back as k-mer {} / \
         count {} — the count field is not occupying bytes 16..20",
        decoded_small.kmer,
        decoded_small.count
    );

    // Case 2 — the DISCRIMINATING half: the verifier's 2_000_000 corruption
    // was a COUNT of 2,000,000, not a k-mer of 2,000,000. Written as literal
    // bytes so the reader is judged against the format rather than against the
    // writer it is meant to invert. Observed RED against the pre-fix reader,
    // which returned 2_156_142_080.
    for (kmer, count) in [
        (2_000_000u128, 2_000_000u32),
        (1u128, 16_777_216),
        (u128::MAX, 4_000_000_000),
    ] {
        let mut buf = Vec::with_capacity(RKDB_V2_RECORD_SIZE);
        buf.extend_from_slice(&kmer.to_le_bytes());
        buf.extend_from_slice(&count.to_le_bytes());
        assert_eq!(
            buf.len(),
            RKDB_V2_RECORD_SIZE,
            "the hand-written literal is not a 20-byte record"
        );

        let decoded = KmerEntry::read_from(&mut Cursor::new(buf))?;
        assert_eq!(
            (decoded.kmer, decoded.count),
            (kmer, count),
            "a hand-written little-endian record (k-mer {:#x}, count {}) read back \
             as k-mer {:#x} / count {} — the pre-fix reader returned the \
             byte-swapped value here",
            kmer,
            count,
            decoded.kmer,
            decoded.count
        );
    }
    Ok(())
}

/// Encode a real k-mer at k=21 whose first `K - 2` bases are all `head` and
/// whose last two carry `i` in base 4.
///
/// Varying only the LAST base over `["A","C","G","T"]` yields four distinct
/// k-mers, not eight — the first draft of this fixture did exactly that and
/// `dedup` shrank it to 4, so the "8 distinct k-mers" guarantee below caught
/// it. Two varied positions give 16.
fn fixture_kmer(head: char, i: usize) -> Result<u128> {
    const ALPHABET: [char; 4] = ['A', 'C', 'G', 'T'];
    let mut seq = String::with_capacity(K);
    seq.extend(std::iter::repeat_n(head, K - 2));
    seq.push(ALPHABET[(i / 4) % 4]);
    seq.push(ALPHABET[i % 4]);
    Ok(encode_kmer_bytes_u128(seq.as_bytes())?)
}

/// Build a merge fixture pair where ONE designated k-mer carries `big_count`
/// in input A **only**.
///
/// Input B is built from a different `head` base, so its eight k-mers are
/// disjoint from A's. That disjointness is load-bearing: the in-memory route
/// accumulates with `saturating_add`, so if the designated k-mer were present
/// in both inputs the merged count would be `2 * big_count` and the fixture
/// could no longer distinguish "read correctly" from "summed twice".
fn write_fixture_pair(
    dir: &Path,
    label: &str,
    big_count: u32,
) -> Result<(PathBuf, PathBuf, Vec<u128>, u128)> {
    let mut shared = Vec::with_capacity(8);
    for i in 0..8usize {
        shared.push(fixture_kmer('A', i)?);
    }
    shared.sort_unstable();
    shared.dedup();
    anyhow::ensure!(
        shared.len() == 8,
        "fixture must yield 8 distinct k-mers, got {}",
        shared.len()
    );

    // Input A holds every shared k-mer; the FIRST one additionally carries the
    // above-threshold count.
    let designated = shared[0];
    let a_pairs: Vec<(u128, u32)> = shared
        .iter()
        .enumerate()
        .map(|(i, &k)| (k, if i == 0 { big_count } else { (i + 1) as u32 }))
        .collect();

    // Input B holds a DISJOINT set of eight, all with small counts.
    let mut b_pairs = Vec::with_capacity(8);
    for i in 0..8usize {
        b_pairs.push((fixture_kmer('C', i)?, (i + 1) as u32));
    }
    b_pairs.sort_by_key(|(k, _)| *k);

    anyhow::ensure!(
        a_pairs
            .iter()
            .all(|(k, _)| !b_pairs.iter().any(|(bk, _)| bk == k)),
        "fixture inputs overlap, so the designated count could be a sum of two \
         rather than the single value under test"
    );

    let a = RKDatabase::from_kmer_pairs(a_pairs, K as u8, true, true)?;
    let b = RKDatabase::from_kmer_pairs(b_pairs, K as u8, true, true)?;

    let a_path = dir.join(format!("{}_a.rkdb", label));
    let b_path = dir.join(format!("{}_b.rkdb", label));
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    Ok((a_path, b_path, shared, designated))
}

/// Decode an `RKDatabase`'s entries to a `BTreeMap<String, u32>`.
///
/// D-04 discipline: compare at the DECODED level, never as raw integers —
/// `decode_kmer_u128` is the inverse of `encode_kmer_bytes_u128`, the encoder
/// these fixtures were built with.
fn decoded_map(db: &RKDatabase) -> DecodedMap {
    db.entries
        .iter()
        .map(|e| (decode_kmer_u128(e.kmer, K), e.count))
        .collect()
}

/// A path that does not exist, used as the ROUTE PROBE.
///
/// The streaming route writes sorted chunk files into `config.temp_dir`; the
/// in-memory route never touches it. Pointing `temp_dir` at a nonexistent
/// directory therefore turns path selection into an observable outcome — `Ok`
/// proves the in-memory route ran, `Err` proves the streaming route did. This
/// is the same side-effect discriminator plan 03-01 introduced; reusing it
/// avoids inventing a weaker signal (log capture, or a strategy value the API
/// does not return).
fn missing_temp_dir(root: &Path) -> PathBuf {
    root.join("rustkmer_route_probe_this_dir_does_not_exist")
}

/// Merge the fixture pair twice and return both arms' decoded maps, having
/// PROVEN which route each arm took.
///
/// Returns `(streaming_map, in_memory_map)`. Each arm's route is established
/// before its data is read, so a mis-proven route cannot make the equality
/// assertion pass vacuously.
fn both_routes(
    dir: &Path,
    a: &Path,
    b: &Path,
    designated: u128,
) -> Result<(DecodedMap, DecodedMap)> {
    let inputs = vec![a.to_path_buf(), b.to_path_buf()];

    // --- Derived below-estimate budget -----------------------------------
    //
    // DERIVED, never hard-coded (the lesson of plan 03-04, whose first draft
    // used a literal budget against a fixture needing only 960 bytes — every
    // "streaming" arm silently took the in-memory path and the whole claim was
    // vacuous). `estimate_total_kmers` is the production header-only
    // estimator, so the budget tracks whatever admission model is live at run
    // time.
    let mut estimated_kmers: u64 = 0;
    for path in &inputs {
        estimated_kmers = estimated_kmers.saturating_add(RKDatabase::estimate_total_kmers(path)?);
    }
    let below_estimate = estimated_kmers.saturating_sub(1);

    // The whole point of the derived budget: prove the estimate really does
    // exceed it, so a shrunken fixture fails LOUDLY instead of quietly turning
    // the streaming arm into an in-memory arm.
    assert!(
        estimated_kmers > below_estimate,
        "derived estimate {} must exceed the Arm-A budget {} — the fixture shrank \
         and the streaming arm may no longer be reachable",
        estimated_kmers,
        below_estimate
    );
    assert!(
        estimated_kmers > 0,
        "fixture must hold k-mers for the route split to be reachable at all"
    );

    let real_temp = dir.join("real_temp");
    std::fs::create_dir_all(&real_temp)?;
    let probe_temp = missing_temp_dir(dir);

    // --- Arm A: streaming, budget below the estimate ---------------------
    let streaming_cfg = MergeConfig {
        merge_mode: "auto".to_string(),
        max_memory_usage: below_estimate as usize,
        temp_dir: real_temp.clone(),
        chunk_size: 4,
        ..Default::default()
    };

    // Route probe, same config but a temp_dir that does not exist. ONLY the
    // streaming route can fail here, so `Err` IS the proof.
    let streaming_probe = MergeConfig {
        temp_dir: probe_temp.clone(),
        ..streaming_cfg.clone()
    };
    let probe_err = match RKDatabase::merge_databases(&inputs, &streaming_probe) {
        Ok(_) => anyhow::bail!(
            "Arm A was supposed to take the streaming route, but the merge \
             succeeded with a nonexistent temp_dir — only the streaming route \
             creates chunk files there, so the in-memory route ran and every \
             streaming assertion below would be vacuous"
        ),
        Err(e) => e,
    };
    let probe_msg = probe_err.to_string();
    assert!(
        probe_msg.contains("temp") || probe_msg.contains("No such file"),
        "the Arm-A probe must fail on the missing temp directory to prove the \
         streaming route ran; got: {}",
        probe_msg
    );

    let streaming = RKDatabase::merge_databases(&inputs, &streaming_cfg)?;
    let streaming_map = decoded_map(&streaming);

    // --- Arm B: in-memory, generous budget -------------------------------
    //
    // `n * 96 * 4`. The in-memory admission constant is 96 B/k-mer in plan
    // 03-09 and 24 today, and this margin exceeds BOTH — so this arm takes
    // the in-memory route whether or not 03-09 has landed. No per-k-mer
    // admission constant is PINNED in this file: a whole-file grep for the
    // admission-constant identifier must print 0, because a literal here would
    // be invalidated by the very next wave.
    // If the model ever grows past 384 B/k-mer this arm hits the D-02 `Err`
    // and the test fails loudly — the intended alarm, not a silent flip.
    let n = estimated_kmers;
    let in_memory_budget = n.saturating_mul(96).saturating_mul(4);
    let in_memory_cfg = MergeConfig {
        merge_mode: "memory".to_string(),
        max_memory_usage: in_memory_budget as usize,
        // The SAME nonexistent path as Arm A: `merge_mode: "memory"` with a
        // temp_dir that does not exist SUCCEEDS, which the streaming route
        // could not. That `Ok` IS the in-memory route proof.
        temp_dir: probe_temp,
        ..Default::default()
    };

    let in_memory = RKDatabase::merge_databases(&inputs, &in_memory_cfg)?;
    let in_memory_map = decoded_map(&in_memory);

    // The designated k-mer must be present on BOTH arms — otherwise the count
    // assertion below would be checking `None == None`.
    let designated_str = decode_kmer_u128(designated, K);
    assert!(
        streaming_map.contains_key(&designated_str) && in_memory_map.contains_key(&designated_str),
        "the designated k-mer {} is missing from one arm — the fixture is broken",
        designated_str
    );

    Ok((streaming_map, in_memory_map))
}

/// Assert one route-parity claim over a freshly built fixture pair.
fn assert_routes_agree(dir: &Path, label: &str, big_count: u32) -> Result<()> {
    let (a, b, shared, designated) = write_fixture_pair(dir, label, big_count)?;
    let designated_str = decode_kmer_u128(designated, K);

    let (streaming_map, in_memory_map) = both_routes(dir, &a, &b, designated)?;

    // The union the merge must have produced: A's eight k-mers plus B's eight
    // disjoint ones. Asserting this first means an empty or half-read map
    // cannot pass by being "equal to itself".
    assert_eq!(
        streaming_map.len(),
        16,
        "Arm {}: streaming route merged {} distinct k-mers, expected 16 (8 from \
         each disjoint input)",
        label,
        streaming_map.len()
    );

    assert_eq!(
        streaming_map, in_memory_map,
        "Arm {}: the streaming and in-memory routes produced DIFFERENT DATA for \
         the same input under comparable budgets — this is exactly the defect \
         CR-01 describes",
        label
    );

    // Equality alone is not enough: 16_777_216 was wrong on BOTH routes, so an
    // equal-but-wrong pair would be green. Pin the exact value.
    assert_eq!(
        streaming_map.get(&designated_str).copied(),
        Some(big_count),
        "Arm {}: streaming route returned count {} for the designated k-mer, \
         expected {}",
        label,
        streaming_map.get(&designated_str).copied().unwrap_or(0),
        big_count
    );
    assert_eq!(
        in_memory_map.get(&designated_str).copied(),
        Some(big_count),
        "Arm {}: in-memory route returned count {} for the designated k-mer, \
         expected {} — the pre-fix reader returned the byte-swapped value here",
        label,
        in_memory_map.get(&designated_str).copied().unwrap_or(0),
        big_count
    );

    // The seven shared k-mers carry small counts in A and must survive exactly.
    for (i, &k) in shared.iter().enumerate().skip(1) {
        let s = decode_kmer_u128(k, K);
        assert_eq!(
            streaming_map.get(&s).copied(),
            Some((i + 1) as u32),
            "Arm {}: streaming route lost or altered the count of a shared k-mer",
            label
        );
    }

    Ok(())
}

/// MERGE-02 route parity at count `2_000_000` — the value the phase verifier
/// recorded as `2_156_142_080` on the in-memory route and correct on the
/// streaming route, i.e. the case where the routes demonstrably disagreed.
#[test]
fn routes_agree_and_are_exact_at_count_two_million() -> Result<()> {
    let dir = tempfile::tempdir()?;
    assert_routes_agree(dir.path(), "two_million", 2_000_000)
}

/// MERGE-02 route parity at count `16_777_216` — the value that was wrong on
/// **BOTH** routes (`2^24` byte-swaps to `1`). A route-parity test alone
/// cannot catch this; the exact-count assertions can.
#[test]
fn routes_agree_and_are_exact_at_count_sixteen_million() -> Result<()> {
    let dir = tempfile::tempdir()?;
    assert_routes_agree(dir.path(), "sixteen_million", 16_777_216)
}
