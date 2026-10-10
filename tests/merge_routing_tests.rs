//! Merge routing + admission-control tests (Phase 3, plan 03-01).
//!
//! Requirements covered:
//!   - **MERGE-01** — "Merge defaults to the streaming/external-sort path;
//!     human-scale merges no longer OOM."
//!   - **MERGE-02** — "Memory-budget admission control — estimate required
//!     memory, route to streaming when estimate exceeds budget."
//!
//! Decisions honored (from `.planning/phases/03-memory-safety/03-CONTEXT.md`):
//!   - **D-01** — the merge estimator must read the persisted `total_kmers`
//!     from the 42-byte `.rkdb` header (or fall back to `file_size / 20`)
//!     WITHOUT materializing entries. The pre-fix estimator called
//!     `RKDatabase::from_file_path(path)` per input purely to read
//!     `total_kmers`, which loads every entry into RAM and OOMs *during the
//!     estimate*, before a merge strategy is even chosen.
//!   - **D-02** — `merge_databases_inmemory` is retained behind an explicit
//!     `--merge-mode memory`, and that mode REJECTS (returns `Err`) when the
//!     estimate exceeds `max_memory_usage` rather than silently OOMing.
//!
//! ## Bounding-proof strategy (RESEARCH: "How to PROVE MERGE-01 without a
//! human-scale dataset in CI")
//!
//! CI has no human-genome data, so the routing LOGIC is proven at toy scale.
//! The logic is size-independent: `sum(total_kmers) * 24 > max_memory_usage`
//! → stream. Shrinking the inputs and the budget together preserves the
//! branch being taken while keeping the test instant.
//!
//! ## How "which merge path ran?" is observed
//!
//! `merge_databases` returns an `RKDatabase`, not a strategy tag, so path
//! selection is observed *behaviorally* using the temp directory as a probe:
//!   - the streaming path writes sorted chunk files into `config.temp_dir`
//!     (`ExternalMerger` → `TempFileManager::create_temp_file` → `File::create`),
//!   - the in-memory path never touches `config.temp_dir` at all.
//!
//! Pointing `temp_dir` at a **nonexistent** directory therefore turns path
//! selection into an observable outcome: `Err` proves the streaming path was
//! entered, `Ok` proves the in-memory path was taken. This is a deterministic
//! side-effect discriminator — it does not depend on log capture, on
//! `log::info!` formatting, or on a strategy value the API does not return.
//!
//! Plan 03-01 Task 1 created this file as the Wave-0 scaffold: the four
//! routing/reject tests began `#[ignore]`d so the target compiled against the
//! PRE-fix API (no test body may reference an API that does not exist yet).
//! Task 2 landed the header-only estimator + the D-02 reject branch, un-ignored
//! all four, and strengthened the D-01 test with direct
//! `RKDatabase::estimate_total_kmers` assertions (header value, well-formed
//! input, `total_kmers == 0` file-size fallback, corrupt-magic fallback).
//!
//! No `unsafe`, no pyo3, no new dependencies.

// Factory-only include: this binary uses just `create_test_database` /
// `encode_test_kmer`, so it takes the self-test-free factory core instead of
// full `common` — pulling full `common` would compile the shared helpers'
// own ~20 `common::*::tests::*` cases (one of them timing-flaky) into this
// binary (deferred-items.md `mod common` entry; CI run 37952454763).
#[path = "common/factories.rs"]
mod common;

