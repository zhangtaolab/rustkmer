#!/usr/bin/env python3
"""Phase 10 benchmark-verdict controller (BENCH-V2-02, plan 10-01).

One measured arm per tool over the COMPLETE read-1 set: the two split parts
are one input list, never two half-size arms. Four arms are recorded at each
k: `rk-t16`, `rk-t1` (CLI scaling evidence), `jf-t16` (the pinned reference)
and `py-t16` (the fresh-process `pyrustkmer` worker).

Methodology (locked by 10-CONTEXT.md):

  * parity before timing — counts are exact and nonzero before any median is
    trusted;
  * one discarded warmup per TOOL, then --reps counterbalanced rounds driven
    by output_stage.rotation_schedule, so every round visits every arm once
    with a rotated start;
  * every rep records the honest `cache_state` of its own purge attempt, its
    round index and its arm_order position;
  * memory is recorded as `max(rss, phys_footprint)` (`peak_bytes`) while the
    schema-required raw `peak_rss_bytes` is preserved;
  * the verdict is a pure comparison of recorded medians over arms whose
    recorded `threads == 16`; equality is match-or-beat (`<=`), there is no
    tolerance band, and the `t1` arm never enters a YES/NO computation;
  * the report is rendered mechanically from recorded JSONs — no measurement
    literal, no clock — so re-rendering is byte-identical.

Exit codes are a contract, shared with the rest of scripts/bench/:
  0 — valid result (a measured YES for the verdict stage).
  1 — a genuine measured NO (artifact kept; never used by the synthetic
      spine proof, which returns 0 for either verdict).
  2 — invalid/inapplicable (no artifact written).

Stages:
  synthetic        four arms over two synthetic parts (the plan-10-01 tracer;
                   mode is always "synthetic", never "full")
  slice-gate       pinned head-4M parity gate (plan 10-02)
  cli              full-scale CLI session k=21/k=31 (plan 10-03)
  python           full-scale Python session (plan 10-04)
  preflight-python project the Python peak from the MEASURED CLI distinct
                   count; PROCEED/BLOCKED (plan 10-04 dependency)
  render           mechanical report from recorded documents (plan 10-02)

Python 3.11+ stdlib only — no third-party imports.
"""

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/phase10.py): insert the repo
    # root BEFORE importing so the harness package resolves to this checkout
    # in one shot (output_stage.py's fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench import python_bench
from scripts.bench.bench import (
    DEFAULT_COOLDOWN_S,
    DEFAULT_DISK_FLOOR_GB,
    DEFAULT_HASH_SIZE,
    DEFAULT_RUSTKMER,
    REPO_ROOT,
    SCHEMA_VERSION,
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    check_disk_floor,
    default_decompressor,
    fingerprint,
    gate_parity_reference,
    gather_inputs,
    harness_source_commit,
    jellyfish_count_cmd,
    jellyfish_stats,
    measure,
    provision_slice,
    provision_synthetic,
    reduce_arm,
    run_parity,
    rustkmer_count_cmd,
    slice_kind_for,
    stats,
    validate_provenance,
    validate_schema,
)
from scripts.bench.output_stage import rotation_schedule

EXIT_OK = 0
EXIT_NO = 1
EXIT_INVALID = 2

# Matched-thread acceptance configuration (all cores on the dev host).
ACCEPTANCE_THREADS = 16

# The four arms, in the pinned report order. `ARM_ORDER` is the canonical
# sequence the report uses regardless of JSON order.
ARM_RK_T16 = "rk-t16"
ARM_RK_T1 = "rk-t1"
ARM_JF_T16 = "jf-t16"
ARM_PY_T16 = "py-t16"
ARM_ORDER = (ARM_RK_T16, ARM_RK_T1, ARM_JF_T16, ARM_PY_T16)
TOOL_WARMUP_ORDER = ("rustkmer", "jellyfish", "pyrustkmer")

# Memory model constants, each pinned by measured points (10-RESEARCH Pattern
# 3). Do not tune them to make a projection come out green.
MEMORY_BUDGET_BYTES = 110 * (1 << 30)   # ~18 GiB of the 128 GiB host for OS
PYTHON_BYTES_PER_DISTINCT = 86          # measured single-call coefficient
DEFAULT_PARTITIONS = 64
SLOT_BYTES = 16                         # Dense(hashbrown<u64,u32>) slot, 16 B
PAIR_BYTES = 32                         # (u128,u32) drain pair, 32 B
LOAD_FACTOR = 0.875                     # hashbrown default max load
MODEL_BASE_BYTES = 400_000_000          # fitted base (buffers + fixed costs)

# Fixed inputs / evidence locations for the full-scale stages (plan 10-02+).
DEFAULT_DATA_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")
PARITY_REFERENCE = (Path(__file__).resolve().parent / "baselines"
                    / "slice_parity.crr1936095.json")
PHASE_DIR = (Path(__file__).resolve().parent.parent.parent / ".planning"
             / "phases" / "10-benchmark-verdict")
PINNED_HEAD4M = {"distinct": 229694874, "total": 519271168}
PINNED_SLICE_READS = 4000000
PINNED_SOURCE_SHA256 = (
    "dae91042e42c1a0562a2bda66b7a3409665cddc87e702d99b922e44160c1b0de")
PARITY_HASH_SIZE = "2G"
REFERENCE_SHA256 = (
    "9826bd59c51e34be520c6fca008aea304fb69232f6887cc808b93c4f49ac8a96")
# PRE-RUN CLI projection basis: the research upper estimate for the union
# distinct count. This is a projection input, never a measurement — the
# document records `basis: "research-upper-estimate"`.
CLI_PREFLIGHT_DISTINCT = 1_200_000_000
SLICE_GATE_K_VALUES = (21, 31)
LIVE_PARITY_ONLY = "live-parity-only (no pinned k=31 slice reference)"
PINNED_REFERENCE_GATE = "pinned-reference"

# The five mandatory report literals asserted verbatim by this plan's tests
# and by the Plan 10-04 final gate. Keep them exact and case-sensitive.
REPORT_LITERALS = (
    "BENCH-V2-01",
    "partially satisfied",
    "Dev-host evidence only",
    "scaling evidence",
    "equality",
)

SYNTHETIC_READS = 200_000
DEFAULT_K = 21
PHASE = 10

# Report section ordering for same-k documents.
_SESSION_ORDER = {"cli": 0, "python": 1}


def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict."""
    print(f"phase10.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def file_sha256(path):
    """sha256 hex of one file, streamed in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- arm construction -------------------------------------------------------

def python_worker_argv(python, inputs, k, threads_text, stats_path):
    """List-form argv for one fresh-process pyrustkmer worker (never a shell).

    The Phase-10 worker receives every split part through repeatable
    `--inputs` flags so two `add_from_fastq` calls happen in ONE process —
    the both-parts seam for the Python surface.
    """
    argv = [str(python), str(Path(python_bench.__file__)), "--worker"]
    for path in inputs:
        argv += ["--inputs", str(path)]
    argv += ["--k", str(k), "--threads", str(threads_text),
             "--stats-out", str(stats_path)]
    return argv


