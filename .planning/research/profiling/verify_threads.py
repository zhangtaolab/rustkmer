#!/usr/bin/env python3
"""PROF-02 — observe whether `--threads` sizes BOTH counting pools.

Runs `rustkmer count --threads N` in an INDEPENDENT subprocess per N (the
global rayon pool is initialized once per process, so one child per requested
N is the only honest observation), polls the live child until the expected
total OS thread count is reached, and counts OS threads with a platform
backend:

  * macOS: `sample <pid> 1` (no sudo), keeping the Thread_ line regex and the
    "written to file" redirect handling (sampler="sample");
  * Linux: the entry count of /proc/<pid>/task (sampler="proc-task");
  * anything else: exit 2 (sampler="unsupported") — never a false PASS.

The engine's exact thread model is `expected_total(n)`: `2` for n == 1 (main +
the single rayon worker; the sequential engine spawns no counting thread) and
`2 * n + 1` for n > 1 (main/producer + n persistent engine workers + n rayon
workers). The observer polls until the observed count EQUALS the expectation
(returning immediately, GREEN) or EXCEEDS it (a measured over-count, recorded
as RED); it keeps polling while the count is below the expectation, because
the child legitimately passes through the rayon-only `n + 1` intermediate
state before the engine workers spawn.

Exit contract (the 05-01 gate discipline):
  0 — every record has observed == expected_total(requested);
  1 — the MEASURED verdict: at least one mismatch, including a child that
      exits after at least one successful observation while still below the
      expected total (its HIGHEST observed count is measured RED);
  2 — invalid input / unsupported platform / the child exited before ANY
      successful observation / the polling window timed out with the child
      still alive / any infrastructure failure. Exit-2 paths print NO verdict
      line and write NO JSON, so a crashed run can never masquerade as the
      expected-RED observation. A timeout is never a PASS.

Stdout is machine-greppable: one `requested=<N> observed=<M>` line per N,
then a final `THREAD REALITY verdict=RED|GREEN` line. The structured --json
doc carries one record per N (requested, observed, pid, sampler, platform,
child_returncode, provenance) plus the top-level verdict.

Driven by tests/thread_pool_size_tests.rs (characterization + standing gate)
and scripts/bench/tests/test_verify_threads.py. Python 3.11+ stdlib only.
"""

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 .planning/research/profiling/verify_threads.py):
    # the repo root is not on sys.path yet. Insert it BEFORE importing so the
    # harness package resolves to this checkout in one shot — some environments
    # carry an unrelated `scripts` namespace package in site-packages that
    # would otherwise win the first import (compare.py's fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.bench.bench import binary_provenance, fingerprint

EXIT_GREEN = 0
EXIT_RED = 1
EXIT_INVALID = 2

DEFAULT_THREADS = (1, 4, 16)
DEFAULT_TIMEOUT_S = 30.0
POLL_INTERVAL_S = 0.05
# `sample` can print the SAME thread id twice: once as a
# ``Thread_<tid>: Main Thread`` call-graph summary header (seen when the
# process is sampled during dyld startup) and once as the regular
# ``Thread_<tid> ...`` per-thread section header. Match the id and count
# UNIQUE ids so one OS thread is never double-counted.
THREAD_ID_RE = re.compile(r"^\s*\d+\s+Thread_(\d+)", re.M)
SAMPLE_REDIRECT_RE = re.compile(r"written to file (\S+)")


class ObservationError(Exception):
    """The count child could not be observed (exited early / timed out)."""


def expected_total(n):
    """Exact OS thread total for a `--threads n` counting child.

    `n == 1` is `2`: the main thread plus the single rayon worker; the
    engine's sequential path spawns no counting thread. `n > 1` is
    `2 * n + 1`: the main/producer thread, n persistent engine workers, and
    n rayon workers. This is a hard equality — never a range, never a
    self-report.
    """
    if n < 1:
        raise ValueError(f"requested thread count must be >= 1, got {n}")
    return 2 if n == 1 else 2 * n + 1


