#!/usr/bin/env python3
"""Phase-13 producer-attribution driver (PEXT-01/PEXT-02).

Decisions served (13-CONTEXT.md):

  * D-01 — this script IS the measurement vehicle: a harness-built,
    stdlib-only driver in the `merge_characterize.py` lineage. Arms A-D plus
    the pure-read control are driven from here; every run carries provenance
    (binary sha256, input sha256s, command line, honest cache_state) and the
    evidence lives in a JSON document of its own kind.
  * D-02 — the gate memo is a DETERMINISTIC RENDER of that evidence document
    (`render_memo_text` + byte-identical re-render proof + atomic publish).
  * D-03/D-10 — the fingerprint gate branches on the sha256 of the actual
    release binary bytes: identical to v2.0's recorded fingerprint -> the
    v2.0 walls are citable as the base ('cite'); ANY difference -> a fresh
    arm-A base is mandatory ('re-measure'). The live outcome is 're-measure':
    the current binary is 4539b893...d6d023b, v2.0 recorded 8f38d20c...c87c3d23.
  * D-04 — plain inputs are decompressed once into a directory OUTSIDE the
    repo, provenance-recorded before any run, deleted only after the memo.

Kind boundary: the evidence document's kind is `phase13-producer-attribution`
— its own kind, NEVER a fork of the bench results schema v1 (MBENCH-05).

Arm matrix (RESEARCH "The Arm Matrix"):

  A        stock CLI count, gzip pinned pair, `-o` scratch      (fresh base)
  B        same shape, plain pair                               (no inflate)
  control  `cat` both pinned-pair parts of one input type       (read volume)
  C        engine probe (k=21 committed / k=31 materialized)    (sub-timers)
  D        null consumer (materialized) on plain parts          (parse+extract)

Every measured run goes through `/usr/bin/time` (`measured_run` /
`parse_time_output`) — harness-internal clocks are banned. Probe stdout is
parsed as one JSON object per invocation, per-instrument (13-RESEARCH
Pitfall 8): the committed k=21 probe hardcodes k and emits NO k field, the
materialized probes take k from argv and MUST assert it.

Scratch discipline: probe crates are materialized under the pinned
PROBE_SCRATCH_ROOT (/tmp/phase13-probe-scratch) with the `refuse_repo_root`
guard; no scratch tree ever lands in the repo. Each scratch crate's
Cargo.lock is seeded from a committed lock fixture (scripts/bench/fixtures/
phase13_*.Cargo.lock) and sha256-verified before its `cargo build --release
--locked`; a missing or mismatched fixture is a loud exit-2 abort
(contention_bench.verify_scratch_lockfile semantics).

Verbs:
  --rehearsal                 prove the whole chain at fixture scale
  --stage prep|measure|memo   the full-scale stages (Plan 13-02 / 13-03)
  --generate-lock-fixtures    one-time maintenance: regenerate the committed
                              probe lock fixtures with `cargo generate-lockfile
                              --offline` (documented in the plan; never part of
                              a measurement run)

Exit codes: 0 = a recorded result (GO or NO-GO are both valid), 2 =
infrastructure/invalid input (no artifact published).

Python 3.11+ stdlib only — no third-party imports, no pip installs (the
bench-harness stdlib-only contract, bench.py:25-26).
"""

import argparse
import gzip
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution needs the checkout root for the scripts package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    LARGEST_SINGLE_ARM_TRANSIENT_BYTES,
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    fingerprint,
    parse_time_output,
    reduce_arm,
    rustkmer_count_cmd,
    stats as bench_stats,
    validate_provenance,
)
from scripts.bench.merge_characterize import (
    _guard_zero,
    _run_fail_loud,
    ensure_free_space,
    free_bytes,
    measured_run,
)
from scripts.bench.output_stage import rotation_schedule
from scripts.bench.phase10 import publish_atomic
from scripts.bench.prepare_inputs import (
    DEFAULT_RUSTKMER,
    refuse_repo_root,
)

HERE = Path(__file__).resolve().parent            # scripts/bench/
REPO_ROOT = HERE.parent.parent                    # repo root

EXIT_OK = 0          # a recorded result (GO and NO-GO both exit 0)
EXIT_INVALID = 2     # infrastructure / invalid input (no artifact published)

SCHEMA_VERSION = 1
KIND = "phase13-producer-attribution"
KIND_RENDER_PROOF = "phase13-render-proof"

PHASE = 13

DEFAULT_RESULTS = (REPO_ROOT / ".planning" / "phases"
                   / "13-producer-attribution-research"
                   / "13-ATTRIBUTION.json")
DEFAULT_MEMO = (REPO_ROOT / ".planning" / "phases"
                / "13-producer-attribution-research" / "13-GATE-MEMO.md")
DEFAULT_PROOF = (REPO_ROOT / ".planning" / "phases"
                 / "13-producer-attribution-research"
                 / "13-RENDER-PROOF.json")

# --- D-03/D-10 fingerprint gate ---------------------------------------------
# v2.0's recorded release-binary fingerprint (10-results-full-k21.json
# provenance block). The gate branches on EXACT sha256 equality; the live
# D-10 outcome is 're-measure' (current 4539b893...).
V2_0_RUSTKMER_SHA256 = (
    "8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23")

# --- D-05 pre-registered D3 bar ---------------------------------------------
# Bar on the CONSERVATIVE (efficiency-derated) model, >= semantics, applied
# at BOTH k as a conjunction. The idealized E=M bound is reported alongside
# but is NEVER the bar input.
D3_BAR_FULL_WALL_IMPROVEMENT_PCT = 10.0
EXTRACTOR_COUNT = 16
EXTRACTOR_EFFICIENCY_DERATED = 0.5
# Pre-registered worker-side speedup ceiling (never fitted after seeing data).
WORKER_SCALING_CEILING = EXTRACTOR_COUNT

# --- A3/A4 anomaly criteria (pinned, never judged after the fact) -----------
PROBE_VS_CLI_RATIO_BAND = (0.25, 1.0)
WORKER_BUSY_RATIO_MAX = 1.0

GATE_KS = (21, 31)
GATE_REPS = 3
GATE_ARMS = ("A", "B", "C", "D", "control")
DEFAULT_COOLDOWN_S = 20

# --- D-06 disclosure constants (rendered at memo time, never read back) -----
V2_0_CLI_WALL_K21_S = 144.69
V2_0_CLI_WALL_K31_S = 147.08
V2_0_PYTHON_WALL_K21_S = 165.05
V2_0_PYTHON_WALL_K31_S = 178.22
V2_0_PYTHON_MODULE_SHA256 = (
    "6d5264316e5c3e0587430cd87b49694e408871ddd780619950550cd7f5558ae3")

# --- dataset / lifecycle paths ----------------------------------------------
DATASET_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")
PLAIN_INPUTS_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095-plain")
PINNED_PAIR = ("part_001", "part_006")
EXPECTED_PARTS = tuple(f"part_{index:03d}" for index in range(1, 7))

# Plain part filename rule (D-07): part_001.fq.gz -> PLAIN_INPUTS_DIR/part_001.fq
PLAIN_SUFFIX = ".fq"

# Probe-crate scratch root — pinned so Plan 13-03 can delete exactly this tree.
PROBE_SCRATCH_ROOT = Path("/tmp/phase13-probe-scratch")
PROBE_FIXTURES_DIR = HERE / "fixtures"
COMMITTED_K21_PROBE = REPO_ROOT / "target" / "release" / "examples" / "engine_probe"
STOCK_RELEASE_BINARY = REPO_ROOT / "target" / "release" / "rustkmer"

# D-04/A1 disk arithmetic: plain FASTQ runs ~3.1-3.5x the gzip bytes; the
# research A1 band's upper edge is used, plus the recorded largest single-arm
# transient (bench.py's D-10 constant).
PLAIN_SIZE_FACTOR = 3.5
REQUIRED_TRANSIENT_BYTES = LARGEST_SINGLE_ARM_TRANSIENT_BYTES

# Record fields whose presence the memo derivation requires (threat T-13-04:
# a record without provenance cannot be cited). `part` is identity, not
# provenance, and is legitimately None for the pair-level arms (A/B/control);
# arms C/D must carry it and that is checked per record below.
REQUIRED_RECORD_KEYS = (
    "arm", "k", "rep", "scale", "input_type",
    "wall_s", "peak_rss_bytes", "cache_state",
    "command_line", "binary_sha256", "input_sha256s",
)

# Instrument registry (per-instrument k contract, 13-RESEARCH Pitfall 8).
PROBE_INSTRUMENTS = {
    "engine_probe_k21": {
        "k": 21,
        "k_source": "instrument-build",
        "k_argv": False,
        "emits_producer": True,
    },
    "engine_probe_k31": {
        "k": 31,
        "k_source": "output-json",
        "k_argv": True,
        "emits_producer": True,
    },
    "null_consumer": {
        "k": None,
        "k_source": "output-json",
        "k_argv": True,
        "emits_producer": False,
    },
}


def _now_iso():
    """UTC timestamp for evidence `created` fields."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path):
    """sha256 hex of one file, streamed in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unlink_quiet(path):
    """Delete one file if it exists; a missing file is not an error."""
    try:
        Path(path).unlink()
    except OSError:
        return False
    return True


def read_thermal():
    """Best-effort `pmset -g therm` sample; honest fallback, never raises."""
    try:
        proc = subprocess.run(["pmset", "-g", "therm"],
                              capture_output=True, text=True)
    except OSError:
        return "unavailable"
    if proc.returncode != 0:
        return "unavailable"
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("CPU_Scheduler_Limit") or \
                stripped.startswith("CPU_Speed_Limit"):
            return stripped
    return "unavailable"


# --- measured runs ----------------------------------------------------------
# `measured_run` (imported from merge_characterize) is the A/B/control clock.
# Probe invocations need their stdout, and the pure-read control streams its
# child's stdout to DEVNULL — both keep the same /usr/bin/time wrapper and the
# same units-pinned parser, never a harness-internal clock.


def _measured_run_capture(argv):
    """Like measured_run but keeps stdout (probe JSON) as well.

    Returns (rep_dict, stdout_text). Raises RuntimeError on a non-zero child
    exit — a failed run is never a successful measurement (T-13-01).
    """
    plat = sys.platform
    time_flag = "-l" if plat == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag,
                           *[str(arg) for arg in argv]],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{(proc.stderr or '')[-500:]}")
    return parse_time_output(proc.stderr, plat), proc.stdout


def _measured_run_devnull(argv):
    """Like measured_run but the child's stdout goes to DEVNULL.

    Used by the pure-read control: the same byte volume the pair arms read is
    streamed through `cat` and discarded, with no in-memory capture.
    """
    plat = sys.platform
    time_flag = "-l" if plat == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag,
                           *[str(arg) for arg in argv]],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{(proc.stderr or '')[-500:]}")
    return parse_time_output(proc.stderr, plat)


def _cargo_build(argv, cwd=REPO_ROOT, env=None):
    """Run one list-form cargo build; fail loud with trailing stderr."""
    argv = [str(arg) for arg in argv]
    proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                          env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"cargo build failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{(proc.stderr or '')[-800:]}")
    return proc.stdout


# --- probe materialization (D-01 research-local instruments) ----------------
# Templates below materialize OUTSIDE the repo. The k=31 manifest is the one
# pinned deviation from .planning/research/profiling/microbench_Cargo.toml:
# it enables rustkmer's `profiling` feature, because EngineDiagnostics and
# CountResult::diagnostics are cfg-gated (src/count/engine.rs:195-204,
# 356-359, 975-998) and a bare path dep cannot compile the probe.