def build_arm_specs(inputs, k, rustkmer, python, scratch, include):
    """Build one arm spec per requested arm over the full two-part input.

    Every CLI/jellyfish command derives from one BenchmarkConfig over the
    SAME two-part list (rustkmer gets both files through one `-i`; jellyfish
    gets one `gzcat p1 p2 | jellyfish` pipeline). The py arm carries its
    stats path and the interpreter's site-packages prefix, resolved by ONE
    interpreter_info call at spec-build time — run_rounds never needs an
    `info` argument.
    """
    input_paths = [Path(p) for p in inputs]
    if len(input_paths) != 2:
        raise ValueError(
            f"Phase-10 arms require exactly two split parts, got "
            f"{len(input_paths)} — both parts are ONE measured arm")
    requested = list(include)
    unknown = [name for name in requested if name not in ARM_ORDER]
    if unknown:
        raise ValueError(f"unknown arm name(s): {unknown!r}")
    names = [name for name in ARM_ORDER if name in requested]
    if not names:
        raise ValueError("build_arm_specs needs at least one arm")
    scratch = Path(scratch)
    site_prefix = None
    if ARM_PY_T16 in names:
        info = python_bench.interpreter_info(str(python))
        site_prefix = info["site_prefix"]
        if not isinstance(site_prefix, str) or not site_prefix.strip():
            raise ValueError(
                "the --python interpreter reported no site_prefix — the "
                "measured module cannot be proven to live in the measured "
                "interpreter's site-packages")
    specs = []
    for name in names:
        threads = 1 if name == ARM_RK_T1 else ACCEPTANCE_THREADS
        cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                              hash_size=DEFAULT_HASH_SIZE,
                              inputs=list(input_paths),
                              decompressor=default_decompressor())
        inputs_text = [str(p) for p in input_paths]
        if name in (ARM_RK_T16, ARM_RK_T1):
            out = scratch / f"phase10-{name}.rkdb"
            specs.append({
                "name": name,
                "tool": "rustkmer",
                "threads": threads,
                "inputs": inputs_text,
                "out": str(out),
                "cmd": rustkmer_count_cmd(cfg, out, rustkmer),
            })
        elif name == ARM_JF_T16:
            out = scratch / "phase10-jf-t16.jf"
            specs.append({
                "name": name,
                "tool": "jellyfish",
                "threads": threads,
                "inputs": inputs_text,
                "out": str(out),
                "cmd": jellyfish_count_cmd(cfg, out),
            })
        else:
            stats_path = scratch / "phase10-py-t16.stats.json"
            specs.append({
                "name": name,
                "tool": "pyrustkmer",
                "threads": threads,
                "inputs": inputs_text,
                "out": str(stats_path),
                "cmd": python_worker_argv(python, input_paths, k, threads,
                                          stats_path),
                "stats_path": str(stats_path),
                "site_prefix": site_prefix,
            })
    return specs


# --- measured rounds --------------------------------------------------------

def rep_peak_bytes(rep):
    """The honest peak: recorded peak_bytes, else max(rss, footprint-or-zero).

    Forward-compatible with the pre-extension parser: when the rep carries no
    `peak_bytes` yet, derive it from the recorded RSS (and footprint if the
    parser supplied it) rather than inventing a number.
    """
    if rep.get("peak_bytes") is not None:
        return rep["peak_bytes"]
    return max(rep["peak_rss_bytes"], rep.get("peak_footprint_bytes") or 0)


def run_rounds(specs, reps, cooldown_s, measure_fn=None, purge_fn=None,
               sleep_fn=None, on_rep=None):
    """Warmups + counterbalanced measured rounds; return {arm: [rep dicts]}.

    One discarded warmup per TOOL (the first spec of that tool) runs before
    round 0; the t1 arm deliberately gets no separate warmup because the
    rustkmer warmup covers the tool. Each measured rep records its honest
    cache_state, round and arm_order. For a pyrustkmer spec the stale stats
    file is deleted before the run, the fresh payload is validated through
    python_bench.validate_worker_stats with the spec's site_prefix, the
    payload's input list must equal the spec's two-part list IN ORDER, and
    the exact counts plus module identity are attached — a py run that
    leaves no stats file is invalid, never synthesized.

    The injectable seams default to the module-level primitives at CALL time
    (not at definition time), so a test can patch `phase10.measure` /
    `phase10.attempt_cache_purge` / `time.sleep` and still drive the real
    stage entry points.
    """
    measure_fn = measure if measure_fn is None else measure_fn
    purge_fn = attempt_cache_purge if purge_fn is None else purge_fn
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    if reps < 1:
        raise ValueError(f"reps must be >= 1, got {reps}")
    names = [spec["name"] for spec in specs]
    if not names:
        raise ValueError("run_rounds needs at least one arm spec")
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate arm names in specs: {names!r}")
    schedule = rotation_schedule(names, reps)
    by_name = {spec["name"]: spec for spec in specs}
    reps_by_arm = {name: [] for name in names}

    tool_order = []
    for spec in specs:
        if spec["tool"] not in tool_order:
            tool_order.append(spec["tool"])
    total_runs = len(tool_order) + reps * len(specs)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            sleep_fn(cooldown_s)

    def one_measured_run(spec):
        if spec["tool"] == "pyrustkmer":
            stats_path = Path(spec["stats_path"])
            if stats_path.exists():
                stats_path.unlink()
            rep = measure_fn(spec["cmd"])
            if not stats_path.is_file():
                raise ValueError(
                    f"py arm {spec['name']!r} left no stats file at "
                    f"{stats_path} — never synthesize counts")
            with open(stats_path, encoding="utf-8") as fh:
                payload = json.load(fh)
            counts = python_bench.validate_worker_stats(
                payload, spec["site_prefix"],
                expected_threads=spec["threads"])
            payload_inputs = [str(part) for part in payload.get("inputs") or []]
            spec_inputs = [str(part) for part in spec["inputs"]]
            if payload_inputs != spec_inputs:
                raise ValueError(
                    f"py arm {spec['name']!r} reported inputs "
                    f"{payload_inputs!r} but the arm measured {spec_inputs!r} "
                    f"— both parts must be counted once each, in argv order")
            rep.update(counts)
            rep["inputs"] = payload_inputs
            rep["module_path"] = payload["module_path"]
            rep["module_mtime"] = payload.get("module_mtime")
            rep["threads_resolved"] = payload["threads_resolved"]
            rep["python_version"] = payload.get("python_version")
            rep["module_sha256"] = fingerprint(
                payload["module_path"])["sha256"]
        else:
            rep = measure_fn(spec["cmd"])
        rep.setdefault("peak_footprint_bytes", None)
        rep["peak_bytes"] = rep_peak_bytes(rep)
        return rep

    # One discarded warmup per tool, before any measured round.
    warmup_tools = set()
    for spec in specs:
        if spec["tool"] in warmup_tools:
            continue
        warmup_tools.add(spec["tool"])
        one_measured_run(spec)
        cooldown_gap()

    for rnd, round_order in enumerate(schedule):
        for position, name in enumerate(round_order):
            spec = by_name[name]
            cache_state = purge_fn()
            rep = one_measured_run(spec)
            rep["cache_state"] = cache_state
            rep["round"] = rnd
            rep["arm_order"] = position
            reps_by_arm[name].append(rep)
            if on_rep is not None:
                on_rep(spec, rep)
            cooldown_gap()
    return reps_by_arm


