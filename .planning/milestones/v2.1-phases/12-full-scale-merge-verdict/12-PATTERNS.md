# Phase 12: Full-Scale Merge Verdict - Pattern Map

**Mapped:** 2026-11-17
**Files analyzed:** 8 (2 new code files, 1 modified code file, 4 runtime evidence artifacts, 1 rewritten doc)
**Analogs found:** 7 / 8 with direct codebase analogs (1 partial: Leg-2 recount diff has building blocks but no complete analog)

**Naming warning (D-01 verbatim):** the new controller is `scripts/bench/phase11.py` even though it executes in roadmap Phase 12. The name follows the `phase10.py` precedent's file-naming convention and is locked by D-01 — do NOT "fix" it to `phase12.py`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/bench/phase11.py` (NEW) | controller (staged orchestrator) | event-driven staged pipeline (subprocess + evidence file I/O) | `scripts/bench/phase10.py` | exact |
| Leg-2 recount diff (inside `phase11.py`) | parity-gate utility | streaming file I/O | `scripts/bench/merge_characterize.py` streaming pipeline | role-match (building blocks exact, assembly new) |
| Merge-verdict renderer sections (in `phase11.py`; WR-02 may touch `bench.py`) | renderer (JSON → Markdown transform) | transform | `phase10.py render_report_text` + `bench.py render_report` | exact |
| `scripts/bench/tests/test_phase11_verdict.py` (NEW) | test (unit, stdlib unittest) | in-memory fixtures + injected seams | `scripts/bench/tests/test_phase10_verdict.py` | exact |
| Stage evidence JSONs (`12-PARITY-K*.json`, `12-RESULTS-FULL-K*.json`, `12-VERDICT.json`, `12-RENDER-PROOF.json`) | evidence documents (runtime outputs) | file I/O (validate-then-write) | `merge_characterize.py` doc I/O + `phase10.py write_doc`/`write_evidence_doc` | exact |
| `scripts/bench/bench.py` (MODIFY — optional WR-02 same-touch ONLY) | CLI arg validation | request-response | itself (`bench.py:2527-2531`, `2556-2561`) | exact (self) |
| `docs/benchmark-report.md` (REWRITE — D-04 wrap-up) | documentation | — | itself + `12-MERGE-REPORT.md` as the sole number source | exact (self) |
| D-03 artifact deletion (wrap-up task) | plan task (no new code) | file deletion | `merge_characterize.cleanup_scratch` (precedent only) | n/a (task, not code) |

---

## Pattern Assignments

### 1. `scripts/bench/phase11.py` — the staged controller (controller, event-driven)

**Analog:** `scripts/bench/phase10.py` (copy its skeleton wholesale; D-01 says "modeled on the phase10.py precedent")

**Module header + stdlib contract + script-execution path fixup** (`phase10.py:42-63`; same fixup in `merge_characterize.py:48-49, 62-64`):

```python
Python 3.11+ stdlib only — no third-party imports.

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/phase11.py): insert the repo
    # root BEFORE importing so the harness package resolves to this checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_DISK_FLOOR_GB, DEFAULT_RUSTKMER, SCHEMA_VERSION, BYTES_PER_GIB,
    BenchmarkConfig, attempt_cache_purge, binary_provenance,
    build_merge_cmd, check_disk_floor, fingerprint, jellyfish_merge_cmd,
    jellyfish_stats, reduce_arm, rustkmer_count_cmd, stats,
    validate_provenance, validate_schema,
)
from scripts.bench.output_stage import rotation_schedule
from scripts.bench.merge_characterize import (
    measured_run, route_from_stderr, dump_vs_dump_equal_streaming,
    _normalized_sorted_dump,
)
from scripts.bench.prepare_inputs import revalidate_stage, DEFAULT_ARTIFACTS_DIR
```

**Exit-code constants + invalid() helper** (`phase10.py:97-99, 178-181`):

```python
EXIT_OK = 0        # valid result (the verdict stage's measured YES)
EXIT_NO = 1        # a genuine measured NO (artifact kept)
EXIT_INVALID = 2   # invalid/inapplicable (no artifact written)

def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict."""
    print(f"phase10.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)
```

**Pinned-constants block precedent** (`phase10.py:130-164` — every constant carries a provenance comment naming its evidence file; `phase11.py` constants should cite `11-PREPARE-RECORD.md` / `11-LADDER-RESULTS.json` / `11-FLOOR-DERIVATION.md` the same way):