use common::create_test_database;
use rustkmer::database::format::RKDatabase;
use rustkmer::database::merge_config::MergeConfig;
use std::fs::File;
use std::io::{Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

/// k-mer size used by every synthetic input (inside the D-13 coverage matrix).
const K: u8 = 21;

/// Each input DB carries this many k-mers. Two inputs → 400 k-mers summed →
/// `400 * 24 = 9600` bytes estimated, which clears `TINY_BUDGET_BYTES`.
const INPUT_KMERS: usize = 200;

/// A deliberately absurd merge budget: any real input estimate exceeds it, so
/// the "over budget" branch is taken deterministically.
const TINY_BUDGET_BYTES: usize = 1024;

/// A budget no toy input can approach, so the "within budget" branch is taken
/// deterministically.
const HUGE_BUDGET_BYTES: usize = 1024 * 1024 * 1024;

/// Build a `MergeConfig` with the routing-relevant fields pinned.
///
/// `temp_dir` is the path-selection probe (see the module docstring) — pass a
/// real directory for "may succeed either way" and a nonexistent path to make
/// streaming-vs-in-memory observable.
fn routing_config(temp_dir: &Path, max_memory_usage: usize, merge_mode: &str) -> MergeConfig {
    MergeConfig {
        max_memory_usage,
        merge_mode: merge_mode.to_string(),
        temp_dir: temp_dir.to_path_buf(),
        // Small chunk size so the streaming path exercises its chunk writer
        // even on toy inputs.
        chunk_size: 64,
        ..Default::default()
    }
}

/// Write a synthetic, well-formed `.rkdb` to `dir/name` and return its path.
fn write_input_db(dir: &Path, name: &str, num_kmers: usize) -> anyhow::Result<PathBuf> {
    let db = create_test_database(num_kmers, K, true, true)
        .map_err(|e| anyhow::anyhow!("failed to build synthetic input db: {}", e))?;
    let path = dir.join(name);
    db.to_file_path(&path)
        .map_err(|e| anyhow::anyhow!("failed to write {}: {}", path.display(), e))?;
    Ok(path)
}

/// Write a `.rkdb` whose header claims `declared_kmers` but whose body is
/// truncated to nothing but the 42-byte header.
///
/// This is the D-01 trap: pre-fix, any code that reaches for
/// `RKDatabase::from_file_path` to read `total_kmers` will try to materialize
/// `declared_kmers` entries and fail (or exhaust RAM on a large value). A
/// header-only estimator reads 42 bytes and never notices the body is gone.
fn write_truncated_oversized_db(
    dir: &Path,
    name: &str,
    num_kmers: usize,
    declared_kmers: u64,
) -> anyhow::Result<PathBuf> {
    let db = create_test_database(num_kmers, K, true, true)
        .map_err(|e| anyhow::anyhow!("failed to build synthetic input db: {}", e))?;
    let path = dir.join(name);
    db.to_file_path(&path)
        .map_err(|e| anyhow::anyhow!("failed to write {}: {}", path.display(), e))?;

    // .rkdb v2 header layout (see DatabaseHeader::write_to):
    //   [0..4)   magic "RKDB"
    //   [4..6)   version (u16 LE)
    //   [6]      kmer_size (u8)
    //   [7]      pad (u8)
    //   [8..10)  pad (u16)
    //   [10..18) total_kmers (u64 LE)   <-- overwritten here
    //   ... rest of the 42-byte header, then entries
    let mut f = File::options()
        .read(true)
        .write(true)
        .open(&path)
        .map_err(|e| anyhow::anyhow!("failed to reopen {}: {}", path.display(), e))?;
    f.seek(SeekFrom::Start(10))
        .map_err(|e| anyhow::anyhow!("failed to seek in {}: {}", path.display(), e))?;
    f.write_all(&declared_kmers.to_le_bytes())
        .map_err(|e| anyhow::anyhow!("failed to patch header of {}: {}", path.display(), e))?;
    f.set_len(42)
        .map_err(|e| anyhow::anyhow!("failed to truncate {}: {}", path.display(), e))?;
    f.flush()
        .map_err(|e| anyhow::anyhow!("failed to flush {}: {}", path.display(), e))?;

    Ok(path)
}

/// Write a `.rkdb` whose header reports `total_kmers == 0` (an untrustworthy /
/// legacy value) while the body still holds `num_kmers` real entries.
///
/// Exercises the D-01 file-size fallback: the persisted count cannot be used,
/// so the estimator must derive `(file_size - 42) / 20` instead.
fn write_zero_kmers_db(dir: &Path, name: &str, num_kmers: usize) -> anyhow::Result<PathBuf> {
    let db = create_test_database(num_kmers, K, true, true)
        .map_err(|e| anyhow::anyhow!("failed to build synthetic input db: {}", e))?;
    let path = dir.join(name);
    db.to_file_path(&path)
        .map_err(|e| anyhow::anyhow!("failed to write {}: {}", path.display(), e))?;

    // total_kmers lives at [10..18) in the 42-byte .rkdb v2 header.
    let mut f = File::options()
        .read(true)
        .write(true)
        .open(&path)
        .map_err(|e| anyhow::anyhow!("failed to reopen {}: {}", path.display(), e))?;
    f.seek(SeekFrom::Start(10))
        .map_err(|e| anyhow::anyhow!("failed to seek in {}: {}", path.display(), e))?;
    f.write_all(&0u64.to_le_bytes())
        .map_err(|e| anyhow::anyhow!("failed to zero header of {}: {}", path.display(), e))?;
    f.flush()
        .map_err(|e| anyhow::anyhow!("failed to flush {}: {}", path.display(), e))?;

    Ok(path)
}

/// A temp directory path that does not exist. Used as the "which merge path
/// ran?" probe — see the module docstring.
fn missing_temp_dir(root: &Path) -> PathBuf {
    root.join("this_temp_dir_does_not_exist")
}

/// Overwrite a `u64` field in an already-written `.rkdb` header.
///
/// `.rkdb` v2 header layout (see `DatabaseHeader::write_to`):
///   [0..4)   magic "RKDB"          [4..6)   version (u16 LE)
///   [6]      kmer_size            [7]      pad
///   [8..10)  pad (u16 LE)         [10..18) total_kmers (u64 LE)
///   [18]     flags                [19..26) pad (7 bytes)
///   [26..34) data_offset (u64 LE) [34..42) index_offset (u64 LE)
fn patch_header_u64(path: &Path, field_offset: u64, value: u64) -> anyhow::Result<()> {
    let mut f = File::options()
        .read(true)
        .write(true)
        .open(path)
        .map_err(|e| anyhow::anyhow!("failed to reopen {}: {}", path.display(), e))?;
    f.seek(SeekFrom::Start(field_offset))
        .map_err(|e| anyhow::anyhow!("failed to seek in {}: {}", path.display(), e))?;
    f.write_all(&value.to_le_bytes())
        .map_err(|e| anyhow::anyhow!("failed to patch header of {}: {}", path.display(), e))?;
    f.flush()
        .map_err(|e| anyhow::anyhow!("failed to flush {}: {}", path.display(), e))
}

/// Assert that `err` is the streaming route's temp-chunk-creation failure.
///
/// The exact shape matters. The previous assertion in this file was
/// `msg.contains("temp") || msg.contains("No such file")`, which several
/// unrelated failures satisfy — a wrong k-mer size, a bad input path, a corrupt
/// input all mention one or the other, so the "hard route" proof it was
/// carrying was much weaker than it read. This asserts BOTH halves of the real
/// signature emitted by `TempFileManager::create_temp_file`:
///
///   `Failed to create temp file '<temp_dir>/rustkmer_sort_<pid>_<ts>_<id>.chunk': ...`
///
/// — the operation, and the nonexistent directory we deliberately pointed at.
/// Plan 03-07 reported the weak form and left it here; this is that fix.
fn assert_streaming_route_proved(err: &rustkmer::ProcessingError, missing: &Path) {
    let msg = err.to_string();
    let missing_name = missing
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    assert!(
        msg.contains("Failed to create temp file"),
        "expected the streaming route's chunk-creation failure; the message must name the \
         operation that only the streaming path performs. Got: {}",
        msg
    );
    assert!(
        !missing_name.is_empty() && msg.contains(&missing_name),
        "the failure must name the nonexistent temp dir '{}' we pointed the route probe at, \
         proving the streaming path was entered rather than some other failure. Got: {}",
        missing_name,
        msg
    );
}

/// Smoke test (GREEN in the Wave-0 scaffold — the only test not `#[ignore]`d).
///
/// Two small, overlapping inputs merged under `merge_mode: "auto"` with a
/// budget no toy input approaches. D-02 retains the in-memory fast path for
/// small merges, so this must complete and produce the exact union with
/// per-k-mer counts summed.
#[test]
fn merge_default_routes_small_inputs_to_inmemory_or_streaming() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let a = write_input_db(dir.path(), "a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "b.rkdb", INPUT_KMERS)?;

    // Within budget + "auto": the in-memory fast path is permitted (D-02), so
    // the merge must succeed regardless of which of the two permitted paths
    // the dispatcher picks.
    let config = routing_config(dir.path(), HUGE_BUDGET_BYTES, "auto");
    let merged = RKDatabase::merge_databases(&[a, b], &config)
        .map_err(|e| anyhow::anyhow!("within-budget auto merge must succeed: {}", e))?;

    let merged_kmers: std::collections::HashMap<u128, u32> = merged
        .all_kmers()
        .map_err(|e| anyhow::anyhow!("failed to read merged k-mers: {}", e))?
        .into_iter()
        .collect();

    // Both inputs carry the same `INPUT_KMERS` deterministic k-mers with the
    // same per-k-mer counts, so the union is INPUT_KMERS unique k-mers and
    // every count is exactly doubled.
    assert_eq!(
        merged_kmers.len(),
        INPUT_KMERS,
        "merged union must be the exact set of input k-mers"
    );
    for i in 0..INPUT_KMERS as u64 {
        let kmer = common::encode_test_kmer(i, K);
        let expected = 2 * (i % 1000 + 1) as u32;
        assert_eq!(
            merged_kmers.get(&kmer).copied(),
            Some(expected),
            "k-mer {} must be present with summed count {}",
            kmer,
            expected
        );
    }

    // D-02 (small-input fast path retained): with the budget unreachable, the
    // dispatcher must NOT have entered the streaming path — proven by pointing
    // temp_dir at a nonexistent directory, which the streaming path cannot
    // write chunk files into.
    let no_temp = routing_config(&missing_temp_dir(dir.path()), HUGE_BUDGET_BYTES, "auto");
    let probe_a = write_input_db(dir.path(), "probe_a.rkdb", 8)?;
    let probe_b = write_input_db(dir.path(), "probe_b.rkdb", 8)?;
    let probe = RKDatabase::merge_databases(&[probe_a, probe_b], &no_temp);
    assert!(
        probe.is_ok(),
        "within-budget auto merge must take the in-memory path (no temp_dir use); got: {:?}",
        probe.err()
    );

    Ok(())
}

/// MERGE-01 / D-01 — an over-budget `merge_mode: "auto"` merge must HARD-ROUTE
/// to the streaming path, not warn-and-continue into the in-memory path.
#[test]
fn merge_over_budget_hard_routes_to_streaming() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let a = write_input_db(dir.path(), "a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "b.rkdb", INPUT_KMERS)?;

    // Part 1 — the over-budget merge itself must SUCCEED via streaming and
    // produce the exact union. (No OOM, no silent truncation.)
    let config = routing_config(dir.path(), TINY_BUDGET_BYTES, "auto");
    let merged = RKDatabase::merge_databases(&[a.clone(), b.clone()], &config)
        .map_err(|e| anyhow::anyhow!("over-budget auto merge must succeed via streaming: {}", e))?;
    let merged_kmers: std::collections::HashMap<u128, u32> = merged
        .all_kmers()
        .map_err(|e| anyhow::anyhow!("failed to read merged k-mers: {}", e))?
        .into_iter()
        .collect();
    assert_eq!(
        merged_kmers.len(),
        INPUT_KMERS,
        "over-budget merge must still produce the exact union"
    );
    // k-mer 0 carries count `0 % 1000 + 1 == 1` in each input, so the merged
    // count must be exactly 2.
    assert_eq!(
        merged_kmers.get(&common::encode_test_kmer(0, K)).copied(),
        Some(2),
        "over-budget merge must sum per-k-mer counts"
    );

    // Part 2 — the route must be a HARD route: the same over-budget inputs with
    // a nonexistent temp_dir must FAIL, which is only possible if the
    // streaming path was entered (it must create a chunk file there). A
    // warn-and-continue in-memory fallback would have returned Ok.
    let no_temp = routing_config(&missing_temp_dir(dir.path()), TINY_BUDGET_BYTES, "auto");
    let missing = missing_temp_dir(dir.path());
    let err = RKDatabase::merge_databases(&[a, b], &no_temp).expect_err(
        "over-budget auto merge must hard-route to streaming, not warn-and-continue in-memory",
    );
    assert_streaming_route_proved(&err, &missing);

    Ok(())
}

/// MERGE-02 / D-02 — an explicit `merge_mode: "memory"` merge whose estimate
/// exceeds `max_memory_usage` must be REJECTED with a clear error, never
/// silently OOM.
#[test]
fn merge_explicit_memory_mode_over_budget_rejects() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let a = write_input_db(dir.path(), "a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "b.rkdb", INPUT_KMERS)?;

    // Explicit "memory" mode, absurdly small budget → must be rejected.
    let config = routing_config(dir.path(), TINY_BUDGET_BYTES, "memory");
    let err = RKDatabase::merge_databases(&[a.clone(), b.clone()], &config).expect_err(
        "merge_mode='memory' over budget must be rejected (D-02), not silently attempted in-memory",
    );
    let msg = err.to_string();
    assert!(
        msg.contains("memory"),
        "reject message must name the memory mode; got: {}",
        msg
    );
    assert!(
        msg.contains("streaming"),
        "reject message must point the user at the streaming mode; got: {}",
        msg
    );

    // Control: the SAME inputs within budget must still merge fine under
    // explicit "memory" mode (D-02 retains the in-memory fast path).
    let ok_config = routing_config(dir.path(), HUGE_BUDGET_BYTES, "memory");
    let merged = RKDatabase::merge_databases(&[a, b], &ok_config)
        .map_err(|e| anyhow::anyhow!("within-budget memory-mode merge must succeed: {}", e))?;
    let merged_kmers: std::collections::HashMap<u128, u32> = merged
        .all_kmers()
        .map_err(|e| anyhow::anyhow!("failed to read merged k-mers: {}", e))?
        .into_iter()
        .collect();
    assert_eq!(
        merged_kmers.len(),
        INPUT_KMERS,
        "within-budget memory-mode merge must produce the exact union"
    );

    Ok(())
}

/// MERGE-01 — `merge_mode: "streaming"` must ALWAYS take the streaming path,
/// regardless of the estimate. Proved with a within-budget input set and a
/// nonexistent temp_dir: only the streaming path can fail there.
#[test]
fn merge_explicit_streaming_mode_always_streams() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;

    // Within budget, yet explicitly streaming: the temp_dir probe must fail.
    let probe_inputs = [
        write_input_db(dir.path(), "p1.rkdb", 8)?,
        write_input_db(dir.path(), "p2.rkdb", 8)?,
    ];
    let missing = missing_temp_dir(dir.path());
    let err = RKDatabase::merge_databases(
        &probe_inputs,
        &routing_config(&missing, HUGE_BUDGET_BYTES, "streaming"),
    )
    .expect_err(
        "merge_mode='streaming' must take the streaming path even when the estimate is within budget",
    );
    assert_streaming_route_proved(&err, &missing);

    // Control: the same explicit streaming mode with a real temp_dir must
    // succeed and produce the exact union.
    let a = write_input_db(dir.path(), "a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "b.rkdb", INPUT_KMERS)?;
    let config = routing_config(dir.path(), TINY_BUDGET_BYTES, "streaming");
    let merged = RKDatabase::merge_databases(&[a, b], &config)
        .map_err(|e| anyhow::anyhow!("explicit streaming merge must succeed: {}", e))?;
    let merged_kmers: std::collections::HashMap<u128, u32> = merged
        .all_kmers()
        .map_err(|e| anyhow::anyhow!("failed to read merged k-mers: {}", e))?
        .into_iter()
        .collect();
    assert_eq!(
        merged_kmers.len(),
        INPUT_KMERS,
        "explicit streaming merge must produce the exact union"
    );

    Ok(())
}

/// MERGE-02 / D-01 — the estimator must be HEADER-ONLY: it reads the
/// persisted `total_kmers` and never materializes entries.
#[test]
fn estimator_reads_header_only_no_materialization() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;

    // A file whose header claims 5 billion k-mers but whose body is truncated
    // to the bare 42-byte header. `RKDatabase::from_file_path` on this file
    // reserves `5e9 * sizeof(KmerEntry)` and ABORTS the process on a typical
    // CI box — that abort IS the D-01 OOM bug, which is why the premise below
    // is checked with a SMALL declared count and the huge one is only ever
    // handed to the header-only estimator.
    const DECLARED: u64 = 5_000_000_000;
    let path = write_truncated_oversized_db(dir.path(), "truncated.rkdb", 16, DECLARED)?;

    // Premise (D-01): the materializing loader genuinely fails when the
    // header promises entries the body does not contain — so an estimator
    // that still returns a number on such a file has, by construction, not
    // materialized anything. A small declared count keeps this Err rather
    // than an allocation abort.
    const DECLARED_SMALL: u64 = 1_000;
    let small =
        write_truncated_oversized_db(dir.path(), "truncated_small.rkdb", 0, DECLARED_SMALL)?;
    let materialize = RKDatabase::from_file_path(&small);
    assert!(
        materialize.is_err(),
        "premise: from_file_path must fail on a truncated body (it materializes entries): {:?}",
        materialize.err()
    );

    // The D-01 assertion: the header-only estimator reads the persisted
    // `total_kmers` straight out of the 42-byte header. It returns DECLARED
    // instantly even though the body is empty AND the declared count would
    // need 100 GB of RAM to materialize — which is only possible if it never
    // touched an entry.
    let estimated = RKDatabase::estimate_total_kmers(&path)
        .map_err(|e| anyhow::anyhow!("header-only estimate must succeed: {}", e))?;
    assert_eq!(
        estimated, DECLARED,
        "estimator must return the header's persisted total_kmers, not a materialization-derived count"
    );

    // A well-formed file must yield exactly its own entry count, so the
    // estimate is not merely "some large number".
    let ok_path = write_input_db(dir.path(), "ok.rkdb", 37)?;
    let ok_estimated = RKDatabase::estimate_total_kmers(&ok_path)
        .map_err(|e| anyhow::anyhow!("estimate on a well-formed db must succeed: {}", e))?;
    assert_eq!(
        ok_estimated, 37,
        "estimator must return the header total_kmers of a well-formed input"
    );

    // D-01 fallback: a header reporting total_kmers == 0 is untrustworthy, so
    // the estimate must come from the file size instead — and must
    // over-estimate (never under-estimate into an unsafe in-memory admission).
    let zeroed = write_zero_kmers_db(dir.path(), "zeroed.rkdb", 25)?;
    let fallback = RKDatabase::estimate_total_kmers(&zeroed)
        .map_err(|e| anyhow::anyhow!("estimate on a zero-total_kmers db must succeed: {}", e))?;
    let actual_len = std::fs::metadata(&zeroed)?.len();
    let size_bound = actual_len.saturating_sub(42) / 20;
    assert_eq!(
        fallback, size_bound,
        "a zero total_kmers must fall back to (file_size - 42) / 20"
    );
    assert_eq!(
        fallback, 25,
        "for this input the file-size fallback must recover the true entry count"
    );

    // Corrupt magic: the header is untrustworthy, so the estimator must still
    // return a conservative (file-size-derived) upper bound rather than
    // failing the merge outright or reporting 0.
    let corrupt = dir.path().join("corrupt.rkdb");
    std::fs::copy(&ok_path, &corrupt)?;
    {
        use std::io::Seek;
        let mut f = File::options().write(true).open(&corrupt)?;
        f.seek(SeekFrom::Start(0))?;
        f.write_all(b"XXXX")?;
        f.flush()?;
    }
    let corrupt_estimate = RKDatabase::estimate_total_kmers(&corrupt).map_err(|e| {
        anyhow::anyhow!("estimate on a corrupt-header db must not hard-fail: {}", e)
    })?;
    let corrupt_len = std::fs::metadata(&corrupt)?.len();
    assert_eq!(
        corrupt_estimate,
        corrupt_len.saturating_sub(42) / 20,
        "a corrupt header must fall back to the file-size upper bound (threat T-03-01)"
    );

    Ok(())
}

