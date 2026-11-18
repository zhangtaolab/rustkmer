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
import math
import os
import platform
import statistics
import subprocess
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
    BYTES_PER_GIB,
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    check_disk_floor,
    default_decompressor,
    fingerprint,
    gate_parity_reference,
    gather_inputs,
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
# The canonical full four-arm tool sequence. Documents record the order
# actually warmed up (tool_warmup_order(specs)), never this constant: a
# session that measures a subset of tools must not claim the missing tools.
TOOL_WARMUP_ORDER = ("rustkmer", "jellyfish", "pyrustkmer")

# Memory model constants, each pinned by measured points (10-RESEARCH Pattern
# 3). Do not tune them to make a projection come out green.
MEMORY_BUDGET_BYTES = 110 * (1 << 30)   # ~18 GiB of the 128 GiB host for OS
PYTHON_BYTES_PER_DISTINCT = 86          # measured single-call coefficient
# Two-call (part-by-part) model: ~33 B/entry on each part's engine tables plus
# ~53.5 B/entry on the union DashMap. Since D_part <= D_union, the peak is at
# most 86.5 B per union distinct; the projection ceils that true upper bound.
PYTHON_TWO_CALL_BYTES_PER_DISTINCT = 86.5
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

# The two sessions each re-measure the SAME jellyfish command over the same
# two-part input, but timing is session-local (cache/thermal/run-chain state).
# When the two reference medians differ by more than this documented factor,
# the report states the divergence and declines any cross-session timing
# claim. The verdict rule itself is unchanged: each surface is compared only
# with the jellyfish median recorded in ITS OWN session.
CROSS_SESSION_JELLYFISH_MAX_RATIO = 2.0

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
                "rustkmer": str(rustkmer),
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


def tool_warmup_order(specs):
    """The unique tool sequence run_rounds actually warms up, in spec order.

    The document records THIS list, never the canonical four-arm constant: a
    CLI session must not claim a `pyrustkmer` warmup (and a Python session
    must not claim a `rustkmer` one) that never ran.
    """
    order = []
    for spec in specs:
        if spec["tool"] not in order:
            order.append(spec["tool"])
    return order


def read_rep_counts(spec):
    """Read one measured rep's exact counts from that rep's OWN output.

    Every rep overwrites the same output path, so this runs immediately after
    each measured run (never after the next run has overwritten it). A zero or
    invalid count is ValueError: a rep that silently counted nothing must
    invalidate the arm BEFORE any median is computed, not disappear behind
    the next rep's positive artifact.
    """
    if spec["tool"] == "jellyfish":
        raw = jellyfish_stats(spec["out"])
        unique = raw.get("distinct")
        total = raw.get("total")
    elif spec["tool"] == "rustkmer":
        raw = stats(spec["out"], spec["rustkmer"])
        unique = raw.get("unique_kmers")
        total = raw.get("total_kmers")
    else:
        raise ValueError(
            f"arm {spec['name']!r}: per-rep count verification applies only "
            f"to the CLI/jellyfish arms, not tool {spec['tool']!r}")
    for key, value in (("unique_kmers", unique), ("total_kmers", total)):
        if (not isinstance(value, int) or isinstance(value, bool)
                or value <= 0):
            raise ValueError(
                f"arm {spec['name']!r}: per-rep {key}={value!r} must be a "
                f"positive integer — a zero count after a measured run is a "
                f"silent input failure, never a measurement")
    return {"unique_kmers": unique, "total_kmers": total}


def run_rounds(specs, reps, cooldown_s, measure_fn=None, purge_fn=None,
               sleep_fn=None, on_rep=None, counts_fn=None):
    """Warmups + counterbalanced measured rounds; return {arm: [rep dicts]}.

    One discarded warmup per TOOL (the first spec of that tool) runs before
    round 0; the t1 arm deliberately gets no separate warmup because the
    rustkmer warmup covers the tool. Each measured rep records its honest
    cache_state, round and arm_order. For a pyrustkmer spec the stale stats
    file is deleted before the run, the fresh payload is validated through
    python_bench.validate_worker_stats with the spec's site_prefix, the
    payload's input list must equal the spec's two-part list IN ORDER, and
    the exact counts plus module identity are attached — a py run that
    leaves no stats file is invalid, never synthesized. For a CLI/jellyfish
    spec `counts_fn` reads that rep's OWN output immediately after the run
    (the next rep overwrites the path), so a silently empty rep invalidates
    the arm instead of entering the medians (WR-06).

    The injectable seams default to the module-level primitives at CALL time
    (not at definition time), so a test can patch `phase10.measure` /
    `phase10.attempt_cache_purge` / `time.sleep` and still drive the real
    stage entry points.
    """
    measure_fn = measure if measure_fn is None else measure_fn
    purge_fn = attempt_cache_purge if purge_fn is None else purge_fn
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    counts_fn = read_rep_counts if counts_fn is None else counts_fn
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

    tool_order = tool_warmup_order(specs)
    total_runs = len(tool_order) + reps * len(specs)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            sleep_fn(cooldown_s)

    def one_measured_run(spec, verify_counts=True):
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
            if verify_counts:
                rep.update(counts_fn(spec))
        rep.setdefault("peak_footprint_bytes", None)
        rep["peak_bytes"] = rep_peak_bytes(rep)
        return rep

    # One discarded warmup per tool, before any measured round.
    warmup_tools = set()
    for spec in specs:
        if spec["tool"] in warmup_tools:
            continue
        warmup_tools.add(spec["tool"])
        one_measured_run(spec, verify_counts=False)
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
    prove both sessions counted the same bytes. The documents must also BE
    the sessions they claim: a python-session document passed as the CLI side
    would silently compare a session with itself (WR-12).
    """
    if cli_doc.get("session") != "cli":
        raise ValueError(
            f"cross-session: the CLI-side document is session="
            f"{cli_doc.get('session')!r}, not 'cli' — a python-session "
            f"document can never stand in for the CLI session")
    if python_doc.get("session") != "python":
        raise ValueError(
            f"cross-session: the Python-side document is session="
            f"{python_doc.get('session')!r}, not 'python'")
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
    For the CLI/jellyfish arms every measured rep recorded its OWN counts
    after its run; those must agree with each other and with the final
    artifact, and a zero count is invalid — never a measurement, and never
    hidden behind the next rep's positive output (WR-06).
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
        per_rep = {(rep.get("unique_kmers"), rep.get("total_kmers"))
                   for rep in reps}
        if len(per_rep) != 1 or None in per_rep:
            raise ValueError(
                f"arm {spec['name']!r}: per-rep exact counts disagree "
                f"({sorted(per_rep, key=str)}) — a rep that counted nothing "
                f"or counted different bytes is never averaged into a median")
        recorded_counts = per_rep.pop()
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
        if (exact["unique_kmers"], exact["total_kmers"]) != recorded_counts:
            raise ValueError(
                f"arm {spec['name']!r}: final output counts {exact} differ "
                f"from the last measured rep's counts {recorded_counts} — "
                f"the artifact was replaced after its rep was measured")
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
    """Every measured rep must carry honest, positive, FINITE memory fields.

    `value <= 0` alone is not enough: `NaN` and `+inf` both compare False
    against zero, and Python's `json.load` accepts the non-standard `NaN` /
    `Infinity` literals from a committed document. A non-finite measurement
    is invalid (exit 2), never a number that can enter a median.
    """
    for field in ("wall_s", "peak_rss_bytes", "peak_bytes"):
        value = rep.get(field)
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value) or value <= 0):
            raise ValueError(
                f"rep field {field}={value!r} must be a positive finite number")
    footprint = rep.get("peak_footprint_bytes")
    if footprint is not None and (
            not isinstance(footprint, (int, float))
            or isinstance(footprint, bool)
            or not math.isfinite(footprint) or footprint < 0):
        raise ValueError(
            f"rep field peak_footprint_bytes={footprint!r} must be a "
            f"non-negative finite number")
    if rep["peak_bytes"] < rep["peak_rss_bytes"]:
        raise ValueError(
            f"rep peak_bytes={rep['peak_bytes']!r} is below the recorded "
            f"peak_rss_bytes={rep['peak_rss_bytes']!r} — max() rule violated")


# --- verdict ----------------------------------------------------------------

def surface_result(tool_median, jellyfish_median):
    """Match-or-beat rule: `tool <= jellyfish` is YES; equality is a match.

    There is no tolerance band and no re-roll — a NO is a recorded outcome.
    Both inputs must be finite numbers: `Infinity <= Infinity` and comparisons
    involving `NaN` must never decide a verdict.
    """
    for label, value in (("tool", tool_median),
                         ("jellyfish", jellyfish_median)):
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value)):
            raise ValueError(
                f"surface_result: {label} median {value!r} must be a finite "
                f"number")
    return "YES" if float(tool_median) <= float(jellyfish_median) else "NO"


def _finite_positive(value, label):
    """A positive finite number, or ValueError naming `label`."""
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or value <= 0):
        raise ValueError(f"{label}={value!r} must be a positive finite number")
    return float(value)


def validate_arm_medians(arm, label):
    """Recompute every recorded median from the raw reps; require agreement.

    The verdict must never trust a recorded `medians` block that the document's
    own raw reps contradict: a stale, partially regenerated, or hand-edited
    median would otherwise drive a YES/NO while the evidence says otherwise.
    `medians.wall_s`, `medians.peak_rss_bytes` and `medians.peak_bytes` are
    each recomputed with the same reducer that produced them
    (`statistics.median`, with `rep_peak_bytes` for the honest peak) and must
    match exactly. Returns the validated medians dict.
    """
    name = arm.get("name")
    medians = arm.get("medians")
    if not isinstance(medians, dict):
        raise ValueError(f"{label}: arm {name!r} has no medians block")
    reps = arm.get("reps")
    if not isinstance(reps, list) or not reps:
        raise ValueError(
            f"{label}: arm {name!r} has zero reps — no median may exist")
    walls = []
    rss = []
    peaks = []
    for index, rep in enumerate(reps):
        if not isinstance(rep, dict):
            raise ValueError(
                f"{label}: arm {name!r} rep[{index}] is not an object")
        walls.append(_finite_positive(
            rep.get("wall_s"), f"{label}: arm {name!r} rep[{index}] wall_s"))
        rss.append(_finite_positive(
            rep.get("peak_rss_bytes"),
            f"{label}: arm {name!r} rep[{index}] peak_rss_bytes"))
        peaks.append(_finite_positive(
            rep_peak_bytes(rep),
            f"{label}: arm {name!r} rep[{index}] peak_bytes"))
    recorded = {
        key: _finite_positive(medians.get(key),
                              f"{label}: arm {name!r} medians.{key}")
        for key in ("wall_s", "peak_rss_bytes", "peak_bytes")
    }
    recomputed = {
        "wall_s": statistics.median(walls),
        "peak_rss_bytes": statistics.median(rss),
        "peak_bytes": statistics.median(peaks),
    }
    for key in ("wall_s", "peak_rss_bytes", "peak_bytes"):
        if recorded[key] != recomputed[key]:
            raise ValueError(
                f"{label}: arm {name!r} recorded medians.{key}="
                f"{recorded[key]!r} but its raw reps recompute to "
                f"{recomputed[key]!r} — a median the reps contradict can "
                f"never drive a verdict")
    return medians


def _acceptance_arm(doc, name, label, k):
    """The single arm named `name` measured at ACCEPTANCE_THREADS.

    Missing, ambiguous, zero-rep or non-positive-median arms are ValueError
    (exit 2 upstream): a verdict may never be fabricated from absent data.
    The recorded medians must also be reproducible from the raw reps. The t1
    arm cannot match this filter by construction.
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
    medians = validate_arm_medians(matches[0],
                                   f"k={k} {label} document")
    return float(medians["wall_s"])


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
            medians = validate_arm_medians(arm, f"k={k} cli scaling arm")
            scaling = {"arm": ARM_RK_T1, "threads": 1,
                       "wall_s": float(medians["wall_s"])}
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


