//! CLI merge front-end validation tests (Phase 3, plan 03-14 — gap WR-05).
//!
//! Requirement covered:
//!   - **MERGE-01** at the CLI surface — "A merge invoked through the CLI
//!     front-end does not materialize input databases — compatibility
//!     validation reads 42-byte headers only" (03-VERIFICATION.md gaps[3]).
//!
//! ## The header-only proof strategy
//!
//! `validate_merge_compatibility` is asserted against inputs whose HEADERS are
//! valid but whose BODIES are absent (a well-formed `.rkdb` truncated to
//! exactly its 42-byte header). The materializing loader
//! (`RKDatabase::from_file_path`) provably FAILS on such a file — it tries to
//! read `header.total_kmers` 20-byte records past EOF — so if the front-end
//! returns `Ok(())` on these inputs, the validation CANNOT have loaded a body.
//! This mirrors `header_only_read_agrees_with_the_materializing_loader` in
//! `tests/merge_routing_tests.rs` (the same premise discipline: the loader's
//! failure is ASSERTED, not assumed, or the `Ok` below would prove nothing).
//!
//! The rejection arms pin the CLI's error-UX contract: the k-mismatch message
//! with its recovery bullets, the canonical-mode message, the
//! `Failed to load database` wrapper, and the `--use-prefix-cache` canonical
//! skip (the capability the prefix-cache route advertises).

use rustkmer::cli::commands::merge::validate_merge_compatibility;
use rustkmer::database::format::RKDatabase;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Command;

/// The `.rkdb` v2 header is exactly 42 bytes (see `DatabaseHeader::write_to`).
const HEADER_BYTES: u64 = 42;

/// Build a small well-formed `.rkdb` with `declared` records, then truncate
/// the file to exactly the 42-byte header.
///
/// The result is a file whose header parses cleanly (valid magic, version,
/// `data_offset == 42`, a persisted record count) but whose body is absent.
/// `RKDatabase::from_file_path` MUST fail on it; `read_header_of` MUST
/// succeed. That asymmetry is the discriminator the header-only property is
/// proven with.
fn truncated_header_db(dir: &Path, name: &str, k: u8, declared: u64, canonical: bool) -> PathBuf {
    assert!(
        declared >= 1,
        "a declared count of 0 would make the empty body legitimate"
    );
    let pairs: Vec<(u128, u32)> = (0..declared)
        .map(|i| (0x1000 + i as u128, (i + 1) as u32))
        .collect();
    let path = dir.join(name);
    let db = RKDatabase::from_kmer_pairs(pairs, k, canonical, true)
        .expect("fixture database must build");
    db.to_file_path(&path).expect("fixture database must write");

    let file = std::fs::File::options()
        .write(true)
        .open(&path)
        .expect("fixture must reopen for truncation");
    file.set_len(HEADER_BYTES)
        .expect("fixture must truncate to the 42-byte header");
    path
}

/// A small well-formed (untruncated) fixture database.
fn well_formed_db(
    dir: &Path,
    name: &str,
    pairs: Vec<(u128, u32)>,
    k: u8,
    canonical: bool,
) -> PathBuf {
    let path = dir.join(name);
    let db = RKDatabase::from_kmer_pairs(pairs, k, canonical, true)
        .expect("fixture database must build");
    db.to_file_path(&path).expect("fixture database must write");
    path
}

