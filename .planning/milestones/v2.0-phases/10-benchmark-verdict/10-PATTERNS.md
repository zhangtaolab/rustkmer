# Phase 10: Benchmark Verdict - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 10 (5 code/test to create or modify, 3 evidence artifacts, 1 report, 1 optional doc)
**Analogs found:** 10 / 10 (some only partial at the function level; gaps listed below)

All analog paths below were verified with `git ls-files --error-unmatch` at HEAD.
Current sizes: `scripts/bench/bench.py` = 2,099 lines; `scripts/bench/python_bench.py` = 1,105;
`scripts/bench/output_stage.py` = 698; `scripts/bench/thread_scaling.py` = 491;
`scripts/bench/n_read_differential.py` = 401. **Every edit to these files shifts every cited
line number** — cite function names in plan actions, not just numbers. Line numbers here are
at commit `0b56427` (working tree clean).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/bench/bench.py` (MODIFY: both-parts arm, py-arm hook, footprint parser, Phase-10 renderer) | harness core / utility | batch measurement + transform (report) | `scripts/bench/bench.py` itself (self-extension); protocol analog `scripts/bench/output_stage.py` | exact (self-extension) |
| `scripts/bench/python_bench.py` (MODIFY: full-mode worker, two `add_from_fastq` calls) | worker / controller harness | file-I/O + request-response (fresh subprocess) | `scripts/bench/python_bench.py` itself (`run_worker`, `measure_arm`) | exact (self-extension) |
| `scripts/bench/phase10.py` (NEW — permitted by CONTEXT discretion; alternatively functions appended to `bench.py`) | controller + pure verdict helpers | batch + transform | `scripts/bench/output_stage.py` (controller/verdict) + `scripts/bench/thread_scaling.py` (verdict validation) | exact / role-match |
| `scripts/bench/tests/test_phase10_verdict.py` (NEW) | test | — | `scripts/bench/tests/test_output_stage.py` + `test_render_report.py` | exact |
| `scripts/bench/tests/test_python_full_arm.py` (NEW) | test | — | `scripts/bench/tests/test_python_bench.py` | exact |
| `scripts/bench/tests/test_time_parser.py` (MODIFY) | test | — | itself + `tests/fixtures/time_l_macos.txt` | exact |
| `.planning/phases/10-benchmark-verdict/10-slice-gate.json` (NEW) | artifact (provenance record) | request-response record | `bench.py` parity-record emission (`run_parity_cli`, lines 1123-1155) | role-match |
| `.planning/phases/10-benchmark-verdict/10-results-full-k21.json`, `10-results-full-k31.json` (NEW) | artifact (measurement record) | batch | `.planning/phases/08-.../pre/phase8_output_stage_pre.json` + `output_stage.assemble_doc` | role-match |
| `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md` (NEW) | artifact (rendered report) | transform | `bench.render_report` (lines 1875-1962) + committed `docs/benchmark-report.md` (v1.0 precedent, do not overwrite) | role-match |
| `scripts/bench/README.md` (MODIFY, optional but recommended) | docs/config | — | same file `## Layout`, `## Provenance fields`, `## Python baseline classes` | exact |

**Confirmed scope guardrails:** no file under `scripts/bench/baselines/` is created or modified
(`slice_parity.crr1936095.json`, `python_bench_baseline.darwin.json` are read-only inputs);
`docs/benchmark-report.md` is not overwritten; no Rust file under `src/` or `pyo3/src/` changes.

---

## Pattern Assignments

### `scripts/bench/bench.py` (harness core, batch + transform)

**Analog:** itself. The phase extends this file; it does not rewrite it. Its existing
functions are the pattern source for each seam.

**Imports pattern** (lines 29-42) — stdlib only, no third-party imports, no pip installs:
```python
import argparse
import dataclasses
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
```

**Seam 1 — `parse_time_output` extension** (analog lines 66-79 regexes, 100-134 parser).
Current contract returns exactly `{'wall_s', 'peak_rss_bytes'}` and raises `ValueError` on a
missing line. Phase 10 adds a third regex and two keys; **keep `peak_rss_bytes` meaning raw
macOS RSS** because `validate_schema` requires that key and `reduce_arm` consumes it:
```python
MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")
MAC_FOOTPRINT = re.compile(r"^\s*(\d+)\s+peak memory footprint\s*$")   # new

# inside the existing per-line loop:
if footprint_bytes is None:
    m = MAC_FOOTPRINT.search(line)
    if m:
        footprint_bytes = int(m.group(1))
# after the loop: raise ValueError if footprint missing on darwin? No —
# footprint is Linux-absent; on darwin a missing line is format drift and
# must raise, matching the existing fail-loud stance (lines 128-133).
return {"wall_s": wall_s, "peak_rss_bytes": peak_rss_bytes,
        "peak_footprint_bytes": footprint_bytes,
        "peak_bytes": max(peak_rss_bytes, footprint_bytes)}
```
Fixture evidence (current `tests/fixtures/time_l_macos.txt` line 18 already carries a footprint
line `6128072`): pipeline arm values to pin are `(526_532_608, 1_294_648)`; direct child values
are `(1_194_852_352, 1_192_199_608)` (RESEARCH Pitfall 5). Existing tests assert individual
keys only (no whole-dict equality), so extra keys are backward-compatible; do **not** change
`peak_rss_bytes` semantics.

