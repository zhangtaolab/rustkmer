#!/usr/bin/env python3
"""Lib-aware aggregation of a samply processed profile (column tables).

Resolves rustkmer-lib RVAs against `nm` of the binary; labels system-lib
frames by library. Produces self-time, inclusive-time, and a category
rollup that answers: where does counting CPU go?

Usage: python3 -I analyze_profile.py profile.json.gz [--top 30]
"""
import bisect
import gzip
import json
import subprocess
import sys
from collections import defaultdict

BIN = "/Users/forrest/GitHub/rustkmer/target/release/rustkmer"
BASE = 0x100000000


def load_syms():
    out = subprocess.run(["nm", "-n", BIN], capture_output=True, text=True).stdout
    syms = []
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 3 and p[1] in ("T", "t"):
            syms.append((int(p[0], 16), p[2]))
    syms.sort()
    return [a for a, _ in syms], syms


def load(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        return json.load(f)


def categorize(name):
    n = name.lower()
    if "libsystem_kernel" in n:
        return "kernel wait/spin/syscall"
    if "libsystem_pthread" in n:
        return "pthread lock/cond"
    if "libz" in n:
        return "gzip inflate (libz)"
    if "libsystem_malloc" in n:
        return "malloc/free"
    if "libsystem_platform" in n:
        return "platform (memcpy/bzero)"
    if "increment" in n or "dashmap" in n or "hashbrown" in n or "ahash" in n:
        return "DashMap increment/hash"
    if "process_one_record" in n or "encode_kmer" in n or "canonical" in n or "reverse_complement" in n:
        return "encode+canonical (per-window)"
    if "rayon" in n or "join_context" in n or "bridge_producer" in n or "registry" in n or "latch" in n:
        return "rayon fork-join plumbing"
    if "sort" in n or "get_all_counts" in n or "get_filtered" in n or "write_to" in n or "kmerentry" in n or "from_kmer_pairs" in n:
        return "output collect/sort/write"
    if "bio" in n or "fastq" in n or "read_line" in n or "read_until" in n:
        return "FASTQ parse (bio)"
    if "flate2" in n or "multigz" in n or "decompress" in n:
        return "flate2 decoder"
    return "other"


def main():
    path = sys.argv[1]
    topn = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    addrs, syms = load_syms()
    prof = load(path)
    libs = [l["name"] for l in prof["libs"]]
    total = 0
    self_c = defaultdict(int)
    cat_c = defaultdict(int)
    incl_c = defaultdict(int)
    per_thread = []
    for th in prof["threads"]:
        strings = th["stringArray"]
        fname = th["funcTable"]["name"]
        fresource = th["funcTable"]["resource"]
        res_lib = th["resourceTable"]["lib"]
        frame_func = th["frameTable"]["func"]
        sp = th["stackTable"]["prefix"]
        sf = th["stackTable"]["frame"]
        s = th["samples"]
        # precompute resolved name per func
        resolved = []
        for i in range(len(fname)):
            raw = strings[fname[i]]
            ridx = fresource[i]
            lib = libs[res_lib[ridx]] if ridx is not None and ridx >= 0 else "?"
            if lib == "rustkmer" and raw.startswith("0x"):
                va = BASE + int(raw, 16)
                j = bisect.bisect_right(addrs, va) - 1
                resolved.append(syms[j][1] if j >= 0 else raw)
            elif raw.startswith("0x"):
                resolved.append(f"{lib}+{raw}")
            else:
                resolved.append(raw)
        n = 0
        tself = defaultdict(int)
        weights = s["weight"] if s.get("weight") else [1] * s["length"]
        for sidx, w in zip(s["stack"], weights):
            if sidx is None or sidx < 0:
                continue
            n += w
            frames = []
            cur = sidx
            while cur is not None and cur >= 0:
                frames.append(resolved[frame_func[sf[cur]]])
                cur = sp[cur]
            leaf = frames[0]
            self_c[leaf] += w
            tself[leaf] += w
            cat_c[categorize(leaf)] += w
            seen = set()
            for name in frames:
                if name not in seen:
                    incl_c[name] += w
                    seen.add(name)
        total += n
        per_thread.append((th.get("name", "?"), n, tself))
    print(f"TOTAL WEIGHTED SAMPLES (~ms CPU): {total}")
    print("\nCATEGORY ROLLUP (by SELF/leaf frame):")
    for name, c in sorted(cat_c.items(), key=lambda kv: -kv[1]):
        print(f"  {100.0*c/total:6.2f}%  {c:9d}  {name}")
    print("\nPER-THREAD ON-CPU (~ms):")
    for name, n, tself in sorted(per_thread, key=lambda x: -x[1])[:4]:
        top3 = sorted(tself.items(), key=lambda kv: -kv[1])[:3]
        top3s = "; ".join(f"{categorize(k)}:{v}" for k, v in top3)
        print(f"  {name[:24]:24s} n={n:8d} ({100.0*n/total:4.1f}%)  {top3s}")
    print(f"\nTOP {topn} SELF (resolved):")
    for name, c in sorted(self_c.items(), key=lambda kv: -kv[1])[:topn]:
        print(f"  {100.0*c/total:6.2f}%  {c:9d}  [{categorize(name)}]  {name[:110]}")


if __name__ == "__main__":
    main()