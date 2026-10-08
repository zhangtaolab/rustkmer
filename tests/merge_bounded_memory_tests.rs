//! Merge output-boundedness tests (Phase 3, plan 03-10) — closes the
//! substantive half of gap **G2** (code-review finding **CR-02**).
//!
//! ## The gap this file closes
//!
//! Plan 03-09 removed the merge routes' INPUT materialization (every route
//! now reads its inputs' 42-byte headers instead of loading whole
//! databases). Plan 03-10 removes the OUTPUT materialization, which was the
//! reason "streaming" was not a memory escape at all:
//! `merge_databases_streaming` drained the entire merged stream into
//! `sorted_kmers: Vec<(u128, u32)>` and then called `from_kmer_pairs` —
//! building a THIRD full copy as a `Vec<KmerEntry>` — before the caller
//! wrote the result to disk. The route chosen precisely because the inputs
//! do not fit held roughly **2x the dataset at peak**, strictly worse than
//! the in-memory path it replaced. The prefix-cache path had the same shape
//! (`from_file_path` read-back of its own finished output).
//!
//! The fix under test: `RKDatabase::merge_databases_to_path` writes `.rkdb`
//! bytes as `merge_sorted_chunks` yields them (streaming route), hands the
//! prefix-cache result over by rename, and both shipped front-ends call it.
//!
//! ## The measurement method — and the one design fact that matters
//!
//! **The bound is DERIVED FROM THE PINNED CHUNK SIZE, not from N.** The test
//! pins `chunk_size = CHUNK_ENTRIES = 50_000` on its `MergeConfig` and
//! asserts the resident-memory growth stays under
//! `4 * CHUNK_ENTRIES * size_of::<KmerEntry>()` = 6,400,000 bytes:
//!
//! - **Post-fix working set is O(chunk)**: `DatabaseStreamIterator::next`
//!   allocates `Vec::with_capacity(min(chunk_size, remaining))` of
//!   `KmerEntry`, and `size_of::<KmerEntry>()` is 32 (a 16-byte `u128` at
//!   align 16 plus a 4-byte `u32` plus 4 bytes of tail padding — asserted
//!   below so the derivation cannot quietly become false). With the pinned
//!   value that is 1,600,000 B per chunk load, plus one `BufWriter` and the
//!   run-head heap. Measured growth must stay under 6,400,000 B — 4x
//!   headroom over a single chunk load.
//! - **Pre-fix peak was O(N)**: `sorted_kmers` at 32 B per record
//!   (32,000,000 B at N = 1,000,000) alive at the same time as the
//!   `from_kmer_pairs` `Vec<KmerEntry>` (another 32,000,000 B) —
//!   64,000,000 B, **10x the threshold**, on the far side of it.
//! - The two land on OPPOSITE sides of the threshold; that is the only
//!   property that makes this test a discriminator. An earlier revision of
//!   the plan asserted an N-relative bound (five million bytes at
//!   N = 1,000,000 — twenty bytes per k-mer, quartered) while never pinning
//!   `chunk_size`: it inherited
//!   `MergeConfig::default().chunk_size = 50_000_000`, whose chunk `Vec`
//!   alone is 32 MB — 6.4x over its own threshold, with the pre-fix peak
//!   also over it. That bound could not pass on a correct implementation and
//!   would have gone red under the mutation for the wrong reason. The
//!   withdrawn N-relative formula does not appear in this file, by design.
//!
//! The RSS figure is the **peak resident set during the merge**, sampled by
//! a background thread, minus the baseline taken after the fixture build
//! (and its drop) completes. A plain before/after delta would be masked
//! whenever the allocator returns the merge's freed pages to the OS before
//! the second reading — the merge's transient 64 MB would come and go
//! unnoticed. Plan 03-06 recorded exactly that failure mode ("an RSS delta
//! after a drop measures allocator free-list reuse, not footprint").
//!
//! ## RSS sources
//!
//! On Linux the source is the `VmRSS:` line of `/proc/self/status` (kB), as
//! in `tests/dense_memory_tests.rs`. Elsewhere (this file must stay
//! meaningful on non-Linux dev hosts — a bound that never executes proves
//! nothing) it is `ps -o rss= -p <pid>`, which reports the same quantity in
//! the same unit. Both are per-process, so:
//!
//! ## Running this binary
//!
//! ```text
//! cargo test --test merge_bounded_memory_tests -- --test-threads=1 --nocapture
//! ```
//!
//! `--test-threads=1` because the measurement is process-global: a sibling
//! test allocating concurrently would be charged to the merge.
//!
//! `mod common;` is deliberately omitted (the `tests/merge_route_parity_
//! tests.rs` precedent): the shared module's own unit tests would run
//! concurrently with the measurement inside this binary under a default
//! `cargo test` invocation, and the fixture builders are 8 lines.
//!
//! No `unsafe`, no pyo3, no new dependencies.

