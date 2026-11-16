#!/usr/bin/env python3
"""Two-point merge-characterization ladder (Plan 11-06, D-07/D-08/D-09).

Characterizes `jellyfish merge` AND `rustkmer merge` on real-data slice
pairs at intermediate scale: two rungs pinned at N=3,500,000 (~10% of part
scale) and N=14,000,000 (~40%) reads per slice, at both k=21 and k=31.
Every rung runs the COMPLETE prepare -> count -> merge chain per side —
the ladder is the first live exercise of the slice-provisioning +
prepare-stage logic on real data (D-08), deliberately, so harness bugs
surface here and not mid-session.

Slices are provisioned via `random_slice.reservoir_slice` with the pinned
seed 4242 — one slice from part_001 and one from part_006 per rung (the
pinned merge arrangement). Ladder scratch lives OUTSIDE the repo by
default (/tmp/rustkmer-phase11/ladder; D-03 discipline, the Plan 11-02
`refuse_repo_root` guard is reused and any in-repo scratch is refused).

Per rung x k x tool the evidence records the merge wall and peak bytes
from `/usr/bin/time` (never harness-internal clocks), output sizes
(.rkdb and .jf bytes), entry counts (distinct/total, SUM-OF-COUNTS
definition), the honest per-rep cache_state, the rustkmer merge route
attribution IF the tool reports one on stderr (else honestly recorded as
"not-reported" — no Rust changes this phase), and full provenance.

Before any rung record is accepted the PARITY-GATE.md legs execute at
rung scale: the aggregate conservation legs (assert_merge_parity) at
every rung, and the dump-vs-dump deep leg at the 10% rung where dumps
are cheap. A rung whose slice count yields distinct or total 0 aborts
the rung loud (zero-entry protection, probe MBENCH-01/empty semantics).

The output `.planning/phases/11-merge-characterization-harness-prep/
11-LADDER-RESULTS.json` is an evidence document of its own kind
(`merge-characterization-ladder`) — NEVER a fork of the bench results
schema v1 (MBENCH-05 boundary). Its summary carries per tool-k fitted
wall-per-entry slopes, measured output bytes per entry, the coarse
linearity check (a wall-per-entry ratio beyond 2x between the 10% and
40% rungs is flagged as a recorded non-linearity finding for MBENCH-04's
full-scale backstop, never silently smoothed), and the extrapolated
full-scale merge wall WITH the caveat that no slice-scale number is a
full-scale prediction without naming that backstop (milestone Pitfall
14). RSS is recorded as context, never as a decision axis — jellyfish
merge is a streaming comparator (~6.8 MB RSS); there is no memory-win
framing anywhere in this harness.

Verbs: --run (execute the ladder), --summarize (recompute the summary
block of an existing evidence JSON from its rung records, idempotent).

Python 3.11+ stdlib only — no third-party imports, no pip installs (the
bench-harness stdlib-only contract, bench.py:25-26).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution needs the checkout root for the scripts package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    BenchmarkConfig,
    assert_merge_parity,
    attempt_cache_purge,
    binary_provenance,
    build_merge_cmd,
    fingerprint,
    jellyfish_count_cmd,
    jellyfish_merge_cmd,
    jellyfish_stats,
    parse_time_output,
    rustkmer_count_cmd,
    stats,
)
from scripts.bench.prepare_inputs import (
    DEFAULT_DATA_DIR,
    DEFAULT_RUSTKMER,
    derive_hash_size,
    discover_part_pair,
    hash_size_slots,
    part_token,
    refuse_repo_root,
    run_command,
)
from scripts.bench.random_slice import reservoir_slice

HERE = Path(__file__).resolve().parent            # scripts/bench/
REPO_ROOT = HERE.parent.parent                    # repo root

SCHEMA_VERSION = 1
KIND = "merge-characterization-ladder"
DEFAULT_RESULTS = (
    REPO_ROOT / ".planning" / "phases"
    / "11-merge-characterization-harness-prep" / "11-LADDER-RESULTS.json")

# D-07 pinned rungs: (n_reads, seed). ~10% and ~40% of the ~34.5M-read part
# scale (anchor arithmetic: 8,967,099,203 union Total / 2 parts / 130
# k-positions per 150 bp read — RESEARCH A3). Seed 4242 pinned for both
# rungs; the SAME seed + N reproduce the same slice pair deterministically.
RUNGS = ((3500000, 4242), (14000000, 4242))
KS = (21, 31)
PART_SCALE_READS_ANCHOR = 34_500_000
SCALE_LABELS = {3500000: "~10% of part scale",
                14000000: "~40% of part scale"}

# D-03: ladder scratch lives outside the repo, never in REPO_ROOT.
DEFAULT_SCRATCH = Path("/tmp/rustkmer-phase11/ladder")
DEFAULT_MIN_FREE_GB = 20.0

# Coarse linearity check (D-07): a wall-per-entry ratio beyond this between
# the 10% and 40% rungs is flagged non-linear — a recorded finding for
# MBENCH-04's full-scale backstop, never silently smoothed.
LINEARITY_FLAG_RATIO = 2.0

# Committed Phase-10 union Distinct anchors — the merged Distinct at full
# scale (merged Distinct == union Distinct; disjoint key spaces). Read
# verbatim from .planning/milestones/v2.0-phases/10-benchmark-verdict/
# 10-results-full-k{21,31}.json. These drive the full-scale extrapolation.
UNION_DISTINCT_ANCHORS = {21: 897266581, 31: 1146353600}

FULL_SCALE_CAVEAT = (
    "slice-scale extrapolation under a two-point linear model — MBENCH-04's "
    "predicted-vs-measured check at full scale is the backstop (D-07); no "
    "slice-scale number is presented as a full-scale prediction without this "
    "caveat and the backstop named (milestone Pitfall 14)")

# Route attribution markers (T-11-15): scanned in the merge tool's stderr.
# The rustkmer merge default route prints no route line, and jellyfish merge
# is single-strategy — both land on "not-reported", recorded honestly.
ROUTE_MARKER_RE = re.compile(r"prefix cache", re.IGNORECASE)


def _now_iso():
    """UTC timestamp for evidence `created` fields."""
    return datetime.now(timezone.utc).isoformat()


# --- measured runs (route-attribution variant of bench.measure) --------------


def measured_run(argv):
    """Run argv under /usr/bin/time with bench.measure's semantics, keeping
    stderr for route attribution.

    Same `/usr/bin/time -l/-v` invocation and the SAME units-pinned
    `bench.parse_time_output` parser measure() uses — /usr/bin/time stays
    the only clock (harness-internal clocks are banned). stderr is retained
    because bench.measure discards it and the ladder must record the
    rustkmer merge route IF the tool reports one (T-11-15: fail-loud on
    failure, no invention on success).

    Returns (rep_dict, stderr_text); raises RuntimeError on non-zero exit.
    """
    plat = sys.platform
    time_flag = "-l" if plat == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag, *[str(a) for a in argv]],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return parse_time_output(proc.stderr, plat), proc.stderr


def route_from_stderr(stderr_text):
    """Route attribution from tool stderr — 'not-reported' when silent.

    No invention (T-11-15): only a tool-stated route marker is recorded;
    silence is recorded as 'not-reported', never guessed from flags.
    """
    if ROUTE_MARKER_RE.search(stderr_text or ""):
        return "prefix-cache"
    return "not-reported"


# --- deep dump-vs-dump gate (PARITY-GATE.md §4, streaming form) ----------------
# bench.py's dump_vs_dump_equal normalizes both dumps in-process; at the
# measured 10%-rung scale (3.5M-read slices -> ~200M distinct per part ->
# ~356M lines per merged dump side) that requires ~120-150 GB of Python
# heap and cannot run on this host. This ladder implementation executes
# the WRITTEN spec's original §4 pipeline — dump both sides, strip '#'
# comments, normalize every line fail-loud to "kmer<TAB>count", LC_ALL=C
# external sort, exact comparison — streaming, within practical memory.
# Byte order is identical to the in-process variant (both are LC_ALL=C
# over the pure-ASCII k-mer/digit/tab alphabet; the 11-04 equivalence
# argument realized literally).

_AWK_NORMALIZE = r"""
/^#/ { next }
{
    if (NF != 2 || $2 !~ /^[0-9]+$/) {
        printf "dump parse: expected exactly 'kmer count', got %d fields " \
               "in line: %s\n", NF, $0 > "/dev/stderr"
        exit 2
    }
    seen++
    print $1 "\t" $2
}
END {
    if (seen == 0) {
        print "dump parse: empty dump output (zero data lines) — an " \
              "empty dump can never pass the gate (MBENCH-02/empty)" \
              > "/dev/stderr"
        exit 2
    }
}
"""


def _run_fail_loud(argv, stdout_path=None, env=None, side_label=""):
    """Run one list-form pipeline element; fail loud on non-zero exit."""
    argv = [str(a) for a in argv]
    if stdout_path is not None:
        with open(stdout_path, "w", encoding="utf-8") as fh:
            proc = subprocess.run(argv, stdout=fh, stderr=subprocess.PIPE,
                                  text=True, env=env)
    else:
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"dump-vs-dump gate ({side_label}): step failed rc="
            f"{proc.returncode}: {argv}\n"
            f"trailing stderr:\n{(proc.stderr or '')[-500:]}")


def _normalized_sorted_dump(dump_cmd_builder, workdir, stem, side_label,
                            via_stdout=True):
    """One dump side: dump -> fail-loud normalize -> LC_ALL=C sort.

    dump_cmd_builder(raw_path) returns the dump argv for this side's raw
    output (rustkmer dump writes via `-o`; jellyfish dump -c writes
    stdout, hence via_stdout). Streams (never loads) so the gate runs at
    ladder scale; returns the sorted canonical "kmer<TAB>count" file path
    and its line count.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    raw = workdir / f"{stem}.raw"
    norm = workdir / f"{stem}.norm"
    sorted_path = workdir / f"{stem}.sorted"
    try:
        if via_stdout:
            _run_fail_loud(dump_cmd_builder(raw), stdout_path=raw,
                           side_label=side_label)
        else:
            _run_fail_loud(dump_cmd_builder(raw), side_label=side_label)
        _run_fail_loud(["awk", _AWK_NORMALIZE, str(raw)],
                       stdout_path=norm, side_label=side_label)
        sort_env = dict(os.environ, LC_ALL="C")
        _run_fail_loud(["sort", "-T", str(workdir), "-o", str(sorted_path),
                        str(norm)], env=sort_env, side_label=side_label)
        wc = subprocess.run(["wc", "-l", str(sorted_path)],
                            capture_output=True, text=True)
        if wc.returncode != 0:
            raise RuntimeError(
                f"dump-vs-dump gate ({side_label}): wc -l failed rc="
                f"{wc.returncode}")
        lines = int(wc.stdout.split()[0])
        if lines <= 0:
            raise RuntimeError(
                f"dump-vs-dump gate ({side_label}): sorted dump has "
                f"{lines} lines — an empty dump can never pass "
                "(MBENCH-02/empty)")
        return sorted_path, lines
    finally:
        for leftover in (raw, norm):
            try:
                leftover.unlink()
            except OSError:
                pass