/// G2a — the header-only read is the ONLY way a merge route learns an input's
/// shape, so it must (a) agree with the materializing loader field for field on
/// a well-formed file, and (b) succeed on a file whose body is absent entirely.
///
/// (b) is the property that makes the over-budget path safe:
/// `merge_databases_streaming` used to call `from_file_path` on
/// `input_paths[0]` purely to learn `kmer_size` and `canonical` — on the route
/// chosen precisely because the inputs do not fit. A header claiming 5 billion
/// k-mers over an empty body would need ~100 GB to materialize, so returning a
/// number for it is only possible if nothing was loaded. The premise assertion
/// keeps that honest: the materializing loader must genuinely FAIL on the same
/// file, so a green here cannot be explained by the file being readable anyway.
#[test]
fn header_only_read_agrees_with_the_materializing_loader() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;

    // (a) Field-for-field agreement on a well-formed file. The streaming route
    // takes `kmer_size`/`canonical` and `ExternalSortMerger::new` takes
    // `kmer_size`/`canonical`/`total_kmers` from this read, so a divergence here
    // would silently change merge output.
    let ok = write_input_db(dir.path(), "ok.rkdb", 23)?;
    let header = RKDatabase::read_header_of(&ok)?;
    let materialized = RKDatabase::from_file_path(&ok)?;
    assert_eq!(header.kmer_size, materialized.kmer_size_u8());
    assert_eq!(header.canonical, materialized.is_canonical());
    assert_eq!(header.total_kmers, materialized.total_kmers());
    assert_eq!(
        header.total_kmers, 23,
        "the header's record count must be the real entry count on a well-formed file"
    );

    // (b) A header over an empty body. `write_truncated_oversized_db` writes
    // exactly 42 bytes of header and then truncates the body away.
    const DECLARED: u64 = 5_000_000_000;
    const DECLARED_SMALL: u64 = 1_000;
    let bomb = write_truncated_oversized_db(dir.path(), "bomb.rkdb", 16, DECLARED)?;
    let small = write_truncated_oversized_db(dir.path(), "small.rkdb", 0, DECLARED_SMALL)?;
    assert!(
        RKDatabase::from_file_path(&small).is_err(),
        "premise: the materializing loader must fail on a truncated body, otherwise the \
         next assertion proves nothing"
    );

    let bomb_header = RKDatabase::read_header_of(&bomb)?;
    assert_eq!(
        bomb_header.total_kmers, DECLARED,
        "the header-only read must return the persisted count without materializing anything"
    );
    assert_eq!(bomb_header.kmer_size, K);
    assert!(bomb_header.canonical);

    Ok(())
}

