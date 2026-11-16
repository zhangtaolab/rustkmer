#!/usr/bin/env python3
"""Build, revalidate, and describe the Phase-11 merge input artifacts.

The 8 full-scale merge inputs (part_001/part_006 x .rkdb/.jf x k=21/31) are
pre-built by this stage, never at Phase 12 round 0 (D-01). Every artifact
records its own provenance — sha256, stats counts, exact command line — in
a manifest written beside the artifacts, so Phase 12's round-0 revalidation
consumes records, not memory (D-04). Artifacts live in a dedicated
directory OUTSIDE the repo tree (D-03) and are kept until the Phase 12
merge verdict lands (D-02).

Build order (D-04, RESEARCH Pattern 1 — the order is load-bearing):
  1. all per-part .rkdb counts first (first-ever per-part Distinct);
  2. per-k union-anchor reconciliation immediately after both parts of
     that k are counted — a dataset-drift or harness-bug finding aborts
     mid-stage, before the next k's counts and before any -s derivation;
  3. shared jellyfish -s derivation per k-pair with the occupancy
     assertion (jellyfish auto-grow is correct but slow and would change
     provenance mid-build — one step over the threshold forces the next
     standard size up, never a silent correction);
  4. per-part .jf counts with identical -m/-s/-C within each k-pair
     (merge enforces hash-size equality);
  5. `jellyfish info` recorded per .jf via a fail-loud parser.

Verbs: build (--stage rkdb|jf), revalidate, manifest.

Python 3.11+ stdlib only — no third-party imports, no pip installs (the
bench-harness stdlib-only contract, bench.py:25-26).
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution needs the checkout root for the scripts package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    BenchmarkConfig,
    binary_provenance,
    fingerprint,
    jellyfish_count_cmd,
    rustkmer_count_cmd,
    stats,
)

HERE = Path(__file__).resolve().parent            # scripts/bench/
REPO_ROOT = HERE.parent.parent                    # repo root

# The stage runs from any cwd, so the rustkmer default is REPO_ROOT-resolved
# (bench.py's relative "target/release/rustkmer" assumes repo-root cwd).
DEFAULT_RUSTKMER = REPO_ROOT / "target" / "release" / "rustkmer"
JELLYFISH_BIN = "jellyfish"
RUSTKMER_BUILD_PROFILE = "release"

# D-03: artifacts live next to the source data, never inside the repo tree.
DEFAULT_ARTIFACTS_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs")
DEFAULT_DATA_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")

# phase10.py's pinned-token pattern: gather_inputs' sorted-six-parts +
# first-two selection (bench.py:667-674) can never silently pick part_002.
_COMPRESSION_SUFFIXES = (".fastq.gz", ".fq.gz")
_SPLIT_PART_TOKENS = (".part_001", ".part_006")

OCCUPANCY_TARGET = 0.75
KS = (21, 31)
# jellyfish -s ladder (M/G = 2^20/2^30 slots); smallest standard size wins.
HASH_SIZE_LADDER = ("1M", "2M", "5M", "10M", "20M", "50M", "100M",
                    "200M", "500M", "1G", "2G", "5G", "10G")

# Committed Phase-10 union anchors (sum-of-counts from `rustkmer stats -f
# json`, read verbatim from 10-results-full-k21.json / 10-results-full-k31.json).
# Total is additive over the two disjoint read sets, so the per-part sums
# MUST equal these — a mismatch is dataset drift or a harness bug.
UNION_ANCHORS = {21: 8967099203, 31: 8275694030}

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_KIND = "merge-input-manifest"
MANIFEST_NAME = "manifest.json"
RETENTION_NOTE = "keep until the Phase 12 merge verdict lands (D-02)"


def _now_iso():
    """UTC timestamp for manifest/provenance `created` fields."""
    return datetime.now(timezone.utc).isoformat()


# --- jellyfish -s derivation (D-04 build-order step 2) ------------------------


def hash_size_slots(size_str):
    """Exact slot count for a jellyfish -s string (M/G = 2^20/2^30)."""
    text = str(size_str)
    if len(text) < 2 or text[-1] not in "MG":
        raise ValueError(f"unsupported jellyfish hash size: {size_str!r}")
    try:
        count = int(text[:-1])
    except ValueError:
        raise ValueError(
            f"unsupported jellyfish hash size: {size_str!r}") from None
    if count < 1:
        raise ValueError(f"unsupported jellyfish hash size: {size_str!r}")
    return count << (20 if text[-1] == "M" else 30)


def derive_hash_size(max_per_part_distinct):
    """Smallest standard jellyfish -s satisfying the occupancy assertion.

    max_per_part_distinct <= OCCUPANCY_TARGET * slots keeps jellyfish's
    load headroom. The assertion is the structural defense against
    jellyfish's slow auto-grow mid-artifact-build (research Pitfall 3):
    one step over the threshold forces the NEXT size up — auto-grow
    territory must be unreachable, not corrected silently (D-04).

    Raises:
        ValueError: If max_per_part_distinct is not a positive integer.
        RuntimeError: If no standard size satisfies the assertion.
    """
    if (isinstance(max_per_part_distinct, bool)
            or not isinstance(max_per_part_distinct, int)
            or max_per_part_distinct < 1):
        raise ValueError(
            "max_per_part_distinct must be a positive integer, got "
            f"{max_per_part_distinct!r}")
    for size_str in HASH_SIZE_LADDER:
        slots = hash_size_slots(size_str)
        if max_per_part_distinct <= OCCUPANCY_TARGET * slots:
            return size_str
    raise RuntimeError(
        "no standard jellyfish -s size satisfies the occupancy assertion "
        f"(max_per_part_distinct={max_per_part_distinct} > "
        f"{OCCUPANCY_TARGET} * slots of the largest standard size "
        f"{HASH_SIZE_LADDER[-1]}) — refusing to enter jellyfish's slow "
        "auto-grow territory mid-artifact-build")


# --- part-pair + repo-exit guards (D-03, Pitfall 2/Pitfall 9) -----------------


def strip_compression_suffix(name):
    """The basename minus a trailing `.fq.gz`/`.fastq.gz`, else None.

    The part token lives BEFORE the compression suffix, so the suffix must
    be stripped first (phase10.py precedent).
    """
    for suffix in _COMPRESSION_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return None


def resolve_part_pair(inputs):
    """Exactly part_001 then part_006, matched on the stripped stem.

    Raises:
        ValueError: On any path count, compression-suffix, token, or
            ordering mismatch — the pinned pair is part_001+part_006 in
            that order and nothing else (probe MBENCH-01/adjacency).
    """
    paths = [Path(p) for p in inputs]
    if len(paths) != 2:
        raise ValueError(
            "the merge-input stage requires exactly the two pinned split "
            f"parts, got {len(paths)}: {[str(path) for path in paths]}")
    stems = []
    for path in paths:
        stem = strip_compression_suffix(path.name)
        if stem is None:
            raise ValueError(
                f"split part {path} is not a .fq.gz/.fastq.gz file — the "
                f"part token is matched on the compression-stripped stem")
        stems.append(stem)
    if not (stems[0].endswith(_SPLIT_PART_TOKENS[0])
            and stems[1].endswith(_SPLIT_PART_TOKENS[1])):
        raise ValueError(
            "expected the two parts to end with .part_001 then .part_006 "
            f"after stripping the compression suffix; got {stems!r} — "
            "part_002 can never be silently substituted (probe "
            "MBENCH-01/adjacency, D-03)")
    return paths


def discover_part_pair(data_dir):
    """Find the pinned part_001/part_006 pair inside data_dir (exact order).

    Raises:
        ValueError: If the directory is missing, a token matches more than
            one file, or either pinned part cannot be found.
    """
    root = Path(data_dir)
    if not root.is_dir():
        raise ValueError(f"data dir not found or not a directory: {root}")
    matches = {}
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        stem = strip_compression_suffix(path.name)
        if stem is None:
            continue
        for token in _SPLIT_PART_TOKENS:
            if stem.endswith(token):
                if token in matches:
                    raise ValueError(
                        f"ambiguous split parts: multiple files in {root} "
                        f"match {token}")
                matches[token] = path
    missing = [token for token in _SPLIT_PART_TOKENS if token not in matches]
    if missing:
        raise ValueError(
            f"could not find split parts matching {missing} in {root}")
    return resolve_part_pair(
        [matches[_SPLIT_PART_TOKENS[0]], matches[_SPLIT_PART_TOKENS[1]]])


def part_token(part_path):
    """The `part_001`-style artifact-name token for a pinned split part."""
    stem = strip_compression_suffix(Path(part_path).name)
    if stem is None:
        raise ValueError(
            f"split part {part_path} is not a .fq.gz/.fastq.gz file")
    for token in _SPLIT_PART_TOKENS:
        if stem.endswith(token):
            return token.lstrip(".")
    raise ValueError(f"not a pinned split part: {part_path}")


def refuse_repo_root(path):
    """Reject an artifacts root inside the repo tree (D-03, Pitfall 9).

    bench.py's DEFAULT_SCRATCH (scripts/bench/scratch, bench.py:49) is the
    in-repo default this stage must never inherit: any artifact, manifest,
    or scratch inside REPO_ROOT is a mis-commit risk. Returns the resolved
    Path on success.

    Raises:
        ValueError: If the resolved path is the repo root or below it.
    """
    resolved = Path(path).expanduser().resolve()
    repo = REPO_ROOT.resolve()
    if resolved == repo or repo in resolved.parents:
        raise ValueError(
            f"artifacts root {resolved} is inside REPO_ROOT ({repo}) — "
            "artifacts must live outside the repo tree (D-03)")
    return resolved


# --- union-anchor reconciliation (Phase-10 pre-gate, enforced mid-build) ------


def reconcile_anchors(totals_by_k, anchors=None, ks=None):
    """Compare summed per-part Totals against the committed union anchors.

    totals_by_k maps k -> summed per-part Total (sum-of-counts from the
    rustkmer stats JSON — never the header field, IN-03/Pitfall 5).

    The build calls this with ks=(k,) immediately after both parts of that
    k are counted, so a mismatch aborts mid-stage before the next k's
    counts and before any -s derivation. The default (ks=None) checks the
    full anchor set — the manifest-time shape. A k with no recorded total
    is a loud error in either call shape (probe MBENCH-01/empty), and a
    total recorded for a k with no committed anchor is rejected too.

    Raises:
        RuntimeError: On any missing k, mismatched sum, or unknown k.
    """
    anchor_map = UNION_ANCHORS if anchors is None else anchors
    checked = tuple(anchor_map) if ks is None else tuple(ks)
    if not checked:
        raise RuntimeError("union-anchor reconciliation: no k to check")
    for k in checked:
        if k not in totals_by_k:
            raise RuntimeError(
                "union-anchor reconciliation: no summed per-part total "
                f"recorded for k={k}")
        measured = totals_by_k[k]
        anchor = anchor_map[k]
        if measured != anchor:
            raise RuntimeError(
                f"union-anchor reconciliation failed for k={k}: summed "
                f"per-part total {measured} != committed Phase-10 union "
                f"anchor {anchor} (sum-of-counts from rustkmer stats JSON; "
                f"10-results-full-k{k}.json) — dataset drift or harness "
                "bug, aborting before any downstream artifact")
    unknown = sorted(set(totals_by_k) - set(anchor_map))
    if unknown:
        raise RuntimeError(
            "union-anchor reconciliation: totals recorded for k values "
            f"with no committed anchor: {unknown!r}")


# --- fail-loud subprocess + parsers (T-11-04/T-11-06) -------------------------


def run_command(argv):
    """Run one list-form argv, raising with trailing stderr on failure.

    List-form subprocess only — the stage adds no shell pipeline of its
    own (T-11-04); the only sh -c string is jellyfish_count_cmd's existing
    decompressor pipe, built solely from validate_path-screened paths.
    """
    argv = [str(arg) for arg in argv]
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return proc.stdout


def parse_jellyfish_info(text):
    """Parse `jellyfish info` output into a dict — fail loud on drift.

    Pinned to the 2.3.1 output shape (verified verbatim 2026-11-16):
    `command:`, `where:`, `when:`, `canonical:` lines. A parse that
    tolerated a missing line would record an incomplete provenance block
    (threat T-11-06) — a missing or unparsable line raises ValueError.
    """
    info = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(
                f"jellyfish info text has an unparsable line: {line!r}")
        info[key.strip()] = value.strip()
    for required in ("command", "where", "when", "canonical"):
        if required not in info:
            raise ValueError(
                f"jellyfish info text has no {required!r} line: {text!r}")
    return info


def jellyfish_info(jf_path, jellyfish_bin=JELLYFISH_BIN):
    """Return the parsed `jellyfish info` dict for one .jf (fail loud)."""
    proc = subprocess.run([str(jellyfish_bin), "info", str(jf_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"jellyfish info failed rc={proc.returncode} on {jf_path}: "
            f"{proc.stderr[-500:]}")
    return parse_jellyfish_info(proc.stdout)


# --- manifest I/O (RESEARCH Pattern 1 shape) ----------------------------------


def write_manifest(path, manifest):
    """Write the manifest JSON (indent=2, sort_keys, trailing newline)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_manifest(artifacts_dir):
    """Load and identity-check the manifest from an artifacts dir.

    Raises:
        ValueError: If the manifest is missing or not a
            merge-input-manifest at schema_version 1.
    """
    path = Path(artifacts_dir) / MANIFEST_NAME
    if not path.is_file():
        raise ValueError(
            f"no manifest at {path} — run `build --stage rkdb` first")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("kind") != MANIFEST_KIND:
        raise ValueError(
            f"{path} is not a {MANIFEST_KIND!r} manifest "
            f"(kind={manifest.get('kind')!r})")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"{path} carries schema_version "
            f"{manifest.get('schema_version')!r}, expected "
            f"{MANIFEST_SCHEMA_VERSION}")
    return manifest


