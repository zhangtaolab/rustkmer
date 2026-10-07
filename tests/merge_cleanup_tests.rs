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

use rustkmer::database::temp_lifecycle::{
    create_merge_temp_subdir, sweep_stale_merge_dirs, DEFAULT_MERGE_TEMP_TTL, MERGE_TEMP_PREFIX,
};
use std::path::{Path, PathBuf};
use std::time::Duration;
use tempfile::TempDir;

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
// TODO(03-02 Task 2): un-ignore.
#[test]
#[ignore]
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
// TODO(03-02 Task 2): un-ignore.
#[test]
#[ignore]
fn orphan_subdir_swept_on_next_start() {
    let parent = TempDir::new().unwrap();

    // An orphan standing in for what an aborted merge left behind. Its mtime is
    // "now", so a tiny TTL is what marks it stale — that keeps the test
    // portable (no `filetime` dev-dependency, no `std::fs::set_modified`, which
    // is still unstable) while exercising the real age comparison.
    let orphan = parent.path().join(format!("{}orphan", MERGE_TEMP_PREFIX));
    std::fs::create_dir_all(&orphan).unwrap();
    std::fs::write(orphan.join("ext_sort_AAAA_file_000.tmp"), b"shard").unwrap();

    // A live merge's subdir, which must survive the same sweep.
    let live = create_merge_temp_subdir(parent.path()).unwrap();

    sweep_stale_merge_dirs(parent.path(), Duration::from_nanos(1));

    assert!(
        !orphan.exists(),
        "stale merge temp dir should have been swept"
    );
    assert!(
        live.path().exists(),
        "a fresh merge temp dir must survive the sweep"
    );

    // The production TTL is what protects in-flight merges at real scale.
    sweep_stale_merge_dirs(parent.path(), DEFAULT_MERGE_TEMP_TTL);
    assert!(
        live.path().exists(),
        "the 7-day TTL must not remove a live merge subdir"
    );
}

/// RAII must clean up on `panic = "unwind"` — the mode `cargo test` runs in and
/// therefore the mode in which a real early-return bug is catchable.
/// TODO(03-02 Task 2): un-ignore.
#[test]
#[ignore]
fn cleanup_runs_on_panic_unwind() {
    let parent = TempDir::new().unwrap();
    let subdir: std::cell::RefCell<Option<PathBuf>> = std::cell::RefCell::new(None);

    let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let subdir_guard = create_merge_temp_subdir(parent.path()).unwrap();
        *subdir.borrow_mut() = Some(subdir_guard.path().to_path_buf());
        // Stand in for shards already written mid-merge.
        std::fs::write(
            subdir_guard.path().join("ext_sort_AAAA_file_000.tmp"),
            b"shard",
        )
        .unwrap();
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

/// Two merges running at once must not be able to reach each other's shards.
/// TODO(03-02 Task 2): un-ignore.
#[test]
#[ignore]
fn two_concurrent_merges_do_not_collide() {
    let parent = TempDir::new().unwrap();

    let paths: Vec<PathBuf> = std::thread::scope(|scope| {
        let handles: Vec<_> = (0..2)
            .map(|_| {
                let parent = parent.path().to_path_buf();
                scope.spawn(move || {
                    let subdir = create_merge_temp_subdir(&parent).unwrap();
                    let shard = subdir.path().join("ext_sort_AAAA_file_000.tmp");
                    std::fs::write(&shard, b"shard").unwrap();
                    shard
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).collect()
    });

    assert_eq!(merge_subdirs(parent.path()).len(), 2);
    assert_ne!(paths[0], paths[1], "concurrent merges wrote the same shard");

    // Both shards still exist: neither merge clobbered or deleted the other.
    assert!(paths[0].exists() && paths[1].exists());
}
