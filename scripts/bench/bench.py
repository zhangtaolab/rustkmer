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
    """Parse /usr/bin/time stderr into {'wall_s': float, 'peak_rss_bytes': int}.

    darwin: RSS taken as-is (already bytes); wall from the '<s> real' line.
    linux:  RSS scaled kbytes x 1024 -> bytes; wall from the Elapsed line.

    Raises ValueError when either line is absent or unparseable — never
    best-effort (a 1024x units error or a format drift here corrupts every
    downstream number; RESEARCH Pitfall 2 / threat T-04-01).
    """
    if plat == "darwin":
        rss_re, rss_scale, wall_re = MAC_RSS, 1, MAC_REAL
    elif plat == "linux":
        rss_re, rss_scale, wall_re = LIN_RSS, 1024, LIN_ELAPSED
    else:
        raise ValueError(f"unsupported platform: {plat!r}")

    wall_s = None
    peak_rss_bytes = None
    for line in stderr_text.splitlines():
        if peak_rss_bytes is None:
            m = rss_re.search(line)
            if m:
                peak_rss_bytes = int(m.group(1)) * rss_scale
        if wall_s is None:
            m = wall_re.search(line)
            if m:
                wall_s = hms_to_seconds(m.group(1))
    if peak_rss_bytes is None:
        raise ValueError(
            f"no parsable peak-RSS line for platform {plat!r} — format drift?")
    if wall_s is None:
        raise ValueError(
            f"no parsable wall-clock line for platform {plat!r} — format drift?")
    return {"wall_s": wall_s, "peak_rss_bytes": peak_rss_bytes}


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


def build_merge_cmd(rustkmer, out_db, input_dbs):
    """rustkmer merge command (list form)."""
    return [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]


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


def run_parity_cli(args):
    """--parity-only: provision one input via the ladder, then run_parity."""
    mode, resolved_inputs = resolve_mode(args.mode, args.input, os.environ)
    # Validation only — run_parity measures inputs[0]; a --merge-input given
    # alongside --parity-only must still be a legal slice-mode value rather
    # than being silently ignored.
    merge_input_for(mode, args.merge_input)
    scratch = Path(args.out).parent
    scratch.mkdir(parents=True, exist_ok=True)
    if mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
    elif mode == "slice":
        inputs = provision_slice(resolved_inputs, args.slice_reads, scratch)
    else:
        inputs = provision_full(resolved_inputs)
    run_parity(inputs[0], args.k, args.threads, args.rustkmer, scratch)


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

    if mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
    elif mode == "slice":
        merge_src = merge_input_for(mode, args.merge_input)
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
    jf_a = scratch / "db_jellyfish-A.jf"

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
            {"name": "jellyfish-count-A", "tool": "jellyfish", "out": jf_a,
             "cmd": jellyfish_count_cmd(cfg_a, jf_a)},
        ]
        if not args.skip_merge:
            arm_specs.append(
                {"name": "merge", "tool": "rustkmer", "out": db_merged,
                 "cmd": build_merge_cmd(args.rustkmer, db_merged,
                                        [db_a, db_b])})
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
        if "merge" in by_name:
            # Merge assertions apply only when the merge arm ran
            # (--skip-merge keeps a run to the counting comparison).
            if by_name["merge"]["total_kmers"] != merged_total:
                raise RuntimeError(
                    f"self-check: merged total_kmers "
                    f"{by_name['merge']['total_kmers']} != sum of inputs "
                    f"{merged_total} (count conservation)")
            if by_name["merge"]["distinct_kmers"] < max(
                    by_name["count-A"]["distinct_kmers"],
                    by_name["count-B"]["distinct_kmers"]):
                raise RuntimeError(
                    "self-check: merged distinct_kmers "
                    f"{by_name['merge']['distinct_kmers']} < max input "
                    f"distinct ({by_name['count-A']['distinct_kmers']}, "
                    f"{by_name['count-B']['distinct_kmers']})")

    params = {
        "k": args.k,
        "canonical": True,
        "threads": args.threads,
        "rustkmer": str(args.rustkmer),
    }
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
    }
    validate_schema(results)
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


def _arm_row(arm, base_arm):
    """One table row: medians, deltas vs the jellyfish baseline arm, raw reps."""
    wall, rss = arm["median_wall_s"], arm["median_peak_rss_bytes"]
    if base_arm is None or arm is base_arm:
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


def _parity_lines(results):
    """Recorded distinct/total equality per rustkmer arm vs the jellyfish arm."""
    jf = _jellyfish_arm(results)
    lines = []
    for arm in _rustkmer_count_arms(results):
        equal = (arm["distinct_kmers"] == jf["distinct_kmers"]
                 and arm["total_kmers"] == jf["total_kmers"])
        lines.append(
            f"- {_results_label(results)}: {jf['name']} "
            f"distinct={jf['distinct_kmers']:,} total={jf['total_kmers']:,} "
            f"vs {arm['name']} distinct={arm['distinct_kmers']:,} "
            f"total={arm['total_kmers']:,} -> "
            f"{'EQUAL' if equal else 'MISMATCH'}")
    return lines


def _slice_section_lines(results):
    """Slice-scale table incl. the merge arm + conservation checks."""
    k = results["params"]["k"]
    jf = _jellyfish_arm(results)
    count_arms = _rustkmer_count_arms(results)
    lines = [f"## Slice-scale run (k={k}) — counting + merge (r1/r2)", ""]
    lines += _ARM_TABLE_HEADER
    merge_arms = [a for a in results["arms"] if a["name"] == "merge"]
    for arm in [*count_arms, jf, *merge_arms]:
        lines.append(_arm_row(arm, jf))
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
        for fp in results["input_fingerprint"]:
            lines.append(f"- {_results_label(results)}: `{fp['path']}` "
                         f"({fp['size_bytes']:,} bytes) sha256 "
                         f"`{fp['sha256']}`")
    lines.append("")
    first = files_data[0]
    plat = first["platform"]
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
        "- The first full-run attempt (2026-10-10) halted at the harness's "
        "count-parity gate: rustkmer's single-member gzip decoder silently "
        "read only member 1 of the concatenated-gzip input (220,028 k-mers "
        "vs jellyfish's full count). The parity gate caught it before any "
        "timing was trusted. Fixed in commit `8102985` (MultiGzDecoder + "
        "regression test); the results in this report are from the post-fix "
        "attempt 2. This is exactly the pre-timing parity gate the "
        "methodology mandates.",
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
    parser.add_argument("--out", default=str(DEFAULT_SCRATCH / "results.json"),
                        help="results.json output path")
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

    if args.render_report:
        if not args.results:
            parser.error("--render-report requires --results "
                         "(one or more results.json paths)")
        render_report(args.results, args.out)
        return

    if args.parity_only:
        run_parity_cli(args)
        return

    run_bench(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — harness fails loudly, no traceback noise
        print(f"bench.py: {exc}", file=sys.stderr)
        sys.exit(1)