/// G2a / the documented semantic change of routing the estimator through
/// `read_header_of`: a file whose header PARSES but carries a `data_offset`
/// other than 42 is now refused by both the header-only read and the
/// materializing loader, with the identical message — and the estimator, which
/// is a fallback-by-design function, falls back to the file-size bound rather
/// than trusting a header no reader will accept.
///
/// This is asserted rather than described because the plan's warning is
/// explicit that "semantics preserved exactly" would be a false claim: the
/// estimator is now the STRICTER of the two for this field, and that is the
/// safe direction.
#[test]
fn header_only_read_and_estimator_reject_an_unaccepted_data_offset() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let path = write_input_db(dir.path(), "odd_offset.rkdb", 30)?;
    patch_header_u64(&path, 26, 64)?; // data_offset := 64, not 42

    // Both readers refuse it, and they say the SAME thing, so a corrupt or
    // incompatible file fails identically whether or not a body was loaded.
    let header_err = RKDatabase::read_header_of(&path)
        .expect_err("read_header_of must reject a data_offset no reader in the crate accepts");
    let loader_err = RKDatabase::from_file_path(&path).expect_err(
        "from_file_path must reject the same data_offset (premise for the equality below)",
    );
    assert_eq!(
        header_err.to_string(),
        loader_err.to_string(),
        "the header-only read and the materializing loader must produce the identical error text"
    );
    assert!(
        header_err
            .to_string()
            .contains("Unsupported data_offset 64"),
        "the message must name the offending offset; got: {}",
        header_err
    );

    // The estimator, unlike before this plan, no longer trusts this header: it
    // falls back to the file-size upper bound (over-estimating routes the merge
    // conservatively to streaming — threat T-03-01).
    let estimated = RKDatabase::estimate_total_kmers(&path)?;
    let len = std::fs::metadata(&path)?.len();
    assert_eq!(
        estimated,
        len.saturating_sub(42) / 20,
        "an unaccepted data_offset must send the estimator to its file-size fallback, not the header"
    );

    Ok(())
}

