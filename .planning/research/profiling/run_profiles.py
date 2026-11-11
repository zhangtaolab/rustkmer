#!/usr/bin/env python3
"""samply profiling runs (after the clean matrix finishes)."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/tmp/rkmer-v2-prof")
RK = "/Users/forrest/GitHub/rustkmer/target/release/rustkmer"
SAMPLY = "/Users/forrest/.cargo/bin/samply"
FQ = str(ROOT / "data/slice4M.fq")
GZ = str(ROOT / "data/slice4M.fq.gz")


def prof(label, k, src, threads):
    out = str(ROOT / "profiles" / f"{label}.json.gz")
    rkdb = str(ROOT / "out" / f"{label}.rkdb")
    argv = [SAMPLY, "record", "--save-only", "--rate", "1000", "-o", out, "--",
            RK, "count", "-k", str(k), "-C", "--threads", str(threads),
            "-i", src, "-o", rkdb]
    t0 = time.monotonic()
    p = subprocess.run(argv, capture_output=True, text=True)
    dt = time.monotonic() - t0
    (ROOT / "logs" / f"{label}.log").write_text(p.stderr + "\n---\n" + p.stdout)
    print(f"{label}: rc={p.returncode} wall={dt:.1f}s -> {out}", flush=True)
    time.sleep(3)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "p1"):
        prof("prof21-gz-t16", 21, GZ, 16)
    if which in ("all", "p2"):
        prof("prof21-fq-t16", 21, FQ, 16)
    if which in ("all", "p3"):
        prof("prof21-fq-t1", 21, FQ, 1)
    if which in ("all", "p4"):
        prof("prof31-fq-t16", 31, FQ, 16)
    print("PROFILES DONE", flush=True)


if __name__ == "__main__":
    main()