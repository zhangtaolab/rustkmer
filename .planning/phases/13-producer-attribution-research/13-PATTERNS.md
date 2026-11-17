# Phase 13: Producer Attribution Research - Pattern Map

**Mapped:** 2026-11-17
**Files analyzed:** 6 (5 new artifacts + 1 modified planning doc)
**Analogs found:** 6 / 6 (one composed rather than copied — see No Analog Found)

**Phase character:** measurement-only. Zero Rust source changes land; every Rust file
named below is a READ-ONLY instrument analog or a template for driver-materialized
scratch builds (never committed). Tracked-source gate satisfied: every analog path in
this document was verified with `git ls-files` (all print non-empty).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/bench/phase13.py` (name is planner discretion per D-01) | harness driver (utility CLI) | batch orchestration + subprocess invocation + evidence emission | `scripts/bench/merge_characterize.py` | exact |
| `scripts/bench/phase13.py` — staged verbs / exit codes / doc validation | harness driver | same | `scripts/bench/phase11.py` | exact (complementary) |
| Probe materialization (arm C k=31 probe + arm D null consumer — template strings in the driver, built in `/tmp` scratch, never committed) | generated build inputs (Rust microbench) | transform (read → parse → extract → discard) | `scripts/bench/contention_bench.py` + `.planning/research/profiling/microbench_Cargo.toml` + `examples/engine_probe.rs` | exact for materialization; composed for the probe bodies |
| `scripts/bench/tests/test_phase13_driver.py` | test (stdlib unittest) | fixture-driven pure functions | `scripts/bench/tests/test_merge_arms.py` | exact (conventions) |
| `.planning/phases/13-producer-attribution-research/13-ATTRIBUTION.json` | evidence data artifact (D-01/D-02) | write-once JSON, incremental per arm-k | `.planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json` | exact (shape) |
| `.planning/phases/13-producer-attribution-research/13-GATE-MEMO.md` | committed markdown deliverable (D-02) | rendered from evidence JSON | `scripts/bench/phase11.py` `run_render`/`render_report_text` → artifact precedent `12-MERGE-REPORT.md` | role-match |
| `.planning/ROADMAP.md` §Phase 14 (modified — conditional annotation pointing at the memo) | planning doc | one-line edit | n/a (documentation edit, no code pattern) | n/a |

## Pattern Assignments

### `scripts/bench/phase13.py` (harness driver, batch orchestration + evidence emission)

**Primary analog:** `scripts/bench/merge_characterize.py`

**Module header contract** (lines 2, 48-49) — copy the docstring discipline: state
the phase decisions served, the stdlib-only contract, the evidence-kind boundary:

```python
#!/usr/bin/env python3
"""Two-point merge-characterization ladder (Plan 11-06, D-07/D-08/D-09).
...
Python 3.11+ stdlib only — no third-party imports, no pip installs (the
bench-harness stdlib-only contract, bench.py:25-26).
"""
```

**Import block** (lines 52-93) — stdlib first, then the checkout-root fixup, then
named imports from the harness primitives. Phase 13 needs the same list minus
jellyfish/slice functions, plus `rotation_schedule` from `output_stage`:

```python
if __package__ in (None, ""):
    # Direct script execution needs the checkout root for the scripts package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    fingerprint,
    parse_time_output,
    reduce_arm,
    rustkmer_count_cmd,
)
from scripts.bench.prepare_inputs import (
    DEFAULT_DATA_DIR, DEFAULT_RUSTKMER,
    refuse_repo_root, run_command,
)
from scripts.bench.output_stage import rotation_schedule

HERE = Path(__file__).resolve().parent            # scripts/bench/
REPO_ROOT = HERE.parent.parent                    # repo root