PROBE_CRATES = {
    "engine_probe_k31": {
        "package": "phase13-probe-k31",
        "binary": "phase13-probe-k31",
        "lock_fixture": "phase13_probe_k31.Cargo.lock",
        "manifest": """[package]
name = "phase13-probe-k31"
version = "0.1.0"
edition = "2021"
rust-version = "1.82"

[dependencies]
# Phase-13 materialized k=31 producer/worker timing probe. The `profiling`
# feature is REQUIRED: EngineDiagnostics/CountResult::diagnostics exist only
# under #[cfg(feature = "profiling")] in the rustkmer crate.
rustkmer = { path = "@REPO_ROOT@", features = ["profiling"] }
serde_json = "=1.0.145"

[profile.release]
lto = true
codegen-units = 1
opt-level = 3

[workspace]
""",
        "source": r'''//! Phase-13 materialized k-parameterized producer/worker timing probe.
//!
//! Structure copied from examples/engine_probe.rs (07-04) with exactly one
//! pinned change: k comes from argv and is asserted into the JSON document,
//! so the k=31 arm can never silently record k=21 diagnostics (Pitfall 8).
//!
//! Run: <binary> <input-path> <fasta|fastq> <threads> <k>

use std::path::PathBuf;
use std::process::ExitCode;

use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() != 5 {
        eprintln!("usage: phase13-probe-k31 <input-path> <fasta|fastq> <threads> <k>");
        return ExitCode::from(2);
    }
    let input = PathBuf::from(&arguments[1]);
    let kind = match arguments[2].as_str() {
        "fasta" => SequenceKind::Fasta,
        "fastq" => SequenceKind::Fastq,
        other => {
            eprintln!("phase13-probe-k31: unsupported format {other:?} (expected fasta|fastq)");
            return ExitCode::from(2);
        }
    };
    let threads = match arguments[3].parse::<usize>() {
        Ok(threads) if threads >= 1 => threads,
        _ => {
            eprintln!("phase13-probe-k31: threads must be a positive integer");
            return ExitCode::from(2);
        }
    };
    let k = match arguments[4].parse::<usize>() {
        Ok(k) if (1..=64).contains(&k) => k,
        _ => {
            eprintln!("phase13-probe-k31: k must be an integer in 1..=64");
            return ExitCode::from(2);
        }
    };

    let config = EngineConfig::new(k, true, threads, 1_000_000);
    let mut engine = match CountEngine::new(config) {
        Ok(engine) => engine,
        Err(error) => {
            eprintln!("phase13-probe-k31: failed to build the counting engine: {error}");
            return ExitCode::from(2);
        }
    };
    if let Err(error) = engine.count_file(&input, kind) {
        eprintln!("phase13-probe-k31: counting failed: {error}");
        return ExitCode::from(2);
    }
    let result = match engine.finish() {
        Ok(result) => result,
        Err(error) => {
            eprintln!("phase13-probe-k31: finish failed: {error}");
            return ExitCode::from(2);
        }
    };
    let Some(diagnostics) = result.diagnostics() else {
        eprintln!("phase13-probe-k31: diagnostics unavailable from the finished result");
        return ExitCode::from(2);
    };
    let workers: Vec<serde_json::Value> = diagnostics
        .workers
        .iter()
        .map(|worker| {
            serde_json::json!({
                "batches": worker.batches,
                "busy_nanos": worker.busy_nanos,
            })
        })
        .collect();
    let document = serde_json::json!({
        "input": input.display().to_string(),
        "k": k,
        "threads": threads,
        "wall_nanos": diagnostics.wall_nanos,
        "producer_nanos": diagnostics.producer_nanos,
        "workers": workers,
    });
    println!("{document}");
    ExitCode::SUCCESS
}
''',
    },
    "null_consumer": {
        "package": "phase13-null-consumer",
        "binary": "phase13-null-consumer",
        "lock_fixture": "phase13_null_consumer.Cargo.lock",
        "manifest": """[package]
name = "phase13-null-consumer"
version = "0.1.0"
edition = "2021"
rust-version = "1.82"

[dependencies]
# Phase-13 arm-D null consumer: read + parse + extract only. The bare path
# dep is correct here — this instrument consumes no diagnostics.
rustkmer = { path = "@REPO_ROOT@" }
bio = "=2.3.0"
serde_json = "=1.0.145"

[profile.release]
lto = true
codegen-units = 1
opt-level = 3

[workspace]
""",
        "source": r'''//! Phase-13 arm-D null consumer: read + parse + extract, no routing,
//! no counting tables, no worker sends.
//!
//! The timed section is the bio FASTQ record loop feeding the public
//! `for_each_window` extractor with a discard emit closure — the
//! count_file_inner parse shape minus the engine (src/count/engine.rs:835-848,
//! src/kmer/extract.rs:90-98).
//!
//! Run: <binary> <input.fq> <k>

use std::fs::File;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use rustkmer::kmer::extract::for_each_window;

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() != 3 {
        eprintln!("usage: phase13-null-consumer <input.fq> <k>");
        return ExitCode::from(2);
    }
    let input = PathBuf::from(&arguments[1]);
    let k = match arguments[2].parse::<usize>() {
        Ok(k) if (1..=64).contains(&k) => k,
        _ => {
            eprintln!("phase13-null-consumer: k must be an integer in 1..=64");
            return ExitCode::from(2);
        }
    };
    let file = match File::open(&input) {
        Ok(file) => file,
        Err(error) => {
            eprintln!("phase13-null-consumer: cannot open input: {error}");
            return ExitCode::from(2);
        }
    };
    let started = Instant::now();
    let reader = bio::io::fastq::Reader::new(file);
    let mut records: u64 = 0;
    let mut windows: u64 = 0;
    for record_result in reader.records() {
        let record = match record_result {
            Ok(record) => record,
            Err(error) => {
                eprintln!("phase13-null-consumer: record parse failed: {error}");
                return ExitCode::from(2);
            }
        };
        let summary = match for_each_window(record.seq(), k, true, |_value| Ok::<(), ()>(())) {
            Ok(summary) => summary,
            Err(error) => {
                eprintln!("phase13-null-consumer: extract failed: {error:?}");
                return ExitCode::from(2);
            }
        };
        records += 1;
        windows += summary.emitted;
    }
    let wall_nanos = started.elapsed().as_nanos() as u64;
    let document = serde_json::json!({
        "input": input.display().to_string(),
        "k": k,
        "records": records,
        "windows": windows,
        "wall_nanos": wall_nanos,
    });
    println!("{document}");
    ExitCode::SUCCESS
}
''',
    },
}


def probe_manifest(probe, repo_root=REPO_ROOT):
    """The manifest text for one materialized probe crate.

    `@REPO_ROOT@` is substituted from THIS file's location (never a user
    string), exactly like contention_bench.materialize_crate.
    """
    if probe not in PROBE_CRATES:
        raise ValueError(f"unknown probe crate {probe!r}")
    template = PROBE_CRATES[probe]["manifest"]
    if "@REPO_ROOT@" not in template:
        raise ValueError(f"probe manifest template has no @REPO_ROOT@: {probe}")
    return template.replace("@REPO_ROOT@", str(Path(repo_root).resolve()))


def verify_scratch_lockfile(crate_dir, fixture_path):
    """Verify a scratch crate's Cargo.lock against its committed fixture.

    Missing fixture, missing scratch lock, or any byte difference is a loud
    abort (contention_bench.verify_scratch_lockfile semantics): `cargo build
    --locked` cannot create a lock file, so an unprovisioned crate must fail
    BEFORE the build — never build unlocked.
    """
    crate_dir = Path(crate_dir)
    fixture_path = Path(fixture_path)
    if not fixture_path.is_file():
        raise RuntimeError(
            f"committed probe lock fixture missing: {fixture_path} — "
            "refusing to build a scratch probe crate without a provisioned "
            "lock (cargo build --locked cannot create one)")
    target = crate_dir / "Cargo.lock"
    if not target.is_file():
        raise RuntimeError(
            f"scratch lockfile missing: {target} — refusing to build "
            "unlocked (cargo build --locked cannot create one)")
    fixture_sha = _sha256_file(fixture_path)
    scratch_sha = _sha256_file(target)
    if scratch_sha != fixture_sha:
        raise RuntimeError(
            f"scratch lockfile sha256 {scratch_sha} != committed fixture "
            f"{fixture_sha} ({fixture_path}) — the measured dependency graph "
            "would drift; refusing to build")
    return scratch_sha


def seed_and_verify_lockfile(crate_dir, fixture_path):
    """Seed a scratch crate's Cargo.lock from its committed fixture, then
    sha256-verify the seeded copy."""
    crate_dir = Path(crate_dir)
    fixture_path = Path(fixture_path)
    if not fixture_path.is_file():
        raise RuntimeError(
            f"committed probe lock fixture missing: {fixture_path} — "
            "refusing to build a scratch probe crate without a provisioned "
            "lock (cargo build --locked cannot create one)")
    target = crate_dir / "Cargo.lock"
    try:
        target.write_bytes(fixture_path.read_bytes())
    except OSError as exc:
        raise RuntimeError(
            f"cannot seed scratch lockfile {target} from {fixture_path}: "
            f"{exc}") from exc
    return verify_scratch_lockfile(crate_dir, fixture_path)


def materialize_probe_binaries(scratch_dir, repo_root=None, fixtures_dir=None,
                               build_fn=None, target_dir=None):
    """Materialize + build BOTH research-local probe crates outside the repo.

    Returns {probe: {"binary": Path, "provenance": dict}} where `probe` is
    `engine_probe_k31` or `null_consumer`. Every crate is materialized from
    the embedded template, seeded with its committed lock fixture and
    sha256-verified BEFORE `cargo build --release --locked`.

    `build_fn(crate_dir)` is the unit seam (default `_cargo_build`); tests
    inject a stub so no cargo runs in the unit suite.
    """
    repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
    scratch_dir = refuse_repo_root(Path(scratch_dir))
    fixtures_dir = Path(fixtures_dir) if fixtures_dir is not None else PROBE_FIXTURES_DIR
    scratch_dir.mkdir(parents=True, exist_ok=True)
    if target_dir is None:
        # One shared scratch target dir: the two crates reuse the dependency
        # builds (the feature-specific rustkmer artifacts stay distinct).
        target_dir = scratch_dir / "target"
    target_dir = Path(target_dir)

    if build_fn is None:
        def build_fn(crate_dir):
            """Default seam: `cargo build --release --locked --manifest-path`
            with the shared scratch CARGO_TARGET_DIR (never the repo target)."""
            crate_dir = Path(crate_dir)
            env = dict(os.environ, CARGO_TARGET_DIR=str(target_dir))
            return _cargo_build(
                ["cargo", "build", "--release", "--locked",
                 "--manifest-path", str(crate_dir / "Cargo.toml")],
                cwd=crate_dir, env=env)

    built = {}
    for probe, spec in PROBE_CRATES.items():
        crate_dir = scratch_dir / spec["package"]
        (crate_dir / "src").mkdir(parents=True, exist_ok=True)
        (crate_dir / "Cargo.toml").write_text(
            probe_manifest(probe, repo_root), encoding="utf-8")
        (crate_dir / "src" / "main.rs").write_text(
            spec["source"], encoding="utf-8")
        seed_and_verify_lockfile(
            crate_dir, fixtures_dir / spec["lock_fixture"])
        build_fn(crate_dir)
        binary = target_dir / "release" / spec["binary"]
        if not binary.is_file():
            raise RuntimeError(
                f"probe build produced no binary at {binary} — the build "
                f"seam did not materialize {probe}")
        built[probe] = {
            "binary": binary,
            "provenance": binary_provenance(binary, "release"),
        }
    return built


def generate_lock_fixtures(scratch_dir=None, repo_root=None, fixtures_dir=None):
    """One-time maintenance verb: regenerate the committed probe lock fixtures.

    Materializes each crate WITHOUT a lock, runs `cargo generate-lockfile
    --offline` (resolution stays inside the warm local cache — no registry
    fetch), and copies the resulting lock into the committed fixture. Never
    called by a measurement run.
    """
    repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
    scratch_dir = refuse_repo_root(
        Path(scratch_dir) if scratch_dir is not None
        else PROBE_SCRATCH_ROOT / "lock-gen")
    fixtures_dir = Path(fixtures_dir) if fixtures_dir is not None else PROBE_FIXTURES_DIR
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for probe, spec in PROBE_CRATES.items():
        crate_dir = scratch_dir / spec["package"]
        (crate_dir / "src").mkdir(parents=True, exist_ok=True)
        (crate_dir / "Cargo.toml").write_text(
            probe_manifest(probe, repo_root), encoding="utf-8")
        (crate_dir / "src" / "main.rs").write_text(
            spec["source"], encoding="utf-8")
        lock = crate_dir / "Cargo.lock"
        if lock.is_file():
            lock.unlink()
        _cargo_build(["cargo", "generate-lockfile", "--offline",
                      "--manifest-path", str(crate_dir / "Cargo.toml")],
                     cwd=crate_dir)
        if not lock.is_file():
            raise RuntimeError(
                f"cargo generate-lockfile produced no lock for {probe}")
        fixture = fixtures_dir / spec["lock_fixture"]
        fixture.write_bytes(lock.read_bytes())
        written[probe] = fixture
    return written


# --- per-instrument probe parsing -------------------------------------------