/// Wave-merge cross-validation (added by plan 03-04).
///
/// The four routing tests above each pin the union *size* and spot-check a
/// couple of counts. None of them pins the two whole-database invariants a
/// merge can violate without changing either of those:
///
///   1. **Header accounting** — `header.total_kmers` must equal the number of
///      records actually present. A merge that silently skips work and still
///      returns `Ok` produces a structurally valid `.rkdb` that undercounts
///      itself; nothing downstream notices, because every reader trusts the
///      header. There is a live instance of this shape on the prefix-cache
///      path (`merge_prefix_buckets` logs bucket failures but returns `Ok(())`),
///      which is why the invariant is asserted here rather than left for a
///      reader to discover.
///   2. **Total-count conservation** — the merged counts must sum to the sum of
///      the input counts. A dropped k-mer, or a count read twice, moves this
///      total even when the k-mer *set* is unchanged.
///
/// Both are asserted on **both** permitted routes, since MERGE-01 promotes
/// streaming to the default and D-02 retains in-memory for small inputs: a
/// route that satisfied neither would defeat the hard route.
#[test]
fn merged_database_accounts_for_every_input_kmer_on_both_routes() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let a = write_input_db(dir.path(), "acct_a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "acct_b.rkdb", INPUT_KMERS)?;

    // The inputs' own accounting, read from disk rather than recomputed, so the
    // expectation is the inputs' claim and the assertion is that the merge
    // preserves it.
    let input_total: u64 = [&a, &b]
        .iter()
        .map(|p| {
            RKDatabase::from_file_path(p)
                .and_then(|db| db.all_kmers())
                .map(|pairs| pairs.iter().map(|(_, c)| *c as u64).sum::<u64>())
                .map_err(|e| anyhow::anyhow!("failed to read input {}: {}", p.display(), e))
        })
        .collect::<anyhow::Result<Vec<u64>>>()?
        .into_iter()
        .sum();
    assert!(
        input_total > 0,
        "premise: the synthetic inputs must actually carry counts"
    );

    for (label, config) in [
        (
            "in-memory",
            routing_config(dir.path(), HUGE_BUDGET_BYTES, "auto"),
        ),
        (
            "streaming",
            routing_config(dir.path(), TINY_BUDGET_BYTES, "auto"),
        ),
    ] {
        let merged = RKDatabase::merge_databases(&[a.clone(), b.clone()], &config)
            .map_err(|e| anyhow::anyhow!("{} merge must succeed: {}", label, e))?;
        let pairs = merged
            .all_kmers()
            .map_err(|e| anyhow::anyhow!("{}: failed to read merged k-mers: {}", label, e))?;

        // (1) Header accounting.
        assert_eq!(
            merged.header.total_kmers,
            pairs.len() as u64,
            "{}: header total_kmers ({}) must equal the number of records present ({}) — \
             a header that undercounts makes the file structurally valid but wrong",
            label,
            merged.header.total_kmers,
            pairs.len()
        );
        assert_eq!(
            merged.header.data_offset, 42,
            "{}: merged output must be a canonical .rkdb v2 file",
            label
        );
        assert_eq!(
            merged.header.kmer_size, K,
            "{}: merged output must preserve the input k-mer size",
            label
        );
        assert!(
            merged.header.sorted,
            "{}: a merged database must be sorted — the readers' binary search \
             depends on it",
            label
        );

        // (2) Total-count conservation.
        let merged_total: u64 = pairs.iter().map(|(_, c)| *c as u64).sum();
        assert_eq!(
            merged_total, input_total,
            "{}: merged counts must sum to the inputs' total ({}) — a dropped or \
             double-counted k-mer moves this even when the k-mer set is unchanged",
            label, input_total
        );

        // The invariant must survive the write/read round trip, since the header
        // is what a downstream reader trusts.
        let out = dir.path().join(format!("accounted_{}.rkdb", label));
        merged.to_file_path(&out)?;
        let reloaded = RKDatabase::from_file_path(&out)?;
        assert_eq!(
            reloaded.header.total_kmers, merged.header.total_kmers,
            "{}: header total_kmers must survive write -> read unchanged",
            label
        );
        assert_eq!(
            reloaded.all_kmers()?,
            pairs,
            "{}: merged records must survive write -> read unchanged",
            label
        );
        assert_eq!(
            RKDatabase::estimate_total_kmers(&out)?,
            merged.header.total_kmers,
            "{}: the MERGE-02 header-only estimator must agree with the record count \
             on the written output — it reads the header, so disagreement means the \
             header lies",
            label
        );
    }

    Ok(())
}

/// MERGE-03 / threat T-03-34 — the prefix-cache intermediate result must live
/// inside the merger's process-unique subdir and be reclaimed when the merge
/// returns.
///
/// `deferred-items.md` recorded that the intermediate result was written to
/// `config.temp_dir.join("external_sort_merge_output.tmp")` — a FIXED basename
/// in a SHARED directory, never removed. Two defects in one: two concurrent
/// prefix-cache merges sharing a temp dir overwrote each other, and a
/// dataset-sized file survived the merge that produced it.
///
/// The assertion has two halves on purpose. Checking only the subdir would
/// pass if the file had simply moved somewhere else outside RAII; checking only
/// `temp_dir` would pass if the subdir copy still existed. Both must be absent.
#[test]
fn prefix_cache_intermediate_result_is_inside_the_raii_subdir_and_reclaimed() -> anyhow::Result<()>
{
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;
    let a = write_input_db(dir.path(), "pc_a.rkdb", INPUT_KMERS)?;
    let b = write_input_db(dir.path(), "pc_b.rkdb", INPUT_KMERS)?;

    let config = MergeConfig {
        use_prefix_cache: true,
        temp_dir: work.path().to_path_buf(),
        ..routing_config(work.path(), HUGE_BUDGET_BYTES, "auto")
    };

    let merged = RKDatabase::merge_databases(&[a, b], &config)
        .map_err(|e| anyhow::anyhow!("prefix-cache merge must succeed: {}", e))?;
    let merged_kmers: std::collections::HashMap<u128, u32> = merged
        .all_kmers()
        .map_err(|e| anyhow::anyhow!("failed to read merged k-mers: {}", e))?
        .into_iter()
        .collect();
    assert_eq!(
        merged_kmers.len(),
        INPUT_KMERS,
        "the prefix-cache route must still produce the exact union — this test is about \
         where its intermediate file lives, not about relaxing what it produces"
    );

    // Half 1: nothing named `external_sort_merge_output.tmp` survives anywhere
    // under a `rustkmer-merge-*` subdir.
    let mut subdirs_seen = 0usize;
    for entry in std::fs::read_dir(work.path())? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().to_string();
        if !name.starts_with("rustkmer-merge-") {
            continue;
        }
        subdirs_seen += 1;
        if !entry.path().is_dir() {
            continue;
        }
        for inner in std::fs::read_dir(entry.path())? {
            let inner = inner?;
            let inner_name = inner.file_name().to_string_lossy().to_string();
            assert_ne!(
                inner_name,
                "external_sort_merge_output.tmp",
                "the intermediate result must not survive inside {}: the TempDir's Drop \
                 owns every file beneath it, so a leftover here means the merge result was \
                 written somewhere RAII does not own",
                entry.path().display()
            );
        }
    }
    if subdirs_seen == 0 {
        // The success case: Drop removed the whole subdir, so there is nothing
        // left to inspect. Logged, never a silent pass.
        eprintln!(
            "prefix-cache reclamation: the whole rustkmer-merge-* subdir is already gone, \
             which is the RAII success case"
        );
    }

    // Half 2: the OLD fixed location, directly in the shared temp dir, must
    // also be absent — otherwise the file merely moved outside RAII.
    let old_location = work.path().join("external_sort_merge_output.tmp");
    assert!(
        !old_location.exists(),
        "the intermediate result must not be written to the shared temp dir at {} \
         (fixed basename: collides between concurrent merges, survives the merge)",
        old_location.display()
    );

    Ok(())
}