use anyhow::Result;
use rustkmer::database::format::RKDatabase;
use rustkmer::database::merge_config::{MergeConfig, MergeStrategy};
use rustkmer::database::temp_lifecycle::{DEFAULT_MERGE_TEMP_TTL, MERGE_TEMP_PREFIX};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;

/// k-mer size used by every fixture (inside the D-13 coverage matrix).
const K: u8 = 21;

/// The chunk size the measurement PINS on its `MergeConfig` — 50,000
/// `KmerEntry` per chunk `Vec`.
///
/// Everything else in the measurement arithmetic is derived from this
/// constant, so the bound cannot drift away from the working set it bounds.
const CHUNK_ENTRIES: usize = 50_000;

/// `size_of::<KmerEntry>()`: a 16-byte `u128` (align 16) + a 4-byte `u32` +
/// 4 bytes of tail padding = 32. Asserted, not assumed, in
/// `streaming_merge_peak_memory_is_bounded_by_chunk_not_dataset`.
const KMER_ENTRY_BYTES: usize = 32;

/// One chunk load of `KmerEntry` at the pinned chunk size: 1,600,000 B.
const CHUNK_BYTES: u64 = (CHUNK_ENTRIES * KMER_ENTRY_BYTES) as u64;

/// The RSS bound: 4x one chunk load = 6,400,000 B.
///
/// 4x headroom over a single chunk load covers the run-head heap, the
/// `BufWriter`s and allocator granularity, while sitting 10x BELOW the
/// pre-fix 64,000,000 B peak at N = 1,000,000 — the two figures land on
/// opposite sides of it, which is what makes the bound a discriminator.
const RSS_BOUND_BYTES: u64 = CHUNK_BYTES * 4;

/// A budget no toy fixture can approach, so the within-budget branch is
/// taken deterministically.
const HUGE_BUDGET_BYTES: usize = 1024 * 1024 * 1024;

/// Fixture entry count for the measurement. If the machine is
/// memory-constrained this may be lowered — but **neither `CHUNK_ENTRIES`
/// nor `RSS_BOUND_BYTES` may be loosened to fit a smaller N**: the bound is
/// a property of the chunk size, and moving it to accommodate a fixture
/// reintroduces exactly the defect this file exists to catch.
const MEASUREMENT_ENTRIES: usize = 1_000_000;

/// Encode `value` as a base-4 k-mer over `kmer_size` bases (A=0, C=1, G=2,
/// T=3), the same factory `tests/common` provides — duplicated locally per
/// the parity-binary precedent so no sibling tests run inside this process.
///
/// Injective for `value < 4^kmer_size`, so `0..MEASUREMENT_ENTRIES` yields
/// `MEASUREMENT_ENTRIES` distinct k-mers at k=21.
fn encode_test_kmer(value: u64, kmer_size: u8) -> u128 {
    let mut kmer = 0u128;
    let mut v = value;
    for i in 0..kmer_size {
        let base = (v % 4) as u128;
        kmer |= base << (2 * i);
        v /= 4;
    }
    kmer
}

/// Current resident set size in kB.
///
/// The `VmRSS:` line of `/proc/self/status` — the Linux-authoritative
/// source, same as `tests/dense_memory_tests.rs` — parsed for the value
/// before the unit.
#[cfg(target_os = "linux")]
fn current_rss_kb() -> Option<u64> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    status.lines().find_map(|line| {
        let rest = line.strip_prefix("VmRSS:")?;
        rest.split_whitespace().next()?.parse::<u64>().ok()
    })
}

/// Current resident set size in kB, via `ps -o rss= -p <pid>`.
///
/// The portable fallback for hosts without `/proc` (macOS among them): `ps`
/// reports the same quantity — the process's resident set — in the same kB
/// unit, so the measurement executes instead of being silently skipped. A
/// memory bound that never runs on the developer's machine proves nothing
/// (this plan's own RED discipline demands the measurement be executable
/// wherever the tests run).
#[cfg(not(target_os = "linux"))]
fn current_rss_kb() -> Option<u64> {
    let out = std::process::Command::new("ps")
        .args(["-o", "rss=", "-p", &std::process::id().to_string()])
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    String::from_utf8_lossy(&out.stdout).trim().parse::<u64>().ok()
}

