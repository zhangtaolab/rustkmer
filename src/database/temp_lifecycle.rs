//! Merge temp-file lifecycle: process-unique subdirs + orphan sweep.
//!
//! Covers **MERGE-03** — "failed/interrupted streaming merges clean up
//! temporary shard files (RAII guard) — no silent disk exhaustion" — and
//! decision **D-06** from `.planning/phases/03-memory-safety/03-CONTEXT.md`:
//!
//! > RAII on the prefix-cache path + process-unique temp subdir + startup
//! > stale-shard sweep. No signal handler. Not resumable.
//!
//! ## Why RAII alone is not enough (Pitfall 2)
//!
//! The release profile sets `panic = "abort"` (`Cargo.toml`, `[profile.release]`).
//! Under abort the runtime calls `abort()` immediately — **no stack unwinding, so
//! no `Drop`**. SIGKILL, `std::process::exit`, and power loss behave the same.
//! [`TempDir`] relies on `Drop` for cleanup, so under those conditions the shards
//! survive.
//!
//! That makes this module's two halves complementary, not redundant:
//!
//! 1. **RAII** ([`create_merge_temp_subdir`] → `TempDir`) covers the common case:
//!    normal scope exit, early `?` return, and `panic = "unwind"` (which is what
//!    `cargo test` uses).
//! 2. **The startup sweep** ([`sweep_stale_merge_dirs`]) is the real defense
//!    against abort/SIGKILL/power loss: on the *next* merge, any
//!    `rustkmer-merge-*` directory older than a generous TTL is removed.
//!
//! ## Naming contract
//!
//! Every merge subdir is `rustkmer-merge-<8 random bytes>` under the configured
//! `temp_dir`. The `rustkmer-merge-` prefix is the sweep's only selector, so it
//! is load-bearing: changing it silently disables orphan cleanup.
//! [`MERGE_TEMP_PREFIX`] is the single source of truth for that string.

use std::path::Path;
use std::time::Duration;

use tempfile::TempDir;

use crate::error::{ProcessingError, ProcessingResult};

/// Prefix on every merge temp subdir.
///
/// The startup sweep selects orphans by this prefix, so it must stay in sync
/// between [`create_merge_temp_subdir`] and [`sweep_stale_merge_dirs`].
pub const MERGE_TEMP_PREFIX: &str = "rustkmer-merge-";

/// Number of random bytes in a merge subdir name (8 bytes = 2^64 namespace).
///
/// Random bytes — not the PID — are what make two *concurrent* merges unable to
/// collide, and what keep a reboot's PID reuse from resurrecting a name.
const MERGE_TEMP_RAND_BYTES: usize = 8;

/// Default orphan TTL for [`sweep_stale_merge_dirs`]: 7 days.
///
/// Deliberately far longer than any realistic merge (hours). A longer TTL only
/// costs leftover disk for a few more days; a shorter one risks deleting the
/// subdir of a legitimately long-running concurrent merge. This is the
/// conservative side of that trade (D-06).
pub const DEFAULT_MERGE_TEMP_TTL: Duration = Duration::from_secs(60 * 60 * 24 * 7);

/// Create a process-unique merge temp subdirectory under `parent`.
///
/// The returned [`TempDir`] owns the directory: dropping it removes the whole
/// tree recursively, which is what makes RAII cleanup cover every shard written
/// beneath it (normal return, early `?` return, and `panic = "unwind"`).
///
/// `parent` must already exist — callers get `config.temp_dir`, which the CLI's
/// `--temp-dir` flag and [`crate::database::merge_config::MergeConfig::default`]
/// both provide.
///
/// # Errors
///
/// Returns [`ProcessingError::io_error`] if `parent` does not exist, is not a
/// directory, or the filesystem refuses the create.
pub fn create_merge_temp_subdir(parent: &Path) -> ProcessingResult<TempDir> {
    let parent_display = parent.display();
    tempfile::Builder::new()
        .prefix(MERGE_TEMP_PREFIX)
        .rand_bytes(MERGE_TEMP_RAND_BYTES)
        .tempdir_in(parent)
        .map_err(|e| {
            ProcessingError::io_error(format!(
                "Failed to create merge temp subdir in '{}': {}",
                parent_display, e
            ))
        })
}

/// Remove orphaned `rustkmer-merge-*` directories left behind by a merge that
/// could not clean up after itself (SIGKILL, `panic = "abort"`,
/// `std::process::exit`, power loss).
///
/// A directory is an orphan candidate when **both** hold:
///   1. its file name starts with [`MERGE_TEMP_PREFIX`], and
///   2. its mtime is strictly older than `SystemTime::now() - ttl`.
///
/// Every failure mode is swallowed and, where informative, logged — a stale
/// sweep must never be able to abort the merge that triggered it. In particular
/// a `temp_dir` that does not exist is a no-op, not an error.
pub fn sweep_stale_merge_dirs(temp_dir: &Path, ttl: Duration) {
    use std::time::SystemTime;

    // `now - ttl` can underflow for an absurd TTL; clamp to the epoch rather
    // than panicking, which would abort the merge the sweep exists to protect.
    let cutoff = SystemTime::now()
        .checked_sub(ttl)
        .unwrap_or(SystemTime::UNIX_EPOCH);

    // A missing / unreadable temp_dir is a no-op, not an error: this sweep runs
    // on the merge path and must never be the reason a merge fails.
    let entries = match std::fs::read_dir(temp_dir) {
        Ok(entries) => entries,
        Err(e) => {
            log::debug!(
                "Stale merge temp sweep skipped: cannot read '{}': {}",
                temp_dir.display(),
                e
            );
            return;
        }
    };

    for entry in entries.flatten() {
        let name = entry.file_name();
        if !name.to_string_lossy().starts_with(MERGE_TEMP_PREFIX) {
            continue;
        }

        let path = entry.path();
        // `entry.metadata()` follows symlinks; `file_type()` does not. A symlink
        // carrying our prefix is NOT ours to recurse into — refuse it rather
        // than deleting whatever it points at.
        match entry.file_type() {
            Ok(ft) if ft.is_dir() => {}
            Ok(_) => continue,
            Err(e) => {
                log::warn!(
                    "Stale merge temp sweep: cannot stat '{}': {}",
                    path.display(),
                    e
                );
                continue;
            }
        }

        let mtime = match entry.metadata().and_then(|m| m.modified()) {
            Ok(mtime) => mtime,
            Err(e) => {
                log::warn!(
                    "Stale merge temp sweep: cannot read mtime of '{}': {}",
                    path.display(),
                    e
                );
                continue;
            }
        };

        if mtime >= cutoff {
            // Younger than the TTL: assumed to belong to a merge that is still
            // running. Deleting it would corrupt a live merge (T-03-06).
            continue;
        }

        match std::fs::remove_dir_all(&path) {
            Ok(()) => log::info!("Swept stale merge temp dir: {}", path.display()),
            Err(e) => log::warn!(
                "Failed to sweep stale merge temp dir '{}': {}",
                path.display(),
                e
            ),
        }
    }
}
