#!/usr/bin/env python3
"""rustkmer benchmark harness core (BENCH-01/02/03/04).

Measures `rustkmer count` and `rustkmer merge` wall-clock and peak RSS via
/usr/bin/time, emits a schema-versioned results.json, and sanity-asserts that
every measured run actually counted k-mers (RESEARCH Pitfall 1: a silent
zero-count success must abort the harness).

BENCH-02 fairness lives here too: one BenchmarkConfig derives both tools'
matched command lines, a --parity-only gate proves the counts equal before
any timing is trusted, and --reps >= 2 runs the interleaved counterbalanced
protocol with honestly-recorded per-rep cache_state, medians, and CV%.

04-04 milestone tooling: --merge-input provisions the second slice from a
second gz input (the r1/r2 merge arrangement), and --skip-merge keeps a run
to the counting comparison — the full-scale runs measure counting only;
merge wall/RSS is measured at slice scale (plan 04-04 must_haves).

--render-report (04-04 Task 3) is the ONLY writer of the milestone report's
numbers: it reads committed results JSONs and emits Markdown with zero
measurement literals of its own and no clock, so re-rendering reproduces a
byte-identical file and any hand-edit is detectable (threat T-04-07).

Every headline number comes from a --release binary (never a debug build) and
from OS rusage accounting (never a harness-internal clock). Python 3.10+
stdlib only — no third-party imports, no pip installs.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

HERE = Path(__file__).resolve().parent            # scripts/bench/
REPO_ROOT = HERE.parent.parent                    # repo root
GEN_SYNTHETIC = HERE / "gen_synthetic.py"
DEFAULT_SCRATCH = HERE / "scratch"

# Synthetic provisioning constants (two disjoint seeded inputs per run).
SYNTHETIC_LENGTH = 150
SEED_A = 42
SEED_B = 1337

# --- BENCH-02 fair-comparison constants (04-02) ------------------------------
DEFAULT_RUSTKMER = "target/release/rustkmer"
DEFAULT_HASH_SIZE = "10G"      # generous -s: undersizing silently penalizes
                               # the comparator (Pitfall 4); recorded in results
DEFAULT_COOLDOWN_S = 5         # thermal gap between measured runs (Pitfall 5)
DEFAULT_DISK_FLOOR_GB = 150    # Pitfall 8: full-run .rkdb artifacts alone can
                               # reach 55-60 GB per database + merge scratch
CV_WARNING_THRESHOLD_PCT = 10.0
DISK_FLOOR_EXIT = 3

# --- /usr/bin/time output parsing (dual-platform, units-pinned) -------------
# macOS BSD `time -l` reports peak RSS in BYTES (verified on this repo's dev
# host):            "  60391424  maximum resident set size"
MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")
# macOS `time -l` also reports the DIRECT CHILD's footprint in BYTES:
#                   "             1294648  peak memory footprint"
# For a pipeline arm this describes only the shell (~1 MB), while the RSS
# line aggregates the waited-for child — the two lines must both be parsed
# and the honest peak is max(rss, footprint) (10-RESEARCH Pitfall 5).
MAC_FOOTPRINT = re.compile(r"^\s*(\d+)\s+peak memory footprint\s*$")
# Linux GNU `time -v` reports peak RSS in KBYTES and must be scaled x1024:
#                   "Maximum resident set size (kbytes): 62384"
LIN_RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")
# macOS real line (seconds float; m:ss.cc shape past one minute):
#                   "        0.05 real         0.00 user         0.00 sys"
MAC_REAL = re.compile(r"^\s*([0-9:.]+)\s+real\b")
# Linux elapsed line (both documented shapes):
#                   "\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:05.12"
LIN_ELAPSED = re.compile(
    r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)")


def hms_to_seconds(text):
    """Parse 'ss.ff', 'm:ss.ff', or 'h:mm:ss' into seconds (float).

    '0:05.12' -> 5.12; '1:23:45' -> 5025.0. Raises ValueError on garbage.
    """
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"unparseable elapsed time: {text!r}")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"unparseable elapsed time: {text!r}") from None
    seconds = 0.0
    for n in nums:
        seconds = seconds * 60 + n
    return seconds


def parse_time_output(stderr_text, plat):
    """Parse /usr/bin/time stderr into wall and honest peak-memory fields.

    Returns four keys:
      wall_s                float seconds
      peak_rss_bytes        int bytes (darwin: raw; linux: kbytes x 1024)
      peak_footprint_bytes  int bytes on darwin, None on linux
      peak_bytes            max(peak_rss_bytes, peak_footprint_bytes-or-rss)

    The project convention is `max(rss, phys_footprint)` (10-CONTEXT). macOS
    `time -l` prints BOTH `maximum resident set size` (the waited-for child
    pipeline's high-water mark) and `peak memory footprint` (the direct child
    only — a pipeline shell reports ~1 MB). Recording only RSS can miss
    compressed-memory peaks on direct children; recording only footprint
    under-reports pipeline arms by orders of magnitude. Hence the max.

    darwin: RSS taken as-is (already bytes); a missing footprint line raises
    (format drift). linux: RSS scaled kbytes x 1024; `time -v` has no
    footprint line, so peak_footprint_bytes is None and peak_bytes equals
    the RSS.

    Raises ValueError when a required line is absent or unparseable — never
    best-effort (a 1024x units error or a format drift here corrupts every
    downstream number; RESEARCH Pitfall 2 / threat T-04-01).
    """
    if plat == "darwin":
        rss_re, rss_scale, wall_re = MAC_RSS, 1, MAC_REAL
        footprint_re = MAC_FOOTPRINT
    elif plat == "linux":
        rss_re, rss_scale, wall_re = LIN_RSS, 1024, LIN_ELAPSED
        footprint_re = None
    else:
        raise ValueError(f"unsupported platform: {plat!r}")

    wall_s = None
    peak_rss_bytes = None
    peak_footprint_bytes = None
    for line in stderr_text.splitlines():
        if peak_rss_bytes is None:
            m = rss_re.search(line)
            if m:
                peak_rss_bytes = int(m.group(1)) * rss_scale
        if footprint_re is not None and peak_footprint_bytes is None:
            m = footprint_re.search(line)
            if m:
                peak_footprint_bytes = int(m.group(1))
        if wall_s is None:
            m = wall_re.search(line)
            if m:
                wall_s = hms_to_seconds(m.group(1))
    if peak_rss_bytes is None:
        raise ValueError(
            f"no parsable peak-RSS line for platform {plat!r} — format drift?")
    if footprint_re is not None and peak_footprint_bytes is None:
        raise ValueError(
            f"no parsable peak-footprint line for platform {plat!r} — "
            f"format drift?")
    if wall_s is None:
        raise ValueError(
            f"no parsable wall-clock line for platform {plat!r} — format drift?")
    peak_bytes = (peak_rss_bytes if peak_footprint_bytes is None
                  else max(peak_rss_bytes, peak_footprint_bytes))
    return {"wall_s": wall_s, "peak_rss_bytes": peak_rss_bytes,
            "peak_footprint_bytes": peak_footprint_bytes,
            "peak_bytes": peak_bytes}


def measure(argv):
    """Run argv (LIST form, no shell) under /usr/bin/time; return the rep dict.

    A non-zero child exit raises RuntimeError carrying the trailing stderr.
    """
    plat = sys.platform
    time_flag = "-l" if plat == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag, *argv],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return parse_time_output(proc.stderr, plat)


# --- BENCH-02 fairness matrix: one config derives both tools (04-02) ---------
# T-04-03: the jellyfish gz arm is the ONLY place a shell string is assembled;
# every path entering it is screened by validate_path against a strict
# character allowlist first. All other invocations stay list-form (no shell).
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9./_-]+$")
HASH_SIZE_RE = re.compile(r"^\d+[KMG]?$")
DECOMPRESSOR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 -]*$")


def default_decompressor(platform_str=sys.platform):
    """gzcat on darwin, gunzip -c otherwise — never macOS zcat (Pitfall 1)."""
    return "gzcat" if platform_str == "darwin" else "gunzip -c"


@dataclasses.dataclass(frozen=True)
class BenchmarkConfig:
    """Every knob for BOTH tools' count commands — the fairness matrix.

    One config derives rustkmer's and jellyfish's command lines so the two
    cannot drift: k mirrors -m, canonical mirrors -C, threads mirror
    --threads/-t (identical literals), hash_size is jellyfish's generous -s,
    and gz inputs reach jellyfish only through the decompressor pipe while
    rustkmer reads them natively (decompression counted for BOTH arms).
    """

    k: int
    canonical: bool = True
    threads: int = 1
    hash_size: str = DEFAULT_HASH_SIZE
    inputs: list = dataclasses.field(default_factory=list)
    decompressor: str = dataclasses.field(default_factory=default_decompressor)


def validate_path(path):
    """T-04-03 mitigation: screen a path before it enters any shell string.

    Accepts only characters within letters, digits, dot, slash, underscore,
    and hyphen; anything else (spaces, metacharacters, $()/` forms) raises
    ValueError naming the offending path. Returns the path as a string.
    """
    text = str(path)
    if not text:
        raise ValueError("path rejected (empty)")
    if not SAFE_PATH_RE.match(text):
        raise ValueError(f"path rejected (unsafe characters): {text!r}")
    return text


def rustkmer_count_cmd(cfg, out, rustkmer=DEFAULT_RUSTKMER):
    """rustkmer count argv derived from one BenchmarkConfig (list form).

    Inputs pass via -i (num_args = 1.., per src/cli/args.rs) — NOT as
    positional arguments. List-form subprocess with no shell: paths cannot
    inject here, so metacharacter screening is scoped to the sh -c arm.
    """
    argv = [str(rustkmer), "count", "-k", str(cfg.k)]
    if cfg.canonical:
        argv.append("-C")
    argv += ["--threads", str(cfg.threads), "-o", str(out),
             "-i", *[str(p) for p in cfg.inputs]]
    return argv


def jellyfish_count_cmd(cfg, out):
    """jellyfish count argv derived from the same BenchmarkConfig.

    Plain inputs: direct path arguments (list form — no shell). Any gz
    input: ONE sh -c pipeline (decompressor | jellyfish count ... /dev/stdin),
    the only shell string the harness ever assembles, built solely from
    validate_path-screened paths and harness constants (T-04-03). The pipe
    exists because jellyfish aborts on .gz path arguments (Pitfall 3); it
    keeps decompression INSIDE jellyfish's measured wall-clock, mirroring
    rustkmer's native gz reading.
    """
    if not HASH_SIZE_RE.match(str(cfg.hash_size)):
        raise ValueError(f"hash_size rejected (unsafe characters): "
                         f"{cfg.hash_size!r}")
    if not DECOMPRESSOR_RE.match(str(cfg.decompressor)):
        raise ValueError(f"decompressor rejected (unsafe characters): "
                         f"{cfg.decompressor!r}")
    inputs = [validate_path(p) for p in cfg.inputs]
    out_v = validate_path(out)
    common = ["-m", str(cfg.k), "-s", str(cfg.hash_size),
              "-t", str(cfg.threads)]
    if cfg.canonical:
        common.append("-C")
    common += ["-o", out_v]
    if any(p.endswith(".gz") for p in inputs):
        pipeline = (f"{cfg.decompressor} {' '.join(inputs)} | "
                    f"jellyfish count {' '.join(common)} /dev/stdin")
        return ["sh", "-c", pipeline]
    return ["jellyfish", "count", *common, *inputs]


def build_merge_cmd(rustkmer, out_db, input_dbs, num_threads=None):
    """rustkmer merge command (list form).

    num_threads (MBENCH-01): append --num-threads only when not None — the
    flag exists on the CLI (src/cli/args.rs Merge variant, default "0" =
    all cores); the merge-t1 arm pins a like-for-like single-thread run
    while the merge arm keeps the tool default.
    """
    argv = [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]
    if num_threads is not None:
        argv += ["--num-threads", str(num_threads)]
    return argv


def jellyfish_merge_cmd(out_jf, input_jfs):
    """jellyfish merge argv (list form): defaults only, never flag copying.

    Inputs are .jf files (never .gz), so there is NO sh -c pipeline here;
    every path still passes validate_path for T-04-03 consistency. Defaults
    only — SUM semantics; -m/-M/-j/-t/-s are NOT passed because in merge
    -m is MIN mode, a flag collision with count's mer length: flag strings
    are never copied between jellyfish subcommands. The count arms' byte-
    identical -m/-s/-C sets make the jellyfish-merge arm's hash-size
    equality precondition hold by construction (MBENCH-01).
    """
    out_v = validate_path(out_jf)
    inputs = [validate_path(p) for p in input_jfs]
    return ["jellyfish", "merge", "-o", out_v, *inputs]


def stats(db_path, rustkmer):
    """Return the parsed `rustkmer stats -f json` dict for db_path.

    Reads the snake_case serde keys (unique_kmers / total_kmers) — never the
    text-format prose labels.
    """
    proc = subprocess.run([str(rustkmer), "stats", "-f", "json", str(db_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"rustkmer stats failed rc={proc.returncode} on {db_path}: "
            f"{proc.stderr[-500:]}")
    return json.loads(proc.stdout)


def fingerprint(path):
    """{'path', 'size_bytes', 'sha256'} for one input file (threat T-04-02)."""
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"path": str(p), "size_bytes": p.stat().st_size,
            "sha256": h.hexdigest()}


# --- PROF-01 shared binary provenance (05-01) ---------------------------------
# Every Phase 5 results/evidence artifact records WHICH executable bytes
# produced it (threat T-05-02: a path string without a hash is not provenance).
# SCHEMA_VERSION stays 1 and validate_schema is untouched — it tolerates extra
# keys, so committed v1 baselines stay loadable; validate_provenance is the
# SEPARATE strict gate for new provenance-bearing artifacts.

PROVENANCE_KEYS = ("binary", "git_commit", "git_dirty", "build_profile",
                   "rust_toolchain", "platform", "created")
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_HEX_RE = re.compile(r"^[0-9a-f]{40}$")


def _provenance_tool_output(argv):
    """Run a provenance query (LIST form, no shell) from the repo root.

    Non-zero child exits raise RuntimeError with the trailing stderr — the
    fail-loud subprocess stance of measure(): an unattributable artifact must
    never gate, so a failed git/rustc query aborts instead of recording
    'unknown'.
    """
    proc = subprocess.run(argv, capture_output=True, text=True,
                          cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        raise RuntimeError(
            f"provenance query failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return proc.stdout


def binary_provenance(executable, build_profile):
    """Shared provenance builder for every results/evidence artifact.

    Hashes the ACTUAL executable bytes (never the command-line string), and
    records the repo HEAD (not the last commit touching this file — the
    artifact must attribute the tree the binary was built from), the dirty
    flag, the caller-supplied build profile, the Rust toolchain, and the
    platform. Raises on a missing executable or a failed git/rustc query.
    """
    if not isinstance(build_profile, str) or not build_profile.strip():
        raise ValueError("provenance: build_profile must be a non-empty string")
    exe = Path(executable)
    if not exe.is_file():
        found = shutil.which(str(executable))
        if found is None:
            raise RuntimeError(
                f"provenance: executable not found: {executable}")
        exe = Path(found)
    exe = exe.resolve()
    return {
        "binary": fingerprint(exe),
        "git_commit": _provenance_tool_output(
            ["git", "rev-parse", "HEAD"]).strip(),
        "git_dirty": bool(_provenance_tool_output(
            ["git", "status", "--porcelain"]).strip()),
        "build_profile": build_profile,
        "rust_toolchain": _provenance_tool_output(
            ["rustc", "--version"]).strip(),
        "platform": f"{sys.platform}-{platform.machine()}",
        "created": datetime.now(timezone.utc).isoformat(),
    }


def validate_provenance(doc):
    """Strict validator for provenance-bearing artifacts (PROF-01).

    SEPARATE from validate_schema by design: v1 baselines carry no provenance
    and must stay valid under validate_schema, while every NEW artifact must
    carry a complete, well-formed provenance block or it cannot gate
    (T-05-02). Raises ValueError naming the missing/bad field.
    """
    if not isinstance(doc, dict):
        raise ValueError("provenance: results must be a dict")
    prov = doc.get("provenance")
    if not isinstance(prov, dict):
        raise ValueError("provenance: missing provenance block")
    for key in PROVENANCE_KEYS:
        if key not in prov:
            raise ValueError(f"provenance: missing field {key!r}")
    binary = prov["binary"]
    if not isinstance(binary, dict):
        raise ValueError(
            "provenance: binary must be a dict (path/size_bytes/sha256)")
    for key in ("path", "size_bytes", "sha256"):
        if key not in binary:
            raise ValueError(f"provenance: binary missing field {key!r}")
    if not isinstance(binary["path"], str) or not binary["path"].strip():
        raise ValueError("provenance: binary.path must be a non-empty string")
    if (not isinstance(binary["size_bytes"], int)
            or isinstance(binary["size_bytes"], bool)
            or binary["size_bytes"] <= 0):
        raise ValueError(
            "provenance: binary.size_bytes must be a positive integer")
    if (not isinstance(binary["sha256"], str)
            or not SHA256_HEX_RE.match(binary["sha256"])):
        raise ValueError(
            "provenance: binary.sha256 must be 64-char lowercase hex")
    if (not isinstance(prov["git_commit"], str)
            or not GIT_COMMIT_HEX_RE.match(prov["git_commit"])):
        raise ValueError("provenance: git_commit must be 40-char hex")
    if not isinstance(prov["git_dirty"], bool):
        raise ValueError("provenance: git_dirty must be a bool")
    for key in ("build_profile", "rust_toolchain", "platform", "created"):
        if not isinstance(prov[key], str) or not prov[key].strip():
            raise ValueError(f"provenance: {key} must be a non-empty string")


def validate_schema(results):
    """Raise ValueError unless `results` matches schema_version 1 shape.

    Single source of truth for the results contract — 04-03's compare.py
    imports this same function (renaming keys later invalidates committed
    baselines; do not).
    """
    if not isinstance(results, dict):
        raise ValueError("results must be a dict")
    if "schema_version" not in results:
        raise ValueError("results missing schema_version")
    if results["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version {results['schema_version']!r} "
            f"(expected {SCHEMA_VERSION})")
    arms = results.get("arms")
    if not isinstance(arms, list) or not arms:
        raise ValueError("results must carry a non-empty arms list")
    for i, arm in enumerate(arms):
        if not isinstance(arm, dict) or "name" not in arm:
            raise ValueError(f"arm[{i}] missing name")
        reps = arm.get("reps")
        if not isinstance(reps, list) or not reps:
            raise ValueError(f"arm {arm['name']!r} has no reps")
        for j, rep in enumerate(reps):
            if not isinstance(rep, dict) or "wall_s" not in rep:
                raise ValueError(
                    f"arm {arm['name']!r} rep[{j}] missing wall_s")
            if "peak_rss_bytes" not in rep:
                raise ValueError(
                    f"arm {arm['name']!r} rep[{j}] missing peak_rss_bytes")


def generate_synthetic_input(reads, length, seed, out_path):
    """Generate one synthetic FASTQ via the gen_synthetic.py CLI (seeded)."""
    cmd = [sys.executable, str(GEN_SYNTHETIC),
           "--reads", str(reads), "--length", str(length),
           "--seed", str(seed), "--out", str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"gen_synthetic failed rc={proc.returncode}: {proc.stderr[-500:]}")


def provision_synthetic(reads, scratch):
    """Provision two disjoint seeded inputs into scratch; return their paths."""
    scratch.mkdir(parents=True, exist_ok=True)
    in_a = scratch / "inputA.fq"
    in_b = scratch / "inputB.fq"
    generate_synthetic_input(reads, SYNTHETIC_LENGTH, SEED_A, in_a)
    generate_synthetic_input(reads, SYNTHETIC_LENGTH, SEED_B, in_b)
    return [in_a, in_b]


# --- BENCH-04 degradation ladder -------------------------------------------
VALID_MODES = ("synthetic", "slice", "full")
DEFAULT_SIZE_THRESHOLD_BYTES = 1 << 30  # 1 GiB: at/above -> full, below -> slice


def gather_inputs(spec):
    """Resolve an input spec to a sorted list of existing input paths.

    A directory is scanned for .fq.gz/.fastq.gz (sorted); a plain file is
    returned as-is; a glob pattern expands via pathlib. Read-only — no
    filesystem mutation happens during resolution.
    """
    p = Path(spec)
    if p.is_dir():
        return sorted(x for x in p.iterdir()
                      if x.is_file()
                      and x.name.endswith((".fq.gz", ".fastq.gz")))
    if p.is_file():
        return [p]
    if any(ch in spec for ch in "*?["):
        return sorted(x for x in p.parent.glob(p.name) if x.is_file())
    return []


def resolve_mode(explicit_mode, input_arg, env,
                 size_threshold_bytes=DEFAULT_SIZE_THRESHOLD_BYTES):
    """Pure BENCH-04 ladder: explicit --mode beats RUSTKMER_BENCH_MODE beats
    size-based resolution; a missing or empty input resolves to synthetic.

    Returns (mode, resolved_input_paths). The caller must record both in
    results.json — the resolver never guesses silently. Raises ValueError on
    an invalid mode string from the environment (V5: env is a trust boundary).
    """
    if size_threshold_bytes < 1:
        raise ValueError("size_threshold_bytes must be >= 1")
    mode = explicit_mode if explicit_mode is not None \
        else env.get("RUSTKMER_BENCH_MODE")
    spec = input_arg if input_arg is not None \
        else env.get("RUSTKMER_BENCH_INPUT")
    inputs = gather_inputs(spec) if spec else []
    if mode is not None:
        if mode not in VALID_MODES:
            raise ValueError(
                f"invalid mode {mode!r} (expected one of {VALID_MODES})")
        return mode, inputs
    if not inputs:
        return "synthetic", []
    total = sum(p.stat().st_size for p in inputs)
    if total >= size_threshold_bytes:
        return "full", inputs
    return "slice", inputs


def merge_input_for(mode, merge_input):
    """Validate --merge-input against the resolved mode (04-04).

    --merge-input is a slice-mode-only knob: it names the SECOND gz input
    (the r2 side of the r1/r2 merge arrangement) whose slice joins the run.
    Returns the validated Path, or None when no merge input was given.
    Raises ValueError for a non-slice mode or a missing file — never a
    silent ignore.
    """
    if merge_input is None:
        return None
    if mode != "slice":
        raise ValueError(
            f"--merge-input is only supported in slice mode (resolved mode "
            f"is {mode!r})")
    path = Path(merge_input)
    if not path.is_file():
        raise ValueError(f"--merge-input not found or not a file: {path}")
    return path


def extract_slice(gz_path, n_reads, output_path):
    """Write the first n_reads (4 lines each) of gunzip -c output to a file.

    Deterministic: identical bytes for the same input and N on every machine.
    Decompresses with gunzip -c (portable) — the macOS compress-family zcat
    variant is never invoked (RESEARCH Pitfall 1). Pure subprocess (no shell),
    so environment-provided paths cannot inject commands. Raises on an empty
    result (zero reads would measure nothing) or a failed decompressor.
    """
    line_limit = 4 * n_reads
    proc = subprocess.Popen(["gunzip", "-c", str(gz_path)],
                            stdout=subprocess.PIPE)
    written = 0
    truncated = False
    try:
        with open(output_path, "wb") as out:
            for line in proc.stdout:
                if written >= line_limit:
                    truncated = True
                    break
                out.write(line)
                written += 1
    finally:
        proc.stdout.close()
        if truncated:
            proc.terminate()  # head semantics: stop the producer early
        proc.wait()
    if written == 0:
        raise RuntimeError(
            f"slice of {gz_path} produced 0 lines — empty or invalid gz input")
    if not truncated and proc.returncode != 0:
        raise RuntimeError(
            f"gunzip failed rc={proc.returncode} on {gz_path}")


def provision_slice(resolved_inputs, slice_reads, scratch, merge_input=None):
    """Provision two slice inputs (first two resolved sources; a single
    source is extracted once and measured twice).

    merge_input (04-04): provision the second slice from this gz path
    instead — the r1/r2 arrangement the milestone merge measurement uses
    (slice A from --input, slice B from --merge-input, same --slice-reads).
    """
    if not resolved_inputs:
        raise RuntimeError("slice mode requires a resolved input")
    scratch.mkdir(parents=True, exist_ok=True)
    if merge_input is not None:
        srcs = [resolved_inputs[0], Path(merge_input)]
    elif len(resolved_inputs) >= 2:
        srcs = resolved_inputs[:2]
    else:
        srcs = [resolved_inputs[0], resolved_inputs[0]]
    slices = []
    extracted = {}
    for i, src in enumerate(srcs):
        if src in extracted:
            slices.append(extracted[src])
            continue
        dst = scratch / f"slice-{i}.fq"
        extract_slice(src, slice_reads, dst)
        extracted[src] = dst
        slices.append(dst)
    return slices


def provision_random_slice(resolved_inputs, slice_reads, scratch, seed,
                           merge_input=None):
    """Provision seeded random-record subslices + sidecar manifests (05-04).

    Mirrors provision_slice's source arrangement (first two resolved sources;
    a single source is sampled once and measured twice; --merge-input samples
    slice B from the second gz), but each distinct source is sampled with
    random_slice.reservoir_slice instead of first-N truncation. The selection
    manifest is written beside each slice.

    Returns (slices, selections): slices is the list of slice Paths (aligned
    with provision_slice's output); selections is the parallel list of
    {"slice", "manifest_path", "manifest"} dicts for the distinct sources.
    """
    if not resolved_inputs:
        raise RuntimeError("slice mode requires a resolved input")
    if __package__ in (None, ""):
        # Direct script execution: make the scripts package importable so the
        # lazy reservoir_slice import resolves to this checkout (random_slice
        # uses the same fixup). Lazy import avoids the bench<->random_slice
        # import cycle (random_slice imports fingerprint/validate_path here).
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.bench.random_slice import reservoir_slice

    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    if merge_input is not None:
        srcs = [resolved_inputs[0], Path(merge_input)]
    elif len(resolved_inputs) >= 2:
        srcs = resolved_inputs[:2]
    else:
        srcs = [resolved_inputs[0], resolved_inputs[0]]
    slices = []
    selections = []
    extracted = {}
    for i, src in enumerate(srcs):
        if src in extracted:
            dst, info = extracted[src]
            slices.append(dst)
            selections.append(info)
            continue
        dst = scratch / f"slice-random-{i}.fq"
        manifest_path = scratch / f"slice-random-{i}.manifest.json"
        manifest = reservoir_slice(src, slice_reads, seed, dst, manifest_path)
        info = {"slice": str(dst), "manifest_path": str(manifest_path),
                "manifest": manifest}
        extracted[src] = (dst, info)
        slices.append(dst)
        selections.append(info)
    return slices, selections


def provision_full(resolved_inputs):
    """Measure the resolved inputs directly (first two; a single input is
    measured twice — an honest repeated measurement, not a fabrication)."""
    if not resolved_inputs:
        raise RuntimeError("full mode requires a resolved input")
    if len(resolved_inputs) >= 2:
        return resolved_inputs[:2]
    return [resolved_inputs[0], resolved_inputs[0]]


# --- BENCH-02 parity gate (04-02) --------------------------------------------
# Exit codes are a contract: 0 parity holds, 1 count mismatch (a methodology
# finding, never a silent pass), 2 jellyfish required but absent.
PARITY_MISMATCH_EXIT = 1
JELLYFISH_MISSING_EXIT = 2
PARITY_SMOKE_HASH_SIZE = "1G"  # smoke-scale -s; real runs use the 10G default

# --- PROF-01 fingerprint-bound parity reference (05-04) ----------------------
# Pinned head-4M counts copied from .planning/research/profiling/evidence.json
# (slice.k21_distinct_canonical / slice.k21_instances) and parity_report.json —
# the single source for the historical reference. NEVER applied to a random
# sample; a changed dataset is a loud methodology finding, not a re-pin.
PARITY_PINNED_HEAD4M = {"distinct": 229694874, "total": 519271168}
HEAD4M_READS = 4000000
DEFAULT_SLICE_SEED = 20261112
HEAD4M_SLICE_KIND = "head-4M-profiling-reference"
RANDOM_SLICE_KIND = "random-record"
PARITY_REFERENCE_TOOL = "jellyfish 2.3.1"
PARITY_REF_INVALID_EXIT = 2


def require_jellyfish():
    """Exit 2 with an explicit message when jellyfish arms are requested but
    the binary is not on PATH (shutil.which presence check).

    The CI synthetic path never requests jellyfish arms, so absence there is
    never an error.
    """
    if shutil.which("jellyfish") is None:
        print("bench.py: jellyfish arms were requested but `jellyfish` is "
              "not on PATH — install jellyfish 2.3.x (e.g. brew install "
              "jellyfish) or run without jellyfish arms", file=sys.stderr)
        sys.exit(JELLYFISH_MISSING_EXIT)


def parse_jellyfish_stats(text):
    """Extract {'distinct': int, 'total': int} from `jellyfish stats` text.

    Pure function pinned to the 2.3.1 output shape (verified verbatim:
    'Distinct:  24000' / 'Total:     24000'). Text missing either line raises
    ValueError — a parse that tolerated a missing line would let the parity
    assertion run against nothing.
    """
    distinct = None
    total = None
    for line in text.splitlines():
        m = re.match(r"^Distinct:\s*(\d+)\s*$", line)
        if m:
            distinct = int(m.group(1))
        m = re.match(r"^Total:\s*(\d+)\s*$", line)
        if m:
            total = int(m.group(1))
    if distinct is None:
        raise ValueError(f"jellyfish stats text has no 'Distinct:' line: "
                         f"{text!r}")
    if total is None:
        raise ValueError(f"jellyfish stats text has no 'Total:' line: "
                         f"{text!r}")
    return {"distinct": distinct, "total": total}


def jellyfish_stats(jf_path):
    """Return the parse_jellyfish_stats dict for a .jf database (list form)."""
    proc = subprocess.run(["jellyfish", "stats", str(jf_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"jellyfish stats failed rc={proc.returncode} on "
                           f"{jf_path}: {proc.stderr[-500:]}")
    return parse_jellyfish_stats(proc.stdout)


def run_parity(input_path, k, threads, rustkmer, scratch,
               hash_size=PARITY_SMOKE_HASH_SIZE):
    """Count the same input with both tools and prove the counts equal.

    The BENCH-02 correctness gate: runs before any timing comparison is
    trusted. Parity equality (jellyfish Distinct == rustkmer unique_kmers,
    jellyfish Total == rustkmer total_kmers, Distinct > 0) exits 0 printing
    a PARITY OK line; any mismatch exits 1 with both tools' numbers and the
    N-handling caveat. A mismatch is a methodology finding — real-data parity
    (N-containing / lowercase reads) is re-proven on the actual slice in
    04-04 before the full milestone run (RESEARCH Pitfall 10).

    Both commands derive from ONE BenchmarkConfig — the same fairness
    guarantee the comparison protocol measures under.
    """
    require_jellyfish()
    input_path = Path(input_path)
    rk_db = scratch / "parity_rustkmer.rkdb"
    jf_db = scratch / "parity_jellyfish.jf"
    cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                          hash_size=hash_size, inputs=[input_path],
                          decompressor=default_decompressor())

    # rustkmer arm: list-form invocation; stats via the shared helper.
    proc = subprocess.run(rustkmer_count_cmd(cfg, rk_db, rustkmer),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"parity: rustkmer count failed rc="
                           f"{proc.returncode}: {proc.stderr[-500:]}")
    rk = stats(rk_db, rustkmer)

    # jellyfish arm: plain input takes a direct path argument; gz input goes
    # through the decompression pipe (jellyfish aborts on .gz paths, Pitfall 3)
    # — jellyfish_count_cmd owns that branch.
    proc = subprocess.run(jellyfish_count_cmd(cfg, jf_db),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"parity: jellyfish count failed rc="
                           f"{proc.returncode}: {proc.stderr[-500:]}")
    jf = jellyfish_stats(jf_db)

    if (jf["distinct"] == rk["unique_kmers"]
            and jf["total"] == rk["total_kmers"]
            and jf["distinct"] > 0):
        print(f"PARITY OK distinct={jf['distinct']} total={jf['total']}")
        return {"distinct": jf["distinct"], "total": jf["total"]}

    # Distinct == 0 with equal counts also lands here: a zero count is a
    # silent-input failure (Pitfall 1), never a parity pass.
    print(f"PARITY MISMATCH: jellyfish distinct={jf['distinct']} "
          f"total={jf['total']} vs rustkmer unique_kmers={rk['unique_kmers']} "
          f"total_kmers={rk['total_kmers']} — methodology finding, not a "
          f"pass. N-containing/lowercase real data is re-checked on the "
          f"actual slice before the full run (Pitfall 10).", file=sys.stderr)
    sys.exit(PARITY_MISMATCH_EXIT)


def _parity_ref_invalid(message):
    """Print a reference-gate input problem and exit 2 — never a silent
    fallback (an unbound/ambiguous reference is not a gate)."""
    print(f"bench.py: {message}", file=sys.stderr)
    sys.exit(PARITY_REF_INVALID_EXIT)


def slice_kind_for(selection, slice_reads):
    """Reference slice_kind for a slice recipe (05-04).

    head selection + 4000000 reads -> the pinned profiling reference kind;
    random selection -> random-record. Head selections of other sizes have
    NO reference recipe (None) — the gate/capture flow rejects them loudly
    rather than mislabeling a head prefix as a random sample.
    """
    if selection == "random":
        return RANDOM_SLICE_KIND
    if selection == "head" and slice_reads == HEAD4M_READS:
        return HEAD4M_SLICE_KIND
    return None


def _validate_reference_record(rec):
    """Raise ValueError unless rec is a complete, well-formed reference.

    Every record must be bound to a source fingerprint and carry positive
    expected counts plus full provenance (an unattributable reference must
    never gate — T-05-02). Random records additionally carry the FULL
    selection identity: seed + selection_manifest_sha256 + output_sha256,
    cross-checked against the embedded selection manifest.
    """
    if not isinstance(rec, dict):
        raise ValueError("reference record must be a dict")
    sha = rec.get("source_sha256")
    if not isinstance(sha, str) or not SHA256_HEX_RE.match(sha):
        raise ValueError("reference record missing/invalid source_sha256 — "
                         "an unbound record can never gate")
    kind = rec.get("slice_kind")
    if kind not in (HEAD4M_SLICE_KIND, RANDOM_SLICE_KIND):
        raise ValueError(f"reference record has unknown slice_kind {kind!r}")
    reads = rec.get("reads")
    if not isinstance(reads, int) or isinstance(reads, bool) or reads < 1:
        raise ValueError("reference record reads must be a positive integer")
    k = rec.get("k")
    if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 64:
        raise ValueError("reference record k must be an integer in 1..64")
    if not isinstance(rec.get("canonical"), bool):
        raise ValueError("reference record canonical must be a bool")
    tool = rec.get("reference_tool")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("reference record missing reference_tool")
    expected = rec.get("expected")
    if not isinstance(expected, dict):
        raise ValueError("reference record missing expected counts")
    for key in ("distinct", "total"):
        v = expected.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ValueError(f"reference record expected.{key} must be a "
                             f"positive integer")
    validate_provenance(rec)
    if kind == RANDOM_SLICE_KIND:
        seed = rec.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("random reference record missing/invalid seed "
                             "identity")
        for key in ("selection_manifest_sha256", "output_sha256"):
            v = rec.get(key)
            if not isinstance(v, str) or not SHA256_HEX_RE.match(v):
                raise ValueError(f"random reference record missing/invalid "
                                 f"{key} identity")
        manifest = rec.get("selection_manifest")
        if not isinstance(manifest, dict):
            raise ValueError("random reference record missing "
                             "selection_manifest")
        if (manifest.get("seed") != seed
                or manifest.get("output_sha256") != rec["output_sha256"]):
            raise ValueError("random reference selection_manifest disagrees "
                             "with its identity fields")


def _reference_full_key(rec):
    """The exact-match key: source + recipe, plus the full random selection
    identity for random records (validated records only)."""
    key = (rec["source_sha256"], rec["slice_kind"], rec["reads"], rec["k"],
           rec["canonical"])
    if rec["slice_kind"] == RANDOM_SLICE_KIND:
        key += (rec["seed"], rec["selection_manifest_sha256"],
                rec["output_sha256"])
    return key


def _load_reference_doc(path):
    """Load and strictly validate every record in a reference file, or exit 2."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        _parity_ref_invalid(f"parity reference file not found: {path}")
    except OSError as exc:
        _parity_ref_invalid(f"parity reference file unreadable: {path} ({exc})")
    except json.JSONDecodeError as exc:
        _parity_ref_invalid(f"parity reference file is not parseable JSON: "
                            f"{path} ({exc})")
    if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
        _parity_ref_invalid(f"parity reference file must hold a records "
                            f"list: {path}")
    for i, rec in enumerate(doc["records"]):
        try:
            _validate_reference_record(rec)
        except ValueError as exc:
            _parity_ref_invalid(f"parity reference record[{i}] invalid: {exc}")
    return doc


def load_parity_reference(path, source_sha256, slice_kind, reads, k, canonical,
                          selection=None):
    """Return the exactly-matching parity reference record, or exit 2.

    The match key is (source_sha256, slice_kind, reads, k, canonical); for
    slice_kind "random-record" the caller MUST pass selection = {seed,
    selection_manifest_sha256, output_sha256} (computed at gate time from the
    LIVE provisioned slice bytes + sidecar manifest) and ALL three identity
    fields must equal the record's stored values. No matching record, a
    record missing any identity field, a missing selection argument, or more
    than one full-key match are all invalid (exit 2) — never a silent
    fallback, never first-match-wins.
    """
    doc = _load_reference_doc(path)
    if slice_kind == RANDOM_SLICE_KIND:
        if not isinstance(selection, dict):
            _parity_ref_invalid("random-record reference gate requires a "
                                "selection identity {seed, "
                                "selection_manifest_sha256, output_sha256}")
        seed = selection.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            _parity_ref_invalid("selection identity missing/invalid seed")
        for key in ("selection_manifest_sha256", "output_sha256"):
            v = selection.get(key)
            if not isinstance(v, str) or not SHA256_HEX_RE.match(v):
                _parity_ref_invalid(f"selection identity missing/invalid "
                                    f"{key}")
        want = (source_sha256, slice_kind, reads, k, canonical, seed,
                selection["selection_manifest_sha256"],
                selection["output_sha256"])
    else:
        want = (source_sha256, slice_kind, reads, k, canonical)
    matches = [r for r in doc["records"] if _reference_full_key(r) == want]
    if not matches:
        _parity_ref_invalid(f"no parity reference record for this "
                            f"fingerprint/recipe (source={source_sha256[:12]}"
                            f"… kind={slice_kind} reads={reads} k={k} "
                            f"canonical={canonical}) — never a silent "
                            f"fallback")
    if len(matches) > 1:
        _parity_ref_invalid(f"ambiguous parity reference: {len(matches)} "
                            f"records match the FULL key — ambiguity is "
                            f"invalid, never first-match-wins")
    return matches[0]


def gate_parity_reference(counts, path, source_sha256, slice_kind, reads, k,
                          canonical, selection=None):
    """Gate live parity counts against the bound reference (after a live pass).

    Reference recipe/fingerprint mismatch exits 2 (via load_parity_reference);
    reference counts != live counts exits 1 printing both sides — a
    methodology finding, never a silent pass. Returns the matching record.
    """
    rec = load_parity_reference(path, source_sha256, slice_kind, reads, k,
                                canonical, selection=selection)
    expected = rec["expected"]
    if (expected["distinct"] != counts["distinct"]
            or expected["total"] != counts["total"]):
        print(f"PARITY REFERENCE MISMATCH: reference "
              f"distinct={expected['distinct']} total={expected['total']} "
              f"vs live distinct={counts['distinct']} "
              f"total={counts['total']} — methodology finding, not a pass",
              file=sys.stderr)
        sys.exit(PARITY_MISMATCH_EXIT)
    print(f"PARITY REFERENCE OK distinct={counts['distinct']} "
          f"total={counts['total']} (bound to source {source_sha256[:12]}… "
          f"kind={slice_kind})")
    return rec


def selection_identity_from(slice_path, manifest_path, seed):
    """Compute the gate-time random selection identity from LIVE bytes.

    Recomputes the slice output sha256 from the provisioned slice bytes and
    cross-checks it against the sidecar manifest's own output_sha256; the
    manifest's seed must equal the requested seed. Any mismatch exits 2
    (tampered or mismatched slice/manifest can never gate). Returns
    {seed, selection_manifest_sha256 (hash of the manifest FILE bytes),
    output_sha256 (the live slice hash)}.
    """
    live_out = fingerprint(slice_path)["sha256"]
    try:
        manifest_bytes = Path(manifest_path).read_bytes()
    except OSError as exc:
        _parity_ref_invalid(f"selection manifest unreadable: {manifest_path} "
                            f"({exc})")
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as exc:
        _parity_ref_invalid(f"selection manifest is not parseable JSON: "
                            f"{manifest_path} ({exc})")
    if not isinstance(manifest, dict):
        _parity_ref_invalid(f"selection manifest must be a dict: "
                            f"{manifest_path}")
    if manifest.get("output_sha256") != live_out:
        _parity_ref_invalid(f"slice output hash {live_out[:12]}… differs "
                            f"from the sidecar manifest's output_sha256 — "
                            f"tampered or mismatched slice bytes")
    if manifest.get("seed") != seed:
        _parity_ref_invalid(f"sidecar manifest seed {manifest.get('seed')!r} "
                            f"!= requested seed {seed!r}")
    return {
        "seed": seed,
        "selection_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "output_sha256": live_out,
    }


def capture_parity_reference(path, record):
    """Append a verified reference record to the baseline file (create if
    absent) — only ever called AFTER a live parity pass.

    The head-4M recipe additionally asserts the pinned constants before
    writing: changed live counts are a loud methodology finding (exit 1),
    never a re-pinned constant. A record for an already-referenced EXACT
    recipe is rejected (exit 2) rather than creating a duplicate full-key
    record that would brick the gate.
    """
    try:
        _validate_reference_record(record)
    except ValueError as exc:
        _parity_ref_invalid(f"cannot capture invalid parity reference "
                            f"record: {exc}")
    if (record["slice_kind"] == HEAD4M_SLICE_KIND
            and record["expected"] != PARITY_PINNED_HEAD4M):
        print(f"PINNED PARITY MISMATCH: head-4M live counts "
              f"distinct={record['expected']['distinct']} "
              f"total={record['expected']['total']} != pinned "
              f"{PARITY_PINNED_HEAD4M} — the measured dataset changed; this "
              f"is a loud methodology finding, never a re-pinned constant",
              file=sys.stderr)
        sys.exit(PARITY_MISMATCH_EXIT)
    path = Path(path)
    if path.exists():
        doc = _load_reference_doc(path)
        key = _reference_full_key(record)
        if any(_reference_full_key(r) == key for r in doc["records"]):
            _parity_ref_invalid("a reference record for this EXACT recipe "
                                "already exists — delete it explicitly to "
                                "re-capture; refusing to create a duplicate "
                                "full-key record")
        records = doc["records"] + [record]
    else:
        records = [record]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"schema_version": SCHEMA_VERSION, "records": records},
                  fh, indent=2)
        fh.write("\n")
    print(f"parity reference captured: kind={record['slice_kind']} "
          f"reads={record['reads']} distinct={record['expected']['distinct']} "
          f"total={record['expected']['total']} -> {path}")


def run_parity_cli(args, out_explicit=False):
    """--parity-only: provision via the ladder, run_parity, then optionally
    gate against / capture a fingerprint-bound reference and emit a
    provenance-bearing parity record to --out (when explicitly given)."""
    mode, resolved_inputs = resolve_mode(args.mode, args.input, os.environ)
    # Validation only — run_parity measures inputs[0]; a --merge-input given
    # alongside --parity-only must still be a legal slice-mode value rather
    # than being silently ignored.
    merge_input_for(mode, args.merge_input)
    scratch = Path(args.out).parent
    scratch.mkdir(parents=True, exist_ok=True)
    if args.slice_selection == "random" and mode != "slice":
        _parity_ref_invalid("--slice-selection random requires slice mode "
                            f"(resolved mode is {mode!r})")
    selection_info = None
    if mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
    elif mode == "slice":
        if args.slice_selection == "random":
            inputs, selections = provision_random_slice(
                resolved_inputs, args.slice_reads, scratch, args.slice_seed)
            selection_info = selections[0]
        else:
            inputs = provision_slice(resolved_inputs, args.slice_reads, scratch)
    else:
        inputs = provision_full(resolved_inputs)

    # Real runs need a generous -s (the 1G smoke default silently penalizes
    # the 229M-distinct real slice); --hash-size is threaded into run_parity.
    counts = run_parity(inputs[0], args.k, args.threads, args.rustkmer,
                        scratch, hash_size=args.hash_size)

    source_sha256 = None
    kind = slice_kind_for(args.slice_selection, args.slice_reads) \
        if mode == "slice" else None
    selection = None
    if args.parity_reference or args.capture_parity_reference:
        if mode != "slice":
            _parity_ref_invalid("parity references are slice-mode recipes "
                                "(head-4M pinned or random-record); resolved "
                                f"mode is {mode!r}")
        if kind is None:
            _parity_ref_invalid(f"no parity reference recipe for head "
                                f"selection with {args.slice_reads} reads "
                                f"(the pinned recipe is head {HEAD4M_READS}; "
                                f"use --slice-selection random for other "
                                f"sizes)")
        source_sha256 = fingerprint(resolved_inputs[0])["sha256"]
        if args.slice_selection == "random":
            selection = selection_identity_from(
                inputs[0], selection_info["manifest_path"], args.slice_seed)
            if selection_info["manifest"]["source"]["sha256"] != source_sha256:
                _parity_ref_invalid("selection manifest source fingerprint "
                                    "differs from the live source fingerprint")
        if args.parity_reference:
            gate_parity_reference(counts, args.parity_reference,
                                  source_sha256, kind, args.slice_reads,
                                  args.k, True, selection=selection)
        else:
            record = {
                "slice_kind": kind,
                "source_sha256": source_sha256,
                "reads": args.slice_reads,
                "k": args.k,
                "canonical": True,
                "reference_tool": PARITY_REFERENCE_TOOL,
                "expected": dict(counts),
                "provenance": binary_provenance(args.rustkmer, "release"),
            }
            if selection is not None:
                # Verify the manifest's slice-output hash against a LIVE
                # fingerprint of the slice before writing the reference.
                live_out = fingerprint(inputs[0])["sha256"]
                if selection_info["manifest"]["output_sha256"] != live_out:
                    _parity_ref_invalid("slice output hash differs from the "
                                        "selection manifest before capture")
                record.update({
                    "seed": args.slice_seed,
                    "selection_manifest": selection_info["manifest"],
                    "selection_manifest_sha256":
                        selection["selection_manifest_sha256"],
                    "output_sha256": live_out,
                })
            capture_parity_reference(args.capture_parity_reference, record)

    if out_explicit:
        recipe = {"mode": mode, "k": args.k, "canonical": True,
                  "threads": args.threads, "hash_size": args.hash_size}
        if mode == "slice":
            if source_sha256 is None:
                source_sha256 = fingerprint(resolved_inputs[0])["sha256"]
            recipe.update({"slice_selection": args.slice_selection,
                           "slice_reads": args.slice_reads,
                           "slice_kind": kind,
                           "source_sha256": source_sha256})
            if args.slice_selection == "random":
                recipe["slice_seed"] = args.slice_seed
        elif mode == "synthetic":
            recipe["reads"] = args.reads
        doc = {
            "schema_version": SCHEMA_VERSION,
            "kind": "parity-record",
            "mode": mode,
            "distinct": counts["distinct"],
            "total": counts["total"],
            "input_fingerprint": [fingerprint(inputs[0])],
            "slice_recipe": recipe,
            "created": datetime.now(timezone.utc).isoformat(),
            "provenance": binary_provenance(args.rustkmer, "release"),
        }
        if selection_info is not None:
            doc["selection_manifest"] = selection_info["manifest"]
        validate_provenance(doc)
        out_path = Path(args.out)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")
        print(f"parity record written to {out_path}")


# --- BENCH-02 measurement protocol (04-02) ------------------------------------

def round_schedule(n_rounds):
    """Counterbalanced tool order per round (thermal/order-bias defense,
    Pitfall 5): rustkmer measures first in even rounds, jellyfish first in
    odd rounds. Recorded verbatim in results.json params.round_schedule."""
    schedule = {}
    for rnd in range(n_rounds):
        first = "rustkmer" if rnd % 2 == 0 else "jellyfish"
        second = "jellyfish" if first == "rustkmer" else "rustkmer"
        schedule[str(rnd)] = [first, second]
    return schedule


def cache_state_from(in_ci, platform, purge_succeeded):
    """Pure honest-label decision (T-04-04): the cache_state label derives
    from the actual attempt context — the GITHUB_ACTIONS marker, the
    platform, and the purge subprocess's real outcome — never from
    configuration intent."""
    if in_ci:
        return "runner-fresh"
    if platform != "darwin":
        return "unavailable"
    return "purged" if purge_succeeded else "unavailable"


def attempt_cache_purge(env=None):
    """Attempt a cold-cache purge before a measured run; return the honest
    cache_state label.

    GITHUB_ACTIONS set -> 'runner-fresh' (fresh runner; no purge attempted).
    darwin -> `sudo -n purge` (non-interactive flag; rc 0 records 'purged',
    any failure records 'unavailable'). Any other platform records
    'unavailable' without attempting.
    """
    env = os.environ if env is None else env
    if env.get("GITHUB_ACTIONS"):
        return cache_state_from(True, sys.platform, None)
    if sys.platform != "darwin":
        return cache_state_from(False, sys.platform, None)
    proc = subprocess.run(["sudo", "-n", "purge"],
                          capture_output=True, text=True)
    return cache_state_from(False, sys.platform, proc.returncode == 0)


def reduce_arm(reps):
    """Reduce an arm's reps to headline medians + CV% (order-insensitive).

    CV% = stdev over mean x 100 on wall times; a single-rep arm records null
    (stdev needs >= 2 points). CV above the threshold sets cv_warning in
    results.json WITHOUT failing the run — a dirty measurement is a warning,
    not an error.
    """
    walls = [r["wall_s"] for r in reps]
    rss = [r["peak_rss_bytes"] for r in reps]
    reduced = {
        "median_wall_s": statistics.median(walls),
        "median_peak_rss_bytes": statistics.median(rss),
        "cv_wall_pct": None,
        "cv_warning": False,
    }
    if len(walls) >= 2:
        mean = sum(walls) / len(walls)
        cv = (statistics.stdev(walls) / mean * 100) if mean > 0 else 0.0
        reduced["cv_wall_pct"] = cv
        reduced["cv_warning"] = cv > CV_WARNING_THRESHOLD_PCT
    return reduced


def check_disk_floor(directory, floor_gb):
    """Abort with exit 3 before any mode=full measurement when free space on
    the output directory's volume is below the floor (Pitfall 8: full-human
    .rkdb artifacts alone can reach 55-60 GB per database, with merge scratch
    on top). Returns the free bytes when the guard passes."""
    st = os.statvfs(str(directory))
    free_bytes = st.f_bavail * st.f_frsize
    required_bytes = int(floor_gb * (1 << 30))
    if free_bytes < required_bytes:
        print(f"bench.py: disk guardrail: {free_bytes} bytes free on "
              f"{directory} but the configured floor is {required_bytes} "
              f"bytes ({floor_gb} GiB) — aborting before any measurement "
              f"(exit {DISK_FLOOR_EXIT})", file=sys.stderr)
        sys.exit(DISK_FLOOR_EXIT)
    return free_bytes


def assert_arm_ordering(arm_specs):
    """Fail loud unless, per tool, every count arm precedes every merge arm.

    run_comparison_protocol executes the FIRST spec of each tool as the
    discarded warmup (the `next(s for s in arm_specs ...)` lookup) and runs
    same-tool arms in spec order — a spec list whose merge arm precedes a
    count arm would silently change what the warmup measures (T-11-02).
    The invariant is generic over any arm list, not just the shipped seven:
    within one tool's spec order, an arm whose name contains 'merge' must
    not precede an arm whose name contains 'count' (e.g. jellyfish-merge
    preceding jellyfish-count-B, or merge-t1 preceding count-A).

    Raises:
        RuntimeError: On any count-after-merge ordering violation within a
            tool, naming both arms and their positions.
    """
    tools = []
    for spec in arm_specs:
        if spec["tool"] not in tools:
            tools.append(spec["tool"])
    for tool in tools:
        order = [s["name"] for s in arm_specs if s["tool"] == tool]
        first_merge = None
        for position, name in enumerate(order):
            if "merge" in name and first_merge is None:
                first_merge = position
            if "count" in name and first_merge is not None:
                raise RuntimeError(
                    f"arm spec ordering violated for tool {tool!r}: count "
                    f"arm {name!r} (position {position}) follows merge arm "
                    f"{order[first_merge]!r} (position {first_merge}) — "
                    f"warmup (first spec per tool) and in-round execution "
                    f"follow spec order, so a merge arm must never precede "
                    f"a count arm within a tool")


def assert_merge_parity(by_name):
    """Three-way aggregate merge-parity pre-gate (MBENCH-02, PARITY-GATE.md §2).

    Checks the aggregate conservation invariants of a merge comparison and
    raises BEFORE any median is trusted:

      - rustkmer-merge Total == jellyfish-merge Total
        == count-A Total + count-B Total
      - rustkmer-merge Distinct == jellyfish-merge Distinct
      - merged Distinct >= max input Distinct (boundary exact-at-max passes;
        one count short raises — GREEN/RED unit-proven)

    Every Total read here is the SUM-OF-COUNTS definition carried on the arm
    dicts by the protocol's stats readers (stats() / jellyfish_stats() ->
    unique_kmers/total_kmers) — NEVER the DatabaseHeader record-count field
    (the IN-03 collision; mixing the two definitions fails mysteriously or
    passes vacuously, milestone Pitfall 2). Aggregate conservation alone
    cannot prove parity — it holds even under jellyfish's silent canonicality
    mixing — so this pre-gate is the fast failure path; the per-k-mer
    dump-vs-dump leg (dump_vs_dump_equal) is the verdict gate.

    Args:
        by_name: Mapping arm name -> arm dict with distinct_kmers and
            total_kmers keys ('count-A', 'count-B', 'merge',
            'jellyfish-merge' required).

    Raises:
        RuntimeError: On any violated invariant, naming the arms and values.
    """
    merged_total = (by_name["count-A"]["total_kmers"]
                    + by_name["count-B"]["total_kmers"])
    if by_name["merge"]["total_kmers"] != merged_total:
        raise RuntimeError(
            f"merge parity: rustkmer merge Total "
            f"{by_name['merge']['total_kmers']} != sum of input Totals "
            f"{merged_total} (count-A {by_name['count-A']['total_kmers']} + "
            f"count-B {by_name['count-B']['total_kmers']}; sum-of-counts "
            f"definition)")
    if by_name["jellyfish-merge"]["total_kmers"] != merged_total:
        raise RuntimeError(
            f"merge parity: jellyfish-merge Total "
            f"{by_name['jellyfish-merge']['total_kmers']} != sum of input "
            f"Totals {merged_total} (sum-of-counts definition) — "
            f"methodology finding, not a comparable measurement")
    if (by_name["merge"]["distinct_kmers"]
            != by_name["jellyfish-merge"]["distinct_kmers"]):
        raise RuntimeError(
            f"merge parity: merged Distinct differs across tools: rustkmer "
            f"{by_name['merge']['distinct_kmers']} vs jellyfish "
            f"{by_name['jellyfish-merge']['distinct_kmers']} — union "
            f"key-spaces must agree exactly")
    max_input = max(by_name["count-A"]["distinct_kmers"],
                    by_name["count-B"]["distinct_kmers"])
    if by_name["merge"]["distinct_kmers"] < max_input:
        raise RuntimeError(
            f"merge parity: merged Distinct "
            f"{by_name['merge']['distinct_kmers']} < max input Distinct "
            f"{max_input} — a merge cannot lose the largest input's "
            f"key space")


def normalize_dump_lines(text):
    """Normalize a rustkmer dump / `jellyfish dump -c` text to sorted-comparable
    "kmer<TAB>count" lines (MBENCH-02, PARITY-GATE.md §4).

    Skips '#'-prefixed comment lines (the rustkmer dump header) and blank
    lines, splits each data line on whitespace, and emits one
    "kmer<TAB>count" string per entry. Both tools' dump formats normalize to
    this same shape so the gate can byte-compare them after an LC_ALL=C-
    ordered sort (keys are unique, so sorted-line byte equality is per-k-mer
    count equality).

    Fail-loud parsing (threat T-11-09): any line that does not parse into
    exactly a k-mer and an integer count raises RuntimeError naming the
    offending line; empty or whitespace-only input raises as well — a
    tolerant parser would let the gate run against nothing (the vacuous-gate
    class, MBENCH-02/empty).

    Args:
        text: Full stdout of one dump command.

    Returns:
        List of normalized "kmer<TAB>count" strings in input order.

    Raises:
        RuntimeError: On empty input or any malformed data line.
    """
    normalized = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 2:
            raise RuntimeError(
                f"dump parse: expected exactly 'kmer count', got "
                f"{len(fields)} fields in line: {raw_line!r}")
        kmer, count_text = fields
        try:
            int(count_text)
        except ValueError:
            raise RuntimeError(
                f"dump parse: count field {count_text!r} is not an integer "
                f"in line: {raw_line!r}") from None
        normalized.append(f"{kmer}\t{count_text}")
    if not normalized:
        raise RuntimeError(
            "dump parse: empty dump output (zero data lines) — an empty "
            "dump can never pass the gate (MBENCH-02/empty)")
    return normalized


def _dump_rustkmer_stdout(rkdb_path, rustkmer, workdir):
    """Run `rustkmer dump` (list form) and return its dump text.

    Output goes to a file inside workdir via the dump CLI's -o flag rather
    than through a giant stdout pipe; fail-loud on non-zero exit.
    """
    out_path = Path(workdir) / "parity-rk-dump.txt"
    argv = [str(rustkmer), "dump", str(rkdb_path), "-o", str(out_path)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"rustkmer dump failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return out_path.read_text(encoding="utf-8")


def _dump_jellyfish_stdout(jf_path, workdir):
    """Run `jellyfish dump -c` (list form) and return its dump text.

    stdout is redirected to a file inside workdir (`jellyfish dump -c` writes
    2-column kmer<TAB>count lines); fail-loud on non-zero exit.
    """
    out_path = Path(workdir) / "parity-jf-dump.txt"
    with open(out_path, "w", encoding="utf-8") as fh:
        proc = subprocess.run(["jellyfish", "dump", "-c", str(jf_path)],
                              stdout=fh, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"jellyfish dump -c failed rc={proc.returncode} on {jf_path}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return out_path.read_text(encoding="utf-8")


def dump_vs_dump_equal(rkdb_path, jf_path, rustkmer, workdir,
                       dump_rk=None, dump_jf=None):
    """Cross-tool verdict gate (MBENCH-02, PARITY-GATE.md §4): exact per-k-mer
    equality of the two merged outputs.

    Runs `rustkmer dump` on the merged .rkdb and `jellyfish dump -c` on the
    merged .jf (list-form subprocesses, fail-loud on non-zero exit),
    normalizes both to (kmer, count) lines, sorts both with LC_ALL=C byte
    ordering, and demands byte equality. Keys are unique within each dump, so
    byte equality after sorting is per-k-mer count equality at every shared
    key — the gate accepts nothing less than identity, which is the
    structural defense jellyfish's silent canonicality mixing cannot pass.

    LC_ALL=C ordering: the sort runs in-process with Python str ordering,
    which over the pure-ASCII k-mer/digit/tab alphabet of both dump formats
    is byte-order identical to LC_ALL=C sort — deterministic regardless of
    the host locale, no external sort process.

    Empty or whitespace-only dump output from either side is a loud
    RuntimeError — a zero-line dump can never pass (MBENCH-02/empty).

    The dump helpers are injectable seams defaulting at CALL time to the
    module-level subprocess runners, so unit tests drive the real
    normalize/sort/compare logic on fixture text without binaries (the
    phase10 run_rounds injectable-seam pattern).

    Args:
        rkdb_path: Path to the rustkmer merged .rkdb.
        jf_path: Path to the jellyfish merged .jf.
        rustkmer: Path to the rustkmer binary.
        workdir: Directory for the intermediate dump files (created if
            missing; files are removed after reading).
        dump_rk: Optional seam replacing _dump_rustkmer_stdout.
        dump_jf: Optional seam replacing _dump_jellyfish_stdout.

    Returns:
        True when the two dumps are exactly equal.

    Raises:
        RuntimeError: On non-zero dump exit, empty output, malformed lines,
            or any mismatch (naming the first differing line pair or the
            length difference).
    """
    dump_rk = _dump_rustkmer_stdout if dump_rk is None else dump_rk
    dump_jf = _dump_jellyfish_stdout if dump_jf is None else dump_jf
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rk_text = dump_rk(rkdb_path, rustkmer, workdir)
    jf_text = dump_jf(jf_path, workdir)
    for leftover in ("parity-rk-dump.txt", "parity-jf-dump.txt"):
        try:
            (workdir / leftover).unlink()
        except OSError:
            pass
    rk_sorted = sorted(normalize_dump_lines(rk_text))
    jf_sorted = sorted(normalize_dump_lines(jf_text))
    if rk_sorted == jf_sorted:
        return True
    for position, (rk_line, jf_line) in enumerate(zip(rk_sorted, jf_sorted)):
        if rk_line != jf_line:
            raise RuntimeError(
                f"dump-vs-dump gate: dumps differ at sorted line {position}: "
                f"rustkmer={rk_line!r} vs jellyfish={jf_line!r} — per-k-mer "
                f"parity violated")
    raise RuntimeError(
        f"dump-vs-dump gate: dumps differ in length: rustkmer "
        f"{len(rk_sorted)} lines vs jellyfish {len(jf_sorted)} lines (the "
        f"first {min(len(rk_sorted), len(jf_sorted))} sorted lines agree) — "
        f"per-k-mer parity violated")


def run_comparison_protocol(arm_specs, reps, cooldown_s, rustkmer):
    """Interleaved, counterbalanced, honestly-recorded protocol (BENCH-02).

    One warmup run per tool is executed and discarded before round 1; tool
    order alternates each round; a cooldown sleep separates runs; the two
    tools never run concurrently (memory-pool and core contention — RESEARCH
    anti-pattern); and every measured rep records the cache_state of its own
    actual purge attempt plus its round index and arm-order position.

    Returns (arms_list, round_schedule_dict).
    """
    schedule = round_schedule(reps)
    tools = []
    for spec in arm_specs:
        if spec["tool"] not in tools:
            tools.append(spec["tool"])
    measured = {spec["name"]: {"name": spec["name"], "tool": spec["tool"],
                               "reps": []}
                for spec in arm_specs}
    total_runs = len(tools) + reps * len(arm_specs)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            time.sleep(cooldown_s)

    # One warmup run per tool, executed and discarded before round 1.
    for tool in tools:
        spec = next(s for s in arm_specs if s["tool"] == tool)
        measure(spec["cmd"])
        cooldown_gap()

    for rnd in range(reps):
        position = 0
        for tool in schedule[str(rnd)]:
            for spec in [s for s in arm_specs if s["tool"] == tool]:
                cache_state = attempt_cache_purge()
                rep = measure(spec["cmd"])
                rep["cache_state"] = cache_state
                rep["round"] = rnd
                rep["arm_order"] = position
                measured[spec["name"]]["reps"].append(rep)
                position += 1
                cooldown_gap()

    # Post-protocol stats, sanity assertion, and median/CV reduction per arm.
    arms_out = []
    for spec in arm_specs:
        rec = measured[spec["name"]]
        if spec["tool"] == "jellyfish":
            jf = jellyfish_stats(spec["out"])
            rec["distinct_kmers"] = jf["distinct"]
            rec["total_kmers"] = jf["total"]
        else:
            st = stats(spec["out"], rustkmer)
            rec["distinct_kmers"] = st["unique_kmers"]
            rec["total_kmers"] = st["total_kmers"]
        if rec["distinct_kmers"] <= 0:
            # Silent zero-count trap (Pitfall 1): a tool can exit 0 with an
            # empty database — that is a failure, not a success.
            raise RuntimeError(
                f"arm {rec['name']!r}: distinct_kmers == 0 after "
                f"{spec['cmd']} — silent input failure? (Pitfall 1)")
        rec.update(reduce_arm(rec["reps"]))
        arms_out.append(rec)
    return arms_out, schedule


def measure_arm(name, cmd, reps, rustkmer, out_db):
    """Run one measured arm: reps x measure(), then stats sanity (Pitfall 1)."""
    rep_results = []
    for _ in range(reps):
        rep_results.append(measure(cmd))
    st = stats(out_db, rustkmer)
    if st.get("unique_kmers", 0) <= 0:
        # Silent zero-count trap: a tool can exit 0 with an empty database
        # (e.g. macOS zcat delivering EOF) — that is a failure, not a success.
        raise RuntimeError(
            f"arm {name!r}: unique_kmers == 0 after {cmd} — silent input "
            f"failure? (RESEARCH Pitfall 1)")
    return {
        "name": name,
        "tool": "rustkmer",
        "reps": rep_results,
        "distinct_kmers": st["unique_kmers"],
        "total_kmers": st["total_kmers"],
    }


def run_bench(args):
    """Provision, measure, sanity-assert, emit. Returns the results dict."""
    mode, resolved_inputs = resolve_mode(args.mode, args.input, os.environ)

    out_path = Path(args.out)
    scratch = out_path.parent
    scratch.mkdir(parents=True, exist_ok=True)

    # Disk guardrail (Pitfall 8) — aborts with exit 3 BEFORE any mode=full
    # provisioning or measurement.
    if mode == "full":
        check_disk_floor(scratch, args.disk_floor_gb)

    selections = None
    if mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
    elif mode == "slice":
        merge_src = merge_input_for(mode, args.merge_input)
        if args.slice_selection == "random":
            inputs, selections = provision_random_slice(
                resolved_inputs, args.slice_reads, scratch, args.slice_seed,
                merge_input=merge_src)
        else:
            inputs = provision_slice(resolved_inputs, args.slice_reads, scratch,
                                     merge_input=merge_src)
    else:
        if args.merge_input is not None:
            # Fail loudly rather than silently ignoring the r2 input.
            merge_input_for(mode, args.merge_input)
        inputs = provision_full(resolved_inputs)
    db_a = scratch / "db_count-A.rkdb"
    db_b = scratch / "db_count-B.rkdb"
    db_merged = scratch / "db_merged.rkdb"
    db_merged_t1 = scratch / "db_merged-t1.rkdb"
    jf_a = scratch / "db_jellyfish-A.jf"
    jf_b = scratch / "db_jellyfish-B.jf"
    jf_merged = scratch / "db_jellyfish-merged.jf"

    # Both tools' count commands derive from ONE BenchmarkConfig per input —
    # the fairness matrix in code (matched k/canonical/threads; gz piped for
    # jellyfish only; generous hash_size).
    cfg_a = BenchmarkConfig(k=args.k, canonical=True, threads=args.threads,
                            hash_size=args.hash_size, inputs=[inputs[0]],
                            decompressor=default_decompressor())
    cfg_b = dataclasses.replace(cfg_a, inputs=[inputs[1]])

    comparison = args.reps >= 2
    round_sched = None
    if comparison:
        # Fair-comparison protocol (BENCH-02): jellyfish arms are part of a
        # multi-rep run, so the binary must be present (explicit exit 2).
        require_jellyfish()
        arm_specs = [
            {"name": "count-A", "tool": "rustkmer", "out": db_a,
             "cmd": rustkmer_count_cmd(cfg_a, db_a, args.rustkmer)},
            {"name": "count-B", "tool": "rustkmer", "out": db_b,
             "cmd": rustkmer_count_cmd(cfg_b, db_b, args.rustkmer)},
        ]
        if not args.skip_merge:
            # Merge arms consume their tool's count-arm outputs, so within
            # each tool they stay AFTER every count arm in spec order — the
            # warmup executes the first spec per tool and same-tool arms run
            # in spec order (assert_arm_ordering guards this below).
            arm_specs += [
                {"name": "merge", "tool": "rustkmer", "out": db_merged,
                 "cmd": build_merge_cmd(args.rustkmer, db_merged,
                                        [db_a, db_b])},
                {"name": "merge-t1", "tool": "rustkmer", "out": db_merged_t1,
                 "cmd": build_merge_cmd(args.rustkmer, db_merged_t1,
                                        [db_a, db_b], num_threads=1)},
            ]
        arm_specs += [
            {"name": "jellyfish-count-A", "tool": "jellyfish", "out": jf_a,
             "cmd": jellyfish_count_cmd(cfg_a, jf_a)},
            {"name": "jellyfish-count-B", "tool": "jellyfish", "out": jf_b,
             "cmd": jellyfish_count_cmd(cfg_b, jf_b)},
        ]
        if not args.skip_merge:
            arm_specs.append(
                {"name": "jellyfish-merge", "tool": "jellyfish",
                 "out": jf_merged,
                 "cmd": jellyfish_merge_cmd(jf_merged, [jf_a, jf_b])})
        assert_arm_ordering(arm_specs)
        arms, round_sched = run_comparison_protocol(
            arm_specs, args.reps, args.cooldown_s, args.rustkmer)

        # A timing comparison between tools that counted DIFFERENT things is
        # meaningless — parity is asserted on the measured input itself.
        by_name = {a["name"]: a for a in arms}
        if (by_name["jellyfish-count-A"]["distinct_kmers"]
                != by_name["count-A"]["distinct_kmers"]
                or by_name["jellyfish-count-A"]["total_kmers"]
                != by_name["count-A"]["total_kmers"]):
            raise RuntimeError(
                f"parity failed on the measured input: jellyfish "
                f"distinct={by_name['jellyfish-count-A']['distinct_kmers']} "
                f"total={by_name['jellyfish-count-A']['total_kmers']} vs "
                f"rustkmer unique={by_name['count-A']['distinct_kmers']} "
                f"total={by_name['count-A']['total_kmers']} — methodology "
                f"finding (Pitfall 10), not a comparable measurement")

        # Three-way merge parity gate (MBENCH-02, PARITY-GATE.md): the
        # aggregate pre-gate raises BEFORE any median is trusted when any
        # aggregate invariant fails; the dump-vs-dump deep leg (§4) is the
        # per-k-mer verdict gate on the two merged outputs — exact identity,
        # the defense jellyfish's silent canonicality mixing cannot pass.
        # Both run before the results doc is written/accepted. Guarded on
        # the jellyfish-merge arm being present (a comparison run without
        # --skip-merge); at full scale the deep leg runs inside Phase 12's
        # protocol (MBENCH-02/03 split).
        if "jellyfish-merge" in by_name:
            assert_merge_parity(by_name)
            dump_vs_dump_equal(db_merged, jf_merged, args.rustkmer, scratch)
    else:
        # Single-rep run (CI path): rustkmer-only arms, no jellyfish needed.
        arms = [
            measure_arm("count-A",
                        rustkmer_count_cmd(cfg_a, db_a, args.rustkmer),
                        args.reps, args.rustkmer, db_a),
            measure_arm("count-B",
                        rustkmer_count_cmd(cfg_b, db_b, args.rustkmer),
                        args.reps, args.rustkmer, db_b),
        ]
        if not args.skip_merge:
            arms.append(measure_arm(
                "merge",
                build_merge_cmd(args.rustkmer, db_merged, [db_a, db_b]),
                args.reps, args.rustkmer, db_merged))

    if args.self_check:
        # Exact per-input formula holds only for synthetic input (known
        # reads x length); merge conservation and distinct-union hold for
        # every mode.
        by_name = {a["name"]: a for a in arms}
        if mode == "synthetic":
            expected_total = args.reads * (SYNTHETIC_LENGTH - args.k + 1)
            for name in ("count-A", "count-B"):
                if by_name[name]["total_kmers"] != expected_total:
                    raise RuntimeError(
                        f"self-check: arm {name!r} total_kmers "
                        f"{by_name[name]['total_kmers']} != reads x (L - k + 1)"
                        f" = {expected_total}")
        merged_total = (by_name["count-A"]["total_kmers"]
                        + by_name["count-B"]["total_kmers"])
        for merge_name in ("merge", "merge-t1"):
            if merge_name not in by_name:
                # Merge assertions apply only when the merge arm ran
                # (--skip-merge keeps a run to the counting comparison); the
                # merge-t1 arm, when present, satisfies the same Total-
                # conservation and Distinct-union invariants as merge.
                continue
            if by_name[merge_name]["total_kmers"] != merged_total:
                raise RuntimeError(
                    f"self-check: {merge_name} total_kmers "
                    f"{by_name[merge_name]['total_kmers']} != sum of inputs "
                    f"{merged_total} (count conservation)")
            if by_name[merge_name]["distinct_kmers"] < max(
                    by_name["count-A"]["distinct_kmers"],
                    by_name["count-B"]["distinct_kmers"]):
                raise RuntimeError(
                    f"self-check: {merge_name} distinct_kmers "
                    f"{by_name[merge_name]['distinct_kmers']} < max input "
                    f"distinct ({by_name['count-A']['distinct_kmers']}, "
                    f"{by_name['count-B']['distinct_kmers']})")

    params = {
        "k": args.k,
        "canonical": True,
        "threads": args.threads,
        "rustkmer": str(args.rustkmer),
    }
    if mode == "slice":
        params["slice_selection"] = args.slice_selection
        if args.slice_selection == "random":
            params["slice_seed"] = args.slice_seed
            params["selection_manifests"] = selections
    if comparison:
        params.update({
            "hash_size": args.hash_size,
            "decompressor": default_decompressor(),
            "reps": args.reps,
            "cooldown_s": args.cooldown_s,
            "round_schedule": round_sched,
        })

    results = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "resolved_inputs": [str(p) for p in resolved_inputs],
        "input_fingerprint": [fingerprint(p) for p in inputs],
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "created": datetime.now(timezone.utc).isoformat(),
        "params": params,
        "arms": arms,
        "provenance": binary_provenance(args.rustkmer, "release"),
    }
    validate_schema(results)
    validate_provenance(results)
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
        fh.write("\n")

    for arm in arms:
        rep = arm["reps"][-1]
        line = (f"{arm['name']} [{arm['tool']}]: "
                f"wall={rep['wall_s']:.3f}s "
                f"peak_rss={rep['peak_rss_bytes'] / (1 << 20):.1f}MiB "
                f"distinct={arm['distinct_kmers']} "
                f"total={arm['total_kmers']}")
        if "median_wall_s" in arm:
            cv = arm["cv_wall_pct"]
            line += (f" median_wall={arm['median_wall_s']:.3f}s "
                     f"cv={'n/a' if cv is None else f'{cv:.1f}%'}"
                     f"{' [cv_warning]' if arm['cv_warning'] else ''}")
        print(line)
    print(f"results written to {out_path}")
    return results


# --- 04-04 mechanical report renderer ------------------------------------------
# Contract (threat T-04-07): every MEASUREMENT number in the rendered report
# is read from the results JSONs — the code below carries no measurement
# literals and consults no clock, so a re-render is byte-identical and a
# hand-edited number is detectable. The only external input is the harness
# provenance line, which uses the LAST COMMIT THAT TOUCHED bench.py (stable
# across re-renders even as the repo moves forward — unlike HEAD).

BYTES_PER_GIB = 1 << 30            # display unit constant, not a measurement
COLD_CACHE_SATISFIED_STATES = ("purged", "runner-fresh")


def harness_source_commit():
    """Last commit that touched this file — the harness provenance line.

    Deterministic across re-renders (unrelated commits do not move it), so
    byte-identity holds as the repo advances. Returns 'unknown' outside a
    git checkout (deterministic in that environment too).
    """
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--",
             str(Path(__file__).resolve())],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
    except OSError:
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _gib(num_bytes):
    return num_bytes / BYTES_PER_GIB


def _delta_pct(value, base):
    """Signed percent of `value` relative to `base` (negative = below base)."""
    if base <= 0:
        raise ValueError(f"delta base must be positive, got {base!r}")
    return (value - base) / base * 100.0


def _jellyfish_arm(results):
    arms = [a for a in results["arms"] if a["tool"] == "jellyfish"]
    if not arms:
        raise ValueError("render needs a jellyfish comparison arm "
                         "(results from a --reps >= 2 comparison run)")
    return arms[0]


def _rustkmer_count_arms(results):
    arms = [a for a in results["arms"]
            if a["tool"] == "rustkmer" and a["name"].startswith("count")]
    if not arms:
        raise ValueError("render needs at least one rustkmer count arm")
    return arms


def _results_label(results):
    return f"mode={results['mode']} k={results['params'].get('k')}"


def _rep_series(arm, key, scale=1.0, fmt="{:.2f}"):
    return " / ".join(fmt.format(r[key] / scale) for r in arm["reps"])


def _arm_row(arm, base_arm, merge_base=None):
    """One table row: medians, deltas vs the jellyfish baseline arm, raw reps.

    merge_base (MBENCH-01): the same results file's jellyfish-merge arm when
    one exists — the merge row then carries real deltas against that arm
    instead of the legacy n/a marker. With no jellyfish-merge arm in the
    file the n/a branch is preserved byte-compatibly for committed
    pre-Phase-11 results files.
    """
    wall, rss = arm["median_wall_s"], arm["median_peak_rss_bytes"]
    if arm["name"] == "merge":
        if merge_base is None:
            # No jellyfish counterpart exists for the merge operation — a
            # delta against the jellyfish COUNT arm would be semantically
            # void.
            d_wall = d_rss = "n/a"
        else:
            wall_base = merge_base["median_wall_s"]
            rss_base = merge_base["median_peak_rss_bytes"]
            d_wall = f"{_delta_pct(wall, wall_base):+.1f}%"
            d_rss = f"{_delta_pct(rss, rss_base):+.1f}%"
    elif base_arm is None or arm is base_arm:
        d_wall = d_rss = "baseline"
    else:
        d_wall = f"{_delta_pct(wall, base_arm['median_wall_s']):+.1f}%"
        d_rss = (f"{_delta_pct(rss, base_arm['median_peak_rss_bytes']):+.1f}%")
    cv = arm.get("cv_wall_pct")
    cv_txt = "n/a" if cv is None else f"{cv:.1f}%"
    warn = " **[cv_warning]**" if arm.get("cv_warning") else ""
    return (f"| {arm['name']} | {arm['tool']} | {wall:.2f} | {_gib(rss):.2f} "
            f"| {d_wall} | {d_rss} | {_rep_series(arm, 'wall_s')} "
            f"| {_rep_series(arm, 'peak_rss_bytes', BYTES_PER_GIB)} "
            f"| {cv_txt}{warn} |")


_ARM_TABLE_HEADER = (
    "| arm | tool | median wall (s) | median peak RSS (GiB) "
    "| wall vs jellyfish | RSS vs jellyfish | per-rep wall (s) "
    "| per-rep RSS (GiB) | CV wall |",
    "|-----|------|-----------------|----------------------"
    "|-------------------|------------------|------------------"
    "|-------------------|---------|")


def _count_verdict(results):
    """YES iff every rustkmer count arm's median wall <= jellyfish's.

    'Matches or beats': equal medians count as a match. Conservative across
    multiple rustkmer arms — ALL must satisfy the rule.
    """
    jf = _jellyfish_arm(results)
    rk = _rustkmer_count_arms(results)
    return (all(a["median_wall_s"] <= jf["median_wall_s"] for a in rk),
            [a["median_wall_s"] for a in rk], jf["median_wall_s"])


def _full_table_lines(results, label):
    """Headline/secondary full-scale table + its verdict line."""
    k = results["params"]["k"]
    jf = _jellyfish_arm(results)
    lines = [f"## {label}: k={k} — full-scale counting", ""]
    lines += _ARM_TABLE_HEADER
    for arm in [*_rustkmer_count_arms(results), jf]:
        lines.append(_arm_row(arm, jf))
    verdict, rk_medians, jf_median = _count_verdict(results)
    rk_txt = ", ".join(f"{m:.2f}" for m in rk_medians)
    lines += [
        "",
        (f"**Verdict (k={k}):** rustkmer matches-or-beats jellyfish on "
         f"counting speed — **{'YES' if verdict else 'NO'}** "
         f"(rule: every rustkmer count-arm median wall <= jellyfish median "
         f"wall; rustkmer [{rk_txt}] s vs jellyfish {jf_median:.2f} s). "
         f"Peak-memory deltas are in the table above — memory wins/losses "
         f"are as visible as speed (BENCH-03)."),
        "",
    ]
    return lines, verdict


def _inputs_differ(results):
    """True when the run's two provisioned inputs are different bytes.

    Full mode measures the SAME input twice (identical fingerprints); a
    slice run with --merge-input provisions r1 and r2 slices whose
    sha256 differ. Parity across count arms is only a claim in the first
    arrangement — in the second, count-B measures data no jellyfish arm
    ever saw.
    """
    fps = results.get("input_fingerprint", [])
    if len(fps) < 2:
        return False
    return fps[1]["sha256"] != fps[0]["sha256"]


def _parity_lines(results):
    """Recorded distinct/total equality, paired the way the protocol asserts.

    The harness's parity gate compares jellyfish-count-A vs count-A (the
    same input A). Only that pairing is rendered as a parity claim; further
    rustkmer count arms are either same-input repeats (equality expected)
    or — in a merge-input slice run — measure a different input no jellyfish
    arm saw, which is stated rather than mislabeled a MISMATCH.
    """
    jf = _jellyfish_arm(results)
    count_arms = _rustkmer_count_arms(results)
    lines = []
    arm_a = count_arms[0]
    equal = (arm_a["distinct_kmers"] == jf["distinct_kmers"]
             and arm_a["total_kmers"] == jf["total_kmers"])
    lines.append(
        f"- {_results_label(results)}: {jf['name']} "
        f"distinct={jf['distinct_kmers']:,} total={jf['total_kmers']:,} "
        f"vs {arm_a['name']} distinct={arm_a['distinct_kmers']:,} "
        f"total={arm_a['total_kmers']:,} -> "
        f"{'EQUAL' if equal else 'MISMATCH'}")
    for arm in count_arms[1:]:
        if _inputs_differ(results):
            lines.append(
                f"- {_results_label(results)}: {arm['name']} "
                f"distinct={arm['distinct_kmers']:,} "
                f"total={arm['total_kmers']:,} — its input differs from "
                f"input A (see fingerprints; the r2 side of a merge-input "
                f"run); no jellyfish arm measured it, so this is not a "
                f"parity claim")
        else:
            eq = (arm["distinct_kmers"] == arm_a["distinct_kmers"]
                  and arm["total_kmers"] == arm_a["total_kmers"])
            lines.append(
                f"- {_results_label(results)}: {arm['name']} "
                f"distinct={arm['distinct_kmers']:,} "
                f"total={arm['total_kmers']:,} vs {arm_a['name']} -> "
                f"{'EQUAL' if eq else 'MISMATCH'} (same input measured "
                f"twice)")
    return lines


def _slice_section_lines(results):
    """Slice-scale table incl. the merge arm + conservation checks."""
    k = results["params"]["k"]
    jf = _jellyfish_arm(results)
    count_arms = _rustkmer_count_arms(results)
    lines = [f"## Slice-scale run (k={k}) — counting + merge (r1/r2)", ""]
    lines += _ARM_TABLE_HEADER
    merge_arms = [a for a in results["arms"] if a["name"] == "merge"]
    jf_merge = next((a for a in results["arms"]
                     if a["name"] == "jellyfish-merge"), None)
    for arm in [*count_arms, jf, *merge_arms]:
        lines.append(_arm_row(arm, jf, merge_base=jf_merge))
    lines.append("")
    if merge_arms:
        mg = merge_arms[0]
        sum_total = sum(a["total_kmers"] for a in count_arms)
        max_distinct = max(a["distinct_kmers"] for a in count_arms)
        total_ok = mg["total_kmers"] == sum_total
        distinct_ok = mg["distinct_kmers"] >= max_distinct
        lines += [
            (f"- merge total_kmers {mg['total_kmers']:,} == sum of count-arm "
             f"totals {sum_total:,} -> "
             f"{'EQUAL (count conservation)' if total_ok else 'MISMATCH'}"),
            (f"- merge distinct_kmers {mg['distinct_kmers']:,} >= max input "
             f"distinct {max_distinct:,} -> "
             f"{'OK (distinct union)' if distinct_ok else 'VIOLATED'}"),
            "",
        ]
    else:
        lines.append("- no merge arm recorded in this results file")
        lines.append("")
    return lines


def _cache_summary(results):
    """Per-arm cache_state census, e.g. 'count-A: unavailable x3'."""
    lines = []
    for arm in results["arms"]:
        counts = {}
        for rep in arm["reps"]:
            state = rep.get("cache_state", "absent")
            counts[state] = counts.get(state, 0) + 1
        census = ", ".join(f"{state} x{n}"
                           for state, n in sorted(counts.items()))
        lines.append(f"  - {arm['name']} ({arm['tool']}): {census}")
    return lines


def _all_cache_states(files_data):
    for results in files_data:
        for arm in results["arms"]:
            for rep in arm["reps"]:
                yield rep.get("cache_state", "absent")


def _methodology_lines(files_data):
    """Reps/schedule, cache states, CV flags, -s, decompression asymmetry,
    fingerprints, harness provenance, and the recorded methodology finding."""
    lines = ["## Methodology", ""]
    cold_partial = any(state not in COLD_CACHE_SATISFIED_STATES
                       for state in _all_cache_states(files_data))
    for results in files_data:
        params = results["params"]
        sched = params.get("round_schedule")
        sched_txt = "n/a (single-rep run)"
        if sched:
            sched_txt = "; ".join(
                f"round {rnd}: {' then '.join(order)}"
                for rnd, order in sorted(sched.items()))
        lines += [
            f"### Run {_results_label(results)} "
            f"(created {results['created']})",
            "",
            (f"- reps: {params.get('reps', 1)} measured per arm (one warmup "
             f"per tool executed and discarded before round 0); cooldown "
             f"{params.get('cooldown_s', 0)} s between runs; threads "
             f"{params['threads']}; canonical (-C on both tools)"),
            f"- counterbalanced schedule: {sched_txt}",
            f"- jellyfish `-s {params.get('hash_size', 'n/a')}` "
            f"(generous initial hash; recorded in results)",
            (f"- decompression arrangement: rustkmer reads the .gz natively; "
             f"jellyfish receives `{params.get('decompressor', 'n/a')} | "
             f"jellyfish count ... /dev/stdin` — decompression is inside "
             f"BOTH tools' measured wall; the residual asymmetry (pipe and "
             f"context-switch overhead on the jellyfish arm only) remains "
             f"and is stated here per protocol"),
            "- cache_state per arm:",
            *_cache_summary(results),
            "",
        ]
    if cold_partial:
        lines.append(
            "- **Cold cache: PARTIALLY SATISFIED.** Some measured reps "
            "recorded cache_state other than purged/runner-fresh (the "
            "between-run purge needs sudo and was not run — user-approved "
            "no-sudo execution). The cold-cache wording of the BENCH-02 "
            "methodology is therefore only partially satisfied; the "
            "criterion's evidence is this recording, not a claim.")
        lines.append("")
    cv_flagged = []
    for results in files_data:
        for arm in results["arms"]:
            if arm.get("cv_warning"):
                cv = arm.get("cv_wall_pct")
                cv_txt = "n/a" if cv is None else f"{cv:.1f}%"
                cv_flagged.append(f"{_results_label(results)} arm "
                                  f"{arm['name']}: CV {cv_txt} "
                                  f"(threshold 10%)")
    if cv_flagged:
        lines.append("- cv_warning flags: " + "; ".join(cv_flagged)
                     + " — treat those medians with care")
    else:
        lines.append("- cv_warning flags: none")
    lines.append("")
    lines.append("### Input fingerprints (size + sha256 per file, as recorded)")
    lines.append("")
    for results in files_data:
        for fp in results.get("input_fingerprint") or []:
            lines.append(f"- {_results_label(results)}: `{fp['path']}` "
                         f"({fp['size_bytes']:,} bytes) sha256 "
                         f"`{fp['sha256']}`")
    lines.append("")
    first = files_data[0]
    plat = first["platform"]
    # WR-08: the halt-note figure must come from the first mode=FULL file —
    # files_data[0] is the first file *as given*, which may be a slice file
    # whose (smaller) input size would attach the number to the wrong run.
    # render_report's guard guarantees a mode=full entry exists by the time
    # this builder runs.
    full0 = next(d for d in files_data if d["mode"] == "full")
    fps = full0.get("input_fingerprint") or []
    if not fps:
        raise ValueError(
            f"render needs a non-empty input_fingerprint on the mode=full "
            f"results file (created {full0.get('created')}) to source the "
            f"methodology note's input-size figure")
    fp0 = fps[0]
    # Zero measurement literals (04-04 prohibition P7): the attempt-1 count
    # is un-sourced narrative — no committed JSON carries it — so the note
    # derives its only figure from the fingerprinted input size instead.
    halt_note = (
        "- The first full-run attempt (2026-10-10) halted at the harness's "
        "count-parity gate: rustkmer's single-member gzip decoder silently "
        "read only member 1 of the concatenated-gzip input — a small prefix "
        f"of the {fp0['size_bytes']:,}-byte input fingerprinted below, whose "
        "k-mer count was a tiny fraction of jellyfish's full count. The "
        "parity gate caught it before any timing was trusted. Fixed in "
        "commit `8102985` (MultiGzDecoder + regression test); the results "
        "in this report are from the post-fix attempt 2. This is exactly "
        "the pre-timing parity gate the methodology mandates.")
    lines += [
        "### Harness provenance",
        "",
        f"- harness: `scripts/bench/bench.py` @ git commit "
        f"`{harness_source_commit()}`; results schema_version "
        f"{first['schema_version']}",
        f"- platform (as recorded): {plat['system']} {plat['release']} "
        f"{plat['machine']}, python {plat['python']}",
        f"- rustkmer binary path (as recorded): `{first['params']['rustkmer']}`",
        "",
        "### Recorded methodology finding (attempt 1 of the full run)",
        "",
        halt_note,
        "",
    ]
    return lines