SCHEMA_VERSION = 1
KIND = "merge-characterization-ladder"            # phase13: its OWN kind, never a fork (MBENCH-05)
DEFAULT_RESULTS = (REPO_ROOT / ".planning" / "phases" / "...phase-dir..." / "13-ATTRIBUTION.json")
```

**Measured run — /usr/bin/time, fail-loud, units-pinned** (`measured_run`, lines
146-167; twin primitive `bench.measure` at `bench.py:228-241`). Harness-internal
clocks are banned; `/usr/bin/time` is the only clock:

```python
def measured_run(argv):
    plat = sys.platform
    time_flag = "-l" if plat == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag, *[str(a) for a in argv]],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return parse_time_output(proc.stderr, plat), proc.stderr
```

**Disk arithmetic before heavy I/O (D-04)** (`free_bytes` + `ensure_free_space`,
lines 328-356) — reuse verbatim; phase13 checks free space BEFORE the plain-input
decompression:

```python
def ensure_free_space(path, min_free_gb):
    free = free_bytes(path)
    required = int(min_free_gb * (1 << 30))
    if free < required:
        raise RuntimeError(
            f"ladder disk guard: {free} bytes free on the scratch volume "
            f"({path}) but the ladder requires {required} bytes "
            f"({min_free_gb} GiB) — aborting before provisioning; free "
            "space or re-point --scratch")
```

**Zero-entry guard** (`_guard_zero`, lines 359-368) — the fail-loud pattern for
probe JSON and run outputs (RESEARCH Pitfall: probe JSON missing k → loud abort):

```python
def _guard_zero(label, distinct, total, stage):
    if distinct is None or total is None or distinct <= 0 or total <= 0:
        raise RuntimeError(
            f"zero-entry protection: {label} produced distinct={distinct!r} "
            f"total={total!r} after {stage} — a zero-count artifact is a "
            "loud rung abort, never an input to downstream builds or a "
            "measurement (probe MBENCH-01/empty)")
```

**Summary math as pure functions over records** (`fit_slope` + `build_summary`,
lines 663-790) — the structural analog for phase13's attribution/predicted-win
functions: pure, deterministic, refuse-to-invent when an input is missing:

```python
            else:
                entry["slope_wall_s_per_entry"] = None
                entry["ratio_40_over_10"] = None
                entry["linear"] = None
                entry["note"] = ("second scale point missing — slope "
                                 "undetermined, never invented")
```

**Evidence doc I/O** (`new_doc`/`load_doc`/`upsert_rung`/`write_doc`, lines
796-847) — the exact lifecycle for `13-ATTRIBUTION.json`, including the
never-merge-across-kinds guard:

```python
def new_doc():
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "rungs": [],
        "summary": {},
        "scratch_cleaned": False,
        "created": _now_iso(),
    }

def load_doc(path):
    path = Path(path)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("kind") != KIND:
        raise ValueError(
            f"{path} is not a {KIND!r} document (kind="
            f"{doc.get('kind')!r}) — refusing to merge across kinds")
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} carries schema_version {doc.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION}")
    return doc

def upsert_rung(doc, record):
    rungs = [r for r in doc.get("rungs", [])
             if not (r.get("n_reads") == record["n_reads"]
                     and r.get("k") == record["k"])]
    rungs.append(record)
    rungs.sort(key=lambda r: (r["n_reads"], r["k"]))
    doc["rungs"] = rungs