def _validate_fingerprint(fp, label):
    """One well-formed input fingerprint: path, size, and 64-char sha256."""
    if not isinstance(fp, dict):
        raise ValueError(f"{label}: input fingerprint must be a dict")
    path = fp.get("path")
    size = fp.get("size_bytes")
    sha = fp.get("sha256")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{label}: fingerprint path must be a non-empty string")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError(f"{label}: fingerprint size_bytes={size!r} invalid")
    if not isinstance(sha, str) or len(sha) != 64:
        raise ValueError(f"{label}: fingerprint sha256={sha!r} invalid")
    return {"path": path, "size_bytes": size, "sha256": sha}


def _validate_warmup_order(doc):
    """The recorded warmup order names exactly the tools the document ran.

    The pre-fix harness wrote a constant three-tool list into every session,
    so a CLI session claimed a `pyrustkmer` warmup it never performed and a
    Python session claimed a `rustkmer` one. Warmups are discarded runs and
    carry no measured value, but a document that claims a tool it never
    measured misdescribes the session — the render stage must refuse it
    (WR-01). Returns the document unchanged.
    """
    schedule = doc.get("schedule")
    if not isinstance(schedule, dict) or "warmup_order" not in schedule:
        return doc
    order = schedule.get("warmup_order")
    if (not isinstance(order, list)
            or not all(isinstance(tool, str) and tool for tool in order)):
        raise ValueError(
            f"render: schedule.warmup_order={order!r} must be a list of "
            f"non-empty tool names")
    if len(set(order)) != len(order):
        raise ValueError(
            f"render: schedule.warmup_order={order!r} names a tool more "
            f"than once")
    tools = {arm.get("tool") for arm in doc.get("arms", [])
             if isinstance(arm, dict) and isinstance(arm.get("tool"), str)}
    unknown = [tool for tool in order if tool not in tools]
    if unknown:
        raise ValueError(
            f"render: schedule.warmup_order names tool(s) {unknown!r} that "
            f"the document never measured (arms use {sorted(tools)!r}) — a "
            f"warmup order can only describe tools that actually ran")
    missing = sorted(tool for tool in tools if tool not in order)
    if missing:
        raise ValueError(
            f"render: schedule.warmup_order={order!r} omits measured "
            f"tool(s) {missing!r} — every measured tool is warmed once")
    return doc


def _validate_render_document(doc):
    """Validate one results document and return it unchanged."""
    if not isinstance(doc, dict):
        raise ValueError("render: every document must be a JSON object")
    validate_schema(doc)
    validate_provenance(doc)
    kind = doc.get("kind")
    if kind is not None:
        raise ValueError(
            f"render: unsupported document kind {kind!r} — only results "
            f"documents are rendered")
    if doc.get("mode") not in ("synthetic", "full"):
        raise ValueError(
            f"render: supports mode=synthetic/full, got "
            f"mode={doc.get('mode')!r}")
    _validate_warmup_order(doc)
    return doc