/// Run `f`, tracking the PEAK resident set observed while it runs.
///
/// Returns `(f's result, peak_kb)`. The peak is sampled by a background
/// thread every ~2 ms because the merge's transient allocations are freed
/// before it returns: an after-the-fact reading would measure whatever the
/// allocator chose to retain, not what the merge actually held (the 03-06
/// lesson — see the module docstring).
fn run_tracking_peak_rss<T>(f: impl FnOnce() -> T) -> (T, u64) {
    let peak_kb = Arc::new(AtomicU64::new(0));
    let stop = Arc::new(AtomicBool::new(false));

    let sampler_peak = Arc::clone(&peak_kb);
    let sampler_stop = Arc::clone(&stop);
    let sampler = std::thread::spawn(move || {
        while !sampler_stop.load(Ordering::Relaxed) {
            if let Some(kb) = current_rss_kb() {
                sampler_peak.fetch_max(kb, Ordering::Relaxed);
            }
            std::thread::sleep(Duration::from_millis(2));
        }
    });

    let result = f();

    stop.store(true, Ordering::Relaxed);
    let _ = sampler.join();
    (result, peak_kb.load(Ordering::Relaxed))
}

/// A temp directory path that does not exist — the route probe (plan 03-01).
///
/// The streaming route writes sorted chunk files into `config.temp_dir`; the
/// in-memory route never touches it. Pointing `temp_dir` at a nonexistent
/// directory therefore turns route selection into an observable outcome.
fn missing_temp_dir(root: &Path) -> PathBuf {
    root.join("this_temp_dir_does_not_exist")
}

/// Assert `err` is the STREAMING route's chunk-creation failure.
///
/// The 03-09 form: the message must name BOTH the operation only the
/// streaming path performs (`Failed to create temp file`, from
/// `TempFileManager::create_temp_file`) AND the nonexistent directory the
/// probe pointed at — a k-mer-size mismatch, a bad input path or a corrupt
/// input satisfies neither pair.
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
        "the failure must name the nonexistent temp dir '{}' the route probe pointed at, \
         proving the streaming path was entered rather than some other failure. Got: {}",
        missing_name,
        msg
    );
}

/// Assert `err` is the PREFIX-CACHE route's subdir-creation failure.
///
/// The prefix-cache analogue of [`assert_streaming_route_proved`]: the route
/// creates its process-unique merge subdir inside `config.temp_dir`
/// (`create_merge_temp_subdir` inside `ExternalSortMerger::new`) before any
/// other filesystem work, so a nonexistent `temp_dir` fails there first,
/// with that operation named.
fn assert_prefix_cache_route_proved(err: &rustkmer::ProcessingError, missing: &Path) {
    let msg = err.to_string();
    let missing_name = missing
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    assert!(
        msg.contains("Failed to create merge temp subdir"),
        "expected the prefix-cache route's merge-subdir-creation failure; the message must \
         name the operation only the prefix-cache path performs. Got: {}",
        msg
    );
    assert!(
        !missing_name.is_empty() && msg.contains(&missing_name),
        "the failure must name the nonexistent temp dir '{}' the route probe pointed at. \
         Got: {}",
        missing_name,
        msg
    );
}

/// Backdate `path`'s mtime by `age`.
///
/// `File::set_times` (stable since Rust 1.75), the same technique
/// `tests/merge_cleanup_tests.rs` proves works — duplicated here rather
/// than shared because the two binaries belong to different plans and a
/// `tests/common` module would be a cross-wave coupling for 6 lines (and
/// would put sibling tests inside this measurement's process).
fn backdate(path: &Path, age: Duration) {
    let handle = std::fs::File::open(path).expect("open for mtime update");
    let modified = std::time::SystemTime::now() - age;
    handle
        .set_times(std::fs::FileTimes::new().set_modified(modified))
        .unwrap_or_else(|e| panic!("backdate {}: {}", path.display(), e));
}