def parse_probe_output(raw_stdout, arm_k, instrument):
    """Parse one probe invocation's JSON, per instrument (fail loud, T-13-01).

    Per-instrument k contract (13-RESEARCH Pitfall 8):
      * `output-json` instruments (materialized k=31 probe, null consumer)
        take k from argv and MUST carry a matching `k` field — missing or
        mismatched k aborts the run;
      * `instrument-build` (the committed k=21 probe, whose JSON at
        examples/engine_probe.rs:79-85 has NO k field) is keyed by the
        registry-declared build-time k, asserted against the arm k.
    Zeroed nanos abort every instrument (merge_characterize._guard_zero class).
    """
    if instrument not in PROBE_INSTRUMENTS:
        raise ValueError(f"unknown probe instrument {instrument!r}")
    spec = PROBE_INSTRUMENTS[instrument]
    text = (raw_stdout or "").strip()
    if not text:
        raise ValueError(
            f"probe {instrument}: empty stdout — expected exactly one JSON "
            "object (a silent probe can never be a measurement)")
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise ValueError(
            f"probe {instrument}: stdout is not JSON ({exc}); "
            f"raw={text[:200]!r}") from None
    if not isinstance(document, dict):
        raise ValueError(
            f"probe {instrument}: stdout JSON is not an object "
            f"({type(document).__name__})")

    if spec["k_source"] == "output-json":
        if "k" not in document:
            raise ValueError(
                f"probe {instrument}: output JSON carries no k field — the "
                "materialized instruments must assert their k (Pitfall 8); "
                "refusing to attribute across k")
        if document["k"] != arm_k:
            raise ValueError(
                f"probe {instrument}: output k={document['k']!r} != arm "
                f"k={arm_k} — refusing to attribute across k")
    else:
        registered = spec["k"]
        if registered != arm_k:
            raise ValueError(
                f"probe {instrument}: registry-declared (build-time) k="
                f"{registered} != arm k={arm_k} — the committed probe is "
                "k=21-hardcoded; use the materialized variant for k=31")
        if "k" in document and document["k"] != arm_k:
            raise ValueError(
                f"probe {instrument}: output k={document['k']!r} != arm "
                f"k={arm_k}")

    wall_nanos = document.get("wall_nanos")
    if (not isinstance(wall_nanos, int) or isinstance(wall_nanos, bool)
            or wall_nanos <= 0):
        raise ValueError(
            f"probe {instrument}: wall_nanos={wall_nanos!r} — zeroed or "
            "missing nanos abort the run (guard-zero class)")
    if spec["emits_producer"]:
        producer_nanos = document.get("producer_nanos")
        if (not isinstance(producer_nanos, int)
                or isinstance(producer_nanos, bool)
                or producer_nanos <= 0):
            raise ValueError(
                f"probe {instrument}: producer_nanos={producer_nanos!r} — "
                "zeroed or missing nanos abort the run (guard-zero class)")
        workers = document.get("workers")
        if not isinstance(workers, list) or not workers:
            raise ValueError(
                f"probe {instrument}: workers must be a non-empty list "
                f"(got {workers!r})")
        for worker in workers:
            if not isinstance(worker, dict):
                raise ValueError(
                    f"probe {instrument}: malformed worker entry {worker!r}")
            busy = worker.get("busy_nanos")
            batches = worker.get("batches")
            if (not isinstance(busy, int) or isinstance(busy, bool)
                    or busy < 0):
                raise ValueError(
                    f"probe {instrument}: worker busy_nanos={busy!r} is not "
                    "a non-negative integer")
            if (not isinstance(batches, int) or isinstance(batches, bool)
                    or batches < 0):
                raise ValueError(
                    f"probe {instrument}: worker batches={batches!r} is not "
                    "a non-negative integer")
        if sum(worker["busy_nanos"] for worker in workers) <= 0:
            raise ValueError(
                f"probe {instrument}: aggregate worker busy_nanos is zero — "
                "zeroed nanos abort the run (guard-zero class)")
    else:
        records = document.get("records")
        if (not isinstance(records, int) or isinstance(records, bool)
                or records <= 0):
            raise ValueError(
                f"probe {instrument}: records={records!r} — a zero-record "
                "run is a loud abort (guard-zero class)")
    return document


# --- evidence document I/O ---------------------------------------------------


def new_doc():
    """Fresh evidence document in the pinned top-level shape."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "phase": PHASE,
        "created": _now_iso(),
        "runs": [],
        "prep": {},
        "fingerprint_gate": {},
        "attribution": {"per_k": {}},
        "predicted_win": {"per_k": {}},
        "scratch_cleaned": False,
    }


def load_doc(path):
    """Load an existing evidence JSON, or None when absent.

    Raises ValueError on a kind/schema mismatch — never merge across kinds
    (the phase-13 evidence document is its own kind, MBENCH-05 boundary).
    """
    path = Path(path)
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("kind") != KIND:
        raise ValueError(
            f"{path} is not a {KIND!r} document (kind="
            f"{document.get('kind')!r}) — refusing to merge across kinds")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} carries schema_version {document.get('schema_version')!r},"
            f" expected {SCHEMA_VERSION}")
    return document


def upsert_run(doc, record):
    """Insert/replace one run record keyed on its FULL identity.

    Identity is (arm, k, rep, part, input_type): records sharing arm/k/rep
    but differing in part or input_type persist as distinct records (arm C
    holds 4 and arm D 2 per rep at rehearsal; control 2), while a
    same-identity rewrite replaces the previous record.
    """
    identity = (record["arm"], record["k"], record["rep"],
                record.get("part"), record.get("input_type"))
    runs = [
        existing for existing in doc.get("runs", [])
        if (existing.get("arm"), existing.get("k"), existing.get("rep"),
            existing.get("part"), existing.get("input_type")) != identity
    ]
    runs.append(record)
    runs.sort(key=lambda item: (
        str(item.get("arm")), int(item.get("k") or 0),
        int(item.get("rep") or 0), str(item.get("part") or ""),
        str(item.get("input_type") or "")))
    doc["runs"] = runs


def write_doc(path, doc):
    """Write the evidence JSON (indent=2, sort_keys, trailing newline)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")


# --- pure attribution / predicted-win / decision functions ------------------


def fingerprint_gate(current_provenance):
    """D-03/D-10 gate: branch on EXACT sha256 equality, record both hashes.

    Returns {"current_sha256", "v2_0_sha256", "branch"} where branch is
    'cite' on exact equality else 're-measure'. The gate never silently
    defaults: an unreadable/missing current hash raises.
    """
    binary = (current_provenance or {}).get("binary")
    if not isinstance(binary, dict):
        raise ValueError(
            "fingerprint_gate: provenance block carries no binary sub-dict — "
            "the gate cannot branch without the actual executable hash")
    current_sha = binary.get("sha256")
    if not isinstance(current_sha, str) or not current_sha.strip():
        raise ValueError(
            "fingerprint_gate: provenance binary.sha256 is missing — the "
            "D-03 gate cannot branch without the current fingerprint")
    branch = "cite" if current_sha == V2_0_RUSTKMER_SHA256 else "re-measure"
    return {
        "current_sha256": current_sha,
        "v2_0_sha256": V2_0_RUSTKMER_SHA256,
        "branch": branch,
    }


def assert_clean_tree(provenance):
    """D-10 clean-rebuild precondition: a dirty tree cannot gate.

    The stock binary must be rebuilt clean from HEAD before the gate
    computation, with git_dirty false asserted and recorded (T-13-03).
    """
    if (provenance or {}).get("git_dirty") is not False:
        raise RuntimeError(
            "clean-rebuild assertion: the stock binary's provenance records "
            f"git_dirty={provenance.get('git_dirty')!r} — the D-10 gate "
            "requires a clean rebuild from HEAD (git_dirty must be false). "
            f"Provenance: {provenance!r}")


def _arm_records(runs, arm, k):
    """Every record of ONE arm at ONE k (order preserved)."""
    return [record for record in runs
            if record.get("arm") == arm and record.get("k") == k]


def _cite(record):
    """The citation key of one run record (arm/k/rep/part/input_type)."""
    return {
        "arm": record.get("arm"),
        "k": record.get("k"),
        "rep": record.get("rep"),
        "part": record.get("part"),
        "input_type": record.get("input_type"),
    }


def _cite_sort_key(citation):
    return (str(citation.get("arm")), int(citation.get("k") or 0),
            int(citation.get("rep") or 0),
            str(citation.get("part") or ""),
            str(citation.get("input_type") or ""))


def _sorted_citations(citations):
    """Dedupe by citation identity and sort deterministically (arm/k/rep/part)."""
    keyed = {}
    for item in citations:
        keyed.setdefault(_cite_sort_key(item), item)
    return [keyed[key] for key in sorted(keyed)]


def _pair_sum_median(arm_records, value_fn, k, input_type):
    """Pair-sum-then-median reduction over ONE arm's named input-type subset.

    Filters the arm's records to `k` and `input_type`, groups the surviving
    pinned-pair part records by rep, requires EXACTLY the two PINNED_PAIR
    parts per rep (a missing or extra part raises naming the rep and input
    type), sums the parts' values per rep, then takes the median over reps.

    Bench.reduce_arm is never applied to probe JSON (bench.py:1319-1340 reads
    only wall_s/peak_rss_bytes); probe nanos always reduce this way.

    Returns {"value_s", "per_rep_s", "citations"}.
    """
    subset = [record for record in arm_records
              if record.get("k") == k
              and record.get("input_type") == input_type]
    if not subset:
        raise ValueError(
            f"_pair_sum_median: no records for k={k} input_type="
            f"{input_type!r} — refusing to invent a reduction")
    by_rep = {}
    for record in subset:
        by_rep.setdefault(record.get("rep"), []).append(record)
    per_rep = {}
    citations = []
    for rep in sorted(by_rep):
        part_records = by_rep[rep]
        parts = [record.get("part") for record in part_records]
        if (len(parts) != len(PINNED_PAIR)
                or sorted(str(part) for part in parts) != sorted(PINNED_PAIR)):
            raise ValueError(
                f"_pair_sum_median: rep {rep} input_type {input_type!r} "
                f"carries parts {parts!r}; expected exactly the pinned pair "
                f"{list(PINNED_PAIR)} (a missing or extra part is a loud "
                "abort, never a silently thinner reduction)")
        total = sum(int(value_fn(record)) for record in part_records)
        if total <= 0:
            raise ValueError(
                f"_pair_sum_median: rep {rep} input_type {input_type!r} "
                f"sums to {total} nanos — zeroed nanos abort the reduction "
                "(guard-zero class)")
        per_rep[rep] = total / 1e9
        citations.extend(_cite(record) for record in part_records)
    if not per_rep:
        raise ValueError(
            f"_pair_sum_median: no reps for k={k} input_type={input_type!r}")
    return {
        "value_s": statistics.median(per_rep.values()),
        "per_rep_s": {str(rep): per_rep[rep] for rep in sorted(per_rep)},
        "citations": _sorted_citations(citations),
    }


def _wall_median(records, label, k):
    """bench.reduce_arm median wall over one arm's records (loud if absent)."""
    if not records:
        raise ValueError(
            f"build_attribution: missing {label} record for k={k} — "
            "refusing to compute a partial attribution table")
    return reduce_arm(records)["median_wall_s"]