def verify_recorded_artifacts(manifest, rustkmer=DEFAULT_RUSTKMER):
    """Re-fingerprint (+ re-stats .rkdb) every recorded artifact.

    Compares against the manifest ONLY — no regeneration, no silent
    repair. A single changed byte raises RuntimeError naming the artifact
    and field (threat T-11-03; probe MBENCH-01/empty applied to identity).
    """
    for record in manifest.get("artifacts", []):
        path = Path(record["path"])
        if not path.is_file():
            raise RuntimeError(
                f"revalidate: recorded artifact missing: {path}")
        fp = fingerprint(path)
        if fp["size_bytes"] != record["size_bytes"]:
            raise RuntimeError(
                f"revalidate: {path.name} size_bytes {fp['size_bytes']} "
                f"!= recorded {record['size_bytes']}")
        if fp["sha256"] != record["sha256"]:
            raise RuntimeError(
                f"revalidate: {path.name} sha256 {fp['sha256']} != "
                f"recorded {record['sha256']} — tampered or rebuilt "
                "artifact, never a silent repair")
        counts = stats(path, rustkmer)
        if counts["unique_kmers"] != record["distinct"]:
            raise RuntimeError(
                f"revalidate: {path.name} distinct "
                f"{counts['unique_kmers']} != recorded "
                f"{record['distinct']}")
        if counts["total_kmers"] != record["total"]:
            raise RuntimeError(
                f"revalidate: {path.name} total {counts['total_kmers']} "
                f"!= recorded {record['total']}")
    for record in manifest.get("jellyfish_inputs", []):
        path = Path(record["path"])
        if not path.is_file():
            raise RuntimeError(
                f"revalidate: recorded jellyfish input missing: {path}")
        fp = fingerprint(path)
        if fp["size_bytes"] != record["size_bytes"]:
            raise RuntimeError(
                f"revalidate: {path.name} size_bytes {fp['size_bytes']} "
                f"!= recorded {record['size_bytes']}")
        if fp["sha256"] != record["sha256"]:
            raise RuntimeError(
                f"revalidate: {path.name} sha256 {fp['sha256']} != "
                f"recorded {record['sha256']} — tampered or rebuilt "
                "artifact, never a silent repair")