def _render_groups(docs, allow_synthetic):
    """Group validated documents per k and session; raise on missing pairs."""
    groups = {}
    for doc in docs:
        k = _doc_k(doc)
        session = doc.get("session")
        if not isinstance(session, str) or not session:
            raise ValueError(f"render: k={k} document has no session")
        groups.setdefault(k, {}).setdefault(session, []).append(doc)
    pairs = {}
    for k in sorted(groups):
        sessions = groups[k]
        if "synthetic" in sessions:
            if not allow_synthetic:
                raise ValueError(
                    f"render: k={k} is a synthetic document — the full "
                    f"render stage needs committed cli/python documents")
            if len(sessions) != 1 or len(sessions["synthetic"]) != 1:
                raise ValueError(
                    f"render: k={k}: a synthetic document must be the only "
                    f"document for its k")
            pairs[k] = (sessions["synthetic"][0], sessions["synthetic"][0])
            continue
        unknown = sorted(set(sessions) - {"cli", "python"})
        if unknown:
            raise ValueError(
                f"render: k={k}: unsupported session(s) {unknown!r}")
        for session in ("cli", "python"):
            if len(sessions.get(session, [])) != 1:
                raise ValueError(
                    f"render: k={k}: need exactly one {session}-session "
                    f"document, found {len(sessions.get(session, []))} — a "
                    f"missing document is never rendered as an empty table")
        pairs[k] = (sessions["cli"][0], sessions["python"][0])
    if not pairs:
        raise ValueError("render: no documents to render")
    if not allow_synthetic and set(pairs) != set(SLICE_GATE_K_VALUES):
        raise ValueError(
            f"render: the full render requires exactly the pinned k values "
            f"{SLICE_GATE_K_VALUES} with one cli + one python document each, "
            f"got k={sorted(pairs)} — a subset of the pinned k values can "
            f"never publish an overall verdict")
    return pairs


_REPORT_ARM_HEADER = (
    "| arm | threads | per-rep wall (s) | median wall (s) "
    "| median peak (GiB) | distinct | total | notes |",
    "|-----|---------|------------------|-----------------|"
    "------------------|----------|-------|-------|",
)


def _report_arm_row(arm):
    """One table row: raw rep walls, recorded median, peak GiB, exact counts."""
    name = arm.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("render: every arm needs a non-empty name")
    medians = arm.get("medians")
    if not isinstance(medians, dict):
        raise ValueError(f"render: arm {name!r} has no medians block")
    reps = arm.get("reps")
    if not isinstance(reps, list) or not reps:
        raise ValueError(
            f"render: arm {name!r} has zero reps — no median may exist")
    medians = validate_arm_medians(arm, "render")
    wall = medians["wall_s"]
    peak = medians["peak_bytes"]
    unique, total = _exact_counts(arm, f"render arm {name!r}")
    walls = " / ".join(repr(rep.get("wall_s")) for rep in reps)
    warn = " `[cv_warning]`" if medians.get("cv_warning") else ""
    return (f"| {name} | {arm.get('threads')} | {walls} | {wall!r} "
            f"| {peak / BYTES_PER_GIB:.2f} | {unique:,} | {total:,} "
            f"|{warn} |")


def _ordered_arms(doc):
    """The document's arms in the pinned canonical order, never JSON order."""
    by_name = {}
    for arm in doc.get("arms", []):
        if not isinstance(arm, dict):
            raise ValueError("render: every arm must be an object")
        name = arm.get("name")
        if name not in ARM_ORDER:
            raise ValueError(
                f"render: unsupported arm {name!r} — the pinned order is "
                f"{ARM_ORDER}")
        if name in by_name:
            raise ValueError(f"render: duplicate arm {name!r}")
        by_name[name] = arm
    session = doc.get("session")
    required = {
        "cli": (ARM_RK_T16, ARM_RK_T1, ARM_JF_T16),
        "python": (ARM_JF_T16, ARM_PY_T16),
    }.get(session)
    if required is not None:
        missing = [name for name in required if name not in by_name]
        if missing:
            raise ValueError(
                f"render: the {session}-session document is missing arm(s) "
                f"{missing} — a missing arm is never rendered as a row")
    return [by_name[name] for name in ARM_ORDER if name in by_name]


def _cache_census(docs):
    """Count each distinct cache_state value across every rep of every doc."""
    counts = {}
    for doc in docs:
        for arm in doc.get("arms", []):
            for rep in arm.get("reps", []):
                state = str(rep.get("cache_state", "absent"))
                counts[state] = counts.get(state, 0) + 1
    return counts


def _dataset_lines(docs):
    """Both split parts, each path, size, and sha256 — from the documents."""
    by_path = {}
    for doc in docs:
        for raw in doc.get("input_fingerprint") or []:
            fp = _validate_fingerprint(
                raw, f"render k={_doc_k(doc)} {doc.get('session')}")
            previous = by_path.get(fp["path"])
            if previous is not None and previous["sha256"] != fp["sha256"]:
                raise ValueError(
                    f"render: dataset fingerprint mismatch for {fp['path']!r} "
                    f"— {previous['sha256']} vs {fp['sha256']}")
            by_path[fp["path"]] = fp
    if not by_path:
        raise ValueError("render: the documents carry no input fingerprints")
    lines = ["## Dataset provenance", ""]
    for path in sorted(by_path):
        fp = by_path[path]
        lines.append(
            f"- `{path}` — size_bytes={fp['size_bytes']:,} "
            f"sha256=`{fp['sha256']}`")
    lines += [
        "",
        "- Both split parts of the CRR1936095 read-1 set form ONE measured "
        "input per arm; no arm measures a single part.",
        "- The fingerprints above are read from the committed result "
        "documents, not re-read at render time.",
        "",
    ]
    return lines


def _table_lines(doc, session_label):
    """One session's arm table, plus the t1 scaling-evidence line."""
    lines = [f"### {session_label} session", ""]
    lines += list(_REPORT_ARM_HEADER)
    for arm in _ordered_arms(doc):
        lines.append(_report_arm_row(arm))
    by_name = {arm["name"]: arm for arm in doc.get("arms", [])}
    t1 = by_name.get(ARM_RK_T1)
    if t1 is not None:
        medians = t1.get("medians") if isinstance(t1.get("medians"),
                                                   dict) else {}
        lines.append(
            f"Scaling evidence (excluded from the verdict): `{ARM_RK_T1}` at "
            f"{t1.get('threads')} thread(s), median "
            f"{medians.get('wall_s')!r} s.")
    lines.append("")
    return lines


def _verdict_lines(pairs, docs):
    """The per-k verdict from recorded medians plus every mandatory statement."""
    lines = ["## Verdict", ""]
    overall = "YES"
    for k in sorted(pairs):
        cli_doc, python_doc = pairs[k]
        block = verdict_block(k, cli_doc, python_doc)
        if block["result"] != "YES":
            overall = "NO"
        label = ("primary acceptance question" if k == 21
                 else ("matched-hash re-verification" if k == 31
                       else "secondary comparison"))
        lines.append(
            f"- k={k} ({label}): **{block['result']}** — rustkmer "
            f"{block['rustkmer_result']} (median {block['rustkmer_wall_s']!r} "
            f"s vs jellyfish {block['jellyfish_cli_wall_s']!r} s), python "
            f"{block['python_result']} (median {block['python_wall_s']!r} s "
            f"vs jellyfish {block['jellyfish_python_wall_s']!r} s).")
        cli_jf = block["jellyfish_cli_wall_s"]
        python_jf = block["jellyfish_python_wall_s"]
        ratio = max(cli_jf, python_jf) / min(cli_jf, python_jf)
        if ratio > CROSS_SESSION_JELLYFISH_MAX_RATIO:
            caveat = (
                f" The identical `jf-t16` command counted the same bytes in "
                f"both sessions, so each surface is judged only against its "
                f"own session's jellyfish median; no cross-session timing "
                f"claim is made.")
        else:
            caveat = (
                f" Both sessions' reference medians are within the "
                f"documented {CROSS_SESSION_JELLYFISH_MAX_RATIO:.1f}x "
                f"comparability factor.")
        lines.append(
            f"- k={k} cross-session jellyfish reference: CLI session median "
            f"{cli_jf!r} s vs Python session median {python_jf!r} s "
            f"(ratio {ratio:.2f}x).{caveat}")
    lines += [
        f"- Overall: **{overall}** — k=21 is the primary acceptance "
        f"question; k=31 re-verifies the v1.0 matched-hash comparison.",
        "",
        "- Rule: the comparison is `rustkmer_median <= jellyfish_median` per "
        "surface in the SAME session; equality counts as match-or-beat, with "
        "no tolerance band and no re-roll.",
        "- Only arms recorded at `threads == 16` enter the verdict.",
        "- The t1 arm is scaling evidence only and never enters a YES/NO "
        "computation.",
        "- A NO is a recorded outcome, not a failure to explain away; the "
        "phase never re-runs until a result turns green.",
        "",
        "- BENCH-V2-01 (KMC3 comparison) is descoped: by user decision on "
        "2026-11-13 the KMC3 comparison was removed from this phase's scope. "
        "No KMC3 binary was downloaded, installed, or executed, and its "
        "absence from this report is intentional.",
        "- the cold-cache criterion is only partially satisfied: no sudo "
        "purge was run on this host, so no rep claims a cold cache. Per-rep "
        "cache_state census: "
        + ", ".join(f"{state} x{count}" for state, count
                    in sorted(_cache_census(docs).items()))
        + ".",
        "- Dev-host evidence only. No CI-class baseline was regenerated, "
        "written, or modified by this phase, and these numbers must never be "
        "copied into a CI baseline slot.",
        "",
    ]
    return lines


