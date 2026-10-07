//! Merge temp-shard cleanup tests (Phase 3, plan 03-02).
//!
//! Requirement covered:
//!   - **MERGE-03** — "failed/interrupted streaming merges clean up temporary
//!     shard files (RAII guard) — no silent disk exhaustion."
//!
//! Decision honored — **D-06** from
//! `.planning/phases/03-memory-safety/03-CONTEXT.md`: RAII on the prefix-cache
//! path + a process-unique temp subdir + a startup stale-shard sweep. No signal
//! handler. Not resumable.
//!
//! ## The scenario this file exists for
//!
//! `prefix_cache_merge.rs` used to `remove_file` its shards only on the success
//! branch. Any other exit — an early `?` return, a panic, `kill -9`, a power
//! loss — leaked every shard. Because shard names were also flat inside the
//! shared `temp_dir`, an orphan was indistinguishable from a concurrent merge's
//! live scratch space, so nothing could safely clean it up later.
//!
//! ## What RAII can and cannot prove here
//!
//! `cargo test` builds with `panic = "unwind"`, so these tests exercise the
//! unwind half of the defense. The release profile sets `panic = "abort"`,
//! where `Drop` does **not** run — that case is deliberately NOT asserted by a
//! Rust test (it would kill the harness). It is covered instead by the
//! *sweep* test: `orphan_subdir_swept_on_next_start` asserts that whatever an
//! abort left behind is removed on the next merge, which is the property that
//! actually protects the disk.
//!
//! ## Scope note
//!
//! D-06 deliberately does NOT add a `ctrlc`/signal handler, and a failed merge
//! is a clean restart rather than a resumable one (both deferred to v2).
//!
//! No `unsafe`, no pyo3, no new dependencies (`tempfile` was promoted to
//! `[dependencies]` in plan 03-02 Task 1 for production use).

mod common;

use common::create_test_database;
use rustkmer::database::format::RKDatabase;
use rustkmer::database::merge_config::MergeConfig;
use rustkmer::database::temp_lifecycle::{
    create_merge_temp_subdir, sweep_stale_merge_dirs, DEFAULT_MERGE_TEMP_TTL, MERGE_TEMP_PREFIX,
};
use rustkmer::database::ExternalSortMerger;
use std::path::{Path, PathBuf};
use std::time::Duration;
use tempfile::TempDir;

/// k-mer size for the synthetic merge inputs (inside the D-13 matrix).
const K: u8 = 21;

/// Write two small, compatible `.rkdb` files and return their paths.
///
/// Two inputs (not one) because the prefix-cache merge shards per (bucket,
/// input file) pair — a single input would exercise a fraction of the shard
/// naming scheme.
fn write_merge_inputs(dir: &Path) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    for idx in 0..2 {
        let db = create_test_database(200, K, true, true).expect("test database");
        let path = dir.join(format!("input_{}.rkdb", idx));
        db.write_to_file(&path).expect("write test database");
        paths.push(path);
    }
    paths
}

/// Directory entries in `parent` whose names carry the merge prefix.
fn merge_subdirs(parent: &Path) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = std::fs::read_dir(parent)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .map(|n| n.starts_with(MERGE_TEMP_PREFIX))
                .unwrap_or(false)
        })
        .collect();
    found.sort();
    found
}

/// A merge subdir must be process-unique, or two concurrent merges share shard
/// paths and corrupt each other's output (threat T-03-06).
#[test]
fn subdir_is_process_unique() {
    let parent = TempDir::new().unwrap();

    let first = create_merge_temp_subdir(parent.path()).unwrap();
    let second = create_merge_temp_subdir(parent.path()).unwrap();

    assert_ne!(
        first.path(),
        second.path(),
        "two merge subdirs must not share a path"
    );
    assert_eq!(merge_subdirs(parent.path()).len(), 2);

    for dir in [first.path(), second.path()] {
        let name = dir.file_name().unwrap().to_str().unwrap();
        assert!(
            name.starts_with(MERGE_TEMP_PREFIX),
            "subdir name must carry the sweep prefix, got {:?}",
            name
        );
        // The random suffix keeps two merges apart even when both report the
        // same PID (a restarted process, or two threads in one process).
        let suffix = name.strip_prefix(MERGE_TEMP_PREFIX).unwrap();
        assert!(!suffix.is_empty(), "subdir name must carry a random suffix");
    }
}