def write_doc(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
```

**Incremental write-per-run + CLI + exit-code handling** (`main`, lines 866-965;
error mapping at 964-965) — evidence is written after EVERY arm-k so a crashed
session keeps completed records:

```python
        for n, seed, k in planned:
            record = run_rung(...)
            upsert_rung(doc, record)
            doc["summary"] = build_summary(doc["rungs"])
            write_doc(args.results, doc)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
```

**Secondary analog — staged verbs, reserved exit codes, strict doc validation:**
`scripts/bench/phase11.py`

**Exit-code contract** (lines 105-107) — RESEARCH §Evidence & Memo Structure
adopts this shape (0 = memo recorded, either GO or NO-GO; 2 = infrastructure,
no artifact):

```python
EXIT_OK = 0        # valid result (the verdict stage's measured YES)
EXIT_NO = 1        # a genuine measured NO (artifact kept/published)
EXIT_INVALID = 2   # invalid/inapplicable (no artifact written)
```

**D-03 fingerprint-gate analog — `assert_binary_identity`** (lines 208-234).
IMPORTANT polarity difference: phase11 RAISES on mismatch (rebuilt binary
invalidates attribution); phase13's D-03 gate BRANCHES — match → cite v2.0 walls
as base, mismatch → force fresh arm-A base. Copy the mechanics (compare actual
executable bytes via `binary_provenance`, name both hashes), invert the outcome:

```python
def assert_binary_identity(provenance_fn=None):
    provenance_fn = binary_provenance if provenance_fn is None else provenance_fn
    rust_prov = provenance_fn(DEFAULT_RUSTKMER, "release")
    ...
    rust_sha = rust_prov["binary"]["sha256"]
    if rust_sha != RUSTKMER_BIN_SHA256 or jf_sha != JELLYFISH_BIN_SHA256:
        raise RuntimeError(
            "binary identity tripwire: rustkmer sha256 "
            f"{rust_sha} (expected {RUSTKMER_BIN_SHA256}) / ...")
```

**Memo-render stage** (`run_render`, lines 1784-1851) — the D-02 memo pattern:
render deterministically from validated evidence docs, prove byte-identical
re-render, publish atomically; committed artifact precedent is
`.planning/phases/12-full-scale-merge-verdict/12-MERGE-REPORT.md`:

```python
        text = render_report_text(docs)
        text_again = render_report_text(docs)
        if text != text_again:
            raise RuntimeError(
                "render: re-render is not byte-identical — the renderer is "
                "carrying nondeterminism (a clock read, iteration order, or "
                "an unstable environment read); refusing to publish a proof")
        ...
        publish_atomic([
            (out_path, text),
            (proof_path, json.dumps(proof_doc, indent=2) + "\n"),
        ])
```

**Verdict-document shape** (`run_verdict`, lines 1732-1781) — the gate-memo
carrier pattern: decision + rule + inputs + provenance, `validate_provenance`
before write, both outcomes are valid recorded results:

```python
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
```

---

### Probe materialization (arm C k=31 variant + arm D null consumer; driver-embedded templates, built in `/tmp` scratch)

**Analog:** `scripts/bench/contention_bench.py` (Phase 5 precedent) + `.planning/research/profiling/microbench_Cargo.toml`

**Repo-root resolution from `__file__`, never user strings** (`contention_bench.py:85-94`) — the substitution target cannot be pointed at another tree:

```python
# T-05-09: the repo root is resolved from THIS file's location, never from
# user strings — the template substitution cannot be pointed at another tree.
REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILING_DIR = REPO_ROOT / ".planning" / "research" / "profiling"
```

**Manifest template with `@REPO_ROOT@` placeholder + `[workspace]` exemption**
(`microbench_Cargo.toml`, whole file, 26 lines) — phase13's scratch manifest
copies this shape; deps are microbench-only and already in the production
lockfile (`serde_json`; phase13 adds `bio` for the parse-stage instrument, same
class as the precedent's `dashmap`):

```toml
[package]
name = "rk-microbench"
version = "0.1.0"
edition = "2021"
rust-version = "1.82"

[dependencies]
# Template placeholder: the controller (scripts/bench/contention_bench.py)
# substitutes the repo root resolved from its own __file__ at materialization.
rustkmer = { path = "@REPO_ROOT@" }
dashmap = "=6.2.1"
serde_json = "1.0"

[profile.release]
lto = true
codegen-units = 1
opt-level = 3

[workspace]
```

**Materialize + lockfile-verify + build** (`materialize_crate` +
`verify_scratch_lockfile`, `contention_bench.py:152-197`) — copy template into
scratch, substitute `@REPO_ROOT@`, verify sha256 of the lock, build
`--release --locked --manifest-path <scratch>/Cargo.toml`, fingerprint the
resulting binary per run (phase13 adds the `refuse_repo_root` guard on the
scratch root — scratch lives in `/tmp`, never in-repo):

```python
def materialize_crate(repo_root=REPO_ROOT, crate_dir=CRATE_DIR):
    for src in (main_src, toml_src, lock_src):
        if not src.is_file():
            invalid(f"microbench template file missing: {src}")
    (crate_dir / "src").mkdir(parents=True, exist_ok=True)
    (crate_dir / "src" / "main.rs").write_bytes(main_src.read_bytes())
    template = toml_src.read_text(encoding="utf-8")
    if "@REPO_ROOT@" not in template:
        invalid(f"manifest template has no @REPO_ROOT@ placeholder: {toml_src}")
    (crate_dir / "Cargo.toml").write_text(
        template.replace("@REPO_ROOT@", str(repo_root)), encoding="utf-8")
    return verify_scratch_lockfile(crate_dir, lock_src)
```

**Probe .rs body — committed k=21 instrument** (`examples/engine_probe.rs`,
lines 1-97). The k=31 variant copies this structure and changes ONLY: k from
argv (asserted into the output JSON — RESEARCH Pitfall 8), retaining
`canonical=true` to match the arms' `-C`:

```rust
//! Build and run:
//! cargo build --release --locked --features profiling --example engine_probe
//! target/release/examples/engine_probe <input-path> <fasta|fastq> <threads>

use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};
...
    let config = EngineConfig::new(21, true, threads, 1_000_000);   // :45 — k HARDCODED; the k=31 variant takes k from argv
    let mut engine = match CountEngine::new(config) { ... };
    if let Err(error) = engine.count_file(&input, kind) { ... }     // exit 2 on every failure — fail-loud throughout
    let result = engine.finish()?;
    let Some(diagnostics) = result.diagnostics() else { ... };
    let document = serde_json::json!({
        "input": input.display().to_string(),
        "threads": threads,
        "wall_nanos": diagnostics.wall_nanos,
        "producer_nanos": diagnostics.producer_nanos,
        "workers": workers,     // per-worker {"batches":…, "busy_nanos":…}
    });
    println!("{document}");