def build_attribution(runs, k):
    """The D-09 stage attribution for one k, from recorded runs only.

    Exact keys: inflate_s, parse_extract_s, route_send_s, output_stage_s
    (the D-09 names), raw_a_minus_b_s, delta_correction_s, plus the three
    probe terms and the arm medians they derive from, and citations.

    Derivation (13-RESEARCH "Attribution arithmetic"), all unrounded:
      raw_a_minus_b_s       = median_A - median_B
      delta_correction_s    = median_read_gz - median_read_plain
      inflate_s             = raw_a_minus_b_s - delta_correction_s
      parse_extract_s       = pair-sum median of arm-D plain wall_nanos
      producer_plain_probe_s= pair-sum median of arm-C plain producer_nanos
      count_phase_wall_probe_s = pair-sum median of arm-C gzip wall_nanos
      worker_busy_total_s   = pair-sum median of arm-C gzip aggregate busy
      route_send_s          = producer_plain_probe_s - parse_extract_s
      output_stage_s        = median_A - count_phase_wall_probe_s

    A zero/negative delta-corrected inflate share is recorded EXACTLY as
    measured — never clamped positive, never rounded away from zero (D-09).
    Context/excluded (D-07) records are structurally refused.
    """
    k_records = [record for record in runs if record.get("k") == k]
    if not k_records:
        raise ValueError(
            f"build_attribution: no records for k={k} — refusing to compute "
            "an attribution table from an empty run set")
    context = [record for record in k_records
               if record.get("context") or record.get("excluded")]
    if context:
        offender = context[0]
        raise ValueError(
            "build_attribution: refusing context/excluded records "
            f"(arm={offender.get('arm')!r} k={offender.get('k')!r} "
            f"rep={offender.get('rep')!r} part={offender.get('part')!r}) — "
            "the D-07 context matrix is structurally invisible to the gate")

    arm_a = _arm_records(k_records, "A", k)
    arm_b = _arm_records(k_records, "B", k)
    control_gz = [record for record in _arm_records(k_records, "control", k)
                  if record.get("input_type") == "gzip"]
    control_plain = [record for record in _arm_records(k_records, "control", k)
                     if record.get("input_type") == "plain"]
    arm_c = _arm_records(k_records, "C", k)
    arm_d = _arm_records(k_records, "D", k)

    median_a = _wall_median(arm_a, "arm-A (stock gzip)", k)
    median_b = _wall_median(arm_b, "arm-B (pre-decompressed)", k)
    median_read_gz = _wall_median(control_gz, "control gzip", k)
    median_read_plain = _wall_median(control_plain, "control plain", k)
    if not arm_c:
        raise ValueError(
            f"build_attribution: missing arm-C (stage sub-timer) records for "
            f"k={k} — refusing to compute route_send/output_stage")
    if not arm_d:
        raise ValueError(
            f"build_attribution: missing arm-D (null consumer) records for "
            f"k={k} — refusing to compute parse_extract")

    count_phase = _pair_sum_median(
        arm_c, lambda record: record["probe_output_json"]["wall_nanos"],
        k, "gzip")
    producer_plain = _pair_sum_median(
        arm_c, lambda record: record["probe_output_json"]["producer_nanos"],
        k, "plain")
    worker_busy = _pair_sum_median(
        arm_c, lambda record: record["aggregate_worker_busy_nanos"],
        k, "gzip")
    parse_extract = _pair_sum_median(
        arm_d, lambda record: record["probe_output_json"]["wall_nanos"],
        k, "plain")

    raw_a_minus_b_s = median_a - median_b
    delta_correction_s = median_read_gz - median_read_plain
    inflate_s = raw_a_minus_b_s - delta_correction_s
    route_send_s = producer_plain["value_s"] - parse_extract["value_s"]
    output_stage_s = median_a - count_phase["value_s"]

    citations = {
        "arm_a_median_s": [_cite(record) for record in arm_a],
        "arm_b_median_s": [_cite(record) for record in arm_b],
        "median_read_gz_s": [_cite(record) for record in control_gz],
        "median_read_plain_s": [_cite(record) for record in control_plain],
        "raw_a_minus_b_s": ([_cite(record) for record in arm_a]
                            + [_cite(record) for record in arm_b]),
        "delta_correction_s": ([_cite(record) for record in control_gz]
                               + [_cite(record) for record in control_plain]),
        "inflate_s": ([_cite(record) for record in arm_a]
                      + [_cite(record) for record in arm_b]
                      + [_cite(record) for record in control_gz]
                      + [_cite(record) for record in control_plain]),
        "count_phase_wall_probe_s": count_phase["citations"],
        "producer_plain_probe_s": producer_plain["citations"],
        "worker_busy_total_s": worker_busy["citations"],
        "parse_extract_s": parse_extract["citations"],
        "route_send_s": (producer_plain["citations"]
                         + parse_extract["citations"]),
        "output_stage_s": ([_cite(record) for record in arm_a]
                           + count_phase["citations"]),
    }
    return {
        "k": k,
        "inflate_s": inflate_s,
        "parse_extract_s": parse_extract["value_s"],
        "route_send_s": route_send_s,
        "output_stage_s": output_stage_s,
        "raw_a_minus_b_s": raw_a_minus_b_s,
        "delta_correction_s": delta_correction_s,
        "count_phase_wall_probe_s": count_phase["value_s"],
        "producer_plain_probe_s": producer_plain["value_s"],
        "worker_busy_total_s": worker_busy["value_s"],
        "arm_a_median_s": median_a,
        "arm_b_median_s": median_b,
        "median_read_gz_s": median_read_gz,
        "median_read_plain_s": median_read_plain,
        "pair_sum_per_rep_s": {
            "count_phase_wall_probe_s": count_phase["per_rep_s"],
            "producer_plain_probe_s": producer_plain["per_rep_s"],
            "worker_busy_total_s": worker_busy["per_rep_s"],
            "parse_extract_s": parse_extract["per_rep_s"],
        },
        "citations": {key: _sorted_citations(value)
                      for key, value in citations.items()},
    }