/// GAP WR-05, behavioral core: the front-end validation reads 42-byte headers
/// only — it returns `Ok` on inputs whose bodies are absent, which any body
/// load would have failed on.
#[test]
fn frontend_validation_reads_headers_only() {
    let dir = tempfile::tempdir().unwrap();
    let a = truncated_header_db(dir.path(), "a_header_only.rkdb", 31, 2, false);
    let b = truncated_header_db(dir.path(), "b_header_only.rkdb", 31, 3, false);

    // PREMISE: the materializing loader fails on these exact files. Without
    // this assertion the Ok below would prove nothing — a validation that
    // loaded bodies would also pass if the loader tolerated truncation.
    assert!(
        RKDatabase::from_file_path(&a).is_err(),
        "premise: the materializing loader must fail on a truncated body, otherwise \
         the Ok below proves nothing"
    );
    assert!(
        RKDatabase::from_file_path(&b).is_err(),
        "premise: the materializing loader must fail on a truncated body, otherwise \
         the Ok below proves nothing"
    );

    // Two body-absent inputs with matching headers validate Ok: the
    // validation cannot have loaded a body (any load would have errored).
    validate_merge_compatibility(&[a.clone(), b.clone()], false, false, true)
        .expect("header-only validation must pass on body-absent inputs whose headers match");

    // Single-input shape: the skip(1) loop is a no-op, but the reference
    // header read still happens (and still must not load a body).
    validate_merge_compatibility(std::slice::from_ref(&a), false, false, true)
        .expect("the single-input shape must still validate header-only");

    // And the prefix-cache shape on the same body-absent pair: k is still
    // checked (headers only), canonical is skipped — Ok either way here.
    validate_merge_compatibility(&[a, b], true, false, true)
        .expect("prefix-cache shape must also validate header-only");
}

/// The CLI's error-UX contract survives the extraction: every rejection the
/// front-end made pre-plan is still made, with the same recovery text, and
/// the `--use-prefix-cache` canonical skip is preserved.
#[test]
fn frontend_validation_rejects_mismatches_with_recovery_text() {
    let dir = tempfile::tempdir().unwrap();
    let k21 = well_formed_db(dir.path(), "k21.rkdb", vec![(0x1, 1)], 21, false);
    let k31 = well_formed_db(dir.path(), "k31.rkdb", vec![(0x2, 1)], 31, false);
    let canon = well_formed_db(dir.path(), "canon.rkdb", vec![(0x3, 1)], 31, true);
    let noncanon = well_formed_db(dir.path(), "noncanon.rkdb", vec![(0x4, 1)], 31, false);

    // (i) k-mer size mismatch: headline + recovery block + the count-command
    // bullet (the third bullet loop 2's prefix-cache message previously
    // lacked — one of the two documented deliberate message deltas).
    let err = validate_merge_compatibility(&[k31.clone(), k21], false, false, true)
        .expect_err("a k=21 input against a k=31 reference must be rejected");
    let msg = format!("{err:#}");
    assert!(
        msg.contains("has k-mer size"),
        "k mismatch must keep its headline; got: {msg}"
    );
    assert!(
        msg.contains("Recovery suggestions"),
        "k mismatch must keep its recovery block; got: {msg}"
    );
    assert!(
        msg.contains("rustkmer count --k"),
        "k mismatch must keep the 'rustkmer count --k' bullet; got: {msg}"
    );

    // (ii) canonical mismatch WITHOUT prefix cache: rejected.
    let err = validate_merge_compatibility(&[noncanon.clone(), canon.clone()], false, false, true)
        .expect_err("a mixed-canonical pair must be rejected without --use-prefix-cache");
    assert!(
        format!("{err:#}").contains("canonical mode"),
        "canonical mismatch must keep its headline; got: {err:#}"
    );

    // (iii) the SAME mixed-canonical pair WITH prefix cache: Ok — the
    // advertised capability (the route converts to canonical), k still
    // checked from headers.
    validate_merge_compatibility(&[noncanon, canon], true, false, true)
        .expect("--use-prefix-cache must skip the canonical check (k still checked)");

    // (iv) unreadable input: the load-failure wrapper survives.
    let missing = dir.path().join("does_not_exist.rkdb");
    let err = validate_merge_compatibility(&[k31.clone(), missing], false, false, true)
        .expect_err("a nonexistent input must be rejected");
    assert!(
        format!("{err:#}").contains("Failed to load database"),
        "an unreadable input must keep the 'Failed to load database' wrapper; got: {err:#}"
    );
}

fn as_str(p: &Path) -> &str {
    p.to_str().expect("temp paths are valid UTF-8")
}

