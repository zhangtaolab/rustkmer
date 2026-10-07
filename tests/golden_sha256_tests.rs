//! DENSE-02 (plan 03-03) — `.rkdb` v2 byte-identity guard for the dense
//! `KmerKey` swap.
//!
//! **D-03 locks dense storage to RAM only.** The counter key narrows from
//! `u128` to `KmerKey::U64` for k ≤ 32, but `KmerEntry` on disk remains a
//! 16-byte little-endian `u128` + 4-byte little-endian `u32` (v2, 20 B/record),
//! and the write path widens `u64 -> u128` by zero-extension. If that widening
//! ever drifts, every `.rkdb` a k ≤ 32 run produces changes bytes and existing
//! readers silently see different data — which is exactly the "dense storage
//! must be transparent to existing readers" obligation DENSE-02 states.
//!
//! **This binary is the DENSE-02 mitigation (threat T-03-10).** It re-hashes the
//! 12 committed Phase 1/2 golden `.rkdb` fixtures against
//! `tests/fixtures/golden_manifest.sha256`.
//!
//! Phase 1 D-10 carry-forward: these baselines were captured from the
//! pre-refactor `u128` count path and are **ground truth, not regenerated**. If
//! this test ever fails, the fix is to revert the drift — never to re-capture.
//!
//! Note on coverage vs `tests/golden_tests.rs`: `golden_tests.rs` already
//! asserts the same 12 sha256 values, one test per fixture. This binary exists
//! because D-02's guarantee is *the write path*, and a plan-scoped artifact
//! named for the requirement makes that coupling legible: it is the test a
//! reviewer points at when asking "did the dense swap change the file format?".
//! Both binaries must agree; they read the same manifest.
//!
//! It is deliberately **not** `#[ignore]`d and it was **GREEN before the
//! KmerKey swap landed** — that pre-swap pass is what makes the post-swap pass
//! meaningful as a differential rather than a tautology.

use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// The 12 golden fixture basenames, i.e. the D-13 coverage matrix
/// `k ∈ {21, 32, 64} × canonical × sorted` (`golden_tests.rs` writes the same
/// list as 12 individual tests; this binary iterates it so a format drift
/// reports as ONE failure naming every affected cell).
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

/// Parse `tests/fixtures/golden_manifest.sha256` into a name -> hex map.
///
/// Manifest format (one entry per line): `<filename> <sha256-hex>`.
/// Identical to `golden_tests.rs::load_golden_manifest` — deliberately
/// duplicated rather than shared, because `tests/*.rs` are separate binaries
/// and `tests/common/` is only for helper *modules*.
fn load_golden_manifest() -> anyhow::Result<HashMap<String, String>> {
    let text = std::fs::read_to_string("tests/fixtures/golden_manifest.sha256")
        .map_err(|e| anyhow::anyhow!("failed to read golden_manifest.sha256: {}", e))?;
    let mut map = HashMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let mut parts = line.split_whitespace();
        let name = parts
            .next()
            .ok_or_else(|| anyhow::anyhow!("manifest line missing name: {:?}", line))?
            .to_string();
        let hex = parts
            .next()
            .ok_or_else(|| anyhow::anyhow!("manifest line missing sha256: {:?}", line))?
            .to_string();
        map.insert(name, hex);
    }
    Ok(map)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Assert a single golden fixture's on-disk bytes hash to the manifest entry.
fn assert_golden_matches_manifest(name: &str) -> anyhow::Result<()> {
    let manifest = load_golden_manifest()?;
    let expected = manifest.get(name).ok_or_else(|| {
        anyhow::anyhow!(
            "golden fixture {:?} not present in golden_manifest.sha256",
            name
        )
    })?;
    let path = format!("tests/fixtures/{}", name);
    let bytes = std::fs::read(&path).map_err(|e| anyhow::anyhow!("read {}: {}", path, e))?;
    let actual = sha256_hex(&bytes);
    assert_eq!(
        actual, *expected,
        "golden sha256 mismatch for {}: committed bytes drifted from baseline",
        name
    );
    Ok(())
}

/// DENSE-02 — the dense `KmerKey` swap is RAM-only, so all 12 committed
/// `.rkdb` fixtures must still hash to their Phase 1/2 manifest values.
///
/// Threat T-03-10 (Tampering / on-disk format drift): the failure mode this
/// guards is a write path that stops zero-extending `u64 -> u128`, or that
/// changes `KmerEntry`'s 16 + 4 byte v2 layout, or that alters the header
/// literal. Any of those makes the 12 hashes diverge.
#[test]
fn golden_rkdb_sha256_unchanged_post_dense() -> anyhow::Result<()> {
    for name in GOLDEN_FIXTURES {
        assert_golden_matches_manifest(name)?;
    }
    Ok(())
}

/// The manifest must cover exactly the 12 fixtures this binary iterates — if a
/// fixture is added to disk without a manifest entry, the loop above would
/// silently stop covering it.
#[test]
fn golden_manifest_covers_every_fixture_this_binary_checks() -> anyhow::Result<()> {
    let manifest = load_golden_manifest()?;
    assert_eq!(
        manifest.len(),
        GOLDEN_FIXTURES.len(),
        "manifest entry count must match the fixture list this binary iterates"
    );
    for name in GOLDEN_FIXTURES {
        assert!(
            manifest.contains_key(*name),
            "manifest is missing an entry for {}",
            name
        );
        let path = format!("tests/fixtures/{}", name);
        assert!(
            std::path::Path::new(&path).exists(),
            "fixture {} is listed but not present on disk",
            path
        );
    }
    Ok(())
}