def _require_number(attribution, key):
    """One attribution input must be a real number, or the model refuses."""
    value = attribution.get(key)
    if (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise ValueError(
            f"build_predicted_win: attribution input {key!r} is "
            f"{value!r} — refusing to model from an unresolved input "
            "(every input number must cite a named full-scale run)")
    return float(value)


def build_predicted_win(attribution, k, runs):
    """The PEXT-02 predicted-win model for one k: BOTH ceilings, every input
    cited, point-or-bounds mode (D-09 + A3/A4).

    serial_terms_s        = inflate_s + route_send_s
    parallelizable floor  = serial_terms_s + parse_extract_s / extractors,
                            under the derated (E=0.5) AND idealized E=M
                            extractor-efficiency bounds
    worker_floor_s        = worker_busy_total_s / WORKER_SCALING_CEILING
                            (the pre-registered, never-fitted ceiling)
    predicted_full_wall_s = max(parallelizable floor, worker floor)
                            + output_stage_s
    improvement_pct       = (1 - predicted_full_wall_s / arm_A_median) * 100

    mode='bounds' when either A3/A4 anomaly criterion trips
    (probe_vs_cli_ratio outside PROBE_VS_CLI_RATIO_BAND, worker_busy_ratio >
    WORKER_BUSY_RATIO_MAX, or a non-positive worker busy total). In bounds
    mode the point keys carry the CONSERVATIVE (derated) end so
    derive_gate_decision consumes the same input in both modes.
    """
    inflate_s = _require_number(attribution, "inflate_s")
    parse_extract_s = _require_number(attribution, "parse_extract_s")
    route_send_s = _require_number(attribution, "route_send_s")
    output_stage_s = _require_number(attribution, "output_stage_s")
    count_phase_wall_probe_s = _require_number(
        attribution, "count_phase_wall_probe_s")
    worker_busy_total_s = _require_number(attribution, "worker_busy_total_s")

    arm_a = _arm_records(runs, "A", k)
    if arm_a:
        arm_a_median_s = reduce_arm(arm_a)["median_wall_s"]
        arm_a_citations = [_cite(record) for record in arm_a]
    else:
        arm_a_median_s = _require_number(attribution, "arm_a_median_s")
        arm_a_citations = list(
            (attribution.get("citations") or {}).get("arm_a_median_s") or [])
    if arm_a_median_s <= 0:
        raise ValueError(
            f"build_predicted_win: arm-A median {arm_a_median_s!r} for k={k} "
            "is not positive — the predicted-win denominator must be a "
            "measured wall")

    serial_terms_s = inflate_s + route_send_s
    derated_extractors = EXTRACTOR_COUNT * EXTRACTOR_EFFICIENCY_DERATED
    parallelizable_floor_derated_s = (
        serial_terms_s + parse_extract_s / derated_extractors)
    parallelizable_floor_idealized_s = (
        serial_terms_s + parse_extract_s / EXTRACTOR_COUNT)
    worker_floor_s = worker_busy_total_s / WORKER_SCALING_CEILING

    derated_full_wall_s = (max(parallelizable_floor_derated_s, worker_floor_s)
                           + output_stage_s)
    idealized_full_wall_s = (
        max(parallelizable_floor_idealized_s, worker_floor_s)
        + output_stage_s)
    derated_improvement_pct = (
        (1 - derated_full_wall_s / arm_a_median_s) * 100)
    idealized_improvement_pct = (
        (1 - idealized_full_wall_s / arm_a_median_s) * 100)

    probe_vs_cli_ratio = count_phase_wall_probe_s / arm_a_median_s
    worker_busy_ratio = (
        worker_busy_total_s / (EXTRACTOR_COUNT * count_phase_wall_probe_s)
        if count_phase_wall_probe_s > 0 else float("inf"))

    anomalies = []
    low, high = PROBE_VS_CLI_RATIO_BAND
    if not (low < probe_vs_cli_ratio <= high):
        anomalies.append(
            "probe_vs_cli_ratio={:.4f} outside the pinned band ({}, {}] — the "
            "arm-C probe's count-phase wall is not a valid instrument for the "
            "CLI pair-run count phase at this k (A3)".format(
                probe_vs_cli_ratio, low, high))
    if worker_busy_ratio > WORKER_BUSY_RATIO_MAX:
        anomalies.append(
            "worker_busy_ratio={:.4f} exceeds WORKER_BUSY_RATIO_MAX={} — "
            "aggregate busy_nanos does not bound the worker-side ceiling "
            "(A4)".format(worker_busy_ratio, WORKER_BUSY_RATIO_MAX))
    if worker_busy_total_s <= 0:
        anomalies.append(
            "worker_busy_total_s={:.6f} is not positive — the worker floor is "
            "undefined at this k (A4)".format(worker_busy_total_s))
    mode = "bounds" if anomalies else "point"

    thresholds = {
        "probe_vs_cli_ratio_band": list(PROBE_VS_CLI_RATIO_BAND),
        "worker_busy_ratio_max": WORKER_BUSY_RATIO_MAX,
        "extractor_count": EXTRACTOR_COUNT,
        "extractor_efficiency_derated": EXTRACTOR_EFFICIENCY_DERATED,
        "worker_scaling_ceiling": WORKER_SCALING_CEILING,
    }
    citations = {
        "inflate_s": list((attribution.get("citations") or {}).get(
            "inflate_s") or []),
        "route_send_s": list((attribution.get("citations") or {}).get(
            "route_send_s") or []),
        "parse_extract_s": list((attribution.get("citations") or {}).get(
            "parse_extract_s") or []),
        "count_phase_wall_probe_s": list(
            (attribution.get("citations") or {}).get(
                "count_phase_wall_probe_s") or []),
        "worker_busy_total_s": list((attribution.get("citations") or {}).get(
            "worker_busy_total_s") or []),
        "output_stage_s": list((attribution.get("citations") or {}).get(
            "output_stage_s") or []),
        "arm_a_median_s": arm_a_citations,
    }
    for key, value in citations.items():
        if not value:
            raise ValueError(
                f"build_predicted_win: model input {key!r} carries no "
                "citation — every input number must name its source run "
                "(PEXT-02)")

    block = {
        "k": k,
        "mode": mode,
        "serial_terms_s": serial_terms_s,
        "parallelizable_floor_derated_s": parallelizable_floor_derated_s,
        "parallelizable_floor_idealized_s": parallelizable_floor_idealized_s,
        "worker_floor_s": worker_floor_s,
        "output_stage_s": output_stage_s,
        "predicted_full_wall_s": derated_full_wall_s,
        "predicted_improvement_pct": derated_improvement_pct,
        "idealized_predicted_full_wall_s": idealized_full_wall_s,
        "idealized_predicted_improvement_pct": idealized_improvement_pct,
        "arm_a_median_s": arm_a_median_s,
        "worker_scaling_ceiling": WORKER_SCALING_CEILING,
        "extractor_count": EXTRACTOR_COUNT,
        "extractor_efficiency_derated": EXTRACTOR_EFFICIENCY_DERATED,
        "probe_vs_cli_ratio": probe_vs_cli_ratio,
        "worker_busy_ratio": worker_busy_ratio,
        "thresholds": thresholds,
        "citations": {key: _sorted_citations(value)
                      for key, value in citations.items()},
    }
    if mode == "bounds":
        block["bounds"] = {
            "predicted_full_wall_s": {
                "lower_s": derated_full_wall_s,
                "upper_s": idealized_full_wall_s,
            },
            "predicted_improvement_pct": {
                "lower_pct": derated_improvement_pct,
                "upper_pct": idealized_improvement_pct,
            },
        }
        block["what_would_need_to_be_true"] = [
            anomaly for anomaly in anomalies
        ] + [
            "the arm-C probe and the CLI pair-run must measure the same "
            "count-phase topology (one file per probe invocation vs one "
            "engine over the pinned pair) before point shares are quoted "
            "(Pitfall 7)",
            "aggregate worker busy_nanos must stay a valid worker-side "
            "ceiling numerator at 16 threads (A4)",
        ]
    return block


def derive_gate_decision(predicted_win_by_k):
    """D-05: GO iff the CONSERVATIVE (derated) predicted improvement is
    >= D3_BAR_FULL_WALL_IMPROVEMENT_PCT at BOTH k.

    Exactly the bar at both k is GO (>= semantics); either k below is
    NO-GO (conjunction). The idealized E=M bound is reported alongside but
    NEVER participates in this test.
    """
    per_k = {}
    for k in GATE_KS:
        block = (predicted_win_by_k.get(str(k))
                 or predicted_win_by_k.get(k))
        if not isinstance(block, dict):
            raise ValueError(
                f"derive_gate_decision: no predicted-win block for k={k} — "
                "the bar is applied at both k, never one")
        value = block.get("predicted_improvement_pct")
        if (not isinstance(value, (int, float)) or isinstance(value, bool)):
            raise ValueError(
                f"derive_gate_decision: k={k} carries no numeric "
                f"predicted_improvement_pct ({value!r})")
        per_k[str(k)] = float(value)
    decision = ("GO"
                if all(value >= D3_BAR_FULL_WALL_IMPROVEMENT_PCT
                       for value in per_k.values())
                else "NO-GO")
    return {
        "decision": decision,
        "bar_pct": D3_BAR_FULL_WALL_IMPROVEMENT_PCT,
        "per_k_improvement_pct": per_k,
        "conservative_bound_used": True,
    }


def _gate_records(doc):
    """The doc's gate records: full-scale-eligible, never context/excluded."""
    return [record for record in (doc.get("runs") or [])
            if not record.get("context") and not record.get("excluded")]


def compute_gate_blocks(doc):
    """Attach doc['attribution'] and doc['predicted_win'] from gate records.

    Same pure functions in rehearsal and at full scale — the rehearsal
    exercises production code, not a parallel demo path.
    """
    gate = _gate_records(doc)
    attribution = {}
    predicted = {}
    for k in GATE_KS:
        attribution[str(k)] = build_attribution(gate, k)
    for k in GATE_KS:
        predicted[str(k)] = build_predicted_win(
            attribution[str(k)], k, gate)
    decision = derive_gate_decision(predicted)
    doc["attribution"] = {"per_k": attribution}
    doc["predicted_win"] = {"per_k": predicted, **decision}
    return doc


# --- memo rendering (D-02 deterministic projection) --------------------------


def _format_seconds(value):
    return f"{float(value):.4f}"


def _citation_text(citations):
    if not citations:
        return "no citation"
    return "; ".join(
        "{arm}/k{k}/rep{rep}/part={part}/input={input_type}".format(
            arm=item.get("arm"), k=item.get("k"), rep=item.get("rep"),
            part=item.get("part") if item.get("part") is not None else "-",
            input_type=item.get("input_type"))
        for item in citations)


def _part_spread_rows(doc):
    """Arm-C per-part rows: pinned pair from gate records, the four
    non-pinned parts from the excluded context matrix (single-rep context).

    Deterministic: fixed part order, sorted input types, no clock.
    """
    arm_c = [record for record in (doc.get("runs") or [])
             if record.get("arm") == "C"]
    rows = []
    for part in EXPECTED_PARTS:
        for input_type in ("gzip", "plain"):
            gate = [record for record in arm_c
                    if record.get("part") == part
                    and record.get("input_type") == input_type
                    and not record.get("context")
                    and not record.get("excluded")]
            context = [record for record in arm_c
                       if record.get("part") == part
                       and record.get("input_type") == input_type
                       and (record.get("context") or record.get("excluded"))]
            if gate:
                cells = []
                for k in GATE_KS:
                    values = [
                        record["probe_output_json"]["wall_nanos"] / 1e9
                        for record in gate if record.get("k") == k
                    ]
                    if values:
                        cells.append(
                            f"k={k}: {statistics.median(values):.4f} s "
                            f"({len(values)} reps)")
                if cells:
                    rows.append((part, input_type, "gate records",
                                 "; ".join(cells)))
            elif context:
                chosen = sorted(
                    context,
                    key=lambda record: (int(record.get("k") or 0),
                                        int(record.get("rep") or 0)))[0]
                rows.append((
                    part, input_type, "single-rep context",
                    f"k={chosen.get('k')}: "
                    f"{chosen['probe_output_json']['wall_nanos'] / 1e9:.4f} s"))
    return rows


def render_memo_text(doc):
    """Render the D-02 gate memo deterministically from the evidence doc.

    No clock reads, no environment reads, fixed decimal formatting — two
    invocations on the same doc are byte-identical by construction.

    Sections: decision + the D-05 pre-registered bar; stage attribution at
    both k (D-09 names, every cell cited); predicted-win arithmetic with BOTH
    ceilings (and, in bounds mode, the interval bounds plus the
    what-would-need-to-be-true list instead of point shares); fresh-base
    statement + v2.0 CLI corroboration with the fingerprint delta disclosed;
    the D-06 Python-surface context block (context only); the D-03/D-10 gate
    provenance block; on GO the six-part Phase-14 sizing context + the
    probe-vs-CLI topology sentence, on NO-GO the revisit conditions; the D-04
    lifecycle/deletion record.
    """
    attribution = (doc.get("attribution") or {}).get("per_k") or {}
    predicted = doc.get("predicted_win") or {}
    decision = predicted.get("decision")
    if decision not in ("GO", "NO-GO"):
        raise ValueError(
            f"render_memo_text: predicted_win.decision is {decision!r} — "
            "refusing to render a memo without a recorded decision")
    bar = predicted.get("bar_pct", D3_BAR_FULL_WALL_IMPROVEMENT_PCT)
    gate = doc.get("fingerprint_gate") or {}
    branch = gate.get("branch")
    if branch not in ("cite", "re-measure"):
        raise ValueError(
            f"render_memo_text: fingerprint_gate.branch is {branch!r} — the "
            "memo must carry the D-03/D-10 branch, never a silent default")
    per_k_predicted = predicted.get("per_k") or {}

    lines = []
    lines.append("# Phase 13 — Producer Attribution Gate Memo (D-02)")
    lines.append("")
    lines.append("> Deterministic render of the Phase-13 evidence document "
                 "(`phase13-producer-attribution`). Every number below cites "
                 "a named full-scale run record; the renderer reads no clock "
                 "and no environment.")
    lines.append("")
    lines.append("## 1. Decision")
    lines.append("")
    lines.append(f"DECISION: {decision}")
    lines.append("")
    lines.append(
        "Pre-registered D-05 bar: predicted full-wall improvement "
        f">= {float(bar):.1f}% on the CONSERVATIVE (efficiency-derated, "
        f"E = {EXTRACTOR_EFFICIENCY_DERATED}) model at "
        f"{EXTRACTOR_COUNT} extractor threads, applied at BOTH k as a "
        "conjunction (exactly the bar at both k is GO; either k below is "
        "NO-GO). The idealized E=M bound is reported alongside but is never "
        "the bar input.")
    lines.append("")
    per_k_improvement = predicted.get("per_k_improvement_pct") or {}
    for k in GATE_KS:
        value = per_k_improvement.get(str(k))
        if value is not None:
            lines.append(f"- k={k}: conservative predicted improvement "
                         f"{float(value):.4f}%")
    lines.append("")

    lines.append("## 2. Stage attribution (D-09)")
    lines.append("")
    lines.append(
        "The four D-09 stage names plus the control correction. A zero or "
        "negative delta-corrected inflate share is recorded exactly as "
        "measured — never clamped positive, never rounded away from zero.")
    lines.append("")
    for k in GATE_KS:
        block = attribution.get(str(k))
        if not isinstance(block, dict):
            raise ValueError(
                f"render_memo_text: attribution.per_k[{str(k)!r}] is missing "
                "— refusing to render a partial stage table")
        lines.append(f"### k={k}")
        lines.append("")
        lines.append("| Stage | Seconds | Source records |")
        lines.append("|---|---|---|")
        citations = block.get("citations") or {}
        stage_names = (
            "inflate_s", "parse_extract_s", "route_send_s", "output_stage_s",
            "raw_a_minus_b_s", "delta_correction_s",
            "count_phase_wall_probe_s", "producer_plain_probe_s",
            "worker_busy_total_s",
        )
        for name in stage_names:
            lines.append(
                f"| {name} | {_format_seconds(block[name])} | "
                f"{_citation_text(citations.get(name) or [])} |")
        lines.append("")

    lines.append("## 3. Predicted-win model (PEXT-02, both ceilings)")
    lines.append("")
    lines.append(
        "Composition rule (D-09): predicted_full_wall = "
        "max(parallelizable floor, worker floor) + output_stage_s.")
    lines.append("")
    for k in GATE_KS:
        block = per_k_predicted.get(str(k))
        if not isinstance(block, dict):
            raise ValueError(
                f"render_memo_text: predicted_win.per_k[{str(k)!r}] is "
                "missing — refusing to render a partial model")
        citations = block.get("citations") or {}
        lines.append(f"### k={k}")
        lines.append("")
        lines.append(
            f"- PARALLELIZABLE CEILING (derated E={EXTRACTOR_EFFICIENCY_DERATED}"
            f", extractors={EXTRACTOR_COUNT * EXTRACTOR_EFFICIENCY_DERATED:.1f}): "
            f"{_format_seconds(block['parallelizable_floor_derated_s'])} s "
            f"[{_citation_text(citations.get('parse_extract_s') or [])}]")
        lines.append(
            f"- PARALLELIZABLE CEILING (idealized E=M, extractors="
            f"{EXTRACTOR_COUNT}): "
            f"{_format_seconds(block['parallelizable_floor_idealized_s'])} s")
        lines.append(
            f"- WORKER-SIDE CEILING (worker_busy_total_s / "
            f"WORKER_SCALING_CEILING={block['worker_scaling_ceiling']}): "
            f"{_format_seconds(block['worker_floor_s'])} s "
            f"[{_citation_text(citations.get('worker_busy_total_s') or [])}]")
        lines.append(
            f"- serial terms (inflate + route_send): "
            f"{_format_seconds(block['serial_terms_s'])} s "
            f"[{_citation_text(citations.get('route_send_s') or [])}]")
        lines.append(
            f"- output stage (sort + write): "
            f"{_format_seconds(block['output_stage_s'])} s "
            f"[{_citation_text(citations.get('output_stage_s') or [])}]")
        lines.append(
            f"- anomaly criteria: probe_vs_cli_ratio="
            f"{block['probe_vs_cli_ratio']:.4f} (band "
            f"{list(PROBE_VS_CLI_RATIO_BAND)}), worker_busy_ratio="
            f"{block['worker_busy_ratio']:.4f} "
            f"(max {WORKER_BUSY_RATIO_MAX}), mode={block['mode']}")
        if block["mode"] == "bounds":
            bounds = block.get("bounds") or {}
            walls = bounds.get("predicted_full_wall_s") or {}
            pcts = bounds.get("predicted_improvement_pct") or {}
            lines.append(
                "- BOUNDS MODE: point shares withheld. "
                f"predicted_full_wall in [{_format_seconds(walls.get('lower_s', 0.0))}, "
                f"{_format_seconds(walls.get('upper_s', 0.0))}] s; "
                f"improvement in [{float(pcts.get('lower_pct', 0.0)):.4f}, "
                f"{float(pcts.get('upper_pct', 0.0)):.4f}] %")
            lines.append("- What would need to be true:")
            for item in block.get("what_would_need_to_be_true") or []:
                lines.append(f"  - {item}")
        else:
            lines.append(
                f"- predicted_full_wall = max({_format_seconds(block['parallelizable_floor_derated_s'])}, "
                f"{_format_seconds(block['worker_floor_s'])}) + output stage = "
                f"{_format_seconds(block['predicted_full_wall_s'])} s")
            lines.append(
                f"- predicted improvement vs fresh arm-A median "
                f"({_format_seconds(block['arm_a_median_s'])} s): "
                f"{block['predicted_improvement_pct']:.4f}% (conservative/"
                f"derated); idealized E=M bound: "
                f"{block['idealized_predicted_improvement_pct']:.4f}%")
            lines.append(
                f"- arm-A citations: "
                f"{_citation_text(citations.get('arm_a_median_s') or [])}")
        lines.append("")

    lines.append("## 4. Fresh base and v2.0 corroboration (D-03/D-10)")
    lines.append("")
    lines.append(
        "Fingerprint gate: current release binary sha256 "
        f"`{gate.get('current_sha256')}` vs v2.0's recorded fingerprint "
        f"`{V2_0_RUSTKMER_SHA256}` -> branch `{branch}`.")
    lines.append("")
    if branch == "re-measure":
        lines.append(
            "Because the gate fired `re-measure`, arm A's own fresh medians "
            "are the ONLY decision denominator. The v2.0 CLI walls "
            f"({V2_0_CLI_WALL_K21_S:.2f} s k=21 / "
            f"{V2_0_CLI_WALL_K31_S:.2f} s k=31) are disclosed-fingerprint "
            "corroboration only; no memo percentage uses a v2.0 wall as its "
            "denominator while the fingerprint mismatch stands.")
    else:
        lines.append(
            "The gate fired `cite`: the current binary is byte-identical to "
            "v2.0's recorded release binary, so the v2.0 walls "
            f"({V2_0_CLI_WALL_K21_S:.2f} s k=21 / "
            f"{V2_0_CLI_WALL_K31_S:.2f} s k=31) are citable as the base.")
    lines.append("")
    lines.append("### D-03/D-10 gate provenance")
    lines.append("")
    lines.append(f"- current_sha256: `{gate.get('current_sha256')}`")
    lines.append(f"- v2_0_sha256: `{V2_0_RUSTKMER_SHA256}`")
    lines.append(f"- branch: `{branch}`")
    provenance = doc.get("provenance") or {}
    if provenance:
        lines.append(
            f"- git_commit: `{provenance.get('git_commit')}`; "
            f"git_dirty: `{provenance.get('git_dirty')}`; "
            f"build_profile: `{provenance.get('build_profile')}`; "
            f"platform: `{provenance.get('platform')}`; "
            f"rust_toolchain: `{provenance.get('rust_toolchain')}`")
    lines.append("")

    lines.append("## 5. Python-surface context (D-06)")
    lines.append("")
    lines.append(
        "The decision surface is the CLI count wall only. The Python-surface "
        f"walls (k=21 {V2_0_PYTHON_WALL_K21_S:.2f} s, "
        f"k=31 {V2_0_PYTHON_WALL_K31_S:.2f} s) are context only, recorded "
        f"against the v2.0 module fingerprint "
        f"`{V2_0_PYTHON_MODULE_SHA256}`. "
        "The binary-fingerprint caveat applies: those Python walls were "
        "measured on a different binary fingerprint than the current release "
        "build, so they are neither a denominator nor a headline — context "
        "only.")
    lines.append("")

    if decision == "GO":
        lines.append("## 6. Phase-14 sizing context (excluded from the gate)")
        lines.append("")
        lines.append(
            "probe-vs-CLI topology: arm C/D probes count ONE file per "
            "invocation with a fresh engine, while CLI arms A/B count the "
            "pinned pair in ONE engine (RESEARCH Pitfall 7) — the per-part "
            "spread below is sizing context, never a gate input.")
        lines.append("")
        lines.append("| Part | Input | Source | Wall |")
        lines.append("|---|---|---|---|")
        rows = _part_spread_rows(doc)
        for part, input_type, source, cell in rows:
            lines.append(f"| {part} | {input_type} | {source} | {cell} |")
        measured_parts = sorted({row[0] for row in rows})
        if len(measured_parts) < len(EXPECTED_PARTS):
            lines.append("")
            lines.append(
                f"Context matrix coverage: {len(measured_parts)} of "
                f"{len(EXPECTED_PARTS)} dataset parts recorded at this scale.")
        lines.append("")
    else:
        lines.append("## 6. Revisit conditions (NO-GO)")
        lines.append("")
        lines.append(
            "PEXT-03/04 remain unexecuted BY RECORDED DECISION. Revisit only "
            "if one of the following changes and is re-pre-registered before "
            "any measurement:")
        lines.append("")
        lines.append(
            "- the conservative predicted improvement at either k rises to "
            f">= {D3_BAR_FULL_WALL_IMPROVEMENT_PCT:.1f}% on a fresh full-scale "
            "session (bar unchanged);")
        lines.append(
            "- the inflate share measures >= ~20% of producer wall, firing "
            "the separate zlib-rs decision;")
        lines.append(
            "- the arm-C/D topology confound is removed by a paired "
            "instrument, turning the bounds interval into point shares.")
        lines.append("")

    lines.append("## 7. Lifecycle / deletion record (D-04)")
    lines.append("")
    lines.append(
        f"Plain inputs were decompressed once into "
        f"`{PLAIN_INPUTS_DIR}` (the `CRR1936095-plain` path token) and are "
        "regenerable per part:")
    lines.append("")
    lines.append(
        f"    gunzip -c <DATASET_DIR>/<part>.fq.gz > "
        f"{PLAIN_INPUTS_DIR}/<part>.fq")
    lines.append("")
    lines.append(
        "Their provenance (part, path, size_bytes, sha256, "
        "decompression_command) is recorded in the evidence document's prep "
        "block BEFORE any deletion; deletion happens only after this memo is "
        "committed.")
    lines.append("")
    text = "\n".join(lines)
    return text if text.endswith("\n") else text + "\n"


def _assert_memo_contract(text, doc):
    """The D-02 contract gate: refuse to publish a memo missing a pinned block."""
    required = [
        "DECISION:",
        "Pre-registered D-05 bar",
        "PARALLELIZABLE CEILING",
        "WORKER-SIDE CEILING",
        "Fresh base and v2.0 corroboration",
        "D-03/D-10 gate provenance",
        "Python-surface context (D-06)",
        f"{V2_0_PYTHON_WALL_K21_S:.2f}",
        f"{V2_0_PYTHON_WALL_K31_S:.2f}",
        V2_0_PYTHON_MODULE_SHA256,
        "context only",
        "binary-fingerprint caveat",
        "Lifecycle / deletion record",
        f"{D3_BAR_FULL_WALL_IMPROVEMENT_PCT:.1f}",
    ]
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(
            "memo contract: the rendered text is missing required tokens "
            f"{missing!r} — refusing to publish")
    decision = (doc.get("predicted_win") or {}).get("decision")
    bounds_yet = any(
        (block or {}).get("mode") == "bounds"
        for block in ((doc.get("predicted_win") or {}).get("per_k") or {}
                      ).values())
    if bounds_yet:
        for token in ("BOUNDS MODE", "What would need to be true"):
            if token not in text:
                raise RuntimeError(
                    "memo contract: a bounds-mode model must render the "
                    f"interval bounds and {token!r}")
    if decision == "GO":
        for token in ("Phase-14 sizing context", "probe-vs-CLI topology"):
            if token not in text:
                raise RuntimeError(
                    f"memo contract: a GO memo must carry {token!r}")
    return True


# --- record building ---------------------------------------------------------


def build_run_record(arm, k, rep, scale, input_type, part, measured,
                     command_line, binary_sha256, input_fingerprints,
                     cache_state, thermal, now=None,
                     probe_output_json=None,
                     aggregate_worker_busy_nanos=None, context=False,
                     **extra):
    """One evidence record carrying every provenance field the memo needs.

    `wall_s` and `peak_rss_bytes` are both recorded because
    bench.reduce_arm reads exactly those two keys (bench.py:1319-1340).
    """
    record = {
        "arm": arm,
        "k": k,
        "rep": rep,
        "scale": scale,
        "input_type": input_type,
        "part": part,
        "wall_s": measured["wall_s"],
        "peak_rss_bytes": measured["peak_rss_bytes"],
        "peak_footprint_bytes": measured.get("peak_footprint_bytes"),
        "peak_bytes": measured.get("peak_bytes"),
        "cache_state": cache_state,
        "command_line": [str(arg) for arg in command_line],
        "binary_sha256": binary_sha256,
        "input_sha256s": [item["sha256"] for item in input_fingerprints],
        "input_paths": [item["path"] for item in input_fingerprints],
        "thermal": thermal,
        "created": (now or _now_iso)(),
    }
    if probe_output_json is not None:
        record["probe_output_json"] = probe_output_json
    if aggregate_worker_busy_nanos is not None:
        record["aggregate_worker_busy_nanos"] = int(
            aggregate_worker_busy_nanos)
    if context:
        record["context"] = True
        record["excluded"] = True
    record.update(extra)
    return record


def _build_ctx(scale, parts, inputs, input_fingerprints, stock_binary,
               stock_provenance, probe_binaries, probe_provenance, out_dir,
               context_parts=(), cooldown=True, context=False,
               run_measured=None, run_devnull=None, run_with_stdout=None,
               stats_fn=None, cache_state=None, thermal=None, delete=None,
               now=None, sleep=None, threads=EXTRACTOR_COUNT):
    """The per-run context: real seams by default, injectable for unit tests."""
    return {
        "scale": scale,
        "parts": tuple(parts),
        "context_parts": tuple(context_parts),
        "inputs": inputs,
        "fingerprints": input_fingerprints,
        "stock_binary": str(stock_binary),
        "stock_provenance": stock_provenance,
        "probe_binaries": probe_binaries,
        "probe_provenance": probe_provenance,
        "out_dir": Path(out_dir),
        "threads": int(threads),
        "cooldown": bool(cooldown),
        "context": bool(context),
        "run_measured": measured_run if run_measured is None else run_measured,
        "run_devnull": (_measured_run_devnull if run_devnull is None
                        else run_devnull),
        "run_with_stdout": (_measured_run_capture if run_with_stdout is None
                            else run_with_stdout),
        "stats": bench_stats if stats_fn is None else stats_fn,
        "cache_state": (attempt_cache_purge if cache_state is None
                        else cache_state),
        "thermal": read_thermal if thermal is None else thermal,
        "delete": _unlink_quiet if delete is None else delete,
        "now": _now_iso if now is None else now,
        "sleep": time.sleep if sleep is None else sleep,
    }


# --- arm builders ------------------------------------------------------------


def _pair_arm_records(arm, k, rep, ctx):
    """Arm A (gzip) / B (plain): stock CLI count over the pinned pair.

    D-08: every rep writes a `.rkdb` output to scratch via `-o` and the
    output is deleted immediately after the rep's stats are recorded — the
    wall stays comparable to the sort+write-inclusive v2.0 base.
    """
    input_type = "gzip" if arm == "A" else "plain"
    parts = ctx["parts"]
    paths = [ctx["inputs"][part][input_type] for part in parts]
    out_path = Path(ctx["out_dir"]) / f"arm-{arm}.k{k}.rep{rep}.rkdb"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    config = BenchmarkConfig(k=k, canonical=True, threads=ctx["threads"],
                             inputs=[str(path) for path in paths])
    argv = rustkmer_count_cmd(config, out_path, ctx["stock_binary"])
    cache_state = ctx["cache_state"]()
    measured, _stderr = ctx["run_measured"](argv)
    stats = ctx["stats"](out_path, ctx["stock_binary"])
    _guard_zero(f"arm {arm} k={k} rep={rep}",
                stats["unique_kmers"], stats["total_kmers"],
                "the stock count run")
    output_bytes = out_path.stat().st_size
    ctx["delete"](out_path)
    record = build_run_record(
        arm=arm, k=k, rep=rep, scale=ctx["scale"], input_type=input_type,
        part=None, measured=measured, command_line=argv,
        binary_sha256=ctx["stock_provenance"]["binary"]["sha256"],
        input_fingerprints=[ctx["fingerprints"][part][input_type]
                            for part in parts],
        cache_state=cache_state, thermal=ctx["thermal"](), now=ctx["now"],
        output_bytes=output_bytes, distinct_kmers=stats["unique_kmers"],
        total_kmers=stats["total_kmers"])
    return [record]


def _control_records(k, rep, ctx):
    """Pure-read control: `cat` BOTH pinned-pair parts of ONE input type.

    One record per input type per rep; the child's stdout goes to DEVNULL,
    so each invocation reads the same byte volume the pair arms read and the
    read-delta correction is like-for-like (Pitfall 3).
    """
    records = []
    for input_type in ("gzip", "plain"):
        parts = ctx["parts"]
        paths = [ctx["inputs"][part][input_type] for part in parts]
        argv = ["cat", *[str(path) for path in paths]]
        cache_state = ctx["cache_state"]()
        measured = ctx["run_devnull"](argv)
        records.append(build_run_record(
            arm="control", k=k, rep=rep, scale=ctx["scale"],
            input_type=input_type, part=None, measured=measured,
            command_line=argv, binary_sha256=ctx["cat_sha256"],
            input_fingerprints=[ctx["fingerprints"][part][input_type]
                                for part in parts],
            cache_state=cache_state, thermal=ctx["thermal"](),
            now=ctx["now"], pair_parts=list(parts)))
    return records


def _probe_instrument_for_k(k):
    """Arm C's instrument: the committed k=21 probe or the materialized k=31."""
    if k == 21:
        return "engine_probe_k21"
    if k == 31:
        return "engine_probe_k31"
    raise ValueError(f"no arm-C instrument for k={k} (GATE_KS={GATE_KS})")


def _arm_c_records(k, rep, ctx):
    """Arm C: the profiling probe on each part x both input types.

    The committed k=21 probe takes no k argument (its k is a build-time
    constant, recorded from the instrument registry); the materialized k=31
    probe takes k from argv and asserts it into its JSON.
    """
    instrument = _probe_instrument_for_k(k)
    spec = PROBE_INSTRUMENTS[instrument]
    binary = ctx["probe_binaries"][instrument]
    provenance = ctx["probe_provenance"][instrument]
    records = []
    for part in ctx["parts"]:
        for input_type in ("gzip", "plain"):
            path = ctx["inputs"][part][input_type]
            argv = [str(binary), str(path), "fastq", str(ctx["threads"])]
            if spec["k_argv"]:
                argv.append(str(k))
            cache_state = ctx["cache_state"]()
            measured, stdout = ctx["run_with_stdout"](argv)
            probe_document = parse_probe_output(stdout, k, instrument)
            busy_total = sum(
                worker["busy_nanos"] for worker in probe_document["workers"])
            records.append(build_run_record(
                arm="C", k=k, rep=rep, scale=ctx["scale"],
                input_type=input_type, part=part, measured=measured,
                command_line=argv,
                binary_sha256=provenance["binary"]["sha256"],
                input_fingerprints=[ctx["fingerprints"][part][input_type]],
                cache_state=cache_state, thermal=ctx["thermal"](),
                now=ctx["now"], probe_output_json=probe_document,
                aggregate_worker_busy_nanos=busy_total,
                instrument=instrument, context=ctx["context"]))
    return records


def _arm_d_records(k, rep, ctx):
    """Arm D: the null consumer on each plain part (read + parse + extract)."""
    binary = ctx["probe_binaries"]["null_consumer"]
    provenance = ctx["probe_provenance"]["null_consumer"]
    records = []
    for part in ctx["parts"]:
        path = ctx["inputs"][part]["plain"]
        argv = [str(binary), str(path), str(k)]
        cache_state = ctx["cache_state"]()
        measured, stdout = ctx["run_with_stdout"](argv)
        probe_document = parse_probe_output(stdout, k, "null_consumer")
        records.append(build_run_record(
            arm="D", k=k, rep=rep, scale=ctx["scale"], input_type="plain",
            part=part, measured=measured, command_line=argv,
            binary_sha256=provenance["binary"]["sha256"],
            input_fingerprints=[ctx["fingerprints"][part]["plain"]],
            cache_state=cache_state, thermal=ctx["thermal"](),
            now=ctx["now"], probe_output_json=probe_document,
            instrument="null_consumer", context=ctx["context"]))
    return records


def _execute_arm(arm, k, rep, ctx):
    """Dispatch one gate-arm execution to its builder."""
    if arm in ("A", "B"):
        return _pair_arm_records(arm, k, rep, ctx)
    if arm == "control":
        return _control_records(k, rep, ctx)
    if arm == "C":
        return _arm_c_records(k, rep, ctx)
    if arm == "D":
        return _arm_d_records(k, rep, ctx)
    raise ValueError(f"unknown gate arm {arm!r}")


# --- rehearsal (tracer path) -------------------------------------------------


def _write_rehearsal_fixtures(fixtures_dir, parts=PINNED_PAIR,
                              records=2000, length=150, seed=4242):
    """Deterministic fixture-scale pinned pair: plain FASTQ + gzip, seeded.

    The gzip container is written with mtime=0 so the fixture bytes (and
    therefore the recorded input fingerprints) are reproducible.
    """
    fixtures_dir = Path(fixtures_dir)
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    fixtures = {}
    for part in parts:
        sequences = [
            "".join(rng.choice("ACGT") for _ in range(length))
            for _ in range(records)
        ]
        text = "".join(
            f"@phase13_{part}_{index}\n{sequence}\n+\n"
            f"{'I' * length}\n"
            for index, sequence in enumerate(sequences))
        plain = fixtures_dir / f"{part}.fq"
        plain.write_text(text, encoding="utf-8", newline="\n")
        gz_path = fixtures_dir / f"{part}.fq.gz"
        with open(gz_path, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                               mtime=0) as gz_handle:
                gz_handle.write(text.encode("utf-8"))
        fixtures[part] = {"plain": plain, "gzip": gz_path}
    return fixtures


def _rehearsal_ctx(args, scratch):
    """Build the fixture-scale context (probes materialized + built)."""
    stock = Path(args.rustkmer)
    _cargo_build(["cargo", "build", "--release", "--locked"], cwd=REPO_ROOT)
    _cargo_build(["cargo", "build", "--release", "--locked",
                  "--features", "profiling", "--example", "engine_probe"],
                 cwd=REPO_ROOT)
    probes = materialize_probe_binaries(scratch / "probes", REPO_ROOT)
    fixtures = _write_rehearsal_fixtures(scratch / "fixtures")
    inputs = {part: {"gzip": entry["gzip"], "plain": entry["plain"]}
              for part, entry in fixtures.items()}
    fingerprints = {
        part: {kind: fingerprint(path) for kind, path in entry.items()}
        for part, entry in inputs.items()
    }
    k21_provenance = binary_provenance(COMMITTED_K21_PROBE, "release")
    ctx = _build_ctx(
        scale="rehearsal", parts=PINNED_PAIR, inputs=inputs,
        input_fingerprints=fingerprints, stock_binary=stock,
        stock_provenance=binary_provenance(stock, "release"),
        probe_binaries={
            "engine_probe_k21": COMMITTED_K21_PROBE,
            "engine_probe_k31": probes["engine_probe_k31"]["binary"],
            "null_consumer": probes["null_consumer"]["binary"],
        },
        probe_provenance={
            "engine_probe_k21": k21_provenance,
            "engine_probe_k31": probes["engine_probe_k31"]["provenance"],
            "null_consumer": probes["null_consumer"]["provenance"],
        },
        out_dir=scratch / "out", cooldown=False)
    ctx["cat_sha256"] = fingerprint(shutil.which("cat") or "/bin/cat")["sha256"]
    return ctx


def run_rehearsal(args):
    """Prove the whole chain end-to-end at fixture scale (the tracer).

    Materialize probes -> measure all arms + control -> evidence doc ->
    attribution -> predicted win -> decision -> memo text, all in a scratch
    tree under PROBE_SCRATCH_ROOT. Every record carries scale='rehearsal', so
    the committed memo derivation (run_memo) structurally cannot consume it.
    """
    scratch = refuse_repo_root(Path(PROBE_SCRATCH_ROOT) / "rehearsal")
    scratch.mkdir(parents=True, exist_ok=True)
    ctx = _rehearsal_ctx(args, scratch)
    doc_path = scratch / "13-ATTRIBUTION.rehearsal.json"
    doc = new_doc()
    doc["provenance"] = ctx["stock_provenance"]
    doc["fingerprint_gate"] = fingerprint_gate(ctx["stock_provenance"])
    doc["rehearsal"] = True
    schedule = rotation_schedule(GATE_ARMS, 1)
    for arm in schedule[0]:
        for k in GATE_KS:
            for record in _execute_arm(arm, k, 1, ctx):
                upsert_run(doc, record)
                write_doc(doc_path, doc)
    compute_gate_blocks(doc)
    validate_provenance(doc)
    write_doc(doc_path, doc)
    memo_path = scratch / "13-GATE-MEMO.rehearsal.md"
    memo_path.write_text(render_memo_text(doc), encoding="utf-8")
    print(f"[phase13] rehearsal evidence: {doc_path}")
    print(f"[phase13] rehearsal memo:     {memo_path}")
    return scratch


# --- full-scale stage: prep --------------------------------------------------


def plain_part_path(part, plain_dir=None):
    """The pinned plain-part filename rule: part_001.fq.gz -> <part>.fq."""
    directory = Path(plain_dir) if plain_dir is not None else PLAIN_INPUTS_DIR
    return directory / f"{part}{PLAIN_SUFFIX}"


def discover_gzip_parts(data_dir=None):
    """The six dataset gzip parts, keyed by their pinned part token."""
    data_dir = Path(data_dir) if data_dir is not None else DATASET_DIR
    if not data_dir.is_dir():
        raise ValueError(f"dataset directory not found: {data_dir}")
    found = {}
    for path in sorted(data_dir.iterdir()):
        if not path.is_file() or not path.name.endswith(".fq.gz"):
            continue
        match = re.search(r"(part_\d+)", path.name)
        if match:
            found[match.group(1)] = path
    if sorted(found) != list(EXPECTED_PARTS):
        raise ValueError(
            f"dataset parts must be exactly {list(EXPECTED_PARTS)}, got "
            f"{sorted(found)} under {data_dir}")
    return {part: found[part] for part in EXPECTED_PARTS}


def _decompress_part(gz_path, target_path):
    """Stream one gzip part's bytes straight to its plain output path.

    The open output file is the child's stdout (merge_characterize
    `_run_fail_loud(..., stdout_path=...)` form) — the ~9.7 GB decompressed
    stream is never captured in memory. Returns the list-form argv.
    """
    argv = ["gunzip", "-c", str(gz_path)]
    _run_fail_loud(argv, stdout_path=str(target_path),
                   side_label=f"plain part decompression ({gz_path})")
    return argv


def _record_missing(record, key):
    """True when a record field is absent or empty (memo-derivation guard)."""
    if key not in record:
        return True
    value = record[key]
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, dict)) and not value:
        return True
    return False