def dump_vs_dump_equal_streaming(rkdb_path, jf_path, rustkmer, workdir):
    """Cross-tool verdict gate at ladder scale (PARITY-GATE.md §4).

    Same legs and identical semantics as bench.dump_vs_dump_equal —
    fail-loud dumps, '#' comments stripped, every data line normalized to
    (kmer, count) with a loud error naming the offending line, non-empty
    both sides, LC_ALL=C byte ordering, exact per-k-mer identity required,
    first difference named — realized as the spec's original streaming
    pipeline (external sort + streaming compare) so ~356M-line dumps run
    within practical memory.

    Returns True on exact equality; raises RuntimeError otherwise.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rk_sorted, rk_lines = _normalized_sorted_dump(
        lambda raw: [str(rustkmer), "dump", str(rkdb_path), "-o", str(raw)],
        workdir, "rk", "rustkmer side", via_stdout=False)
    jf_sorted, jf_lines = _normalized_sorted_dump(
        lambda raw: ["jellyfish", "dump", "-c", str(jf_path)],
        workdir, "jf", "jellyfish side", via_stdout=True)
    try:
        with open(rk_sorted, "r", encoding="utf-8") as fa, \
                open(jf_sorted, "r", encoding="utf-8") as fb:
            compared = 0
            for la, lb in zip(fa, fb):
                if la != lb:
                    raise RuntimeError(
                        f"dump-vs-dump gate: dumps differ at sorted line "
                        f"{compared}: rustkmer={la!r} vs jellyfish={lb!r} "
                        "— per-k-mer parity violated")
                compared += 1
            if compared != rk_lines or compared != jf_lines:
                raise RuntimeError(
                    f"dump-vs-dump gate: dumps differ in length: rustkmer "
                    f"{rk_lines} lines vs jellyfish {jf_lines} lines (the "
                    f"first {compared} sorted lines agree) — per-k-mer "
                    "parity violated")
        return True
    finally:
        for leftover in (rk_sorted, jf_sorted):
            try:
                leftover.unlink()
            except OSError:
                pass


# --- disk + zero-entry guards -------------------------------------------------


def free_bytes(path):
    """Free bytes on the volume holding path (os.statvfs, as bench.py).

    os.statvfs requires an existing path, so the nearest existing ancestor
    is probed when path itself does not exist yet (a fresh scratch root on
    a fresh host) — same volume, same answer.
    """
    probe = Path(path)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    st = os.statvfs(str(probe))
    return st.f_bavail * st.f_frsize


def ensure_free_space(path, min_free_gb):
    """Abort the rung loud before any provisioning when free space is short
    (T-11-14: GiB-scale ladder scratch on the shared volume; the shortfall
    is named, never a silent continue)."""
    free = free_bytes(path)
    required = int(min_free_gb * (1 << 30))
    if free < required:
        raise RuntimeError(
            f"ladder disk guard: {free} bytes free on the scratch volume "
            f"({path}) but the ladder requires {required} bytes "
            f"({min_free_gb} GiB) — aborting before provisioning; free "
            "space or re-point --scratch")


def _guard_zero(label, distinct, total, stage):
    """Zero-entry protection: a rung yielding distinct or total 0 aborts
    loud (existing zero-count sanity semantics carried into the ladder,
    probe MBENCH-01/empty)."""
    if distinct is None or total is None or distinct <= 0 or total <= 0:
        raise RuntimeError(
            f"zero-entry protection: {label} produced distinct={distinct!r} "
            f"total={total!r} after {stage} — a zero-count artifact is a "
            "loud rung abort, never an input to downstream builds or a "
            "measurement (probe MBENCH-01/empty)")


# --- slice provisioning (D-08) -------------------------------------------------


def _slice_paths(slices_dir, token, n_reads, seed):
    """Deterministic slice + manifest paths for one part at one rung."""
    stem = f"{token}.n{n_reads}.seed{seed}"
    return slices_dir / f"{stem}.fq", slices_dir / f"{stem}.manifest.json"


def _load_or_provision_slice(part, n_reads, seed, out_path, manifest_path):
    """Reuse an existing slice only when its full identity re-verifies.

    A reused slice must match the pinned seed/N, the CURRENT source part
    fingerprint, and the manifest's recorded output sha256 — otherwise it
    is re-provisioned deterministically (same seed + N + source reproduce
    the same selection). Honest reuse, never blind reuse.
    """
    if out_path.is_file() and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = None
        if isinstance(manifest, dict):
            source_fp = fingerprint(part)
            output_fp = fingerprint(out_path)
            if (manifest.get("seed") == seed
                    and manifest.get("requested_reads") == n_reads
                    and manifest.get("selected_reads") == n_reads
                    and isinstance(manifest.get("source"), dict)
                    and manifest["source"].get("sha256")
                    == source_fp["sha256"]
                    and manifest.get("output_sha256")
                    == output_fp["sha256"]):
                return manifest
    return reservoir_slice(part, n_reads, seed, out_path, manifest_path)


def provision_rung_slices(n_reads, seed, scratch_root, data_dir):
    """Provision the pinned part_001 + part_006 slice pair for one rung.

    Both slices use the SAME N and seed (D-08). Each slice carries its own
    selection manifest (random_slice.reservoir_slice contract). Returns
    {token: {slice, manifest_path, manifest, source_part}}.
    """
    scratch_root = refuse_repo_root(scratch_root)
    slices_dir = scratch_root / f"n{n_reads}" / "slices"
    slices_dir.mkdir(parents=True, exist_ok=True)
    slices = {}
    for part in discover_part_pair(data_dir):
        token = part_token(part)
        out_path, manifest_path = _slice_paths(slices_dir, token, n_reads, seed)
        manifest = _load_or_provision_slice(
            part, n_reads, seed, out_path, manifest_path)
        if manifest.get("selected_reads") != n_reads:
            raise RuntimeError(
                f"slice manifest for {token} records selected_reads="
                f"{manifest.get('selected_reads')!r} != pinned {n_reads}")
        slices[token] = {
            "slice": str(out_path),
            "manifest_path": str(manifest_path),
            "manifest": manifest,
            "source_part": str(part),
        }
        print(f"[ladder] slice {token}: {manifest['selected_reads']} reads "
              f"(seed {seed}) -> {out_path}", flush=True)
    expected = {"part_001", "part_006"}
    if set(slices) != expected:
        raise RuntimeError(
            f"ladder slices must be exactly {sorted(expected)}, got "
            f"{sorted(slices)} — the pinned merge arrangement is part_001 "
            "+ part_006 (Pitfall 2)")
    return slices


# --- one rung: provision -> counts -> merges -> gates --------------------------


def run_rung(n_reads, seed, k, rustkmer=DEFAULT_RUSTKMER,
             scratch_root=DEFAULT_SCRATCH, data_dir=DEFAULT_DATA_DIR,
             threads=None, slices=None, min_free_gb=DEFAULT_MIN_FREE_GB,
             deep_gate=None, provenance=None):
    """Run one ladder rung end-to-end and return its evidence record.

    The complete prepare -> count -> merge chain per D-08: provision the
    slice pair (unless a provisioned `slices` dict is passed), per-part
    rustkmer counts, per-part jellyfish counts with the ladder-scale -s
    derived via derive_hash_size from the measured per-part Distinct (the
    D-04 occupancy logic exercised at slice scale), rustkmer merge
    (defaults), jellyfish merge — each merge measured under /usr/bin/time
    with honest cache_state and route attribution. The PARITY-GATE.md
    aggregate legs execute before the record is returned; the dump-vs-dump
    deep leg runs at the 10% rung (deep_gate defaults to that condition).

    Raises RuntimeError/ValueError on any guard, gate, or subprocess
    failure — a failing rung is evidence, never smoothed over.
    """
    if (n_reads, seed) not in RUNGS:
        raise ValueError(f"n_reads/seed {(n_reads, seed)} is not a pinned "
                         f"ladder rung {RUNGS} (D-07)")
    if k not in KS:
        raise ValueError(f"k={k} is not a pinned ladder k {KS}")
    scratch_root = refuse_repo_root(Path(scratch_root))
    ensure_free_space(scratch_root, min_free_gb)
    threads = os.cpu_count() if threads is None else int(threads)
    rustkmer = str(rustkmer)
    if slices is None:
        slices = provision_rung_slices(n_reads, seed, scratch_root, data_dir)
    rung_dir = scratch_root / f"n{n_reads}" / f"k{k}"
    rung_dir.mkdir(parents=True, exist_ok=True)

    # -- per-part counts: rustkmer first (first-ever slice-scale Distinct),
    #    then the jellyfish -s derivation from those measured values (D-04
    #    build-order logic exercised at slice scale).
    counts = {}
    distinct_for_s = {}
    for token in ("part_001", "part_006"):
        slice_path = slices[token]["slice"]
        out_rkdb = rung_dir / f"{token}.k{k}.rkdb"
        cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                              inputs=[slice_path])
        argv = rustkmer_count_cmd(cfg, out_rkdb, rustkmer)
        run_command(argv)
        st = stats(out_rkdb, rustkmer)
        distinct, total = st["unique_kmers"], st["total_kmers"]
        _guard_zero(f"rustkmer count {token}", distinct, total,
                    f"k={k} count of the {token} slice")
        fp = fingerprint(out_rkdb)
        counts[token] = {
            "tool": "rustkmer", "distinct": distinct, "total": total,
            "rkdb_path": str(out_rkdb), "rkdb_bytes": fp["size_bytes"],
            "rkdb_sha256": fp["sha256"], "command_line": argv,
        }
        distinct_for_s[token] = distinct
        print(f"[ladder] counted {token} (rustkmer k={k}): distinct="
              f"{distinct} total={total}", flush=True)

    d_max = max(distinct_for_s.values())
    hash_size = derive_hash_size(d_max)
    slots = hash_size_slots(hash_size)
    hash_size_plan = {
        "hash_size": hash_size, "slots": slots,
        "max_per_part_distinct": d_max,
        "occupancy_target": 0.75, "occupancy": d_max / slots,
        "distinct_per_part": dict(distinct_for_s),
    }

    jellyfish_counts = {}
    for token in ("part_001", "part_006"):
        slice_path = slices[token]["slice"]
        out_jf = rung_dir / f"{token}.k{k}.jf"
        cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                              hash_size=hash_size, inputs=[slice_path])
        argv = jellyfish_count_cmd(cfg, out_jf)
        run_command(argv)
        jst = jellyfish_stats(out_jf)
        _guard_zero(f"jellyfish count {token}", jst["distinct"],
                    jst["total"], f"k={k} count of the {token} slice")
        fp = fingerprint(out_jf)
        jellyfish_counts[token] = {
            "tool": "jellyfish", "distinct": jst["distinct"],
            "total": jst["total"], "jf_path": str(out_jf),
            "jf_bytes": fp["size_bytes"], "jf_sha256": fp["sha256"],
            "hash_size": hash_size, "command_line": argv,
        }
        print(f"[ladder] counted {token} (jellyfish k={k}, -s {hash_size}): "
              f"distinct={jst['distinct']} total={jst['total']}", flush=True)

    # -- merges: rustkmer defaults vs jellyfish defaults, one measured rep
    #    each on the SAME slice pair (D-09). One rep per rung point is the
    #    two-point-ladder design (D-07): the slope comes from BETWEEN rungs.
    if provenance is None:
        provenance = {
            "rustkmer": binary_provenance(rustkmer, "release"),
            "jellyfish": binary_provenance("jellyfish",
                                           "pinned-comparator-2.3.1"),
        }
    merged_rkdb = rung_dir / f"merged.k{k}.rkdb"
    merged_jf = rung_dir / f"merged.k{k}.jf"
    merge_specs = [
        ("rustkmer", "rkdb", merged_rkdb,
         build_merge_cmd(rustkmer, merged_rkdb,
                         [counts["part_001"]["rkdb_path"],
                          counts["part_006"]["rkdb_path"]])),
        ("jellyfish", "jf", merged_jf,
         jellyfish_merge_cmd(merged_jf,
                             [jellyfish_counts["part_001"]["jf_path"],
                              jellyfish_counts["part_006"]["jf_path"]])),
    ]
    merges = []
    merged_counts = {}
    for tool, kind, out_path, argv in merge_specs:
        cache_state = attempt_cache_purge()
        rep, stderr = measured_run(argv)
        route = route_from_stderr(stderr)
        out_bytes = Path(out_path).stat().st_size
        if kind == "rkdb":
            mst = stats(out_path, rustkmer)
            distinct, total = mst["unique_kmers"], mst["total_kmers"]
        else:
            jmst = jellyfish_stats(out_path)
            distinct, total = jmst["distinct"], jmst["total"]
        _guard_zero(f"merged output ({tool})", distinct, total,
                    f"the {tool} merge at n={n_reads} k={k}")
        merged_counts[tool] = {"distinct": distinct, "total": total}
        merges.append({
            "tool": tool,
            "wall_s": rep["wall_s"],
            "peak_bytes": rep["peak_bytes"],
            "peak_rss_bytes": rep["peak_rss_bytes"],
            "peak_footprint_bytes": rep["peak_footprint_bytes"],
            "output_path": str(out_path),
            "output_bytes": out_bytes,
            "distinct": distinct,
            "total": total,
            "cache_state": cache_state,
            "route": route,
            "reps": 1,
            "command_line": argv,
            "provenance": provenance[tool],
        })
        print(f"[ladder] merged ({tool}, k={k}): wall={rep['wall_s']:.2f}s "
              f"peak={rep['peak_bytes']} bytes out={out_bytes} "
              f"distinct={distinct} route={route} cache={cache_state}",
              flush=True)

    # -- gates BEFORE the record is accepted (PARITY-GATE.md §2 aggregate
    #    legs at rung scale; deep dump-vs-dump leg at the 10% rung).
    by_name = {
        "count-A": {"distinct_kmers": counts["part_001"]["distinct"],
                    "total_kmers": counts["part_001"]["total"]},
        "count-B": {"distinct_kmers": counts["part_006"]["distinct"],
                    "total_kmers": counts["part_006"]["total"]},
        "merge": {"distinct_kmers": merged_counts["rustkmer"]["distinct"],
                  "total_kmers": merged_counts["rustkmer"]["total"]},
        "jellyfish-merge": {
            "distinct_kmers": merged_counts["jellyfish"]["distinct"],
            "total_kmers": merged_counts["jellyfish"]["total"]},
    }
    assert_merge_parity(by_name)
    if deep_gate is None:
        deep_gate = (n_reads == RUNGS[0][0])
    if deep_gate:
        dump_vs_dump_equal_streaming(merged_rkdb, merged_jf, rustkmer,
                                     rung_dir / "gate")
        dump_verdict = ("green (streaming PARITY-GATE.md §4 form: fail-loud "
                        "normalization, LC_ALL=C external sort, exact "
                        "per-k-mer identity)")
        legs = ["aggregate-conservation", "distinct-union", "dump-vs-dump"]
    else:
        dump_verdict = ("not-run: deep dump-vs-dump leg scheduled at the "
                        "10% rung only (Plan 11-06 action)")
        legs = ["aggregate-conservation", "distinct-union"]

    return {
        "n_reads": n_reads,
        "seed": seed,
        "k": k,
        "scale_label": SCALE_LABELS[n_reads],
        "scale_pct_of_part": round(n_reads / PART_SCALE_READS_ANCHOR * 100, 2),
        "slices": [slices[token]["manifest_path"]
                   for token in ("part_001", "part_006")],
        "slices_detail": {token: {
            "slice": slices[token]["slice"],
            "manifest_path": slices[token]["manifest_path"],
            "source_part": slices[token]["source_part"],
            "selected_reads": slices[token]["manifest"]["selected_reads"],
            "seed": seed,
            "output_sha256": slices[token]["manifest"]["output_sha256"],
            "source_sha256": slices[token]["manifest"]["source"]["sha256"],
        } for token in ("part_001", "part_006")},
        "counts": {
            "definition": "distinct/total are the SUM-OF-COUNTS definition "
                          "from the stats readers — never the header "
                          "record-count field (PARITY-GATE.md §5)",
            "rustkmer_per_part": counts,
            "jellyfish_per_part": jellyfish_counts,
            "hash_size_plan": hash_size_plan,
        },
        "merges": merges,
        "gates": {
            "legs_executed": legs,
            "aggregate_parity": "green (assert_merge_parity, "
                                "sum-of-counts Totals)",
            "dump_vs_dump": dump_verdict,
        },
        "created": _now_iso(),
    }


# --- slope fit + summary (D-07; feeds Phase 12 scheduling and D-10) ------------


def fit_slope(rungs_results):
    """Two-point wall-per-entry slope per tool-k + the coarse linearity check.

    Entries are the merged Distinct each tool's own output reports (equal
    across tools once the parity gate is green; each tool's slope uses its
    OWN output's entries). slope = delta-wall / delta-entries between the
    10% and 40% rungs; ratio_40_over_10 compares wall-per-entry between
    rungs and flags > LINEARITY_FLAG_RATIO as non-linear (a recorded
    finding, never smoothed). A missing scale point yields slope None with
    an explicit note — never an invented slope.
    """
    low_n, high_n = RUNGS[0][0], RUNGS[1][0]
    slopes = {}
    for tool in ("jellyfish", "rustkmer"):
        for k in KS:
            key = f"{tool}_k{k}"
            points = {}
            for rec in rungs_results:
                if rec.get("k") != k:
                    continue
                for m in rec.get("merges", []):
                    if m.get("tool") != tool or not m.get("distinct"):
                        continue
                    points[rec["n_reads"]] = {
                        "entries": m["distinct"],
                        "wall_s": m["wall_s"],
                        "wall_per_entry": m["wall_s"] / m["distinct"],
                        "output_bytes": m.get("output_bytes"),
                        "bytes_per_entry": (
                            m["output_bytes"] / m["distinct"]
                            if m.get("output_bytes") else None),
                    }
            low, high = points.get(low_n), points.get(high_n)
            entry = {"per_rung": {str(n): points[n]
                                  for n in sorted(points)}}
            if low and high:
                entry["slope_wall_s_per_entry"] = (
                    (high["wall_s"] - low["wall_s"])
                    / (high["entries"] - low["entries"]))
                entry["ratio_40_over_10"] = (
                    high["wall_per_entry"] / low["wall_per_entry"]
                    if low["wall_per_entry"] else None)
                entry["linear"] = (entry["ratio_40_over_10"] is not None
                                   and entry["ratio_40_over_10"]
                                   <= LINEARITY_FLAG_RATIO)
            else:
                entry["slope_wall_s_per_entry"] = None
                entry["ratio_40_over_10"] = None
                entry["linear"] = None
                entry["note"] = ("second scale point missing — slope "
                                 "undetermined, never invented")
            slopes[key] = entry
    return slopes


def build_summary(rungs_results):
    """Build the evidence document's summary block (Task 3's deliverable).

    Per tool-k: fitted wall-per-entry slope, measured output bytes per
    entry (.rkdb expected ~20 B/entry vs .jf measured bytes/entry — the
    format asymmetry MBENCH-04 will surface), the coarse linearity
    verdict, and the extrapolated full-scale merge wall with the D-07
    caveat + MBENCH-04 backstop named.
    """
    slopes = fit_slope(rungs_results)
    low_n, high_n = RUNGS[0][0], RUNGS[1][0]

    bytes_per_entry = {
        "note": "rkdb entries are 20 bytes on disk (42-byte header + "
                "20-byte records, format.rs) so ~20 B/entry is the "
                "expected constant; .jf bytes/entry is the measured "
                "capacity-derived asymmetry MBENCH-04 will surface",
    }
    for key, entry in slopes.items():
        for n, pt in entry["per_rung"].items():
            if pt.get("bytes_per_entry") is not None:
                bytes_per_entry.setdefault(key, {})[f"n{n}"] = \
                    pt["bytes_per_entry"]

    linearity = {
        "threshold_ratio": LINEARITY_FLAG_RATIO,
        "rule": "wall-per-entry ratio between the 10% and 40% rungs; "
                "ratio > 2.0 is flagged non-linear — a recorded finding "
                "for MBENCH-04's full-scale backstop, never silently "
                "smoothed",
    }
    for key, entry in slopes.items():
        ratio = entry["ratio_40_over_10"]
        if ratio is None:
            verdict = "undetermined (missing scale point)"
        elif ratio > LINEARITY_FLAG_RATIO:
            verdict = "non-linear (flagged)"
        else:
            verdict = "linear"
        linearity[key] = {"ratio_40_over_10": ratio, "verdict": verdict}

    extrapolated = {
        "full_scale_entries": {str(k): UNION_DISTINCT_ANCHORS[k]
                               for k in KS},
        "entries_source": "committed Phase-10 union Distinct anchors "
                          "(10-results-full-k{21,31}.json); merged "
                          "Distinct == union Distinct (disjoint key "
                          "spaces)",
        "caveat": FULL_SCALE_CAVEAT,
    }
    for key, entry in slopes.items():
        k = int(key.rsplit("k", 1)[1])
        low = entry["per_rung"].get(str(low_n))
        slope = entry["slope_wall_s_per_entry"]
        full_entries = UNION_DISTINCT_ANCHORS[k]
        if low and slope is not None:
            predicted = low["wall_s"] + slope * (full_entries
                                                 - low["entries"])
            extrapolated[key] = {
                "predicted_full_scale_wall_s": predicted,
                "method": f"two-point linear: wall(n={low_n}) + slope x "
                          f"(full_scale_entries - entries(n={low_n}))",
                "flagged_nonlinear": entry["linear"] is not True,
            }
        else:
            extrapolated[key] = {
                "predicted_full_scale_wall_s": None,
                "note": "insufficient scale points — extrapolation "
                        "refused",
            }
    return {"slopes": slopes, "bytes_per_entry": bytes_per_entry,
            "linearity": linearity,
            "extrapolated_full_scale": extrapolated}


# --- evidence document I/O ------------------------------------------------------


def new_doc():
    """Fresh evidence document in the pinned top-level shape."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "rungs": [],
        "summary": {},
        "scratch_cleaned": False,
        "created": _now_iso(),
    }