**Seam 2 — both-parts arm construction** (analog `BenchmarkConfig` lines 167-183,
`rustkmer_count_cmd` 201-213, `jellyfish_count_cmd` 216-244). The required shape is one arm
whose `inputs` is the full two-part list:
```python
cfg_full = BenchmarkConfig(k=k, canonical=True, threads=16,
                           hash_size=DEFAULT_HASH_SIZE,
                           inputs=[part_001, part_006],
                           decompressor=default_decompressor())
rustkmer_count_cmd(cfg_full, db_out, rustkmer)   # -i p1 p2
jellyfish_count_cmd(cfg_full, jf_out)            # gzcat p1 p2 | jellyfish ... /dev/stdin
```
`provision_full` (lines 631-638) returns the first two resolved inputs and `run_bench`
(lines 1370-1376) builds `cfg_a=inputs[0]`, `cfg_b=inputs[1]` — that is the v1.0 **two-arm**
arrangement and must NOT be reused as the Phase-10 input seam. Leave `DEFAULT_HASH_SIZE = "10G"`
(line 58) and never pass `--size` to rustkmer (Pitfall 2; `--size` is divided across 64
partitions at `src/count/engine.rs:604`, default 1,000,000 at `src/cli/args.rs:53-54`).

**Seam 3 — arm scheduling / protocol** (analog `run_comparison_protocol` lines 1244-1311).
The working pattern to preserve: one discarded warmup per *tool* before round 0, then
`schedule[str(rnd)]` rounds, each rep recording `cache_state`, `round`, `arm_order`:
```python
for rnd in range(reps):
    position = 0
    for tool in schedule[str(rnd)]:
        for spec in [s for s in arm_specs if s["tool"] == tool]:
            cache_state = attempt_cache_purge()
            rep = measure(spec["cmd"])
            rep["cache_state"] = cache_state
            rep["round"] = rnd
            rep["arm_order"] = position
            ...
```
**Do not use `round_schedule` (lines 1160-1169)** — it is hardcoded to two tools
(`rustkmer`/`jellyfish`). Use the start-offset round-robin from
`output_stage.rotation_schedule` (output_stage.py:121-137) / `thread_scaling.rotation_schedule`
(:100-115), which is generic over N arm names and unit-tested.

**Import-cycle constraint (planner must decide):** `python_bench.py` imports
`scripts.bench.bench` at its lines 88-105. Therefore `bench.py` must NOT import
`python_bench`. For a `pyrustkmer` arm inside `run_comparison_protocol`, either (a) the arm
spec carries a pre-read stats payload (the phase-10 module reads the worker stats and passes a
callable/dict), or (b) put the mixed three-tool protocol in a new `phase10.py` that imports both
modules and reuses `measure`, `reduce_arm`, `attempt_cache_purge`, `fingerprint`. Option (b)
matches `output_stage.py`/`thread_scaling.py`, which are standalone controllers importing
primitives from `bench.py`; option (a) keeps RESEARCH's "extend `bench.py`" recommendation.
Either way, no `python_bench` import may appear inside `bench.py`.

**Seam 4 — verdict (new function, do NOT reuse `_count_verdict`)** (analog lines 1617-1626):
```python
def _count_verdict(results):
    jf = _jellyfish_arm(results)
    rk = _rustkmer_count_arms(results)
    return (all(a["median_wall_s"] <= jf["median_wall_s"] for a in rk), ...)
```
This is v1.0-specific and wrong for Phase 10: with a `t1` arm in the document it compares a
1-thread run against a 16-thread jellyfish run and manufactures a NO. The Phase-10 verdict must
filter to arms whose recorded `threads == 16`, compare `rustkmer` and `pyrustkmer` medians to
`jellyfish`, and treat **equality as a match** (`<=`). t1 arms are reported as scaling evidence
only. Use the validation-first shape of `thread_scaling.scaling_verdict` (lines 126-208):
schema → provenance → platform → arm presence/ambiguity → positive counts → positive medians →
then pure arithmetic; return `(exit_code, lines, verdict_block)` with `verdict_block is None` on
every exit-2 path.

**Seam 5 — Phase-10 renderer (new function; leave `render_report` byte-identical)** (analog
`render_report` 1875-1962, `_arm_row` 1587-1605, `_cache_summary` 1741-1752,
`harness_source_commit` 1533-1549). The mechanical-render contract to copy:
- no clock, no measurement literals; every number read from the JSONs;
- `Path.write_text`/`open(..., newline="\n")` for byte-identical re-render (line 1959);
- `harness_source_commit()` uses the **last commit touching the harness file** (stable across
  re-renders), not `HEAD`.