/// Write a small deterministic two-input fixture: `entries` distinct k-mers
/// per input, counts varied, canonical, sorted.
///
/// The two inputs are built from DISJOINT value ranges (the second offset by
/// `1 << 40`, far beyond `entries` at k=21) so their k-mer sets cannot
/// overlap — the union is exactly `2 * entries` and a dropped input moves
/// the output size, not just a count.
fn write_fixture_pair(dir: &Path, label: &str, entries: u64) -> Result<(PathBuf, PathBuf)> {
    let mut paths = Vec::with_capacity(2);
    for (idx, offset) in [0u64, 1 << 40].into_iter().enumerate() {
        let kmers: Vec<(u128, u32)> = (0..entries)
            .map(|i| {
                (
                    encode_test_kmer(offset + i, K),
                    ((offset + i) % 17 + 1) as u32,
                )
            })
            .collect();
        let db = RKDatabase::from_kmer_pairs(kmers, K, true, true)?;
        let path = dir.join(format!("{}_{}.rkdb", label, idx));
        db.to_file_path(&path)?;
        paths.push(path);
    }
    Ok((paths.remove(0), paths.remove(0)))
}

/// The measurement: a streaming merge's resident growth is bounded by the
/// PINNED CHUNK, not by the dataset.
///
/// The pre-fix body this test exists to catch held `sorted_kmers`
/// (32,000,000 B at N = 1,000,000) plus a `from_kmer_pairs` `Vec<KmerEntry>`
/// (another 32,000,000 B) — 64,000,000 B against this test's 6,400,000 B
/// bound, 10x over. The post-fix working set is one chunk `Vec` (1,600,000
/// B) plus buffers. Task 3's mutation check restored the accumulating body
/// and observed the RED figure recorded in the plan SUMMARY.
#[test]
fn streaming_merge_peak_memory_is_bounded_by_chunk_not_dataset() -> Result<()> {
    // The derivation's floor: if `KmerEntry` ever stops being 32 bytes, the
    // constant arithmetic above is wrong and must be re-derived, not
    // re-asserted.
    assert_eq!(
        std::mem::size_of::<rustkmer::database::format::KmerEntry>(),
        KMER_ENTRY_BYTES,
        "the bound's derivation assumes size_of::<KmerEntry>() == {}",
        KMER_ENTRY_BYTES
    );

    // --- The fixture: N distinct k-mers, dropped before the baseline -------
    let dir = tempfile::tempdir()?;
    let input = dir.path().join("measurement_input.rkdb");
    {
        let kmers: Vec<(u128, u32)> = (0..MEASUREMENT_ENTRIES)
            .map(|i| (encode_test_kmer(i as u64, K), (i % 1000 + 1) as u32))
            .collect();
        let db = RKDatabase::from_kmer_pairs(kmers, K, true, true)?;
        db.to_file_path(&input)?;
    } // the in-memory structure is dropped HERE, before the baseline

    let n = RKDatabase::estimate_total_kmers(&input)?;
    assert_eq!(
        n as usize, MEASUREMENT_ENTRIES,
        "premise: the fixture really holds N records"
    );
    assert!(
        (CHUNK_ENTRIES as u64) < n,
        "the fixture ({} records) must be larger than one pinned chunk ({} entries) — \
         otherwise the chunk-derived bound is not being tested at all",
        n,
        CHUNK_ENTRIES
    );

    // --- The budget: DERIVED from the estimator, provably streaming --------
    //
    // The 03-04 discipline: derive the budget from
    // `estimate_total_kmers` and ASSERT the derived estimate exceeds it, so
    // a shrunken fixture fails loudly instead of silently measuring the
    // in-memory path.
    let estimated =
        RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, n);
    let budget = estimated - 1;
    assert!(
        estimated > budget,
        "GUARD: the derived estimate ({}) must exceed the budget ({}) for the streaming \
         route to be selected",
        estimated,
        budget
    );

    let work = tempfile::tempdir()?;
    let output = dir.path().join("measurement_output.rkdb");
    let config = MergeConfig {
        max_memory_usage: budget as usize,
        chunk_size: CHUNK_ENTRIES,
        temp_dir: work.path().to_path_buf(),
        ..Default::default()
    };

    // --- The measurement ----------------------------------------------------
    let baseline_kb = current_rss_kb().expect("the RSS source must be readable");
    let input_clone = input.clone();
    let (result, peak_kb) = run_tracking_peak_rss(move || {
        RKDatabase::merge_databases_to_path(&[input_clone], &config, &output)
    });
    let summary = result?;
    let rss_delta_bytes = peak_kb.saturating_sub(baseline_kb) * 1024;

    eprintln!(
        "rss_delta_bytes={} rss_bound_bytes={} chunk_size={} budget_bytes={} n={} baseline_kb={} peak_kb={}",
        rss_delta_bytes, RSS_BOUND_BYTES, CHUNK_ENTRIES, budget, n, baseline_kb, peak_kb
    );

    assert_eq!(
        summary.total_kmers, n,
        "the streaming merge must write every input record exactly once"
    );
    assert!(summary.sorted);
    assert_eq!(summary.kmer_size, K as usize);

    assert!(
        rss_delta_bytes < RSS_BOUND_BYTES,
        "streaming merge added {} bytes of resident memory against the {} byte bound \
         (4 x chunk_size {} x {} B/entry); the pre-fix accumulation measured ~64,000,000 B \
         at this N — if this assert fires with a figure near that, the accumulating body \
         is back (CR-02 regression)",
        rss_delta_bytes,
        RSS_BOUND_BYTES,
        CHUNK_ENTRIES,
        KMER_ENTRY_BYTES
    );

    Ok(())
}