def sampler_for(system):
    """Pure backend selection: explicit, and unsupported is never a PASS."""
    if system == "Darwin":
        return "sample"
    if system == "Linux":
        return "proc-task"
    return "unsupported"


def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict."""
    print(f"verify_threads.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def parse_thread_count(text):
    """Count UNIQUE thread ids in a `sample` call-graph report.

    `sample` sometimes emits the main thread twice (a
    ``Thread_<tid>: Main Thread`` summary header plus the regular
    ``Thread_<tid> ...`` section header), so counting matching lines would
    over-report by one. Deduplicating by thread id makes the observed count
    equal the real OS thread count.
    """
    return len(set(THREAD_ID_RE.findall(text)))


def _thread_count(pid, sampler):
    """One observation attempt; None means 'not observable yet, retry'."""
    if sampler == "proc-task":
        try:
            return len(os.listdir(f"/proc/{pid}/task"))
        except OSError:
            return None
    # macOS `sample` (no sudo). A failed sample (e.g. the child just died)
    # is a retry; the poll loop's proc.poll() check catches a dead child.
    s = subprocess.run(["sample", str(pid), "1"], capture_output=True, text=True)
    if s.returncode != 0:
        return None
    txt = s.stdout
    # sample writes its analysis to a file when redirected; find and read it.
    m = SAMPLE_REDIRECT_RE.search(txt)
    if m:
        try:
            txt = Path(m.group(1)).read_text()
        except OSError:
            return None
    count = parse_thread_count(txt)
    # A live process always has at least one OS thread, so a SUCCESSFUL sample
    # whose report carries no thread lines is a transient sampling artifact
    # (typically a sample straddling the child's exit) — never evidence.
    # Return None so the poll loop retries; a zero can never become
    # peak_observed, so a child that exits after only empty reports ends as
    # exit 2 (never observed) instead of a spurious measured RED. The check
    # sits AFTER the redirect handling so a redirected empty report is
    # retried too.
    if count == 0:
        return None
    return count


def observe(proc, timeout_s, sampler, expected):
    """Poll the live child until its OS thread count reaches `expected`.

    Returns immediately when the observed unique-thread count EQUALS the
    expectation (GREEN) or EXCEEDS it (a measured over-count the caller must
    record as RED). Keeps polling while the count is below the expectation:
    the child legitimately passes through the rayon-only `n + 1` intermediate
    state before the engine workers spawn, so an early sample is never
    accepted as the answer.

    A child that exits after at least one successful observation returns the
    HIGHEST (peak) observed count, so a below-expected run is recorded as a
    measured RED mismatch (exit 1) rather than an unobservable exit 2. A
    truncated exit-window sample cannot lower it: a late, partially reported
    `sample` can only under-count.
    `ObservationError` is raised ONLY when the child was never successfully
    observed (it exited before the first sample) or the deadline expires
    with the child still alive; both are unobservable/infrastructure, never a
    PASS.
    """
    deadline = time.monotonic() + timeout_s
    peak_observed = None
    while time.monotonic() < deadline:
        count = _thread_count(proc.pid, sampler)
        if count is not None:
            # A macOS `sample <pid> 1` spans a ~1 s window, so the final
            # sample of an undershooting child necessarily straddles its
            # exit, and a truncated report can only UNDER-count. A counting
            # child's OS thread set is monotonically non-decreasing before
            # exit (persistent engine workers + rayon pools), so the highest
            # nonzero observation is the honest measurement; last-sample
            # semantics would let the exit-window artifact clobber a correct
            # count. The guard is sampler-agnostic: Linux /proc reads can
            # also race teardown.
            if peak_observed is None or count > peak_observed:
                peak_observed = count
            if count >= expected:
                return count
        if proc.poll() is not None:
            if peak_observed is not None:
                return peak_observed
            raise ObservationError(
                f"count process (pid {proc.pid}) exited rc={proc.returncode} "
                "before a successful thread observation"
            )
        time.sleep(POLL_INTERVAL_S)
    if peak_observed is not None and proc.poll() is not None:
        return peak_observed
    raise ObservationError(
        f"pid {proc.pid} did not reach expected={expected} threads within "
        f"{timeout_s}s (peak observed={peak_observed})"
    )


def verdict_for_records(records):
    """Pure GREEN/RED decision: every record must match the exact formula."""
    return (
        "GREEN"
        if all(r["observed"] == expected_total(r["requested"]) for r in records)
        else "RED"
    )


def run_one(binary, input_path, n, out_path, timeout_s, sampler):
    """One independent count child for one requested N; always reaped."""
    proc = subprocess.Popen(
        [str(binary), "count", "-k", "21", "-C", "--threads", str(n),
         "-i", str(input_path), "-o", str(out_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        observed = observe(proc, timeout_s, sampler, expected_total(n))
    finally:
        # T-05-05: terminate/reap the child even when observation fails, so
        # no orphan count process survives a failed run.
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return observed, proc.pid, proc.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Observe the ACTUAL OS thread total (engine counting "
                    "workers + rayon workers + main) of rustkmer count under "
                    "--threads N (PROF-02).")
    parser.add_argument("--binary", required=True,
                        help="rustkmer executable to observe")
    parser.add_argument("--input", required=True,
                        help="FASTQ input large enough to keep counting alive")
    parser.add_argument("--threads", type=int, nargs="+",
                        default=list(DEFAULT_THREADS),
                        help="requested thread counts (default: 1 4 16)")
    parser.add_argument("--json", required=True,
                        help="path for the structured observation records")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S,
                        help="per-N observation deadline in seconds "
                             "(default: 30)")
    parser.add_argument("--build-profile", default="release",
                        help="build profile of --binary for provenance "
                             "(default: release; the Rust tests pass debug)")
    args = parser.parse_args(argv)

    if any(n < 1 for n in args.threads):
        invalid(f"--threads values must be >= 1, got {args.threads}")
    if args.timeout_s <= 0:
        invalid(f"--timeout-s must be > 0, got {args.timeout_s}")
    binary = Path(args.binary)
    if not binary.is_file():
        invalid(f"--binary not found: {args.binary}")
    input_path = Path(args.input)
    if not input_path.is_file():
        invalid(f"--input not found: {args.input}")
    system = platform.system()
    sampler = sampler_for(system)
    if sampler == "unsupported":
        invalid(f"unsupported platform {system!r} (sampler=unsupported): "
                "pool-size observation needs macOS sample or Linux /proc")

    # Fail loud BEFORE any observation if the artifact cannot be attributed
    # (T-05-02: a path string without a hash is not provenance).
    provenance = binary_provenance(binary, args.build_profile)
    plat = f"{sys.platform}-{platform.machine()}"

    records = []
    # T-05-05: process-unique temp dir for the count outputs — no predictable
    # /tmp names; the partial .rkdb files of terminated children are cleaned
    # up with the directory.
    with tempfile.TemporaryDirectory(prefix="verify-threads-") as td:
        for n in args.threads:
            out_path = Path(td) / f"threadcheck{n}.rkdb"
            observed, pid, child_rc = run_one(
                binary, input_path, n, out_path, args.timeout_s, sampler)
            records.append({
                "requested": n,
                "observed": observed,
                "pid": pid,
                "sampler": sampler,
                "platform": plat,
                "child_returncode": child_rc,
                "provenance": provenance,
            })
            print(f"requested={n} observed={observed}", flush=True)

    verdict = verdict_for_records(records)
    doc = {
        "schema_version": 1,
        "created": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "input": fingerprint(input_path),
        "records": records,
    }
    with open(args.json, "w") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    print(f"THREAD REALITY verdict={verdict}", flush=True)
    return EXIT_GREEN if verdict == "GREEN" else EXIT_RED


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("verify_threads.py: interrupted", file=sys.stderr)
        sys.exit(EXIT_INVALID)
    except Exception as exc:
        # Infrastructure failures exit 2, never 1 (05-01 decision): an
        # uncaught exception must never masquerade as the measured RED
        # verdict. Short message, no traceback — the freshness-bound
        # capture rejects tracebacks outright.
        print(f"verify_threads.py: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