/// Task-2 route wiring smoke, through the REAL CLI binary
/// (`CARGO_BIN_EXE_rustkmer` — clap flag parsing included). Proves the
/// extraction did not break the wiring between the header-only validation
/// and the bounded core: both route shapes merge correctly end-to-end, and
/// a mismatched-k pair is rejected with the recovery text reaching the
/// user's stderr — a front-end rejection, not a core panic.
#[test]
fn cli_smoke_both_routes_and_mismatch_rejection() {
    let dir = tempfile::tempdir().unwrap();
    let a = well_formed_db(
        dir.path(),
        "a.rkdb",
        vec![(0x1234, 10), (0x5678, 20)],
        31,
        false,
    );
    let b = well_formed_db(
        dir.path(),
        "b.rkdb",
        vec![(0x1234, 5), (0x9ABC, 15)],
        31,
        false,
    );
    let bin = env!("CARGO_BIN_EXE_rustkmer");

    let assert_merged_output = |out: &Path, route: &str| {
        let merged = RKDatabase::from_file_path(out)
            .unwrap_or_else(|e| panic!("{route} route: output must be a readable .rkdb: {e}"));
        assert_eq!(
            merged.total_kmers(),
            3,
            "{route} route: 2 unique k-mers in a + 1 additional unique in b"
        );
        let kmer_map: HashMap<u128, u32> = merged
            .all_kmers()
            .unwrap_or_else(|e| panic!("{route} route: all_kmers: {e}"))
            .into_iter()
            .collect();
        assert_eq!(kmer_map.get(&0x1234), Some(&15), "{route}: 10 + 5");
        assert_eq!(kmer_map.get(&0x5678), Some(&20), "{route}");
        assert_eq!(kmer_map.get(&0x9ABC), Some(&15), "{route}");
    };

    // (1) plain route through the real binary.
    let out_plain = dir.path().join("merged_plain.rkdb");
    let status = Command::new(bin)
        .args([
            "merge",
            // MergeArgs declares `num_args = 2..` on --input: ONE `-i`
            // followed by both paths (the module doc's usage shape).
            "-i",
            as_str(&a),
            as_str(&b),
            "-o",
            as_str(&out_plain),
            "-q",
        ])
        .status()
        .expect("the rustkmer binary must launch");
    assert!(status.success(), "plain route must exit 0, got {status}");
    assert_merged_output(&out_plain, "plain");

    // (2) the SAME shape with --use-prefix-cache — the memory-bounded route
    // the WR-05 fix exists to protect (this is the route whose front-end
    // previously full-loaded every input).
    let out_pc = dir.path().join("merged_prefix_cache.rkdb");
    let status = Command::new(bin)
        .args([
            "merge",
            "-i",
            as_str(&a),
            as_str(&b),
            "-o",
            as_str(&out_pc),
            "--use-prefix-cache",
            "-q",
        ])
        .status()
        .expect("the rustkmer binary must launch");
    assert!(
        status.success(),
        "--use-prefix-cache route must exit 0, got {status}"
    );
    assert_merged_output(&out_pc, "prefix-cache");

    // (3) negative smoke: mismatched k through the same invocation shape —
    // non-zero exit whose stderr carries the front-end recovery text.
    let k21 = well_formed_db(dir.path(), "k21.rkdb", vec![(0x5, 1)], 21, false);
    let out_bad = dir.path().join("merged_bad.rkdb");
    let output = Command::new(bin)
        .args([
            "merge",
            "-i",
            as_str(&a),
            as_str(&k21),
            "-o",
            as_str(&out_bad),
        ])
        .output()
        .expect("the rustkmer binary must launch");
    assert!(
        !output.status.success(),
        "a mismatched-k merge must exit non-zero, got {}",
        output.status
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("has k-mer size"),
        "the front-end k rejection must reach the user's stderr; got: {stderr}"
    );
    assert!(
        stderr.contains("Recovery suggestions"),
        "the recovery block must reach the user's stderr; got: {stderr}"
    );
    assert!(
        !out_bad.exists(),
        "a rejected merge must not write its output file"
    );
}
