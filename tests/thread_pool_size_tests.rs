//! PROF-02 — live counting-pool observation tests (plan 05-03, Phase 6 PAR-01;
//! updated by Phase 7 ENGINE-01 / plan 07-02).
//!
//! # Why subprocess observation is the only honest evidence
//!
//! rayon's global pool is initialized ONCE per process (`build_global`
//! returns `Err` on a second call — see the constraint comment in
//! `tests/parallel_count_tests.rs`), so no in-test call can observe the pools
//! the CLI actually builds. The v1.0 1-vs-N count differential passed for a
//! year while `--threads` did nothing: count commutativity is NOT pool-size
//! evidence, and neither is the pure precedence helper tested by
//! `test_thread_resolution`. These tests therefore drive the real CLI binary
//! (`CARGO_BIN_EXE_rustkmer`) through the hardened cross-platform observer
//! `.planning/research/profiling/verify_threads.py`, one independent child
//! process per requested N, and read its structured `--json` records.
//!
//! # The standing gate
//!
//! [`pool_size_matches_requested_threads`] runs in the default suite and is
//! the standing gate: one fresh CLI child per N in {1, 4, 16} must observe
//! EXACTLY the engine's thread total — `2` at `--threads 1` (main + one rayon
//! worker; the sequential engine spawns no counting thread) and `2N + 1` at
//! `--threads 4` (9) / `16` (33) (main/producer + N persistent engine workers
//! + N rayon workers). The exactness is the point: no `>=`, no override, no
//! self-reported pool size.
//!
//! [`pool_size_characterization_records_requested_pool`] pins the same
//! contract for a single `--threads 1` child in the default suite.
//!
//! Every pool-size assertion message embeds the literal pattern
//! `requested=<N> observed=<M>` so a failure is mechanically distinguishable
//! from a build/infra failure by grepping the test log.
//!
//! Windows: the test-root CI matrix includes windows-latest, where neither
//! macOS `sample` nor Linux `/proc/<pid>/task` exists; both tests return
//! early with an explicit platform-skip message (the helper itself exits 2
//! on unsupported platforms — never a false PASS).

use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

/// The engine's exact OS thread total for `requested` counting threads.
///
/// `--threads 1` takes the sequential path (no counting thread), so the total
/// is just main + the single rayon worker. `--threads N > 1` adds N persistent
/// engine workers on top of main + N rayon workers.
fn expected_total(requested: u64) -> u64 {
    if requested == 1 {
        2
    } else {
        2 * requested + 1
    }
}

/// The hardened cross-platform thread observer (05-03), located relative to
/// the crate root so the test works from any checkout path.
fn helper_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(".planning/research/profiling/verify_threads.py")
}

/// Deterministic FASTQ fixture: inline LCG (seed 0x5EED), 100_000 reads of
/// 150 ACGT bases, four-line records, no Ns. The debug test binary counts
/// slowly enough that the child stays alive for sampling; the helper
/// terminates it right after the observation (try/finally reaps it).
fn write_fastq_fixture(dir: &Path) -> PathBuf {
    const BASES: [u8; 4] = *b"ACGT";
    const READS: usize = 100_000;
    const LEN: usize = 150;
    let mut state: u64 = 0x5EED;
    let mut next_base = || {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        BASES[((state >> 33) & 3) as usize] as char
    };
    let qual = "I".repeat(LEN);
    let mut buf = String::with_capacity(READS * (2 * LEN + 32));
    for i in 0..READS {
        writeln!(buf, "@read_{i}").expect("writing to a String is infallible");
        for _ in 0..LEN {
            buf.push(next_base());
        }
        buf.push_str("\n+\n");
        buf.push_str(&qual);
        buf.push('\n');
    }
    let path = dir.join("pool_fixture.fq");
    std::fs::write(&path, buf).expect("fixture FASTQ must be writable");
    path
}

/// Drive the helper against the Cargo-built CLI binary. `--build-profile
/// debug` keeps the provenance honest: `CARGO_BIN_EXE_rustkmer` is the debug
/// profile under `cargo test`, not the release binary the dev-host evidence
/// capture uses.
fn run_helper(fixture: &Path, json_path: &Path, threads: &[u32]) -> Output {
    let mut cmd = Command::new("python3");
    cmd.arg(helper_path())
        .arg("--binary")
        .arg(env!("CARGO_BIN_EXE_rustkmer"))
        .arg("--input")
        .arg(fixture)
        .arg("--json")
        .arg(json_path)
        .arg("--build-profile")
        .arg("debug")
        .arg("--threads");
    for n in threads {
        cmd.arg(n.to_string());
    }
    cmd.output()
        .expect("python3 must launch the verify_threads.py helper")
}

