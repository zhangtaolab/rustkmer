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
//! Plan 03-01 Task 1 is the Wave-0 scaffold: the four routing/reject tests
//! below are `#[ignore]`d so the target compiles against the PRE-fix API
//! (no test body may reference an API that does not exist yet). Task 2
//! un-ignores them, lands the header-only estimator + the D-02 reject branch,
//! and strengthens the two D-01 assertions with a direct
//! `RKDatabase::estimate_total_kmers` call.
//!
//! No `unsafe`, no pyo3, no new dependencies.

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

/// A temp directory path that does not exist. Used as the "which merge path
/// ran?" probe — see the module docstring.
fn missing_temp_dir(root: &Path) -> PathBuf {
    root.join("this_temp_dir_does_not_exist")
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
///
/// RED until Task 2 lands the header-only estimator and the hard route.
// TODO(03-01 Task 2): un-ignore once the estimator + hard route land.
#[test]
#[ignore = "RED stub — awaiting 03-01 Task 2 header-only estimator + hard route"]
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
    let err = RKDatabase::merge_databases(&[a, b], &no_temp).expect_err(
        "over-budget auto merge must hard-route to streaming, not warn-and-continue in-memory",
    );
    let msg = err.to_string();
    assert!(
        msg.contains("temp") || msg.contains("No such file"),
        "expected a temp-chunk-creation failure proving the streaming path ran; got: {}",
        msg
    );

    Ok(())
}

/// MERGE-02 / D-02 — an explicit `merge_mode: "memory"` merge whose estimate
/// exceeds `max_memory_usage` must be REJECTED with a clear error, never
/// silently OOM.
///
/// RED until Task 2 adds the reject branch.
// TODO(03-01 Task 2): un-ignore once the D-02 reject branch lands.
#[test]
#[ignore = "RED stub — awaiting 03-01 Task 2 D-02 reject branch"]
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
///
/// RED until Task 2 preserves/lands the explicit streaming short-circuit.
// TODO(03-01 Task 2): un-ignore once the streaming short-circuit is asserted.
#[test]
#[ignore = "RED stub — awaiting 03-01 Task 2 streaming short-circuit assertion"]
fn merge_explicit_streaming_mode_always_streams() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;

    // Within budget, yet explicitly streaming: the temp_dir probe must fail.
    let probe_inputs = [
        write_input_db(dir.path(), "p1.rkdb", 8)?,
        write_input_db(dir.path(), "p2.rkdb", 8)?,
    ];
    let err = RKDatabase::merge_databases(
        &probe_inputs,
        &routing_config(&missing_temp_dir(dir.path()), HUGE_BUDGET_BYTES, "streaming"),
    )
    .expect_err(
        "merge_mode='streaming' must take the streaming path even when the estimate is within budget",
    );
    let msg = err.to_string();
    assert!(
        msg.contains("temp") || msg.contains("No such file"),
        "expected a temp-chunk-creation failure proving the streaming path ran; got: {}",
        msg
    );

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
///
/// RED until Task 2 exposes `RKDatabase::estimate_total_kmers`.
/// TODO(03-01 Task 2): un-ignore and assert the header-only helper directly.
#[test]
#[ignore = "RED stub — awaiting 03-01 Task 2 RKDatabase::estimate_total_kmers"]
fn estimator_reads_header_only_no_materialization() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;

    // A file whose header claims 5 billion k-mers but whose body is truncated
    // to the bare 42-byte header. `from_file_path` cannot load this.
    const DECLARED: u64 = 5_000_000_000;
    let path = write_truncated_oversized_db(dir.path(), "truncated.rkdb", 16, DECLARED)?;

    // Premise (D-01): the materializing loader genuinely fails on this file,
    // so a test that can still read the estimate has proven header-only
    // behavior. This assertion is independent of the fix and stays meaningful
    // afterwards.
    let materialize = RKDatabase::from_file_path(&path);
    assert!(
        materialize.is_err(),
        "premise: from_file_path must fail on a truncated body (it materializes entries): {:?}",
        materialize.err()
    );

    // Task 2 replaces this block with a direct assertion on the header-only
    // helper: `RKDatabase::estimate_total_kmers(&path) == DECLARED`, which
    // only holds if the 42-byte header is read and the body is never touched.
    Ok(())
}