def arm_medians(reps):
    """Nested medians block: medians plus CV, with the honest peak_bytes."""
    reduced = reduce_arm(reps)
    return {
        "wall_s": reduced["median_wall_s"],
        "peak_rss_bytes": reduced["median_peak_rss_bytes"],
        "peak_bytes": statistics.median([rep_peak_bytes(r) for r in reps]),
        "cv_wall_pct": reduced["cv_wall_pct"],
        "cv_warning": reduced["cv_warning"],
    }


def finalize_python_arm(name, reps, expected=None):
    """The py arm's strict end-of-session reduction.

    `check_rep_identity` is a HARD failure on any rep-count, module, or
    resolved-thread disagreement (never averaged away); the arm then carries
    the nested medians plus the exact counts and the per-rep measured
    module/input identity. `db_sha256` is null because the Python arm writes
    no database — the measured artifact is the worker payload.
    """
    exact = python_bench.check_rep_identity(reps, expected=expected)
    first = reps[0]
    return {
        "name": name,
        "tool": "pyrustkmer",
        "threads": first["threads_resolved"],
        "inputs": list(first.get("inputs") or []),
        "reps": reps,
        "medians": arm_medians(reps),
        "unique_kmers": exact["unique_kmers"],
        "total_kmers": exact["total_kmers"],
        "db_sha256": None,
    }


def _single_arm(doc, name, label):
    """The one arm named `name` in `doc`, or ValueError on absence/ambiguity."""
    matches = [arm for arm in doc.get("arms", [])
               if isinstance(arm, dict) and arm.get("name") == name]
    if len(matches) != 1:
        observed = [arm.get("name") for arm in doc.get("arms", [])
                    if isinstance(arm, dict)]
        raise ValueError(
            f"{label}: expected exactly one arm {name!r}, found "
            f"{len(matches)} in {observed}")
    return matches[0]


def _exact_counts(arm, label):
    """The arm's positive exact (unique, total) pair, or ValueError."""
    unique = arm.get("unique_kmers")
    total = arm.get("total_kmers")
    for key, value in (("unique_kmers", unique), ("total_kmers", total)):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(
                f"{label}: {key}={value!r} must be a positive integer — a "
                f"zero count is a silent input failure, never a measurement")
    return unique, total


def assert_session_parity(doc, *arm_names):
    """Every named arm must report the SAME positive exact counts.

    A mismatch means the arms did not count the same bytes (or the worker
    dropped a part) — a hard failure, never averaged. Returns the parity
    block describing the agreed counts.
    """
    names = list(arm_names)
    if len(names) < 2:
        raise ValueError("assert_session_parity needs at least two arms")
    observed = {}
    for name in names:
        arm = _single_arm(doc, name, "session parity")
        observed[name] = _exact_counts(arm, f"session parity arm {name!r}")
    reference_name = names[0]
    reference = observed[reference_name]
    for name in names[1:]:
        if observed[name] != reference:
            raise ValueError(
                f"session parity mismatch: {reference_name} counts "
                f"{reference} vs {name} counts {observed[name]} — the arms "
                f"counted different bytes on the same measured input")
    return {"arms": names, "unique_kmers": reference[0],
            "total_kmers": reference[1], "equal": True}


def assert_cross_session_jellyfish(cli_doc, python_doc):
    """The two sessions' jellyfish arms must agree on counts AND input bytes.

    The jellyfish reference is re-measured in each session; identical counts
    prove both sessions counted the same bytes. A difference is a hard
    failure because a venv/run-chain change would silently invalidate the
    cross-session comparison.
    """
    cli_arm = _single_arm(cli_doc, ARM_JF_T16, "cross-session cli")
    python_arm = _single_arm(python_doc, ARM_JF_T16, "cross-session python")
    cli_counts = _exact_counts(cli_arm, "cross-session cli jellyfish")
    python_counts = _exact_counts(python_arm, "cross-session python jellyfish")
    if cli_counts != python_counts:
        raise ValueError(
            f"cross-session jellyfish counts differ: cli {cli_counts} vs "
            f"python {python_counts} — the two sessions counted different "
            f"bytes")
    cli_fp = cli_doc.get("input_fingerprint")
    python_fp = python_doc.get("input_fingerprint")
    if cli_fp != python_fp:
        raise ValueError(
            "cross-session input fingerprint differs between the CLI and "
            f"Python sessions: {cli_fp!r} vs {python_fp!r}")
    return {"cli": cli_counts, "python": python_counts,
            "input_fingerprint": cli_fp, "equal": True}


def build_arms(specs, reps_by_arm, rustkmer):
    """Reduce measured reps to arm records with exact nonzero counts.

    Counts come from the producer of the bytes: `rustkmer stats` for the CLI
    arms, `jellyfish stats` for the reference arm, and the validated worker
    payloads for the Python arm (through the strict `finalize_python_arm`).
    A zero count is invalid, never a measurement.
    """
    arms = []
    for spec in specs:
        reps = reps_by_arm[spec["name"]]
        if not reps:
            raise ValueError(f"arm {spec['name']!r} has zero successful reps")
        if spec["tool"] == "pyrustkmer":
            arm = finalize_python_arm(spec["name"], reps)
            if not arm["inputs"]:
                arm["inputs"] = list(spec["inputs"])
            arms.append(arm)
            continue
        if spec["tool"] == "jellyfish":
            jf = jellyfish_stats(spec["out"])
            exact = {"unique_kmers": jf["distinct"], "total_kmers": jf["total"]}
        else:
            st = stats(spec["out"], rustkmer)
            exact = {"unique_kmers": st["unique_kmers"],
                     "total_kmers": st["total_kmers"]}
        if exact["unique_kmers"] <= 0 or exact["total_kmers"] <= 0:
            raise ValueError(
                f"arm {spec['name']!r}: zero counts {exact} after the reps — "
                f"silent input failure, never a measurement")
        db_sha256 = fingerprint(spec["out"])["sha256"]
        arms.append({
            "name": spec["name"],
            "tool": spec["tool"],
            "threads": spec["threads"],
            "inputs": list(spec["inputs"]),
            "reps": reps,
            "medians": arm_medians(reps),
            "unique_kmers": exact["unique_kmers"],
            "total_kmers": exact["total_kmers"],
            "db_sha256": db_sha256,
        })
    return arms


def validate_rep_memory(rep):
    """Every measured rep must carry honest, positive memory fields."""
    for field in ("wall_s", "peak_rss_bytes", "peak_bytes"):
        value = rep.get(field)
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or value <= 0):
            raise ValueError(
                f"rep field {field}={value!r} must be a positive number")
    if rep["peak_bytes"] < rep["peak_rss_bytes"]:
        raise ValueError(
            f"rep peak_bytes={rep['peak_bytes']!r} is below the recorded "
            f"peak_rss_bytes={rep['peak_rss_bytes']!r} — max() rule violated")