```python
# Fixed inputs / evidence locations for the full-scale stages (plan 10-02+).
DEFAULT_DATA_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")
PHASE_DIR = (Path(__file__).resolve().parent.parent.parent / ".planning"
             / "phases" / "10-benchmark-verdict")
# The five mandatory report literals asserted verbatim by this plan's tests...
REPORT_LITERALS = (...)
PHASE = 10
```

**Stage dispatch + parser + main** (`phase10.py:2539-2610`) — `phase11.py` stages per D-01/research: `("revalidate", "parity", "timed", "verdict", "render")`:

```python
STAGES = ("synthetic", "slice-gate", "cli", "python", "render",
          "preflight-python")

def build_parser():
    parser = argparse.ArgumentParser(description="Phase 10 ...")
    parser.add_argument("--stage", choices=STAGES, default="synthetic")
    parser.add_argument("--out", required=True,
                        help="results/decision document output path")
    # ... per-stage input paths as --docs / --cli-doc style args (resume contract)
    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # ... validate numeric args with parser.error(...)
    if args.stage == "synthetic":
        return run_synthetic(args)
    # ... one branch per stage
    invalid(f"stage {args.stage!r} not implemented in plan 10-02")
    return EXIT_INVALID
```

**Top-level exception mapping (the exit-code contract, verbatim shape)** (`phase10.py:2613-2622`):

```python
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
```

Exit 3 is reserved for the disk-floor block (`bench.py:63 DISK_FLOOR_EXIT = 3`) — it surfaces from `check_disk_floor`/`ensure_disk_headroom` and must not be remapped by the controller.

**Resume contract:** each stage takes its predecessors' artifacts by explicit `--`-args and re-runs idempotently from recorded JSON — `run_render` (`phase10.py:1677-1694`) is the template: it validates required args via `invalid(...)`, loads only recorded documents, and never needs the release binary.

---

### 2. STAGE revalidate — round-0 gate (controller stage, request-response)

**Analog:** `scripts/bench/prepare_inputs.py` `revalidate_stage` (lines 616-645) — the controller calls this; it does NOT reimplement hashing:

```python
# Source: scripts/bench/prepare_inputs.py:616-645
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
        raise RuntimeError(...)
    verify_recorded_artifacts(manifest, rustkmer)
    recorded_names = {...}
    for path in sorted(artifacts_dir.iterdir()):
        if (path.is_file() and path.suffix in (".rkdb", ".jf")
                and path.name not in recorded_names):
            raise RuntimeError(...)
    return manifest
```

CLI equivalent also available (`prepare_inputs.py:711-717`): `python3 scripts/bench/prepare_inputs.py revalidate` (exit 2 on drift).

**Anchor equality** is controller-level arithmetic over the verified manifest's per-part `total` records (sum-of-counts definition), compared EXACT against the union anchors: k=21 → 4,483,548,820 + 4,483,550,383 = 8,967,099,203; k=31 → 4,137,846,285 + 4,137,847,745 = 8,275,694,030. Model the loud-mismatch message on `assert_merge_parity`'s style (name the arms/records and values).

**Disk budget:** round 0 runs the FULL check via `check_disk_floor(dir, floor_gb, phase=..., override=...)` (`bench.py:1343-1368`) with the controller-computed session budget passed explicitly (D-12); per-rep light re-checks use `ensure_disk_headroom` (`bench.py:1371-1381`).

---

### 3. STAGE parity — three-way gate (parity utility, streaming file I/O)

**Leg 1 (aggregate conservation) analog:** `bench.py:1420-1478` `assert_merge_parity` — import as-is; feed it arm dicts from the stats readers ONLY:

```python
# Source: scripts/bench/bench.py:1429-1439 (docstring core)
#   - rustkmer-merge Total == jellyfish-merge Total
#     == count-A Total + count-B Total
#   - rustkmer-merge Distinct == jellyfish-merge Distinct
#   - merged Distinct >= max input Distinct
# Every Total read here is the SUM-OF-COUNTS definition carried on the arm
# dicts by the protocol's stats readers (stats() / jellyfish_stats() ->
# unique_kmers/total_kmers) — NEVER the DatabaseHeader record-count field
# (the IN-03 collision...). Aggregate conservation alone cannot prove parity
# ... the per-k-mer dump-vs-dump leg is the verdict gate.
```