The v1.0 statement blocks are dataset/phase-specific and must not be copied (see
"Copy carefully" below). Required Phase-10 statements per RESEARCH Pattern 4: CRR1936095 both
parts + fingerprints; KMC3 descope sentence; per-rep `cache_state` census + cold-cache
"partially satisfied"; dev-host-only; t16-only rule; CLI binary sha + git commit/dirty + build
profile + Python module sha + interpreter + maturin version.

**Provenance pattern** (lines 268-276 `fingerprint`, 286-289 key list, 309-339
`binary_provenance`, 342-383 `validate_provenance`) — reuse verbatim for the CLI artifact, and
extend the `provenance` block with the Python fields exactly as `python_bench.build_provenance`
does (python_bench.py:744-753: `module`, `python_executable`, `python_version`,
`maturin_version`). `PROVENANCE_KEYS` does not reject extra keys; `validate_provenance` tolerates
them, so `provenance.python_module`-style additions remain schema-valid.

**Error handling / exit contract** (whole file): fail loud on subprocess error with trailing
stderr (`measure` 146-149, `stats` 261-264, `_provenance_tool_output` 302-306); `ValueError` on
format drift and unsafe input; `sys.exit(2)` for invalid/inapplicable gates
(`_parity_ref_invalid` 769-773, `require_jellyfish` 662-673, parity mismatch exit 1 at 644,
`PARITY_REF_INVALID_EXIT = 2` at 659); exit 3 for the disk floor (1227-1241). Never write an
artifact before `validate_schema` + `validate_provenance` (1498-1502).

---

### `scripts/bench/python_bench.py` (worker/controller, file-I/O + fresh subprocess)

**Analog:** itself. Phase 10 adds a full-input mode; it must reuse the fresh-worker discipline
and identity guards rather than re-derive them.

**Imports / package fixup** (lines 81-105): direct-script execution inserts the repo root, then
imports primitives from `scripts.bench.bench`. Any new phase-10 module should copy this fixup
(`output_stage.py:66-72`, `thread_scaling.py:56-62`, `n_read_differential.py:47-51`).

**Exit contract and `invalid`** (lines 107-109, 142-145):
```python
EXIT_OK = 0
EXIT_COMPARISON_RESERVED = 1  # valid measurement, verdict FAIL (artifact kept)
EXIT_INVALID = 2              # no artifact

def invalid(message):
    print(f"python_bench.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)
```
Copy this 0/1/2 contract into the Phase-10 Python arm and report: 0 measured match-or-beat /
1 measured NO (artifact kept) / 2 invalid (no artifact).

**Fresh-worker worker mode** (lines 615-668). The only place `pyrustkmer` is imported:
```python
def run_worker(args):
    threads = parse_threads(args.threads)
    import pyrustkmer
    module_path = _native_module_file(pyrustkmer)
    counter = pyrustkmer.PyCounter(args.k, canonical=True, threads=threads)
    counter.add_from_fastq(str(args.input))
    st = counter.get_stats()
    payload = {
        "total_kmers": int(st.total_kmers),
        "unique_kmers": int(st.unique_kmers),
        "threads": args.threads,
        "threads_resolved": int(st.threads),   # observed, not requested
        "module_path": str(module_path),
        "module_mtime": os.path.getmtime(module_path),
        "python_version": platform.python_version(),
    }
    with open(args.stats_out, "w", encoding="utf-8") as fh: ...
```
Phase-10 full mode requires **two successive `add_from_fastq` calls in the same fresh process**
(one per split part), accumulating exactly (Phase 9 adjacency proof). Keep `threads_resolved` —
`validate_worker_stats` uses it to prove the binding honored `threads=16`. The module sha is
computed by `build_provenance` (`fingerprint(module_path)`), not sent as a payload key; do not
invent a second mechanism.

**Controller arm measurement** (lines 673-741) — the pattern for a fresh-process rep:
`[python, THIS_FILE, "--worker", "--input", ..., "--k", ..., "--threads", ..., "--stats-out", ...]`
wrapped by `bench.measure`; delete a stale stats file before each run; validate the written
payload; persist exact counts in each rep; pin reps with `check_rep_identity`; reduce with
`reduce_arm`. The arm shape recorded here is the one Phase 10 should normalize on:
```python
arm = {"name": ..., "tool": "pyrustkmer",
       "threads": "default" if requested_threads is None else requested_threads,
       "threads_resolved": resolved_threads,
       "reps": reps,
       "medians": {"wall_s": ..., "peak_rss_bytes": ..., "cv_wall_pct": ..., "cv_warning": ...},
       "unique_kmers": exact["unique_kmers"], "total_kmers": exact["total_kmers"]}
```

