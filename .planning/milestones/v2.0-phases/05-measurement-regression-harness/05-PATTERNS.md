# Phase 5: Measurement & Regression Harness - Pattern Map

**Mapped:** 2026-11-12
**Files analyzed:** 23 proposed new/modified files (exact new names remain Claude's discretion under CONTEXT)
**Analogs found:** 23 / 23, including composite analogs where no single file provides the whole capability
**Scope guard:** harness, tests, evidence, and CI only. Do not modify `src/cli/commands/count.rs`, `src/hash/table.rs`, `pyo3/src/counter.rs`, or the `.rkdb` writer in this phase.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/bench/random_slice.py` (new) | utility | streaming file-I/O, deterministic batch transform | `scripts/bench/gen_synthetic.py` + `bench.py::extract_slice` | composite exact-role |
| `scripts/bench/bench.py` (modify) | benchmark service | subprocess batch, file-I/O, request-response | itself; `.planning/research/profiling/run_matrix.py` | exact |
| `scripts/bench/thread_scaling.py` (new) | benchmark service / gate | subprocess batch, transform | `run_matrix.py` + `compare.py` | composite exact-role |
| `.planning/research/profiling/verify_threads.py` (modify) | process-inspection utility | live process request-response | itself | exact |
| `tests/thread_pool_size_tests.rs` (new) | integration test | subprocess request-response | `tests/merge_frontend_validation_tests.rs` + `verify_threads.py` | composite exact-role |
| `.planning/research/profiling/microbench_main.rs` (modify) | microbenchmark | in-memory batch transform | itself + `tests/parallel_count_tests.rs` | exact |
| `.planning/research/profiling/microbench_Cargo.toml` (modify) | config | build | itself | exact |
| `scripts/bench/python_bench.py` (new) | benchmark service / worker | subprocess batch, PyO3 file-I/O | `bench.py::measure` + `pyo3/tests/test_counter.py` | composite exact-role |
| `scripts/bench/n_read_differential.py` (new) | differential utility | CLI/PyO3 batch transform | `pyo3/tests/test_counter.py` + `test_export.py` | composite exact-role |
| `scripts/bench/tests/test_degradation.py` (modify) | unit test | temporary file-I/O | itself + `test_generator.py` | exact |
| `scripts/bench/tests/test_schema.py` (modify) | unit test | JSON request-response | itself | exact |
| `scripts/bench/tests/test_thread_scaling.py` (new) | unit test | JSON transform, exit-code contract | `scripts/bench/tests/test_compare.py` | exact-role |
| `scripts/bench/tests/test_python_bench.py` (new) | unit/integration test | subprocess request-response | `test_schema.py` + `test_generator.py` | role-match |
| `scripts/bench/tests/test_n_read_differential.py` (new) | unit test | deterministic transform | `test_compare.py` + `pyo3/tests/test_counter.py` | role-match |
| `scripts/bench/baselines/slice_parity.crr1936095.json` (new) | versioned reference config | batch evidence | `.planning/research/profiling/parity_report.json` | exact-role |
| `scripts/bench/baselines/python_bench_baseline.darwin.json` (new) | platform baseline config | batch evidence | `baselines/bench_baseline.darwin.json` | exact |
| `scripts/bench/baselines/python_bench_baseline.linux.json` (new) | platform baseline config | batch evidence | `baselines/bench_baseline.linux.json` | exact |
| `.planning/phases/05-measurement-regression-harness/contention_evidence.json` (new) | evidence artifact | batch measurements | `.planning/research/profiling/evidence.json` | exact-role |
| `.planning/phases/05-measurement-regression-harness/n_read_differential.json` (new) | evidence artifact | batch differential | `parity_report.json` + `evidence.json` | composite exact-role |
| `.planning/phases/05-measurement-regression-harness/golden_capture.json` (new) | evidence artifact | file-I/O, immutable capture | `tests/fixtures/golden_manifest.sha256` + `evidence.json` | composite exact-role |
| `scripts/bench/README.md` (modify) | maintainer config/docs | batch procedures | itself | exact |
| `.github/workflows/benchmark.yml` (modify) | CI config | event-driven batch | itself | exact |
| `.github/workflows/ci.yml` (modify) | CI config | event-driven build/test | itself | exact |

**Not modified:** `scripts/bench/compare.py` remains the general wall/RSS comparator; `tests/golden_generate.rs`, the committed golden `.rkdb` files, and `tests/fixtures/golden_manifest.sha256` remain immutable pre-refactor inputs. `tests/golden_sha256_tests.rs` can be run as-is; no golden regeneration is part of this phase.

## Pattern Assignments

### `scripts/bench/random_slice.py` (new; utility, deterministic streaming file-I/O)

**Analogs:** `scripts/bench/gen_synthetic.py` and `scripts/bench/bench.py`.

Copy the explicit seeded-RNG discipline (generator lines 52-54):

```python
# Seed BEFORE any sequence generation — the determinism contract.
random.seed(args.seed)
generate_fastq(args.reads, args.length, args.out)
```

Copy the streaming producer cleanup and empty-input failure from `bench.py` lines 417-439, but replace first-N truncation with record-oriented random selection:

```python
proc = subprocess.Popen(["gunzip", "-c", str(gz_path)],
                        stdout=subprocess.PIPE)
try:
    with open(output_path, "wb") as out:
        for line in proc.stdout:
            out.write(line)
finally:
    proc.stdout.close()
    if truncated:
        proc.terminate()
    proc.wait()
if written == 0:
    raise RuntimeError(f"slice of {gz_path} produced 0 lines")
```

Required adaptation: treat four lines as one FASTQ record, use a fixed `--seed`, record source fingerprint/seed/requested count/actual count/selected source indices, and never call `head`. Reservoir sampling gives a single-pass uniform random-record subslice without loading the human dataset. Keep the existing `make_slice.sh` first-N behavior unchanged for backward compatibility; the new tool owns random-record selection.

---

### `scripts/bench/bench.py` (modify; benchmark service, subprocess batch)

**Analog:** itself, supplemented by `run_matrix.py`.

Reuse `measure` unchanged for all new outer-process timing (lines 137-150):

```python
plat = sys.platform
time_flag = "-l" if plat == "darwin" else "-v"
proc = subprocess.run(["/usr/bin/time", time_flag, *argv],
                      capture_output=True, text=True)
if proc.returncode != 0:
    raise RuntimeError(
        f"measured command failed rc={proc.returncode}: {argv}\n"
        f"trailing stderr:\n{proc.stderr[-500:]}")
return parse_time_output(proc.stderr, plat)
```

Generalize `fingerprint` (lines 268-276) for binary/module provenance, not only inputs:

```python
def fingerprint(path):
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"path": str(p), "size_bytes": p.stat().st_size,
            "sha256": h.hexdigest()}