# --- verdict ----------------------------------------------------------------

def surface_result(tool_median, jellyfish_median):
    """Match-or-beat rule: `tool <= jellyfish` is YES; equality is a match.

    There is no tolerance band and no re-roll — a NO is a recorded outcome.
    """
    return "YES" if float(tool_median) <= float(jellyfish_median) else "NO"


def _acceptance_arm(doc, name, label, k):
    """The single arm named `name` measured at ACCEPTANCE_THREADS.

    Missing, ambiguous, zero-rep or non-positive-median arms are ValueError
    (exit 2 upstream): a verdict may never be fabricated from absent data.
    The t1 arm cannot match this filter by construction.
    """
    matches = [arm for arm in doc.get("arms", [])
               if isinstance(arm, dict) and arm.get("name") == name
               and arm.get("threads") == ACCEPTANCE_THREADS]
    if len(matches) != 1:
        observed = [(arm.get("name"), arm.get("threads"))
                    for arm in doc.get("arms", []) if isinstance(arm, dict)]
        raise ValueError(
            f"k={k}: required arm {name!r} at threads="
            f"{ACCEPTANCE_THREADS} is missing or ambiguous in the {label} "
            f"document (found {len(matches)}); observed {observed}")
    arm = matches[0]
    reps = arm.get("reps")
    if not isinstance(reps, list) or not reps:
        raise ValueError(f"k={k}: arm {name!r} in the {label} document has "
                         f"zero reps — no median may exist")
    medians = arm.get("medians")
    wall = medians.get("wall_s") if isinstance(medians, dict) else None
    if (not isinstance(wall, (int, float)) or isinstance(wall, bool)
            or wall <= 0):
        raise ValueError(
            f"k={k}: arm {name!r} in the {label} document has a non-positive "
            f"median wall {wall!r}")
    return float(wall)


def verdict_block(k, cli_doc, python_doc):
    """The k's two surface results, four recorded medians, and the rule.

    The CLI document supplies the rustkmer and jellyfish medians; the Python
    document supplies the pyrustkmer and jellyfish medians (the jellyfish arm
    is re-measured in each session, so both are recorded). Only arms whose
    recorded `threads == 16` are consulted; the `t1` arm is reported under
    `scaling` and never enters a YES/NO computation.
    """
    for label, doc in (("cli", cli_doc), ("python", python_doc)):
        params = doc.get("params") if isinstance(doc, dict) else None
        doc_k = params.get("k") if isinstance(params, dict) else None
        if doc_k is not None and doc_k != k:
            raise ValueError(
                f"verdict_block k={k} paired with a {label} document for "
                f"k={doc_k} — mismatched measurements")

    rustkmer_wall = _acceptance_arm(cli_doc, ARM_RK_T16, "cli", k)
    jellyfish_cli = _acceptance_arm(cli_doc, ARM_JF_T16, "cli", k)
    python_wall = _acceptance_arm(python_doc, ARM_PY_T16, "python", k)
    jellyfish_python = _acceptance_arm(python_doc, ARM_JF_T16, "python", k)

    rustkmer_result = surface_result(rustkmer_wall, jellyfish_cli)
    python_result = surface_result(python_wall, jellyfish_python)

    scaling = None
    for arm in cli_doc.get("arms", []):
        if (isinstance(arm, dict) and arm.get("name") == ARM_RK_T1
                and arm.get("threads") == 1):
            medians = arm.get("medians")
            wall = medians.get("wall_s") if isinstance(medians, dict) else None
            if (isinstance(wall, (int, float)) and not isinstance(wall, bool)
                    and wall > 0):
                scaling = {"arm": ARM_RK_T1, "threads": 1,
                           "wall_s": float(wall)}
            break

    return {
        "k": k,
        "result": ("YES" if rustkmer_result == "YES"
                   and python_result == "YES" else "NO"),
        "rustkmer_result": rustkmer_result,
        "python_result": python_result,
        "rustkmer_wall_s": rustkmer_wall,
        "python_wall_s": python_wall,
        "jellyfish_cli_wall_s": jellyfish_cli,
        "jellyfish_python_wall_s": jellyfish_python,
        "scaling": scaling,
        "rule": ("acceptance compares t16 medians only; a surface is YES when "
                 "its median wall <= the jellyfish median wall in the same "
                 "session (equality is match-or-beat; no tolerance band); "
                 "rk-t1 is scaling evidence and never enters the verdict"),
    }


def verdict_line(verdict):
    """The one machine-greppable stdout line; repr() round-trips the floats."""
    return (
        f"PHASE10 VERDICT k={verdict['k']} result={verdict['result']} "
        f"rustkmer={verdict['rustkmer_result']} "
        f"rustkmer_wall_s={verdict['rustkmer_wall_s']!r} "
        f"python={verdict['python_result']} "
        f"python_wall_s={verdict['python_wall_s']!r} "
        f"jellyfish_cli_wall_s={verdict['jellyfish_cli_wall_s']!r} "
        f"jellyfish_python_wall_s={verdict['jellyfish_python_wall_s']!r}")


# --- document assembly / writing -------------------------------------------

def assemble_doc(mode, session, k, params, inputs, arms, scratch, provenance,
                 extra=None):
    """Assemble the schema-v1 provenance-bearing Phase-10 document.

    Pure apart from `created` and the input fingerprints. `extra` adds the
    schedule block (and any stage-specific extension) without being able to
    silently overwrite a pinned key.
    """
    doc = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "phase": PHASE,
        "session": session,
        "params": params,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "created": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": [fingerprint(p) for p in inputs],
        "arms": arms,
        "scratch": str(scratch),
        "provenance": provenance,
    }
    if extra:
        overlap = sorted(set(extra) & set(doc))
        if overlap:
            raise ValueError(
                f"assemble_doc extra keys collide with pinned keys: {overlap}")
        doc.update(extra)
    return doc


def write_doc(doc, out_path):
    """Validate schema AND provenance, then write — invalid docs never land."""
    validate_schema(doc)
    validate_provenance(doc)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    return out


def python_session_provenance(args, module_path):
    """Python-session provenance: the interpreter + module, plus the CLI.

    The Python artifact must name BOTH measured surfaces: the native module
    that produced the Python number (sha256 of the actual `.so` bytes) and
    the CLI binary used as the session's parity reference.
    """
    info = python_bench.interpreter_info(str(args.python))
    prov = python_bench.build_provenance(args, info, module_path)
    prov["cli_binary"] = binary_provenance(args.rustkmer, "release")
    return prov


def write_evidence_doc(doc, out_path):
    """Validate provenance, then write an evidence (non-results) document.

    Used by the slice-gate record: its shape is a `kind` document, not the
    results schema, so `validate_schema` does not apply — but no artifact
    may reach disk without complete provenance (T-10-06).
    """
    validate_provenance(doc)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    return out