def render_report(results_paths, out_path):
    """Render the milestone Markdown report from committed results JSONs.

    Deterministic by construction: no clock, no render-time measurements, no
    measurement literals — re-rendering the same JSONs reproduces a
    byte-identical file (plan 04-04 Task 3 verify chain).
    """
    files_data = []
    for path in results_paths:
        with open(path) as fh:
            results = json.load(fh)
        validate_schema(results)
        if results["mode"] not in ("full", "slice"):
            raise ValueError(f"render supports mode=full/slice results, "
                             f"got mode={results['mode']!r} in {path}")
        files_data.append(results)
    full_files = [d for d in files_data if d["mode"] == "full"]
    slice_files = [d for d in files_data if d["mode"] == "slice"]
    if not full_files:
        raise ValueError("--render-report needs at least one mode=full "
                         "results file")

    lines = [
        "# rustkmer vs Jellyfish2 — milestone benchmark report",
        "",
        "*Mechanically rendered from the committed results JSONs by "
        "`scripts/bench/bench.py --render-report`. Every measurement below "
        "is read from those JSONs — the renderer contains no measurement "
        "literals — and re-rendering reproduces this file byte-for-byte, so "
        "a hand-edited number is detectable (BENCH-02/T-04-07).*",
        "",
        "## Dataset provenance",
        "",
        "**CRR2044018 is the user-approved substitute for CRR1936095** "
        "(CRR1936095 was absent from this host's disk; the substitution was "
        "approved 2026-10-09). The harness is path-configurable: when "
        "CRR1936095 returns, the same protocol re-runs on it via `--input`.",
        "",
    ]

    verdicts = []
    for i, results in enumerate(full_files):
        label = ("Headline (primary)" if i == 0
                 else "Secondary" if i == 1 else f"Additional #{i + 1}")
        table_lines, verdict = _full_table_lines(results, label)
        lines += table_lines
        verdicts.append((results["params"]["k"], verdict))

    overall = all(v for _, v in verdicts)
    per_k = "; ".join(f"k={k}: {'YES' if v else 'NO'}" for k, v in verdicts)
    lines += [
        "## BENCH-02 verdict (counting speed, from recorded medians)",
        "",
        (f"**{'YES' if overall else 'NO'}** — rustkmer matches-or-beats "
         f"Jellyfish2 on counting speed across the full-scale tables above "
         f"({per_k}; rule: every rustkmer count-arm median wall <= jellyfish "
         f"median wall in every full-scale table). A NO on any k is a valid "
         f"measured outcome and is reported as-is."),
        "",
        "## Count parity evidence (recorded distinct/total equality)",
        "",
    ]
    for results in full_files:
        lines += _parity_lines(results)
    for results in slice_files:
        lines += _parity_lines(results)
    lines.append("")

    for results in slice_files:
        lines += _slice_section_lines(results)

    lines += _methodology_lines(files_data)
    lines += [
        "---",
        "",
        "*Generated file — do not edit by hand. Regenerate with "
        "`python3 scripts/bench/bench.py --render-report --results <jsons> "
        "--out docs/benchmark-report.md`; the evidence JSONs are committed "
        "beside this report under `.planning/phases/04-benchmark-validation/`.",
        "",
    ]

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"report written to {out}")
    return out