**Identity guards to reuse** (lines 239-286 `validate_worker_stats`, 289-322
`check_rep_identity`, 325-344 `parity_counts`): nonzero counts, module resolves under the
interpreter's `site_prefix` and has a native suffix (`.so/.pyd/.dylib`), `threads_resolved`
equals the arm's requested configuration, all reps report identical counts/module/threads,
CLI-vs-Python parity on the same bytes is nonzero and equal. These are the Phase-9 discipline the
CONTEXT asks the full arm to reuse.

**Provenance builder** (lines 744-753): `binary_provenance(info["executable"], "release")` then
`prov["module"] = fingerprint(module_path)`, `python_executable`, `python_version`,
`maturin_version`. Reuse for the Python surface of the Phase-10 artifact.

**Validation-before-write** (lines 756-765 `write_json`): `validate_schema` + `validate_provenance`
then write. Copy for the Phase-10 artifacts.

**Do NOT use `--compare-baseline` for the full arm** (lines 782-810; `--mode` choices at
line 1069 are `("synthetic", "slice")`). It is slice-mode and t1-only by construction. The full
arm needs a new `--mode full` (or a phase-10 worker entry) that accepts **multiple** `--input`
paths, calls `add_from_fastq` once per part at `--threads 16`, and writes stats. Do not call
`--emit-baseline` (Pitfall 12).

---

### `scripts/bench/phase10.py` (NEW controller + pure verdict/render helpers) — or functions appended to `bench.py`

**Analog:** `scripts/bench/output_stage.py` (module shape) + `scripts/bench/thread_scaling.py`
(verdict shape) + `n_read_differential.py` (pinned prior-artifact loading).

**Module shape to copy** (output_stage.py:1-55, 66-118): docstring stating the exit contract and
methodology, package fixup, `invalid()`, constants, pure helpers first, controller last,
`main(argv=None)` for unit-test injection, and the terminal exception mapping:
```python
if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"phase10.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)   # infra failures are 2, never the measured 1
```

**Pure rotation** (output_stage.py:121-137): copy verbatim — it is generic over arm count and
unit-tested for per-round coverage, rotation, and wrap:
```python
def rotation_schedule(arm_names, reps):
    names = list(arm_names)
    if not names: raise ValueError(...)
    if reps < 1: raise ValueError(...)
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]
```

**Injectable measured rounds** (output_stage.py:175-208) — the best analog for driving mixed
arms (CLI, jellyfish, Python worker) with tests that never sleep or invoke sudo:
```python
def run_measured_rounds(schedule, arm_cmds, cooldown_s, measure_fn=measure,
                        purge_fn=attempt_cache_purge, sleep_fn=time.sleep,
                        on_rep=None):
    ...
    rep = measure_fn(arm_cmds[name])
    rep["cache_state"] = purge_fn()
    rep["round"] = rnd
    rep["arm_order"] = position
```
The same shape appears in thread_scaling.py:280-289. A Phase-10 CLI-only version can copy it;
for mixed tools, `arm_cmds` becomes per-arm callables and `on_rep` can capture the Python
worker's stats JSON per rep.

**Pure document assembly** (output_stage.py:313-331 `assemble_doc`, 334-355 `build_doc`,
358-370 `write_doc`): pure assembly so unit tests can push the doc through
`bench.validate_schema`/`validate_provenance`; runtime builder adds fingerprint/platform/
provenance; writer validates before touching disk. This is the shape for
`10-results-full-k21.json` / `-k31.json`.

**Pure verdict** (output_stage.py:404-488 `stage_verdict`, 491-497 `verdict_line`):
- validate both docs first; return `EXIT_INVALID, [reason], None` on malformed input;
- collect observations only after validation; any missing/ambiguous arm is exit 2;
- return `(exit_code, report_lines, verdict_block)`;
- machine-greppable verdict line printed only after the validated doc is on disk, floats emitted
  with `repr()` so they round-trip.
For Phase 10 the verdict block carries both surfaces per k, e.g.
`{"result": "YES"|"NO", "k": 21, "rustkmer_wall_s": ..., "python_wall_s": ...,
"jellyfish_wall_s": ..., "rule": "t16 medians; equality is match"}`.

**Pinned prior evidence** (n_read_differential.py:144-194 `load_previous`): validate the prior
artifact structurally **and record its sha256** before embedding. CONTEXT's Phase-9 review
finding applies: if the Phase-10 Python arm consumes any committed evidence (e.g. the slice
parity baseline or `python_bench_baseline.darwin.json`), pin its sha256 in the artifact; the
shape `{"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), ...}` is the analog.

**Memory preflight** (no direct analog; gate shape from `check_disk_floor` bench.py:1227-1241):
pure functions returning projected bytes, plus a gate that exits 2 before any run when the
projection exceeds `BUDGET = 110 * (1 << 30)`:
```python
def cli_peak_bytes(distinct, partitions=64): ...
def python_peak_bytes(d_part, d_union): ...
```
The user-stop behaviour (CONTEXT: STOP and ask) is a controller concern, not an exception —
surface it as a distinct exit path/message, never as a skipped arm.