# --- build stage (D-04 fixed order) -------------------------------------------


def build_stage(data_dir, artifacts_dir, stage, rustkmer=DEFAULT_RUSTKMER,
                threads=None, ks=None, anchors=None,
                jellyfish_bin=JELLYFISH_BIN):
    """Run one prepare stage and (re)write the manifest.

    stage="rkdb": the fixed D-04 order — per-part .rkdb counts first
    (first-ever per-part Distinct), per-k anchor reconciliation
    immediately after both parts of that k, then the shared -s derivation
    per k-pair. The manifest is written with jellyfish_inputs empty and
    hash_size_plan filled.

    stage="jf": completes an existing manifest — re-verifies the recorded
    .rkdb identity first (the -s plan was derived from those Distinct
    values), then builds each part .jf with the shared -s from the
    recorded plan and records `jellyfish info` per artifact.

    ks/anchors default to the module constants AT CALL TIME (phase10's
    injectable-seam pattern), so tests drive the real stage at synthetic
    scale with honest anchors.

    Raises:
        ValueError: On unknown stage, guard failures, or a missing/
            incomplete manifest for the jf stage.
        RuntimeError: On any subprocess failure, zero-count artifact,
            anchor mismatch, -s exhaustion, or identity drift.
    """
    if stage not in ("rkdb", "jf"):
        raise ValueError(f"unknown build stage: {stage!r}")
    ks = tuple(KS) if ks is None else tuple(ks)
    artifacts_dir = refuse_repo_root(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifacts_dir / MANIFEST_NAME
    parts = discover_part_pair(data_dir)
    source_fingerprints = [fingerprint(part) for part in parts]
    threads = os.cpu_count() if threads is None else int(threads)
    rustkmer = str(rustkmer)

    if stage == "rkdb":
        artifacts = []
        totals_by_k = {}
        distinct_by_k = {}
        for k in ks:
            totals_by_k[k] = 0
            distinct_by_k[k] = {}
            for part in parts:
                token = part_token(part)
                out = artifacts_dir / f"{token}.k{k}.rkdb"
                cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                                      inputs=[part])
                argv = rustkmer_count_cmd(cfg, out, rustkmer)
                run_command(argv)
                try:
                    counts = stats(out, rustkmer)
                except RuntimeError as exc:
                    raise RuntimeError(
                        f"count produced no readable stats for {out} — "
                        "an empty/zero-count artifact is a loud error, "
                        "never an input to downstream builds (probe "
                        f"MBENCH-01/empty): {exc}") from exc
                distinct = counts["unique_kmers"]
                total = counts["total_kmers"]
                if total == 0:
                    raise RuntimeError(
                        f"zero-count artifact: {out} stats total is 0 — "
                        "an empty count is a loud error, never an input "
                        "to downstream builds (probe MBENCH-01/empty)")
                fp = fingerprint(out)
                artifacts.append({
                    "path": str(out),
                    "size_bytes": fp["size_bytes"],
                    "sha256": fp["sha256"],
                    "command_line": argv,
                    "k": k,
                    "canonical": True,
                    "tool": "rustkmer",
                    "distinct": distinct,
                    "total": total,
                })
                totals_by_k[k] += total
                distinct_by_k[k][token] = distinct
                print(f"counted {part.name} -> {out.name} "
                      f"(distinct={distinct} total={total})")
            # Mid-build enforcement: the anchors must reconcile BEFORE the
            # next k's counts and before any -s derivation (Plan 11-05's
            # post-build verify re-proves this from the manifest).
            reconcile_anchors({k: totals_by_k[k]}, anchors=anchors, ks=(k,))
        hash_size_plan = {}
        for k in ks:
            d_max = max(distinct_by_k[k].values())
            hash_size = derive_hash_size(d_max)
            slots = hash_size_slots(hash_size)
            hash_size_plan[str(k)] = {
                "distinct_per_part": dict(distinct_by_k[k]),
                "max_per_part_distinct": d_max,
                "hash_size": hash_size,
                "slots": slots,
                "occupancy_target": OCCUPANCY_TARGET,
                "occupancy": d_max / slots,
            }
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "kind": MANIFEST_KIND,
            "stage": "rkdb",
            "artifacts": artifacts,
            "jellyfish_inputs": [],
            "hash_size_plan": hash_size_plan,
            "source_fingerprints": source_fingerprints,
            "provenance": binary_provenance(rustkmer,
                                            RUSTKMER_BUILD_PROFILE),
            "created": _now_iso(),
            "retention": RETENTION_NOTE,
        }
        write_manifest(manifest_path, manifest)
        return manifest

    # stage == "jf": complete the existing manifest.
    manifest = load_manifest(artifacts_dir)
    missing = [str(k) for k in ks
               if str(k) not in manifest.get("hash_size_plan", {})]
    if missing:
        raise ValueError(
            f"manifest hash_size_plan has no entry for k={missing} — run "
            "`build --stage rkdb` first")
    # The .rkdb identity the -s plan was derived from must still hold
    # before anything is built on top of it.
    verify_recorded_artifacts(manifest, rustkmer)
    recorded_sources = {entry["path"]: entry
                        for entry in manifest.get("source_fingerprints", [])}
    for part, fp in zip(parts, source_fingerprints):
        recorded = recorded_sources.get(fp["path"])
        if recorded is None:
            raise RuntimeError(
                f"source part {part} is not recorded in the manifest "
                "source_fingerprints")
        if (fp["sha256"] != recorded["sha256"]
                or fp["size_bytes"] != recorded["size_bytes"]):
            raise RuntimeError(
                f"source part {part} changed since the rkdb stage — "
                "refusing to build .jf inputs on drifted sources")
    jellyfish_inputs = []
    for k in ks:
        plan = manifest["hash_size_plan"][str(k)]
        hash_size = plan["hash_size"]
        for part in parts:
            token = part_token(part)
            out = artifacts_dir / f"{token}.k{k}.jf"
            cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                                  hash_size=hash_size, inputs=[part])
            argv = jellyfish_count_cmd(cfg, out)
            run_command(argv)
            fp = fingerprint(out)
            info = jellyfish_info(out, jellyfish_bin)
            jellyfish_inputs.append({
                "path": str(out),
                "size_bytes": fp["size_bytes"],
                "sha256": fp["sha256"],
                "k": k,
                "hash_size": hash_size,
                "jellyfish_info": info,
            })
            print(f"counted {part.name} -> {out.name} (-s {hash_size})")
    per_k_sizes = {}
    for record in jellyfish_inputs:
        per_k_sizes.setdefault(record["k"], set()).add(record["hash_size"])
    for k, sizes in per_k_sizes.items():
        if len(sizes) != 1:
            raise RuntimeError(
                f"jellyfish inputs for k={k} do not share one hash size: "
                f"{sizes!r} — merge enforces hash-size equality")
    manifest["jellyfish_inputs"] = jellyfish_inputs
    manifest["stage"] = "complete"
    write_manifest(manifest_path, manifest)
    return manifest