def validate_memo_inputs(doc):
    """The three memo-derivation refusals, each with its own message.

    1. incomplete gate matrix (any gate arm x k with fewer than GATE_REPS
       full-scale reps);
    2. a record whose scale is not 'full' (rehearsal numbers never gate);
    3. a record missing any required provenance field.
    """
    gate = _gate_records(doc)
    if not gate:
        raise ValueError(
            "memo derivation: the evidence document carries no gate run "
            "records — refusing to derive a decision from nothing")
    for record in gate:
        missing = [key for key in REQUIRED_RECORD_KEYS
                   if _record_missing(record, key)]
        if record.get("arm") in ("C", "D") and record.get("part") is None:
            missing.append("part")
        if missing:
            raise ValueError(
                "memo derivation: record "
                f"arm={record.get('arm')!r} k={record.get('k')!r} "
                f"rep={record.get('rep')!r} part={record.get('part')!r} "
                f"input_type={record.get('input_type')!r} is missing required "
                f"provenance fields {missing!r} — cite only complete runs")
    non_full = [record for record in gate if record.get("scale") != "full"]
    if non_full:
        offender = non_full[0]
        raise ValueError(
            "memo derivation: record "
            f"arm={offender.get('arm')!r} k={offender.get('k')!r} "
            f"rep={offender.get('rep')!r} part={offender.get('part')!r} "
            f"carries scale={offender.get('scale')!r} — the committed memo "
            "derives only from scale='full' records (rehearsal numbers never "
            "feed the gate)")
    for arm in GATE_ARMS:
        for k in GATE_KS:
            reps = {record.get("rep") for record in gate
                    if record.get("arm") == arm and record.get("k") == k}
            if len(reps) < GATE_REPS:
                raise ValueError(
                    "memo derivation: incomplete gate matrix — arm "
                    f"{arm} k={k} carries {len(reps)} full-scale reps "
                    f"(need {GATE_REPS}); refusing to compute a decision "
                    "from a partial session")
    return True