---

### `scripts/bench/tests/test_phase10_verdict.py` (NEW test)

**Analogs:** `tests/test_output_stage.py` (verdict/rotation/fixture style),
`tests/test_render_report.py` (byte-identity/render statements), `tests/test_thread_scaling.py`
(`--current`-style driver and truth tables).

**Fixture style** (test_output_stage.py:41-134): hand-built constants, `make_provenance()`,
`make_arm(...)`, `make_doc(...)` returning schema-valid documents; no filesystem except tempdir.
Copy the constants-first approach:
```python
def make_provenance():
    return {"binary": {"path": "/repo/target/release/rustkmer",
                       "size_bytes": 2_965_056, "sha256": "a" * 64},
            "git_commit": "b" * 40, "git_dirty": False,
            "build_profile": "release",
            "rust_toolchain": "rustc 1.82.0 (f6e511eec 2024-10-15)",
            "platform": "darwin-arm64",
            "created": "2026-11-13T00:00:00+00:00"}
```

**Rotation tests** (test_output_stage.py:187-218): per-round coverage, consecutive round start
offsets, wrap when reps > arms, rejection of empty/zero. **Verdict truth table**
(test_thread_scaling.py:130-226): material win YES; identical medians YES (equality matches);
one arm worse NO; missing arm / zero counts / malformed provenance / wrong platform exit 2 and
print no verdict line; assert the one `PHASE10 VERDICT` line (repr-round-trip) on verdict paths
and its absence on exit-2 paths (see `assert_verdict_line` / `assert_no_verdict_line`,
test_thread_scaling.py:111-127).

**Render tests** (test_render_report.py:70-109, 158-186): `RenderFixtureBase` writes JSON to a
tempdir, renders twice, asserts byte equality; edit one JSON number and assert the report
changes and the new number appears. New mandatory-statement tests: KMC3 descope sentence,
cold-cache "partially satisfied" census, dev-host-only statement, t16-only verdict rule, CLI +
Python provenance shas. Use `Path.write_text(..., newline="\n")` (3.10+, documented in
test_render_report.py:80); the suite must run under `python3` 3.13, not `/usr/bin/python3` 3.9.

**Discovery:** `scripts/bench/tests/__init__.py` is empty and the suite runs via
`python3 -m unittest discover -s scripts/bench/tests -t .`, so a new file is auto-collected.

---

### `scripts/bench/tests/test_python_full_arm.py` (NEW test)

**Analog:** `tests/test_python_bench.py` — the canonical controller-test pattern without PyO3.

**Fake worker/measure** (test_python_bench.py:31-81): `fake_provenance()`, `make_fake_measure()`
writes the stats file the controller reads and returns deterministic wall/RSS; models a binding
that honors `--threads` by default and can model one that ignores it:
```python
def make_fake_measure(module_path, total=100, unique=90, vary=False,
                      write_stats=True, threads_resolved=None):
    def fake_measure(argv):
        stats_out = Path(argv[argv.index("--stats-out") + 1])
        requested = (argv[argv.index("--threads") + 1] if "--threads" in argv else "1")
        ...
        stats_out.write_text(json.dumps(payload), encoding="utf-8")
        return {"wall_s": 1.0 + i, "peak_rss_bytes": 1_000_000 + i}
    return fake_measure
```
**Two-input accumulation exactness:** build two tiny FASTQ fixtures (see
`fastq_record`/`build_gz_fixture`, test_python_bench.py:84-98) and assert the worker argv
carries both inputs and that the mocked worker call count/order is `part1` then `part2`; a fake
worker can return a summed count so the controller-level expectation is exact. For real
accumulation, follow the opt-in integration gate (`RUSTKMER_PYBENCH_VENV`, test at
test_python_bench.py:1002-1018) — skip when unset.

**Controller harness** (test_python_bench.py:626-688): `mock.patch.object(pb, ...)` over
`interpreter_info`, `maturin_version`, `binary_provenance`, `attempt_cache_purge`, `measure`,
optionally `cli_count_counts`/`fingerprint`; capture `SystemExit`, stdout, stderr. Reuse for the
full-mode entry point. Required negative cases: zero counts exit 2, missing stats file exit 2,
module outside site-packages exit 2, shim (non-native suffix) exit 2, `threads_resolved`
mismatch exit 2, no artifact written on any exit-2 path.

---

### `scripts/bench/tests/test_time_parser.py` (MODIFY)

**Analog:** itself (101 lines, fully read). Existing structure to extend:
- fixture-driven darwin/linux tests (lines 22-67);
- malformed-input `ValueError` tests (lines 69-97);
- `FIXTURES = Path(__file__).resolve().parent / "fixtures"`.

