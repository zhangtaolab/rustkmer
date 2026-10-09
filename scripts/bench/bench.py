#!/usr/bin/env python3
"""rustkmer benchmark harness core (BENCH-01/03/04).

Measures `rustkmer count` and `rustkmer merge` wall-clock and peak RSS via
/usr/bin/time, emits a schema-versioned results.json, and sanity-asserts that
every measured run actually counted k-mers (RESEARCH Pitfall 1: a silent
zero-count success must abort the harness).

Every headline number comes from a --release binary (never a debug build) and
from OS rusage accounting (never a harness-internal clock). Python 3.10+
stdlib only — no third-party imports, no pip installs.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
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


def build_count_cmd(rustkmer, k, threads, out_db, inputs):
    """rustkmer count command (list form).

    Inputs are passed via -i (num_args = 1.., per src/cli/args.rs) — they are
    NOT positional arguments.
    """
    return [str(rustkmer), "count", "-k", str(k), "-C",
            "--threads", str(threads), "-o", str(out_db),
            "-i", *[str(p) for p in inputs]]


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


def provision_slice(resolved_inputs, slice_reads, scratch):
    """Provision two slice inputs (first two resolved sources; a single
    source is extracted once and measured twice)."""
    if not resolved_inputs:
        raise RuntimeError("slice mode requires a resolved input")
    scratch.mkdir(parents=True, exist_ok=True)
    srcs = resolved_inputs[:2] if len(resolved_inputs) >= 2 \
        else [resolved_inputs[0], resolved_inputs[0]]
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

    if mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
    elif mode == "slice":
        inputs = provision_slice(resolved_inputs, args.slice_reads, scratch)
    else:
        inputs = provision_full(resolved_inputs)
    db_a = scratch / "db_count-A.rkdb"
    db_b = scratch / "db_count-B.rkdb"
    db_merged = scratch / "db_merged.rkdb"

    arms = [
        measure_arm("count-A",
                    build_count_cmd(args.rustkmer, args.k, args.threads,
                                    db_a, [inputs[0]]),
                    args.reps, args.rustkmer, db_a),
        measure_arm("count-B",
                    build_count_cmd(args.rustkmer, args.k, args.threads,
                                    db_b, [inputs[1]]),
                    args.reps, args.rustkmer, db_b),
        measure_arm("merge",
                    build_merge_cmd(args.rustkmer, db_merged, [db_a, db_b]),
                    args.reps, args.rustkmer, db_merged),
    ]

    if args.self_check:
        # Exact per-input formula holds only for synthetic input (known
        # reads x length); merge conservation and distinct-union hold for
        # every mode.
        if mode == "synthetic":
            expected_total = args.reads * (SYNTHETIC_LENGTH - args.k + 1)
            for arm in (arms[0], arms[1]):
                if arm["total_kmers"] != expected_total:
                    raise RuntimeError(
                        f"self-check: arm {arm['name']!r} total_kmers "
                        f"{arm['total_kmers']} != reads x (L - k + 1) = "
                        f"{expected_total}")
        merged_total = arms[0]["total_kmers"] + arms[1]["total_kmers"]
        if arms[2]["total_kmers"] != merged_total:
            raise RuntimeError(
                f"self-check: merged total_kmers {arms[2]['total_kmers']} != "
                f"sum of inputs {merged_total} (count conservation)")
        if arms[2]["distinct_kmers"] < max(arms[0]["distinct_kmers"],
                                           arms[1]["distinct_kmers"]):
            raise RuntimeError(
                "self-check: merged distinct_kmers "
                f"{arms[2]['distinct_kmers']} < max input distinct "
                f"({arms[0]['distinct_kmers']}, {arms[1]['distinct_kmers']})")

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
        "params": {
            "k": args.k,
            "canonical": True,
            "threads": args.threads,
            "rustkmer": str(args.rustkmer),
        },
        "arms": arms,
    }
    validate_schema(results)
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
        fh.write("\n")

    for arm in arms:
        rep = arm["reps"][-1]
        print(f"{arm['name']}: wall={rep['wall_s']:.3f}s "
              f"peak_rss={rep['peak_rss_bytes'] / (1 << 20):.1f}MiB "
              f"distinct={arm['distinct_kmers']} total={arm['total_kmers']}")
    print(f"results written to {out_path}")
    return results


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
                        help="repetitions per arm (multi-rep protocol is "
                             "04-02's scope)")
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

    run_bench(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — harness fails loudly, no traceback noise
        print(f"bench.py: {exc}", file=sys.stderr)
        sys.exit(1)