/// The startup sweep is the defense against `panic = "abort"` / SIGKILL /
/// power loss, where `Drop` never runs. An orphan older than the TTL is removed
/// on the next merge; a *fresh* one is left alone so a concurrent merge is safe.
#[test]
fn orphan_subdir_swept_on_next_start() {
    let parent = TempDir::new().unwrap();

    let orphan = parent.path().join(format!("{}orphan", MERGE_TEMP_PREFIX));
    std::fs::create_dir_all(&orphan).unwrap();
    std::fs::write(orphan.join("ext_sort_AAAA_file_000.tmp"), b"shard").unwrap();
    backdate(&orphan, DEFAULT_MERGE_TEMP_TTL + Duration::from_secs(60));

    // A live merge's subdir, which must survive the same sweep.
    let live = create_merge_temp_subdir(parent.path()).unwrap();

    sweep_stale_merge_dirs(parent.path(), DEFAULT_MERGE_TEMP_TTL);

    assert!(
        !orphan.exists(),
        "a merge temp dir older than the TTL must be swept"
    );
    assert!(
        live.path().exists(),
        "the 7-day TTL must not remove a live merge subdir"
    );
}

/// Backdate `path`'s mtime by `age`.
///
/// `File::set_times` (stable since Rust 1.75) lets this test age a directory
/// without a `filetime` dev-dependency and without the still-unstable
/// `std::fs::set_modified`.
fn backdate(path: &Path, age: Duration) {
    let handle = std::fs::File::open(path).expect("open for mtime update");
    let modified = std::time::SystemTime::now() - age;
    handle
        .set_times(std::fs::FileTimes::new().set_modified(modified))
        .unwrap_or_else(|e| panic!("backdate {}: {}", path.display(), e));
}

/// RAII on the *merger* must clean up on `panic = "unwind"` — the mode
/// `cargo test` runs in, and therefore the mode in which a real early-return or
/// bug-panic is catchable. This is the MERGE-03 regression guard for the exact
/// gap that shipped: shards used to be removed only on the success branch.
#[test]
fn cleanup_runs_on_panic_unwind() {
    let parent = TempDir::new().unwrap();
    let inputs = write_merge_inputs(parent.path());
    let subdir: std::cell::RefCell<Option<PathBuf>> = std::cell::RefCell::new(None);

    let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let merger = ExternalSortMerger::new(
            inputs.clone(),
            parent.path().to_path_buf(),
            1024,
            1,
            "auto".to_string(),
            false,
        )
        .unwrap();
        let owned = merger.merge_temp_subdir_path().unwrap().to_path_buf();
        *subdir.borrow_mut() = Some(owned.clone());

        // Stand in for shards already written mid-merge, so cleanup is proven
        // against a NON-empty subdir rather than an empty one.
        for prefix in ["AAAA", "CCCC"] {
            std::fs::write(
                owned.join(format!("ext_sort_{}_file_000.tmp", prefix)),
                b"shard",
            )
            .unwrap();
        }

        panic!("injected mid-merge panic (MERGE-03 cleanup probe)");
    }));

    assert!(outcome.is_err(), "the injected panic must have unwound");

    let leaked = subdir.borrow().clone().expect("subdir path was captured");
    assert!(
        !leaked.exists(),
        "merge temp subdir must be gone after an unwind: {}",
        leaked.display()
    );
    assert!(
        merge_subdirs(parent.path()).is_empty(),
        "no merge temp subdir may survive an unwind, found {:?}",
        merge_subdirs(parent.path())
    );
}

/// A *successful* merge must also leave nothing behind — the common case, and
/// the one the old success-only cleanup already handled. Asserted separately so
/// a regression in either direction (leak, or over-eager deletion of the
/// merged output) is distinguishable.
#[test]
fn successful_merge_leaves_no_shards() {
    let parent = TempDir::new().unwrap();
    let inputs = write_merge_inputs(parent.path());
    let output = parent.path().join("merged.rkdb");

    let mut merger = ExternalSortMerger::new(
        inputs,
        parent.path().to_path_buf(),
        1024,
        1,
        "auto".to_string(),
        false,
    )
    .unwrap();
    let subdir = merger.merge_temp_subdir_path().unwrap().to_path_buf();
    merger.external_sort_merge(&output).unwrap();

    assert!(output.exists(), "the merge must still produce its output");
    drop(merger);

    assert!(
        !subdir.exists(),
        "merge temp subdir must be gone after a successful merge: {}",
        subdir.display()
    );
    assert!(merge_subdirs(parent.path()).is_empty());
}

