#!/usr/bin/env python3
"""Post-matrix: count parity (rk vs jf) + distinct/total extraction for all arms."""
import json
import subprocess
from pathlib import Path

ROOT = Path("/tmp/rkmer-v2-prof")
RK = "/Users/forrest/GitHub/rustkmer/target/release/rustkmer"
JF = "/opt/homebrew/bin/jellyfish"


def rk_stats(path):
    p = subprocess.run([RK, "stats", "-f", "json", str(path)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return {"error": p.stderr[:300]}
    return json.loads(p.stdout)


def jf_stats(path):
    p = subprocess.run([JF, "stats", str(path)], capture_output=True, text=True)
    out = {}
    for line in p.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip().split()[0]
            if v.isdigit():
                out[k.strip().lower()] = int(v)
    return out


def main():
    pairs = [
        ("rk21-gz-t16.rkdb", "jf21-gz-t16.jf"),
        ("rk21-fq-t16.rkdb", "jf21-fq-t16.jf"),
    ]
    report = {}
    for rkdb, jf in pairs:
        rp, jp = ROOT / "out" / rkdb, ROOT / "out" / jf
        if not rp.exists() or not jp.exists():
            print(f"SKIP {rkdb} / {jf} (missing)")
            continue
        r, j = rk_stats(rp), jf_stats(jp)
        print(f"== {rkdb} vs {jf}")
        print("  rk:", json.dumps(r))
        print("  jf:", json.dumps(j))
        report[rkdb] = {"rk": r, "jf": j}
    # also stats for the other rkdb outputs (distinct/total record)
    for rp in sorted((ROOT / "out").glob("*.rkdb")):
        if rp.name in report:
            continue
        r = rk_stats(rp)
        print(f"== {rp.name}: {json.dumps(r)}")
        report[rp.name] = {"rk": r}
    (ROOT / "parity_report.json").write_text(json.dumps(report, indent=1))
    print("saved parity_report.json")


if __name__ == "__main__":
    main()