/// DENSE-02: the streaming route's emitted header is field-for-field the
/// header `from_kmer_pairs(sorted_kmers, kmer_size, canonical, true)`
/// produces — INCLUDING `file_size == 0`.
///
/// This is the guard that replaces the inert `grep -c 'file_size: 0'`
/// source-shape criterion: the literal already occurred 4 times in
/// `format.rs` before this plan, so a count cannot observe the streaming
/// writer at all. Only reading the streaming output's own header back can —
/// and it goes red if the placeholder-then-seek-back writer populates a
/// field `from_kmer_pairs` leaves alone, which would be a silent on-disk
/// format change (threat T-03-37).
#[test]
fn streaming_to_path_header_equals_the_from_kmer_pairs_header_field_for_field() -> Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    let pairs: Vec<(u128, u32)> = (0..300u64)
        .map(|i| (encode_test_kmer(i, K), (i % 13 + 1) as u32))
        .collect();
    let input_path = dir.path().join("header_input.rkdb");
    RKDatabase::from_kmer_pairs(pairs.clone(), K, true, true)?.to_file_path(&input_path)?;

    // The reference: what the pre-plan writer produced for the same pairs.
    let reference = RKDatabase::from_kmer_pairs(pairs.clone(), K, true, true)?;
    let ref_header = reference.header().clone();

    let config = MergeConfig {
        merge_mode: "streaming".to_string(),
        max_memory_usage: HUGE_BUDGET_BYTES,
        chunk_size: 64,
        temp_dir: work.path().to_path_buf(),
        ..Default::default()
    };

    // Prove the route before asserting anything about its output: with a
    // nonexistent temp_dir only the streaming path can fail (03-01 probe).
    let missing = missing_temp_dir(dir.path());
    let probe_err = RKDatabase::merge_databases_to_path(
        std::slice::from_ref(&input_path),
        &MergeConfig {
            temp_dir: missing.clone(),
            ..config.clone()
        },
        &dir.path().join("header_probe_out.rkdb"),
    )
    .expect_err("the probe must take the streaming route (explicit merge_mode)");
    assert_streaming_route_proved(&probe_err, &missing);

    let out = dir.path().join("header_streaming_out.rkdb");
    let summary = RKDatabase::merge_databases_to_path(&[input_path], &config, &out)?;
    let header = RKDatabase::read_header_of(&out)?;

    // Field for field — every field of DatabaseHeader, including the two the
    // 42-byte on-disk format does not serialize (unique_kmers, file_size),
    // because the comparison runs through the readers both forms share.
    assert_eq!(header.magic, ref_header.magic, "magic");
    assert_eq!(header.version, ref_header.version, "version");
    assert_eq!(header.kmer_size, ref_header.kmer_size, "kmer_size");
    assert_eq!(header.total_kmers, ref_header.total_kmers, "total_kmers");
    assert_eq!(header.unique_kmers, ref_header.unique_kmers, "unique_kmers");
    assert_eq!(header.sorted, ref_header.sorted, "sorted");
    assert_eq!(header.canonical, ref_header.canonical, "canonical");
    assert_eq!(header.data_offset, ref_header.data_offset, "data_offset");
    assert_eq!(header.index_offset, ref_header.index_offset, "index_offset");
    assert_eq!(header.file_size, ref_header.file_size, "file_size");

    // file_size == 0, stated on its own because it is the field a "helpful"
    // streaming writer would be most tempted to populate. Every writer in
    // this crate has always left it zero on this route; filling it in would
    // be a silent on-disk format change the golden fixtures would catch only
    // by accident.
    assert_eq!(
        header.file_size, 0,
        "the streaming writer must leave file_size == 0, as from_kmer_pairs always has"
    );

    // The summary and the written header must agree — they are the two
    // claims the entry point makes about its own output.
    assert_eq!(summary.total_kmers, header.total_kmers);
    assert_eq!(summary.kmer_size, header.kmer_size as usize);
    assert_eq!(summary.canonical, header.canonical);
    assert_eq!(summary.sorted, header.sorted);

    // The strongest form of the same guard: the streaming output's full
    // bytes (42-byte header AND the entries) equal a from_kmer_pairs-written
    // file of the same pairs.
    let ref_file = dir.path().join("header_reference.rkdb");
    reference.to_file_path(&ref_file)?;
    let streaming_bytes = std::fs::read(&out)?;
    let reference_bytes = std::fs::read(&ref_file)?;
    assert_eq!(
        &streaming_bytes[..42],
        &reference_bytes[..42],
        "the streaming writer's on-disk 42-byte header must be byte-identical to \
         from_kmer_pairs' (DENSE-02)"
    );
    assert_eq!(
        streaming_bytes, reference_bytes,
        "the streaming output must be byte-identical to the from_kmer_pairs output for \
         the same pairs — header and entries"
    );

    Ok(())
}