def _parity_lines(pairs, docs):
    """One explicit parity statement per k from the recorded exact counts.

    The statement claims every arm counted the SAME two-part input, so each
    arm's recorded `inputs` must equal its document's input fingerprint paths
    (WR-10): an arm measured over a different file list can never support a
    parity claim.
    """
    lines = ["## Parity evidence", ""]
    for k in sorted(pairs):
        entries = []
        for doc in docs:
            if _doc_k(doc) != k:
                continue
            fingerprint_paths = [
                fp.get("path") for fp in doc.get("input_fingerprint") or []
                if isinstance(fp, dict)]
            for arm in _ordered_arms(doc):
                arm_inputs = [str(path) for path in arm.get("inputs") or []]
                if arm_inputs != fingerprint_paths:
                    raise ValueError(
                        f"render: k={k}: arm {arm.get('name')!r} in the "
                        f"{doc.get('session')}-session document measured "
                        f"{arm_inputs!r} but the document fingerprints "
                        f"{fingerprint_paths!r} — no parity claim may be "
                        f"rendered for arms that measured different inputs")
                unique, total = _exact_counts(
                    arm, f"parity {arm.get('name')!r}")
                entries.append((arm.get("name"), doc.get("session"),
                                unique, total))
        distincts = {entry[2] for entry in entries}
        totals = {entry[3] for entry in entries}
        if len(distincts) != 1 or len(totals) != 1:
            raise ValueError(
                f"render: k={k}: recorded exact counts differ across arms "
                f"({sorted(distincts)} distinct, {sorted(totals)} total) — "
                f"no parity claim may be rendered")
        distinct = entries[0][2]
        total = entries[0][3]
        arms_text = ", ".join(f"{name} ({session})"
                              for name, session, _, _ in entries)
        lines.append(
            f"- k={k}: distinct={distinct:,} total={total:,} — EQUAL across "
            f"{arms_text} on the same two-part input.")
    lines.append("")
    return lines


def _shared_params(docs):
    """The params block all documents must agree on (reps/cooldown/hash_size)."""
    reference = docs[0].get("params")
    if not isinstance(reference, dict):
        raise ValueError("render: the first document carries no params block")
    for key in ("reps", "cooldown_s", "hash_size"):
        for doc in docs[1:]:
            params = doc.get("params") or {}
            if params.get(key) != reference.get(key):
                raise ValueError(
                    f"render: documents disagree on params.{key}: "
                    f"{reference.get(key)!r} vs {params.get(key)!r}")
    return reference


def _session_schedules(docs):
    """The (session, schedule) pairs the methodology section must render.

    The schedule is SESSION-LOCAL: the CLI session warms `rustkmer` and
    rotates three arms; the Python session warms `jellyfish` and rotates two.
    Reading `docs[0]`'s schedule report-wide would attribute the CLI warmup
    and rotation to a session that never ran either (WR-05). Every document
    of one session must record the same schedule; a disagreement raises
    rather than silently picking one. Sessions are ordered CLI first, then
    Python, then any other name, so the output does not depend on `--docs`
    order.
    """
    grouped = {}
    for doc in docs:
        session = doc.get("session")
        if not isinstance(session, str) or not session:
            raise ValueError(
                "render: a document carries no session for the schedule")
        grouped.setdefault(session, []).append(doc)
    schedules = []
    for session in sorted(
            grouped, key=lambda name: (_SESSION_ORDER.get(name, 99), name)):
        session_docs = sorted(grouped[session], key=_doc_k)
        reference = session_docs[0].get("schedule")
        reference = reference if isinstance(reference, dict) else {}
        for doc in session_docs[1:]:
            other = doc.get("schedule")
            other = other if isinstance(other, dict) else {}
            for key in ("policy", "warmup_order", "rounds"):
                if other.get(key) != reference.get(key):
                    raise ValueError(
                        f"render: {session}-session documents disagree on "
                        f"schedule.{key}: {reference.get(key)!r} vs "
                        f"{other.get(key)!r} — a session has one recorded "
                        f"schedule")
        schedules.append((session, reference))
    if not schedules:
        raise ValueError("render: the documents carry no schedule")
    return schedules


def _methodology_lines(docs):
    """Reps, per-session rotation/warmup, -s, asymmetry, stats cost."""
    params = _shared_params(docs)
    lines = [
        "## Methodology",
        "",
        f"- reps: {params.get('reps')} measured per arm; cooldown "
        f"{params.get('cooldown_s')} s between measured runs.",
        "- rotation: round-robin rotation — every round visits every arm "
        "once, and round r starts at arm r mod N, so order bias cannot "
        "accumulate inside one arm's block.",
        "- one discarded warmup per TOOL before round 0.",
    ]
    for session, schedule in _session_schedules(docs):
        label = {"cli": "CLI session",
                 "python": "Python session",
                 "synthetic": "synthetic session"}.get(
                     session, f"{session} session")
        lines.append(
            f"- {label} schedule policy: {schedule.get('policy')}; warmup "
            f"order: {', '.join(schedule.get('warmup_order') or [])}.")
        rounds = schedule.get("rounds") or []
        if rounds:
            schedule_text = "; ".join(
                f"round {index}: {' then '.join(order)}"
                for index, order in enumerate(rounds))
            lines.append(f"- {label} recorded rotation: {schedule_text}.")
    lines += [
        f"- jellyfish `-s {params.get('hash_size')}` (generous initial hash).",
        "- rustkmer `--size` stayed at its default and is NOT matched to "
        "jellyfish `-s`: rustkmer auto-grows while jellyfish receives a "
        "generous `-s`; matching the numbers would pre-reserve roughly "
        "160 GB.",
        "- decompression asymmetry: rustkmer reads the `.gz` natively; "
        "jellyfish receives `gzcat <part_001> <part_006> | jellyfish count "
        "... /dev/stdin`, so decompression is inside BOTH measured walls (the "
        "residual pipe overhead remains and is stated here per protocol).",
        "- exact counts are re-read from every measured run's OWN output "
        "immediately after that run, outside the timed wall, so a rep that "
        "silently counts nothing invalidates its arm before any median "
        "exists; `rustkmer stats` scans the whole database per read, so these "
        "per-rep parity reads are not part of any recorded wall time.",
        "- every number in this report is read from the committed result "
        "documents; the renderer holds no measurement literals and consults "
        "no clock.",
        "",
    ]
    return lines