/// WR-01 — the admission model is a PER-ROUTE model, and each constant is
/// derived from the structures that route actually holds live.
///
/// This test is a floor and a drift alarm, not proof the model is right: a
/// `size_of` constant cannot observe a source change (plan 03-06's lesson).
/// The behavioural evidence that the model changed and matters is
/// `model_change_routes_a_budget_the_old_model_admitted_to_streaming`.
#[test]
fn estimated_bytes_per_route_reflects_each_routes_peak() {
    use rustkmer::database::merge_config::MergeStrategy;

    const N: u64 = 1_000;
    // 32 + 32 + 32, and the derivation is checkable: `KmerEntry` and
    // `(u128, u32)` are both 32 B (20 B of payload padded to u128's 16-byte
    // alignment). If a future layout change moves either, this fails loudly
    // instead of leaving the comment above the constant quietly wrong.
    assert_eq!(
        std::mem::size_of::<rustkmer::database::format::KmerEntry>(),
        32,
        "the INMEMORY derivation's first 32 B is size_of::<KmerEntry>()"
    );
    assert_eq!(
        std::mem::size_of::<(u128, u32)>(),
        32,
        "the hashbrown bucket and the drained Vec both store (u128, u32)"
    );

    assert_eq!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, N),
        N * 96,
        "the in-memory route is charged all three live structures"
    );
    assert_eq!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::Streaming, N),
        N * 32,
        "the streaming route reports a diagnostic-only 32"
    );
    assert_eq!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::PrefixCache, N),
        N * 32,
        "the prefix-cache route reports a diagnostic-only 32"
    );
    // Hybrid is defined, not a panic and not a silent zero. It starts in
    // memory, so it is charged the in-memory peak.
    assert_eq!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::Hybrid, N),
        N * 96,
        "Hybrid starts in-memory, so its first-resort peak is the in-memory one"
    );

    // The retired 24 B/k-mer model must be gone: it modelled roughly a quarter
    // of the peak it was meant to bound (WR-01), so a merge the gate admitted
    // could still exhaust memory.
    assert_ne!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, N),
        N * 24,
        "the pre-WR-01 model must not be back"
    );

    // Threat T-03-32: a crafted header claiming u64::MAX k-mers saturates
    // rather than wrapping to a small number that would slip under a budget.
    assert_eq!(
        RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, u64::MAX),
        u64::MAX
    );
}

/// WR-01 — the model change is BEHAVIOURAL, not cosmetic.
///
/// A budget of `48 * N` is above the retired 24 B/k-mer and below the new 96
/// B/k-mer, so the same inputs and the same budget take DIFFERENT routes
/// before and after this change. Under the old model `48*N >= 24*N` put the
/// merge in memory; under the new one `96*N > 48*N` hard-routes it to
/// streaming (MERGE-02's hard route), which is proven behaviourally by
/// pointing `temp_dir` at a directory that does not exist: only the streaming
/// path can fail there, so an `Err` naming that directory IS the route proof.
#[test]
fn model_change_routes_a_budget_the_old_model_admitted_to_streaming() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let path = write_input_db(dir.path(), "single.rkdb", INPUT_KMERS)?;

    // N from the production estimator, never hard-coded.
    let n = RKDatabase::estimate_total_kmers(&path)?;
    assert_eq!(
        n, INPUT_KMERS as u64,
        "premise: N is the input's record count"
    );

    // The discriminating budget. 48*N > 24*N (old model admitted it) and
    // 48*N < 96*N (new model rejects it).
    let budget = 48 * n;
    let derived = RKDatabase::estimated_bytes_for_route(
        rustkmer::database::merge_config::MergeStrategy::InMemory,
        n,
    );
    assert!(
        derived > budget,
        "GUARD: the derived estimate ({}) must EXCEED the budget ({}) for this test to mean \
         anything. If a future model change drops the estimate below 48 bytes/k-mer, the merge \
         below would silently take the in-memory path and this test would pass for the wrong \
         reason — the exact failure mode plan 03-04 shipped.",
        derived,
        budget
    );
    assert!(
        24 * n <= budget,
        "premise: this budget is one the retired 24 B/k-mer model would have ADMITTED in memory"
    );

    let missing = missing_temp_dir(dir.path());
    let err =
        RKDatabase::merge_databases(&[path], &routing_config(&missing, budget as usize, "auto"))
            .expect_err(
                "a budget between the old and new per-k-mer models must hard-route to streaming, \
         which is observable only as a chunk-creation failure in a nonexistent temp dir",
            );
    assert_streaming_route_proved(&err, &missing);

    // Control: the SAME inputs under a budget the new model also admits take
    // the in-memory path and never touch temp_dir. Without this arm, "it
    // streamed" would be the only thing proven and a route that always streams
    // would pass.
    let merged = RKDatabase::merge_databases(
        &[write_input_db(dir.path(), "control.rkdb", INPUT_KMERS)?],
        &routing_config(&missing, derived as usize, "auto"),
    )
    .map_err(|e| {
        anyhow::anyhow!(
            "control: a budget at/above the derived estimate must take the in-memory path \
             (no temp_dir use); got: {}",
            e
        )
    })?;
    assert_eq!(
        merged.all_kmers()?.len(),
        INPUT_KMERS,
        "the in-memory control must produce the exact union"
    );

    Ok(())
}

/// WR-06 / threat T-03-35 — `merge_databases(&[], ..)` returns `Err`, it does
/// not panic.
///
/// Pre-fix the dispatcher ran straight into `&input_paths[0]` in the streaming
/// route, so an empty list was an index-out-of-bounds abort rather than a
/// reportable error. The assertion is on the error TEXT as well as the absence
/// of a panic, so a future "fix" that returns some unrelated error still fails.
#[test]
fn merge_databases_with_empty_input_list_returns_err() -> anyhow::Result<()> {
    // A generous budget and a real temp dir, so the ONLY thing that can fail
    // here is the empty-input guard.
    let dir = tempfile::tempdir()?;
    let config = routing_config(dir.path(), HUGE_BUDGET_BYTES, "auto");

    let result = std::panic::catch_unwind(|| {
        let config = config.clone();
        RKDatabase::merge_databases(&[], &config).map_err(|e| e.to_string())
    })
    .expect("merge_databases(&[], ..) must not panic");

    let message = result.expect_err("an empty input list must return Err, not Ok");
    assert!(
        message.contains("At least one input database is required"),
        "the error must name the actual cause; got: {}",
        message
    );

    // The same guard must cover the other two selectors too — it lives in the
    // dispatcher, above the strategy branch, not in one strategy.
    for mode in ["memory", "streaming"] {
        let cfg = routing_config(dir.path(), HUGE_BUDGET_BYTES, mode);
        let err = RKDatabase::merge_databases(&[], &cfg)
            .expect_err("empty input must be rejected under every merge_mode")
            .to_string();
        assert!(
            err.contains("At least one input database is required"),
            "merge_mode={} must report the empty-input cause; got: {}",
            mode,
            err
        );
    }

    // And the prefix-cache route, which has its own copy of the guard.
    let cfg = MergeConfig {
        use_prefix_cache: true,
        ..routing_config(dir.path(), HUGE_BUDGET_BYTES, "auto")
    };
    let err = RKDatabase::merge_databases(&[], &cfg)
        .expect_err("empty input must be rejected on the prefix-cache route too")
        .to_string();
    assert!(
        err.contains("At least one input database is required"),
        "the prefix-cache route must report the empty-input cause; got: {}",
        err
    );

    Ok(())
}