/// The three routes a `MergeConfig` can select, for the byte-identity test.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Route {
    InMemory,
    Streaming,
    PrefixCache,
}

/// `merge_databases_to_path` and `merge_databases` produce BYTE-IDENTICAL
/// `.rkdb` files for the same inputs and the same route — all three routes.
///
/// **Actual scope, stated plainly:** after Task 1's Part D,
/// `merge_databases`' streaming and prefix-cache branches both DELEGATE to
/// `merge_databases_to_path` and then round-trip the result through
/// `from_file_path`/`to_file_path`, so for those two routes this test
/// verifies that the compatibility shim's READ-WRITE ROUND TRIP is lossless
/// — it cannot compare against the pre-plan header, because no code path
/// produces it any more. The pre-plan header is guarded by
/// `streaming_to_path_header_equals_the_from_kmer_pairs_header_field_for_field`
/// against `from_kmer_pairs` directly. The IN-MEMORY arm is the one where
/// the two entry points genuinely run different code, so it is the one that
/// would catch a shim that stopped delegating.
#[test]
fn to_path_and_in_ram_entry_points_agree_byte_for_byte() -> Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;

    for route in [Route::InMemory, Route::Streaming, Route::PrefixCache] {
        let (a, b) = write_fixture_pair(dir.path(), &format!("parity_{:?}", route), 300)?;

        let config = match route {
            Route::InMemory => {
                // Budget 4x the in-memory estimate: above whatever the
                // current admission constant charges, without pinning the
                // constant itself (the 03-07 discipline — a literal here
                // would be invalidated by the next model change).
                let mut n = 0u64;
                for p in [&a, &b] {
                    n = n.saturating_add(RKDatabase::estimate_total_kmers(p)?);
                }
                let budget = RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, n)
                    .saturating_mul(4);
                MergeConfig {
                    merge_mode: "memory".to_string(),
                    max_memory_usage: budget as usize,
                    temp_dir: work.path().to_path_buf(),
                    ..Default::default()
                }
            }
            Route::Streaming => MergeConfig {
                merge_mode: "streaming".to_string(),
                max_memory_usage: HUGE_BUDGET_BYTES,
                chunk_size: 64,
                temp_dir: work.path().to_path_buf(),
                ..Default::default()
            },
            Route::PrefixCache => MergeConfig {
                merge_mode: "auto".to_string(),
                max_memory_usage: HUGE_BUDGET_BYTES,
                use_prefix_cache: true,
                temp_dir: work.path().to_path_buf(),
                ..Default::default()
            },
        };

        // PROVE the route before asserting anything (03-04 discipline): the
        // temp_dir probe must flip the outcome the way this route predicts.
        let inputs = vec![a.clone(), b.clone()];
        let missing = missing_temp_dir(dir.path());
        let probe = MergeConfig {
            temp_dir: missing.clone(),
            ..config.clone()
        };
        match route {
            Route::InMemory => {
                let ok = RKDatabase::merge_databases_to_path(
                    &inputs,
                    &probe,
                    &dir.path().join("probe_inmemory.rkdb"),
                );
                assert!(
                    ok.is_ok(),
                    "{:?}: the in-memory route never touches temp_dir, so the probe must \
                     succeed; got: {:?}",
                    route,
                    ok.err()
                );
            }
            Route::Streaming => {
                let err = RKDatabase::merge_databases_to_path(
                    &inputs,
                    &probe,
                    &dir.path().join("probe_streaming.rkdb"),
                )
                .expect_err("{route}: the streaming route must fail on a nonexistent temp_dir");
                assert_streaming_route_proved(&err, &missing);
            }
            Route::PrefixCache => {
                let err = RKDatabase::merge_databases_to_path(
                    &inputs,
                    &probe,
                    &dir.path().join("probe_prefix.rkdb"),
                )
                .expect_err("{route}: the prefix-cache route must fail on a nonexistent temp_dir");
                assert_prefix_cache_route_proved(&err, &missing);
            }
        }

        // Arm 1: the bounded, path-shaped entry point.
        let to_path_file = dir.path().join(format!("to_path_{:?}.rkdb", route));
        RKDatabase::merge_databases_to_path(&inputs, &config, &to_path_file)?;

        // Arm 2: the materializing compatibility shim, then written out.
        let merged = RKDatabase::merge_databases(&inputs, &config)?;
        let in_ram_file = dir.path().join(format!("in_ram_{:?}.rkdb", route));
        merged.to_file_path(&in_ram_file)?;

        // Full-file byte identity, 42-byte header included.
        let to_path_bytes = std::fs::read(&to_path_file)?;
        let in_ram_bytes = std::fs::read(&in_ram_file)?;
        assert_eq!(
            to_path_bytes, in_ram_bytes,
            "{:?}: merge_databases_to_path and merge_databases must produce byte-identical \
             .rkdb output for the same inputs and route ({} vs {} bytes)",
            route,
            to_path_bytes.len(),
            in_ram_bytes.len()
        );
    }

    Ok(())
}