def renderer_source_commit():
    """Last commit that touched THIS renderer (`phase10.py`) — provenance.

    `harness_source_commit()` from bench.py hashes bench.py, not this file, so
    using it here labeled bench.py's commit as the renderer's (IN-02) — a
    reader checking out that commit could get a `phase10.py` without the
    guards the report relies on. Deterministic across re-renders (unrelated
    commits do not move it), and 'unknown' outside a git checkout —
    deterministic in that environment too.
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


def _provenance_lines(docs):
    """CLI binary + Python module provenance, selected by SESSION, not order.

    `--docs` order is unrestricted: a python-session document's `provenance`
    block describes the INTERPRETER (`binary`), so using `docs[0]` positionally
    mislabels `/venv/bin/python` as the CLI binary. The CLI lines come from
    the cli-session document (every cli-session document must name the same
    measured binary bytes); the Python lines come from the python-session
    document, including the CLI parity reference it recorded.
    """
    cli_docs = sorted((doc for doc in docs if doc.get("session") == "cli"),
                      key=_doc_k)
    python_docs = sorted(
        (doc for doc in docs if doc.get("session") == "python"), key=_doc_k)
    if cli_docs:
        primary = cli_docs[0].get("provenance")
    elif python_docs:
        raise ValueError(
            "render: a cli-session document is required to name the CLI "
            "binary — a python-session provenance must never be labeled as "
            "the CLI binary")
    else:
        # Synthetic stage: the document's primary binary IS the CLI binary.
        primary = docs[0].get("provenance")
    if not isinstance(primary, dict):
        raise ValueError("render: the cli-session document carries no "
                         "provenance")
    binary = primary.get("binary")
    if not isinstance(binary, dict):
        raise ValueError("render: the cli-session provenance has no binary "
                         "block")
    for doc in cli_docs[1:]:
        other = (doc.get("provenance") or {}).get("binary")
        if other != binary:
            raise ValueError(
                f"render: cli-session documents name different measured "
                f"binaries ({binary!r} vs {other!r}) — the report cannot "
                f"attribute one measured CLI binary")
    lines = [
        "## Provenance",
        "",
        f"- CLI binary: `{binary['path']}` — size_bytes={binary['size_bytes']} "
        f"sha256=`{binary['sha256']}`",
        f"- CLI build: git commit `{primary['git_commit']}`, dirty="
        f"{primary['git_dirty']}, profile {primary['build_profile']}, "
        f"{primary['rust_toolchain']}",
    ]
    if python_docs:
        module_sources = [doc.get("provenance") for doc in python_docs]
    elif not cli_docs:
        module_sources = [primary]
    else:
        module_sources = []
    if module_sources:
        module_prov = module_sources[0]
        if (not isinstance(module_prov, dict)
                or not isinstance(module_prov.get("module"), dict)):
            raise ValueError(
                "render: the python-session document carries no module "
                "provenance")
        module = module_prov["module"]
        for other_prov in module_sources[1:]:
            other = (other_prov or {}).get("module")
            if other != module:
                raise ValueError(
                    f"render: python-session documents name different "
                    f"measured modules ({module!r} vs {other!r}) — the "
                    f"report cannot attribute one measured extension")
        lines.append(
            f"- Python module: `{module['path']}` — "
            f"size_bytes={module['size_bytes']} sha256=`{module['sha256']}`")
        lines.append(
            f"- Python interpreter: {module_prov.get('python_executable')} "
            f"({module_prov.get('python_version')}); maturin "
            f"{module_prov.get('maturin_version')}")
        cli_reference = module_prov.get("cli_binary")
        if (isinstance(cli_reference, dict)
                and isinstance(cli_reference.get("binary"), dict)):
            ref = cli_reference["binary"]
            lines.append(
                f"- Python session CLI parity reference: `{ref['path']}` — "
                f"size_bytes={ref['size_bytes']} sha256=`{ref['sha256']}`")
    lines += [
        f"- Harness source commit (last commit touching this renderer): "
        f"`{renderer_source_commit()}`",
        "",
    ]
    return lines


def validate_report_text(text):
    """Assert the five mandatory literals are present, case-sensitively."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("render: the report text is empty")
    for literal in REPORT_LITERALS:
        if literal not in text:
            raise ValueError(
                f"render: mandatory report literal {literal!r} is missing — "
                f"the report cannot be published without it")
    return text


def render_report_text(docs):
    """Render the Phase-10 Markdown report text from recorded documents.

    Mechanical by construction: every number comes from the documents, the
    only environment read is `renderer_source_commit()`, and no clock is
    consulted — re-rendering the same documents is byte-identical, so a
    hand-edited number is detectable. The five mandatory literals are
    validated in memory before any byte is published.
    """
    if not docs:
        raise ValueError("render_report needs at least one document")
    validated = [_validate_render_document(doc) for doc in docs]
    pairs = _render_groups(validated, allow_synthetic=True)
    lines = [
        "# rustkmer vs Jellyfish2 — Phase 10 benchmark report",
        "",
        "*Mechanically rendered from the committed result documents by "
        "`python3 scripts/bench/phase10.py --stage render`. Every number "
        "below is read from those documents — the renderer holds no "
        "measurement literals and consults no clock — so re-rendering "
        "reproduces this file byte-for-byte and a hand-edited number is "
        "detectable (BENCH-V2-02/T-10-05).*",
        "",
    ]
    lines += _dataset_lines(validated)
    for k in sorted(pairs):
        cli_doc, python_doc = pairs[k]
        lines += [f"## k={k}", ""]
        if cli_doc is python_doc:
            lines += _table_lines(cli_doc, "combined")
        else:
            lines += _table_lines(cli_doc, "CLI")
            lines += _table_lines(python_doc, "Python")
    lines += _verdict_lines(pairs, validated)
    lines += _parity_lines(pairs, validated)
    lines += _methodology_lines(validated)
    lines += _provenance_lines(validated)
    lines += [
        "---",
        "",
        "*Generated file — do not edit by hand. Regenerate with "
        "`python3 scripts/bench/phase10.py --stage render --docs "
        "<cli-k21.json> <cli-k31.json> <python-k21.json> <python-k31.json> "
        "--verdict-out .planning/phases/10-benchmark-verdict/10-verdict.json "
        "--out .planning/phases/10-benchmark-verdict/"
        "10-BENCHMARK-REPORT.md`; phase directory "
        "`.planning/phases/10-benchmark-verdict/`.*",
        "",
    ]
    return validate_report_text("\n".join(lines))


def render_report(docs, out_path):
    """Write the rendered report (byte-identical on re-render)."""
    text = render_report_text(docs)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(text)
    return out


def _unlink_quiet(path):
    """Best-effort unlink; an OSError (directory, permission) never escapes."""
    try:
        Path(path).unlink()
    except OSError:
        pass


def _restore_file(path, data):
    """Best-effort atomic restore of pre-existing bytes.

    Used only on the publish failure path: a restore problem must never
    replace the exception that caused the failure, so OSError is swallowed.
    """
    temp_name = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".restore", dir=str(path.parent))
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(temp_name, str(path))
        temp_name = None
    except OSError:
        pass
    finally:
        if temp_name is not None:
            _unlink_quiet(temp_name)


def publish_atomic(artifacts):
    """Publish [(destination, text)] via sibling temps + os.replace.

    All-or-nothing: on ANY failure the temps and every destination that did
    not exist before are removed, while every PRE-EXISTING destination is
    restored to its previous bytes — a failed re-render must never destroy a
    previously published verdict/report. Identical destinations and
    non-regular-file destinations are rejected up front, and cleanup errors
    never mask the original exception (WR-11).
    """
    destinations = [Path(path) for path, _text in artifacts]
    resolved = [path.resolve() for path in destinations]
    if len(set(resolved)) != len(resolved):
        raise ValueError(
            "publish: every destination must be a distinct file path, got "
            f"{[str(path) for path in destinations]!r} — publishing the same "
            f"path twice would silently keep only one artifact")
    backups = {}
    for path in destinations:
        if not path.exists():
            continue
        if not path.is_file():
            raise ValueError(
                f"publish: destination {path} exists and is not a regular "
                f"file — refusing to replace it")
        try:
            backups[path] = path.read_bytes()
        except OSError as exc:
            raise ValueError(
                f"publish: cannot back up existing destination {path}: "
                f"{exc}") from exc
    temps = []
    try:
        for path, text in artifacts:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            os.close(fd)
            temp = Path(temp_name)
            temps.append(temp)
            with open(temp, "w", newline="\n", encoding="utf-8") as fh:
                fh.write(text)
        for (path, _text), temp in zip(artifacts, temps):
            os.replace(str(temp), str(Path(path)))
    except BaseException:
        for temp in temps:
            _unlink_quiet(temp)
        for path in reversed(destinations):
            if path in backups:
                _restore_file(path, backups[path])
            else:
                _unlink_quiet(path)
        raise