**Legs 2-3 (deep per-k-mer) analog:** the ONLY full-scale route is the streaming form — `merge_characterize.py:193-322`. WR-01 (locked): never `bench.dump_vs_dump_equal` / `normalize_dump_lines` at full scale.

Fail-loud awk normalizer (`merge_characterize.py:193-212`):

```python
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
```

One dump side — dump → normalize → LC_ALL=C external sort, with `finally`-unlink of raw/norm (`merge_characterize.py:231-275`):

```python
def _normalized_sorted_dump(dump_cmd_builder, workdir, stem, side_label,
                            via_stdout=True):
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
        # ... wc -l guard: lines <= 0 -> RuntimeError (empty dump never passes)
        return sorted_path, lines
    finally:
        for leftover in (raw, norm):
            try: leftover.unlink()
            except OSError: pass
```

The streaming compare — first difference named, length equality required (`merge_characterize.py:299-316`):

```python
with open(rk_sorted, ...) as fa, open(jf_sorted, ...) as fb:
    compared = 0
    for la, lb in zip(fa, fb):
        if la != lb:
            raise RuntimeError(f"dump-vs-dump gate: dumps differ at sorted "
                f"line {compared}: rustkmer={la!r} vs jellyfish={lb!r} ...")
        compared += 1
    if compared != rk_lines or compared != jf_lines:
        raise RuntimeError("... dumps differ in length ...")
return True
```

**Leg-2 recount diff (NEW — no complete analog):** reuse the same pipeline with TWO `.rkdb` sides (`via_stdout=False` for both, dump argv `[rustkmer, "dump", <rkdb>, "-o", <raw>]`):
1. Recount: `rustkmer count -k K -C --threads <N> -o recount.rkdb -i part_001 part_006` — built via `bench.rustkmer_count_cmd` with `BenchmarkConfig(inputs=[part_001, part_006])` (both parts as ONE input list — `bench.py:299-303` shows `-i` takes the multi-input list).
2. `_normalized_sorted_dump` on `recount.rkdb` and on the rustkmer merged `.rkdb`.
3. Streaming zip-compare identical to the loop above.
Budget the transients (raw+norm coexist ≈ 2x dump text per side; sort `-T workdir` on the same APFS volume) and sequence deletions (recount `.rkdb` deleted after its sorted dump exists; k21 parity before k31).

**Merge execution in the parity stage** (one merge per tool, both k): `build_merge_cmd(rustkmer, merged_rkdb, [part_001.rkdb, part_006.rkdb])` and `jellyfish_merge_cmd(merged_jf, [part_001.jf, part_006.jf])` — both builders already exist:

```python
# Source: scripts/bench/bench.py:346-350 (defaults-only by construction)
def build_merge_cmd(rustkmer, out_db, input_dbs, num_threads=None):
    argv = [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]
    if num_threads is not None:
        argv += ["--num-threads", str(num_threads)]
    return argv

# Source: scripts/bench/bench.py:353-361
def jellyfish_merge_cmd(out_jf, input_jfs):
    # Defaults only — SUM semantics; -m/-M/-j/-t/-s are NOT passed because in
    # merge -m is MIN mode ... flag strings are never copied between subcommands.
    out_v = validate_path(out_jf)
    inputs = [validate_path(p) for p in input_jfs]
    return ["jellyfish", "merge", "-o", out_v, *inputs]
```

---

### 4. STAGE timed — merge-only counterbalanced protocol (controller stage, subprocess measurement)

**Arm ordering analog:** `output_stage.py:121-137` `rotation_schedule` — pure, unit-testable; do not hand-roll ordering:

```python
def rotation_schedule(arm_names, reps):
    """Pure counterbalanced round-robin schedule (unit-testable, no I/O).

    Round r (0-based) starts at arm index r mod len(arm_names); every round
    contains every arm exactly once. ...
    """
    names = list(arm_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one arm name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]
```

Arms: `("merge", "merge-t1", "jellyfish-merge")` × 3 reps. The t1 arm is `build_merge_cmd(..., num_threads=1)`; merge and jellyfish-merge take defaults only.

**Per-rep loop precedent:** `phase10.py:346-452` `run_rounds` — copy its structure (warmups per TOOL before round 0; schedule iteration; per-rep honest cache_state + round + arm_order recorded; injectable `measure_fn`/`purge_fn`/`sleep_fn` seams defaulting to module primitives at CALL time). For Phase 12 the measured-run seam is `merge_characterize.measured_run` (NOT `bench.measure`) because stderr must survive for route attribution:

