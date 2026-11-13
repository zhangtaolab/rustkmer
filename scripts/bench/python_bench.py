#!/usr/bin/env python3
"""PROF-04 Python counting benchmark (05-06, Phase 9 comparison).

Measures the PyO3 file-counting pipeline
(pyrustkmer.PyCounter.add_from_fastq, canonical=True) under the OS-rusage
protocol: every rep is a FRESH worker process measured via
bench.measure([python, __file__, "--worker", ...]) so /usr/bin/time
wall/RSS covers interpreter startup + extension import + the entire count.
There is no in-process wall clock anywhere in this file. Workers accept
--threads default|N (default "1"): the global rayon pool is first-call-wins,
so the threads=1 isolation arm and the all-cores default arm must always be
measured as separate fresh processes, never in one worker.

Slice-mode baselines carry a parity-validated N-free control as the PRIMARY
comparison basis (comparison_basis: "n-free-control"): the random subslice
is deterministically filtered into a sibling N-free FASTQ (drop whole
4-line records whose sequence line contains N or n), CLI and Python counts
are proven equal on those exact bytes BEFORE timing, and every control rep
must reproduce those exact counts. Because the control contains no N bytes,
CLI skip-N and Python semantics produce identical counts on it both before
and after Phase 9's D2 unification — its exact counts are a parity invariant
Phase 9 must preserve and its timing is the like-for-like win basis. The
real-N arm is separately labeled timing-only post-D2 evidence: its exact
counts are post-D2 skip-N values, not comparable to the pre-D2 committed
baseline, and it is never a parity gate.

--compare-baseline is the Phase 9 dev-host comparison mode. It requires
slice mode and validates the committed baseline's identity (platform
flavor, provenance platform, k/canonical, control-fingerprint shape and
positive exact counts) before provisioning. Before ANY timing it re-proves
CLI-vs-Python parity on the regenerated N-free control, requires that
control's exact counts and sha256 to equal the committed baseline's, then
measures BOTH the threads=1 and default-threads arms as fresh workers. The
verdict comes only from recorded medians with locked inclusive thresholds:
speedup_t1 = baseline_t1 / new_t1 must be >= 1.0 (non-regressive) and
speedup_default = baseline_t1 / new_default must be >= 1.2 (the measured
win), with no noise band. The artifact is written on PASS and on a genuine
FAIL; this is dev-host evidence only and adds no CI gate (Phase 10 owns
CI-class baselines).

The measured extension must be freshly rebuilt from source (pyo3/README.md:
env -u CONDA_PREFIX VIRTUAL_ENV=... maturin develop --release -m
pyo3/Cargo.toml in .venv313). The worker reports the native module's
path/mtime and the controller asserts it resolves under the --python
interpreter's site-packages and fingerprints the ACTUAL .so bytes
(maturin 1.11's editable develop wraps the .so in a generated shim package;
the worker resolves the inner native module so the fingerprint covers the
measured binary, not the shim). A stale/shadowed module is an INVALID
benchmark (exit 2), never a pytest-style skip.

Exit codes are a contract:
  0 — valid measurement (doc written, schema + provenance validated) and,
      in --compare-baseline mode, a PASS verdict.
  1 — valid measurement whose --compare-baseline verdict is FAIL; the
      artifact is STILL written with verdict.exit_code == 1. Never emitted
      by a non-comparison run, never converted into a pass.
  2 — invalid: missing/broken extension import, zero counts, rep-count
      disagreement, shadowed/stale module, control parity mismatch,
      malformed stats, baseline identity/fingerprint/exact-count guard
      failure, provisioning or measurement failure. No artifact is written.

Stdlib only; pyrustkmer is imported lazily inside the worker only, so the
unit suite runs without PyO3/NumPy/pytest/the human dataset.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution: insert the repo root BEFORE importing so the
    # harness package resolves to this checkout in one shot (compare.py's
    # fixup — some environments carry an unrelated `scripts` namespace
    # package in site-packages that would otherwise win the first import).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_COOLDOWN_S,
    DEFAULT_RUSTKMER,
    SCHEMA_VERSION,
    SEED_A,
    SYNTHETIC_LENGTH,
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    fingerprint,
    generate_synthetic_input,
    measure,
    reduce_arm,
    rustkmer_count_cmd,
    stats,
    validate_provenance,
    validate_schema,
)

EXIT_OK = 0
EXIT_COMPARISON_RESERVED = 1  # valid measurement, comparison verdict FAIL (artifact kept)
EXIT_INVALID = 2

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
THIS_FILE = Path(__file__).resolve()
DEFAULT_PYTHON = REPO_ROOT / ".venv313" / "bin" / "python"
DEFAULT_OUT = HERE / "scratch" / "python_bench.json"
SUPPORTED_SYSTEMS = ("Darwin", "Linux")
NATIVE_SUFFIXES = (".so", ".pyd", ".dylib")

HOST_CLASS = "dev-host Apple M4 Max (16 cores, 128 GiB)"
BASELINE_SCOPE = "dev-host-local-comparison"
COMPARISON_BASIS = "n-free-control"
N_FREE_FILTER = "drop-records-with-N"
REAL_N_EVIDENCE_CLASS = "timing-only-real-N-post-D2"
REAL_N_SEMANTICS_NOTE = (
    "exact counts are post-D2 skip-N values, not comparable to the pre-D2 "
    "committed baseline — timing-only evidence; the N-free control is the "
    "only comparison basis"
)
CONTROL_EVIDENCE_CLASS = "parity-validated-n-free-control"
# Locked comparison thresholds (inclusive boundaries, no noise band):
# t1 must be non-regressive against the committed sequential baseline and the
# default thread configuration must deliver the measured win.
MIN_SPEEDUP_T1 = 1.0
MIN_SPEEDUP_DEFAULT = 1.2
HOST_NOTE = (
    "dev-host capture for Phase 9 same-host comparison; NOT a CI baseline — "
    "CI-class baselines bootstrap from CI runner artifacts "
    "(scripts/bench/README.md; Phase 10 owns that)"
)


def invalid(message):
    """Print an input/infra problem and exit 2 — never a measurement."""
    print(f"python_bench.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def parse_threads(text):
    """Parse a --threads value: "default" -> None (all cores), else int >= 1.

    PyO3's `PyCounter(threads=None)` resolves to all available cores — the
    CLI's default. Any other value must be a positive integer literal; an
    invalid configuration is a ValueError (exit 2 upstream), never a silent
    fallback to 1.
    """
    if text == "default":
        return None
    if not isinstance(text, str):
        raise ValueError(f"threads must be 'default' or an integer, got {text!r}")
    try:
        value = int(text)
    except ValueError:
        raise ValueError(
            f"threads must be 'default' or an integer >= 1, got {text!r}")
    if value < 1:
        raise ValueError(f"threads must be >= 1, got {value}")
    return value


def threads_suffix(threads_text):
    """Arm-name suffix that matches the ACTUAL thread configuration.

    ``"1"`` -> ``"t1"``, ``"default"`` -> ``"tdefault"``, ``"N"`` -> ``"tN"``.
    An arm whose name claims ``t1`` must have been measured at one thread
    (WR-01): the suffix is derived from the configuration the workers are
    actually given, never hard-coded.
    """
    value = parse_threads(threads_text)
    return "tdefault" if value is None else f"t{value}"


# --- pure helpers (unit-tested without PyO3) --------------------------------

def baseline_filename(system_name):
    """Platform baseline naming: absolute numbers never cross platforms.

    Returns (filename, flavor) for a supported system; raises ValueError on
    an unsupported platform (a baseline for it would be incomparable).
    """
    flavors = {"Darwin": "darwin", "Linux": "linux"}
    if system_name not in flavors:
        raise ValueError(
            f"unsupported platform {system_name!r} (expected one of "
            f"{SUPPORTED_SYSTEMS})")
    flavor = flavors[system_name]
    return f"python_bench_baseline.{flavor}.json", flavor


def filter_n_free(src, dst):
    """Deterministic order-preserving N-free filter of a plain FASTQ.

    Drops WHOLE 4-line records whose sequence line contains N or n; kept
    records are written byte-for-byte in source order. Returns
    {'kept_reads', 'dropped_reads'}. Raises ValueError on malformed framing
    or an all-N input (a control with zero reads would measure nothing).
    """
    kept = 0
    dropped = 0
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        while True:
            header = fin.readline()
            if header == b"":
                break
            seq = fin.readline()
            plus = fin.readline()
            qual = fin.readline()
            if not seq or not plus or not qual:
                raise ValueError(
                    f"malformed FASTQ {src}: incomplete 4-line record at "
                    f"read index {kept + dropped}")
            if not header.startswith(b"@") or not plus.startswith(b"+"):
                raise ValueError(
                    f"malformed FASTQ {src}: bad record framing at read "
                    f"index {kept + dropped}")
            if b"N" in seq or b"n" in seq:
                dropped += 1
                continue
            fout.write(header)
            fout.write(seq)
            fout.write(plus)
            fout.write(qual)
            kept += 1
    if kept == 0:
        raise ValueError(
            f"N-free filter of {src} kept 0 records — nothing to measure")
    return {"kept_reads": kept, "dropped_reads": dropped}


def validate_worker_stats(payload, site_prefix):
    """Validate one worker stats payload; return its exact counts.

    Raises ValueError on missing fields, non-positive/non-integer counts,
    or a module that does not resolve under the interpreter's site-packages
    prefix as a native extension (a stale/shadowed module elsewhere — or a
    bare Python shim with no native bytes — is an invalid benchmark,
    T-05-11).
    """
    for key in ("total_kmers", "unique_kmers", "module_path", "module_mtime",
                "python_version"):
        if key not in payload:
            raise ValueError(f"worker stats missing field {key!r}")
    for key in ("total_kmers", "unique_kmers"):
        value = payload[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(
                f"worker stats {key}={value!r} — a zero/invalid count is a "
                f"silent input failure, never a measurement")
    module = Path(payload["module_path"]).resolve()
    prefix = Path(site_prefix).resolve()
    if not module.is_relative_to(prefix):
        raise ValueError(
            f"worker module {module} is outside the interpreter's "
            f"site-packages {prefix} — stale/shadowed extension; rebuild "
            f"via maturin develop --release in the --python venv")
    if module.suffix not in NATIVE_SUFFIXES:
        raise ValueError(
            f"worker module {module} is not a native extension "
            f"({NATIVE_SUFFIXES}) — the measured bytes must be the .so, "
            f"not a Python shim")
    return {"total_kmers": payload["total_kmers"],
            "unique_kmers": payload["unique_kmers"]}


def check_rep_identity(reps, expected=None):
    """All reps of one input must report identical exact counts and module.

    Any disagreement is a nondeterministic pipeline (exit 2 upstream) —
    never averaged away. `expected` optionally pins the counts to a
    parity-checked reference. Returns the exact-counts dict.
    """
    if not reps:
        raise ValueError("check_rep_identity: no reps")
    seen = {(r["total_kmers"], r["unique_kmers"]) for r in reps}
    if len(seen) != 1:
        raise ValueError(
            f"rep-count disagreement: {sorted(seen)} — nondeterministic "
            f"pipeline, never averaged away")
    modules = {r["module_path"] for r in reps}
    if len(modules) != 1:
        raise ValueError(
            f"rep module disagreement: {sorted(modules)} — the measured "
            f"extension changed mid-run")
    total, unique = next(iter(seen))
    exact = {"total_kmers": total, "unique_kmers": unique}
    if expected is not None and (
            total != expected["total_kmers"]
            or unique != expected["unique_kmers"]):
        raise ValueError(
            f"rep counts {exact} differ from the parity-checked reference "
            f"{expected}")
    return exact


def parity_counts(cli_stats, python_counts):
    """CLI-vs-Python parity on the SAME bytes, both nonzero (pre-timing).

    Returns the parity_control block; raises ValueError on any mismatch —
    a performance baseline without correctness evidence is invalid.
    """
    cli = {"distinct": int(cli_stats["unique_kmers"]),
           "total": int(cli_stats["total_kmers"])}
    py = {"unique_kmers": int(python_counts["unique_kmers"]),
          "total_kmers": int(python_counts["total_kmers"])}
    if cli["distinct"] <= 0 or cli["total"] <= 0:
        raise ValueError(f"parity control: CLI zero counts {cli}")
    if py["unique_kmers"] <= 0 or py["total_kmers"] <= 0:
        raise ValueError(f"parity control: Python zero counts {py}")
    if cli["distinct"] != py["unique_kmers"] or cli["total"] != py["total_kmers"]:
        raise ValueError(
            f"control parity mismatch: CLI {cli} vs Python {py} on the same "
            f"N-free bytes — invalid baseline (parity-before-timing)")
    return {"reference": "rustkmer-cli-same-bytes",
            "cli": cli, "python": py, "equal": True}


def _control_arm_wall(control, suffix):
    """The one arm of `control` whose name ends with `suffix`, its wall_s."""
    arms = control.get("arms") if isinstance(control, dict) else None
    if not isinstance(arms, list) or not arms:
        raise ValueError("new doc has no n_free_control.arms list")
    matches = [a for a in arms
               if isinstance(a, dict)
               and str(a.get("name", "")).endswith(suffix)]
    if len(matches) != 1:
        names = [a.get("name") for a in arms if isinstance(a, dict)]
        raise ValueError(
            f"expected exactly one control arm ending {suffix!r}, found "
            f"{len(matches)} in {names}")
    medians = matches[0].get("medians")
    wall = medians.get("wall_s") if isinstance(medians, dict) else None
    if (not isinstance(wall, (int, float)) or isinstance(wall, bool)
            or wall <= 0):
        raise ValueError(
            f"control arm {matches[0].get('name')!r}: medians.wall_s must be "
            f"a positive number, got {wall!r} — no timing observation")
    return float(wall)


def _arm_threads_is_one(arm):
    """True when an arm records a real integer thread count of 1 (not bool)."""
    threads = arm.get("threads")
    return (isinstance(threads, int) and not isinstance(threads, bool)
            and threads == 1)


def _baseline_control_t1_arm(control):
    """The committed baseline's unambiguous threads=1 control arm.

    Selection is by IDENTITY — the name ends with ``-n-free-control-t1``
    AND the arm records ``threads == 1`` — never by list position (WR-01).
    A baseline whose only control arm was measured at another configuration
    cannot supply ``speedup_t1``/``speedup_default`` and is invalid.
    """
    arms = control.get("arms") if isinstance(control, dict) else None
    if not isinstance(arms, list) or not arms:
        raise ValueError("baseline has no n_free_control.arms")
    matches = [arm for arm in arms
               if isinstance(arm, dict)
               and str(arm.get("name", "")).endswith("-n-free-control-t1")
               and _arm_threads_is_one(arm)]
    if len(matches) != 1:
        observed = [(arm.get("name"), arm.get("threads"))
                    for arm in arms if isinstance(arm, dict)]
        raise ValueError(
            "baseline has no unambiguous threads=1 control arm (exactly one "
            "arm named '*-n-free-control-t1' with threads == 1); observed "
            f"{observed}")
    return matches[0]


def compare_to_baseline(baseline, new_doc):
    """Locked comparison math: committed control median vs the two new arms.

    `speedup_t1 = baseline_t1 / new_t1` must reach MIN_SPEEDUP_T1 (1.0,
    non-regressive) and `speedup_default = baseline_t1 / new_default` must
    reach MIN_SPEEDUP_DEFAULT (1.2, the measured win). Boundaries are
    inclusive and there is no tolerance band. The verdict is computed only
    from the recorded medians; missing/ambiguous arms are a ValueError
    (exit 2 upstream), never a fabricated verdict.
    """
    control = baseline.get("n_free_control") if isinstance(baseline, dict) else None
    baseline_arm = _baseline_control_t1_arm(control)
    medians = baseline_arm.get("medians")
    baseline_t1 = medians.get("wall_s") if isinstance(medians, dict) else None
    if (not isinstance(baseline_t1, (int, float))
            or isinstance(baseline_t1, bool) or baseline_t1 <= 0):
        raise ValueError(
            f"baseline control arm {baseline_arm.get('name')!r} "
            f"medians.wall_s must be a positive number, got {baseline_t1!r}")
    baseline_t1 = float(baseline_t1)

    new_control = new_doc.get("n_free_control") if isinstance(new_doc, dict) else None
    new_t1 = _control_arm_wall(new_control, "-n-free-control-t1")
    new_default = _control_arm_wall(new_control, "-n-free-control-tdefault")

    speedup_t1 = baseline_t1 / new_t1
    speedup_default = baseline_t1 / new_default
    passed = (speedup_t1 >= MIN_SPEEDUP_T1
              and speedup_default >= MIN_SPEEDUP_DEFAULT)
    return {
        "baseline_wall_s": baseline_t1,
        "new_t1_wall_s": new_t1,
        "new_default_wall_s": new_default,
        "speedup_t1": speedup_t1,
        "speedup_default": speedup_default,
        "min_speedup_t1": MIN_SPEEDUP_T1,
        "min_speedup_default": MIN_SPEEDUP_DEFAULT,
        "result": "PASS" if passed else "FAIL",
    }


def validate_baseline_identity(baseline, expected_flavor, host_platform, k,
                               canonical):
    """Reject a baseline captured on another host/configuration (exit 2).

    A dev-host baseline is only comparable to a run with the same platform
    flavor, provenance platform, k, canonical setting, an unambiguous
    threads=1 control arm, control fingerprint presence, and positive exact
    counts. No absolute numbers are hard-coded here — the committed baseline
    file is the source of truth.
    """
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a JSON object")
    if baseline.get("platform") != expected_flavor:
        raise ValueError(
            f"baseline platform {baseline.get('platform')!r} != "
            f"{expected_flavor!r} — absolute numbers never cross platforms")
    provenance = baseline.get("provenance")
    prov_platform = (provenance.get("platform")
                     if isinstance(provenance, dict) else None)
    if prov_platform != host_platform:
        raise ValueError(
            f"baseline provenance.platform {prov_platform!r} != "
            f"{host_platform!r} — cross-host comparison is invalid")
    params = baseline.get("params")
    if not isinstance(params, dict):
        raise ValueError("baseline has no params block")
    if params.get("k") != k:
        raise ValueError(
            f"baseline k {params.get('k')!r} != {k!r}")
    if params.get("canonical") is not canonical:
        raise ValueError(
            f"baseline canonical {params.get('canonical')!r} != "
            f"{canonical!r}")
    control = baseline.get("n_free_control")
    if not isinstance(control, dict):
        raise ValueError("baseline has no n_free_control block")
    _baseline_control_t1_arm(control)
    fingerprint_block = control.get("input_fingerprint")
    sha = (fingerprint_block.get("sha256")
           if isinstance(fingerprint_block, dict) else None)
    if not isinstance(sha, str) or not sha.strip():
        raise ValueError(
            "baseline n_free_control.input_fingerprint.sha256 must be a "
            "non-empty string")
    exact = control.get("exact_counts")
    if not isinstance(exact, dict):
        raise ValueError("baseline has no n_free_control.exact_counts block")
    for key in ("total_kmers", "unique_kmers"):
        value = exact.get(key)
        if (not isinstance(value, int) or isinstance(value, bool)
                or value <= 0):
            raise ValueError(
                f"baseline n_free_control.exact_counts.{key} must be a "
                f"positive integer, got {value!r}")


def build_baseline(doc, control_block, flavor):
    """Assemble the dev-host baseline envelope from a validated run doc.

    A slice-mode baseline WITHOUT a parity-passing n_free_control block is
    invalid (ValueError → exit 2 upstream): the N-free control is the
    primary comparison basis that survives Phase 9's D2 semantics change.
    The top-level arms remain the real-N measurement, labeled timing-only.
    """
    if doc.get("mode") != "slice":
        raise ValueError(
            "baselines are slice-mode only — the committed comparison basis "
            "is the parity-validated N-free control of a real random subslice")
    if not isinstance(control_block, dict):
        raise ValueError(
            "slice-mode baseline requires an n_free_control block")
    parity = control_block.get("parity_control")
    if not isinstance(parity, dict) or parity.get("equal") is not True:
        raise ValueError(
            "baseline requires a parity-passing n_free_control "
            "(parity_control.equal must be true)")
    exact = control_block.get("exact_counts")
    if (not isinstance(exact, dict)
            or exact.get("total_kmers", 0) <= 0
            or exact.get("unique_kmers", 0) <= 0):
        raise ValueError(
            "baseline n_free_control lacks positive exact_counts")
    control_arms = control_block.get("arms")
    if not isinstance(control_arms, list) or not control_arms:
        raise ValueError("baseline n_free_control has no measured arms")
    _baseline_control_t1_arm(control_block)
    for arm in control_arms:
        for rep in arm.get("reps", []):
            if (rep.get("total_kmers") != exact["total_kmers"]
                    or rep.get("unique_kmers") != exact["unique_kmers"]):
                raise ValueError(
                    "baseline n_free_control rep counts differ from its "
                    "exact_counts — cross-rep identity violated")
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "platform": flavor,
        "mode": doc["mode"],
        "created": doc["created"],
        "generated": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": doc["input_fingerprint"],
        "params": doc["params"],
        "host_note": HOST_NOTE,
        "host_class": HOST_CLASS,
        "baseline_scope": BASELINE_SCOPE,
        "comparison_basis": COMPARISON_BASIS,
        "arms": doc["arms"],
        "n_free_control": control_block,
        "provenance": doc["provenance"],
    }
    validate_schema(baseline)
    validate_provenance(baseline)
    return baseline


# --- interpreter / build-tool attribution -----------------------------------

def interpreter_info(python):
    """Query the --python interpreter (list form) for its executable,
    version, and site-packages prefix. Fail loud on a broken interpreter."""
    code = (
        "import json, platform, sys, sysconfig; "
        "print(json.dumps({'executable': sys.executable, "
        "'version': platform.python_version(), "
        "'site_prefix': sysconfig.get_paths()['purelib']}))"
    )
    proc = subprocess.run([str(python), "-c", code],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"--python interpreter query failed rc={proc.returncode}: "
            f"{python}\ntrailing stderr:\n{proc.stderr[-500:]}")
    return json.loads(proc.stdout)


def maturin_version(python):
    """Attribute the build tool: maturin beside the interpreter, else the
    interpreter's installed distribution metadata. Fail loud — an
    unattributable build tool must never gate."""
    maturin = Path(python).resolve().parent / "maturin"
    if maturin.is_file():
        proc = subprocess.run([str(maturin), "--version"],
                              capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    proc = subprocess.run(
        [str(python), "-c",
         "import importlib.metadata as m; print('maturin ' + m.version('maturin'))"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"cannot attribute maturin version for {python} — install "
            f"maturin in the venv (pyo3/README.md source-install pattern)")
    return proc.stdout.strip()


def cli_count_counts(input_path, k, rustkmer, db_path):
    """Count the SAME bytes through the CLI (parity reference, not timed).

    List-form rustkmer_count_cmd with the same k/canonical and --threads 1;
    counts read via `rustkmer stats -f json` (snake_case serde keys).
    """
    cfg = BenchmarkConfig(k=k, canonical=True, threads=1,
                          inputs=[input_path])
    cmd = rustkmer_count_cmd(cfg, db_path, rustkmer)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"CLI parity count failed rc={proc.returncode}: {cmd}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return stats(db_path, rustkmer)


# --- worker mode (the ONLY place pyrustkmer is imported) --------------------

def _native_module_file(mod):
    """Resolve the actual native extension file of the imported module.

    maturin 1.11's editable `develop` installs a generated shim package
    (__init__.py: `from .pyrustkmer import *`) around the .so; the measured
    bytes are the inner native module, so a .py __file__ resolves through
    the native submodule. A shim with no native submodule is invalid.
    """
    path = Path(mod.__file__)
    if path.suffix in NATIVE_SUFFIXES:
        return path.resolve()
    native = getattr(mod, mod.__name__, None)
    native_file = getattr(native, "__file__", None)
    if native_file and Path(native_file).suffix in NATIVE_SUFFIXES:
        return Path(native_file).resolve()
    raise RuntimeError(
        f"pyrustkmer resolved to {path} with no native extension submodule "
        f"— stale/shadowed install; rebuild via maturin develop --release")


def run_worker(args):
    """One fresh-process count; stats to --stats-out AND stdout."""
    threads = parse_threads(args.threads)
    try:
        import pyrustkmer
    except Exception as exc:
        print(
            f"python_bench worker: INVALID benchmark — cannot import "
            f"pyrustkmer: {exc}. Rebuild the extension from source: "
            f"env -u CONDA_PREFIX VIRTUAL_ENV=\"$PWD/.venv313\" "
            f"PATH=\"$PWD/.venv313/bin:$PATH\" .venv313/bin/maturin develop "
            f"--release -m pyo3/Cargo.toml", file=sys.stderr)
        return EXIT_INVALID
    module_path = _native_module_file(pyrustkmer)
    counter = pyrustkmer.PyCounter(args.k, canonical=True, threads=threads)
    counter.add_from_fastq(str(args.input))
    st = counter.get_stats()
    payload = {
        "total_kmers": int(st.total_kmers),
        "unique_kmers": int(st.unique_kmers),
        "threads": args.threads,
        "module_path": str(module_path),
        "module_mtime": os.path.getmtime(module_path),
        "python_version": platform.python_version(),
    }
    with open(args.stats_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(json.dumps(payload))
    return EXIT_OK


# --- controller --------------------------------------------------------------

def measure_arm(args, info, input_path, scratch, arm_name, gap,
                expected_counts=None, threads_text="1"):
    """One discarded warmup + --reps fresh-worker measured reps on one input.

    Every run's wall/RSS comes from bench.measure of a FRESH worker process
    (OS rusage — never an in-process clock). Each worker gets its own
    --threads value (`default|N`): the global rayon pool is first-call-wins,
    so one worker process can only ever measure one thread configuration.
    After each run the stats file is validated (nonzero counts, module under
    site-packages) and the EXACT counts are persisted in the rep record.
    Returns (arm_dict, exact_counts).
    """
    stats_path = scratch / f"{arm_name}.stats.json"
    worker_argv = [str(args.python), str(THIS_FILE), "--worker",
                   "--input", str(input_path), "--k", str(args.k),
                   "--threads", str(threads_text),
                   "--stats-out", str(stats_path)]

    def one_run():
        if stats_path.exists():
            stats_path.unlink()
        rep = measure(worker_argv)
        if not stats_path.is_file():
            raise ValueError(
                f"worker wrote no stats file at {stats_path} — malformed "
                f"worker run")
        with open(stats_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        counts = validate_worker_stats(payload, info["site_prefix"])
        rep.update(counts)
        rep["module_path"] = payload["module_path"]
        return rep, counts

    warmup_rep, warmup_counts = one_run()
    gap()
    pin = expected_counts if expected_counts is not None else warmup_counts
    reps = []
    for i in range(args.reps):
        cache_state = attempt_cache_purge()
        rep, _ = one_run()
        rep["cache_state"] = cache_state
        rep["rep"] = i
        reps.append(rep)
        gap()
    exact = check_rep_identity(reps, expected=pin)
    reduced = reduce_arm(reps)
    threads_value = parse_threads(threads_text)
    arm = {
        "name": arm_name,
        "tool": "pyrustkmer",
        # "default" records the all-cores configuration; a concrete int is
        # the identical --threads value the workers were given. Never null.
        "threads": "default" if threads_value is None else threads_value,
        "reps": reps,
        "medians": {
            "wall_s": reduced["median_wall_s"],
            "peak_rss_bytes": reduced["median_peak_rss_bytes"],
            "cv_wall_pct": reduced["cv_wall_pct"],
            "cv_warning": reduced["cv_warning"],
        },
        "unique_kmers": exact["unique_kmers"],
        "total_kmers": exact["total_kmers"],
    }
    return arm, exact


def build_provenance(args, info, module_path):
    """binary_provenance of the measured interpreter, extended with the
    native module fingerprint (ACTUAL .so bytes) and build-tool attribution."""
    prov = binary_provenance(info["executable"], "release")
    prov["module"] = fingerprint(module_path)
    prov["python_executable"] = info["executable"]
    prov["python_version"] = info["version"]
    prov["maturin_version"] = maturin_version(args.python)
    prov["build_profile"] = "release"
    return prov


def write_json(doc, out_path):
    """Validate schema AND provenance, then write — an invalid artifact
    never reaches disk (Phase 9 consumes the baseline as a gate input)."""
    validate_schema(doc)
    validate_provenance(doc)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


def run_controller(args):
    """Provision, measure fresh-worker reps, emit the doc (+ baseline)."""
    system = platform.system()
    expected_name, flavor = baseline_filename(system)
    if args.emit_baseline is not None:
        if args.mode != "slice":
            raise ValueError(
                "--emit-baseline is slice-mode only — the committed "
                "comparison basis is the parity-validated N-free control")
        if Path(args.emit_baseline).name != expected_name:
            raise ValueError(
                f"--emit-baseline filename must be {expected_name} on this "
                f"platform (got {Path(args.emit_baseline).name}) — absolute "
                f"numbers never cross platforms")
    if args.compare_baseline is not None:
        if args.mode != "slice":
            raise ValueError(
                "--compare-baseline requires --mode slice — the N-free "
                "control of a real random subslice is the only comparison "
                "basis")
        if args.emit_baseline is not None:
            raise ValueError(
                "--emit-baseline and --compare-baseline are mutually "
                "exclusive — a comparison run never re-pins a baseline")
        if not Path(args.compare_baseline).is_file():
            raise ValueError(
                f"--compare-baseline file not found: {args.compare_baseline}")
    if args.reps < 1:
        raise ValueError(f"--reps must be >= 1, got {args.reps}")
    if not 1 <= args.k <= 64:
        raise ValueError(f"--k must be in 1..64, got {args.k}")
    threads_value = parse_threads(args.threads)
    if args.emit_baseline is not None and threads_value != 1:
        raise ValueError(
            "--emit-baseline requires --threads 1: the committed comparison "
            f"basis is a threads=1 control arm (got {args.threads!r}) — an "
            "arm named '-t1' measured at another configuration cannot be a "
            "baseline")
    if not Path(args.python).is_file():
        raise ValueError(f"--python interpreter not found: {args.python}")
    if args.mode == "slice":
        if args.input is None:
            raise ValueError("slice mode requires --input <gz>")
        if not Path(args.input).is_file():
            raise ValueError(f"--input not found: {args.input}")
        if not Path(args.rustkmer).is_file():
            raise ValueError(
                f"rustkmer binary not found: {args.rustkmer} — build it "
                f"first (cargo build --release --locked); it is the "
                f"control's CLI parity reference")

    info = interpreter_info(args.python)
    out_path = Path(args.out)
    scratch = out_path.parent
    scratch.mkdir(parents=True, exist_ok=True)

    # Cooldown accounting across EVERY run (warmups + measured reps, plus
    # the slice mode's extra parity warmup), so the thermal gap separates
    # runs but never trails the last one. Compare mode measures two control
    # arms (t1 + default) — the same two-arm shape as slice mode.
    runs_per_arm = 1 + args.reps
    total_runs = runs_per_arm * (2 if args.mode == "slice" else 1)
    if args.mode == "slice":
        total_runs += 1  # parity warmup on the N-free control
    done_runs = 0

    def gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            time.sleep(args.cooldown_s)

    selection_manifest = None
    control_block = None
    baseline = None
    comparison = None
    exit_code = EXIT_OK
    compare = args.compare_baseline is not None
    if args.mode == "synthetic":
        input_path = scratch / "inputA.fq"
        generate_synthetic_input(args.reads, SYNTHETIC_LENGTH, SEED_A,
                                 input_path)
        arm, _ = measure_arm(args, info, input_path, scratch,
                             f"py{args.k}-synthetic-"
                             f"{threads_suffix(args.threads)}", gap,
                             threads_text=args.threads)
        arm["evidence_class"] = "synthetic-smoke"
        arms = [arm]
    else:
        from scripts.bench.random_slice import reservoir_slice
        input_path = scratch / "slice-random-0.fq"
        manifest_path = scratch / "slice-random-0.manifest.json"
        selection_manifest = reservoir_slice(
            args.input, args.slice_reads, args.slice_seed, input_path,
            manifest_path)

        # --- parity-validated N-free control (primary comparison basis) ---
        control_path = scratch / "slice-nfree-control.fq"
        filter_counts = filter_n_free(input_path, control_path)
        if compare:
            with open(args.compare_baseline, encoding="utf-8") as fh:
                baseline = json.load(fh)
            validate_baseline_identity(
                baseline, flavor, f"{sys.platform}-{platform.machine()}",
                args.k, True)
        control_name = (f"py{args.k}-n-free-control-"
                        f"{threads_suffix(args.threads)}")
        # The control's discarded warmup doubles as the Python side of the
        # pre-timing parity gate (thread_scaling's warmup-as-parity pattern).
        control_stats_path = scratch / f"{control_name}.stats.json"
        if control_stats_path.exists():
            control_stats_path.unlink()
        measure([str(args.python), str(THIS_FILE), "--worker",
                 "--input", str(control_path), "--k", str(args.k),
                 "--stats-out", str(control_stats_path)])
        gap()
        if not control_stats_path.is_file():
            raise ValueError("control warmup worker wrote no stats file")
        with open(control_stats_path, encoding="utf-8") as fh:
            warmup_payload = json.load(fh)
        warmup_counts = validate_worker_stats(warmup_payload,
                                              info["site_prefix"])
        cli_db = scratch / "nfree-control-cli.rkdb"
        cli_st = cli_count_counts(control_path, args.k, args.rustkmer, cli_db)
        parity = parity_counts(cli_st, warmup_counts)
        print(f"control parity OK distinct={parity['cli']['distinct']} "
              f"total={parity['cli']['total']} "
              f"(kept={filter_counts['kept_reads']} "
              f"dropped={filter_counts['dropped_reads']})")

        if compare:
            # Pre-timing identity: the regenerated control must reproduce the
            # committed baseline's exact counts AND its fingerprint. Either
            # mismatch is an invalid measurement (exit 2), never a verdict.
            expected_exact = baseline["n_free_control"]["exact_counts"]
            if (warmup_counts["total_kmers"] != expected_exact["total_kmers"]
                    or warmup_counts["unique_kmers"]
                    != expected_exact["unique_kmers"]):
                raise ValueError(
                    f"control exact counts {warmup_counts} differ from the "
                    f"committed baseline {expected_exact} — the N-free "
                    f"control's counts are a parity invariant post-D2 "
                    f"Python counting must preserve")
            control_fp = fingerprint(control_path)["sha256"]
            baseline_fp = baseline["n_free_control"]["input_fingerprint"]["sha256"]
            if control_fp != baseline_fp:
                raise ValueError(
                    f"regenerated control fingerprint {control_fp} differs "
                    f"from the committed baseline {baseline_fp} — "
                    f"deterministic provisioning or the source input changed")

        if compare:
            control_arm, control_exact = measure_arm(
                args, info, control_path, scratch, control_name, gap,
                expected_counts=warmup_counts, threads_text="1")
            control_arm["evidence_class"] = CONTROL_EVIDENCE_CLASS
            default_name = f"py{args.k}-n-free-control-tdefault"
            default_arm, _ = measure_arm(
                args, info, control_path, scratch, default_name, gap,
                expected_counts=warmup_counts, threads_text="default")
            default_arm["evidence_class"] = CONTROL_EVIDENCE_CLASS
            control_block = {
                "input_fingerprint": fingerprint(control_path),
                "source_selection_manifest": selection_manifest,
                "kept_reads": filter_counts["kept_reads"],
                "dropped_reads": filter_counts["dropped_reads"],
                "filter": N_FREE_FILTER,
                "parity_control": parity,
                "exact_counts": control_exact,
                "arms": [control_arm, default_arm],
                "cli_provenance": binary_provenance(args.rustkmer, "release"),
            }
            arms = [control_arm, default_arm]
        else:
            control_arm, control_exact = measure_arm(
                args, info, control_path, scratch, control_name, gap,
                expected_counts=warmup_counts, threads_text=args.threads)
            control_arm["evidence_class"] = CONTROL_EVIDENCE_CLASS
            control_block = {
                "input_fingerprint": fingerprint(control_path),
                "source_selection_manifest": selection_manifest,
                "kept_reads": filter_counts["kept_reads"],
                "dropped_reads": filter_counts["dropped_reads"],
                "filter": N_FREE_FILTER,
                "parity_control": parity,
                "exact_counts": control_exact,
                "arms": [control_arm],
                "cli_provenance": binary_provenance(args.rustkmer, "release"),
            }

            # --- real-N arm: timing-only post-D2 evidence ---
            arm, _ = measure_arm(args, info, input_path, scratch,
                                 f"py{args.k}-real-n-"
                                 f"{threads_suffix(args.threads)}", gap,
                                 threads_text=args.threads)
            arm["evidence_class"] = REAL_N_EVIDENCE_CLASS
            arm["semantics_note"] = REAL_N_SEMANTICS_NOTE
            arms = [arm]

    params = {
        "k": args.k,
        "canonical": True,
        # Compare mode's baseline-comparable arm is threads=1; otherwise the
        # controller's own --threads value is recorded honestly.
        "threads": 1 if compare else (
            "default" if threads_value is None else threads_value),
        "reps": args.reps,
        "cooldown_s": args.cooldown_s,
        "python": str(args.python),
        "rustkmer": str(args.rustkmer),
    }
    if args.mode == "synthetic":
        params["reads"] = args.reads
    else:
        params["slice_reads"] = args.slice_reads
        params["slice_seed"] = args.slice_seed
        params["input"] = str(args.input)
    if compare:
        params["threads_default"] = "default"
        params["compare_baseline"] = str(args.compare_baseline)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "mode": "compare-baseline" if compare else args.mode,
        "params": params,
        "platform": {
            "system": system,
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "created": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": [fingerprint(input_path)],
        "arms": arms,
        "provenance": build_provenance(args, info, arms[0]["reps"][0]["module_path"]),
    }
    if selection_manifest is not None:
        doc["selection_manifest"] = selection_manifest
    if control_block is not None:
        doc["n_free_control"] = control_block
    if compare:
        comparison = compare_to_baseline(baseline, doc)
        exit_code = (EXIT_OK if comparison["result"] == "PASS"
                     else EXIT_COMPARISON_RESERVED)
        doc["comparison"] = comparison
        doc["verdict"] = {"result": comparison["result"],
                          "exit_code": exit_code}
        doc["baseline"] = {
            "path": str(args.compare_baseline),
            "sha256": fingerprint(args.compare_baseline)["sha256"],
            "created": baseline.get("created"),
            "host_class": baseline.get("host_class"),
            "comparison_basis": baseline.get("comparison_basis"),
            "control_wall_s": comparison["baseline_wall_s"],
            "exact_counts": baseline["n_free_control"]["exact_counts"],
        }
    # Exit 2 paths never reach this write: every guard above raises first.
    # PASS and a genuine FAIL both land here — a FAIL keeps its artifact.
    write_json(doc, out_path)
    print(f"results written to {out_path}")

    if args.emit_baseline is not None:
        baseline_doc = build_baseline(doc, control_block, flavor)
        write_json(baseline_doc, args.emit_baseline)
        print(f"dev-host baseline written to {args.emit_baseline} "
              f"(scope={BASELINE_SCOPE}, basis={COMPARISON_BASIS})")

    for arm in arms:
        print(f"{arm['name']}: median wall {arm['medians']['wall_s']:.3f}s "
              f"unique={arm['unique_kmers']} total={arm['total_kmers']}")
    if compare:
        print(f"COMPARISON VERDICT result={comparison['result']} "
              f"speedup_t1={comparison['speedup_t1']!r} "
              f"speedup_default={comparison['speedup_default']!r} "
              f"min_speedup_t1={comparison['min_speedup_t1']!r} "
              f"min_speedup_default={comparison['min_speedup_default']!r}")
    return exit_code


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PROF-04 PyO3 counting benchmark (fresh-worker OS-rusage "
                    "protocol); --compare-baseline adds the Phase 9 dev-host "
                    "baseline verdict with the 0/1/2 exit contract.")
    parser.add_argument("--worker", action="store_true",
                        help="internal: run one fresh-process count")
    parser.add_argument("--input",
                        help="worker: plain FASTQ; controller: gz source")
    parser.add_argument("--k", type=int, default=21)
    parser.add_argument("--stats-out", help="worker: stats JSON destination")
    parser.add_argument("--threads", default="1", type=str,
                        help="worker/arm thread count: 'default' (all "
                             "cores) or an integer >= 1")
    parser.add_argument("--python", default=str(DEFAULT_PYTHON),
                        help="interpreter with the freshly built extension")
    parser.add_argument("--mode", choices=("synthetic", "slice"),
                        default="synthetic")
    parser.add_argument("--reads", type=int, default=200000,
                        help="synthetic read count")
    parser.add_argument("--slice-reads", type=int, default=1000000)
    parser.add_argument("--slice-seed", type=int, default=20261112)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--cooldown-s", type=float, default=DEFAULT_COOLDOWN_S)
    parser.add_argument("--rustkmer", default=DEFAULT_RUSTKMER,
                        help="CLI parity reference for the N-free control")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--emit-baseline",
                        help="slice-mode: also write the dev-host baseline")
    parser.add_argument("--compare-baseline",
                        help="slice-mode: compare the N-free control medians "
                             "against a committed dev-host baseline "
                             "(exit 0 PASS, 1 valid FAIL with artifact, "
                             "2 invalid)")
    args = parser.parse_args(argv)

    if args.worker:
        if args.input is None or args.stats_out is None:
            invalid("--worker requires --input and --stats-out")
        return run_worker(args)
    try:
        return run_controller(args)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        invalid(str(exc))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # infra failures exit 2, never a traceback
        print(f"python_bench.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)