Add a `TestPeakFootprint` class with inline fixtures or new fixture files:
```python
PIPELINE = ("        1.02 real         0.00 user         0.00 sys\n"
            "           526532608  maximum resident set size\n"
            "             1294648  peak memory footprint\n")
DIRECT = ("        2.34 real         2.00 user         0.30 sys\n"
          "          1194852352  maximum resident set size\n"
          "          1192199608  peak memory footprint\n")
```
Assertions: `peak_rss_bytes` stays raw; `peak_footprint_bytes` parses; `peak_bytes ==
max(rss, footprint)` for both shapes; a darwin text with an RSS line but no footprint line
raises (format drift) if the implementation chooses to require it — decide and pin it. The
existing fixture `time_l_macos.txt` already has a footprint line, so its two tests continue to
pass unchanged.

---

### Evidence artifacts (`.planning/phases/10-benchmark-verdict/10-*.json`)

**Analog shapes:** `.planning/phases/08-.../pre/phase8_output_stage_pre.json` (fully read;
3.7 KB) and `bench.run_parity_cli`'s emitted parity record (bench.py:1137-1155).

Top-level shape to follow (schema v1 + provenance, all numbers recorded, no prose):
```json
{
  "schema_version": 1,
  "mode": "full" | "parity-record",
  "params": {"k": 21, "canonical": true, "threads": 16, "reps": 3,
             "cooldown_s": 5, "hash_size": "10G", "decompressor": "gzcat",
             "arm_order": ["rk-t16", "rk-t1", "jf-t16", "py-t16"]},
  "platform": {"system": "...", "release": "...", "machine": "...", "python": "..."},
  "created": "<iso8601>",
  "input_fingerprint": [{"path": "...", "size_bytes": 0, "sha256": "..."}],
  "arms": [{"name": "...", "tool": "...", "threads": 16, "reps": [...],
            "medians": {"wall_s": 0.0, "peak_rss_bytes": 0, "peak_bytes": 0,
                        "cv_wall_pct": null, "cv_warning": false},
            "unique_kmers": 0, "total_kmers": 0}],
  "schedule": {"policy": "round-robin-rotation", "warmup_order": [...], "rounds": [[...]]},
  "verdict": {"result": "YES" | "NO", ...},
  "provenance": {"binary": {...}, "module": {...}, "git_commit": "...", ...}
}
```
Notes:
- Normalize on the **nested `medians` arm shape** used by `output_stage`/`thread_scaling`/
  `python_bench`, not the flat `median_wall_s`/`distinct_kmers` shape used by v1.0 `bench.py`
  (both are schema-valid because `validate_schema` only requires `name`/`reps[]/wall_s/
  peak_rss_bytes`, but one shape must be chosen; nested covers all four modules and carries
  `threads`, which the t16 filter needs).
- `10-slice-gate.json` copies the parity-record emission (bench.py:1123-1155): `kind:
  "parity-record"`, `slice_recipe` (mode/k/canonical/threads/hash_size/slice_selection/
  slice_reads/slice_source_sha256), `distinct`, `total`, `input_fingerprint`, `created`,
  `provenance`; add a `parity_reference` block with the reference file path **and sha256**
  (pin-before-consume, per CONTEXT). JSON is written with `indent=2` + trailing newline
  (bench.py:1500-1502) — keep it for diff stability.
- Do not record `--size` as matched to jellyfish's `-s`; record the actual default 1,000,000 and
  state that jellyfish received a generous `-s` (Pitfall 2).

---

### `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md` (NEW report)

**Analog:** `bench.render_report` (1875-1962) and the v1.0 committed `docs/benchmark-report.md`
(reference only — never overwrite it; render the Phase-10 report phase-locally).

Structural pattern to copy from `render_report`:
- introductory paragraph naming the generating command and the "no measurement literals /
  byte-identical re-render" contract (lines 1897-1905);
- per-k table sections built from `_ARM_TABLE_HEADER` + `_arm_row` (1587-1615), with raw reps
  beside medians and `[cv_warning]` surfaced;
- verdict section computed from medians with the rule spelled out (1617-1649);
- parity evidence section from recorded counts (1667-1706);
- methodology section: reps/schedule, cache census, `-s`, decompression asymmetry, input
  fingerprints, harness provenance (1762-1872);
- generated-file footer (1950-1955).

Phase-10-specific sections (must be present): dataset = CRR1936095 both parts + part_001 sha
`dae91042…`; KMC3 descope sentence; cold-cache "partially satisfied"; dev-host-only; t16-only
verdict rule with t1 as scaling evidence; CLI + Python provenance.

---

### `scripts/bench/README.md` (MODIFY, optional)

**Analog:** same file `## Layout` (539-575), `## Provenance fields` (332-351), `## Python
baseline classes` (353-383). If the phase adds `phase10.py` and new flags/modes, add them to the
Layout tree and document the full-mode invocation. Note the README already promises "CI class —
produced from CI runner artifacts only (Phase 10)" — Phase 10 deliberately does **not** produce a
CI baseline; update that line or state dev-host-only to avoid a false promise.