def build_session_provenance(args, arms):
    """CLI binary provenance, extended with the Python module when measured."""
    prov = binary_provenance(args.rustkmer, "release")
    py_arm = next((arm for arm in arms if arm["tool"] == "pyrustkmer"), None)
    if py_arm is not None:
        module_path = py_arm["reps"][0]["module_path"]
        info = python_bench.interpreter_info(str(args.python))
        prov["module"] = fingerprint(module_path)
        prov["python_executable"] = info["executable"]
        prov["python_version"] = info["version"]
        prov["maturin_version"] = python_bench.maturin_version(args.python)
    return prov


# --- mechanical report ------------------------------------------------------

def _doc_k(doc):
    params = doc.get("params")
    k = params.get("k") if isinstance(params, dict) else None
    if not isinstance(k, int) or isinstance(k, bool):
        raise ValueError(f"document has no integer params.k: {k!r}")
    return k


def render_report(docs, out_path):
    """Render the Phase-10 Markdown report from recorded documents.

    Mechanical by construction: every number comes from the documents, the
    only environment read is `harness_source_commit()`, and no clock is
    consulted — re-rendering the same documents is byte-identical, so a
    hand-edited number is detectable.
    """
    if not docs:
        raise ValueError("render_report needs at least one document")
    validated = []
    for doc in docs:
        validate_schema(doc)
        validate_provenance(doc)
        if doc.get("mode") not in ("synthetic", "full"):
            raise ValueError(
                f"render_report supports mode=synthetic/full, got "
                f"mode={doc.get('mode')!r}")
        validated.append(doc)
    validated.sort(key=lambda d: (
        _doc_k(d), _SESSION_ORDER.get(d.get("session"), 99),
        str(d.get("session"))))

    lines = [
        "# rustkmer vs Jellyfish2 — Phase 10 benchmark report",
        "",
        "*Mechanically rendered from the recorded results JSONs by "
        "`python3 scripts/bench/phase10.py --stage render`. Every number "
        "below is read from those JSONs — the renderer carries no measurement "
        "literals and consults no clock — so re-rendering reproduces this "
        "file byte-for-byte and a hand-edited number is detectable "
        "(BENCH-V2-02/T-10-01).*",
        "",
        "## Dataset provenance",
        "",
    ]
    seen_fingerprints = set()
    for doc in validated:
        for fp in doc.get("input_fingerprint", []):
            sha = fp.get("sha256")
            if sha in seen_fingerprints:
                continue
            seen_fingerprints.add(sha)
            lines.append(
                f"- `{fp.get('path')}` — size_bytes={fp.get('size_bytes')} "
                f"sha256=`{sha}`")
        lines.append(
            f"- mode={doc.get('mode')} session={doc.get('session')} "
            f"k={_doc_k(doc)} created={doc.get('created')}")
    lines.append("")

    table_header = [
        "| arm | tool | threads | median wall (s) | median peak bytes "
        "| reps | per-rep wall (s) | per-rep peak bytes | per-rep cache_state |",
        "|-----|------|---------|-----------------|-------------------"
        "|------|-------------------|--------------------|---------------------|",
    ]
    for doc in validated:
        lines += ["", f"## k={_doc_k(doc)} — mode={doc.get('mode')} "
                      f"session={doc.get('session')}", ""]
        lines += table_header
        by_name = {arm.get("name"): arm for arm in doc.get("arms", [])
                   if isinstance(arm, dict)}
        ordered = [name for name in ARM_ORDER if name in by_name]
        ordered += [name for name in by_name if name not in ARM_ORDER]
        for name in ordered:
            arm = by_name[name]
            medians = arm.get("medians")
            if not isinstance(medians, dict):
                raise ValueError(f"arm {name!r} has no medians block")
            reps = arm.get("reps")
            if not isinstance(reps, list):
                raise ValueError(f"arm {name!r} has no reps list")
            walls = " / ".join(repr(r.get("wall_s")) for r in reps)
            peaks = " / ".join(repr(rep_peak_bytes(r)) for r in reps)
            states = " / ".join(str(r.get("cache_state")) for r in reps)
            lines.append(
                f"| {name} | {arm.get('tool')} | {arm.get('threads')} "
                f"| {medians.get('wall_s')!r} | {medians.get('peak_bytes')!r} "
                f"| {len(reps)} | {walls} | {peaks} | {states} |")
        # Trim the leading blank added above when this is the first document.
        while lines and lines[-1] == "":
            lines.pop()
    lines.append("")

    lines += ["## Verdict (from recorded medians)", ""]
    for k in sorted({_doc_k(doc) for doc in validated}):
        docs_k = [doc for doc in validated if _doc_k(doc) == k]
        cli_doc = next((d for d in docs_k if d.get("session") == "cli"), None)
        python_doc = next(
            (d for d in docs_k if d.get("session") == "python"), None)
        if cli_doc is None or python_doc is None:
            if len(docs_k) != 1:
                raise ValueError(
                    f"k={k}: render needs a cli and a python session document "
                    f"(or exactly one combined document); got "
                    f"{[d.get('session') for d in docs_k]}")
            cli_doc = python_doc = docs_k[0]
        block = verdict_block(k, cli_doc, python_doc)
        lines.append(
            f"- k={k}: **{block['result']}** — rustkmer "
            f"{block['rustkmer_result']} ({block['rustkmer_wall_s']!r} s vs "
            f"jellyfish {block['jellyfish_cli_wall_s']!r} s), python "
            f"{block['python_result']} ({block['python_wall_s']!r} s vs "
            f"jellyfish {block['jellyfish_python_wall_s']!r} s)")
        lines.append(f"  - rule: {block['rule']}")
    lines += [
        "",
        "---",
        "",
        "*Generated file — do not edit by hand. Regenerate with "
        "`python3 scripts/bench/phase10.py --stage render --out <results.json> "
        "--report-out <this file>`; harness source commit "
        f"`{harness_source_commit()}`.*",
        "",
    ]

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="\n") as fh:
        fh.write("\n".join(lines))
    return out


# --- memory projection (plan 10-03/10-04 preflight) -------------------------

def cli_peak_bytes(distinct, partitions=DEFAULT_PARTITIONS):
    """Project the CLI both-parts peak from a measured distinct count.

    Capacity is the next power of two at or above D/(P*0.875); each slot is
    16 B (Dense hashbrown<u64,u32> entry — 8 B key + 4 B count, padded), the
    pair buffer is 32 B per distinct k-mer ((u128,u32) drain pair), plus the
    fitted base. Validated against three measured points (measured RSS):
    229,694,874 -> 12.04 GB (model ~12.05), 256,606,202 -> 17.52 GB (model
    ~17.20), 537,770,176 -> 35.71 GB (model ~34.79); all within 5%.
    """
    if (not isinstance(distinct, int) or isinstance(distinct, bool)
            or distinct <= 0):
        raise ValueError(f"distinct must be a positive integer, got "
                         f"{distinct!r}")
    if partitions < 1:
        raise ValueError(f"partitions must be >= 1, got {partitions}")
    needed = distinct / partitions / LOAD_FACTOR
    capacity = 1
    while capacity < needed:
        capacity <<= 1
    tables = SLOT_BYTES * capacity * partitions
    pairs = PAIR_BYTES * distinct
    return tables + pairs + MODEL_BASE_BYTES