/// The 03-01/03-07/03-09 route discriminators must survive the to-path entry
/// point: `merge_databases_to_path` with a `temp_dir` that does not exist
/// and a budget that selects streaming returns `Err` naming the missing
/// directory.
///
/// If this test fails, `tests/merge_routing_tests.rs` has been silently made
/// vacuous — that is the alarm it exists to raise. The budget is DERIVED
/// from the estimator (never hard-coded) and asserted to sit below the
/// estimate, per the 03-04 lesson.
#[test]
fn streaming_route_probe_survives_the_to_path_entry_point() -> Result<()> {
    let dir = tempfile::tempdir()?;
    let work = tempfile::tempdir()?;
    let (a, b) = write_fixture_pair(dir.path(), "probe", 200)?;

    let inputs = vec![a, b];
    let mut n = 0u64;
    for p in &inputs {
        n = n.saturating_add(RKDatabase::estimate_total_kmers(p)?);
    }
    let estimated = RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, n);
    let budget = estimated - 1;
    assert!(
        estimated > budget,
        "GUARD: the derived estimate ({}) must exceed the budget ({})",
        estimated,
        budget
    );

    let missing = missing_temp_dir(dir.path());
    let config = MergeConfig {
        max_memory_usage: budget as usize,
        temp_dir: missing.clone(),
        chunk_size: 64,
        ..Default::default()
    };

    let err = RKDatabase::merge_databases_to_path(
        &inputs,
        &config,
        &dir.path().join("probe_to_path_out.rkdb"),
    )
    .expect_err(
        "an over-budget auto merge through merge_databases_to_path must hard-route to \
         streaming, which cannot write chunk files into a nonexistent temp_dir",
    );
    assert_streaming_route_proved(&err, &missing);

    // Control: the same inputs and budget with a REAL temp_dir must succeed
    // through the to-path form — the probe's Err is the route, not the data.
    let ok_config = MergeConfig {
        temp_dir: work.path().to_path_buf(),
        ..config
    };
    let summary =
        RKDatabase::merge_databases_to_path(&inputs, &ok_config, &dir.path().join("probe_ok.rkdb"))?;
    assert_eq!(
        summary.total_kmers, n,
        "the streaming merge must produce the exact union of both disjoint inputs"
    );

    Ok(())
}