def run_prep(args, seams=None):
    """Full-scale prep: clean rebuild -> gate block -> disk check ->
    decompress all six parts (streamed) -> fingerprints -> probes.

    Structural order (D-10/T-13-03): the stock binary is rebuilt clean first,
    its provenance block (git_dirty false asserted) is stored BEFORE the gate
    block, and the disk arithmetic runs BEFORE any decompression.
    """
    seams = seams or {}
    provenance = seams.get("provenance", binary_provenance)
    build = seams.get("build", _cargo_build)
    free_bytes_fn = seams.get("free_bytes", free_bytes)
    ensure_free_fn = seams.get("ensure_free_space", ensure_free_space)
    decompress = seams.get("decompress", _decompress_part)
    fingerprint_fn = seams.get("fingerprint", fingerprint)
    materialize = seams.get("materialize_probes", materialize_probe_binaries)
    now = seams.get("now", _now_iso)

    results_path = Path(args.results)
    doc = load_doc(results_path) or new_doc()

    build(["cargo", "build", "--release", "--locked"], cwd=REPO_ROOT)
    stock_provenance = provenance(Path(args.rustkmer), "release")
    assert_clean_tree(stock_provenance)
    doc["provenance"] = stock_provenance
    gate_block = fingerprint_gate(stock_provenance)
    doc["fingerprint_gate"] = gate_block
    print(f"[phase13] fingerprint gate: current={gate_block['current_sha256']} "
          f"v2_0={gate_block['v2_0_sha256']} branch={gate_block['branch']}")

    data_dir = Path(args.data_dir)
    gzip_parts = discover_gzip_parts(data_dir)
    plain_dir = refuse_repo_root(Path(args.plain_dir))
    gzip_fingerprints = {part: fingerprint_fn(path)
                         for part, path in gzip_parts.items()}
    measured_gzip_bytes = sum(item["size_bytes"]
                              for item in gzip_fingerprints.values())
    required_free_bytes = (int(round(measured_gzip_bytes * PLAIN_SIZE_FACTOR))
                           + int(REQUIRED_TRANSIENT_BYTES))
    free_before = free_bytes_fn(data_dir)
    ensure_free_fn(data_dir, required_free_bytes / (1 << 30))
    print(f"[phase13] disk check: {free_before} bytes free, "
          f"{required_free_bytes} required")

    previous = {}
    for entry in (doc.get("prep") or {}).get("plain_inputs", []) or []:
        if isinstance(entry, dict) and entry.get("part"):
            previous[entry["part"]] = entry
    plain_inputs = []
    decompression_commands = []
    for part in EXPECTED_PARTS:
        target = plain_part_path(part, plain_dir)
        prior = previous.get(part)
        if (target.is_file() and isinstance(prior, dict)
                and prior.get("size_bytes") == target.stat().st_size
                and prior.get("sha256") == _sha256_file(target)):
            plain_inputs.append(prior)
            decompression_commands.append(prior.get("decompression_command"))
            print(f"[phase13] plain part {part}: re-verified, skipped")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        argv = decompress(gzip_parts[part], target)
        item = fingerprint_fn(target)
        plain_inputs.append({
            "part": part,
            "path": str(target),
            "size_bytes": item["size_bytes"],
            "sha256": item["sha256"],
            "decompression_command": [str(arg) for arg in argv],
        })
        decompression_commands.append([str(arg) for arg in argv])
        print(f"[phase13] plain part {part}: {item['size_bytes']} bytes")

    build(["cargo", "build", "--release", "--locked",
           "--features", "profiling", "--example", "engine_probe"],
          cwd=REPO_ROOT)
    k21_provenance = provenance(COMMITTED_K21_PROBE, "release")
    scratch_probes = materialize(PROBE_SCRATCH_ROOT / "session-probes",
                                 REPO_ROOT)
    probes = {
        "engine_probe_k21": {
            "provenance": k21_provenance,
            "k": PROBE_INSTRUMENTS["engine_probe_k21"]["k"],
            "k_source": PROBE_INSTRUMENTS["engine_probe_k21"]["k_source"],
        },
        "engine_probe_k31": {
            "provenance": scratch_probes["engine_probe_k31"]["provenance"],
            "k": PROBE_INSTRUMENTS["engine_probe_k31"]["k"],
            "k_source": PROBE_INSTRUMENTS["engine_probe_k31"]["k_source"],
        },
        "null_consumer": {
            "provenance": scratch_probes["null_consumer"]["provenance"],
            "k": PROBE_INSTRUMENTS["null_consumer"]["k"],
            "k_source": PROBE_INSTRUMENTS["null_consumer"]["k_source"],
        },
    }
    doc["prep"] = {
        "disk_check_passed": True,
        "free_bytes_before_decompression": int(free_before),
        "required_free_bytes": int(required_free_bytes),
        "decompression_commands": decompression_commands,
        "gzip_inputs": [gzip_fingerprints[part] for part in EXPECTED_PARTS],
        "plain_inputs": plain_inputs,
        "probes": probes,
        "probe_scratch_root": str(PROBE_SCRATCH_ROOT),
        "created": now(),
    }
    validate_provenance(doc)
    write_doc(results_path, doc)
    print(f"[phase13] prep complete -> {results_path}")
    return EXIT_OK