```python
# Source: scripts/bench/merge_characterize.py:146-178
def measured_run(argv):
    """Run argv under /usr/bin/time with bench.measure's semantics, keeping
    stderr for route attribution. ...
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
    if ROUTE_MARKER_RE.search(stderr_text or ""):
        return "prefix-cache"
    return "not-reported"      # silence is recorded, never guessed from flags
```

Per-rep mechanics (reuse, in this order — `merge_characterize.py:561-594` `run_rung`'s merge loop is the live-proven sequence):

```python
cache_state = attempt_cache_purge()                    # honest label (bench.py:1300-1316)
ensure_disk_headroom(disk_dir, floor_gb, phase=f"rep round {rnd}",
                     override=disk_override)           # D-12, exit 3 on breach
rep, stderr = measured_run(argv)                       # /usr/bin/time; keeps stderr
route = route_from_stderr(stderr)
```

**Reduction:** `bench.reduce_arm` (`bench.py:1319-1340`) — medians + CV%, CV > 10.0 (`CV_WARNING_THRESHOLD_PCT`) sets `cv_warning` without failing.

Count arms do NOT re-run: the prepared artifacts ARE the validated count outputs (research Pattern 3; re-counting breaks the parity-validated premise).

---

### 5. STAGE verdict — pure comparison of recorded medians (controller stage, transform)

**Analog:** `phase10.py:771-832` `verdict_block` + `verdict_line` — pure function over recorded docs, the rule stated verbatim IN the verdict doc, both outcomes valid, t1 excluded from YES/NO:

```python
# Source: scripts/bench/phase10.py:805-820 (the return shape)
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

# Source: scripts/bench/phase10.py:823-832 — the one machine-greppable line
def verdict_line(verdict):
    """repr() round-trips the floats."""
    return (
        f"PHASE10 VERDICT k={verdict['k']} result={verdict['result']} "
        f"rustkmer={verdict['rustkmer_result']} "
        f"rustkmer_wall_s={verdict['rustkmer_wall_s']!r} ...")
```

Phase 12 shape: verdict per k from `merge` vs `jellyfish-merge` medians (match-or-beat `<=`, no tolerance band), overall YES only if both k; `merge-t1` recorded under `scaling`, never in YES/NO; greppable line `PHASE11 VERDICT k=… result=… rustkmer_wall_s=…`. Exit polarity (A1): exit 0 = NO-INVEST / exit 1 = INVEST — confirm wording at plan review (Open Question 1 in 12-RESEARCH.md).

---

### 6. STAGE render — mechanical report + byte-identical re-render proof (renderer, transform)

**Contract analog (T-04-07, verbatim statement)** (`bench.py:1971-1979`):

```python
# --- 04-04 mechanical report renderer ------------------------------------------
# Contract (threat T-04-07): every MEASUREMENT number in the rendered report
# is read from the results JSONs — the code below carries no measurement
# literals and consults no clock, so a re-render is byte-identical and a
# hand-edited number is detectable. The only external input is the harness
# provenance line, which uses the LAST COMMIT THAT TOUCHED bench.py (stable
# across re-renders even as the repo moves forward — unlike HEAD).
```

Deterministic provenance helper (`bench.py:1983-1999` `harness_source_commit`) — `git log -1 --format=%H -- <renderer file>`; returns "unknown" outside a checkout; the phase10 variant exists at `phase10.py:1398+` (renderer_source_commit). The phase11 renderer should hash ITS OWN file.

**Publish + verdict emission analog:** `phase10.py:1677-1739` `run_render` — build both artifacts IN MEMORY, `publish_atomic`, print verdict lines, map overall to exit code; a failure NEVER unlinks destinations:

```python
# Source: scripts/bench/phase10.py:1722-1739 (core)
    validate_provenance(verdict_doc)
    report_text = render_report_text(docs)
    publish_atomic([
        (verdict_path, json.dumps(verdict_doc, indent=2) + "\n"),
        (out_path, report_text),
    ])
except SystemExit:
    raise
except Exception as exc:  # noqa: BLE001 — invalid publish, never a verdict
    # `publish_atomic` already restored any pre-existing artifact; ...
    # Never unlink here: that would destroy a previously published verdict/report.
    print(f"phase10.py: {exc}", file=sys.stderr)
    return EXIT_INVALID
for block in verdicts:
    print(verdict_line(block))
print(f"PHASE10 VERDICT overall={overall}")
return EXIT_OK if overall == "YES" else EXIT_NO
```

**Atomic multi-artifact publish** (`phase10.py:1613-1667` `publish_atomic`) — sibling temps + `os.replace`, pre-existing destinations backed up and restored on ANY failure, duplicate destinations rejected up front. Import from `phase10` or replicate verbatim.

**Re-render proof mechanics:** render → sha256 → re-render → sha256 → byte equality, recorded in `12-RENDER-PROOF.json`. The unit-test template is `test_phase10_verdict.py:824-828`:

```python
def test_re_render_is_byte_identical(self):
    docs = self.full_docs()
    first = self.render(docs, "a.md")
    second = self.render(docs, "b.md")
    self.assertEqual(first, second)
```

**Merge-verdict sections to add (MBENCH-04)** — extend, do not repurpose, the existing row machinery. `_arm_row` (`bench.py:2037-2069`) keeps its merge `n/a` special case byte-compatible for committed pre-Phase-11 files — a new phase11 renderer adds its own rows rather than editing that one:

```python
# Source: scripts/bench/bench.py:2046-2052 (the load-bearing special case)
    wall, rss = arm["median_wall_s"], arm["median_peak_rss_bytes"]
    if arm["name"] == "merge":
        if merge_base is None:
            # No jellyfish counterpart exists for the merge operation — a
            # delta against the jellyfish COUNT arm would be semantically
            # void.
            d_wall = d_rss = "n/a"
```

New sections and their sources:
- Per-arm methodology rows (threads/flags/merge-route/sha256) — from recorded arm dicts + `binary_provenance` blocks.
- Asymmetry sentence — pre-agreed wording from milestone Pitfall 3 / `.planning/research/SUMMARY.md`: "each tool merges its own representation of identical, parity-validated input data".
- Entry-rate (entries/s) and byte-rate (output bytes/s or B/entry) per arm — computed from recorded `output_bytes` / medians; make the `.jf` 10/12 vs `.rkdb` 20 B/entry asymmetry visible (ladder precedent: `merge_characterize.py:730-740` bytes_per_entry block).
- Predicted-vs-measured table — read `summary.slopes` / `summary.extrapolated_full_scale` (rustkmer 53.8/73.4 s; jellyfish 77.3/105.5 s) from `11-LADDER-RESULTS.json` and carry `summary.extrapolated_full_scale.caveat` VERBATIM (defined at `merge_characterize.py:126-130` `FULL_SCALE_CAVEAT`).
- RSS-is-context framing (milestone Pitfall 6) — no memory-win claims; merge-t1 labeled with the pool contract (t1 = 2-OS-thread pool; `scripts/bench/README.md:466-471` wording).

**WR-02 opportunistic same-touch target** (only if bench.py's renderer is extended — `bench.py:2527-2531` + `2556-2561`): `--render-report` currently falls through to the historical `--out` default (`DEFAULT_SCRATCH / "results.json"`) and clobbers it. Fix = require explicit `--out` under `--render-report` (a `parser.error` branch alongside `2556-2560`).

---

### 7. Stage evidence JSONs (evidence documents, file I/O)

**Two proven writer patterns — pick per document kind:**

Results-schema documents (schema v1, `arms`/`reps`/`medians`) — `phase10.py:837-881`:

```python
# Source: scripts/bench/phase10.py:845-869 (shape) + 872-881 (validate-then-write)
doc = {
    "schema_version": SCHEMA_VERSION,
    "mode": mode, "phase": PHASE, "session": session,
    "params": params,
    "platform": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine(),
                 "python": platform.python_version()},
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

def write_doc(doc, out_path):
    """Validate schema AND provenance, then write — invalid docs never land."""
    validate_schema(doc)
    validate_provenance(doc)
    ...
```

Non-results evidence documents (own `kind`, MBENCH-05 boundary — never fork a second results schema) — `merge_characterize.py:796-847`:

```python
def new_doc():
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,                      # e.g. "merge-characterization-ladder"
        "rungs": [], "summary": {},
        "scratch_cleaned": False,
        "created": _now_iso(),
    }

def load_doc(path):
    """... Raises ValueError on a kind/schema mismatch — never merge across kinds."""
    if doc.get("kind") != KIND:
        raise ValueError(
            f"{path} is not a {KIND!r} document (kind="
            f"{doc.get('kind')!r}) — refusing to merge across kinds")

def write_doc(path, doc):
    """Write the evidence JSON (indent=2, sort_keys, trailing newline)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
```

The non-results variant that still requires provenance is `phase10.write_evidence_doc` (`phase10.py:897-910`): "no artifact may reach disk without complete provenance (T-10-06)".

Schema gate (`bench.py:502-532` `validate_schema`) tolerates extra keys; A6 in 12-RESEARCH.md recommends reusing it via `assemble_doc` for timed-stage docs, falling back to a dedicated `kind` (like the ladder's) only if a required field genuinely doesn't fit.

Provenance blocks: `bench.binary_provenance(executable, build_profile)` + `bench.validate_provenance(doc)` — path-without-hash is not provenance (T-05-02). Build profile strings in use: `"release"` for rustkmer, `"pinned-comparator-2.3.1"` for jellyfish (`merge_characterize.py:542-546`).

---

### 8. `scripts/bench/tests/test_phase11_verdict.py` (test, in-memory)

**Analog:** `scripts/bench/tests/test_phase10_verdict.py` — copy its skeleton: stdlib unittest only, hand-built constants, no binaries invoked, injected seams.

**Header + path fixup + imports** (`test_phase10_verdict.py:1-17, 35-41`):

```python
"""Unit suite for the Phase-10 verdict controller (scripts/bench/phase10.py).

Hand-built constants, no filesystem beyond tempdir, no binaries invoked: the
controller's measured-round seams (`measure_fn`, `purge_fn`, `sleep_fn`) and
the interpreter query are injected, so this suite proves the arm/rotation/
verdict/document contract without a real `/usr/bin/time` run.
...
Stdlib unittest only — no pytest.
"""

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.bench import phase10 as p10
from scripts.bench.bench import validate_provenance
```

(Phase 12's run command is pytest-invoked — `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` — but the file itself stays stdlib-unittest, matching the suite.)

**Fixture builders** (`test_phase10_verdict.py:47-158`) — provenance-clean fake, rep/arm/doc factories with tunable walls:

```python
def fake_provenance():
    """A structurally valid provenance block (validate_provenance-clean)."""
    return {"binary": {"path": "/repo/target/release/rustkmer",
                       "size_bytes": 1234, "sha256": "a" * 64},
            "git_commit": "b" * 40, "git_dirty": False,
            "build_profile": "release", ...}

def make_rep(wall=1.0, peak_rss=1000, peak_bytes=None, cache_state="unavailable",
             round_index=0, arm_order=0): ...

def make_arm(name, tool, threads, wall, peak=1000, reps=None, unique=100,
             total=200): ...

def make_doc(arms, k=21, session="cli", mode="full"): ...
```

**Test class conventions** (`test_phase10_verdict.py:792-828`): one class per renderer/stage concern; `setUp` mkdtemp + addCleanup rmtree; literal-text assertions for mandatory report statements; render-twice byte equality; `assertRaises(ValueError)` for invalid documents ("an invalid document never reaches disk").

**Wave 0 coverage per 12-RESEARCH.md test map:** stage isolation + exit codes (infra → 2); round-0 gate (revalidate drift → loud failure; anchor equality from manifest records); schedule shape over `rotation_schedule` (3 arms × 3 reps, rotated starts); Leg-2 recount GREEN/RED on small synthetic dump fixtures through the streaming pipeline; renderer no-measurement-literals, entry-rate/byte-rate formulas, asymmetry sentence present, predicted-vs-measured caveat carried; byte-identity re-render on fixture JSONs.

---

### 9. `scripts/bench/bench.py` (MODIFY — WR-02 same-touch ONLY, opportunistic)

No other bench.py change is in scope. The fix site: `bench.py:2527-2531` keeps a historical `--out` default (`DEFAULT_SCRATCH / "results.json"`); `bench.py:2556-2560` dispatches `--render-report` to `render_report(args.results, args.out)` — without an explicit `--out` this overwrites the default results path. Fix shape: a `parser.error("--render-report requires an explicit --out ...")` branch next to the existing `--results` requirement at `2557-2559`. Keep the diff minimal and test-covered (HYG-04-style same-touch rule).

---

### 10. `docs/benchmark-report.md` (REWRITE — D-04 wrap-up, documentation)

**Analog:** the file itself (132 lines). Rewrite rules locked by D-04 + research Pitfall 11:
- Source of EVERY number: the rendered `12-MERGE-REPORT.md` (itself rendered from committed JSONs). Prose numbers the renderer can't reproduce are forbidden.
- Remove the hand-added superseded banner (current lines 1-16 — the HYG-01/D-05 exception block) and the v1.0 dataset section (lines 22-24, CRR2044018 substitute-dataset prose).
- Keep the generated-file contract framing: current line 20 (mechanically rendered, no measurement literals, byte-for-byte re-render) and the footer regeneration note (line 132) as the model for the new footer pointing at the Phase-12 evidence JSONs.
- Carry over the section skeleton that survives: dataset provenance (updated to CRR1936095 + the merge-inputs lifecycle incl. D-03 deletion + rebuild path), headline tables per k, verdict statements with the rule verbatim, parity evidence lines, methodology blocks (threads/flags/merge-route/sha256 per arm; t1 pool contract), input fingerprints, harness provenance.
- v2.0 verdict reference numbers for context: 144.69/147.08 s walls, 43.97/68.52 GiB MEM (`.planning/PROJECT.md`).

---

## Shared Patterns

### Exit-code contract (0/1/2 verdict carrier + 3 disk block)
**Source:** `phase10.py:97-99, 2613-2622`; `bench.py:63`
**Apply to:** all `phase11.py` stages and the top-level handler.
0 = measured YES (NO-INVEST per A1), 1 = measured NO/INVEST (artifacts published), 2 = invalid/infra (no artifact written), 3 = disk-floor block (from `check_disk_floor`/`ensure_disk_headroom`). Never map infra failures to 1; never retry around a verdict exit.

### Stdlib-only harness + script-path fixup
**Source:** `bench.py:25-26` (contract statement), `merge_characterize.py:48-49`, fixup at `phase10.py:59-63`
**Apply to:** every new/modified Python file. No third-party imports, no pip installs; `sys.path.insert(0, repo_root)` before `from scripts.bench...` imports when run as a script.

### List-form argv + path screening (command injection defense)
**Source:** `bench.py:277-289` (`validate_path`), `bench.py:346-361` (merge builders)
**Apply to:** every subprocess invocation in the controller. No `shell=True` anywhere in merge paths; all argv paths through the builders (which already call `validate_path`).

### /usr/bin/time is the only clock
**Source:** `merge_characterize.py:146-167` (`measured_run`), `bench.py:161` (`parse_time_output`)
**Apply to:** parity merges, timed reps, recount leg (uncounted runs may use `prepare_inputs.run_command`). Harness-internal clocks are banned; stderr kept for `route_from_stderr`.

### Honest cache_state labels
**Source:** `bench.py:1288-1316` (`cache_state_from`, `attempt_cache_purge`)
**Apply to:** every measured rep. `purged`/`unavailable`/`runner-fresh` — never assume cold cache; sudo-purge failure records `unavailable` and never blocks.

### Disk guards: full budget at round 0, per-rep light re-check
**Source:** `bench.py:1343-1368` (`check_disk_floor`, exit 3, stated shortfall, `--disk-floor-override` semantics), `bench.py:1371-1381` (`ensure_disk_headroom`)
**Apply to:** revalidate stage (full, computed budget passed explicitly per D-12) and every measured rep (D-12). Floor constant: `DEFAULT_DISK_FLOOR_GB = 136`, import-time tripwire-pinned to `derive_disk_floor` (`bench.py:109-119`) — never hand-edit past the formula.

### Parity before timing; deep legs streamed only
**Source:** `bench.py:1420-1478` (`assert_merge_parity`), `merge_characterize.py:193-322` (streaming gate), WR-01 hazard at `bench.py:1857-1859` (in-process gate wired after ALL reps — the OOM path)
**Apply to:** controller stage ORDER is the structural fix — revalidate → parity → timed → verdict → render; parity evidence persisted per stage before the next stage starts. NEVER invoke `bench.py run_bench` / `--mode full` for this session; NEVER import `normalize_dump_lines` into a full-scale path (unit-level only, ~120-150 GB heap at the 10% rung per `merge_characterize.py:181-191`).

### total_kmers definition discipline (IN-03)
**Source:** `bench.py:1432-1439` (assert_merge_parity docstring)
**Apply to:** every conservation check and report line: read ONLY `stats()` → `unique_kmers`/`total_kmers` and `jellyfish_stats()` → `distinct`/`total` (sum-of-counts); NEVER `DatabaseHeader.total_kmers` (record count). Every check names its definition.

### Provenance on every artifact
**Source:** `bench.py:425+` (`binary_provenance`), `bench.py:458+` (`validate_provenance`), `phase10.py:872-910` (validate-then-write)
**Apply to:** every evidence document before it lands. sha256 + commit + build profile + command line; fingerprints come from `fingerprint()`/`revalidate_stage`, never hand-transcribed.

### Mechanical renderer + atomic publish
**Source:** `bench.py:1971-1979` (T-04-07 contract), `phase10.py:1613-1667` (`publish_atomic`), `phase10.py:1677-1739` (`run_render`)
**Apply to:** render stage. No measurement literals, no clock reads, provenance line = last commit touching the renderer file; build in memory → publish_atomic → print verdict lines → exit code; failures never unlink destinations.

### Binary identity: rustkmer sha256 must stay `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`
**Source:** `11-LADDER-RESULTS.json` provenance; re-verified 2026-11-17
**Apply to:** all stages. A rebuild changes the hash and breaks predicted-vs-measured attribution — escalate, don't silently rebuild. jellyfish stays 2.3.1 pinned (never upgraded mid-milestone).

---

## No Analog Found

| File / Concern | Role | Data Flow | Reason | Planner Guidance |
|------|------|-----------|--------|------------------|
| Leg-2 independent-recount diff (in `phase11.py`) | parity gate | streaming file I/O | No harness code counts both parts as ONE input list and per-k-mer diffs the recount against the merged db (PARITY-GATE.md §8 maps only Legs 1 and 3) | Assemble from exact building blocks: `bench.rustkmer_count_cmd` with a 2-input `BenchmarkConfig` (bench.py:292-304), `_normalized_sorted_dump` twice with `via_stdout=False` (merge_characterize.py:231-275), streaming zip-compare loop (merge_characterize.py:299-316). Wave-0 GREEN/RED fixtures required. |
| D-03 artifact deletion | plan task (not code) | file deletion | A sequencing task: rm the 8 artifacts under `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (~86.74 GiB) STRICTLY after report + results JSONs + exit-code record are committed | Precedent for scripted cleanup: `merge_characterize.cleanup_scratch` (merge_characterize.py:850-860). Rebuild escape hatch: `prepare_inputs.py build` (~30-90 min). |

---

## Anti-Pattern Summary (binding, from 12-RESEARCH.md — planner should encode these as plan constraints)

1. **Never** run `bench.py --mode full` / `run_bench` for the session (re-counts fresh inputs + in-process deep gate after all reps — WR-01 OOM path, hours lost).
2. **Never** in-process dump normalization (`normalize_dump_lines` + `sorted()`) at full scale — unit-level only.
3. **Never** aggregate-only parity — per-k-mer dump identity is the verdict gate (canonicality mixing conserves totals).
4. **Never** read `DatabaseHeader.total_kmers` for conservation — stats readers only, definition named per check.
5. **No** memory-win framing — jellyfish merge is streaming (~6.8 MB RSS); RSS is context, never a decision axis; t1 never enters YES/NO and is labeled with the pool contract.
6. **No** hand-written numbers or hand-transcribed fingerprints in report/evidence — renderer reads recorded JSONs; fingerprints from `fingerprint()`/`revalidate_stage`.
7. **No** new results-schema fork — reuse schema v1 via `assemble_doc`/`validate_schema` or a dedicated `kind` document (MBENCH-05).
8. **No** deviating from defaults-only flags during measurement; no `-s` on any merge arm (jellyfish merge `-m` is MIN mode — flag strings never copied between subcommands).
9. **No** deviating from the ladder's caveat — predicted-vs-measured deviations are FINDINGS recorded with `FULL_SCALE_CAVEAT` verbatim, never smoothed or re-run-until-green.

## Metadata

**Analog search scope:** `scripts/bench/` (bench.py, phase10.py, merge_characterize.py, prepare_inputs.py, output_stage.py, tests/), `docs/`, `.planning/phases/11-merge-characterization-harness-prep/` (evidence shapes)
**Files scanned:** 10 analog candidates, all verified git-tracked (`git ls-files`); 7 read in depth
**Pattern extraction date:** 2026-11-17
**All excerpts verified against working tree at commit 0fe14a9 (branch dev).**