/// The external-sort compatibility rules kept their exact error text when they
/// moved from `&[&RKDatabase]` to `&[DatabaseHeader]`, so the message a caller
/// sees did not change as a side effect of making the route memory-bounded.
///
/// The plan required the strings to be byte-identical because
/// `tests/merge_routing_tests.rs` and the PyO3 docstring describe them. That is
/// true by construction — the format! arguments were not touched — but nothing
/// asserted it, and "byte-identical by construction" is exactly the kind of
/// claim that stops being true the first time someone tidies a format string.
/// This test is the assertion.
///
/// It drives the real prefix-cache route with two genuinely incompatible
/// inputs, so it covers the whole path: header read -> `validate_header_
/// compatibility` -> Err, with no database body ever loaded.
#[test]
fn prefix_cache_kmer_size_mismatch_keeps_its_error_text() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    let a = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 31, true, true)?;
    let b = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30)], 51, true, true)?;
    let a_path = dir.path().join("k31.rkdb");
    let b_path = dir.path().join("k51.rkdb");
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    let config = MergeConfig {
        use_prefix_cache: true,
        temp_dir: work.path().to_path_buf(),
        // `verbose` is what selects the multi-line diagnostic form of the
        // message — the branch this refactor rewrote most heavily, since it
        // formats `first_header.total_kmers` and `header.canonical` rather
        // than calling accessors on materialized databases.
        verbose: true,
        ..routing_config(work.path(), HUGE_BUDGET_BYTES, "auto")
    };

    let err = RKDatabase::merge_databases(&[a_path, b_path], &config)
        .expect_err("a k-mer-size mismatch must be rejected before any merge work happens")
        .to_string();

    // The pre-refactor wording, verbatim.
    assert!(
        err.contains("Database 2 has k-mer size 51, expected 31"),
        "the mismatch message must keep its exact wording; got: {}",
        err
    );
    assert!(
        err.contains("All databases must have the same k-mer size to merge"),
        "the hint line must survive the header refactor; got: {}",
        err
    );
    // The verbose diagnostic reads its numbers off the HEADERS now. A
    // regression that mixed the two sources up (e.g. reporting database 1's
    // values in database 2's line) would pass every assertion above.
    assert!(
        err.contains("Database 1: k-mer size=31, canonical=true, k-mers=2")
            && err.contains("Database 2: k-mer size=51, canonical=true, k-mers=1"),
        "the verbose diagnostic must report each database's OWN header values; got: {}",
        err
    );

    Ok(())
}

/// CR-03 (03-VERIFICATION.md gaps[0]): the streaming merge route — the DEFAULT
/// over-budget route, reachable directly from `PyDatabase.merge` — performed no
/// cross-input k-mer-size validation. `merge_databases_streaming_to_path` read
/// `kmer_size`/`canonical` from `read_header_of(input_paths[0])` only, so a
/// k=21 + k=31 merge under a streaming-selecting budget silently wrote a
/// corrupt database whose header claimed input[0]'s k-mer size. The in-memory
/// and prefix-cache routes already rejected; streaming was the outlier.
///
/// This test drove that gap RED on the pre-fix tree: the merge returned `Ok`
/// and wrote the corrupt output. The fix routes the rejection through
/// `merge_prologue`, so all three routes and both entry points now share it.
///
/// Route-proof discipline (03-04/03-05): a "streaming" arm is only proven if
/// the route ITSELF is asserted. The budget is derived from
/// `estimate_total_kmers` with the over-budget premise asserted first — a
/// hard-coded small budget silently goes vacuous if the fixture ever shrinks
/// below it.
#[test]
fn streaming_route_rejects_cross_input_kmer_size_mismatch() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    // Two well-formed .rkdb files at DIFFERENT k (the construction pattern the
    // message-identity test above uses), each with a handful of records.
    let a = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 21, true, true)?;
    let b = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30), (0xDEF0, 40)], 31, true, true)?;
    let a_path = dir.path().join("k21.rkdb");
    let b_path = dir.path().join("k31.rkdb");
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    // Premise: the estimator sees a positive total, and the budget of 1 byte
    // puts that total strictly over it — `total * 96 > 1` selects the MERGE-02
    // hard route to streaming under "auto".
    let total =
        RKDatabase::estimate_total_kmers(&a_path)? + RKDatabase::estimate_total_kmers(&b_path)?;
    assert!(total > 0, "fixture must carry a positive k-mer estimate");
    assert!(
        total * 96 > 1,
        "the over-budget premise must hold: {} k-mers estimate to {} bytes against a 1-byte budget",
        total,
        total * 96
    );

    let out = work.path().join("merged_kmismatch.rkdb");

    // Arm 1: over-budget "auto" — the streaming route is selected, then the
    // prologue must reject the incompatible set BEFORE any merge work runs.
    let config = routing_config(work.path(), 1, "auto");
    let err = RKDatabase::merge_databases_to_path(&[a_path.clone(), b_path.clone()], &config, &out)
        .expect_err("a k-mer-size mismatch must be rejected on the streaming route")
        .to_string();
    assert!(
        err.contains("Database 2 has k-mer size 31, expected 21"),
        "the rejection must be the compatibility message naming the mismatch; got: {}",
        err
    );
    // Header-only rejection proof: the failure is the compatibility check, not
    // a temp-dir/IO error from chunk work that already started.
    assert!(
        !err.contains("Failed to create temp file") && !err.contains("No such file"),
        "the rejection must fire at validation, before any temp chunk is created; got: {}",
        err
    );
    assert!(
        !out.exists(),
        "an incompatible input set must not write any output byte"
    );

    // Arm 2: the SAME inputs under an explicit `merge_mode: "streaming"` —
    // same rejection, same message.
    let streaming_config = routing_config(work.path(), 1, "streaming");
    let err2 = RKDatabase::merge_databases_to_path(&[a_path, b_path], &streaming_config, &out)
        .expect_err("explicit merge_mode='streaming' must reject the mismatch too")
        .to_string();
    assert!(
        err2.contains("has k-mer size"),
        "the explicit-streaming arm must carry the same compatibility text; got: {}",
        err2
    );
    assert!(!out.exists(), "still no output byte after the second arm");

    // Arm 3 (premise, mirroring the file's premise-assertion style): two
    // SAME-k inputs under the SAME over-budget config merge Ok — so the
    // rejection above is attributable to the mismatch, not to the budget.
    let c = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 21, true, true)?;
    let d = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30), (0xDEF0, 40)], 21, true, true)?;
    let c_path = dir.path().join("k21_c.rkdb");
    let d_path = dir.path().join("k21_d.rkdb");
    c.to_file_path(&c_path)?;
    d.to_file_path(&d_path)?;
    let out_ok = work.path().join("merged_same_k.rkdb");
    RKDatabase::merge_databases_to_path(&[c_path, d_path], &config, &out_ok)
        .expect("same-k inputs under the same over-budget config must merge Ok");
    assert!(
        out_ok.exists(),
        "the compatible merge must have written its output"
    );

    Ok(())
}