def python_projection_bytes(d_union, bytes_per_distinct=PYTHON_BYTES_PER_DISTINCT):
    """Conservative Python two-call upper bound: 86 B per union distinct.

    The measured single-call coefficient is 86 B/distinct. For the two-call
    (part-by-part) full arm the calibrated split is ~33 B/entry on each
    part's engine tables plus ~53.5 B/entry on the union DashMap. Because
    each part's distinct count is at most the union distinct count,
    `33*D_part + 53.5*D_union <= 33*D_union + 53.5*D_union = 86.5*D_union`,
    and 86 B is the measured value quoted as the conservative bound.
    """
    if (not isinstance(d_union, int) or isinstance(d_union, bool)
            or d_union <= 0):
        raise ValueError(f"d_union must be a positive integer, got {d_union!r}")
    return bytes_per_distinct * d_union


def memory_gate(projected_bytes, budget_bytes=MEMORY_BUDGET_BYTES):
    """Pure gate: (ok, detail); equality passes, one byte over is blocked."""
    ok = projected_bytes <= budget_bytes
    headroom = budget_bytes - projected_bytes
    if ok:
        detail = (f"projected {projected_bytes} bytes <= budget "
                  f"{budget_bytes} bytes ({headroom} bytes headroom)")
    else:
        detail = (f"projected {projected_bytes} bytes > budget "
                  f"{budget_bytes} bytes ({-headroom} bytes deficit)")
    return ok, detail


def preflight_record(k, distinct, distinct_source, distinct_source_sha256,
                     budget_bytes=MEMORY_BUDGET_BYTES):
    """The serializable Python preflight record for one k.

    `projected_bytes` is computed INTERNALLY from the measured distinct count
    and `decision` is derived from the gate — no caller-supplied projection
    and no caller-supplied decision exists, so a blocked projection cannot be
    recorded as PROCEED.
    """
    projected = python_projection_bytes(distinct)
    ok, detail = memory_gate(projected, budget_bytes)
    return {
        "k": k,
        "distinct_source": str(distinct_source),
        "distinct_source_sha256": distinct_source_sha256,
        "distinct": distinct,
        "projected_bytes": projected,
        "budget_bytes": budget_bytes,
        "decision": "PROCEED" if ok else "BLOCKED",
        "headroom_bytes": budget_bytes - projected,
        "model": "python-86B-per-distinct-conservative-two-call-upper-bound",
        "detail": detail,
    }


# --- synthetic stage (the plan-10-01 tracer) --------------------------------

