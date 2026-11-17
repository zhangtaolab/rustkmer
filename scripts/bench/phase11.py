#!/usr/bin/env python3
"""Phase-12 full-scale merge-verdict controller (``scripts/bench/phase11.py``).

D-01 locks the controller FILE name as ``phase11.py`` — the phase10.py
controller-name lineage is deliberate (do NOT rename to phase12.py) — while
the evidence documents it writes carry the phase-12 roadmap prefix to match
the ``12-*.json`` evidence filenames.

Stages — the order is pinned by construction (parity before timing; the
streaming deep-leg form is the ONLY full-scale route, WR-01):

  revalidate   round-0 gate: re-hash + re-stats the prepared artifacts,
               union-anchor equality, full disk budget (plan 12-04)
  parity       three-way parity gate per k; deep legs streamed (plan 12-04)
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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/phase11.py): insert the repo
    # root BEFORE importing so the harness package resolves to this checkout
    # in one shot (phase10.py's fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_COOLDOWN_S,
    DEFAULT_DISK_FLOOR_GB,
    DEFAULT_RUSTKMER,
    REPO_ROOT,
    SCHEMA_VERSION,
    BenchmarkConfig,
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


def assert_binary_identity():
    """Tripwire: the measured binaries must be the ladder's exact bytes.

    Compares the sha256 of the ACTUAL executable bytes (never the command
    string) against the 11-LADDER-RESULTS.json provenance constants. A
    rebuilt rustkmer or an upgraded jellyfish breaks predicted-vs-measured
    attribution — this raises naming both hashes; escalate, never rebuild.
    """
    rust_prov = binary_provenance(DEFAULT_RUSTKMER, "release")
    jf_prov = binary_provenance("jellyfish", JELLYFISH_BUILD_PROFILE)
    rust_sha = rust_prov["binary"]["sha256"]
    jf_sha = jf_prov["binary"]["sha256"]
    if rust_sha != RUSTKMER_BIN_SHA256 or jf_sha != JELLYFISH_BIN_SHA256:
        raise RuntimeError(
            "binary identity tripwire: rustkmer sha256 "
            f"{rust_sha} (expected {RUSTKMER_BIN_SHA256}) / jellyfish sha256 "
            f"{jf_sha} (expected {JELLYFISH_BIN_SHA256}) — a rebuilt or "
            "upgraded binary breaks predicted-vs-measured attribution "
            "(11-LADDER-RESULTS.json provenance); escalate, never rebuild")
    return {"rustkmer": rust_prov["binary"], "jellyfish": jf_prov["binary"]}


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
                    "(D-01; the revalidate/parity/timed stage functions "
                    "land with plan 12-04).")
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

    if args.stage == "verdict":
        return run_verdict(args)
    if args.stage == "render":
        return run_render(args)
    # Dispatch stays TOTAL: a stage whose function plan 12-04 has not added
    # yet is exit 2 naming the missing stage — never silence.
    invalid(f"stage {args.stage!r} is not implemented yet (plan 12-04); "
            "this skeleton implements the verdict and render stages")
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