def _load_result_documents(paths):
    docs = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            docs.append(json.load(fh))
    return docs


def run_render(args):
    """Build the verdict document and the report IN MEMORY, then publish.

    A fresh invocation writes neither destination on EXIT_INVALID; a failed
    re-render preserves every pre-existing destination (never destroys a
    previously published verdict/report). The verdict document's
    `provenance.created` is its only varying field and the report never
    includes it, so the report alone is byte-comparable.

    The stage consumes recorded JSON only: its provenance is the MEASURED CLI
    provenance carried by the source documents, so no local release binary or
    Rust toolchain is required to re-render the verdict (WR-04).
    """
    if not args.docs:
        invalid("the render stage requires --docs <the four result documents>")
    if args.verdict_out is None:
        invalid("the render stage requires --verdict-out <verdict document>")
    out_path = Path(args.out)
    verdict_path = Path(args.verdict_out)
    try:
        docs = [_validate_render_document(doc)
                for doc in _load_result_documents(args.docs)]
        pairs = _render_groups(docs, allow_synthetic=False)
        verdicts = [verdict_block(k, cli_doc, python_doc)
                    for k, (cli_doc, python_doc) in sorted(pairs.items())]
        overall = "YES" if all(block["result"] == "YES"
                               for block in verdicts) else "NO"
        verdict_doc = {
            "schema_version": SCHEMA_VERSION,
            "kind": "phase10-verdict",
            "phase": PHASE,
            "created": datetime.now(timezone.utc).isoformat(),
            "verdicts": verdicts,
            "overall": overall,
            "descoped": {
                "requirement": "BENCH-V2-01",
                "decision": ("descoped by user decision on 2026-11-13; no "
                             "KMC3 binary downloaded, installed, or executed"),
            },
            "inputs": [fingerprint(path) for path in args.docs],
            "dev_host_only": True,
            "kmc3_executed": False,
            "ci_baseline_written": False,
            "provenance": _measured_provenance(docs, "render"),
        }
        validate_provenance(verdict_doc)
        report_text = render_report_text(docs)
        publish_atomic([
            (verdict_path, json.dumps(verdict_doc, indent=2) + "\n"),
            (out_path, report_text),
        ])
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — invalid publish, never a verdict
        # `publish_atomic` already restored any pre-existing artifact; a
        # failure before publish never touched the destinations. Never unlink
        # here: that would destroy a previously published verdict/report.
        print(f"phase10.py: {exc}", file=sys.stderr)
        return EXIT_INVALID
    for block in verdicts:
        print(verdict_line(block))
    print(f"PHASE10 VERDICT overall={overall}")
    return EXIT_OK if overall == "YES" else EXIT_NO


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


def python_projection_bytes(d_union,
                            bytes_per_distinct=PYTHON_TWO_CALL_BYTES_PER_DISTINCT):
    """Conservative Python two-call upper bound: ceil(86.5 B / union distinct).

    The measured single-call coefficient is 86 B/distinct. For the two-call
    (part-by-part) full arm the calibrated split is ~33 B/entry on each
    part's engine tables plus ~53.5 B/entry on the union DashMap. Because
    each part's distinct count is at most the union distinct count,
    `33*D_part + 53.5*D_union <= 33*D_union + 53.5*D_union = 86.5*D_union`,
    so `ceil(86.5 * D_union)` is a TRUE upper bound (86 B under-projects by
    0.5 B/distinct). The measured 86 B coefficient is kept as
    `PYTHON_BYTES_PER_DISTINCT`; it is not the two-call bound.
    """
    if (not isinstance(d_union, int) or isinstance(d_union, bool)
            or d_union <= 0):
        raise ValueError(f"d_union must be a positive integer, got {d_union!r}")
    return int(math.ceil(bytes_per_distinct * d_union))


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
        "model": "python-86.5B-per-distinct-conservative-two-call-upper-bound",
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
            "warmup_order": tool_warmup_order(specs),
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

def _measured_provenance(docs, label):
    """The measured CLI provenance block (never a render-time binary).

    The `render` and `preflight-python` stages consume recorded JSON only;
    they must not require a local release binary or Rust toolchain (WR-04).
    The artifact therefore attributes the binary that actually produced the
    source measurements. Every cli-session source document must name the same
    measured binary bytes.
    """
    cli_docs = sorted((doc for doc in docs if doc.get("session") == "cli"),
                      key=_doc_k)
    if not cli_docs:
        raise ValueError(
            f"{label}: a cli-session source document is required to "
            f"attribute the measured binary")
    provenance = cli_docs[0].get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"{label}: source document carries no provenance")
    binary = provenance.get("binary")
    for doc in cli_docs[1:]:
        other = (doc.get("provenance") or {}).get("binary")
        if other != binary:
            raise ValueError(
                f"{label}: source documents name different measured binaries "
                f"({binary!r} vs {other!r}) — the artifact cannot attribute "
                f"one measured CLI binary")
    return provenance