/// CR-03's second axis: mixed CANONICAL modes were as silently merged as the
/// k-mismatch above — the streaming route read `canonical` from input[0]'s
/// header alone. The prologue now rejects mixed canonical on every route
/// EXCEPT the prefix-cache route, whose mixed-canonical merging is an
/// advertised capability (see the capability-guard test below).
///
/// Same route-proof discipline: the budget is derived from
/// `estimate_total_kmers`, and the over-budget premise is asserted first.
#[test]
fn streaming_route_rejects_mixed_canonical_without_prefix_cache() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    // Same k, DIFFERENT canonical modes.
    let a = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 21, true, true)?;
    let b = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30), (0xDEF0, 40)], 21, false, true)?;
    let a_path = dir.path().join("canon_true.rkdb");
    let b_path = dir.path().join("canon_false.rkdb");
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    // Over-budget premise, derived not hard-coded.
    let total =
        RKDatabase::estimate_total_kmers(&a_path)? + RKDatabase::estimate_total_kmers(&b_path)?;
    assert!(total > 0, "fixture must carry a positive k-mer estimate");
    assert!(
        total * 96 > 1,
        "the over-budget premise must hold: {} k-mers estimate to {} bytes against a 1-byte budget",
        total,
        total * 96
    );

    let out = work.path().join("merged_canon_mismatch.rkdb");
    let config = routing_config(work.path(), 1, "auto");
    let err = RKDatabase::merge_databases_to_path(&[a_path, b_path], &config, &out)
        .expect_err("mixed canonical modes must be rejected on the streaming route")
        .to_string();
    assert!(
        err.contains("Database 2 has canonical mode false, expected true"),
        "the rejection must be the canonical compatibility message; got: {}",
        err
    );
    assert!(
        !err.contains("Failed to create temp file") && !err.contains("No such file"),
        "the rejection must fire at validation, before any temp chunk is created; got: {}",
        err
    );
    assert!(
        !out.exists(),
        "an incompatible input set must not write any output byte"
    );

    Ok(())
}

/// The capability guard that makes the prologue's `!use_prefix_cache` gate
/// load-bearing: the SAME mixed-canonical pair that the test above rejects
/// MUST still merge successfully under `use_prefix_cache: true`, because the
/// prefix-cache route advertises flexible-canonical merging (its own error
/// hint sends users there). Tightening the prologue unconditionally would
/// break this route's contract — that change belongs to WR-04's developer
/// triage, not to CR-03.
#[test]
fn prefix_cache_route_still_merges_mixed_canonical() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    // The exact pair the rejection test above refuses on the streaming route.
    let a = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 21, true, true)?;
    let b = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30), (0xDEF0, 40)], 21, false, true)?;
    let a_path = dir.path().join("canon_true.rkdb");
    let b_path = dir.path().join("canon_false.rkdb");
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    let out = work.path().join("merged_prefix_cache_mixed.rkdb");
    let config = MergeConfig {
        use_prefix_cache: true,
        temp_dir: work.path().to_path_buf(),
        ..routing_config(work.path(), HUGE_BUDGET_BYTES, "auto")
    };
    RKDatabase::merge_databases_to_path(&[a_path.clone(), b_path.clone()], &config, &out)
        .expect("the prefix-cache route must still merge mixed canonical modes");

    // The output header's canonical flag follows ANY-input semantics —
    // `ExternalSortMerger::new` folds `has_canonical` from EVERY input
    // header (true iff at least one input is canonical), not input[0]'s
    // mode. After the 03-16 fix the output content is genuinely canonical
    // too: `split_files_by_prefix` stores the canonicalized `processed_kmer`
    // (CR-01), so the flag and the records agree.
    let out_header = RKDatabase::read_header_of(&out)?;
    let in0_header = RKDatabase::read_header_of(&a_path)?;
    assert_eq!(
        out_header.canonical, in0_header.canonical,
        "the prefix-cache output header must be canonical — input[0] (a) is, \
         and the flag folds ANY input"
    );
    assert!(
        out.exists(),
        "the capability merge must have written its output"
    );

    // ANY-input semantics pinned NON-coincidentally: the REVERSED input
    // order puts the NON-canonical input first — the order under which an
    // input[0]-mode claim would predict `false` — and the output header
    // must still report `canonical: true` (03-16).
    let out2 = work.path().join("merged_prefix_cache_mixed_rev.rkdb");
    RKDatabase::merge_databases_to_path(&[b_path, a_path], &config, &out2)
        .expect("the prefix-cache route must still merge mixed canonical modes (reversed)");
    let out2_header = RKDatabase::read_header_of(&out2)?;
    assert!(
        out2_header.canonical,
        "reversed input order (input[0] NON-canonical): the output header must \
         still be canonical — ANY-input semantics"
    );

    Ok(())
}

/// Parity guarantee for the route that ALREADY rejected: the in-memory route
/// refused a k-mismatched set (via `validate_compatibility_verbose`, after
/// `from_file_path` had loaded every input). With the prologue validation in
/// place the rejection now fires EARLIER — from 42-byte header reads, before
/// any body is materialized — but the OUTCOME is unchanged: `Err`, same
/// message shape. This test pins that the prologue did not make the
/// previously-safe route stricter or looser for incompatible sets.
#[test]
fn inmemory_route_still_rejects_mismatched_inputs() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    let a = RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 21, true, true)?;
    let b = RKDatabase::from_kmer_pairs(vec![(0x9ABC, 30), (0xDEF0, 40)], 31, true, true)?;
    let a_path = dir.path().join("k21.rkdb");
    let b_path = dir.path().join("k31.rkdb");
    a.to_file_path(&a_path)?;
    b.to_file_path(&b_path)?;

    // Within budget + explicit in-memory mode: the route that always
    // rejected, unchanged in outcome.
    let config = routing_config(work.path(), HUGE_BUDGET_BYTES, "memory");
    let out = work.path().join("merged_inmemory_kmismatch.rkdb");
    let err = RKDatabase::merge_databases_to_path(&[a_path, b_path], &config, &out)
        .expect_err("the in-memory route must keep rejecting mismatched inputs")
        .to_string();
    assert!(
        err.contains("Database 2 has k-mer size 31, expected 21"),
        "the in-memory rejection must keep the same message shape; got: {}",
        err
    );
    assert!(
        !out.exists(),
        "the rejected in-memory merge must not write any output byte"
    );

    Ok(())
}