---

## Shared Patterns

### Provenance on every artifact
**Source:** `scripts/bench/bench.py:268-383` (`fingerprint`, `binary_provenance`,
`validate_provenance`) + `scripts/bench/python_bench.py:744-753` (`build_provenance`).
**Apply to:** every JSON artifact and the report.
```python
prov = binary_provenance(args.rustkmer, "release")
prov["module"] = fingerprint(module_path)          # Python surface only
prov["python_executable"] = info["executable"]
prov["python_version"] = info["version"]
prov["maturin_version"] = maturin_version(args.python)
validate_provenance(doc)
```
Never record a path without a sha; never "unknown" on a failed query (raise instead).

### Counterbalanced rotation + honest per-rep record
**Source:** `output_stage.py:121-137, 175-208`; `thread_scaling.py:100-115, 280-289`.
**Apply to:** the Phase-10 measured rounds.
Every round visits every arm once in rotated order; each rep records `cache_state` (from the
actual purge attempt), `round`, `arm_order`; one discarded warmup per tool. `cache_state` comes
from `bench.cache_state_from`/`attempt_cache_purge` (bench.py:1172-1200) — never from config.

### Parity before timing
**Source:** `bench.run_parity` (712-766) + `gate_parity_reference` (929-951); python_bench
`parity_counts` (325-344).
**Apply to:** every stage/gate.
Live distinct/total must be nonzero and equal across tools **on the measured input** before any
median is trusted; the slice gate is fingerprint-bound to `part_001` (`dae91042…`) and the
committed reference must never be re-pinned. Missing reference/ambiguity exits 2; a mismatch
exits 1.

### Exit contract 0/1/2 + validate-before-write
**Source:** `output_stage.py:92-94, 358-370`; `thread_scaling.py:83-85, 348-360`;
`python_bench.py:107-109, 756-765`.
**Apply to:** the Phase-10 driver, Python arm, and report step.
0 = valid result (YES), 1 = genuine measured NO (artifact kept), 2 = invalid (no artifact).
Infrastructure exceptions map to 2, never 1. `validate_schema` + `validate_provenance` run
before `json.dump`.

### Python fresh-process discipline
**Source:** `python_bench.py:615-741`.
**Apply to:** the `py-t16` arm.
One process = one thread configuration (global rayon pool is first-call-wins). Every rep is a
fresh interpreter under `/usr/bin/time`; the module is resolved to the inner native `.so` and
fingerprinted; `threads_resolved` must equal the requested configuration.

### Memory accounting
**Source:** `bench.py:66-134` (`parse_time_output`), `bench.py:1203-1224` (`reduce_arm`).
**Apply to:** all arms and the preflight.
Record `peak_rss_bytes` (raw), `peak_footprint_bytes` (raw), `peak_bytes = max(...)` per rep.
Report `peak_bytes`; keep `peak_rss_bytes` for schema/reduction compatibility. For pipeline arms
the max is the RSS; for direct children the two are close (Pitfall 5).

### Baseline immutability and host class
**Source:** `bench.py:648-659` (pinned reference constants); `python_bench.py:119-139`
(`HOST_CLASS`, `BASELINE_SCOPE`, `HOST_NOTE`) and baseline identity guards (443-497).
**Apply to:** the report and any consumed baseline.
Never write under `scripts/bench/baselines/`; never pass `--emit-baseline`; pin the sha256 of any
committed evidence consumed; the report states dev-host evidence only.

---

## Copy Carefully — v1.0 / dataset-specific code that must NOT be reused as-is