def run_synthetic(args):
    """Four arms over two synthetic parts: the end-to-end spine proof."""
    if args.report_out is None:
        invalid("the synthetic stage requires --report-out")
    out_path = Path(args.out)
    scratch = (Path(args.scratch) if args.scratch
               else out_path.parent / "scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    inputs = provision_synthetic(SYNTHETIC_READS, scratch)
    specs = build_arm_specs(inputs, args.k, args.rustkmer, args.python,
                            scratch, ARM_ORDER)
    reps_by_arm = run_rounds(specs, args.reps, args.cooldown_s)
    for reps in reps_by_arm.values():
        for rep in reps:
            validate_rep_memory(rep)
    arms = build_arms(specs, reps_by_arm, args.rustkmer)
    params = {
        "k": args.k,
        "canonical": True,
        "threads": ACCEPTANCE_THREADS,
        "reps": args.reps,
        "cooldown_s": args.cooldown_s,
        "hash_size": DEFAULT_HASH_SIZE,
        "arm_order": list(ARM_ORDER),
    }
    provenance = build_session_provenance(args, arms)
    doc = assemble_doc(
        mode="synthetic", session="synthetic", k=args.k, params=params,
        inputs=inputs, arms=arms, scratch=scratch, provenance=provenance,
        extra={"schedule": {
            "policy": "round-robin-rotation",
            "warmup_order": list(TOOL_WARMUP_ORDER),
            "rounds": rotation_schedule([s["name"] for s in specs],
                                        args.reps),
        }})
    verdict = verdict_block(args.k, doc, doc)
    write_doc(doc, out_path)
    render_report([doc], args.report_out)
    for arm in arms:
        medians = arm["medians"]
        print(f"{arm['name']}: median wall {medians['wall_s']!r}s "
              f"peak_bytes {medians['peak_bytes']!r} "
              f"reps {len(arm['reps'])}")
    print(verdict_line(verdict))
    return EXIT_OK


# --- python preflight stage (plan 10-04 dependency) -------------------------

def load_cli_document(path):
    """Load, validate and return one full-mode CLI results document."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate_schema(doc)
    validate_provenance(doc)
    if doc.get("mode") != "full":
        raise ValueError(
            f"preflight source {path} is mode={doc.get('mode')!r}, not 'full' "
            f"— only a full CLI measurement may anchor the projection")
    return doc


def preflight_records(paths, budget_bytes=MEMORY_BUDGET_BYTES):
    """Build one preflight_record per consumed CLI document."""
    if len(paths) != 2:
        raise ValueError(
            f"preflight-python consumes exactly the two CLI documents "
            f"(k=21 and k=31), got {len(paths)}")
    records = []
    seen_k = set()
    for path in paths:
        doc = load_cli_document(path)
        k = _doc_k(doc)
        if k in seen_k:
            raise ValueError(f"duplicate k={k} among the CLI documents")
        seen_k.add(k)
        arm = next((a for a in doc.get("arms", [])
                    if isinstance(a, dict) and a.get("name") == ARM_RK_T16
                    and a.get("threads") == ACCEPTANCE_THREADS), None)
        if arm is None:
            raise ValueError(
                f"{path}: no {ARM_RK_T16} arm at threads={ACCEPTANCE_THREADS} "
                f"— the Python projection needs the measured distinct count")
        distinct = arm.get("unique_kmers")
        if (not isinstance(distinct, int) or isinstance(distinct, bool)
                or distinct <= 0):
            raise ValueError(
                f"{path}: {ARM_RK_T16}.unique_kmers={distinct!r} is not a "
                f"positive integer")
        records.append(preflight_record(
            k, distinct, str(path), file_sha256(path), budget_bytes))
    return records


def run_preflight_python(args):
    """Project the Python peak from the measured CLI distinct count."""
    if not args.cli_docs:
        invalid("the preflight-python stage requires --cli-docs <two paths>")
    records = preflight_records(args.cli_docs)
    overall = ("PROCEED" if all(r["decision"] == "PROCEED" for r in records)
               else "BLOCKED")
    doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": "phase10-python-preflight",
        "phase": PHASE,
        "created": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "overall": overall,
        "provenance": binary_provenance(args.rustkmer, "release"),
    }
    validate_provenance(doc)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    for record in records:
        print(f"k={record['k']}: projected {record['projected_bytes']} bytes "
              f"budget {record['budget_bytes']} -> {record['decision']}")
    print(f"Python preflight overall: {overall} (record written to {out})")
    return EXIT_OK if overall == "PROCEED" else EXIT_INVALID


# --- full-scale sessions (plans 10-03/10-04) --------------------------------

def _stage_paths(args):
    out_path = Path(args.out)
    scratch = Path(args.scratch) if args.scratch else out_path.parent / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return out_path, scratch


def _resolve_two_parts(data_dir):
    """The complete read-1 set: exactly the two split parts, sorted."""
    inputs = [Path(p) for p in gather_inputs(str(data_dir))]
    if len(inputs) != 2:
        raise ValueError(
            f"the full-scale stages require exactly two split parts under "
            f"{data_dir}, found {len(inputs)} — both parts are ONE measured "
            f"input list, never two half-size arms")
    return inputs


def _stage_params(k, reps, cooldown_s):
    """The pinned params sub-shape Plans 10-03/10-04 assert by key."""
    return {
        "k": k,
        "canonical": True,
        "threads": ACCEPTANCE_THREADS,
        "reps": reps,
        "cooldown_s": cooldown_s,
        "hash_size": DEFAULT_HASH_SIZE,
        "arm_order": list(ARM_ORDER),
    }


def _stage_schedule(specs, reps):
    return {
        "policy": "round-robin-rotation",
        "warmup_order": list(TOOL_WARMUP_ORDER),
        "rounds": rotation_schedule([spec["name"] for spec in specs], reps),
    }


def _cli_preflight():
    """The PRE-RUN CLI projection at the research upper estimate.

    `basis` is recorded as `research-upper-estimate` so a projection can
    never be mistaken for a measurement; the decision is derived through
    `memory_gate`, never caller-supplied.
    """
    projected = cli_peak_bytes(CLI_PREFLIGHT_DISTINCT)
    ok, detail = memory_gate(projected)
    return {
        "basis": "research-upper-estimate",
        "distinct_assumed": CLI_PREFLIGHT_DISTINCT,
        "projected_bytes": projected,
        "budget_bytes": MEMORY_BUDGET_BYTES,
        "decision": "PROCEED" if ok else "BLOCKED",
        "model": "cli-16B-slot-32B-pair-64-partitions",
        "detail": detail,
    }


def run_cli_session(args):
    """Full-scale CLI session: `rk-t16`, `rk-t1` and `jf-t16` over both parts.

    The disk floor and the PRE-RUN projection are checked BEFORE any measured
    run; the post-arm exact counts are read once per arm; the two rustkmer
    databases must be byte-identical; the scratch databases are deleted after
    their sha256 is recorded. Any failure exits 2 with no artifact.
    """
    out_path, scratch = _stage_paths(args)
    try:
        inputs = _resolve_two_parts(args.data_dir)
        check_disk_floor(scratch, DEFAULT_DISK_FLOOR_GB)
        preflight = _cli_preflight()
        if preflight["decision"] != "PROCEED":
            raise ValueError(
                f"pre-run CLI projection blocked: {preflight['detail']}")
        specs = build_arm_specs(
            inputs, args.k, args.rustkmer, args.python, scratch,
            [ARM_RK_T16, ARM_RK_T1, ARM_JF_T16])
        reps_by_arm = run_rounds(specs, args.reps, args.cooldown_s)
        for reps in reps_by_arm.values():
            for rep in reps:
                validate_rep_memory(rep)
        arms = build_arms(specs, reps_by_arm, args.rustkmer)
        rk_shas = {arm["db_sha256"] for arm in arms
                   if arm["tool"] == "rustkmer"}
        if len(rk_shas) != 1 or None in rk_shas:
            raise ValueError(
                f"rustkmer arms recorded unequal database sha256 values "
                f"{sorted(str(sha) for sha in rk_shas)} — t16 and t1 must "
                f"produce identical .rkdb bytes")
        doc = assemble_doc(
            mode="full", session="cli", k=args.k,
            params=_stage_params(args.k, args.reps, args.cooldown_s),
            inputs=inputs, arms=arms, scratch=scratch,
            provenance=build_session_provenance(args, arms),
            extra={"preflight": preflight,
                   "schedule": _stage_schedule(specs, args.reps)})
        assert_session_parity(doc, ARM_RK_T16, ARM_RK_T1, ARM_JF_T16)
        for spec in specs:
            out = Path(spec["out"])
            if out.exists():
                out.unlink()
        write_doc(doc, out_path)
    except Exception as exc:  # noqa: BLE001 — invalid session, never a verdict
        print(f"phase10.py: {exc}", file=sys.stderr)
        return EXIT_INVALID
    for arm in arms:
        medians = arm["medians"]
        print(f"{arm['name']}: median wall {medians['wall_s']!r}s "
              f"peak_bytes {medians['peak_bytes']!r} reps {len(arm['reps'])}")
    return EXIT_OK


def _load_slice_gate_doc(path):
    """Read the slice-gate artifact and assert it is still the pinned gate."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("kind") != "phase10-slice-gate":
        raise ValueError(
            f"pre-gate {path} is kind={doc.get('kind')!r}, not "
            f"'phase10-slice-gate'")
    matches = [gate for gate in doc.get("gates", [])
               if isinstance(gate, dict) and gate.get("k") == 21]
    if len(matches) != 1:
        raise ValueError(
            f"pre-gate {path}: expected exactly one k=21 gate, found "
            f"{len(matches)}")
    gate = matches[0]
    for key in ("distinct", "total"):
        if gate.get(key) != PINNED_HEAD4M[key]:
            raise ValueError(
                f"pre-gate {path}: k=21 gate {key}={gate.get(key)!r} != "
                f"pinned {PINNED_HEAD4M[key]!r} — this is not the pinned "
                f"head-4M reference gate")
    reference = gate.get("parity_reference")
    if (not isinstance(reference, dict)
            or reference.get("sha256") != REFERENCE_SHA256):
        raise ValueError(
            f"pre-gate {path}: k=21 gate does not carry the pinned reference "
            f"sha256 {REFERENCE_SHA256}")
    return doc


def _load_python_preflight(path, k):
    """Read the preflight record for `k` and re-derive its decision."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("kind") != "phase10-python-preflight":
        raise ValueError(
            f"preflight {path} is kind={doc.get('kind')!r}, not "
            f"'phase10-python-preflight'")
    matches = [record for record in doc.get("records", [])
               if isinstance(record, dict) and record.get("k") == k]
    if len(matches) != 1:
        raise ValueError(
            f"preflight {path}: expected exactly one record for k={k}, "
            f"found {len(matches)}")
    record = matches[0]
    distinct = record.get("distinct")
    projected = record.get("projected_bytes")
    budget = record.get("budget_bytes")
    if (not isinstance(distinct, int) or isinstance(distinct, bool)
            or distinct <= 0):
        raise ValueError(f"preflight {path}: distinct={distinct!r} invalid")
    if (not isinstance(budget, int) or isinstance(budget, bool)
            or budget <= 0):
        raise ValueError(f"preflight {path}: budget_bytes={budget!r} invalid")
    model_projection = python_projection_bytes(distinct)
    if projected != model_projection:
        raise ValueError(
            f"preflight {path}: projected_bytes={projected!r} != the model's "
            f"{model_projection} — a tampered projection cannot gate the "
            f"Python arm")
    ok, detail = memory_gate(projected, budget)
    want = "PROCEED" if ok else "BLOCKED"
    if record.get("decision") != want:
        raise ValueError(
            f"preflight {path}: decision={record.get('decision')!r} but the "
            f"model derives {want!r} ({detail})")
    if want != "PROCEED":
        raise ValueError(
            f"preflight {path}: Python projection BLOCKED ({detail}) — the "
            f"Python arm must not run; this is a user stop, never a silent "
            f"skip")
    for key in ("distinct_source", "distinct_source_sha256"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"preflight {path}: {key} missing")
    return record


def run_python_session(args):
    """Full-scale Python session: `jf-t16` and `py-t16` over both parts.

    Consumes committed evidence only after pinning its sha256: the slice-gate
    artifact must still carry the pinned k=21 counts, and the preflight
    record's projection/decision is re-derived. Every rep is a fresh
    interpreter validated by the `py-t16` branch of `run_rounds`; the session
    is parity-checked internally and against the committed CLI document. The
    scratch `.jf` is deleted after its sha256 is recorded.
    """
    if not args.pre_gate:
        invalid("the python stage requires --pre-gate <10-slice-gate.json>")
    if not args.preflight:
        invalid("the python stage requires --preflight "
                "<10-python-preflight.json>")
    if not args.cli_doc:
        invalid("the python stage requires --cli-doc <the matching CLI "
                "document>")
    out_path, scratch = _stage_paths(args)
    try:
        inputs = _resolve_two_parts(args.data_dir)
        check_disk_floor(scratch, DEFAULT_DISK_FLOOR_GB)
        _load_slice_gate_doc(args.pre_gate)
        preflight = _load_python_preflight(args.preflight, args.k)
        cli_doc = load_cli_document(args.cli_doc)
        if _doc_k(cli_doc) != args.k:
            raise ValueError(
                f"--cli-doc {args.cli_doc} is k={_doc_k(cli_doc)} but the "
                f"Python session measures k={args.k}")
        specs = build_arm_specs(
            inputs, args.k, args.rustkmer, args.python, scratch,
            [ARM_JF_T16, ARM_PY_T16])
        reps_by_arm = run_rounds(specs, args.reps, args.cooldown_s)
        for reps in reps_by_arm.values():
            for rep in reps:
                validate_rep_memory(rep)
        arms = build_arms(specs, reps_by_arm, args.rustkmer)
        py_arm = next(arm for arm in arms if arm["name"] == ARM_PY_T16)
        doc = assemble_doc(
            mode="full", session="python", k=args.k,
            params=_stage_params(args.k, args.reps, args.cooldown_s),
            inputs=inputs, arms=arms, scratch=scratch,
            provenance=python_session_provenance(
                args, py_arm["reps"][0]["module_path"]),
            extra={
                "pre_gate": {
                    "path": str(args.pre_gate),
                    "sha256": file_sha256(args.pre_gate),
                },
                "memory_preflight": {
                    "decision": preflight["decision"],
                    "distinct": preflight["distinct"],
                    "projected_bytes": preflight["projected_bytes"],
                    "budget_bytes": preflight["budget_bytes"],
                    "headroom_bytes": (preflight["budget_bytes"]
                                       - preflight["projected_bytes"]),
                    "observed_peak_bytes": py_arm["medians"]["peak_bytes"],
                    "source": preflight["distinct_source"],
                    "source_sha256": preflight["distinct_source_sha256"],
                },
                "cross_session": {
                    "cli_doc": str(args.cli_doc),
                    "cli_doc_sha256": file_sha256(args.cli_doc),
                },
                "schedule": _stage_schedule(specs, args.reps),
            })
        assert_session_parity(doc, ARM_JF_T16, ARM_PY_T16)
        assert_cross_session_jellyfish(cli_doc, doc)
        for spec in specs:
            if spec["tool"] == "jellyfish":
                out = Path(spec["out"])
                if out.exists():
                    out.unlink()
        write_doc(doc, out_path)
    except Exception as exc:  # noqa: BLE001 — invalid session, never a verdict
        print(f"phase10.py: {exc}", file=sys.stderr)
        return EXIT_INVALID
    for arm in arms:
        medians = arm["medians"]
        print(f"{arm['name']}: median wall {medians['wall_s']!r}s "
              f"peak_bytes {medians['peak_bytes']!r} reps {len(arm['reps'])}")
    return EXIT_OK


# --- CLI --------------------------------------------------------------------

STAGES = ("synthetic", "slice-gate", "cli", "python", "render",
          "preflight-python")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Phase 10 benchmark-verdict controller: four arms over "
                    "the complete two-part read-1 set, counterbalanced reps, "
                    "honest max(rss, footprint) accounting, and a verdict "
                    "computed from recorded t16 medians (exit 0/1/2).")
    parser.add_argument("--stage", choices=STAGES, default="synthetic")
    parser.add_argument("--out", required=True,
                        help="results/decision document output path")
    parser.add_argument("--report-out", default=None,
                        help="rendered Markdown report path")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="CRR1936095 r1 split directory (full stages)")
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--rustkmer", default=DEFAULT_RUSTKMER,
                        help="path to the rustkmer RELEASE binary")
    parser.add_argument("--python", default=str(python_bench.DEFAULT_PYTHON),
                        help="interpreter with the freshly built extension")
    parser.add_argument("--reps", type=int, default=3,
                        help="measured counterbalanced rounds (default 3)")
    parser.add_argument("--cooldown-s", type=float, default=DEFAULT_COOLDOWN_S,
                        help="cooldown seconds between measured runs")
    parser.add_argument("--scratch", default=None,
                        help="scratch directory (default: beside --out)")
    parser.add_argument("--cli-docs", nargs="+", default=None,
                        help="preflight-python: the two full-mode CLI "
                             "documents (k=21 and k=31)")
    parser.add_argument("--cli-doc", default=None,
                        help="python stage: the matching full-mode CLI "
                             "document (same k)")
    parser.add_argument("--pre-gate", default=None,
                        help="python stage: the slice-gate artifact "
                             "(10-slice-gate.json)")
    parser.add_argument("--preflight", default=None,
                        help="python stage: the Python preflight artifact "
                             "(10-python-preflight.json)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.k <= 64:
        parser.error("--k must be in 1..64")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")

    if args.stage == "synthetic":
        return run_synthetic(args)
    if args.stage == "preflight-python":
        return run_preflight_python(args)
    if args.stage == "cli":
        return run_cli_session(args)
    if args.stage == "python":
        return run_python_session(args)
    invalid(f"stage {args.stage!r} not implemented in plan 10-02")
    return EXIT_INVALID


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail loudly, no traceback noise
        # Infrastructure failures are INVALID (exit 2), never a measured NO
        # (exit 1): the verdict code is reserved for a recorded observation.
        print(f"phase10.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