/// MERGE-03 / W6: an IN-MEMORY merge through `merge_databases_to_path` still
/// sweeps a stale orphan out of `temp_dir`.
///
/// WHY this test exists: `merge_prologue` is what keeps the in-memory route
/// inside MERGE-03's orphan reclamation. Without it, a refactor that moved
/// the sweep into `merge_databases_to_path`'s non-in-memory arms (or back
/// into `merge_databases` alone) would silently drop it for one of the three
/// routes while the source-shape grep on the sweep's call-site count still
/// read `1` — a shape grep cannot tell "one site reached by every route"
/// apart from "one site some route skips". Only this assertion can.
#[test]
fn in_memory_route_still_sweeps_stale_orphans() -> Result<()> {
    let work = tempfile::tempdir()?;
    let (a, b) = write_fixture_pair(work.path(), "sweep", 200)?;

    // Plant a backdated orphan (with a file inside, so it is not trivially
    // empty) in the temp_dir this merge will sweep.
    let orphan = work.path().join(format!("{}orphan", MERGE_TEMP_PREFIX));
    std::fs::create_dir_all(&orphan)?;
    std::fs::write(orphan.join("ext_sort_AAAA_file_000.tmp"), b"orphan")?;
    backdate(&orphan, DEFAULT_MERGE_TEMP_TTL + Duration::from_secs(60));

    let config = MergeConfig {
        merge_mode: "memory".to_string(),
        max_memory_usage: HUGE_BUDGET_BYTES,
        use_prefix_cache: false,
        temp_dir: work.path().to_path_buf(),
        ..Default::default()
    };

    let out = work.path().join("sweep_merged.rkdb");
    RKDatabase::merge_databases_to_path(&[a, b], &config, &out)?;

    assert!(
        !orphan.exists(),
        "an in-memory merge through merge_databases_to_path must still sweep stale \
         merge temp dirs ({} left behind) — the sweep lives in merge_prologue, not in \
         any single route",
        orphan.display()
    );
    assert!(out.exists(), "the merge itself must have succeeded");

    Ok(())
}

/// Plan 03-09's reclamation assertion, extended to the rename-based handoff:
/// after a prefix-cache merge through `merge_databases_to_path`, neither
/// `<temp_dir>/external_sort_merge_output.tmp` nor any
/// `rustkmer-merge-*/external_sort_merge_output.tmp` survives.
///
/// After the rename there is nothing left to reclaim — the merged bytes ARE
/// the output file — and this test proves it: the intermediate never leaks
/// into the shared temp dir, and the RAII subdir that held it goes away.
#[test]
fn prefix_cache_to_path_leaves_no_intermediate_behind() -> Result<()> {
    let work = tempfile::tempdir()?;
    let (a, b) = write_fixture_pair(work.path(), "pc_cleanup", 200)?;

    let config = MergeConfig {
        use_prefix_cache: true,
        merge_mode: "auto".to_string(),
        max_memory_usage: HUGE_BUDGET_BYTES,
        temp_dir: work.path().to_path_buf(),
        ..Default::default()
    };

    let out = work.path().join("pc_to_path_merged.rkdb");
    let summary = RKDatabase::merge_databases_to_path(&[a.clone(), b.clone()], &config, &out)?;

    assert!(out.exists(), "the renamed output must exist");
    assert_eq!(
        summary.total_kmers, 400,
        "premise: the disjoint fixture pair merges to 400 records"
    );

    // Half 1: the OLD fixed location, directly in the shared temp dir.
    let old_location = work.path().join("external_sort_merge_output.tmp");
    assert!(
        !old_location.exists(),
        "the intermediate result must not be written to the shared temp dir at {} \
         (fixed basename: collides between concurrent merges, survives the merge)",
        old_location.display()
    );

    // Half 2: nothing named external_sort_merge_output.tmp survives anywhere
    // under a rustkmer-merge-* subdir. (The success case is the subdir being
    // gone entirely — Drop removed it — which this loop then simply does not
    // find; that is logged, never a silent pass.)
    let mut subdirs_seen = 0usize;
    for entry in std::fs::read_dir(work.path())? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().to_string();
        if !name.starts_with(MERGE_TEMP_PREFIX) {
            continue;
        }
        subdirs_seen += 1;
        if !entry.path().is_dir() {
            continue;
        }
        for inner in std::fs::read_dir(entry.path())? {
            let inner = inner?;
            assert_ne!(
                inner.file_name().to_string_lossy().to_string(),
                "external_sort_merge_output.tmp",
                "the intermediate result must not survive inside {}: after the rename \
                 there is nothing left to reclaim",
                entry.path().display()
            );
        }
    }
    if subdirs_seen == 0 {
        eprintln!(
            "prefix-cache to-path cleanup: the whole rustkmer-merge-* subdir is already \
             gone, which is the RAII success case"
        );
    }

    Ok(())
}