def load_cli_document(path):
    """Load, validate and return one full-mode CLI results document."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate_schema(doc)
    validate_provenance(doc)
    if doc.get("session") != "cli":
        raise ValueError(
            f"preflight source {path} is session={doc.get('session')!r}, "
            f"not 'cli' — only a CLI-session measurement may anchor the "
            f"projection or the cross-session comparison")
    if doc.get("mode") != "full":
        raise ValueError(
            f"preflight source {path} is mode={doc.get('mode')!r}, not 'full' "
            f"— only a full CLI measurement may anchor the projection")
    return doc


def preflight_records(paths, budget_bytes=MEMORY_BUDGET_BYTES):
    """Build one preflight_record per consumed CLI document.

    Returns `(records, provenance)`: the provenance is the measured CLI
    block from the consumed documents, so the artifact never depends on a
    render-time binary (WR-04).
    """
    if len(paths) != 2:
        raise ValueError(
            f"preflight-python consumes exactly the two CLI documents "
            f"(k=21 and k=31), got {len(paths)}")
    records = []
    docs = []
    seen_k = set()
    for path in paths:
        doc = load_cli_document(path)
        docs.append(doc)
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
    if seen_k != set(SLICE_GATE_K_VALUES):
        raise ValueError(
            f"preflight-python requires exactly the pinned k values "
            f"{SLICE_GATE_K_VALUES}, got {sorted(seen_k)} — a projection "
            f"over a different k pair cannot gate the pinned Python arms")
    return records, _measured_provenance(docs, "preflight-python")


def run_preflight_python(args):
    """Project the Python peak from the measured CLI distinct count."""
    if not args.cli_docs:
        invalid("the preflight-python stage requires --cli-docs <two paths>")
    records, provenance = preflight_records(args.cli_docs)
    overall = ("PROCEED" if all(r["decision"] == "PROCEED" for r in records)
               else "BLOCKED")
    doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": "phase10-python-preflight",
        "phase": PHASE,
        "created": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "overall": overall,
        "provenance": provenance,
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


# --- slice gate (stage built here; executed against real data in plan 10-03) -

_COMPRESSION_SUFFIXES = (".fastq.gz", ".fq.gz")
_SPLIT_PART_TOKENS = (".part_001", ".part_006")


def strip_compression_suffix(name):
    """The basename minus a trailing `.fq.gz`/`.fastq.gz`, else None.

    The real split parts are `CRR1936095_r1.part_001.fq.gz` and
    `CRR1936095_r1.part_006.fq.gz`: the part token lives BEFORE the
    compression suffix, so the suffix must be stripped first or a token
    match against the full name can never succeed.
    """
    for suffix in _COMPRESSION_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return None


def require_split_parts(inputs):
    """Exactly part_001 then part_006, matched on the stripped stem."""
    paths = [Path(p) for p in inputs]
    if len(paths) != 2:
        raise ValueError(
            f"the full-scale/slice stages require exactly the two split "
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
            f"expected the two parts to end with .part_001 then .part_006 "
            f"after stripping the compression suffix; got {stems!r}")
    return paths


def build_slice_gate_doc(inputs, rustkmer, scratch, k_values=(21, 31)):
    """Provision the head-4M slice ONCE and record both k gates.

    k=21 is gated against the committed pinned reference, whose sha256 is
    re-checked BEFORE consumption (a modified reference exits 2 with no
    artifact). k=31 has no pinned slice reference, so it is recorded as an
    explicitly labeled live-parity-only gate; no expectation is invented and
    the k=21 counts are never reused. The slice is provisioned from the
    FIRST part only, and the reference is bound to the SOURCE part's
    fingerprint, not the slice's.
    """
    paths = require_split_parts(inputs)
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    fingerprints = [fingerprint(path) for path in paths]
    source_sha256 = fingerprints[0]["sha256"]
    slices = provision_slice([paths[0]], PINNED_SLICE_READS, scratch)
    slice_path = Path(slices[0])
    reference_sha256 = fingerprint(PARITY_REFERENCE)["sha256"]
    if reference_sha256 != REFERENCE_SHA256:
        raise ValueError(
            f"parity reference sha256 {reference_sha256} != pinned "
            f"{REFERENCE_SHA256} — refusing to consume a modified reference")
    try:
        reference_rel = str(PARITY_REFERENCE.relative_to(REPO_ROOT))
    except ValueError:
        reference_rel = str(PARITY_REFERENCE)
    gates = []
    for k in k_values:
        if k not in SLICE_GATE_K_VALUES:
            raise ValueError(
                f"the slice gate only records k={SLICE_GATE_K_VALUES}, "
                f"got {k}")
        counts = run_parity(slice_path, k, ACCEPTANCE_THREADS, rustkmer,
                            scratch, hash_size=PARITY_HASH_SIZE)
        recipe = {
            "mode": "slice",
            "k": k,
            "canonical": True,
            "threads": ACCEPTANCE_THREADS,
            "hash_size": PARITY_HASH_SIZE,
            "slice_selection": "head",
            "slice_reads": PINNED_SLICE_READS,
            "source_sha256": source_sha256,
        }
        if k == 21:
            gate_parity_reference(
                counts, str(PARITY_REFERENCE), source_sha256,
                slice_kind_for("head", PINNED_SLICE_READS),
                PINNED_SLICE_READS, 21, True)
            parity_reference = {"path": reference_rel,
                                "sha256": reference_sha256}
            reference_gate = PINNED_REFERENCE_GATE
        else:
            parity_reference = None
            reference_gate = LIVE_PARITY_ONLY
        gates.append({
            "k": k,
            "slice_recipe": recipe,
            "distinct": counts["distinct"],
            "total": counts["total"],
            "parity_reference": parity_reference,
            "reference_gate": reference_gate,
        })
    doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": "phase10-slice-gate",
        "phase": PHASE,
        "gates": gates,
        "input_fingerprint": fingerprints,
        "created": datetime.now(timezone.utc).isoformat(),
        "provenance": binary_provenance(rustkmer, "release"),
    }
    validate_provenance(doc)
    return doc


def run_slice_gate(args):
    """Resolve the split directory, build the gate record, write it once.

    Input-shape and reference-pin problems return EXIT_INVALID with no
    artifact. A live parity mismatch (exit 1) or an invalid reference (exit
    2) is raised by the bench primitives themselves and propagates.
    """
    out_path = Path(args.out)
    scratch = Path(args.scratch) if args.scratch else out_path.parent / "scratch"
    try:
        inputs = [Path(p) for p in gather_inputs(str(args.data_dir))]
        doc = build_slice_gate_doc(inputs, args.rustkmer, scratch)
    except Exception as exc:  # noqa: BLE001 — invalid gate, never a verdict
        print(f"phase10.py: {exc}", file=sys.stderr)
        return EXIT_INVALID
    write_evidence_doc(doc, out_path)
    for gate in doc["gates"]:
        print(f"SLICE GATE k={gate['k']} distinct={gate['distinct']} "
              f"total={gate['total']} reference={gate['reference_gate']}")
    print(f"slice gate record written to {out_path}")
    return EXIT_OK


# --- full-scale sessions (plans 10-03/10-04) --------------------------------

def _stage_paths(args):
    out_path = Path(args.out)
    scratch = Path(args.scratch) if args.scratch else out_path.parent / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return out_path, scratch


def _resolve_two_parts(data_dir):
    """The complete read-1 set: exactly the pinned two split parts, sorted.

    The full-scale stages measure the pinned CRR1936095 read-1 set: the names
    must be part_001 then part_006 AND the part_001 bytes must match
    `PINNED_SOURCE_SHA256`. A directory of two unrelated `.fq.gz` files can
    never produce a full-scale verdict that the report describes as the
    pinned set (WR-10).
    """
    inputs = require_split_parts(
        [Path(path) for path in gather_inputs(str(data_dir))])
    source_sha = fingerprint(inputs[0])["sha256"]
    if source_sha != PINNED_SOURCE_SHA256:
        raise ValueError(
            f"part_001 sha256 {source_sha} != pinned "
            f"{PINNED_SOURCE_SHA256} — the full-scale stages measure only "
            f"the pinned CRR1936095 read-1 split parts")
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
        "warmup_order": tool_warmup_order(specs),
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

    The session consumes the slice-gate artifact: `--pre-gate` is required and
    validated for complete provenance, the session's k, the same input
    fingerprints, and the gate's slice source sha256 against part_001 BEFORE
    the disk floor, the PRE-RUN projection, the arm specs, or any measured
    round. A failed gate exits 2 with no artifact and no measurement. The
    recorded `pre_gate` block pins the consumed gate's path+sha256, with the
    digest taken before any measured work. The post-arm exact counts are read
    once per arm; the two rustkmer databases must be byte-identical; the
    scratch databases are deleted after their sha256 is recorded. Any failure
    exits 2 with no artifact.
    """
    if not args.pre_gate:
        invalid("the cli stage requires --pre-gate <10-slice-gate.json>")
    out_path, scratch = _stage_paths(args)
    try:
        inputs = _resolve_two_parts(args.data_dir)
        gate_doc = _load_slice_gate_doc(args.pre_gate, args.k)
        current_fingerprints = [fingerprint(path) for path in inputs]
        if gate_doc.get("input_fingerprint") != current_fingerprints:
            raise ValueError(
                f"--pre-gate {args.pre_gate} was measured on different input "
                f"bytes ({gate_doc.get('input_fingerprint')!r}) than the "
                f"current two parts ({current_fingerprints!r})")
        session_gate = next(
            gate for gate in gate_doc["gates"] if gate.get("k") == args.k)
        session_source_sha = session_gate["slice_recipe"]["source_sha256"]
        part1_sha = current_fingerprints[0]["sha256"]
        if session_source_sha != part1_sha:
            raise ValueError(
                f"--pre-gate {args.pre_gate}: the k={args.k} gate's slice "
                f"source sha256 {session_source_sha!r} != part_001's "
                f"{part1_sha!r} — "
                "the gate must have been measured on the pinned slice source")
        pre_gate_sha256 = file_sha256(args.pre_gate)
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
                   "pre_gate": {"path": str(args.pre_gate),
                                "sha256": pre_gate_sha256},
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