def main():
    parser = argparse.ArgumentParser(
        description="rustkmer benchmark harness (stdlib only).")
    parser.add_argument("--mode", choices=["synthetic", "slice", "full"],
                        default=None,
                        help="input mode (default: resolved by the "
                             "degradation ladder; explicit wins)")
    parser.add_argument("--input", default=None,
                        help="input file, glob, or directory (.fq.gz scan) "
                             "for slice/full modes")
    parser.add_argument("--out", default=None,
                        help="results.json output path (with --parity-only, an "
                             "explicit --out also emits a provenance-bearing "
                             "parity record there)")
    parser.add_argument("--self-check", action="store_true",
                        help="assert exact k-mer counts (synthetic mode)")
    parser.add_argument("--k", type=int, default=31, help="k-mer size")
    parser.add_argument("--threads", type=int, default=os.cpu_count(),
                        help="thread count passed to rustkmer")
    parser.add_argument("--reads", type=int, default=200000,
                        help="reads per synthetic input")
    parser.add_argument("--slice-reads", type=int, default=1000000,
                        help="reads per slice in slice mode (deterministic "
                             "first-N extraction)")
    parser.add_argument("--slice-selection", choices=["head", "random"],
                        default="head",
                        help="slice provisioning policy: head = historical "
                             "first-N extraction (default, byte-compatible); "
                             "random = seeded reservoir random-record subslice "
                             "with a sidecar selection manifest (05-04)")
    parser.add_argument("--slice-seed", type=int, default=DEFAULT_SLICE_SEED,
                        help=f"RNG seed for --slice-selection random "
                             f"(default {DEFAULT_SLICE_SEED})")
    parser.add_argument("--parity-reference", default=None,
                        help="after a live parity pass, gate against the "
                             "fingerprint-bound reference record at this path "
                             "(count mismatch exit 1; unbound/ambiguous/"
                             "missing recipe exit 2). Requires --parity-only.")
    parser.add_argument("--capture-parity-reference", default=None,
                        help="after a live parity pass, append a reference "
                             "record to this path (the head-4M recipe asserts "
                             "the pinned constants first). Requires "
                             "--parity-only.")
    parser.add_argument("--reps", type=int, default=1,
                        help="repetitions per arm; N >= 2 engages the "
                             "fair-comparison protocol (jellyfish arms, "
                             "counterbalanced interleaved rounds, medians)")
    parser.add_argument("--hash-size", default=DEFAULT_HASH_SIZE,
                        help="jellyfish -s initial hash size (generous by "
                             "default — undersizing silently penalizes the "
                             "comparator, Pitfall 4; recorded in results.json)")
    parser.add_argument("--cooldown-s", type=int, default=DEFAULT_COOLDOWN_S,
                        help="cooldown sleep in seconds between measured "
                             "runs (thermal/order-bias defense, Pitfall 5)")
    parser.add_argument("--disk-floor-gb", type=int,
                        default=DEFAULT_DISK_FLOOR_GB,
                        help="abort mode=full runs (exit 3) when free space "
                             "on the output volume is below this floor in "
                             "GiB (Pitfall 8)")
    parser.add_argument("--parity-only", action="store_true",
                        help="count the same input with rustkmer and "
                             "jellyfish, assert equal Distinct/Total, and "
                             "exit before any timing comparison")
    parser.add_argument("--merge-input", default=None,
                        help="slice mode only: provision the second slice "
                             "from this gz input instead of a second resolved "
                             "input — the r1/r2 merge arrangement (04-04)")
    parser.add_argument("--skip-merge", action="store_true",
                        help="omit the merge arm (04-04 full runs are "
                             "counting comparisons; merge is measured at "
                             "slice scale)")
    parser.add_argument("--render-report", action="store_true",
                        help="render the milestone Markdown report from "
                             "committed results JSONs (--results, one or "
                             "more) to --out; deterministic, no measurement "
                             "literals — re-render is byte-identical "
                             "(04-04 Task 3, T-04-07)")
    parser.add_argument("--results", nargs="+", default=None,
                        help="results.json paths for --render-report "
                             "(mode=full files render as comparison tables "
                             "in the order given; mode=slice files render "
                             "the slice+merge section)")
    parser.add_argument("--rustkmer", default="target/release/rustkmer",
                        help="path to the rustkmer RELEASE binary")
    args = parser.parse_args()

    # --out keeps its historical default; an EXPLICIT --out additionally
    # enables parity-record emission under --parity-only (05-04).
    out_explicit = args.out is not None
    if args.out is None:
        args.out = str(DEFAULT_SCRATCH / "results.json")

    if args.k < 1 or args.k > 64:
        parser.error("--k must be in 1..64")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.reads < 1:
        parser.error("--reads must be >= 1")
    if args.slice_reads < 1:
        parser.error("--slice-reads must be >= 1")
    if not HASH_SIZE_RE.match(str(args.hash_size)):
        parser.error("--hash-size must match ^\\d+[KMG]?$ (e.g. 10G, 100M, "
                     "1000000)")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")
    if args.disk_floor_gb < 0:
        parser.error("--disk-floor-gb must be >= 0")
    if args.parity_reference and args.capture_parity_reference:
        parser.error("--parity-reference and --capture-parity-reference are "
                     "mutually exclusive")
    if ((args.parity_reference or args.capture_parity_reference)
            and not args.parity_only):
        parser.error("--parity-reference / --capture-parity-reference "
                     "require --parity-only")

    if args.render_report:
        if not args.results:
            parser.error("--render-report requires --results "
                         "(one or more results.json paths)")
        render_report(args.results, args.out)
        return

    if args.parity_only:
        run_parity_cli(args, out_explicit)
        return

    run_bench(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — harness fails loudly, no traceback noise
        print(f"bench.py: {exc}", file=sys.stderr)
        sys.exit(1)
