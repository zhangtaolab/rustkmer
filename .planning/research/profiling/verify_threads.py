#!/usr/bin/env python3
"""Verify whether --threads actually controls the rayon pool size.

Runs rustkmer count --threads N on a small slice, samples the live process
with macOS `sample` (no sudo), and counts the OS threads. Repeats for N=1,4.
"""
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/tmp/rkmer-v2-prof")
RK = "/Users/forrest/GitHub/rustkmer/target/release/rustkmer"
SMALL = str(ROOT / "data/slice200k.fq")


def check(n):
    out = str(ROOT / "out" / f"threadcheck{n}.rkdb")
    p = subprocess.Popen(
        [RK, "count", "-k", "21", "-C", "--threads", str(n), "-i", SMALL, "-o", out],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(4)  # let it enter the counting phase
    if p.poll() is not None:
        print(f"--threads {n}: process already exited (too fast to sample)")
        return
    s = subprocess.run(["sample", str(p.pid), "1"], capture_output=True, text=True)
    txt = s.stdout
    # sample writes analysis to a file; find it
    m = re.search(r"written to file (\S+)", txt)
    if m:
        txt = Path(m.group(1)).read_text()
    threads = len(re.findall(r"^\s*\d+ Thread_", txt, re.M))
    print(f"--threads {n}: OS threads observed = {threads} (expected ~{n + 1} incl. main)")
    p.wait()


def main():
    # small slice: 200k reads
    if not Path(SMALL).exists():
        with open(SMALL, "wb") as out:
            subprocess.run(["head", "-n", "800000", str(ROOT / "data/slice4M.fq")],
                           stdout=out, check=True)
    check(1)
    check(4)


if __name__ == "__main__":
    main()