/// Two merges running at once must not be able to reach each other's shards
/// (threat T-03-06). Both mergers here are constructed over the *same* inputs
/// and the *same* parent temp dir — the collision the flat naming scheme made
/// possible before D-06.
#[test]
fn two_concurrent_merges_do_not_collide() {
    let parent = TempDir::new().unwrap();
    let inputs = write_merge_inputs(parent.path());

    let (subdir_a, merger_a, subdir_b, merger_b) = std::thread::scope(|scope| {
        let a = scope.spawn({
            let inputs = inputs.clone();
            let parent = parent.path().to_path_buf();
            move || start_merger(inputs, parent)
        });
        let b = scope.spawn({
            let inputs = inputs.clone();
            let parent = parent.path().to_path_buf();
            move || start_merger(inputs, parent)
        });
        let (subdir_a, merger_a) = a.join().unwrap();
        let (subdir_b, merger_b) = b.join().unwrap();
        (subdir_a, merger_a, subdir_b, merger_b)
    });

    assert_ne!(
        subdir_a, subdir_b,
        "concurrent merges must not share a temp subdir"
    );
    assert_eq!(
        merge_subdirs(parent.path()).len(),
        2,
        "both merges must still own a live subdir"
    );
    // Both shards still exist: neither merge clobbered or deleted the other.
    assert!(subdir_a.join("ext_sort_AAAA_file_000.tmp").exists());
    assert!(subdir_b.join("ext_sort_AAAA_file_000.tmp").exists());

    drop(merger_a);
    drop(merger_b);

    assert!(
        !subdir_a.exists() && !subdir_b.exists(),
        "both merge temp subdirs must be cleaned up on drop"
    );
    assert!(merge_subdirs(parent.path()).is_empty());
}

/// Build a merger over `inputs`/`parent` and plant a shard inside its subdir.
///
/// The merger is returned alongside the subdir path so the caller can keep it
/// alive while asserting that neither merge disturbed the other's shards.
fn start_merger(inputs: Vec<PathBuf>, parent: PathBuf) -> (PathBuf, ExternalSortMerger) {
    let merger =
        ExternalSortMerger::new(inputs, parent, 1024, 1, "auto".to_string(), false).unwrap();
    let subdir = merger
        .merge_temp_subdir_path()
        .expect("merger owns a temp subdir")
        .to_path_buf();
    std::fs::write(subdir.join("ext_sort_AAAA_file_000.tmp"), b"shard").unwrap();
    (subdir, merger)
}

/// The sweep is only a defense if something actually calls it. This asserts the
/// wiring: an orphan dropped into `config.temp_dir` is gone after a plain
/// `RKDatabase::merge_databases` call.
///
/// The merge is deliberately routed to the **in-memory** path, which never
/// touches `temp_dir` for anything else — so the orphan's disappearance can
/// only be attributed to the sweep at the top of the dispatch, not to some
/// side effect of the merge strategy.
#[test]
fn merge_databases_sweeps_stale_orphans() {
    let parent = TempDir::new().unwrap();
    let inputs = write_merge_inputs(parent.path());

    let orphan = parent.path().join(format!("{}orphan", MERGE_TEMP_PREFIX));
    std::fs::create_dir_all(&orphan).unwrap();
    std::fs::write(orphan.join("ext_sort_ACGT_file_000.tmp"), b"orphan").unwrap();
    backdate(&orphan, DEFAULT_MERGE_TEMP_TTL + Duration::from_secs(60));

    let config = MergeConfig {
        temp_dir: parent.path().to_path_buf(),
        merge_mode: "memory".to_string(),
        use_prefix_cache: false,
        keep_intermediate: false,
        // Comfortably above the 200-k-mer input's estimate so the in-memory
        // path is admissible (03-01's D-02 reject does not fire).
        max_memory_usage: 64 * 1024 * 1024,
        ..Default::default()
    };

    RKDatabase::merge_databases(&inputs, &config).expect("merge should succeed");

    assert!(
        !orphan.exists(),
        "merge_databases must sweep stale merge temp dirs on entry ({} left behind)",
        orphan.display()
    );
}
