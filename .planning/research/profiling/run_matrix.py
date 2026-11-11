#!/usr/bin/env python3
"""v2.0 root-cause profiling matrix runner.

Measurement discipline mirrors scripts/bench/bench.py (v1.0):
- /usr/bin/time -l, macOS peak RSS in BYTES
- wall = 'real' seconds from time(1)
- list-form argv (no shell) except the jellyfish gz pipe arm (sh -c),
  exactly as the v1.0 harness did
- rustkmer internal phase timestamps parsed from stderr:
  'Elapsed time: X seconds' fires AFTER counting, BEFORE output;
  'Total time: Y seconds' fires at the end -> output phase = Y - X.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/tmp/rkmer-v2-prof")
RK = "/Users/forrest/GitHub/rustkmer/target/release/rustkmer"
JF = "/opt/homebrew/bin/jellyfish"
FQ = str(ROOT / "data/slice4M.fq")
GZ = str(ROOT / "data/slice4M.fq.gz")
RESULTS = ROOT / "results.jsonl"

MAC_REAL = re.compile(r"^\s*([\d.]+)\s+real")
MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size")
RK_ELAPSED = re.compile(r"Elapsed time:\s+([\d.]+) seconds")
RK_TOTAL = re.compile(r"Total time:\s+([\d.]+) seconds")


def run(label, argv, threads, note=""):
    log = ROOT / "logs" / f"{label}.log"
    t0 = time.monotonic()
    proc = subprocess.run(
        ["/usr/bin/time", "-l", *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    outer_wall = time.monotonic() - t0
    err = proc.stderr
    log.write_text(err + "\n---STDOUT---\n" + proc.stdout)
    wall = rss = None
    for line in err.splitlines():
        m = MAC_REAL.search(line)
        if m and wall is None:
            wall = float(m.group(1))
        m = MAC_RSS.search(line)
        if m and rss is None:
            rss = int(m.group(1))
    rec = {
        "label": label,
        "argv": argv,
        "threads": threads,
        "note": note,
        "rc": proc.returncode,
        "wall_s": wall,
        "outer_wall_s": round(outer_wall, 2),
        "peak_rss_bytes": rss,
        "peak_rss_gib": round(rss / 2**30, 2) if rss else None,
    }
    el = RK_ELAPSED.findall(err)
    tot = RK_TOTAL.findall(err)
    if el:
        rec["rk_count_phase_s"] = float(el[-1])
    if tot:
        rec["rk_total_s"] = float(tot[-1])
    if el and tot:
        rec["rk_output_phase_s"] = round(float(tot[-1]) - float(el[-1]), 2)
    with RESULTS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(
        f"{label:26s} rc={proc.returncode} wall={wall}s rss={rec['peak_rss_gib']}GiB "
        f"count_phase={rec.get('rk_count_phase_s')} output_phase={rec.get('rk_output_phase_s')}",
        flush=True,
    )
    if proc.returncode != 0:
        print(f"  FAILED {label}; see {log}", flush=True)
    time.sleep(3)  # cooldown between arms (v1.0 used 5s)
    return rec


def rk(label, k, src, threads, extra=(), note=""):
    out = str(ROOT / "out" / f"{label}.rkdb")
    argv = [RK, "count", "-k", str(k), "-C", "--threads", str(threads),
            "-i", src, "-o", out, *extra]
    return run(label, argv, threads, note)


def jf(label, k, src, threads, size="2G", note=""):
    out = str(ROOT / "out" / f"{label}.jf")
    common = [JF, "count", "-m", str(k), "-s", size, "-t", str(threads),
              "-C", "-o", out]
    if src.endswith(".gz"):
        argv = ["sh", "-c", f"gzcat {src} | {' '.join(common)} /dev/stdin"]
    else:
        argv = [*common, src]
    return run(label, argv, threads, note)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "main"):
        # Core comparison: same slice, same threads, canonical both sides.
        rk("rk21-gz-t16", 21, GZ, 16, note="v1.0-style: native gz, default --size 1M")
        rk("rk31-gz-t16", 31, GZ, 16)
        jf("jf21-gz-t16", 21, GZ, 16, note="v1.0-style: gzcat pipe, -s 2G")
        jf("jf31-gz-t16", 31, GZ, 16)
        # Hypothesis (a): decompression — raw FASTQ vs gz.
        rk("rk21-fq-t16", 21, FQ, 16)
        rk("rk31-fq-t16", 31, FQ, 16)
        jf("jf21-fq-t16", 21, FQ, 16, note="decompression excluded reference")
        # Decompression floor alone.
        run("gzcat-only", ["sh", "-c", f"gzcat {GZ} > /dev/null"], 1,
            note="pure single-thread decompression floor")
    if which in ("all", "scaling"):
        # Hypothesis (b): thread scaling on raw input (no decompression).
        rk("rk21-fq-t1", 21, FQ, 1)
        rk("rk21-fq-t4", 21, FQ, 4)
        rk("rk21-fq-t8", 21, FQ, 8)
        rk("rk21-gz-t1", 21, GZ, 1)
    if which in ("all", "extras"):
        # Output-phase isolation: skip the sort.
        rk("rk21-fq-t16-nosort", 21, FQ, 16, extra=["--no-sort"])
        # Rehash isolation: presize the DashMap.
        rk("rk21-fq-t16-size500M", 21, FQ, 16, extra=["--size", "500000000"])
    print("DONE", flush=True)


if __name__ == "__main__":
    main()