| Location | Why not to copy | What Phase 10 needs instead |
|---|---|---|
| `bench.py:1617-1626` `_count_verdict` | Requires **every** rustkmer count arm to beat jellyfish; a `t1` arm manufactures a NO | Filter `threads == 16`; compare rk and py separately; equality = match |
| `bench.py:1160-1169` `round_schedule` | Hardcoded two tools (`rustkmer`/`jellyfish`) | Generic `rotation_schedule` (output_stage.py:121-137) |
| `bench.py:631-638` `provision_full` + `run_bench` 1370-1376 | Builds two arms from `inputs[0]`/`inputs[1]` (half the dataset per arm) | One arm, `inputs=[part_001, part_006]` |
| `bench.py:1875-1962` `render_report` | Pinned byte-identically by `test_render_report.py`; hardcodes CRR2044018 and the attempt-1 halt note | New Phase-10 render function; leave v1.0 renderer/tests untouched |
| `bench.py:1908-1911` dataset paragraph | "CRR2044018 is the user-approved substitute" — false for Phase 10 | Real CRR1936095 provenance |
| `bench.py:1847-1856` halt note | v1.0 attempt-1 narrative (commit `8102985`), no Phase-10 relevance | Keep only the methodological rule (parity gate catches multi-member gzip), no historical figure |
| `bench.py:1950-1955` footer | Points at `.planning/phases/04-benchmark-validation/` and `docs/benchmark-report.md` | Phase-10 paths and `10-BENCHMARK-REPORT.md` |
| `bench.py:1652-1706` `_inputs_differ`/`_parity_lines` | Narrative "same input measured twice" / merge-input r2 | Three tools on the same two-part input; one explicit parity statement per k |
| `bench.py:1587-1605` `_arm_row` | Reads flat `median_wall_s`; labels merge arm "n/a" | Phase-10 nested-medians reader; no merge arm |
| `python_bench.py:782-810` `--compare-baseline` guards | Slice-mode and t1-only by construction | New full mode, t16, multi-input |
| `python_bench.py:1069` `--mode choices ("synthetic","slice")` | No full mode | Add `"full"` (or a phase-10 worker entry point) |
| `python_bench.py:637-668` `run_worker` | Single `add_from_fastq`; single `--input` | Two calls, multi-input argv |
| `python_bench.py:199-236` `filter_n_free` / `n_free_control` | Slice-comparison device that removes N bytes | Full arm measures real N-containing data unchanged |
| `python_bench.py:1080-1086` `--emit-baseline` | Writes an immutable comparison basis (Pitfall 12) | Never invoked in Phase 10 |
| `bench.py:57-58` `DEFAULT_RUSTKMER`, `DEFAULT_HASH_SIZE` | Reusable **as constants**, not as a mandate to match `--size` | Keep `-s 10G`; leave rustkmer `--size` at default (Pitfall 2) |
| `bench.py:646` `PARITY_SMOKE_HASH_SIZE = "1G"` | Smoke-scale only | Real gate uses `--hash-size 2G`; full arms use 10G |

**Not dataset-specific (safe to reuse):** `default_decompressor()` (`gzcat` on darwin, never
`zcat`), `validate_path`/`HASH_SIZE_RE`/`DECOMPRESSOR_RE` screening for the one `sh -c` pipeline,
`jellyfish_count_cmd`'s gz-pipe branch, `parse_jellyfish_stats`'s strict line-anchored parser,
`require_jellyfish`, `check_disk_floor`, `cache_state_from`/`attempt_cache_purge`.

---

## No Analog Found (function-level gaps — planner uses RESEARCH.md patterns)

| Gap | Role | Data Flow | Reason |
|---|---|---|---|
| Full-mode Python worker (two `add_from_fastq` calls, t16) | worker | file-I/O | Only slice/synthetic single-input workers exist (`python_bench.py:637-668`) |
| Both-parts CLI/jellyfish arm (one arm, two inputs) | arm builder | batch | `provision_full`/`run_bench` intentionally use one input per arm |
| Peak-memory preflight projection (`cli_peak_bytes`, `python_peak_bytes`) | utility | transform | No projection model exists; closest gate shape is `check_disk_floor` (bench.py:1227-1241) |
| Phase-10 verdict over three tools with t16 filtering | utility | transform | `_count_verdict` is two-tool and all-arms; `scaling_verdict`/`stage_verdict` are single-tool gates |
| Phase-10 report renderer | renderer | transform | v1.0 renderer is pinned and dataset-specific; a new function is required |

---

## Metadata

**Analog search scope:** `scripts/bench/` (all modules + `tests/` + `baselines/`), `.planning/phases/08-output-pipeline-rkdb-v2-parity/` evidence JSONs, `.planning/REQUIREMENTS.md`, `docs/benchmark-report.md` (referenced, not modified).
**Files read in full:** `bench.py` (2,099), `python_bench.py` (1,105), `output_stage.py` (698), `thread_scaling.py` (491), `n_read_differential.py` (401), `tests/test_time_parser.py` (101), `tests/fixtures/time_l_macos.txt`, `pre/phase8_output_stage_pre.json`, `10-CONTEXT.md`, `10-RESEARCH.md`, `10-VALIDATION.md`.
**Files sampled:** `tests/test_output_stage.py` (1-140, test inventory), `tests/test_thread_scaling.py` (1-135, inventory), `tests/test_python_bench.py` (1-195, 626-715, inventory), `tests/test_render_report.py` (1-115, inventory), `tests/test_cmd_matrix.py` (260-299), `scripts/bench/README.md` (332-400, 539-575), `scripts/bench/baselines/*.json` (headers).
**Tracked-source check:** all named analog paths verified with `git ls-files --error-unmatch`; no `.gsd/capabilities/` mirror paths are used or recommended.
**Harness test baseline:** 415 stdlib tests (1 skip) via `python3 -m unittest discover -s scripts/bench/tests -t .`; run with `python3` 3.13, not `/usr/bin/python3` 3.9.
**Pattern extraction date:** 2026-11-13 (commit `0b56427`, tree clean).