# --- full-scale stage: measure ----------------------------------------------


def _full_scale_ctx(args, doc):
    """Build the full-scale context from the recorded prep block."""
    prep = doc.get("prep") or {}
    if not prep:
        raise ValueError(
            "measure requires the prep block (run --stage prep first) — the "
            "structural order is prep -> measure -> memo")
    data_dir = Path(args.data_dir)
    gzip_parts = discover_gzip_parts(data_dir)
    plain_dir = refuse_repo_root(Path(args.plain_dir))
    inputs = {}
    fingerprints = {}
    recorded_plain = {entry.get("part"): entry
                      for entry in prep.get("plain_inputs") or []}
    for part in EXPECTED_PARTS:
        plain_path = plain_part_path(part, plain_dir)
        if not plain_path.is_file():
            raise ValueError(
                f"plain input missing for {part}: {plain_path} — run "
                "--stage prep (decompression) before measure")
        inputs[part] = {"gzip": gzip_parts[part], "plain": plain_path}
        fingerprints[part] = {
            "gzip": fingerprint(gzip_parts[part]),
            "plain": fingerprint(plain_path),
        }
        recorded = recorded_plain.get(part) or {}
        if recorded.get("sha256") and \
                recorded["sha256"] != fingerprints[part]["plain"]["sha256"]:
            raise ValueError(
                f"plain input {part} sha256 changed since prep "
                f"({fingerprints[part]['plain']['sha256']} vs recorded "
                f"{recorded['sha256']}) — refusing to measure against an "
                "unrecorded input")
    stock = Path(args.rustkmer)
    stock_provenance = doc.get("provenance") or {}
    recorded_sha = (stock_provenance.get("binary") or {}).get("sha256")
    if recorded_sha and fingerprint(stock)["sha256"] != recorded_sha:
        raise ValueError(
            f"stock binary {stock} changed since prep (sha256 "
            f"{fingerprint(stock)['sha256']} vs recorded {recorded_sha}) — "
            "rebuild/repair and re-run prep; the gate block would be stale")
    probes = prep.get("probes") or {}
    probe_binaries = {}
    probe_provenance = {}
    for instrument in PROBE_INSTRUMENTS:
        entry = probes.get(instrument)
        if not isinstance(entry, dict) or not entry.get("provenance"):
            raise ValueError(
                f"prep block carries no provenance for probe {instrument!r} "
                "— run --stage prep first")
        probe_provenance[instrument] = entry["provenance"]
        probe_binaries[instrument] = Path(
            entry["provenance"]["binary"]["path"])
    context_parts = tuple(part for part in EXPECTED_PARTS
                          if part not in PINNED_PAIR)
    ctx = _build_ctx(
        scale="full", parts=PINNED_PAIR, inputs=inputs,
        input_fingerprints=fingerprints, stock_binary=stock,
        stock_provenance=stock_provenance,
        probe_binaries=probe_binaries, probe_provenance=probe_provenance,
        out_dir=PROBE_SCRATCH_ROOT / "session-out",
        context_parts=context_parts, cooldown=True)
    ctx["cat_sha256"] = fingerprint(shutil.which("cat") or "/bin/cat")["sha256"]
    return ctx


def run_measure(args, ctx_factory=None):
    """Full-scale measure: the counterbalanced A/B/C/D + control matrix,
    per-rep output deletion, crash-safe incremental writes, then the context
    matrix, the gate math and the decision.

    Every probe-nanos term reduces through the input-type-scoped
    `_pair_sum_median`; arm walls reduce through `bench.reduce_arm`.
    """
    results_path = Path(args.results)
    doc = load_doc(results_path)
    if doc is None:
        raise ValueError(
            f"no evidence document at {results_path} — run --stage prep "
            "first")
    if not doc.get("prep"):
        raise ValueError(
            "measure requires the prep block in the evidence document — the "
            "structural order is prep -> measure -> memo")
    validate_provenance(doc)
    ctx = (ctx_factory(args, doc) if ctx_factory is not None
           else _full_scale_ctx(args, doc))

    schedule = rotation_schedule(GATE_ARMS, GATE_REPS)
    for rep, order in enumerate(schedule, start=1):
        for arm in order:
            for k in GATE_KS:
                print(f"[phase13] rep {rep} arm {arm} k={k}")
                for record in _execute_arm(arm, k, rep, ctx):
                    upsert_run(doc, record)
                    write_doc(results_path, doc)
                if ctx["cooldown"]:
                    ctx["sleep"](DEFAULT_COOLDOWN_S)

    context_ctx = dict(ctx, context=True, parts=())
    for k in GATE_KS:
        for part in ctx["context_parts"]:
            part_ctx = dict(context_ctx, parts=(part,))
            for record in _arm_c_records(k, 1, part_ctx):
                upsert_run(doc, record)
                write_doc(results_path, doc)
        print(f"[phase13] context matrix k={k} recorded (excluded)")

    compute_gate_blocks(doc)
    validate_provenance(doc)
    write_doc(results_path, doc)
    decision = doc["predicted_win"]["decision"]
    print(f"[phase13] attribution + predicted win computed; decision "
          f"{decision} (bar {D3_BAR_FULL_WALL_IMPROVEMENT_PCT}) -> "
          f"{results_path}")
    return EXIT_OK


# --- full-scale stage: memo --------------------------------------------------


def run_memo(args):
    """Render the committed memo from complete full-scale evidence only.

    Refuses partial evidence (missing attribution/predicted_win blocks), a
    non-full record, an incomplete matrix, and an invalid provenance block.
    Proves byte-identical re-render, then publishes the memo + proof document
    atomically. Both GO and NO-GO exit 0 (a recorded decision is a valid
    result); only infrastructure failures exit 2.
    """
    results_path = Path(args.results)
    doc = load_doc(results_path)
    if doc is None:
        raise ValueError(
            f"no evidence document at {results_path} — nothing to render")
    if not (doc.get("attribution") or {}).get("per_k") or \
            not (doc.get("predicted_win") or {}).get("per_k"):
        raise ValueError(
            "memo requires BOTH the attribution and predicted_win blocks — "
            "the memo is never rendered from partial evidence")
    validate_provenance(doc)
    validate_memo_inputs(doc)

    text = render_memo_text(doc)
    text_again = render_memo_text(doc)
    if text != text_again:
        raise RuntimeError(
            "render: re-render is not byte-identical — the renderer is "
            "carrying nondeterminism (a clock read, iteration order, or an "
            "unstable environment read); refusing to publish a proof")
    _assert_memo_contract(text, doc)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest_again = hashlib.sha256(text_again.encode("utf-8")).hexdigest()

    out_path = Path(args.out) if args.out else DEFAULT_MEMO
    proof_path = Path(args.proof_out) if args.proof_out else DEFAULT_PROOF
    proof_doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_RENDER_PROOF,
        "phase": PHASE,
        "created": _now_iso(),
        "byte_identical": True,
        "first_render_sha256": digest,
        "second_render_sha256": digest_again,
        "decision": doc["predicted_win"]["decision"],
        "bar_pct": doc["predicted_win"].get(
            "bar_pct", D3_BAR_FULL_WALL_IMPROVEMENT_PCT),
        "evidence": fingerprint(results_path),
    }
    validate_provenance(doc)
    publish_atomic([
        (out_path, text),
        (proof_path, json.dumps(proof_doc, indent=2, sort_keys=True) + "\n"),
    ])
    print(f"[phase13] memo published: {out_path}")
    print(f"[phase13] render proof:   {proof_path}")
    print(f"[phase13] decision: {proof_doc['decision']} "
          f"(bar {proof_doc['bar_pct']})")
    return EXIT_OK


# --- CLI ---------------------------------------------------------------------


def build_parser():
    """The driver CLI: rehearsal (tracer) + the three full-scale stages."""
    parser = argparse.ArgumentParser(
        prog="phase13.py",
        description="Phase-13 producer-attribution driver (PEXT-01/PEXT-02): "
                    "probe materialization, measured arms A-D + control, "
                    "evidence JSON, D-09 attribution, the two-ceiling "
                    "predicted-win model, the D-05 gate, and the D-02 memo.")
    parser.add_argument("--rehearsal", action="store_true",
                        help="prove the whole chain at fixture scale under "
                             "PROBE_SCRATCH_ROOT (rehearsal numbers never "
                             "feed the gate)")
    parser.add_argument("--stage", choices=("prep", "measure", "memo"),
                        default=None,
                        help="run one full-scale stage (prep -> measure -> "
                             "memo)")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS),
                        help="evidence JSON path")
    parser.add_argument("--out", default=str(DEFAULT_MEMO),
                        help="memo output path (memo stage)")
    parser.add_argument("--proof-out", default=str(DEFAULT_PROOF),
                        help="render-proof JSON path (memo stage)")
    parser.add_argument("--scratch", default=str(PROBE_SCRATCH_ROOT),
                        help="probe scratch root (must be outside the repo)")
    parser.add_argument("--rustkmer", default=str(DEFAULT_RUSTKMER),
                        help="rustkmer RELEASE binary path")
    parser.add_argument("--data-dir", default=str(DATASET_DIR),
                        help="split-parts source directory")
    parser.add_argument("--plain-dir", default=str(PLAIN_INPUTS_DIR),
                        help="pre-decompressed plain FASTQ directory "
                             "(outside the repo; deleted post-memo)")
    parser.add_argument("--generate-lock-fixtures", action="store_true",
                        help="one-time maintenance: regenerate the committed "
                             "probe Cargo.lock fixtures (offline "
                             "generate-lockfile; never a measurement run)")
    return parser


def main(argv=None):
    """Run the driver; invalid inputs and infra failures exit 2."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.rehearsal or args.stage or args.generate_lock_fixtures):
        parser.error("nothing to do: pass --rehearsal, --stage "
                     "prep|measure|memo, or --generate-lock-fixtures")
    try:
        if args.generate_lock_fixtures:
            written = generate_lock_fixtures()
            for probe, path in sorted(written.items()):
                print(f"[phase13] lock fixture {probe}: {path}")
            return EXIT_OK
        if args.rehearsal:
            scratch = run_rehearsal(args)
            print(f"[phase13] rehearsal complete: {scratch}")
            return EXIT_OK
        handlers = {"prep": run_prep, "measure": run_measure,
                    "memo": run_memo}
        return handlers[args.stage](args)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(EXIT_INVALID, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    main()
