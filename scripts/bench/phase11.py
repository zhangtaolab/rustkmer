#!/usr/bin/env python3
"""Phase-12 full-scale merge-verdict controller (``scripts/bench/phase11.py``).

D-01 locks the controller FILE name as ``phase11.py`` — the phase10.py
controller-name lineage is deliberate (do NOT rename to phase12.py) — while
the evidence documents it writes carry the phase-12 roadmap prefix to match
the ``12-*.json`` evidence filenames.

Stages — the order is pinned by construction (parity before timing; the
streaming deep-leg form is the ONLY full-scale route, WR-01):

  revalidate   round-0 gate: re-hash + re-stats the prepared artifacts,
               union-anchor equality, full session budget (this file)
  parity       three-way parity gate per k; deep legs streamed (this file;
               Leg 2 is the NEW independent-recount diff through the
               streaming pipeline — the WR-01 structural fix)
  timed        3 merge arms x 3 counterbalanced reps per k (plan 12-04)
  verdict      invest/no-invest from recorded medians (exit 0/1 — this file)
  render       mechanical report + byte-identical re-render proof (this file)

The verdict stage is a pure comparison of RECORDED medians: exit 0 =
NO-INVEST (rustkmer merge matches-or-beats the jellyfish-merge median at
both k), exit 1 = INVEST (loses at either k), exit 2 = invalid/infrastructure
(no artifact written), and the disk-floor block keeps bench.py's exit 3. Any
stage exception maps to exit 2 — the verdict codes are reserved for recorded
observations; a measured NO publishes its artifacts.

Python 3.11+ stdlib only — no third-party imports, no pip installs.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/phase11.py): insert the repo
    # root BEFORE importing so the harness package resolves to this checkout
    # in one shot (phase10.py's fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    BYTES_PER_GIB,
    DEFAULT_COOLDOWN_S,
    DEFAULT_DISK_FLOOR_GB,
    DEFAULT_RUSTKMER,
    MEASURED_INPUT_ARTIFACTS_BYTES,
    REPO_ROOT,
    SCHEMA_VERSION,
    BenchmarkConfig,
    assert_merge_parity,
    attempt_cache_purge,
    binary_provenance,
    build_merge_cmd,
    check_disk_floor,
    ensure_disk_headroom,
    fingerprint,
    jellyfish_merge_cmd,
    jellyfish_stats,
    reduce_arm,
    rustkmer_count_cmd,
    stats,
    validate_provenance,
    validate_schema,
)
from scripts.bench.output_stage import rotation_schedule
from scripts.bench.merge_characterize import (
    FULL_SCALE_CAVEAT,
    UNION_DISTINCT_ANCHORS,
    _normalized_sorted_dump,
    dump_vs_dump_equal_streaming,
    measured_run,
    route_from_stderr,
)
from scripts.bench.prepare_inputs import (
    DEFAULT_ARTIFACTS_DIR,
    revalidate_stage,
    run_command,
)
from scripts.bench.phase10 import (
    publish_atomic,
    write_doc,
    write_evidence_doc,
)

# NOTE: `attempt_cache_purge`, `check_disk_floor`, `ensure_disk_headroom`,
# `rotation_schedule`, `measured_run`, `route_from_stderr`,
# `dump_vs_dump_equal_streaming`, `_normalized_sorted_dump`, `revalidate_stage`,
# `run_command`, `stats`, `jellyfish_stats`, `reduce_arm`, `rustkmer_count_cmd`,
# `BenchmarkConfig`, and `write_doc` are the session-stage seams plan 12-04
# consumes (run_revalidate / run_parity / run_timed). They are imported HERE so
# the controller's dependency surface is pinned in one place; this plan wires
# only the verdict and render stages.

EXIT_OK = 0        # valid result (the verdict stage's measured YES)
EXIT_NO = 1        # a genuine measured NO (artifact kept/published)
EXIT_INVALID = 2   # invalid/inapplicable (no artifact written)

# D-01: the stage order is pinned by construction — parity BEFORE timing, so
# the WR-01 hazard (a deep gate over in-process state at full scale) is
# structurally impossible in this controller.
STAGES = ("revalidate", "parity", "timed", "verdict", "render")

PHASE = 12  # roadmap phase recorded in doc dicts

# Controller-name lineage (D-01 / 12-PATTERNS.md): the verdict line and the
# verdict document kind carry `phase11`, matching the file name.
VERDICT_PREFIX = "PHASE11 VERDICT"

# Evidence document kinds. The verdict kind carries the phase11 controller
# lineage; the session evidence kinds carry the phase-12 roadmap prefix to
# match the 12-*.json evidence filenames (12-PATTERNS.md §7).
KIND_VERDICT = "phase11-merge-verdict"
KIND_PARITY = "phase12-merge-parity"
KIND_ROUND0 = "phase12-round0-revalidation"
KIND_RENDER_PROOF = "phase12-render-proof"

# The three timed merge arms, in the pinned report order (research Pattern 3).
MERGE_ARMS = ("merge", "merge-t1", "jellyfish-merge")

# D-02: the protocol minimum — 3 counterbalanced reps per arm. The ladder
# showed linear scaling with tight ratios, so extra reps buy little.
REPS = 3

PARITY_KS = (21, 31)

# Fixed inputs / evidence locations for the full-scale stages (plan 12-02+).
DEFAULT_DATA_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")
# Same APFS volume as the inputs — deep-leg `sort -T` locality (research A3).
DEFAULT_SCRATCH = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch")
# The pinned part pair (Phase 11 D-04 / 11-PREPARE-RECORD.md §3): the parity
# and timed stages consume the PREPARED artifacts; these source paths anchor
# the round-0 source-fingerprint cross-check.
PART_PATHS = {
    "part_001": DEFAULT_DATA_DIR / "CRR1936095_r1.part_001.fq.gz",
    "part_006": DEFAULT_DATA_DIR / "CRR1936095_r1.part_006.fq.gz",
}

# PARITY-GATE.md §2 + 11-PREPARE-RECORD.md §3: the committed Phase-10 union
# Total anchors (SUM-OF-COUNTS definition from the stats readers — never the
# header record-count field, IN-03). Exact round-0 equality targets.
UNION_TOTALS = {21: 8_967_099_203, 31: 8_275_694_030}

# 11-LADDER-RESULTS.json provenance — binary-identity tripwires. A rebuilt
# rustkmer or an upgraded jellyfish breaks predicted-vs-measured attribution:
# escalate, never rebuild (12-PATTERNS.md shared pattern).
RUSTKMER_BIN_SHA256 = (
    "4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b")
JELLYFISH_BIN_SHA256 = (
    "e99c676bbead8f5f520b84359088740aa853b0a0b3b122a21373fe93ae8091ee")
JELLYFISH_BUILD_PROFILE = "pinned-comparator-2.3.1"

# The pre-agreed disclosure wording (.planning/research/SUMMARY.md, Pitfall 3).
ASYMMETRY_SENTENCE = ("each tool merges its own representation of identical, "
                      "parity-validated input data")

# Research assumption A3: conservative per-line byte estimate used to BUDGET
# the deep-gate dump transients (raw+norm coexist ≈ 2x dump text per side).
# A budget input, never a measurement.
DUMP_BYTES_PER_LINE = 30

# A2 — the verdict rule, stated verbatim inside the verdict document and
# every per-k block. Plan 12-02's gates read this field.
VERDICT_RULE = ("acceptance compares merge-arm wall medians only; rustkmer "
                "merge is YES at a k when its median wall <= the "
                "jellyfish-merge median wall at that k (equality is "
                "match-or-beat; no tolerance band); overall YES requires YES "
                "at both k=21 and k=31; merge-t1 is scaling evidence and "
                "never enters the verdict")

# Milestone Pitfall 6 / README wording: RSS framing + the t1 pool contract.
RSS_CONTEXT_FRAMING = (
    "Peak RSS and physical footprint are recorded per rep as context only — "
    "the merge verdict compares recorded wall medians only. No "
    "memory-superiority claim over the streaming jellyfish merge comparator "
    "is made or implied (milestone Pitfall 6).")
T1_POOL_CONTRACT = (
    "merge-t1 (--num-threads 1) reads as a like-for-like single-worker "
    "scheduling point: the CLI child pool contract is exactly 2 OS threads at "
    "N=1 (2N+1 at N>1, tests/thread_pool_size_tests.rs), not a one-OS-thread "
    "measurement; merge-t1 is scaling evidence and never enters the "
    "YES/NO verdict")

# The three-way gate legs a parity document must have executed (PARITY-GATE.md
# §2-§4; leg names pinned by plan 12-01 for the phase12-merge-parity kind).
PARITY_LEGS = ("leg1-aggregate-conservation", "leg2-recount-vs-merged",
               "leg3-dump-vs-dump")


def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict."""
    print(f"phase11.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def assert_binary_identity(provenance_fn=None):
    """Tripwire: the measured binaries must be the ladder's exact bytes.

    Compares the sha256 of the ACTUAL executable bytes (never the command
    string) against the 11-LADDER-RESULTS.json provenance constants. A
    rebuilt rustkmer or an upgraded jellyfish breaks predicted-vs-measured
    attribution — this raises naming both hashes; escalate, never rebuild.

    Returns {"rustkmer": binary dict, "jellyfish": binary dict,
    "provenance": the rustkmer release provenance block} — the block the
    evidence documents carry (T-12-06: no artifact lands without complete
    provenance, and it must attribute the hashed bytes themselves).
    """
    provenance_fn = binary_provenance if provenance_fn is None else provenance_fn
    rust_prov = provenance_fn(DEFAULT_RUSTKMER, "release")
    jf_prov = provenance_fn("jellyfish", JELLYFISH_BUILD_PROFILE)
    rust_sha = rust_prov["binary"]["sha256"]
    jf_sha = jf_prov["binary"]["sha256"]
    if rust_sha != RUSTKMER_BIN_SHA256 or jf_sha != JELLYFISH_BIN_SHA256:
        raise RuntimeError(
            "binary identity tripwire: rustkmer sha256 "
            f"{rust_sha} (expected {RUSTKMER_BIN_SHA256}) / jellyfish sha256 "
            f"{jf_sha} (expected {JELLYFISH_BIN_SHA256}) — a rebuilt or "
            "upgraded binary breaks predicted-vs-measured attribution "
            "(11-LADDER-RESULTS.json provenance); escalate, never rebuild")
    return {"rustkmer": rust_prov["binary"], "jellyfish": jf_prov["binary"],
            "provenance": rust_prov}


# --- merge arm argv (defaults-only by construction) --------------------------


def _manifest_inputs(manifest, section, k):
    """The pinned two-part input paths for one k, resolved FROM the manifest.

    Arms cannot drift from the parity-validated artifacts: the inputs are
    the revalidated manifest records, never re-derived paths.
    """
    records = [record for record in manifest.get(section, [])
               if isinstance(record, dict) and record.get("k") == k]
    if len(records) != 2:
        raise ValueError(
            f"merge_arm_argv: manifest section {section!r} carries "
            f"{len(records)} records for k={k} (expected the pinned "
            "part_001+part_006 pair) — refusing to build an arm from "
            "drifted inputs")
    return [record["path"] for record in
            sorted(records, key=lambda record: record["path"])]


def merge_arm_argv(name, k, manifest, scratch, rustkmer=DEFAULT_RUSTKMER):
    """Defaults-only merge argv for one timed arm (list form, no shell).

    `merge` passes NO --num-threads (tool default), `merge-t1` pins exactly
    --num-threads 1 (the like-for-like arm), and `jellyfish-merge` is
    defaults-only — no -t/-s exists on jellyfish merge and flag strings are
    never copied between subcommands (MBENCH-01).
    """
    if name not in MERGE_ARMS:
        raise ValueError(
            f"merge_arm_argv: unknown arm {name!r} (expected one of "
            f"{list(MERGE_ARMS)})")
    scratch = Path(scratch)
    if name in ("merge", "merge-t1"):
        inputs = _manifest_inputs(manifest, "artifacts", k)
        out_db = scratch / f"merged.k{k}.rkdb"
        num_threads = 1 if name == "merge-t1" else None
        return build_merge_cmd(rustkmer, out_db, inputs,
                               num_threads=num_threads)
    inputs = _manifest_inputs(manifest, "jellyfish_inputs", k)
    out_jf = scratch / f"merged.k{k}.jf"
    return jellyfish_merge_cmd(out_jf, inputs)


# --- round-0 revalidate stage (plan 12-04 Task 1) ----------------------------


def _now_iso():
    """UTC timestamp for evidence `created` fields (merge_characterize)."""
    return datetime.now(timezone.utc).isoformat()


# The .rkdb entry size (16-byte k-mer + 4-byte count, format.rs KmerEntry):
# the budget's timed-transient term prices the largest merged output at this
# ladder-fitted rate (11-FLOOR-DERIVATION.md §3). A budget input, never a
# measurement.
RKDB_BYTES_PER_ENTRY = 20


def session_budget(inputs_bytes=None, entries=None,
                   dump_bytes_per_line=DUMP_BYTES_PER_LINE,
                   rkdb_bytes_per_entry=RKDB_BYTES_PER_ENTRY):
    """D-12 session-budget arithmetic (pure, deterministic).

    The budget prices the whole session's working set in GiB:

    - inputs: the recorded artifact bytes (default MEASURED_INPUT_ARTIFACTS_
      BYTES, 11-PREPARE-RECORD.md §11);
    - parity transients per k: union Distinct x DUMP_BYTES_PER_LINE x 3 —
      raw+norm coexistence ~2x dump text per side + the sorted output ~1x
      (research A3; the sort's peak is sorted-A + norm-B + sorted-B = 3x);
    - timed transient: largest merged .rkdb output = max union Distinct x
      RKDB_BYTES_PER_ENTRY.

    # Arguments
    inputs_bytes: recorded input-artifact bytes; None uses the D-10 measured
        inventory constant.
    entries: union Distinct per k; None uses UNION_DISTINCT_ANCHORS — the
        11-LADDER-RESULTS.json summary.extrapolated_full_scale.
        full_scale_entries values (imported from the harness constant that
        wrote them, never re-transcribed).

    # Returns
    A breakdown dict whose `session_budget_gb` is the GiB integer the
    round-0 stage passes explicitly to check_disk_floor (D-12).
    """
    inputs = (MEASURED_INPUT_ARTIFACTS_BYTES if inputs_bytes is None
              else int(inputs_bytes))
    if inputs <= 0:
        raise ValueError(
            "session_budget: inputs_bytes must be > 0 (got "
            f"{inputs_bytes!r}) — a budget derived from nothing guards "
            "nothing")
    entry_map = ({str(k): int(v) for k, v in UNION_DISTINCT_ANCHORS.items()}
                 if entries is None
                 else {str(k): int(v) for k, v in entries.items()})
    if not entry_map:
        raise ValueError(
            "session_budget: entries must cover the union ks (got empty) — "
            "the deep-gate and merged-output transients price from the "
            "ladder's full_scale_entries")
    parity = {k: math.ceil(v * dump_bytes_per_line * 3 / BYTES_PER_GIB)
              for k, v in sorted(entry_map.items())}
    timed = math.ceil(max(entry_map.values()) * rkdb_bytes_per_entry
                      / BYTES_PER_GIB)
    inputs_gb = math.ceil(inputs / BYTES_PER_GIB)
    return {
        "session_budget_gb": inputs_gb + sum(parity.values()) + timed,
        "inputs_bytes": inputs,
        "inputs_gb": inputs_gb,
        "parity_transient_gb": parity,
        "parity_transient_terms": (
            "union Distinct x DUMP_BYTES_PER_LINE x 3 (raw+norm coexistence "
            "~2x dump text per side + the sorted output ~1x)"),
        "timed_transient_gb": timed,
        "timed_transient_terms": (
            "largest merged .rkdb output: max union Distinct x "
            "RKDB_BYTES_PER_ENTRY (20 B/entry)"),
        "constants": {
            "dump_bytes_per_line": dump_bytes_per_line,
            "rkdb_bytes_per_entry": rkdb_bytes_per_entry,
            "entries_source": (
                "UNION_DISTINCT_ANCHORS — 11-LADDER-RESULTS.json summary."
                "extrapolated_full_scale.full_scale_entries"),
        },
    }


def session_budget_gb(inputs_bytes=None, entries=None):
    """The GiB integer D-12 session budget (deterministic; see
    session_budget for the terms)."""
    return session_budget(inputs_bytes=inputs_bytes,
                          entries=entries)["session_budget_gb"]


def anchor_totals_from_manifest(manifest):
    """Per-k summed per-part Totals from the manifest's artifact records.

    The SUM-OF-COUNTS definition (PARITY-GATE.md §5): the manifest's `total`
    records were read by the sanctioned stats reader at prepare time and
    re-proved at revalidate time — never the DatabaseHeader record-count
    field (IN-03).
    """
    totals = {}
    for record in manifest.get("artifacts", []):
        k = record.get("k")
        if k not in PARITY_KS:
            raise RuntimeError(
                f"round-0 anchors: manifest records an artifact with "
                f"k={k!r} outside the pinned ks {list(PARITY_KS)}")
        totals[k] = totals.get(k, 0) + int(record["total"])
    for k in PARITY_KS:
        if k not in totals:
            raise RuntimeError(
                f"round-0 anchors: manifest records no per-part artifact "
                f"Totals for k={k} — the union anchor cannot reconcile")
    return totals


def assert_anchor_equality(manifest):
    """EXACT union-anchor equality per k (PARITY-GATE.md §2.1).

    The per-part input Totals must sum to the committed Phase-10 union
    anchors (8,967,099,203 at k=21; 8,275,694,030 at k=31) — recorded
    constants, not new measurements. Raises naming the computed sum and the
    expected anchor; otherwise returns the anchors dict keyed by the STRING
    k values ('21'/'31'), each entry carrying exactly {sum, expected,
    exact} — the layout plan 12-02's gates read.
    """
    totals = anchor_totals_from_manifest(manifest)
    anchors = {}
    for k in PARITY_KS:
        computed = totals[k]
        expected = UNION_TOTALS[k]
        if computed != expected:
            raise RuntimeError(
                f"round-0 anchor equality failed for k={k}: summed per-part "
                f"total {computed} != committed Phase-10 union anchor "
                f"{expected} (sum-of-counts definition from the sanctioned "
                "stats readers, never the header record-count field) — "
                "dataset drift or harness bug")
        anchors[str(k)] = {"sum": computed, "expected": expected,
                           "exact": True}
    return anchors


def check_source_fingerprints(manifest, source_paths=None,
                              fingerprint_fn=None):
    """Source-swap defense: re-fingerprint the pinned part pair.

    The prepared artifacts certify a specific pair of SOURCE read files
    (11-PREPARE-RECORD.md §3). A swapped or regenerated source invalidates
    everything downstream (Pitfall 8) — each pinned part is re-fingerprinted
    and compared against the manifest's source_fingerprints records, raising
    naming both hashes on any mismatch.
    """
    fingerprint_fn = fingerprint if fingerprint_fn is None else fingerprint_fn
    source_paths = PART_PATHS if source_paths is None else source_paths

    def record_for(name):
        """The one manifest record for a part name.

        The recorded paths name the real files (e.g.
        CRR1936095_r1.part_001.fq.gz), so matching is token-based on the
        file name/stem, never a bare equality against the part key.
        """
        matches = []
        for record in manifest.get("source_fingerprints", []):
            file_name = Path(record["path"]).name
            stem = Path(record["path"]).stem
            if (file_name == name
                    or file_name.startswith(f"{name}.")
                    or stem == name
                    or stem.endswith(f".{name}")):
                matches.append(record)
        return matches

    fingerprints = []
    for name in sorted(source_paths):
        path = Path(source_paths[name])
        matches = record_for(name)
        if not matches:
            raise RuntimeError(
                f"round-0 source cross-check: the manifest carries no "
                f"source_fingerprints record for {name} — the manifest "
                "predates the pinned part-pair contract "
                "(11-PREPARE-RECORD.md §3)")
        if len(matches) > 1:
            raise RuntimeError(
                f"round-0 source cross-check: ambiguous source_fingerprints "
                f"records for {name}: "
                f"{[record['path'] for record in matches]}")
        record = matches[0]
        if not path.is_file():
            raise RuntimeError(
                f"round-0 source cross-check: source part missing: {path}")
        fp = fingerprint_fn(path)
        if fp["sha256"] != record["sha256"]:
            raise RuntimeError(
                f"round-0 source cross-check: {name} sha256 {fp['sha256']} "
                f"!= recorded {record['sha256']} — the source reads were "
                "swapped or regenerated after the artifacts were prepared "
                "(Pitfall 8); everything downstream is invalid")
        if fp["size_bytes"] != record["size_bytes"]:
            raise RuntimeError(
                f"round-0 source cross-check: {name} size_bytes "
                f"{fp['size_bytes']} != recorded {record['size_bytes']}")
        fingerprints.append(fp)
    return fingerprints


def round0_doc(*, manifest_digest, anchors, budget, df_sample,
               binary_identity, source_fingerprints, provenance,
               artifacts_dir):
    """The phase12-round0-revalidation evidence document.

    `anchors` is keyed by the string k values ('21'/'31'), each entry
    carrying exactly {sum, expected, exact} — the layout plan 12-02's
    gates consume verbatim.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_ROUND0,
        "phase": PHASE,
        "session": "round0-revalidation",
        "created": _now_iso(),
        "artifacts_dir": str(artifacts_dir),
        "manifest_digest": manifest_digest,
        "anchors": anchors,
        "anchors_definition": (
            "per-part Totals summed across the pinned part pair and compared "
            "EXACT against the committed Phase-10 union anchors — the "
            "sum-of-counts definition from the sanctioned stats readers, "
            "never the DatabaseHeader record-count field (PARITY-GATE.md §5)"),
        "binary_identity": binary_identity,
        "session_budget": budget,
        "df_sample": df_sample,
        "source_fingerprints": source_fingerprints,
        "input_revalidation": (
            "green (revalidate_stage re-hash + re-stats over every recorded "
            "artifact; unrecorded artifacts rejected loudly)"),
        "provenance": provenance,
    }


def run_revalidate(args, *, revalidate_fn=None, provenance_fn=None,
                   fingerprint_fn=None, df_fn=None, budget_fn=None,
                   disk_fn=None, source_paths=None, artifacts_dir=None,
                   manifest_path=None):
    """Round-0 gate: revalidate, anchor equality, budget, round-0 doc.

    The controller invokes — never reimplements — the prepare-inputs
    revalidation: revalidate_stage re-hashes and re-stats every recorded
    artifact and rejects unrecorded ones (the tamper tripwire), and
    assert_binary_identity pins the measured binaries to the ladder
    provenance. A failure raises; the top-level handler maps raises to
    exit 2 with NO artifact written — a failed gate never lands a doc.
    """
    revalidate_fn = revalidate_stage if revalidate_fn is None else revalidate_fn
    provenance_fn = binary_provenance if provenance_fn is None else provenance_fn
    fingerprint_fn = fingerprint if fingerprint_fn is None else fingerprint_fn
    df_fn = shutil.disk_usage if df_fn is None else df_fn
    budget_fn = session_budget if budget_fn is None else budget_fn
    disk_fn = check_disk_floor if disk_fn is None else disk_fn
    source_paths = PART_PATHS if source_paths is None else source_paths
    artifacts_dir = (DEFAULT_ARTIFACTS_DIR if artifacts_dir is None
                     else Path(artifacts_dir))
    manifest_path = (artifacts_dir / "manifest.json"
                     if manifest_path is None else Path(manifest_path))
    identity = assert_binary_identity(provenance_fn=provenance_fn)
    manifest = revalidate_fn(artifacts_dir)
    anchors = assert_anchor_equality(manifest)
    source_fingerprints = check_source_fingerprints(
        manifest, source_paths=source_paths, fingerprint_fn=fingerprint_fn)
    inputs_bytes = sum(
        int(record["size_bytes"])
        for record in [*manifest.get("artifacts", []),
                       *manifest.get("jellyfish_inputs", [])])
    budget = budget_fn(inputs_bytes=inputs_bytes)
    # D-12: the COMPUTED session budget is passed explicitly — the floor is
    # not a round number and the exit-3 block semantics stay untouched
    # (override only via the explicit flag).
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    disk_fn(scratch, budget["session_budget_gb"],
            override=args.disk_floor_override, phase="round-0")
    usage = df_fn(str(scratch))
    df_sample = {"path": str(scratch), "total": usage.total,
                 "used": usage.used, "free": usage.free}
    doc = round0_doc(
        manifest_digest=fingerprint_fn(manifest_path), anchors=anchors,
        budget=budget, df_sample=df_sample,
        binary_identity={"rustkmer": identity["rustkmer"],
                         "jellyfish": identity["jellyfish"]},
        source_fingerprints=source_fingerprints,
        provenance=identity["provenance"],
        artifacts_dir=artifacts_dir)
    write_evidence_doc(doc, Path(args.out))
    print(f"PHASE11 ROUND0 anchors=exact "
          f"budget_gb={budget['session_budget_gb']} "
          f"artifacts={len(manifest.get('artifacts', []))}")
    return EXIT_OK


# --- parity stage: three-way gate with the NEW Leg-2 recount diff ------------


def recount_vs_merged_equal(recount_rkdb, merged_rkdb,
                            rustkmer=DEFAULT_RUSTKMER, workdir=None, *,
                            recount_dump_builder=None,
                            merged_dump_builder=None):
    """Leg 2 — the independent-recount diff (NEW code, no analog).

    The only parity leg anchored OUTSIDE the two merge tools (PARITY-GATE.md
    §3): the recount database (one count over both parts as a single input
    list) is per-k-mer diffed against the merged database through the SAME
    streaming pipeline as the cross-tool gate — two `_normalized_sorted_dump`
    sides with via_stdout=False semantics (a rustkmer dump -o side writes
    its own file; stdout is never captured), then the same streaming
    zip-compare (first difference named with both sides, length equality
    required, sorted files unlinked in finally).

    Returns True on exact per-k-mer equality; raises RuntimeError otherwise.
    """
    workdir = Path(workdir) if workdir is not None else DEFAULT_SCRATCH / "leg2"
    workdir.mkdir(parents=True, exist_ok=True)

    def default_builder(db_path):
        return lambda raw: [str(rustkmer), "dump", str(db_path), "-o",
                            str(raw)]

    recount_builder = (default_builder(recount_rkdb)
                       if recount_dump_builder is None
                       else recount_dump_builder)
    merged_builder = (default_builder(merged_rkdb)
                      if merged_dump_builder is None else merged_dump_builder)
    recount_sorted, recount_lines = _normalized_sorted_dump(
        recount_builder, workdir, "recount", "recount side", via_stdout=False)
    merged_sorted, merged_lines = _normalized_sorted_dump(
        merged_builder, workdir, "merged", "merged side", via_stdout=False)
    try:
        with open(recount_sorted, "r", encoding="utf-8") as fa, \
                open(merged_sorted, "r", encoding="utf-8") as fb:
            compared = 0
            for la, lb in zip(fa, fb):
                if la != lb:
                    raise RuntimeError(
                        f"recount-vs-merged gate: dumps differ at sorted "
                        f"line {compared}: recount={la!r} vs "
                        f"merged={lb!r} — per-k-mer parity violated")
                compared += 1
        if compared != recount_lines or compared != merged_lines:
            raise RuntimeError(
                f"recount-vs-merged gate: dumps differ in length: recount "
                f"{recount_lines} lines vs merged {merged_lines} lines (the "
                f"first {compared} sorted lines agree) — per-k-mer parity "
                "violated")
        return True
    finally:
        for leftover in (recount_sorted, merged_sorted):
            try:
                leftover.unlink()
            except OSError:
                pass


def parity_doc(*, k, anchors_exact_total, merges, merged_stats,
               recount_stats, input_revalidation, binary_identity,
               transients_deleted, provenance, legs=None):
    """The phase12-merge-parity evidence document.

    Aggregate-only parity is never presented as parity: the doc records all
    three gate legs, EXACT anchor equality, and the warmup-marked merges
    (A5: the parity merges double as the protocol's discarded warmups — the
    timed stage cites them as warmup_provenance and runs no additional
    warmup). The builder never emits an inexact document.
    """
    if k not in PARITY_KS:
        raise ValueError(
            f"parity doc: k {k!r} is not one of {list(PARITY_KS)}")
    if anchors_exact_total != UNION_TOTALS[k]:
        raise ValueError(
            f"parity k={k}: merged Total {anchors_exact_total} != union "
            f"anchor {UNION_TOTALS[k]} — the builder never emits an inexact "
            "parity document (PARITY-GATE.md §2 anchors are EXACT)")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_PARITY,
        "phase": PHASE,
        "session": "merge-parity",
        "k": k,
        "created": _now_iso(),
        "legs_executed": list(PARITY_LEGS if legs is None else legs),
        "anchors": {
            "sum": anchors_exact_total,
            "expected": UNION_TOTALS[k],
            "actual": anchors_exact_total,
            "exact": True,
            "definition": "sum-of-counts",
        },
        "merges": list(merges),
        "warmup_note": (
            "the parity merges are the protocol's discarded warmups (A5): "
            "their walls are recorded but never enter any timed median; the "
            "timed stage records them as warmup_provenance"),
        "merged_stats": merged_stats,
        "recount": recount_stats,
        "input_revalidation": input_revalidation,
        "binary_identity": binary_identity,
        "transients_deleted": list(transients_deleted),
        "provenance": provenance,
    }


def run_parity(args, *, revalidate_fn=None, provenance_fn=None,
               measure_fn=None):
    """Three-way parity gate for one k; write the parity evidence doc.

    One warmup-marked merge per tool (A5), then the three legs in order:
    Leg 1 aggregate conservation (assert_merge_parity, sum-of-counts), the
    NEW Leg 2 independent-recount diff through the streaming pipeline, and
    Leg 3 the cross-tool streaming dump-vs-dump verdict gate. Deep legs run
    ONLY the streaming form (WR-01). Transients are deleted in sequence and
    the deletions are recorded. Any gate failure raises — exit 2, no doc.
    """
    revalidate_fn = revalidate_stage if revalidate_fn is None else revalidate_fn
    provenance_fn = binary_provenance if provenance_fn is None else provenance_fn
    measure_fn = measured_run if measure_fn is None else measure_fn
    if not args.round0:
        invalid("the parity stage requires --round0 <the round-0 "
                "revalidation document> — parity runs only after the "
                "round-0 gate (structural stage order, D-01)")
    round0_path = Path(args.round0)
    round0 = _load_json(round0_path)
    if not isinstance(round0, dict) or round0.get("kind") != KIND_ROUND0:
        invalid(f"{round0_path} is not a {KIND_ROUND0!r} document — the "
                "parity stage refuses to run without a valid round-0 gate")
    identity = assert_binary_identity(provenance_fn=provenance_fn)
    manifest = revalidate_fn(DEFAULT_ARTIFACTS_DIR)
    anchors = assert_anchor_equality(manifest)
    input_revalidation = {
        "revalidate": (
            "green (revalidate_stage re-hash + re-stats at stage start — "
            "input-swap defense)"),
        "binary_identity": (
            "green (pinned ladder sha256 verified at stage start)"),
        "anchors": anchors,
    }
    k = args.k
    rustkmer = args.rustkmer
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    provenance = provenance_fn(rustkmer, "release")

    # -- one merge per tool, warmup-marked (A5). Honest cache_state labels;
    #    the walls are recorded but never enter any timed median.
    rk_argv = merge_arm_argv("merge", k, manifest, scratch, rustkmer=rustkmer)
    rk_cache = attempt_cache_purge()
    rk_rep, _rk_stderr = measure_fn(rk_argv)
    jf_argv = merge_arm_argv("jellyfish-merge", k, manifest, scratch,
                             rustkmer=rustkmer)
    jf_cache = attempt_cache_purge()
    jf_rep, _jf_stderr = measure_fn(jf_argv)
    merges = [
        {"tool": "rustkmer", "warmup": True, "argv": rk_argv,
         "wall_s": rk_rep["wall_s"], "cache_state": rk_cache},
        {"tool": "jellyfish", "warmup": True, "argv": jf_argv,
         "wall_s": jf_rep["wall_s"], "cache_state": jf_cache},
    ]
    merged_rkdb = scratch / f"merged.k{k}.rkdb"
    merged_jf = scratch / f"merged.k{k}.jf"
    rk_stats_d = stats(merged_rkdb, rustkmer)
    jf_stats_d = jellyfish_stats(merged_jf)

    # -- Leg 1: aggregate conservation (the fast pre-gate). Every value is
    #    the SUM-OF-COUNTS definition carried by the sanctioned stats
    #    readers — never the header record-count field (IN-03).
    part_records = sorted(
        (record for record in manifest.get("artifacts", [])
         if record.get("k") == k),
        key=lambda record: record["path"])
    if len(part_records) != 2:
        raise RuntimeError(
            f"parity k={k}: manifest carries {len(part_records)} artifact "
            "records (expected the pinned part_001+part_006 pair)")
    count_a, count_b = part_records
    by_name = {
        "count-A": {"distinct_kmers": count_a["distinct"],
                    "total_kmers": count_a["total"]},
        "count-B": {"distinct_kmers": count_b["distinct"],
                    "total_kmers": count_b["total"]},
        "merge": {"distinct_kmers": rk_stats_d["unique_kmers"],
                  "total_kmers": rk_stats_d["total_kmers"]},
        "jellyfish-merge": {"distinct_kmers": jf_stats_d["distinct"],
                            "total_kmers": jf_stats_d["total"]},
    }
    assert_merge_parity(by_name)
    merged_total = by_name["merge"]["total_kmers"]

    # -- Leg 2 (NEW, no analog): independent recount of the union — one
    #    count over BOTH parts as a single input list — anchored outside the
    #    two merge tools. Untimed (prepare_inputs.run_command), then
    #    per-k-mer diffed against the merged db through the streaming
    #    pipeline (WR-01: never any in-process form at full scale).
    leg2_dir = scratch / f"leg2.k{k}"
    recount_rkdb = scratch / f"recount.k{k}.rkdb"
    recount_cfg = BenchmarkConfig(
        k=k, canonical=True, threads=os.cpu_count(),
        inputs=[PART_PATHS["part_001"], PART_PATHS["part_006"]])
    run_command(rustkmer_count_cmd(recount_cfg, recount_rkdb,
                                   rustkmer=rustkmer))
    recount_stats_d = stats(recount_rkdb, rustkmer)
    if recount_stats_d["unique_kmers"] <= 0:
        raise RuntimeError(
            f"parity k={k}: recount produced zero distinct k-mers — an "
            "empty recount can never pass the gate (MBENCH-01/empty)")
    if recount_stats_d["total_kmers"] != UNION_TOTALS[k]:
        raise RuntimeError(
            f"parity k={k}: recount Total {recount_stats_d['total_kmers']} "
            f"!= union anchor {UNION_TOTALS[k]} (sum-of-counts definition) "
            "— the independent recount does not reproduce the union; "
            "aborting before the per-k-mer diff")
    recount_vs_merged_equal(recount_rkdb, merged_rkdb, rustkmer,
                            workdir=leg2_dir)
    # Deletion sequencing (research Pitfall 5): the recount db is dead once
    # its sorted dump exists — the compare's finally already unlinked the
    # sorted transients, so unlink the recount db immediately.
    recount_rkdb.unlink()
    transients_deleted = [str(recount_rkdb)]

    # -- Leg 3: the verdict gate — cross-tool dump-vs-dump, streamed.
    leg3_dir = scratch / f"leg3.k{k}"
    dump_vs_dump_equal_streaming(merged_rkdb, merged_jf, rustkmer,
                                 workdir=leg3_dir)
    # Merged outputs die only after Leg 3 is green; then the leg workdirs.
    for merged_out in (merged_rkdb, merged_jf):
        merged_out.unlink()
        transients_deleted.append(str(merged_out))
    for leg_dir in (leg2_dir, leg3_dir):
        shutil.rmtree(leg_dir, ignore_errors=True)
        transients_deleted.append(str(leg_dir) + "/")

    doc = parity_doc(
        k=k, anchors_exact_total=merged_total, merges=merges,
        merged_stats={
            "rustkmer": {"distinct": rk_stats_d["unique_kmers"],
                         "total": rk_stats_d["total_kmers"],
                         "definition": "sum-of-counts"},
            "jellyfish": {"distinct": jf_stats_d["distinct"],
                          "total": jf_stats_d["total"],
                          "definition": "sum-of-counts"},
        },
        recount_stats={"distinct": recount_stats_d["unique_kmers"],
                       "total": recount_stats_d["total_kmers"],
                       "definition": "sum-of-counts"},
        input_revalidation=input_revalidation,
        binary_identity={"rustkmer": identity["rustkmer"],
                         "jellyfish": identity["jellyfish"]},
        transients_deleted=transients_deleted,
        provenance=provenance)
    write_evidence_doc(doc, Path(args.out))
    print(f"PHASE11 PARITY k={k} legs=3/3 anchors_exact=true "
          f"recount=identical")
    return EXIT_OK


# --- verdict stage: pure comparison of recorded medians ----------------------


def _doc_k(doc):
    """The document's recorded k; raises unless it is one of the pinned ks."""
    params = doc.get("params") if isinstance(doc, dict) else None
    k = params.get("k") if isinstance(params, dict) else None
    if k not in PARITY_KS:
        raise ValueError(
            f"document params.k {k!r} is not one of the pinned merge-verdict "
            f"ks {list(PARITY_KS)}")
    return k


def _required_arm(doc, name, k, label="verdict"):
    """Exactly one recorded arm with `name`; missing/ambiguous is invalid."""
    matches = [arm for arm in doc.get("arms", [])
               if isinstance(arm, dict) and arm.get("name") == name]
    if len(matches) != 1:
        raise ValueError(
            f"{label}: k={k} document carries {len(matches)} {name!r} arms "
            "(exactly one required)")
    reps = matches[0].get("reps")
    if not isinstance(reps, list) or not reps:
        raise ValueError(f"{label}: k={k} {name!r} arm has no reps")
    return matches[0]


def _median_wall(arm, name, k, label="verdict"):
    """The arm's recorded median wall — a positive number, or invalid."""
    medians = arm.get("medians")
    wall = medians.get("wall_s") if isinstance(medians, dict) else None
    if (not isinstance(wall, (int, float)) or isinstance(wall, bool)
            or wall <= 0):
        raise ValueError(
            f"{label}: k={k} {name!r} arm median wall_s {wall!r} is not a "
            "positive recorded number")
    return float(wall)


def verdict_block(k, results_doc):
    """The k's merge-vs-jellyfish verdict from RECORDED medians, plus the rule.

    Pure: the merge arm median vs the jellyfish-merge arm median from the
    recorded arm dicts; match-or-beat `<=` (exact equality wins; no
    tolerance band). The merge-t1 arm is reported under `scaling` and never
    enters the YES/NO computation (A2).
    """
    params = (results_doc.get("params")
              if isinstance(results_doc, dict) else None)
    doc_k = params.get("k") if isinstance(params, dict) else None
    if doc_k is not None and doc_k != k:
        raise ValueError(
            f"verdict_block k={k} paired with a document for k={doc_k} — "
            "mismatched measurements")
    merge_arm = _required_arm(results_doc, "merge", k)
    jf_arm = _required_arm(results_doc, "jellyfish-merge", k)
    merge_wall = _median_wall(merge_arm, "merge", k)
    jf_wall = _median_wall(jf_arm, "jellyfish-merge", k)
    scaling = None
    for arm in results_doc.get("arms", []):
        if isinstance(arm, dict) and arm.get("name") == "merge-t1":
            medians = arm.get("medians")
            wall = (medians.get("wall_s")
                    if isinstance(medians, dict) else None)
            if isinstance(wall, (int, float)) and not isinstance(wall, bool):
                scaling = {"arm": "merge-t1", "threads": arm.get("threads"),
                           "wall_s": float(wall)}
            break
    return {
        "k": k,
        "result": "YES" if merge_wall <= jf_wall else "NO",
        "rustkmer_wall_s": merge_wall,
        "jellyfish_wall_s": jf_wall,
        "scaling": scaling,
        "rule": VERDICT_RULE,
    }


def verdict_line(verdict):
    """The one machine-greppable stdout line; repr() round-trips the floats."""
    return (
        f"{VERDICT_PREFIX} k={verdict['k']} result={verdict['result']} "
        f"rustkmer_wall_s={verdict['rustkmer_wall_s']!r} "
        f"jellyfish_wall_s={verdict['jellyfish_wall_s']!r}")


# --- document validation (what the stages may consume) -----------------------


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _validate_results_document(doc, label="results"):
    """Kind-tolerant gate over one timed results document.

    The timed docs ride results schema v1 (assemble_doc/validate_schema —
    never a second results schema, MBENCH-05); this adds the phase/session
    keys and the per-arm provenance the controller's stages rely on. A
    foreign phase, an evidence-kind document, or a count-era arm name is
    rejected loudly rather than silently consumed.
    """
    validate_schema(doc)
    validate_provenance(doc)
    if doc.get("phase") != PHASE:
        raise ValueError(
            f"{label}: document phase {doc.get('phase')!r} != {PHASE} — "
            "refusing to consume a foreign phase's measurements")
    session = doc.get("session")
    if not isinstance(session, str) or not session.strip():
        raise ValueError(f"{label}: document carries no session key")
    kind = doc.get("kind")
    if kind in (KIND_VERDICT, KIND_PARITY, KIND_ROUND0, KIND_RENDER_PROOF):
        raise ValueError(
            f"{label}: kind {kind!r} is an evidence kind, not a timed "
            "results document (never a second results schema — MBENCH-05)")
    for arm in doc.get("arms", []):
        if not isinstance(arm, dict) or arm.get("name") not in MERGE_ARMS:
            raise ValueError(
                f"{label}: arm {arm!r} is not one of the merge arms "
                f"{list(MERGE_ARMS)} — refusing to consume a non-merge "
                "results document")
        arm_prov = arm.get("provenance")
        if (not isinstance(arm_prov, dict)
                or not isinstance(arm_prov.get("binary"), dict)):
            raise ValueError(
                f"{label}: arm {arm.get('name')!r} carries no provenance "
                "block — a path without a hash is not provenance (T-05-02)")
        for key in ("unique_kmers", "total_kmers", "output_bytes"):
            value = arm.get(key)
            if (not isinstance(value, int) or isinstance(value, bool)
                    or value < 0):
                raise ValueError(
                    f"{label}: arm {arm.get('name')!r} carries {key!r} "
                    f"{value!r} — the rates need recorded non-negative "
                    "integers")
    return doc


def _validate_parity_document(doc, label="parity"):
    """Gate over one phase12-merge-parity evidence document.

    Aggregate-only parity is never accepted: the document must record all
    three gate legs (PARITY-GATE.md §2-§4), exact anchor equality, and the
    merges the gate ran against.
    """
    if not isinstance(doc, dict) or doc.get("kind") != KIND_PARITY:
        raise ValueError(
            f"{label}: kind {(doc or {}).get('kind')!r} != {KIND_PARITY!r} — "
            "refusing to consume a foreign document as parity evidence")
    if doc.get("phase") != PHASE:
        raise ValueError(
            f"{label}: document phase {doc.get('phase')!r} != {PHASE}")
    if doc.get("k") not in PARITY_KS:
        raise ValueError(
            f"{label}: parity k {doc.get('k')!r} is not one of "
            f"{list(PARITY_KS)}")
    legs = doc.get("legs_executed")
    if not isinstance(legs, list) or not set(PARITY_LEGS).issubset(set(legs)):
        raise ValueError(
            f"{label}: legs_executed {legs!r} does not cover the three-way "
            f"gate legs {list(PARITY_LEGS)} — aggregate-only parity is "
            "never accepted (PARITY-GATE.md §4)")
    anchors = doc.get("anchors")
    if not isinstance(anchors, dict) or anchors.get("exact") is not True:
        raise ValueError(
            f"{label}: anchors.exact must be true — the union anchors "
            f"{UNION_TOTALS} are the exact round-0 equality targets")
    merges = doc.get("merges")
    if not isinstance(merges, list) or not merges:
        raise ValueError(
            f"{label}: parity document carries no merge records")
    validate_provenance(doc)
    return doc


def _validate_verdict_document(doc, label="verdict"):
    """Gate over the phase11-merge-verdict carrier document.

    Pins the exact key layout plan 12-02's gates consume: top-level
    overall/decision/exit_code/rule plus per-k blocks carrying
    k/result/rustkmer_wall_s/jellyfish_wall_s.
    """
    if not isinstance(doc, dict) or doc.get("kind") != KIND_VERDICT:
        raise ValueError(
            f"{label}: kind {(doc or {}).get('kind')!r} != {KIND_VERDICT!r} "
            "— refusing to consume a foreign document as the verdict")
    if doc.get("phase") != PHASE:
        raise ValueError(
            f"{label}: document phase {doc.get('phase')!r} != {PHASE}")
    overall = doc.get("overall")
    if overall not in ("YES", "NO"):
        raise ValueError(f"{label}: overall {overall!r} is not YES|NO")
    decision = doc.get("decision")
    expected_decision = "NO-INVEST" if overall == "YES" else "INVEST"
    if decision != expected_decision:
        raise ValueError(
            f"{label}: decision {decision!r} is inconsistent with overall "
            f"{overall!r} (expected {expected_decision!r})")
    exit_code = doc.get("exit_code")
    expected_exit = EXIT_OK if overall == "YES" else EXIT_NO
    if exit_code != expected_exit:
        raise ValueError(
            f"{label}: exit_code {exit_code!r} is inconsistent with overall "
            f"{overall!r} (expected {expected_exit!r})")
    if doc.get("rule") != VERDICT_RULE:
        raise ValueError(
            f"{label}: rule {doc.get('rule')!r} is not the pinned verdict "
            "rule verbatim")
    blocks = doc.get("verdicts")
    if (not isinstance(blocks, list) or not blocks
            or sorted(block.get("k") for block in blocks) != list(PARITY_KS)):
        raise ValueError(
            f"{label}: verdicts {blocks!r} do not cover both pinned ks "
            f"{list(PARITY_KS)}")
    for block in blocks:
        for key in ("k", "result", "rustkmer_wall_s", "jellyfish_wall_s"):
            if key not in block:
                raise ValueError(
                    f"{label}: verdict block for k={block.get('k')!r} is "
                    f"missing {key!r}")
        if block.get("rule") != VERDICT_RULE:
            raise ValueError(
                f"{label}: verdict block for k={block.get('k')!r} does not "
                "carry the pinned rule verbatim")
        if block.get("result") not in ("YES", "NO"):
            raise ValueError(
                f"{label}: verdict block result {block.get('result')!r} is "
                "not YES|NO")
    validate_provenance(doc)
    return doc


def _measured_provenance(result_docs, label):
    """The measured provenance block carried by the results documents.

    The verdict/render stages consume recorded JSON only — they must not
    require a local release binary or Rust toolchain (WR-04 precedent): the
    artifact attributes the binary that actually produced the measurements.
    Every results document must name the same measured binary bytes.
    """
    provenance = None
    for doc in result_docs:
        block = doc.get("provenance")
        if not isinstance(block, dict):
            raise ValueError(
                f"{label}: results document carries no provenance")
        if provenance is None:
            provenance = block
        elif block.get("binary") != provenance.get("binary"):
            raise ValueError(
                f"{label}: results documents name different measured "
                f"binaries ({provenance.get('binary')!r} vs "
                f"{block.get('binary')!r}) — the artifact cannot attribute "
                "one measured CLI binary")
    if provenance is None:
        raise ValueError(f"{label}: no results documents to attribute")
    return provenance


# --- render stage: mechanical report + byte-identical re-render proof --------


def renderer_source_commit():
    """Last commit that touched THIS renderer (`phase11.py`) — provenance.

    Deterministic across re-renders (unrelated commits do not move it) and
    'unknown' outside a git checkout — deterministic in that environment
    too (phase10.py's IN-02 precedent).
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


def _threads_cell(threads):
    """The methodology row's threads cell — 'defaults' when unset."""
    return "defaults" if threads is None else str(threads)


def _headline_lines(verdict_doc):
    lines = [
        "## Verdict",
        "",
        "| k | verdict | rustkmer merge median wall (s) "
        "| jellyfish merge median wall (s) |",
        "|---|---|---|---|",
    ]
    for block in sorted(verdict_doc["verdicts"], key=lambda b: b["k"]):
        lines.append(
            f"| {block['k']} | {block['result']} "
            f"| {block['rustkmer_wall_s']!r} "
            f"| {block['jellyfish_wall_s']!r} |")
    lines += [
        "",
        f"Overall: **{verdict_doc['overall']}** — decision "
        f"**{verdict_doc['decision']}** (exit code "
        f"{verdict_doc['exit_code']}). Both outcomes are valid recorded "
        "results.",
        "",
        f"Rule: {verdict_doc['rule']}",
        "",
    ]
    return lines


def _methodology_lines(results_by_k):
    lines = []
    for k in PARITY_KS:
        doc = results_by_k[k]
        lines += [f"### Per-arm methodology (k={k})", ""]
        lines += [
            "| arm | tool | threads | argv | route | output sha256 "
            "| binary sha256 |",
            "|---|---|---|---|---|---|---|",
        ]
        for name in MERGE_ARMS:
            arm = _required_arm(doc, name, k, label="render")
            binary = arm["provenance"]["binary"]
            argv = " ".join(str(part)
                            for part in arm.get("command_line", []))
            lines.append(
                f"| {name} | {arm.get('tool')} "
                f"| {_threads_cell(arm.get('threads'))} | `{argv}` "
                f"| {arm.get('route')} | `{arm.get('output_sha256')}` "
                f"| `{binary.get('sha256')}` |")
        lines += ["", f"#### Rates (k={k}) — computed only from recorded "
                      "values", ""]
        lines += [
            "| arm | entry rate (distinct/s) | byte rate (output B/s) "
            "| output B/entry |",
            "|---|---|---|---|",
        ]
        for name in MERGE_ARMS:
            arm = _required_arm(doc, name, k, label="render")
            wall = _median_wall(arm, name, k, label="render")
            distinct = arm["unique_kmers"]
            out_bytes = arm["output_bytes"]
            entry_rate = distinct / wall
            byte_rate = out_bytes / wall
            bytes_per_entry = out_bytes / distinct
            lines.append(
                f"| {name} | {entry_rate!r} | {byte_rate!r} "
                f"| {bytes_per_entry!r} |")
        lines += ["", ""]
    return lines


def _predicted_lines(results_by_k, ladder_summary):
    """Predicted-vs-measured rows read from the ladder doc — caveat verbatim.

    The predictions are scheduling inputs with a recorded caveat; the
    measured medians are the deliverable; deviations are FINDINGS to record,
    never smoothed (milestone Pitfall 14).
    """
    extrapolated = ladder_summary["extrapolated_full_scale"]
    lines = [
        "## Predicted vs measured (ladder extrapolation)",
        "",
        "| k | arm | predicted wall (s) | measured median wall (s) "
        "| delta (s) |",
        "|---|---|---|---|---|",
    ]
    for k in PARITY_KS:
        doc = results_by_k[k]
        for arm_name, ladder_key in (
                ("merge", f"rustkmer_k{k}"),
                ("jellyfish-merge", f"jellyfish_k{k}")):
            arm = _required_arm(doc, arm_name, k, label="render")
            measured = _median_wall(arm, arm_name, k, label="render")
            prediction = extrapolated.get(ladder_key)
            if not isinstance(prediction, dict):
                raise ValueError(
                    f"render: ladder extrapolated_full_scale carries no "
                    f"{ladder_key!r} block")
            predicted = prediction.get("predicted_full_scale_wall_s")
            if (not isinstance(predicted, (int, float))
                    or isinstance(predicted, bool)):
                raise ValueError(
                    f"render: ladder {ladder_key!r} carries no "
                    "predicted_full_scale_wall_s number")
            delta = measured - float(predicted)
            lines.append(
                f"| {k} | {arm_name} | {float(predicted)!r} | {measured!r} "
                f"| {delta!r} |")
    lines += ["", f"Caveat: {extrapolated['caveat']}", ""]
    return lines


def _parity_lines(parity_docs):
    lines = ["## Parity evidence", ""]
    for doc in sorted(parity_docs, key=lambda item: item.get("k")):
        anchors = doc.get("anchors") or {}
        legs = ", ".join(doc.get("legs_executed", []))
        merges = doc.get("merges") or []
        lines.append(
            f"- k={doc.get('k')}: legs [{legs}]; anchors exact="
            f"{anchors.get('exact')} expected={anchors.get('expected')!r} "
            f"actual={anchors.get('actual')!r}; merges recorded="
            f"{len(merges)}")
    lines.append("")
    return lines


def _fingerprint_lines(results_docs):
    lines = ["## Input fingerprints", ""]
    seen = set()
    for doc in results_docs:
        for fp in doc.get("input_fingerprint") or []:
            key = (fp.get("path"), fp.get("sha256"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"- `{fp.get('path')}` — sha256=`{fp.get('sha256')}` "
                f"size_bytes={fp.get('size_bytes')}")
    lines.append("")
    return lines


def _jellyfish_provenance(results_docs):
    """The jellyfish arm's recorded provenance (disclosure row source)."""
    for doc in sorted(results_docs, key=_doc_k):
        for arm in doc.get("arms", []):
            if isinstance(arm, dict) and arm.get("name") == "jellyfish-merge":
                return arm.get("provenance")
    return None


def _provenance_lines(results_docs, verdict_doc):
    prov = (verdict_doc.get("provenance")
            or _measured_provenance(results_docs, "render"))
    binary = prov.get("binary") or {}
    lines = [
        "## Provenance",
        "",
        f"- rustkmer binary: `{binary.get('path')}` — "
        f"size_bytes={binary.get('size_bytes')} "
        f"sha256=`{binary.get('sha256')}`",
    ]
    jf_prov = _jellyfish_provenance(results_docs)
    if isinstance(jf_prov, dict):
        jf_binary = jf_prov.get("binary") or {}
        lines.append(
            f"- jellyfish binary: `{jf_binary.get('path')}` — "
            f"size_bytes={jf_binary.get('size_bytes')} "
            f"sha256=`{jf_binary.get('sha256')}` (build profile "
            f"{jf_prov.get('build_profile')})")
    lines += [
        f"- results build: git commit `{prov.get('git_commit')}`, dirty="
        f"{prov.get('git_dirty')}, profile {prov.get('build_profile')}, "
        f"{prov.get('rust_toolchain')}",
        "- Renderer source commit (last commit touching this renderer): "
        f"`{renderer_source_commit()}`",
        "",
    ]
    return lines


def render_report_text(docs):
    """Render the merge-verdict Markdown report from recorded documents.

    Mechanical by construction (threat T-12-01, T-04-07 contract): every
    number is read from the validated recorded documents, the only
    environment read is `renderer_source_commit()`, and no clock is
    consulted — re-rendering the same documents is byte-identical and the
    report carries no per-artifact clock fields, so a hand-edited number is
    detectable.

    `docs` is the mapping {"results": [k21, k31], "parity": [k21, k31],
    "verdict": verdict_doc, "ladder": ladder_doc}.
    """
    if not isinstance(docs, dict):
        raise ValueError(
            "render_report_text expects the docs mapping (results/parity/"
            "verdict/ladder)")
    results_docs = [_validate_results_document(doc, label="render results")
                    for doc in docs.get("results") or []]
    parity_docs = [_validate_parity_document(doc, label="render parity")
                   for doc in docs.get("parity") or []]
    verdict_doc = _validate_verdict_document(docs.get("verdict") or {},
                                             label="render verdict")
    ladder_doc = docs.get("ladder")
    if (not isinstance(ladder_doc, dict)
            or not isinstance(ladder_doc.get("summary"), dict)):
        raise ValueError("render: the ladder document carries no summary")
    ladder_summary = ladder_doc["summary"]
    for key in ("slopes", "extrapolated_full_scale"):
        if not isinstance(ladder_summary.get(key), dict):
            raise ValueError(
                f"render: ladder summary carries no {key!r} block")
    extrapolated = ladder_summary["extrapolated_full_scale"]
    caveat = extrapolated.get("caveat")
    if not isinstance(caveat, str) or not caveat.strip():
        raise ValueError(
            "render: ladder extrapolated_full_scale carries no caveat — no "
            "slice-scale number is presented as a full-scale prediction "
            "without it (milestone Pitfall 14)")
    if caveat != FULL_SCALE_CAVEAT:
        raise ValueError(
            "render: ladder caveat does not match the harness's own "
            "FULL_SCALE_CAVEAT wording — the document was not written by "
            "this harness; refusing to render it")
    if len(results_docs) != len(PARITY_KS):
        raise ValueError(
            f"render: expected {len(PARITY_KS)} results documents, got "
            f"{len(results_docs)}")
    results_by_k = {}
    for doc in results_docs:
        k = _doc_k(doc)
        if k in results_by_k:
            raise ValueError(f"render: two results documents carry k={k}")
        results_by_k[k] = doc
    missing = [k for k in PARITY_KS if k not in results_by_k]
    if missing:
        raise ValueError(f"render: missing results documents for k={missing}")
    if len(parity_docs) != len(PARITY_KS):
        raise ValueError(
            f"render: expected {len(PARITY_KS)} parity documents, got "
            f"{len(parity_docs)}")
    # The report renders ONE consistent evidence set: the verdict doc's
    # recorded walls must equal the results documents' recorded medians.
    for block in verdict_doc["verdicts"]:
        k = block["k"]
        for arm_name, key in (("merge", "rustkmer_wall_s"),
                              ("jellyfish-merge", "jellyfish_wall_s")):
            arm = _required_arm(results_by_k[k], arm_name, k, label="render")
            wall = _median_wall(arm, arm_name, k, label="render")
            if block[key] != wall:
                raise ValueError(
                    f"render: verdict doc k={k} {key} {block[key]!r} != the "
                    f"results document's recorded median {wall!r} — the "
                    "report cannot render inconsistent evidence")
    lines = [
        "# rustkmer vs Jellyfish2 — Phase 12 full-scale merge verdict report",
        "",
        "*Mechanically rendered from the committed evidence documents by "
        "`python3 scripts/bench/phase11.py --stage render`. Every number "
        "below is read from those documents — the renderer holds no "
        "measurement literals and consults no clock — so re-rendering "
        "reproduces this file byte-for-byte and a hand-edited number is "
        "detectable (T-12-01/T-04-07 contract). The report carries no "
        "per-artifact clock fields by construction.*",
        "",
    ]
    lines += _headline_lines(verdict_doc)
    lines += [
        "## Comparator-shape asymmetry",
        "",
        f"{ASYMMETRY_SENTENCE}. Threads/flags/merge-route/sha256 are "
        "recorded per arm below; defaults-only flags during measurement "
        "(no flag sweep — MBF-01 is post-verdict v2.2+ work, only on "
        "INVEST).",
        "",
    ]
    lines += _methodology_lines(results_by_k)
    lines += _predicted_lines(results_by_k, ladder_summary)
    lines += _parity_lines(parity_docs)
    lines += [
        "## Memory is context, not a decision axis",
        "",
        RSS_CONTEXT_FRAMING,
        "",
        T1_POOL_CONTRACT,
        "",
    ]
    lines += _fingerprint_lines(results_docs)
    lines += _provenance_lines(results_docs, verdict_doc)
    lines += [
        "---",
        "",
        "*Generated file — do not edit by hand. Regenerate with "
        "`python3 scripts/bench/phase11.py --stage render --results "
        "<k21 results> <k31 results> --parity-doc <k21 parity> <k31 parity> "
        "--verdict-doc 12-VERDICT.json --ladder-doc 11-LADDER-RESULTS.json "
        "--out 12-MERGE-REPORT.md --proof-out 12-RENDER-PROOF.json`; phase "
        "directory `.planning/phases/12-full-scale-merge-verdict/`.*",
        "",
    ]
    text = "\n".join(lines)
    if not text.strip():
        raise ValueError("render: the report text is empty")
    return text


# --- stage runners -----------------------------------------------------------


def run_verdict(args):
    """Compare recorded medians; write the 0/1/2-carrier verdict document.

    Both outcomes are valid recorded results: overall YES publishes with
    EXIT_OK (decision NO-INVEST); a genuine measured NO publishes with
    EXIT_NO (decision INVEST). Only an infrastructure failure raises and
    maps to EXIT_INVALID with NO artifact written — the verdict codes are
    reserved for recorded observations.
    """
    if not args.results or len(args.results) != 2:
        invalid("the verdict stage requires --results <k21 results> "
                "<k31 results>")
    out_path = Path(args.out)
    docs = [_validate_results_document(_load_json(path), label=str(path))
            for path in args.results]
    by_k = {}
    for doc in docs:
        k = _doc_k(doc)
        if k in by_k:
            invalid(f"two results documents carry k={k} — one per k")
        by_k[k] = doc
    missing = [k for k in PARITY_KS if k not in by_k]
    if missing:
        invalid(f"missing results documents for k={missing}")
    verdicts = [verdict_block(k, by_k[k]) for k in PARITY_KS]
    overall = "YES" if all(block["result"] == "YES"
                           for block in verdicts) else "NO"
    decision = "NO-INVEST" if overall == "YES" else "INVEST"
    exit_code = EXIT_OK if overall == "YES" else EXIT_NO
    verdict_doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_VERDICT,
        "phase": PHASE,
        "session": "merge-verdict",
        "created": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "decision": decision,
        "exit_code": exit_code,
        "rule": VERDICT_RULE,
        "verdicts": verdicts,
        "inputs": [fingerprint(path) for path in args.results],
        "provenance": _measured_provenance(docs, "verdict"),
    }
    validate_provenance(verdict_doc)
    write_evidence_doc(verdict_doc, out_path)
    for block in verdicts:
        print(verdict_line(block))
    print(f"{VERDICT_PREFIX} overall={overall} decision={decision} "
          f"exit_code={exit_code}")
    return exit_code


def run_render(args):
    """Render the report, prove byte-identical re-render, publish atomically.

    The proof is render -> sha256 -> re-render -> sha256 -> byte equality; a
    mismatch raises and nothing publishes (T-12-01). A failure on any path
    returns EXIT_INVALID without unlinking destinations — `publish_atomic`
    already restored any pre-existing artifact, and a failure before publish
    never touched the destinations (phase10.py shape). The render stage is
    not a verdict carrier: success is EXIT_OK.
    """
    if not args.results or len(args.results) != 2:
        invalid("the render stage requires --results <k21 results> "
                "<k31 results>")
    if not args.parity_doc or len(args.parity_doc) != 2:
        invalid("the render stage requires --parity-doc <k21 parity> "
                "<k31 parity>")
    if not args.verdict_doc:
        invalid("the render stage requires --verdict-doc <verdict document>")
    if not args.ladder_doc:
        invalid("the render stage requires --ladder-doc "
                "<11-LADDER-RESULTS.json>")
    if not args.proof_out:
        invalid("the render stage requires --proof-out <re-render proof "
                "path>")
    out_path = Path(args.out)
    proof_path = Path(args.proof_out)
    try:
        results_docs = [
            _validate_results_document(_load_json(path), label=str(path))
            for path in args.results]
        parity_docs = [
            _validate_parity_document(_load_json(path), label=str(path))
            for path in args.parity_doc]
        verdict_doc = _validate_verdict_document(
            _load_json(args.verdict_doc), label=str(args.verdict_doc))
        ladder_doc = _load_json(args.ladder_doc)
        docs = {"results": results_docs, "parity": parity_docs,
                "verdict": verdict_doc, "ladder": ladder_doc}
        text = render_report_text(docs)
        text_again = render_report_text(docs)
        if text != text_again:
            raise RuntimeError(
                "render: re-render is not byte-identical — the renderer is "
                "carrying nondeterminism (a clock read, iteration order, or "
                "an unstable environment read); refusing to publish a proof")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        digest_again = hashlib.sha256(
            text_again.encode("utf-8")).hexdigest()
        proof_doc = {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND_RENDER_PROOF,
            "phase": PHASE,
            "created": datetime.now(timezone.utc).isoformat(),
            "first_render_sha256": digest,
            "second_render_sha256": digest_again,
            "byte_identical": True,
            "renderer_commit": renderer_source_commit(),
            "inputs": [fingerprint(path) for path in
                       [*args.results, *args.parity_doc, args.verdict_doc,
                        args.ladder_doc]],
            "provenance": _measured_provenance(results_docs, "render"),
        }
        validate_provenance(proof_doc)
        publish_atomic([
            (out_path, text),
            (proof_path, json.dumps(proof_doc, indent=2) + "\n"),
        ])
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — invalid publish, never a verdict
        # `publish_atomic` already restored any pre-existing artifact; a
        # failure before publish never touched the destinations. Never unlink
        # here: that would destroy a previously published report/proof.
        print(f"phase11.py: {exc}", file=sys.stderr)
        return EXIT_INVALID
    print(f"{VERDICT_PREFIX} render byte_identical=true "
          f"report_sha256={digest}")
    return EXIT_OK


# --- CLI ---------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        description="Phase 12 full-scale merge-verdict controller: staged "
                    "revalidate -> parity -> timed -> verdict -> render over "
                    "the parity-validated prepared artifacts, with the "
                    "0/1/2 exit-code contract as the verdict carrier "
                    "(D-01; the timed stage function lands with plan "
                    "12-04's Task 2).")
    parser.add_argument("--stage", choices=STAGES, default="revalidate")
    parser.add_argument("--out", required=True,
                        help="results/decision document output path")
    parser.add_argument("--k", type=int, default=21,
                        help="k value for the parity/timed stages (21|31)")
    parser.add_argument("--round0", default=None,
                        help="timed stage: the round-0 revalidation evidence "
                             "document")
    parser.add_argument("--parity-doc", nargs="+", default=None,
                        help="render stage: the two parity evidence "
                             "documents (k=21 and k=31)")
    parser.add_argument("--results", nargs="+", default=None,
                        help="verdict stage: the two results documents; "
                             "render stage: the two results documents")
    parser.add_argument("--verdict-doc", default=None,
                        help="render stage: the verdict document")
    parser.add_argument("--ladder-doc", default=None,
                        help="render stage: 11-LADDER-RESULTS.json")
    parser.add_argument("--proof-out", default=None,
                        help="render stage: the re-render proof document "
                             "path")
    parser.add_argument("--scratch", default=str(DEFAULT_SCRATCH),
                        help="scratch directory on the data volume "
                             "(sort -T locality)")
    parser.add_argument("--rustkmer", default=DEFAULT_RUSTKMER,
                        help="path to the rustkmer RELEASE binary")
    parser.add_argument("--reps", type=int, default=REPS,
                        help="measured counterbalanced rounds (default 3, "
                             "D-02)")
    parser.add_argument("--cooldown-s", type=float, default=DEFAULT_COOLDOWN_S,
                        help="cooldown seconds between measured runs")
    parser.add_argument("--disk-floor-override", action="store_true",
                        help="print-and-continue under the disk floor "
                             "(deliberate runs only; the default blocks "
                             "with exit 3)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.stage in ("parity", "timed") and args.k not in PARITY_KS:
        parser.error(f"--k must be one of {list(PARITY_KS)} for the "
                     f"{args.stage} stage")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")

    if args.stage == "revalidate":
        return run_revalidate(args)
    if args.stage == "parity":
        return run_parity(args)
    if args.stage == "verdict":
        return run_verdict(args)
    if args.stage == "render":
        return run_render(args)
    # Dispatch stays TOTAL: a stage whose function has not landed yet is
    # exit 2 naming the missing stage — never silence.
    invalid(f"stage {args.stage!r} is not implemented yet (plan 12-04 "
            "Task 2); this build implements revalidate/parity/verdict/"
            "render")
    return EXIT_INVALID


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail loudly, no traceback noise
        # Infrastructure failures are INVALID (exit 2), never a measured NO
        # (exit 1): the verdict code is reserved for a recorded observation.
        print(f"phase11.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