```

**Arm D null consumer — core call is public** (`src/kmer/extract.rs:74-98`,
doctest + signature). The null-consumer probe times `bio::io::fastq::Reader`
record loops (exactly as `count_file_inner` does) feeding `for_each_window`
with a discard emit closure:

```rust
/// use rustkmer::kmer::extract::for_each_window;
/// let summary = for_each_window(b"ACGTNACG", 3, false, |value| {
///     windows.push(value);
///     Ok::<(), ()>(())
/// })
...
pub fn for_each_window<E, F>(
    seq: &[u8],
    k: usize,
    canonical: bool,
    mut emit: F,
) -> Result<WindowSummary, WindowError<E>>
where
    F: FnMut(u128) -> Result<(), E>,
```

**The parse stage being replicated** (`src/count/engine.rs:803-871`,
`count_file_inner` — READ-ONLY reference for what arm C/D decompose; the
producer span ends BEFORE the flush at :857-864, so probe `producer_nanos`
excludes flush wait):

```rust
    #[cfg(feature = "profiling")]
    let producer_started = Instant::now();
    let (reader, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(...)?;   // read + inflate (:806-812)
    ...
            SequenceKind::Fastq => {
                let reader = bio::io::fastq::Reader::new(reader);
                for record_result in reader.records() {
                    let record = record_result.map_err(...)?;
                    let summary = self.count_sequence(record.seq())?;       // extract + route (:843)
                    ...
    #[cfg(feature = "profiling")]
    {
        self.producer_nanos = self
            .producer_nanos
            .saturating_add(elapsed_nanos(producer_started));               // span ends BEFORE flush (:857-864)
    }
```

---

### `scripts/bench/tests/test_phase13_driver.py` (test, stdlib unittest)

**Analog:** `scripts/bench/tests/test_merge_arms.py` (conventions; RESEARCH
Validation Architecture: discovered via `python3 -m unittest discover -s
scripts/bench/tests -t .`, no pytest/conftest).

**Header + import + fixture-helper conventions** (lines 1-42) — one class per
function under test, stdlib-only, binary-light (no cargo/dataset dependency):

```python
"""Unit tests for the MBENCH-01 merge arm set: builders, ordering, threads.
...
One class per function under test, stdlib unittest only, following
test_merge_input.py conventions.
...the live two-tool comparator run stays out of the unit suite (binary-light).
"""

import unittest

from scripts.bench.bench import (
    assert_arm_ordering,
    assert_merge_parity,
    ...
)

def spec(name, tool):
    """A minimal arm spec for ordering tests (only name and tool matter)."""
    return {"name": name, "tool": tool}
```

Required coverage per RESEARCH §Wave 0 Gaps: fingerprint-gate branch fixtures,
attribution arithmetic on fixture numbers, full-scale-only schema enforcement,
provenance completeness, fail-loud probe parsing, model-completeness (both
ceilings resolved to named records or loud failure).

---

### `13-ATTRIBUTION.json` (evidence artifact, D-01/D-04)

**Analog:** `.planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json`

**Shape to copy** (top level: `created` / `kind` / `rungs` / `summary` /
`scratch_cleaned`; per-run records embed full `command_line` list-form argv,
sha256s, and honest labels — see lines 1-50 of the analog). Phase 13's doc:

```json
{
  "created": "<UTC ISO>",
  "kind": "phase13-producer-attribution",
  "runs": [ { "arm": "A|B|C|D|control", "k": 21, "rep": 1,
              "scale": "full",
              "wall_s": 0.0, "peak_rss_bytes": 0, "peak_bytes": 0,
              "cache_state": "unavailable",
              "command_line": ["..."],
              "binary_sha256": "...", "input_sha256s": ["..."],
              "thermal": "...", "created": "..." } ],
  "fingerprint_gate": { "current_sha256": "...", "v2_0_sha256": "...", "branch": "re-measure" },
  "attribution": { "per_k": { "21": { "inflate_s": {}, "parse_extract_s": {}, "route_send_s": {}, "output_stage_s": {} } } },
  "predicted_win": { "both ceilings, every input cited to a named run record" },
  "scratch_cleaned": false
}
```

Rules carried from the analog: `scale` field on every record and the
memo-derivation REFUSES non-`full` records (RESEARCH Pitfall 5); kind is its
own — never a fork of bench results schema v1; provenance block passes
`bench.validate_provenance` (`bench.py:458-499`).

---

### `13-GATE-MEMO.md` (D-02 committed memo)

**Analog:** `phase11.py run_render` (excerpts above) + artifact precedent
`.planning/phases/12-full-scale-merge-verdict/12-MERGE-REPORT.md` (verified
git-tracked). Structure per RESEARCH §Evidence & Memo Structure: (1) decision +
pre-registered bar; (2) stage table at both k with per-cell citations; (3)
predicted-win model, both ceilings, arithmetic shown; (4) fresh-base statement +
v2.0 corroboration with fingerprint delta disclosed; (5) D-03 gate provenance
(both sha256s); (6) revisit conditions on NO-GO; (7) D-04 lifecycle/deletion
record. Render deterministically from the evidence JSON (byte-identical
re-render proof) so the memo is a pure projection of recorded evidence.

### `.planning/ROADMAP.md` §Phase 14 (modified)

One-line conditional annotation pointing at `13-GATE-MEMO.md` (D-02). No code
pattern; text edit only.

---

## Shared Patterns

### Provenance on every run
**Source:** `scripts/bench/bench.py:384-392` (`fingerprint`), `:425-455`
(`binary_provenance`), `:458-499` (`validate_provenance`)
**Apply to:** every run record in `13-ATTRIBUTION.json`; the D-03 gate block;
both probe binaries (each probe build is fingerprinted separately — three
distinct binaries exist: stock CLI, stock probe, research-local probes)

```python
def fingerprint(path):
    """{'path', 'size_bytes', 'sha256'} for one input file (threat T-04-02)."""
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"path": str(p), "size_bytes": p.stat().st_size,
            "sha256": h.hexdigest()}
```
`binary_provenance` hashes the ACTUAL executable bytes and records
`git_commit`, `git_dirty` (must be asserted false for the D-03 gate run),
`build_profile`, `rust_toolchain`, `platform`, `created`.

### Measured runs — /usr/bin/time only
**Source:** `scripts/bench/bench.py:161-241` (`parse_time_output`, `measure`);
`merge_characterize.py:146-167` (`measured_run`, keeps stderr)
**Apply to:** arms A/B, controls, probe invocations. Never a harness-internal
clock. `parse_time_output` is units-pinned and raises on any missing line —
never best-effort.

### Fail-loud subprocess + parsing
**Source:** `scripts/bench/prepare_inputs.py:301-314` (`run_command`);
`merge_characterize.py:215-228` (`_run_fail_loud`); `bench.py:184` docstring
stance
**Apply to:** every subprocess (gunzip decompression, cat controls, cargo
builds, probe runs) and every tool-output parse. List-form argv only, no shell;
`json.loads` + schema assertions for probe JSON, never regex-on-prose.

### Honest cache_state
**Source:** `scripts/bench/bench.py:1288-1316` (`cache_state_from`,
`attempt_cache_purge`)
**Apply to:** every measured rep. On this host `sudo -n purge` fails → records
`unavailable`; counterbalancing + cooldown are the real defense.

```python
def attempt_cache_purge(env=None):
    env = os.environ if env is None else env
    if env.get("GITHUB_ACTIONS"):
        return cache_state_from(True, sys.platform, None)
    if sys.platform != "darwin":
        return cache_state_from(False, sys.platform, None)
    proc = subprocess.run(["sudo", "-n", "purge"],
                          capture_output=True, text=True)
    return cache_state_from(False, sys.platform, proc.returncode == 0)
```

### Counterbalanced arm order per rep
**Source:** `scripts/bench/output_stage.py:121-137` (`rotation_schedule`)
**Apply to:** the A/B/(C/D)/control matrix — pure function, schedule persisted
with the records (thermal/order-bias defense, RESEARCH Pitfall 4).

```python
def rotation_schedule(arm_names, reps):
    names = list(arm_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one arm name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]
```

### Medians + CV reduction
**Source:** `scripts/bench/bench.py:1319-1340` (`reduce_arm`)
**Apply to:** every arm-k reduction (median wall, cv_wall_pct, cv_warning) —
the same reduction as every prior verdict.

### Scratch outside the repo + disk guard
**Source:** `scripts/bench/prepare_inputs.py:234-251` (`refuse_repo_root`);
`merge_characterize.py:328-356` (`free_bytes`, `ensure_free_space`)
**Apply to:** plain-inputs root (`/Users/forrest/Data/data/illumina/CRR1936095-plain/`),
`/tmp` probe scratch, per-rep output paths. The D-04 disk check runs BEFORE
decompression.

### CLI-arm command construction
**Source:** `scripts/bench/bench.py:258-304` (`BenchmarkConfig`,
`rustkmer_count_cmd`)
**Apply to:** arms A/B — one config derives the argv; `-i` takes multi-input
(list form), `-C` canonical, `--threads`, `-o` pinned to scratch (RESEARCH Open
Question 4 recommendation: outputs comparable to v2.0 walls):

```python
@dataclasses.dataclass(frozen=True)
class BenchmarkConfig:
    k: int
    canonical: bool = True
    threads: int = 1
    hash_size: str = DEFAULT_HASH_SIZE
    inputs: list = dataclasses.field(default_factory=list)
    decompressor: str = dataclasses.field(default_factory=default_decompressor)

def rustkmer_count_cmd(cfg, out, rustkmer=DEFAULT_RUSTKMER):
    argv = [str(rustkmer), "count", "-k", str(cfg.k)]
    if cfg.canonical:
        argv.append("-C")
    argv += ["--threads", str(cfg.threads), "-o", str(out),
             "-i", *[str(p) for p in cfg.inputs]]
    return argv
```

### Test suite conventions
**Source:** `scripts/bench/tests/test_merge_arms.py:1-42`; suite command in
`scripts/bench/README.md:302`
**Apply to:** `test_phase13_driver.py` — stdlib unittest, one class per
function, binary-light fixtures, `python3 -m unittest discover -s
scripts/bench/tests -t .`

## No Analog Found

| File/Component | Role | Data Flow | Reason | Planner Guidance |
|----------------|------|-----------|--------|------------------|
| Arm D null-consumer probe `.rs` body | generated microbench source | transform (read → parse → extract → discard) | No committed Rust file does parse+extract-without-routing; it is a new composition | Compose from three verified pieces: `engine_probe.rs` argument/JSON/exit-code skeleton, `bio::io::fastq::Reader` record loop (`src/count/engine.rs:835-848`), `rustkmer::kmer::extract::for_each_window(seq, k, canonical, discard)` (`src/kmer/extract.rs:90-98`) |
| Attribution arithmetic + predicted-win model | driver pure functions | compute-over-records | No existing implementation (RESEARCH §Attribution arithmetic is the spec) | Structural analog: `merge_characterize.fit_slope`/`build_summary` (lines 663-790) — pure, refuse-to-invent on missing inputs, every output traceable to a record |
| D-03 gate branch logic | driver decision function | compare-and-branch | Closest analog `phase11.assert_binary_identity` RAISES on mismatch; phase13 BRANCHES (match → cite v2.0 base; mismatch → force fresh arm-A base) | Copy the mechanics (sha256 comparison via `binary_provenance`, both hashes recorded), invert the outcome; also record `git_dirty` must be false for the gate run |
| ROADMAP §Phase 14 annotation | planning doc edit | — | Documentation, no code analog | One-line conditional note pointing at `13-GATE-MEMO.md` |

## Metadata

**Analog search scope:** `scripts/bench/` (drivers, primitives, tests),
`.planning/research/profiling/`, `examples/`, `src/count/`, `src/kmer/`,
`.planning/phases/{11-merge-characterization-harness-prep,12-full-scale-merge-verdict}/`,
`.planning/ROADMAP.md`
**Files scanned:** ~40 (2 full reads > 900 lines, 6 full reads ≤ 725 lines, 7
targeted section reads in large files)
**Tracked-source gate:** all named analog paths verified `git ls-files` non-empty
(including `.planning/research/profiling/microbench_Cargo.toml`,
`11-LADDER-RESULTS.json`, `12-MERGE-REPORT.md`) — no mirror paths emitted
**Key planning facts baked into assignments:** D-03 gate FIRES (current binary
sha256 `4539b893…` ≠ v2.0 `8f38d20c…` → fresh arm-A base is mandatory);
`engine_probe.rs` is k=21-hardcoded (`EngineConfig::new(21, …)` at :45) → the
k=31 arm C probe MUST be a materialized variant taking k from argv with a `k`
field asserted in its output JSON; stock `count` CLI exposes no diagnostics →
arm C/D instruments are library-API probes only
**Pattern extraction date:** 2026-11-17