# --- revalidate + manifest verbs ----------------------------------------------


def revalidate_stage(artifacts_dir, rustkmer=DEFAULT_RUSTKMER):
    """Re-hash and re-stats every recorded artifact; fail loud on drift.

    Also rejects any .rkdb/.jf in the artifacts dir that carries no
    manifest record — an unrecorded artifact is a loud error, never a
    silent rebuild (probe MBENCH-01/empty applied to identity).

    Returns the verified manifest. Raises RuntimeError on any mismatch.
    """
    artifacts_dir = Path(artifacts_dir)
    manifest = load_manifest(artifacts_dir)
    if not manifest.get("artifacts"):
        raise RuntimeError(
            f"revalidate: manifest {artifacts_dir / MANIFEST_NAME} "
            "records no artifacts — an empty manifest is a loud error, "
            "never a silent rebuild (probe MBENCH-01/empty)")
    verify_recorded_artifacts(manifest, rustkmer)
    recorded_names = {
        Path(record["path"]).name
        for record in (manifest["artifacts"]
                       + manifest.get("jellyfish_inputs", []))
    }
    for path in sorted(artifacts_dir.iterdir()):
        if (path.is_file() and path.suffix in (".rkdb", ".jf")
                and path.name not in recorded_names):
            raise RuntimeError(
                f"revalidate: artifact {path.name} has no manifest "
                "record — an unrecorded artifact is a loud error, never "
                "a silent rebuild (probe MBENCH-01/empty)")
    return manifest