def _load_slice_gate_doc(path, k):
    """Read the slice-gate artifact and validate the gate for session k.

    The artifact is a consumed TRUST BOUNDARY: its provenance block must be
    complete before any field is trusted (WR-05), and the gate that
    authorizes THIS session is the one whose k equals the session's k
    (IN-01). Validating only k=21 would leave a k=31 session's gate
    unchecked. The k=31 gate has no pinned reference, so it is validated by
    shape (positive counts) and by the source sha256 its slice recipe shares
    with the k=21 gate — both gates describe the same provisioned slice.
    """
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate_provenance(doc)
    if doc.get("kind") != "phase10-slice-gate":
        raise ValueError(
            f"pre-gate {path} is kind={doc.get('kind')!r}, not "
            f"'phase10-slice-gate'")
    by_k = {}
    for gate in doc.get("gates", []):
        if not isinstance(gate, dict):
            continue
        gate_k = gate.get("k")
        if gate_k in by_k:
            raise ValueError(
                f"pre-gate {path}: duplicate gate for k={gate_k!r}")
        by_k[gate_k] = gate
    if k not in by_k:
        raise ValueError(
            f"pre-gate {path}: no gate for the session's k={k} "
            f"(recorded gates: {sorted(by_k, key=str)}) — a session must "
            f"validate its own k's gate")
    gate = by_k[k]
    for key in ("distinct", "total"):
        value = gate.get(key)
        if (not isinstance(value, int) or isinstance(value, bool)
                or value <= 0):
            raise ValueError(
                f"pre-gate {path}: k={k} gate {key}={value!r} must be a "
                f"positive integer")
    recipe = gate.get("slice_recipe")
    if not isinstance(recipe, dict):
        raise ValueError(
            f"pre-gate {path}: k={k} gate has no slice_recipe")
    source_sha = recipe.get("source_sha256")
    if not isinstance(source_sha, str) or not source_sha:
        raise ValueError(
            f"pre-gate {path}: k={k} gate slice_recipe has no source_sha256")
    if k != 21:
        if 21 not in by_k:
            raise ValueError(
                f"pre-gate {path}: a k={k} session needs the k=21 reference "
                f"gate to prove both gates measured the same slice")
        reference_recipe = by_k[21].get("slice_recipe")
        reference_sha = (reference_recipe.get("source_sha256")
                         if isinstance(reference_recipe, dict) else None)
        if source_sha != reference_sha:
            raise ValueError(
                f"pre-gate {path}: k={k} slice source sha256 {source_sha!r} "
                f"!= the k=21 gate's {reference_sha!r} — both gates must "
                f"describe the same provisioned slice")
    if k == 21:
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
                f"pre-gate {path}: k=21 gate does not carry the pinned "
                f"reference sha256 {REFERENCE_SHA256}")
    return doc


def _load_python_preflight(path, k):
    """Read the preflight record for `k`; return (record, sha256 of the file).

    The artifact is a consumed TRUST BOUNDARY: its provenance block must be
    complete (WR-05) and the bytes are parsed and hashed once, so the sha256
    the Python document pins describes the content actually consumed.

    The gate is re-derived with the harness constant `MEMORY_BUDGET_BYTES`,
    never the record's own `budget_bytes`: a record whose budget differs from
    the pinned budget is rejected outright, so editing the record can never
    turn a blocked projection into PROCEED.
    """
    data = Path(path).read_bytes()
    doc = json.loads(data)
    validate_provenance(doc)
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
    if budget != MEMORY_BUDGET_BYTES:
        raise ValueError(
            f"preflight {path}: budget_bytes={budget!r} != the pinned "
            f"MEMORY_BUDGET_BYTES {MEMORY_BUDGET_BYTES} — a record's own "
            f"budget can never re-derive its gate")
    model_projection = python_projection_bytes(distinct)
    if projected != model_projection:
        raise ValueError(
            f"preflight {path}: projected_bytes={projected!r} != the model's "
            f"{model_projection} — a tampered projection cannot gate the "
            f"Python arm")
    ok, detail = memory_gate(projected, MEMORY_BUDGET_BYTES)
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
    return record, hashlib.sha256(data).hexdigest()


def _check_preflight_matches_cli(preflight, cli_doc, cli_doc_path):
    """The preflight must have been computed from THIS CLI document.

    A projection computed from a different (smaller) CLI document would
    authorize a run whose measured distinct count is higher, so the measured
    count AND the source sha256 are cross-checked against the CLI document
    actually consumed before any measurement starts.
    """
    arm = next((candidate for candidate in cli_doc.get("arms", [])
                if isinstance(candidate, dict)
                and candidate.get("name") == ARM_RK_T16
                and candidate.get("threads") == ACCEPTANCE_THREADS), None)
    if arm is None:
        raise ValueError(
            f"--cli-doc {cli_doc_path}: no {ARM_RK_T16} arm at "
            f"threads={ACCEPTANCE_THREADS} — the preflight cannot be "
            f"cross-checked")
    unique, _total = _exact_counts(arm, f"preflight source {cli_doc_path}")
    if preflight["distinct"] != unique:
        raise ValueError(
            f"--preflight distinct={preflight['distinct']!r} but the consumed "
            f"CLI document {cli_doc_path} records {ARM_RK_T16}.unique_kmers="
            f"{unique} — the projection was not computed from this document")
    actual_sha = file_sha256(cli_doc_path)
    recorded_sha = preflight["distinct_source_sha256"]
    if recorded_sha != actual_sha:
        raise ValueError(
            f"--preflight was computed from a different CLI document "
            f"(distinct_source_sha256={recorded_sha!r} != {actual_sha} for "
            f"{cli_doc_path}) — a preflight over other bytes can never "
            f"authorize this Python run")


def run_python_session(args):
    """Full-scale Python session: `jf-t16` and `py-t16` over both parts.

    Consumes committed evidence only after pinning and validating it: the
    slice-gate artifact must carry complete provenance and the same input
    fingerprints as the current two parts, the preflight record's
    projection/decision is re-derived and cross-checked against the consumed
    CLI document, and the Python artifact records the preflight's path+sha256
    (WR-05). Every rep is a fresh interpreter validated by the `py-t16`
    branch of `run_rounds`; the session is parity-checked internally and
    against the committed CLI document. The scratch `.jf` is deleted after
    its sha256 is recorded.
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
        gate_doc = _load_slice_gate_doc(args.pre_gate, args.k)
        current_fingerprints = [fingerprint(path) for path in inputs]
        if gate_doc.get("input_fingerprint") != current_fingerprints:
            raise ValueError(
                f"--pre-gate {args.pre_gate} was measured on different input "
                f"bytes ({gate_doc.get('input_fingerprint')!r}) than the "
                f"current two parts ({current_fingerprints!r})")
        preflight, preflight_sha256 = _load_python_preflight(
            args.preflight, args.k)
        cli_doc = load_cli_document(args.cli_doc)
        if _doc_k(cli_doc) != args.k:
            raise ValueError(
                f"--cli-doc {args.cli_doc} is k={_doc_k(cli_doc)} but the "
                f"Python session measures k={args.k}")
        _check_preflight_matches_cli(preflight, cli_doc, args.cli_doc)
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
                "preflight": {
                    "path": str(args.preflight),
                    "sha256": preflight_sha256,
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
                        help="cli and python stages: the slice-gate artifact "
                             "(10-slice-gate.json)")
    parser.add_argument("--preflight", default=None,
                        help="python stage: the Python preflight artifact "
                             "(10-python-preflight.json)")
    parser.add_argument("--docs", nargs="+", default=None,
                        help="render stage: the full-mode result documents "
                             "(cli and python, one per k)")
    parser.add_argument("--verdict-out", default=None,
                        help="render stage: the verdict document output path")
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
    if args.stage == "slice-gate":
        return run_slice_gate(args)
    if args.stage == "cli":
        return run_cli_session(args)
    if args.stage == "python":
        return run_python_session(args)
    if args.stage == "render":
        return run_render(args)
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