```

Add one shared provenance builder used by slice, scaling, Python, contention, N-differential, and golden-capture artifacts. Required fields: resolved executable/module path, its `sha256`, `git rev-parse HEAD`, `git status --porcelain` dirty flag, build profile (`release` or `release+debug-assertions` as applicable), Rust toolchain, Python version for Python artifacts, and platform. Use the existing subprocess error handling in `harness_source_commit` (lines 977-993), but capture **HEAD**, not the last commit that touched `bench.py`.

Preserve the result emission shape at lines 928-946 and add provenance rather than creating an unrelated report format:

```python
results = {
    "schema_version": SCHEMA_VERSION,
    "mode": mode,
    "resolved_inputs": [str(p) for p in resolved_inputs],
    "input_fingerprint": [fingerprint(p) for p in inputs],
    "platform": { ... },
    "created": datetime.now(timezone.utc).isoformat(),
    "params": params,
    "arms": arms,
}
validate_schema(results)
with open(out_path, "w") as fh:
    json.dump(results, fh, indent=2)
    fh.write("\n")
```

Parity must remain a hard pre-timing gate. Copy the equality/zero-count logic at lines 581-594 and the measured-input check at lines 851-864. For the pinned profiling slice, assert Distinct `229694874` and Total `519271168`; for each new random subslice, derive that subslice's Jellyfish reference and persist its selection manifest. Do not apply the 4M head-slice constants to a different random sample.

**Schema compatibility warning:** `SCHEMA_VERSION = 1` and `validate_schema` are shared with `compare.py` and all committed v1 baselines. Do not casually bump the global version or make old baseline files invalid. Add a separate strict validator for new provenance-bearing artifacts, or a deliberate backward-compatible schema migration with legacy-baseline tests.

---

### `scripts/bench/thread_scaling.py` (new; benchmark service/gate, batch)

**Analogs:** `.planning/research/profiling/run_matrix.py`, `scripts/bench/bench.py`, and `compare.py`.

Copy the explicit t1/t4/t8/t16 arm construction from `run_matrix.py` lines 118-128, replacing hard-coded host paths with CLI arguments and adding the required t16 arm:

```python
rk("rk21-fq-t1", 21, FQ, 1)
rk("rk21-fq-t4", 21, FQ, 4)
rk("rk21-fq-t8", 21, FQ, 8)
rk("rk21-gz-t1", 21, GZ, 1)
```

Derive each command through `BenchmarkConfig` / `rustkmer_count_cmd` (`bench.py` lines 167-183 and 201-213) so k, canonical mode, input, and output protocol cannot drift. Give every arm its own output path. Run parity/count-map equality before accepting timing, then use `measure`, per-rep `cache_state`, cooldown, `reduce_arm`, and medians from `bench.py` lines 629-681 and 701-768.

Copy comparator exit semantics from `compare.py` lines 57-59:

```python
EXIT_WITHIN = 0
EXIT_REGRESSION = 1
EXIT_INVALID = 2
```

The scaling gate owns its verdict just as `compare.py` does: 0 only when t1/t4/t16 differ by the chosen material-scaling rule, 1 for a measured no-op/regression, 2 for malformed/missing provenance or parity inputs. Persist raw per-arm reps and derived speedups, not only a PASS/FAIL string. The current tree is expected to produce RED; do not soften the workflow exit code.

---

### `.planning/research/profiling/verify_threads.py` (modify; process inspection)

**Analog:** itself.

Retain the live subprocess + OS observation mechanism at lines 17-35:

```python
p = subprocess.Popen(
    [RK, "count", "-k", "21", "-C", "--threads", str(n), "-i", SMALL, "-o", out],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
s = subprocess.run(["sample", str(p.pid), "1"], capture_output=True, text=True)
threads = len(re.findall(r"^\s*\d+ Thread_", txt, re.M))
print(f"--threads {n}: OS threads observed = {threads} (expected ~{n + 1} incl. main)")
p.wait()
```

Required hardening for a standing gate:

- Replace absolute `RK`, `SMALL`, and `/tmp` constants with required CLI arguments.
- Return structured records containing requested threads, observed threads, PID, platform, sampler, return code, and provenance; do not rely on parsing the prose line.
- Poll for the counting phase instead of a fixed four-second sleep; fail loudly if the process exits before observation.
- Use `try/finally` to terminate/reap the child on sampler or assertion failure.
- Keep macOS `sample`, and add Linux `/proc/<pid>/task` or `ps -L` observation for CI. Unsupported platforms are invalid/skip-by-explicit-platform-gate, never a false PASS.
- Preserve independent processes for N=1, 4, and 16 because rayon global initialization is once per process.

---

### `tests/thread_pool_size_tests.rs` (new; Rust integration test, subprocess)

**Analogs:** `tests/merge_frontend_validation_tests.rs` and `tests/parallel_count_tests.rs`.

Use Cargo's real CLI binary path and `Command`, as in `merge_frontend_validation_tests.rs` lines 199 and 221-235:

```rust
let bin = env!("CARGO_BIN_EXE_rustkmer");
let status = Command::new(bin)
    .args(["merge", "-i", as_str(&a), as_str(&b), "-o", as_str(&out_plain), "-q"])
    .status()
    .expect("the rustkmer binary must launch");
assert!(status.success(), "plain route must exit 0, got {status}");
```

Adapt the args to `count -k 21 -C --threads N -i <fixture> -o <temp.rkdb>`, and drive the machine-readable `verify_threads.py` helper with `std::process::Command`. Use `tempfile::tempdir()` and assert both child success and observed pool size.

Do **not** try to build multiple global rayon pools in one test process. The existing differential states the controlling constraint at `parallel_count_tests.rs` lines 139-145:

```rust
// `build_global` is one-call-per-process (rayon returns Err on a second
// `ThreadPoolBuilder::build_global`), so we cannot drive the 1-vs-N
// parallelism through `execute_count` in a single test process.
```

Also do not treat `test_thread_resolution` (lines 400-443) or 1-vs-N count equality as sufficient: those test the pure precedence helper and count commutativity, not the actual pool. The new test is intentionally observably RED on the current tree (`--threads 1` observes 17 OS threads on the profiling host).

---

### `.planning/research/profiling/microbench_main.rs` (modify; contention microbenchmark)

**Analogs:** itself, `src/hash/table.rs`, and `tests/parallel_count_tests.rs`.

Keep the same pre-encoded-key increment-only control at lines 147-164:

```rust
let mut keys: Vec<u64> = Vec::with_capacity(windows);
for seq in &reads {
    rolling_canonical(seq, k, |x| keys.push(x));
}
let c = KmerCounter::new(k, true, 1_000_000, 1).unwrap();
let t = Instant::now();
for &x in &keys {
    c.increment(x as u128).unwrap();
}
let dt = t.elapsed();
```

Add multi-thread arms using scoped threads and disjoint key ranges, following `parallel_count_tests.rs` lines 168-205. Join every handle and propagate failures; do not discard worker results.

The arms must isolate mechanisms, not just report another end-to-end number:

1. Shared `KmerCounter`: production DashMap access plus per-window `total_kmers.fetch_add` and insert-time `unique_kmers.fetch_add`.
2. Shared raw `DashMap<u64, u32>`: identical `entry().and_modify().or_insert_with()` table work without the two global counters.
3. Atomic-only control: the same number of shared `AtomicU64` increments without table traffic.
4. Thread-local tables/counters with end reduction: locality/bandwidth control, included as evidence rather than a production engine implementation.

The production operations being isolated are visible at `src/hash/table.rs` lines 259-310; `total_kmers` uses `Ordering::Relaxed` after every successful table increment. Reproduce that operation in the microbenchmark; do not make the private table public or edit production code for measurement.

Add `--threads`, `--reps`, `--variant`, `--input`, and `--json <path>` arguments. Emit per-rep records with variant, threads, k, reads, windows, elapsed ns/window, unique/total conservation checks, and provenance. Persist raw records and derived atomics-vs-bandwidth attribution in `contention_evidence.json`, not inline prose.

---

### `.planning/research/profiling/microbench_Cargo.toml` (modify; standalone config)

**Analog:** itself.

Preserve the isolated workspace and release optimization at lines 9-14:

```toml
[profile.release]
lto = true
codegen-units = 1
opt-level = 3

[workspace]
```

Add direct microbenchmark-only dependencies for raw DashMap and any JSON support used; transitive crates cannot be imported merely because `rustkmer` depends on them. Keep `rust-version = "1.80"` and edition 2021 explicit, and use the same locked `dashmap 6.2.1` line as production. This standalone manifest is not permission to add dependencies to the production crates.

---

### `scripts/bench/python_bench.py` (new; Python benchmark service + worker mode)

**Analogs:** `bench.py`, `pyo3/tests/test_counter.py`, `pyo3/README.md`, and `pyo3/pyproject.toml`.

Use one file with an outer controller and a `--worker` mode. The controller invokes a fresh worker via `bench.measure([sys.executable, __file__, "--worker", ...])`, ensuring OS wall/RSS includes the real sequential PyO3 file-counting pipeline. Do not copy `tests/performance/test_fuzzy_query_performance.py`: it uses an obsolete import and harness-internal `time.time()` rather than the release/OS-rusage protocol.

The worker should mirror `test_counter.py` lines 545-550:

```python
counter = pyrustkmer.PyCounter(21, canonical=True, threads=1)
counter.add_from_fastq(str(fastq_file))
stats = counter.get_stats()
assert stats.total_kmers > 0
assert stats.unique_kmers > 0
```

Emit stats as JSON on stdout for controller validation. Unlike pytest, a missing/stale extension is an invalid benchmark (exit 2), not `pytest.skip`.

Rebuild before capture using the source-install pattern at `pyo3/README.md` lines 36-44 (`maturin develop --release`), with the phase-specified `.venv313` Python and `CONDA_PREFIX` unset. Assert the imported module is the newly loaded one before timing.

Hash `pyrustkmer.__file__`: `pyo3/pyproject.toml` lines 73-82 confirms this is a pure-Rust extension named `pyrustkmer`, with no Python shim:

```toml
[tool.maturin]
features = ["pyo3/extension-module"]
module-name = "pyrustkmer"
manifest-path = "Cargo.toml"
```

Record module sha256, path, Python executable/version, git HEAD/dirty state, release build profile, maturin version, and Rust toolchain in every result. Reuse `bench.py` medians/cache-state/provenance helpers and `compare.py` platform/baseline semantics.

---

### `scripts/bench/n_read_differential.py` (new; CLI/PyO3 differential)

**Analogs:** `pyo3/tests/test_counter.py`, `pyo3/tests/test_export.py`, and `bench.py`.

Build deterministic four-line FASTQ records following `test_counter.py` lines 577-588. Cover no-N control plus N at the first/last/base-of-k-window positions, multiple Ns, lowercase N, record boundaries, and reads shorter than k. Use `canonical=True` and `threads=1` on both surfaces.

Count through the CLI into a temporary `.rkdb`; count the same bytes through `PyCounter.add_from_fastq`. Obtain Python counts with `get_all_counts`, whose order-independent dict comparison is demonstrated at `test_counter.py` lines 1062-1082:

```python
counter1 = pyrustkmer.PyCounter(21, canonical=True, threads=1)
counter1.add_from_fastq(str(fastq_file))
counts_1 = counter1.get_all_counts()
assert counts_1 == counts_4
```

For the CLI map, load the resulting database with `PyDatabase(..., LoadMode.Preload)` and use `export_all_kmers()`; `pyo3/src/database.rs` lines 2043-2060 documents that no limit exports all records and each result has decoded `kmer` and `count`. This avoids adding a second binary RKDB decoder and avoids relying on prose output.

Persist per-case maps or compact symmetric-difference records, CLI/Python distinct and sum-of-counts, chimeric keys present only in Python, missing skip-N keys, input sha256, and binary/module provenance. The no-N control must be equal; N-containing cases are expected to diverge before Phase 9. This phase records D2 evidence and does not “fix” either surface.

---

### `scripts/bench/tests/test_degradation.py` (modify; random-slice tests)

**Analogs:** itself and `test_generator.py`.

Reuse `build_gz_fixture` (lines 31-42) and the byte-determinism assertions at lines 200-210. Add tests that two identical random-slice invocations produce identical bytes and selection manifest, different seeds select different records, every selected record is four complete lines, output count is exact, and selected indices are within source range.

Also test small-input behavior (`N > available`), empty/malformed FASTQ, nonnumeric/zero counts, missing input, and that selection is not simply the first N records. Keep the existing first-N `make_slice.sh` tests untouched to prevent an accidental behavior change.

Copy the hash-based determinism style from `test_generator.py` lines 44-54:

```python
def test_same_seed_same_sha256(self):
    a = self.run_gen("a.fq")
    b = self.run_gen("b.fq")
    self.assertEqual(sha256_of(a), sha256_of(b))
```

---

### `scripts/bench/tests/test_schema.py` (modify; provenance/schema tests)

**Analog:** itself.

Extend `_minimal_results` (lines 47-61) only in new provenance-specific fixtures; retain the existing minimal v1 case to prove old committed baselines still load. Add positive tests for binary sha256 + git commit + build profile and negative tests for missing/empty/wrongly typed provenance fields.

Follow the existing rejection pattern at lines 63-89: mutate one field, assert `ValueError`, and name the missing contract in the test. Add a real small synthetic run assertion analogous to lines 27-41 that provenance identifies the actual `target/release/rustkmer` bytes, not merely the string supplied on the command line.

For Python results, add a fixture proving the native module fingerprint is distinct from the CLI fingerprint and includes the Python executable/version.

---

### `scripts/bench/tests/test_thread_scaling.py` (new; gate unit tests)

**Analog:** `scripts/bench/tests/test_compare.py`.

Copy `CompareHarness` lines 64-83 to invoke `main(argv)` directly and capture `SystemExit`, stdout, and stderr:

```python
out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    with self.assertRaises(SystemExit) as ctx:
        compare.main(["--baseline", str(base_path),
                      "--current", str(cur_path), *extra])
return ctx.exception.code, out.getvalue(), err.getvalue()
```

Use synthetic timing docs; do not sleep in unit tests. Cover: materially different t1/t4/t16 medians exits 0; identical medians exit 1; insufficient scaling exits 1; threshold equality follows the chosen boundary; missing t4/t16 arm, count mismatch, zero count, malformed provenance, and platform mismatch exit 2. Include a mutation test proving that changing only count maps cannot make a no-op timing matrix pass, and changing only timings cannot hide a parity failure.

---

### `scripts/bench/tests/test_python_bench.py` (new; Python harness tests)

**Analogs:** `test_schema.py` and `test_generator.py`.

Keep controller logic unit-testable without importing PyO3: fake `measure` results and worker JSON, then assert median reduction, schema validation, nonzero-count sanity, platform-specific baseline selection, and exit 0/1/2 behavior. Use `tempfile.TemporaryDirectory` and list-form subprocesses from `test_schema.py` lines 27-41.

Add one opt-in integration test only when an environment variable points at the freshly built `.venv313` extension. It must assert module path/sha provenance and a nonzero count. The default stdlib unit suite must remain runnable without PyO3, NumPy, pytest, or the human dataset.

---

### `scripts/bench/tests/test_n_read_differential.py` (new; differential logic tests)

**Analogs:** `test_compare.py` and `pyo3/tests/test_counter.py`.

Unit-test pure map-difference reduction with hand-built dictionaries: equal no-N maps, Python-only chimeric key, unequal count for a shared key, and missing key on Python. Assert exact symmetric-difference counts and stable JSON ordering.

Test FASTQ fixture construction using the four-line shape at `test_counter.py` lines 579-588 and assert every requested N position. Keep the real CLI/PyO3 execution opt-in; a differential artifact with no records, a missing control, or failed child process is invalid, never an empty PASS.

---

### `scripts/bench/baselines/slice_parity.crr1936095.json` (new; parity reference)

**Analogs:** `.planning/research/profiling/parity_report.json` and `evidence.json`.

Copy the explicit two-tool count record from `parity_report.json` lines 2-13:

```json
{
  "rustkmer": {"records": 229694874, "sum_counts": 519271168},
  "jellyfish": {"Distinct": 229694874, "Total": 519271168},
  "parity": "PASS"
}
```

Add schema version, dataset accession, source path/fingerprint, slice kind (`head-4M-profiling-reference` versus `random-record`), read count, selection seed/indices manifest for random slices, k/canonical, reference tool version, expected distinct/total, and binary provenance. Copy dataset facts from `evidence.json` lines 5-10 rather than retyping prose as the source of truth.

The head-4M reference and each random subslice are separate records. Never reuse expected counts across different input fingerprints.

---

### `scripts/bench/baselines/python_bench_baseline.{darwin,linux}.json` (new; platform baselines)

**Analogs:** existing `bench_baseline.darwin.json` / `.linux.json` and `scripts/bench/README.md`.

Preserve the existing baseline envelope: schema version, platform flavor, mode, created/generated timestamps, input fingerprints, params, host note, and nonempty arms with wall/RSS reps and distinct/total sanity values (`bench_baseline.darwin.json` lines 1-64). Add Python module provenance and Python worker params.

Follow the platform rule in README lines 59-74: absolute numbers never cross platforms. A CI-consumed baseline must be generated from that CI runner's uploaded artifact (README lines 76-105), not copied from the M4 Max development host. A dev-host baseline used for Phase 9 local comparison must be labeled with its host/runner class and must not be presented as a CI baseline.

---

### `.planning/phases/05-measurement-regression-harness/contention_evidence.json` (new; measured evidence)

**Analog:** `.planning/research/profiling/evidence.json` lines 37-47.

Use named numeric fields like the existing `microbench_ns_per_window_single_thread` and `parallel_scaling` objects. Include raw per-rep arms, thread counts, input fingerprint, cache state, binary provenance, conservation checks, and derived differences/ratios:

- `shared_counter_ns`
- `shared_dashmap_without_global_atomics_ns`
- `atomic_only_ns`
- `thread_local_ns`
- `global_atomics_attribution_ns` / `_pct`
- `memory_bandwidth_attribution_ns` / `_pct`

State the subtraction formula in a versioned `method` field so the attribution is reproducible. Do not store only the final 9.4x multiplier or a prose conclusion.

---

### `.planning/phases/05-measurement-regression-harness/n_read_differential.json` (new; measured evidence)

**Analogs:** `parity_report.json`, `evidence.json`, and `bench.py::fingerprint`.

Use one record per N-position case with a no-N control. Include input sha256, read/sequence literals for the small fixture, CLI and Python stats, count-map differences, example chimeric k-mers, both executable/module fingerprints, git/build provenance, and the current expected semantic (`CLI=skip-N-windows`, `Python=strip-and-join-pre-Phase-9`). This is evidence for D2, not a regenerated golden and not a new semantic contract.

---

### `.planning/phases/05-measurement-regression-harness/golden_capture.json` (new; immutable capture evidence)

**Analogs:** `tests/golden_generate.rs`, `tests/golden_sha256_tests.rs`, and `tests/fixtures/golden_manifest.sha256`.

The existing generator already covers the full matrix at lines 55-68: `k ∈ {21,32,64} × canonical × sorted`. Its manifest writer is deterministic and name-sorted (lines 202-209). Reuse those 12 committed files and hashes as the pre-refactor ground truth.

Record capture timestamp, source git HEAD/dirty state, binary sha256/profile, the manifest's own sha256, and all 12 filename/hash pairs in `golden_capture.json`. Run `golden_rkdb_sha256_unchanged_post_dense` and record its result. Do **not** run the ignored generator over the committed fixtures.

Copy the discipline stated at `golden_sha256_tests.rs` lines 29-31: goldens are ground truth, never regenerated to make a diff green. Also retain the warning at lines 174-186 that rehashing static fixtures does not exercise the writer; Phase 8 still needs an actual old-vs-new write-path differential.

---

### `scripts/bench/README.md` (modify; maintainer procedures)

**Analog:** itself.

Extend the existing quick-run and baseline sections rather than creating separate harness documentation. Document commands for random slice + parity, t1/t4/t16 scaling, live pool-size observation, contention microbench, Python rebuild/baseline, and N-read differential. Document every artifact's provenance fields and expected current RED gates.

Copy the existing fail-loud bootstrap stance (lines 76-105) and per-platform regeneration discipline (lines 107-154). Update the layout at lines 194-204. Explicitly distinguish expected-RED PROF-02 evidence from ordinary regressions and prohibit `continue-on-error`, `|| true`, or baseline recapture to silence a gate.

---

### `.github/workflows/benchmark.yml` (modify; standing CI gates)

**Analog:** itself.

Preserve the existing release-build -> upload -> gate order at lines 70-87. Upload result/contention/Python artifacts **before** comparator steps so invalid or missing baselines still leave evidence. Keep synthetic/degraded inputs for ordinary CI; real CRR1936095/Jellyfish gates run where their explicit inputs/tools exist, not as hidden CI skips.

The workflow's comments at lines 8-14 are the controlling pattern: gate semantics live in scripts, with no error swallowing, exit-code laundering, or conditional softening. Add harness unit tests, thread-scaling and Python baseline steps using their script exit codes directly. PROF-02 is expected RED until Phase 6; the planner must surface how the milestone handles that intentional red rather than hiding it with `continue-on-error`.

---

### `.github/workflows/ci.yml` (modify; MSRV-aware clippy)

**Analog:** itself.

Keep test jobs on stable, but pin **both clippy jobs** to Rust 1.80 with the clippy component. The root pattern is lines 48-69:

```yaml
- uses: dtolnay/rust-toolchain@stable
  with:
    components: clippy
- run: cargo clippy --locked --all-targets -- -D warnings
```

The PyO3 equivalent is lines 105-127, including its separate `pyo3/target` cache and `working-directory: pyo3`. Change the toolchain input to `1.80.0` (or the repo's normalized `1.80` form) for these two jobs, retain `--locked --all-targets -- -D warnings`, and preserve separate cache namespaces.

Local prerequisite, not a source edit: `rustup toolchain install 1.80.0 --component clippy` and run both crates' clippy with that toolchain. Do not add a root `rust-toolchain.toml` merely as a side effect; stable test/build jobs are an existing intentional convention.

## Shared Patterns

### Fail-loud subprocess and gate exits

**Sources:** `scripts/bench/bench.py` lines 137-150; `compare.py` lines 74-101 and 210-277.
**Apply to:** every new Python controller and CI-called script.

- List-form argv except the existing tightly screened Jellyfish gzip pipe.
- Nonzero child exits raise with trailing stderr.
- 0 = measured gate passes; 1 = measured regression/no-op/divergence where that is the gate condition; 2 = invalid/missing/unparseable input or unavailable required tool.
- CI trusts script exits; never `|| true`, `continue-on-error`, or silently skip a missing baseline.

### Parity before timing

**Sources:** `bench.py` lines 540-594 and 851-864; `parity_report.json`.
**Apply to:** random slice benchmark, thread scaling, any Python baseline used for later performance claims.

Assert nonzero counts and identical semantics on the measured input before wall times are trusted. A mismatch is methodology evidence, not a reason to alter rustkmer counts.

### Measurement and reduction

**Sources:** `bench.py` lines 100-150, 617-681, and 701-768.
**Apply to:** slice, scaling, Python, and contention controllers.

Use `/usr/bin/time` for whole-process wall/RSS, counterbalanced reps where tools are compared, one discarded warmup per tool, cooldowns, honest per-rep cache state, medians, and CV warnings. Do not introduce `time.time()` micro-benchmark assertions into pytest.

### Deterministic inputs and degradation

**Sources:** `gen_synthetic.py` lines 16-28 and 52-54; `bench.py` lines 333-383; `test_degradation.py`.
**Apply to:** all gates.

Fixed seed before sampling/generation, input sha256 on every artifact, explicit full/slice/synthetic mode resolution, and no fabrication of real-data parity when data/Jellyfish is absent. Random-record selection is mandatory for new representativeness checks; retain first-N only for the pinned historical reference.

### Provenance

**Sources:** `bench.py::fingerprint` lines 268-276; `evidence.json`; `pyo3/pyproject.toml` lines 73-82.
**Apply to:** every results/evidence artifact, including microbench and N differential.

Hash the actual CLI binary or native `pyrustkmer` module, record git HEAD + dirty state + build profile, and include input fingerprints and platform/toolchain. A path string without a hash is not provenance.

### Golden immutability and differential validity

**Sources:** `tests/golden_generate.rs`; `tests/golden_sha256_tests.rs` lines 13-39 and 316-336.
**Apply to:** golden capture and Phase 8 handoff.

Never regenerate a baseline after the code it is meant to judge changes. Static fixture rehashing detects fixture tampering only; meaningful old-vs-new proof must drive the production write path against an independent reference.

### Python rebuild discipline

**Sources:** `pyo3/README.md` lines 36-44; `pyo3/pyproject.toml` lines 73-87; phase CONTEXT.
**Apply to:** Python baseline and N differential.

Use `.venv313`, unset `CONDA_PREFIX`, run `maturin develop --release`, then import and fingerprint the loaded native module before measurement. Do not copy outdated scripts that import `rustkmer_pyo3` or assume a Python shim.

## No Single Analog Found (Composite Required)

No proposed file is wholly without a usable analog. These capabilities require composing the cited files rather than copying one file verbatim:

| File | Missing single capability | Required composition |
|---|---|---|
| `tests/thread_pool_size_tests.rs` | Existing Rust tests do not observe a live CLI rayon pool; `verify_threads.py` is macOS-only and prose-based | Cargo CLI subprocess pattern + hardened cross-platform `verify_threads.py` |
| `.planning/research/profiling/microbench_main.rs` | Existing microbenchmark is single-threaded | Existing increment-only arms + scoped-thread differential + raw DashMap/atomic controls |
| `scripts/bench/python_bench.py` | No current benchmark measures `PyCounter.add_from_fastq`; old performance pytest uses the wrong API and internal clocks | `bench.py` OS timing/schema + `PyCounter` worker + native-module provenance |
| `scripts/bench/n_read_differential.py` | Existing N tests assert only `total_kmers > 0`, not CLI/Python map divergence | CLI subprocess + `PyCounter` + `PyDatabase.export_all_kmers` + evidence schema |

## Metadata

**Analog search scope:** `scripts/bench/`, `.planning/research/profiling/`, `tests/`, `pyo3/tests/`, `pyo3/src/`, `src/hash/`, `src/cli/commands/`, `.github/workflows/`
**Files scanned:** 39 read in full or targeted non-overlapping sections, plus tracked-file/name/content searches across the directories above
**Tracked-source gate:** every analog path cited here was verified with `git ls-files`; no cache, `__pycache__`, installed-module, target, or runtime-mirror path is used
**Pattern extraction date:** 2026-11-12