def show_manifest(artifacts_dir):
    """Print the manifest path and a compact artifact table to stdout."""
    manifest = load_manifest(artifacts_dir)
    plans = manifest.get("hash_size_plan", {})
    print(f"manifest: {Path(artifacts_dir) / MANIFEST_NAME}")
    print("path\tpath_bytes\tk\t-s\tdistinct\ttotal")
    for record in manifest.get("artifacts", []):
        plan = plans.get(str(record["k"]), {})
        print(f"{Path(record['path']).name}\t{record['size_bytes']}\t"
              f"{record['k']}\t{plan.get('hash_size', '-')}\t"
              f"{record['distinct']}\t{record['total']}")
    for record in manifest.get("jellyfish_inputs", []):
        print(f"{Path(record['path']).name}\t{record['size_bytes']}\t"
              f"{record['k']}\t{record['hash_size']}\t-\t-")
    return manifest


# --- CLI ----------------------------------------------------------------------


def main(argv=None):
    """Run the prepare-inputs CLI; invalid inputs always exit 2."""
    parser = argparse.ArgumentParser(
        prog="prepare_inputs.py",
        description="Build, revalidate, and describe the Phase-11 "
                    "full-scale merge input artifacts (D-01/D-03/D-04).")
    subparsers = parser.add_subparsers(dest="verb", required=True)

    build_p = subparsers.add_parser(
        "build", help="build artifacts and (re)write the manifest")
    build_p.add_argument(
        "--stage", required=True, choices=("rkdb", "jf"),
        help="rkdb counts first (produces per-part Distinct + the -s "
             "plan); jf completes the manifest with the .jf inputs")
    build_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                         help="split-parts source directory")
    build_p.add_argument("--artifacts-dir",
                         default=str(DEFAULT_ARTIFACTS_DIR),
                         help="artifacts root (must be outside the repo)")
    build_p.add_argument("--rustkmer", default=str(DEFAULT_RUSTKMER),
                         help="rustkmer release binary path")
    build_p.add_argument("--threads", type=int, default=None,
                         help="count threads (default: all cores)")

    reval_p = subparsers.add_parser(
        "revalidate", help="re-hash + re-stats every recorded artifact")
    reval_p.add_argument("--artifacts-dir",
                         default=str(DEFAULT_ARTIFACTS_DIR),
                         help="artifacts root holding manifest.json")
    reval_p.add_argument("--rustkmer", default=str(DEFAULT_RUSTKMER),
                         help="rustkmer release binary path")

    man_p = subparsers.add_parser(
        "manifest", help="print the manifest path + a compact table")
    man_p.add_argument("--artifacts-dir",
                       default=str(DEFAULT_ARTIFACTS_DIR),
                       help="artifacts root holding manifest.json")

    args = parser.parse_args(argv)
    try:
        if args.verb == "build":
            build_stage(args.data_dir, args.artifacts_dir, args.stage,
                        rustkmer=args.rustkmer, threads=args.threads)
        elif args.verb == "revalidate":
            manifest = revalidate_stage(args.artifacts_dir,
                                        rustkmer=args.rustkmer)
            print(f"revalidate OK: {len(manifest['artifacts'])} artifacts "
                  f"+ {len(manifest.get('jellyfish_inputs', []))} jellyfish "
                  f"inputs verified against "
                  f"{Path(args.artifacts_dir) / MANIFEST_NAME}")
        else:
            show_manifest(args.artifacts_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    main()