/// Read the helper's JSON records REGARDLESS of its exit code: a measured
/// mismatch exits 1 but still writes complete records (only exit-2 invalid
/// paths write nothing). A missing/unparseable doc is an infrastructure
/// failure, reported with the helper's own stderr.
fn read_records(json_path: &Path, out: &Output) -> Vec<serde_json::Value> {
    let text = std::fs::read_to_string(json_path).unwrap_or_else(|e| {
        panic!(
            "PROF-02: helper must write JSON records to {} (helper exit {:?}): {e}\nhelper stderr:\n{}",
            json_path.display(),
            out.status.code(),
            String::from_utf8_lossy(&out.stderr)
        )
    });
    let doc: serde_json::Value = serde_json::from_str(&text)
        .unwrap_or_else(|e| panic!("PROF-02: helper JSON must parse: {e}\n{text}"));
    doc["records"]
        .as_array()
        .unwrap_or_else(|| panic!("PROF-02: helper JSON must carry a records array: {text}"))
        .clone()
}

/// Characterization of the fixed behavior (default suite): a fresh
/// `--threads 1` child must observe EXACTLY 2 OS threads — the main thread plus
/// the single rayon worker. The sequential engine path spawns no counting
/// thread, so the formula applies on every host (including single-core hosts,
/// where a one-worker rayon pool is still one worker).
#[test]
fn pool_size_characterization_records_requested_pool() {
    if cfg!(windows) {
        eprintln!(
            "PROF-02 platform-skip: pool-size observation needs macOS `sample` or Linux \
             /proc/<pid>/task; on Windows the helper exits 2 (unsupported platform)"
        );
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir for fixture/JSON must be creatable");
    let fixture = write_fastq_fixture(dir.path());
    let json_path = dir.path().join("threads_t1.json");
    let out = run_helper(&fixture, &json_path, &[1]);
    let records = read_records(&json_path, &out);
    assert_eq!(
        records.len(),
        1,
        "PROF-02: exactly one observation record for --threads 1"
    );
    let requested = records[0]["requested"]
        .as_u64()
        .expect("record.requested must be an integer");
    let observed = records[0]["observed"]
        .as_u64()
        .expect("record.observed must be an integer");
    assert_eq!(
        requested, 1,
        "PROF-02: the record must pin the requested thread count"
    );
    let code = out.status.code();
    assert!(
        code == Some(0) || code == Some(1),
        "PROF-02: helper must complete the observation (exit 0 match / 1 mismatch), got \
         {code:?}\nhelper stderr:\n{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(
        observed,
        expected_total(requested),
        "PROF-02 pool-size mismatch: requested={requested} observed={observed} — \
         --threads 1 must observe main + one rayon worker (the sequential engine spawns no \
         counting thread)"
    );
    eprintln!(
        "PROF-02 characterization: requested={requested} observed={observed} — the \
         sequential engine and the one-worker rayon pool are both sized"
    );
}

/// Standing gate: the observed OS thread count must equal the engine formula
/// exactly — `2` for N = 1 and `2N + 1` for N = 4 (9) and 16 (33), each
/// observed in an independent subprocess because rayon's global pool is
/// once-per-process. Per-N assertions run BEFORE the exit-code assertion so a
/// failure log always carries the machine-greppable `requested=<N>
/// observed=<M>` pattern.
#[test]
fn pool_size_matches_requested_threads() {
    if cfg!(windows) {
        eprintln!(
            "PROF-02 platform-skip: pool-size observation needs macOS `sample` or Linux \
             /proc/<pid>/task; on Windows the helper exits 2 (unsupported platform)"
        );
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir for fixture/JSON must be creatable");
    let fixture = write_fastq_fixture(dir.path());
    let json_path = dir.path().join("threads_gate.json");
    let out = run_helper(&fixture, &json_path, &[1, 4, 16]);
    let records = read_records(&json_path, &out);
    assert_eq!(
        records.len(),
        3,
        "PROF-02: one observation record per requested N (1, 4, 16)"
    );
    for rec in &records {
        let requested = rec["requested"]
            .as_u64()
            .expect("record.requested must be an integer");
        let observed = rec["observed"]
            .as_u64()
            .expect("record.observed must be an integer");
        assert_eq!(
            observed,
            expected_total(requested),
            "PROF-02 pool-size mismatch: requested={requested} observed={observed} — \
             the engine formula is 2 at N=1 and 2N+1 for N>1"
        );
    }
    assert_eq!(
        out.status.code(),
        Some(0),
        "PROF-02: helper must exit 0 when every pool matches (1 = measured mismatch, \
         2 = invalid)\nhelper stderr:\n{}",
        String::from_utf8_lossy(&out.stderr)
    );
}
