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
//! `mod common;` is deliberately omitted — this binary builds its fixtures
//! directly so the counts it needs are stated literally at the call site
//! rather than buried in a shared factory. Same reasoning as
//! `tests/dense_differential_tests.rs`.
//!
//! No `unsafe`, no pyo3, no new dependencies.

use anyhow::Result;
use rustkmer::database::format::KmerEntry;
use std::io::Cursor;

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
    let mut buf = Vec::with_capacity(RKDB_V2_RECORD_SIZE);
    buf.extend_from_slice(&2_000_000u128.to_le_bytes());
    buf.extend_from_slice(&5u32.to_le_bytes());

    let decoded = KmerEntry::read_from(&mut Cursor::new(buf))?;
    assert_eq!(
        (decoded.kmer, decoded.count),
        (2_000_000u128, 5u32),
        "a hand-written little-endian record read back as k-mer {} / count {} — \
         the pre-fix reader returned 2156142080 here",
        decoded.kmer,
        decoded.count
    );
    Ok(())
}