def load_doc(path):
    """Load an existing evidence JSON, or None when absent.

    Raises ValueError on a kind/schema mismatch — never merge across
    kinds (the ladder evidence is its own document, MBENCH-05 boundary).
    """
    path = Path(path)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("kind") != KIND:
        raise ValueError(
            f"{path} is not a {KIND!r} document (kind="
            f"{doc.get('kind')!r}) — refusing to merge across kinds")
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} carries schema_version {doc.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION}")
    return doc


def upsert_rung(doc, record):
    """Insert/replace one rung record keyed by (n_reads, k), keeping the
    rungs list sorted (2 scale points x 2 k = exactly 4 records when
    complete)."""
    rungs = [r for r in doc.get("rungs", [])
             if not (r.get("n_reads") == record["n_reads"]
                     and r.get("k") == record["k"])]
    rungs.append(record)
    rungs.sort(key=lambda r: (r["n_reads"], r["k"]))
    doc["rungs"] = rungs


def write_doc(path, doc):
    """Write the evidence JSON (indent=2, sort_keys, trailing newline)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")


def cleanup_scratch(scratch_root):
    """Remove the ladder scratch tree; True when the root is gone."""
    root = Path(scratch_root)
    if not root.exists():
        return True
    shutil.rmtree(root)
    try:
        root.parent.rmdir()          # only succeeds when empty
    except OSError:
        pass
    return not root.exists()


# --- CLI -------------------------------------------------------------------------


def main(argv=None):
    """Run the characterization-ladder CLI; invalid inputs exit 2."""
    parser = argparse.ArgumentParser(
        prog="merge_characterize.py",
        description="Two-point merge-characterization ladder (Plan 11-06, "
                    "D-07/D-08/D-09): jellyfish merge vs rustkmer merge on "
                    "seeded real-data slice pairs at both k.")
    parser.add_argument("--run", action="store_true",
                        help="execute the pinned ladder (RUNGS x KS), "
                             "write evidence incrementally, clean scratch, "
                             "record the summary block")
    parser.add_argument("--summarize", action="store_true",
                        help="recompute the summary block of an existing "
                             "evidence JSON from its rung records "
                             "(idempotent)")
    parser.add_argument("--n-reads", type=int,
                        choices=sorted({n for n, _ in RUNGS}), default=None,
                        help="re-run only this scale point (evidence is "
                             "merged into the existing document)")
    parser.add_argument("--k", type=int, choices=KS, default=None,
                        help="re-run only this k (evidence is merged)")
    parser.add_argument("--scratch", default=str(DEFAULT_SCRATCH),
                        help="ladder scratch root (must be outside the "
                             "repo; default /tmp/rustkmer-phase11/ladder)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="split-parts source directory")
    parser.add_argument("--rustkmer", default=str(DEFAULT_RUSTKMER),
                        help="rustkmer release binary path")
    parser.add_argument("--threads", type=int, default=None,
                        help="count threads (default: all cores)")
    parser.add_argument("--min-free-gb", type=float,
                        default=DEFAULT_MIN_FREE_GB,
                        help="minimum free GiB on the scratch volume "
                             "before each rung (default: 20)")
    parser.add_argument("--keep-scratch", action="store_true",
                        help="skip scratch cleanup (scratch_cleaned stays "
                             "false)")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS),
                        help="evidence JSON path")
    args = parser.parse_args(argv)
    if not (args.run or args.summarize):
        parser.error("nothing to do: pass --run (execute the ladder) or "
                     "--summarize (recompute the summary block)")

    try:
        if args.summarize:
            doc = load_doc(args.results)
            if doc is None:
                raise ValueError(
                    f"no evidence JSON at {args.results} — run --run first")
            doc["summary"] = build_summary(doc.get("rungs", []))
            write_doc(args.results, doc)
            print(f"[ladder] summary recomputed from "
                  f"{len(doc.get('rungs', []))} rung records -> {args.results}")
            return

        provenance = {
            "rustkmer": binary_provenance(args.rustkmer, "release"),
            "jellyfish": binary_provenance("jellyfish",
                                           "pinned-comparator-2.3.1"),
        }
        doc = load_doc(args.results) or new_doc()
        planned = [(n, seed, k)
                   for n, seed in RUNGS
                   if args.n_reads is None or n == args.n_reads
                   for k in KS
                   if args.k is None or k == args.k]
        if not planned:
            raise ValueError("the --n-reads/--k filters select no rung")
        for n, seed, k in planned:
            print(f"[ladder] === rung n={n} seed={seed} k={k} starting "
                  f"({_now_iso()}) ===", flush=True)
            record = run_rung(
                n, seed, k,
                rustkmer=args.rustkmer,
                scratch_root=Path(args.scratch),
                data_dir=args.data_dir,
                threads=args.threads,
                slices=None,
                min_free_gb=args.min_free_gb,
                provenance=provenance)
            upsert_rung(doc, record)
            doc["summary"] = build_summary(doc["rungs"])
            write_doc(args.results, doc)
            print(f"[ladder] === rung n={n} k={k} recorded, evidence "
                  f"written ({_now_iso()}) ===", flush=True)
        if args.keep_scratch:
            doc["scratch_cleaned"] = False
            print("[ladder] --keep-scratch: scratch left in place; "
                  "scratch_cleaned recorded false", flush=True)
        else:
            doc["scratch_cleaned"] = cleanup_scratch(args.scratch)
            print(f"[ladder] scratch cleaned: {doc['scratch_cleaned']}",
                  flush=True)
        doc["summary"] = build_summary(doc["rungs"])
        write_doc(args.results, doc)
        print(f"[ladder] complete: {len(doc['rungs'])} rung records in "
              f"{args.results} (scratch_cleaned={doc['scratch_cleaned']})")
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    main()
